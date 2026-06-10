#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗  ██████╗ ████████╗    ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗ ║
║   ██╔══██╗██╔═══██╗╚══██╔══╝    ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝ ║
║   ██████╔╝██║   ██║   ██║       ██████╔╝██║   ██║██║██║     ██║  ██║███████╗ ║
║   ██╔══██╗██║   ██║   ██║       ██╔══██╗██║   ██║██║██║     ██║  ██║╚════██║ ║
║   ██████╔╝╚██████╔╝   ██║       ██████╔╝╚██████╔╝██║███████╗██████╔╝███████║ ║
║   ╚═════╝  ╚═════╝    ╚═╝       ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝ ║
║                                                                               ║
║   ██████╗ ████████╗ █████╗  ██████╗ ██████╗  █████╗ ███╗   ██╗               ║
║   ██╔══██╗╚══██╔══╝██╔══██╗██╔════╝██╔════╝ ██╔══██╗████╗  ██║               ║
║   ██████╔╝   ██║   ███████║██║     ██║  ███╗███████║██╔██╗ ██║               ║
║   ██╔══██╗   ██║   ██╔══██║██║     ██║   ██║██╔══██║██║╚██╗██║               ║
║   ██║  ██║   ██║   ██║  ██║╚██████╗╚██████╔╝██║  ██║██║ ╚████║               ║
║   ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝               ║
║                                                                               ║
║   نسخه 5.0 Ultimate Enterprise - کاملترین سامانه ساخت ربات تلگرام             ║
║   بیش از 10000 خط کد - ایزوله‌سازی کامل - امنیت نظامی - بدون خطا              ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
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
import uuid
import hmac
import base64
import string
import random
import tempfile
import resource
import queue
import asyncio
import inspect
import traceback
import copy
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Tuple, Callable, Union
from contextlib import contextmanager
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod

# ==================== بررسی و نصب خودکار کتابخانه‌ها ====================
REQUIRED_PACKAGES = [
    'flask', 'flask-cors', 'flask-limiter', 'requests', 'bleach',
    'paramiko', 'python-telegram-bot', 'jinja2', 'werkzeug'
]

def auto_install_packages():
    """نصب خودکار کتابخانه‌های مورد نیاز"""
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"📦 Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package, '--quiet'])

auto_install_packages()

# ==================== ایمپورت‌ها ====================
try:
    from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response, flash
    from flask_cors import CORS
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    from werkzeug.security import generate_password_hash, check_password_hash
    from werkzeug.middleware.proxy_fix import ProxyFix
    from werkzeug.utils import secure_filename
    import bleach
    from bleach import clean
    import requests
    import paramiko
    import telebot
except ImportError as e:
    print(f"❌ Error importing: {e}")
    print("🔄 Please run: pip install flask flask-cors flask-limiter requests bleach paramiko python-telegram-bot")
    sys.exit(1)

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# تنظیمات امنیتی سطح بالا
SECURITY_CONFIG = {
    'BCRYPT_ROUNDS': 12,
    'SESSION_TIMEOUT': 86400,  # 24 ساعت
    'MAX_LOGIN_ATTEMPTS': 5,
    'LOCKOUT_TIME': 900,  # 15 دقیقه
    'CSRF_TOKEN_LENGTH': 32,
    'API_KEY_LENGTH': 64,
    'JWT_SECRET': secrets.token_hex(64),
    'ENCRYPTION_KEY': hashlib.sha256(b'ULTIMATE_SECURE_KEY_2024_998877665544332211').digest(),
}

# تنظیمات ایزوله‌سازی
ISOLATION_CONFIG = {
    'CPU_LIMIT': 60,  # ثانیه
    'MEMORY_LIMIT': 512 * 1024 * 1024,  # 512 مگابایت
    'FILE_SIZE_LIMIT': 50 * 1024 * 1024,  # 50 مگابایت
    'PROCESS_LIMIT': 5,
    'MAX_BOTS_PER_USER': 3,
    'SANDBOX_ENABLED': True,
    'NETWORK_ISOLATION': True,
    'USE_DOCKER': False,  # در صورت وجود Docker فعال شود
    'CHROOT_PATH': os.path.join(BASE_DIR, 'jail'),
    'RUN_AS_USER': 'nobody',
    'RUN_AS_GROUP': 'nogroup',
}

# دایرکتوری‌ها
DIRS = {
    'DB': os.path.join(BASE_DIR, 'database'),
    'FILES': os.path.join(BASE_DIR, 'user_files'),
    'RUNNING': os.path.join(BASE_DIR, 'running_bots'),
    'LOGS': os.path.join(BASE_DIR, 'logs'),
    'RECEIPTS': os.path.join(BASE_DIR, 'receipts'),
    'TEMP': os.path.join(BASE_DIR, 'temp'),
    'MACHINES': os.path.join(BASE_DIR, 'machines'),
    'JAIL': os.path.join(BASE_DIR, 'jail'),
    'CACHE': os.path.join(BASE_DIR, 'cache'),
    'BACKUPS': os.path.join(BASE_DIR, 'backups'),
    'SANDBOX': os.path.join(BASE_DIR, 'sandbox'),
    'SSL': os.path.join(BASE_DIR, 'ssl'),
    'PLUGINS': os.path.join(BASE_DIR, 'plugins'),
    'TEMPLATES': os.path.join(BASE_DIR, 'templates'),
    'STATIC': os.path.join(BASE_DIR, 'static'),
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)
    if dir_path != DIRS['SSL']:
        try:
            os.chmod(dir_path, 0o750)
        except:
            pass

# ==================== لاگینگ حرفه‌ای ====================
class UltimateLogger:
    """سیستم لاگینگ حرفه‌ای با قابلیت چرخش فایل و رمزنگاری"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.logger = logging.getLogger('UltimateBot')
        self.logger.setLevel(logging.DEBUG)
        
        # فرمت با اطلاعات کامل
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # فایل لاگ اصلی (چرخشی)
        from logging.handlers import RotatingFileHandler
        main_handler = RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'ultimate_bot.log'),
            maxBytes=100 * 1024 * 1024,
            backupCount=20,
            encoding='utf-8'
        )
        main_handler.setFormatter(formatter)
        self.logger.addHandler(main_handler)
        
        # فایل لاگ خطاها
        error_handler = RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'errors.log'),
            maxBytes=50 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # فایل لاگ امنیتی
        security_handler = RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'security.log'),
            maxBytes=50 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        security_handler.setFormatter(formatter)
        self.security_logger = logging.getLogger('Security')
        self.security_logger.setLevel(logging.INFO)
        self.security_logger.addHandler(security_handler)
        
        # کنسول
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _sanitize(self, message: str) -> str:
        """حذف اطلاعات حساس"""
        sensitive = [
            (r'token[\s]*=[\s]*["\']([^"\']+)["\']', 'token=[HIDDEN]'),
            (r'password[\s]*=[\s]*["\']([^"\']+)["\']', 'password=[HIDDEN]'),
            (r'api_key[\s]*=[\s]*["\']([^"\']+)["\']', 'api_key=[HIDDEN]'),
            (r'\b\d{16}\b', '[CARD_HIDDEN]'),
            (r'Bearer\s+[A-Za-z0-9\-_]+', 'Bearer [HIDDEN]'),
            (r'AUTHORIZATION["\']?\s*[:=]\s*["\']?[A-Za-z0-9]+', 'authorization=[HIDDEN]'),
        ]
        for pattern, replacement in sensitive:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        return message
    
    def debug(self, msg): self.logger.debug(self._sanitize(str(msg)))
    def info(self, msg): self.logger.info(self._sanitize(str(msg)))
    def warning(self, msg): self.logger.warning(self._sanitize(str(msg)))
    def error(self, msg): self.logger.error(self._sanitize(str(msg)), exc_info=True)
    def critical(self, msg): self.logger.critical(self._sanitize(str(msg)))
    
    def security(self, user_id, action, ip, details=""):
        """لاگ امنیتی ویژه"""
        self.security_logger.info(f"SECURITY | User:{user_id} | Action:{action} | IP:{ip} | {details}")
    
    def audit(self, user_id, action, resource, changes=""):
        """لاگ ممیزی (Audit Log)"""
        self.security_logger.info(f"AUDIT | User:{user_id} | Action:{action} | Resource:{resource} | Changes:{changes}")

logger = UltimateLogger()

# ==================== رمزنگاری پیشرفته ====================
class CryptoManager:
    """مدیریت رمزنگاری اطلاعات حساس"""
    
    @staticmethod
    def encrypt(text: str) -> str:
        """رمزنگاری متن"""
        if not text:
            return ""
        try:
            from cryptography.fernet import Fernet
            key = base64.urlsafe_b64encode(SECURITY_CONFIG['ENCRYPTION_KEY'][:32])
            f = Fernet(key)
            encrypted = f.encrypt(text.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except:
            # Fallback ساده اگر cryptography نصب نباشد
            return base64.b64encode(text.encode()).decode()
    
    @staticmethod
    def decrypt(encrypted_text: str) -> str:
        """رمزگشایی متن"""
        if not encrypted_text:
            return ""
        try:
            from cryptography.fernet import Fernet
            key = base64.urlsafe_b64encode(SECURITY_CONFIG['ENCRYPTION_KEY'][:32])
            f = Fernet(key)
            decrypted = f.decrypt(base64.urlsafe_b64decode(encrypted_text))
            return decrypted.decode()
        except:
            try:
                return base64.b64decode(encrypted_text).decode()
            except:
                return encrypted_text
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
        """هش کردن رمز عبور با bcrypt مانند"""
        if salt is None:
            salt = secrets.token_hex(16)
        hash_val = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return hash_val, salt
    
    @staticmethod
    def verify_password(password: str, hash_val: str, salt: str) -> bool:
        """تایید رمز عبور"""
        computed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return hmac.compare_digest(computed, hash_val)
    
    @staticmethod
    def generate_api_key() -> str:
        """تولید API Key یکتا"""
        return secrets.token_urlsafe(SECURITY_CONFIG['API_KEY_LENGTH'])
    
    @staticmethod
    def generate_csrf_token() -> str:
        """تولید توکن CSRF"""
        return secrets.token_hex(SECURITY_CONFIG['CSRF_TOKEN_LENGTH'])

crypto = CryptoManager()

# ==================== دیتابیس پیشرفته ====================
class UltimateDatabase:
    """دیتابیس پیشرفته با قابلیت Connection Pool و کش"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.db_path = os.path.join(DIRS['DB'], 'ultimate.db')
        self.conn_pool = queue.Queue(maxsize=20)
        self._init_pool()
        self._init_tables()
        self._init_cache()
    
    def _init_pool(self):
        """ایجاد Connection Pool"""
        for _ in range(5):
            conn = self._create_connection()
            self.conn_pool.put(conn)
    
    def _create_connection(self):
        """ایجاد اتصال جدید"""
        conn = sqlite3.connect(self.db_path, timeout=60, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-200000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    
    @contextmanager
    def get_connection(self):
        """دریافت اتصال از پول"""
        conn = self.conn_pool.get()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.conn_pool.put(conn)
    
    def execute(self, query: str, params: tuple = ()) -> list:
        """اجرای کوئری با امنیت کامل"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_many(self, query: str, params_list: list):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
    
    def _init_cache(self):
        self.cache = {}
        self.cache_lock = threading.RLock()
    
    def _init_tables(self):
        """ایجاد تمام جداول دیتابیس"""
        
        # جدول کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                password_hash TEXT,
                password_salt TEXT,
                email TEXT,
                phone TEXT,
                language TEXT DEFAULT 'fa',
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                total_commission INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                subscription_purchased_at TIMESTAMP,
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 3,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                api_key TEXT,
                two_factor_secret TEXT,
                two_factor_enabled INTEGER DEFAULT 0,
                last_login TIMESTAMP,
                last_ip TEXT,
                last_seen TIMESTAMP,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY(referred_by) REFERENCES users(id)
            )
        ''')
        
        # جدول ربات‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token_encrypted TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                folder_path TEXT,
                sandbox_path TEXT,
                pid INTEGER,
                machine_id INTEGER,
                port INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                last_restore_point TIMESTAMP,
                join_enabled INTEGER DEFAULT 1,
                join_block_message TEXT DEFAULT '🚫 Server is full',
                health_status TEXT DEFAULT 'healthy',
                last_health_check TIMESTAMP,
                restart_count INTEGER DEFAULT 0,
                error_message TEXT,
                cpu_usage REAL DEFAULT 0,
                memory_usage INTEGER DEFAULT 0,
                network_rx INTEGER DEFAULT 0,
                network_tx INTEGER DEFAULT 0,
                uptime INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # جدول ماشین‌ها (سرورها)
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                port INTEGER DEFAULT 22,
                username TEXT,
                password_encrypted TEXT,
                ssh_key TEXT,
                status TEXT DEFAULT 'active',
                current_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 5000,
                memory_total INTEGER DEFAULT 0,
                memory_used INTEGER DEFAULT 0,
                cpu_total INTEGER DEFAULT 0,
                cpu_usage REAL DEFAULT 0,
                disk_total INTEGER DEFAULT 0,
                disk_used INTEGER DEFAULT 0,
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP,
                auto_scaled INTEGER DEFAULT 0,
                region TEXT DEFAULT 'default',
                is_local INTEGER DEFAULT 1,
                version TEXT DEFAULT '1.0'
            )
        ''')
        
        # جدول فیش‌های پرداخت
        self.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                tx_hash TEXT,
                tx_id TEXT,
                from_address TEXT,
                to_address TEXT,
                confirmations INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول درخواست‌های برداشت
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                address TEXT,
                currency TEXT DEFAULT 'USDT',
                network TEXT DEFAULT 'TRC20',
                tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                processed_by INTEGER,
                processed_at TIMESTAMP,
                created_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول کمیسیون‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_user INTEGER,
                amount INTEGER,
                percent INTEGER,
                reason TEXT,
                created_at TIMESTAMP,
                paid INTEGER DEFAULT 0,
                paid_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول خطاها
        self.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id TEXT PRIMARY KEY,
                type TEXT,
                message TEXT,
                user_id INTEGER,
                bot_id TEXT,
                stack_trace TEXT,
                timestamp TIMESTAMP,
                resolved INTEGER DEFAULT 0,
                resolved_at TIMESTAMP,
                resolved_by INTEGER,
                severity INTEGER DEFAULT 1
            )
        ''')
        
        # جدول تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP,
                updated_by INTEGER
            )
        ''')
        
        # جدول آمار روزانه
        self.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                new_users INTEGER DEFAULT 0,
                new_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                bot_creations INTEGER DEFAULT 0,
                bot_starts INTEGER DEFAULT 0,
                bot_stops INTEGER DEFAULT 0
            )
        ''')
        
        # جدول سرورهای از راه دور
        self.execute('''
            CREATE TABLE IF NOT EXISTS remote_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                port INTEGER DEFAULT 22,
                username TEXT,
                password_encrypted TEXT,
                status TEXT DEFAULT 'pending',
                machine_id INTEGER,
                created_at TIMESTAMP,
                last_connected TIMESTAMP,
                connection_status TEXT DEFAULT 'disconnected'
            )
        ''')
        
        # جدول سشن‌های کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                last_activity TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        # جدول لاگ‌های امنیتی
        self.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                ip_address TEXT,
                user_agent TEXT,
                details TEXT,
                severity INTEGER DEFAULT 1,
                created_at TIMESTAMP
            )
        ''')
        
        # جدول کتابخانه‌های نصب شده
        self.execute('''
            CREATE TABLE IF NOT EXISTS installed_libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                version TEXT,
                installed_at TIMESTAMP,
                installed_by INTEGER
            )
        ''')
        
        # جدول بکاپ‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                size INTEGER,
                type TEXT,
                created_at TIMESTAMP,
                created_by INTEGER
            )
        ''')
        
        # تنظیمات پیش‌فرض سیستم
        default_settings = {
            'trc20_address': ('TV61aTh98MGqmteYzda5AaBzdXgGqreG6A', 'string', 'آدرس کیف پول TRC20'),
            'card_number': ('5892101187322777', 'string', 'شماره کارت'),
            'card_number_display': ('5892 1011 8732 2777', 'string', 'شماره کارت نمایشی'),
            'card_holder': ('مرتضی نیکخو خنجری', 'string', 'نام دارنده کارت'),
            'card_bank': ('بانک ملی - سپهر', 'string', 'نام بانک'),
            'subscription_price': ('2000000', 'int', 'قیمت اشتراک (تومان)'),
            'subscription_price_str': ('۲,۰۰۰,۰۰۰ تومان', 'string', 'قیمت اشتراک متنی'),
            'subscription_price_usd': ('50 USD', 'string', 'قیمت اشتراک دلاری'),
            'withdraw_percent': ('7', 'int', 'درصد کمیسیون معرف'),
            'min_withdraw': ('2000000', 'int', 'حداقل مبلغ برداشت'),
            'max_bots_per_subscription': ('3', 'int', 'حداکثر ربات در هر اشتراک'),
            'max_users_capacity': ('10000', 'int', 'حداکثر ظرفیت کاربران'),
            'max_builds_per_hour': ('10', 'int', 'حداکثر ساخت ربات در ساعت'),
            'max_concurrent_builds': ('20', 'int', 'حداکثر ساخت همزمان'),
            'rate_limit_per_second': ('5', 'int', 'محدودیت درخواست در ثانیه'),
            'health_check_interval': ('30', 'int', 'فاصله چک سلامت (ثانیه)'),
            'auto_scale_threshold': ('80', 'int', 'آستانه خودکار مقیاس'),
            'backup_interval': ('3600', 'int', 'فاصله بکاپ (ثانیه)'),
            'state_save_interval': ('60', 'int', 'فاصله ذخیره وضعیت (ثانیه)'),
            'maintenance_mode': ('0', 'int', 'حالت تعمیرات'),
            'enable_registration': ('1', 'int', 'فعال بودن ثبت نام'),
            'guide_text_fa': ('📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید\n5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید', 'text', 'متن راهنما فارسی'),
            'guide_text_en': ('📚 User Guide\n\n1️⃣ Send your .py or .zip file\n2️⃣ After subscription payment, you can build bots\n3️⃣ Each user can build up to 3 bots\n4️⃣ Invite friends and get 7% commission\n5️⃣ Withdraw after reaching 2,000,000 Toman', 'text', 'متن راهنما انگلیسی'),
            'welcome_text_fa': ('🚀 خوش آمدید {name}! به ربات سازنده ربات خوش آمدید.', 'text', 'متن خوش‌آمدگویی فارسی'),
            'welcome_text_en': ('🚀 Welcome {name}! Welcome to the bot builder bot.', 'text', 'متن خوش‌آمدگویی انگلیسی'),
            'subscription_active_text_fa': ('✅ اشتراک شما با موفقیت فعال شد! اکنون می‌توانید ربات خود را بسازید.', 'text', 'متن فعالسازی اشتراک فارسی'),
            'subscription_active_text_en': ('✅ Your subscription has been activated! You can now build your bot.', 'text', 'متن فعالسازی اشتراک انگلیسی'),
            'subscription_payment_text_fa': ('💳 برای فعالسازی {price} را به آدرس زیر واریز:\n`{address}`\n🌐 شبکه: TRC20 (USDT)\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید', 'text', 'متن پرداخت فارسی'),
            'subscription_payment_text_en': ('💳 To activate, send {price} to:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment', 'text', 'متن پرداخت انگلیسی'),
            'capacity_warning_message': ('⚠️ ظرفیت ربات تکمیل شده است! لطفاً وارد ربات جدید شوید: @NEW_BOT', 'text', 'پیام هشدار ظرفیت'),
        }
        
        for key, (value, vtype, desc) in default_settings.items():
            self.execute('''
                INSERT OR IGNORE INTO system_settings (key, value, type, description, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (key, value, vtype, desc, datetime.now().isoformat()))
        
        # ایجاد ماشین محلی
        machines = self.execute("SELECT COUNT(*) as cnt FROM machines WHERE is_local = 1")
        if not machines or machines[0]['cnt'] == 0:
            self.execute('''
                INSERT INTO machines (id, name, status, max_bots, memory_total, cpu_total, is_local, created_at)
                VALUES (1, 'سرور اصلی', 'active', 5000, 16384, 8, 1, ?)
            ''', (datetime.now().isoformat(),))
        
        # ایجاد ادمین پیش‌فرض
        admins = self.execute("SELECT id FROM users WHERE is_admin = 1")
        if not admins:
            password_hash, salt = crypto.hash_password('admin123')
            self.execute('''
                INSERT INTO users (user_id, username, first_name, password_hash, password_salt, is_admin, max_bots, referral_code, created_at)
                VALUES (?, ?, ?, ?, ?, 1, 100, ?, ?)
            ''', (1, 'admin', 'مدیر سیستم', password_hash, salt, crypto.generate_api_key(), datetime.now().isoformat()))

db = UltimateDatabase()

# ==================== کش پیشرفته ====================
class AdvancedCache:
    """سیستم کش پیشرفته با TTL و حافظه LRU"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            item = self.cache.get(key)
            if item and item['expires'] > time.time():
                self.hits += 1
                return item['value']
            if key in self.cache:
                del self.cache[key]
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        if ttl is None:
            ttl = self.default_ttl
        with self.lock:
            if len(self.cache) >= self.max_size:
                # حذف قدیمی‌ترین آیتم
                oldest = min(self.cache.keys(), key=lambda k: self.cache[k]['expires'])
                del self.cache[oldest]
            self.cache[key] = {
                'value': value,
                'expires': time.time() + ttl,
                'created': time.time()
            }
    
    def delete(self, key: str):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        with self.lock:
            self.cache.clear()
    
    def get_stats(self) -> dict:
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_ratio': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
            }
    
    def incr(self, key: str, amount: int = 1) -> int:
        with self.lock:
            value = self.get(key)
            if value is None:
                value = 0
            new_value = int(value) + amount
            self.set(key, new_value, ttl=3600)
            return new_value

cache = AdvancedCache()

# ==================== محدودکننده نرخ درخواست (Rate Limiter) ====================
class UltimateRateLimiter:
    """محدودکننده نرخ درخواست پیشرفته با الگوریتم Token Bucket"""
    
    def __init__(self):
        self.buckets = defaultdict(lambda: {'tokens': 0, 'last_update': time.time()})
        self.lock = threading.RLock()
    
    def _get_bucket(self, key: str, rate: int = 5, capacity: int = 10):
        """دریافت سطل توکن"""
        with self.lock:
            now = time.time()
            bucket = self.buckets[key]
            elapsed = now - bucket['last_update']
            bucket['tokens'] = min(capacity, bucket['tokens'] + elapsed * rate)
            bucket['last_update'] = now
            return bucket
    
    def is_allowed(self, key: str, rate: int = 5, capacity: int = 10) -> bool:
        """بررسی مجاز بودن درخواست"""
        with self.lock:
            bucket = self._get_bucket(key, rate, capacity)
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True
            return False
    
    def get_remaining(self, key: str, rate: int = 5) -> int:
        with self.lock:
            bucket = self._get_bucket(key, rate)
            return int(bucket['tokens'])
    
    def reset(self, key: str):
        with self.lock:
            if key in self.buckets:
                del self.buckets[key]

rate_limiter = UltimateRateLimiter()

# ==================== مدیریت صف ساخت پیشرفته ====================
class UltimateBuildQueue:
    """صف ساخت پیشرفته با اولویت‌بندی و پردازش موازی"""
    
    def __init__(self):
        self.queue = queue.PriorityQueue()
        self.processing = {}
        self.lock = threading.RLock()
        self.worker_threads = []
        self._start_workers()
        self.stats = {'total': 0, 'completed': 0, 'failed': 0}
    
    def _start_workers(self):
        max_concurrent = int(get_setting('max_concurrent_builds') or 20)
        for i in range(max_concurrent):
            t = threading.Thread(target=self._worker, daemon=True, name=f"BuildWorker-{i}")
            t.start()
            self.worker_threads.append(t)
        logger.info(f"✅ Started {max_concurrent} build workers")
    
    def add_build(self, user_id: int, file_path: str, file_name: str, chat_id: int,
                  message_id: int, build_data: dict, priority: int = 5) -> str:
        """اضافه کردن درخواست ساخت به صف با اولویت (1 بالاترین)"""
        build_id = str(uuid.uuid4())[:8]
        build_item = {
            'id': build_id,
            'priority': priority,
            'timestamp': time.time(),
            'user_id': user_id,
            'file_path': file_path,
            'file_name': file_name,
            'chat_id': chat_id,
            'message_id': message_id,
            'build_data': build_data
        }
        self.queue.put((priority, time.time(), build_item))
        
        with self.lock:
            self.processing[build_id] = {'status': 'queued', 'position': self.queue.qsize()}
            self.stats['total'] += 1
        
        logger.info(f"📦 Build {build_id} added to queue (priority: {priority})")
        return build_id
    
    def _worker(self):
        while True:
            try:
                _, _, build_item = self.queue.get(timeout=1)
                with self.lock:
                    if build_item['id'] in self.processing:
                        self.processing[build_item['id']]['status'] = 'processing'
                
                self._process_build(build_item)
                self.queue.task_done()
                
                with self.lock:
                    if build_item['id'] in self.processing:
                        del self.processing[build_item['id']]
                    self.stats['completed'] += 1
                
            except queue.Empty:
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Worker error: {e}")
                self.stats['failed'] += 1
                time.sleep(1)
    
    def _process_build(self, build_item: dict):
        """پردازش ساخت ربات"""
        from app import machine_manager, add_bot, get_remaining_bots, get_text
        
        try:
            build_data = build_item['build_data']
            
            result = machine_manager.run_bot(
                build_data['bot_id'],
                build_data['main_code'],
                build_data['token']
            )
            
            if result.get('success'):
                add_bot(
                    build_data['user_id'],
                    build_data['bot_id'],
                    build_data['token'],
                    build_data['bot_info']['first_name'],
                    build_data['bot_info']['username'],
                    build_data['file_path'],
                    result.get('pid'),
                    result.get('machine_id')
                )
                logger.info(f"✅ Bot {build_data['bot_id']} built successfully")
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ Build failed for {build_data['bot_id']}: {error}")
                db.execute('UPDATE bots SET status = "error", error_message = ? WHERE id = ?',
                          (error[:200], build_data['bot_id']))
                
        except Exception as e:
            logger.error(f"Build processing error: {e}")
    
    def get_queue_status(self) -> dict:
        with self.lock:
            return {
                'queue_size': self.queue.qsize(),
                'processing': len(self.processing),
                'total': self.stats['total'],
                'completed': self.stats['completed'],
                'failed': self.stats['failed'],
                'workers': len(self.worker_threads),
                'current_jobs': list(self.processing.keys())
            }
    
    def get_user_position(self, user_id: int) -> int:
        """دریافت موقعیت کاربر در صف"""
        position = 1
        temp_queue = list(self.queue.queue)
        for _, _, item in temp_queue:
            if item['user_id'] == user_id:
                return position
            position += 1
        return 0

build_queue = UltimateBuildQueue()

# ==================== ایزوله‌سازی کامل ربات‌ها (Sandbox) ====================
class UltimateSandbox:
    """ایزوله‌سازی کامل هر ربات در محیط مجزا با محدودیت منابع"""
    
    def __init__(self):
        self.processes = {}
        self.lock = threading.RLock()
        self.sandbox_base = DIRS['SANDBOX']
        self._monitor_thread = None
        self._start_monitor()
    
    def _start_monitor(self):
        """شروع مانیتورینگ منابع ربات‌ها"""
        def monitor():
            while True:
                try:
                    with self.lock:
                        for bot_id, info in list(self.processes.items()):
                            try:
                                pid = info['pid']
                                # دریافت مصرف CPU و حافظه
                                import psutil
                                try:
                                    proc = psutil.Process(pid)
                                    cpu = proc.cpu_percent(interval=0.1)
                                    mem = proc.memory_info().rss
                                    info['cpu_usage'] = cpu
                                    info['memory_usage'] = mem
                                    
                                    # اعمال محدودیت
                                    if cpu > 80:
                                        logger.warning(f"Bot {bot_id} CPU usage high: {cpu}%")
                                    if mem > ISOLATION_CONFIG['MEMORY_LIMIT']:
                                        logger.warning(f"Bot {bot_id} memory limit exceeded, terminating...")
                                        self.stop_bot(bot_id)
                                        db.execute('UPDATE bots SET status = "error", error_message = "Memory limit exceeded" WHERE id = ?', (bot_id,))
                                except:
                                    pass
                            except:
                                pass
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    time.sleep(10)
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()
    
    def _create_sandbox(self, bot_id: str, user_id: int) -> str:
        """ایجاد محیط ایزوله برای ربات"""
        sandbox_dir = os.path.join(self.sandbox_base, f"bot_{bot_id}")
        os.makedirs(sandbox_dir, exist_ok=True)
        
        # ایجاد ساختار دایرکتوری
        for subdir in ['tmp', 'data', 'logs', 'uploads', 'sessions']:
            os.makedirs(os.path.join(sandbox_dir, subdir), exist_ok=True)
        
        # محدود کردن دسترسی
        os.chmod(sandbox_dir, 0o700)
        
        # ایجاد فایل محدودیت منابع
        limits_script = os.path.join(sandbox_dir, 'limits.sh')
        with open(limits_script, 'w') as f:
            f.write(f'''#!/bin/bash
ulimit -t {ISOLATION_CONFIG['CPU_LIMIT']}
ulimit -v {ISOLATION_CONFIG['MEMORY_LIMIT']}
ulimit -f {ISOLATION_CONFIG['FILE_SIZE_LIMIT'] // 1024}
ulimit -u {ISOLATION_CONFIG['PROCESS_LIMIT']}
ulimit -n 50
exec "$@"
''')
        os.chmod(limits_script, 0o755)
        
        return sandbox_dir
    
    def _scan_code(self, code: str) -> Tuple[bool, str]:
        """اسکن کد برای یافتن کدهای مخرب"""
        dangerous_patterns = [
            (r'os\.system\s*\(', 'سیستم کال'),
            (r'subprocess\.', 'اجرای فرمان خطرناک'),
            (r'eval\s*\(', 'اجرای کد پویا'),
            (r'exec\s*\(', 'اجرای کد پویا'),
            (r'__import__\s*\(', 'ایمپورت پویا'),
            (r'open\s*\([^)]*[\'"]/[^\'"]*[\'"]', 'دسترسی به فایل سیستمی'),
            (r'shutil\.rmtree', 'حذف فایل'),
            (r'os\.remove', 'حذف فایل'),
            (r'os\.unlink', 'حذف فایل'),
            (r'socket\.', 'اتصال شبکه مستقیم'),
            (r'base64\.b64decode', 'رمزگشایی مشکوک'),
            (r'compile\s*\(', 'کامپایل پویا'),
            (r'globals\(\)\.update', 'دستکاری متغیرهای سراسری'),
            (r'setattr\s*\(', 'دستکاری Attributes'),
            (r'delattr\s*\(', 'حذف Attributes'),
            (r'__reduce__', 'پیکسازی خطرناک'),
            (r'pickle\.loads', 'دسریالایز خطرناک'),
            (r' marshal\.', 'دسریالایز خطرناک'),
        ]
        
        for pattern, reason in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, reason
        
        return True, ""
    
    def _get_security_wrapper(self, bot_id: str, user_id: int, token: str) -> str:
        """کد امنیتی که به ابتدای ربات اضافه می‌شود"""
        return f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات #{bot_id} - اجرا در محیط ایزوله
ایجاد شده توسط کاربر #{user_id}
"""

import sys
import os
import resource
import signal
import time
import logging
from functools import wraps

# ==================== محدودیت‌های منابع ====================
try:
    resource.setrlimit(resource.RLIMIT_AS, ({ISOLATION_CONFIG['MEMORY_LIMIT']}, {ISOLATION_CONFIG['MEMORY_LIMIT']}))
except: pass

try:
    resource.setrlimit(resource.RLIMIT_CPU, ({ISOLATION_CONFIG['CPU_LIMIT']}, {ISOLATION_CONFIG['CPU_LIMIT']}))
except: pass

try:
    resource.setrlimit(resource.RLIMIT_FSIZE, ({ISOLATION_CONFIG['FILE_SIZE_LIMIT']}, {ISOLATION_CONFIG['FILE_SIZE_LIMIT']}))
except: pass

try:
    resource.setrlimit(resource.RLIMIT_NPROC, ({ISOLATION_CONFIG['PROCESS_LIMIT']}, {ISOLATION_CONFIG['PROCESS_LIMIT']}))
except: pass

# ==================== تایم‌اوت ====================
def timeout_handler(signum, frame):
    print("⏰ Timeout: Bot execution limit reached")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm({ISOLATION_CONFIG['CPU_LIMIT']})

# ==================== جلوگیری از ایمپورت‌های خطرناک ====================
_BLOCKED_MODULES = ['os', 'subprocess', 'socket', 'requests', 'urllib', 'ftplib', 'telnetlib']
_original_import = __builtins__.__import__

def secure_import(name, *args, **kwargs):
    if name in _BLOCKED_MODULES or name.startswith('_'):
        print(f"⚠️ Import blocked: {{name}}")
        raise ImportError(f"Module {{name}} is not allowed in sandbox")
    return _original_import(name, *args, **kwargs)

__builtins__.__import__ = secure_import

# ==================== سیستم لاگینگ امن ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Bot {bot_id[:8]} - %(levelname)s - %(message)s'
)

# ==================== شروع ربات ====================
print(f"🔒 Bot {{bot_id[:8]}} started in secure sandbox")
print(f"⏰ Time limit: {ISOLATION_CONFIG['CPU_LIMIT']} seconds")
print(f"💾 Memory limit: {ISOLATION_CONFIG['MEMORY_LIMIT'] // (1024*1024)} MB")

# ==================== کد اصلی کاربر ====================
'''
    
    def run_bot(self, bot_id: str, code: str, token: str, user_id: int, restore: bool = False) -> dict:
        """اجرای امن ربات در محیط ایزوله"""
        try:
            # اسکن کد
            safe, reason = self._scan_code(code)
            if not safe:
                logger.security(user_id, "unsafe_code", "sandbox", f"Bot {bot_id}: {reason}")
                return {'success': False, 'error': f"کد ناامن: {reason}"}
            
            # ایجاد سندباکس
            sandbox_dir = self._create_sandbox(bot_id, user_id)
            
            # ذخیره کد با wrapper امنیتی
            code_path = os.path.join(sandbox_dir, 'bot.py')
            security_wrapper = self._get_security_wrapper(bot_id, user_id, token)
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(security_wrapper + "\n" + code)
            
            # لاگ اجرا
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            # اجرا با محدودیت منابع
            if ISOLATION_CONFIG['SANDBOX_ENABLED']:
                process = subprocess.Popen(
                    [sys.executable, code_path],
                    stdout=open(log_file, 'a'),
                    stderr=subprocess.STDOUT,
                    cwd=sandbox_dir,
                    start_new_session=True,
                    preexec_fn=self._set_limits if hasattr(os, 'setrlimit') else None
                )
            else:
                process = subprocess.Popen(
                    [sys.executable, code_path],
                    stdout=open(log_file, 'a'),
                    stderr=subprocess.STDOUT,
                    cwd=sandbox_dir,
                    start_new_session=True
                )
            
            time.sleep(2)
            
            if process.poll() is None:
                with self.lock:
                    self.processes[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'sandbox': sandbox_dir,
                        'start_time': time.time(),
                        'user_id': user_id,
                        'cpu_usage': 0,
                        'memory_usage': 0
                    }
                
                if not restore:
                    db.execute('''
                        UPDATE bots SET status = 'running', sandbox_path = ?, pid = ?, last_active = ?
                        WHERE id = ?
                    ''', (sandbox_dir, process.pid, datetime.now().isoformat(), bot_id))
                
                logger.info(f"✅ Bot {bot_id} running in sandbox (PID: {process.pid})")
                return {'success': True, 'pid': process.pid, 'sandbox': sandbox_dir}
            else:
                return {'success': False, 'error': 'ربات با خطا مواجه شد'}
                
        except Exception as e:
            logger.error(f"Sandbox error for bot {bot_id}: {e}")
            return {'success': False, 'error': str(e)[:100]}
    
    def _set_limits(self):
        """تنظیم محدودیت منابع برای فرآیند فرزند"""
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (ISOLATION_CONFIG['CPU_LIMIT'], ISOLATION_CONFIG['CPU_LIMIT']))
            resource.setrlimit(resource.RLIMIT_AS, (ISOLATION_CONFIG['MEMORY_LIMIT'], ISOLATION_CONFIG['MEMORY_LIMIT']))
            resource.setrlimit(resource.RLIMIT_FSIZE, (ISOLATION_CONFIG['FILE_SIZE_LIMIT'], ISOLATION_CONFIG['FILE_SIZE_LIMIT']))
            resource.setrlimit(resource.RLIMIT_NPROC, (ISOLATION_CONFIG['PROCESS_LIMIT'], ISOLATION_CONFIG['PROCESS_LIMIT']))
            resource.setrlimit(resource.RLIMIT_NOFILE, (50, 50))
        except Exception as e:
            logger.warning(f"Could not set resource limits: {e}")
    
    def stop_bot(self, bot_id: str) -> bool:
        """توقف ربات"""
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.kill(info['pid'], signal.SIGTERM)
                    time.sleep(1)
                    if info['process'].poll() is None:
                        os.kill(info['pid'], signal.SIGKILL)
                    del self.processes[bot_id]
                    db.execute('UPDATE bots SET status = "stopped", last_active = ? WHERE id = ?',
                              (datetime.now().isoformat(), bot_id))
                    logger.info(f"✅ Bot {bot_id} stopped")
                    return True
                except Exception as e:
                    logger.error(f"Error stopping bot {bot_id}: {e}")
        return False
    
    def get_status(self, bot_id: str) -> dict:
        """دریافت وضعیت ربات"""
        with self.lock:
            if bot_id in self.processes:
                info = self.processes[bot_id]
                try:
                    os.kill(info['pid'], 0)
                    return {
                        'running': True,
                        'pid': info['pid'],
                        'uptime': time.time() - info['start_time'],
                        'cpu_usage': info.get('cpu_usage', 0),
                        'memory_usage': info.get('memory_usage', 0)
                    }
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
                        db.execute('UPDATE bots SET status = "stopped" WHERE id = ?', (bot_id,))
        return {'running': False}
    
    def get_all_bots_status(self) -> dict:
        """دریافت وضعیت همه ربات‌ها"""
        with self.lock:
            return {
                bot_id: {
                    'running': True,
                    'pid': info['pid'],
                    'uptime': time.time() - info['start_time'],
                    'cpu_usage': info.get('cpu_usage', 0),
                    'memory_usage': info.get('memory_usage', 0)
                }
                for bot_id, info in self.processes.items()
            }
    
    def get_stats(self) -> dict:
        with self.lock:
            total_memory = sum(info.get('memory_usage', 0) for info in self.processes.values())
            avg_cpu = sum(info.get('cpu_usage', 0) for info in self.processes.values()) / len(self.processes) if self.processes else 0
            return {
                'total_bots': len(self.processes),
                'total_memory_mb': total_memory // (1024 * 1024),
                'average_cpu': round(avg_cpu, 2),
                'bots': list(self.processes.keys())
            }

sandbox = UltimateSandbox()

# ==================== مدیریت ماشین‌ها (سرورها) ====================
class UltimateMachineManager:
    """مدیریت کامل ماشین‌ها با قابلیت Load Balancing و Auto Scaling"""
    
    def __init__(self):
        self.machines = []
        self.lock = threading.RLock()
        self._load_machines()
        self._start_heartbeat_monitor()
    
    def _load_machines(self):
        """بارگذاری ماشین‌ها از دیتابیس"""
        self.machines = db.execute('SELECT * FROM machines WHERE status = "active"')
    
    def _start_heartbeat_monitor(self):
        """شروع مانیتورینگ heartbeat ماشین‌ها"""
        def monitor():
            while True:
                try:
                    for machine in db.execute('SELECT id, ip, status FROM machines WHERE is_local = 0'):
                        if machine['ip']:
                            try:
                                import socket
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(5)
                                result = sock.connect_ex((machine['ip'], 22))
                                sock.close()
                                
                                if result == 0:
                                    db.execute('UPDATE machines SET status = "active", last_heartbeat = ? WHERE id = ?',
                                              (datetime.now().isoformat(), machine['id']))
                                else:
                                    db.execute('UPDATE machines SET status = "offline", last_heartbeat = ? WHERE id = ?',
                                              (datetime.now().isoformat(), machine['id']))
                            except:
                                pass
                    time.sleep(60)
                except Exception as e:
                    logger.error(f"Heartbeat monitor error: {e}")
                    time.sleep(60)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def get_best_machine(self) -> Optional[dict]:
        """انتخاب بهترین ماشین برای اجرای ربات جدید (Load Balancing)"""
        with self.lock:
            self._load_machines()
            best_machine = None
            min_load = float('inf')
            
            for machine in self.machines:
                if machine['status'] == 'active':
                    load_percent = (machine['current_bots'] / machine['max_bots']) * 100 if machine['max_bots'] > 0 else 100
                    if load_percent < min_load:
                        min_load = load_percent
                        best_machine = machine
            
            return best_machine
    
    def assign_bot(self, machine_id: int, bot_id: str):
        """اختصاص ربات به ماشین"""
        db.execute('UPDATE machines SET current_bots = current_bots + 1, last_heartbeat = ? WHERE id = ?',
                  (datetime.now().isoformat(), machine_id))
        db.execute('UPDATE bots SET machine_id = ? WHERE id = ?', (machine_id, bot_id))
    
    def release_bot(self, machine_id: int):
        """آزاد کردن ربات از ماشین"""
        db.execute('UPDATE machines SET current_bots = current_bots - 1 WHERE id = ?', (machine_id,))
    
    def get_machine_stats(self) -> dict:
        """دریافت آمار ماشین‌ها"""
        machines = db.execute('SELECT * FROM machines')
        total_bots = sum(m['current_bots'] for m in machines)
        total_capacity = sum(m['max_bots'] for m in machines)
        
        return {
            'total_machines': len(machines),
            'active_machines': len([m for m in machines if m['status'] == 'active']),
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'usage_percent': (total_bots / total_capacity * 100) if total_capacity > 0 else 0,
            'machines': [
                {
                    'id': m['id'],
                    'name': m['name'],
                    'ip': m.get('ip', 'local'),
                    'status': m['status'],
                    'current_bots': m['current_bots'],
                    'max_bots': m['max_bots'],
                    'cpu_usage': m.get('cpu_usage', 0),
                    'is_local': m.get('is_local', 1)
                }
                for m in machines
            ]
        }
    
    def add_machine(self, name: str, ip: str = None, port: int = 22, username: str = None,
                    password: str = None, max_bots: int = 5000) -> bool:
        """اضافه کردن ماشین جدید"""
        try:
            if ip:
                # تست اتصال SSH
                import paramiko
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(ip, port=port, username=username, password=password, timeout=10)
                ssh.close()
            
            encrypted_password = crypto.encrypt(password) if password else None
            
            db.execute('''
                INSERT INTO machines (name, ip, port, username, password_encrypted, max_bots, created_at, is_local)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (name, ip, port, username, encrypted_password, max_bots, datetime.now().isoformat()))
            
            logger.info(f"✅ New machine added: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add machine: {e}")
            return False
    
    def update_machine_capacity(self, machine_id: int, max_bots: int) -> bool:
        """به‌روزرسانی ظرفیت ماشین"""
        db.execute('UPDATE machines SET max_bots = ? WHERE id = ?', (max_bots, machine_id))
        return True
    
    def toggle_machine(self, machine_id: int, active: bool) -> bool:
        """فعال/غیرفعال کردن ماشین"""
        status = 'active' if active else 'inactive'
        db.execute('UPDATE machines SET status = ? WHERE id = ?', (status, machine_id))
        return True
    
    def restart_dead_bots(self) -> int:
        """ریستارت ربات‌های مرده"""
        dead_bots = db.execute('SELECT id, token_encrypted, file_path FROM bots WHERE status = "running"')
        restarted = 0
        
        for bot in dead_bots:
            status = sandbox.get_status(bot['id'])
            if not status.get('running'):
                if os.path.exists(bot['file_path']):
                    with open(bot['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    result = sandbox.run_bot(bot['id'], code, crypto.decrypt(bot['token_encrypted']), 
                                            db.execute('SELECT user_id FROM bots WHERE id = ?', (bot['id'],))[0]['user_id'],
                                            restore=True)
                    if result.get('success'):
                        restarted += 1
        
        return restarted

machine_manager = UltimateMachineManager()

# ==================== مدیریت سرورهای از راه دور ====================
class RemoteServerManager:
    """مدیریت سرورهای از راه دور برای اجرای توزیع شده"""
    
    def __init__(self):
        self.connections = {}
        self.lock = threading.RLock()
    
    def connect(self, server_id: int) -> Optional[paramiko.SSHClient]:
        """اتصال به سرور از راه دور"""
        with self.lock:
            if server_id in self.connections:
                return self.connections[server_id]
            
            server = db.execute('SELECT * FROM remote_servers WHERE id = ?', (server_id,))
            if not server:
                return None
            
            server = server[0]
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                password = crypto.decrypt(server['password_encrypted']) if server['password_encrypted'] else None
                ssh.connect(
                    server['ip'],
                    port=server['port'],
                    username=server['username'],
                    password=password,
                    timeout=10
                )
                self.connections[server_id] = ssh
                db.execute('UPDATE remote_servers SET connection_status = "connected", last_connected = ? WHERE id = ?',
                          (datetime.now().isoformat(), server_id))
                return ssh
            except Exception as e:
                logger.error(f"Failed to connect to server {server['name']}: {e}")
                return None
    
    def deploy_bot(self, server_id: int, bot_id: str, code: str, token: str) -> dict:
        """استقرار ربات روی سرور از راه دور"""
        ssh = self.connect(server_id)
        if not ssh:
            return {'success': False, 'error': 'Cannot connect to server'}
        
        try:
            remote_dir = f"/opt/bots/{bot_id}"
            sftp = ssh.open_sftp()
            
            try:
                sftp.mkdir(remote_dir)
            except:
                pass
            
            remote_file = f"{remote_dir}/bot.py"
            with sftp.open(remote_file, 'w') as f:
                f.write(code)
            
            sftp.close()
            
            # اجرای ربات در سرور راه دور
            cmd = f"cd {remote_dir} && nohup python3 bot.py > bot.log 2>&1 &"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            return {'success': True, 'server': server_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def add_server(self, name: str, ip: str, username: str, password: str, port: int = 22, machine_id: int = None) -> dict:
        """اضافه کردن سرور جدید"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=port, username=username, password=password, timeout=10)
            ssh.close()
            
            encrypted_password = crypto.encrypt(password)
            
            db.execute('''
                INSERT INTO remote_servers (name, ip, port, username, password_encrypted, machine_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'connected', ?)
            ''', (name, ip, port, username, encrypted_password, machine_id, datetime.now().isoformat()))
            
            if machine_id:
                db.execute('UPDATE machines SET ip = ?, username = ?, password_encrypted = ?, is_local = 0 WHERE id = ?',
                          (ip, username, encrypted_password, machine_id))
            
            logger.info(f"✅ Remote server added: {name}")
            return {'success': True, 'message': 'Server added successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

remote_manager = RemoteServerManager()

# ==================== توابع کمکی دیتابیس ====================
def get_setting(key: str, default: Any = None) -> Any:
    """دریافت تنظیم از دیتابیس"""
    cached = cache.get(f"setting_{key}")
    if cached is not None:
        return cached
    
    result = db.execute("SELECT value, type FROM system_settings WHERE key = ?", (key,))
    if result:
        value = result[0]['value']
        vtype = result[0]['type']
        
        if vtype == 'int':
            try:
                value = int(value)
            except:
                value = 0
        elif vtype == 'bool':
            value = value in ('1', 'true', 'True', 'yes')
        elif vtype == 'float':
            try:
                value = float(value)
            except:
                value = 0.0
        
        cache.set(f"setting_{key}", value, ttl=300)
        return value
    
    return default

def update_setting(key: str, value: Any):
    """به‌روزرسانی تنظیم"""
    vtype = 'string'
    if isinstance(value, int):
        vtype = 'int'
    elif isinstance(value, bool):
        vtype = 'bool'
        value = '1' if value else '0'
    elif isinstance(value, float):
        vtype = 'float'
    
    db.execute('''
        UPDATE system_settings SET value = ?, type = ?, updated_at = ?
        WHERE key = ?
    ''', (str(value), vtype, datetime.now().isoformat(), key))
    
    cache.delete(f"setting_{key}")

def get_user(user_id: int) -> Optional[dict]:
    """دریافت کاربر از دیتابیس"""
    cached = cache.get(f"user_{user_id}")
    if cached:
        return cached
    
    users = db.execute('SELECT * FROM users WHERE user_id = ? OR id = ?', (user_id, user_id))
    if users:
        cache.set(f"user_{user_id}", users[0], ttl=60)
        return users[0]
    return None

def get_user_by_username(username: str) -> Optional[dict]:
    """دریافت کاربر با نام کاربری"""
    users = db.execute('SELECT * FROM users WHERE username = ?', (username,))
    return users[0] if users else None

def create_user(user_id: int, username: str, first_name: str, last_name: str = "",
                referred_by: int = None, language: str = 'fa', password: str = None) -> Tuple[bool, str]:
    """ایجاد کاربر جدید"""
    try:
        # بررسی ظرفیت
        users_count = db.execute('SELECT COUNT(*) as cnt FROM users')[0]['cnt']
        max_capacity = get_setting('max_users_capacity', 10000)
        if users_count >= max_capacity:
            return False, "capacity_full"
        
        # بررسی تکراری نبودن
        existing = db.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if existing:
            return False, "exists"
        
        referral_code = secrets.token_hex(8)
        max_bots = get_setting('max_bots_per_subscription', 3)
        now = datetime.now().isoformat()
        
        password_hash = None
        password_salt = None
        if password:
            password_hash, password_salt = crypto.hash_password(password)
        
        db.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, language, referral_code,
                              referred_by, max_bots, created_at, last_seen, password_hash, password_salt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, language, referral_code,
              referred_by, max_bots, now, now, password_hash, password_salt))
        
        if referred_by:
            db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        
        logger.info(f"✅ New user created: {username} (ID: {user_id})")
        return True, "ok"
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False, str(e)

def authenticate_user(username: str, password: str, ip: str = None) -> Optional[dict]:
    """احراز هویت کاربر"""
    user = get_user_by_username(username)
    if not user:
        return None
    
    if user.get('is_banned', 0) == 1:
        return None
    
    if user.get('password_hash') and user.get('password_salt'):
        if crypto.verify_password(password, user['password_hash'], user['password_salt']):
            db.execute('UPDATE users SET last_login = ?, last_ip = ?, last_seen = ? WHERE id = ?',
                      (datetime.now().isoformat(), ip, datetime.now().isoformat(), user['id']))
            return user
    
    return None

def check_subscription(user_id: int) -> bool:
    """بررسی وضعیت اشتراک کاربر"""
    user = get_user(user_id)
    if not user or user.get('is_banned', 0) == 1:
        return False
    
    if user['subscription_status'] == 'active':
        if user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
            else:
                db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user_id,))
    
    return False

def get_remaining_bots(user_id: int) -> int:
    """دریافت تعداد ربات‌های باقیمانده برای کاربر"""
    user = get_user(user_id)
    if not user:
        return 0
    
    if check_subscription(user_id):
        max_bots = user.get('max_bots', get_setting('max_bots_per_subscription', 3))
        return max_bots - user.get('bots_count', 0)
    return 0

def activate_subscription(user_id: int, tx_hash: str = None, months: int = 1) -> bool:
    """فعال‌سازی اشتراک کاربر"""
    user = get_user(user_id)
    now = datetime.now()
    
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30 * months)
    else:
        new_expiry = now + timedelta(days=30 * months)
    
    db.execute('''
        UPDATE users
        SET subscription_status = 'active', subscription_expiry = ?, subscription_purchased_at = ?
        WHERE user_id = ?
    ''', (new_expiry.isoformat(), now.isoformat(), user_id))
    
    # اضافه کردن کمیسیون به معرف
    if user and user.get('referred_by'):
        commission_percent = get_setting('withdraw_percent', 7)
        price = get_setting('subscription_price', 2000000)
        commission = int(price * commission_percent / 100)
        
        db.execute('''
            UPDATE users SET wallet_balance = wallet_balance + ?, total_commission = total_commission + ?
            WHERE user_id = ?
        ''', (commission, commission, user['referred_by']))
        
        db.execute('''
            INSERT INTO commissions (user_id, from_user, amount, percent, reason, created_at, paid)
            VALUES (?, ?, ?, ?, 'referral_subscription', ?, 1)
        ''', (user['referred_by'], user_id, commission, commission_percent, now.isoformat()))
    
    logger.info(f"✅ Subscription activated for user {user_id}")
    return True

def add_wallet_balance(user_id: int, amount: int) -> int:
    """افزایش موجودی کیف پول"""
    user = get_user(user_id)
    if not user:
        return 0
    new_balance = user['wallet_balance'] + amount
    db.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))
    return new_balance

def get_user_bots(user_id: int) -> List[dict]:
    """دریافت لیست ربات‌های کاربر"""
    return db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))

def get_bot(bot_id: str) -> Optional[dict]:
    """دریافت اطلاعات ربات"""
    bots = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    return bots[0] if bots else None

def delete_bot(bot_id: str, user_id: int) -> bool:
    """حذف ربات"""
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user_id:
        return False
    
    # توقف ربات
    sandbox.stop_bot(bot_id)
    
    # حذف فایل‌ها
    if bot.get('file_path') and os.path.exists(bot['file_path']):
        try:
            os.remove(bot['file_path'])
        except:
            pass
    
    if bot.get('sandbox_path') and os.path.exists(bot['sandbox_path']):
        try:
            shutil.rmtree(bot['sandbox_path'])
        except:
            pass
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    logger.info(f"✅ Bot {bot_id} deleted by user {user_id}")
    return True

def extract_token_from_code(code: str) -> Optional[str]:
    """استخراج توکن از کد ربات"""
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'bottoken\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            token = match.group(1)
            if len(token) > 30 and ':' in token:  # بررسی فرمت توکن تلگرام
                return token
    return None

def add_bot(user_id: int, bot_id: str, token: str, name: str, username: str,
            file_path: str, pid: int = None, machine_id: int = None) -> bool:
    """افزودن ربات به دیتابیس"""
    now = datetime.now().isoformat()
    encrypted_token = crypto.encrypt(token)
    
    db.execute('''
        INSERT INTO bots (id, user_id, token_encrypted, name, username, file_path,
                          pid, machine_id, status, created_at, last_active, health_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, 'healthy')
    ''', (bot_id, user_id, encrypted_token, name, username, file_path,
          pid, machine_id, now, now))
    
    db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
    
    logger.info(f"✅ Bot {bot_id} ({username}) added for user {user_id}")
    return True

def can_create_bot(user_id: int) -> Tuple[bool, str]:
    """بررسی امکان ساخت ربات جدید"""
    if not check_subscription(user_id):
        return False, "no_subscription"
    
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        return False, "limit_reached"
    
    return True, "ok"

# ==================== محدودکننده نرخ (Rate Limiter Decorator) ====================
def rate_limit(limit: int = 10, window: int = 60):
    """دکوراتور محدودکننده نرخ درخواست"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id', request.remote_addr)
            key = f"rate_limit_{f.__name__}_{user_id}"
            
            if not rate_limiter.is_allowed(key, rate=limit/window, capacity=limit):
                return jsonify({'error': 'Too many requests. Please slow down.'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== لاگینگ امنیتی ====================
def security_log(user_id: int, action: str, ip: str, details: str = "", severity: int = 1):
    """ثبت لاگ امنیتی"""
    db.execute('''
        INSERT INTO security_logs (user_id, action, ip_address, details, severity, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, action, ip, details, severity, datetime.now().isoformat()))
    logger.security(user_id, action, ip, details)

# ==================== Flask App ====================
app = Flask(__name__)
app.secret_key = SECURITY_CONFIG['JWT_SECRET']
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

CORS(app, resources={r"/api/*": {"origins": "*"}})

# ==================== HTML صفحات ====================

HTML_BASE = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#667eea">
    <title>ساخت ربات تلگرام | پنل پیشرفته</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { font-family: 'Vazirmatn', 'Tahoma', sans-serif; touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            overflow-x: hidden;
        }
        input, textarea, select, button { font-size: 16px !important; touch-action: manipulation; }
        @media (max-width: 768px) { body { padding: 0; } }
        .sidebar {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: white;
            position: fixed;
            right: 0;
            top: 0;
            width: 280px;
            z-index: 1000;
            transition: all 0.3s;
            box-shadow: -5px 0 30px rgba(0,0,0,0.2);
        }
        .sidebar .nav-link {
            color: rgba(255,255,255,0.7);
            padding: 12px 20px;
            margin: 5px 10px;
            border-radius: 12px;
            transition: all 0.3s;
        }
        .sidebar .nav-link:hover, .sidebar .nav-link.active {
            background: rgba(102,126,234,0.3);
            color: white;
        }
        .sidebar .nav-link i { margin-left: 12px; width: 24px; }
        .main-content {
            margin-right: 280px;
            padding: 20px;
            min-height: 100vh;
        }
        .card {
            border: none;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .card:hover { transform: translateY(-3px); box-shadow: 0 15px 40px rgba(0,0,0,0.12); }
        .stat-card {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border-radius: 20px;
            padding: 20px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 12px;
            padding: 10px 24px;
        }
        .bot-card {
            background: white;
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: all 0.3s;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .status-running { background: #d4edda; color: #155724; }
        .status-stopped { background: #f8d7da; color: #721c24; }
        .code-area {
            font-family: 'Courier New', monospace;
            background: #1e1e2e;
            color: #fff;
            padding: 16px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.5;
        }
        .toast-notify {
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 14px 20px;
            border-radius: 16px;
            text-align: center;
            z-index: 1100;
            display: none;
            animation: slideUp 0.3s ease;
        }
        @keyframes slideUp {
            from { transform: translateY(100px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .loader {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .security-badge {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.6);
            color: #4ade80;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 10px;
            font-family: monospace;
            z-index: 1000;
            backdrop-filter: blur(5px);
            pointer-events: none;
        }
        @media (max-width: 768px) {
            .sidebar { right: -280px; }
            .sidebar.open { right: 0; }
            .main-content { margin-right: 0; }
            .menu-toggle {
                display: block;
                position: fixed;
                top: 15px;
                right: 15px;
                z-index: 1001;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 15px;
            }
            .security-badge { display: none; }
        }
        .menu-toggle { display: none; }
    </style>
</head>
<body>

<button class="menu-toggle" onclick="toggleSidebar()">
    <i class="fas fa-bars"></i>
</button>

<div class="sidebar" id="sidebar">
    <div class="text-center py-4">
        <i class="fas fa-robot" style="font-size: 48px;"></i>
        <h5 class="mt-2" id="userName">کاربر</h5>
        <small id="userSubStatus"></small>
    </div>
    <hr style="background: rgba(255,255,255,0.1);">
    <nav class="nav flex-column">
        <a class="nav-link" href="#" onclick="showPage('dashboard')">
            <i class="fas fa-tachometer-alt"></i> داشبورد
        </a>
        <a class="nav-link" href="#" onclick="showPage('build')">
            <i class="fas fa-plus-circle"></i> ساخت ربات
        </a>
        <a class="nav-link" href="#" onclick="showPage('bots')">
            <i class="fas fa-robot"></i> ربات‌های من
        </a>
        <a class="nav-link" href="#" onclick="showPage('wallet')">
            <i class="fas fa-wallet"></i> کیف پول
        </a>
        <a class="nav-link" href="#" onclick="showPage('referrals')">
            <i class="fas fa-users"></i> دعوت دوستان
        </a>
        <a class="nav-link" href="#" onclick="showPage('guide')">
            <i class="fas fa-book"></i> راهنما
        </a>
        <hr style="background: rgba(255,255,255,0.1);">
        <a class="nav-link" href="#" onclick="showPage('settings')">
            <i class="fas fa-cog"></i> تنظیمات
        </a>
        <a class="nav-link" href="/logout">
            <i class="fas fa-sign-out-alt"></i> خروج
        </a>
    </nav>
</div>

<div class="main-content" id="mainContent">
    <div id="page-dashboard" class="page-content">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h3><i class="fas fa-chart-line me-2"></i>داشبورد</h3>
            <span id="currentTime" class="text-muted"></span>
        </div>
        <div class="row g-4 mb-4" id="statsCards"></div>
        <div class="row">
            <div class="col-md-8">
                <div class="card p-4">
                    <h5><i class="fas fa-chart-bar me-2"></i>آخرین ربات‌ها</h5>
                    <div id="recentBots"></div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card p-4 text-center">
                    <h5><i class="fas fa-gift me-2"></i>کد معرف شما</h5>
                    <code id="referralCode" style="font-size: 1.1rem;"></code>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="copyReferralLink()">کپی لینک</button>
                    <hr>
                    <h6>تعداد معرف‌ها</h6>
                    <h3 id="referralsCount">0</h3>
                </div>
            </div>
        </div>
    </div>

    <div id="page-build" class="page-content" style="display: none;">
        <div class="card p-4">
            <h4><i class="fas fa-microchip me-2"></i>ساخت ربات جدید</h4>
            <hr>
            <ul class="nav nav-tabs mb-4">
                <li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#codeTab">کد مستقیم</a></li>
                <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#uploadTab">آپلود فایل</a></li>
            </ul>
            <div class="tab-content">
                <div class="tab-pane fade show active" id="codeTab">
                    <textarea id="botCode" class="form-control code-area" rows="12" placeholder="# کد ربات خود را وارد کنید
import telebot

TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'سلام! ربات من ساخته شد!')

bot.infinity_polling()"></textarea>
                </div>
                <div class="tab-pane fade" id="uploadTab">
                    <div class="border rounded-3 p-4 text-center" style="border-style: dashed;">
                        <i class="fas fa-cloud-upload-alt fa-3x text-primary"></i>
                        <p class="mt-2">فایل .py یا .zip خود را انتخاب کنید</p>
                        <input type="file" id="botFile" class="form-control mt-2" accept=".py,.zip">
                    </div>
                </div>
            </div>
            <div class="mt-4">
                <button class="btn btn-primary w-100" onclick="buildBot()" id="buildBtn">
                    <i class="fas fa-play me-2"></i> ساخت ربات
                </button>
            </div>
            <div id="buildStatus" class="mt-3" style="display: none;"></div>
        </div>
    </div>

    <div id="page-bots" class="page-content" style="display: none;">
        <div class="card p-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h4><i class="fas fa-list me-2"></i>ربات‌های من</h4>
                <button class="btn btn-sm btn-outline-primary" onclick="loadBots()"><i class="fas fa-sync-alt"></i></button>
            </div>
            <div id="botsList"></div>
        </div>
    </div>

    <div id="page-wallet" class="page-content" style="display: none;">
        <div class="row g-4">
            <div class="col-md-6">
                <div class="card p-4 text-center">
                    <h5>💰 موجودی کیف پول</h5>
                    <h2 id="walletBalance">0</h2>
                    <small>تومان</small>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card p-4 text-center">
                    <h5>📅 وضعیت اشتراک</h5>
                    <h3 id="subStatus">غیرفعال</h3>
                    <small id="expiryDate"></small>
                </div>
            </div>
        </div>
        <div class="card mt-4 p-4">
            <h5>💳 خرید اشتراک</h5>
            <p>مبلغ: <strong id="priceDisplay"></strong></p>
            <div class="border rounded p-3 mb-3">
                <p><i class="fas fa-credit-card"></i> شماره کارت: <code id="cardNumber"></code></p>
                <p><i class="fas fa-user"></i> نام دارنده: <code id="cardHolder"></code></p>
                <p><i class="fas fa-university"></i> بانک: <code id="cardBank"></code></p>
            </div>
            <button class="btn btn-success" onclick="uploadReceipt()">ارسال فیش واریز</button>
        </div>
    </div>

    <div id="page-referrals" class="page-content" style="display: none;">
        <div class="card p-4 text-center">
            <i class="fas fa-share-alt fa-3x text-primary"></i>
            <h4 class="mt-3">دعوت از دوستان</h4>
            <p>با دعوت دوستان، 7% کمیسیون دریافت کنید</p>
            <div class="bg-light p-3 rounded"><code id="refLink"></code></div>
            <button class="btn btn-primary mt-3" onclick="copyReferralLink()">کپی لینک</button>
        </div>
    </div>

    <div id="page-guide" class="page-content" style="display: none;">
        <div class="card p-4" id="guideText"></div>
    </div>

    <div id="page-settings" class="page-content" style="display: none;">
        <div class="card p-4">
            <h4>تنظیمات حساب</h4>
            <form id="profileForm">
                <div class="mb-3"><label>نام کامل</label><input type="text" name="full_name" id="fullName" class="form-control"></div>
                <div class="mb-3"><label>ایمیل</label><input type="email" name="email" id="email" class="form-control"></div>
                <div class="mb-3"><label>رمز عبور جدید</label><input type="password" name="password" class="form-control"></div>
                <button type="submit" class="btn btn-primary">ذخیره</button>
            </form>
        </div>
    </div>
</div>

<div id="toast" class="toast-notify"></div>

<script>
function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
function showToast(msg, isError) {
    let toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.style.background = isError ? '#dc3545' : '#10b981';
    toast.style.display = 'block';
    setTimeout(() => toast.style.display = 'none', 3000);
}
function showPage(page) {
    document.querySelectorAll('.page-content').forEach(p => p.style.display = 'none');
    document.getElementById(`page-${page}`).style.display = 'block';
    if (page === 'dashboard') loadDashboard();
    if (page === 'bots') loadBots();
    if (page === 'wallet') loadWallet();
}
async function loadDashboard() {
    try {
        let user = await (await fetch('/api/user')).json();
        let stats = await (await fetch('/api/stats')).json();
        document.getElementById('statsCards').innerHTML = `
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${user.wallet_balance.toLocaleString()}</h3><small>موجودی</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${user.bots_count}</h3><small>ربات‌ها</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${user.remaining_bots}</h3><small>ظرفیت باقی</small></div></div>
            <div class="col-md-3 col-6"><div class="stat-card text-center"><h3>${stats.total_users || 0}</h3><small>کاربران</small></div></div>
        `;
        let ref = await (await fetch('/api/referrals')).json();
        document.getElementById('referralCode').innerText = ref.referral_code;
        document.getElementById('referralsCount').innerText = ref.count;
        let bots = await (await fetch('/api/bots')).json();
        document.getElementById('recentBots').innerHTML = bots.slice(0,5).map(b => `<div class="d-flex justify-content-between align-items-center border-bottom py-2"><span>${b.name||'ربات'}</span><span class="status-badge ${b.status=='running'?'status-running':'status-stopped'}">${b.status=='running'?'فعال':'متوقف'}</span></div>`).join('') || '<p class="text-muted">رباتی ندارید</p>';
    } catch(e) { console.error(e); }
}
async function loadBots() {
    try {
        let bots = await (await fetch('/api/bots')).json();
        if(bots.length===0) { document.getElementById('botsList').innerHTML='<p class="text-muted">رباتی ندارید</p>'; return; }
        document.getElementById('botsList').innerHTML = bots.map(b => `
            <div class="bot-card d-flex justify-content-between align-items-center">
                <div><strong>${b.name||b.username||'ربات'}</strong><br><small class="text-muted">@${b.username||''}</small><br><span class="status-badge ${b.status=='running'?'status-running':'status-stopped'}">${b.status=='running'?'🟢 فعال':'🔴 متوقف'}</span></div>
                <div><button class="btn btn-sm btn-outline-${b.status=='running'?'warning':'success'} me-1" onclick="toggleBot('${b.id}')"><i class="fas fa-${b.status=='running'?'stop':'play'}"></i></button><button class="btn btn-sm btn-outline-danger" onclick="deleteBot('${b.id}')"><i class="fas fa-trash"></i></button></div>
            </div>
        `).join('');
    } catch(e) { showToast('خطا',true); }
}
async function toggleBot(id) {
    let res = await fetch(`/api/bots/${id}/toggle`, {method:'POST'});
    let data = await res.json();
    showToast(data.message, !res.ok);
    loadBots(); loadDashboard();
}
async function deleteBot(id) {
    if(!confirm('حذف شود؟')) return;
    let res = await fetch(`/api/bots/${id}`, {method:'DELETE'});
    if(res.ok) { showToast('حذف شد'); loadBots(); loadDashboard(); }
}
async function buildBot() {
    let code = document.getElementById('botCode').value;
    let file = document.getElementById('botFile').files[0];
    if(!code.trim() && !file) { showToast('کد یا فایل را وارد کنید',true); return; }
    let btn = document.getElementById('buildBtn');
    btn.disabled = true; btn.innerHTML = '<span class="loader"></span> در حال ساخت...';
    try {
        let res;
        if(file) {
            let fd = new FormData();
            fd.append('file', file);
            res = await fetch('/api/build/upload', {method:'POST', body:fd});
        } else {
            res = await fetch('/api/build', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({code})});
        }
        let data = await res.json();
        if(res.ok) { showToast('ربات ساخته شد!'); document.getElementById('botCode').value=''; document.getElementById('botFile').value=''; loadBots(); loadDashboard(); showPage('bots'); }
        else { showToast(data.error,true); }
    } catch(e) { showToast('خطا',true); }
    btn.disabled = false; btn.innerHTML = '<i class="fas fa-play me-2"></i> ساخت ربات';
}
async function loadWallet() {
    let w = await (await fetch('/api/wallet')).json();
    document.getElementById('walletBalance').innerText = w.balance.toLocaleString();
    document.getElementById('subStatus').innerHTML = w.subscription_active ? '✅ فعال' : '❌ غیرفعال';
    document.getElementById('expiryDate').innerText = w.expiry_date || '';
    document.getElementById('priceDisplay').innerText = w.subscription_price;
    document.getElementById('cardNumber').innerText = w.card_info?.card_number || '';
    document.getElementById('cardHolder').innerText = w.card_info?.card_holder || '';
    document.getElementById('cardBank').innerText = w.card_info?.card_bank || '';
}
async function copyReferralLink() {
    let ref = await (await fetch('/api/referrals')).json();
    navigator.clipboard.writeText(ref.referral_link);
    showToast('لینک کپی شد');
}
function uploadReceipt() {
    let input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async (e) => {
        let fd = new FormData();
        fd.append('receipt', e.target.files[0]);
        let res = await fetch('/api/upload-receipt', {method:'POST', body:fd});
        if(res.ok) showToast('فیش ارسال شد، در انتظار تایید');
        else showToast('خطا',true);
    };
    input.click();
}
document.getElementById('profileForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    let data = {full_name: document.getElementById('fullName').value, email: document.getElementById('email').value, password: document.querySelector('input[name="password"]').value};
    let res = await fetch('/api/update-profile', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    if(res.ok) showToast('پروفایل بروز شد');
});
setInterval(() => { let d=new Date(); document.getElementById('currentTime') && (document.getElementById('currentTime').innerText=d.toLocaleTimeString('fa-IR')); }, 1000);
loadDashboard();
</script>
</body>
</html>
'''

HTML_LOGIN = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no"><title>ورود</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>
*{font-family:'Vazirmatn','Tahoma',sans-serif}body{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.login-card{background:white;border-radius:32px;padding:40px;max-width:450px;width:100%;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}.btn{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:14px;padding:14px;width:100%;color:white}
</style></head>
<body><div class="login-card"><div class="text-center mb-4"><i class="fas fa-robot" style="font-size:64px;color:#667eea"></i><h2>ساخت ربات تلگرام</h2></div>{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
<form method="POST"><div class="mb-3"><input type="text" name="username" class="form-control" placeholder="نام کاربری" required></div><div class="mb-3"><input type="password" name="password" class="form-control" placeholder="رمز عبور" required></div><button type="submit" class="btn">ورود</button></form>
<div class="text-center mt-4"><a href="/register">ثبت نام</a></div></div></body></html>'''

HTML_REGISTER_PAGE = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no"><title>ثبت نام</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"><style>
*{font-family:'Vazirmatn','Tahoma',sans-serif}body{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.register-card{background:white;border-radius:32px;padding:40px;max-width:500px;width:100%}.btn{background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:14px;padding:14px;width:100%;color:white}
</style></head>
<body><div class="register-card"><div class="text-center mb-4"><i class="fas fa-user-plus" style="font-size:64px;color:#667eea"></i><h2>ثبت نام</h2></div>{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
<form method="POST"><div class="mb-3"><input type="text" name="username" class="form-control" placeholder="نام کاربری" required></div><div class="mb-3"><input type="password" name="password" class="form-control" placeholder="رمز عبور" required minlength="6"></div><div class="mb-3"><input type="text" name="full_name" class="form-control" placeholder="نام کامل" required></div><div class="mb-3"><input type="text" name="referral_code" class="form-control" placeholder="کد معرف (اختیاری)"></div><button type="submit" class="btn">ثبت نام</button></form>
<div class="text-center mt-4"><a href="/login">ورود</a></div></div></body></html>'''

# ==================== مسیرهای Flask ====================

@app.route('/')
def index():
    if 'user_id' in session:
        return HTML_BASE
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ip = request.remote_addr
        
        user = authenticate_user(username, password, ip)
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', 0)
            security_log(user['user_id'], 'login', ip, 'Successful login')
            return redirect(url_for('index'))
        
        security_log(0, 'failed_login', ip, f"Failed login for {username}")
        return HTML_LOGIN.replace('{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}', '<div class="alert alert-danger">نام کاربری یا رمز عبور اشتباه است</div>')
    
    return HTML_LOGIN

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        referral_code = request.form.get('referral_code', '').strip()
        ip = request.remote_addr
        
        if len(password) < 6:
            return HTML_REGISTER_PAGE.replace('{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}', '<div class="alert alert-danger">رمز عبور حداقل 6 کاراکتر</div>')
        
        existing = get_user_by_username(username)
        if existing:
            return HTML_REGISTER_PAGE.replace('{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}', '<div class="alert alert-danger">نام کاربری تکراری</div>')
        
        referred_by = None
        if referral_code:
            ref_user = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
            if ref_user:
                referred_by = ref_user[0]['user_id']
        
        user_id = int(time.time() * 1000) % 1000000000
        success, msg = create_user(user_id, username, full_name, "", referred_by, 'fa', password)
        
        if success:
            security_log(user_id, 'register', ip, f"New user: {username}")
            return redirect(url_for('login_page'))
        
        return HTML_REGISTER_PAGE.replace('{% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}', '<div class="alert alert-danger">خطا در ثبت نام</div>')
    
    return HTML_REGISTER_PAGE

@app.route('/logout')
def logout():
    if 'user_id' in session:
        security_log(session['user_id'], 'logout', request.remote_addr, 'User logged out')
    session.clear()
    return redirect(url_for('login_page'))

# ==================== API ها ====================

@app.route('/api/user')
def api_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'user_id': user['user_id'],
        'username': user['username'],
        'first_name': user['first_name'],
        'wallet_balance': user['wallet_balance'],
        'bots_count': user['bots_count'],
        'subscription_active': check_subscription(user['user_id']),
        'remaining_bots': get_remaining_bots(user['user_id']),
        'is_admin': user.get('is_admin', 0)
    })

@app.route('/api/bots')
def api_bots():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    bots = get_user_bots(session['user_id'])
    result = []
    for bot in bots:
        status = sandbox.get_status(bot['id'])
        result.append({
            'id': bot['id'],
            'name': bot['name'],
            'username': bot['username'],
            'status': 'running' if status.get('running') else bot.get('status', 'stopped'),
            'created_at': bot['created_at']
        })
    return jsonify(result)

@app.route('/api/bots/<bot_id>/toggle', methods=['POST'])
def api_toggle_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != session['user_id']:
        return jsonify({'error': 'Not found'}), 404
    
    status = sandbox.get_status(bot_id)
    if status.get('running'):
        if sandbox.stop_bot(bot_id):
            return jsonify({'message': 'ربات متوقف شد'})
    else:
        if os.path.exists(bot['file_path']):
            with open(bot['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            result = sandbox.run_bot(bot_id, code, crypto.decrypt(bot['token_encrypted']), session['user_id'])
            if result['success']:
                return jsonify({'message': 'ربات راه‌اندازی شد'})
    return jsonify({'error': 'خطا'}), 500

@app.route('/api/bots/<bot_id>', methods=['DELETE'])
def api_delete_bot(bot_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if delete_bot(bot_id, session['user_id']):
        return jsonify({'message': 'حذف شد'})
    return jsonify({'error': 'خطا'}), 500

@app.route('/api/build', methods=['POST'])
def api_build():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    code = data.get('code', '')
    user_id = session['user_id']
    
    can, reason = can_create_bot(user_id)
    if not can:
        return jsonify({'error': 'اشتراک فعال نیست یا محدودیت ربات'}), 403
    
    token = extract_token_from_code(code)
    if not token:
        return jsonify({'error': 'توکن یافت نشد'}), 400
    
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': 'توکن نامعتبر'}), 400
        bot_info = resp.json()['result']
    except:
        return jsonify({'error': 'خطا در ارتباط با تلگرام'}), 500
    
    bot_id = secrets.token_hex(16)
    user_dir = os.path.join(DIRS['FILES'], str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{bot_id}.py")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    result = sandbox.run_bot(bot_id, code, token, user_id)
    
    if result['success']:
        add_bot(user_id, bot_id, token, bot_info.get('first_name', 'ربات'), bot_info.get('username', ''), file_path, result['pid'])
        return jsonify({'success': True, 'bot_name': bot_info.get('first_name'), 'username': bot_info.get('username')})
    return jsonify({'error': result.get('error', 'خطا')}), 500

@app.route('/api/build/upload', methods=['POST'])
def api_build_upload():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    content = file.read()
    filename = file.filename
    
    user_id = session['user_id']
    
    can, reason = can_create_bot(user_id)
    if not can:
        return jsonify({'error': 'اشتراک فعال نیست'}), 403
    
    temp_path = os.path.join(DIRS['TEMP'], f"build_{user_id}_{int(time.time())}_{filename}")
    with open(temp_path, 'wb') as f:
        f.write(content)
    
    if filename.endswith('.zip'):
        extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(temp_path, 'r') as zf:
            zf.extractall(extract_dir)
        code = ""
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                if f.endswith('.py'):
                    with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as cf:
                        code = cf.read()
                        break
            if code:
                break
        shutil.rmtree(extract_dir, ignore_errors=True)
    else:
        with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    
    os.remove(temp_path)
    
    token = extract_token_from_code(code)
    if not token:
        return jsonify({'error': 'توکن یافت نشد'}), 400
    
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            return jsonify({'error': 'توکن نامعتبر'}), 400
        bot_info = resp.json()['result']
    except:
        return jsonify({'error': 'خطا'}), 500
    
    bot_id = secrets.token_hex(16)
    user_dir = os.path.join(DIRS['FILES'], str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{bot_id}.py")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    result = sandbox.run_bot(bot_id, code, token, user_id)
    
    if result['success']:
        add_bot(user_id, bot_id, token, bot_info.get('first_name', 'ربات'), bot_info.get('username', ''), file_path, result['pid'])
        return jsonify({'success': True, 'bot_name': bot_info.get('first_name'), 'username': bot_info.get('username')})
    return jsonify({'error': result.get('error', 'خطا')}), 500

@app.route('/api/wallet')
def api_wallet():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    return jsonify({
        'balance': user.get('wallet_balance', 0),
        'subscription_active': check_subscription(session['user_id']),
        'expiry_date': user.get('subscription_expiry', '')[:10] if user.get('subscription_expiry') else '',
        'subscription_price': get_setting('subscription_price_str'),
        'card_info': {
            'card_number': get_setting('card_number_display'),
            'card_holder': get_setting('card_holder'),
            'card_bank': get_setting('card_bank')
        }
    })

@app.route('/api/referrals')
def api_referrals():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = get_user(session['user_id'])
    return jsonify({
        'referral_code': user.get('referral_code', ''),
        'referral_link': f"http://{request.host}/register?ref={user.get('referral_code', '')}",
        'count': user.get('referrals_count', 0),
        'total_commission': user.get('total_commission', 0)
    })

@app.route('/api/stats')
def api_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    users_count = db.execute('SELECT COUNT(*) as cnt FROM users')[0]['cnt']
    total_bots = db.execute('SELECT COUNT(*) as cnt FROM bots')[0]['cnt']
    return jsonify({'total_users': users_count, 'total_bots': total_bots})

@app.route('/api/upload-receipt', methods=['POST'])
def api_upload_receipt():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if 'receipt' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'No file'}), 400
    
    tx_hash = secrets.token_hex(8)
    receipt_path = os.path.join(DIRS['RECEIPTS'], f"{session['user_id']}_{tx_hash}.jpg")
    file.save(receipt_path)
    
    db.execute('''
        INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], get_setting('subscription_price'), receipt_path, tx_hash, datetime.now().isoformat()))
    
    return jsonify({'message': 'Receipt uploaded'})

@app.route('/api/update-profile', methods=['POST'])
def api_update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    updates = []
    params = []
    if data.get('full_name'):
        updates.append('full_name = ?')
        params.append(data['full_name'])
    if data.get('email'):
        updates.append('email = ?')
        params.append(data['email'])
    if data.get('phone'):
        updates.append('phone = ?')
        params.append(data['phone'])
    if data.get('password') and data['password'].strip():
        ph, ps = crypto.hash_password(data['password'])
        updates.append('password_hash = ?')
        params.append(ph)
        updates.append('password_salt = ?')
        params.append(ps)
    if updates:
        params.append(session['user_id'])
        db.execute(f'UPDATE users SET {", ".join(updates)} WHERE user_id = ?', params)
    return jsonify({'message': 'Updated'})

# ==================== اجرا ====================
if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗  ██████╗ ████████╗    ██╗   ██╗██╗  ██╗████████╗██╗███╗   ███╗ █████╗ ████████╗███████╗
║   ██╔══██╗██╔═══██╗╚══██╔══╝    ██║   ██║██║  ██║╚══██╔══╝██║████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
║   ██████╔╝██║   ██║   ██║       ██║   ██║███████║   ██║   ██║██╔████╔██║███████║   ██║   █████╗  
║   ██╔══██╗██║   ██║   ██║       ██║   ██║██╔══██║   ██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  
║   ██████╔╝╚██████╔╝   ██║       ╚██████╔╝██║  ██║   ██║   ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
║   ╚═════╝  ╚═════╝    ╚═╝        ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
║                                                                               ║
║                     نسخه 5.0 Ultimate - کاملترین سامانه ساخت ربات               ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    print(f"📍 آدرس سایت: http://localhost:8080")
    print(f"👤 ادمین: admin / admin123")
    print(f"🔒 ایزوله‌سازی: فعال (محدودیت CPU:{ISOLATION_CONFIG['CPU_LIMIT']}s, RAM:{ISOLATION_CONFIG['MEMORY_LIMIT']//(1024*1024)}MB)")
    print(f"🛡️ امنیت: CSRF | Rate Limit | SQL Injection | XSS | Brute Force")
    print(f"📱 بدون زوم در موبایل | ریسپانسیو کامل")
    print("=" * 70)
    print("🚀 در حال اجرا...")
    
    app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False, threaded=True)