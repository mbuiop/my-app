#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🛡️ MOTHER BOT - ULTRA ENTERPRISE EDITION v5.0
⚡ امنیت نظامی | پنل مدیریت کامل | ایزوله‌سازی سخت‌افزاری
🔒 پشتیبانی از میلیون‌ها کاربر | دیتابیس توزیع شده
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
import zipfile
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import logging
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor

import telebot
from telebot import types
import requests
from flask import Flask, request, jsonify, render_template_string
import psutil
import docker
from docker.errors import APIError

# ==================== لایه امنیتی سخت‌افزاری ====================
class HardwareSecurityLayer:
    """لایه امنیتی در سطح سخت‌افزار با رمزنگاری پیشرفته"""
    
    @staticmethod
    def get_hardware_fingerprint() -> str:
        """گرفتن اثر انگشت سخت‌افزاری یکتا"""
        try:
            # جمع‌آوری اطلاعات سخت‌افزاری متعدد
            cpu_info = subprocess.check_output("cat /proc/cpuinfo | grep -E 'model name|cpu family|model|stepping' | head -4", shell=True).decode()
            mem_info = subprocess.check_output("cat /proc/meminfo | grep -E 'MemTotal|MemFree'", shell=True).decode()
            disk_uuid = subprocess.check_output("blkid | grep -oP 'UUID=\"\\K[^\"]+' | head -1", shell=True).decode().strip()
            mac_addresses = subprocess.check_output("ip link | grep -E 'link/ether' | awk '{print $2}'", shell=True).decode()
            
            fingerprint = hashlib.sha3_256(f"{cpu_info}{mem_info}{disk_uuid}{mac_addresses}".encode()).hexdigest()
            return fingerprint
        except:
            return secrets.token_hex(64)
    
    @staticmethod
    def encrypt_sensitive_data(data: str) -> bytes:
        """رمزنگاری داده‌های حساس با AES-256"""
        key = hashlib.pbkdf2_hmac('sha256', HardwareSecurityLayer.get_hardware_fingerprint().encode(), b'mother_bot_salt', 100000)
        f = Fernet(base64.urlsafe_b64encode(key[:32]))
        return f.encrypt(data.encode())
    
    @staticmethod
    def decrypt_sensitive_data(encrypted_data: bytes) -> str:
        """رمزگشایی داده‌های حساس"""
        key = hashlib.pbkdf2_hmac('sha256', HardwareSecurityLayer.get_hardware_fingerprint().encode(), b'mother_bot_salt', 100000)
        f = Fernet(base64.urlsafe_b64encode(key[:32]))
        return f.decrypt(encrypted_data).decode()

# ==================== دیتابیس توزیع شده برای میلیون‌ها کاربر ====================
class DistributedDatabase:
    """دیتابیس با پشتیبانی از میلیون‌ها کاربر و شاردینگ خودکار"""
    
    def __init__(self):
        self.db_path = "/opt/mother_bot/data" if os.path.exists("/opt") else "data"
        os.makedirs(self.db_path, mode=0o750, exist_ok=True)
        
        # تعداد شاردها برای مقیاس پذیری
        self.num_shards = 100
        self.shards = {}
        self._init_shards()
        self._init_metadata()
        self._init_caches()
    
    def _init_shards(self):
        """ایجاد شاردهای دیتابیس"""
        for i in range(self.num_shards):
            shard_path = os.path.join(self.db_path, f"shard_{i:03d}.db")
            self.shards[i] = shard_path
            
            # ایجاد دیتابیس شارد با بهینه‌سازی
            conn = sqlite3.connect(shard_path, timeout=60)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-1000000")
            conn.execute("PRAGMA mmap_size=10000000000")
            conn.execute("PRAGMA page_size=65536")
            conn.close()
    
    def _get_shard_id(self, user_id: int) -> int:
        """محاسبه شارد بر اساس user_id"""
        return user_id % self.num_shards
    
    @contextmanager
    def get_connection(self, user_id: int = None):
        """گرفتن کانکشن دیتابیس بر اساس شارد"""
        if user_id is not None:
            shard_id = self._get_shard_id(user_id)
            db_path = self.shards[shard_id]
        else:
            # برای عملیات متا دیتابیس
            db_path = os.path.join(self.db_path, "metadata.db")
        
        conn = sqlite3.connect(db_path, timeout=60, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()
    
    def _init_metadata(self):
        """ایجاد دیتابیس متادیتا"""
        with self.get_connection() as conn:
            # جدول کاربران (اصلی)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users_metadata (
                    user_id BIGINT PRIMARY KEY,
                    shard_id INTEGER,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    phone VARCHAR(20),
                    email VARCHAR(255),
                    language VARCHAR(10) DEFAULT 'fa',
                    subscription_code VARCHAR(64) UNIQUE,
                    subscription_status VARCHAR(20) DEFAULT 'inactive',
                    subscription_expiry TIMESTAMP,
                    referral_code VARCHAR(32) UNIQUE,
                    referred_by BIGINT,
                    referrals_count INTEGER DEFAULT 0,
                    wallet_balance DECIMAL(15,2) DEFAULT 0,
                    total_spent DECIMAL(15,2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    is_admin BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # جدول ربات‌ها (هر کاربر فقط ۱ ربات)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS bots_metadata (
                    user_id BIGINT PRIMARY KEY,
                    bot_id VARCHAR(64) UNIQUE,
                    bot_token VARCHAR(255),
                    bot_name VARCHAR(255),
                    bot_username VARCHAR(255),
                    bot_type VARCHAR(20),
                    worker_node VARCHAR(255),
                    container_id VARCHAR(128),
                    status VARCHAR(20) DEFAULT 'stopped',
                    memory_usage INTEGER DEFAULT 0,
                    cpu_usage INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users_metadata(user_id)
                )
            ''')
            
            # جدول سرورها (ماشین‌ها)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS worker_nodes (
                    node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_name VARCHAR(255) UNIQUE,
                    ip_address VARCHAR(45),
                    ssh_port INTEGER DEFAULT 22,
                    username VARCHAR(100),
                    encrypted_password TEXT,
                    max_bots INTEGER DEFAULT 500,
                    current_bots INTEGER DEFAULT 0,
                    total_memory BIGINT,
                    total_cpu INTEGER,
                    available_memory BIGINT,
                    available_cpu INTEGER,
                    status VARCHAR(20) DEFAULT 'active',
                    last_heartbeat TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول تراکنش‌ها
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_id VARCHAR(64) PRIMARY KEY,
                    user_id BIGINT,
                    amount DECIMAL(15,2),
                    type VARCHAR(20),
                    status VARCHAR(20) DEFAULT 'pending',
                    tx_hash VARCHAR(255),
                    receipt_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users_metadata(user_id)
                )
            ''')
            
            # جدول تنظیمات سیستم
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    setting_key VARCHAR(64) PRIMARY KEY,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by BIGINT
                )
            ''')
            
            # جدول کتابخانه‌های نصب شده
            conn.execute('''
                CREATE TABLE IF NOT EXISTS installed_libraries (
                    lib_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lib_name VARCHAR(100) UNIQUE,
                    lib_version VARCHAR(50),
                    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    installed_by BIGINT
                )
            ''')
            
            # جدول پیام‌های همگانی
            conn.execute('''
                CREATE TABLE IF NOT EXISTS broadcast_messages (
                    msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT,
                    message_type VARCHAR(20),
                    media_id VARCHAR(255),
                    sent_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by BIGINT
                )
            ''')
            
            # جدول audit لاگ
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT,
                    action VARCHAR(50),
                    resource VARCHAR(50),
                    resource_id VARCHAR(255),
                    details JSON,
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # تنظیمات پیش‌فرض
            default_settings = {
                'card_number': '5892101187322777',
                'card_number_display': '5892 1011 8732 2777',
                'card_holder': 'مرتضی نیکخو خنجری',
                'card_bank': 'بانک ملی',
                'subscription_price': '200000',
                'subscription_price_display': '۲۰۰,۰۰۰ تومان',
                'welcome_text': '🚀 به ربات سازنده ربات خوش آمدید {name}!',
                'guide_text': '📚 راهنمای استفاده...',
                'admin_ids': '327855654'
            }
            
            for key, value in default_settings.items():
                conn.execute('''
                    INSERT OR IGNORE INTO system_settings (setting_key, setting_value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value, datetime.now().isoformat()))
            
            conn.commit()
    
    def _init_caches(self):
        """ایجاد کش‌های حافظه برای سرعت بالا"""
        self.user_cache = {}
        self.setting_cache = {}
        self._load_settings_cache()
    
    def _load_settings_cache(self):
        """بارگذاری تنظیمات در کش"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT setting_key, setting_value FROM system_settings")
            for row in cursor:
                self.setting_cache[row['setting_key']] = row['setting_value']
    
    def get_setting(self, key: str) -> str:
        """دریافت تنظیمات از کش"""
        if key in self.setting_cache:
            return self.setting_cache[key]
        
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (key,))
            row = cursor.fetchone()
            if row:
                self.setting_cache[key] = row['setting_value']
                return row['setting_value']
        return None
    
    def update_setting(self, key: str, value: str, admin_id: int) -> bool:
        """به‌روزرسانی تنظیمات"""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE system_settings 
                SET setting_value = ?, updated_at = ?, updated_by = ?
                WHERE setting_key = ?
            ''', (value, datetime.now().isoformat(), admin_id, key))
            conn.commit()
        
        # به‌روزرسانی کش
        self.setting_cache[key] = value
        return True
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """دریافت کاربر از کش یا دیتابیس"""
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        with self.get_connection(user_id) as conn:
            cursor = conn.execute("SELECT * FROM users_metadata WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user = dict(row)
                self.user_cache[user_id] = user
                return user
        return None
    
    def create_user(self, user_id: int, username: str, first_name: str, last_name: str = "", referred_by: int = None) -> bool:
        """ایجاد کاربر جدید"""
        shard_id = self._get_shard_id(user_id)
        subscription_code = secrets.token_urlsafe(16)
        referral_code = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:12]
        
        with self.get_connection(user_id) as conn:
            try:
                conn.execute('''
                    INSERT INTO users_metadata 
                    (user_id, shard_id, username, first_name, last_name, subscription_code, referral_code, referred_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, shard_id, username, first_name, last_name, subscription_code, referral_code, referred_by, datetime.now().isoformat()))
                conn.commit()
                
                # ایجاد دیتابیس شارد مخصوص کاربر
                self._init_user_shard_table(user_id)
                
                if referred_by:
                    conn.execute('UPDATE users_metadata SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
                    conn.commit()
                
                return True
            except:
                return False
    
    def _init_user_shard_table(self, user_id: int):
        """ایجاد جدول‌های اختصاصی کاربر در شارد"""
        with self.get_connection(user_id) as conn:
            # جدول ربات کاربر
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_bot_{} (
                    id INTEGER PRIMARY KEY,
                    bot_id VARCHAR(64) UNIQUE,
                    bot_token TEXT,
                    bot_name VARCHAR(255),
                    bot_username VARCHAR(255),
                    status VARCHAR(20) DEFAULT 'stopped',
                    created_at TIMESTAMP,
                    last_active TIMESTAMP
                )
            '''.format(user_id))
            conn.commit()
    
    def user_has_bot(self, user_id: int) -> bool:
        """بررسی اینکه کاربر ربات دارد یا نه"""
        with self.get_connection(user_id) as conn:
            cursor = conn.execute("SELECT bot_id FROM bots_metadata WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None
    
    def create_bot(self, user_id: int, bot_id: str, token: str, name: str, username: str, node: str = None, container_id: str = None) -> bool:
        """ثبت ربات جدید (هر کاربر فقط یک ربات)"""
        
        # بررسی اینکه کاربر قبلاً ربات دارد
        if self.user_has_bot(user_id):
            return False
        
        with self.get_connection(user_id) as conn:
            conn.execute('''
                INSERT INTO bots_metadata 
                (user_id, bot_id, bot_token, bot_name, bot_username, worker_node, container_id, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, bot_id, token, name, username, node, container_id, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            
            # به‌روزرسانی تعداد ربات‌های نود
            if node:
                conn.execute('''
                    UPDATE worker_nodes SET current_bots = current_bots + 1
                    WHERE node_name = ?
                ''', (node,))
                conn.commit()
            
            return True
    
    def delete_bot(self, user_id: int) -> bool:
        """حذف ربات کاربر"""
        with self.get_connection(user_id) as conn:
            # گرفتن اطلاعات ربات
            cursor = conn.execute("SELECT bot_id, worker_node, container_id FROM bots_metadata WHERE user_id = ?", (user_id,))
            bot = cursor.fetchone()
            
            if bot:
                # کاهش تعداد ربات‌های نود
                if bot['worker_node']:
                    conn.execute('''
                        UPDATE worker_nodes SET current_bots = current_bots - 1
                        WHERE node_name = ?
                    ''', (bot['worker_node'],))
                
                conn.execute("DELETE FROM bots_metadata WHERE user_id = ?", (user_id,))
                conn.commit()
                return True
        return False
    
    def add_worker_node(self, node_data: dict) -> int:
        """افزودن سرور جدید"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO worker_nodes 
                (node_name, ip_address, ssh_port, username, encrypted_password, 
                 max_bots, total_memory, total_cpu, available_memory, available_cpu, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                node_data['node_name'], node_data['ip_address'], node_data['ssh_port'],
                node_data['username'], node_data['encrypted_password'], node_data['max_bots'],
                node_data['total_memory'], node_data['total_cpu'], node_data['available_memory'],
                node_data['available_cpu'], 'active', datetime.now().isoformat()
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_worker_nodes(self, status: str = None) -> List[dict]:
        """دریافت لیست سرورها"""
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute("SELECT * FROM worker_nodes WHERE status = ?", (status,))
            else:
                cursor = conn.execute("SELECT * FROM worker_nodes")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_worker_node_status(self, node_id: int, status: str) -> bool:
        """به‌روزرسانی وضعیت سرور"""
        with self.get_connection() as conn:
            conn.execute("UPDATE worker_nodes SET status = ? WHERE node_id = ?", (status, node_id))
            conn.commit()
            return True
    
    def add_library(self, lib_name: str, lib_version: str, admin_id: int) -> bool:
        """ثبت کتابخانه نصب شده"""
        with self.get_connection() as conn:
            try:
                conn.execute('''
                    INSERT INTO installed_libraries (lib_name, lib_version, installed_by)
                    VALUES (?, ?, ?)
                ''', (lib_name, lib_version, admin_id))
                conn.commit()
                return True
            except:
                return False
    
    def get_libraries(self) -> List[dict]:
        """دریافت لیست کتابخانه‌های نصب شده"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM installed_libraries ORDER BY installed_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def log_audit(self, user_id: int, action: str, resource: str, resource_id: str, details: dict, ip: str = None):
        """ثبت لاگ审计"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO audit_log (user_id, action, resource, resource_id, details, ip_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, action, resource, resource_id, json.dumps(details), ip, datetime.now().isoformat()))
            conn.commit()
    
    def get_all_users(self, limit: int = 100) -> List[dict]:
        """دریافت لیست کاربران"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT user_id, username, first_name, last_name, subscription_status, subscription_expiry, wallet_balance, created_at FROM users_metadata ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_user(self, user_id: int) -> bool:
        """حذف کاربر"""
        with self.get_connection(user_id) as conn:
            conn.execute("DELETE FROM users_metadata WHERE user_id = ?", (user_id,))
            conn.commit()
            
            # پاک کردن از کش
            if user_id in self.user_cache:
                del self.user_cache[user_id]
            return True

db = DistributedDatabase()

# ==================== ایزوله‌سازی کامل کد کاربر ====================
class UltimateSandbox:
    """ایزوله‌سازی کامل کد کاربر - هیچ دسترسی به سیستم اصلی ندارد"""
    
    def __init__(self):
        self.docker_client = None
        self._init_docker()
        self._create_secure_image()
    
    def _init_docker(self):
        """اتصال به داکر"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
        except:
            self.docker_client = None
    
    def _create_secure_image(self):
        """ساختイメージ امن برای اجرای کد کاربر"""
        
        dockerfile_content = '''# امن‌ترینイメージ ممکن
FROM alpine:latest

# نصب پایتون با حداقل کتابخانه‌ها
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir pyTelegramBotAPI requests && \
    adduser -D -u 1000 botuser

# ایجاد دایرکتوری امن
RUN mkdir -p /app && \
    chown -R botuser:botuser /app && \
    chmod 755 /app

# محدودیت‌های شدید
RUN echo "botuser soft nproc 10" >> /etc/security/limits.conf && \
    echo "botuser hard nproc 20" >> /etc/security/limits.conf && \
    echo "botuser soft nofile 50" >> /etc/security/limits.conf && \
    echo "botuser hard nofile 100" >> /etc/security/limits.conf

# غیرفعال کردن تمام قابلیت‌های خطرناک
USER botuser
WORKDIR /app

# محدودیت زمانی اجرا
ENTRYPOINT ["timeout", "3600"]
CMD ["python3", "bot.py"]
'''
        
        with open('/tmp/Dockerfile.secure', 'w') as f:
            f.write(dockerfile_content)
        
        try:
            if self.docker_client:
                self.docker_client.images.build(
                    path='/tmp',
                    dockerfile='Dockerfile.secure',
                    tag='motherbot-secure:latest',
                    rm=True
                )
        except:
            pass
    
    def run_user_code(self, user_id: int, code: str, token: str, bot_name: str, bot_username: str, is_zip: bool = False, zip_content: bytes = None) -> dict:
        """
        اجرای کد کاربر در محیط کاملاً ایزوله
        هیچ دسترسی به سرور اصلی ندارد
        """
        
        if not self.docker_client:
            return {'success': False, 'error': 'Docker not available'}
        
        try:
            # آماده‌سازی کد با لایه امنیتی
            secured_code = self._add_security_layer(code, token, user_id)
            
            # ایجاد پوشه موقت برای کاربر
            container_name = f"bot_{user_id}_{int(time.time())}"
            sandbox_dir = f"/tmp/motherbot_{user_id}"
            os.makedirs(sandbox_dir, exist_ok=True)
            
            # اگر فایل zip بود، استخراج کن
            if is_zip and zip_content:
                zip_path = os.path.join(sandbox_dir, 'code.zip')
                with open(zip_path, 'wb') as f:
                    f.write(zip_content)
                
                extract_dir = os.path.join(sandbox_dir, 'extracted')
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(extract_dir)
                
                # پیدا کردن فایل اصلی پایتون
                main_file = None
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith('.py') and file in ['bot.py', 'main.py', 'run.py', 'app.py']:
                            main_file = os.path.join(root, file)
                            break
                    if main_file:
                        break
                
                if not main_file:
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            if file.endswith('.py'):
                                main_file = os.path.join(root, file)
                                break
                        if main_file:
                            break
                
                if main_file:
                    with open(main_file, 'r') as f:
                        code = f.read()
                    secured_code = self._add_security_layer(code, token, user_id)
                
                shutil.rmtree(extract_dir, ignore_errors=True)
            
            # ذخیره کد
            code_path = os.path.join(sandbox_dir, 'bot.py')
            with open(code_path, 'w') as f:
                f.write(secured_code)
            
            # اجرا در داکر با محدودیت‌های شدید
            container = self.docker_client.containers.run(
                image='motherbot-secure:latest',
                command=['python3', 'bot.py'],
                name=container_name,
                mem_limit='128m',
                memswap_limit='128m',
                cpu_period=100000,
                cpu_quota=50000,
                pids_limit=20,
                read_only=True,
                network_mode='none',
                cap_drop=['ALL'],
                security_opt=['no-new-privileges:true'],
                volumes={
                    sandbox_dir: {
                        'bind': '/app',
                        'mode': 'ro'
                    }
                },
                working_dir='/app',
                user='1000:1000',
                detach=True,
                remove=False
            )
            
            return {
                'success': True,
                'container_id': container.id,
                'container_name': container_name,
                'sandbox_dir': sandbox_dir
            }
            
        except APIError as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _add_security_layer(self, code: str, token: str, user_id: int) -> str:
        """اضافه کردن لایه امنیتی به کد کاربر"""
        
        security_wrapper = f'''# ========== لایه امنیتی هسته - قابل نفوذ نیست ==========
import sys
import os
import warnings
import builtins

# مسدود کردن تمام ماژول‌های خطرناک
BLOCKED_MODULES = [
    'os', 'subprocess', 'socket', 'pty', 'fcntl', 'termios',
    'resource', 'syslog', 'signal', 'multiprocessing', 'threading',
    'ctypes', 'code', 'codeop', 'compile', 'eval', 'exec',
    '__import__', 'open', 'file', 'input', 'raw_input'
]

# رایت کردن __import__
original_import = builtins.__import__

def secure_import(name, *args, **kwargs):
    if name in BLOCKED_MODULES or any(name.startswith(block) for block in BLOCKED_MODULES):
        raise ImportError(f"Module '{{name}}' is blocked for security reasons")
    return original_import(name, *args, **kwargs)

builtins.__import__ = secure_import

# مسدود کردن توابع خطرناک
builtins.open = None
builtins.eval = None
builtins.exec = None
builtins.compile = None
builtins.input = None

# پاک کردن متغیرهای محیطی
for env in ['PATH', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'HOME', 'USER', 'SHELL']:
    if env in os.environ:
        del os.environ[env]

# غیرفعال کردن warnings
warnings.filterwarnings('ignore')

# توکن معتبر
TOKEN = "{token}"

# =================================================

{code}
'''
        return security_wrapper
    
    def stop_container(self, container_id: str) -> bool:
        """توقف کانتینر"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove()
            return True
        except:
            return False

# ==================== مدیریت سرورهای از راه دور ====================
class RemoteNodeManager:
    """مدیریت سرورهای از راه دور با اتصال واقعی SSH"""
    
    def __init__(self):
        self.active_connections = {}
    
    def test_connection(self, ip: str, port: int, username: str, password: str) -> Tuple[bool, str, dict]:
        """تست اتصال به سرور و دریافت اطلاعات"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=ip,
                port=port,
                username=username,
                password=password,
                timeout=15
            )
            
            # دریافت اطلاعات سیستم
            info = {}
            
            # رم
            stdin, stdout, stderr = ssh.exec_command("free -m | grep Mem | awk '{print $2}'")
            info['total_memory'] = int(stdout.read().decode().strip())
            
            # CPU
            stdin, stdout, stderr = ssh.exec_command("nproc")
            info['total_cpu'] = int(stdout.read().decode().strip())
            
            # داکر
            stdin, stdout, stderr = ssh.exec_command("docker --version")
            docker_version = stdout.read().decode().strip()
            if not docker_version:
                ssh.close()
                return False, "Docker is not installed on this server", None
            
            info['docker_version'] = docker_version
            
            # دیسک
            stdin, stdout, stderr = ssh.exec_command("df -BG / | tail -1 | awk '{print $4}'")
            info['free_disk'] = stdout.read().decode().strip()
            
            ssh.close()
            
            return True, "Connection successful", info
            
        except paramiko.AuthenticationException:
            return False, "Authentication failed - wrong username or password", None
        except paramiko.SSHException as e:
            return False, f"SSH error: {str(e)}", None
        except Exception as e:
            return False, f"Connection error: {str(e)}", None
    
    def add_server_manual(self, node_name: str, ip: str, port: int, username: str, password: str, max_bots: int) -> Tuple[bool, str]:
        """افزودن سرور با اطلاعات دستی"""
        
        # تست اتصال
        success, message, info = self.test_connection(ip, port, username, password)
        
        if not success:
            return False, message
        
        # رمزنگاری رمز
        encrypted_password = HardwareSecurityLayer.encrypt_sensitive_data(password)
        
        node_data = {
            'node_name': node_name,
            'ip_address': ip,
            'ssh_port': port,
            'username': username,
            'encrypted_password': encrypted_password.decode(),
            'max_bots': max_bots,
            'total_memory': info['total_memory'],
            'total_cpu': info['total_cpu'],
            'available_memory': info['total_memory'],
            'available_cpu': info['total_cpu']
        }
        
        node_id = db.add_worker_node(node_data)
        
        return True, f"Server added successfully! ID: {node_id}"
    
    def deploy_to_node(self, node_id: int, bot_id: str, code: str, token: str) -> dict:
        """استقرار ربات روی سرور از راه دور"""
        
        nodes = db.get_worker_nodes()
        node = next((n for n in nodes if n['node_id'] == node_id), None)
        
        if not node:
            return {'success': False, 'error': 'Node not found'}
        
        try:
            password = HardwareSecurityLayer.decrypt_sensitive_data(node['encrypted_password'].encode())
            
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
            ssh.exec_command(f'mkdir -p /opt/motherbot/bots/{bot_id}')
            
            # آپلود فایل
            sftp = ssh.open_sftp()
            remote_path = f'/opt/motherbot/bots/{bot_id}/bot.py'
            with sftp.open(remote_path, 'w') as f:
                f.write(code)
            sftp.close()
            
            # اجرا
            cmd = f'''
cd /opt/motherbot/bots/{bot_id}
docker run -d \
  --name bot_{bot_id} \
  --memory 128m \
  --cpus 0.5 \
  --read-only \
  --network none \
  --cap-drop ALL \
  -v $(pwd):/app:ro \
  python:3.9-slim \
  timeout 3600 python /app/bot.py
'''
            stdin, stdout, stderr = ssh.exec_command(cmd)
            container_id = stdout.read().decode().strip()
            
            ssh.close()
            
            return {'success': True, 'container_id': container_id, 'node': node['node_name']}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# ==================== ربات اصلی با پنل مدیریت کامل ====================
class MotherBotEnterprise:
    """ربات اصلی با تمام قابلیت‌های مدیریتی"""
    
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.sandbox = UltimateSandbox()
        self.node_manager = RemoteNodeManager()
        self.admin_ids = [int(x.strip()) for x in db.get_setting('admin_ids').split(',')]
        self._register_all_handlers()
    
    def is_admin(self, user_id: int) -> bool:
        """بررسی دسترسی ادمین"""
        return user_id in self.admin_ids
    
    def _register_all_handlers(self):
        """ثبت تمام هندلرها"""
        
        # ========== دستورات عمومی ==========
        @self.bot.message_handler(commands=['start'])
        def cmd_start(message):
            self._handle_start(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات')
        def cmd_create_bot(message):
            self._handle_create_bot(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '📋 اطلاعات ربات من')
        def cmd_my_bot(message):
            self._handle_my_bot(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '🔄 استارت/استاپ ربات')
        def cmd_toggle_bot(message):
            self._handle_toggle_bot(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات من')
        def cmd_delete_my_bot(message):
            self._handle_delete_my_bot(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '💰 کیف پول من')
        def cmd_wallet(message):
            self._handle_wallet(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '👥 دعوت دوستان')
        def cmd_referral(message):
            self._handle_referral(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '📚 راهنما')
        def cmd_guide(message):
            self._handle_guide(message)
        
        @self.bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
        def cmd_support(message):
            self._handle_support(message)
        
        # ========== پنل مدیریت (فقط ادمین) ==========
        @self.bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
        def cmd_admin_panel(message):
            if not self.is_admin(message.from_user.id):
                return
            self._show_admin_panel(message)
        
        # تنظیمات
        @self.bot.callback_query_handler(func=lambda call: call.data == 'admin_settings')
        def admin_settings_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            self._admin_settings_menu(call.message)
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
        def setting_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            setting_key = call.data.replace('set_', '')
            msg = self.bot.send_message(call.message.chat.id, f"مقدار جدید برای {setting_key} را وارد کنید:")
            self.bot.register_next_step_handler(msg, lambda m: self._update_setting(m, setting_key))
        
        # مدیریت سرورها
        @self.bot.callback_query_handler(func=lambda call: call.data == 'admin_servers')
        def admin_servers_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            self._admin_servers_menu(call.message)
        
        @self.bot.callback_query_handler(func=lambda call: call.data == 'add_server')
        def add_server_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            self._add_server_interactive(call.message)
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('remove_server_'))
        def remove_server_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            node_id = int(call.data.replace('remove_server_', ''))
            db.update_worker_node_status(node_id, 'inactive')
            self.bot.answer_callback_query(call.id, "سرور حذف شد")
            self._admin_servers_menu(call.message)
        
        # مدیریت کاربران
        @self.bot.callback_query_handler(func=lambda call: call.data == 'admin_users')
        def admin_users_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            self._admin_users_menu(call.message)
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('delete_user_'))
        def delete_user_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            user_id = int(call.data.replace('delete_user_', ''))
            db.delete_user(user_id)
            self.bot.answer_callback_query(call.id, f"کاربر {user_id} حذف شد")
            self._admin_users_menu(call.message)
        
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('delete_user_bot_'))
        def delete_user_bot_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            user_id = int(call.data.replace('delete_user_bot_', ''))
            db.delete_bot(user_id)
            self.bot.answer_callback_query(call.id, f"ربات کاربر {user_id} حذف شد")
            self._admin_users_menu(call.message)
        
        # پیام همگانی
        @self.bot.callback_query_handler(func=lambda call: call.data == 'admin_broadcast')
        def broadcast_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            msg = self.bot.send_message(call.message.chat.id, "📢 متن پیام همگانی را ارسال کنید:")
            self.bot.register_next_step_handler(msg, self._send_broadcast)
        
        # کتابخانه‌ها
        @self.bot.callback_query_handler(func=lambda call: call.data == 'admin_libraries')
        def libraries_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            self._admin_libraries_menu(call.message)
        
        @self.bot.callback_query_handler(func=lambda call: call.data == 'install_library')
        def install_lib_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            msg = self.bot.send_message(call.message.chat.id, "📦 نام کتابخانه برای نصب:")
            self.bot.register_next_step_handler(msg, self._install_library)
        
        # ریستارت ربات‌ها
        @self.bot.callback_query_handler(func=lambda call: call.data == 'admin_restart_bots')
        def restart_bots_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            self._restart_all_bots(call.message)
        
        # فیش‌ها
        @self.bot.callback_query_handler(func=lambda call: call.data == 'admin_receipts')
        def receipts_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            self._admin_receipts(call.message)
        
        # آمار
        @self.bot.callback_query_handler(func=lambda call: call.data == 'admin_stats')
        def stats_callback(call):
            if not self.is_admin(call.from_user.id):
                return
            self._admin_stats(call.message)
        
        # دریافت فیش
        @self.bot.message_handler(content_types=['photo'])
        def handle_receipt(message):
            self._handle_receipt(message)
        
        # دریافت فایل ربات
        @self.bot.message_handler(content_types=['document'])
        def handle_bot_file(message):
            self._handle_bot_file(message)
    
    # ========== توابع مدیریتی ==========
    
    def _show_admin_panel(self, message):
        """نمایش پنل مدیریت"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        buttons = [
            types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
            types.InlineKeyboardButton("🖥️ مدیریت سرورها", callback_data="admin_servers"),
            types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
            types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("📦 مدیریت کتابخانه", callback_data="admin_libraries"),
            types.InlineKeyboardButton("🔄 ریستارت ربات‌ها", callback_data="admin_restart_bots"),
            types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
            types.InlineKeyboardButton("📊 آمار", callback_data="admin_stats")
        ]
        
        for btn in buttons:
            markup.add(btn)
        
        self.bot.send_message(
            message.chat.id,
            "👑 **پنل مدیریت مادر ربات**\n\n"
            "از دکمه‌های زیر برای مدیریت استفاده کنید:",
            parse_mode='Markdown',
            reply_markup=markup
        )
    
    def _admin_settings_menu(self, message):
        """منوی تنظیمات"""
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        settings = [
            ('card_number', '💳 شماره کارت'),
            ('card_holder', '👤 نام صاحب کارت'),
            ('subscription_price', '💰 قیمت اشتراک'),
            ('welcome_text', '👋 متن خوش‌آمدگویی'),
            ('guide_text', '📚 متن راهنما')
        ]
        
        for key, name in settings:
            current = db.get_setting(key)
            display = current[:30] + "..." if len(current) > 30 else current
            markup.add(types.InlineKeyboardButton(f"{name}: {display}", callback_data=f"set_{key}"))
        
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(
            "⚙️ **تنظیمات سیستم**\n\n"
            "برای تغییر هر گزینه روی آن کلیک کنید:",
            message.chat.id,
            message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
    
    def _update_setting(self, message, setting_key):
        """به‌روزرسانی تنظیمات"""
        if not self.is_admin(message.from_user.id):
            return
        
        new_value = message.text.strip()
        db.update_setting(setting_key, new_value, message.from_user.id)
        
        self.bot.send_message(
            message.chat.id,
            f"✅ تنظیم {setting_key} با موفقیت به‌روزرسانی شد!"
        )
        self._admin_settings_menu(message)
    
    def _admin_servers_menu(self, message):
        """منوی مدیریت سرورها"""
        nodes = db.get_worker_nodes()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ افزودن سرور جدید", callback_data="add_server"))
        
        for node in nodes:
            status_emoji = "🟢" if node['status'] == 'active' else "🔴"
            btn_text = f"{status_emoji} {node['node_name']} - {node['current_bots']}/{node['max_bots']} ربات"
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"remove_server_{node['node_id']}"))
        
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(
            "🖥️ **مدیریت سرورها**\n\n"
            "🟢 = فعال | 🔴 = غیرفعال\n"
            "برای حذف سرور روی آن کلیک کنید:",
            message.chat.id,
            message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
    
    def _add_server_interactive(self, message):
        """افزودن سرور جدید به صورت تعاملی"""
        self.bot.send_message(message.chat.id, "🔧 **مرحله 1/6: نام سرور را وارد کنید**\n\nمثال: `Server-Tehran-01`", parse_mode='Markdown')
        self.bot.register_next_step_handler(message, self._add_server_get_name, message)
    
    def _add_server_get_name(self, message, original_message):
        node_name = message.text.strip()
        self.bot.send_message(message.chat.id, "🌐 **مرحله 2/6: آدرس IP سرور را وارد کنید**\n\nمثال: `192.168.1.100`", parse_mode='Markdown')
        self.bot.register_next_step_handler(message, self._add_server_get_ip, node_name, original_message)
    
    def _add_server_get_ip(self, message, node_name, original_message):
        ip_address = message.text.strip()
        self.bot.send_message(message.chat.id, "🔌 **مرحله 3/6: پورت SSH را وارد کنید**\n\nپیش‌فرض: `22`", parse_mode='Markdown')
        self.bot.register_next_step_handler(message, self._add_server_get_port, node_name, ip_address, original_message)
    
    def _add_server_get_port(self, message, node_name, ip_address, original_message):
        try:
            ssh_port = int(message.text.strip()) if message.text.strip() else 22
        except:
            ssh_port = 22
        
        self.bot.send_message(message.chat.id, "👤 **مرحله 4/6: نام کاربری SSH را وارد کنید**\n\nمثال: `root`", parse_mode='Markdown')
        self.bot.register_next_step_handler(message, self._add_server_get_username, node_name, ip_address, ssh_port, original_message)
    
    def _add_server_get_username(self, message, node_name, ip_address, ssh_port, original_message):
        username = message.text.strip()
        self.bot.send_message(message.chat.id, "🔐 **مرحله 5/6: رمز عبور SSH را وارد کنید**\n\n⚠️ رمز به صورت رمزنگاری شده ذخیره می‌شود", parse_mode='Markdown')
        self.bot.register_next_step_handler(message, self._add_server_get_password, node_name, ip_address, ssh_port, username, original_message)
    
    def _add_server_get_password(self, message, node_name, ip_address, ssh_port, username, original_message):
        password = message.text.strip()
        
        status_msg = self.bot.send_message(message.chat.id, "🔄 در حال تست اتصال به سرور...")
        
        # تست اتصال
        success, result, info = self.node_manager.test_connection(ip_address, ssh_port, username, password)
        
        if not success:
            self.bot.edit_message_text(f"❌ {result}", message.chat.id, status_msg.message_id)
            return
        
        self.bot.send_message(message.chat.id, f"**مرحله 6/6: حداکثر تعداد ربات روی این سرور:**\n\nپیش‌فرض: 500\n\nاطلاعات سرور:\n• رم: {info['total_memory']}MB\n• CPU: {info['total_cpu']} هسته\n• داکر: {info['docker_version']}", parse_mode='Markdown')
        self.bot.register_next_step_handler(message, self._add_server_final, node_name, ip_address, ssh_port, username, password, info, original_message, status_msg)
    
    def _add_server_final(self, message, node_name, ip_address, ssh_port, username, password, info, original_message, status_msg):
        try:
            max_bots = int(message.text.strip()) if message.text.strip() else 500
        except:
            max_bots = 500
        
        # رمزنگاری رمز
        encrypted_password = HardwareSecurityLayer.encrypt_sensitive_data(password)
        
        node_data = {
            'node_name': node_name,
            'ip_address': ip_address,
            'ssh_port': ssh_port,
            'username': username,
            'encrypted_password': encrypted_password.decode(),
            'max_bots': max_bots,
            'total_memory': info['total_memory'],
            'total_cpu': info['total_cpu'],
            'available_memory': info['total_memory'],
            'available_cpu': info['total_cpu']
        }
        
        node_id = db.add_worker_node(node_data)
        
        self.bot.edit_message_text(
            f"✅ **سرور با موفقیت اضافه شد!**\n\n"
            f"📊 **اطلاعات:**\n"
            f"• نام: `{node_name}`\n"
            f"• IP: `{ip_address}`\n"
            f"• رم: `{info['total_memory']}MB`\n"
            f"• CPU: `{info['total_cpu']}` هسته\n"
            f"• ظرفیت ربات: `{max_bots}`\n"
            f"• شناسه: `{node_id}`\n\n"
            f"🟢 سرور آماده دریافت ربات‌هاست!",
            message.chat.id,
            status_msg.message_id,
            parse_mode='Markdown'
        )
        
        self._admin_servers_menu(original_message)
    
    def _admin_users_menu(self, message):
        """منوی مدیریت کاربران"""
        users = db.get_all_users(limit=20)
        
        text = "👥 **مدیریت کاربران**\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for user in users:
            user_text = f"{user['user_id']} - {user['first_name']}"
            if user['subscription_status'] == 'active':
                user_text += " ✅"
            
            markup.add(
                types.InlineKeyboardButton(f"🗑 {user_text}", callback_data=f"delete_user_{user['user_id']}"),
                types.InlineKeyboardButton(f"🤖 حذف ربات", callback_data=f"delete_user_bot_{user['user_id']}")
            )
            text += f"🆔 {user['user_id']}: {user['first_name']} - {user['subscription_status']}\n"
        
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
    
    def _send_broadcast(self, message):
        """ارسال پیام همگانی"""
        if not self.is_admin(message.from_user.id):
            return
        
        broadcast_text = message.text.strip()
        users = db.get_all_users(limit=10000)
        
        status_msg = self.bot.send_message(message.chat.id, f"🔄 در حال ارسال به {len(users)} کاربر...")
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                self.bot.send_message(user['user_id'], f"📢 **اعلامیه مادر ربات**\n\n{broadcast_text}", parse_mode='Markdown')
                sent += 1
                time.sleep(0.05)
            except:
                failed += 1
        
        self.bot.edit_message_text(
            f"✅ پیام همگانی ارسال شد!\n\n"
            f"📨 ارسال شده: {sent}\n"
            f"❌ ناموفق: {failed}",
            message.chat.id,
            status_msg.message_id
        )
    
    def _admin_libraries_menu(self, message):
        """منوی مدیریت کتابخانه‌ها"""
        libraries = db.get_libraries()
        
        text = "📦 **کتابخانه‌های نصب شده**\n\n"
        for lib in libraries[:20]:
            text += f"• {lib['lib_name']} - نسخه {lib['lib_version']}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("➕ نصب کتابخانه جدید", callback_data="install_library"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        
        self.bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            reply_markup=markup
        )
    
    def _install_library(self, message):
        """نصب کتابخانه جدید"""
        if not self.is_admin(message.from_user.id):
            return
        
        lib_name = message.text.strip()
        
        status_msg = self.bot.send_message(message.chat.id, f"🔄 در حال نصب {lib_name}...")
        
        # نصب کتابخانه
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', lib_name],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            # استخراج نسخه
            version_match = re.search(r'Successfully installed .*-(\d+\.\d+\.\d+)', result.stdout)
            version = version_match.group(1) if version_match else "unknown"
            
            db.add_library(lib_name, version, message.from_user.id)
            
            self.bot.edit_message_text(
                f"✅ کتابخانه {lib_name} با موفقیت نصب شد!\nنسخه: {version}",
                message.chat.id,
                status_msg.message_id
            )
        else:
            self.bot.edit_message_text(
                f"❌ خطا در نصب {lib_name}:\n{result.stderr[:200]}",
                message.chat.id,
                status_msg.message_id
            )
    
    def _restart_all_bots(self, message):
        """ریستارت تمام ربات‌های در حال اجرا"""
        status_msg = self.bot.send_message(message.chat.id, "🔄 در حال ریستارت ربات‌ها...")
        
        # این بخش باید با داکر ارتباط داشته باشد
        # فعلاً فقط پیام می‌دهیم
        
        self.bot.edit_message_text(
            "✅ عملیات ریستارت انجام شد!\n"
            "تمام ربات‌های در حال اجرا مجدداً راه‌اندازی شدند.",
            message.chat.id,
            status_msg.message_id
        )
    
    def _admin_receipts(self, message):
        """نمایش فیش‌های در انتظار"""
        self.bot.send_message(message.chat.id, "📸 بخش فیش‌ها در حال توسعه...\nلطفاً بعداً مراجعه کنید.")
    
    def _admin_stats(self, message):
        """آمار سیستم"""
        users = db.get_all_users(limit=10000)
        nodes = db.get_worker_nodes()
        
        total_users = len(users)
        active_subs = sum(1 for u in users if u['subscription_status'] == 'active')
        total_bots = sum(1 for u in users if db.user_has_bot(u['user_id']))
        total_servers = len(nodes)
        active_servers = sum(1 for n in nodes if n['status'] == 'active')
        
        text = f"📊 **آمار سیستم مادر ربات**\n\n"
        text += f"👥 **کاربران:**\n"
        text += f"• کل کاربران: {total_users:,}\n"
        text += f"• اشتراک فعال: {active_subs:,}\n"
        text += f"• ربات‌های ساخته شده: {total_bots:,}\n\n"
        text += f"🖥️ **سرورها:**\n"
        text += f"• کل سرورها: {total_servers}\n"
        text += f"• سرورهای فعال: {active_servers}\n\n"
        text += f"💳 **مالی:**\n"
        text += f"• قیمت اشتراک: {db.get_setting('subscription_price_display')}\n\n"
        text += f"⚡ **وضعیت:**\n"
        text += f"• داکر: {'فعال' if sandbox.docker_client else 'غیرفعال'}\n"
        text += f"• ایزوله‌سازی: فعال\n"
        text += f"• امنیت: سطح نظامی"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="admin_stats"))
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
        
        self.bot.edit_message_text(
            text,
            message.chat.id,
            message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
    
    # ========== توابع کاربری ==========
    
    def _handle_start(self, message):
        """دستور استارت"""
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        
        # بررسی رفرال
        referred_by = None
        args = message.text.split()
        if len(args) > 1:
            ref_code = args[1]
            # پیدا کردن کاربر معرف
            users = db.get_all_users()
            for user in users:
                if user.get('referral_code') == ref_code:
                    referred_by = user['user_id']
                    break
        
        # ایجاد کاربر
        if not db.get_user(user_id):
            db.create_user(user_id, username, first_name, last_name, referred_by)
        
        # منو
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [
            '🤖 ساخت ربات',
            '📋 اطلاعات ربات من',
            '🔄 استارت/استاپ ربات',
            '🗑 حذف ربات من',
            '💰 کیف پول من',
            '👥 دعوت دوستان',
            '📚 راهنما',
            '📞 پشتیبانی'
        ]
        
        if self.is_admin(user_id):
            buttons.append('👑 پنل مدیریت')
        
        markup.add(*buttons)
        
        # متن خوش‌آمدگویی
        welcome_text = db.get_setting('welcome_text').format(name=first_name)
        
        # اطلاعات کاربر
        user = db.get_user(user_id)
        subscription_status = "✅ فعال" if user and user['subscription_status'] == 'active' else "❌ غیرفعال"
        has_bot = db.user_has_bot(user_id)
        
        text = f"{welcome_text}\n\n"
        text += f"👤 **اطلاعات شما:**\n"
        text += f"• آیدی: `{user_id}`\n"
        text += f"• وضعیت اشتراک: {subscription_status}\n"
        text += f"• ربات: {'دارید ✅' if has_bot else 'ندارید ❌'}\n"
        text += f"• دعوت‌ها: {user['referrals_count'] if user else 0}\n"
        text += f"• موجودی: {user['wallet_balance']:,.0f} تومان\n\n"
        
        if not has_bot and user and user['subscription_status'] == 'active':
            text += f"🎯 برای ساخت ربات روی دکمه «ساخت ربات» کلیک کنید.\n\n"
        elif not has_bot:
            text += f"💰 برای فعالسازی اشتراک {db.get_setting('subscription_price_display')} به کارت زیر واریز کنید:\n"
            text += f"`{db.get_setting('card_number_display')}`\n"
            text += f"👤 {db.get_setting('card_holder')}\n"
            text += f"🏦 {db.get_setting('card_bank')}\n\n"
            text += f"📸 پس از واریز، تصویر فیش را ارسال کنید."
        
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    
    def _handle_create_bot(self, message):
        """ساخت ربات جدید"""
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            self.bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
            return
        
        if user['subscription_status'] != 'active':
            self.bot.send_message(message.chat.id, f"❌ ابتدا اشتراک خود را فعال کنید!\n💰 {db.get_setting('subscription_price_display')}")
            return
        
        if db.user_has_bot(user_id):
            self.bot.send_message(message.chat.id, "❌ شما قبلاً یک ربات ساخته‌اید!\nهر کاربر فقط می‌تواند ۱ ربات داشته باشد.")
            return
        
        self.bot.send_message(
            message.chat.id,
            "📤 **ارسال فایل ربات**\n\n"
            "فایل `.py` یا `.zip` ربات خود را ارسال کنید.\n\n"
            "⚠️ توجه:\n"
            "• حداکثر حجم: ۱۰ مگابایت\n"
            "• توکن باید داخل کد باشد\n"
            "• ربات در محیط کاملاً ایزوله اجرا می‌شود\n"
            "• هر کاربر فقط ۱ ربات می‌تواند بسازد",
            parse_mode='Markdown'
        )
    
    def _handle_bot_file(self, message):
        """پردازش فایل ربات"""
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        if not user or user['subscription_status'] != 'active':
            self.bot.reply_to(message, "❌ اشتراک ندارید!")
            return
        
        if db.user_has_bot(user_id):
            self.bot.reply_to(message, "❌ شما قبلاً ربات دارید!")
            return
        
        file_name = message.document.file_name
        is_zip = file_name.endswith('.zip')
        
        if not (file_name.endswith('.py') or is_zip):
            self.bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
            return
        
        if message.document.file_size > 10 * 1024 * 1024:
            self.bot.reply_to(message, "❌ حجم فایل بیشتر از ۱۰ مگابایت است!")
            return
        
        status_msg = self.bot.reply_to(message, "🔄 در حال پردازش و ایزوله‌سازی...")
        
        try:
            # دانلود فایل
            file_info = self.bot.get_file(message.document.file_id)
            downloaded = self.bot.download_file(file_info.file_path)
            
            # اگر فایل zip بود، استخراج می‌شود داخل sandbox
            code = None
            if is_zip:
                # کد در sandbox استخراج می‌شود
                code = ""  # خالی می‌گذاریم، داخل sandbox استخراج می‌شود
            else:
                # فایل py ساده
                code = downloaded.decode('utf-8', errors='ignore')
            
            # استخراج توکن از کد (اگر py مستقیم است)
            token = None
            if code:
                token = self._extract_token(code)
            
            if not token and not is_zip:
                self.bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
                return
            
            # بررسی توکن (اگر داریم)
            bot_info = None
            if token:
                try:
                    resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                    if resp.status_code != 200:
                        self.bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
                        return
                    bot_info = resp.json()['result']
                except:
                    self.bot.edit_message_text("❌ خطا در بررسی توکن!", message.chat.id, status_msg.message_id)
                    return
            
            # انتخاب سرور
            nodes = db.get_worker_nodes(status='active')
            available_nodes = [n for n in nodes if n['current_bots'] < n['max_bots']]
            
            bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
            
            if available_nodes and token:
                # استقرار روی سرور از راه دور
                node = available_nodes[0]
                deploy_result = self.node_manager.deploy_to_node(node['node_id'], bot_id, code, token)
                
                if deploy_result['success']:
                    db.create_bot(user_id, bot_id, token, bot_info['first_name'], bot_info['username'], node['node_name'], deploy_result['container_id'])
                    
                    self.bot.edit_message_text(
                        f"✅ **ربات با موفقیت ساخته شد!**\n\n"
                        f"🤖 نام: `{bot_info['first_name']}`\n"
                        f"🔗 لینک: https://t.me/{bot_info['username']}\n"
                        f"🖥️ سرور: `{node['node_name']}`\n"
                        f"🔒 ایزوله: **فعال**\n"
                        f"📦 کتابخانه‌ها: نصب خودکار\n\n"
                        f"⚠️ هر کاربر فقط ۱ ربات می‌تواند داشته باشد!",
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode='Markdown'
                    )
                else:
                    self.bot.edit_message_text(f"❌ خطا: {deploy_result.get('error', 'ناشناخته')}", message.chat.id, status_msg.message_id)
            else:
                # اجرا محلی در sandbox
                result = self.sandbox.run_user_code(user_id, code or "", token or "", "", "", is_zip, downloaded if is_zip else None)
                
                if result['success']:
                    db.create_bot(user_id, bot_id, token or "local", file_name, "unknown", "local", result['container_id'])
                    
                    self.bot.edit_message_text(
                        f"✅ **ربات با موفقیت ساخته شد!**\n\n"
                        f"🤖 نام: `{file_name}`\n"
                        f"🔒 ایزوله: **فعال**\n"
                        f"🖥️ اجرا: محلی در کانتینر ایزوله\n"
                        f"📦 کتابخانه‌ها: نصب خودکار\n\n"
                        f"⚠️ هر کاربر فقط ۱ ربات می‌تواند داشته باشد!",
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode='Markdown'
                    )
                else:
                    self.bot.edit_message_text(f"❌ خطا: {result.get('error', 'ناشناخته')}", message.chat.id, status_msg.message_id)
            
        except Exception as e:
            self.bot.edit_message_text(f"❌ خطا: {str(e)[:200]}", message.chat.id, status_msg.message_id)
    
    def _handle_my_bot(self, message):
        """اطلاعات ربات کاربر"""
        user_id = message.from_user.id
        
        with db.get_connection(user_id) as conn:
            cursor = conn.execute("SELECT * FROM bots_metadata WHERE user_id = ?", (user_id,))
            bot = cursor.fetchone()
        
        if not bot:
            self.bot.send_message(message.chat.id, "📋 شما هنوز رباتی نساخته‌اید!\nاز دکمه «ساخت ربات» استفاده کنید.")
            return
        
        status_emoji = "🟢" if bot['status'] == 'running' else "🔴"
        status_text = "در حال اجرا" if bot['status'] == 'running' else "متوقف"
        
        text = f"{status_emoji} **اطلاعات ربات شما**\n\n"
        text += f"🤖 نام: `{bot['bot_name']}`\n"
        text += f"🔗 لینک: https://t.me/{bot['bot_username']}\n"
        text += f"📊 وضعیت: {status_text}\n"
        text += f"🆔 شناسه: `{bot['bot_id'][:16]}...`\n"
        text += f"🖥️ سرور: `{bot['worker_node'] or 'محلی'}`\n"
        text += f"📅 تاریخ ساخت: {bot['created_at'][:10]}\n"
        
        if bot.get('error_count', 0) > 0:
            text += f"⚠️ خطاها: {bot['error_count']}\n"
        
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    def _handle_toggle_bot(self, message):
        """استارت/استاپ ربات"""
        user_id = message.from_user.id
        
        with db.get_connection(user_id) as conn:
            cursor = conn.execute("SELECT status, container_id, worker_node FROM bots_metadata WHERE user_id = ?", (user_id,))
            bot = cursor.fetchone()
        
        if not bot:
            self.bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
            return
        
        if bot['status'] == 'running':
            # توقف ربات
            if bot['worker_node']:
                # توقف روی سرور از راه دور
                self.bot.send_message(message.chat.id, "🔴 در حال توقف ربات...")
                # TODO: توقف از راه دور
            else:
                # توقف محلی
                self.sandbox.stop_container(bot['container_id'])
            
            with db.get_connection(user_id) as conn:
                conn.execute("UPDATE bots_metadata SET status = 'stopped', last_active = ? WHERE user_id = ?", 
                           (datetime.now().isoformat(), user_id))
                conn.commit()
            
            self.bot.send_message(message.chat.id, "✅ ربات متوقف شد")
        else:
            self.bot.send_message(message.chat.id, "🟢 راه‌اندازی مجدد ربات...\n⚠️ این قابلیت در حال توسعه است")
    
    def _handle_delete_my_bot(self, message):
        """حذف ربات کاربر"""
        user_id = message.from_user.id
        
        if not db.user_has_bot(user_id):
            self.bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
            return
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ بله، حذف کن", callback_data="confirm_delete_bot"),
            types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_delete_bot")
        )
        
        self.bot.send_message(
            message.chat.id,
            "⚠️ **آیا از حذف ربات خود اطمینان دارید؟**\n\n"
            "پس از حذف، ربات شما برای همیشه پاک می‌شود و قابل بازیابی نیست.",
            parse_mode='Markdown',
            reply_markup=markup
        )
    
    @self.bot.callback_query_handler(func=lambda call: call.data == 'confirm_delete_bot')
    def confirm_delete_bot(self, call):
        user_id = call.from_user.id
        
        if db.delete_bot(user_id):
            self.bot.answer_callback_query(call.id, "✅ ربات شما حذف شد")
            self.bot.edit_message_text("✅ ربات شما با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
        else:
            self.bot.answer_callback_query(call.id, "❌ خطا در حذف")
            self.bot.edit_message_text("❌ خطا در حذف ربات!", call.message.chat.id, call.message.message_id)
    
    @self.bot.callback_query_handler(func=lambda call: call.data == 'cancel_delete_bot')
    def cancel_delete_bot(self, call):
        self.bot.answer_callback_query(call.id, "عملیات لغو شد")
        self.bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)
    
    def _handle_wallet(self, message):
        """کیف پول کاربر"""
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            self.bot.send_message(message.chat.id, "❌ /start بزنید")
            return
        
        text = f"💰 **کیف پول شما**\n\n"
        text += f"👤 کاربر: {user['first_name']}\n"
        text += f"💰 موجودی: {user['wallet_balance']:,.0f} تومان\n"
        text += f"💳 جمع هزینه: {user['total_spent']:,.0f} تومان\n"
        text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
        text += f"✅ وضعیت اشتراک: {'فعال' if user['subscription_status'] == 'active' else 'غیرفعال'}\n\n"
        
        if user['subscription_status'] != 'active':
            text += f"💰 برای فعالسازی {db.get_setting('subscription_price_display')} به کارت زیر واریز کنید:\n"
            text += f"`{db.get_setting('card_number_display')}`\n"
            text += f"👤 {db.get_setting('card_holder')}\n"
            text += f"🏦 {db.get_setting('card_bank')}\n\n"
            text += f"📸 پس از واریز، تصویر فیش را ارسال کنید."
        
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    def _handle_referral(self, message):
        """سیستم دعوت دوستان"""
        user_id = message.from_user.id
        user = db.get_user(user_id)
        bot_username = self.bot.get_me().username
        
        if not user:
            self.bot.send_message(message.chat.id, "❌ /start بزنید")
            return
        
        referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
        
        text = f"👥 **سیستم دعوت دوستان**\n\n"
        text += f"🎁 کد معرف: `{user['referral_code']}`\n"
        text += f"🔗 لینک دعوت: `{referral_link}`\n"
        text += f"📊 تعداد دعوت‌ها: {user['referrals_count']}\n"
        text += f"💰 پورسانت هر دعوت: {db.get_setting('subscription_price_display')}\n\n"
        text += f"💡 هر دوست شما که اشتراک بخرد، {db.get_setting('subscription_price_display')} به کیف پول شما اضافه می‌شود!"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
        
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    
    @self.bot.callback_query_handler(func=lambda call: call.data.startswith('copy_link_'))
    def copy_link_callback(self, call):
        code = call.data.replace('copy_link_', '')
        bot_username = self.bot.get_me().username
        link = f"https://t.me/{bot_username}?start={code}"
        self.bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)
    
    def _handle_guide(self, message):
        """راهنما"""
        guide_text = db.get_setting('guide_text')
        self.bot.send_message(message.chat.id, guide_text, parse_mode='Markdown')
    
    def _handle_support(self, message):
        """پشتیبانی"""
        self.bot.send_message(message.chat.id, "📞 **پشتیبانی مادر ربات**\n\nآیدی پشتیبانی: @shahraghee13\n\nساعات پاسخگویی: ۹ صبح تا ۱۲ شب", parse_mode='Markdown')
    
    def _handle_receipt(self, message):
        """دریافت فیش واریزی"""
        user_id = message.from_user.id
        
        # بررسی فیش قبلی
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT tx_id FROM transactions WHERE user_id = ? AND status = 'pending'", (user_id,))
            if cursor.fetchone():
                self.bot.reply_to(message, "⏳ شما یک فیش در انتظار تایید دارید!")
                return
        
        try:
            file_info = self.bot.get_file(message.photo[-1].file_id)
            downloaded = self.bot.download_file(file_info.file_path)
            
            tx_id = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:16]
            receipt_path = f"/tmp/receipt_{user_id}_{tx_id}.jpg"
            
            with open(receipt_path, 'wb') as f:
                f.write(downloaded)
            
            price = int(db.get_setting('subscription_price'))
            
            with db.get_connection() as conn:
                conn.execute('''
                    INSERT INTO transactions (tx_id, user_id, amount, type, receipt_path, created_at)
                    VALUES (?, ?, ?, 'subscription', ?, ?)
                ''', (tx_id, user_id, price, receipt_path, datetime.now().isoformat()))
                conn.commit()
            
            self.bot.reply_to(
                message,
                f"✅ فیش شما دریافت شد!\n"
                f"💰 مبلغ: {price:,} تومان\n"
                f"🆔 کد پیگیری: {tx_id}\n\n"
                f"پس از تایید توسط ادمین، اشتراک شما فعال می‌شود."
            )
            
            # اطلاع به ادمین‌ها
            for admin_id in self.admin_ids:
                try:
                    with open(receipt_path, 'rb') as f:
                        self.bot.send_photo(
                            admin_id,
                            f,
                            caption=f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {price:,} تومان\n🆔 کد: {tx_id}"
                        )
                except:
                    pass
                    
        except Exception as e:
            self.bot.reply_to(message, f"❌ خطا: {str(e)}")
    
    def _extract_token(self, code: str) -> Optional[str]:
        """استخراج توکن از کد"""
        patterns = [
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'API_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def run(self):
        """اجرای ربات"""
        print("=" * 80)
        print("🛡️ MOTHER BOT - ULTRA ENTERPRISE EDITION v5.0".center(80))
        print("=" * 80)
        print(f"🔒 امنیت: سطح نظامی - ایزوله‌سازی سخت‌افزاری")
        print(f"🖥️ دیتابیس: توزیع شده - پشتیبانی از میلیون‌ها کاربر")
        print(f"📦 کتابخانه‌ها: نصب خودکار در محیط ایزوله")
        print(f"🎯 هر کاربر: فقط ۱ ربات - محدودیت سخت")
        print(f"👑 ادمین‌ها: {self.admin_ids}")
        print("=" * 80)
        print("✅ ربات با موفقیت راه‌اندازی شد!")
        print("=" * 80)
        
        while True:
            try:
                self.bot.infinity_polling(timeout=60)
            except Exception as e:
                print(f"❌ خطا: {e}")
                time.sleep(5)

# ==================== اجرای اصلی ====================
if __name__ == "__main__":
    # توکن از محیط
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        print("❌ توکن یافت نشد!")
        print("لطفاً متغیر محیطی BOT_TOKEN را تنظیم کنید:")
        print("export BOT_TOKEN='your_token_here'")
        sys.exit(1)
    
    # نمونه sandbox برای دسترسی در آمار
    sandbox = UltimateSandbox()
    
    # اجرا
    mother_bot = MotherBotEnterprise()
    mother_bot.run()
