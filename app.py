# ============================================================
# UTYOB Bot - Trading Course + AI Chart Analysis + Referral Program
# EN/FA bilingual | Sharded DB | Cached knowledge base | Auto backups
# ============================================================

import asyncio
import base64
import logging
import sqlite3
import base58
import aiohttp
import threading
import time
import os
import shutil
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ============================================================
# ⬇️⬇️⬇️  تنظیمات — مقادیر خودت رو دقیقاً همینجا وارد کن  ⬇️⬇️⬇️
# CONFIG — fill in your own values right here
# ============================================================

BOT_TOKEN = "اینجا توکن ربات را بگذار"                       # ⬅️ از @BotFather

ADMIN_IDS = [
    111111111,                                                # ⬅️ آیدی عددی ادمین (می‌تونی چند خط اضافه کنی)
]

# ⬅️ کلید(های) TronGrid برای تایید خودکار پرداخت (بعداً هم از پنل قابل افزودنه)
TRONGRID_APIS = [
    "اینجا کلید TronGrid API را بگذار",
]

DESTINATION_WALLET = "اینجا آدرس کیف پول TRC20 را بگذار"       # ⬅️ آدرس مقصد پرداخت‌ها

# ⬅️ کلید OpenAI برای تحلیل هوشمند چارت + چت هوش مصنوعی (از platform.openai.com بگیر)
OPENAI_API_KEY = "اینجا کلید OpenAI API را بگذار"
AI_MODEL = "gpt-4o"

WELCOME_STICKER_ID = ""     # ⬅️ اختیاری: یک file_id استیکر واقعی اینجا بگذار (خالی = بدون استیکر)

PAYMENT_AMOUNT = 100          # مبلغ اشتراک به دلار
SUBSCRIPTION_DAYS = 30        # مدت اعتبار دسترسی (روز)
DB_SHARDS = 200                # تعداد شارد دیتابیس (برای ۵۰۰k+ کاربر)
CACHE_TTL = 600
DEFAULT_LANG = 'en'

CHART_ANALYSIS_DAILY_LIMIT = 2      # سقف تحلیل چارت روزانه برای هر مشترک
POINTS_PER_REFERRAL = 10             # امتیاز به‌ازای هر رفرال موفق (خرید اشتراک)
POINTS_FOR_PAYOUT = 1000              # امتیاز لازم برای برداشت
PAYOUT_USD = 50                       # مبلغ دلاری معادل POINTS_FOR_PAYOUT

BACKUP_INTERVAL_HOURS = 6
BACKUP_RETENTION = 20

# ============================================================
# ⬆️⬆️⬆️  پایان بخش تنظیمات  ⬆️⬆️⬆️
# ============================================================

BOT_USERNAME = None  # در main() از تلگرام گرفته می‌شود


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
                referred_by INTEGER,
                referral_rewarded INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                chart_date TEXT,
                chart_count INTEGER DEFAULT 0,
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
        # Used only when automatic on-chain verification fails.
        # The user can submit a TX hash and/or a payment screenshot; an admin reviews it.
        c.execute('''
            CREATE TABLE IF NOT EXISTS pending_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_hash TEXT,
                photo_file_id TEXT,
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
        # Admin-trained knowledge base: Q&A pairs and keyword-triggered replies.
        c.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT,
                key_text TEXT,
                value_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                points INTEGER,
                amount_usd REAL,
                wallet_address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_verifications(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_withdraw_status ON withdrawal_requests(status)')
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
# In-memory cache (keeps the bot fast as users scale up)
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
# Bilingual text
# ============================================================
GUIDE_EN = """📖 **Guide — How This Bot Works**

We do NOT sell trading signals. We never tell you "buy here, sell there."

Instead, we teach you the financial markets using high-level technology and several AI-driven methods, so that YOU become independent — not dependent on someone else's calls.

Here's what you get with a subscription:

1️⃣ A structured trading education course, delivered straight to this chat (text, video and files).
2️⃣ An AI-powered chart analysis tool — upload a screenshot of any chart and get an educational, technical breakdown (trend structure, support/resistance zones, patterns) up to 2 times a day.
3️⃣ A trained knowledge assistant you can ask trading questions to, any time.
4️⃣ Regular updates — new lessons are pushed to you automatically as they're added.

How to get access:

1. Tap "Trading Course" in the main menu.
2. Enter the TRC20 wallet address you'll pay from.
3. Send the payment to the address shown.
4. Tap "I've made the payment" — your transaction is checked automatically on-chain.
5. If automatic verification can't confirm it right away, you can send your TX hash and/or a payment screenshot, and our team will verify it manually.
6. Once verified, your access activates immediately and all course content is sent to you.

Our goal isn't to hand you fish — it's to teach you how to fish, using real technology, real analysis tools, and a real curriculum, so you can read the market on your own two feet.

📞 Questions? Just message us, or use the AI knowledge assistant.
"""

GUIDE_FA = """📖 **راهنما — این ربات چطور کار می‌کند**

ما هیچ‌وقت سیگنال ترید نمی‌فروشیم. هیچ‌وقت نمی‌گیم «اینجا بخر، اونجا بفروش».

در عوض، بازار مالی رو با تکنولوژی بالا و چند روش مبتنی بر هوش مصنوعی به شما آموزش می‌دیم؛ تا خودتون مستقل بشید، نه وابسته به تحلیل یا نظر کس دیگه‌ای.

با خرید اشتراک چه چیزی دریافت می‌کنید:

1️⃣ یک دوره‌ی آموزشی ساختاریافته‌ی ترید، مستقیم در همین چت (متن، ویدیو و فایل).
2️⃣ ابزار تحلیل هوشمند چارت با هوش مصنوعی — عکس چارت رو بفرستید و یک تحلیل تکنیکال آموزشی (روند، نواحی حمایت/مقاومت، الگوها) دریافت کنید؛ تا روزی ۲ بار.
3️⃣ یک دستیار هوشمند آموزش‌دیده که هر زمان سوال ترید داشتید می‌تونید ازش بپرسید.
4️⃣ به‌روزرسانی مداوم — درس‌های جدید به‌محض اضافه‌شدن خودکار براتون ارسال می‌شه.

مراحل دریافت دسترسی:

۱. روی «دوره آموزش ترید» در منوی اصلی بزنید.
۲. آدرس کیف‌پول TRC20 که پرداخت رو ازش انجام می‌دید وارد کنید.
۳. مبلغ رو به آدرس نمایش‌داده‌شده واریز کنید.
۴. روی «پرداخت را انجام دادم» بزنید — تراکنش شما خودکار روی بلاکچین بررسی می‌شه.
۵. اگه تایید خودکار سریع انجام نشد، می‌تونید هش تراکنش و/یا اسکرین‌شات پرداخت رو بفرستید تا تیم ما به‌صورت دستی بررسی کنه.
۶. به‌محض تایید، دسترسی شما فوراً فعال و تمام محتوای دوره براتون ارسال می‌شه.

هدف ما این نیست که ماهی بهتون بدیم؛ هدف اینه که با ابزار واقعی، تحلیل واقعی و یک برنامه‌ی درسی واقعی، ماهیگیری رو یادتون بدیم تا روی پای خودتون بازار رو بخونید.

📞 سوالی داشتید؟ همینجا پیام بدید یا از دستیار هوشمند دانش استفاده کنید.
"""

LANGUAGES = {
    'en': {
        'name': 'English',
        'welcome': "🎉 **Welcome to UTYOB Trading Academy!** 🎉\n\nWe're glad you're here. Explore the menu below to get started:",
        'main_menu': "🎯 **Main Menu**",
        'education': "📚 Trading Course",
        'guide': "📖 Guide",
        'language_btn': "🌐 Language",
        'ai_chart_btn': "🤖 AI Chart Analysis",
        'referral_btn': "👥 Referral Program",
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
        'verify_failed': "❌ We couldn't automatically confirm the transaction yet.\n\nIf you're sure you paid, send your **TX hash** and/or a **screenshot** of the payment here — you can send either or both — and admin will verify it manually:",
        'tx_hash_invalid': "❌ Invalid TX hash. It must be 64 characters.",
        'proof_received': "✅ Received — thanks!\n⏳ Your payment proof is being reviewed by admin. You'll be notified once verified.",
        'proof_submit': "✅ Submit for manual review",
        'guide_text': GUIDE_EN,
        'invalid_command': "🤔 I didn't quite catch that — try the menu buttons, or just ask me a trading question!",
        'error_message': "⚠️ Something went wrong. Please try again.",
        'payment_confirmed_admin_note': "✅ Payment auto-verified\n👤 User: {}\n💰 Amount: {}$",
        'admin_only': "⛔ Unauthorized.",
        # AI chart analysis
        'chart_not_subscribed': "🔒 AI Chart Analysis is available to active subscribers only. Get the Trading Course to unlock it!",
        'chart_prompt': "🤖 **AI Chart Analysis**\n\nSend a screenshot of your chart. You have {} analysis/analyses left today.",
        'chart_limit_reached': "⏳ You've used today's AI chart analyses ({}/day). Come back tomorrow!",
        'chart_analyzing': "🔎 Analyzing your chart with AI... this can take a few seconds.",
        'chart_result': "🤖 **AI Chart Analysis**\n\n{}\n\n_Educational analysis only — not financial advice._",
        'chart_error': "⚠️ Couldn't analyze the chart right now. Please try again in a bit.",
        # Referral
        'referral_text': "👥 **Referral Program**\n\nYour personal invite link:\n`{}`\n\n⭐ Your points: {}\n🎯 {} points = ${}\n📊 You need {} more points to cash out.\n\nEvery friend who buys a subscription through your link earns you {} points!",
        'withdraw_btn': "💰 Withdraw (${})",
        'withdraw_not_enough': "❌ You need at least {} points to withdraw. You currently have {}.",
        'withdraw_ask_wallet': "📤 Send the TRC20 wallet address where you want to receive your ${} payout:",
        'withdraw_requested': "✅ Withdrawal request submitted!\n⭐ {} points → 💵 ${}\n\nYou'll be paid after admin approval.",
    },
    'fa': {
        'name': 'فارسی',
        'welcome': "🎉 **به آکادمی ترید UTYOB خوش آمدید!** 🎉\n\nخوشحالیم که اینجایید. از منوی زیر شروع کنید:",
        'main_menu': "🎯 **منوی اصلی**",
        'education': "📚 دوره آموزش ترید",
        'guide': "📖 راهنما",
        'language_btn': "🌐 زبان",
        'ai_chart_btn': "🤖 تحلیل هوشمند چارت",
        'referral_btn': "👥 برنامه معرفی دوستان",
        'back': "🔙 بازگشت",
        'main_menu_btn': "🏠 منوی اصلی",
        'cancel': "❌ انصراف",
        'retry': "🔄 تلاش مجدد",
        'education_title': "📚 **دوره آموزش ترید**\n\nترید حرفه‌ای را از صفر تا صد یاد بگیرید.\n\n💰 هزینه: {}$ (USDT-TRC20)\n📅 مدت دسترسی: {} روز",
        'education_buy': "💳 خرید / تمدید دسترسی",
        'education_active': "✅ شما در حال حاضر دسترسی فعال دارید.\n📅 تا تاریخ: {}",
        'enter_wallet': "📤 **آدرس کیف‌پول TRC20 خودتان را وارد کنید:**",
        'invalid_wallet': "❌ آدرس کیف‌پول نامعتبر است.\nفرمت صحیح: `TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`",
        'after_wallet': "✅ آدرس ذخیره شد.\n\n💰 لطفاً مبلغ {}$ (USDT-TRC20) را به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ پس از واریز، دکمه‌ی **✅ پرداخت را انجام دادم** را بزنید.",
        'confirm_payment': "✅ پرداخت را انجام دادم",
        'verifying': "⏳ در حال بررسی تراکنش روی بلاکچین... چند لحظه صبر کنید.",
        'verify_success': "✅ **پرداخت تایید شد!**\n\n🔗 هش تراکنش: `{}`\n\n📚 {} محتوا برای شما ارسال شد.",
        'verify_failed': "❌ تراکنش هنوز به‌صورت خودکار تایید نشد.\n\nاگر مطمئنید پرداخت را انجام دادید، **هش تراکنش** و/یا **اسکرین‌شات** پرداخت را همینجا بفرستید — می‌تونید فقط یکی یا هر دو رو بفرستید — تا مدیریت به‌صورت دستی بررسی کند:",
        'tx_hash_invalid': "❌ هش تراکنش نامعتبر است. هش باید ۶۴ کاراکتر باشد.",
        'proof_received': "✅ دریافت شد — ممنون!\n⏳ مدرک پرداخت شما در حال بررسی توسط مدیریت است. به محض تایید به شما اطلاع داده می‌شود.",
        'proof_submit': "✅ ارسال برای بررسی دستی",
        'guide_text': GUIDE_FA,
        'invalid_command': "🤔 متوجه نشدم — از دکمه‌های منو استفاده کنید، یا مستقیم یک سوال ترید بپرسید!",
        'error_message': "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
        'payment_confirmed_admin_note': "✅ پرداخت به‌صورت خودکار تایید شد\n👤 کاربر: {}\n💰 مبلغ: {}$",
        'admin_only': "⛔ دسترسی غیرمجاز.",
        'chart_not_subscribed': "🔒 تحلیل هوشمند چارت فقط برای مشترکین فعال است. با خرید دوره آموزش ترید فعالش کنید!",
        'chart_prompt': "🤖 **تحلیل هوشمند چارت**\n\nعکس چارت خود را ارسال کنید. امروز {} بار دیگر می‌توانید تحلیل بگیرید.",
        'chart_limit_reached': "⏳ سقف تحلیل امروز شما تمام شد (روزی {} بار). فردا دوباره تلاش کنید!",
        'chart_analyzing': "🔎 در حال تحلیل چارت شما با هوش مصنوعی... چند لحظه صبر کنید.",
        'chart_result': "🤖 **تحلیل هوشمند چارت**\n\n{}\n\n_این تحلیل صرفاً آموزشی است و توصیه‌ی مالی محسوب نمی‌شود._",
        'chart_error': "⚠️ در حال حاضر امکان تحلیل چارت نیست. کمی بعد دوباره تلاش کنید.",
        'referral_text': "👥 **برنامه معرفی دوستان**\n\nلینک اختصاصی دعوت شما:\n`{}`\n\n⭐ امتیاز شما: {}\n🎯 {} امتیاز = {}$\n📊 برای برداشت {} امتیاز دیگر لازم دارید.\n\nهر دوستی که با لینک شما اشتراک بخرد، {} امتیاز به شما می‌دهد!",
        'withdraw_btn': "💰 برداشت ({}$)",
        'withdraw_not_enough': "❌ برای برداشت حداقل به {} امتیاز نیاز دارید. امتیاز فعلی شما: {}",
        'withdraw_ask_wallet': "📤 آدرس کیف‌پول TRC20 که می‌خواهید {}$ به آن واریز شود را ارسال کنید:",
        'withdraw_requested': "✅ درخواست برداشت ثبت شد!\n⭐ {} امتیاز → 💵 {}$\n\nپس از تایید مدیریت پرداخت انجام می‌شود.",
    }
}

# Admin panel is always shown in Persian regardless of the admin's own language setting.
ADMIN_TEXTS = {
    'admin_panel_title': "⚙️ **پنل مدیریت**\n\n👥 کاربران: {}\n⏳ در انتظار بررسی دستی: {}\n💰 درخواست برداشت در انتظار: {}\n📚 محتوای دوره: {}\n🔑 کلیدهای API: {}",
    'admin_broadcast_btn': "📢 ارسال پیام همگانی",
    'admin_manual_verify_btn': "✅ تایید دستی پرداخت ({})",
    'admin_withdrawals_btn': "💰 درخواست‌های برداشت ({})",
    'admin_send_course_btn': "📚 ارسال محتوای دوره",
    'admin_add_content_btn': "📝 افزودن محتوای جدید",
    'admin_add_api_btn': "🔑 افزودن کلید API",
    'admin_knowledge_btn': "🧠 آموزش سوال و جواب و کلمات کلیدی",
    'admin_stats_btn': "📊 آمار",
    'admin_back_btn': "🔙 بازگشت",
    'admin_cancel_btn': "🔙 انصراف",
    'admin_broadcast_prompt': "📢 **ارسال پیام همگانی**\n\nمتن پیام را ارسال کنید:",
    'admin_no_pending': "✅ موردی در انتظار بررسی نیست!",
    'admin_pending_header': "✅ **صف بررسی دستی پرداخت**\n(فقط مواردی که تایید خودکار روی بلاکچین برایشان ممکن نشد)\n\n",
    'admin_approve': "✅ تایید #{}",
    'admin_reject': "❌ رد #{}",
    'admin_send_course_prompt': "📚 **ارسال محتوای دوره**\n\nآیدی عددی کاربر را وارد کنید، یا برای ارسال به همه: `ALL`",
    'admin_add_content_step1': "📝 **افزودن محتوای جدید**\n\nمرحله ۱/۳: عنوان را وارد کنید:",
    'admin_add_content_step2': "📝 مرحله ۲/۳: توضیحات متن را وارد کنید:",
    'admin_add_content_step3': "📝 مرحله ۳/۳: فایل را ارسال کنید (عکس/ویدیو/سند)، یا برای فقط متن: /skip",
    'admin_content_added': "✅ محتوا اضافه شد و برای همه‌ی مشترکین فعال ارسال می‌شود! ID: {}",
    'admin_add_api_prompt': "🔑 **افزودن کلید TronGrid API**\n\nکلید را ارسال کنید.\n⚠️ هرچه کلید بیشتر، تایید خودکار سریع‌تر و پایدارتر می‌شود.",
    'admin_api_added': "✅ کلید API اضافه شد!\n🔑 تعداد کلیدها: {}",
    'admin_api_duplicate': "❌ این کلید قبلاً اضافه شده است!",
    'admin_stats_title': "📊 **آمار سیستم**\n\n👥 کاربران کل: {}\n✅ اشتراک فعال: {}\n📚 محتوای دوره: {}\n🧠 آیتم‌های دانش: {}\n⏳ در انتظار بررسی دستی: {}\n💰 درخواست برداشت در انتظار: {}\n🔑 کلیدهای API: {}\n\n⚡ کش: {} آیتم | نرخ برخورد {:.1f}%",
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
    'admin_new_manual_request': "🆕 درخواست بررسی دستی پرداخت (تایید خودکار ناموفق بود)\n\n👤 کاربر: {}\n💰 مبلغ: {}$\n📤 از آدرس: {}\n🔗 هش: {}",
    'admin_knowledge_menu': "🧠 **آموزش مغز ربات**\n\nهر چیزی که اینجا اضافه کنی، ربات همیشه به‌خاطر می‌سپاره و در پاسخ به کاربران ازش استفاده می‌کنه.",
    'admin_add_qa_btn': "➕ افزودن سوال و جواب",
    'admin_add_keyword_btn': "➕ افزودن کلمه‌ی کلیدی",
    'admin_qa_step1': "❓ سوال را ارسال کنید:",
    'admin_qa_step2': "💬 حالا جواب این سوال را ارسال کنید:",
    'admin_qa_saved': "✅ سوال و جواب ذخیره شد! ربات از الان اینو بلده.",
    'admin_keyword_step1': "🔑 کلمه‌ی کلیدی را ارسال کنید:",
    'admin_keyword_step2': "💬 حالا پاسخی که باید برای این کلمه‌ی کلیدی نمایش داده شود را ارسال کنید:",
    'admin_keyword_saved': "✅ کلمه‌ی کلیدی ذخیره شد! ربات از الان اینو بلده.",
    'admin_withdrawals_none': "✅ درخواست برداشتی در انتظار نیست!",
    'admin_withdrawals_header': "💰 **درخواست‌های برداشت**\n\n",
    'admin_withdraw_approve': "✅ پرداخت شد #{}",
    'admin_withdraw_reject': "❌ رد #{}",
    'admin_withdraw_approved_note': "✅ برداشت تایید شد! (پرداخت را دستی برای کاربر انجام بده)\n👤 کاربر: {}\n💵 مبلغ: {}$",
    'admin_withdraw_rejected_note': "❌ برداشت رد شد و امتیاز به کاربر برگشت.\n👤 کاربر: {}",
    'admin_withdraw_approved_user_msg': "✅ درخواست برداشت شما تایید شد و به‌زودی مبلغ برایتان واریز می‌شود.",
    'admin_withdraw_rejected_user_msg': "❌ درخواست برداشت شما رد شد و امتیازتان بازگردانده شد.",
}


# ============================================================
# OpenAI AI client (chart analysis + trained chat assistant)
# ============================================================
class AIClient:
    def __init__(self):
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45))
        return self.session

    def is_configured(self):
        return bool(OPENAI_API_KEY) and "اینجا" not in OPENAI_API_KEY

    async def _call(self, system_prompt, user_content, max_tokens=1024):
        if not self.is_configured():
            return None, "AI API key not configured"
        session = await self.get_session()
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": AI_MODEL,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        try:
            async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body) as resp:
                data = await resp.json()
                if resp.status != 200:
                    logger.error(f"AI API error {resp.status}: {data}")
                    return None, f"API error {resp.status}"
                text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return text.strip(), None
        except Exception as e:
            logger.error(f"AI API exception: {e}")
            return None, str(e)

    async def analyze_chart(self, image_b64, media_type, lang):
        lang_note = "Respond in English." if lang == 'en' else "پاسخ را به زبان فارسی بده."
        system_prompt = (
            "You are a professional technical-analysis educator for a trading academy. "
            "Analyze the uploaded chart screenshot and describe: overall trend, key support/resistance zones, "
            "notable candlestick or chart patterns, and general market structure. "
            "This is for EDUCATIONAL purposes only — never give direct buy/sell signals, price targets, or financial advice. "
            "Keep it clear, structured, and useful for someone learning to read charts themselves. " + lang_note
        )
        user_content = [
            {"type": "text", "text": "Please analyze this trading chart."},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
        ]
        return await self._call(system_prompt, user_content, max_tokens=800)

    async def chat_answer(self, user_message, knowledge_context, lang):
        lang_note = "Respond in English." if lang == 'en' else "پاسخ را به زبان فارسی بده."
        system_prompt = (
            "You are the knowledge assistant for a trading education academy (UTYOB). "
            "You teach trading concepts and never provide direct buy/sell signals or guaranteed outcomes. "
            "Use the following admin-provided reference knowledge whenever it's relevant — treat it as ground truth:\n\n"
            f"{knowledge_context}\n\n"
            "If the question is unrelated to trading/the academy and the reference knowledge doesn't cover it, "
            "answer briefly and helpfully anyway. Keep answers concise. " + lang_note
        )
        return await self._call(system_prompt, user_message, max_tokens=500)


ai_client = AIClient()


# ============================================================
# TronGrid payment verification
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
                    return True, result
            except Exception as e:
                logger.warning(f"TronGrid API error ({api[:8]}...): {e}")
                continue
        return False, None

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
    def register_user(user_id, username=None, first_name=None, last_name=None, referred_by=None):
        try:
            cur = db.execute(user_id, "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cur.fetchone():
                return False
            db.execute(user_id,
                "INSERT INTO users (user_id, username, first_name, last_name, referred_by) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, first_name, last_name, referred_by)
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
# Knowledge base manager (the "brain" — admin-trained Q&A + keywords)
# ============================================================
class KnowledgeManager:
    @staticmethod
    def add(kind, key_text, value_text):
        cur = db.execute(0, "INSERT INTO knowledge_base (kind, key_text, value_text) VALUES (?, ?, ?)", (kind, key_text, value_text))
        cache.delete("kb_all")
        return cur.lastrowid

    @staticmethod
    def get_all():
        cached = cache.get("kb_all")
        if cached is not None:
            return cached
        results = db.execute_global("SELECT * FROM knowledge_base ORDER BY created_at DESC")
        cache.set("kb_all", results, ttl=1800)
        return results

    @staticmethod
    def match_keyword(text):
        text_low = text.lower()
        for row in KnowledgeManager.get_all():
            if row['kind'] == 'keyword' and row['key_text'].lower() in text_low:
                return row['value_text']
        return None

    @staticmethod
    def build_context(max_chars=4000):
        parts = []
        total = 0
        for row in KnowledgeManager.get_all():
            if row['kind'] == 'qa':
                line = f"Q: {row['key_text']}\nA: {row['value_text']}\n"
            else:
                line = f"Keyword '{row['key_text']}' -> {row['value_text']}\n"
            if total + len(line) > max_chars:
                break
            parts.append(line)
            total += len(line)
        return "\n".join(parts) if parts else "(no trained knowledge yet)"


knowledge_manager = KnowledgeManager()


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
        app.add_handler(CallbackQueryHandler(self.proof_submit_callback, pattern="^proof_submit$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.ai_chart_callback, pattern="^ai_chart$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.withdraw_callback, pattern="^withdraw$"))

        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_send_course_callback, pattern="^admin_send_course$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_content_callback, pattern="^admin_add_content$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api_callback, pattern="^admin_add_api$"))
        app.add_handler(CallbackQueryHandler(self.admin_knowledge_menu_callback, pattern="^admin_knowledge$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_qa_callback, pattern="^admin_add_qa$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_keyword_callback, pattern="^admin_add_keyword$"))
        app.add_handler(CallbackQueryHandler(self.admin_withdrawals_callback, pattern="^admin_withdrawals$"))
        app.add_handler(CallbackQueryHandler(self.admin_withdraw_approve_callback, pattern="^admin_withdraw_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_withdraw_reject_callback, pattern="^admin_withdraw_reject_"))
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

    def _ta(self, key, *args):
        """Admin-panel text — always Persian regardless of the admin's own language."""
        text = ADMIN_TEXTS.get(key, key)
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

    async def _broadcast_content_to_active_subscribers(self, content):
        """Fire-and-forget push of freshly added content to everyone with active access."""
        users = db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')")
        for u in users:
            if await course_manager.send_content_to_user(self.application.bot, u['user_id'], content):
                course_manager.mark_as_sent(u['user_id'], content['id'])
            await asyncio.sleep(0.1)

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
            [InlineKeyboardButton(self._t(user_id, 'ai_chart_btn'), callback_data="ai_chart"),
             InlineKeyboardButton(self._t(user_id, 'referral_btn'), callback_data="referral")],
            [InlineKeyboardButton(self._t(user_id, 'guide'), callback_data="guide"),
             InlineKeyboardButton(self._t(user_id, 'language_btn'), callback_data="language_menu")],
        ]
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)

    def _referral_link(self, user_id):
        username = BOT_USERNAME or "your_bot"
        return f"https://t.me/{username}?start=ref_{user_id}"

    # ---------------- /start & language ----------------
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        referred_by = None
        if context.args:
            arg = context.args[0]
            if arg.startswith('ref_'):
                try:
                    ref_id = int(arg.split('_', 1)[1])
                    if ref_id != user.id:
                        referred_by = ref_id
                except ValueError:
                    pass

        is_new = user_manager.register_user(user.id, user.username, user.first_name, user.last_name, referred_by)
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

        await self._send_welcome(update.message.reply_text, self.application.bot, user.id)

    async def _send_welcome(self, reply_func, bot, user_id):
        if WELCOME_STICKER_ID:
            try:
                await bot.send_sticker(user_id, WELCOME_STICKER_ID)
            except Exception:
                pass
        await reply_func(self._t(user_id, 'welcome'), reply_markup=self._main_menu_keyboard(user_id), parse_mode=ParseMode.MARKDOWN)

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
        if WELCOME_STICKER_ID:
            try:
                await self.application.bot.send_sticker(user_id, WELCOME_STICKER_ID)
            except Exception:
                pass
        await query.edit_message_text(
            self._t(user_id, 'welcome'), reply_markup=self._main_menu_keyboard(user_id), parse_mode=ParseMode.MARKDOWN
        )

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        await query.edit_message_text(self._t(user_id, 'main_menu'), reply_markup=self._main_menu_keyboard(user_id), parse_mode=ParseMode.MARKDOWN)

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
        ok, tx_id = await payment_verifier.verify_transaction(user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT)

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
                    await self.application.bot.send_message(admin_id, f"✅ پرداخت به‌صورت خودکار تایید شد\n👤 کاربر: {user_id}\n💰 مبلغ: {PAYMENT_AMOUNT}$")
                except Exception:
                    pass
        else:
            context.user_data['waiting_for_proof'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            keyboard = [
                [InlineKeyboardButton(self._t(user_id, 'retry'), callback_data="education_confirm")],
                [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="education")]
            ]
            await query.edit_message_text(self._t(user_id, 'verify_failed'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def proof_submit_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """User taps 'submit for review' after sending hash and/or photo."""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        await self._finalize_proof_submission(user_id, context)
        await query.edit_message_text(self._t(user_id, 'proof_received'), parse_mode=ParseMode.MARKDOWN)

    async def _finalize_proof_submission(self, user_id, context):
        tx_hash = context.user_data.get('proof_tx_hash')
        photo_id = context.user_data.get('proof_photo_id')
        from_address = context.user_data.get('tx_from_address')
        cur = db.execute(0,
            "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, tx_hash, photo_file_id, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
            (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash, photo_id)
        )
        cache.delete("pending_count")
        context.user_data['waiting_for_proof'] = False
        context.user_data['proof_tx_hash'] = None
        context.user_data['proof_photo_id'] = None
        pid = cur.lastrowid
        for admin_id in ADMIN_IDS:
            try:
                keyboard = [[
                    InlineKeyboardButton("✅", callback_data=f"admin_verify_approve_{pid}"),
                    InlineKeyboardButton("❌", callback_data=f"admin_verify_reject_{pid}")
                ]]
                note = self._ta('admin_new_manual_request', user_id, PAYMENT_AMOUNT, from_address, tx_hash or '—')
                if photo_id:
                    await self.application.bot.send_photo(admin_id, photo_id, caption=note, reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    await self.application.bot.send_message(admin_id, note, reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                pass

    async def _activate_subscription(self, user_id, from_address, tx_id):
        end_date = (datetime.now() + timedelta(days=SUBSCRIPTION_DAYS)).strftime('%Y-%m-%d')
        user_manager.update_user(user_id, has_subscription=1, subscription_end=end_date)
        db.execute(user_id,
            "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
            (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
        )
        # Reward the referrer once per user.
        user = user_manager.get_user(user_id)
        if user and user.get('referred_by') and not user.get('referral_rewarded'):
            referrer_id = user['referred_by']
            referrer = user_manager.get_user(referrer_id)
            if referrer:
                user_manager.update_user(referrer_id, points=(referrer.get('points') or 0) + POINTS_PER_REFERRAL)
                user_manager.update_user(user_id, referral_rewarded=1)
                try:
                    await self.application.bot.send_message(
                        referrer_id,
                        f"🎉 +{POINTS_PER_REFERRAL} points! Someone you invited just subscribed."
                        if self._get_lang(referrer_id) == 'en' else
                        f"🎉 {POINTS_PER_REFERRAL}+ امتیاز! یکی از دعوت‌شده‌های شما اشتراک خرید."
                    )
                except Exception:
                    pass

    # ---------------- Guide ----------------
    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
        await query.edit_message_text(self._t(user_id, 'guide_text'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ---------------- AI Chart Analysis ----------------
    async def ai_chart_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if not user_manager.has_active_subscription(user):
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'education'), callback_data="education")],
                        [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
            await query.edit_message_text(self._t(user_id, 'chart_not_subscribed'), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        today = datetime.now().strftime('%Y-%m-%d')
        used_today = user.get('chart_count') or 0
        if user.get('chart_date') != today:
            used_today = 0
        remaining = max(0, CHART_ANALYSIS_DAILY_LIMIT - used_today)

        if remaining <= 0:
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
            await query.edit_message_text(self._t(user_id, 'chart_limit_reached', CHART_ANALYSIS_DAILY_LIMIT), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        context.user_data['waiting_for_chart'] = True
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
        await query.edit_message_text(self._t(user_id, 'chart_prompt', remaining), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def _handle_chart_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user = user_manager.get_user(user_id)
        if not user_manager.has_active_subscription(user):
            return

        today = datetime.now().strftime('%Y-%m-%d')
        used_today = user.get('chart_count') or 0
        if user.get('chart_date') != today:
            used_today = 0
        if used_today >= CHART_ANALYSIS_DAILY_LIMIT:
            await update.message.reply_text(self._t(user_id, 'chart_limit_reached', CHART_ANALYSIS_DAILY_LIMIT))
            return

        context.user_data['waiting_for_chart'] = False
        msg = await update.message.reply_text(self._t(user_id, 'chart_analyzing'))

        try:
            photo = update.message.photo[-1]
            tg_file = await context.bot.get_file(photo.file_id)
            raw = await tg_file.download_as_bytearray()
            b64 = base64.b64encode(bytes(raw)).decode('utf-8')
            analysis, err = await ai_client.analyze_chart(b64, "image/jpeg", self._get_lang(user_id))
        except Exception as e:
            logger.error(f"Chart analysis error: {e}")
            analysis, err = None, str(e)

        if analysis:
            user_manager.update_user(user_id, chart_date=today, chart_count=used_today + 1)
            await msg.edit_text(self._t(user_id, 'chart_result', analysis), parse_mode=ParseMode.MARKDOWN)
        else:
            await msg.edit_text(self._t(user_id, 'chart_error'))

    # ---------------- Referral & withdrawal ----------------
    async def referral_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)
        points = (user.get('points') or 0) if user else 0
        needed = max(0, POINTS_FOR_PAYOUT - points)
        link = self._referral_link(user_id)

        text = self._t(user_id, 'referral_text', link, points, POINTS_FOR_PAYOUT, PAYOUT_USD, needed, POINTS_PER_REFERRAL)
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'withdraw_btn', PAYOUT_USD), callback_data="withdraw")],
                    [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)
        points = (user.get('points') or 0) if user else 0

        if points < POINTS_FOR_PAYOUT:
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="referral")]]
            await query.edit_message_text(self._t(user_id, 'withdraw_not_enough', POINTS_FOR_PAYOUT, points), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        context.user_data['waiting_for_payout_wallet'] = True
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'cancel'), callback_data="referral")]]
        await query.edit_message_text(self._t(user_id, 'withdraw_ask_wallet', PAYOUT_USD), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def _create_withdrawal(self, user_id, wallet_address):
        user = user_manager.get_user(user_id)
        points = (user.get('points') or 0) if user else 0
        if points < POINTS_FOR_PAYOUT:
            return False
        user_manager.update_user(user_id, points=points - POINTS_FOR_PAYOUT)
        cur = db.execute(0,
            "INSERT INTO withdrawal_requests (user_id, points, amount_usd, wallet_address, status) VALUES (?, ?, ?, ?, 'pending')",
            (user_id, POINTS_FOR_PAYOUT, PAYOUT_USD, wallet_address)
        )
        cache.delete("withdraw_count")
        wid = cur.lastrowid
        for admin_id in ADMIN_IDS:
            try:
                keyboard = [[
                    InlineKeyboardButton(self._ta('admin_withdraw_approve', wid), callback_data=f"admin_withdraw_approve_{wid}"),
                    InlineKeyboardButton(self._ta('admin_withdraw_reject', wid), callback_data=f"admin_withdraw_reject_{wid}")
                ]]
                await self.application.bot.send_message(
                    admin_id,
                    f"💰 درخواست برداشت جدید\n👤 کاربر: {user_id}\n⭐ امتیاز: {POINTS_FOR_PAYOUT}\n💵 مبلغ: {PAYOUT_USD}$\n📤 آدرس: {wallet_address}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception:
                pass
        return True

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

        wpending = cache.get("withdraw_count")
        if wpending is None:
            wpending = len(db.execute_global("SELECT * FROM withdrawal_requests WHERE status = 'pending'"))
            cache.set("withdraw_count", wpending, ttl=60)

        keyboard = [
            [InlineKeyboardButton(self._ta('admin_broadcast_btn'), callback_data="admin_broadcast")],
            [InlineKeyboardButton(self._ta('admin_manual_verify_btn', pending), callback_data="admin_manual_verify"),
             InlineKeyboardButton(self._ta('admin_withdrawals_btn', wpending), callback_data="admin_withdrawals")],
            [InlineKeyboardButton(self._ta('admin_send_course_btn'), callback_data="admin_send_course"),
             InlineKeyboardButton(self._ta('admin_add_content_btn'), callback_data="admin_add_content")],
            [InlineKeyboardButton(self._ta('admin_knowledge_btn'), callback_data="admin_knowledge")],
            [InlineKeyboardButton(self._ta('admin_add_api_btn'), callback_data="admin_add_api"),
             InlineKeyboardButton(self._ta('admin_stats_btn'), callback_data="admin_stats")],
            [InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="main_menu")]
        ]
        text = self._ta('admin_panel_title', f"{user_count:,}", pending, wpending, course_manager.get_content_count(), len(payment_verifier.apis))
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'broadcast'
        keyboard = [[InlineKeyboardButton(self._ta('admin_cancel_btn'), callback_data="admin_panel")]]
        await query.edit_message_text(self._ta('admin_broadcast_prompt'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        pending = db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC LIMIT 5")
        if not pending:
            keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]]
            await query.edit_message_text(self._ta('admin_no_pending'), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        text = self._ta('admin_pending_header')
        keyboard = []
        for p in pending:
            text += f"👤 {p['user_id']}\n💰 ${p['amount']}\n📤 {p['from_address']}\n🔗 {p['tx_hash'] or '—'}\n📷 {'✅' if p['photo_file_id'] else '—'}\n\n"
            keyboard.append([
                InlineKeyboardButton(self._ta('admin_approve', p['id']), callback_data=f"admin_verify_approve_{p['id']}"),
                InlineKeyboardButton(self._ta('admin_reject', p['id']), callback_data=f"admin_verify_reject_{p['id']}")
            ])
        keyboard.append([InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_withdrawals_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        pending = db.execute_global("SELECT * FROM withdrawal_requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT 5")
        if not pending:
            keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]]
            await query.edit_message_text(self._ta('admin_withdrawals_none'), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        text = self._ta('admin_withdrawals_header')
        keyboard = []
        for w in pending:
            text += f"👤 {w['user_id']}\n💵 ${w['amount_usd']}\n📤 {w['wallet_address']}\n\n"
            keyboard.append([
                InlineKeyboardButton(self._ta('admin_withdraw_approve', w['id']), callback_data=f"admin_withdraw_approve_{w['id']}"),
                InlineKeyboardButton(self._ta('admin_withdraw_reject', w['id']), callback_data=f"admin_withdraw_reject_{w['id']}")
            ])
        keyboard.append([InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_withdraw_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        wid = int(query.data.split('_')[-1])
        w = db.execute(0, "SELECT * FROM withdrawal_requests WHERE id = ? AND status = 'pending'", (wid,)).fetchone()
        if not w:
            await query.edit_message_text(self._ta('admin_not_found'))
            return
        db.execute(0, "UPDATE withdrawal_requests SET status = 'approved', processed_at = CURRENT_TIMESTAMP WHERE id = ?", (wid,))
        cache.delete("withdraw_count")
        try:
            await self.application.bot.send_message(w['user_id'], self._ta('admin_withdraw_approved_user_msg'))
        except Exception:
            pass
        await query.edit_message_text(self._ta('admin_withdraw_approved_note', w['user_id'], w['amount_usd']))

    async def admin_withdraw_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        wid = int(query.data.split('_')[-1])
        w = db.execute(0, "SELECT * FROM withdrawal_requests WHERE id = ? AND status = 'pending'", (wid,)).fetchone()
        if not w:
            await query.edit_message_text(self._ta('admin_not_found'))
            return
        db.execute(0, "UPDATE withdrawal_requests SET status = 'rejected', processed_at = CURRENT_TIMESTAMP WHERE id = ?", (wid,))
        cache.delete("withdraw_count")
        refunded = user_manager.get_user(w['user_id'])
        if refunded:
            user_manager.update_user(w['user_id'], points=(refunded.get('points') or 0) + w['points'])
        try:
            await self.application.bot.send_message(w['user_id'], self._ta('admin_withdraw_rejected_user_msg'))
        except Exception:
            pass
        await query.edit_message_text(self._ta('admin_withdraw_rejected_note', w['user_id']))

    async def admin_send_course_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'send_course'
        keyboard = [[InlineKeyboardButton(self._ta('admin_cancel_btn'), callback_data="admin_panel")]]
        await query.edit_message_text(self._ta('admin_send_course_prompt'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_add_content_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_content'
        context.user_data['content_step'] = 1
        keyboard = [[InlineKeyboardButton(self._ta('admin_cancel_btn'), callback_data="admin_panel")]]
        await query.edit_message_text(self._ta('admin_add_content_step1'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_api'
        keyboard = [[InlineKeyboardButton(self._ta('admin_cancel_btn'), callback_data="admin_panel")]]
        await query.edit_message_text(self._ta('admin_add_api_prompt'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_knowledge_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        keyboard = [
            [InlineKeyboardButton(self._ta('admin_add_qa_btn'), callback_data="admin_add_qa")],
            [InlineKeyboardButton(self._ta('admin_add_keyword_btn'), callback_data="admin_add_keyword")],
            [InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]
        ]
        await query.edit_message_text(self._ta('admin_knowledge_menu'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_add_qa_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_qa'
        context.user_data['qa_step'] = 1
        keyboard = [[InlineKeyboardButton(self._ta('admin_cancel_btn'), callback_data="admin_knowledge")]]
        await query.edit_message_text(self._ta('admin_qa_step1'), reply_markup=InlineKeyboardMarkup(keyboard))

    async def admin_add_keyword_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_keyword'
        context.user_data['kw_step'] = 1
        keyboard = [[InlineKeyboardButton(self._ta('admin_cancel_btn'), callback_data="admin_knowledge")]]
        await query.edit_message_text(self._ta('admin_keyword_step1'), reply_markup=InlineKeyboardMarkup(keyboard))

    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        user_count = len(db.execute_global("SELECT user_id FROM users"))
        active = len(db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"))
        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        wpending = len(db.execute_global("SELECT * FROM withdrawal_requests WHERE status = 'pending'"))
        kb_count = len(knowledge_manager.get_all())
        cache_stats = cache.get_stats()
        keyboard = [
            [InlineKeyboardButton(self._ta('admin_refresh'), callback_data="admin_stats")],
            [InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]
        ]
        text = self._ta('admin_stats_title', f"{user_count:,}", f"{active:,}", course_manager.get_content_count(), kb_count,
                         pending, wpending, len(payment_verifier.apis), cache_stats['size'], cache_stats['hit_rate'])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    async def admin_verify_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        pending_id = int(query.data.split('_')[-1])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text(self._ta('admin_not_found'))
            return
        await self._activate_subscription(p['user_id'], p['from_address'], p['tx_hash'] or 'manual-photo-review')
        db.execute(0, "UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")
        try:
            await self._send_all_course(p['user_id'])
            await self.application.bot.send_message(p['user_id'], self._ta('admin_approved_user_msg'))
        except Exception:
            pass
        await query.edit_message_text(self._ta('admin_approved_note', p['user_id']))

    async def admin_verify_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.from_user.id not in ADMIN_IDS:
            return
        pending_id = int(query.data.split('_')[-1])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text(self._ta('admin_not_found'))
            return
        db.execute(0, "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")
        try:
            await self.application.bot.send_message(p['user_id'], self._ta('admin_rejected_user_msg'))
        except Exception:
            pass
        await query.edit_message_text(self._ta('admin_rejected_note', p['user_id']))

    # ---------------- Text messages ----------------
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        user_manager.register_user(user_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)
        admin_action = context.user_data.get('admin_action')

        if admin_action == 'broadcast':
            await update.message.reply_text(self._ta('admin_broadcast_sending'))
            sent, failed = await self._broadcast_to_all(text)
            context.user_data['admin_action'] = None
            keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]]
            await update.message.reply_text(self._ta('admin_broadcast_sent', f"{sent:,}", f"{failed:,}"), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if admin_action == 'send_course':
            if text.strip().upper() == 'ALL':
                users = user_manager.get_all_users()
                await update.message.reply_text(self._ta('admin_send_course_sending_all', len(users)))
                sent = 0
                for u in users:
                    if await self._send_all_course(u['user_id']) > 0:
                        sent += 1
                    await asyncio.sleep(0.15)
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]]
                await update.message.reply_text(self._ta('admin_send_course_done_all', sent), reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                try:
                    target_id = int(text.strip())
                    count = await self._send_all_course(target_id)
                    context.user_data['admin_action'] = None
                    keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]]
                    await update.message.reply_text(self._ta('admin_send_course_done_one', count, target_id), reply_markup=InlineKeyboardMarkup(keyboard))
                except ValueError:
                    await update.message.reply_text(self._ta('admin_invalid_id'))
            return

        if admin_action == 'add_content':
            step = context.user_data.get('content_step', 1)
            if step == 1:
                context.user_data['content_title'] = text
                context.user_data['content_step'] = 2
                await update.message.reply_text(self._ta('admin_add_content_step2'))
            elif step == 2:
                context.user_data['content_text'] = text
                context.user_data['content_step'] = 3
                await update.message.reply_text(self._ta('admin_add_content_step3'))
            elif step == 3 and text.strip().lower() == '/skip':
                title = context.user_data.get('content_title', 'Untitled')
                content_text = context.user_data.get('content_text', '')
                cid = course_manager.add_content('text', title, content_text)
                context.user_data['admin_action'] = None
                context.user_data['content_step'] = None
                keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]]
                await update.message.reply_text(self._ta('admin_content_added', cid), reply_markup=InlineKeyboardMarkup(keyboard))
                new_content = db.execute(0, "SELECT * FROM course_content WHERE id = ?", (cid,)).fetchone()
                if new_content:
                    asyncio.create_task(self._broadcast_content_to_active_subscribers(new_content))
            return

        if admin_action == 'add_api':
            api_key = text.strip()
            if payment_verifier.add_api(api_key):
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]]
                await update.message.reply_text(self._ta('admin_api_added', len(payment_verifier.apis)), reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(self._ta('admin_api_duplicate'))
            return

        if admin_action == 'add_qa':
            step = context.user_data.get('qa_step', 1)
            if step == 1:
                context.user_data['qa_question'] = text
                context.user_data['qa_step'] = 2
                await update.message.reply_text(self._ta('admin_qa_step2'))
            elif step == 2:
                knowledge_manager.add('qa', context.user_data.get('qa_question', ''), text)
                context.user_data['admin_action'] = None
                context.user_data['qa_step'] = None
                keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_knowledge")]]
                await update.message.reply_text(self._ta('admin_qa_saved'), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if admin_action == 'add_keyword':
            step = context.user_data.get('kw_step', 1)
            if step == 1:
                context.user_data['kw_keyword'] = text
                context.user_data['kw_step'] = 2
                await update.message.reply_text(self._ta('admin_keyword_step2'))
            elif step == 2:
                knowledge_manager.add('keyword', context.user_data.get('kw_keyword', ''), text)
                context.user_data['admin_action'] = None
                context.user_data['kw_step'] = None
                keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_knowledge")]]
                await update.message.reply_text(self._ta('admin_keyword_saved'), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if context.user_data.get('waiting_for_payout_wallet'):
            wallet = text.strip()
            if not self._validate_wallet(wallet):
                await update.message.reply_text(self._t(user_id, 'invalid_wallet'), parse_mode=ParseMode.MARKDOWN)
                return
            context.user_data['waiting_for_payout_wallet'] = False
            await self._create_withdrawal(user_id, wallet)
            await update.message.reply_text(self._t(user_id, 'withdraw_requested', POINTS_FOR_PAYOUT, PAYOUT_USD), parse_mode=ParseMode.MARKDOWN)
            return

        if context.user_data.get('waiting_for_proof'):
            tx_hash = text.strip()
            if self._validate_tx_hash(tx_hash):
                context.user_data['proof_tx_hash'] = tx_hash
                keyboard = [[InlineKeyboardButton(self._t(user_id, 'proof_submit'), callback_data="proof_submit")]]
                await update.message.reply_text("✅ " + tx_hash[:16] + "... " + ("received. Add a screenshot too, or tap submit." if self._get_lang(user_id) == 'en' else "دریافت شد. عکس هم می‌تونی اضافه کنی، یا دکمه‌ی ارسال رو بزن."),
                                                 reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(self._t(user_id, 'tx_hash_invalid'), parse_mode=ParseMode.MARKDOWN)
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

        # ---------------- Fallback: trained brain (keywords -> AI chat) ----------------
        keyword_reply = knowledge_manager.match_keyword(text)
        if keyword_reply:
            await update.message.reply_text(keyword_reply)
            return

        if ai_client.is_configured():
            context_text = knowledge_manager.build_context()
            answer, err = await ai_client.chat_answer(text, context_text, self._get_lang(user_id))
            if answer:
                await update.message.reply_text(answer)
                return

        keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
        await update.message.reply_text(self._t(user_id, 'invalid_command'), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ---------------- Media ----------------
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if context.user_data.get('waiting_for_chart'):
            await self._handle_chart_photo(update, context)
            return

        if context.user_data.get('waiting_for_proof'):
            photo = update.message.photo[-1]
            context.user_data['proof_photo_id'] = photo.file_id
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'proof_submit'), callback_data="proof_submit")]]
            await update.message.reply_text(
                "✅ Screenshot received. Add a TX hash too, or tap submit." if self._get_lang(user_id) == 'en' else "✅ اسکرین‌شات دریافت شد. هش تراکنش هم می‌تونی اضافه کنی، یا دکمه‌ی ارسال رو بزن.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

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
        content_text = context.user_data.get('content_text', '')
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
            cid = course_manager.add_content(media_type, title, content_text, file_id, file_name, file_size)
            context.user_data['admin_action'] = None
            context.user_data['content_step'] = None
            keyboard = [[InlineKeyboardButton(self._ta('admin_back_btn'), callback_data="admin_panel")]]
            await update.message.reply_text(self._ta('admin_content_added', cid), reply_markup=InlineKeyboardMarkup(keyboard))
            new_content = db.execute(0, "SELECT * FROM course_content WHERE id = ?", (cid,)).fetchone()
            if new_content:
                asyncio.create_task(self._broadcast_content_to_active_subscribers(new_content))

    # ---------------- Errors ----------------
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.effective_user:
                await self.application.bot.send_message(update.effective_user.id, self._t(update.effective_user.id, 'error_message'), parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass


# ============================================================
# Backup system
# ============================================================
async def backup_loop():
    while True:
        try:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join("backups", ts)
            os.makedirs(backup_dir, exist_ok=True)
            for fname in os.listdir("data"):
                if fname.endswith(".db"):
                    shutil.copy2(os.path.join("data", fname), os.path.join(backup_dir, fname))
            logger.info(f"Backup completed: {backup_dir}")

            # prune old backups
            all_backups = sorted(os.listdir("backups")) if os.path.isdir("backups") else []
            while len(all_backups) > BACKUP_RETENTION:
                old = all_backups.pop(0)
                shutil.rmtree(os.path.join("backups", old), ignore_errors=True)
        except Exception as e:
            logger.error(f"Backup error: {e}")
        await asyncio.sleep(BACKUP_INTERVAL_HOURS * 3600)


# ============================================================
# Entry point
# ============================================================
async def main():
    global BOT_USERNAME
    bot = UTYOBot()
    logger.info("Starting bot...")
    logger.info(f"Admins: {ADMIN_IDS}")
    logger.info(f"TronGrid keys: {len(payment_verifier.apis)}")
    logger.info(f"AI configured: {ai_client.is_configured()}")
    logger.info(f"DB shards: {DB_SHARDS}")

    await bot.application.initialize()
    me = await bot.application.bot.get_me()
    BOT_USERNAME = me.username
    logger.info(f"Bot username: @{BOT_USERNAME}")

    await bot.application.start()
    await bot.application.updater.start_polling()
    logger.info("Bot is running.")

    asyncio.create_task(backup_loop())

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
