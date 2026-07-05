# ============================================================
# ربات قرعه‌کشی هوشمند UTYOB - نسخه کامل و قدرتمند
# ============================================================

import asyncio
import logging
import random
import json
import sqlite3
import hashlib
import base58
import aiohttp
import psutil
import threading
import time
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any
from flask import Flask, request, jsonify, render_template
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# تنظیمات اولیه
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# توکن ربات - از متغیر محیطی یا مستقیم
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '123456789').split(',')]

# API های ترون برای تایید تراکنش
TRONGRID_APIS = [
    "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
    # API های جدید در运行时 اضافه می‌شوند
]

# آدرس مقصد برای واریز
DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PAYMENT_AMOUNT = 100  # دلار

# تنظیمات دیتابیس
DB_SHARDS = 100
CACHE_TTL = 300  # ثانیه

# ============================================================
# دیتابیس با ۱۰۰ شارد برای مقیاس‌پذیری
# ============================================================
class DatabaseManager:
    """مدیریت دیتابیس با شاردینگ برای پشتیبانی از میلیون‌ها کاربر"""
    
    def __init__(self, num_shards=DB_SHARDS):
        self.num_shards = num_shards
        self.connections = {}
        self.locks = {}
        self._init_shards()
        
    def _init_shards(self):
        """ایجاد و مقداردهی اولیه شاردها"""
        os.makedirs("data", exist_ok=True)
        for i in range(self.num_shards):
            db_path = f"data/shard_{i}.db"
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            self.connections[i] = conn
            self.locks[i] = threading.Lock()
            self._create_tables(conn, i)
            logger.info(f"شارد {i} ایجاد شد")
            
    def _create_tables(self, conn, shard_id):
        """ایجاد جداول مورد نیاز"""
        cursor = conn.cursor()
        
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'en',
                wallet_address TEXT,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                has_subscription INTEGER DEFAULT 0,
                subscription_end TEXT,
                total_participations INTEGER DEFAULT 0,
                wins_count INTEGER DEFAULT 0,
                last_win_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تراکنش‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_id TEXT,
                status TEXT DEFAULT 'pending',
                verified_at TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول قرعه‌کشی‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lotteries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winners_count INTEGER,
                prize_per_winner REAL,
                total_prize REAL,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                ended_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول برندگان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_id INTEGER,
                user_id INTEGER,
                prize_amount REAL,
                wallet_address TEXT,
                paid_status INTEGER DEFAULT 0,
                paid_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تنظیمات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول نظرسنجی‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                options TEXT,
                votes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ایندکس‌ها برای سرعت بالا
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_user ON winners(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_paid ON winners(paid_status)')
        
        conn.commit()
        
    def get_shard(self, user_id):
        """تعیین شارد بر اساس آیدی کاربر"""
        return hash(str(user_id)) % self.num_shards
        
    def get_connection(self, user_id):
        """دریافت اتصال به شارد مربوطه"""
        shard = self.get_shard(user_id)
        return self.connections[shard], self.locks[shard]
        
    def execute(self, user_id, query, params=(), commit=True):
        """اجرای کوئری با قفل"""
        conn, lock = self.get_connection(user_id)
        with lock:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor
            
    def execute_global(self, query, params=()):
        """اجرای کوئری روی تمام شاردها"""
        results = []
        for shard_id, conn in self.connections.items():
            with self.locks[shard_id]:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                results.extend(cursor.fetchall())
        return results
        
    def execute_all_with_shard(self, query, params=()):
        """اجرای کوئری روی تمام شاردها و بازگرداندن با شناسه شارد"""
        results = []
        for shard_id, conn in self.connections.items():
            with self.locks[shard_id]:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                for row in cursor.fetchall():
                    results.append((shard_id, row))
        return results

db = DatabaseManager()

# ============================================================
# سیستم کش قدرتمند با TTL
# ============================================================
class CacheManager:
    """سیستم کش با پشتیبانی از TTL و قفل"""
    
    def __init__(self):
        self.cache = {}
        self.expiry = {}
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        
    def set(self, key, value, ttl=CACHE_TTL):
        """ذخیره در کش با زمان انقضا"""
        with self.lock:
            self.cache[key] = value
            self.expiry[key] = time.time() + ttl
            
    def get(self, key):
        """دریافت از کش"""
        with self.lock:
            if key in self.cache and time.time() < self.expiry[key]:
                self.hits += 1
                return self.cache[key]
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]
            self.misses += 1
            return None
            
    def delete(self, key):
        """حذف از کش"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]
                
    def clear(self):
        """پاک کردن کل کش"""
        with self.lock:
            self.cache.clear()
            self.expiry.clear()
            
    def get_stats(self):
        """آمار کش"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'size': len(self.cache)
            }

cache = CacheManager()

# ============================================================
# سیستم تایید پرداخت با چندین API
# ============================================================
class PaymentVerifier:
    """تایید پرداخت با استفاده از چندین API برای دقت بالا"""
    
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.api_stats = {api: {'requests': 0, 'success': 0, 'errors': 0, 'last_reset': time.time()} for api in self.apis}
        self.pending_verifications = {}
        self.lock = threading.Lock()
        self.session = None
        
    async def get_session(self):
        """دریافت یا ایجاد session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=20)
            )
        return self.session
        
    async def verify_transaction(self, from_address, to_address, amount, tx_id=None, retry_count=0):
        """
        تایید تراکنش با استفاده از API های مختلف
        بازگشت: (موفقیت, tx_id, پیام خطا)
        """
        session = await self.get_session()
        
        # اگر tx_id داده شده، مستقیماً بررسی می‌کنیم
        if tx_id:
            return await self._verify_by_txid(session, tx_id, from_address, to_address, amount)
            
        # جستجوی تراکنش‌های اخیر
        return await self._search_transactions(session, from_address, to_address, amount)
        
    async def _verify_by_txid(self, session, tx_id, from_address, to_address, amount):
        """بررسی تراکنش با tx_id"""
        for api in self.apis:
            try:
                url = f"https://api.trongrid.io/v1/transactions/{tx_id}"
                headers = {"TRON-PRO-API-KEY": api}
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if self._validate_transaction_data(data, from_address, to_address, amount):
                            self._update_api_stats(api, True)
                            return True, tx_id, "Verified"
                    else:
                        self._update_api_stats(api, False)
            except Exception as e:
                logger.error(f"API error for {api}: {e}")
                self._update_api_stats(api, False)
                
        return False, None, "Transaction not found or invalid"
        
    async def _search_transactions(self, session, from_address, to_address, amount):
        """جستجوی تراکنش‌ها"""
        for api in self.apis:
            try:
                # جستجوی تراکنش‌های اخیر از آدرس مبدا
                url = f"https://api.trongrid.io/v1/accounts/{from_address}/transactions"
                params = {
                    "limit": 50,
                    "order_by": "block_timestamp,desc"
                }
                headers = {"TRON-PRO-API-KEY": api}
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for tx in data.get('data', []):
                            if self._validate_transaction_data(tx, from_address, to_address, amount):
                                self._update_api_stats(api, True)
                                return True, tx.get('txID'), "Verified"
                    else:
                        self._update_api_stats(api, False)
            except Exception as e:
                logger.error(f"API search error for {api}: {e}")
                self._update_api_stats(api, False)
                
        return False, None, "No matching transaction found"
        
    def _validate_transaction_data(self, tx_data, from_address, to_address, amount):
        """اعتبارسنجی داده‌های تراکنش"""
        try:
            # بررسی آدرس مقصد
            if tx_data.get('to') != to_address:
                return False
                
            # بررسی مبلغ (با احتساب ۶ رقم اعشار TRX)
            tx_amount = tx_data.get('amount', 0) / 1_000_000
            if abs(tx_amount - amount) > 0.01:  # خطای ۰.۰۱ دلار مجاز
                return False
                
            # بررسی وضعیت تراکنش
            status = tx_data.get('status', '')
            if status and status != 'SUCCESS':
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
            
    def _update_api_stats(self, api, success):
        """به‌روزرسانی آمار API"""
        with self.lock:
            if api in self.api_stats:
                self.api_stats[api]['requests'] += 1
                if success:
                    self.api_stats[api]['success'] += 1
                else:
                    self.api_stats[api]['errors'] += 1
                    
    def get_best_api(self):
        """دریافت بهترین API بر اساس成功率"""
        with self.lock:
            best_api = None
            best_score = -1
            
            for api, stats in self.api_stats.items():
                # بازنشانی آمار هر ساعت
                if time.time() - stats['last_reset'] > 3600:
                    stats['requests'] = 0
                    stats['success'] = 0
                    stats['errors'] = 0
                    stats['last_reset'] = time.time()
                    
                if stats['requests'] == 0:
                    score = 100  # API جدید
                else:
                    score = (stats['success'] / stats['requests']) * 100
                    
                if score > best_score:
                    best_score = score
                    best_api = api
                    
            return best_api or self.apis[0]
            
    def add_api(self, api_key):
        """اضافه کردن API جدید"""
        if api_key not in self.apis:
            self.apis.append(api_key)
            self.api_stats[api_key] = {'requests': 0, 'success': 0, 'errors': 0, 'last_reset': time.time()}
            logger.info(f"API جدید اضافه شد: {api_key}")
            return True
        return False
        
    def remove_api(self, api_key):
        """حذف API"""
        if api_key in self.apis and len(self.apis) > 1:
            self.apis.remove(api_key)
            del self.api_stats[api_key]
            return True
        return False

payment_verifier = PaymentVerifier()

# ============================================================
# سیستم قرعه‌کشی هوشمند با الگوریتم منصفانه
# ============================================================
class LotterySystem:
    """سیستم قرعه‌کشی با الگوریتم پیشرفته و هوشمند"""
    
    def __init__(self):
        self.current_lottery = None
        self.is_running = False
        self.participants = {}
        self.winners_history = []
        self.excluded_users = set()
        self.lock = threading.Lock()
        self.last_lottery_time = None
        
    def start_lottery(self, winners_count, prize_per_winner):
        """
        شروع قرعه‌کشی با الگوریتم هوشمند
        بازگشت: (موفقیت, نتیجه/پیام خطا)
        """
        with self.lock:
            if self.is_running:
                return False, "قرعه‌کشی در حال اجراست"
                
            # دریافت کاربران واجد شرایط
            eligible_users = self._get_eligible_users()
            
            if not eligible_users:
                return False, "هیچ کاربر واجد شرایطی یافت نشد"
                
            if len(eligible_users) < winners_count:
                return False, f"تعداد کاربران واجد شرایط ({len(eligible_users)}) کمتر از تعداد برندگان ({winners_count}) است"
                
            # اعمال الگوریتم هوشمند
            winners = self._smart_select_winners(eligible_users, winners_count)
            
            if not winners or len(winners) < winners_count:
                return False, "خطا در انتخاب برندگان"
                
            # ثبت قرعه‌کشی
            lottery_id = self._save_lottery(winners_count, prize_per_winner, winners)
            
            if not lottery_id:
                return False, "خطا در ثبت قرعه‌کشی"
                
            # ثبت برندگان
            self._save_winners(lottery_id, winners, prize_per_winner)
            
            # به‌روزرسانی آمار کاربران
            for winner in winners:
                self._update_winner_stats(winner)
                
            self.current_lottery = {
                'id': lottery_id,
                'winners': winners,
                'prize_per_winner': prize_per_winner,
                'winners_count': winners_count,
                'timestamp': datetime.now()
            }
            
            self.is_running = False
            self.last_lottery_time = datetime.now()
            
            return True, {
                'lottery_id': lottery_id,
                'winners': winners,
                'prize_per_winner': prize_per_winner
            }
            
    def _get_eligible_users(self):
        """دریافت کاربران دارای اشتراک فعال"""
        cursor = db.execute_global(
            """SELECT user_id FROM users 
               WHERE has_subscription = 1 
               AND subscription_end >= date('now')"""
        )
        return [row['user_id'] for row in cursor]
        
    def _smart_select_winners(self, eligible_users, winners_count):
        """
        انتخاب هوشمند برندگان با استفاده از الگوریتم چندمعیاره
        """
        if not eligible_users:
            return []
            
        # محاسبه وزن برای هر کاربر
        weighted_users = []
        for user_id in eligible_users:
            weight = self._calculate_user_weight(user_id)
            if weight > 0:
                weighted_users.extend([user_id] * weight)
                
        if not weighted_users:
            return []
            
        # اگر تعداد کاربران وزن‌دار کمتر از تعداد برندگان است
        if len(weighted_users) < winners_count:
            # استفاده از روش جایگزین
            return random.sample(eligible_users, min(winners_count, len(eligible_users)))
            
        # انتخاب با وزن
        selected = []
        temp_users = weighted_users.copy()
        
        for _ in range(min(winners_count, len(set(temp_users)))):
            if not temp_users:
                break
                
            # انتخاب تصادفی با وزن
            winner = random.choice(temp_users)
            
            # جلوگیری از انتخاب مجدد
            temp_users = [u for u in temp_users if u != winner]
            selected.append(winner)
            
        return selected
        
    def _calculate_user_weight(self, user_id):
        """
        محاسبه وزن کاربر بر اساس معیارهای متعدد
        """
        try:
            cursor = db.execute(user_id,
                """SELECT total_participations, wins_count, last_win_date 
                   FROM users WHERE user_id = ?""",
                (user_id,)
            )
            user_data = cursor.fetchone()
            
            if not user_data:
                return 1
                
            # وزن پایه
            weight = 1
            
            # افزایش وزن برای کاربران فعال
            if user_data['total_participations'] > 0:
                weight += min(user_data['total_participations'] / 5, 3)
                
            # کاهش وزن برای برندگان اخیر
            if user_data['wins_count'] > 0:
                weight = max(1, weight - user_data['wins_count'] * 0.5)
                
            # کاهش وزن برای برندگان اخیر (۳ روز اخیر)
            if user_data['last_win_date']:
                try:
                    last_win = datetime.strptime(user_data['last_win_date'], '%Y-%m-%d')
                    days_since_win = (datetime.now() - last_win).days
                    if days_since_win < 3:
                        weight *= 0.3  # کاهش ۷۰٪ شانس
                    elif days_since_win < 7:
                        weight *= 0.6  # کاهش ۴۰٪ شانس
                except:
                    pass
                    
            # افزایش وزن برای کاربرانی که مدت زیادی شرکت نکرده‌اند
            if user_data['total_participations'] > 0:
                avg_participation = user_data['total_participations'] / max(1, user_data['wins_count'] + 1)
                if avg_participation > 10:
                    weight *= 1.5  # افزایش ۵۰٪ شانس
                    
            return max(1, int(weight))
            
        except Exception as e:
            logger.error(f"Error calculating weight for {user_id}: {e}")
            return 1
            
    def _save_lottery(self, winners_count, prize_per_winner, winners):
        """ثبت قرعه‌کشی در دیتابیس"""
        try:
            total_prize = winners_count * prize_per_winner
            cursor = db.execute(0,  # شارد ۰ برای داده‌های عمومی
                """INSERT INTO lotteries 
                   (winners_count, prize_per_winner, total_prize, status, started_at) 
                   VALUES (?, ?, ?, 'running', CURRENT_TIMESTAMP)""",
                (winners_count, prize_per_winner, total_prize)
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving lottery: {e}")
            return None
            
    def _save_winners(self, lottery_id, winners, prize_amount):
        """ثبت برندگان در دیتابیس"""
        try:
            for user_id in winners:
                # دریافت آدرس کیف پول کاربر
                cursor = db.execute(user_id,
                    "SELECT wallet_address FROM users WHERE user_id = ?",
                    (user_id,)
                )
                user_data = cursor.fetchone()
                wallet_address = user_data['wallet_address'] if user_data else None
                
                db.execute(user_id,
                    """INSERT INTO winners 
                       (lottery_id, user_id, prize_amount, wallet_address, paid_status) 
                       VALUES (?, ?, ?, ?, 0)""",
                    (lottery_id, user_id, prize_amount, wallet_address)
                )
            return True
        except Exception as e:
            logger.error(f"Error saving winners: {e}")
            return False
            
    def _update_winner_stats(self, user_id):
        """به‌روزرسانی آمار برنده"""
        try:
            db.execute(user_id,
                """UPDATE users 
                   SET wins_count = wins_count + 1, 
                       last_win_date = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP 
                   WHERE user_id = ?""",
                (user_id,)
            )
        except Exception as e:
            logger.error(f"Error updating winner stats for {user_id}: {e}")
            
    def get_lottery_history(self, limit=10):
        """دریافت تاریخچه قرعه‌کشی‌ها"""
        try:
            cursor = db.execute(0,
                """SELECT * FROM lotteries 
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting lottery history: {e}")
            return []
            
    def get_winner_details(self, lottery_id):
        """دریافت جزئیات برندگان یک قرعه‌کشی"""
        try:
            # جستجو در تمام شاردها
            results = db.execute_global(
                """SELECT * FROM winners WHERE lottery_id = ?""",
                (lottery_id,)
            )
            return results
        except Exception as e:
            logger.error(f"Error getting winner details: {e}")
            return []

lottery_system = LotterySystem()

# ============================================================
# سیستم مدیریت کاربران
# ============================================================
class UserManager:
    """مدیریت کاربران و اشتراک‌ها"""
    
    @staticmethod
    def register_user(user_id, username=None, first_name=None, last_name=None):
        """ثبت کاربر جدید"""
        try:
            cursor = db.execute(user_id,
                "SELECT user_id FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not cursor.fetchone():
                referral_code = UserManager._generate_referral_code(user_id)
                db.execute(user_id,
                    """INSERT INTO users 
                       (user_id, username, first_name, last_name, referral_code) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, username, first_name, last_name, referral_code)
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            return False
            
    @staticmethod
    def _generate_referral_code(user_id):
        """تولید کد رفرال منحصر به فرد"""
        import hashlib
        base = f"UTYOB_{user_id}_{time.time()}_{random.randint(1000, 9999)}"
        hash_obj = hashlib.sha256(base.encode())
        return hash_obj.hexdigest()[:10].upper()
        
    @staticmethod
    def get_user(user_id):
        """دریافت اطلاعات کاربر"""
        try:
            cursor = db.execute(user_id,
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
            
    @staticmethod
    def update_user(user_id, **kwargs):
        """به‌روزرسانی اطلاعات کاربر"""
        try:
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            db.execute(user_id,
                f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
            
    @staticmethod
    def get_user_by_referral(referral_code):
        """دریافت کاربر با کد رفرال"""
        try:
            # جستجو در تمام شاردها
            results = db.execute_global(
                "SELECT user_id FROM users WHERE referral_code = ?",
                (referral_code,)
            )
            return results[0]['user_id'] if results else None
        except Exception as e:
            logger.error(f"Error getting user by referral {referral_code}: {e}")
            return None
            
    @staticmethod
    def get_user_count():
        """تعداد کل کاربران"""
        try:
            total = 0
            for conn in db.connections.values():
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM users")
                total += cursor.fetchone()['count']
            return total
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0
            
    @staticmethod
    def get_active_users():
        """دریافت کاربران فعال (با اشتراک)"""
        try:
            results = db.execute_global(
                """SELECT user_id FROM users 
                   WHERE has_subscription = 1 
                   AND subscription_end >= date('now')"""
            )
            return [row['user_id'] for row in results]
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []

user_manager = UserManager()

# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    """ربات اصلی UTYOB با تمام قابلیت‌ها"""
    
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.admin_panel = AdminPanel(self)
        self._setup_handlers()
        self._init_settings()
        
    def _init_settings(self):
        """مقداردهی اولیه تنظیمات"""
        try:
            cursor = db.execute(0,
                "SELECT value FROM settings WHERE key = 'bot_started'"
            )
            if not cursor.fetchone():
                db.execute(0,
                    "INSERT INTO settings (key, value) VALUES ('bot_started', 'true')"
                )
                logger.info("تنظیمات اولیه ایجاد شد")
        except Exception as e:
            logger.error(f"Error initializing settings: {e}")
            
    def _setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        app = self.application
        
        # دستورات عمومی
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("referral", self.referral_command))
        app.add_handler(CommandHandler("language", self.language_command))
        
        # دکمه‌های منو
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language$"))
        
        # دکمه‌های قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.join_lottery_callback, pattern="^join_lottery$"))
        app.add_handler(CallbackQueryHandler(self.verify_payment_callback, pattern="^verify_payment$"))
        
        # دکمه‌های پنل مدیریت
        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_start_lottery_callback, pattern="^admin_start_lottery$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_poll_callback, pattern="^admin_poll$"))
        app.add_handler(CallbackQueryHandler(self.admin_pay_winners_callback, pattern="^admin_pay_winners$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api_callback, pattern="^admin_add_api$"))
        app.add_handler(CallbackQueryHandler(self.admin_stats_callback, pattern="^admin_stats$"))
        
        # مراحل قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.start_lottery_confirm_callback, pattern="^start_lottery_confirm$"))
        app.add_handler(CallbackQueryHandler(self.start_lottery_winners_callback, pattern="^start_lottery_winners$"))
        app.add_handler(CallbackQueryHandler(self.start_lottery_prize_callback, pattern="^start_lottery_prize$"))
        app.add_handler(CallbackQueryHandler(self.start_lottery_final_callback, pattern="^start_lottery_final$"))
        
        # برداشت جایزه
        app.add_handler(CallbackQueryHandler(self.withdraw_prize_callback, pattern="^withdraw_prize$"))
        app.add_handler(CallbackQueryHandler(self.confirm_withdraw_callback, pattern="^confirm_withdraw$"))
        
        # مدیریت پیام‌ها
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # مدیریت خطاها
        app.add_error_handler(self.error_handler)
        
    # ============================================================
    # دستورات عمومی
    # ============================================================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start - نمایش دکمه پلی"""
        user = update.effective_user
        
        # ثبت کاربر
        user_manager.register_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name
        )
        
        # زبان کاربر
        lang = self._get_user_language(user.id)
        
        # دکمه پلی
        keyboard = [[InlineKeyboardButton("▶️ PLAY", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 **Welcome to UTYOB Lottery Bot!**\n\n"
            "💰 Win amazing prizes up to $10,000!\n"
            "🎯 Fair and transparent lottery system\n"
            "🌟 Join now and test your luck!\n\n"
            "Click PLAY to enter the game.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /help"""
        help_text = """
📖 **راهنمای ربات UTYOB**

🎯 **درباره ربات:**
ربات قرعه‌کشی هوشمند با جایزه‌های نقدی

🎰 **چگونه شرکت کنیم:**
1. اشتراک تهیه کنید
2. مبلغ ۱۰۰ دلار واریز کنید
3. در قرعه‌کشی شرکت کنید
4. شانس برنده شدن داشته باشید

💰 **جایزه‌ها:**
- قرعه‌کشی‌های روزانه
- جوایز تا ۱۰۰۰۰ دلار
- واریز فوری به کیف پول

🔗 **سیستم رفرال:**
با دعوت دوستان، پاداش بگیرید

📞 **پشتیبانی:**
در صورت نیاز با مدیریت تماس بگیرید
        """
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /referral"""
        user_id = update.effective_user.id
        await self._show_referral(update, user_id)
        
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /language"""
        await self._show_language_selector(update, update.effective_user.id)
        
    # ============================================================
    # کالبک‌های منوی اصلی
    # ============================================================
    
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی اصلی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        keyboard = [
            [InlineKeyboardButton("🎰 شرکت در قرعه‌کشی", callback_data="lottery")],
            [InlineKeyboardButton("🔗 رفرال و دعوت دوستان", callback_data="referral")],
            [InlineKeyboardButton("📖 راهنمایی و قوانین", callback_data="guide")],
            [InlineKeyboardButton("🌐 تغییر زبان", callback_data="language")]
        ]
        
        # دکمه پنل مدیریت برای ادمین‌ها
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 **UTYOB Lottery Bot**\n\n"
            "یکی از گزینه‌های زیر را انتخاب کنید:\n"
            "👇👇👇",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # بررسی اشتراک
        user = user_manager.get_user(user_id)
        if not user or not user['has_subscription']:
            keyboard = [
                [InlineKeyboardButton("🔄 تمدید اشتراک", callback_data="main_menu")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ **شما اشتراک فعال ندارید!**\n\n"
                "برای شرکت در قرعه‌کشی، ابتدا باید اشتراک تهیه کنید.\n\n"
                "💰 هزینه اشتراک: ۱۰۰ دلار\n"
                "📅 مدت اعتبار: ۱ ماه\n\n"
                "برای تهیه اشتراک، روی دکمه زیر کلیک کنید.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # نمایش وضعیت قرعه‌کشی
        keyboard = [
            [InlineKeyboardButton("✅ شرکت در قرعه‌کشی", callback_data="join_lottery")],
            [InlineKeyboardButton("📊 آخرین نتایج", callback_data="last_results")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎰 **قرعه‌کشی UTYOB**\n\n"
            f"👤 کاربر: {user['first_name'] or user_id}\n"
            f"📅 تاریخ عضویت: {user['created_at']}\n\n"
            "💰 **جوایز:**\n"
            "• جایزه اول: تا ۵۰۰۰ دلار\n"
            "• جایزه دوم: تا ۲۰۰۰ دلار\n"
            "• جایزه سوم: تا ۱۰۰۰ دلار\n\n"
            "📊 تعداد شرکت‌کنندگان: متغیر\n"
            "🎯 شانس برنده شدن: عادلانه و شفاف",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def referral_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش اطلاعات رفرال"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        await self._show_referral(update, user_id)
        
    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش راهنمایی"""
        query = update.callback_query
        await query.answer()
        
        guide_text = """
📖 **راهنمای کامل ربات UTYOB**

🎯 **نحوه کار:**
1. **ثبت‌نام**: با دستور /start ثبت‌نام کنید
2. **اشتراک**: برای شرکت در قرعه‌کشی، اشتراک تهیه کنید
3. **واریز**: مبلغ ۱۰۰ دلار به آدرس مشخص واریز کنید
4. **شرکت**: پس از تایید، در قرعه‌کشی شرکت کنید
5. **برنده**: در صورت برنده شدن، جایزه دریافت کنید

💰 **مبلغ واریز:**
- مبلغ ثابت: ۱۰۰ دلار
- آدرس واریز: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A
- شبکه: TRC20

🎁 **جوایز:**
- جایزه اول: ۵۰٪ از کل مبلغ
- جایزه دوم: ۳۰٪ از کل مبلغ  
- جایزه سوم: ۲۰٪ از کل مبلغ

🔗 **سیستم رفرال:**
- هر کاربر کد رفرال اختصاصی دارد
- به ازای هر دعوت، ۵٪ پاداش دریافت کنید

⚠️ **قوانین:**
- هر کاربر فقط یک بار در هر قرعه‌کشی شرکت می‌کند
- برندگان قبلی شانس کمتری در قرعه‌کشی‌های بعدی دارند
- تمامی تراکنش‌ها به صورت خودکار تایید می‌شوند

📞 **پشتیبانی:**
برای سوالات و مشکلات با مدیریت تماس بگیرید.
        """
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            guide_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تغییر زبان"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        await self._show_language_selector(update, user_id)
        
    # ============================================================
    # کالبک‌های شرکت در قرعه‌کشی
    # ============================================================
    
    async def join_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شرکت در قرعه‌کشی - دریافت آدرس کیف پول"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # بررسی اشتراک
        user = user_manager.get_user(user_id)
        if not user or not user['has_subscription']:
            await query.edit_message_text(
                "❌ شما اشتراک فعال ندارید!\n\n"
                "لطفاً ابتدا اشتراک تهیه کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                ])
            )
            return
            
        # بررسی شرکت قبلی در قرعه‌کشی فعلی
        if self._has_participated(user_id):
            await query.edit_message_text(
                "⚠️ شما قبلاً در این قرعه‌کشی شرکت کرده‌اید!\n\n"
                "منتظر قرعه‌کشی بعدی باشید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                ])
            )
            return
            
        # ذخیره وضعیت برای دریافت آدرس
        context.user_data['waiting_for_wallet'] = True
        
        keyboard = [
            [InlineKeyboardButton("✅ تایید واریز", callback_data="verify_payment")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💳 **واریز برای شرکت در قرعه‌کشی**\n\n"
            "لطفاً آدرس کیف پول مبدا (TRC20) خود را وارد کنید:\n\n"
            "🔹 **مبلغ واریز:** ۱۰۰ دلار\n"
            "🔹 **آدرس مقصد:**\n"
            f"`{DESTINATION_WALLET}`\n\n"
            "⚠️ **نکات مهم:**\n"
            "• فقط از شبکه TRC20 استفاده کنید\n"
            "• مبلغ دقیقاً ۱۰۰ دلار باشد\n"
            "• پس از واریز، سیستم به صورت خودکار تایید می‌کند\n"
            "• کد تراکنش را برای پیگیری ذخیره کنید\n\n"
            "📤 **آدرس مبدا خود را وارد کنید:**",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def verify_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید پرداخت"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # بررسی اینکه آیا کاربر آدرس وارد کرده
        if not context.user_data.get('waiting_for_wallet'):
            await query.edit_message_text(
                "⚠️ لطفاً ابتدا آدرس کیف پول خود را وارد کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                ])
            )
            return
            
        # دریافت آدرس کیف پول از دیتابیس
        user = user_manager.get_user(user_id)
        if not user or not user['wallet_address']:
            await query.edit_message_text(
                "❌ آدرس کیف پول یافت نشد!\n\n"
                "لطفاً آدرس خود را مجدداً وارد کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                ])
            )
            return
            
        # تایید خودکار پرداخت
        await query.edit_message_text(
            "⏳ در حال بررسی پرداخت شما...\n"
            "لطفاً چند لحظه صبر کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # اجرای تایید پرداخت
        result = await self._auto_verify_payment(
            user_id,
            user['wallet_address'],
            DESTINATION_WALLET,
            PAYMENT_AMOUNT
        )
        
        if result['success']:
            await query.edit_message_text(
                "✅ **پرداخت شما تایید شد!**\n\n"
                f"🔹 مبلغ: ${PAYMENT_AMOUNT}\n"
                f"🔹 تراکنش: `{result['tx_id']}`\n\n"
                "🎉 شما با موفقیت در قرعه‌کشی ثبت نام کردید.\n"
                "🙏 برای شما آرزوی موفقیت داریم!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎰 بازگشت به قرعه‌کشی", callback_data="lottery")],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # اطلاع به ادمین‌ها
            for admin_id in ADMIN_IDS:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=f"✅ **پرداخت جدید تایید شد**\n\n"
                         f"👤 کاربر: {user_id}\n"
                         f"💰 مبلغ: ${PAYMENT_AMOUNT}\n"
                         f"🔗 تراکنش: {result['tx_id']}\n"
                         f"📤 از: {user['wallet_address']}",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await query.edit_message_text(
                "❌ **پرداخت شما تایید نشد!**\n\n"
                f"🔹 دلیل: {result['message']}\n\n"
                "📌 **راهکارها:**\n"
                "1. مبلغ دقیقاً ۱۰۰ دلار باشد\n"
                "2. آدرس مقصد صحیح باشد\n"
                "3. تراکنش انجام شده باشد\n"
                "4. از شبکه TRC20 استفاده کنید\n\n"
                "🔄 پس از بررسی، مجدداً تلاش کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="join_lottery")],
                    [InlineKeyboardButton("📞 پشتیبانی", callback_data="main_menu")],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # اطلاع به ادمین‌ها برای بررسی دستی
            for admin_id in ADMIN_IDS:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ **پرداخت تایید نشد - نیاز به بررسی دستی**\n\n"
                         f"👤 کاربر: {user_id}\n"
                         f"💰 مبلغ: ${PAYMENT_AMOUNT}\n"
                         f"📤 از: {user['wallet_address']}\n"
                         f"📥 به: {DESTINATION_WALLET}\n"
                         f"🔹 دلیل: {result['message']}",
                    parse_mode=ParseMode.MARKDOWN
                )
                
    # ============================================================
    # کالبک‌های پنل مدیریت
    # ============================================================
    
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل مدیریت"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            await query.edit_message_text(
                "⛔ دسترسی غیرمجاز!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                ])
            )
            return
            
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton("✅ تایید دستی کاربران", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📊 ارسال نظرسنجی", callback_data="admin_poll")],
            [InlineKeyboardButton("💰 واریز به برندگان", callback_data="admin_pay_winners")],
            [InlineKeyboardButton("🔑 اضافه کردن API جدید", callback_data="admin_add_api")],
            [InlineKeyboardButton("📈 آمار و اطلاعات", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # دریافت آمار
        user_count = user_manager.get_user_count()
        active_users = len(user_manager.get_active_users())
        
        stats_text = (
            f"⚙️ **پنل مدیریت**\n\n"
            f"📊 **آمار:**\n"
            f"• کل کاربران: {user_count:,}\n"
            f"• کاربران فعال: {active_users:,}\n"
            f"• کش: {cache.get_stats()['size']} آیتم\n"
            f"• API‌ها: {len(payment_verifier.apis)}\n\n"
            f"انتخاب کنید:"
        )
        
        await query.edit_message_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال پیام همگانی"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'broadcast'
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📢 **ارسال پیام همگانی**\n\n"
            "لطفاً متن پیام را ارسال کنید:\n\n"
            "⚠️ **توجه:**\n"
            "• این پیام به تمام کاربران ارسال می‌شود\n"
            "• از مارک‌داون برای قالب‌بندی استفاده کنید\n"
            "• برای انصراف، دکمه بازگشت را بزنید",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def admin_start_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        # بررسی اینکه قرعه‌کشی در حال اجرا نباشد
        if lottery_system.is_running:
            await query.edit_message_text(
                "⚠️ **قرعه‌کشی در حال اجراست!**\n\n"
                "لطفاً تا پایان قرعه‌کشی فعلی صبر کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
                ])
            )
            return
            
        context.user_data['admin_action'] = 'start_lottery'
        context.user_data['lottery_step'] = 1
        
        keyboard = [
            [InlineKeyboardButton("✅ تایید شروع", callback_data="start_lottery_confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # تعداد کاربران واجد شرایط
        eligible = lottery_system._get_eligible_users()
        
        await query.edit_message_text(
            "🎰 **شروع قرعه‌کشی جدید**\n\n"
            f"👥 کاربران واجد شرایط: {len(eligible)} نفر\n\n"
            "آیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟\n\n"
            "⚠️ **توجه:**\n"
            "• تمام کاربران دارای اشتراک شرکت می‌کنند\n"
            "• برندگان قبلی شانس کمتری دارند\n"
            "• قرعه‌کشی به صورت عادلانه انجام می‌شود",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید دستی کاربران"""
        query = update.callback_query
        await query.answer()
        
        # دریافت تراکنش‌های تایید نشده
        transactions = self._get_pending_transactions()
        
        if not transactions:
            await query.edit_message_text(
                "✅ **همه تراکنش‌ها تایید شده‌اند!**\n\n"
                "هیچ تراکنش تایید نشده‌ای وجود ندارد.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
                ])
            )
            return
            
        # نمایش تراکنش‌های تایید نشده
        text = "✅ **تایید دستی تراکنش‌ها**\n\n"
        for tx in transactions[:10]:
            text += f"👤 کاربر: {tx['user_id']}\n"
            text += f"💰 مبلغ: ${tx['amount']}\n"
            text += f"📤 از: {tx['from_address']}\n"
            text += f"📥 به: {tx['to_address']}\n"
            text += f"🔄 وضعیت: {tx['status']}\n\n"
            
        text += f"📊 تعداد کل: {len(transactions)}\n"
        text += "برای تایید هر کاربر، دستور `/verify USER_ID` را ارسال کنید."
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ])
        )
        
    async def admin_poll_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال نظرسنجی"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'create_poll'
        
        await query.edit_message_text(
            "📊 **ایجاد نظرسنجی جدید**\n\n"
            "لطفاً سوال نظرسنجی را ارسال کنید:\n\n"
            "مثال: `نظر شما درباره قرعه‌کشی چیست؟`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]
            ])
        )
        
    async def admin_pay_winners_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """واریز به برندگان"""
        query = update.callback_query
        await query.answer()
        
        # دریافت برندگان تایید نشده
        winners = self._get_unpaid_winners()
        
        if not winners:
            await query.edit_message_text(
                "✅ **همه برندگان پرداخت شده‌اند!**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
                ])
            )
            return
            
        text = "💰 **واریز به برندگان**\n\n"
        for winner in winners[:10]:
            text += f"👤 کاربر: {winner['user_id']}\n"
            text += f"💰 مبلغ: ${winner['prize_amount']}\n"
            text += f"📤 آدرس: {winner['wallet_address'] or 'نامشخص'}\n\n"
            
        text += f"📊 تعداد کل: {len(winners)}\n"
        text += "برای پرداخت، دستور `/pay USER_ID` را ارسال کنید."
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ])
        )
        
    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اضافه کردن API جدید"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'add_api'
        
        await query.edit_message_text(
            "🔑 **اضافه کردن API جدید**\n\n"
            "لطفاً کلید API جدید را وارد کنید:\n\n"
            "⚠️ **نکات:**\n"
            "• API برای تایید تراکنش‌ها استفاده می‌شود\n"
            "• هر API می‌تواند هزاران کاربر را پوشش دهد\n"
            "• API‌های بیشتر = سرعت بیشتر",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]
            ])
        )
        
    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار کامل"""
        query = update.callback_query
        await query.answer()
        
        # جمع‌آوری آمار
        user_count = user_manager.get_user_count()
        active_users = len(user_manager.get_active_users())
        cache_stats = cache.get_stats()
        
        # آمار تراکنش‌ها
        tx_stats = self._get_transaction_stats()
        
        # آمار قرعه‌کشی
        lottery_stats = self._get_lottery_stats()
        
        stats_text = (
            f"📈 **آمار کامل سیستم**\n\n"
            f"👥 **کاربران:**\n"
            f"• کل: {user_count:,}\n"
            f"• فعال: {active_users:,}\n"
            f"• درصد فعال: {(active_users/user_count*100):.1f}%\n\n"
            f"💳 **تراکنش‌ها:**\n"
            f"• کل: {tx_stats['total']:,}\n"
            f"• تایید شده: {tx_stats['verified']:,}\n"
            f"• در انتظار: {tx_stats['pending']:,}\n\n"
            f"🎰 **قرعه‌کشی:**\n"
            f"• تعداد: {lottery_stats['total']}\n"
            f"• برندگان کل: {lottery_stats['total_winners']}\n"
            f"• آخرین: {lottery_stats['last'] or 'ندارد'}\n\n"
            f"⚡ **سیستم:**\n"
            f"• کش: {cache_stats['size']} آیتم\n"
            f"• نرخ برخورد: {cache_stats['hit_rate']:.1f}%\n"
            f"• API‌ها: {len(payment_verifier.apis)}\n"
            f"• شاردها: {DB_SHARDS}"
        )
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="admin_stats")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        
    # ============================================================
    # کالبک‌های مراحل قرعه‌کشی
    # ============================================================
    
    async def start_lottery_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید شروع قرعه‌کشی - دریافت تعداد برندگان"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['lottery_step'] = 2
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 **تعداد برندگان**\n\n"
            "لطفاً تعداد برندگان این قرعه‌کشی را وارد کنید:\n"
            "(حداکثر ۱۰۰ نفر)\n\n"
            "مثال: `5`",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def start_lottery_winners_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت تعداد برندگان"""
        # این کالبک توسط handle_message مدیریت می‌شود
        pass
        
    async def start_lottery_prize_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت مبلغ جایزه"""
        # این کالبک توسط handle_message مدیریت می‌شود
        pass
        
    async def start_lottery_final_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مرحله نهایی شروع قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        # دریافت اطلاعات از context
        winners_count = context.user_data.get('lottery_winners', 1)
        prize_per_winner = context.user_data.get('lottery_prize', 100)
        
        # اجرای قرعه‌کشی
        success, result = lottery_system.start_lottery(winners_count, prize_per_winner)
        
        if success:
            # ارسال پیام به برندگان
            for user_id in result['winners']:
                keyboard = [
                    [InlineKeyboardButton("💰 برداشت جایزه", callback_data="withdraw_prize")],
                    [InlineKeyboardButton("🎰 قرعه‌کشی بعدی", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=f"🎉 **تبریک! شما برنده شدید!** 🎉\n\n"
                             f"💰 مبلغ جایزه: **${prize_per_winner:,}**\n"
                             f"🏆 قرعه‌کشی شماره: {result['lottery_id']}\n\n"
                             f"✅ برای برداشت جایزه، روی دکمه زیر کلیک کنید:\n"
                             f"📌 آدرس کیف پول خود را وارد کنید",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Error sending message to {user_id}: {e}")
                    
            # گزارش به ادمین
            winners_list = "\n".join([f"• کاربر {uid}" for uid in result['winners']])
            
            await query.edit_message_text(
                f"✅ **قرعه‌کشی با موفقیت انجام شد!** 🎉\n\n"
                f"📊 **جزئیات:**\n"
                f"• شماره قرعه‌کشی: {result['lottery_id']}\n"
                f"• تعداد برندگان: {winners_count}\n"
                f"• جایزه هر نفر: ${prize_per_winner:,}\n"
                f"• کل جایزه: ${winners_count * prize_per_winner:,}\n\n"
                f"👥 **برندگان:**\n{winners_list}\n\n"
                f"✅ پیام‌های تبریک به برندگان ارسال شد.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # ثبت در تاریخچه
            logger.info(f"Lottery {result['lottery_id']} completed with {winners_count} winners")
            
        else:
            await query.edit_message_text(
                f"❌ **خطا در اجرای قرعه‌کشی**\n\n"
                f"🔹 دلیل: {result}\n\n"
                "لطفاً موارد زیر را بررسی کنید:\n"
                "• تعداد کاربران واجد شرایط\n"
                "• تعداد برندگان وارد شده\n"
                "• اتصال به دیتابیس",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="admin_start_lottery")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            
    # ============================================================
    # کالبک‌های برداشت جایزه
    # ============================================================
    
    async def withdraw_prize_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """برداشت جایزه - دریافت آدرس کیف پول"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # بررسی اینکه کاربر برنده شده
        winner = self._check_winner(user_id)
        if not winner:
            await query.edit_message_text(
                "❌ شما برنده‌ای ندارید!\n\n"
                "در قرعه‌کشی‌های بعدی شرکت کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎰 شرکت در قرعه‌کشی", callback_data="lottery")],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
                ])
            )
            return
            
        # اگر جایزه قبلاً پرداخت شده
        if winner['paid_status'] == 1:
            await query.edit_message_text(
                "✅ جایزه شما قبلاً پرداخت شده است!\n\n"
                f"💰 مبلغ: ${winner['prize_amount']}\n"
                f"📅 تاریخ: {winner['paid_at']}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
                ])
            )
            return
            
        # ذخیره وضعیت برای دریافت آدرس
        context.user_data['withdraw_pending'] = True
        context.user_data['winner_id'] = winner['id']
        
        keyboard = [
            [InlineKeyboardButton("✅ تایید آدرس", callback_data="confirm_withdraw")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💰 **برداشت جایزه**\n\n"
            f"مبلغ جایزه: **${winner['prize_amount']:,}**\n\n"
            f"لطفاً آدرس کیف پول TRC20 خود را وارد کنید:\n\n"
            f"⚠️ **نکات مهم:**\n"
            f"• فقط از شبکه TRC20 استفاده کنید\n"
            f"• آدرس باید دقیق و صحیح باشد\n"
            f"• پس از تایید، واریز انجام می‌شود\n\n"
            f"📤 **آدرس کیف پول خود را وارد کنید:**",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def confirm_withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید برداشت"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # بررسی وضعیت برداشت
        if not context.user_data.get('withdraw_pending'):
            await query.edit_message_text(
                "⚠️ هیچ درخواست برداشتی در انتظار نیست.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                ])
            )
            return
            
        # دریافت آدرس کیف پول
        user = user_manager.get_user(user_id)
        if not user or not user['wallet_address']:
            await query.edit_message_text(
                "❌ آدرس کیف پول یافت نشد!\n\n"
                "لطفاً آدرس خود را وارد کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                ])
            )
            return
            
        # به‌روزرسانی برنده
        winner_id = context.user_data.get('winner_id')
        if winner_id:
            db.execute(user_id,
                """UPDATE winners 
                   SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (user['wallet_address'], winner_id)
            )
            
            context.user_data['withdraw_pending'] = False
            
            # پیام تایید به کاربر
            await query.edit_message_text(
                f"✅ **برداشت شما با موفقیت ثبت شد!** 🎉\n\n"
                f"💰 مبلغ: ${user.get('prize_amount', 0):,}\n"
                f"📤 آدرس: {user['wallet_address']}\n\n"
                "⏳ مبلغ به زودی به حساب شما واریز می‌شود.\n"
                "🔔 پس از واریز، به شما اطلاع داده می‌شود.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎰 قرعه‌کشی بعدی", callback_data="lottery")],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=f"💰 **درخواست برداشت جدید**\n\n"
                         f"👤 کاربر: {user_id}\n"
                         f"💰 مبلغ: ${user.get('prize_amount', 0):,}\n"
                         f"📤 آدرس: {user['wallet_address']}\n\n"
                         f"✅ جهت واریز، به پنل مدیریت مراجعه کنید.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
    # ============================================================
    # توابع کمکی
    # ============================================================
    
    async def _show_referral(self, update, user_id):
        """نمایش اطلاعات رفرال"""
        user = user_manager.get_user(user_id)
        if not user:
            return
            
        referral_code = user['referral_code']
        bot_username = "UTYOB_Bot"
        referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
        
        # تعداد دعوت‌ها
        referred_count = len(db.execute_global(
            "SELECT user_id FROM users WHERE referred_by = ?",
            (user_id,)
        ))
        
        text = (
            f"🔗 **سیستم رفرال UTYOB**\n\n"
            f"👤 شما: {user['first_name'] or user_id}\n"
            f"📊 تعداد دعوت‌ها: {referred_count}\n\n"
            f"🔑 **کد رفرال شما:**\n"
            f"`{referral_code}`\n\n"
            f"🔗 **لینک دعوت:**\n"
            f"{referral_link}\n\n"
            f"💰 **پاداش دعوت:**\n"
            f"• به ازای هر دعوت: ۵٪ از واریز\n"
            f"• پاداش فوری پس از تایید\n\n"
            f"📤 لینک را برای دوستان خود ارسال کنید!"
        )
        
        keyboard = [
            [InlineKeyboardButton("📤 اشتراک‌گذاری", url=f"https://t.me/share/url?url={referral_link}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if isinstance(update, Update):
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
    async def _show_language_selector(self, update, user_id):
        """نمایش انتخابگر زبان"""
        current_lang = self._get_user_language(user_id)
        
        languages = {
            'en': '🇬🇧 English',
            'fa': '🇮🇷 فارسی',
            'tr': '🇹🇷 Türkçe'
        }
        
        keyboard = []
        for code, name in languages.items():
            if code == current_lang:
                name = f"✅ {name}"
            keyboard.append([InlineKeyboardButton(name, callback_data=f"set_lang_{code}")])
            
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"🌐 **تغییر زبان**\n\nزبان فعلی: {languages.get(current_lang, 'English')}"
        
        if isinstance(update, Update):
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
    async def _auto_verify_payment(self, user_id, from_address, to_address, amount):
        """تایید خودکار پرداخت"""
        try:
            # بررسی در کش
            cache_key = f"payment_{from_address}_{to_address}_{amount}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
                
            # تایید با سیستم پرداخت
            success, tx_id, message = await payment_verifier.verify_transaction(
                from_address, to_address, amount
            )
            
            if success:
                # ثبت تراکنش
                db.execute(user_id,
                    """INSERT INTO transactions 
                       (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
                       VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)""",
                    (user_id, from_address, to_address, amount, tx_id)
                )
                
                # به‌روزرسانی کاربر
                db.execute(user_id,
                    "UPDATE users SET total_participations = total_participations + 1 WHERE user_id = ?",
                    (user_id,)
                )
                
                result = {
                    'success': True,
                    'tx_id': tx_id,
                    'message': 'Verified'
                }
                
            else:
                # ثبت تراکنش ناموفق
                db.execute(user_id,
                    """INSERT INTO transactions 
                       (user_id, from_address, to_address, amount, status) 
                       VALUES (?, ?, ?, ?, 'failed')""",
                    (user_id, from_address, to_address, amount)
                )
                
                result = {
                    'success': False,
                    'tx_id': None,
                    'message': message or 'Verification failed'
                }
                
            # ذخیره در کش
            cache.set(cache_key, result, ttl=60)  # ۱ دقیقه کش
            return result
            
        except Exception as e:
            logger.error(f"Error in auto verify payment: {e}")
            return {
                'success': False,
                'tx_id': None,
                'message': str(e)
            }
            
    def _get_user_language(self, user_id):
        """دریافت زبان کاربر"""
        user = user_manager.get_user(user_id)
        return user['language'] if user else 'en'
        
    def _has_participated(self, user_id):
        """بررسی شرکت قبلی در قرعه‌کشی فعلی"""
        # بررسی تراکنش‌های تایید شده امروز
        cursor = db.execute(user_id,
            """SELECT COUNT(*) as count FROM transactions 
               WHERE user_id = ? 
               AND status = 'verified' 
               AND date(created_at) = date('now')""",
            (user_id,)
        )
        result = cursor.fetchone()
        return result['count'] > 0
        
    def _get_pending_transactions(self):
        """دریافت تراکنش‌های تایید نشده"""
        results = db.execute_global(
            "SELECT * FROM transactions WHERE status = 'pending' OR status = 'failed'"
        )
        return results
        
    def _get_unpaid_winners(self):
        """دریافت برندگان پرداخت نشده"""
        results = db.execute_global(
            "SELECT * FROM winners WHERE paid_status = 0"
        )
        return results
        
    def _check_winner(self, user_id):
        """بررسی برنده بودن کاربر"""
        cursor = db.execute(user_id,
            """SELECT * FROM winners 
               WHERE user_id = ? 
               AND paid_status = 0 
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,)
        )
        return cursor.fetchone()
        
    def _get_transaction_stats(self):
        """آمار تراکنش‌ها"""
        results = db.execute_global(
            "SELECT status, COUNT(*) as count FROM transactions GROUP BY status"
        )
        stats = {'total': 0, 'verified': 0, 'pending': 0, 'failed': 0}
        for row in results:
            stats['total'] += row['count']
            if row['status'] == 'verified':
                stats['verified'] += row['count']
            elif row['status'] == 'pending':
                stats['pending'] += row['count']
            elif row['status'] == 'failed':
                stats['failed'] += row['count']
        return stats
        
    def _get_lottery_stats(self):
        """آمار قرعه‌کشی"""
        cursor = db.execute(0,
            "SELECT COUNT(*) as total FROM lotteries"
        )
        total = cursor.fetchone()['total']
        
        cursor = db.execute(0,
            "SELECT COUNT(*) as total_winners FROM winners"
        )
        total_winners = cursor.fetchone()['total_winners']
        
        cursor = db.execute(0,
            "SELECT started_at FROM lotteries ORDER BY started_at DESC LIMIT 1"
        )
        last = cursor.fetchone()
        
        return {
            'total': total,
            'total_winners': total_winners,
            'last': last['started_at'] if last else None
        }
        
    # ============================================================
    # مدیریت پیام‌ها
    # ============================================================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت پیام‌های دریافتی"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # بررسی اقدامات ادمین
        admin_action = context.user_data.get('admin_action')
        
        if admin_action == 'broadcast':
            # ارسال پیام همگانی
            await self._send_broadcast(update, text, context)
            return
            
        elif admin_action == 'start_lottery':
            # مدیریت مراحل قرعه‌کشی
            await self._handle_lottery_steps(update, text, context)
            return
            
        elif admin_action == 'add_api':
            # اضافه کردن API
            await self._handle_add_api(update, text, context)
            return
            
        elif admin_action == 'create_poll':
            # ایجاد نظرسنجی
            await self._handle_create_poll(update, text, context)
            return
            
        # بررسی انتظار برای آدرس کیف پول
        if context.user_data.get('waiting_for_wallet'):
            await self._handle_wallet_address(update, text, context)
            return
            
        # بررسی انتظار برای آدرس برداشت
        if context.user_data.get('withdraw_pending'):
            await self._handle_withdraw_address(update, text, context)
            return
            
        # پیام معمولی
        await update.message.reply_text(
            "⚠️ دستور نامعتبر!\n\n"
            "از دکمه‌های موجود استفاده کنید یا /help را ببینید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ])
        )
        
    async def _handle_wallet_address(self, update, text, context):
        """مدیریت آدرس کیف پول برای شرکت در قرعه‌کشی"""
        user_id = update.effective_user.id
        wallet_address = text.strip()
        
        # اعتبارسنجی آدرس
        if not self._validate_wallet_address(wallet_address):
            await update.message.reply_text(
                "❌ آدرس کیف پول نامعتبر!\n\n"
                "لطفاً یک آدرس معتبر TRC20 وارد کنید.\n"
                "مثال: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # ذخیره آدرس
        user_manager.update_user(user_id, wallet_address=wallet_address)
        context.user_data['waiting_for_wallet'] = False
        
        # تایید خودکار پرداخت
        result = await self._auto_verify_payment(
            user_id,
            wallet_address,
            DESTINATION_WALLET,
            PAYMENT_AMOUNT
        )
        
        if result['success']:
            await update.message.reply_text(
                f"✅ **پرداخت شما تایید شد!** 🎉\n\n"
                f"💰 مبلغ: ${PAYMENT_AMOUNT}\n"
                f"🔗 تراکنش: `{result['tx_id']}`\n\n"
                "🎉 با موفقیت در قرعه‌کشی ثبت نام کردید.\n"
                "🙏 برای شما آرزوی موفقیت داریم!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎰 قرعه‌کشی", callback_data="lottery")],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"❌ **پرداخت شما تایید نشد!**\n\n"
                f"🔹 دلیل: {result['message']}\n\n"
                "لطفاً موارد زیر را بررسی کنید:\n"
                "• مبلغ دقیقاً ۱۰۰ دلار باشد\n"
                "• آدرس مقصد صحیح باشد\n"
                "• تراکنش انجام شده باشد\n\n"
                "🔄 پس از بررسی، مجدداً تلاش کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="join_lottery")],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            
    async def _handle_withdraw_address(self, update, text, context):
        """مدیریت آدرس برای برداشت جایزه"""
        user_id = update.effective_user.id
        wallet_address = text.strip()
        
        # اعتبارسنجی آدرس
        if not self._validate_wallet_address(wallet_address):
            await update.message.reply_text(
                "❌ آدرس کیف پول نامعتبر!\n\n"
                "لطفاً یک آدرس معتبر TRC20 وارد کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # ذخیره آدرس
        user_manager.update_user(user_id, wallet_address=wallet_address)
        
        # به‌روزرسانی برنده
        winner_id = context.user_data.get('winner_id')
        if winner_id:
            db.execute(user_id,
                """UPDATE winners 
                   SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (wallet_address, winner_id)
            )
            
            context.user_data['withdraw_pending'] = False
            
            await update.message.reply_text(
                f"✅ **برداشت شما با موفقیت ثبت شد!** 🎉\n\n"
                f"💰 مبلغ: ${await self._get_winner_amount(user_id):,}\n"
                f"📤 آدرس: {wallet_address}\n\n"
                "⏳ مبلغ به زودی به حساب شما واریز می‌شود.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎰 قرعه‌کشی بعدی", callback_data="lottery")],
                    [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=f"💰 **درخواست برداشت جدید**\n\n"
                         f"👤 کاربر: {user_id}\n"
                         f"📤 آدرس: {wallet_address}\n\n"
                         f"✅ جهت واریز، به پنل مدیریت مراجعه کنید.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
    async def _handle_lottery_steps(self, update, text, context):
        """مدیریت مراحل شروع قرعه‌کشی"""
        step = context.user_data.get('lottery_step', 1)
        
        if step == 2:
            # دریافت تعداد برندگان
            try:
                winners_count = int(text)
                if 1 <= winners_count <= 100:
                    context.user_data['lottery_winners'] = winners_count
                    context.user_data['lottery_step'] = 3
                    
                    await update.message.reply_text(
                        f"✅ تعداد برندگان: {winners_count}\n\n"
                        f"💰 **مبلغ جایزه هر نفر**\n\n"
                        f"لطفاً مبلغ جایزه برای هر برنده را وارد کنید:\n"
                        f"(حداقل ۱۰ دلار)\n\n"
                        f"مثال: `100`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        "❌ تعداد نامعتبر!\n"
                        "لطفاً عددی بین ۱ تا ۱۰۰ وارد کنید."
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ لطفاً یک عدد معتبر وارد کنید!"
                )
                
        elif step == 3:
            # دریافت مبلغ جایزه
            try:
                prize = float(text)
                if prize >= 10:
                    context.user_data['lottery_prize'] = prize
                    context.user_data['lottery_step'] = 4
                    
                    winners = context.user_data['lottery_winners']
                    total_prize = winners * prize
                    
                    keyboard = [
                        [InlineKeyboardButton("✅ تایید نهایی", callback_data="start_lottery_final")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"✅ **اطلاعات قرعه‌کشی:**\n\n"
                        f"• تعداد برندگان: {winners}\n"
                        f"• جایزه هر نفر: ${prize:,}\n"
                        f"• کل جایزه: ${total_prize:,}\n\n"
                        f"⚠️ آیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        "❌ مبلغ جایزه باید حداقل ۱۰ دلار باشد!"
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ لطفاً یک عدد معتبر وارد کنید!"
                )
                
    async def _handle_add_api(self, update, text, context):
        """اضافه کردن API جدید"""
        api_key = text.strip()
        
        if payment_verifier.add_api(api_key):
            context.user_data['admin_action'] = None
            await update.message.reply_text(
                f"✅ **API جدید با موفقیت اضافه شد!**\n\n"
                f"🔑 کلید: `{api_key}`\n"
                f"📊 تعداد کل API‌ها: {len(payment_verifier.apis)}\n\n"
                "این API برای تایید تراکنش‌ها استفاده می‌شود.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "❌ **خطا در اضافه کردن API!**\n\n"
                "این API قبلاً اضافه شده است یا نامعتبر است.",
                parse_mode=ParseMode.MARKDOWN
            )
            
    async def _handle_create_poll(self, update, text, context):
        """ایجاد نظرسنجی"""
        context.user_data['poll_question'] = text
        context.user_data['poll_step'] = 2
        
        await update.message.reply_text(
            "📊 **گزینه‌های نظرسنجی**\n\n"
            "لطفاً گزینه‌های نظرسنجی را وارد کنید (هر گزینه در یک خط):\n\n"
            "مثال:\n"
            "عالی بود\n"
            "خوب بود\n"
            "متوسط\n"
            "ضعیف",
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def _send_broadcast(self, update, text, context):
        """ارسال پیام همگانی"""
        await update.message.reply_text(
            "⏳ در حال ارسال پیام به کاربران...\n"
            "لطفاً صبر کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # دریافت تمام کاربران
        users = db.execute_global("SELECT user_id FROM users")
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(
                    chat_id=user['user_id'],
                    text=text,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                
                # تأخیر برای جلوگیری از محدودیت
                if sent % 30 == 0:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error sending to {user['user_id']}: {e}")
                failed += 1
                
        context.user_data['admin_action'] = None
        
        await update.message.reply_text(
            f"✅ **ارسال پیام همگانی کامل شد!**\n\n"
            f"📤 ارسال شده: {sent:,}\n"
            f"❌ ناموفق: {failed:,}\n"
            f"📊 کل: {sent + failed:,}",
            parse_mode=ParseMode.MARKDOWN
        )
        
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت عکس‌ها"""
        await update.message.reply_text(
            "📸 عکس دریافت شد!\n"
            "اما این قابلیت پشتیبانی نمی‌شود.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
            ])
        )
        
    # ============================================================
    # اعتبارسنجی و توابع کمکی
    # ============================================================
    
    def _validate_wallet_address(self, address):
        """اعتبارسنجی آدرس کیف پول TRC20"""
        try:
            # طول آدرس باید ۳۴ کاراکتر باشد
            if len(address) != 34:
                return False
                
            # کاراکترهای مجاز Base58
            valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
            if not all(c in valid_chars for c in address):
                return False
                
            # بررسی Base58
            try:
                decoded = base58.b58decode(address)
                return True
            except:
                return False
                
        except Exception as e:
            logger.error(f"Error validating address: {e}")
            return False
            
    async def _get_winner_amount(self, user_id):
        """دریافت مبلغ جایزه برنده"""
        cursor = db.execute(user_id,
            "SELECT prize_amount FROM winners WHERE user_id = ? AND paid_status = 0",
            (user_id,)
        )
        result = cursor.fetchone()
        return result['prize_amount'] if result else 0
        
    # ============================================================
    # مدیریت خطاها
    # ============================================================
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت خطاها"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_user:
                await self.application.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="⚠️ خطایی رخ داد! لطفاً دوباره تلاش کنید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
                    ])
                )
        except:
            pass

# ============================================================
# اجرای ربات
# ============================================================

async def main():
    """تابع اصلی اجرای ربات"""
    try:
        # ایجاد و راه‌اندازی ربات
        bot = UTYOBot()
        
        logger.info("🚀 ربات UTYOB در حال راه‌اندازی...")
        logger.info(f"👥 تعداد ادمین‌ها: {len(ADMIN_IDS)}")
        logger.info(f"🗄️ تعداد شاردها: {DB_SHARDS}")
        logger.info(f"🔑 تعداد API‌ها: {len(TRONGRID_APIS)}")
        
        # شروع ربات
        await bot.application.initialize()
        await bot.application.start()
        await bot.application.updater.start_polling()
        
        logger.info("✅ ربات با موفقیت راه‌اندازی شد!")
        
        # نگه‌داری اجرا
        while True:
            await asyncio.sleep(3600)
            
    except KeyboardInterrupt:
        logger.info("🛑 ربات متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا در اجرای ربات: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 برنامه با موفقیت متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {e}")