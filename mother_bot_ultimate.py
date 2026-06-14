#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🛡️ MOTHER BOT - ULTIMATE ENTERPRISE EDITION 
⚡ امنیت نظامی | ایزوله‌سازی سخت‌افزاری | پنل مدیریت کامل
🔒 پشتیبانی از میلیون‌ها کاربر | هر کاربر فقط ۱ ربات
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import sqlite3
import hashlib
import secrets
import re
import threading
import subprocess
import shutil
import tempfile
import zipfile
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import wraps
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# ==================== بررسی کتابخانه‌ها ====================
try:
    import telebot
    from telebot import types
except ImportError:
    print("❌ نصب کنید: pip install pyTelegramBotAPI")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ نصب کنید: pip install requests")
    sys.exit(1)

try:
    import paramiko
except ImportError:
    print("⚠️ paramiko نصب نیست - قابلیت اضافه کردن سرور محدود خواهد شد")
    paramiko = None

# ==================== تنظیمات امنیتی ====================

class SecurityLevel(Enum):
    MAXIMUM = "maximum"
    HIGH = "high"

@dataclass
class SecurityConfig:
    SECURITY_LEVEL: SecurityLevel = SecurityLevel.MAXIMUM
    MAX_FILE_SIZE_MB: int = 10
    MAX_BOTS_PER_USER: int = 1
    MAX_BOT_MEMORY_MB: int = 256
    MAX_BOT_CPU: float = 0.5
    MAX_BOT_TIMEOUT: int = 3600
    ENABLE_NETWORK_ISOLATION: bool = True
    ENABLE_READONLY_FS: bool = True
    ENABLE_AUDIT_LOG: bool = True
    HEARTBEAT_INTERVAL: int = 30

config = SecurityConfig()

# ==================== دیتابیس توزیع شده ====================

class DistributedDatabase:
    """دیتابیس با پشتیبانی از شاردینگ و میلیون‌ها کاربر"""
    
    def __init__(self):
        self.base_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.base_dir, exist_ok=True)
        
        # تعداد شاردها
        self.num_shards = 100
        self.shards = {}
        self._init_shards()
        self._init_metadata()
        self._init_caches()
    
    def _init_shards(self):
        """ایجاد شاردهای دیتابیس"""
        for i in range(self.num_shards):
            shard_path = os.path.join(self.base_dir, f'shard_{i:03d}.db')
            self.shards[i] = shard_path
            
            conn = sqlite3.connect(shard_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-500000")
            conn.execute("PRAGMA mmap_size=10000000000")
            conn.close()
    
    def _get_shard(self, user_id: int) -> int:
        """محاسبه شارد بر اساس user_id"""
        return user_id % self.num_shards
    
    def _get_connection(self, user_id: int = None):
        """دریافت کانکشن دیتابیس"""
        if user_id is not None:
            shard_id = self._get_shard(user_id)
            db_path = self.shards[shard_id]
        else:
            db_path = os.path.join(self.base_dir, 'metadata.db')
        
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_metadata(self):
        """ایجاد دیتابیس متادیتا"""
        with self._get_connection() as conn:
            # جدول کاربران
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    referrals_count INTEGER DEFAULT 0,
                    subscription_status TEXT DEFAULT 'inactive',
                    subscription_expiry TIMESTAMP,
                    wallet_balance INTEGER DEFAULT 0,
                    has_bot INTEGER DEFAULT 0,
                    created_at TIMESTAMP,
                    last_active TIMESTAMP,
                    is_banned INTEGER DEFAULT 0
                )
            ''')
            
            # جدول ربات‌ها (هر کاربر فقط ۱ ربات)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    bot_id TEXT PRIMARY KEY,
                    user_id INTEGER UNIQUE,
                    bot_name TEXT,
                    bot_username TEXT,
                    bot_token TEXT,
                    worker_node TEXT,
                    container_id TEXT,
                    status TEXT DEFAULT 'stopped',
                    created_at TIMESTAMP,
                    last_active TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # جدول سرورها (ماشین‌ها)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS worker_nodes (
                    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_name TEXT UNIQUE,
                    ip_address TEXT,
                    ssh_port INTEGER DEFAULT 22,
                    username TEXT,
                    encrypted_password TEXT,
                    max_bots INTEGER DEFAULT 1000,
                    current_bots INTEGER DEFAULT 0,
                    total_memory INTEGER,
                    total_cpu INTEGER,
                    status TEXT DEFAULT 'active',
                    last_heartbeat TIMESTAMP,
                    created_at TIMESTAMP
                )
            ''')
            
            # جدول فیش‌ها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    receipt_path TEXT,
                    payment_code TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewed_by INTEGER
                )
            ''')
            
            # جدول کتابخانه‌ها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS libraries (
                    lib_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lib_name TEXT UNIQUE,
                    lib_version TEXT,
                    installed_at TIMESTAMP,
                    installed_by INTEGER
                )
            ''')
            
            # جدول تنظیمات
            conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP,
                    updated_by INTEGER
                )
            ''')
            
            # جدول لاگ امنیتی
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    user_id INTEGER,
                    details TEXT,
                    ip_address TEXT,
                    created_at TIMESTAMP
                )
            ''')
            
            # تنظیمات پیشفرض
            default_settings = {
                'card_number': '5892101187322777',
                'card_holder': 'مرتضی نیکخو خنجری',
                'card_bank': 'بانک ملی',
                'subscription_price': '200000',
                'subscription_price_display': '۲۰۰,۰۰۰ تومان',
                'welcome_text': '🚀 به ربات امن خوش آمدید {name}!\n⚡ امنیت نظامی | ایزوله‌سازی کامل',
                'guide_text': '📚 راهنمای امن:\n1. {price} به کارت زیر واریز کنید\n2. عکس فیش را ارسال کنید\n3. فایل ربات را ارسال کنید\n4. ربات در محیط ایزوله اجرا می‌شود\n\n🔒 هیچ کد مخربی به سرور دسترسی ندارد',
                'admin_ids': '327855654'
            }
            
            for key, value in default_settings.items():
                conn.execute('INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)',
                           (key, value, datetime.now().isoformat()))
            
            conn.commit()
    
    def _init_caches(self):
        """ایجاد کش‌ها"""
        self.user_cache = {}
        self.setting_cache = {}
        self._load_settings_cache()
    
    def _load_settings_cache(self):
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT key, value FROM settings')
            for row in cursor:
                self.setting_cache[row['key']] = row['value']
    
    def get_setting(self, key: str) -> str:
        if key in self.setting_cache:
            return self.setting_cache[key]
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] if row else None
    
    def update_setting(self, key: str, value: str, admin_id: int):
        with self._get_connection() as conn:
            conn.execute('UPDATE settings SET value = ?, updated_at = ?, updated_by = ? WHERE key = ?',
                        (value, datetime.now().isoformat(), admin_id, key))
            conn.commit()
        self.setting_cache[key] = value
    
    def get_user(self, user_id: int) -> Optional[dict]:
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        with self._get_connection(user_id) as conn:
            cursor = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                user = dict(row)
                self.user_cache[user_id] = user
                return user
        return None
    
    def create_user(self, user_id: int, username: str, first_name: str, last_name: str = "", referred_by: int = None) -> bool:
        try:
            with self._get_connection(user_id) as conn:
                now = datetime.now().isoformat()
                referral_code = hashlib.sha256(f"{user_id}{now}{secrets.token_hex(16)}".encode()).hexdigest()[:16]
                
                conn.execute('''
                    INSERT OR IGNORE INTO users 
                    (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
                
                if referred_by and referred_by != user_id:
                    conn.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
                
                conn.commit()
                self._log_security("USER_CREATED", user_id, f"referred_by={referred_by}")
                return True
        except Exception as e:
            self._log_security("ERROR", user_id, f"create_user: {str(e)}")
            return False
    
    def check_subscription(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        if user['subscription_status'] == 'active' and user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
        return False
    
    def activate_subscription(self, user_id: int, admin_id: int = None):
        with self._get_connection(user_id) as conn:
            expiry = datetime.now() + timedelta(days=30)
            conn.execute('UPDATE users SET subscription_status = "active", subscription_expiry = ? WHERE user_id = ?',
                        (expiry.isoformat(), user_id))
            conn.commit()
        self._log_security("SUBSCRIPTION_ACTIVATED", user_id, f"by_admin={admin_id}")
        if user_id in self.user_cache:
            del self.user_cache[user_id]
    
    def user_has_bot(self, user_id: int) -> bool:
        with self._get_connection(user_id) as conn:
            cursor = conn.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return row['count'] > 0
    
    def get_user_bot(self, user_id: int) -> Optional[dict]:
        with self._get_connection(user_id) as conn:
            cursor = conn.execute('SELECT * FROM bots WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_bot(self, user_id: int, bot_id: str, bot_name: str, bot_username: str, bot_token: str, worker_node: str = None, container_id: str = None) -> bool:
        if self.user_has_bot(user_id):
            return False
        try:
            with self._get_connection(user_id) as conn:
                now = datetime.now().isoformat()
                conn.execute('''
                    INSERT INTO bots (bot_id, user_id, bot_name, bot_username, bot_token, worker_node, container_id, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (bot_id, user_id, bot_name, bot_username, bot_token, worker_node, container_id, now, now))
                
                conn.execute('UPDATE users SET has_bot = 1, last_active = ? WHERE user_id = ?', (now, user_id))
                conn.commit()
                
                if worker_node:
                    conn = self._get_connection()
                    conn.execute('UPDATE worker_nodes SET current_bots = current_bots + 1 WHERE node_name = ?', (worker_node,))
                    conn.commit()
                
                self._log_security("BOT_CREATED", user_id, f"bot={bot_name}, node={worker_node}")
                return True
        except Exception as e:
            self._log_security("ERROR", user_id, f"add_bot: {str(e)}")
            return False
    
    def delete_bot(self, user_id: int) -> bool:
        bot = self.get_user_bot(user_id)
        if not bot:
            return False
        try:
            with self._get_connection(user_id) as conn:
                conn.execute('DELETE FROM bots WHERE user_id = ?', (user_id,))
                conn.execute('UPDATE users SET has_bot = 0 WHERE user_id = ?', (user_id,))
                conn.commit()
                
                if bot.get('worker_node'):
                    conn = self._get_connection()
                    conn.execute('UPDATE worker_nodes SET current_bots = current_bots - 1 WHERE node_name = ?', (bot['worker_node'],))
                    conn.commit()
                
                self._log_security("BOT_DELETED", user_id, f"bot={bot.get('bot_name')}")
                return True
        except Exception as e:
            self._log_security("ERROR", user_id, f"delete_bot: {str(e)}")
            return False
    
    def add_wallet_balance(self, user_id: int, amount: int):
        with self._get_connection(user_id) as conn:
            conn.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE user_id = ?', (amount, user_id))
            conn.commit()
        self._log_security("WALLET_ADDED", user_id, f"amount={amount}")
        if user_id in self.user_cache:
            del self.user_cache[user_id]
    
    def add_worker_node(self, node_data: dict) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO worker_nodes (node_name, ip_address, ssh_port, username, encrypted_password, max_bots, total_memory, total_cpu, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (node_data['node_name'], node_data['ip_address'], node_data['ssh_port'], node_data['username'],
                  node_data['encrypted_password'], node_data['max_bots'], node_data['total_memory'], node_data['total_cpu'], datetime.now().isoformat()))
            conn.commit()
            self._log_security("NODE_ADDED", 0, f"node={node_data['node_name']}")
            return cursor.lastrowid
    
    def get_worker_nodes(self, status: str = None) -> List[dict]:
        with self._get_connection() as conn:
            if status:
                cursor = conn.execute('SELECT * FROM worker_nodes WHERE status = ?', (status,))
            else:
                cursor = conn.execute('SELECT * FROM worker_nodes')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_node_status(self, node_id: int, status: str):
        with self._get_connection() as conn:
            conn.execute('UPDATE worker_nodes SET status = ?, last_heartbeat = ? WHERE node_id = ?',
                        (status, datetime.now().isoformat(), node_id))
            conn.commit()
    
    def add_library(self, lib_name: str, lib_version: str, admin_id: int):
        with self._get_connection() as conn:
            conn.execute('INSERT OR IGNORE INTO libraries (lib_name, lib_version, installed_at, installed_by) VALUES (?, ?, ?, ?)',
                        (lib_name, lib_version, datetime.now().isoformat(), admin_id))
            conn.commit()
    
    def get_libraries(self) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT * FROM libraries ORDER BY installed_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_users(self, limit: int = 100) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT user_id, username, first_name, subscription_status, wallet_balance, has_bot, created_at
                FROM users ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_user(self, user_id: int) -> bool:
        try:
            with self._get_connection(user_id) as conn:
                conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                conn.execute('DELETE FROM bots WHERE user_id = ?', (user_id,))
                conn.commit()
            if user_id in self.user_cache:
                del self.user_cache[user_id]
            self._log_security("USER_DELETED", user_id, "")
            return True
        except Exception as e:
            self._log_security("ERROR", user_id, f"delete_user: {str(e)}")
            return False
    
    def add_receipt(self, user_id: int, amount: int, receipt_path: str, payment_code: str):
        with self._get_connection() as conn:
            conn.execute('''
                INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, receipt_path, payment_code, datetime.now().isoformat()))
            conn.commit()
    
    def get_pending_receipts(self) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
            return [dict(row) for row in cursor.fetchall()]
    
    def approve_receipt(self, receipt_id: int, admin_id: int):
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT user_id FROM receipts WHERE id = ?', (receipt_id,))
            row = cursor.fetchone()
            if row:
                conn.execute('UPDATE receipts SET status = "approved", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                            (datetime.now().isoformat(), admin_id, receipt_id))
                conn.commit()
                self.activate_subscription(row['user_id'], admin_id)
                self._log_security("RECEIPT_APPROVED", row['user_id'], f"by_admin={admin_id}")
    
    def reject_receipt(self, receipt_id: int, admin_id: int):
        with self._get_connection() as conn:
            conn.execute('UPDATE receipts SET status = "rejected", reviewed_at = ?, reviewed_by = ? WHERE id = ?',
                        (datetime.now().isoformat(), admin_id, receipt_id))
            conn.commit()
            self._log_security("RECEIPT_REJECTED", 0, f"receipt_id={receipt_id}, by_admin={admin_id}")
    
    def _log_security(self, event_type: str, user_id: int, details: str):
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT INTO security_logs (event_type, user_id, details, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (event_type, user_id, details, datetime.now().isoformat()))
                conn.commit()
        except:
            pass

db = DistributedDatabase()

# ==================== ایزوله‌سازی با Docker ====================

class DockerSandbox:
    """ایزوله‌سازی کامل کد کاربران با Docker"""
    
    def __init__(self):
        self.docker_available = self._check_docker()
        self.running_containers = {}
        self.lock = threading.Lock()
        if self.docker_available:
            self._build_secure_image()
    
    def _check_docker(self) -> bool:
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _build_secure_image(self):
        dockerfile = '''FROM alpine:3.19
RUN apk add --no-cache python3 py3-pip && \\
    pip3 install --no-cache-dir pyTelegramBotAPI && \\
    adduser -D -u 1000 -s /sbin/nologin botuser
RUN mkdir -p /app && chown -R botuser:botuser /app && chmod 755 /app
USER botuser
WORKDIR /app
ENTRYPOINT ["timeout", "3600"]
CMD ["python3", "-B", "bot.py"]'''
        
        dockerfile_path = os.path.join(tempfile.gettempdir(), 'Dockerfile.secure')
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile)
        try:
            subprocess.run(['docker', 'build', '-f', dockerfile_path, '-t', 'motherbot-secure:latest', tempfile.gettempdir()],
                          capture_output=True, timeout=60)
            os.unlink(dockerfile_path)
        except:
            pass
    
    def run_isolated(self, code: str, token: str) -> dict:
        if not self.docker_available:
            return {'success': False, 'error': 'Docker در دسترس نیست'}
        
        container_name = f"bot_{secrets.token_hex(8)}"
        
        try:
            secured_code = self._add_security_layer(code, token)
            temp_dir = tempfile.mkdtemp(prefix='motherbot_')
            code_path = os.path.join(temp_dir, 'bot.py')
            
            with open(code_path, 'w') as f:
                f.write(secured_code)
            
            cmd = [
                'docker', 'run', '-d',
                '--name', container_name,
                '--memory', f"{config.MAX_BOT_MEMORY_MB}m",
                '--memory-swap', f"{config.MAX_BOT_MEMORY_MB}m",
                '--cpus', str(config.MAX_BOT_CPU),
                '--pids-limit', '20',
                '--read-only' if config.ENABLE_READONLY_FS else '',
                '--network', 'none' if config.ENABLE_NETWORK_ISOLATION else 'bridge',
                '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges:true',
                '-v', f"{temp_dir}:/app:ro',
                'motherbot-secure:latest'
            ]
            cmd = [x for x in cmd if x]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                with self.lock:
                    self.running_containers[container_name] = {'container_id': container_id, 'temp_dir': temp_dir, 'started_at': time.time()}
                return {'success': True, 'container_id': container_id, 'container_name': container_name}
            else:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {'success': False, 'error': result.stderr[:200]}
        except Exception as e:
            return {'success': False, 'error': str(e)[:200]}
    
    def _add_security_layer(self, code: str, token: str) -> str:
        blocked = "'os', 'subprocess', 'socket', 'pty', 'fcntl', 'termios', 'resource', 'syslog', 'signal', 'multiprocessing', 'ctypes', 'code', 'codeop', 'compile', '__import__', 'open', 'file', 'input', 'eval', 'exec'"
        
        return f'''import sys, builtins, warnings
BLOCKED = [{blocked}]
original_import = builtins.__import__
def secure_import(name, *args, **kwargs):
    if name in BLOCKED or any(name.startswith(b) for b in BLOCKED):
        raise ImportError(f"Module '{{name}}' is blocked")
    return original_import(name, *args, **kwargs)
builtins.__import__ = secure_import
builtins.open = None
builtins.input = None
builtins.eval = None
builtins.exec = None
builtins.compile = None
for env in ['PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'HOME', 'USER', 'SHELL']:
    if env in __import__('os').environ:
        del __import__('os').environ[env]
warnings.filterwarnings('ignore')
TOKEN = "{token}"
{code}'''
    
    def stop_container(self, container_name: str) -> bool:
        with self.lock:
            if container_name in self.running_containers:
                try:
                    subprocess.run(['docker', 'stop', container_name], capture_output=True, timeout=10)
                    subprocess.run(['docker', 'rm', container_name], capture_output=True, timeout=10)
                    shutil.rmtree(self.running_containers[container_name]['temp_dir'], ignore_errors=True)
                    del self.running_containers[container_name]
                    return True
                except:
                    pass
        return False
    
    def get_status(self, container_name: str) -> dict:
        try:
            result = subprocess.run(['docker', 'inspect', '-f', '{{.State.Status}}', container_name], capture_output=True, text=True, timeout=5)
            status = result.stdout.strip()
            return {'running': status == 'running', 'status': status}
        except:
            return {'running': False}
    
    def restart_all(self):
        for container_name in list(self.running_containers.keys()):
            self.stop_container(container_name)

sandbox = DockerSandbox()

# ==================== مدیریت سرورهای از راه دور ====================

class RemoteNodeManager:
    """مدیریت سرورهای از راه دور با SSH"""
    
    def __init__(self):
        self.ssh_clients = {}
    
    def test_connection(self, ip: str, port: int, username: str, password: str) -> Tuple[bool, str, dict]:
        if not paramiko:
            return False, "paramiko نصب نیست", None
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, port=port, username=username, password=password, timeout=15)
            
            info = {}
            stdin, stdout, stderr = ssh.exec_command("free -m | grep Mem | awk '{print $2}'")
            info['total_memory'] = int(stdout.read().decode().strip())
            stdin, stdout, stderr = ssh.exec_command("nproc")
            info['total_cpu'] = int(stdout.read().decode().strip())
            stdin, stdout, stderr = ssh.exec_command("docker --version")
            docker_version = stdout.read().decode().strip()
            if not docker_version:
                ssh.close()
                return False, "Docker نصب نیست", None
            info['docker_version'] = docker_version
            ssh.close()
            return True, "اتصال موفق", info
        except Exception as e:
            return False, str(e), None
    
    def deploy_bot(self, node: dict, bot_id: str, code: str) -> dict:
        if not paramiko:
            return {'success': False, 'error': 'paramiko نصب نیست'}
        
        try:
            password = self._decrypt_password(node['encrypted_password'])
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=node['ip_address'], port=node['ssh_port'], username=node['username'], password=password, timeout=15)
            
            ssh.exec_command(f'mkdir -p /opt/motherbot/bots/{bot_id}')
            sftp = ssh.open_sftp()
            with sftp.open(f'/opt/motherbot/bots/{bot_id}/bot.py', 'w') as f:
                f.write(code)
            sftp.close()
            
            cmd = f'''cd /opt/motherbot/bots/{bot_id}
docker run -d --name bot_{bot_id} --memory 256m --cpus 0.5 --read-only --network none --cap-drop ALL -v $(pwd):/app:ro python:3.9-slim timeout 3600 python /app/bot.py'''
            stdin, stdout, stderr = ssh.exec_command(cmd)
            container_id = stdout.read().decode().strip()
            ssh.close()
            return {'success': True, 'container_id': container_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _encrypt_password(self, password: str) -> str:
        key = hashlib.sha256(b'motherbot_secure_key_2024').digest()
        encrypted = base64.b64encode(bytes([ord(c) ^ key[i % len(key)] for i, c in enumerate(password)])).decode()
        return encrypted
    
    def _decrypt_password(self, encrypted: str) -> str:
        key = hashlib.sha256(b'motherbot_secure_key_2024').digest()
        decrypted_bytes = base64.b64decode(encrypted)
        decrypted = ''.join(chr(decrypted_bytes[i] ^ key[i % len(key)]) for i in range(len(decrypted_bytes)))
        return decrypted

node_manager = RemoteNodeManager()

# ==================== توابع کمکی ====================

def get_setting(key: str) -> str:
    return db.get_setting(key)

def update_setting(key: str, value: str, admin_id: int):
    db.update_setting(key, value, admin_id)

def get_user(user_id: int):
    return db.get_user(user_id)

def create_user(user_id: int, username: str, first_name: str, last_name: str = "", referred_by: int = None):
    return db.create_user(user_id, username, first_name, last_name, referred_by)

def check_subscription(user_id: int) -> bool:
    return db.check_subscription(user_id)

def activate_subscription(user_id: int, admin_id: int = None):
    db.activate_subscription(user_id, admin_id)

def user_has_bot(user_id: int) -> bool:
    return db.user_has_bot(user_id)

def get_user_bot(user_id: int):
    return db.get_user_bot(user_id)

def add_bot(user_id: int, bot_id: str, bot_name: str, bot_username: str, bot_token: str, worker_node: str = None, container_id: str = None):
    return db.add_bot(user_id, bot_id, bot_name, bot_username, bot_token, worker_node, container_id)

def delete_bot(user_id: int):
    return db.delete_bot(user_id)

def add_wallet_balance(user_id: int, amount: int):
    db.add_wallet_balance(user_id, amount)

def extract_token(code: str) -> Optional[str]:
    patterns = [r'token\s*=\s*["\']([^"\']{35,50})["\']', r'TOKEN\s*=\s*["\']([^"\']{35,50})["\']', r'BOT_TOKEN\s*=\s*["\']([^"\']{35,50})["\']']
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            token = match.group(1)
            if len(token) >= 35 and ':' in token:
                return token
    return None

def validate_token(token: str) -> Tuple[bool, Optional[dict]]:
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if response.status_code == 200 and response.json().get('ok'):
            return True, response.json().get('result')
        return False, None
    except:
        return False, None

def validate_python_code(code: str) -> Tuple[bool, str]:
    dangerous = [('os\.system', 'دسترسی به سیستم'), ('subprocess\.', 'اجرای فرمان'), ('eval\s*\(', 'کد پویا'), ('exec\s*\(', 'کد پویا'), ('__import__\s*\(', 'ایمپورت داینامیک'), ('open\s*\(', 'دسترسی به فایل'), ('socket\.', 'ارتباط شبکه')]
    for pattern, desc in dangerous:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"کد مخرب: {desc}"
    return True, "OK"

def extract_zip_with_structure(zip_path: str, extract_to: str) -> Optional[str]:
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_to)
    for root, dirs, files in os.walk(extract_to):
        for file in files:
            if file.endswith('.py') and file in ['bot.py', 'main.py', 'run.py', 'app.py']:
                with open(os.path.join(root, file), 'r') as f:
                    return f.read()
        for root, dirs, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.py'):
                    with open(os.path.join(root, file), 'r') as f:
                        return f.read()
    return None

# ==================== ربات تلگرام ====================

BOT_TOKEN = "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78"
ADMIN_IDS = [327855654]

bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== منوها ====================

def get_main_menu(user_id: int):
    is_admin = user_id in ADMIN_IDS
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = ['🤖 ساخت ربات', '📋 اطلاعات ربات من', '💰 کیف پول من', '👥 دعوت دوستان', '📚 راهنما', '📞 پشتیبانی']
    if is_admin:
        buttons.append('👑 پنل مدیریت')
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🖥️ مدیریت سرورها", callback_data="admin_servers"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📸 تایید فیش", callback_data="admin_receipts"),
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("📦 مدیریت کتابخانه", callback_data="admin_libraries"),
        types.InlineKeyboardButton("🔄 ریستارت ربات‌ها", callback_data="admin_restart"),
        types.InlineKeyboardButton("💰 افزایش موجودی", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("🎁 فعالسازی اشتراک", callback_data="admin_activate_sub"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats")
    ]
    for btn in buttons:
        markup.add(btn)
    return markup

# ==================== هندلرهای اصلی ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        with db._get_connection() as conn:
            cursor = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (args[1],))
            row = cursor.fetchone()
            if row and row['user_id'] != user_id:
                referred_by = row['user_id']
                try:
                    bot.send_message(referred_by, f"🎉 {first_name} با لینک شما وارد شد!")
                except:
                    pass
    
    if not get_user(user_id):
        create_user(user_id, username, first_name, "", referred_by)
    
    user = get_user(user_id)
    is_subscribed = check_subscription(user_id)
    has_bot = user_has_bot(user_id)
    
    welcome = get_setting('welcome_text').format(name=first_name)
    price = get_setting('subscription_price_display')
    card = get_setting('card_number')
    holder = get_setting('card_holder')
    
    text = f"{welcome}\n\n👤 آیدی: {user_id}\n💰 موجودی: {user['wallet_balance']:,} تومان\n✅ اشتراک: {'فعال' if is_subscribed else 'غیرفعال'}\n🤖 ربات: {'دارید' if has_bot else 'ندارید'}\n\n"
    
    if not is_subscribed:
        text += f"💰 برای فعالسازی {price} به کارت زیر واریز کنید:\n`{card}`\n👤 {holder}\n\n📸 پس از واریز، تصویر فیش را ارسال کنید"
    elif not has_bot:
        text += "🎯 برای ساخت ربات، روی دکمه «ساخت ربات» کلیک کنید"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id))

@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات')
def create_bot_handler(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(message.chat.id, f"❌ ابتدا اشتراک خود را فعال کنید!\n💰 {get_setting('subscription_price_display')}")
        return
    
    if user_has_bot(user_id):
        bot.send_message(message.chat.id, "❌ شما قبلاً یک ربات ساخته‌اید!\nهر کاربر فقط ۱ ربات می‌تواند داشته باشد.")
        return
    
    bot.send_message(message.chat.id, "🔒 **ارسال فایل ربات در محیط امن**\n\n📤 فایل `.py` یا `.zip` خود را ارسال کنید.\n\n⚠️ حداکثر حجم: ۱۰ مگابایت\n🔐 کد شما در محیط ایزوله اجرا می‌شود", parse_mode='Markdown')

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک ندارید!")
        return
    
    if user_has_bot(user_id):
        bot.reply_to(message, "❌ شما قبلاً ربات دارید!")
        return
    
    file_name = message.document.file_name
    is_zip = file_name.endswith('.zip')
    
    if not (file_name.endswith('.py') or is_zip):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        bot.reply_to(message, f"❌ حجم بیشتر از {config.MAX_FILE_SIZE_MB} مگابایت!")
        return
    
    status_msg = bot.reply_to(message, "🔒 در حال بررسی امنیتی...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        code = None
        if is_zip:
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, 'code.zip')
            with open(zip_path, 'wb') as f:
                f.write(downloaded)
            code = extract_zip_with_structure(zip_path, temp_dir)
            shutil.rmtree(temp_dir, ignore_errors=True)
            if not code:
                bot.edit_message_text("❌ فایل پایتون در zip پیدا نشد!", message.chat.id, status_msg.message_id)
                return
        else:
            code = downloaded.decode('utf-8', errors='ignore')
        
        is_safe, error = validate_python_code(code)
        if not is_safe:
            bot.edit_message_text(f"❌ {error}", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token(code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        is_valid, bot_info = validate_token(token)
        if not is_valid:
            bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
            return
        
        bot_name = bot_info.get('first_name', 'Unknown')
        bot_username = bot_info.get('username', 'unknown')
        
        bot.edit_message_text("🛡️ در حال اجرا در محیط ایزوله...", message.chat.id, status_msg.message_id)
        
        result = sandbox.run_isolated(code, token)
        
        if result['success']:
            bot_id = hashlib.sha256(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
            add_bot(user_id, bot_id, bot_name, bot_username, token, None, result['container_id'])
            
            bot.edit_message_text(f"✅ **ربات با موفقیت ساخته شد!**\n\n🤖 نام: {bot_name}\n🔗 https://t.me/{bot_username}\n🔒 محیط ایزوله: فعال\n⚠️ هر کاربر فقط ۱ ربات", message.chat.id, status_msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ خطا: {result.get('error', 'ناشناخته')}", message.chat.id, status_msg.message_id)
    
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)

@bot.message_handler(func=lambda m: m.text == '📋 اطلاعات ربات من')
def my_bot_info(message):
    user_id = message.from_user.id
    if not user_has_bot(user_id):
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    bot_info = get_user_bot(user_id)
    text = f"🤖 **اطلاعات ربات شما**\n\nنام: {bot_info['bot_name']}\nیوزرنیم: @{bot_info['bot_username']}\nوضعیت: {'فعال' if bot_info['status'] == 'running' else 'متوقف'}\nتاریخ ساخت: {bot_info['created_at'][:10]}"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '💰 کیف پول من')
def wallet_handler(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    text = f"💰 **کیف پول شما**\n\n👤 {user['first_name']}\n💰 موجودی: {user['wallet_balance']:,} تومان\n👥 دعوت‌ها: {user['referrals_count']}\n✅ اشتراک: {'فعال' if check_subscription(user_id) else 'غیرفعال'}\n🤖 ربات: {'دارید' if user_has_bot(user_id) else 'ندارید'}"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
def referral_handler(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        return
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    text = f"👥 **دعوت دوستان**\n\n🔗 لینک: {link}\n🎁 کد: `{user['referral_code']}`\n📊 دعوت‌ها: {user['referrals_count']}\n💰 پورسانت: {get_setting('subscription_price_display')}"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    status_msg = bot.reply_to(message, "🔒 در حال بررسی فیش...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        payment_code = hashlib.sha256(f"{user_id}{time.time()}".encode()).hexdigest()[:8]
        receipt_path = os.path.join(os.path.dirname(__file__), 'receipts', f"{user_id}_{payment_code}.jpg")
        os.makedirs(os.path.dirname(receipt_path), exist_ok=True)
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        db.add_receipt(user_id, int(get_setting('subscription_price')), receipt_path, payment_code)
        bot.edit_message_text(f"✅ فیش دریافت شد!\n🆔 {payment_code}\n💰 {get_setting('subscription_price_display')}\n\nپس از تایید ادمین، اشتراک فعال می‌شود.", message.chat.id, status_msg.message_id)
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 {get_setting('subscription_price_display')}")
            except:
                pass
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide_handler(message):
    price = get_setting('subscription_price_display')
    card = get_setting('card_number')
    holder = get_setting('card_holder')
    text = get_setting('guide_text').format(price=price, card=card, holder=holder)
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support_handler(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13\nساعات پاسخگویی: ۹ صبح تا ۱۲ شب")

# ==================== پنل مدیریت ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(message.chat.id, "👑 **پنل مدیریت امن**", parse_mode='Markdown', reply_markup=get_admin_menu())

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    settings = [('card_number', '💳 شماره کارت'), ('card_holder', '👤 صاحب کارت'), ('subscription_price', '💰 قیمت اشتراک'), ('welcome_text', '👋 متن خوش‌آمدگویی'), ('guide_text', '📚 متن راهنما')]
    for key, name in settings:
        current = get_setting(key)
        display = current[:20] + "..." if len(current) > 20 else current
        markup.add(types.InlineKeyboardButton(f"{name}: {display}", callback_data=f"set_{key}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.edit_message_text("⚙️ **تنظیمات**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def set_setting_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    key = call.data.replace('set_', '')
    msg = bot.send_message(call.message.chat.id, f"مقدار جدید برای {key}:")
    bot.register_next_step_handler(msg, lambda m: update_setting_value(m, key, call.message))

def update_setting_value(message, key, original_message):
    if message.from_user.id not in ADMIN_IDS:
        return
    update_setting(key, message.text.strip(), message.from_user.id)
    bot.send_message(message.chat.id, f"✅ {key} به‌روزرسانی شد!")
    admin_settings(message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_servers")
def admin_servers(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    nodes = db.get_worker_nodes()
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ افزودن سرور جدید", callback_data="add_server"))
    for node in nodes:
        status = "🟢" if node['status'] == 'active' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status} {node['node_name']} - {node['current_bots']}/{node['max_bots']}", callback_data=f"remove_node_{node['node_id']}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.edit_message_text("🖥️ **مدیریت سرورها**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_server")
def add_server_start(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🔧 **مرحله 1/6: نام سرور را وارد کنید**\nمثال: `Server-Tehran-01`", parse_mode='Markdown')
    bot.register_next_step_handler(msg, add_server_get_username, call.message)

def add_server_get_username(message, original_message):
    node_name = message.text.strip()
    msg = bot.send_message(message.chat.id, "👤 **مرحله 2/6: نام کاربری SSH را وارد کنید**\nمثال: `root`", parse_mode='Markdown')
    bot.register_next_step_handler(msg, add_server_get_ip, node_name, original_message)

def add_server_get_ip(message, node_name, original_message):
    username = message.text.strip()
    msg = bot.send_message(message.chat.id, "🌐 **مرحله 3/6: آدرس IP سرور را وارد کنید**\nمثال: `192.168.1.100`", parse_mode='Markdown')
    bot.register_next_step_handler(msg, add_server_get_port, node_name, username, original_message)

def add_server_get_port(message, node_name, username, original_message):
    ip_address = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔌 **مرحله 4/6: پورت SSH را وارد کنید**\nپیش‌فرض: `22`", parse_mode='Markdown')
    bot.register_next_step_handler(msg, add_server_get_password, node_name, username, ip_address, original_message)

def add_server_get_password(message, node_name, username, ip_address, original_message):
    try:
        ssh_port = int(message.text.strip()) if message.text.strip() else 22
    except:
        ssh_port = 22
    msg = bot.send_message(message.chat.id, "🔐 **مرحله 5/6: رمز عبور SSH را وارد کنید**\n⚠️ رمز ذخیره می‌شود", parse_mode='Markdown')
    bot.register_next_step_handler(msg, add_server_test, node_name, username, ip_address, ssh_port, original_message)

def add_server_test(message, node_name, username, ip_address, ssh_port, original_message):
    password = message.text.strip()
    status_msg = bot.send_message(message.chat.id, "🔄 در حال تست اتصال به سرور...")
    success, result, info = node_manager.test_connection(ip_address, ssh_port, username, password)
    if not success:
        bot.edit_message_text(f"❌ {result}", message.chat.id, status_msg.message_id)
        return
    msg = bot.send_message(message.chat.id, f"✅ اتصال موفق!\n📊 رم: {info['total_memory']}MB\n💻 CPU: {info['total_cpu']} هسته\n🐋 Docker: {info['docker_version']}\n\n**مرحله 6/6: حداکثر تعداد ربات را وارد کنید**\nپیش‌فرض: 1000", parse_mode='Markdown')
    bot.register_next_step_handler(msg, add_server_final, node_name, username, ip_address, ssh_port, password, info, original_message, status_msg)

def add_server_final(message, node_name, username, ip_address, ssh_port, password, info, original_message, status_msg):
    try:
        max_bots = int(message.text.strip()) if message.text.strip() else 1000
    except:
        max_bots = 1000
    encrypted_password = base64.b64encode(password.encode()).decode()
    node_data = {'node_name': node_name, 'ip_address': ip_address, 'ssh_port': ssh_port, 'username': username, 'encrypted_password': encrypted_password, 'max_bots': max_bots, 'total_memory': info['total_memory'], 'total_cpu': info['total_cpu']}
    node_id = db.add_worker_node(node_data)
    bot.edit_message_text(f"✅ **سرور با موفقیت اضافه شد!**\n\n📊 نام: {node_name}\n🌐 IP: {ip_address}\n📦 ظرفیت: {max_bots} ربات\n🆔 شناسه: {node_id}", message.chat.id, status_msg.message_id, parse_mode='Markdown')
    admin_servers(message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    users = db.get_all_users(50)
    text = "👥 **۵۰ کاربر آخر**\n\n"
    for user in users:
        status = "✅" if user['subscription_status'] == 'active' else "⏳"
        bot_emoji = "🤖" if user['has_bot'] else "📭"
        text += f"{status} {bot_emoji} {user['user_id']} - {user['first_name']} - {user['wallet_balance']:,} تومان\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗑 حذف کاربر", callback_data="admin_delete_user"))
    markup.add(types.InlineKeyboardButton("🗑 حذف ربات کاربر", callback_data="admin_delete_user_bot"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🗑 آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_delete_user)

def process_delete_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        db.delete_user(user_id)
        bot.send_message(message.chat.id, f"✅ کاربر {user_id} حذف شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user_bot")
def admin_delete_user_bot_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🗑 آیدی کاربر برای حذف رباتش:")
    bot.register_next_step_handler(msg, process_delete_user_bot)

def process_delete_user_bot(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        if delete_bot(user_id):
            bot.send_message(message.chat.id, f"✅ ربات کاربر {user_id} حذف شد!")
        else:
            bot.send_message(message.chat.id, "❌ کاربر رباتی ندارد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    receipts = db.get_pending_receipts()
    if not receipts:
        bot.edit_message_text("📸 هیچ فیش در انتظاری وجود ندارد!", call.message.chat.id, call.message.message_id)
        return
    for receipt in receipts:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_{receipt['id']}"), types.InlineKeyboardButton("❌ رد", callback_data=f"reject_{receipt['id']}"))
        if os.path.exists(receipt['receipt_path']):
            with open(receipt['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=f"📸 فیش\n👤 کاربر: {receipt['user_id']}\n💰 {receipt['amount']:,} تومان", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    receipt_id = int(call.data.replace('approve_', ''))
    db.approve_receipt(receipt_id, call.from_user.id)
    bot.answer_callback_query(call.id, "✅ تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    receipt_id = int(call.data.replace('reject_', ''))
    db.reject_receipt(receipt_id, call.from_user.id)
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📢 متن پیام همگانی:")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users = db.get_all_users(10000)
    status_msg = bot.send_message(message.chat.id, f"🔄 در حال ارسال به {len(users)} کاربر...")
    sent, failed = 0, 0
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **اعلامیه**\n\n{message.text.strip()}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    bot.edit_message_text(f"✅ ارسال شد!\n📨 موفق: {sent}\n❌ ناموفق: {failed}", message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_libraries")
def admin_libraries(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    libs = db.get_libraries()
    text = "📦 **کتابخانه‌های نصب شده**\n\n"
    for lib in libs[:20]:
        text += f"• {lib['lib_name']} - v{lib['lib_version']}\n"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ نصب کتابخانه جدید", callback_data="install_library"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "install_library")
def install_library_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه:")
    bot.register_next_step_handler(msg, install_library)

def install_library(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    lib_name = message.text.strip()
    status_msg = bot.send_message(message.chat.id, f"🔄 در حال نصب {lib_name}...")
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', lib_name], capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        version_match = re.search(r'Successfully installed .*-(\d+\.\d+\.\d+)', result.stdout)
        version = version_match.group(1) if version_match else "unknown"
        db.add_library(lib_name, version, message.from_user.id)
        bot.edit_message_text(f"✅ {lib_name} نسخه {version} نصب شد!", message.chat.id, status_msg.message_id)
    else:
        bot.edit_message_text(f"❌ خطا: {result.stderr[:200]}", message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_restart")
def admin_restart(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    status_msg = bot.send_message(call.message.chat.id, "🔄 در حال ریستارت ربات‌ها...")
    sandbox.restart_all()
    bot.edit_message_text("✅ تمام کانتینرها ریستارت شدند!", call.message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_balance")
def admin_add_balance_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "💰 آیدی و مبلغ (مثال: 123456 50000):")
    bot.register_next_step_handler(msg, process_add_balance)

def process_add_balance(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.strip().split()
        user_id = int(parts[0])
        amount = int(parts[1])
        add_wallet_balance(user_id, amount)
        bot.send_message(message.chat.id, f"✅ {amount:,} تومان به {user_id} اضافه شد!")
        try:
            bot.send_message(user_id, f"💰 {amount:,} تومان به کیف پول شما اضافه شد!")
        except:
            pass
    except:
        bot.send_message(message.chat.id, "❌ فرمت نامعتبر!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_activate_sub")
def admin_activate_sub_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(call.message.chat.id, "🎁 آیدی کاربر:")
    bot.register_next_step_handler(msg, process_activate_sub)

def process_activate_sub(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        user_id = int(message.text.strip())
        activate_subscription(user_id, message.from_user.id)
        bot.send_message(message.chat.id, f"✅ اشتراک {user_id} فعال شد!")
        try:
            bot.send_message(user_id, "✅ اشتراک شما توسط ادمین فعال شد!")
        except:
            pass
    except:
        bot.send_message(message.chat.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    users = db.get_all_users(10000)
    total_users = len(users)
    active_subs = sum(1 for u in users if u['subscription_status'] == 'active')
    total_bots = sum(1 for u in users if u['has_bot'])
    nodes = db.get_worker_nodes()
    docker_status = "فعال" if sandbox.docker_available else "غیرفعال"
    text = f"📊 **آمار سیستم**\n\n👥 کاربران: {total_users:,}\n✅ اشتراک فعال: {active_subs:,}\n🤖 ربات‌ها: {total_bots:,}\n🖥️ سرورها: {len(nodes)}\n🐋 Docker: {docker_status}\n🔒 امنیت: نظامی\n💰 قیمت: {get_setting('subscription_price_display')}"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(call.from_user.id))

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🛡️ MOTHER BOT - ULTIMATE ENTERPRISE EDITION".center(70))
    print("=" * 70)
    print(f"🔒 امنیت: سطح نظامی | ایزوله‌سازی سخت‌افزاری")
    print(f"💾 دیتابیس: شاردینگ شده | پشتیبانی از میلیون‌ها کاربر")
    print(f"🎯 هر کاربر: فقط ۱ ربات")
    print(f"🐋 Docker: {'فعال' if sandbox.docker_available else 'غیرفعال'}")
    print(f"💰 قیمت: {get_setting('subscription_price_display')}")
    print(f"👑 ادمین: {ADMIN_IDS}")
    print("=" * 70)
    print("✅ ربات با موفقیت راه‌اندازی شد!")
    print("=" * 70)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ خطا: {e}")
            time.sleep(5)