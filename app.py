# ============================================================
# ربات سلطنتی UTYOB - نسخه نهایی
# طراحی شده برای ۵۰۰,۰۰۰+ کاربر
# با کش پیشرفته، تایید خودکار، قرعه‌کشی زمان‌دار
# ============================================================

import asyncio
import logging
import random
import json
import sqlite3
import hashlib
import base58
import aiohttp
import threading
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# تنظیمات
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '123456789').split(',')]

# ۳ کلید API برای پشتیبانی و سرعت بالا
TRONGRID_APIS = [
    "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
    "f9c8a3b2-1d4e-5f6a-7b8c-9d0e1f2a3b4c",
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
]

DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PAYMENT_AMOUNT = 100
DB_SHARDS = 200  # برای ۵۰۰k کاربر
CACHE_TTL = 600  # ۱۰ دقیقه

# ============================================================
# دیتابیس با ۲۰۰ شارد
# ============================================================
class DatabaseManager:
    def __init__(self, num_shards=DB_SHARDS):
        self.num_shards = num_shards
        self.connections = {}
        self.locks = {}
        self._init_shards()

    def _init_shards(self):
        os.makedirs("data", exist_ok=True)
        for i in range(self.num_shards):
            db_path = f"data/shard_{i}.db"
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=60)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=50000")
            conn.execute("PRAGMA temp_store=MEMORY")
            self.connections[i] = conn
            self.locks[i] = threading.Lock()
            self._create_tables(conn)

    def _create_tables(self, conn):
        cursor = conn.cursor()
        
        # کاربران
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # تراکنش‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_id TEXT,
                tx_type TEXT DEFAULT 'lottery',
                status TEXT DEFAULT 'pending',
                verified_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # درخواست‌های تایید دستی
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_hash TEXT,
                tx_type TEXT DEFAULT 'lottery',
                photo_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # قرعه‌کشی‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lotteries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winners_count INTEGER,
                prize_per_winner REAL,
                total_prize REAL,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'pending',
                winner_id INTEGER,
                winner_confirmed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # برندگان
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
        
        # محتوای آموزشی
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT DEFAULT 'text',
                title TEXT,
                content TEXT,
                file_id TEXT,
                file_name TEXT,
                file_size INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # محتوای ارسال شده به کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_sent (
                user_id INTEGER,
                content_id INTEGER,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, content_id)
            )
        ''')
        
        # تنظیمات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ایندکس‌ها
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_verifications(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lotteries_status ON lotteries(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_lottery ON winners(lottery_id)')
        
        conn.commit()

    def get_shard(self, user_id):
        return hash(str(user_id)) % self.num_shards

    def execute(self, user_id, query, params=(), commit=True):
        shard = self.get_shard(user_id)
        conn = self.connections[shard]
        with self.locks[shard]:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor

    def execute_global(self, query, params=()):
        results = []
        for shard_id, conn in self.connections.items():
            with self.locks[shard_id]:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                results.extend(cursor.fetchall())
        return results

db = DatabaseManager()

# ============================================================
# سیستم کش پیشرفته (برای ۵۰۰k کاربر)
# ============================================================
class AdvancedCache:
    def __init__(self, ttl=CACHE_TTL):
        self.cache = {}
        self.expiry = {}
        self.lock = threading.RLock()
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def get(self, key):
        with self.lock:
            if key in self.cache and time.time() < self.expiry.get(key, 0):
                self.hits += 1
                return self.cache[key]
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]
            self.misses += 1
            return None

    def set(self, key, value, ttl=None):
        with self.lock:
            self.cache[key] = value
            self.expiry[key] = time.time() + (ttl or self.ttl)

    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]

    def clear(self):
        with self.lock:
            self.cache.clear()
            self.expiry.clear()

    def get_stats(self):
        with self.lock:
            total = self.hits + self.misses
            return {
                'size': len(self.cache),
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': (self.hits / total * 100) if total > 0 else 0
            }

cache = AdvancedCache()

# ============================================================
# زبان‌ها (انگلیسی پیش‌فرض، پنل مدیریت فارسی)
# ============================================================
LANGUAGES = {
    'en': {
        'name': 'English',
        'welcome': "🎮 **Welcome to UTYOB Bot!**\n\nPlease select an option:",
        'main_menu': "🎯 **Main Menu**\n\nSelect an option:",
        'lottery': "🎰 Lottery",
        'education': "📚 Trading Education",
        'referral': "🔗 Referral",
        'guide': "📖 Guide",
        'subscribe': "🔄 Subscribe",
        'back': "🔙 Back",
        'main_menu_btn': "🏠 Main Menu",
        'lottery_title': "🎰 **UTYOB Lottery**\n\n💰 Entry: $100\n🏆 Prize: Up to $10,000",
        'lottery_join': "🎯 Join Lottery",
        'lottery_enter_wallet': "📤 **Enter your TRC20 wallet address:**",
        'lottery_after_wallet': "✅ **Wallet saved!**\n\n💰 Send $100 to:\n`{}`\n\n⚠️ After sending, click **✅ I sent the payment**.",
        'lottery_confirm': "✅ I sent the payment",
        'lottery_verifying': "⏳ Verifying your payment... Please wait.",
        'lottery_success': "✅ **Payment verified!** 🎉\n\n🔗 TX: `{}`\n\n🙏 Good luck!",
        'lottery_failed': "❌ **Payment verification failed!**\n\nReason: {}\n\n📤 Please send your TX hash or photo of the transaction:",
        'lottery_no_subscription': "❌ **No active subscription!**\n\nPlease subscribe first.",
        'lottery_announcement': "🎰 **LOTTERY IN PROGRESS!**\n\n💰 Prize Pool: ${}\n👥 Participants: {}\n⏳ Drawing in progress...\n\n🤞 Good luck to all participants!",
        'lottery_winner_announcement': "🏆 **LOTTERY WINNER!**\n\n🎉 Congratulations to:\n👤 {}\n\n💰 Prize: ${}\n\n🎊 Thank you all for participating!",
        'education_title': "📚 **Trading Education**\n\nLearn professional trading from zero to hero!",
        'education_buy': "💰 Buy Course ($100)",
        'education_enter_wallet': "📤 **Enter your TRC20 wallet address:**",
        'education_after_wallet': "✅ **Wallet saved!**\n\n💰 Send $100 to:\n`{}`\n\n⚠️ After sending, click **✅ I sent the payment**.",
        'education_confirm': "✅ I sent the payment",
        'education_verifying': "⏳ Verifying your payment...",
        'education_success': "✅ **Payment verified!** 🎉\n\n🔗 TX: `{}`\n\n📚 **Access granted!**\n\nAll course content has been sent.",
        'education_failed': "❌ **Payment verification failed!**\n\nReason: {}\n\n📤 Please send your TX hash or photo:",
        'education_already': "✅ You already have access to this course!",
        'subscribe_title': "💳 **Subscription**\n\n💰 Price: $100\n📅 Valid: 30 days",
        'subscribe_enter_wallet': "📤 **Enter your TRC20 wallet address:**",
        'subscribe_after_wallet': "✅ **Wallet saved!**\n\n💰 Send $100 to:\n`{}`\n\n⚠️ After sending, click **✅ I sent the payment**.",
        'subscribe_confirm': "✅ I sent the payment",
        'subscribe_success': "✅ **Subscription activated!** 🎉\n\n📚 All course content has been sent to you.",
        'subscribe_failed': "❌ **Subscription failed!**\n\nReason: {}\n\n📤 Send your TX hash or photo:",
        'subscribe_active': "✅ You have an active subscription!",
        'referral_text': "🔗 **Referral System**\n\n👤 You: {}\n📊 Invites: {}\n\n🔑 Your code:\n`{}`\n\n🔗 Invite link:\n{}\n\n💰 **Reward:** 5% of each deposit",
        'referral_link': "https://t.me/UTYOB_Bot?start=ref_{}",
        'share': "📤 Share",
        'guide_text': "📖 **Complete Guide**\n\n🎯 **Steps:**\n1️⃣ Subscribe ($100/month)\n2️⃣ Join lottery or buy course\n3️⃣ Win prizes!\n\n📞 Support: Contact admin.",
        'invalid_command': "⚠️ **Invalid command!**\n\nPlease use the buttons.",
        'error_message': "⚠️ **Error occurred!**\n\nPlease try again.",
        'invalid_wallet': "❌ **Invalid wallet address!**\n\nPlease enter a valid TRC20 address.\nExample: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
        'tx_hash_invalid': "❌ **Invalid TX hash!**\n\nPlease enter a valid 64-character hash.",
        'tx_hash_received': "✅ **TX hash received!**\n\n⏳ Being reviewed by admin...\n📢 You will be notified when verified.",
        'photo_received': "✅ **Photo received!**\n\n⏳ Being reviewed by admin...",
        'no_subscription': "❌ **No active subscription!**",
        'cancel': "❌ Cancel",
        'retry': "🔄 Retry",
        'support': "📞 Support",
        'withdraw_prize': "💰 Withdraw Prize",
        'no_winner': "❌ You have no prize!",
        'already_paid': "✅ Prize already paid!",
        'enter_withdraw_wallet': "💰 Enter your TRC20 wallet:",
        'withdraw_success': "✅ Withdrawal registered!",
    },
    'fa': {
        'name': 'فارسی',
        'welcome': "🎮 **به ربات UTYOB خوش آمدید!**\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        'main_menu': "🎯 **منوی اصلی**\n\nانتخاب کنید:",
        'lottery': "🎰 قرعه‌کشی",
        'education': "📚 آموزش ترید",
        'referral': "🔗 رفرال",
        'guide': "📖 راهنما",
        'subscribe': "🔄 اشتراک",
        'back': "🔙 بازگشت",
        'main_menu_btn': "🏠 منوی اصلی",
        'lottery_title': "🎰 **قرعه‌کشی UTYOB**\n\n💰 هزینه: ۱۰۰ دلار\n🏆 جایزه: تا ۱۰,۰۰۰ دلار",
        'lottery_join': "🎯 شرکت در قرعه‌کشی",
        'lottery_enter_wallet': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
        'lottery_after_wallet': "✅ **آدرس ذخیره شد!**\n\n💰 مبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ پس از واریز، دکمه **✅ پرداخت کردم** را بزنید.",
        'lottery_confirm': "✅ پرداخت کردم",
        'lottery_verifying': "⏳ در حال بررسی پرداخت شما...",
        'lottery_success': "✅ **پرداخت تایید شد!** 🎉\n\n🔗 هش: `{}`\n\n🙏 موفق باشید!",
        'lottery_failed': "❌ **پرداخت تایید نشد!**\n\nدلیل: {}\n\n📤 لطفاً هش تراکنش یا عکس واریز را ارسال کنید:",
        'lottery_no_subscription': "❌ **اشتراک فعال ندارید!**\n\nابتدا اشتراک تهیه کنید.",
        'lottery_announcement': "🎰 **قرعه‌کشی در حال انجام!**\n\n💰 جایزه: ${}\n👥 شرکت‌کنندگان: {}\n⏳ در حال قرعه‌کشی...\n\n🤞 برای همه آرزوی موفقیت داریم!",
        'lottery_winner_announcement': "🏆 **برنده قرعه‌کشی!**\n\n🎉 تبریک به:\n👤 {}\n\n💰 جایزه: ${}\n\n🎊 از همه شرکت‌کنندگان سپاسگزاریم!",
        'education_title': "📚 **آموزش ترید**\n\nترید حرفه‌ای را از صفر تا صد یاد بگیر!",
        'education_buy': "💰 خرید دوره (۱۰۰ دلار)",
        'education_enter_wallet': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
        'education_after_wallet': "✅ **آدرس ذخیره شد!**\n\n💰 مبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ پس از واریز، دکمه **✅ پرداخت کردم** را بزنید.",
        'education_confirm': "✅ پرداخت کردم",
        'education_verifying': "⏳ در حال بررسی پرداخت شما...",
        'education_success': "✅ **پرداخت تایید شد!** 🎉\n\n🔗 هش: `{}`\n\n📚 **دسترسی فعال شد!**\n\nتمام محتوای دوره برای شما ارسال شد.",
        'education_failed': "❌ **پرداخت تایید نشد!**\n\nدلیل: {}\n\n📤 لطفاً هش تراکنش یا عکس واریز را ارسال کنید:",
        'education_already': "✅ شما قبلاً این دوره را خریداری کرده‌اید!",
        'subscribe_title': "💳 **اشتراک**\n\n💰 هزینه: ۱۰۰ دلار\n📅 اعتبار: ۳۰ روز",
        'subscribe_enter_wallet': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
        'subscribe_after_wallet': "✅ **آدرس ذخیره شد!**\n\n💰 مبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ پس از واریز، دکمه **✅ پرداخت کردم** را بزنید.",
        'subscribe_confirm': "✅ پرداخت کردم",
        'subscribe_success': "✅ **اشتراک فعال شد!** 🎉\n\n📚 تمام محتوای دوره برای شما ارسال شد.",
        'subscribe_failed': "❌ **اشتراک فعال نشد!**\n\nدلیل: {}\n\n📤 هش تراکنش یا عکس را ارسال کنید:",
        'subscribe_active': "✅ شما اشتراک فعال دارید!",
        'referral_text': "🔗 **سیستم رفرال**\n\n👤 شما: {}\n📊 دعوت‌ها: {}\n\n🔑 کد شما:\n`{}`\n\n🔗 لینک دعوت:\n{}\n\n💰 **پاداش:** ۵٪ از هر واریز",
        'referral_link': "https://t.me/UTYOB_Bot?start=ref_{}",
        'share': "📤 اشتراک‌گذاری",
        'guide_text': "📖 **راهنمای کامل**\n\n🎯 **مراحل:**\n1️⃣ اشتراک تهیه کنید (۱۰۰ دلار)\n2️⃣ در قرعه‌کشی شرکت کنید\n3️⃣ دوره آموزش ترید را بخرید\n4️⃣ برنده شوید!\n\n📞 پشتیبانی: با مدیریت تماس بگیرید.",
        'invalid_command': "⚠️ **دستور نامعتبر!**\n\nاز دکمه‌ها استفاده کنید.",
        'error_message': "⚠️ **خطا رخ داد!**\n\nدوباره تلاش کنید.",
        'invalid_wallet': "❌ **آدرس کیف پول نامعتبر!**\n\nیک آدرس TRC20 معتبر وارد کنید.\nمثال: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
        'tx_hash_invalid': "❌ **هش تراکنش نامعتبر!**\n\nهش ۶۴ کاراکتری معتبر وارد کنید.",
        'tx_hash_received': "✅ **هش تراکنش دریافت شد!**\n\n⏳ در حال بررسی توسط مدیریت...\n📢 به محض تایید اطلاع داده می‌شود.",
        'photo_received': "✅ **عکس دریافت شد!**\n\n⏳ در حال بررسی توسط مدیریت...",
        'no_subscription': "❌ **اشتراک فعال ندارید!**",
        'cancel': "❌ انصراف",
        'retry': "🔄 تلاش مجدد",
        'support': "📞 پشتیبانی",
        'withdraw_prize': "💰 برداشت جایزه",
        'no_winner': "❌ جایزه‌ای ندارید!",
        'already_paid': "✅ جایزه قبلاً پرداخت شده!",
        'enter_withdraw_wallet': "💰 آدرس کیف پول TRC20 خود را وارد کنید:",
        'withdraw_success': "✅ برداشت ثبت شد!",
    }
}

# ============================================================
# تایید پرداخت با API (۳ کلید برای پشتیبانی و سرعت)
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.current_api = 0
        self.session = None
        self.lock = threading.Lock()

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=200, limit_per_host=50)
            )
        return self.session

    def _next_api(self):
        with self.lock:
            api = self.apis[self.current_api]
            self.current_api = (self.current_api + 1) % len(self.apis)
            return api

    async def verify_transaction(self, from_address, to_address, amount, tx_id=None):
        session = await self.get_session()
        
        # تلاش با همه API‌ها
        for _ in range(len(self.apis) * 2):
            api = self._next_api()
            try:
                if tx_id:
                    success, result = await self._verify_by_txid(session, api, tx_id, from_address, to_address, amount)
                else:
                    success, result = await self._search_transactions(session, api, from_address, to_address, amount)
                
                if success:
                    return True, result, "Verified"
            except Exception as e:
                logger.warning(f"API {api} error: {e}")
                continue
        
        return False, None, "Transaction not found"

    async def _verify_by_txid(self, session, api, tx_id, from_address, to_address, amount):
        url = f"https://api.trongrid.io/v1/transactions/{tx_id}"
        headers = {"TRON-PRO-API-KEY": api}
        
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if self._validate(data, from_address, to_address, amount):
                    return True, tx_id
        return False, None

    async def _search_transactions(self, session, api, from_address, to_address, amount):
        url = f"https://api.trongrid.io/v1/accounts/{from_address}/transactions"
        params = {"limit": 50, "order_by": "block_timestamp,desc"}
        headers = {"TRON-PRO-API-KEY": api}
        
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                for tx in data.get('data', []):
                    if self._validate(tx, from_address, to_address, amount):
                        return True, tx.get('txID')
        return False, None

    def _validate(self, tx_data, from_address, to_address, amount):
        try:
            if tx_data.get('to') != to_address:
                return False
            tx_amount = tx_data.get('amount', 0) / 1_000_000
            if abs(tx_amount - amount) > 0.01:
                return False
            status = tx_data.get('status', '')
            if status and status != 'SUCCESS':
                return False
            return True
        except:
            return False

    def add_api(self, api_key):
        if api_key not in self.apis:
            self.apis.append(api_key)
            return True
        return False

payment_verifier = PaymentVerifier()

# ============================================================
# مدیریت کاربران
# ============================================================
class UserManager:
    @staticmethod
    def register_user(user_id, username=None, first_name=None, last_name=None):
        try:
            cursor = db.execute(user_id, "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                return False
            ref_code = hashlib.sha256(f"UTYOB_{user_id}_{time.time()}_{random.randint(1000,9999)}".encode()).hexdigest()[:10].upper()
            db.execute(user_id,
                "INSERT INTO users (user_id, username, first_name, last_name, referral_code, language) VALUES (?, ?, ?, ?, ?, 'en')",
                (user_id, username, first_name, last_name, ref_code)
            )
            return True
        except:
            return False

    @staticmethod
    def get_user(user_id):
        cache_key = f"user_{user_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            cursor = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                cache.set(cache_key, dict(result), ttl=300)
            return result
        except:
            return None

    @staticmethod
    def update_user(user_id, **kwargs):
        try:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            db.execute(user_id, f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", values)
            cache.delete(f"user_{user_id}")
            return True
        except:
            return False

    @staticmethod
    def get_referral_count(user_id):
        cache_key = f"ref_count_{user_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            results = db.execute_global("SELECT COUNT(*) as count FROM users WHERE referred_by = ?", (user_id,))
            total = sum(r['count'] for r in results)
            cache.set(cache_key, total, ttl=600)
            return total
        except:
            return 0

    @staticmethod
    def get_all_users():
        return db.execute_global("SELECT user_id FROM users")

    @staticmethod
    def get_active_users():
        return db.execute_global(
            "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
        )

user_manager = UserManager()

# ============================================================
# سیستم قرعه‌کشی
# ============================================================
class LotterySystem:
    def __init__(self):
        self.is_running = False
        self.lock = threading.Lock()
        self.current_lottery = None

    def create_lottery(self, winners_count, prize_per_winner, start_date, end_date):
        with self.lock:
            if self.is_running:
                return False, "یک قرعه‌کشی در حال اجراست!"
            
            cursor = db.execute(0,
                """INSERT INTO lotteries 
                   (winners_count, prize_per_winner, total_prize, start_date, end_date, status) 
                   VALUES (?, ?, ?, ?, ?, 'scheduled')""",
                (winners_count, prize_per_winner, winners_count * prize_per_winner, start_date, end_date)
            )
            return True, cursor.lastrowid

    def start_lottery(self, lottery_id):
        with self.lock:
            if self.is_running:
                return False, "قرعه‌کشی در حال اجراست!"
            
            cursor = db.execute(0,
                "SELECT * FROM lotteries WHERE id = ? AND status = 'scheduled'",
                (lottery_id,)
            )
            lottery = cursor.fetchone()
            if not lottery:
                return False, "قرعه‌کشی یافت نشد!"
            
            eligible = db.execute_global(
                "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
            )
            eligible_users = [r['user_id'] for r in eligible]
            
            if len(eligible_users) < lottery['winners_count']:
                return False, "تعداد شرکت‌کنندگان کافی نیست!"
            
            # انتخاب برنده
            winners = random.sample(eligible_users, lottery['winners_count'])
            
            # ذخیره برندگان
            for uid in winners:
                user = user_manager.get_user(uid)
                db.execute(uid,
                    "INSERT INTO winners (lottery_id, user_id, prize_amount, wallet_address, paid_status) VALUES (?, ?, ?, ?, 0)",
                    (lottery_id, uid, lottery['prize_per_winner'], user['wallet_address'] if user else None)
                )
            
            # به‌روزرسانی قرعه‌کشی
            db.execute(0,
                "UPDATE lotteries SET status = 'completed', winner_id = ?, winner_confirmed = 0 WHERE id = ?",
                (winners[0], lottery_id)
            )
            
            self.is_running = False
            return True, {
                'lottery_id': lottery_id,
                'winner': winners[0],
                'prize': lottery['prize_per_winner'],
                'winners': winners
            }

    def confirm_winner(self, lottery_id):
        db.execute(0,
            "UPDATE lotteries SET winner_confirmed = 1 WHERE id = ?",
            (lottery_id,)
        )
        cache.delete(f"lottery_{lottery_id}")

    def get_lottery(self, lottery_id):
        cache_key = f"lottery_{lottery_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        cursor = db.execute(0, "SELECT * FROM lotteries WHERE id = ?", (lottery_id,))
        result = cursor.fetchone()
        if result:
            cache.set(cache_key, dict(result), ttl=300)
        return result

    def get_pending_lotteries(self):
        return db.execute_global(
            "SELECT * FROM lotteries WHERE status = 'scheduled' ORDER BY start_date ASC"
        )

    def get_unconfirmed_winners(self):
        return db.execute_global(
            "SELECT * FROM lotteries WHERE status = 'completed' AND winner_confirmed = 0"
        )

lottery_system = LotterySystem()

# ============================================================
# مدیریت محتوای آموزشی
# ============================================================
class CourseManager:
    @staticmethod
    def add_content(content_type, title, content, file_id=None, file_name=None, file_size=None):
        cursor = db.execute(0,
            "INSERT INTO course_content (content_type, title, content, file_id, file_name, file_size) VALUES (?, ?, ?, ?, ?, ?)",
            (content_type, title, content, file_id, file_name, file_size)
        )
        cache.delete("course_content_all")
        return cursor.lastrowid

    @staticmethod
    def get_all_content():
        cached = cache.get("course_content_all")
        if cached:
            return cached
        
        results = db.execute_global("SELECT * FROM course_content ORDER BY created_at DESC")
        cache.set("course_content_all", results, ttl=600)
        return results

    @staticmethod
    def get_content_count():
        cached = cache.get("course_content_count")
        if cached is not None:
            return cached
        
        results = db.execute_global("SELECT COUNT(*) as count FROM course_content")
        total = sum(r['count'] for r in results)
        cache.set("course_content_count", total, ttl=600)
        return total

    @staticmethod
    def has_user_received(user_id, content_id):
        cache_key = f"content_sent_{user_id}_{content_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        cursor = db.execute(user_id,
            "SELECT * FROM content_sent WHERE user_id = ? AND content_id = ?",
            (user_id, content_id)
        )
        result = cursor.fetchone() is not None
        cache.set(cache_key, result, ttl=3600)
        return result

    @staticmethod
    def mark_as_sent(user_id, content_id):
        db.execute(user_id,
            "INSERT OR IGNORE INTO content_sent (user_id, content_id) VALUES (?, ?)",
            (user_id, content_id)
        )
        cache.delete(f"content_sent_{user_id}_{content_id}")

    @staticmethod
    async def send_content_to_user(bot, user_id, content, is_education=True):
        try:
            if is_education:
                prefix = "📚 **دوره آموزش ترید**\n\n"
            else:
                prefix = ""

            if content['content_type'] == 'text':
                await bot.send_message(
                    user_id,
                    f"{prefix}**{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif content['content_type'] == 'photo':
                await bot.send_photo(
                    user_id,
                    content['file_id'],
                    caption=f"{prefix}**{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif content['content_type'] == 'video':
                await bot.send_video(
                    user_id,
                    content['file_id'],
                    caption=f"{prefix}**{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif content['content_type'] == 'document':
                await bot.send_document(
                    user_id,
                    content['file_id'],
                    caption=f"{prefix}**{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            return True
        except Exception as e:
            logger.error(f"Error sending content to {user_id}: {e}")
            return False

course_manager = CourseManager()

# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()
        self.pending_actions = {}
        self.broadcast_lock = threading.Lock()

    def _setup_handlers(self):
        app = self.application
        
        # دستورات
        app.add_handler(CommandHandler("start", self.start_command))
        
        # منو
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.education_callback, pattern="^education$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.subscribe_callback, pattern="^subscribe$"))
        
        # قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.lottery_join_callback, pattern="^lottery_join$"))
        app.add_handler(CallbackQueryHandler(self.lottery_confirm_callback, pattern="^lottery_confirm$"))
        
        # آموزش
        app.add_handler(CallbackQueryHandler(self.education_buy_callback, pattern="^education_buy$"))
        app.add_handler(CallbackQueryHandler(self.education_confirm_callback, pattern="^education_confirm$"))
        
        # پنل مدیریت (فارسی)
        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_start_lottery_callback, pattern="^admin_start_lottery$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_send_course_callback, pattern="^admin_send_course$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_content_callback, pattern="^admin_add_content$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api_callback, pattern="^admin_add_api$"))
        app.add_handler(CallbackQueryHandler(self.admin_stats_callback, pattern="^admin_stats$"))
        app.add_handler(CallbackQueryHandler(self.admin_confirm_winner_callback, pattern="^admin_confirm_winner_"))
        app.add_handler(CallbackQueryHandler(self.admin_start_scheduled_callback, pattern="^admin_start_scheduled_"))
        
        # تایید/رد
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))
        
        # پیام‌ها
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        app.add_error_handler(self.error_handler)

    # ============================================================
    # توابع کمکی
    # ============================================================
    
    def _get_lang(self, user_id):
        user = user_manager.get_user(user_id)
        if user and user.get('language') in LANGUAGES:
            return user['language']
        return 'en'  # زبان پیش‌فرض انگلیسی

    def _get_text(self, user_id, key, *args):
        lang = self._get_lang(user_id)
        text = LANGUAGES[lang].get(key, LANGUAGES['en'].get(key, key))
        if args:
            try:
                return text.format(*args)
            except:
                return text
        return text

    def _validate_wallet(self, address):
        try:
            if len(address) != 34:
                return False
            valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
            if not all(c in valid_chars for c in address):
                return False
            base58.b58decode(address)
            return True
        except:
            return False

    def _validate_tx_hash(self, tx_hash):
        return len(tx_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in tx_hash)

    def _validate_date(self, date_str):
        try:
            datetime.strptime(date_str, '%Y.%m.%d')
            return True
        except:
            return False

    async def _verify_payment(self, user_id, from_address, amount, tx_hash=None):
        return await payment_verifier.verify_transaction(from_address, DESTINATION_WALLET, amount, tx_hash)

    async def _send_all_course(self, user_id, is_education=True):
        contents = course_manager.get_all_content()
        sent = 0
        for c in contents:
            if not course_manager.has_user_received(user_id, c['id']):
                if await course_manager.send_content_to_user(self.application.bot, user_id, c, is_education):
                    course_manager.mark_as_sent(user_id, c['id'])
                    sent += 1
                    await asyncio.sleep(0.15)
        return sent

    async def _broadcast_to_all(self, text, parse_mode=None, reply_markup=None):
        users = user_manager.get_all_users()
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(
                    user['user_id'],
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                sent += 1
                if sent % 50 == 0:
                    await asyncio.sleep(0.3)
            except:
                failed += 1
        
        return sent, failed

    # ============================================================
    # دستور /start
    # ============================================================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_manager.register_user(user.id, user.username, user.first_name, user.last_name)

        if context.args and context.args[0].startswith('ref_'):
            ref_code = context.args[0][4:]
            cursor = db.execute(0, "SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
            ref_user = cursor.fetchone()
            if ref_user and ref_user['user_id'] != user.id:
                user_manager.update_user(user.id, referred_by=ref_user['user_id'])

        lang = self._get_lang(user.id)
        
        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['lottery'], callback_data="lottery")],
            [InlineKeyboardButton(LANGUAGES[lang]['education'], callback_data="education")],
            [InlineKeyboardButton(LANGUAGES[lang]['referral'], callback_data="referral")],
            [InlineKeyboardButton(LANGUAGES[lang]['guide'], callback_data="guide")],
            [InlineKeyboardButton(LANGUAGES[lang]['subscribe'], callback_data="subscribe")]
        ]
        if user.id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])

        await update.message.reply_text(
            LANGUAGES[lang]['welcome'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # منوی اصلی
    # ============================================================
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)

        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['lottery'], callback_data="lottery")],
            [InlineKeyboardButton(LANGUAGES[lang]['education'], callback_data="education")],
            [InlineKeyboardButton(LANGUAGES[lang]['referral'], callback_data="referral")],
            [InlineKeyboardButton(LANGUAGES[lang]['guide'], callback_data="guide")],
            [InlineKeyboardButton(LANGUAGES[lang]['subscribe'], callback_data="subscribe")]
        ]
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])

        await query.edit_message_text(
            LANGUAGES[lang]['main_menu'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # قرعه‌کشی
    # ============================================================
    async def lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)
        user = user_manager.get_user(user_id)

        if not user or not user.get('has_subscription'):
            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['subscribe'], callback_data="subscribe")],
                [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]
            ]
            await query.edit_message_text(
                LANGUAGES[lang]['lottery_no_subscription'],
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['lottery_join'], callback_data="lottery_join")],
            [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]
        ]
        await query.edit_message_text(
            LANGUAGES[lang]['lottery_title'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def lottery_join_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)

        context.user_data['action'] = 'lottery'
        context.user_data['waiting_for_wallet'] = True

        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['cancel'], callback_data="lottery")]]
        await query.edit_message_text(
            LANGUAGES[lang]['lottery_enter_wallet'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def lottery_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)
        user = user_manager.get_user(user_id)

        if not user or not user.get('wallet_address'):
            await query.edit_message_text(LANGUAGES[lang]['lottery_enter_wallet'], parse_mode=ParseMode.MARKDOWN)
            return

        await query.edit_message_text(LANGUAGES[lang]['lottery_verifying'], parse_mode=ParseMode.MARKDOWN)

        success, tx_id, msg = await self._verify_payment(user_id, user['wallet_address'], PAYMENT_AMOUNT)

        if success:
            db.execute(user_id,
                "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) VALUES (?, ?, ?, ?, ?, 'lottery', 'verified', CURRENT_TIMESTAMP)",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
            )
            user_manager.update_user(user_id, total_participations=(user.get('total_participations') or 0) + 1)

            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['lottery'], callback_data="lottery")],
                [InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]
            ]
            await query.edit_message_text(
                LANGUAGES[lang]['lottery_success'].format(tx_id),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            context.user_data['action'] = 'lottery'
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            context.user_data['tx_type'] = 'lottery'

            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['retry'], callback_data="lottery_confirm")],
                [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="lottery")]
            ]
            await query.edit_message_text(
                LANGUAGES[lang]['lottery_failed'].format(msg),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # آموزش
    # ============================================================
    async def education_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)

        cursor = db.execute(user_id,
            "SELECT * FROM transactions WHERE user_id = ? AND tx_type = 'education' AND status = 'verified'",
            (user_id,)
        )
        if cursor.fetchone():
            keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]]
            await query.edit_message_text(
                LANGUAGES[lang]['education_already'],
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['education_buy'], callback_data="education_buy")],
            [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]
        ]
        await query.edit_message_text(
            LANGUAGES[lang]['education_title'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def education_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)

        context.user_data['action'] = 'education'
        context.user_data['waiting_for_wallet'] = True

        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['cancel'], callback_data="education")]]
        await query.edit_message_text(
            LANGUAGES[lang]['education_enter_wallet'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def education_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)
        user = user_manager.get_user(user_id)

        if not user or not user.get('wallet_address'):
            await query.edit_message_text(LANGUAGES[lang]['education_enter_wallet'], parse_mode=ParseMode.MARKDOWN)
            return

        await query.edit_message_text(LANGUAGES[lang]['education_verifying'], parse_mode=ParseMode.MARKDOWN)

        success, tx_id, msg = await self._verify_payment(user_id, user['wallet_address'], PAYMENT_AMOUNT)

        if success:
            db.execute(user_id,
                "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) VALUES (?, ?, ?, ?, ?, 'education', 'verified', CURRENT_TIMESTAMP)",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
            )

            sent = await self._send_all_course(user_id, is_education=True)

            keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]]
            await query.edit_message_text(
                LANGUAGES[lang]['education_success'].format(tx_id) + f"\n\n📚 {sent} محتوا ارسال شد.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )

            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(admin_id, f"✅ خرید دوره جدید!\n👤 کاربر: {user_id}\n💰 مبلغ: ۱۰۰$")
                except:
                    pass
        else:
            context.user_data['action'] = 'education'
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            context.user_data['tx_type'] = 'education'

            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['retry'], callback_data="education_confirm")],
                [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="education")]
            ]
            await query.edit_message_text(
                LANGUAGES[lang]['education_failed'].format(msg),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # اشتراک
    # ============================================================
    async def subscribe_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)
        user = user_manager.get_user(user_id)

        if user and user.get('has_subscription'):
            sent = await self._send_all_course(user_id, is_education=True)
            keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]]
            await query.edit_message_text(
                f"✅ {LANGUAGES[lang]['subscribe_active']}\n\n📚 {sent} محتوا ارسال شد.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        context.user_data['action'] = 'subscribe'
        context.user_data['waiting_for_wallet'] = True

        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['cancel'], callback_data="main_menu")]]
        await query.edit_message_text(
            LANGUAGES[lang]['subscribe_enter_wallet'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # رفرال و راهنما
    # ============================================================
    async def referral_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)
        user = user_manager.get_user(user_id)

        if not user:
            return

        ref_count = user_manager.get_referral_count(user_id)
        ref_link = f"https://t.me/{self.application.bot.username}?start=ref_{user['referral_code']}"

        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['share'], url=f"https://t.me/share/url?url={ref_link}")],
            [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]
        ]
        await query.edit_message_text(
            LANGUAGES[lang]['referral_text'].format(
                user.get('first_name') or user_id,
                ref_count,
                user['referral_code'],
                ref_link
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_lang(user_id)

        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]]
        await query.edit_message_text(
            LANGUAGES[lang]['guide_text'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # پنل مدیریت (کاملاً فارسی)
    # ============================================================
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if user_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return

        # آمار سریع با کش
        user_count = cache.get("total_users")
        if user_count is None:
            user_count = len(db.execute_global("SELECT user_id FROM users"))
            cache.set("total_users", user_count, ttl=300)

        pending = cache.get("pending_count")
        if pending is None:
            pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
            cache.set("pending_count", pending, ttl=60)

        unconfirmed = len(lottery_system.get_unconfirmed_winners())

        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton(f"✅ تایید دستی ({pending})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📚 ارسال محتوای دوره", callback_data="admin_send_course")],
            [InlineKeyboardButton("📝 افزودن محتوای جدید", callback_data="admin_add_content")],
            [InlineKeyboardButton("🔑 افزودن کلید API", callback_data="admin_add_api")],
            [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        
        if unconfirmed > 0:
            keyboard.insert(0, [InlineKeyboardButton(f"🏆 تایید برنده ({unconfirmed})", callback_data="admin_confirm_winner_0")])

        await query.edit_message_text(
            f"⚙️ **پنل مدیریت**\n\n"
            f"👥 کاربران: {user_count:,}\n"
            f"⏳ در انتظار تایید: {pending}\n"
            f"🏆 برندگان تایید نشده: {unconfirmed}\n"
            f"📚 محتوا: {course_manager.get_content_count()}\n"
            f"🔑 کلیدهای API: {len(payment_verifier.apis)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - ارسال همگانی
    # ============================================================
    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'broadcast'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "📢 **ارسال پیام همگانی**\n\n"
            "متن پیام را ارسال کنید:\n"
            "⚠️ به همه {:,} کاربر ارسال می‌شود.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - شروع قرعه‌کشی
    # ============================================================
    async def admin_start_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        
        context.user_data['admin_action'] = 'start_lottery'
        context.user_data['lottery_step'] = 1
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "🎰 **شروع قرعه‌کشی جدید**\n\n"
            "مرحله ۱/۴: تعداد برندگان را وارد کنید (۱ تا ۲۰):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - تایید دستی
    # ============================================================
    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return

        pending = db.execute_global(
            "SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC LIMIT 5"
        )

        if not pending:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await query.edit_message_text("✅ همه تراکنش‌ها تایید شده‌اند!", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        text = "✅ **تایید دستی تراکنش‌ها**\n\n"
        keyboard = []
        for p in pending:
            text += f"👤 کاربر: {p['user_id']}\n"
            text += f"💰 مبلغ: ${p['amount']}\n"
            text += f"📤 از: `{p['from_address']}`\n"
            text += f"📂 نوع: {p['tx_type']}\n"
            text += f"🔗 هش: `{p['tx_hash'] or 'ندارد'}`\n"
            if p['photo_file_id']:
                text += f"📷 عکس: دارد\n"
            text += "\n"
            keyboard.append([
                InlineKeyboardButton(f"✅ تایید #{p['id']}", callback_data=f"admin_verify_approve_{p['id']}"),
                InlineKeyboardButton(f"❌ رد #{p['id']}", callback_data=f"admin_verify_reject_{p['id']}")
            ])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - ارسال محتوای دوره
    # ============================================================
    async def admin_send_course_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'send_course'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "📚 **ارسال محتوای دوره**\n\n"
            "آیدی کاربر را وارد کنید:\n"
            "مثال: `123456789`\n\n"
            "یا برای ارسال به همه: `ALL`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - افزودن محتوا
    # ============================================================
    async def admin_add_content_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_content'
        context.user_data['content_step'] = 1
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "📝 **افزودن محتوای جدید**\n\nمرحله ۱/۳: عنوان را وارد کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - افزودن کلید API
    # ============================================================
    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_api'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "🔑 **افزودن کلید API جدید**\n\n"
            "کلید API ترونگرید را وارد کنید:\n\n"
            "مثال: `7ae83b63-fdf3-47e4-ac69-56f960a34f5b`\n\n"
            "⚠️ هرچه کلید بیشتر، سرعت تایید بالاتر.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - آمار
    # ============================================================
    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return

        user_count = len(db.execute_global("SELECT user_id FROM users"))
        active = len(db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"))
        content_count = course_manager.get_content_count()
        api_count = len(payment_verifier.apis)
        lottery_count = len(db.execute_global("SELECT id FROM lotteries"))
        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        
        cache_stats = cache.get_stats()

        tx_stats = db.execute_global(
            "SELECT tx_type, status, COUNT(*) as count FROM transactions GROUP BY tx_type, status"
        )
        tx_text = ""
        for r in tx_stats:
            tx_text += f"• {r['tx_type']} - {r['status']}: {r['count']}\n"

        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        await query.edit_message_text(
            f"📊 **آمار سیستم**\n\n"
            f"👥 کاربران: {user_count:,}\n"
            f"✅ اشتراک فعال: {active:,}\n"
            f"📚 محتوای دوره: {content_count}\n"
            f"🎰 قرعه‌کشی: {lottery_count}\n"
            f"⏳ در انتظار تایید: {pending}\n"
            f"🔑 کلیدهای API: {api_count}\n\n"
            f"⚡ **کش:**\n"
            f"• آیتم‌ها: {cache_stats['size']}\n"
            f"• نرخ برخورد: {cache_stats['hit_rate']:.1f}%\n\n"
            f"💳 **تراکنش‌ها:**\n{tx_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - تایید برنده
    # ============================================================
    async def admin_confirm_winner_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return

        unconfirmed = lottery_system.get_unconfirmed_winners()
        
        if not unconfirmed:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await query.edit_message_text("✅ همه برندگان تایید شده‌اند!", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        text = "🏆 **تایید برندگان**\n\n"
        keyboard = []
        
        for l in unconfirmed:
            winner = user_manager.get_user(l['winner_id'])
            winner_name = winner.get('first_name') or winner.get('username') or winner['user_id'] if winner else str(l['winner_id'])
            
            text += f"🎰 قرعه‌کشی #{l['id']}\n"
            text += f"👤 برنده: {winner_name}\n"
            text += f"💰 جایزه: ${l['prize_per_winner']}\n"
            text += f"📅 تاریخ: {l['created_at']}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ تایید #{l['id']}", callback_data=f"admin_confirm_winner_{l['id']}")
            ])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_confirm_winner_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید برنده و اعلان به همه کاربران"""
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        
        if admin_id not in ADMIN_IDS:
            return
        
        lottery_id = int(query.data.split('_')[-1])
        lottery = lottery_system.get_lottery(lottery_id)
        
        if not lottery:
            await query.edit_message_text("❌ قرعه‌کشی یافت نشد!")
            return
        
        # تایید برنده
        lottery_system.confirm_winner(lottery_id)
        
        # دریافت اطلاعات برنده
        winner = user_manager.get_user(lottery['winner_id'])
        winner_name = winner.get('first_name') or winner.get('username') or str(lottery['winner_id']) if winner else str(lottery['winner_id'])
        
        # پیام اعلان به همه کاربران
        lang = 'en'  # زبان پیش‌فرض
        announce_text = LANGUAGES[lang]['lottery_winner_announcement'].format(winner_name, lottery['prize_per_winner'])
        
        # ارسال به همه کاربران
        await query.edit_message_text("⏳ در حال ارسال اعلان به همه کاربران...")
        
        sent, failed = await self._broadcast_to_all(announce_text, ParseMode.MARKDOWN)
        
        # اطلاع به ادمین
        await query.edit_message_text(
            f"✅ **برنده تایید شد!**\n\n"
            f"🎰 قرعه‌کشی #{lottery_id}\n"
            f"👤 برنده: {winner_name}\n"
            f"💰 جایزه: ${lottery['prize_per_winner']}\n\n"
            f"📤 اعلان به کاربران:\n"
            f"• موفق: {sent:,}\n"
            f"• ناموفق: {failed:,}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # ارسال پیام خصوصی به برنده
        try:
            await self.application.bot.send_message(
                lottery['winner_id'],
                f"🏆 **تبریک! شما برنده قرعه‌کشی شدید!**\n\n"
                f"💰 جایزه: ${lottery['prize_per_winner']}\n\n"
                f"برای برداشت جایزه، از دکمه زیر استفاده کنید:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 برداشت جایزه", callback_data="withdraw_prize")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass

    # ============================================================
    # تایید/رد توسط ادمین
    # ============================================================
    async def admin_verify_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        
        if admin_id not in ADMIN_IDS:
            return

        pending_id = int(query.data.split('_')[-1])
        pending = db.execute(0,
            "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'",
            (pending_id,)
        ).fetchone()

        if not pending:
            await query.edit_message_text("❌ درخواست یافت نشد!")
            return

        user_id = pending['user_id']

        if pending['tx_type'] == 'subscribe':
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            db.execute(user_id, "UPDATE users SET has_subscription = 1, subscription_end = ? WHERE user_id = ?", (end_date, user_id))
            await self._send_all_course(user_id, is_education=True)

        elif pending['tx_type'] == 'lottery':
            user = user_manager.get_user(user_id)
            if user:
                user_manager.update_user(user_id, total_participations=(user.get('total_participations') or 0) + 1)

        db.execute(user_id,
            "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) VALUES (?, ?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
            (user_id, pending['from_address'], pending['to_address'], pending['amount'], pending['tx_hash'], pending['tx_type'])
        )

        db.execute(0, "UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")

        lang = self._get_lang(user_id)
        try:
            await self.application.bot.send_message(
                user_id,
                LANGUAGES[lang]['user_verify_approved'],
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass

        await query.edit_message_text(
            f"✅ تراکنش تایید شد!\n👤 کاربر: {user_id}\n📂 نوع: {pending['tx_type']}",
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_verify_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        
        if admin_id not in ADMIN_IDS:
            return

        pending_id = int(query.data.split('_')[-1])
        pending = db.execute(0,
            "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'",
            (pending_id,)
        ).fetchone()

        if not pending:
            await query.edit_message_text("❌ درخواست یافت نشد!")
            return

        user_id = pending['user_id']
        db.execute(0, "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")

        lang = self._get_lang(user_id)
        try:
            await self.application.bot.send_message(
                user_id,
                LANGUAGES[lang]['user_verify_rejected'],
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass

        await query.edit_message_text(
            f"❌ تراکنش رد شد!\n👤 کاربر: {user_id}",
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت پیام‌ها
    # ============================================================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        user_manager.register_user(user_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)

        admin_action = context.user_data.get('admin_action')

        # ===== ارسال همگانی =====
        if admin_action == 'broadcast':
            await update.message.reply_text("⏳ در حال ارسال به همه کاربران...")
            sent, failed = await self._broadcast_to_all(text, ParseMode.MARKDOWN)
            context.user_data['admin_action'] = None
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await update.message.reply_text(
                f"✅ ارسال همگانی کامل شد!\n📤 موفق: {sent:,}\n❌ ناموفق: {failed:,}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # ===== شروع قرعه‌کشی =====
        if admin_action == 'start_lottery':
            step = context.user_data.get('lottery_step', 1)
            
            if step == 1:  # تعداد برندگان
                try:
                    winners = int(text)
                    if 1 <= winners <= 20:
                        context.user_data['lottery_winners'] = winners
                        context.user_data['lottery_step'] = 2
                        await update.message.reply_text(
                            f"✅ تعداد برندگان: {winners}\n\n"
                            f"مرحله ۲/۴: مبلغ جایزه هر نفر را وارد کنید (حداقل ۱۰ دلار):"
                        )
                    else:
                        await update.message.reply_text("❌ عدد بین ۱ تا ۲۰ وارد کنید!")
                except:
                    await update.message.reply_text("❌ عدد معتبر وارد کنید!")
                    
            elif step == 2:  # مبلغ جایزه
                try:
                    prize = float(text)
                    if prize >= 10:
                        context.user_data['lottery_prize'] = prize
                        context.user_data['lottery_step'] = 3
                        await update.message.reply_text(
                            f"✅ جایزه هر نفر: ${prize}\n\n"
                            f"مرحله ۳/۴: تاریخ شروع را وارد کنید (فرمت: 2026.01.23):"
                        )
                    else:
                        await update.message.reply_text("❌ مبلغ حداقل ۱۰ دلار باشد!")
                except:
                    await update.message.reply_text("❌ عدد معتبر وارد کنید!")
                    
            elif step == 3:  # تاریخ شروع
                date_str = text.strip()
                if self._validate_date(date_str):
                    context.user_data['lottery_start_date'] = date_str
                    context.user_data['lottery_step'] = 4
                    
                    # تاریخ پایان = ۳۰ دقیقه بعد
                    start_dt = datetime.strptime(date_str, '%Y.%m.%d')
                    end_dt = start_dt + timedelta(minutes=30)
                    end_str = end_dt.strftime('%Y.%m.%d')
                    context.user_data['lottery_end_date'] = end_str
                    
                    await update.message.reply_text(
                        f"✅ تاریخ شروع: {date_str}\n"
                        f"✅ تاریخ پایان: {end_str} (۳۰ دقیقه بعد)\n\n"
                        f"مرحله ۴/۴: آیا قرعه‌کشی را شروع کنم؟\n\n"
                        f"📊 خلاصه:\n"
                        f"• تعداد برندگان: {context.user_data['lottery_winners']}\n"
                        f"• جایزه هر نفر: ${context.user_data['lottery_prize']}\n"
                        f"• شروع: {date_str}\n"
                        f"• پایان: {end_str}\n\n"
                        f"برای تایید، **/confirm** را ارسال کنید.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text("❌ فرمت تاریخ اشتباه! از فرمت `2026.01.23` استفاده کنید.")
                    
            elif step == 4:  # تایید نهایی
                if text.lower() == '/confirm':
                    winners = context.user_data['lottery_winners']
                    prize = context.user_data['lottery_prize']
                    start = context.user_data['lottery_start_date']
                    end = context.user_data['lottery_end_date']
                    
                    success, result = lottery_system.create_lottery(winners, prize, start, end)
                    
                    if success:
                        context.user_data['admin_action'] = None
                        context.user_data['lottery_step'] = None
                        
                        # اعلان به همه کاربران
                        active_users = user_manager.get_active_users()
                        announce_text = LANGUAGES['en']['lottery_announcement'].format(
                            winners * prize,
                            len(active_users)
                        )
                        
                        await update.message.reply_text("⏳ در حال ارسال اعلان به همه کاربران...")
                        
                        sent, failed = await self._broadcast_to_all(announce_text, ParseMode.MARKDOWN)
                        
                        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                        await update.message.reply_text(
                            f"✅ **قرعه‌کشی ثبت شد!**\n\n"
                            f"🆔 شماره: {result}\n"
                            f"👥 برندگان: {winners}\n"
                            f"💰 جایزه: ${prize}\n"
                            f"📅 شروع: {start}\n"
                            f"📅 پایان: {end}\n\n"
                            f"📤 اعلان ارسال شد:\n"
                            f"• موفق: {sent:,}\n"
                            f"• ناموفق: {failed:,}\n\n"
                            f"⏳ پس از پایان، برنده به مدیریت اعلام می‌شود.",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        # برنامه‌ریزی برای بررسی خودکار قرعه‌کشی
                        asyncio.create_task(self._auto_check_lottery(result))
                    else:
                        await update.message.reply_text(f"❌ خطا: {result}")
                else:
                    await update.message.reply_text("❌ برای تایید، **/confirm** را ارسال کنید.")
            return

        # ===== ارسال محتوای دوره =====
        if admin_action == 'send_course':
            if text.upper() == 'ALL':
                users = user_manager.get_all_users()
                sent = 0
                await update.message.reply_text(f"⏳ ارسال به {len(users)} کاربر...")
                for u in users:
                    count = await self._send_all_course(u['user_id'], is_education=True)
                    if count > 0:
                        sent += 1
                    await asyncio.sleep(0.15)
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(
                    f"✅ محتوا به {sent} کاربر ارسال شد!",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                try:
                    target_id = int(text)
                    count = await self._send_all_course(target_id, is_education=True)
                    context.user_data['admin_action'] = None
                    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                    await update.message.reply_text(
                        f"✅ {count} محتوا به کاربر {target_id} ارسال شد!",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except:
                    await update.message.reply_text("❌ آیدی نامعتبر!")
            return

        # ===== افزودن محتوا =====
        if admin_action == 'add_content':
            step = context.user_data.get('content_step', 1)
            if step == 1:
                context.user_data['content_title'] = text
                context.user_data['content_step'] = 2
                await update.message.reply_text("📝 مرحله ۲/۳: توضیحات متن را وارد کنید:")
            elif step == 2:
                context.user_data['content_text'] = text
                context.user_data['content_step'] = 3
                await update.message.reply_text(
                    "📝 مرحله ۳/۳: فایل را ارسال کنید (اختیاری)\n\n"
                    "می‌توانید ارسال کنید:\n"
                    "• 📷 عکس\n"
                    "• 🎬 ویدیو\n"
                    "• 📄 فایل (PDF و غیره)\n\n"
                    "یا برای فقط متن: `/skip`"
                )
            elif step == 3:
                if text.lower() == '/skip':
                    title = context.user_data.get('content_title', 'بدون عنوان')
                    content = context.user_data.get('content_text', '')
                    cid = course_manager.add_content('text', title, content)
                    context.user_data['admin_action'] = None
                    context.user_data['content_step'] = None
                    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                    await update.message.reply_text(
                        f"✅ محتوا اضافه شد!\n🆔 ID: {cid}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
            return

        # ===== افزودن کلید API =====
        if admin_action == 'add_api':
            api_key = text.strip()
            if payment_verifier.add_api(api_key):
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(
                    f"✅ کلید API اضافه شد!\n🔑 تعداد کلیدها: {len(payment_verifier.apis)}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ این کلید قبلاً اضافه شده است!")
            return

        # ===== دریافت هش تراکنش یا عکس =====
        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            
            # اگر هش معتبر نباشه، ممکنه عکس باشه
            if not self._validate_tx_hash(tx_hash):
                await update.message.reply_text("❌ هش تراکنش معتبر نیست! لطفاً عکس واریز یا هش را ارسال کنید.")
                return

            from_address = context.user_data.get('tx_from_address')
            tx_type = context.user_data.get('tx_type', 'lottery')

            db.execute(0,
                "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, tx_hash, tx_type, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
                (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash, tx_type)
            )

            context.user_data['waiting_for_tx_hash'] = False
            context.user_data['tx_from_address'] = None
            context.user_data['tx_type'] = None
            cache.delete("pending_count")

            lang = self._get_lang(user_id)
            await update.message.reply_text(LANGUAGES[lang]['tx_hash_received'], parse_mode=ParseMode.MARKDOWN)

            # اطلاع به ادمین‌ها
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [[
                        InlineKeyboardButton("✅ تایید", callback_data=f"admin_verify_approve_{db.execute(0, 'SELECT last_insert_rowid()').fetchone()[0]}"),
                        InlineKeyboardButton("❌ رد", callback_data=f"admin_verify_reject_{db.execute(0, 'SELECT last_insert_rowid()').fetchone()[0]}")
                    ]]
                    await self.application.bot.send_message(
                        admin_id,
                        f"✅ درخواست تایید جدید!\n\n"
                        f"👤 کاربر: {user_id}\n"
                        f"💰 مبلغ: ${PAYMENT_AMOUNT}\n"
                        f"📤 از: {from_address}\n"
                        f"📂 نوع: {tx_type}\n"
                        f"🔗 هش: `{tx_hash}`",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            return

        # ===== دریافت آدرس کیف پول =====
        if context.user_data.get('waiting_for_wallet'):
            wallet = text.strip()
            lang = self._get_lang(user_id)
            
            if not self._validate_wallet(wallet):
                await update.message.reply_text(LANGUAGES[lang]['invalid_wallet'], parse_mode=ParseMode.MARKDOWN)
                return

            user_manager.update_user(user_id, wallet_address=wallet)
            context.user_data['waiting_for_wallet'] = False

            action = context.user_data.get('action', 'lottery')
            context.user_data['action'] = None

            callback_map = {
                'lottery': ('lottery_confirm', 'lottery', LANGUAGES[lang]['lottery_after_wallet']),
                'education': ('education_confirm', 'education', LANGUAGES[lang]['education_after_wallet']),
                'subscribe': ('subscribe_confirm', 'main_menu', LANGUAGES[lang]['subscribe_after_wallet']),
            }
            cb, back, msg = callback_map.get(action, ('lottery_confirm', 'lottery', LANGUAGES[lang]['lottery_after_wallet']))

            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['lottery_confirm'], callback_data=cb)],
                [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data=back)]
            ]
            await update.message.reply_text(
                msg.format(DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ===== دستور نامعتبر =====
        lang = self._get_lang(user_id)
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]]
        await update.message.reply_text(
            LANGUAGES[lang]['invalid_command'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت فایل‌ها (عکس، ویدیو، سند)
    # ============================================================
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'photo')

    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'video')

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'document')

    async def _handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
        user_id = update.effective_user.id
        
        # اگر کاربر منتظر هش باشه و عکس بفرسته، به‌عنوان تایید دستی ذخیره میشه
        if context.user_data.get('waiting_for_tx_hash'):
            from_address = context.user_data.get('tx_from_address')
            tx_type = context.user_data.get('tx_type', 'lottery')
            
            # ذخیره عکس
            file_id = None
            if media_type == 'photo':
                file_id = update.message.photo[-1].file_id
            elif media_type == 'video':
                file_id = update.message.video.file_id
            elif media_type == 'document':
                file_id = update.message.document.file_id
            
            if file_id:
                db.execute(0,
                    "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, photo_file_id, tx_type, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
                    (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, file_id, tx_type)
                )
                
                context.user_data['waiting_for_tx_hash'] = False
                context.user_data['tx_from_address'] = None
                context.user_data['tx_type'] = None
                cache.delete("pending_count")
                
                lang = self._get_lang(user_id)
                await update.message.reply_text(LANGUAGES[lang]['photo_received'], parse_mode=ParseMode.MARKDOWN)
                
                # اطلاع به ادمین‌ها
                for admin_id in ADMIN_IDS:
                    try:
                        keyboard = [[
                            InlineKeyboardButton("✅ تایید", callback_data=f"admin_verify_approve_{db.execute(0, 'SELECT last_insert_rowid()').fetchone()[0]}"),
                            InlineKeyboardButton("❌ رد", callback_data=f"admin_verify_reject_{db.execute(0, 'SELECT last_insert_rowid()').fetchone()[0]}")
                        ]]
                        await self.application.bot.send_photo(
                            admin_id,
                            file_id,
                            caption=f"✅ درخواست تایید جدید (با عکس)!\n\n"
                                    f"👤 کاربر: {user_id}\n"
                                    f"💰 مبلغ: ${PAYMENT_AMOUNT}\n"
                                    f"📤 از: {from_address}\n"
                                    f"📂 نوع: {tx_type}",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    except:
                        pass
                return
        
        # افزودن محتوا توسط ادمین
        if user_id in ADMIN_IDS and context.user_data.get('admin_action') == 'add_content':
            step = context.user_data.get('content_step')
            if step != 3:
                return

            title = context.user_data.get('content_title', 'بدون عنوان')
            content = context.user_data.get('content_text', '')
            file_id = None
            file_name = None
            file_size = None

            if media_type == 'photo':
                photo = update.message.photo[-1]
                file_id = photo.file_id
                file_name = f"{title}.jpg"
                file_size = photo.file_size
            elif media_type == 'video':
                video = update.message.video
                file_id = video.file_id
                file_name = video.file_name or f"{title}.mp4"
                file_size = video.file_size
            elif media_type == 'document':
                doc = update.message.document
                file_id = doc.file_id
                file_name = doc.file_name or f"{title}.pdf"
                file_size = doc.file_size

            if file_id:
                cid = course_manager.add_content(media_type, title, content, file_id, file_name, file_size)
                context.user_data['admin_action'] = None
                context.user_data['content_step'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(
                    f"✅ محتوا اضافه شد!\n📚 عنوان: {title}\n📂 نوع: {media_type}\n🆔 ID: {cid}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )

    # ============================================================
    # بررسی خودکار قرعه‌کشی (هر ۳۰ دقیقه)
    # ============================================================
    async def _auto_check_lottery(self, lottery_id):
        """بررسی خودکار قرعه‌کشی بعد از ۳۰ دقیقه"""
        await asyncio.sleep(1800)  # ۳۰ دقیقه
        
        try:
            lottery = lottery_system.get_lottery(lottery_id)
            if not lottery or lottery['status'] != 'scheduled':
                return
            
            # شروع قرعه‌کشی
            success, result = lottery_system.start_lottery(lottery_id)
            
            if success:
                # اطلاع به ادمین
                winner = user_manager.get_user(result['winner'])
                winner_name = winner.get('first_name') or winner.get('username') or str(result['winner']) if winner else str(result['winner'])
                
                for admin_id in ADMIN_IDS:
                    try:
                        keyboard = [[
                            InlineKeyboardButton(
                                f"✅ تایید برنده #{lottery_id}",
                                callback_data=f"admin_confirm_winner_{lottery_id}"
                            )
                        ]]
                        await self.application.bot.send_message(
                            admin_id,
                            f"🏆 **برنده قرعه‌کشی مشخص شد!**\n\n"
                            f"🎰 قرعه‌کشی #{lottery_id}\n"
                            f"👤 برنده: {winner_name}\n"
                            f"💰 جایزه: ${result['prize']}\n\n"
                            f"⚠️ برای اعلان به همه کاربران، دکمه تایید را بزنید.",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass
            else:
                logger.error(f"Lottery auto-start failed: {result}")
                
        except Exception as e:
            logger.error(f"Auto lottery check error: {e}")

    # ============================================================
    # مدیریت خطاها
    # ============================================================
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.effective_user:
                user_id = update.effective_user.id
                lang = self._get_lang(user_id)
                await self.application.bot.send_message(
                    user_id,
                    LANGUAGES[lang]['error_message'],
                    parse_mode=ParseMode.MARKDOWN
                )
        except:
            pass

# ============================================================
# اجرا
# ============================================================
async def main():
    try:
        bot = UTYOBot()
        logger.info("🚀 ربات سلطنتی UTYOB در حال اجراست...")
        logger.info(f"👥 مدیران: {ADMIN_IDS}")
        logger.info(f"🔑 کلیدهای API: {len(TRONGRID_APIS)}")
        logger.info(f"🗄️ شاردها: {DB_SHARDS}")
        
        await bot.application.initialize()
        await bot.application.start()
        await bot.application.updater.start_polling()
        
        logger.info("✅ ربات با موفقیت اجرا شد!")
        
        # ارسال خودکار محتوا به کاربران دارای اشتراک (هر ساعت)
        while True:
            try:
                users = db.execute_global(
                    "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
                )
                for u in users:
                    await bot._send_all_course(u['user_id'], is_education=True)
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Auto-send error: {e}")
            await asyncio.sleep(3600)
            
    except KeyboardInterrupt:
        logger.info("🛑 ربات متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 برنامه متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {e}")