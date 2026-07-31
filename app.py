# ============================================================
# ربات UTYOB - دوره آموزش ترید (اشتراکی)
# بدون قرعه‌کشی / بدون رفرال پولی
# تایید خودکار پرداخت روی بلاکچین (TronGrid) + امکان افزودن کلید API
# طراحی‌شده برای مقیاس ۵۰۰,۰۰۰+ کاربر (دیتابیس شارد‌شده + کش)
# ============================================================

import asyncio
import logging
import random
import sqlite3
import hashlib
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
# تنظیمات
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(i) for i in os.environ.get('ADMIN_IDS', '123456789').split(',')]

# کلیدهای TronGrid برای تایید خودکار تراکنش (از پنل مدیریت هم قابل افزودنه)
TRONGRID_APIS = [
    k.strip() for k in os.environ.get('TRONGRID_APIS', '').split(',') if k.strip()
] or ["YOUR_TRONGRID_API_KEY_HERE"]

DESTINATION_WALLET = os.environ.get('DESTINATION_WALLET', 'YOUR_WALLET_ADDRESS_HERE')
PAYMENT_AMOUNT = float(os.environ.get('PAYMENT_AMOUNT', '100'))
SUBSCRIPTION_DAYS = int(os.environ.get('SUBSCRIPTION_DAYS', '30'))
DB_SHARDS = int(os.environ.get('DB_SHARDS', '200'))   # برای ۵۰۰k+ کاربر
CACHE_TTL = 600  # ۱۰ دقیقه


# ============================================================
# دیتابیس با شاردینگ (مقیاس‌پذیر برای کاربران زیاد)
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
        # فقط برای مواردی که تایید خودکار روی چین شکست بخوره (مثلاً تاخیر شبکه)
        # کاربر هش تراکنش واقعی رو می‌فرسته و ادمین با چک زنجیره تایید می‌کنه
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
# کش ساده در حافظه (برای کاهش فشار روی دیتابیس در مقیاس بالا)
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
# متن‌ها (فارسی)
# ============================================================
TEXTS = {
    'welcome': "🎓 **به ربات آموزش ترید UTYOB خوش آمدید!**\n\nیکی از گزینه‌ها را انتخاب کنید:",
    'main_menu': "🎯 **منوی اصلی**",
    'education': "📚 دوره آموزش ترید",
    'guide': "📖 راهنما",
    'back': "🔙 بازگشت",
    'main_menu_btn': "🏠 منوی اصلی",
    'cancel': "❌ انصراف",
    'retry': "🔄 تلاش مجدد",

    'education_title': (
        "📚 **دوره آموزش ترید**\n\n"
        "ترید حرفه‌ای را از صفر تا صد یاد بگیرید.\n\n"
        f"💰 هزینه: {PAYMENT_AMOUNT}$ (USDT-TRC20)\n"
        f"📅 مدت دسترسی: {SUBSCRIPTION_DAYS} روز"
    ),
    'education_buy': "💳 خرید / تمدید دسترسی",
    'education_active': "✅ شما در حال حاضر دسترسی فعال دارید.\n📅 تا تاریخ: {}",
    'enter_wallet': "📤 **آدرس کیف‌پول TRC20 خودتان را وارد کنید** (همان آدرسی که پرداخت را از آن انجام می‌دهید):",
    'invalid_wallet': "❌ آدرس کیف‌پول نامعتبر است.\nمثال صحیح: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
    'after_wallet': (
        "✅ آدرس ذخیره شد.\n\n"
        "💰 لطفاً مبلغ {}$ (USDT-TRC20) را به آدرس زیر واریز کنید:\n`{}`\n\n"
        "⚠️ پس از واریز، دکمه «✅ پرداخت را انجام دادم» را بزنید."
    ),
    'confirm_payment': "✅ پرداخت را انجام دادم",
    'verifying': "⏳ در حال بررسی تراکنش روی بلاکچین... چند لحظه صبر کنید.",
    'verify_success': "✅ **پرداخت با موفقیت تایید شد!**\n\n🔗 هش تراکنش: `{}`\n\n📚 {} محتوا برای شما ارسال شد.",
    'verify_failed': (
        "❌ تراکنش به‌صورت خودکار پیدا نشد.\n\nدلیل: {}\n\n"
        "اگر مطمئنید پرداخت را انجام دادید، هش تراکنش (TX Hash) را همینجا ارسال کنید تا توسط مدیریت بررسی شود:"
    ),
    'tx_hash_invalid': "❌ هش تراکنش نامعتبر است. هش باید ۶۴ کاراکتر باشد.",
    'tx_hash_received': "✅ هش تراکنش دریافت شد.\n⏳ در حال بررسی توسط مدیریت... به محض تایید به شما اطلاع داده می‌شود.",

    'guide_text': (
        "📖 **راهنما**\n\n"
        "۱️⃣ روی «دوره آموزش ترید» بزنید\n"
        "۲️⃣ آدرس کیف‌پول TRC20 خود را وارد کنید\n"
        "۳️⃣ مبلغ را واریز کنید و «پرداخت را انجام دادم» را بزنید\n"
        "۴️⃣ تراکنش شما خودکار روی بلاکچین بررسی و دسترسی فعال می‌شود\n\n"
        "📞 پشتیبانی: با مدیریت تماس بگیرید."
    ),

    'invalid_command': "⚠️ دستور نامعتبر است. لطفاً از دکمه‌ها استفاده کنید.",
    'error_message': "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
}


# ============================================================
# تایید خودکار پرداخت روی بلاکچین با TronGrid
# (چند کلید API برای پشتیبانی و توزیع بار؛ از پنل هم قابل افزودن است)
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = list(dict.fromkeys(TRONGRID_APIS))  # حذف موارد تکراری با حفظ ترتیب
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
        return False, None, "تراکنش به‌صورت خودکار پیدا نشد یا هنوز روی بلاکچین تایید نشده است"

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
# مدیریت کاربران
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
# مدیریت محتوای دوره
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
            logger.error(f"خطا در ارسال محتوا به {user_id}: {e}")
            return False


course_manager = CourseManager()


# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()

    def _setup_handlers(self):
        app = self.application
        app.add_handler(CommandHandler("start", self.start_command))

        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.education_callback, pattern="^education$"))
        app.add_handler(CallbackQueryHandler(self.education_buy_callback, pattern="^education_buy$"))
        app.add_handler(CallbackQueryHandler(self.education_confirm_callback, pattern="^education_confirm$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))

        # پنل مدیریت
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

    # ---------------- کمکی ----------------
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
            [InlineKeyboardButton(TEXTS['education'], callback_data="education")],
            [InlineKeyboardButton(TEXTS['guide'], callback_data="guide")],
        ]
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)

    # ---------------- دستور /start ----------------
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_manager.register_user(user.id, user.username, user.first_name, user.last_name)
        await update.message.reply_text(
            TEXTS['welcome'], reply_markup=self._main_menu_keyboard(user.id), parse_mode=ParseMode.MARKDOWN
        )

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            TEXTS['main_menu'], reply_markup=self._main_menu_keyboard(query.from_user.id), parse_mode=ParseMode.MARKDOWN
        )

    # ---------------- دوره آموزشی ----------------
    async def education_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if user_manager.has_active_subscription(user):
            sent = await self._send_all_course(user_id)
            keyboard = [[InlineKeyboardButton(TEXTS['main_menu_btn'], callback_data="main_menu")]]
            text = TEXTS['education_active'].format(user['subscription_end'])
            if sent:
                text += f"\n\n📚 {sent} محتوای جدید ارسال شد."
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            return

        keyboard = [
            [InlineKeyboardButton(TEXTS['education_buy'], callback_data="education_buy")],
            [InlineKeyboardButton(TEXTS['back'], callback_data="main_menu")]
        ]
        await query.edit_message_text(TEXTS['education_title'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def education_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data['waiting_for_wallet'] = True
        keyboard = [[InlineKeyboardButton(TEXTS['cancel'], callback_data="education")]]
        await query.edit_message_text(TEXTS['enter_wallet'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def education_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if not user or not user.get('wallet_address'):
            await query.edit_message_text(TEXTS['enter_wallet'], parse_mode=ParseMode.MARKDOWN)
            return

        await query.edit_message_text(TEXTS['verifying'], parse_mode=ParseMode.MARKDOWN)
        ok, tx_id, msg = await payment_verifier.verify_transaction(user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT)

        if ok:
            await self._activate_subscription(user_id, user['wallet_address'], tx_id)
            sent = await self._send_all_course(user_id)
            keyboard = [[InlineKeyboardButton(TEXTS['main_menu_btn'], callback_data="main_menu")]]
            await query.edit_message_text(
                TEXTS['verify_success'].format(tx_id, sent),
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
            )
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(admin_id, f"✅ خرید جدید تایید شد (خودکار)\n👤 کاربر: {user_id}\n💰 مبلغ: {PAYMENT_AMOUNT}$")
                except Exception:
                    pass
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            keyboard = [
                [InlineKeyboardButton(TEXTS['retry'], callback_data="education_confirm")],
                [InlineKeyboardButton(TEXTS['back'], callback_data="education")]
            ]
            await query.edit_message_text(TEXTS['verify_failed'].format(msg), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def _activate_subscription(self, user_id, from_address, tx_id):
        end_date = (datetime.now() + timedelta(days=SUBSCRIPTION_DAYS)).strftime('%Y-%m-%d')
        user_manager.update_user(user_id, has_subscription=1, subscription_end=end_date)
        db.execute(user_id,
            "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
            (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
        )

    # ---------------- راهنما ----------------
    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton(TEXTS['back'], callback_data="main_menu")]]
        await query.edit_message_text(TEXTS['guide_text'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ---------------- پنل مدیریت ----------------
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
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
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton(f"✅ تایید دستی ({pending})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📚 ارسال محتوای دوره", callback_data="admin_send_course")],
            [InlineKeyboardButton("📝 افزودن محتوای جدید", callback_data="admin_add_content")],
            [InlineKeyboardButton("🔑 افزودن کلید API", callback_data="admin_add_api")],
            [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"⚙️ **پنل مدیریت**\n\n"
            f"👥 کاربران: {user_count:,}\n"
            f"⏳ در انتظار تایید دستی: {pending}\n"
            f"📚 محتوا: {course_manager.get_content_count()}\n"
            f"🔑 کلیدهای API: {len(payment_verifier.apis)}",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )

    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'broadcast'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "📢 **ارسال پیام همگانی**\n\nمتن پیام را ارسال کنید (به همه کاربران فرستاده می‌شود):",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )

    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        pending = db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC LIMIT 5")
        if not pending:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await query.edit_message_text("✅ موردی در انتظار تایید نیست!", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        text = "✅ **تایید دستی تراکنش‌ها**\n(فقط مواردی که تایید خودکار روی چین برایشان ممکن نشد)\n\n"
        keyboard = []
        for p in pending:
            text += f"👤 کاربر: {p['user_id']}\n💰 مبلغ: ${p['amount']}\n📤 از: `{p['from_address']}`\n🔗 هش: `{p['tx_hash']}`\n\n"
            keyboard.append([
                InlineKeyboardButton(f"✅ تایید #{p['id']}", callback_data=f"admin_verify_approve_{p['id']}"),
                InlineKeyboardButton(f"❌ رد #{p['id']}", callback_data=f"admin_verify_reject_{p['id']}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_send_course_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'send_course'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "📚 **ارسال محتوای دوره**\n\nآیدی عددی کاربر را وارد کنید، یا برای ارسال به همه: `ALL`",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )

    async def admin_add_content_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_content'
        context.user_data['content_step'] = 1
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text("📝 **افزودن محتوای جدید**\n\nمرحله ۱/۳: عنوان را وارد کنید:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_api'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "🔑 **افزودن کلید TronGrid API**\n\nکلید API را ارسال کنید.\n"
            "⚠️ هرچه کلید بیشتر باشد، سرعت و پایداری تایید خودکار بالاتر می‌رود.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )

    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        user_count = len(db.execute_global("SELECT user_id FROM users"))
        active = len(db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"))
        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        cache_stats = cache.get_stats()
        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        await query.edit_message_text(
            f"📊 **آمار سیستم**\n\n"
            f"👥 کاربران کل: {user_count:,}\n"
            f"✅ اشتراک فعال: {active:,}\n"
            f"📚 محتوای دوره: {course_manager.get_content_count()}\n"
            f"⏳ در انتظار تایید دستی: {pending}\n"
            f"🔑 کلیدهای API: {len(payment_verifier.apis)}\n\n"
            f"⚡ کش: {cache_stats['size']} آیتم | نرخ برخورد {cache_stats['hit_rate']:.1f}%",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
        )

    async def admin_verify_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        pending_id = int(query.data.split('_')[-1])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text("❌ درخواست یافت نشد یا قبلاً بررسی شده!")
            return
        await self._activate_subscription(p['user_id'], p['from_address'], p['tx_hash'])
        db.execute(0, "UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")
        try:
            await self._send_all_course(p['user_id'])
            await self.application.bot.send_message(p['user_id'], "✅ پرداخت شما تایید شد و دسترسی به دوره فعال شد.", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        await query.edit_message_text(f"✅ تراکنش تایید شد!\n👤 کاربر: {p['user_id']}", parse_mode=ParseMode.MARKDOWN)

    async def admin_verify_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        pending_id = int(query.data.split('_')[-1])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text("❌ درخواست یافت نشد!")
            return
        db.execute(0, "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")
        try:
            await self.application.bot.send_message(p['user_id'], "❌ متاسفانه تراکنش شما تایید نشد. با پشتیبانی تماس بگیرید.", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        await query.edit_message_text(f"❌ تراکنش رد شد!\n👤 کاربر: {p['user_id']}", parse_mode=ParseMode.MARKDOWN)

    # ---------------- مدیریت پیام‌های متنی ----------------
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        user_manager.register_user(user_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)
        admin_action = context.user_data.get('admin_action')

        if admin_action == 'broadcast':
            await update.message.reply_text("⏳ در حال ارسال به همه کاربران...")
            sent, failed = await self._broadcast_to_all(text)
            context.user_data['admin_action'] = None
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await update.message.reply_text(f"✅ ارسال همگانی کامل شد!\n📤 موفق: {sent:,}\n❌ ناموفق: {failed:,}", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if admin_action == 'send_course':
            if text.strip().upper() == 'ALL':
                users = user_manager.get_all_users()
                await update.message.reply_text(f"⏳ ارسال به {len(users)} کاربر...")
                sent = 0
                for u in users:
                    if await self._send_all_course(u['user_id']) > 0:
                        sent += 1
                    await asyncio.sleep(0.15)
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(f"✅ محتوا به {sent} کاربر ارسال شد!", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                try:
                    target_id = int(text.strip())
                    count = await self._send_all_course(target_id)
                    context.user_data['admin_action'] = None
                    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                    await update.message.reply_text(f"✅ {count} محتوا به کاربر {target_id} ارسال شد!", reply_markup=InlineKeyboardMarkup(keyboard))
                except ValueError:
                    await update.message.reply_text("❌ آیدی نامعتبر!")
            return

        if admin_action == 'add_content':
            step = context.user_data.get('content_step', 1)
            if step == 1:
                context.user_data['content_title'] = text
                context.user_data['content_step'] = 2
                await update.message.reply_text("📝 مرحله ۲/۳: توضیحات متن را وارد کنید:")
            elif step == 2:
                context.user_data['content_text'] = text
                context.user_data['content_step'] = 3
                await update.message.reply_text("📝 مرحله ۳/۳: فایل را ارسال کنید (عکس/ویدیو/سند) یا برای فقط متن بنویسید: /skip")
            elif step == 3 and text.strip().lower() == '/skip':
                title = context.user_data.get('content_title', 'بدون عنوان')
                content = context.user_data.get('content_text', '')
                cid = course_manager.add_content('text', title, content)
                context.user_data['admin_action'] = None
                context.user_data['content_step'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(f"✅ محتوا اضافه شد! ID: {cid}", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if admin_action == 'add_api':
            api_key = text.strip()
            if payment_verifier.add_api(api_key):
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(f"✅ کلید API اضافه شد!\n🔑 تعداد کلیدها: {len(payment_verifier.apis)}", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text("❌ این کلید قبلاً اضافه شده است!")
            return

        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            if not self._validate_tx_hash(tx_hash):
                await update.message.reply_text(TEXTS['tx_hash_invalid'], parse_mode=ParseMode.MARKDOWN)
                return
            from_address = context.user_data.get('tx_from_address')
            db.execute(0,
                "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, tx_hash, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash)
            )
            context.user_data['waiting_for_tx_hash'] = False
            context.user_data['tx_from_address'] = None
            cache.delete("pending_count")
            await update.message.reply_text(TEXTS['tx_hash_received'], parse_mode=ParseMode.MARKDOWN)

            pid = db.execute(0, "SELECT last_insert_rowid() as id").fetchone()['id']
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [[
                        InlineKeyboardButton("✅ تایید", callback_data=f"admin_verify_approve_{pid}"),
                        InlineKeyboardButton("❌ رد", callback_data=f"admin_verify_reject_{pid}")
                    ]]
                    await self.application.bot.send_message(
                        admin_id,
                        f"✅ درخواست تایید دستی (تایید خودکار ناموفق بود)\n\n👤 کاربر: {user_id}\n💰 مبلغ: ${PAYMENT_AMOUNT}\n📤 از: {from_address}\n🔗 هش: `{tx_hash}`",
                        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
                    )
                except Exception:
                    pass
            return

        if context.user_data.get('waiting_for_wallet'):
            wallet = text.strip()
            if not self._validate_wallet(wallet):
                await update.message.reply_text(TEXTS['invalid_wallet'], parse_mode=ParseMode.MARKDOWN)
                return
            user_manager.update_user(user_id, wallet_address=wallet)
            context.user_data['waiting_for_wallet'] = False
            keyboard = [
                [InlineKeyboardButton(TEXTS['confirm_payment'], callback_data="education_confirm")],
                [InlineKeyboardButton(TEXTS['back'], callback_data="education")]
            ]
            await update.message.reply_text(
                TEXTS['after_wallet'].format(PAYMENT_AMOUNT, DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN
            )
            return

        keyboard = [[InlineKeyboardButton(TEXTS['main_menu_btn'], callback_data="main_menu")]]
        await update.message.reply_text(TEXTS['invalid_command'], reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ---------------- مدیریت فایل‌ها (فقط برای افزودن محتوای دوره توسط ادمین) ----------------
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

        title = context.user_data.get('content_title', 'بدون عنوان')
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
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await update.message.reply_text(f"✅ محتوا اضافه شد!\n📚 عنوان: {title}\n🆔 ID: {cid}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ---------------- خطاها ----------------
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.effective_user:
                await self.application.bot.send_message(update.effective_user.id, TEXTS['error_message'], parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass


# ============================================================
# اجرا
# ============================================================
async def main():
    bot = UTYOBot()
    logger.info("🚀 ربات در حال اجراست...")
    logger.info(f"👥 مدیران: {ADMIN_IDS}")
    logger.info(f"🔑 کلیدهای TronGrid: {len(payment_verifier.apis)}")
    logger.info(f"🗄️ شاردهای دیتابیس: {DB_SHARDS}")

    await bot.application.initialize()
    await bot.application.start()
    await bot.application.updater.start_polling()
    logger.info("✅ ربات با موفقیت اجرا شد!")

    # ارسال خودکار محتوای جدید به کاربران دارای اشتراک فعال (هر ساعت)
    while True:
        try:
            users = db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')")
            for u in users:
                await bot._send_all_course(u['user_id'])
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"خطای ارسال خودکار: {e}")
        await asyncio.sleep(3600)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 ربات متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطای غیرمنتظره: {e}")
