# ============================================================
# ربات کامل UTYOB - قرعه‌کشی + آموزش ترید
# نسخه نهایی - کاملاً فارسی - پنل مدیریت کامل
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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# تنظیمات اولیه
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '123456789').split(',')]

TRONGRID_APIS = ["7ae83b63-fdf3-47e4-ac69-56f960a34f5b"]
DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PAYMENT_AMOUNT = 100
DB_SHARDS = 100

# ============================================================
# دیتابیس
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
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self.connections[i] = conn
            self.locks[i] = threading.Lock()
            self._create_tables(conn)

    def _create_tables(self, conn):
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'fa',
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_hash TEXT,
                tx_type TEXT DEFAULT 'lottery',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_sent (
                user_id INTEGER,
                content_id INTEGER,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, content_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_verifications(status)')
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
# متن‌های فارسی (همه چیز فارسی)
# ============================================================
TEXTS = {
    'welcome': "🎮 **به ربات UTYOB خوش آمدید!**\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
    'main_menu': "🎯 **منوی اصلی**\n\nیکی از گزینه‌ها را انتخاب کنید:",
    'lottery': "🎰 قرعه‌کشی",
    'education': "📚 آموزش ترید",
    'referral': "🔗 رفرال",
    'guide': "📖 راهنما",
    'admin_panel': "⚙️ پنل مدیریت",
    'back': "🔙 بازگشت",
    'main_menu_btn': "🏠 منوی اصلی",
    'lottery_title': "🎰 **قرعه‌کشی UTYOB**\n\n💰 هزینه شرکت: ۱۰۰ دلار\n🏆 جایزه: تا ۱۰,۰۰۰ دلار",
    'lottery_join': "🎯 شرکت در قرعه‌کشی",
    'lottery_enter_wallet': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
    'lottery_after_wallet': "✅ **آدرس کیف پول ذخیره شد!**\n\n💰 مبلغ ۱۰۰ دلار را به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ پس از واریز، دکمه **✅ پرداخت کردم** را بزنید.",
    'lottery_confirm': "✅ پرداخت کردم",
    'lottery_verifying': "⏳ در حال بررسی پرداخت شما... لطفاً صبر کنید.",
    'lottery_success': "✅ **پرداخت شما تایید شد!** 🎉\n\n🔗 هش تراکنش: `{}`\n\n🙏 موفق باشید!",
    'lottery_failed': "❌ **پرداخت تایید نشد!**\n\nدلیل: {}\n\n📤 لطفاً هش تراکنش خود را برای تایید دستی ارسال کنید:",
    'lottery_no_subscription': "❌ **اشتراک فعال ندارید!**\n\nبرای شرکت در قرعه‌کشی، ابتدا اشتراک تهیه کنید.",
    'education_title': "📚 **آموزش ترید و سیگنال**\n\nترید حرفه‌ای را از صفر تا صد یاد بگیر!",
    'education_buy': "💰 خرید دوره (۱۰۰ دلار)",
    'education_enter_wallet': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
    'education_after_wallet': "✅ **آدرس کیف پول ذخیره شد!**\n\n💰 مبلغ ۱۰۰ دلار را به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ پس از واریز، دکمه **✅ پرداخت کردم** را بزنید.",
    'education_confirm': "✅ پرداخت کردم",
    'education_verifying': "⏳ در حال بررسی پرداخت شما...",
    'education_success': "✅ **پرداخت تایید شد!** 🎉\n\n🔗 هش: `{}`\n\n📚 **دسترسی به دوره فعال شد!**\n\nتمام محتوای آموزشی برای شما ارسال شد.",
    'education_failed': "❌ **پرداخت تایید نشد!**\n\nدلیل: {}\n\n📤 لطفاً هش تراکنش خود را ارسال کنید:",
    'education_already': "✅ شما قبلاً این دوره را خریداری کرده‌اید!",
    'subscribe': "🔄 خرید اشتراک",
    'subscribe_title': "💳 **خرید اشتراک**\n\n💰 هزینه: ۱۰۰ دلار\n📅 اعتبار: ۳۰ روز",
    'subscribe_enter_wallet': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
    'subscribe_after_wallet': "✅ **آدرس کیف پول ذخیره شد!**\n\n💰 مبلغ ۱۰۰ دلار را به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ پس از واریز، دکمه **✅ پرداخت کردم** را بزنید.",
    'subscribe_confirm': "✅ پرداخت کردم",
    'subscribe_success': "✅ **اشتراک شما فعال شد!** 🎉\n\n📚 تمام محتوای آموزشی برای شما ارسال شد.",
    'subscribe_failed': "❌ **اشتراک فعال نشد!**\n\nدلیل: {}\n\n📤 هش تراکنش را ارسال کنید:",
    'subscribe_active': "✅ شما اشتراک فعال دارید!",
    'referral_text': "🔗 **سیستم رفرال**\n\n👤 شما: {}\n📊 تعداد دعوت‌ها: {}\n\n🔑 کد رفرال شما:\n`{}`\n\n🔗 لینک دعوت:\n{}\n\n💰 **پاداش:** ۵٪ از هر واریز",
    'referral_link': "https://t.me/UTYOB_Bot?start=ref_{}",
    'share': "📤 اشتراک‌گذاری",
    'guide_text': "📖 **راهنمای کامل**\n\n🎯 **مراحل:**\n1️⃣ اشتراک تهیه کنید (۱۰۰ دلار)\n2️⃣ در قرعه‌کشی شرکت کنید\n3️⃣ یا دوره آموزش ترید را بخرید\n4️⃣ برنده شوید و جایزه بگیرید!\n\n📞 پشتیبانی: با مدیریت تماس بگیرید.",
    'invalid_command': "⚠️ **دستور نامعتبر!**\n\nلطفاً از دکمه‌ها استفاده کنید.",
    'error_message': "⚠️ **خطا رخ داد!**\n\nلطفاً دوباره تلاش کنید.",
    'invalid_wallet': "❌ **آدرس کیف پول نامعتبر!**\n\nلطفاً یک آدرس معتبر TRC20 وارد کنید.\nمثال: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
    'tx_hash_invalid': "❌ **هش تراکنش نامعتبر!**\n\nلطفاً یک هش ۶۴ کاراکتری معتبر وارد کنید.",
    'tx_hash_received': "✅ **هش تراکنش دریافت شد!**\n\n⏳ در حال بررسی توسط مدیریت...\n📢 به محض تایید به شما اطلاع داده می‌شود.",
    'no_subscription': "❌ **اشتراک فعال ندارید!**",
    
    # پنل مدیریت (همه فارسی)
    'admin_panel_title': "⚙️ **پنل مدیریت**\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
    'admin_broadcast': "📢 ارسال پیام همگانی",
    'admin_start_lottery': "🎰 شروع قرعه‌کشی",
    'admin_manual_verify': "✅ تایید دستی تراکنش",
    'admin_send_course': "📚 ارسال محتوای دوره",
    'admin_add_content': "📝 افزودن محتوای جدید",
    'admin_add_api': "🔑 افزودن کلید API",
    'admin_stats': "📊 آمار و اطلاعات",
    'admin_verify_approve': "✅ تایید",
    'admin_verify_reject': "❌ رد",
    'admin_verify_approved': "✅ **تراکنش تایید شد!**\n\n👤 کاربر: {}\n💰 مبلغ: {}$\n🔗 هش: `{}`",
    'admin_verify_rejected': "❌ **تراکنش رد شد!**\n\n👤 کاربر: {}\n🔗 هش: `{}`",
    'user_verify_approved': "✅ **تراکنش شما تایید شد!** 🎉\n\nدسترسی شما فعال شد.",
    'user_verify_rejected': "❌ **تراکنش شما رد شد!**\n\nلطفاً دوباره تلاش کنید.",
    
    # دکمه‌های اضافی
    'cancel': "❌ انصراف",
    'retry': "🔄 تلاش مجدد",
    'support': "📞 پشتیبانی",
    'share_link': "📤 اشتراک‌گذاری",
    'withdraw_prize': "💰 برداشت جایزه",
    'next_lottery': "🎰 قرعه‌کشی بعدی",
    'no_winner': "❌ شما جایزه‌ای ندارید!",
    'already_paid': "✅ جایزه قبلاً پرداخت شده!",
    'enter_withdraw_wallet': "💰 آدرس کیف پول خود را وارد کنید:",
    'withdraw_success': "✅ برداشت با موفقیت ثبت شد!",
}

def get_text(user_id, key, *args):
    """دریافت متن فارسی"""
    text = TEXTS.get(key, key)
    if args:
        try:
            return text.format(*args)
        except:
            return text
    return text

# ============================================================
# تایید پرداخت با API
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self.session

    async def verify_transaction(self, from_address, to_address, amount, tx_id=None):
        session = await self.get_session()
        if tx_id:
            return await self._verify_by_txid(session, tx_id, from_address, to_address, amount)
        return await self._search_transactions(session, from_address, to_address, amount)

    async def _verify_by_txid(self, session, tx_id, from_address, to_address, amount):
        for api in self.apis:
            try:
                url = f"https://api.trongrid.io/v1/transactions/{tx_id}"
                headers = {"TRON-PRO-API-KEY": api}
                async with session.get(url, headers=headers) as r:
                    if r.status == 200:
                        data = await r.json()
                        if self._validate(data, from_address, to_address, amount):
                            return True, tx_id, "Verified"
            except:
                pass
        return False, None, "Transaction not found"

    async def _search_transactions(self, session, from_address, to_address, amount):
        for api in self.apis:
            try:
                url = f"https://api.trongrid.io/v1/accounts/{from_address}/transactions"
                params = {"limit": 50, "order_by": "block_timestamp,desc"}
                headers = {"TRON-PRO-API-KEY": api}
                async with session.get(url, headers=headers, params=params) as r:
                    if r.status == 200:
                        data = await r.json()
                        for tx in data.get('data', []):
                            if self._validate(tx, from_address, to_address, amount):
                                return True, tx.get('txID'), "Verified"
            except:
                pass
        return False, None, "No matching transaction"

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
            ref_code = hashlib.sha256(f"UTYOB_{user_id}_{time.time()}".encode()).hexdigest()[:10].upper()
            db.execute(user_id,
                "INSERT INTO users (user_id, username, first_name, last_name, referral_code, language) VALUES (?, ?, ?, ?, ?, 'fa')",
                (user_id, username, first_name, last_name, ref_code)
            )
            return True
        except:
            return False

    @staticmethod
    def get_user(user_id):
        try:
            cursor = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone()
        except:
            return None

    @staticmethod
    def update_user(user_id, **kwargs):
        try:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            db.execute(user_id, f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", values)
            return True
        except:
            return False

    @staticmethod
    def get_referral_count(user_id):
        try:
            results = db.execute_global("SELECT COUNT(*) as count FROM users WHERE referred_by = ?", (user_id,))
            total = 0
            for r in results:
                total += r['count']
            return total
        except:
            return 0

user_manager = UserManager()

# ============================================================
# سیستم قرعه‌کشی
# ============================================================
class LotterySystem:
    def __init__(self):
        self.is_running = False

    def start_lottery(self, winners_count, prize_per_winner):
        if self.is_running:
            return False, "قرعه‌کشی در حال اجراست!"
        eligible = [r['user_id'] for r in db.execute_global(
            "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
        )]
        if len(eligible) < winners_count:
            return False, "تعداد کاربران واجد شرایط کافی نیست!"
        winners = random.sample(eligible, winners_count)
        cursor = db.execute(0,
            "INSERT INTO lotteries (winners_count, prize_per_winner, total_prize, status, started_at) VALUES (?, ?, ?, 'running', CURRENT_TIMESTAMP)",
            (winners_count, prize_per_winner, winners_count * prize_per_winner)
        )
        lid = cursor.lastrowid
        for uid in winners:
            user = user_manager.get_user(uid)
            db.execute(uid,
                "INSERT INTO winners (lottery_id, user_id, prize_amount, wallet_address, paid_status) VALUES (?, ?, ?, ?, 0)",
                (lid, uid, prize_per_winner, user['wallet_address'] if user else None)
            )
        self.is_running = False
        return True, {'lottery_id': lid, 'winners': winners, 'prize_per_winner': prize_per_winner}

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
        return cursor.lastrowid

    @staticmethod
    def get_all_content():
        return db.execute_global("SELECT * FROM course_content ORDER BY created_at DESC")

    @staticmethod
    def get_content_count():
        results = db.execute_global("SELECT COUNT(*) as count FROM course_content")
        total = 0
        for r in results:
            total += r['count']
        return total

    @staticmethod
    def has_user_received(user_id, content_id):
        cursor = db.execute(user_id, "SELECT * FROM content_sent WHERE user_id = ? AND content_id = ?", (user_id, content_id))
        return cursor.fetchone() is not None

    @staticmethod
    def mark_as_sent(user_id, content_id):
        db.execute(user_id, "INSERT OR IGNORE INTO content_sent (user_id, content_id) VALUES (?, ?)", (user_id, content_id))

    @staticmethod
    async def send_content_to_user(bot, user_id, content):
        try:
            if content['content_type'] == 'text':
                await bot.send_message(user_id, f"📚 **{content['title']}**\n\n{content['content']}", parse_mode=ParseMode.MARKDOWN)
            elif content['content_type'] == 'photo':
                await bot.send_photo(user_id, content['file_id'], caption=f"📚 **{content['title']}**\n\n{content['content']}", parse_mode=ParseMode.MARKDOWN)
            elif content['content_type'] == 'video':
                await bot.send_video(user_id, content['file_id'], caption=f"📚 **{content['title']}**\n\n{content['content']}", parse_mode=ParseMode.MARKDOWN)
            elif content['content_type'] == 'document':
                await bot.send_document(user_id, content['file_id'], caption=f"📚 **{content['title']}**\n\n{content['content']}", parse_mode=ParseMode.MARKDOWN)
            return True
        except:
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
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.education_callback, pattern="^education$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.subscribe_callback, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.lottery_join_callback, pattern="^lottery_join$"))
        app.add_handler(CallbackQueryHandler(self.lottery_confirm_callback, pattern="^lottery_confirm$"))
        app.add_handler(CallbackQueryHandler(self.education_buy_callback, pattern="^education_buy$"))
        app.add_handler(CallbackQueryHandler(self.education_confirm_callback, pattern="^education_confirm$"))
        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_start_lottery_callback, pattern="^admin_start_lottery$"))
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

    # ============================================================
    # توابع کمکی
    # ============================================================
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

    async def _verify_payment(self, user_id, from_address, amount, tx_hash=None):
        return await payment_verifier.verify_transaction(from_address, DESTINATION_WALLET, amount, tx_hash)

    async def _send_all_course(self, user_id):
        contents = course_manager.get_all_content()
        sent = 0
        for c in contents:
            if not course_manager.has_user_received(user_id, c['id']):
                if await course_manager.send_content_to_user(self.application.bot, user_id, c):
                    course_manager.mark_as_sent(user_id, c['id'])
                    sent += 1
                    await asyncio.sleep(0.2)
        return sent

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

        keyboard = [
            [InlineKeyboardButton("🎰 قرعه‌کشی", callback_data="lottery")],
            [InlineKeyboardButton("📚 آموزش ترید", callback_data="education")],
            [InlineKeyboardButton("🔗 رفرال", callback_data="referral")],
            [InlineKeyboardButton("📖 راهنما", callback_data="guide")],
            [InlineKeyboardButton("🔄 خرید اشتراک", callback_data="subscribe")]
        ]
        if user.id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])

        await update.message.reply_text(
            TEXTS['welcome'],
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

        keyboard = [
            [InlineKeyboardButton("🎰 قرعه‌کشی", callback_data="lottery")],
            [InlineKeyboardButton("📚 آموزش ترید", callback_data="education")],
            [InlineKeyboardButton("🔗 رفرال", callback_data="referral")],
            [InlineKeyboardButton("📖 راهنما", callback_data="guide")],
            [InlineKeyboardButton("🔄 خرید اشتراک", callback_data="subscribe")]
        ]
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])

        await query.edit_message_text(
            TEXTS['main_menu'],
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
        user = user_manager.get_user(user_id)

        if not user or not user['has_subscription']:
            keyboard = [
                [InlineKeyboardButton("🔄 خرید اشتراک", callback_data="subscribe")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
            ]
            await query.edit_message_text(
                TEXTS['lottery_no_subscription'],
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        keyboard = [
            [InlineKeyboardButton("🎯 شرکت در قرعه‌کشی", callback_data="lottery_join")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            TEXTS['lottery_title'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def lottery_join_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        context.user_data['action'] = 'lottery'
        context.user_data['waiting_for_wallet'] = True

        keyboard = [[InlineKeyboardButton("❌ انصراف", callback_data="lottery")]]
        await query.edit_message_text(
            TEXTS['lottery_enter_wallet'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def lottery_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if not user or not user['wallet_address']:
            await query.edit_message_text(TEXTS['lottery_enter_wallet'], parse_mode=ParseMode.MARKDOWN)
            return

        await query.edit_message_text(TEXTS['lottery_verifying'], parse_mode=ParseMode.MARKDOWN)

        success, tx_id, msg = await self._verify_payment(user_id, user['wallet_address'], PAYMENT_AMOUNT)

        if success:
            db.execute(user_id,
                "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) VALUES (?, ?, ?, ?, ?, 'lottery', 'verified', CURRENT_TIMESTAMP)",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
            )
            user_manager.update_user(user_id, total_participations=(user['total_participations'] or 0) + 1)

            keyboard = [
                [InlineKeyboardButton("🎰 قرعه‌کشی بعدی", callback_data="lottery")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
            ]
            await query.edit_message_text(
                TEXTS['lottery_success'].format(tx_id),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            context.user_data['action'] = 'lottery'
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            context.user_data['tx_type'] = 'lottery'

            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="lottery")]]
            await query.edit_message_text(
                TEXTS['lottery_failed'].format(msg),
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

        # بررسی خرید قبلی
        cursor = db.execute(user_id,
            "SELECT * FROM transactions WHERE user_id = ? AND tx_type = 'education' AND status = 'verified'",
            (user_id,)
        )
        if cursor.fetchone():
            keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
            await query.edit_message_text(
                TEXTS['education_already'],
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        keyboard = [
            [InlineKeyboardButton("💰 خرید دوره (۱۰۰ دلار)", callback_data="education_buy")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            TEXTS['education_title'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def education_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        context.user_data['action'] = 'education'
        context.user_data['waiting_for_wallet'] = True

        keyboard = [[InlineKeyboardButton("❌ انصراف", callback_data="education")]]
        await query.edit_message_text(
            TEXTS['education_enter_wallet'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def education_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if not user or not user['wallet_address']:
            await query.edit_message_text(TEXTS['education_enter_wallet'], parse_mode=ParseMode.MARKDOWN)
            return

        await query.edit_message_text(TEXTS['education_verifying'], parse_mode=ParseMode.MARKDOWN)

        success, tx_id, msg = await self._verify_payment(user_id, user['wallet_address'], PAYMENT_AMOUNT)

        if success:
            db.execute(user_id,
                "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) VALUES (?, ?, ?, ?, ?, 'education', 'verified', CURRENT_TIMESTAMP)",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
            )

            sent = await self._send_all_course(user_id)

            keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
            await query.edit_message_text(
                TEXTS['education_success'].format(tx_id) + f"\n\n📚 تعداد محتواهای ارسال‌شده: {sent}",
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

            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="education")]]
            await query.edit_message_text(
                TEXTS['education_failed'].format(msg),
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
        user = user_manager.get_user(user_id)

        if user and user['has_subscription']:
            sent = await self._send_all_course(user_id)
            keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
            await query.edit_message_text(
                f"✅ {TEXTS['subscribe_active']}\n\n📚 {sent} محتوای آموزشی ارسال شد.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        context.user_data['action'] = 'subscribe'
        context.user_data['waiting_for_wallet'] = True

        keyboard = [[InlineKeyboardButton("❌ انصراف", callback_data="main_menu")]]
        await query.edit_message_text(
            TEXTS['subscribe_enter_wallet'],
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
        user = user_manager.get_user(user_id)

        if not user:
            return

        ref_count = user_manager.get_referral_count(user_id)
        ref_link = f"https://t.me/{self.application.bot.username}?start=ref_{user['referral_code']}"

        keyboard = [
            [InlineKeyboardButton("📤 اشتراک‌گذاری", url=f"https://t.me/share/url?url={ref_link}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            TEXTS['referral_text'].format(user['first_name'] or user_id, ref_count, user['referral_code'], ref_link),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
        await query.edit_message_text(
            TEXTS['guide_text'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # پنل مدیریت (همه چیز فارسی)
    # ============================================================
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if user_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return

        user_count = len(db.execute_global("SELECT user_id FROM users"))
        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        content_count = course_manager.get_content_count()
        api_count = len(payment_verifier.apis)

        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton(f"✅ تایید دستی تراکنش ({pending})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📚 ارسال محتوای دوره", callback_data="admin_send_course")],
            [InlineKeyboardButton("📝 افزودن محتوای جدید", callback_data="admin_add_content")],
            [InlineKeyboardButton(f"🔑 افزودن کلید API ({api_count})", callback_data="admin_add_api")],
            [InlineKeyboardButton("📊 آمار و اطلاعات", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"⚙️ **پنل مدیریت**\n\n"
            f"👥 کاربران: {user_count}\n"
            f"⏳ در انتظار تایید: {pending}\n"
            f"📚 محتوا: {content_count}\n"
            f"🔑 کلیدهای API: {api_count}",
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
            "📢 **ارسال پیام همگانی**\n\nمتن پیام را ارسال کنید:",
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
            "🎰 **شروع قرعه‌کشی**\n\nتعداد برندگان را وارد کنید (۱ تا ۲۰):",
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
            text += f"🔗 هش: `{p['tx_hash']}`\n\n"
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
            "مثال: `7ae83b63-fdf3-47e4-ac69-56f960a34f5b`",
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

        tx_stats = db.execute_global(
            "SELECT tx_type, status, COUNT(*) as count FROM transactions GROUP BY tx_type, status"
        )
        tx_text = ""
        for r in tx_stats:
            tx_text += f"• {r['tx_type']} - {r['status']}: {r['count']}\n"

        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))

        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        await query.edit_message_text(
            f"📊 **آمار سیستم**\n\n"
            f"👥 کاربران: {user_count}\n"
            f"✅ اشتراک فعال: {active}\n"
            f"📚 محتوای دوره: {content_count}\n"
            f"🎰 قرعه‌کشی: {lottery_count}\n"
            f"⏳ در انتظار تایید: {pending}\n"
            f"🔑 کلیدهای API: {api_count}\n\n"
            f"💳 **تراکنش‌ها:**\n{tx_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

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
            await self._send_all_course(user_id)

        elif pending['tx_type'] == 'lottery':
            user = user_manager.get_user(user_id)
            if user:
                user_manager.update_user(user_id, total_participations=(user['total_participations'] or 0) + 1)

        db.execute(user_id,
            "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) VALUES (?, ?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
            (user_id, pending['from_address'], pending['to_address'], pending['amount'], pending['tx_hash'], pending['tx_type'])
        )

        db.execute(0, "UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))

        try:
            await self.application.bot.send_message(user_id, TEXTS['user_verify_approved'], parse_mode=ParseMode.MARKDOWN)
        except:
            pass

        await query.edit_message_text(
            TEXTS['admin_verify_approved'].format(user_id, pending['amount'], pending['tx_hash']),
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

        try:
            await self.application.bot.send_message(user_id, TEXTS['user_verify_rejected'], parse_mode=ParseMode.MARKDOWN)
        except:
            pass

        await query.edit_message_text(
            TEXTS['admin_verify_rejected'].format(user_id, pending['tx_hash']),
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
            users = db.execute_global("SELECT user_id FROM users")
            sent, failed = 0, 0
            await update.message.reply_text("⏳ در حال ارسال...")
            for u in users:
                try:
                    await self.application.bot.send_message(u['user_id'], text, parse_mode=ParseMode.MARKDOWN)
                    sent += 1
                    if sent % 30 == 0:
                        await asyncio.sleep(0.5)
                except:
                    failed += 1
            context.user_data['admin_action'] = None
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await update.message.reply_text(f"✅ ارسال شد!\n📤 موفق: {sent}\n❌ ناموفق: {failed}", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        # ===== شروع قرعه‌کشی =====
        if admin_action == 'start_lottery':
            step = context.user_data.get('lottery_step', 1)
            if step == 1:
                try:
                    winners = int(text)
                    if 1 <= winners <= 20:
                        context.user_data['lottery_winners'] = winners
                        context.user_data['lottery_step'] = 2
                        await update.message.reply_text(f"✅ تعداد برندگان: {winners}\n\n💰 مبلغ جایزه هر نفر را وارد کنید (حداقل ۱۰ دلار):")
                    else:
                        await update.message.reply_text("❌ عدد بین ۱ تا ۲۰ وارد کنید!")
                except:
                    await update.message.reply_text("❌ عدد معتبر وارد کنید!")
            elif step == 2:
                try:
                    prize = float(text)
                    if prize >= 10:
                        winners = context.user_data['lottery_winners']
                        success, result = lottery_system.start_lottery(winners, prize)
                        context.user_data['admin_action'] = None
                        context.user_data['lottery_step'] = None
                        if success:
                            for wid in result['winners']:
                                try:
                                    await self.application.bot.send_message(wid, f"🎉 **تبریک!**\n\nشما برنده **${prize}** در قرعه‌کشی شدید!", parse_mode=ParseMode.MARKDOWN)
                                except:
                                    pass
                            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                            await update.message.reply_text(f"✅ **قرعه‌کشی انجام شد!**\n\nتعداد برندگان: {len(result['winners'])}\nجایزه هر نفر: ${prize}", reply_markup=InlineKeyboardMarkup(keyboard))
                        else:
                            await update.message.reply_text(f"❌ خطا: {result}")
                    else:
                        await update.message.reply_text("❌ مبلغ حداقل ۱۰ دلار باشد!")
                except:
                    await update.message.reply_text("❌ عدد معتبر وارد کنید!")
            return

        # ===== ارسال محتوای دوره =====
        if admin_action == 'send_course':
            if text.upper() == 'ALL':
                users = db.execute_global("SELECT user_id FROM users")
                sent = 0
                await update.message.reply_text(f"⏳ ارسال به {len(users)} کاربر...")
                for u in users:
                    count = await self._send_all_course(u['user_id'])
                    if count > 0:
                        sent += 1
                    await asyncio.sleep(0.2)
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(f"✅ محتوا به {sent} کاربر ارسال شد!", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                try:
                    target_id = int(text)
                    count = await self._send_all_course(target_id)
                    context.user_data['admin_action'] = None
                    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                    await update.message.reply_text(f"✅ {count} محتوا به کاربر {target_id} ارسال شد!", reply_markup=InlineKeyboardMarkup(keyboard))
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
                    await update.message.reply_text(f"✅ محتوا اضافه شد!\n🆔 ID: {cid}", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        # ===== افزودن کلید API =====
        if admin_action == 'add_api':
            api_key = text.strip()
            if api_key not in payment_verifier.apis:
                payment_verifier.apis.append(api_key)
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(f"✅ کلید API اضافه شد!\n🔑 تعداد کلیدها: {len(payment_verifier.apis)}", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text("❌ این کلید قبلاً اضافه شده است!")
            return

        # ===== دریافت هش تراکنش =====
        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            if not self._validate_tx_hash(tx_hash):
                await update.message.reply_text(TEXTS['tx_hash_invalid'], parse_mode=ParseMode.MARKDOWN)
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

            await update.message.reply_text(TEXTS['tx_hash_received'], parse_mode=ParseMode.MARKDOWN)

            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [[
                        InlineKeyboardButton("✅ تایید", callback_data=f"admin_verify_approve_{db.execute(0, 'SELECT last_insert_rowid()').fetchone()[0]}"),
                        InlineKeyboardButton("❌ رد", callback_data=f"admin_verify_reject_{db.execute(0, 'SELECT last_insert_rowid()').fetchone()[0]}")
                    ]]
                    await self.application.bot.send_message(
                        admin_id,
                        f"✅ درخواست تایید جدید!\n\n👤 کاربر: {user_id}\n💰 مبلغ: ${PAYMENT_AMOUNT}\n📤 از: {from_address}\n📂 نوع: {tx_type}\n🔗 هش: `{tx_hash}`",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            return

        # ===== دریافت آدرس کیف پول =====
        if context.user_data.get('waiting_for_wallet'):
            wallet = text.strip()
            if not self._validate_wallet(wallet):
                await update.message.reply_text(TEXTS['invalid_wallet'], parse_mode=ParseMode.MARKDOWN)
                return

            user_manager.update_user(user_id, wallet_address=wallet)
            context.user_data['waiting_for_wallet'] = False

            action = context.user_data.get('action', 'lottery')
            context.user_data['action'] = None

            callback_map = {
                'lottery': ('lottery_confirm', 'lottery', TEXTS['lottery_after_wallet']),
                'education': ('education_confirm', 'education', TEXTS['education_after_wallet']),
                'subscribe': ('subscribe_confirm', 'main_menu', TEXTS['subscribe_after_wallet']),
            }
            cb, back, msg = callback_map.get(action, ('lottery_confirm', 'lottery', TEXTS['lottery_after_wallet']))

            keyboard = [
                [InlineKeyboardButton("✅ پرداخت کردم", callback_data=cb)],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=back)]
            ]
            await update.message.reply_text(
                msg.format(DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ===== دستور نامعتبر =====
        keyboard = [[InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]]
        await update.message.reply_text(
            TEXTS['invalid_command'],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت فایل‌ها
    # ============================================================
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
    # مدیریت خطاها
    # ============================================================
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.effective_user:
                await self.application.bot.send_message(
                    update.effective_user.id,
                    TEXTS['error_message'],
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
        logger.info("🚀 ربات در حال اجراست...")
        await bot.application.initialize()
        await bot.application.start()
        await bot.application.updater.start_polling()
        logger.info("✅ ربات با موفقیت اجرا شد!")

        # ارسال خودکار محتوا به کاربران دارای اشتراک
        while True:
            try:
                users = db.execute_global(
                    "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
                )
                for u in users:
                    await bot._send_all_course(u['user_id'])
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Auto-send error: {e}")
            await asyncio.sleep(3600)

    except KeyboardInterrupt:
        logger.info("🛑 ربات متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 برنامه متوقف شد")