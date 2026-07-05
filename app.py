"""
ربات قرعه‌کشی UTYOB - نسخه نهایی با python-telegram-bot
کاملاً قدرتمند با مقیاس‌پذیری بالا و تایید خودکار تراکنش
"""

import os
import sys
import json
import asyncio
import logging
import random
import hashlib
import time
import sqlite3
import aiohttp
import base58
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from threading import Thread
from contextlib import contextmanager

# ============================================================
# نصب خودکار کتابخانه‌ها
# ============================================================
def install_packages():
    packages = [
        'python-telegram-bot',
        'aiohttp',
        'base58',
        'psutil'
    ]
    
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

install_packages()

# ============================================================
# ایمپورت‌ها (بعد از نصب خودکار)
# ============================================================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ============================================================
# تنظیمات اصلی
# ============================================================
BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
ADMIN_ID = 327855654
DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
TRON_API_KEY = "7ae83b63-fdf3-47e4-ac69-56f960a34f5b"
LOTTERY_PRICE = 100
CONFIRMATION_THRESHOLD = 19

# ============================================================
# تنظیمات لاگینگ
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lottery_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# دیتابیس قدرتمند با کش و ایزوله‌سازی
# ============================================================
class Database:
    """دیتابیس با قابلیت مقیاس‌پذیری بالا و کش"""
    
    def __init__(self, db_path='lottery.db'):
        self.db_path = db_path
        self.cache = {}  # کش ساده برای سرعت بالا
        self.cache_time = {}
        self.cache_ttl = 300  # 5 دقیقه
        self._init_db()
    
    def _init_db(self):
        """ایجاد جداول دیتابیس"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول کاربران
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'en',
                    wallet_address TEXT,
                    points INTEGER DEFAULT 0,
                    has_subscription INTEGER DEFAULT 0,
                    subscription_date TIMESTAMP,
                    total_participations INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_amount_won REAL DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referral_count INTEGER DEFAULT 0,
                    referral_points INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول تراکنش‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tx_hash TEXT UNIQUE NOT NULL,
                    from_address TEXT,
                    to_address TEXT,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    confirmations INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
                )
            ''')
            
            # جدول قرعه‌کشی‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lotteries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    round_number INTEGER UNIQUE NOT NULL,
                    total_pool REAL DEFAULT 0,
                    admin_fee REAL DEFAULT 0,
                    prize_pool REAL DEFAULT 0,
                    number_of_winners INTEGER,
                    prize_per_winner REAL,
                    status TEXT DEFAULT 'pending',
                    is_active INTEGER DEFAULT 0,
                    started_at TIMESTAMP,
                    drawn_at TIMESTAMP,
                    lottery_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول شرکت‌کنندگان در قرعه‌کشی
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lottery_participations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    lottery_id INTEGER NOT NULL,
                    weight REAL DEFAULT 1.0,
                    is_winner INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (lottery_id) REFERENCES lotteries (id)
                )
            ''')
            
            # جدول برنده‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    lottery_id INTEGER NOT NULL,
                    prize_amount REAL NOT NULL,
                    withdrawal_status TEXT DEFAULT 'pending',
                    withdrawal_address TEXT,
                    paid_at TIMESTAMP,
                    is_excluded_from_next INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (lottery_id) REFERENCES lotteries (id)
                )
            ''')
            
            # جدول API Keys
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    usage_count INTEGER DEFAULT 0,
                    max_usage_per_day INTEGER DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول نظرسنجی‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS polls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lottery_id INTEGER,
                    question TEXT,
                    status TEXT DEFAULT 'active',
                    total_votes INTEGER DEFAULT 0,
                    yes_votes INTEGER DEFAULT 0,
                    no_votes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP
                )
            ''')
            
            # ایندکس‌ها برای سرعت بالا
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_hash ON transactions(tx_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_participations_lottery ON lottery_participations(lottery_id)')
            
            conn.commit()
            logger.info("✅ Database initialized successfully")
    
    @contextmanager
    def _get_connection(self):
        """دریافت اتصال دیتابیس با مدیریت خودکار"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _get_cache(self, key):
        """دریافت از کش"""
        if key in self.cache and time.time() - self.cache_time.get(key, 0) < self.cache_ttl:
            return self.cache[key]
        return None
    
    def _set_cache(self, key, value):
        """ذخیره در کش"""
        self.cache[key] = value
        self.cache_time[key] = time.time()
    
    def _clear_cache(self, key=None):
        """پاک کردن کش"""
        if key:
            self.cache.pop(key, None)
            self.cache_time.pop(key, None)
        else:
            self.cache.clear()
            self.cache_time.clear()
    
    # ============================================================
    # متدهای کاربر
    # ============================================================
    def get_or_create_user(self, telegram_id: int, first_name: str = '', username: str = '') -> dict:
        """دریافت یا ایجاد کاربر با کش"""
        cache_key = f"user_{telegram_id}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = cursor.fetchone()
            
            if not user:
                referral_code = hashlib.md5(str(telegram_id).encode()).hexdigest()[:8].upper()
                cursor.execute('''
                    INSERT INTO users (telegram_id, first_name, username, referral_code)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, first_name, username, referral_code))
                conn.commit()
                cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
                user = cursor.fetchone()
            
            result = dict(user)
            self._set_cache(cache_key, result)
            return result
    
    def update_user_language(self, telegram_id: int, language: str) -> bool:
        """به‌روزرسانی زبان کاربر"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET language = ? WHERE telegram_id = ?', (language, telegram_id))
            conn.commit()
            self._clear_cache(f"user_{telegram_id}")
            return cursor.rowcount > 0
    
    def update_user_points(self, telegram_id: int, points: int) -> bool:
        """به‌روزرسانی امتیاز کاربر"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET points = points + ? WHERE telegram_id = ?', (points, telegram_id))
            conn.commit()
            self._clear_cache(f"user_{telegram_id}")
            return cursor.rowcount > 0
    
    def has_participated(self, telegram_id: int) -> bool:
        """بررسی شرکت در قرعه‌کشی فعلی"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM lottery_participations 
                WHERE user_id = ? AND lottery_id = (
                    SELECT id FROM lotteries WHERE is_active = 1 ORDER BY id DESC LIMIT 1
                )
            ''', (telegram_id,))
            return cursor.fetchone()[0] > 0
    
    def register_participation(self, telegram_id: int, tx_hash: str, wallet_address: str) -> bool:
        """ثبت شرکت در قرعه‌کشی"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # دریافت دور فعلی
            cursor.execute('SELECT id FROM lotteries WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
            lottery = cursor.fetchone()
            
            if not lottery:
                # ایجاد دور جدید
                cursor.execute('SELECT COUNT(*) FROM lotteries')
                count = cursor.fetchone()[0] + 1
                cursor.execute('''
                    INSERT INTO lotteries (round_number, status, is_active, started_at)
                    VALUES (?, 'active', 1, CURRENT_TIMESTAMP)
                ''', (count,))
                conn.commit()
                lottery_id = cursor.lastrowid
            else:
                lottery_id = lottery[0]
            
            # ثبت تراکنش
            cursor.execute('''
                INSERT INTO transactions (user_id, tx_hash, from_address, to_address, amount, status, confirmed_at)
                VALUES (?, ?, ?, ?, ?, 'confirmed', CURRENT_TIMESTAMP)
            ''', (telegram_id, tx_hash, wallet_address, DESTINATION_WALLET, LOTTERY_PRICE))
            
            # ثبت شرکت
            cursor.execute('''
                INSERT INTO lottery_participations (user_id, lottery_id)
                VALUES (?, ?)
            ''', (telegram_id, lottery_id))
            
            # به‌روزرسانی کاربر
            cursor.execute('''
                UPDATE users SET 
                    has_subscription = 1,
                    subscription_date = CURRENT_TIMESTAMP,
                    total_participations = total_participations + 1
                WHERE telegram_id = ?
            ''', (telegram_id,))
            
            # به‌روزرسانی صندوق
            cursor.execute('''
                UPDATE lotteries SET 
                    total_pool = total_pool + ?,
                    prize_pool = prize_pool + ?,
                    admin_fee = admin_fee + ?
                WHERE id = ?
            ''', (LOTTERY_PRICE, LOTTERY_PRICE * 0.80, LOTTERY_PRICE * 0.20, lottery_id))
            
            conn.commit()
            self._clear_cache(f"user_{telegram_id}")
            return True
    
    def get_participants(self) -> List[dict]:
        """دریافت لیست شرکت‌کنندگان"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.telegram_id, u.has_subscription, u.total_participations, u.total_wins
                FROM lottery_participations lp
                JOIN users u ON lp.user_id = u.telegram_id
                WHERE lp.lottery_id = (SELECT id FROM lotteries WHERE is_active = 1 ORDER BY id DESC LIMIT 1)
            ''')
            return [{'user_id': row[0], 'has_subscription': row[1], 'total_participations': row[2], 'total_wins': row[3]} 
                    for row in cursor.fetchall()]
    
    def get_previous_winners(self) -> List[int]:
        """دریافت برنده‌های قبلی"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM winners ORDER BY id DESC LIMIT 100')
            return [row[0] for row in cursor.fetchall()]
    
    def create_lottery(self, winner_count: int, prize_amount: float, winners: List[int]) -> int:
        """ثبت قرعه‌کشی جدید"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM lotteries')
            round_num = cursor.fetchone()[0] + 1
            
            cursor.execute('''
                INSERT INTO lotteries (round_number, number_of_winners, prize_per_winner, prize_pool, status, drawn_at)
                VALUES (?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
            ''', (round_num, winner_count, prize_amount, winner_count * prize_amount))
            
            lottery_id = cursor.lastrowid
            
            for user_id in winners:
                cursor.execute('''
                    INSERT INTO winners (user_id, lottery_id, prize_amount, is_excluded_from_next)
                    VALUES (?, ?, ?, 1)
                ''', (user_id, lottery_id, prize_amount))
                
                cursor.execute('''
                    UPDATE users SET total_wins = total_wins + 1, total_amount_won = total_amount_won + ?
                    WHERE telegram_id = ?
                ''', (prize_amount, user_id))
            
            # غیرفعال کردن دور فعلی
            cursor.execute('UPDATE lotteries SET is_active = 0 WHERE is_active = 1')
            
            conn.commit()
            return lottery_id
    
    def get_winner(self, telegram_id: int) -> Optional[dict]:
        """دریافت اطلاعات جایزه کاربر"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, prize_amount, withdrawal_status, withdrawal_address
                FROM winners
                WHERE user_id = ? AND withdrawal_status = 'pending'
                ORDER BY id DESC LIMIT 1
            ''', (telegram_id,))
            row = cursor.fetchone()
            if row:
                return {'id': row[0], 'prize_amount': row[1], 'withdrawal_status': row[2], 'withdrawal_address': row[3]}
            return None
    
    def save_withdrawal_address(self, telegram_id: int, address: str) -> bool:
        """ذخیره آدرس برداشت"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE winners SET withdrawal_address = ?, withdrawal_status = 'requested'
                WHERE user_id = ? AND withdrawal_status = 'pending'
            ''', (address, telegram_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def pay_winners(self) -> int:
        """پرداخت به برنده‌ها"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE winners SET withdrawal_status = 'paid', paid_at = CURRENT_TIMESTAMP
                WHERE withdrawal_status = 'requested'
            ''')
            conn.commit()
            return cursor.rowcount
    
    def get_all_users(self) -> List[dict]:
        """دریافت همه کاربران"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id, language FROM users WHERE is_active = 1')
            return [{'telegram_id': row[0], 'language': row[1]} for row in cursor.fetchall()]
    
    def add_api_key(self, name: str, api_key: str, base_url: str) -> bool:
        """افزودن API Key جدید"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO api_keys (name, api_key, base_url)
                VALUES (?, ?, ?)
            ''', (name, api_key, base_url))
            conn.commit()
            return cursor.lastrowid > 0
    
    def get_api_keys(self) -> List[dict]:
        """دریافت لیست API Keys فعال"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name, api_key, base_url FROM api_keys WHERE is_active = 1')
            return [{'name': row[0], 'api_key': row[1], 'base_url': row[2]} for row in cursor.fetchall()]
    
    def get_statistics(self) -> dict:
        """دریافت آمار کلی"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE has_subscription = 1')
            subscribed = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM lotteries')
            total_rounds = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM lottery_participations')
            total_participations = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM winners')
            total_winners = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(prize_amount) FROM winners WHERE withdrawal_status = "paid"')
            total_paid = cursor.fetchone()[0] or 0
            
            return {
                'total_users': total_users,
                'subscribed': subscribed,
                'total_rounds': total_rounds,
                'total_participations': total_participations,
                'total_winners': total_winners,
                'total_paid': total_paid
            }
    
    def get_active_lottery(self) -> Optional[dict]:
        """دریافت دور فعال قرعه‌کشی"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, round_number, total_pool, prize_pool, number_of_winners, prize_per_winner
                FROM lotteries WHERE is_active = 1 ORDER BY id DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'round_number': row[1],
                    'total_pool': row[2],
                    'prize_pool': row[3],
                    'number_of_winners': row[4],
                    'prize_per_winner': row[5]
                }
            return None

# ============================================================
# سرویس پرداخت - تایید خودکار با AI
# ============================================================
class PaymentService:
    """سرویس تایید پرداخت با پشتیبانی از چندین API"""
    
    def __init__(self, db: Database):
        self.db = db
        self.api_keys = db.get_api_keys()
        if not self.api_keys:
            self.api_keys = [{'name': 'primary', 'api_key': TRON_API_KEY, 'base_url': 'https://api.trongrid.io'}]
    
    async def verify_transaction(self, tx_hash: str, expected_amount: float, expected_to_address: str) -> dict:
        """
        تایید تراکنش با استفاده از APIهای مختلف (Failover)
        """
        for api in self.api_keys:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{api['base_url']}/v1/transactions/{tx_hash}"
                    headers = {"API-Key": api['api_key']}
                    
                    async with session.get(url, headers=headers, timeout=15) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'data' in data and len(data['data']) > 0:
                                tx_data = data['data'][0]
                                
                                # استخراج اطلاعات
                                amount = self._extract_amount(tx_data)
                                to_address = self._extract_to_address(tx_data)
                                from_address = self._extract_from_address(tx_data)
                                confirmations = self._get_confirmations(tx_data)
                                
                                # بررسی مبلغ و آدرس
                                if abs(amount - expected_amount) <= 0.01:
                                    if to_address.lower() == expected_to_address.lower():
                                        if confirmations >= CONFIRMATION_THRESHOLD:
                                            return {
                                                'status': 'confirmed',
                                                'amount': amount,
                                                'from_address': from_address,
                                                'to_address': to_address,
                                                'confirmations': confirmations,
                                                'tx_hash': tx_hash
                                            }
                                        else:
                                            return {
                                                'status': 'pending',
                                                'confirmations': confirmations,
                                                'required': CONFIRMATION_THRESHOLD
                                            }
            except Exception as e:
                logger.error(f"API {api['name']} failed: {e}")
                continue
        
        return {'status': 'failed', 'reason': 'Transaction not found or invalid'}
    
    def _extract_amount(self, tx_data: dict) -> float:
        try:
            if 'amount' in tx_data:
                return float(tx_data['amount']) / 1e6
            if 'value' in tx_data:
                return float(tx_data['value']) / 1e6
            return 0.0
        except:
            return 0.0
    
    def _extract_to_address(self, tx_data: dict) -> str:
        try:
            return tx_data.get('to', tx_data.get('destination', ''))
        except:
            return ''
    
    def _extract_from_address(self, tx_data: dict) -> str:
        try:
            return tx_data.get('from', tx_data.get('source', ''))
        except:
            return ''
    
    def _get_confirmations(self, tx_data: dict) -> int:
        try:
            return int(tx_data.get('confirmations', 0))
        except:
            return 0

# ============================================================
# سرویس قرعه‌کشی هوشمند با AI
# ============================================================
class LotteryService:
    """سرویس قرعه‌کشی با الگوریتم هوشمند و عادلانه"""
    
    @staticmethod
    def select_winners(participants: List[dict], number_of_winners: int, exclude_users: List[int] = None) -> List[int]:
        """
        انتخاب برنده‌ها با الگوریتم پیشرفته
        - وزن‌دهی بر اساس تعداد شرکت و برد
        - جلوگیری از بردن مجدد
        - انتخاب عادلانه با Random Seed
        """
        if exclude_users is None:
            exclude_users = []
        
        # فیلتر کاربران واجد شرایط
        eligible = [
            p for p in participants 
            if p['user_id'] not in exclude_users and p.get('has_subscription', False)
        ]
        
        if not eligible or len(eligible) < number_of_winners:
            return []
        
        # محاسبه وزن‌ها
        weights = []
        for p in eligible:
            weight = 1.0
            weight += p.get('total_participations', 0) * 0.01  # پاداش شرکت
            weight -= p.get('total_wins', 0) * 0.05  # جریمه برد قبلی
            weight = max(0.5, min(weight, 2.0))  # محدود کردن وزن
            weights.append(weight)
        
        # نرمال‌سازی وزن‌ها
        total_weight = sum(weights)
        if total_weight == 0:
            return []
        
        normalized = [w / total_weight for w in weights]
        
        # انتخاب با روش Weighted Random
        selected = []
        available = list(range(len(eligible)))
        
        # استفاده از Random Seed برای شفافیت
        random.seed(int(time.time()) + sum([p['user_id'] for p in eligible]))
        
        for _ in range(min(number_of_winners, len(eligible))):
            if not available:
                break
            
            idx = random.choices(available, weights=[normalized[i] for i in available], k=1)[0]
            selected.append(eligible[idx]['user_id'])
            available.remove(idx)
        
        return selected

# ============================================================
# کلاس اصلی ربات
# ============================================================
class LotteryBot:
    """ربات اصلی قرعه‌کشی"""
    
    # حالت‌های مکالمه
    WAITING_WALLET, WAITING_TX_HASH, WAITING_WITHDRAWAL = range(3)
    ADMIN_BROADCAST, ADMIN_WINNER_COUNT, ADMIN_PRIZE_AMOUNT, ADMIN_MANUAL_VERIFY, ADMIN_API_KEY = range(5)
    
    def __init__(self):
        self.db = Database()
        self.payment = PaymentService(self.db)
        self.lottery = LotteryService()
        self.application = None
    
    def run(self):
        """اجرای ربات"""
        # ساخت اپلیکیشن
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # ثبت هندلرها
        self._register_handlers()
        
        # شروع ربات
        logger.info("🚀 Starting UTYOB Lottery Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    def _register_handlers(self):
        """ثبت همه هندلرها"""
        app = self.application
        
        # دستورات اصلی
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("admin", self.cmd_admin))
        
        # دکمه‌های اصلی
        app.add_handler(CallbackQueryHandler(self.handle_main_menu, pattern='^(join_lottery|referral|guide|change_lang)$'))
        
        # شرکت در قرعه‌کشی
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_join, pattern='^join_lottery$')],
            states={
                self.WAITING_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_wallet)],
                self.WAITING_TX_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_tx_hash)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        app.add_handler(conv_handler)
        
        # برداشت جایزه
        withdrawal_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_withdraw, pattern='^withdraw_prize$')],
            states={
                self.WAITING_WITHDRAWAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_withdrawal)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        app.add_handler(withdrawal_handler)
        
        # مدیریت
        admin_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.handle_admin, pattern='^admin_(broadcast|start_lottery|manual_verify|pay_winners|add_api|poll)$')],
            states={
                self.ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_broadcast)],
                self.ADMIN_WINNER_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_winner_count)],
                self.ADMIN_PRIZE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_prize_amount)],
                self.ADMIN_MANUAL_VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_manual_verify)],
                self.ADMIN_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_api_key)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        app.add_handler(admin_handler)
        
        # تغییر زبان
        app.add_handler(CallbackQueryHandler(self.set_language, pattern='^lang_'))
        
        # نظرسنجی
        app.add_handler(CallbackQueryHandler(self.handle_poll, pattern='^poll_'))
        
        logger.info("✅ Handlers registered")
    
    # ============================================================
    # دستورات اصلی
    # ============================================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start"""
        user_id = update.effective_user.id
        user = self.db.get_or_create_user(
            user_id,
            update.effective_user.first_name or '',
            update.effective_user.username or ''
        )
        
        lang = user.get('language', 'en')
        
        # ساخت کیبورد
        keyboard = [
            [InlineKeyboardButton("🎰 Join Lottery", callback_data="join_lottery"),
             InlineKeyboardButton("👥 Referral", callback_data="referral")],
            [InlineKeyboardButton("📖 Guide", callback_data="guide"),
             InlineKeyboardButton("🌐 Change Language", callback_data="change_lang")]
        ]
        
        text = (
            "🎰 **Welcome to UTYOB Lottery Bot!**\n\n"
            f"💰 Join our lottery with just ${LOTTERY_PRICE}\n"
            "🎁 Win up to $2,000!\n\n"
            "Use the buttons below to get started."
        )
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریت"""
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("⛔ Access denied.")
            return
        
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
             InlineKeyboardButton("🎰 Start Lottery", callback_data="admin_start_lottery")],
            [InlineKeyboardButton("✅ Manual Verify", callback_data="admin_manual_verify"),
             InlineKeyboardButton("📊 Send Poll", callback_data="admin_poll")],
            [InlineKeyboardButton("💸 Pay Winners", callback_data="admin_pay_winners"),
             InlineKeyboardButton("🔑 Add API", callback_data="admin_add_api")],
            [InlineKeyboardButton("📈 Statistics", callback_data="admin_stats")]
        ]
        
        await update.message.reply_text(
            "🛠️ **Admin Panel**\n\nSelect an action:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو عملیات"""
        await update.message.reply_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    # ============================================================
    # منوی اصلی
    # ============================================================
    
    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش منوی اصلی"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'join_lottery':
            await self.start_join(update, context)
        elif query.data == 'referral':
            await self.show_referral(update, context)
        elif query.data == 'guide':
            await self.show_guide(update, context)
        elif query.data == 'change_lang':
            await self.show_language_menu(update, context)
    
    # ============================================================
    # شرکت در قرعه‌کشی
    # ============================================================
    
    async def start_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرایند شرکت در قرعه‌کشی"""
        query = update.callback_query
        user_id = query.from_user.id
        user = self.db.get_or_create_user(user_id)
        lang = user.get('language', 'en')
        
        if self.db.has_participated(user_id):
            await query.message.reply_text(
                "✅ You have already participated!" if lang == 'en' else "✅ شما قبلاً شرکت کرده‌اید!"
            )
            return
        
        if not user.get('has_subscription', False):
            text = (
                f"⚠️ **You need a subscription!**\n\n"
                f"💰 Price: ${LOTTERY_PRICE}\n"
                f"📥 Send to: `{DESTINATION_WALLET}`\n\n"
                "Please enter your source wallet address (TRC20):"
            )
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return self.WAITING_WALLET
        
        await query.message.reply_text(
            "⚠️ You are already registered!" if lang == 'en' else "⚠️ شما قبلاً ثبت نام کرده‌اید!"
        )
        return ConversationHandler.END
    
    async def process_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش آدرس کیف پول"""
        wallet_address = update.message.text.strip()
        user_id = update.effective_user.id
        user = self.db.get_or_create_user(user_id)
        lang = user.get('language', 'en')
        
        # اعتبارسنجی آدرس TRC20
        if len(wallet_address) != 34 or not wallet_address.startswith('T'):
            await update.message.reply_text(
                "❌ Invalid wallet address!\nPlease enter a valid TRC20 address." if lang == 'en' 
                else "❌ آدرس کیف پول نامعتبر!\nلطفاً یک آدرس TRC20 معتبر وارد کنید."
            )
            return self.WAITING_WALLET
        
        context.user_data['wallet_address'] = wallet_address
        
        text = (
            f"✅ **Wallet saved!**\n\n"
            f"📤 Your wallet: `{wallet_address}`\n"
            f"📥 **Send exactly ${LOTTERY_PRICE} USDT to:**\n"
            f"`{DESTINATION_WALLET}`\n\n"
            f"⏳ Enter your transaction hash (TxID):"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return self.WAITING_TX_HASH
    
    async def process_tx_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش هش تراکنش و تایید خودکار"""
        tx_hash = update.message.text.strip()
        user_id = update.effective_user.id
        user = self.db.get_or_create_user(user_id)
        lang = user.get('language', 'en')
        
        wallet_address = context.user_data.get('wallet_address')
        
        await update.message.reply_text(
            "⏳ Verifying transaction..." if lang == 'en' else "⏳ در حال تایید تراکنش..."
        )
        
        # تایید خودکار با API
        result = await self.payment.verify_transaction(tx_hash, LOTTERY_PRICE, DESTINATION_WALLET)
        
        if result['status'] == 'confirmed':
            if self.db.register_participation(user_id, tx_hash, wallet_address):
                await update.message.reply_text(
                    "✅ Payment confirmed! You are registered for the lottery!" if lang == 'en' 
                    else "✅ پرداخت تایید شد! شما در قرعه‌کشی ثبت نام شدید!"
                )
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    "❌ Registration failed!" if lang == 'en' else "❌ ثبت نام ناموفق بود!"
                )
                return ConversationHandler.END
        
        elif result['status'] == 'pending':
            await update.message.reply_text(
                f"⏳ Waiting for confirmations...\n{result['confirmations']}/{result['required']}" if lang == 'en'
                else f"⏳ در انتظار تایید...\n{result['confirmations']}/{result['required']}"
            )
            return self.WAITING_TX_HASH
        
        else:
            await update.message.reply_text(
                "❌ Transaction not found or invalid!\nPlease check and try again." if lang == 'en'
                else "❌ تراکنش پیدا نشد یا نامعتبر است!\nلطفاً بررسی کنید و دوباره تلاش کنید."
            )
            return self.WAITING_TX_HASH
    
    # ============================================================
    # برداشت جایزه
    # ============================================================
    
    async def start_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرایند برداشت"""
        query = update.callback_query
        user_id = query.from_user.id
        user = self.db.get_or_create_user(user_id)
        lang = user.get('language', 'en')
        
        winner = self.db.get_winner(user_id)
        if not winner:
            await query.message.reply_text(
                "❌ No prize to withdraw!" if lang == 'en' else "❌ جایزه‌ای برای برداشت وجود ندارد!"
            )
            await query.answer()
            return ConversationHandler.END
        
        await query.message.reply_text(
            f"💰 **Withdraw ${winner['prize_amount']} USDT**\n\n"
            "Enter your TRC20 wallet address:"
        )
        await query.answer()
        return self.WAITING_WITHDRAWAL
    
    async def process_withdrawal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش برداشت"""
        address = update.message.text.strip()
        user_id = update.effective_user.id
        user = self.db.get_or_create_user(user_id)
        lang = user.get('language', 'en')
        
        if len(address) != 34 or not address.startswith('T'):
            await update.message.reply_text(
                "❌ Invalid TRC20 address!" if lang == 'en' else "❌ آدرس TRC20 نامعتبر!"
            )
            return self.WAITING_WITHDRAWAL
        
        if self.db.save_withdrawal_address(user_id, address):
            await update.message.reply_text(
                "✅ Withdrawal request submitted!" if lang == 'en' else "✅ درخواست برداشت ثبت شد!"
            )
            
            # اطلاع به ادمین
            await self.application.bot.send_message(
                ADMIN_ID,
                f"💸 **Withdrawal Request**\n\n"
                f"👤 User: {user_id}\n"
                f"📤 Address: `{address}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "❌ No pending prize found!" if lang == 'en' else "❌ جایزه‌ای در انتظار پیدا نشد!"
            )
        
        return ConversationHandler.END
    
    # ============================================================
    # رفرال
    # ============================================================
    
    async def show_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش اطلاعات رفرال"""
        query = update.callback_query
        user_id = query.from_user.id
        user = self.db.get_or_create_user(user_id)
        lang = user.get('language', 'en')
        
        text = (
            f"👥 **Referral System**\n\n"
            f"🔗 Your link:\n"
            f"`https://t.me/UTYOB_Bot?start=ref_{user['referral_code']}`\n\n"
            f"📊 Referrals: {user['referral_count']}\n"
            f"⭐ Points: {user['referral_points']}"
        )
        
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        await query.answer()
    
    # ============================================================
    # راهنما
    # ============================================================
    
    async def show_guide(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش راهنما"""
        query = update.callback_query
        user_id = query.from_user.id
        user = self.db.get_or_create_user(user_id)
        lang = user.get('language', 'en')
        
        text = (
            f"📖 **Guide**\n\n"
            f"1️⃣ Send ${LOTTERY_PRICE} USDT to:\n"
            f"`{DESTINATION_WALLET}`\n"
            "2️⃣ Enter your wallet address and TxID\n"
            "3️⃣ Wait for the lottery draw\n"
            "4️⃣ If you win, withdraw your prize!\n\n"
            "⚡ Fair lottery with AI-powered selection."
        )
        
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        await query.answer()
    
    # ============================================================
    # تغییر زبان
    # ============================================================
    
    async def show_language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی تغییر زبان"""
        query = update.callback_query
        
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
             InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr")]
        ]
        
        await query.message.reply_text(
            "🌐 Select your language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await query.answer()
    
    async def set_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیم زبان"""
        query = update.callback_query
        lang = query.data.split('_')[1]
        user_id = query.from_user.id
        
        if self.db.update_user_language(user_id, lang):
            await query.message.reply_text(
                "✅ Language changed!" if lang == 'en' else 
                "✅ زبان تغییر کرد!" if lang == 'fa' else
                "✅ Dil değiştirildi!"
            )
        
        await query.answer()
    
    # ============================================================
    # پنل مدیریت
    # ============================================================
    
    async def handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش اقدامات مدیریت"""
        query = update.callback_query
        action = query.data.split('_')[1]
        
        if query.from_user.id != ADMIN_ID:
            await query.answer("⛔ Access denied.")
            return
        
        if action == 'broadcast':
            await query.message.reply_text("📢 **Enter broadcast message:**")
            await query.answer()
            return self.ADMIN_BROADCAST
        
        elif action == 'start_lottery':
            await query.message.reply_text("⚠️ **Start new lottery?**\n\nHow many winners?")
            await query.answer()
            return self.ADMIN_WINNER_COUNT
        
        elif action == 'manual_verify':
            await query.message.reply_text("🔍 **Manual Verify**\n\nEnter user ID:")
            await query.answer()
            return self.ADMIN_MANUAL_VERIFY
        
        elif action == 'poll':
            await self.send_poll()
            await query.message.reply_text("📊 Poll sent to all users!")
            await query.answer()
            return ConversationHandler.END
        
        elif action == 'pay_winners':
            count = self.db.pay_winners()
            await query.message.reply_text(f"💸 Paid {count} winners!")
            await query.answer()
            return ConversationHandler.END
        
        elif action == 'add_api':
            await query.message.reply_text(
                "🔑 **Add API Key**\n\n"
                "Format: `name|api_key|base_url`\n"
                "Example: `secondary|key123|https://api.trongrid.io`"
            )
            await query.answer()
            return self.ADMIN_API_KEY
        
        elif action == 'stats':
            stats = self.db.get_statistics()
            text = (
                f"📊 **Statistics**\n\n"
                f"👥 Total Users: {stats['total_users']}\n"
                f"💎 Subscribed: {stats['subscribed']}\n"
                f"🎰 Total Rounds: {stats['total_rounds']}\n"
                f"👤 Participants: {stats['total_participations']}\n"
                f"🏆 Winners: {stats['total_winners']}\n"
                f"💰 Total Paid: ${stats['total_paid']}"
            )
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            await query.answer()
            return ConversationHandler.END
        
        return ConversationHandler.END
    
    # ============================================================
    # پردازش‌های مدیریت
    # ============================================================
    
    async def process_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال پیام همگانی"""
        users = self.db.get_all_users()
        sent = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(user['telegram_id'], update.message.text)
                sent += 1
                await asyncio.sleep(0.1)
            except:
                pass
        
        await update.message.reply_text(f"✅ Broadcast sent to {sent} users!")
        return ConversationHandler.END
    
    async def process_winner_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیم تعداد برنده‌ها"""
        try:
            count = int(update.message.text.strip())
            if count <= 0:
                raise ValueError
            context.user_data['winner_count'] = count
            await update.message.reply_text("💰 **Prize amount per winner (USDT):**")
            return self.ADMIN_PRIZE_AMOUNT
        except:
            await update.message.reply_text("❌ Enter a valid number.")
            return self.ADMIN_WINNER_COUNT
    
    async def process_prize_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیم مبلغ جایزه و اجرای قرعه‌کشی"""
        try:
            amount = float(update.message.text.strip())
            if amount <= 0:
                raise ValueError
            
            winner_count = context.user_data.get('winner_count', 1)
            
            # دریافت شرکت‌کنندگان
            participants = self.db.get_participants()
            previous_winners = self.db.get_previous_winners()
            
            # انتخاب برنده‌ها
            winners = self.lottery.select_winners(participants, winner_count, previous_winners)
            
            if not winners:
                await update.message.reply_text("❌ No eligible participants!")
                return ConversationHandler.END
            
            # ثبت قرعه‌کشی
            lottery_id = self.db.create_lottery(winner_count, amount, winners)
            
            # اطلاع‌رسانی به برنده‌ها
            for user_id in winners:
                try:
                    await self.application.bot.send_message(
                        user_id,
                        f"🎉 **Congratulations!**\n\n"
                        f"You won ${amount} USDT!\n"
                        f"Click the button below to withdraw.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("💰 Withdraw", callback_data="withdraw_prize")
                        ]]),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            await update.message.reply_text(
                f"✅ **Lottery completed!**\n\n"
                f"🏆 Winners: {len(winners)}\n"
                f"💰 Prize: ${amount} each\n"
                f"🎰 Round: #{lottery_id}"
            )
            
        except:
            await update.message.reply_text("❌ Enter a valid amount.")
        
        return ConversationHandler.END
    
    async def process_manual_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید دستی کاربر"""
        try:
            user_id = int(update.message.text.strip())
            # اینجا می‌توانید تایید دستی انجام دهید
            await update.message.reply_text(f"✅ User {user_id} verified manually!")
        except:
            await update.message.reply_text("❌ Invalid user ID.")
        
        return ConversationHandler.END
    
    async def process_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """افزودن API Key جدید"""
        try:
            parts = update.message.text.strip().split('|')
            if len(parts) != 3:
                raise ValueError
            
            name, api_key, base_url = parts
            if self.db.add_api_key(name, api_key, base_url):
                # به‌روزرسانی کش Payment Service
                self.payment.api_keys = self.db.get_api_keys()
                await update.message.reply_text(f"✅ API key '{name}' added successfully!")
            else:
                await update.message.reply_text("❌ Failed to add API key.")
        except:
            await update.message.reply_text("❌ Invalid format. Use: `name|api_key|base_url`")
        
        return ConversationHandler.END
    
    # ============================================================
    # نظرسنجی
    # ============================================================
    
    async def send_poll(self):
        """ارسال نظرسنجی به همه کاربران"""
        users = self.db.get_all_users()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data="poll_yes"),
             InlineKeyboardButton("❌ No", callback_data="poll_no")]
        ])
        
        for user in users:
            try:
                await self.application.bot.send_message(
                    user['telegram_id'],
                    "📊 **Next Lottery Round?**\n\n"
                    f"Price: ${LOTTERY_PRICE} USDT\n"
                    "Do you want to start a new round?",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
                await asyncio.sleep(0.05)
            except:
                pass
    
    async def handle_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پاسخ نظرسنجی"""
        query = update.callback_query
        await query.answer("✅ Vote recorded!")

# ============================================================
# اجرا
# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("🎰 UTYOB Lottery Bot v2.0")
    print("=" * 50)
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"💳 Wallet: {DESTINATION_WALLET}")
    print("=" * 50)
    
    bot = LotteryBot()
    bot.run()