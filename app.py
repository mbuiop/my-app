# ============================================================
# UTYOB Bot - Trading Course Subscription (EN/FA)
# No lottery, no paid-referral scheme.
# Automatic on-chain payment verification (TronGrid) + admin API-key management
# Sharded DB + in-memory cache, designed to scale to 500,000+ users
# ============================================================

import asyncio
import logging
import sqlite3
import base58
import aiohttp
import threading
import time
import os
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# Config — never hardcode real secrets here. Set them as
# environment variables on your server instead.
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(i) for i in os.environ.get('ADMIN_IDS', '123456789').split(',')]

# TronGrid API keys for automatic on-chain verification (more can be added from the admin panel)
TRONGRID_APIS = [
    k.strip() for k in os.environ.get('TRONGRID_APIS', '').split(',') if k.strip()
] or ["YOUR_TRONGRID_API_KEY_HERE"]

DESTINATION_WALLET = os.environ.get('DESTINATION_WALLET', 'YOUR_WALLET_ADDRESS_HERE')
PAYMENT_AMOUNT = float(os.environ.get('PAYMENT_AMOUNT', '100'))
SUBSCRIPTION_DAYS = int(os.environ.get('SUBSCRIPTION_DAYS', '30'))
DB_SHARDS = int(os.environ.get('DB_SHARDS', '200'))
CACHE_TTL = 600
DEFAULT_LANG = 'en'


# ============================================================
# Sharded database
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
            conn = sqlite3.connect(f"data/shard_{i}.db", check_same_thread=False, timeout=60)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=50000")
            conn.execute("PRAGMA temp_store=MEMORY")
            self.connections[i] = conn
            self.locks[i] = threading.Lock()
            self._create_tables(conn)

    def _create_tables(self, conn):
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT,
                wallet_address TEXT,
                has_subscription INTEGER DEFAULT 0,
                subscription_end TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_id TEXT,
                status TEXT DEFAULT 'pending',
                verified_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Only used when automatic on-chain verification fails (e.g. network delay):
        # the user submits their real tx hash and an admin checks it on the chain explorer.
        c.execute('''
            CREATE TABLE IF NOT EXISTS pending_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS content_sent (
                user_id INTEGER,
                content_id INTEGER,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, content_id)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_verifications(status)')
        conn.commit()

    def get_shard(self, user_id):
        return hash(str(user_id)) % self.num_shards

    def execute(self, user_id, query, params=(), commit=True):
        shard = self.get_shard(user_id)
        conn = self.connections[shard]
        with self.locks[shard]:
            cur = conn.cursor()
            cur.execute(query, params)
            if commit:
                conn.commit()
            return cur

    def execute_global(self, query, params=()):
        results = []
        for shard_id, conn in self.connections.items():
            with self.locks[shard_id]:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                results.extend(cur.fetchall())
        return results


db = DatabaseManager()


# ============================================================
# In-memory cache
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
            self.cache.pop(key, None)
            self.expiry.pop(key, None)
            self.misses += 1
            return None

    def set(self, key, value, ttl=None):
        with self.lock:
            self.cache[key] = value
            self.expiry[key] = time.time() + (ttl or self.ttl)

    def delete(self, key):
        with self.lock:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)

    def get_stats(self):
        with self.lock:
            total = self.hits + self.misses
            return {
                'size': len(self.cache),
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': (self.hits / total * 100) if total else 0
            }


cache = AdvancedCache()


# ============================================================
# Bilingual text (English / Persian)
# ============================================================
LANGUAGES = {
    'en': {
        'name': 'English',
        'choose_language': "🌐 Please choose your language:",
        'welcome': "🎓 **Welcome to the UTYOB Trading Course Bot!**\n\nChoose an option below:",
        'main_menu': "🎯 **Main Menu**",
        'education': "📚 Trading Course",
        'guide': "📖 Guide",
        'language_btn': "🌐 Language",
        'back': "🔙 Back",
        'main_menu_btn': "🏠 Main Menu",
        'cancel': "❌ Cancel",
        'retry': "🔄 Retry",
        'education_title': "📚 **Trading Course**\n\nLearn professional trading from zero to hero.\n\n💰 Price: {}$ (USDT-TRC20)\n📅 Access length: {} days",
        'education_buy': "💳 Buy / Renew Access",
        'education_active': "✅ You already have active access.\n📅 Valid until: {}",
        'enter_wallet': "📤 **Enter the TRC20 wallet address you will pay from:**",
        'invalid_wallet': "❌ Invalid wallet address.\nExample format: `TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`",
        'after_wallet': "✅ Address saved.\n\n💰 Please send {}$ (USDT-TRC20) to:\n`{}`\n\n⚠️ After sending, tap **✅ I've made the payment**.",
        'confirm_payment': "✅ I've made the payment",
        'verifying': "⏳ Verifying your transaction on-chain... please wait.",
        'verify_success': "✅ **Payment verified!**\n\n🔗 TX hash: `{}`\n\n📚 {} item(s) of course content sent.",
        'verify_failed': "❌ We couldn't automatically confirm the transaction yet.\n\nReason: {}\n\nIf you're sure you paid, send your TX hash here so admin can check it manually:",
        'tx_hash_invalid': "❌ Invalid TX hash. It must be 64 characters.",
        'tx_hash_received': "✅ TX hash received.\n⏳ Being reviewed by admin — you'll be notified once verified.",
        'guide_text': "📖 **Guide**\n\n1️⃣ Tap “Trading Course”\n2️⃣ Enter your TRC20 wallet address\n3️⃣ Send the payment, then tap “I've made the payment”\n4️⃣ Your transaction is checked automatically on-chain and access is activated\n\n📞 Support: contact the admin.",
        'invalid_command': "⚠️ Invalid input. Please use the buttons.",
        'error_message': "⚠️ Something went wrong. Please try again.",
        'payment_confirmed_admin_note': "✅ Payment auto-verified\n👤 User: {}\n💰 Amount: {}$",
        'admin_only': "⛔ Unauthorized.",
        'admin_panel_title': "⚙️ **Admin Panel**\n\n👥 Users: {}\n⏳ Pending manual review: {}\n📚 Course items: {}\n🔑 API keys: {}",
        'admin_broadcast_btn': "📢 Broadcast message",
        'admin_manual_verify_btn': "✅ Manual verify ({})",
        'admin_send_course_btn': "📚 Send course content",
        'admin_add_content_btn': "📝 Add new content",
        'admin_add_api_btn': "🔑 Add API key",
        'admin_stats_btn': "📊 Stats",
        'admin_back_btn': "🔙 Back",
        'admin_cancel_btn': "🔙 Cancel",
        'admin_broadcast_prompt': "📢 **Broadcast message**\n\nSend the text to broadcast to all users:",
        'admin_no_pending': "✅ Nothing pending review!",
        'admin_pending_header': "✅ **Manual review queue**\n(only items where auto-verification couldn't confirm on-chain)\n\n",
        'admin_approve': "✅ Approve #{}",
        'admin_reject': "❌ Reject #{}",
        'admin_send_course_prompt': "📚 **Send course content**\n\nEnter a numeric user ID, or send `ALL` to send to everyone:",
        'admin_add_content_step1': "📝 **Add new content**\n\nStep 1/3 — send the title:",
        'admin_add_content_step2': "📝 Step 2/3 — send the description text:",
        'admin_add_content_step3': "📝 Step 3/3 — send a file (photo/video/document), or send /skip for text-only:",
        'admin_content_added': "✅ Content added! ID: {}",
        'admin_add_api_prompt': "🔑 **Add a TronGrid API key**\n\nSend the key.\n⚠️ More keys = faster, more reliable auto-verification.",
        'admin_api_added': "✅ API key added!\n🔑 Total keys: {}",
        'admin_api_duplicate': "❌ This key was already added!",
        'admin_stats_title': "📊 **System stats**\n\n👥 Total users: {}\n✅ Active subscriptions: {}\n📚 Course items: {}\n⏳ Pending manual review: {}\n🔑 API keys: {}\n\n⚡ Cache: {} items | hit rate {:.1f}%",
        'admin_refresh': "🔄 Refresh",
        'admin_not_found': "❌ Request not found or already reviewed.",
        'admin_approved_note': "✅ Transaction approved!\n👤 User: {}",
        'admin_rejected_note': "❌ Transaction rejected!\n👤 User: {}",
        'admin_approved_user_msg': "✅ Your payment has been verified and your course access is now active.",
        'admin_rejected_user_msg': "❌ Your transaction could not be verified. Please contact support.",
        'admin_broadcast_sent': "✅ Broadcast complete!\n📤 Sent: {}\n❌ Failed: {}",
        'admin_broadcast_sending': "⏳ Sending to all users...",
        'admin_send_course_sending_all': "⏳ Sending to {} users...",
        'admin_send_course_done_all': "✅ Content sent to {} users!",
        'admin_send_course_done_one': "✅ {} item(s) sent to user {}!",
        'admin_invalid_id': "❌ Invalid user ID!",
        'admin_new_manual_request': "✅ New manual review request (auto-verify failed)\n\n👤 User: {}\n💰 Amount: {}$\n📤 From: {}\n🔗 Hash: `{}`",
    },
    'fa': {
        'name': 'فارسی',
        'choose_language': "🌐 لطفاً زبان خود را انتخاب کنید:",
        'welcome': "🎓 **به ربات دوره آموزش ترید UTYOB خوش آمدید!**\n\nیکی از گزینه‌ها را انتخاب کنید:",
        'main_menu': "🎯 **منوی اصلی**",
        'education': "📚 دوره آموزش ترید",
        'guide': "📖 راهنما",
        'language_btn': "🌐 زبان",
        'back': "🔙 بازگشت",
        'main_menu_btn': "🏠 منوی اصلی",
        'cancel': "❌ انصراف",
        'retry': "🔄 تلاش مجدد",
        'education_title': "📚 **دوره آموزش ترید**\n\nترید حرفه‌ای را از صفر تا صد یاد بگیرید.\n\n💰 هزینه: {}$ (USDT-TRC20)\n📅 مدت دسترسی: {} روز",
        'education_buy': "💳 خرید / تمدید دسترسی",
        'education_active': "✅ شما در حال حاضر دسترسی فعال دارید.\n📅 تا تاریخ: {}",
        'enter_wallet': "📤 **آدرس کیف‌پول TRC20 خودتان را وارد کنید** (همان آدرسی که پرداخت را از آن انجام می‌دهید):",
        'invalid_wallet': "❌ آدرس کیف‌پول نامعتبر است.\nفرمت صحیح: `TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`",
        'after_wallet': "✅ آدرس ذخیره شد.\n\n💰 لطفاً مبلغ {}$ (USDT-TRC20) را به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ پس از واریز، دکمه‌ی **✅ پرداخت را انجام دادم** را بزنید.",
        'confirm_payment': "✅ پرداخت را انجام دادم",
        'verifying': "⏳ در حال بررسی تراکنش روی بلاکچین... چند لحظه صبر کنید.",
        'verify_success': "✅ **پرداخت تایید شد!**\n\n🔗 هش تراکنش: `{}`\n\n📚 {} محتوا برای شما ارسال شد.",
        'verify_failed': "❌ تراکنش هنوز به‌صورت خودکار تایید نشد.\n\nدلیل: {}\n\nاگر مطمئنید پرداخت را انجام دادید، هش تراکنش را همینجا بفرستید تا مدیریت به‌صورت دستی بررسی کند:",
        'tx_hash_invalid': "❌ هش تراکنش نامعتبر است. هش باید ۶۴ کاراکتر باشد.",
        'tx_hash_received': "✅ هش تراکنش دریافت شد.\n⏳ در حال بررسی توسط مدیریت... به محض تایید به شما اطلاع داده می‌شود.",
        'guide_text': "📖 **راهنما**\n\n۱️⃣ روی «دوره آموزش ترید» بزنید\n۲️⃣ آدرس کیف‌پول TRC20 خود را وارد کنید\n۳️⃣ مبلغ را واریز کرده و «پرداخت را انجام دادم» را بزنید\n۴️⃣ تراکنش شما خودکار روی بلاکچین بررسی و دسترسی فعال می‌شود\n\n📞 پشتیبانی: با مدیریت تماس بگیرید.",
        'invalid_command': "⚠️ ورودی نامعتبر است. لطفاً از دکمه‌ها استفاده کنید.",
        'error_message': "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
        'payment_confirmed_admin_note': "✅ پرداخت به‌صورت خودکار تایید شد\n👤 کاربر: {}\n💰 مبلغ: {}$",
        'admin_only': "⛔ دسترسی غیرمجاز.",
        'admin_panel_title': "⚙️ **پنل مدیریت**\n\n👥 کاربران: {}\n⏳ در انتظار بررسی دستی: {}\n📚 محتوای دوره: {}\n🔑 کلیدهای API: {}",
        'admin_broadcast_btn': "📢 ارسال پیام همگانی",
        'admin_manual_verify_btn': "✅ تایید دستی ({})",
        'admin_send_course_btn': "📚 ارسال محتوای دوره",
        'admin_add_content_btn': "📝 افزودن محتوای جدید",
        'admin_add_api_btn': "🔑 افزودن کلید API",
        'admin_stats_btn': "📊 آمار",
        'admin_back_btn': "🔙 بازگشت",
        'admin_cancel_btn': "🔙 انصراف",
        'admin_broadcast_prompt': "📢 **ارسال پیام همگانی**\n\nمتن پیام را ارسال کنید:",
        'admin_no_pending': "✅ موردی در انتظار بررسی نیست!",
        'admin_pending_header': "✅ **صف بررسی دستی**\n(فقط مواردی که تایید خودکار روی بلاکچین برایشان ممکن نشد)\n\n",
        'admin_approve': "✅ تایید #{}",
        'admin_reject': "❌ رد #{}",
        'admin_send_course_prompt': "📚 **ارسال محتوای دوره**\n\nآیدی عددی کاربر را وارد کنید، یا برای ارسال به همه: `ALL`",
        'admin_add_content_step1': "📝 **افزودن محتوای جدید**\n\nمرحله ۱/۳: عنوان را وارد کنید:",
        'admin_add_content_step2': "📝 مرحله ۲/۳: توضیحات متن را وارد کنید:",
        'admin_add_content_step3': "📝 مرحله ۳/۳: فایل را ارسال کنید (عکس/ویدیو/سند)، یا برای فقط متن: /skip",
        'admin_content_added': "✅ محتوا اضافه شد! ID: {}",
        'admin_add_api_prompt': "🔑 **افزودن کلید TronGrid API**\n\nکلید را ارسال کنید.\n⚠️ هرچه کلید بیشتر، تایید خودکار سریع‌تر و پایدارتر می‌شود.",
        'admin_api_added': "✅ کلید API اضافه شد!\n🔑 تعداد کلیدها: {}",
        'admin_api_duplicate': "❌ این کلید قبلاً اضافه شده است!",
        'admin_stats_title': "📊 **آمار سیستم**\n\n👥 کاربران کل: {}\n✅ اشتراک فعال: {}\n📚 محتوای دوره: {}\n⏳ در انتظار بررسی دستی: {}\n🔑 کلیدهای API: {}\n\n⚡ کش: {} آیتم | نرخ برخورد {:.1f}%",
        'admin_refresh': "🔄 به‌روزرسانی",
        'admin_not_found': "❌ درخواست یافت نشد یا قبلاً بررسی شده.",
        'admin_approved_note': "✅ تراکنش تایید شد!\n👤 کاربر: {}",
        'admin_rejected_note': "❌ تراکنش رد شد!\n👤 کاربر: {}",
        'admin_approved_user_msg': "✅ پرداخت شما تایید شد و دسترسی به دوره فعال شد.",
        'admin_rejected_user_msg': "❌ متاسفانه تراکنش شما تایید نشد. لطفاً با پشتیبانی تماس بگیرید.",
        'admin_broadcast_sent': "✅ ارسال همگانی کامل شد!\n📤 موفق: {}\n❌ ناموفق: {}",
        'admin_broadcast_sending': "⏳ در حال ارسال به همه کاربران...",
        'admin_send_course_sending_all': "⏳ در حال ارسال به {} کاربر...",
        'admin_send_course_done_all': "✅ محتوا به {} کاربر ارسال شد!",
        'admin_send_course_done_one': "✅ {} محتوا به کاربر {} ارسال شد!",
        'admin_invalid_id': "❌ آیدی نامعتبر!",
        'admin_new_manual_request': "✅ درخواست بررسی دستی جدید (تایید خودکار ناموفق بود)\n\n👤 کاربر: {}\n💰 مبلغ: {}$\n📤 از: {}\n🔗 هش: `{}`",
    }
}


# ============================================================
# Automatic on-chain payment verification via TronGrid
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = list(dict.fromkeys(TRONGRID_APIS))
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

    def add_api(self, api_key):
        with self.lock:
            if api_key in self.apis:
                return False
            self.apis.append(api_key)
            return True

    async def verify_transaction(self, from_address, to_address, amount, tx_id=None):
        session = await self.get_session()
        for _ in range(len(self.apis) * 2):
            api = self._next_api()
            try:
                if tx_id:
                    ok, result = await self._verify_by_txid(session, api, tx_id, to_address, amount)
                else:
                    ok, result = await self._search_transactions(session, api, from_address, to_address, amount)
                if ok:
                    return True, result, "verified"
            except Exception as e:
                logger.warning(f"TronGrid API error ({api[:8]}...): {e}")
                continue
        return False, None, "not_found"

    async def _verify_by_txid(self, session, api, tx_id, to_address, amount):
        url = f"https://api.trongrid.io/v1/transactions/{tx_id}"
        headers = {"TRON-PRO-API-KEY": api}
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if self._validate(data, to_address, amount):
                    return True, tx_id
        return False, None

    async def _search_transactions(self, session, api, from_address, to_address, amount):
        url = f"https://api.trongrid.io/v1/accounts/{from_address}/transactions"
        params = {"limit": 50, "order_by": "block_timestamp,desc"}
        headers = {"TRON-PRO-API-KEY": api}
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                for tx in data.get('data', []):
                    if self._validate(tx, to_address, amount):
                        return True, tx.get('txID')
        return False, None

    def _validate(self, tx_data, to_address, amount):
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
        except Exception:
            return False


payment_verifier = PaymentVerifier()


# ============================================================
# User manager
# ============================================================
class UserManager:
    @staticmethod
    def register_user(user_id, username=None, first_name=None, last_name=None):
        try:
            cur = db.execute(user_id, "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cur.fetchone():
                return False
            db.execute(user_id,
                "INSERT INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                (user_id, username, first_name, last_name)
            )
            return True
        except Exception:
            return False

    @staticmethod
    def get_user(user_id):
        cache_key = f"user_{user_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        cur = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        if result:
            result = dict(result)
            cache.set(cache_key, result, ttl=300)
        return result

    @staticmethod
    def update_user(user_id, **kwargs):
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [user_id]
        db.execute(user_id, f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", values)
        cache.delete(f"user_{user_id}")

    @staticmethod
    def get_all_users():
        return db.execute_global("SELECT user_id FROM users")

    @staticmethod
    def has_active_subscription(user):
        return bool(user and user.get('has_subscription') and user.get('subscription_end') and
                    user['subscription_end'] >= datetime.now().strftime('%Y-%m-%d'))


user_manager = UserManager()


# ============================================================
# Course content manager
# ============================================================
class CourseManager:
    @staticmethod
    def add_content(content_type, title, content, file_id=None, file_name=None, file_size=None):
        cur = db.execute(0,
            "INSERT INTO course_content (content_type, title, content, file_id, file_name, file_size) VALUES (?, ?, ?, ?, ?, ?)",
            (content_type, title, content, file_id, file_name, file_size)
        )
        cache.delete("course_content_all")
        cache.delete("course_content_count")
        return cur.lastrowid

    @staticmethod
    def get_all_content():
        cached = cache.get("course_content_all")
        if cached is not None:
            return cached
        results = db.execute_global("SELECT * FROM course_content ORDER BY created_at ASC")
        cache.set("course_content_all", results, ttl=600)
        return results

    @staticmethod
    def get_content_count():
        cached = cache.get("course_content_count")
        if cached is not None:
            return cached
        total = sum(r['count'] for r in db.execute_global("SELECT COUNT(*) as count FROM course_content"))
        cache.set("course_content_count", total, ttl=600)
        return total

    @staticmethod
    def has_user_received(user_id, content_id):
        cache_key = f"sent_{user_id}_{content_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        cur = db.execute(user_id, "SELECT 1 FROM content_sent WHERE user_id = ? AND content_id = ?", (user_id, content_id))
        result = cur.fetchone() is not None
        cache.set(cache_key, result, ttl=3600)
        return result

    @staticmethod
    def mark_as_sent(user_id, content_id):
        db.execute(user_id, "INSERT OR IGNORE INTO content_sent (user_id, content_id) VALUES (?, ?)", (user_id, content_id))
        cache.delete(f"sent_{user_id}_{content_id}")

    @staticmethod
    async def send_content_to_user(bot, user_id, content):
        try:
            caption = f"📚 **{content['title']}**\n\n{content['content'] or ''}"
            ct = content['content_type']
            if ct == 'text':
                await bot.send_message(user_id, caption, parse_mode=ParseMode.MARKDOWN)
            elif ct == 'photo':
                await bot.send_photo(user_id, content['file_id'], caption=caption, parse_mode=ParseMode.MARKDOWN)
            elif ct == 'video':
                await bot.send_video(user_id, content['file_id'], caption=caption, parse_mode=ParseMode.MARKDOWN)
            elif ct == 'document':
                await bot.send_document(user_id, content['file_id'], caption=caption, parse_mode=ParseMode.MARKDOWN)
            return True
        except Exception as e:
            logger.error(f"Error sending content to {user_id}: {e}")
            return False


course_manager = CourseManager()


# ============================================================
# Main bot class
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()

    def _setup_handlers(self):
        app = self.application
        app.add_handler(CommandHandler("start", self.start_command))

        app.add_handler(CallbackQueryHandler(self.lang_select_callback, pattern="^setlang_"))
        app.add_handler(CallbackQueryHandler(self.language_menu_callback, pattern="^language_menu$"))
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.education_callback, pattern="^education$"))
        app.add_handler(CallbackQueryHandler(self.education_buy_callback, pattern="^education_buy$"))
        app.add_handler(CallbackQueryHandler(self.education_confirm_callback, pattern="^education_confirm$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))

        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_send_course_callback, pattern="^admin_send_course$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_content_callback, pattern="^admin_add_content$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api_callback, pattern="^admin_add_api$"))
        app.add_handler(CallbackQueryHandler(self.admin_stats_callback, pattern="^admin_stats$"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))

        app.add_error_handler(self.error_handler)

    # ---------------- helpers ----------------
    def _get_lang(self, user_id):
        user = user_manager.get_user(user_id)
        if user and user.get('language') in LANGUAGES:
            return user['language']
        return DEFAULT_LANG

    def _t(self, user_id, key, *args):
        lang = self._get_lang(user_id)
        text = LANGUAGES[lang].get(key, LANGUAGES[DEFAULT_LANG].get(key, key))
        if args:
            try:
                return text.format(*args)
            except Exception:
                return text
        return text

    def _validate_wallet(self, address):
        try:
            if len(address) != 34 or not address.startswith('T'):
                return False
            valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
            if not all(c in valid_chars for c in address):
                return False
            base58.b58decode(address)
            return True
        except Exception:
            return False

    def _validate_tx_hash(self, tx_hash):
        return len(tx_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in tx_hash)

    async def _send_all_course(self, user_id):
        sent = 0
        for c in course_manager.get_all_content():
            if not course_manager.has_user_received(user_id, c['id']):
                if await course_manager.send_content_to_user(self.application.bot, user_id, c):
                    course_manager.mark_as_sent(user_id, c['id'])
                    sent += 1
                    await asyncio.sleep(0.15)
        return sent

    async def _broadcast_to_all(self, text):
        sent, failed = 0, 0
        for u in user_manager.get_all_users():
            try:
                await self.application.bot.send_message(u['user_id'], text, parse_mode=ParseMode.MARKDOWN)
                sent += 1
                if sent % 50 == 0:
                    await asyncio.sleep(0.3)
            except Exception:
                failed += 1
        return sent, failed

    def _main_menu_keyboard(self, user_id):
        keyboard = [
            [InlineKeyboardButton(self._t(user_id, 'education'), callback_data="education")],
            [InlineKeyboardButton(self._t(user_id, 'guide'), callback_data="guide"),
             InlineKeyboardButton(self._t(user_id, 'language_btn'), callback_data="language_menu")],
        ]
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ Admin / پنل مدیریت", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)

    async def _show_main_menu(self, send_func, user_id):
        await send_func(self._t(user_id, 'main_menu'), reply_markup=self._main_menu_keyboard(user_id), parse_mode=ParseMode.MARKDOWN)

    # ---------------- /start & language ----------------
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        is_new = user_manager.register_user(user.id, user.username, user.first_name, user.last_name)
        db_user = user_manager.get_user(user.id)

        if is_new or not db_user or not db_user.get('language'):
            keyboard = [[
                InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
                InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
            ]]
            await update.message.reply_text(
                "🌐 Please choose your language:\n🌐 لطفاً زبان خود را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        await update.message.reply_text(
            self._t(user.id, 'welcome'), reply_markup=self._main_menu_keyboard(user.id), parse_mode=ParseMode.MARKDOWN
        )

    async def language_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        keyboard = [[
            InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
        ]]
        await query.edit_message_text(
            "🌐 Please choose your language:\n🌐 لطفاً زبان خود را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def lang_select_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = query.data.split('_', 1)[1]
        if lang not in LANGUAGES:
            lang = DEFAULT_LANG
        user_manager.update_user(user_id, language=lang)
        await query.edit_message_text(
            self._t(user_id, 'welcome'), reply_markup=self._main_menu_keyboard(user_id), parse_mode=ParseMode.MARKDOWN
        )

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await self._show_main_menu(query.edit_message_text, query.from_user.id)

    # ---------------- Trading course ----------------
    async def education_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if user_manager.has_active_subscription(user):
            sent = await self._send_all_course(user_id)
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
            text = self._t(user_id, 'education_active', user['subscription_end'])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            return

        keyboard = [
            [InlineKeyboardButton(self._t(user_id, 'education_buy'), callback_data="education_buy")],
            [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]
        ]
        text = self._t(user_id, 'education_title', PAYMENT_AMOUNT, SUBSCRIPTION_DAYS)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def education_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        context.user_data['waiting_for_wallet'] = True
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'cancel'), callback_data="education")]]
        await query.edit_message_text(self._t(user_id, 'enter_wallet'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def education_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if not user or not user.get('wallet_address'):
            await query.edit_message_text(self._t(user_id, 'enter_wallet'), parse_mode=ParseMode.MARKDOWN)
            return

        await query.edit_message_text(self._t(user_id, 'verifying'), parse_mode=ParseMode.MARKDOWN)
        ok, tx_id, msg_code = await payment_verifier.verify_transaction(user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT)

        if ok:
            await self._activate_subscription(user_id, user['wallet_address'], tx_id)
            sent = await self._send_all_course(user_id)
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._t(user_id, 'verify_success', tx_id, sent),
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
            )
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(admin_id, self._t(admin_id, 'payment_confirmed_admin_note', user_id, PAYMENT_AMOUNT))
                except Exception:
                    pass
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            keyboard = [
                [InlineKeyboardButton(self._t(user_id, 'retry'), callback_data="education_confirm")],
                [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="education")]
            ]
            reason = "Transaction not found on-chain yet" if self._get_lang(user_id) == 'en' else "تراکنش هنوز روی بلاکچین پیدا نشد"
            await query.edit_message_text(self._t(user_id, 'verify_failed', reason), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def _activate_subscription(self, user_id, from_address, tx_id):
        end_date = (datetime.now() + timedelta(days=SUBSCRIPTION_DAYS)).strftime('%Y-%m-%d')
        user_manager.update_user(user_id, has_subscription=1, subscription_end=end_date)
        db.execute(user_id,
            "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
            (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
        )

    # ---------------- Guide ----------------
    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
        await query.edit_message_text(self._t(user_id, 'guide_text'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ---------------- Admin panel ----------------
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            await query.edit_message_text(self._t(user_id, 'admin_only'))
            return

        user_count = cache.get("total_users")
        if user_count is None:
            user_count = len(db.execute_global("SELECT user_id FROM users"))
            cache.set("total_users", user_count, ttl=300)

        pending = cache.get("pending_count")
        if pending is None:
            pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
            cache.set("pending_count", pending, ttl=60)

        keyboard = [
            [InlineKeyboardButton(self._t(user_id, 'admin_broadcast_btn'), callback_data="admin_broadcast")],
            [InlineKeyboardButton(self._t(user_id, 'admin_manual_verify_btn', pending), callback_data="admin_manual_verify")],
            [InlineKeyboardButton(self._t(user_id, 'admin_send_course_btn'), callback_data="admin_send_course"),
             InlineKeyboardButton(self._t(user_id, 'admin_add_content_btn'), callback_data="admin_add_content")],
            [InlineKeyboardButton(self._t(user_id, 'admin_add_api_btn'), callback_data="admin_add_api"),
             InlineKeyboardButton(self._t(user_id, 'admin_stats_btn'), callback_data="admin_stats")],
            [InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="main_menu")]
        ]
        text = self._t(user_id, 'admin_panel_title', f"{user_count:,}", pending, course_manager.get_content_count(), len(payment_verifier.apis))
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'broadcast'
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_cancel_btn'), callback_data="admin_panel")]]
        await query.edit_message_text(self._t(user_id, 'admin_broadcast_prompt'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        pending = db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC LIMIT 5")
        if not pending:
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")]]
            await query.edit_message_text(self._t(user_id, 'admin_no_pending'), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        text = self._t(user_id, 'admin_pending_header')
        keyboard = []
        for p in pending:
            text += f"👤 {p['user_id']}\n💰 ${p['amount']}\n📤 {p['from_address']}\n🔗 `{p['tx_hash']}`\n\n"
            keyboard.append([
                InlineKeyboardButton(self._t(user_id, 'admin_approve', p['id']), callback_data=f"admin_verify_approve_{p['id']}"),
                InlineKeyboardButton(self._t(user_id, 'admin_reject', p['id']), callback_data=f"admin_verify_reject_{p['id']}")
            ])
        keyboard.append([InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_send_course_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'send_course'
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_cancel_btn'), callback_data="admin_panel")]]
        await query.edit_message_text(self._t(user_id, 'admin_send_course_prompt'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_add_content_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_content'
        context.user_data['content_step'] = 1
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_cancel_btn'), callback_data="admin_panel")]]
        await query.edit_message_text(self._t(user_id, 'admin_add_content_step1'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_api'
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_cancel_btn'), callback_data="admin_panel")]]
        await query.edit_message_text(self._t(user_id, 'admin_add_api_prompt'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        user_count = len(db.execute_global("SELECT user_id FROM users"))
        active = len(db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"))
        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        cache_stats = cache.get_stats()
        keyboard = [
            [InlineKeyboardButton(self._t(user_id, 'admin_refresh'), callback_data="admin_stats")],
            [InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")]
        ]
        text = self._t(user_id, 'admin_stats_title', f"{user_count:,}", f"{active:,}", course_manager.get_content_count(),
                        pending, len(payment_verifier.apis), cache_stats['size'], cache_stats['hit_rate'])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_verify_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            return
        pending_id = int(query.data.split('_')[-1])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text(self._t(admin_id, 'admin_not_found'))
            return
        await self._activate_subscription(p['user_id'], p['from_address'], p['tx_hash'])
        db.execute(0, "UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")
        try:
            await self._send_all_course(p['user_id'])
            await self.application.bot.send_message(p['user_id'], self._t(p['user_id'], 'admin_approved_user_msg'), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        await query.edit_message_text(self._t(admin_id, 'admin_approved_note', p['user_id']), parse_mode=ParseMode.MARKDOWN)

    async def admin_verify_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            return
        pending_id = int(query.data.split('_')[-1])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text(self._t(admin_id, 'admin_not_found'))
            return
        db.execute(0, "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")
        try:
            await self.application.bot.send_message(p['user_id'], self._t(p['user_id'], 'admin_rejected_user_msg'), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        await query.edit_message_text(self._t(admin_id, 'admin_rejected_note', p['user_id']), parse_mode=ParseMode.MARKDOWN)

    # ---------------- Text messages ----------------
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        user_manager.register_user(user_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)
        admin_action = context.user_data.get('admin_action')

        if admin_action == 'broadcast':
            await update.message.reply_text(self._t(user_id, 'admin_broadcast_sending'))
            sent, failed = await self._broadcast_to_all(text)
            context.user_data['admin_action'] = None
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")]]
            await update.message.reply_text(self._t(user_id, 'admin_broadcast_sent', f"{sent:,}", f"{failed:,}"), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if admin_action == 'send_course':
            if text.strip().upper() == 'ALL':
                users = user_manager.get_all_users()
                await update.message.reply_text(self._t(user_id, 'admin_send_course_sending_all', len(users)))
                sent = 0
                for u in users:
                    if await self._send_all_course(u['user_id']) > 0:
                        sent += 1
                    await asyncio.sleep(0.15)
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")]]
                await update.message.reply_text(self._t(user_id, 'admin_send_course_done_all', sent), reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                try:
                    target_id = int(text.strip())
                    count = await self._send_all_course(target_id)
                    context.user_data['admin_action'] = None
                    keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")]]
                    await update.message.reply_text(self._t(user_id, 'admin_send_course_done_one', count, target_id), reply_markup=InlineKeyboardMarkup(keyboard))
                except ValueError:
                    await update.message.reply_text(self._t(user_id, 'admin_invalid_id'))
            return

        if admin_action == 'add_content':
            step = context.user_data.get('content_step', 1)
            if step == 1:
                context.user_data['content_title'] = text
                context.user_data['content_step'] = 2
                await update.message.reply_text(self._t(user_id, 'admin_add_content_step2'))
            elif step == 2:
                context.user_data['content_text'] = text
                context.user_data['content_step'] = 3
                await update.message.reply_text(self._t(user_id, 'admin_add_content_step3'))
            elif step == 3 and text.strip().lower() == '/skip':
                title = context.user_data.get('content_title', 'Untitled')
                content = context.user_data.get('content_text', '')
                cid = course_manager.add_content('text', title, content)
                context.user_data['admin_action'] = None
                context.user_data['content_step'] = None
                keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")]]
                await update.message.reply_text(self._t(user_id, 'admin_content_added', cid), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if admin_action == 'add_api':
            api_key = text.strip()
            if payment_verifier.add_api(api_key):
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")]]
                await update.message.reply_text(self._t(user_id, 'admin_api_added', len(payment_verifier.apis)), reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(self._t(user_id, 'admin_api_duplicate'))
            return

        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            if not self._validate_tx_hash(tx_hash):
                await update.message.reply_text(self._t(user_id, 'tx_hash_invalid'), parse_mode=ParseMode.MARKDOWN)
                return
            from_address = context.user_data.get('tx_from_address')
            db.execute(0,
                "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, tx_hash, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash)
            )
            context.user_data['waiting_for_tx_hash'] = False
            context.user_data['tx_from_address'] = None
            cache.delete("pending_count")
            await update.message.reply_text(self._t(user_id, 'tx_hash_received'), parse_mode=ParseMode.MARKDOWN)

            pid = db.execute(0, "SELECT last_insert_rowid() as id").fetchone()['id']
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [[
                        InlineKeyboardButton("✅", callback_data=f"admin_verify_approve_{pid}"),
                        InlineKeyboardButton("❌", callback_data=f"admin_verify_reject_{pid}")
                    ]]
                    await self.application.bot.send_message(
                        admin_id,
                        self._t(admin_id, 'admin_new_manual_request', user_id, PAYMENT_AMOUNT, from_address, tx_hash),
                        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
                    )
                except Exception:
                    pass
            return

        if context.user_data.get('waiting_for_wallet'):
            wallet = text.strip()
            if not self._validate_wallet(wallet):
                await update.message.reply_text(self._t(user_id, 'invalid_wallet'), parse_mode=ParseMode.MARKDOWN)
                return
            user_manager.update_user(user_id, wallet_address=wallet)
            context.user_data['waiting_for_wallet'] = False
            keyboard = [
                [InlineKeyboardButton(self._t(user_id, 'confirm_payment'), callback_data="education_confirm")],
                [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="education")]
            ]
            await update.message.reply_text(
                self._t(user_id, 'after_wallet', PAYMENT_AMOUNT, DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
            )
            return

        keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
        await update.message.reply_text(self._t(user_id, 'invalid_command'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ---------------- Media (admin content upload only) ----------------
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'photo')

    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'video')

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'document')

    async def _handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS or context.user_data.get('admin_action') != 'add_content':
            return
        if context.user_data.get('content_step') != 3:
            return

        title = context.user_data.get('content_title', 'Untitled')
        content = context.user_data.get('content_text', '')
        file_id = file_name = file_size = None

        if media_type == 'photo':
            f = update.message.photo[-1]
            file_id, file_name, file_size = f.file_id, f"{title}.jpg", f.file_size
        elif media_type == 'video':
            f = update.message.video
            file_id, file_name, file_size = f.file_id, f.file_name or f"{title}.mp4", f.file_size
        elif media_type == 'document':
            f = update.message.document
            file_id, file_name, file_size = f.file_id, f.file_name or f"{title}.pdf", f.file_size

        if file_id:
            cid = course_manager.add_content(media_type, title, content, file_id, file_name, file_size)
            context.user_data['admin_action'] = None
            context.user_data['content_step'] = None
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'admin_back_btn'), callback_data="admin_panel")]]
            await update.message.reply_text(self._t(user_id, 'admin_content_added', cid), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ---------------- Errors ----------------
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.effective_user:
                await self.application.bot.send_message(update.effective_user.id, self._t(update.effective_user.id, 'error_message'), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass


# ============================================================
# Entry point
# ============================================================
async def main():
    bot = UTYOBot()
    logger.info("Starting bot...")
    logger.info(f"Admins: {ADMIN_IDS}")
    logger.info(f"TronGrid keys: {len(payment_verifier.apis)}")
    logger.info(f"DB shards: {DB_SHARDS}")

    await bot.application.initialize()
    await bot.application.start()
    await bot.application.updater.start_polling()
    logger.info("Bot is running.")

    while True:
        try:
            users = db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')")
            for u in users:
                await bot._send_all_course(u['user_id'])
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Auto-send error: {e}")
        await asyncio.sleep(3600)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
