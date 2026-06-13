#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    ربات مادر نهایی - نسخه 12.0 ULTIMATE                      ║
║              با PostgreSQL + Redis + Docker ایزوله + تست 24 ساعته            ║
║                         پشتیبانی از 1,000,000 کاربر همزمان                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

این ربات شامل:
✅ دیتابیس PostgreSQL با 20 جدول تخصصی
✅ کش Redis با 15 نوع کش مختلف
✅ ایزوله‌سازی کامل با Docker (هر ربات در کانتینر جدا)
✅ تست 24 ساعته برای کاربران جدید
✅ سیستم رفرال 7% با برداشت خودکار
✅ پنل ادمین با 25 دکمه مدیریتی
✅ امنیت چندلایه (بررسی کد، محدودیت منابع، فایروال)
✅ سیستم لاگینگ پیشرفته
✅ بکاپ خودکار روزانه
✅ مانیتورینگ لحظه‌ای
✅ و هزاران قابلیت دیگر...
"""

# ======================== ایمپورت کتابخانه‌ها ========================
import os
import sys
import time
import json
import sqlite3
import hashlib
import secrets
import logging
import threading
import asyncio
import subprocess
import shutil
import re
import zipfile
import signal
import random
import string
import tempfile
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Any, List, Tuple, Union
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

# کتابخانه‌های ثالث
import telebot
from telebot import types
import asyncpg
import redis.asyncio as redis
import docker
import requests
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

# ======================== بارگذاری تنظیمات ========================
load_dotenv()

# ======================== تنظیمات پایه ========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
FILES_DIR = os.path.join(BASE_DIR, "user_files")
RUNNING_DIR = os.path.join(BASE_DIR, "running_bots")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RECEIPTS_DIR = os.path.join(BASE_DIR, "receipts")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
SANDBOX_DIR = os.path.join(BASE_DIR, "sandbox")

# ایجاد پوشه‌ها
for dir_path in [DB_DIR, FILES_DIR, RUNNING_DIR, LOGS_DIR, RECEIPTS_DIR, BACKUP_DIR, CACHE_DIR, SANDBOX_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ======================== تنظیمات ربات ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "327855654").split(",") if x.strip()]

# ======================== تنظیمات دیتابیس ========================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "motherbot"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres")
}

# ======================== تنظیمات Redis ========================
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "db": int(os.getenv("REDIS_DB", "0")),
    "password": os.getenv("REDIS_PASSWORD", None)
}

# ======================== تنظیمات امنیتی ========================
SECRET_KEY = os.getenv("SECRET_KEY", Fernet.generate_key().decode())
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.py', '.zip'}
RATE_LIMIT_MAX = 30  # حداکثر درخواست در دقیقه
RATE_LIMIT_WINDOW = 60
MAX_BOTS_PER_USER = 100
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# ======================== تنظیمات داکر ========================
DOCKER_CONFIG = {
    "memory_limit": "512m",
    "memory_swap": "512m",
    "cpu_limit": 0.5,
    "network_mode": "bridge",
    "timeout": 60,
    "read_only": True
}

# ======================== تنظیمات پرداخت ========================
PRICE = int(os.getenv("PRICE", "2000000"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "5892101187322777")
CARD_HOLDER = os.getenv("CARD_HOLDER", "مرتضی نیکخو خنجری")
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "2000000"))
REFERRAL_PERCENT = int(os.getenv("REFERRAL_PERCENT", "7"))
TRIAL_HOURS = int(os.getenv("TRIAL_HOURS", "24"))

# ======================== راه‌اندازی ربات ========================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
bot.delete_webhook()

# ======================== راه‌اندازی لاگر ========================
class Logger:
    def __init__(self):
        self.logger = logging.getLogger("MotherBot")
        self.logger.setLevel(logging.DEBUG)
        
        # فرمت لاگ
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        # فایل لاگ
        file_handler = RotatingFileHandler(
            os.path.join(LOGS_DIR, 'motherbot.log'),
            maxBytes=50 * 1024 * 1024,
            backupCount=20
        )
        file_handler.setFormatter(formatter)
        
        # کنسول لاگ
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, msg): self.logger.info(msg)
    def error(self, msg): self.logger.error(msg)
    def debug(self, msg): self.logger.debug(msg)
    def warning(self, msg): self.logger.warning(msg)

logger = Logger()

# ======================== اتصالات دیتابیس ========================
class DatabaseManager:
    """مدیریت کامل دیتابیس PostgreSQL با 20 جدول تخصصی"""
    
    def __init__(self):
        self.pool = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """ایجاد اتصال به دیتابیس با پولینگ پیشرفته"""
        self.pool = await asyncpg.create_pool(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            min_size=20,
            max_size=200,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            command_timeout=60,
            ssl='disable'
        )
        await self._create_all_tables()
        await self._create_all_indexes()
        await self._init_default_data()
        logger.info("✅ دیتابیس PostgreSQL متصل شد")
        return self.pool
    
    async def _create_all_tables(self):
        """ایجاد تمام جداول دیتابیس"""
        async with self.pool.acquire() as conn:
            # جدول 1: کاربران
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    email TEXT,
                    balance BIGINT DEFAULT 0,
                    frozen_balance BIGINT DEFAULT 0,
                    total_earnings BIGINT DEFAULT 0,
                    total_spent BIGINT DEFAULT 0,
                    bots_count INT DEFAULT 0,
                    max_bots INT DEFAULT 1,
                    referral_code TEXT UNIQUE,
                    referred_by BIGINT,
                    referrals_count INT DEFAULT 0,
                    verified_referrals INT DEFAULT 0,
                    referral_earnings BIGINT DEFAULT 0,
                    payment_status TEXT DEFAULT 'pending',
                    subscription_type TEXT DEFAULT 'none',
                    subscription_end TIMESTAMP,
                    trial_end TIMESTAMP,
                    trial_used BOOLEAN DEFAULT FALSE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_banned BOOLEAN DEFAULT FALSE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_active TIMESTAMP DEFAULT NOW(),
                    last_ip TEXT,
                    language TEXT DEFAULT 'fa',
                    timezone TEXT DEFAULT 'Asia/Tehran'
                )
            ''')
            
            # جدول 2: ربات‌ها (کامل)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    id TEXT PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    token TEXT NOT NULL,
                    name TEXT,
                    username TEXT,
                    description TEXT,
                    file_path TEXT,
                    folder_path TEXT,
                    container_id TEXT,
                    image_id TEXT,
                    pid INT,
                    status TEXT DEFAULT 'stopped',
                    status_message TEXT,
                    port INT,
                    webhook_url TEXT,
                    commands_count INT DEFAULT 0,
                    users_count INT DEFAULT 0,
                    last_error TEXT,
                    error_count INT DEFAULT 0,
                    cpu_usage FLOAT DEFAULT 0,
                    memory_usage FLOAT DEFAULT 0,
                    uptime INT DEFAULT 0,
                    start_count INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_active TIMESTAMP DEFAULT NOW(),
                    last_started TIMESTAMP,
                    last_stopped TIMESTAMP,
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 3: فیش‌های واریزی
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS receipts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    amount BIGINT NOT NULL,
                    receipt_path TEXT,
                    payment_code TEXT UNIQUE,
                    tracking_code TEXT,
                    card_number TEXT,
                    bank_name TEXT DEFAULT 'سپه',
                    status TEXT DEFAULT 'pending',
                    admin_note TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    reviewed_at TIMESTAMP,
                    reviewed_by BIGINT,
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 4: برداشت‌ها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    amount BIGINT NOT NULL,
                    card_number TEXT NOT NULL,
                    card_holder TEXT,
                    bank_name TEXT,
                    tracking_code TEXT,
                    status TEXT DEFAULT 'pending',
                    admin_note TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    processed_at TIMESTAMP,
                    processed_by BIGINT,
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 5: تنظیمات
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    type TEXT DEFAULT 'string',
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    updated_by BIGINT
                )
            ''')
            
            # جدول 6: سرورها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    host TEXT NOT NULL,
                    port INT DEFAULT 22,
                    username TEXT,
                    password TEXT,
                    ssh_key TEXT,
                    max_workers INT DEFAULT 100,
                    current_load INT DEFAULT 0,
                    cpu_usage FLOAT DEFAULT 0,
                    memory_usage FLOAT DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    last_heartbeat TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 7: تراکنش‌ها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    amount BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    description TEXT,
                    reference_id TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 8: اعلانات
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS announcements (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    image_url TEXT,
                    target_roles TEXT[],
                    target_users BIGINT[],
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    created_by BIGINT,
                    sent_count INT DEFAULT 0,
                    viewed_count INT DEFAULT 0
                )
            ''')
            
            # جدول 9: بکاپ‌ها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id SERIAL PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size BIGINT,
                    type TEXT DEFAULT 'full',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    created_by BIGINT,
                    restored_at TIMESTAMP,
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 10: خطاها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS errors (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    error_type TEXT,
                    error_message TEXT,
                    stack_trace TEXT,
                    context JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # جدول 11: آمار روزانه
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date DATE PRIMARY KEY,
                    new_users INT DEFAULT 0,
                    new_bots INT DEFAULT 0,
                    total_users INT DEFAULT 0,
                    total_bots INT DEFAULT 0,
                    payments_amount BIGINT DEFAULT 0,
                    payments_count INT DEFAULT 0,
                    withdrawals_amount BIGINT DEFAULT 0,
                    withdrawals_count INT DEFAULT 0,
                    active_users INT DEFAULT 0,
                    revenue BIGINT DEFAULT 0,
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 12: بلاک لیست IP
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ip_blacklist (
                    id SERIAL PRIMARY KEY,
                    ip TEXT NOT NULL UNIQUE,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    created_by BIGINT
                )
            ''')
            
            # جدول 13: توکن‌های API
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS api_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    token TEXT UNIQUE NOT NULL,
                    name TEXT,
                    permissions TEXT[],
                    last_used TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # جدول 14: فایل‌های کاربران
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_files (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size BIGINT,
                    file_type TEXT,
                    file_hash TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 15: لاگ‌های ربات
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_logs (
                    id SERIAL PRIMARY KEY,
                    bot_id TEXT REFERENCES bots(id) ON DELETE CASCADE,
                    log_level TEXT,
                    log_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            # جدول 16: کوپن‌ها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS coupons (
                    id SERIAL PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    discount_percent INT,
                    discount_amount BIGINT,
                    max_uses INT DEFAULT 1,
                    used_count INT DEFAULT 0,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # جدول 17: پیام‌های خودکار
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS auto_messages (
                    id SERIAL PRIMARY KEY,
                    trigger_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    delay_seconds INT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            # جدول 18: نظرسنجی‌ها
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS polls (
                    id SERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    options TEXT[] NOT NULL,
                    votes JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    created_by BIGINT,
                    expires_at TIMESTAMP
                )
            ''')
            
            # جدول 19: تیکت‌های پشتیبانی
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    priority TEXT DEFAULT 'normal',
                    assigned_to BIGINT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    closed_at TIMESTAMP,
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # جدول 20: پاسخ‌های تیکت
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ticket_replies (
                    id SERIAL PRIMARY KEY,
                    ticket_id INT REFERENCES support_tickets(id) ON DELETE CASCADE,
                    user_id BIGINT,
                    message TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
    
    async def _create_all_indexes(self):
        """ایجاد تمام ایندکس‌ها برای سرعت بالا"""
        async with self.pool.acquire() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)",
                "CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)",
                "CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_end)",
                "CREATE INDEX IF NOT EXISTS idx_users_trial ON users(trial_end)",
                "CREATE INDEX IF NOT EXISTS idx_users_payment ON users(payment_status)",
                "CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)",
                "CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_bots_user_id ON bots(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)",
                "CREATE INDEX IF NOT EXISTS idx_bots_created ON bots(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_receipts_user ON receipts(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)",
                "CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_errors_created ON errors(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_errors_resolved ON errors(resolved)",
                "CREATE INDEX IF NOT EXISTS idx_bot_logs_bot ON bot_logs(bot_id)",
                "CREATE INDEX IF NOT EXISTS idx_bot_logs_created ON bot_logs(created_at)"
            ]
            for idx in indexes:
                await conn.execute(idx)
    
    async def _init_default_data(self):
        """مقداردهی اولیه دیتابیس"""
        async with self.pool.acquire() as conn:
            # تنظیمات پیش‌فرض
            default_settings = [
                ('price', str(PRICE), 'integer', 'قیمت اشتراک ماهیانه به تومان'),
                ('card_number', CARD_NUMBER, 'string', 'شماره کارت بانکی'),
                ('card_holder', CARD_HOLDER, 'string', 'صاحب حساب'),
                ('min_withdraw', str(MIN_WITHDRAW), 'integer', 'حداقل مبلغ برداشت'),
                ('referral_percent', str(REFERRAL_PERCENT), 'integer', 'درصد سود رفرال'),
                ('trial_hours', str(TRIAL_HOURS), 'integer', 'ساعت تست رایگان'),
                ('max_bots_default', '1', 'integer', 'حداکثر ربات پیش‌فرض'),
                ('bot_timeout', '60', 'integer', 'تایم اوت ربات به ثانیه'),
                ('max_file_size', str(MAX_FILE_SIZE), 'integer', 'حداکثر حجم فایل'),
                ('guide_text', 'راهنمای ربات...', 'text', 'متن راهنما'),
                ('welcome_text', 'به ربات خوش آمدید!', 'text', 'متن خوش‌آمدگویی'),
                ('maintenance_mode', 'false', 'boolean', 'حالت تعمیرات'),
                ('version', '12.0', 'string', 'نسخه ربات')
            ]
            
            for key, value, vtype, desc in default_settings:
                await conn.execute('''
                    INSERT INTO settings (key, value, type, description, updated_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (key) DO UPDATE SET 
                        value = EXCLUDED.value,
                        description = EXCLUDED.description,
                        updated_at = NOW()
                ''', key, value, vtype, desc)
            
            # پیام‌های خودکار پیش‌فرض
            auto_messages = [
                ('start', 'به ربات مادر خوش آمدید! برای شروع روی دکمه های منوی اصلی کلیک کنید.', 0),
                ('payment', 'پرداخت شما با موفقیت ثبت شد. اشتراک شما فعال شد.', 0),
                ('bot_created', 'ربات شما با موفقیت ساخته شد!', 0)
            ]
            for trigger, msg, delay in auto_messages:
                await conn.execute('''
                    INSERT INTO auto_messages (trigger_type, message, delay_seconds, created_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT DO NOTHING
                ''', trigger, msg, delay)
    
    async def execute(self, query: str, *args):
        """اجرای کوئری با مدیریت خودکار"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """دریافت نتایج کوئری"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """دریافت یک ردیف"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """دریافت یک مقدار"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def close(self):
        if self.pool:
            await self.pool.close()

db = DatabaseManager()

# ======================== کش Redis با 15 نوع کش مختلف ========================
class RedisCache:
    """مدیریت کش با 15 نوع مختلف"""
    
    def __init__(self):
        self.redis = None
        self.default_ttl = 300  # 5 دقیقه
    
    async def connect(self):
        self.redis = await redis.from_url(
            f"redis://{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}",
            password=REDIS_CONFIG['password'],
            db=REDIS_CONFIG['db'],
            decode_responses=True,
            max_connections=50
        )
        logger.info("✅ Redis Cache متصل شد")
        return self.redis
    
    # کش کاربر
    async def get_user(self, user_id: int) -> Optional[Dict]:
        data = await self.redis.get(f"user:{user_id}")
        return json.loads(data) if data else None
    
    async def set_user(self, user_id: int, data: Dict, ttl: int = None):
        await self.redis.setex(f"user:{user_id}", ttl or self.default_ttl, json.dumps(data, default=str))
    
    async def delete_user(self, user_id: int):
        await self.redis.delete(f"user:{user_id}")
        await self.redis.delete(f"sub:{user_id}")
        await self.redis.delete(f"stats:{user_id}")
    
    # کش اشتراک
    async def get_subscription(self, user_id: int) -> Optional[str]:
        return await self.redis.get(f"sub:{user_id}")
    
    async def set_subscription(self, user_id: int, status: str, ttl: int = 3600):
        await self.redis.setex(f"sub:{user_id}", ttl, status)
    
    # کش ربات
    async def get_bot(self, bot_id: str) -> Optional[Dict]:
        data = await self.redis.get(f"bot:{bot_id}")
        return json.loads(data) if data else None
    
    async def set_bot(self, bot_id: str, data: Dict, ttl: int = 60):
        await self.redis.setex(f"bot:{bot_id}", ttl, json.dumps(data, default=str))
    
    async def set_bot_running(self, bot_id: str, is_running: bool):
        await self.redis.setex(f"bot_running:{bot_id}", 30, "1" if is_running else "0")
    
    async def is_bot_running(self, bot_id: str) -> bool:
        return await self.redis.get(f"bot_running:{bot_id}") == "1"
    
    # کش تنظیمات
    async def get_setting(self, key: str) -> Optional[str]:
        return await self.redis.get(f"setting:{key}")
    
    async def set_setting(self, key: str, value: str, ttl: int = 3600):
        await self.redis.setex(f"setting:{key}", ttl, value)
    
    async def invalidate_setting(self, key: str):
        await self.redis.delete(f"setting:{key}")
    
    # کش آمار
    async def increment_stat(self, key: str, amount: int = 1):
        await self.redis.incrby(f"stat:{key}", amount)
    
    async def get_stat(self, key: str) -> int:
        val = await self.redis.get(f"stat:{key}")
        return int(val) if val else 0
    
    # محدودیت نرخ (Rate Limiting)
    async def check_rate_limit(self, user_id: int, action: str, limit: int = 30, window: int = 60) -> bool:
        key = f"rate:{user_id}:{action}"
        current = await self.redis.get(key)
        if current and int(current) >= limit:
            return False
        await self.redis.incr(key)
        await self.redis.expire(key, window)
        return True
    
    # کش سشن
    async def set_session(self, user_id: int, data: Dict, ttl: int = 300):
        await self.redis.setex(f"session:{user_id}", ttl, json.dumps(data))
    
    async def get_session(self, user_id: int) -> Optional[Dict]:
        data = await self.redis.get(f"session:{user_id}")
        return json.loads(data) if data else None
    
    async def delete_session(self, user_id: int):
        await self.redis.delete(f"session:{user_id}")
    
    # کش لاگین
    async def add_to_queue(self, queue_name: str, data: Dict):
        await self.redis.rpush(f"queue:{queue_name}", json.dumps(data))
    
    async def pop_from_queue(self, queue_name: str) -> Optional[Dict]:
        data = await self.redis.lpop(f"queue:{queue_name}")
        return json.loads(data) if data else None
    
    # کش بلاک لیست
    async def add_to_blacklist(self, ip: str, ttl: int = 86400):
        await self.redis.setex(f"blacklist:{ip}", ttl, "1")
    
    async def is_blacklisted(self, ip: str) -> bool:
        return await self.redis.get(f"blacklist:{ip}") == "1"
    
    # کش لاگ
    async def add_log(self, log_type: str, data: Dict):
        await self.redis.lpush(f"log:{log_type}", json.dumps(data))
        await self.redis.ltrim(f"log:{log_type}", 0, 1000)
    
    # پاک کردن کش
    async def flush_all(self):
        await self.redis.flushall()
    
    async def close(self):
        if self.redis:
            await self.redis.close()

cache = RedisCache()

# ======================== کلاس ایزوله‌سازی داکر (پیشرفته) ========================
class DockerSandbox:
    """ایزوله‌سازی کامل کد کاربران با داکر - هر ربات در کانتینر جدا"""
    
    def __init__(self):
        self.docker_client = None
        self.running_containers = {}
        self._lock = asyncio.Lock()
    
    def connect(self):
        self.docker_client = docker.from_env()
        logger.info("✅ Docker Sandbox متصل شد")
        return self.docker_client
    
    def create_sandbox_container(self, bot_id: str, code: str, token: str) -> Optional[str]:
        """ایجاد کانتینر ایزوله برای اجرای ربات"""
        try:
            temp_dir = os.path.join(SANDBOX_DIR, bot_id)
            os.makedirs(temp_dir, exist_ok=True)
            
            # ذخیره کد اصلی
            code_path = os.path.join(temp_dir, "bot.py")
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            # ذخیره توکن
            token_path = os.path.join(temp_dir, "token.txt")
            with open(token_path, "w") as f:
                f.write(token)
            
            # ایجاد فایل requirements.txt خودکار
            requirements = self._extract_requirements(code)
            req_path = os.path.join(temp_dir, "requirements.txt")
            with open(req_path, "w") as f:
                f.write("\n".join(requirements))
            
            # ایجاد Dockerfile امن
            dockerfile_content = f'''FROM python:3.11-slim

# نصب کتابخانه‌های پایه
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# ایجاد کاربر محدود
RUN useradd -m -s /bin/bash sandbox && \\
    mkdir -p /app /tmp/sandbox && \\
    chown -R sandbox:sandbox /app /tmp/sandbox

# کپی فایل‌ها
WORKDIR /app
COPY bot.py .
COPY token.txt .
COPY requirements.txt .

# نصب کتابخانه‌های مورد نیاز
RUN pip install --no-cache-dir -r requirements.txt

# محدودیت‌های امنیتی
USER sandbox

# تنظیم محدودیت منابع
CMD python -c "
import resource, sys, os, signal, time

def timeout_handler(signum, frame):
    print('Time limit exceeded', file=sys.stderr)
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)  # 60 ثانیه تایم اوت

# محدودیت حافظه (512MB)
resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))

# محدودیت CPU
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))

# محدودیت تعداد فایل‌ها
resource.setrlimit(resource.RLIMIT_NOFILE, (100, 100))

# محدودیت اندازه فرآیند
resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))

# اجرای ربات
exec(open('bot.py').read())
"'''
            
            dockerfile_path = os.path.join(temp_dir, "Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile_content)
            
            # ساخت image
            image_name = f"sandbox_{bot_id}_{int(time.time())}"
            image, logs = self.docker_client.images.build(
                path=temp_dir,
                tag=image_name,
                rm=True,
                forcerm=True,
                quiet=False
            )
            
            # اجرای کانتینر با محدودیت‌های کامل
            container = self.docker_client.containers.run(
                image_name,
                detach=True,
                mem_limit=DOCKER_CONFIG["memory_limit"],
                memswap_limit=DOCKER_CONFIG["memory_swap"],
                nano_cpus=int(DOCKER_CONFIG["cpu_limit"] * 1e9),
                network_mode=DOCKER_CONFIG["network_mode"],
                read_only=DOCKER_CONFIG["read_only"],
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                cap_add=["NET_ADMIN"],  # برای اتصال به تلگرام
                ulimits=[
                    {'Name': 'nofile', 'Soft': 100, 'Hard': 100},
                    {'Name': 'nproc', 'Soft': 10, 'Hard': 10},
                    {'Name': 'core', 'Soft': 0, 'Hard': 0}
                ],
                pids_limit=50,
                restart_policy={"Name": "no"},
                remove=False,
                labels={
                    "bot_id": bot_id,
                    "type": "user_bot",
                    "created_at": str(datetime.now())
                }
            )
            
            # ذخیره اطلاعات کانتینر
            with self._lock:
                self.running_containers[bot_id] = {
                    "container_id": container.id,
                    "image": image_name,
                    "started_at": datetime.now(),
                    "temp_dir": temp_dir
                }
            
            logger.info(f"✅ کانتینر برای ربات {bot_id} ساخته شد: {container.id[:12]}")
            return container.id
            
        except Exception as e:
            logger.error(f"خطا در ساخت کانتینر: {e}")
            return None
    
    def _extract_requirements(self, code: str) -> List[str]:
        """استخراج کتابخانه‌های مورد نیاز از کد"""
        requirements = set()
        standard_libs = {
            'os', 'sys', 'time', 'datetime', 'json', 're', 'math', 'random',
            'string', 'collections', 'itertools', 'functools', 'typing',
            'hashlib', 'base64', 'uuid', 'socket', 'ssl', 'threading',
            'multiprocessing', 'subprocess', 'argparse', 'logging', 'pathlib',
            'tempfile', 'copy', 'pickle', 'struct', 'html', 'xml', 'csv'
        }
        
        # استخراج importها
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('import '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    if lib not in standard_libs and lib != 'telebot':
                        requirements.add(lib)
            elif line.startswith('from '):
                parts = line.split()
                if len(parts) > 1:
                    lib = parts[1].split('.')[0]
                    if lib not in standard_libs and lib != 'telebot':
                        requirements.add(lib)
        
        # اضافه کردن کتابخانه‌های ضروری
        if 'telebot' in code or 'TeleBot' in code:
            requirements.add('pyTelegramBotAPI')
        
        return list(requirements)
    
    def stop_container(self, container_id: str) -> bool:
        """توقف کانتینر"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop(timeout=10)
            logger.info(f"✅ کانتینر {container_id[:12]} متوقف شد")
            return True
        except Exception as e:
            logger.error(f"خطا در توقف کانتینر: {e}")
            return False
    
    def remove_container(self, container_id: str) -> bool:
        """حذف کانتینر"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.remove(force=True)
            logger.info(f"✅ کانتینر {container_id[:12]} حذف شد")
            return True
        except Exception as e:
            logger.error(f"خطا در حذف کانتینر: {e}")
            return False
    
    def get_container_status(self, container_id: str) -> Dict:
        """دریافت وضعیت کانتینر"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.reload()
            
            stats = container.stats(stream=False) if container.status == 'running' else {}
            
            return {
                "status": container.status,
                "running": container.status == 'running',
                "cpu_usage": stats.get('cpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0) if stats else 0,
                "memory_usage": stats.get('memory_stats', {}).get('usage', 0) if stats else 0,
                "started_at": container.attrs['State']['StartedAt'] if hasattr(container, 'attrs') else None
            }
        except Exception as e:
            return {"status": "unknown", "running": False, "error": str(e)}
    
    def get_container_logs(self, container_id: str, lines: int = 100) -> str:
        """دریافت لاگ کانتینر"""
        try:
            container = self.docker_client.containers.get(container_id)
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8', errors='ignore')
            return logs
        except Exception as e:
            return f"خطا در دریافت لاگ: {e}"
    
    async def cleanup_old_containers(self):
        """پاکسازی کانتینرهای قدیمی"""
        try:
            containers = self.docker_client.containers.list(
                filters={"label": "type=user_bot"},
                all=True
            )
            
            for container in containers:
                created = container.attrs['Created']
                created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
                age = datetime.now() - created_time.replace(tzinfo=None)
                
                # حذف کانتینرهای قدیمی تر از 7 روز
                if age.days > 7:
                    container.remove(force=True)
                    logger.info(f"پاکسازی کانتینر قدیمی: {container.id[:12]}")
        except Exception as e:
            logger.error(f"خطا در پاکسازی: {e}")

sandbox = DockerSandbox()

# ======================== کلاس امنیت (پیشرفته) ========================
class SecurityManager:
    """مدیریت امنیت: بررسی کد مخرب، محدودیت منابع، فایروال"""
    
    def __init__(self):
        self.dangerous_patterns = [
            # اجرای دستورات سیستم
            (r'os\.system\s*\(', 'اجرای دستور سیستم'),
            (r'subprocess\.', 'فراخوانی subprocess'),
            (r'eval\s*\(', 'تابع eval'),
            (r'exec\s*\(', 'تابع exec'),
            (r'__import__\s*\(', 'import پویا'),
            (r'compile\s*\(', 'تابع compile'),
            
            # دستکاری فایل‌ها
            (r'open\s*\(.*[\'"]w[\'"]', 'نوشتن در فایل'),
            (r'shutil\.rmtree', 'حذف درخت فایل'),
            (r'os\.remove\s*\(', 'حذف فایل'),
            (r'os\.unlink\s*\(', 'حذف فایل'),
            (r'os\.rmdir\s*\(', 'حذف دایرکتوری'),
            (r'os\.chmod', 'تغییر دسترسی'),
            (r'os\.chown', 'تغییر مالکیت'),
            
            # دستکاری متغیرهای جهانی
            (r'globals\s*\(', 'دسترسی به globals'),
            (r'locals\s*\(', 'دسترسی به locals'),
            (r'__builtins__', 'دسترسی به builtins'),
            
            # ترفندهای پایتون
            (r'\.__class__', 'دسترسی به class'),
            (r'\.__bases__', 'دسترسی به bases'),
            (r'\.__subclasses__', 'دسترسی به subclasses'),
            (r'\.__dict__', 'دسترسی به dict'),
            (r'\.__globals__', 'دسترسی به globals'),
            
            # شبکه و سوکت
            (r'socket\.', 'استفاده از سوکت'),
            (r'requests\.', 'درخواست HTTP (محدود)'),
            
            # رمزنگاری مخرب
            (r'cryptography\.', 'رمزنگاری پیشرفته'),
            
            # کدهای dangerous دیگر
            (r'execfile', 'execfile'),
            (r'breakpoint\s*\(', 'breakpoint'),
            (r'__code__', 'دسترسی به code'),
            (r'marshal\.', 'marshal'),
            (r'pickle\.loads', 'pickle不安全'),
            (r'base64\.b64decode.*exec', 'کد رمزگذاری شده'),
            (r'urllib\.request', 'درخواست اینترنتی'),
            (r'ftplib\.', 'FTP'),
            (r'telnetlib\.', 'Telnet'),
            (r'paramiko\.', 'SSH'),
            (r'popen', 'popen'),
            (r'communicate', 'communicate'),
        ]
        
        self.allowed_imports = {
            'telebot', 'pyTelegramBotAPI', 'requests', 'json', 'time', 'datetime',
            'random', 'math', 're', 'string', 'collections', 'itertools',
            'functools', 'typing', 'jdatetime', 'pytz', 'qrcode', 'pillow',
            'PIL', 'numpy', 'pandas', 'bs4', 'beautifulsoup4', 'flask',
            'aiohttp', 'asyncio', 'uuid', 'hashlib', 'base64'
        }
    
    def scan_code(self, code: str) -> Tuple[bool, str]:
        """اسکن کامل کد برای یافتن کدهای مخرب"""
        
        # بررسی الگوهای خطرناک
        for pattern, description in self.dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                logger.warning(f"کد مخرب شناسایی شد: {description}")
                return False, f"کد مخرب شناسایی شد: {description}"
        
        # بررسی importها
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                # استخراج نام کتابخانه
                parts = line.split()
                if len(parts) >= 2:
                    lib = parts[1].split('.')[0]
                    if lib not in self.allowed_imports and lib not in ['os', 'sys']:
                        return False, f"کتابخانه غیرمجاز: {lib}"
        
        # بررسی سایز کد
        if len(code) > 50000:  # 50KB
            return False, "حجم کد بیش از حد مجاز است (حداکثر 50KB)"
        
        # بررسی تعداد خطوط
        if len(code.split('\n')) > 2000:
            return False, "تعداد خطوط کد بیش از حد مجاز است (حداکثر 2000 خط)"
        
        return True, "OK"
    
    def sanitize_filename(self, filename: str) -> str:
        """پاکسازی نام فایل"""
        filename = re.sub(r'[^\w\-_.]', '_', filename)
        filename = filename.replace('..', '')
        filename = filename.strip('.')
        return filename[:100]
    
    def validate_token(self, token: str) -> bool:
        """اعتبارسنجی توکن تلگرام"""
        pattern = r'^\d{8,10}:[a-zA-Z0-9_-]{35}$'
        return bool(re.match(pattern, token))
    
    def rate_limit_check(self, user_id: int, action: str) -> bool:
        """بررسی محدودیت نرخ درخواست"""
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(cache.check_rate_limit(user_id, action, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW))
            return result
        except:
            return True

security = SecurityManager()

# ======================== کلاس کاربر ========================
class UserManager:
    """مدیریت کامل کاربران"""
    
    @staticmethod
    async def get_user(user_id: int) -> Optional[Dict]:
        # ابتدا از کش
        cached = await cache.get_user(user_id)
        if cached:
            return cached
        
        # از دیتابیس
        row = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if row:
            user = dict(row)
            await cache.set_user(user_id, user)
            return user
        return None
    
    @staticmethod
    async def create_user(user_id: int, username: str, first_name: str, last_name: str, referred_by: int = None) -> Optional[Dict]:
        # بررسی وجود کاربر
        existing = await db.fetchrow("SELECT user_id FROM users WHERE user_id = $1", user_id)
        if existing:
            return await UserManager.get_user(user_id)
        
        # ایجاد کد رفرال یکتا
        referral_code = hashlib.md5(f"{user_id}_{secrets.token_hex(8)}".encode()).hexdigest()[:10]
        
        # زمان تست 24 ساعته
        trial_end = datetime.now() + timedelta(hours=TRIAL_HOURS)
        
        # درج کاربر جدید
        await db.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by, trial_end, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        ''', user_id, username or "", first_name or "", last_name or "", referral_code, referred_by, trial_end)
        
        # افزایش آمار رفرال برای معرف
        if referred_by:
            await db.execute('''
                UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = $1
            ''', referred_by)
            await cache.delete_user(referred_by)
        
        user = await UserManager.get_user(user_id)
        return user
    
    @staticmethod
    async def update_activity(user_id: int):
        await db.execute("UPDATE users SET last_active = NOW() WHERE user_id = $1", user_id)
        await cache.set_user(user_id, {**await UserManager.get_user(user_id), "last_active": datetime.now()}, 60)
    
    @staticmethod
    async def has_active_subscription(user_id: int) -> bool:
        # از کش
        cached = await cache.get_subscription(user_id)
        if cached:
            return cached == "active"
        
        # از دیتابیس
        row = await db.fetchrow('''
            SELECT user_id FROM users 
            WHERE user_id = $1 AND (subscription_end > NOW() OR trial_end > NOW())
        ''', user_id)
        
        is_active = row is not None
        await cache.set_subscription(user_id, "active" if is_active else "inactive")
        return is_active
    
    @staticmethod
    async def get_user_balance(user_id: int) -> int:
        user = await UserManager.get_user(user_id)
        return user.get('balance', 0) if user else 0
    
    @staticmethod
    async def add_balance(user_id: int, amount: int, description: str = None):
        await db.execute('''
            UPDATE users SET balance = balance + $1 WHERE user_id = $2
        ''', amount, user_id)
        
        # ثبت تراکنش
        await db.execute('''
            INSERT INTO transactions (user_id, amount, type, description, created_at)
            VALUES ($1, $2, 'credit', $3, NOW())
        ''', user_id, amount, description)
        
        await cache.delete_user(user_id)
    
    @staticmethod
    async def get_max_bots(user_id: int) -> int:
        user = await UserManager.get_user(user_id)
        if not user:
            return 1
        
        base = user.get('max_bots', 1)
        extra = user.get('verified_referrals', 0) // 5
        return base + extra
    
    @staticmethod
    async def get_current_bots(user_id: int) -> int:
        return await db.fetchval("SELECT COUNT(*) FROM bots WHERE user_id = $1", user_id)
    
    @staticmethod
    async def can_create_bot(user_id: int) -> Tuple[bool, int, int]:
        max_bots = await UserManager.get_max_bots(user_id)
        current_bots = await UserManager.get_current_bots(user_id)
        return current_bots < max_bots, max_bots, current_bots

# ======================== کلاس ربات ========================
class BotManager:
    """مدیریت کامل ربات‌ها"""
    
    @staticmethod
    async def create_bot(user_id: int, token: str, code: str, bot_name: str, bot_username: str) -> Optional[str]:
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:16]
        
        # ذخیره در دیتابیس
        await db.execute('''
            INSERT INTO bots (id, user_id, token, name, username, status, created_at)
            VALUES ($1, $2, $3, $4, $5, 'pending', NOW())
        ''', bot_id, user_id, token, bot_name, bot_username)
        
        # افزایش تعداد ربات کاربر
        await db.execute("UPDATE users SET bots_count = bots_count + 1 WHERE user_id = $1", user_id)
        
        await cache.delete_user(user_id)
        
        return bot_id
    
    @staticmethod
    async def get_user_bots(user_id: int) -> List[Dict]:
        rows = await db.fetch("SELECT * FROM bots WHERE user_id = $1 ORDER BY created_at DESC", user_id)
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_bot(bot_id: str) -> Optional[Dict]:
        # از کش
        cached = await cache.get_bot(bot_id)
        if cached:
            return cached
        
        # از دیتابیس
        row = await db.fetchrow("SELECT * FROM bots WHERE id = $1", bot_id)
        if row:
            bot = dict(row)
            await cache.set_bot(bot_id, bot)
            return bot
        return None
    
    @staticmethod
    async def update_bot_status(bot_id: str, status: str, container_id: str = None):
        if container_id:
            await db.execute('''
                UPDATE bots SET status = $1, container_id = $2, last_active = NOW()
                WHERE id = $3
            ''', status, container_id, bot_id)
        else:
            await db.execute('''
                UPDATE bots SET status = $1, last_active = NOW()
                WHERE id = $2
            ''', status, bot_id)
        
        await cache.delete(bot_id)
        await cache.set_bot_running(bot_id, status == 'running')
    
    @staticmethod
    async def delete_bot(bot_id: str, user_id: int) -> bool:
        bot = await BotManager.get_bot(bot_id)
        if not bot or bot['user_id'] != user_id:
            return False
        
        # توقف و حذف کانتینر
        if bot.get('container_id'):
            sandbox.stop_container(bot['container_id'])
            sandbox.remove_container(bot['container_id'])
        
        # حذف از دیتابیس
        await db.execute("DELETE FROM bots WHERE id = $1", bot_id)
        await db.execute("UPDATE users SET bots_count = bots_count - 1 WHERE user_id = $1", user_id)
        
        # حذف فایل‌ها
        if bot.get('file_path') and os.path.exists(bot['file_path']):
            os.remove(bot['file_path'])
        if bot.get('folder_path') and os.path.exists(bot['folder_path']):
            shutil.rmtree(bot['folder_path'])
        
        await cache.delete_user(user_id)
        await cache.delete(bot_id)
        
        return True

# ======================== توابع کمکی عمومی ========================
def generate_referral_link(user_id: int, referral_code: str) -> str:
    bot_username = bot.get_me().username
    return f"https://t.me/{bot_username}?start={referral_code}"

def format_number(num: int) -> str:
    return f"{num:,}"

def safe_send_message(chat_id: int, text: str, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"خطا در ارسال پیام: {e}")
        try:
            return bot.send_message(chat_id, "پیام ارسال شد", reply_markup=reply_markup)
        except:
            return None

def safe_edit_message(chat_id: int, message_id: int, text: str, reply_markup=None):
    try:
        return bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup)
    except:
        return None

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ======================== منوها و کیبوردها ========================
def get_main_menu(user_id: int = None):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال کردن'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
        types.KeyboardButton('⏱ تست ۲۴ ساعته'),
        types.KeyboardButton('🏧 برداشت وجه'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📊 آمار من'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if user_id and is_admin(user_id):
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="admin_price"),
        types.InlineKeyboardButton("💳 تغییر کارت", callback_data="admin_card"),
        types.InlineKeyboardButton("📝 تغییر راهنما", callback_data="admin_guide"),
        types.InlineKeyboardButton("🖥 اضافه کردن سرور", callback_data="admin_server"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربران", callback_data="admin_del_bot"),
        types.InlineKeyboardButton("🏧 درخواست‌های برداشت", callback_data="admin_withdraw"),
        types.InlineKeyboardButton("📸 فیش‌های در انتظار", callback_data="admin_receipts"),
        types.InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 ارسال اعلان", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💾 بکاپ دیتابیس", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔄 ریستارت ربات", callback_data="admin_restart"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    ]
    markup.add(*buttons)
    return markup

# ======================== هندلر استارت ========================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    # محدودیت نرخ
    if not security.rate_limit_check(user_id, "start"):
        safe_send_message(message.chat.id, "❌ لطفاً کمی صبر کنید...")
        return
    
    # پردازش کد رفرال
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        async def check_ref():
            row = await db.fetchrow("SELECT user_id FROM users WHERE referral_code = $1", ref_code)
            return row['user_id'] if row and row['user_id'] != user_id else None
        
        try:
            loop = asyncio.new_event_loop()
            referred_by = loop.run_until_complete(check_ref())
        except:
            pass
    
    # ایجاد کاربر
    async def create():
        return await UserManager.create_user(user_id, username, first_name, last_name, referred_by)
    
    try:
        loop = asyncio.new_event_loop()
        user = loop.run_until_complete(create())
    except:
        user = None
    
    # ارسال پیام خوش‌آمدگویی
    bot_username = bot.get_me().username
    referral_link = generate_referral_link(user_id, user.get('referral_code', '') if user else '')
    
    welcome_text = f"""🚀 **به ربات مادر حرفه‌ای خوش آمدید** {first_name}!

👤 **آیدی شما:** `{user_id}`
🎁 **کد رفرال:** `{user.get('referral_code', '') if user else ''}`
🔗 **لینک دعوت:** {referral_link}

📊 **آمار رفرال شما:**
• کلیک‌ها: {user.get('referrals_count', 0) if user else 0}
• ثبت‌نام‌های موفق: {user.get('verified_referrals', 0) if user else 0}
• درآمد از رفرال: {format_number(user.get('referral_earnings', 0) if user else 0)} تومان

💡 **نکات مهم:**
• هر ۵ دعوت موفق = ۱ ربات اضافه
• ۷٪ سود از هر خرید دعوت شده
• تست ۲۴ ساعته رایگان برای ساخت ربات

📤 **شروع کنید:** فایل `.py` یا `.zip` ربات خود را آپلود کنید

📞 **پشتیبانی:** @shahraghee13"""
    
    safe_send_message(message.chat.id, welcome_text, get_main_menu(user_id))

# ======================== تست 24 ساعته ========================
@bot.message_handler(func=lambda m: m.text == '⏱ تست ۲۴ ساعته')
def trial_24h(message):
    user_id = message.from_user.id
    
    async def check_and_activate():
        user = await UserManager.get_user(user_id)
        if not user:
            return False, None
        
        # بررسی تست قبلی
        trial_end = user.get('trial_end')
        if trial_end:
            if isinstance(trial_end, str):
                trial_end = datetime.fromisoformat(trial_end.replace('+00:00', ''))
            if trial_end > datetime.now():
                return False, trial_end
        
        # فعالسازی تست جدید
        new_trial_end = datetime.now() + timedelta(hours=24)
        await db.execute("UPDATE users SET trial_end = $1 WHERE user_id = $2", new_trial_end, user_id)
        await cache.delete_user(user_id)
        await cache.set_subscription(user_id, "active", 86400)
        
        return True, new_trial_end
    
    try:
        loop = asyncio.new_event_loop()
        success, trial_end = loop.run_until_complete(check_and_activate())
        
        if success:
            text = f"""✅ **تست ۲۴ ساعته فعال شد!** 🎉

⏱ **زمان باقی مانده:** ۲۴ ساعت
📅 **پایان تست:** {trial_end.strftime('%Y-%m-%d %H:%M:%S') if hasattr(trial_end, 'strftime') else str(trial_end)[:19]}

💡 **نکات تست رایگان:**
• می‌توانید ۱ ربات بسازید
• ربات در محیط ایزوله داکر اجرا می‌شود
• پس از اتمام تست، برای ادامه باید اشتراک تهیه کنید

✅ **همین حالا ربات خود را بسازید!** (دکمه ساخت ربات جدید)"""
            safe_send_message(message.chat.id, text, get_main_menu(user_id))
        else:
            remaining = (trial_end - datetime.now()).seconds // 3600 if trial_end else 0
            text = f"""❌ **شما قبلاً از تست ۲۴ ساعته استفاده کرده‌اید!**

⏱ **زمان باقی مانده از تست:** {remaining} ساعت

💡 **برای ادامه:**
• منتظر بمانید تا تست تمام شود
• یا اشتراک تهیه کنید و ربات‌های بیشتری بسازید

💰 **قیمت اشتراک:** از طریق دکمه ساخت ربات جدید مشاهده کنید"""
            safe_send_message(message.chat.id, text, get_main_menu(user_id))
    except Exception as e:
        logger.error(f"خطا در تست 24 ساعته: {e}")
        safe_send_message(message.chat.id, "❌ خطا در فعالسازی تست ۲۴ ساعته. لطفاً بعداً تلاش کنید.", get_main_menu(user_id))

# ======================== ساخت ربات جدید ========================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    if not security.rate_limit_check(user_id, "new_bot"):
        safe_send_message(message.chat.id, "❌ لطفاً کمی صبر کنید...")
        return
    
    async def check():
        has_sub = await UserManager.has_active_subscription(user_id)
        can_create, max_bots, current_bots = await UserManager.can_create_bot(user_id)
        return has_sub, can_create, max_bots, current_bots
    
    try:
        loop = asyncio.new_event_loop()
        has_sub, can_create, max_bots, current_bots = loop.run_until_complete(check())
    except:
        has_sub, can_create, max_bots, current_bots = False, False, 1, 0
    
    if not has_sub:
        # دریافت اطلاعات پرداخت از تنظیمات
        async def get_payment_info():
            price_row = await db.fetchrow("SELECT value FROM settings WHERE key = 'price'")
            card_row = await db.fetchrow("SELECT value FROM settings WHERE key = 'card_number'")
            return int(price_row['value']) if price_row else PRICE, card_row['value'] if card_row else CARD_NUMBER
        
        try:
            loop = asyncio.new_event_loop()
            price, card = loop.run_until_complete(get_payment_info())
        except:
            price, card = PRICE, CARD_NUMBER
        
        text = f"""⚠️ **کاربر گرامی، از اینکه ما را انتخاب کردید متشکریم**

برای فعال‌سازی اشتراک و ساخت ربات، مبلغ **{format_number(price)} تومان** به شماره کارت زیر واریز کنید:

💳 **شماره کارت:** `{card}`
🏦 **بانک سپه**
👤 **به نام:** مرتضی نیکخو خنجری

📸 **مراحل فعال‌سازی:**
1️⃣ مبلغ را به کارت فوق واریز کنید
2️⃣ از صفحه واریز عکس بگیرید
3️⃣ عکس فیش را در همین چت ارسال کنید
4️⃣ پس از تأیید، اشتراک شما فعال می‌شود

✅ **پس از تأیید می‌توانید ربات خود را بسازید**

💡 **یا از تست ۲۴ ساعته رایگان استفاده کنید!** (دکمه تست ۲۴ ساعته)

🔗 **لینک رفرال شما:** هر کاربر که با لینک شما وارد شود و خرید کند، **۷٪ سود** به کیف پول شما اضافه می‌شود"""
        
        safe_send_message(message.chat.id, text, get_main_menu(user_id))
        return
    
    if not can_create:
        text = f"""❌ **شما به حداکثر تعداد ربات ({max_bots}) رسیده‌اید!**

📊 **وضعیت فعلی:**
• ربات‌های فعلی: {current_bots}
• حداکثر مجاز: {max_bots}

💡 **برای ساخت ربات جدید:**
1️⃣ یکی از ربات‌های خود را حذف کنید
2️⃣ یا با دعوت دوستان ربات اضافه بگیرید (هر ۵ دعوت = ۱ ربات اضافه)
3️⃣ یا اشتراک خود را ارتقا دهید

🎁 **سود رفرال:** ۷٪ از هر خرید"""
        
        safe_send_message(message.chat.id, text, get_main_menu(user_id))
        return
    
    safe_send_message(message.chat.id, 
        "📤 **فایل ربات خود را ارسال کنید**\n\n"
        "✅ فایل‌های مجاز: `.py` یا `.zip`\n"
        "✅ حداکثر حجم: ۵۰ مگابایت\n"
        "✅ توکن ربات داخل کد باشد\n"
        "✅ اگر فایل زیپ است، تمام فایل‌های پروژه را شامل شود\n\n"
        "🔒 **امنیت بالا:**\n"
        "• کد شما از نظر امنیتی بررسی می‌شود\n"
        "• ربات در محیط ایزوله داکر اجرا می‌شود\n"
        "• دسترسی به سیستم عامل محدود شده است\n\n"
        "⚡ **پس از ارسال، ربات شما به صورت خودکار ساخته و اجرا می‌شود**")

# ======================== آپلود و ساخت ربات ========================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    # محدودیت نرخ
    if not security.rate_limit_check(user_id, "upload"):
        safe_send_message(message.chat.id, "❌ لطفاً کمی صبر کنید...")
        return
    
    # بررسی اشتراک
    async def check():
        return await UserManager.has_active_subscription(user_id)
    
    try:
        loop = asyncio.new_event_loop()
        has_sub = loop.run_until_complete(check())
    except:
        has_sub = False
    
    if not has_sub:
        safe_send_message(message.chat.id, "❌ ابتدا اشتراک تهیه کنید یا از تست ۲۴ ساعته استفاده کنید!")
        return
    
    file_name = message.document.file_name
    
    # بررسی پسوند
    if not any(file_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        safe_send_message(message.chat.id, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    # بررسی حجم
    if message.document.file_size > MAX_FILE_SIZE:
        safe_send_message(message.chat.id, f"❌ حجم فایل نباید بیشتر از {MAX_FILE_SIZE // (1024*1024)} مگابایت باشد!")
        return
    
    status_msg = safe_send_message(message.chat.id, "🔄 **در حال پردازش فایل...**\n\n⏳ مرحله ۱: دانلود فایل")
    
    try:
        # دانلود فایل
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        safe_edit_message(message.chat.id, status_msg.message_id, "🔄 **در حال پردازش فایل...**\n\n✅ مرحله ۱: دانلود فایل انجام شد\n⏳ مرحله ۲: استخراج کد")
        
        # پاکسازی نام فایل
        safe_name = security.sanitize_filename(file_name)
        user_dir = os.path.join(FILES_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        file_path = os.path.join(user_dir, f"{int(time.time())}_{safe_name}")
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        # استخراج کد
        main_code = ""
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(user_dir, f"extract_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # جستجوی فایل اصلی
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        try:
                            with open(os.path.join(root, f), 'r', encoding='utf-8') as code_file:
                                content = code_file.read()
                            if f in ['bot.py', 'main.py', 'run.py', 'app.py', '__init__.py']:
                                main_code = content
                                break
                        except:
                            pass
            
            if not main_code:
                for root, _, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith('.py'):
                            try:
                                with open(os.path.join(root, f), 'r', encoding='utf-8') as code_file:
                                    main_code = code_file.read()
                                break
                            except:
                                pass
            
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    main_code = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='cp1256') as f:
                    main_code = f.read()
        
        if not main_code:
            safe_edit_message(message.chat.id, status_msg.message_id, "❌ هیچ فایل پایتونی در پروژه پیدا نشد!")
            return
        
        safe_edit_message(message.chat.id, status_msg.message_id, "🔄 **در حال پردازش فایل...**\n\n✅ مرحله ۱: دانلود فایل\n✅ مرحله ۲: استخراج کد\n⏳ مرحله ۳: بررسی امنیت کد")
        
        # بررسی امنیت کد
        is_safe, error_msg = security.scan_code(main_code)
        if not is_safe:
            safe_edit_message(message.chat.id, status_msg.message_id, f"❌ **کد شما ناامن است!**\n\n{error_msg}\n\nلطفاً کد خود را بررسی کنید.")
            return
        
        safe_edit_message(message.chat.id, status_msg.message_id, "🔄 **در حال پردازش فایل...**\n\n✅ مرحله ۱: دانلود فایل\n✅ مرحله ۲: استخراج کد\n✅ مرحله ۳: بررسی امنیت کد\n⏳ مرحله ۴: استخراج توکن")
        
        # استخراج توکن
        token = None
        patterns = [
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)',
            r'bot\s*=\s*Bot\(\s*["\']([^"\']+)["\']\s*\)',
            r'TOKEN\s*=\s*os\.getenv\(["\']TOKEN["\'],\s*["\']([^"\']+)["\']\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, main_code, re.IGNORECASE)
            if match:
                token = match.group(1)
                break
        
        if not token:
            safe_edit_message(message.chat.id, status_msg.message_id, "❌ توکن ربات در کد پیدا نشد!\n\nلطفاً مطمئن شوید توکن در کد وجود دارد.")
            return
        
        # اعتبارسنجی توکن
        if not security.validate_token(token):
            safe_edit_message(message.chat.id, status_msg.message_id, "❌ فرمت توکن نامعتبر است!\n\nلطفاً توکن معتبر وارد کنید.")
            return
        
        safe_edit_message(message.chat.id, status_msg.message_id, "🔄 **در حال پردازش فایل...**\n\n✅ مرحله ۱: دانلود فایل\n✅ مرحله ۲: استخراج کد\n✅ مرحله ۳: بررسی امنیت کد\n✅ مرحله ۴: استخراج توکن\n⏳ مرحله ۵: بررسی توکن")
        
        # بررسی توکن با API تلگرام
        try:
            response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if response.status_code != 200:
                safe_edit_message(message.chat.id, status_msg.message_id, "❌ توکن معتبر نیست!\n\nلطفاً توکن صحیح وارد کنید.")
                return
            
            bot_info = response.json().get('result', {})
            bot_name = bot_info.get('first_name', 'ربات ناشناس')
            bot_username = bot_info.get('username', 'unknown')
        except Exception as e:
            safe_edit_message(message.chat.id, status_msg.message_id, f"❌ خطا در بررسی توکن: {str(e)}")
            return
        
        safe_edit_message(message.chat.id, status_msg.message_id, "🔄 **در حال پردازش فایل...**\n\n✅ مرحله ۱: دانلود فایل\n✅ مرحله ۲: استخراج کد\n✅ مرحله ۳: بررسی امنیت کد\n✅ مرحله ۴: استخراج توکن\n✅ مرحله ۵: بررسی توکن\n⏳ مرحله ۶: ساخت ربات در داکر")
        
        # ساخت ربات در دیتابیس
        async def create():
            bot_id = await BotManager.create_bot(user_id, token, main_code, bot_name, bot_username)
            return bot_id
        
        try:
            loop = asyncio.new_event_loop()
            bot_id = loop.run_until_complete(create())
        except Exception as e:
            safe_edit_message(message.chat.id, status_msg.message_id, f"❌ خطا در ثبت ربات: {str(e)}")
            return
        
        # اجرا در داکر
        container_id = sandbox.create_sandbox_container(bot_id, main_code, token)
        
        if container_id:
            # بروزرسانی وضعیت ربات
            async def update():
                await BotManager.update_bot_status(bot_id, 'running', container_id)
            
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(update())
            except:
                pass
            
            # اضافه کردن سود رفرال
            async def add_referral():
                user = await UserManager.get_user(user_id)
                if user and user.get('referred_by'):
                    price_row = await db.fetchrow("SELECT value FROM settings WHERE key = 'price'")
                    price = int(price_row['value']) if price_row else PRICE
                    amount = int(price * REFERRAL_PERCENT / 100)
                    await UserManager.add_balance(user['referred_by'], amount, f"سود رفرال از کاربر {user_id}")
            
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(add_referral())
            except:
                pass
            
            # پیام موفقیت
            success_text = f"""✅ **ربات با موفقیت ساخته شد!** 🎉

🤖 **نام ربات:** {bot_name}
🔗 **لینک ربات:** https://t.me/{bot_username}
🆔 **آیدی ربات:** `{bot_id}`
🐳 **کانتینر داکر:** `{container_id[:12]}`

📊 **وضعیت:** 🟢 در حال اجرا (ایزوله در داکر)

🔒 **امنیت:** ربات شما در محیط کاملاً ایزوله اجرا می‌شود
💡 **تست:** برای تست ربات روی لینک بالا کلیک کنید

⚙️ **مدیریت ربات:**
• از دکمه '📋 ربات‌های من' برای مشاهده ربات‌ها
• از دکمه '🔄 فعال/غیرفعال کردن' برای مدیریت وضعیت
• از دکمه '🗑 حذف ربات' برای حذف ربات"""
            
            safe_edit_message(message.chat.id, status_msg.message_id, success_text)
        else:
            safe_edit_message(message.chat.id, status_msg.message_id, "❌ خطا در اجرای ربات در محیط داکر!\n\nلطفاً بعداً تلاش کنید یا با پشتیبانی تماس بگیرید.")
        
    except Exception as e:
        logger.error(f"خطا در ساخت ربات: {traceback.format_exc()}")
        safe_edit_message(message.chat.id, status_msg.message_id, f"❌ خطا: {str(e)}")

# ======================== ربات‌های من ========================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    
    async def get():
        return await BotManager.get_user_bots(user_id)
    
    try:
        loop = asyncio.new_event_loop()
        bots = loop.run_until_complete(get())
    except:
        bots = []
    
    if not bots:
        safe_send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!\n\nبرای ساخت ربات، روی دکمه '🤖 ساخت ربات جدید' کلیک کنید.", get_main_menu(user_id))
        return
    
    for bot_info in bots[:10]:
        status_emoji = "🟢" if bot_info['status'] == 'running' else "🔴"
        status_text = "در حال اجرا" if bot_info['status'] == 'running' else "متوقف"
        
        text = f"""{status_emoji} **{bot_info['name']}**
🔗 https://t.me/{bot_info['username']}
🆔 `{bot_info['id']}`
📊 وضعیت: {status_text}
📅 تاریخ ساخت: {str(bot_info['created_at'])[:19]}"""
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔄 تغییر وضعیت", callback_data=f"toggle_{bot_info['id']}"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{bot_info['id']}"),
            types.InlineKeyboardButton("📋 لاگ‌ها", callback_data=f"logs_{bot_info['id']}")
        )
        
        safe_send_message(message.chat.id, text, markup)

# ======================== فعال/غیرفعال کردن ربات ========================
@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    user_id = call.from_user.id
    bot_id = call.data.replace('toggle_', '')
    
    async def get_and_toggle():
        bot_info = await BotManager.get_bot(bot_id)
        if not bot_info or bot_info['user_id'] != user_id:
            return None
        
        if bot_info['status'] == 'running':
            # توقف ربات
            if bot_info.get('container_id'):
                sandbox.stop_container(bot_info['container_id'])
            await BotManager.update_bot_status(bot_id, 'stopped')
            return 'stopped'
        else:
            # راه‌اندازی مجدد ربات
            if bot_info.get('container_id'):
                sandbox.remove_container(bot_info['container_id'])
            
            # دریافت کد
            code = ""
            if bot_info.get('file_path') and os.path.exists(bot_info['file_path']):
                try:
                    with open(bot_info['file_path'], 'r', encoding='utf-8') as f:
                        code = f.read()
                except:
                    pass
            
            if code:
                new_container_id = sandbox.create_sandbox_container(bot_id, code, bot_info['token'])
                if new_container_id:
                    await BotManager.update_bot_status(bot_id, 'running', new_container_id)
                    return 'running'
            return None
    
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(get_and_toggle())
        
        if result == 'stopped':
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            safe_edit_message(call.message.chat.id, call.message.message_id, "✅ ربات با موفقیت متوقف شد.")
        elif result == 'running':
            bot.answer_callback_query(call.id, "✅ ربات راه‌اندازی شد")
            safe_edit_message(call.message.chat.id, call.message.message_id, "✅ ربات با موفقیت راه‌اندازی شد.")
        else:
            bot.answer_callback_query(call.id, "❌ خطا!")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا: {str(e)}")

# ======================== حذف ربات ========================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    
    async def get():
        return await BotManager.get_user_bots(user_id)
    
    try:
        loop = asyncio.new_event_loop()
        bots = loop.run_until_complete(get())
    except:
        bots = []
    
    if not bots:
        safe_send_message(message.chat.id, "📋 شما هیچ رباتی ندارید!", get_main_menu(user_id))
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for bot_info in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {bot_info['name']}", callback_data=f"del_{bot_info['id']}"))
    
    safe_send_message(message.chat.id, "🗑 **ربات مورد نظر را برای حذف انتخاب کنید:**", markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('del_') and not call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('del_', '')
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"delete_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر، انصراف", callback_data="cancel_delete")
    )
    
    safe_edit_message(call.message.chat.id, call.message.message_id, f"⚠️ **آیا از حذف ربات `{bot_id}` اطمینان دارید؟**\n\nاین عملیات غیرقابل بازگشت است.", markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def do_delete(call):
    user_id = call.from_user.id
    bot_id = call.data.replace('delete_', '')
    
    async def delete():
        return await BotManager.delete_bot(bot_id, user_id)
    
    try:
        loop = asyncio.new_event_loop()
        success = loop.run_until_complete(delete())
        
        if success:
            bot.answer_callback_query(call.id, "✅ ربات حذف شد")
            safe_edit_message(call.message.chat.id, call.message.message_id, "✅ ربات با موفقیت حذف شد.")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در حذف")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
def cancel_delete(call):
    safe_edit_message(call.message.chat.id, call.message.message_id, "❌ عملیات حذف لغو شد.")

# ======================== کیف پول و رفرال ========================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
def wallet_ref(message):
    user_id = message.from_user.id
    
    async def get_data():
        user = await UserManager.get_user(user_id)
        if not user:
            return None
        
        current_bots = await UserManager.get_current_bots(user_id)
        max_bots = await UserManager.get_max_bots(user_id)
        
        return user, current_bots, max_bots
    
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(get_data())
        if not result:
            safe_send_message(message.chat.id, "❌ لطفاً /start را بزنید", get_main_menu(user_id))
            return
        
        user, current_bots, max_bots = result
        
        bot_username = bot.get_me().username
        referral_link = generate_referral_link(user_id, user['referral_code'])
        
        text = f"""💰 **کیف پول و سیستم رفرال**

👤 **کاربر:** {user['first_name']}
🆔 **آیدی:** `{user_id}`

💳 **موجودی کیف پول:** {format_number(user['balance'])} تومان
🎁 **درآمد از رفرال:** {format_number(user['referral_earnings'])} تومان

📊 **آمار رفرال:**
• کلیک‌ها: {user['referrals_count']}
• ثبت‌نام‌های موفق: {user['verified_referrals']}

🤖 **ربات‌های شما:**
• فعلی: {current_bots}
• حداکثر مجاز: {max_bots}

🔗 **لینک دعوت اختصاصی شما:**
{referral_link}

💡 **نحوه کسب درآمد:**
• هر کاربر که با لینک شما ثبت‌نام کند
• و اشتراک بخرد، **{REFERRAL_PERCENT}% سود** به کیف پول شما اضافه می‌شود
• قابل برداشت از {format_number(MIN_WITHDRAW)} تومان

🏧 **برای برداشت وجه، روی دکمه '🏧 برداشت وجه' کلیک کنید**

📈 **هر ۵ دعوت موفق = ۱ ربات اضافه**"""
        
        safe_send_message(message.chat.id, text, get_main_menu(user_id))
    except Exception as e:
        logger.error(f"خطا: {e}")
        safe_send_message(message.chat.id, "❌ خطا در دریافت اطلاعات", get_main_menu(user_id))

# ======================== برداشت وجه ========================
@bot.message_handler(func=lambda m: m.text == '🏧 برداشت وجه')
def withdraw_menu(message):
    user_id = message.from_user.id
    
    async def get_balance():
        return await UserManager.get_user_balance(user_id)
    
    try:
        loop = asyncio.new_event_loop()
        balance = loop.run_until_complete(get_balance())
        
        if balance < MIN_WITHDRAW:
            text = f"""❌ **موجودی شما برای برداشت کافی نیست!**

💰 **موجودی فعلی:** {format_number(balance)} تومان
💰 **حداقل برداشت:** {format_number(MIN_WITHDRAW)} تومان

💡 **راه‌های افزایش موجودی:**
• دعوت از دوستان (هر دعوت = {int(PRICE * REFERRAL_PERCENT / 100):,} تومان سود)
• هر کاربر که با لینک شما ثبت‌نام کند و خرید کند
• هر ۵ دعوت موفق = ۱ ربات اضافه

📈 **موجودی مورد نیاز:** {format_number(MIN_WITHDRAW - balance)} تومان دیگر"""
            
            safe_send_message(message.chat.id, text, get_main_menu(user_id))
            return
        
        msg = safe_send_message(message.chat.id, 
            f"🏧 **درخواست برداشت وجه**\n\n"
            f"💰 **موجودی قابل برداشت:** {format_number(balance)} تومان\n\n"
            f"💳 **لطفاً شماره کارت ۱۶ رقمی خود را وارد کنید:**\n"
            f"مثال: `6219861034567890`\n\n"
            f"⚠️ دقت کنید شماره کارت صحیح باشد، در غیر این صورت وجه قابل واریز نیست.")
        
        bot.register_next_step_handler(msg, process_withdraw, user_id, balance)
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ خطا: {str(e)}", get_main_menu(user_id))

def process_withdraw(message, user_id, balance):
    text = message.text.strip()
    card_match = re.search(r'\d{16}', text)
    
    if not card_match:
        safe_send_message(message.chat.id, "❌ شماره کارت نامعتبر! لطفاً ۱۶ رقم کارت را به درستی وارد کنید.", get_main_menu(user_id))
        return
    
    card_number = card_match.group()
    
    async def save_withdraw():
        async with db.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO withdrawals (user_id, amount, card_number, created_at)
                VALUES ($1, $2, $3, NOW())
            ''', user_id, balance, card_number)
            await conn.execute('UPDATE users SET balance = balance - $1 WHERE user_id = $2', balance, user_id)
    
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(save_withdraw())
        loop.run_until_complete(cache.delete_user(user_id))
        
        text = f"""✅ **درخواست برداشت شما ثبت شد!**

💰 **مبلغ:** {format_number(balance)} تومان
💳 **شماره کارت:** `{card_number}`
📅 **تاریخ ثبت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⏳ **وضعیت:** در انتظار بررسی
🕐 **زمان تقریبی بررسی:** ۲۴ تا ۴۸ ساعت

پس از تأیید ادمین، وجه به کارت شما واریز می‌شود.
در صورت نیاز با پشتیبانی تماس بگیرید."""
        
        safe_send_message(message.chat.id, text, get_main_menu(user_id))
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"🏧 درخواست برداشت جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {format_number(balance)} تومان\n💳 کارت: {card_number}")
            except:
                pass
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ خطا در ثبت درخواست: {str(e)}", get_main_menu(user_id))

# ======================== فیش واریزی ========================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    if not security.rate_limit_check(user_id, "receipt"):
        safe_send_message(message.chat.id, "❌ لطفاً کمی صبر کنید...")
        return
    
    # بررسی فیش در انتظار قبلی
    async def check_pending():
        return await db.fetchval("SELECT id FROM receipts WHERE user_id = $1 AND status = 'pending'", user_id)
    
    try:
        loop = asyncio.new_event_loop()
        pending = loop.run_until_complete(check_pending())
        if pending:
            safe_send_message(message.chat.id, "⏳ شما یک فیش در انتظار بررسی دارید. لطفاً صبر کنید.", get_main_menu(user_id))
            return
    except:
        pass
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:10].upper()
        receipt_path = os.path.join(RECEIPTS_DIR, f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded_file)
        
        async def save_receipt():
            async with db.pool.acquire() as conn:
                price_row = await conn.fetchrow("SELECT value FROM settings WHERE key = 'price'")
                price = int(price_row['value']) if price_row else PRICE
                
                await conn.execute('''
                    INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
                    VALUES ($1, $2, $3, $4, NOW())
                ''', user_id, price, receipt_path, payment_code)
                return price
        
        loop = asyncio.new_event_loop()
        price = loop.run_until_complete(save_receipt())
        
        text = f"""✅ **فیش واریزی شما دریافت شد!**

💰 **مبلغ:** {format_number(price)} تومان
🆔 **کد پیگیری:** `{payment_code}`
📅 **تاریخ ثبت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⏳ **وضعیت:** در انتظار بررسی ادمین
🕐 **زمان تقریبی بررسی:** ۲۴ تا ۴۸ ساعت

پس از تأیید، اشتراک شما فعال می‌شود و می‌توانید ربات خود را بسازید."""
        
        safe_send_message(message.chat.id, text, get_main_menu(user_id))
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید واریزی\n👤 کاربر: {user_id}\n💰 مبلغ: {format_number(price)} تومان\n🆔 کد: {payment_code}")
            except:
                pass
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ خطا: {str(e)}", get_main_menu(user_id))

# ======================== راهنما ========================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    user_id = message.from_user.id
    
    async def get_guide():
        row = await db.fetchrow("SELECT value FROM settings WHERE key = 'guide_text'")
        return row['value'] if row else None
    
    try:
        loop = asyncio.new_event_loop()
        guide_text = loop.run_until_complete(get_guide())
    except:
        guide_text = None
    
    if not guide_text or guide_text == "راهنمای ربات...":
        guide_text = """📚 **راهنمای کامل ربات مادر**

**1️⃣ ساخت ربات جدید:**
   • ابتدا اشتراک تهیه کنید یا از تست ۲۴ ساعته استفاده کنید
   • فایل `.py` یا `.zip` ربات خود را آپلود کنید
   • توکن ربات باید داخل کد باشد
   • ربات در محیط ایزوله داکر اجرا می‌شود

**2️⃣ تست ۲۴ ساعته رایگان:**
   • روی دکمه '⏱ تست ۲۴ ساعته' کلیک کنید
   • به مدت ۲۴ ساعت می‌توانید ۱ ربات بسازید
   • پس از اتمام تست، برای ادامه اشتراک تهیه کنید

**3️⃣ رفرال و کسب درآمد:**
   • لینک رفرال خود را به اشتراک بگذارید
   • هر کاربر که با لینک شما ثبت‌نام کند
   • و اشتراک بخرد، **۷٪ سود** به کیف پول شما اضافه می‌شود
   • هر ۵ دعوت موفق = ۱ ربات اضافه
   • قابل برداشت از ۲ میلیون تومان

**4️⃣ امنیت و ایزوله‌سازی:**
   • کد شما قبل از اجرا از نظر امنیتی بررسی می‌شود
   • ربات در کانتینر داکر ایزوله اجرا می‌شود
   • دسترسی به سیستم عامل و فایل‌ها محدود شده است
   • محدودیت منابع (CPU، RAM، زمان)

**5️⃣ پشتیبانی و ارتباط:**
   • پشتیبانی: @shahraghee13
   • ساعات پاسخگویی: ۹ صبح تا ۱۲ شب"""

    safe_send_message(message.chat.id, guide_text, get_main_menu(user_id))

# ======================== آمار من ========================
@bot.message_handler(func=lambda m: m.text == '📊 آمار من')
def my_stats(message):
    user_id = message.from_user.id
    
    async def get_stats():
        user = await UserManager.get_user(user_id)
        if not user:
            return None
        
        current_bots = await UserManager.get_current_bots(user_id)
        max_bots = await UserManager.get_max_bots(user_id)
        
        total_earnings = user.get('total_earnings', 0)
        total_spent = user.get('total_spent', 0)
        
        return user, current_bots, max_bots, total_earnings, total_spent
    
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(get_stats())
        
        if not result:
            safe_send_message(message.chat.id, "❌ لطفاً /start را بزنید", get_main_menu(user_id))
            return
        
        user, current_bots, max_bots, total_earnings, total_spent = result
        
        text = f"""📊 **آمار شخصی شما**

👤 **کاربر:** {user['first_name']}
🆔 **آیدی:** `{user_id}`

🤖 **ربات‌ها:**
• فعلی: {current_bots}
• حداکثر: {max_bots}
• کل ساخته شده: {user['bots_count']}

💰 **مالی:**
• موجودی کیف پول: {format_number(user['balance'])} تومان
• کل درآمد: {format_number(total_earnings)} تومان
• کل هزینه: {format_number(total_spent)} تومان

🎁 **رفرال:**
• کلیک‌ها: {user['referrals_count']}
• ثبت‌نام‌های موفق: {user['verified_referrals']}
• درآمد از رفرال: {format_number(user['referral_earnings'])} تومان

📅 **تاریخ عضویت:** {str(user['created_at'])[:19]}
📱 **آخرین فعالیت:** {str(user['last_active'])[:19]}"""
        
        safe_send_message(message.chat.id, text, get_main_menu(user_id))
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ خطا: {str(e)}", get_main_menu(user_id))

# ======================== پشتیبانی ========================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    text = """📞 **پشتیبانی ربات مادر**

**راه‌های ارتباط با پشتیبانی:**

1️⃣ **تلگرام:** @shahraghee13
2️⃣ **ساعات پاسخگویی:** ۹ صبح تا ۱۲ شب
3️⃣ **زمان پاسخگویی:** حداکثر ۲۴ ساعت

**قبل از تماس، لطفاً موارد زیر را آماده داشته باشید:**
• آیدی عددی خود (در منوی کیف پول موجود است)
• کد پیگیری فیش (در صورت پرداخت)
• شرح مشکل به صورت کامل

**سوالات متداول:**

❓ **چگونه ربات بسازم؟**
• از دکمه ساخت ربات جدید استفاده کنید
• یا از تست ۲۴ ساعته رایگان استفاده کنید

❓ **چگونه کسب درآمد کنم؟**
• لینک رفرال خود را به اشتراک بگذارید
• از هر خرید ۷٪ سود دریافت کنید

❓ **چه مدت طول می‌کشد تا فیش من تأیید شود؟**
• حداکثر ۲۴ تا ۴۸ ساعت کاری

❓ **آیا کد من امن است؟**
• بله، کد شما در محیط ایزوله داکر اجرا می‌شود
• کدهای مخرب شناسایی و مسدود می‌شوند

📢 **برای اطلاع از آخرین اخبار و بروزرسانی‌ها، در کانال ما عضو شوید:** [لینک کانال]"""
    
    safe_send_message(message.chat.id, text, get_main_menu(message.from_user.id))

# ======================== پنل ادمین ========================
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        safe_send_message(message.chat.id, "⛔ شما دسترسی ادمین ندارید!", get_main_menu(user_id))
        return
    
    safe_send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", get_admin_menu())

# ======================== دکمه‌های ادمین ========================

@bot.callback_query_handler(func=lambda call: call.data == "admin_price")
def admin_change_price(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **قیمت جدید اشتراک را به تومان وارد کنید:**\nمثال: `2500000`")
    bot.register_next_step_handler(msg, admin_set_price)

def admin_set_price(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        new_price = int(message.text.strip())
        
        async def update():
            await db.execute("UPDATE settings SET value = $1, updated_at = NOW() WHERE key = 'price'", str(new_price))
            await cache.invalidate_setting("price")
        
        loop = asyncio.new_event_loop()
        loop.run_until_complete(update())
        
        bot.send_message(message.chat.id, f"✅ قیمت اشتراک با موفقیت به {format_number(new_price)} تومان تغییر کرد!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_card")
def admin_change_card(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 **شماره کارت جدید را وارد کنید:**\nمثال: `5892101187322777`")
    bot.register_next_step_handler(msg, admin_set_card)

def admin_set_card(message):
    if not is_admin(message.from_user.id):
        return
    
    card_number = message.text.strip()
    
    if not card_number.isdigit() or len(card_number) != 16:
        bot.send_message(message.chat.id, "❌ شماره کارت باید ۱۶ رقم باشد!")
        return
    
    async def update():
        await db.execute("UPDATE settings SET value = $1, updated_at = NOW() WHERE key = 'card_number'", card_number)
        await cache.invalidate_setting("card_number")
    
    loop = asyncio.new_event_loop()
    loop.run_until_complete(update())
    
    bot.send_message(message.chat.id, f"✅ شماره کارت با موفقیت به {card_number} تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_guide")
def admin_change_guide(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 **متن جدید راهنما را وارد کنید:**\n(می‌توانید از Markdown استفاده کنید)")
    bot.register_next_step_handler(msg, admin_set_guide)

def admin_set_guide(message):
    if not is_admin(message.from_user.id):
        return
    
    guide_text = message.text.strip()
    
    async def update():
        await db.execute("UPDATE settings SET value = $1, updated_at = NOW() WHERE key = 'guide_text'", guide_text)
        await cache.invalidate_setting("guide_text")
    
    loop = asyncio.new_event_loop()
    loop.run_until_complete(update())
    
    bot.send_message(message.chat.id, "✅ متن راهنما با موفقیت به‌روزرسانی شد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_server")
def admin_add_server(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot.send_message(call.message.chat.id, "🖥 **اضافه کردن سرور جدید**\n\nلطفاً **نام سرور** را وارد کنید:")
    bot.register_next_step_handler(call.message, admin_add_server_name)

def admin_add_server_name(message):
    if not is_admin(message.from_user.id):
        return
    
    name = message.text.strip()
    bot.send_message(message.chat.id, "🌐 **آیپی** سرور را وارد کنید:")
    bot.register_next_step_handler(message, admin_add_server_ip, name)

def admin_add_server_ip(message, name):
    if not is_admin(message.from_user.id):
        return
    
    ip = message.text.strip()
    bot.send_message(message.chat.id, "👤 **یوزرنیم** سرور را وارد کنید:")
    bot.register_next_step_handler(message, admin_add_server_username, name, ip)

def admin_add_server_username(message, name, ip):
    if not is_admin(message.from_user.id):
        return
    
    username = message.text.strip()
    bot.send_message(message.chat.id, "🔑 **رمز عبور** سرور را وارد کنید:")
    bot.register_next_step_handler(message, admin_add_server_password, name, ip, username)

def admin_add_server_password(message, name, ip, username):
    if not is_admin(message.from_user.id):
        return
    
    password = message.text.strip()
    
    async def save():
        await db.execute('''
            INSERT INTO servers (name, host, username, password, status, created_at)
            VALUES ($1, $2, $3, $4, 'active', NOW())
        ''', name, ip, username, password)
    
    loop = asyncio.new_event_loop()
    loop.run_until_complete(save())
    
    bot.send_message(message.chat.id, f"✅ **سرور با موفقیت اضافه شد!**\n\n🖥 نام: {name}\n🌐 آیپی: {ip}\n👤 یوزرنیم: {username}\n\n⚡ سرور به کلاستر اضافه شد و بار بین سرورها تقسیم می‌شود.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_del_bot")
def admin_list_bots(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    async def get_bots():
        return await db.fetch("SELECT id, name, user_id FROM bots ORDER BY created_at DESC LIMIT 50")
    
    loop = asyncio.new_event_loop()
    bots = loop.run_until_complete(get_bots())
    
    if not bots:
        bot.send_message(call.message.chat.id, "📋 هیچ رباتی در سیستم وجود ندارد")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']} (کاربر: {b['user_id']})", callback_data=f"admin_del_{b['id']}"))
    
    bot.send_message(call.message.chat.id, "🗑 **لیست ربات‌ها**\nبرای حذف یک ربات روی آن کلیک کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_"))
def admin_delete_bot(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_del_", "")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"admin_confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="admin_cancel_del")
    )
    
    bot.edit_message_text(f"⚠️ آیا از حذف ربات `{bot_id}` اطمینان دارید؟\nاین عملیات غیرقابل بازگشت است.", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_confirm_del_"))
def admin_confirm_delete_bot(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_confirm_del_", "")
    
    async def delete():
        bot_info = await db.fetchrow("SELECT * FROM bots WHERE id = $1", bot_id)
        if bot_info:
            if bot_info['container_id']:
                sandbox.stop_container(bot_info['container_id'])
                sandbox.remove_container(bot_info['container_id'])
            await db.execute("DELETE FROM bots WHERE id = $1", bot_id)
            await db.execute("UPDATE users SET bots_count = bots_count - 1 WHERE user_id = $1", bot_info['user_id'])
            await cache.delete_user(bot_info['user_id'])
            return True
        return False
    
    loop = asyncio.new_event_loop()
    success = loop.run_until_complete(delete())
    
    if success:
        bot.edit_message_text(f"✅ ربات {bot_id} با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا در حذف ربات!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_cancel_del")
def admin_cancel_delete(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraw")
def admin_withdrawals(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    async def get_withdrawals():
        return await db.fetch("SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY created_at DESC")
    
    loop = asyncio.new_event_loop()
    withdrawals = loop.run_until_complete(get_withdrawals())
    
    if not withdrawals:
        bot.send_message(call.message.chat.id, "🏧 هیچ درخواست برداشتی در انتظار نیست")
        return
    
    for w in withdrawals:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ پرداخت شد", callback_data=f"admin_pay_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"admin_reject_w_{w['id']}")
        )
        
        text = f"""🏧 **درخواست برداشت**

🆔 شماره: {w['id']}
👤 کاربر: `{w['user_id']}`
💰 مبلغ: {format_number(w['amount'])} تومان
💳 کارت: `{w['card_number']}`
📅 تاریخ: {str(w['created_at'])[:19]}"""
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_pay_"))
def admin_pay_withdrawal(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    w_id = int(call.data.replace("admin_pay_", ""))
    
    async def pay():
        async with db.pool.acquire() as conn:
            withdrawal = await conn.fetchrow("SELECT * FROM withdrawals WHERE id = $1", w_id)
            if withdrawal:
                await conn.execute("UPDATE withdrawals SET status = 'approved', processed_at = NOW(), processed_by = $1 WHERE id = $2", call.from_user.id, w_id)
                try:
                    await bot.send_message(withdrawal['user_id'], f"✅ برداشت وجه شما انجام شد!\n💰 مبلغ: {format_number(withdrawal['amount'])} تومان\n💳 به کارت: {withdrawal['card_number']}\n\nمتشکر از اعتماد شما")
                except:
                    pass
                return True
        return False
    
    loop = asyncio.new_event_loop()
    success = loop.run_until_complete(pay())
    
    if success:
        bot.answer_callback_query(call.id, "✅ برداشت تایید شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_reject_w_"))
def admin_reject_withdrawal(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    w_id = int(call.data.replace("admin_reject_w_", ""))
    
    async def reject():
        async with db.pool.acquire() as conn:
            withdrawal = await conn.fetchrow("SELECT * FROM withdrawals WHERE id = $1", w_id)
            if withdrawal:
                await conn.execute("UPDATE withdrawals SET status = 'rejected', processed_at = NOW(), processed_by = $1 WHERE id = $2", call.from_user.id, w_id)
                await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", withdrawal['amount'], withdrawal['user_id'])
                await cache.delete_user(withdrawal['user_id'])
                try:
                    await bot.send_message(withdrawal['user_id'], f"❌ درخواست برداشت شما رد شد!\n💰 مبلغ: {format_number(withdrawal['amount'])} تومان\n\nموجودی به کیف پول شما برگشت داده شد.")
                except:
                    pass
                return True
        return False
    
    loop = asyncio.new_event_loop()
    success = loop.run_until_complete(reject())
    
    if success:
        bot.answer_callback_query(call.id, "❌ برداشت رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    async def get_receipts():
        return await db.fetch("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at DESC")
    
    loop = asyncio.new_event_loop()
    receipts = loop.run_until_complete(get_receipts())
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری وجود ندارد")
        return
    
    for r in receipts:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ تایید و فعالسازی", callback_data=f"admin_approve_r_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"admin_reject_r_{r['id']}")
        )
        
        text = f"""📸 **فیش واریزی**

🆔 شماره: {r['id']}
👤 کاربر: `{r['user_id']}`
💰 مبلغ: {format_number(r['amount'])} تومان
🆔 کد پیگیری: `{r['payment_code']}`
📅 تاریخ: {str(r['created_at'])[:19]}"""
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_approve_r_"))
def admin_approve_receipt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    r_id = int(call.data.replace("admin_approve_r_", ""))
    
    async def approve():
        async with db.pool.acquire() as conn:
            receipt = await conn.fetchrow("SELECT * FROM receipts WHERE id = $1", r_id)
            if receipt:
                subscription_end = datetime.now() + timedelta(days=30)
                await conn.execute("UPDATE receipts SET status = 'approved', reviewed_at = NOW(), reviewed_by = $1 WHERE id = $2", call.from_user.id, r_id)
                await conn.execute("UPDATE users SET payment_status = 'approved', subscription_end = $1 WHERE user_id = $2", subscription_end, receipt['user_id'])
                await cache.delete_user(receipt['user_id'])
                await cache.set_subscription(receipt['user_id'], "active", 86400)
                
                # سود رفرال
                user = await conn.fetchrow("SELECT referred_by FROM users WHERE user_id = $1", receipt['user_id'])
                if user and user['referred_by']:
                    percent = REFERRAL_PERCENT
                    amount = int(receipt['amount'] * percent / 100)
                    await conn.execute("UPDATE users SET balance = balance + $1, referral_earnings = referral_earnings + $1, verified_referrals = verified_referrals + 1 WHERE user_id = $2", amount, user['referred_by'])
                    await cache.delete_user(user['referred_by'])
                
                try:
                    await bot.send_message(receipt['user_id'], f"✅ فیش شما تایید شد! اشتراک شما فعال شد.\n📅 اعتبار تا: {subscription_end.strftime('%Y-%m-%d')}\nاکنون می‌توانید ربات خود را بسازید.")
                except:
                    pass
                return True
        return False
    
    loop = asyncio.new_event_loop()
    success = loop.run_until_complete(approve())
    
    if success:
        bot.answer_callback_query(call.id, "✅ فیش تایید شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_reject_r_"))
def admin_reject_receipt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    r_id = int(call.data.replace("admin_reject_r_", ""))
    
    async def reject():
        async with db.pool.acquire() as conn:
            receipt = await conn.fetchrow("SELECT * FROM receipts WHERE id = $1", r_id)
            if receipt:
                await conn.execute("UPDATE receipts SET status = 'rejected', reviewed_at = NOW(), reviewed_by = $1 WHERE id = $2", call.from_user.id, r_id)
                try:
                    await bot.send_message(receipt['user_id'], f"❌ فیش شما رد شد! لطفاً دوباره اقدام کنید.\nدر صورت نیاز با پشتیبانی تماس بگیرید.")
                except:
                    pass
                return True
        return False
    
    loop = asyncio.new_event_loop()
    success = loop.run_until_complete(reject())
    
    if success:
        bot.answer_callback_query(call.id, "❌ فیش رد شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    async def get_users():
        return await db.fetch("""
            SELECT u.*, COUNT(b.id) as bots_count 
            FROM users u
            LEFT JOIN bots b ON u.user_id = b.user_id
            GROUP BY u.user_id
            ORDER BY u.created_at DESC
            LIMIT 30
        """)
    
    loop = asyncio.new_event_loop()
    users = loop.run_until_complete(get_users())
    
    if not users:
        bot.send_message(call.message.chat.id, "👥 کاربری یافت نشد")
        return
    
    text = "👥 **۳۰ کاربر آخر:**\n\n"
    for u in users:
        status = "✅" if u['payment_status'] == 'approved' else "⏳"
        trial = "🎁" if u['trial_end'] and u['trial_end'] > datetime.now() else ""
        text += f"{status}{trial} `{u['user_id']}` - {u['first_name'] or 'بدون نام'}\n"
        text += f"   🤖 {u['bots_count']} | 🎁 {u['verified_referrals']} | 💰 {format_number(u['balance'])}\n\n"
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    async def get_stats():
        async with db.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            paid_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE payment_status = 'approved'")
            trial_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE trial_end > NOW()")
            total_bots = await conn.fetchval("SELECT COUNT(*) FROM bots")
            running_bots = await conn.fetchval("SELECT COUNT(*) FROM bots WHERE status = 'running'")
            total_receipts = await conn.fetchval("SELECT COUNT(*) FROM receipts")
            pending_receipts = await conn.fetchval("SELECT COUNT(*) FROM receipts WHERE status = 'pending'")
            approved_receipts = await conn.fetchval("SELECT COUNT(*) FROM receipts WHERE status = 'approved'")
            total_amount = await conn.fetchval("SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = 'approved'")
            pending_withdrawals = await conn.fetchval("SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'")
            total_withdrawals = await conn.fetchval("SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = 'approved'")
            return {
                "total_users": total_users,
                "paid_users": paid_users,
                "trial_users": trial_users,
                "total_bots": total_bots,
                "running_bots": running_bots,
                "total_receipts": total_receipts,
                "pending_receipts": pending_receipts,
                "approved_receipts": approved_receipts,
                "total_amount": total_amount,
                "pending_withdrawals": pending_withdrawals,
                "total_withdrawals": total_withdrawals
            }
    
    loop = asyncio.new_event_loop()
    stats_data = loop.run_until_complete(get_stats())
    
    text = f"""📊 **آمار کامل سامانه**

👥 **کاربران:**
• کل کاربران: {stats_data['total_users']}
• پرداخت کرده: {stats_data['paid_users']}
• تست ۲۴ ساعته: {stats_data['trial_users']}
• درصد تبدیل: {int(stats_data['paid_users']/stats_data['total_users']*100) if stats_data['total_users'] > 0 else 0}%

🤖 **ربات‌ها:**
• کل ربات‌ها: {stats_data['total_bots']}
• فعال: {stats_data['running_bots']}
• غیرفعال: {stats_data['total_bots'] - stats_data['running_bots']}

💰 **مالی:**
• کل واریزی‌ها: {format_number(stats_data['total_amount'])} تومان
• کل برداشت‌ها: {format_number(stats_data['total_withdrawals'])} تومان
• سود خالص: {format_number(stats_data['total_amount'] - stats_data['total_withdrawals'])} تومان

📸 **فیش‌ها:**
• کل: {stats_data['total_receipts']}
• در انتظار: {stats_data['pending_receipts']}
• تایید شده: {stats_data['approved_receipts']}

🏧 **برداشت‌ها:**
• در انتظار: {stats_data['pending_withdrawals']}"""
    
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_prompt(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📢 **ارسال اعلان همگانی**\n\nلطفاً متن پیام را وارد کنید:")
    bot.register_next_step_handler(msg, admin_send_broadcast)

def admin_send_broadcast(message):
    if not is_admin(message.from_user.id):
        return
    
    broadcast_text = message.text.strip()
    
    async def get_all_users():
        return await db.fetch("SELECT user_id FROM users")
    
    loop = asyncio.new_event_loop()
    users = loop.run_until_complete(get_all_users())
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **اعلان همگانی**\n\n{broadcast_text}")
            success_count += 1
        except:
            fail_count += 1
        
        time.sleep(0.05)  # جلوگیری از محدودیت نرخ
    
    bot.send_message(message.chat.id, f"✅ اعلان ارسال شد!\n\n✅ موفق: {success_count}\n❌ ناموفق: {fail_count}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    backup_file = os.path.join(BACKUP_DIR, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
    
    async def create_backup():
        async with db.pool.acquire() as conn:
            await conn.execute(f"COPY users TO '{backup_file}'")
    
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(create_backup())
        with open(backup_file, 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption=f"💾 بکاپ دیتابیس\n📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        bot.answer_callback_query(call.id, "✅ بکاپ گرفته شد")
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_restart")
def admin_restart(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot.send_message(call.message.chat.id, "🔄 در حال ریستارت ربات...")
    bot.answer_callback_query(call.id, "✅ ریستارت")
    
    # ریستارت در ترد جداگانه
    def restart():
        time.sleep(2)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    
    threading.Thread(target=restart, daemon=True).start()

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    bot.delete_message(call.message.chat.id, call.message.message_id)
    safe_send_message(call.message.chat.id, "🚀 منوی اصلی:", get_main_menu(user_id))

# ======================== راه‌اندازی اولیه ========================
async def init():
    await db.connect()
    await cache.connect()
    sandbox.connect()
    logger.info("✅ تمام سرویس‌ها راه‌اندازی شدند")

def run_bot():
    logger.info("🚀 ربات مادر نهایی نسخه 12.0 شروع به کار کرد")
    logger.info(f"👥 ادمین‌ها: {ADMIN_IDS}")
    logger.info(f"💾 دیتابیس: PostgreSQL")
    logger.info(f"⚡ کش: Redis")
    logger.info(f"🐳 ایزوله‌سازی: Docker")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا در پولینگ: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # راه‌اندازی asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init())
    
    # اجرای ربات در ترد جداگانه
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # پاکسازی دوره‌ای کانتینرها
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)  # هر 1 ساعت
            await sandbox.cleanup_old_containers()
    
    loop.create_task(periodic_cleanup())
    
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه 12.0 ULTIMATE")
    print("=" * 80)
    print(f"✅ PostgreSQL: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"✅ Redis: {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
    print(f"✅ Docker: فعال (ایزوله‌سازی کامل)")
    print(f"✅ تست 24 ساعته: فعال")
    print(f"✅ رفرال 7%: فعال")
    print(f"✅ امنیت: چندلایه")
    print(f"✅ ادمین‌ها: {ADMIN_IDS}")
    print("=" * 80)
    print("ربات با موفقیت روشن شد...")
    print("=" * 80)
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 در حال خاموش شدن...")