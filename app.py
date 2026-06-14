#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر نهایی نسخه 11.0 - نهایی، کامل، فوق‌امن
==================================================
✅ دیتابیس شارد شده برای میلیون‌ها کاربر
✅ هر کاربر فقط ۱ ربات می‌تواند بسازد
✅ پنل ادمین کامل با ۱۵ گزینه مختلف
✅ اضافه کردن سرور واقعی با SSH (Username/IP/Password)
✅ ایزوله‌سازی کامل کد کاربر در Docker روی سرورهای جداگانه
✅ کد مخرب هیچ اثری روی سرور اصلی نمی‌گذارد
✅ پشتیبانی از فایل .py و .zip
✅ امنیت فوق‌العاده بالا
"""

import telebot
from telebot import types
import sqlite3
import os
import sys
import time
import json
import threading
import shutil
import re
import zipfile
import secrets
import logging
import hashlib
import subprocess
import paramiko
import requests
import signal
import tempfile
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor

# ============================================================
#                     تنظیمات پایه
# ============================================================
BASE_DIR = Path(__file__).parent.absolute()
DB_DIR = BASE_DIR / "database"
FILES_DIR = BASE_DIR / "user_files"
LOGS_DIR = BASE_DIR / "logs"
RECEIPTS_DIR = BASE_DIR / "receipts"
SERVERS_DIR = BASE_DIR / "servers"
TEMP_DIR = BASE_DIR / "temp"
META_DIR = BASE_DIR / "meta"
BACKUP_DIR = BASE_DIR / "backups"

for d in [DB_DIR, FILES_DIR, LOGS_DIR, RECEIPTS_DIR, SERVERS_DIR, TEMP_DIR, META_DIR, BACKUP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# توکن ربات مادر
BOT_TOKEN = "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo"
ADMIN_IDS = [327855654]

# لاگینگ پیشرفته
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'mother_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
#               دیتابیس شارد شده پیشرفته
# ============================================================
class ShardManager:
    """مدیریت شاردهای دیتابیس - پشتیبانی از میلیون‌ها کاربر"""
    
    def __init__(self, base_dir: Path, shard_size: int = 100000):
        self.base_dir = base_dir
        self.shard_size = shard_size
        self.connections: Dict[str, sqlite3.Connection] = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._init_meta_db()
    
    def _init_meta_db(self):
        """دیتابیس متا برای مدیریت شاردها"""
        self.meta_conn = sqlite3.connect(str(META_DIR / "meta.db"), timeout=30, check_same_thread=False)
        self.meta_conn.row_factory = sqlite3.Row
        
        # جدول شاردها
        self.meta_conn.execute('''
            CREATE TABLE IF NOT EXISTS shards (
                shard_id INTEGER PRIMARY KEY,
                shard_name TEXT,
                user_count INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_updated TIMESTAMP
            )
        ''')
        
        # جدول تنظیمات全局
        self.meta_conn.execute('''
            CREATE TABLE IF NOT EXISTS global_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # جدول سرورها
        self.meta_conn.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                username TEXT,
                password TEXT,
                port INTEGER DEFAULT 22,
                max_bots INTEGER DEFAULT 10,
                current_bots INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP,
                last_check TIMESTAMP
            )
        ''')
        
        # جدول آمار
        self.meta_conn.execute('''
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_users INTEGER,
                total_bots INTEGER,
                total_payments INTEGER,
                active_servers INTEGER,
                recorded_at TIMESTAMP
            )
        ''')
        
        self.meta_conn.commit()
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'card_number': '5892101187322777',
            'card_holder': 'مرتضی نیکخو خنجری',
            'price': '2000000',
            'welcome_text': '🚀 به ربات مادر نهایی خوش آمدید!\n\nهر کاربر فقط ۱ ربات می‌تواند بسازد.\nبرای ساخت ربات ابتدا هزینه را پرداخت کنید.',
            'help_text': '📚 راهنمای استفاده:\n\n1️⃣ مبلغ را به کارت زیر واریز کنید\n2️⃣ تصویر فیش را ارسال کنید\n3️⃣ پس از تایید، فایل ربات را ارسال کنید\n\n📞 پشتیبانی: @shahraghee13',
            'max_bots_per_user': '1'
        }
        
        now = datetime.now().isoformat()
        for key, value in default_settings.items():
            self.meta_conn.execute(
                'INSERT OR IGNORE INTO global_settings (key, value, updated_at) VALUES (?, ?, ?)',
                (key, value, now)
            )
        self.meta_conn.commit()
    
    def _get_shard_id(self, user_id: int) -> int:
        return user_id // self.shard_size
    
    def _get_shard_path(self, user_id: int) -> Path:
        shard_id = self._get_shard_id(user_id)
        return self.base_dir / f"shard_{shard_id}.db"
    
    def _get_connection(self, user_id: int) -> sqlite3.Connection:
        shard_path = self._get_shard_path(user_id)
        with self.lock:
            if str(shard_path) not in self.connections:
                conn = sqlite3.connect(str(shard_path), timeout=30, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                self.connections[str(shard_path)] = conn
                self._init_shard(conn)
                
                # به‌روزرسانی آمار شارد
                shard_id = self._get_shard_id(user_id)
                self.meta_conn.execute('''
                    INSERT OR IGNORE INTO shards (shard_id, shard_name, created_at, last_updated)
                    VALUES (?, ?, ?, ?)
                ''', (shard_id, shard_path.name, datetime.now().isoformat(), datetime.now().isoformat()))
                self.meta_conn.commit()
            return self.connections[str(shard_path)]
    
    def _init_shard(self, conn: sqlite3.Connection):
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance INTEGER DEFAULT 0,
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 1,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                payment_status TEXT DEFAULT 'pending',
                payment_date TIMESTAMP,
                payment_code TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                server_id INTEGER,
                server_ip TEXT,
                container_id TEXT,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER,
                payment_code TEXT UNIQUE
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        conn.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON bots(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_payment_status ON users(payment_status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_referral_code ON users(referral_code)')
        conn.commit()
    
    def execute(self, user_id: int, query: str, params: tuple = ()):
        conn = self._get_connection(user_id)
        return conn.execute(query, params)
    
    def execute_meta(self, query: str, params: tuple = ()):
        return self.meta_conn.execute(query, params)
    
    def commit(self, user_id: int):
        conn = self._get_connection(user_id)
        conn.commit()
    
    def commit_meta(self):
        self.meta_conn.commit()
    
    def get_setting(self, key: str) -> str:
        row = self.meta_conn.execute('SELECT value FROM global_settings WHERE key = ?', (key,)).fetchone()
        return row['value'] if row else None
    
    def set_setting(self, key: str, value: str):
        self.meta_conn.execute(
            'INSERT OR REPLACE INTO global_settings (key, value, updated_at) VALUES (?, ?, ?)',
            (key, value, datetime.now().isoformat())
        )
        self.meta_conn.commit()
    
    def get_all_users(self):
        """Generator برای دریافت همه کاربران از همه شاردها"""
        for shard_file in self.base_dir.glob("shard_*.db"):
            conn = sqlite3.connect(str(shard_file), timeout=10)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT user_id, first_name, username FROM users')
            for row in cursor:
                yield dict(row)
            conn.close()
    
    def get_total_users(self) -> int:
        total = 0
        for shard_file in self.base_dir.glob("shard_*.db"):
            conn = sqlite3.connect(str(shard_file), timeout=10)
            count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            total += count
            conn.close()
        return total
    
    def get_total_bots(self) -> int:
        total = 0
        for shard_file in self.base_dir.glob("shard_*.db"):
            conn = sqlite3.connect(str(shard_file), timeout=10)
            count = conn.execute('SELECT COUNT(*) FROM bots').fetchone()[0]
            total += count
            conn.close()
        return total
    
    def get_pending_receipts(self) -> List[dict]:
        receipts = []
        for shard_file in self.base_dir.glob("shard_*.db"):
            conn = sqlite3.connect(str(shard_file), timeout=10)
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at DESC').fetchall()
            for row in rows:
                receipts.append(dict(row))
            conn.close()
        return receipts
    
    def close_all(self):
        for conn in self.connections.values():
            conn.close()
        self.meta_conn.close()

db = ShardManager(DB_DIR, shard_size=100000)

# ============================================================
#                 مدیریت سرورهای خارجی
# ============================================================
@dataclass
class ServerInfo:
    id: int
    name: str
    ip: str
    username: str
    password: str
    port: int
    max_bots: int
    current_bots: int
    status: str

class ServerManager:
    def __init__(self):
        self.servers: List[ServerInfo] = []
        self.lock = threading.Lock()
        self.load_servers()
    
    def load_servers(self):
        try:
            rows = db.execute_meta('SELECT * FROM servers WHERE status = "active"').fetchall()
            with self.lock:
                self.servers = []
                for row in rows:
                    self.servers.append(ServerInfo(
                        id=row['id'],
                        name=row['name'],
                        ip=row['ip'],
                        username=row['username'],
                        password=row['password'],
                        port=row['port'],
                        max_bots=row['max_bots'],
                        current_bots=row['current_bots'],
                        status=row['status']
                    ))
        except Exception as e:
            logger.error(f"خطا در بارگذاری سرورها: {e}")
    
    def add_server(self, name: str, ip: str, username: str, password: str, port: int = 22, max_bots: int = 10) -> bool:
        try:
            now = datetime.now().isoformat()
            db.execute_meta('''
                INSERT INTO servers (name, ip, username, password, port, max_bots, current_bots, status, created_at, last_check)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, ip, username, password, port, max_bots, 0, 'active', now, now))
            db.commit_meta()
            self.load_servers()
            return True
        except Exception as e:
            logger.error(f"خطا در افزودن سرور: {e}")
            return False
    
    def remove_server(self, server_id: int) -> bool:
        try:
            db.execute_meta('UPDATE servers SET status = "deleted" WHERE id = ?', (server_id,))
            db.commit_meta()
            self.load_servers()
            return True
        except:
            return False
    
    def update_server_bots_count(self, server_id: int, delta: int):
        try:
            db.execute_meta('UPDATE servers SET current_bots = current_bots + ? WHERE id = ?', (delta, server_id))
            db.commit_meta()
            self.load_servers()
        except:
            pass
    
    def get_available_server(self) -> Optional[ServerInfo]:
        with self.lock:
            available = [s for s in self.servers if s.status == 'active' and s.current_bots < s.max_bots]
            if not available:
                return None
            # انتخاب سرور با کمترین بار
            return min(available, key=lambda s: s.current_bots)
    
    def test_connection(self, server: ServerInfo) -> Tuple[bool, str]:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=server.ip,
                port=server.port,
                username=server.username,
                password=server.password,
                timeout=10
            )
            # بررسی Docker
            stdin, stdout, stderr = ssh.exec_command('docker --version')
            docker_check = stdout.read().decode().strip()
            ssh.close()
            if 'Docker' in docker_check:
                return True, f"✅ اتصال برقرار - {docker_check}"
            else:
                return True, "✅ اتصال برقرار (Docker نصب نیست)"
        except Exception as e:
            return False, f"❌ خطا: {str(e)}"
    
    def deploy_bot_on_server(self, server: ServerInfo, bot_id: str, code: str, token: str) -> Tuple[Optional[str], str]:
        """استقرار ربات روی سرور با ایزوله‌سازی کامل"""
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=server.ip,
                port=server.port,
                username=server.username,
                password=server.password,
                timeout=15
            )
            
            remote_dir = f"/opt/bots/{bot_id}"
            ssh.exec_command(f"sudo mkdir -p {remote_dir}")
            time.sleep(1)
            
            # آپلود کد
            sftp = ssh.open_sftp()
            remote_file = f"{remote_dir}/bot.py"
            with sftp.open(remote_file, 'w') as f:
                f.write(code)
            
            # ایجاد Dockerfile با ایزوله‌سازی کامل
            dockerfile = f'''FROM python:3.10-slim

# ایجاد کاربر غیر root
RUN useradd -m -s /bin/bash botuser && \\
    mkdir -p /app && \\
    chown -R botuser:botuser /app

WORKDIR /app
COPY bot.py .

# نصب کتابخانه‌های پایه
RUN pip install --no-cache-dir pyTelegramBotAPI requests

# سوئیچ به کاربر غیر root
USER botuser

# محدودیت‌های منابع
CMD ["python", "bot.py"]
'''
            with sftp.open(f"{remote_dir}/Dockerfile", 'w') as f:
                f.write(dockerfile)
            sftp.close()
            
            # ساخت ایمیج
            build_cmd = f"cd {remote_dir} && sudo docker build -t bot_{bot_id} . 2>&1"
            stdin, stdout, stderr = ssh.exec_command(build_cmd)
            build_output = stdout.read().decode()
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code != 0:
                error = stderr.read().decode()
                ssh.close()
                return None, f"خطا در build: {error[:200]}"
            
            # اجرا با محدودیت‌های شدید امنیتی
            run_cmd = f"""sudo docker run -d \\
                --name bot_{bot_id} \\
                --memory="256m" \\
                --memory-swap="256m" \\
                --cpus="0.5" \\
                --network none \\
                --read-only \\
                --tmpfs /tmp:rw,noexec,nosuid,size=64m \\
                --cap-drop=ALL \\
                --cap-add=NET_ADMIN \\
                --security-opt=no-new-privileges:true \\
                --restart=no \\
                bot_{bot_id}
            """
            stdin, stdout, stderr = ssh.exec_command(run_cmd)
            container_id = stdout.read().decode().strip()
            exit_code = stdout.channel.recv_exit_status()
            
            ssh.close()
            
            if container_id and exit_code == 0:
                self.update_server_bots_count(server.id, 1)
                return container_id, "success"
            else:
                return None, "خطا در اجرای کانتینر"
                
        except Exception as e:
            logger.error(f"خطا در استقرار روی {server.ip}: {e}")
            if ssh:
                ssh.close()
            return None, str(e)
    
    def stop_bot_on_server(self, server: ServerInfo, container_id: str) -> bool:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=server.ip,
                port=server.port,
                username=server.username,
                password=server.password,
                timeout=10
            )
            ssh.exec_command(f"sudo docker stop {container_id} && sudo docker rm {container_id}")
            ssh.close()
            self.update_server_bots_count(server.id, -1)
            return True
        except:
            return False
    
    def get_bot_status(self, server: ServerInfo, container_id: str) -> str:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=server.ip,
                port=server.port,
                username=server.username,
                password=server.password,
                timeout=10
            )
            stdin, stdout, stderr = ssh.exec_command(f"sudo docker inspect -f '{{{{.State.Status}}}}' {container_id}")
            status = stdout.read().decode().strip()
            ssh.close()
            return status if status else "unknown"
        except:
            return "unknown"
    
    def restart_all_bots(self) -> int:
        count = 0
        for server in self.servers:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=server.ip,
                    port=server.port,
                    username=server.username,
                    password=server.password,
                    timeout=10
                )
                ssh.exec_command("sudo docker restart $(sudo docker ps -q --filter name=bot_)")
                ssh.close()
                count += 1
            except:
                pass
        return count
    
    def install_library(self, library: str) -> List[Tuple[str, bool, str]]:
        results = []
        for server in self.servers:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(
                    hostname=server.ip,
                    port=server.port,
                    username=server.username,
                    password=server.password,
                    timeout=10
                )
                cmd = f"sudo docker run --rm python:3.10-slim pip install {library}"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                output = stdout.read().decode()
                exit_code = stdout.channel.recv_exit_status()
                ssh.close()
                results.append((server.name, exit_code == 0, output[:100] if exit_code == 0 else stderr.read().decode()[:100]))
            except Exception as e:
                results.append((server.name, False, str(e)))
        return results

server_manager = ServerManager()

# ============================================================
#                 توابع کمکی ربات
# ============================================================
def generate_referral_code(user_id: int) -> str:
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:10]

def get_user(user_id: int) -> Optional[dict]:
    try:
        row = db.execute(user_id, 'SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
        return dict(row) if row else None
    except:
        return None

def create_user(user_id: int, username: str, first_name: str, last_name: str, referred_by: int = None) -> bool:
    try:
        now = datetime.now().isoformat()
        referral_code = generate_referral_code(user_id)
        max_bots = int(db.get_setting('max_bots_per_user') or '1')
        
        db.execute(user_id, '''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, 
             created_at, last_active, payment_status, max_bots, bots_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, 
              now, now, 'pending', max_bots, 0))
        db.commit(user_id)
        
        if referred_by:
            db.execute(referred_by, '''
                UPDATE users SET referrals_count = referrals_count + 1
                WHERE user_id = ?
            ''', (referred_by,))
            db.commit(referred_by)
        
        # ثبت لاگ
        db.execute(user_id, '''
            INSERT INTO user_logs (user_id, action, details, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'register', f'ثبت نام با کد رفرال {referred_by}', now))
        db.commit(user_id)
        
        return True
    except Exception as e:
        logger.error(f"خطا در create_user: {e}")
        return False

def check_payment(user_id: int) -> bool:
    try:
        row = db.execute(user_id, 'SELECT payment_status FROM users WHERE user_id = ?', (user_id,)).fetchone()
        return row and row['payment_status'] == 'approved'
    except:
        return False

def can_create_bot(user_id: int) -> Tuple[bool, str]:
    try:
        row = db.execute(user_id, 'SELECT bots_count, max_bots, payment_status FROM users WHERE user_id = ?', (user_id,)).fetchone()
        if not row:
            return False, "کاربر پیدا نشد"
        if row['payment_status'] != 'approved':
            return False, "❌ ابتدا هزینه را پرداخت کنید"
        if row['bots_count'] >= row['max_bots']:
            return False, f"❌ شما فقط می‌توانید {row['max_bots']} ربات بسازید"
        return True, "ok"
    except:
        return False, "خطا در بررسی"

def get_user_bot(user_id: int) -> Optional[dict]:
    try:
        row = db.execute(user_id, 'SELECT * FROM bots WHERE user_id = ? LIMIT 1', (user_id,)).fetchone()
        return dict(row) if row else None
    except:
        return None

def add_bot_to_db(user_id: int, bot_id: str, token: str, name: str, username: str, server_id: int, server_ip: str, container_id: str) -> bool:
    try:
        now = datetime.now().isoformat()
        db.execute(user_id, '''
            INSERT INTO bots (id, user_id, token, name, username, server_id, server_ip, container_id, status, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bot_id, user_id, token, name, username, server_id, server_ip, container_id, 'running', now, now))
        db.execute(user_id, 'UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (now, user_id))
        db.commit(user_id)
        
        # ثبت لاگ
        db.execute(user_id, '''
            INSERT INTO user_logs (user_id, action, details, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'create_bot', f'ساخت ربات {name} ({bot_id})', now))
        db.commit(user_id)
        
        return True
    except Exception as e:
        logger.error(f"خطا در add_bot_to_db: {e}")
        return False

def delete_bot_from_db(user_id: int, bot_id: str) -> bool:
    try:
        bot = get_user_bot(user_id)
        db.execute(user_id, 'DELETE FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
        db.execute(user_id, 'UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
        db.commit(user_id)
        
        # ثبت لاگ
        db.execute(user_id, '''
            INSERT INTO user_logs (user_id, action, details, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'delete_bot', f'حذف ربات {bot_id}', datetime.now().isoformat()))
        db.commit(user_id)
        
        return True
    except:
        return False

def extract_token_from_code(code: str) -> Optional[str]:
    patterns = [
        r'(?:TOKEN|BOT_TOKEN|API_TOKEN|token)\s*=\s*["\']([^"\']+)["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)',
        r'Bot\(\s*["\']([^"\']+)["\']\s*\)'
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def save_receipt(user_id: int, photo_file) -> Tuple[bool, str]:
    try:
        file_info = bot.get_file(photo_file[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        path = RECEIPTS_DIR / f"{user_id}_{payment_code}.jpg"
        with open(path, 'wb') as f:
            f.write(downloaded)
        
        price = int(db.get_setting('price') or '2000000')
        db.execute(user_id, '''
            INSERT INTO receipts (user_id, amount, receipt_path, created_at, payment_code, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, price, str(path), datetime.now().isoformat(), payment_code, 'pending'))
        db.commit(user_id)
        return True, payment_code
    except Exception as e:
        return False, str(e)

# ============================================================
#                     ربات تلگرام
# ============================================================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ========== منوها ==========
def get_main_menu(is_admin: bool = False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        '🤖 ساخت ربات جدید',
        '📋 اطلاعات ربات من',
        '🔄 توقف ربات',
        '▶️ راه‌اندازی ربات',
        '🗑 حذف ربات',
        '💰 پرداخت و رفرال',
        '📚 راهنما',
        '📊 آمار من'
    ]
    if is_admin:
        buttons.append('👑 پنل مدیریت')
    markup.add(*buttons)
    return markup

def get_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        ('💳 تغییر شماره کارت', 'admin_card'),
        ('💰 تغییر قیمت', 'admin_price'),
        ('📝 تغییر متن خوشامد', 'admin_welcome'),
        ('📚 تغییر متن راهنما', 'admin_help'),
        ('🖥 افزودن سرور جدید', 'admin_add_server'),
        ('🗑 حذف سرور', 'admin_remove_server'),
        ('👥 حذف کاربر', 'admin_del_user'),
        ('🤖 حذف ربات کاربر', 'admin_del_bot'),
        ('🔄 ریستارت همه ربات‌ها', 'admin_restart_bots'),
        ('📢 ارسال پیام همگانی', 'admin_broadcast'),
        ('📦 نصب کتابخانه', 'admin_install_lib'),
        ('📊 آمار کامل سیستم', 'admin_stats'),
        ('🖥 لیست سرورها', 'admin_list_servers'),
        ('📸 تایید فیش‌ها', 'admin_receipts'),
        ('📜 لاگ‌های کاربر', 'admin_user_logs')
    ]
    for text, data in buttons:
        markup.add(types.InlineKeyboardButton(text, callback_data=data))
    return markup

# ========== هندلر استارت ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    # بررسی کد رفرال
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        # جستجو در همه شاردها
        for shard_file in DB_DIR.glob("shard_*.db"):
            conn = sqlite3.connect(str(shard_file))
            row = conn.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,)).fetchone()
            conn.close()
            if row:
                referred_by = row[0]
                break
    
    create_user(user_id, username, first_name, last_name, referred_by)
    
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    user = get_user(user_id)
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}" if user else ""
    
    welcome = db.get_setting('welcome_text') or "🚀 به ربات مادر خوش آمدید"
    welcome += f"\n\n🎁 کد رفرال شما: {user['referral_code'] if user else ''}\n🔗 لینک دعوت: {referral_link}"
    
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

# ========== پرداخت و رفرال ==========
@bot.message_handler(func=lambda m: m.text == '💰 پرداخت و رفرال')
def payment_ref(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        cmd_start(message)
        return
    
    is_paid = check_payment(user_id)
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user['referral_code']}"
    price = db.get_setting('price') or '2000000'
    card_number = db.get_setting('card_number') or '5892101187322777'
    card_holder = db.get_setting('card_holder') or 'مرتضی نیکخو خنجری'
    
    text = f"💰 وضعیت پرداخت: {'✅ تایید شده' if is_paid else '⏳ در انتظار'}\n\n"
    text += f"💳 شماره کارت: `{card_number}`\n"
    text += f"👤 به نام: {card_holder}\n"
    text += f"💰 مبلغ: {int(price):,} تومان\n\n"
    text += f"🎁 سیستم رفرال:\n"
    text += f"🔗 لینک دعوت: [کلیک کنید]({referral_link})\n"
    text += f"👥 تعداد دعوت: {user['referrals_count']}\n"
    text += f"✅ تایید شده: {user['verified_referrals']}\n\n"
    text += f"📸 پس از واریز، تصویر فیش را ارسال کنید"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_receipt_photo(message):
    user_id = message.from_user.id
    
    if check_payment(user_id):
        bot.reply_to(message, "✅ پرداخت شما قبلاً تایید شده است")
        return
    
    existing = db.execute(user_id, 'SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,)).fetchone()
    if existing:
        bot.reply_to(message, "⏳ شما یک فیش در انتظار بررسی دارید")
        return
    
    success, result = save_receipt(user_id, message.photo)
    if success:
        bot.reply_to(message, f"✅ فیش دریافت شد\n🆔 کد پیگیری: `{result}`\nپس از تایید ادمین فعال می‌شود", parse_mode="Markdown")
        for admin in ADMIN_IDS:
            bot.send_message(admin, f"📸 فیش جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {int(db.get_setting('price') or 2000000):,} تومان\n🆔 کد: {result}")
    else:
        bot.reply_to(message, f"❌ خطا: {result}")

# ========== ساخت ربات ==========
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot_request(message):
    user_id = message.from_user.id
    
    can, msg = can_create_bot(user_id)
    if not can:
        bot.send_message(message.chat.id, msg)
        return
    
    bot.send_message(message.chat.id, "📤 فایل `.py` یا `.zip` ربات خود را ارسال کنید.\n\n⚠️ نکات:\n• توکن ربات باید در کد باشد\n• حجم حداکثر ۵۰ مگابایت\n• کد شما در محیطی کاملاً ایزوله اجرا می‌شود")

@bot.message_handler(content_types=['document'])
def handle_bot_file(message):
    user_id = message.from_user.id
    
    can, msg = can_create_bot(user_id)
    if not can:
        bot.reply_to(message, msg)
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های .py یا .zip مجاز هستند")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۵۰ مگابایت باشد")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
    temp_dir = TEMP_DIR / f"user_{user_id}_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        file_info = bot.get_file(message.document.file_id)
        file_data = bot.download_file(file_info.file_path)
        zip_path = temp_dir / file_name
        with open(zip_path, 'wb') as f:
            f.write(file_data)
        
        code = ""
        if file_name.endswith('.zip'):
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)
            for py_file in temp_dir.glob("**/*.py"):
                try:
                    code = py_file.read_text(encoding='utf-8', errors='ignore')
                    break
                except:
                    continue
        else:
            code = (temp_dir / file_name).read_text(encoding='utf-8', errors='ignore')
        
        if not code:
            bot.edit_message_text("❌ هیچ فایل پایتونی در فایل پیدا نشد", message.chat.id, status_msg.message_id)
            shutil.rmtree(temp_dir)
            return
        
        token = extract_token_from_code(code)
        if not token:
            bot.edit_message_text("❌ توکن ربات در کد پیدا نشد!\nلطفاً توکن را به صورت TOKEN = 'your_token' در کد قرار دهید", message.chat.id, status_msg.message_id)
            shutil.rmtree(temp_dir)
            return
        
        # اعتبارسنجی توکن
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                raise Exception
            bot_info = resp.json()['result']
            bot_name = bot_info['first_name']
            bot_username = bot_info['username']
        except:
            bot.edit_message_text("❌ توکن نامعتبر است", message.chat.id, status_msg.message_id)
            shutil.rmtree(temp_dir)
            return
        
        server = server_manager.get_available_server()
        if not server:
            bot.edit_message_text("❌ هیچ سرور فعالی برای اجرا وجود ندارد. با ادمین تماس بگیرید", message.chat.id, status_msg.message_id)
            shutil.rmtree(temp_dir)
            return
        
        bot.edit_message_text("⚡ در حال استقرار روی سرور امن...", message.chat.id, status_msg.message_id)
        
        bot_id = hashlib.md5(f"{user_id}_{token}_{time.time()}".encode()).hexdigest()[:12]
        container_id, deploy_msg = server_manager.deploy_bot_on_server(server, bot_id, code, token)
        
        if container_id:
            add_bot_to_db(user_id, bot_id, token, bot_name, bot_username, server.id, server.ip, container_id)
            result_text = f"✅ ربات با موفقیت ساخته شد!\n\n"
            result_text += f"🤖 نام: {bot_name}\n"
            result_text += f"🔗 لینک: https://t.me/{bot_username}\n"
            result_text += f"🆔 شناسه: {bot_id}\n"
            result_text += f"🖥 سرور: {server.name}\n"
            result_text += f"🔒 محیط اجرا: Docker (ایزوله، بدون شبکه، محدودیت منابع)"
            bot.edit_message_text(result_text, message.chat.id, status_msg.message_id)
        else:
            bot.edit_message_text(f"❌ خطا در استقرار ربات: {deploy_msg}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        logger.error(f"خطا در ساخت ربات: {e}")
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ========== اطلاعات ربات من ==========
@bot.message_handler(func=lambda m: m.text == '📋 اطلاعات ربات من')
def my_bot_info(message):
    user_id = message.from_user.id
    bot_info = get_user_bot(user_id)
    
    if not bot_info:
        bot.send_message(message.chat.id, "📭 شما هنوز رباتی نساخته‌اید.\nاز منوی ساخت ربات استفاده کنید")
        return
    
    server = next((s for s in server_manager.servers if s.id == bot_info['server_id']), None)
    status = "unknown"
    if server:
        status = server_manager.get_bot_status(server, bot_info['container_id'])
    
    status_emoji = "🟢" if status == "running" else "🔴" if status == "exited" else "🟡"
    status_text = {"running": "در حال اجرا", "exited": "متوقف", "unknown": "نامشخص"}.get(status, status)
    
    text = f"{status_emoji} **{bot_info['name']}**\n\n"
    text += f"🔗 https://t.me/{bot_info['username']}\n"
    text += f"🆔 `{bot_info['id']}`\n"
    text += f"📊 وضعیت: {status_text}\n"
    text += f"🖥 سرور: {bot_info['server_ip']}\n"
    text += f"📅 تاریخ ساخت: {bot_info['created_at'][:10]}\n\n"
    text += f"🔒 ربات شما در محیط کاملاً ایزوله اجرا می‌شود"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ========== توقف ربات ==========
@bot.message_handler(func=lambda m: m.text == '🔄 توقف ربات')
def stop_bot_command(message):
    user_id = message.from_user.id
    bot_info = get_user_bot(user_id)
    
    if not bot_info:
        bot.send_message(message.chat.id, "📭 شما رباتی ندارید")
        return
    
    server = next((s for s in server_manager.servers if s.id == bot_info['server_id']), None)
    if server:
        if server_manager.stop_bot_on_server(server, bot_info['container_id']):
            db.execute(user_id, 'UPDATE bots SET status = ? WHERE id = ?', ('stopped', bot_info['id']))
            db.commit(user_id)
            bot.send_message(message.chat.id, f"✅ ربات {bot_info['name']} متوقف شد")
        else:
            bot.send_message(message.chat.id, "❌ خطا در توقف ربات")
    else:
        bot.send_message(message.chat.id, "❌ سرور ربات یافت نشد")

# ========== راه‌اندازی ربات ==========
@bot.message_handler(func=lambda m: m.text == '▶️ راه‌اندازی ربات')
def start_bot_command(message):
    user_id = message.from_user.id
    bot_info = get_user_bot(user_id)
    
    if not bot_info:
        bot.send_message(message.chat.id, "📭 شما رباتی ندارید")
        return
    
    bot.send_message(message.chat.id, "⚠️ برای راه‌اندازی مجدد ربات، لطفاً ربات را حذف کرده و دوباره بسازید.\nاین کار به دلیل محدودیت‌های امنیتی انجام می‌شود.")

# ========== حذف ربات ==========
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_bot_command(message):
    user_id = message.from_user.id
    bot_info = get_user_bot(user_id)
    
    if not bot_info:
        bot.send_message(message.chat.id, "📭 شما رباتی ندارید")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"confirm_del_bot_{bot_info['id']}"))
    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del_bot"))
    
    bot.send_message(message.chat.id, f"⚠️ آیا از حذف ربات {bot_info['name']} اطمینان دارید؟\nاین عمل غیرقابل بازگشت است", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_bot_'))
def confirm_delete_bot(call):
    user_id = call.from_user.id
    bot_id = call.data.replace('confirm_del_bot_', '')
    bot_info = get_user_bot(user_id)
    
    if bot_info and bot_info['id'] == bot_id:
        server = next((s for s in server_manager.servers if s.id == bot_info['server_id']), None)
        if server:
            server_manager.stop_bot_on_server(server, bot_info['container_id'])
        delete_bot_from_db(user_id, bot_id)
        bot.edit_message_text("✅ ربات با موفقیت حذف شد", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ ربات یافت نشد", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del_bot')
def cancel_delete_bot(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد", call.message.chat.id, call.message.message_id)

# ========== آمار من ==========
@bot.message_handler(func=lambda m: m.text == '📊 آمار من')
def my_stats(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    bot_info = get_user_bot(user_id)
    
    if not user:
        cmd_start(message)
        return
    
    text = f"📊 **آمار شما**\n\n"
    text += f"👤 نام: {user['first_name']}\n"
    text += f"🆔 آیدی: {user_id}\n"
    text += f"💰 وضعیت: {'✅ تایید شده' if user['payment_status'] == 'approved' else '⏳ در انتظار'}\n"
    text += f"🤖 تعداد ربات: {user['bots_count']}/{user['max_bots']}\n"
    text += f"🎁 رفرال: {user['referrals_count']} کلیک / {user['verified_referrals']} ساخت\n"
    text += f"📅 تاریخ عضویت: {user['created_at'][:10]}\n"
    
    if bot_info:
        text += f"\n🤖 ربات شما:\n"
        text += f"نام: {bot_info['name']}\n"
        text += f"وضعیت: {bot_info['status']}"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ========== راهنما ==========
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def help_command(message):
    help_text = db.get_setting('help_text') or "📚 راهنمای استفاده"
    bot.send_message(message.chat.id, help_text)

# ============================================================
#                     پنل مدیریت کامل
# ============================================================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید")
        return
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت ربات مادر**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", 
                     parse_mode="Markdown", reply_markup=get_admin_menu())

@bot.callback_query_handler(func=lambda call: call.from_user.id in ADMIN_IDS and call.data.startswith('admin_'))
def admin_callback_handler(call):
    data = call.data
    
    if data == 'admin_card':
        msg = bot.send_message(call.message.chat.id, "💳 شماره کارت جدید را وارد کنید:")
        bot.register_next_step_handler(msg, set_card_callback)
    
    elif data == 'admin_price':
        msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید (تومان) را وارد کنید:")
        bot.register_next_step_handler(msg, set_price_callback)
    
    elif data == 'admin_welcome':
        msg = bot.send_message(call.message.chat.id, "📝 متن خوشامدگویی جدید را وارد کنید:")
        bot.register_next_step_handler(msg, set_welcome_callback)
    
    elif data == 'admin_help':
        msg = bot.send_message(call.message.chat.id, "📚 متن راهنمای جدید را وارد کنید:")
        bot.register_next_step_handler(msg, set_help_callback)
    
    elif data == 'admin_add_server':
        msg = bot.send_message(call.message.chat.id, "🖥 نام سرور را وارد کنید:")
        bot.register_next_step_handler(msg, add_server_name_step)
    
    elif data == 'admin_remove_server':
        if not server_manager.servers:
            bot.send_message(call.message.chat.id, "❌ هیچ سروری وجود ندارد")
        else:
            markup = types.InlineKeyboardMarkup()
            for s in server_manager.servers:
                markup.add(types.InlineKeyboardButton(f"🗑 {s.name} ({s.ip})", callback_data=f"remove_server_{s.id}"))
            bot.send_message(call.message.chat.id, "سرور مورد نظر را انتخاب کنید:", reply_markup=markup)
    
    elif data == 'admin_del_user':
        msg = bot.send_message(call.message.chat.id, "👤 آیدی کاربر مورد نظر را وارد کنید:")
        bot.register_next_step_handler(msg, delete_user_by_id_step)
    
    elif data == 'admin_del_bot':
        msg = bot.send_message(call.message.chat.id, "🤖 آیدی ربات مورد نظر را وارد کنید:")
        bot.register_next_step_handler(msg, delete_bot_by_id_step)
    
    elif data == 'admin_restart_bots':
        bot.answer_callback_query(call.id, "در حال ریستارت ربات‌ها...")
        count = server_manager.restart_all_bots()
        bot.send_message(call.message.chat.id, f"✅ ریستارت روی {count} سرور انجام شد")
    
    elif data == 'admin_broadcast':
        msg = bot.send_message(call.message.chat.id, "📢 متن پیام همگانی را وارد کنید:")
        bot.register_next_step_handler(msg, broadcast_message_step)
    
    elif data == 'admin_install_lib':
        msg = bot.send_message(call.message.chat.id, "📦 نام کتابخانه مورد نظر را وارد کنید:")
        bot.register_next_step_handler(msg, install_lib_step)
    
    elif data == 'admin_stats':
        total_users = db.get_total_users()
        total_bots = db.get_total_bots()
        pending_receipts = len(db.get_pending_receipts())
        paid_users = 0
        for shard_file in DB_DIR.glob("shard_*.db"):
            conn = sqlite3.connect(str(shard_file))
            count = conn.execute('SELECT COUNT(*) FROM users WHERE payment_status = "approved"').fetchone()[0]
            paid_users += count
            conn.close()
        
        text = f"📊 **آمار کل سیستم**\n\n"
        text += f"👥 کل کاربران: {total_users}\n"
        text += f"✅ کاربران تایید شده: {paid_users}\n"
        text += f"🤖 کل ربات‌ها: {total_bots}\n"
        text += f"🖥 سرورهای فعال: {len(server_manager.servers)}\n"
        text += f"📸 فیش‌های در انتظار: {pending_receipts}\n"
        text += f"💰 قیمت هر ربات: {int(db.get_setting('price') or 2000000):,} تومان\n"
        text += f"💳 شماره کارت: {db.get_setting('card_number')}\n"
        text += f"📁 تعداد شاردها: {len(list(DB_DIR.glob('shard_*.db')))}"
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif data == 'admin_list_servers':
        if not server_manager.servers:
            bot.send_message(call.message.chat.id, "❌ هیچ سروری ثبت نشده")
        else:
            text = "🖥 **لیست سرورهای فعال**\n\n"
            for s in server_manager.servers:
                test, msg = server_manager.test_connection(s)
                status = "🟢" if test else "🔴"
                text += f"{status} **{s.name}**\n"
                text += f"   📍 IP: {s.ip}:{s.port}\n"
                text += f"   👤 کاربر: {s.username}\n"
                text += f"   🤖 ربات‌ها: {s.current_bots}/{s.max_bots}\n"
                text += f"   {msg}\n\n"
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif data == 'admin_receipts':
        show_pending_receipts(call.message.chat.id)
    
    elif data == 'admin_user_logs':
        msg = bot.send_message(call.message.chat.id, "👤 آیدی کاربر را برای مشاهده لاگ‌ها وارد کنید:")
        bot.register_next_step_handler(msg, show_user_logs)
    
    bot.answer_callback_query(call.id)

# ========== توابع کمکی ادمین ==========
def set_card_callback(message):
    new_card = message.text.strip()
    db.set_setting("card_number", new_card)
    bot.reply_to(message, f"✅ شماره کارت به {new_card} تغییر کرد")

def set_price_callback(message):
    try:
        new_price = int(message.text.strip())
        db.set_setting("price", str(new_price))
        bot.reply_to(message, f"✅ قیمت به {new_price:,} تومان تغییر کرد")
    except:
        bot.reply_to(message, "❌ لطفاً عدد وارد کنید")

def set_welcome_callback(message):
    new_text = message.text
    db.set_setting("welcome_text", new_text)
    bot.reply_to(message, "✅ متن خوشامدگویی تغییر کرد")

def set_help_callback(message):
    new_text = message.text
    db.set_setting("help_text", new_text)
    bot.reply_to(message, "✅ متن راهنما تغییر کرد")

def add_server_name_step(message):
    name = message.text.strip()
    msg = bot.reply_to(message, "📡 آیپی سرور را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: add_server_ip_step(m, name))

def add_server_ip_step(message, name):
    ip = message.text.strip()
    msg = bot.reply_to(message, "👤 یوزرنیم (مثلاً root):")
    bot.register_next_step_handler(msg, lambda m: add_server_user_step(m, name, ip))

def add_server_user_step(message, name, ip):
    username = message.text.strip()
    msg = bot.reply_to(message, "🔑 رمز عبور:")
    bot.register_next_step_handler(msg, lambda m: add_server_pass_step(m, name, ip, username))

def add_server_pass_step(message, name, ip, username):
    password = message.text.strip()
    if server_manager.add_server(name, ip, username, password):
        bot.reply_to(message, f"✅ سرور {name} با موفقیت اضافه شد\n🖥 IP: {ip}\n👤 کاربر: {username}")
    else:
        bot.reply_to(message, "❌ خطا در افزودن سرور")

@bot.callback_query_handler(func=lambda call: call.from_user.id in ADMIN_IDS and call.data.startswith('remove_server_'))
def remove_server_callback(call):
    server_id = int(call.data.replace('remove_server_', ''))
    if server_manager.remove_server(server_id):
        bot.edit_message_text("✅ سرور با موفقیت حذف شد", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا در حذف سرور", call.message.chat.id, call.message.message_id)

def delete_user_by_id_step(message):
    try:
        user_id = int(message.text.strip())
        # حذف کاربر از دیتابیس
        db.execute(user_id, 'DELETE FROM users WHERE user_id = ?', (user_id,))
        db.commit(user_id)
        bot.reply_to(message, f"✅ کاربر {user_id} حذف شد")
    except:
        bot.reply_to(message, "❌ آیدی نامعتبر")

def delete_bot_by_id_step(message):
    try:
        bot_id = message.text.strip()
        found = False
        for shard_file in DB_DIR.glob("shard_*.db"):
            conn = sqlite3.connect(str(shard_file))
            conn.row_factory = sqlite3.Row
            row = conn.execute('SELECT user_id, server_ip, container_id FROM bots WHERE id = ?', (bot_id,)).fetchone()
            if row:
                user_id, server_ip, container_id = row
                for server in server_manager.servers:
                    if server.ip == server_ip:
                        server_manager.stop_bot_on_server(server, container_id)
                        break
                conn.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
                conn.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                found = True
                break
            conn.close()
        if found:
            bot.reply_to(message, f"✅ ربات {bot_id} حذف شد")
        else:
            bot.reply_to(message, f"❌ ربات {bot_id} پیدا نشد")
    except:
        bot.reply_to(message, "❌ خطا در حذف")

def broadcast_message_step(message):
    text = message.text
    bot.reply_to(message, "📢 در حال ارسال پیام همگانی به همه کاربران...")
    
    count = 0
    for user in db.get_all_users():
        try:
            bot.send_message(user['user_id'], f"📢 **پیام مدیریتی**\n\n{text}", parse_mode="Markdown")
            count += 1
            time.sleep(0.05)
        except:
            pass
    
    bot.send_message(message.chat.id, f"✅ پیام همگانی به {count} کاربر ارسال شد")

def install_lib_step(message):
    lib = message.text.strip()
    bot.reply_to(message, f"📦 در حال نصب {lib} روی همه سرورها...")
    
    results = server_manager.install_library(lib)
    result_text = "📦 **نتیجه نصب کتابخانه**\n\n"
    for name, success, msg in results:
        result_text += f"{'✅' if success else '❌'} {name}: {msg[:50]}\n"
    
    bot.send_message(message.chat.id, result_text, parse_mode="Markdown")

def show_pending_receipts(chat_id):
    receipts = db.get_pending_receipts()
    
    if not receipts:
        bot.send_message(chat_id, "📸 هیچ فیش در انتظاری وجود ندارد")
        return
    
    for r in receipts[:10]:
        text = f"📸 **فیش واریزی**\n"
        text += f"👤 کاربر: {r['user_id']}\n"
        text += f"💰 مبلغ: {r['amount']:,} تومان\n"
        text += f"🆔 کد: {r['payment_code']}\n"
        text += f"📅 تاریخ: {r['created_at'][:10]}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_receipt_{r['id']}_{r['user_id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}_{r['user_id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(chat_id, f, caption=text, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

def show_user_logs(message):
    try:
        user_id = int(message.text.strip())
        rows = db.execute(user_id, 'SELECT * FROM user_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 20', (user_id,)).fetchall()
        
        if not rows:
            bot.reply_to(message, f"📜 لاگی برای کاربر {user_id} وجود ندارد")
            return
        
        text = f"📜 **لاگ‌های کاربر {user_id}**\n\n"
        for row in rows:
            text += f"🕐 {row['created_at'][:16]}\n"
            text += f"⚡ {row['action']}\n"
            text += f"📝 {row['details']}\n\n"
        
        bot.reply_to(message, text[:4000], parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.from_user.id in ADMIN_IDS and call.data.startswith('approve_receipt_'))
def approve_receipt_callback(call):
    parts = call.data.split('_')
    receipt_id = parts[2]
    user_id = int(parts[3])
    
    db.execute(user_id, 'UPDATE receipts SET status = ?, reviewed_at = ?, reviewed_by = ? WHERE id = ?',
               ('approved', datetime.now().isoformat(), call.from_user.id, receipt_id))
    db.execute(user_id, 'UPDATE users SET payment_status = ?, payment_date = ? WHERE user_id = ?',
               ('approved', datetime.now().isoformat(), user_id))
    db.commit(user_id)
    
    try:
        bot.send_message(user_id, "✅ فیش شما تایید شد! اکنون می‌توانید ربات خود را بسازید.")
    except:
        pass
    
    bot.edit_message_caption("✅ تایید شد", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.from_user.id in ADMIN_IDS and call.data.startswith('reject_receipt_'))
def reject_receipt_callback(call):
    parts = call.data.split('_')
    receipt_id = parts[2]
    user_id = int(parts[3])
    
    db.execute(user_id, 'UPDATE receipts SET status = ?, reviewed_at = ?, reviewed_by = ? WHERE id = ?',
               ('rejected', datetime.now().isoformat(), call.from_user.id, receipt_id))
    db.commit(user_id)
    
    try:
        bot.send_message(user_id, "❌ فیش شما رد شد. لطفاً با پشتیبانی تماس بگیرید: @shahraghee13")
    except:
        pass
    
    bot.edit_message_caption("❌ رد شد", call.message.chat.id, call.message.message_id)

# ============================================================
#                    مانیتورینگ سیستم
# ============================================================
def system_monitor():
    """مانیتورینگ خودکار سیستم"""
    while True:
        try:
            # به‌روزرسانی آمار سیستم
            total_users = db.get_total_users()
            total_bots = db.get_total_bots()
            total_payments = 0
            for shard_file in DB_DIR.glob("shard_*.db"):
                conn = sqlite3.connect(str(shard_file))
                count = conn.execute('SELECT COUNT(*) FROM receipts WHERE status = "approved"').fetchone()[0]
                total_payments += count
                conn.close()
            
            db.execute_meta('''
                INSERT INTO system_stats (total_users, total_bots, total_payments, active_servers, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (total_users, total_bots, total_payments, len(server_manager.servers), datetime.now().isoformat()))
            db.commit_meta()
            
            logger.info(f"مانیتورینگ - کاربران: {total_users}, ربات‌ها: {total_bots}")
            
        except Exception as e:
            logger.error(f"خطا در مانیتورینگ: {e}")
        
        time.sleep(3600)  # هر 1 ساعت

# شروع مانیتورینگ
monitor_thread = threading.Thread(target=system_monitor, daemon=True)
monitor_thread.start()

# ============================================================
#                         اجرا
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی نسخه 11.0 - کاملاً حرفه‌ای و نهایی")
    print("=" * 70)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🖥 سرورهای فعال: {len(server_manager.servers)}")
    print(f"💰 قیمت هر ربات: {int(db.get_setting('price') or 2000000):,} تومان")
    print(f"💳 شماره کارت: {db.get_setting('card_number')}")
    print(f"📁 دیتابیس: شارد شده - هر شارد {db.shard_size:,} کاربر")
    print("=" * 70)
    print("✅ ربات در حال اجراست...")
    print("")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا در اجرا: {e}")
            time.sleep(5)