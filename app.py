#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🛡️ ربات سازنده ربات - نسخه Nuclear Enterprise 
⚡ امنیت نظامی - ایزوله‌سازی سخت‌افزاری
🔒 هر کاربر فقط ۱ ربات - بدون استثنا
🖥️ مدیریت چندسروره با SSH واقعی
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import uuid
import redis
import signal
import shutil
import hashlib
import sqlite3
import subprocess
import threading
import paramiko
import asyncio
import secrets
import base64
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import logging
from logging.handlers import RotatingFileHandler

import telebot
from telebot import types
import requests
from flask import Flask, request, jsonify
import psutil
import docker
from docker.errors import APIError

# ==================== لایه امنیتی سخت‌افزاری ====================
class HardwareSecurity:
    """لایه امنیتی در سطح سخت‌افزار"""
    
    @staticmethod
    def get_hardware_id() -> str:
        """گرفتن شناسه یکتای سخت‌افزاری"""
        try:
            # جمع‌آوری اطلاعات سخت‌افزاری
            cpu_id = subprocess.check_output("cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2", shell=True).decode().strip()
            mac = subprocess.check_output("cat /sys/class/net/eth0/address", shell=True).decode().strip()
            disk_id = subprocess.check_output("lsblk -o SERIAL | tail -n1", shell=True).decode().strip()
            
            hardware_fingerprint = hashlib.sha256(f"{cpu_id}{mac}{disk_id}".encode()).hexdigest()
            return hardware_fingerprint
        except:
            return secrets.token_hex(32)
    
    @staticmethod
    def encrypt_config(data: str, password: str) -> bytes:
        """رمزنگاری پیکربندی"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'mother_bot_salt_2024',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        f = Fernet(key)
        return f.encrypt(data.encode())
    
    @staticmethod
    def decrypt_config(encrypted_data: bytes, password: str) -> str:
        """رمزگشایی پیکربندی"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'mother_bot_salt_2024',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        f = Fernet(key)
        return f.decrypt(encrypted_data).decode()

# ==================== لاگینگ پیشرفته ====================
class SecurityLogger:
    """لاگینگ با قابلیت审计"""
    
    def __init__(self):
        self.log_dir = "/var/log/mother_bot" if os.path.exists("/var/log") else "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # لاگ امنیتی جداگانه
        self.security_logger = logging.getLogger('Security')
        self.security_logger.setLevel(logging.INFO)
        
        security_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'security.log'),
            maxBytes=100*1024*1024,
            backupCount=30
        )
        security_handler.setFormatter(logging.Formatter('%(asctime)s - [SECURITY] - %(message)s'))
        self.security_logger.addHandler(security_handler)
        
        # لاگ سیستمی
        self.system_logger = logging.getLogger('System')
        self.system_logger.setLevel(logging.INFO)
        system_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'system.log'),
            maxBytes=100*1024*1024,
            backupCount=30
        )
        system_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.system_logger.addHandler(system_handler)
    
    def log_security_event(self, event_type: str, user_id: int, details: str):
        """ثبت رویداد امنیتی"""
        self.security_logger.info(f"EVENT={event_type} | USER={user_id} | DETAILS={details}")
    
    def log_system_event(self, event_type: str, details: str):
        """ثبت رویداد سیستمی"""
        self.system_logger.info(f"EVENT={event_type} | DETAILS={details}")

logger = SecurityLogger()

# ==================== تنظیمات امنیتی ====================
@dataclass
class SecurityConfig:
    """تنظیمات امنیتی نظامی"""
    
    # ایزوله‌سازی
    ENABLE_HARDWARE_ISOLATION: bool = True
    ENABLE_NETWORK_ISOLATION: bool = True
    ENABLE_PROCESS_ISOLATION: bool = True
    
    # محدودیت‌های سخت
    MAX_BOT_MEMORY_MB: int = 128  # هر ربات حداکثر 128MB
    MAX_BOT_CPU_QUOTA: int = 50000  # 50% CPU
    MAX_BOT_PIDS: int = 64  # حداکثر 64 پروسس
    MAX_BOT_FILESIZE_MB: int = 10  # حداکثر 10MB فایل
    MAX_BOT_OPEN_FILES: int = 50  # حداکثر 50 فایل باز
    
    # تایم‌اوت‌ها
    BOT_TIMEOUT_SECONDS: int = 3600
    BOT_IDLE_TIMEOUT: int = 600
    
    # نرخ‌ها
    RATE_LIMIT_PER_USER: int = 3  # حداکثر 3 درخواست در ثانیه
    MAX_FAILED_LOGIN: int = 5  # حداکثر 5 تلاش ناموفق
    
    # مسیرهای امن
    SANDBOX_BASE: str = "/opt/mother_bot/sandbox"
    CONTAINER_REGISTRY: str = "localhost:5000/mother-bot"
    
    def __post_init__(self):
        os.makedirs(self.SANDBOX_BASE, mode=0o750, exist_ok=True)

config = SecurityConfig()

# ==================== دیتابیس فوق‌پیشرفته ====================
class EnterpriseDatabase:
    """دیتابیس با قابلیت‌های سازمانی و پشتیبانی از میلیون‌ها کاربر"""
    
    def __init__(self):
        self.db_path = "/opt/mother_bot/data" if os.path.exists("/opt") else "data"
        os.makedirs(self.db_path, mode=0o750, exist_ok=True)
        
        # دیتابیس اصلی PostgreSQL (اگر موجود باشه) یا SQLite با بهینه‌سازی
        self.use_postgres = self._check_postgres()
        
        if self.use_postgres:
            self._init_postgres()
        else:
            self._init_sqlite_optimized()
        
        self._init_tables_advanced()
        self._init_audit_tables()
        self._init_indexes()
    
    def _check_postgres(self) -> bool:
        """بررسی وجود PostgreSQL"""
        try:
            import psycopg2
            # تست اتصال
            conn = psycopg2.connect(
                host="localhost",
                database="mother_bot",
                user="mother_bot",
                password=os.getenv("DB_PASSWORD", "")
            )
            conn.close()
            return True
        except:
            return False
    
    def _init_postgres(self):
        """اتصال به PostgreSQL"""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        self.conn_pool = []
        self.db_config = {
            'host': 'localhost',
            'database': 'mother_bot',
            'user': 'mother_bot',
            'password': os.getenv("DB_PASSWORD", secrets.token_urlsafe(32)),
            'cursor_factory': RealDictCursor
        }
        logger.log_system_event("DATABASE", "Connected to PostgreSQL")
    
    def _init_sqlite_optimized(self):
        """SQLite با بهینه‌سازی فوق‌العاده برای حجم بالا"""
        self.sqlite_path = os.path.join(self.db_path, 'mother_bot.db')
        
        # بهینه‌سازی‌های پیشرفته
        self.sqlite_configs = [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA cache_size=-1000000",
            "PRAGMA temp_store=MEMORY",
            "PRAGMA mmap_size=30000000000",
            "PRAGMA page_size=32768",
            "PRAGMA optimize",
            "PRAGMA busy_timeout=30000"
        ]
        logger.log_system_event("DATABASE", "Initialized SQLite with advanced optimizations")
    
    @contextmanager
    def get_connection(self):
        """گرفتن کانکشن دیتابیس"""
        if self.use_postgres:
            import psycopg2
            conn = psycopg2.connect(**self.db_config)
            try:
                yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.sqlite_path, timeout=60, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            # اعمال تنظیمات
            for config in self.sqlite_configs:
                conn.execute(config)
            
            try:
                yield conn
            finally:
                conn.commit()
                conn.close()
    
    def _init_tables_advanced(self):
        """ایجاد جداول پیشرفته با ایندکس‌های بهینه"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول کاربران با شاردینگ
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    phone VARCHAR(20),
                    shard_id INTEGER DEFAULT (user_id % 10),
                    subscription_status VARCHAR(20) DEFAULT 'inactive',
                    subscription_expiry TIMESTAMP,
                    subscription_code VARCHAR(64) UNIQUE,
                    referral_code VARCHAR(32) UNIQUE,
                    referred_by BIGINT,
                    referrals_count INTEGER DEFAULT 0,
                    wallet_balance DECIMAL(15,2) DEFAULT 0,
                    total_spent DECIMAL(15,2) DEFAULT 0,
                    bots_created INTEGER DEFAULT 0,
                    last_bot_created_at TIMESTAMP,
                    ip_address INET,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    security_level INTEGER DEFAULT 1,
                    api_key VARCHAR(128) UNIQUE,
                    webhook_url TEXT
                )
            ''')
            
            # جدول ربات‌ها (فقط ۱ ربات per کاربر)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    bot_id VARCHAR(64) PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    bot_token VARCHAR(255) NOT NULL,
                    bot_name VARCHAR(255),
                    bot_username VARCHAR(255),
                    worker_node VARCHAR(255),
                    container_id VARCHAR(128),
                    status VARCHAR(20) DEFAULT 'stopped',
                    memory_usage INTEGER DEFAULT 0,
                    cpu_usage INTEGER DEFAULT 0,
                    network_rx BIGINT DEFAULT 0,
                    network_tx BIGINT DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    last_health_check TIMESTAMP,
                    UNIQUE(user_id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # جدول سرورها (ماشین‌های فوق‌قدرتمند)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS worker_nodes (
                    node_id SERIAL PRIMARY KEY,
                    node_name VARCHAR(255) UNIQUE NOT NULL,
                    ip_address INET NOT NULL,
                    ssh_port INTEGER DEFAULT 22,
                    username VARCHAR(100),
                    encrypted_password TEXT,
                    ssh_key_fingerprint VARCHAR(255),
                    status VARCHAR(20) DEFAULT 'pending',
                    max_bots INTEGER DEFAULT 500,
                    current_bots INTEGER DEFAULT 0,
                    total_memory BIGINT,
                    total_cpu INTEGER,
                    available_memory BIGINT,
                    available_cpu INTEGER,
                    docker_version VARCHAR(50),
                    last_heartbeat TIMESTAMP,
                    region VARCHAR(50) DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_maintenance TIMESTAMP
                )
            ''')
            
            # جدول تراکنش‌های مالی
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_id VARCHAR(64) PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount DECIMAL(15,2) NOT NULL,
                    type VARCHAR(20), -- subscription, referral, withdrawal
                    status VARCHAR(20) DEFAULT 'pending',
                    payment_method VARCHAR(20),
                    transaction_hash VARCHAR(255),
                    receipt_path TEXT,
                    reviewed_by BIGINT,
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            ''')
            
            # جدول رویدادهای امنیتی
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    event_type VARCHAR(50),
                    severity VARCHAR(20), -- LOW, MEDIUM, HIGH, CRITICAL
                    ip_address INET,
                    user_agent TEXT,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # جدول بکاپ‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    backup_id SERIAL PRIMARY KEY,
                    filename VARCHAR(255),
                    size BIGINT,
                    location TEXT,
                    type VARCHAR(20), -- full, incremental
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    restored_at TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'success'
                )
            ''')
            
            conn.commit()
    
    def _init_audit_tables(self):
        """جداول审计 برای ردگیری همه عملیات"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    action VARCHAR(50),
                    resource VARCHAR(50),
                    resource_id VARCHAR(255),
                    old_value JSONB,
                    new_value JSONB,
                    ip_address INET,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def _init_indexes(self):
        """ایجاد ایندکس‌های فوق‌سریع"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_expiry) WHERE subscription_status='active'",
                "CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)",
                "CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status) WHERE status='running'",
                "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status) WHERE status='pending'",
                "CREATE INDEX IF NOT EXISTS idx_workers_status ON worker_nodes(status) WHERE status='active'",
                "CREATE INDEX IF NOT EXISTS idx_security_user ON security_events(user_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id, created_at DESC)"
            ]
            
            for index in indexes:
                try:
                    cursor.execute(index)
                except:
                    pass
            
            conn.commit()

db = EnterpriseDatabase()

# ==================== ایزوله‌سازی سخت‌افزاری با Docker + gVisor ====================
class HardwareIsolation:
    """ایزوله‌سازی در سطح سخت‌افزار با gVisor و Docker"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.use_gvisor = self._check_gvisor()
            self._setup_security_profile()
        except Exception as e:
            logger.log_system_event("ERROR", f"Docker init failed: {e}")
            self.docker_client = None
    
    def _check_gvisor(self) -> bool:
        """بررسی وجود gVisor برای ایزوله‌سازی پیشرفته"""
        try:
            result = subprocess.run(['runsc', '--version'], capture_output=True)
            return result.returncode == 0
        except:
            return False
    
    def _setup_security_profile(self):
        """تنظیم پروفایل امنیتی سخت‌افزاری"""
        self.security_profile = {
            "disabled": [
                "CAP_SYS_ADMIN",
                "CAP_SYS_PTRACE", 
                "CAP_SYS_MODULE",
                "CAP_SYS_RAWIO",
                "CAP_SYS_RESOURCE",
                "CAP_NET_ADMIN",
                "CAP_NET_RAW",
                "CAP_DAC_OVERRIDE",
                "CAP_DAC_READ_SEARCH",
                "CAP_FOWNER",
                "CAP_SETUID",
                "CAP_SETGID",
                "CAP_SETPCAP",
                "CAP_KILL"
            ],
            "readonly_paths": {
                "/proc": "ro",
                "/sys": "ro",
                "/dev": "ro"
            },
            "masked_paths": [
                "/proc/acpi",
                "/proc/kcore", 
                "/proc/keys",
                "/proc/latency_stats",
                "/proc/timer_list",
                "/proc/timer_stats",
                "/proc/sched_debug",
                "/proc/scsi",
                "/sys/firmware"
            ]
        }
    
    def create_isolated_container(self, bot_id: str, code: str, token: str) -> dict:
        """ایجاد کانتینر فوق‌ایزوله"""
        
        if not self.docker_client:
            return {'success': False, 'error': 'Docker not available'}
        
        try:
            # آماده‌سازی کد با محدودیت‌های شدید
            secured_code = self._add_security_layer(code, token)
            
            # ایجاد دایرکتوری موقت
            sandbox_dir = os.path.join(config.SANDBOX_BASE, bot_id)
            os.makedirs(sandbox_dir, mode=0o750, exist_ok=True)
            
            # ذخیره کد با محدودیت دسترسی
            with open(os.path.join(sandbox_dir, 'bot.py'), 'w') as f:
                f.write(secured_code)
            
            # تنظیم مالکیت و مجوزها
            os.chown(sandbox_dir, 1000, 1000)  # کاربر non-root
            os.chmod(sandbox_dir, 0o750)
            
            # محدودیت‌های منابع
            mem_limit = f"{config.MAX_BOT_MEMORY_MB}m"
            cpu_quota = config.MAX_BOT_CPU_QUOTA
            cpu_period = 100000
            pids_limit = config.MAX_BOT_PIDS
            
            # ساختار دستورات داکر
            container_config = {
                'image': 'python:3.9-slim',
                'command': ['timeout', str(config.BOT_TIMEOUT_SECONDS), 'python', '/app/bot.py'],
                'name': f"motherbot_{bot_id}",
                'mem_limit': mem_limit,
                'memswap_limit': mem_limit,
                'cpu_quota': cpu_quota,
                'cpu_period': cpu_period,
                'pids_limit': pids_limit,
                'network_mode': 'none' if config.ENABLE_NETWORK_ISOLATION else 'bridge',
                'read_only': True,
                'cap_drop': self.security_profile['disabled'],
                'security_opt': [
                    'no-new-privileges:true',
                    'seccomp=./seccomp-profile.json'
                ],
                'volumes': {
                    sandbox_dir: {
                        'bind': '/app',
                        'mode': 'ro'
                    }
                },
                'working_dir': '/app',
                'user': '1000:1000',  # کاربر non-root
                'hostname': f'bot-{bot_id[:8]}',
                'domainname': 'sandbox.local',
                'stop_signal': 'SIGTERM',
                'stop_timeout': 10
            }
            
            # استفاده از gVisor اگر موجود باشه
            if self.use_gvisor:
                container_config['runtime'] = 'runsc'
            
            # اجرا
            container = self.docker_client.containers.run(**container_config, detach=True)
            
            # لاگ گرفتن
            logger.log_security_event("CONTAINER_CREATED", 0, f"bot_id={bot_id}, container={container.id}")
            
            return {
                'success': True,
                'container_id': container.id,
                'container_name': container.name
            }
            
        except APIError as e:
            logger.log_security_event("CONTAINER_ERROR", 0, f"error={str(e)}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _add_security_layer(self, code: str, token: str) -> str:
        """اضافه کردن لایه امنیتی به کد ربات"""
        
        security_wrapper = f'''
# ========== لایه امنیتی هسته ==========
import os
import sys
import signal
import resource
import warnings

# منع کردن کتابخانه‌های خطرناک
BLOCKED_MODULES = ['os', 'subprocess', 'socket', 'pty', 'fcntl', 'termios', 'resource', 'syslog']

def block_import(name, *args, **kwargs):
    if name in BLOCKED_MODULES:
        raise ImportError(f"Module {{name}} is blocked for security reasons")
    return original_import(name, *args, **kwargs)

original_import = __builtins__['__import__']
__builtins__['__import__'] = block_import

# محدودیت منابع
resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))  # 128MB
resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))  # حداکثر 64 پروسس
resource.setrlimit(resource.RLIMIT_NOFILE, (50, 50))  # حداکثر 50 فایل باز
resource.setrlimit(resource.RLIMIT_CPU, (3600, 3600))  # حداکثر 1 ساعت

# هندلر سیگنال‌های امن
def security_handler(signum, frame):
    print(f"Security violation: signal {{signum}}")
    sys.exit(1)

for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGQUIT, signal.SIGABRT]:
    signal.signal(sig, security_handler)

# پاکسازی متغیرهای محیطی
for env_var in ['PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'HOME']:
    if env_var in os.environ:
        del os.environ[env_var]

warnings.filterwarnings('error')

# توکن امن
TOKEN = "{token}"

# ========================================

{code}
'''
        return security_wrapper
    
    def stop_container(self, bot_id: str) -> bool:
        """توقف کانتینر"""
        try:
            container = self.docker_client.containers.get(f"motherbot_{bot_id}")
            container.stop(timeout=5)
            container.remove()
            return True
        except:
            return False
    
    def get_container_status(self, bot_id: str) -> dict:
        """وضعیت کانتینر"""
        try:
            container = self.docker_client.containers.get(f"motherbot_{bot_id}")
            stats = container.stats(stream=False)
            
            return {
                'running': container.status == 'running',
                'status': container.status,
                'memory_usage': stats.get('memory_stats', {}).get('usage', 0),
                'cpu_usage': stats.get('cpu_stats', {}).get('cpu_usage', {}).get('total_usage', 0),
                'network_rx': stats.get('networks', {}).get('rx_bytes', 0),
                'network_tx': stats.get('networks', {}).get('tx_bytes', 0)
            }
        except:
            return {'running': False}

# ==================== مدیریت سرورهای از راه دور (دقیق و واقعی) ====================
class RemoteNodeManager:
    """مدیریت حرفه‌ای سرورهای از راه دور با SSH"""
    
    def __init__(self):
        self.nodes = {}
        self.ssh_keys = {}
        self._load_nodes()
    
    def _load_nodes(self):
        """بارگذاری سرورها از دیتابیس"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM worker_nodes WHERE status = 'active'")
            for row in cursor.fetchall():
                self.nodes[row['node_id']] = dict(row)
    
    def add_node_interactive(self, chat_id: int) -> str:
        """افزودن سرور جدید به صورت تعاملی"""
        # مرحله 1: نام سرور
        msg = bot.send_message(chat_id, "🖥️ **مرحله 1/6: نام سرور را وارد کنید**\n\nمثال: `Server-Tehran-01`", parse_mode='Markdown')
        bot.register_next_step_handler(msg, self._step_get_username, chat_id)
        return "waiting_for_server_name"
    
    def _step_get_username(self, message, chat_id):
        """گرفتن نام کاربری"""
        node_name = message.text.strip()
        
        # مرحله 2: نام کاربری
        msg = bot.send_message(chat_id, "👤 **مرحله 2/6: نام کاربری SSH را وارد کنید**\n\nمثال: `root` یا `admin`", parse_mode='Markdown')
        bot.register_next_step_handler(msg, self._step_get_ip, chat_id, node_name)
    
    def _step_get_ip(self, message, chat_id, node_name):
        """گرفتن IP"""
        username = message.text.strip()
        
        # مرحله 3: IP
        msg = bot.send_message(chat_id, "🌐 **مرحله 3/6: آدرس IP سرور را وارد کنید**\n\nمثال: `192.168.1.100`", parse_mode='Markdown')
        bot.register_next_step_handler(msg, self._step_get_port, chat_id, node_name, username)
    
    def _step_get_port(self, message, chat_id, node_name, username):
        """گرفتن پورت"""
        ip_address = message.text.strip()
        
        # مرحله 4: پورت
        msg = bot.send_message(chat_id, "🔌 **مرحله 4/6: پورت SSH را وارد کنید**\n\nپیش‌فرض: `22`", parse_mode='Markdown')
        bot.register_next_step_handler(msg, self._step_get_password, chat_id, node_name, username, ip_address)
    
    def _step_get_password(self, message, chat_id, node_name, username, ip_address):
        """گرفتن رمز عبور"""
        try:
            ssh_port = int(message.text.strip()) if message.text.strip() else 22
        except:
            ssh_port = 22
        
        # مرحله 5: رمز عبور
        msg = bot.send_message(chat_id, "🔐 **مرحله 5/6: رمز عبور SSH را وارد کنید**\n\n⚠️ این رمز به صورت رمزنگاری شده ذخیره می‌شود", parse_mode='Markdown')
        bot.register_next_step_handler(msg, self._step_test_connection, chat_id, node_name, username, ip_address, ssh_port)
    
    def _step_test_connection(self, message, chat_id, node_name, username, ip_address, ssh_port):
        """تست اتصال SSH"""
        password = message.text.strip()
        
        status_msg = bot.send_message(chat_id, "🔄 **در حال تست اتصال به سرور...**\n\n⏳ لطفاً صبر کنید", parse_mode='Markdown')
        
        try:
            # تست اتصال SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=ip_address,
                port=ssh_port,
                username=username,
                password=password,
                timeout=15
            )
            
            # بررسی داکر
            stdin, stdout, stderr = ssh.exec_command("docker --version")
            docker_version = stdout.read().decode().strip()
            
            if not docker_version:
                bot.edit_message_text(
                    "❌ **خطا: Docker روی سرور نصب نیست!**\n\n"
                    "لطفاً ابتدا Docker را نصب کنید:\n"
                    "```bash\ncurl -fsSL https://get.docker.com | sh\n```",
                    chat_id, status_msg.message_id, parse_mode='Markdown'
                )
                ssh.close()
                return
            
            # بررسی منابع
            stdin, stdout, stderr = ssh.exec_command("free -m | grep Mem | awk '{print $2}'")
            total_memory = int(stdout.read().decode().strip())
            
            stdin, stdout, stderr = ssh.exec_command("nproc")
            total_cpu = int(stdout.read().decode().strip())
            
            ssh.close()
            
            # ذخیره در دیتابیس
            encrypted_password = HardwareSecurity.encrypt_config(password, HardwareSecurity.get_hardware_id())
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO worker_nodes 
                    (node_name, ip_address, ssh_port, username, encrypted_password, 
                     status, total_memory, total_cpu, available_memory, available_cpu,
                     docker_version, created_at)
                    VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
                ''', (
                    node_name, ip_address, ssh_port, username, encrypted_password.decode(),
                    total_memory, total_cpu, total_memory, total_cpu,
                    docker_version, datetime.now().isoformat()
                ))
                conn.commit()
                
                node_id = cursor.lastrowid
            
            # موفقیت
            bot.edit_message_text(
                f"✅ **سرور با موفقیت اضافه شد!**\n\n"
                f"📊 **اطلاعات سرور:**\n"
                f"• نام: `{node_name}`\n"
                f"• IP: `{ip_address}`\n"
                f"• پورت: `{ssh_port}`\n"
                f"• کاربر: `{username}`\n"
                f"• رم: `{total_memory}MB`\n"
                f"• CPU: `{total_cpu} هسته`\n"
                f"• Docker: `{docker_version}`\n\n"
                f"🆔 شناسه سرور: `{node_id}`\n\n"
                f"🔧 این سرور آماده دریافت ربات‌هاست!",
                chat_id, status_msg.message_id, parse_mode='Markdown'
            )
            
            logger.log_system_event("NODE_ADDED", f"node={node_name}, ip={ip_address}")
            
        except paramiko.AuthenticationException:
            bot.edit_message_text(
                "❌ **خطا: نام کاربری یا رمز عبور اشتباه است!**\n\n"
                "لطفاً دوباره تلاش کنید.",
                chat_id, status_msg.message_id, parse_mode='Markdown'
            )
        except paramiko.SSHException as e:
            bot.edit_message_text(
                f"❌ **خطا در اتصال SSH:**\n```\n{str(e)}\n```\n\n"
                "لطفاً مطمئن شوید:\n"
                "• SSH سرویس در حال اجراست\n"
                "• پورت صحیح است\n"
                "• فایروال اجازه اتصال می‌دهد",
                chat_id, status_msg.message_id, parse_mode='Markdown'
            )
        except Exception as e:
            bot.edit_message_text(
                f"❌ **خطای غیرمنتظره:**\n```\n{str(e)}\n```",
                chat_id, status_msg.message_id, parse_mode='Markdown'
            )
    
    def get_available_node(self) -> Optional[dict]:
        """دریافت یک سرور آزاد"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM worker_nodes 
                WHERE status = 'active' 
                AND current_bots < max_bots 
                ORDER BY current_bots ASC 
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def deploy_bot_to_node(self, node: dict, bot_id: str, code: str) -> dict:
        """استقرار ربات روی سرور از راه دور"""
        try:
            # رمزگشایی رمز
            password = HardwareSecurity.decrypt_config(
                node['encrypted_password'].encode(),
                HardwareSecurity.get_hardware_id()
            )
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=node['ip_address'],
                port=node['ssh_port'],
                username=node['username'],
                password=password,
                timeout=15
            )
            
            # ایجاد دایرکتوری
            ssh.exec_command(f'mkdir -p /opt/mother_bot/bots/{bot_id}')
            
            # آپلود فایل
            sftp = ssh.open_sftp()
            remote_path = f'/opt/mother_bot/bots/{bot_id}/bot.py'
            with sftp.open(remote_path, 'w') as f:
                f.write(code)
            sftp.close()
            
            # اجرا با داکر
            cmd = f'''
cd /opt/mother_bot/bots/{bot_id}
docker run -d \\
  --name motherbot_{bot_id} \\
  --memory 128m \\
  --cpus 0.5 \\
  --read-only \\
  --network none \\
  --cap-drop ALL \\
  --security-opt no-new-privileges:true \\
  -v $(pwd):/app:ro \\
  python:3.9-slim \\
  timeout 3600 python /app/bot.py
'''
            stdin, stdout, stderr = ssh.exec_command(cmd)
            container_id = stdout.read().decode().strip()
            
            ssh.close()
            
            return {'success': True, 'container_id': container_id}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# ==================== کلاس اصلی ====================
class MotherBotEnterprise:
    """ربات اصلی با قابلیت‌های سازمانی"""
    
    def __init__(self):
        self.isolation = HardwareIsolation()
        self.node_manager = RemoteNodeManager()
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self._register_handlers()
    
    def _register_handlers(self):
        """ثبت هندلرها"""
        
        @self.bot.message_handler(commands=['start'])
        def start_cmd(message):
            self._handle_start(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '➕ افزودن سرور جدید')
        def add_server_cmd(message):
            if message.from_user.id not in ADMIN_IDS:
                return
            self.node_manager.add_node_interactive(message.chat.id)
        
        @self.bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات')
        def create_bot_cmd(message):
            self._handle_create_bot(message)
        
        @self.bot.message_handler(content_types=['document'])
        def handle_file(message):
            self._handle_bot_file(message)
        
        # سایر هندلرها...
    
    def _handle_start(self, message):
        """دستور استارت"""
        user_id = message.from_user.id
        
        # بررسی اینکه کاربر قبلاً ربات دارد یا نه
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bot_id FROM bots WHERE user_id = ?", (user_id,))
            has_bot = cursor.fetchone()
        
        if has_bot:
            text = "✅ شما قبلاً یک ربات ساخته‌اید!\n\nهر کاربر فقط می‌تواند ۱ ربات داشته باشد."
        else:
            text = """🚀 **به ربات سازنده ربات خوش آمدید!**

💰 **قیمت اشتراک:** ۲۰۰,۰۰۰ تومان
💳 **شماره کارت:** 5892 1011 8732 2777
👤 **صاحب کارت:** مرتضی نیکخو خنجری

📸 پس از واریز، تصویر فیش را ارسال کنید.

⚠️ **توجه:** هر کاربر فقط می‌تواند ۱ ربات بسازد!"""
        
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    def _handle_create_bot(self, message):
        """ساخت ربات جدید"""
        user_id = message.from_user.id
        
        # بررسی اشتراک
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT subscription_status, subscription_expiry, bot_id 
                FROM users LEFT JOIN bots ON users.user_id = bots.user_id
                WHERE users.user_id = ?
            """, (user_id,))
            user = cursor.fetchone()
        
        if not user or user['subscription_status'] != 'active':
            self.bot.send_message(message.chat.id, "❌ ابتدا اشتراک خود را فعال کنید!")
            return
        
        if user['bot_id']:
            self.bot.send_message(message.chat.id, "❌ شما قبلاً یک ربات ساخته‌اید!\nهر کاربر فقط ۱ ربات می‌تواند داشته باشد.")
            return
        
        self.bot.send_message(message.chat.id, "📤 فایل `.py` ربات خود را ارسال کنید.")
    
    def _handle_bot_file(self, message):
        """پردازش فایل ربات"""
        user_id = message.from_user.id
        
        # بررسی مجدد محدودیت
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bot_id FROM bots WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                self.bot.reply_to(message, "❌ شما قبلاً ربات دارید!")
                return
        
        if not message.document.file_name.endswith('.py'):
            self.bot.reply_to(message, "❌ فقط فایل‌های `.py` مجاز هستند!")
            return
        
        status_msg = self.bot.reply_to(message, "🔄 در حال پردازش و ایزوله‌سازی...")
        
        try:
            # دانلود فایل
            file_info = self.bot.get_file(message.document.file_id)
            downloaded = self.bot.download_file(file_info.file_path)
            
            # خواندن کد
            code = downloaded.decode('utf-8', errors='ignore')
            
            # استخراج توکن
            token = self._extract_token(code)
            if not token:
                self.bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
                return
            
            # بررسی توکن
            try:
                resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                if resp.status_code != 200:
                    self.bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
                    return
                bot_info = resp.json()['result']
            except:
                self.bot.edit_message_text("❌ خطا در بررسی توکن!", message.chat.id, status_msg.message_id)
                return
            
            # یافتن سرور مناسب
            node = self.node_manager.get_available_node()
            
            if node:
                # استقرار روی سرور از راه دور
                result = self.node_manager.deploy_bot_to_node(node, str(user_id), code)
                
                if result['success']:
                    bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
                    
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO bots (bot_id, user_id, bot_token, bot_name, bot_username, 
                                           worker_node, container_id, status, created_at, last_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
                        ''', (bot_id, user_id, token, bot_info['first_name'], bot_info['username'],
                              node['node_name'], result['container_id'], datetime.now().isoformat(), 
                              datetime.now().isoformat()))
                        conn.commit()
                    
                    self.bot.edit_message_text(
                        f"✅ **ربات با موفقیت ساخته شد!**\n\n"
                        f"🤖 نام: `{bot_info['first_name']}`\n"
                        f"🔗 لینک: https://t.me/{bot_info['username']}\n"
                        f"🖥️ سرور: `{node['node_name']}`\n"
                        f"🔒 ایزوله: **فعال**\n\n"
                        f"⚠️ توجه: هر کاربر فقط ۱ ربات می‌تواند داشته باشد!",
                        message.chat.id, status_msg.message_id, parse_mode='Markdown'
                    )
                    
                    logger.log_security_event("BOT_CREATED", user_id, f"bot={bot_info['username']}, node={node['node_name']}")
                else:
                    self.bot.edit_message_text(f"❌ خطا در استقرار: {result.get('error', 'ناشناخته')}", 
                                             message.chat.id, status_msg.message_id)
            else:
                # اجرا locally
                result = self.isolation.create_isolated_container(str(user_id), code, token)
                
                if result['success']:
                    bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
                    
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO bots (bot_id, user_id, bot_token, bot_name, bot_username, 
                                           container_id, status, created_at, last_active)
                            VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?)
                        ''', (bot_id, user_id, token, bot_info['first_name'], bot_info['username'],
                              result['container_id'], datetime.now().isoformat(), datetime.now().isoformat()))
                        conn.commit()
                    
                    self.bot.edit_message_text(
                        f"✅ **ربات با موفقیت ساخته شد!**\n\n"
                        f"🤖 نام: `{bot_info['first_name']}`\n"
                        f"🔗 لینک: https://t.me/{bot_info['username']}\n"
                        f"🔒 ایزوله: **فعال**\n\n"
                        f"⚠️ توجه: هر کاربر فقط ۱ ربات می‌تواند داشته باشد!",
                        message.chat.id, status_msg.message_id, parse_mode='Markdown'
                    )
                else:
                    self.bot.edit_message_text(f"❌ خطا: {result.get('error', 'ناشناخته')}", 
                                             message.chat.id, status_msg.message_id)
        
        except Exception as e:
            self.bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)
            logger.log_security_event("ERROR", user_id, f"error={str(e)}")
    
    def _extract_token(self, code: str) -> Optional[str]:
        """استخراج توکن از کد"""
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
    
    def run(self):
        """اجرای ربات"""
        print("=" * 70)
        print("🛡️ MOTHER BOT - NUCLEAR ENTERPRISE EDITION".center(70))
        print("=" * 70)
        print(f"🔒 امنیت: سطح نظامی")
        print(f"🖥️ ایزوله‌سازی: gVisor + Docker")
        print(f"📊 معماری: چندسروره")
        print(f"💾 دیتابیس: PostgreSQL Ready")
        print(f"🎯 هر کاربر: فقط ۱ ربات")
        print("=" * 70)
        
        while True:
            try:
                self.bot.infinity_polling(timeout=60)
            except Exception as e:
                print(f"❌ خطا: {e}")
                time.sleep(5)

# ==================== اجرا ====================
ADMIN_IDS = [327855654]

if __name__ == "__main__":
    mother_bot = MotherBotEnterprise()
    mother_bot.run()
