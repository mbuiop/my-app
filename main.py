# -*- coding: utf-8 -*-
"""
ربات آموزش ترید — نسخه ۴ (تحلیل چارت با مدل Vision محلی + محدودیت روزانه)
=============================================================================
تغییرات نسبت به v3:

1. مشاوره متنی + تحلیل چارت (عکس) حالا هر دو از طریق یک مدل Vision روی
   Ollama انجام می‌شه. کاربر می‌تونه عکس چارت بفرسته، مدل توضیح تکنیکال
   (روند، حمایت/مقاومت، الگوها) می‌ده — نه یک سیگنال مشخص خرید/فروش، چون
   این با فلسفه "آموزش نه سیگنال" ربات در تضاده.

2. محدودیت استفاده:
   - کاربران دارای اشتراک (approved): استفاده نامحدود از مشاوره AI.
   - کاربران عادی: فقط ۱ بار در روز (متن یا عکس، هرکدوم زودتر).

3. نکته مهم درباره‌ی "۸ میلیارد پارامتر مخصوص ترید":
   مدل پیشنهادی qwen2.5vl:7b یک مدل عمومیِ قوی در خوندن تصویر/چارت/نمودار
   است، نه یک مدل که از صفر روی داده مالی ترید شده. تخصصی‌شدنش را با یک
   system prompt مهندسی‌شده برای خواندن چارت انجام دادم. اگر روزی مدل
   واقعاً fine-tune شده روی ترید پیدا کردید/ساختید، کافیه AI_MODEL_NAME رو
   عوض کنید — بقیه کد دست‌نخورده می‌مونه.

راه‌اندازی روی سرور خودتان:
    1. نصب Ollama:  https://ollama.com/download
    2. دانلود مدل:   ollama pull qwen2.5vl:7b
    3. اجرا:          ollama serve      (پیش‌فرض روی پورت 11434 بالا میاد)
    4. تنظیمات پایین فایل:
           AI_API_BASE   = "http://localhost:11434/v1"
           AI_MODEL_NAME = "qwen2.5vl:7b"
           AI_API_KEY    = ""   (خالی — Ollama نیاز به کلید نداره)

    اگر سرور Ollama جای دیگه‌ای (نه همون سرور ربات) اجراست، آدرس IP همون
    سرور رو به‌جای localhost بذارید، مثلا: "http://192.168.1.50:11434/v1"

نصب پکیج‌ها:
    pip install python-telegram-bot==21.4 httpx
"""

import logging
import sqlite3
import asyncio
import base64
from datetime import datetime
from contextlib import closing

import httpx
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter, BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    PicklePersistence,
)

# ==================== تنظیمات اصلی ====================
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
BOT_USERNAME = "UTYOB_Bot"
ADMIN_IDS = [111111111]
WALLET_ADDRESS = "TSED8mCkfaNtavaBw2pQQpUoMRKGCwBsv3"
NETWORK_NAME = "TRC20 (Tron)"
PRICE_USD = 500

REFERRAL_REWARD = 10
MIN_WITHDRAWAL = 500

DB_PATH = "bot.db"
PERSISTENCE_PATH = "bot_state.pickle"
BROADCAST_CONCURRENCY = 20
BROADCAST_DELAY = 0.05

FREE_DAILY_AI_LIMIT = 1   # تعداد استفاده رایگان AI برای کاربران بدون اشتراک، در روز

# ---- تنظیمات مدل هوش مصنوعی محلی (Ollama - سازگار با OpenAI API) ----
AI_API_BASE = "http://localhost:11434/v1"   # آدرس سرور Ollama شما؛ خالی = غیرفعال
AI_API_KEY = ""
AI_MODEL_NAME = "qwen2.5vl:7b"              # مدل vision+text نصب‌شده روی Ollama
AI_TIMEOUT = 30
AI_VISION_TIMEOUT = 90                      # تحلیل تصویر کندتره، timeout بیشتر

AI_TEXT_SYSTEM_PROMPT = (
    "شما دستیار آموزشی یک آکادمی ترید هستید. فقط به سوالات آموزشی درباره "
    "تحلیل بازار، مدیریت ریسک و سرمایه، روانشناسی معامله‌گری و مفاهیم پایه "
    "ترید پاسخ بده. هرگز سیگنال خرید/فروش مشخص برای یک نماد یا لحظه خاص "
    "نده و همیشه در صورت لزوم یادآوری کن که ترید ریسک دارد و این آموزش، "
    "مشاوره مالی رسمی نیست. پاسخ‌ها را کوتاه، دقیق، محاوره‌ای و به زبان "
    "فارسی بده."
)

AI_CHART_SYSTEM_PROMPT = (
    "شما یک مربی آموزش تحلیل تکنیکال هستید که به کاربر کمک می‌کنید خودش "
    "چارت رو یاد بگیره بخونه — نه اینکه بهش بگید چیکار کنه.\n\n"
    "وقتی یک تصویر چارت (کندل‌استیک، نمودار قیمت، اندیکاتور) دریافت می‌کنید:\n"
    "۱. روند کلی قابل مشاهده رو توصیف کنید (صعودی/نزولی/رنج).\n"
    "۲. سطوح حمایت و مقاومت قابل تشخیص در تصویر رو نام ببرید.\n"
    "۳. الگوهای کندلی یا کلاسیک قابل مشاهده (اگر واضح است) رو توضیح بدید و "
    "بگید معمولاً چه معنایی دارن.\n"
    "۴. اگر اندیکاتوری مثل RSI/MACD/میانگین متحرک در تصویر است، وضعیتش رو "
    "توصیف کنید.\n"
    "۵. در پایان، ۱ تا ۲ سوال آموزشی از کاربر بپرسید تا خودش روی تحلیل فکر "
    "کنه (مثلاً: با توجه به این الگو، به نظرت ریسک ورود کجاست؟).\n\n"
    "🚫 هرگز نگید 'بخر' یا 'بفروش'، هرگز قیمت هدف یا حد ضرر مشخص ندید، و "
    "هرگز ادعای قطعیت نکنید — این فقط خوانش آموزشیه، نه توصیه مالی. اگر "
    "تصویر واضح نیست یا چارت نیست، صادقانه بگید که نمی‌تونید تحلیلش کنید.\n"
    "پاسخ را به زبان فارسی و به‌صورت خوانا بدید."
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

GUIDE_TEXT = (
    "📖 <b>راهنمای ربات</b>\n\n"
    "اینجا یک <b>آکادمی آموزش ترید</b> است، نه یک کانال سیگنال.\n\n"
    "🔴 <b>سیگنال چیه و چرا نمی‌دیم؟</b>\n"
    "سیگنال یعنی یک نفر بهتون بگه «الان بخر، الان بفروش» بدون اینکه دلیلش رو "
    "بفهمید. این کار شما رو برای همیشه به یک نفر دیگه وابسته نگه می‌داره.\n\n"
    "🟢 <b>ما چیکار می‌کنیم؟</b>\n"
    "هدف اینه که <b>خودتون یک معامله‌گر مستقل بشید</b>: تحلیل بازار، مدیریت "
    "ریسک، روانشناسی معامله‌گری و ساختن استراتژی شخصی. حتی مشاور هوش‌مصنوعی "
    "ربات هم بهتون یاد می‌ده چارت رو خودتون بخونید، نه اینکه بهتون بگه چیکار "
    "کنید.\n\nبرای ثبت‌نام از دکمه «💳 خرید و ثبت‌نام» استفاده کنید."
)

BUY_TEXT = (
    "💳 <b>خرید و ثبت‌نام دوره</b>\n\n"
    f"💵 هزینه دوره: <b>{PRICE_USD} دلار</b>\n"
    f"🌐 شبکه واریز: <b>{NETWORK_NAME}</b>\n"
    f"📥 آدرس کیف‌پول:\n<code>{WALLET_ADDRESS}</code>\n\n"
    "⚠️ فقط از طریق شبکه TRC20 واریز کنید؛ واریزی به شبکه اشتباه غیرقابل "
    "بازگشت است.\n\nبعد از واریز، عکس رسید رو ارسال کنید."
)

# ==================== دیتابیس ====================

def db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    with closing(db_conn()) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                status TEXT DEFAULT 'new',
                blocked INTEGER DEFAULT 0,
                balance REAL DEFAULT 0,
                referred_by INTEGER,
                referral_rewarded INTEGER DEFAULT 0,
                joined_at TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)")

        c.execute(
            """CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)")

        c.execute(
            """CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                wallet_address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)")

        c.execute(
            """CREATE TABLE IF NOT EXISTS education_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT,
                text TEXT,
                file_id TEXT,
                created_at TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS pending_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                answer TEXT,
                answered INTEGER DEFAULT 0,
                created_at TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_pq_answered ON pending_questions(answered)")

        c.execute(
            """CREATE TABLE IF NOT EXISTS ai_usage (
                user_id INTEGER,
                usage_date TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            )"""
        )
        conn.commit()


def upsert_user(user_id, username, first_name, referred_by=None):
    with closing(db_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if c.fetchone() is None:
            c.execute(
                "INSERT INTO users (user_id, username, first_name, status, balance, "
                "referred_by, referral_rewarded, joined_at) VALUES (?,?,?,?,?,?,?,?)",
                (user_id, username, first_name, "new", 0, referred_by, 0, datetime.now().isoformat()),
            )
        else:
            c.execute(
                "UPDATE users SET username=?, first_name=?, blocked=0 WHERE user_id=?",
                (username, first_name, user_id),
            )
        conn.commit()


def user_exists(user_id):
    with closing(db_conn()) as conn:
        return conn.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone() is not None


def set_user_status(user_id, status):
    with closing(db_conn()) as conn:
        conn.execute("UPDATE users SET status=? WHERE user_id=?", (status, user_id))
        conn.commit()


def get_user(user_id):
    with closing(db_conn()) as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def mark_blocked(user_id):
    with closing(db_conn()) as conn:
        conn.execute("UPDATE users SET blocked=1 WHERE user_id=?", (user_id,))
        conn.commit()


def add_balance(user_id, delta):
    with closing(db_conn()) as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (delta, user_id))
        conn.commit()


def mark_referral_rewarded(user_id):
    with closing(db_conn()) as conn:
        conn.execute("UPDATE users SET referral_rewarded=1 WHERE user_id=?", (user_id,))
        conn.commit()


def count_successful_referrals(user_id):
    with closing(db_conn()) as conn:
        row = conn.execute(
            "SELECT COUNT(*) c FROM users WHERE referred_by=? AND referral_rewarded=1", (user_id,)
        ).fetchone()
        return row["c"]


def all_user_ids(status=None):
    with closing(db_conn()) as conn:
        if status:
            rows = conn.execute(
                "SELECT user_id FROM users WHERE status=? AND blocked=0", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT user_id FROM users WHERE blocked=0").fetchall()
        return [r["user_id"] for r in rows]


def user_stats():
    with closing(db_conn()) as conn:
        row = conn.execute(
            """SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='new' THEN 1 ELSE 0 END) AS new_,
                SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN blocked=1 THEN 1 ELSE 0 END) AS blocked,
                SUM(balance) AS total_balance
               FROM users"""
        ).fetchone()
        d = {k: (row[k] or 0) for k in row.keys()}
        d["pending_withdrawals"] = len(pending_withdrawals())
        return d


def add_receipt(user_id, file_id):
    with closing(db_conn()) as conn:
        cur = conn.execute(
            "INSERT INTO receipts (user_id, file_id, status, created_at) VALUES (?,?,?,?)",
            (user_id, file_id, "pending", datetime.now().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def get_receipt(receipt_id):
    with closing(db_conn()) as conn:
        return conn.execute("SELECT * FROM receipts WHERE id=?", (receipt_id,)).fetchone()


def set_receipt_status(receipt_id, status):
    with closing(db_conn()) as conn:
        conn.execute("UPDATE receipts SET status=? WHERE id=?", (status, receipt_id))
        conn.commit()


def pending_receipts():
    with closing(db_conn()) as conn:
        return conn.execute("SELECT * FROM receipts WHERE status='pending' ORDER BY id").fetchall()


def create_withdrawal(user_id, amount, address):
    with closing(db_conn()) as conn:
        cur = conn.execute(
            "INSERT INTO withdrawals (user_id, amount, wallet_address, status, created_at) VALUES (?,?,?,?,?)",
            (user_id, amount, address, "pending", datetime.now().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def get_withdrawal(wid):
    with closing(db_conn()) as conn:
        return conn.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)).fetchone()


def set_withdrawal_status(wid, status):
    with closing(db_conn()) as conn:
        conn.execute("UPDATE withdrawals SET status=? WHERE id=?", (status, wid))
        conn.commit()


def pending_withdrawals():
    with closing(db_conn()) as conn:
        return conn.execute("SELECT * FROM withdrawals WHERE status='pending' ORDER BY id").fetchall()


def add_education_content(content_type, text, file_id):
    with closing(db_conn()) as conn:
        conn.execute(
            "INSERT INTO education_content (content_type, text, file_id, created_at) VALUES (?,?,?,?)",
            (content_type, text, file_id, datetime.now().isoformat()),
        )
        conn.commit()


def all_education_content():
    with closing(db_conn()) as conn:
        return conn.execute("SELECT * FROM education_content ORDER BY id").fetchall()


def add_pending_question(user_id, question):
    with closing(db_conn()) as conn:
        cur = conn.execute(
            "INSERT INTO pending_questions (user_id, question, answered, created_at) VALUES (?,?,0,?)",
            (user_id, question, datetime.now().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def unanswered_questions():
    with closing(db_conn()) as conn:
        return conn.execute("SELECT * FROM pending_questions WHERE answered=0 ORDER BY id").fetchall()


def answer_question(qid, answer):
    with closing(db_conn()) as conn:
        conn.execute("UPDATE pending_questions SET answer=?, answered=1 WHERE id=?", (answer, qid))
        conn.commit()
        return conn.execute("SELECT * FROM pending_questions WHERE id=?", (qid,)).fetchone()


# ---- سهمیه روزانه AI ----

def get_today_usage_count(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    with closing(db_conn()) as conn:
        row = conn.execute(
            "SELECT count FROM ai_usage WHERE user_id=? AND usage_date=?", (user_id, today)
        ).fetchone()
        return row["count"] if row else 0


def increment_usage(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    with closing(db_conn()) as conn:
        conn.execute(
            "INSERT INTO ai_usage (user_id, usage_date, count) VALUES (?,?,1) "
            "ON CONFLICT(user_id, usage_date) DO UPDATE SET count = count + 1",
            (user_id, today),
        )
        conn.commit()


def check_and_consume_quota(user_id, approved):
    """True یعنی مجاز به استفاده؛ برای کاربر approved همیشه True (و مصرف ثبت نمی‌شه چون نامحدوده)."""
    if approved:
        return True
    used = get_today_usage_count(user_id)
    if used >= FREE_DAILY_AI_LIMIT:
        return False
    increment_usage(user_id)
    return True


# ==================== هوش مصنوعی ====================

async def ask_ai(question: str):
    if not AI_API_BASE:
        return None
    try:
        headers = {"Content-Type": "application/json"}
        if AI_API_KEY:
            headers["Authorization"] = f"Bearer {AI_API_KEY}"
        payload = {
            "model": AI_MODEL_NAME,
            "messages": [
                {"role": "system", "content": AI_TEXT_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            "temperature": 0.4,
            "max_tokens": 700,
        }
        async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
            resp = await client.post(f"{AI_API_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("AI call failed: %s", e)
        return None


async def ask_ai_vision(user_text: str, image_bytes: bytes):
    if not AI_API_BASE:
        return None
    try:
        b64 = base64.b64encode(image_bytes).decode()
        headers = {"Content-Type": "application/json"}
        if AI_API_KEY:
            headers["Authorization"] = f"Bearer {AI_API_KEY}"
        user_content = [
            {"type": "text", "text": user_text or "این چارت رو از نظر تکنیکال و آموزشی تحلیل کن."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]
        payload = {
            "model": AI_MODEL_NAME,
            "messages": [
                {"role": "system", "content": AI_CHART_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
            "max_tokens": 900,
        }
        async with httpx.AsyncClient(timeout=AI_VISION_TIMEOUT) as client:
            resp = await client.post(f"{AI_API_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("AI vision call failed: %s", e)
        return None


# ==================== ارسال امن (flood-safe) ====================

async def safe_send(bot, user_id, kind, **kwargs):
    try:
        if kind == "message":
            await bot.send_message(chat_id=user_id, **kwargs)
        elif kind == "photo":
            await bot.send_photo(chat_id=user_id, **kwargs)
        elif kind == "video":
            await bot.send_video(chat_id=user_id, **kwargs)
        return True
    except RetryAfter as e:
        logger.warning("Flood control: sleeping %s seconds", e.retry_after)
        await asyncio.sleep(e.retry_after + 1)
        return await safe_send(bot, user_id, kind, **kwargs)
    except Forbidden:
        mark_blocked(user_id)
        return False
    except BadRequest as e:
        logger.warning("BadRequest sending to %s: %s", user_id, e)
        return False
    except Exception as e:
        logger.warning("Unexpected error sending to %s: %s", user_id, e)
        return False


async def broadcast_to(bot, user_ids, kind, **kwargs):
    sem = asyncio.Semaphore(BROADCAST_CONCURRENCY)
    counter = {"n": 0}

    async def _one(uid):
        async with sem:
            ok = await safe_send(bot, uid, kind, **kwargs)
            if ok:
                counter["n"] += 1
            await asyncio.sleep(BROADCAST_DELAY)

    await asyncio.gather(*[_one(uid) for uid in user_ids])
    return counter["n"]


async def send_all_education_to_user(context, user_id):
    for row in all_education_content():
        if row["content_type"] == "text":
            await safe_send(context.bot, user_id, "message", text=row["text"])
        elif row["content_type"] == "photo":
            await safe_send(context.bot, user_id, "photo", photo=row["file_id"], caption=row["text"] or None)
        elif row["content_type"] == "video":
            await safe_send(context.bot, user_id, "video", video=row["file_id"], caption=row["text"] or None)
        await asyncio.sleep(BROADCAST_DELAY)


async def approve_user_subscription(context, user_id, notify_text):
    row = get_user(user_id)
    set_user_status(user_id, "approved")

    if row and row["referred_by"] and not row["referral_rewarded"]:
        referrer_id = row["referred_by"]
        add_balance(referrer_id, REFERRAL_REWARD)
        mark_referral_rewarded(user_id)
        ref_row = get_user(referrer_id)
        new_bal = ref_row["balance"] if ref_row else REFERRAL_REWARD
        await safe_send(
            context.bot, referrer_id, "message",
            text=(
                f"🎉 تبریک! یکی از دعوت‌شده‌های شما با لینک اختصاصی‌تون اشتراک خرید.\n"
                f"💵 {REFERRAL_REWARD}$ به موجودی شما اضافه شد.\n"
                f"💰 موجودی فعلی: {new_bal:.2f}$"
            ),
        )

    await safe_send(context.bot, user_id, "message", text=notify_text)
    await send_all_education_to_user(context, user_id)


# ==================== کیبوردها ====================

def user_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📖 راهنما", "💳 خرید و ثبت‌نام"],
            ["📊 وضعیت من", "💬 مشاوره / تحلیل چارت"],
            ["💰 رفرال و موجودی", "🏦 برداشت"],
        ],
        resize_keyboard=True,
    )


def buy_inline_keyboard(show_balance_option, balance):
    buttons = [[InlineKeyboardButton("✅ رسید واریزی را ارسال کردم", callback_data="send_receipt")]]
    if show_balance_option:
        buttons.append(
            [InlineKeyboardButton(f"💰 استفاده از موجودی ({balance:.0f}$) برای خرید", callback_data="use_balance_purchase")]
        )
    return InlineKeyboardMarkup(buttons)


def admin_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🧾 فیش‌ها", "💸 درخواست‌های برداشت"],
            ["📝 ارسال متن آموزش", "📢 پیام همگانی"],
            ["📊 آمار کاربران", "📥 سوالات بی‌پاسخ"],
            ["🔙 بازگشت به منوی عادی"],
        ],
        resize_keyboard=True,
    )


def receipt_decision_keyboard(receipt_id):
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ تایید", callback_data=f"apprv_{receipt_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"rej_{receipt_id}"),
        ]]
    )


def withdrawal_decision_keyboard(wid):
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ پرداخت شد", callback_data=f"wd_apprv_{wid}"),
            InlineKeyboardButton("❌ رد", callback_data=f"wd_rej_{wid}"),
        ]]
    )


def is_admin(user_id):
    return user_id in ADMIN_IDS


STATUS_LABELS = {
    "new": "🆕 هنوز ثبت‌نام نکردید",
    "pending": "⏳ رسید شما در انتظار بررسی است",
    "approved": "✅ اشتراک شما فعال است",
    "rejected": "❌ رسید قبلی رد شد — می‌توانید دوباره تلاش کنید",
}

MAIN_MENU_TEXTS = {
    "📖 راهنما", "💳 خرید و ثبت‌نام", "📊 وضعیت من",
    "💬 مشاوره / تحلیل چارت", "💰 رفرال و موجودی", "🏦 برداشت",
}
ADMIN_MENU_TEXTS = {
    "🧾 فیش‌ها", "💸 درخواست‌های برداشت", "📝 ارسال متن آموزش", "📢 پیام همگانی",
    "📊 آمار کاربران", "📥 سوالات بی‌پاسخ", "🔙 بازگشت به منوی عادی",
}


# ==================== هندلرهای کاربر عادی ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    already_exists = user_exists(u.id)

    referred_by = None
    if not already_exists and context.args:
        arg = context.args[0]
        if arg.startswith("ref"):
            ref_id_str = arg[3:]
            if ref_id_str.isdigit():
                ref_id = int(ref_id_str)
                if ref_id != u.id:
                    referred_by = ref_id

    upsert_user(u.id, u.username, u.first_name, referred_by=referred_by)
    context.user_data.clear()
    await update.message.reply_text(
        f"سلام {u.first_name} 👋\nبه ربات آموزش ترید خوش اومدید.\n\nاز دکمه‌های پایین استفاده کنید:",
        reply_markup=user_main_keyboard(),
    )


async def show_guide(update, context):
    await update.message.reply_text(GUIDE_TEXT, parse_mode=ParseMode.HTML)


async def show_buy(update, context):
    u = update.effective_user
    row = get_user(u.id)
    balance = row["balance"] if row else 0
    await update.message.reply_text(
        BUY_TEXT, parse_mode=ParseMode.HTML,
        reply_markup=buy_inline_keyboard(balance >= PRICE_USD, balance),
    )


async def show_status(update, context):
    row = get_user(update.effective_user.id)
    status = row["status"] if row else "new"
    await update.message.reply_text(f"وضعیت شما: {STATUS_LABELS.get(status, status)}")


async def show_referral(update, context):
    u = update.effective_user
    row = get_user(u.id)
    balance = row["balance"] if row else 0
    referrals = count_successful_referrals(u.id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref{u.id}"
    await update.message.reply_text(
        "🤝 <b>رفرال و موجودی</b>\n\n"
        f"لینک اختصاصی شما:\n<code>{link}</code>\n\n"
        f"به ازای هر نفری که با این لینک بیاد و اشتراک بخره، <b>{REFERRAL_REWARD}$</b> "
        "به موجودی شما اضافه می‌شه.\n\n"
        f"👥 تعداد رفرال موفق: {referrals}\n"
        f"💰 موجودی فعلی: {balance:.2f}$\n\n"
        f"با موجودی {MIN_WITHDRAWAL}$ یا بیشتر می‌تونید برداشت بزنید یا برای خرید اشتراک استفاده کنید.",
        parse_mode=ParseMode.HTML,
    )


async def withdraw_button(update, context):
    u = update.effective_user
    row = get_user(u.id)
    balance = row["balance"] if row else 0
    if balance < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"موجودی فعلی شما: {balance:.2f}$\n"
            f"حداقل مبلغ برداشت {MIN_WITHDRAWAL}$ است.\n"
            f"با معرفی افراد بیشتر (هر خرید موفق = {REFERRAL_REWARD}$) به این مبلغ برسید."
        )
        return
    context.user_data["awaiting_withdraw_address"] = True
    await update.message.reply_text(
        f"موجودی قابل برداشت شما: {balance:.2f}$\nآدرس کیف‌پول TRC20 (USDT) خودتون رو بفرستید:"
    )


async def consult_button(update, context):
    u = update.effective_user
    row = get_user(u.id)
    approved = bool(row and row["status"] == "approved")

    if not approved and get_today_usage_count(u.id) >= FREE_DAILY_AI_LIMIT:
        await update.message.reply_text(
            f"⏳ شما سهمیه رایگان امروز ({FREE_DAILY_AI_LIMIT} بار) رو استفاده کردید.\n"
            "کاربران دارای اشتراک استفاده نامحدود دارن. برای خرید اشتراک از دکمه «💳 خرید و ثبت‌نام» استفاده کنید، "
            "یا فردا دوباره امتحان کنید."
        )
        return

    context.user_data["awaiting_question"] = True
    msg = "🟢 سوالتون رو بنویسید، یا عکس چارت رو برای تحلیل ارسال کنید."
    if not approved:
        msg += f"\n\n(کاربران بدون اشتراک روزی {FREE_DAILY_AI_LIMIT} بار می‌تونن استفاده کنن)"
    await update.message.reply_text(msg)


async def send_receipt_callback(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_receipt"] = True
    await query.message.reply_text("لطفاً عکس رسید واریزی خودتون رو همینجا ارسال کنید 📸")


async def use_balance_callback(update, context):
    query = update.callback_query
    u = update.effective_user
    row = get_user(u.id)
    balance = row["balance"] if row else 0
    if balance < PRICE_USD:
        await query.answer("موجودی کافی نیست.", show_alert=True)
        return
    await query.answer()
    add_balance(u.id, -PRICE_USD)
    await approve_user_subscription(
        context, u.id, "🎉 اشتراک شما با استفاده از موجودی رفرال فعال شد! محتوای آموزشی ارسال می‌شود..."
    )
    await query.message.reply_text("✅ خرید با موفقیت انجام شد.")


# ==================== عکس / ویدیو ====================

async def photo_handler(update, context):
    u = update.effective_user

    # ---- ادمین در حال افزودن محتوای آموزشی ----
    if is_admin(u.id) and context.user_data.get("awaiting_edu_content"):
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        add_education_content("photo", caption, file_id)
        n = await broadcast_to(context.bot, all_user_ids(status="approved"), "photo", photo=file_id, caption=caption or None)
        await update.message.reply_text(f"✅ عکس ثبت شد و برای {n} کاربر ارسال شد.\nبرای پایان /done را بزنید.")
        return

    # ---- کاربر در حال ارسال رسید پرداخت ----
    if context.user_data.get("awaiting_receipt"):
        file_id = update.message.photo[-1].file_id
        receipt_id = add_receipt(u.id, file_id)
        set_user_status(u.id, "pending")
        context.user_data["awaiting_receipt"] = False
        await update.message.reply_text("✅ رسید شما دریافت شد و برای بررسی به مدیریت ارسال شد.")

        caption = (
            f"🧾 رسید جدید\nکاربر: {u.first_name} (@{u.username or '-'})\n"
            f"آیدی: <code>{u.id}</code>\nشماره رسید: {receipt_id}"
        )
        for admin_id in ADMIN_IDS:
            await safe_send(
                context.bot, admin_id, "photo", photo=file_id, caption=caption,
                parse_mode=ParseMode.HTML, reply_markup=receipt_decision_keyboard(receipt_id),
            )
        return

    # ---- کاربر در حالت مشاوره، عکس = چارت برای تحلیل ----
    if context.user_data.get("awaiting_question"):
        row = get_user(u.id)
        approved = bool(row and row["status"] == "approved")

        if not check_and_consume_quota(u.id, approved):
            await update.message.reply_text(
                f"⏳ شما سهمیه رایگان امروز ({FREE_DAILY_AI_LIMIT} بار) رو استفاده کردید. "
                "برای تحلیل نامحدود چارت، اشتراک تهیه کنید یا فردا دوباره امتحان کنید."
            )
            context.user_data["awaiting_question"] = False
            return

        photo = update.message.photo[-1]
        tg_file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await tg_file.download_as_bytearray())
        caption = update.message.caption or ""

        await update.message.reply_text("⏳ در حال تحلیل چارت... (ممکنه چند ثانیه طول بکشه)")
        answer = await ask_ai_vision(caption, image_bytes)

        if answer:
            await update.message.reply_text(answer)
        else:
            add_pending_question(u.id, caption or "[کاربر یک تصویر چارت ارسال کرد]")
            await update.message.reply_text(
                "در حال حاضر تحلیل خودکار چارت در دسترس نیست (سرور AI خاموشه یا مدل نصب نشده)؛ "
                "برای بررسی به مدیر ارسال شد."
            )
            for admin_id in ADMIN_IDS:
                await safe_send(
                    context.bot, admin_id, "photo", photo=photo.file_id,
                    caption=f"❓ چارت بی‌پاسخ از {u.first_name} (@{u.username or '-'}) — آیدی {u.id}\n{caption}",
                )

        if not approved:
            context.user_data["awaiting_question"] = False
        return

    await update.message.reply_text("برای ارسال عکس، اول از منو گزینه مربوطه رو انتخاب کنید.")


async def video_handler(update, context):
    u = update.effective_user
    if is_admin(u.id) and context.user_data.get("awaiting_edu_content"):
        file_id = update.message.video.file_id
        caption = update.message.caption or ""
        add_education_content("video", caption, file_id)
        n = await broadcast_to(context.bot, all_user_ids(status="approved"), "video", video=file_id, caption=caption or None)
        await update.message.reply_text(f"✅ ویدیو ثبت شد و برای {n} کاربر ارسال شد.\nبرای پایان /done را بزنید.")


# ==================== روتر متن ====================

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    text = update.message.text.strip()

    if text == "📖 راهنما":
        return await show_guide(update, context)
    if text == "💳 خرید و ثبت‌نام":
        return await show_buy(update, context)
    if text == "📊 وضعیت من":
        return await show_status(update, context)
    if text == "💬 مشاوره / تحلیل چارت":
        return await consult_button(update, context)
    if text == "💰 رفرال و موجودی":
        return await show_referral(update, context)
    if text == "🏦 برداشت":
        return await withdraw_button(update, context)

    # ---- ثبت آدرس برداشت ----
    if context.user_data.get("awaiting_withdraw_address"):
        context.user_data["awaiting_withdraw_address"] = False
        row = get_user(u.id)
        balance = row["balance"] if row else 0
        if balance < MIN_WITHDRAWAL:
            await update.message.reply_text("موجودی کافی نیست.")
            return
        address = text
        wid = create_withdrawal(u.id, balance, address)
        add_balance(u.id, -balance)
        await update.message.reply_text("✅ درخواست برداشت شما ثبت شد و برای بررسی به مدیریت ارسال شد.")
        note = (
            f"💸 درخواست برداشت جدید\nکاربر: {u.first_name} (@{u.username or '-'})\n"
            f"آیدی: <code>{u.id}</code>\nمبلغ: {balance:.2f}$\nآدرس: <code>{address}</code>\n"
            f"شماره درخواست: {wid}"
        )
        for admin_id in ADMIN_IDS:
            await safe_send(
                context.bot, admin_id, "message", text=note, parse_mode=ParseMode.HTML,
                reply_markup=withdrawal_decision_keyboard(wid),
            )
        return

    # ---- پنل مدیریت ----
    if is_admin(u.id):
        if text == "🔙 بازگشت به منوی عادی":
            context.user_data.clear()
            await update.message.reply_text("بازگشتید.", reply_markup=user_main_keyboard())
            return

        if text == "🧾 فیش‌ها":
            rows = pending_receipts()
            if not rows:
                await update.message.reply_text("فیشی در انتظار بررسی نیست.")
                return
            for r in rows:
                await context.bot.send_photo(
                    chat_id=u.id, photo=r["file_id"], caption=f"فیش #{r['id']} — کاربر: {r['user_id']}",
                    reply_markup=receipt_decision_keyboard(r["id"]),
                )
            return

        if text == "💸 درخواست‌های برداشت":
            rows = pending_withdrawals()
            if not rows:
                await update.message.reply_text("درخواست برداشتی در انتظار نیست.")
                return
            for r in rows:
                await update.message.reply_text(
                    f"درخواست #{r['id']}\nکاربر: {r['user_id']}\nمبلغ: {r['amount']:.2f}$\n"
                    f"آدرس: <code>{r['wallet_address']}</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=withdrawal_decision_keyboard(r["id"]),
                )
            return

        if text == "📝 ارسال متن آموزش":
            context.user_data["awaiting_edu_content"] = True
            await update.message.reply_text(
                "هر متن/عکس/ویدیو بفرستید ذخیره و فوراً برای مشترکین ارسال می‌شه "
                "(و برای مشترکین بعدی هم باقی می‌مونه). برای پایان /done بفرستید."
            )
            return

        if text == "📢 پیام همگانی":
            context.user_data["awaiting_broadcast"] = True
            await update.message.reply_text("متن پیام همگانی رو بفرستید:")
            return

        if text == "📊 آمار کاربران":
            s = user_stats()
            msg = (
                "📊 <b>آمار کاربران</b>\n"
                f"👥 کل: {s['total']}\n🆕 جدید: {s['new_']}\n⏳ در انتظار: {s['pending']}\n"
                f"✅ دارای اشتراک: {s['approved']}\n❌ رد شده: {s['rejected']}\n"
                f"🚫 بلاک‌کرده: {s['blocked']}\n"
                f"💰 مجموع موجودی کاربران (بدهی): {s['total_balance']:.2f}$\n"
                f"💸 درخواست برداشت در انتظار: {s['pending_withdrawals']}\n"
                f"💵 درآمد تقریبی: {s['approved'] * PRICE_USD}$"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            return

        if text == "📥 سوالات بی‌پاسخ":
            rows = unanswered_questions()
            if not rows:
                await update.message.reply_text("سوال بی‌پاسخی نیست. 👍")
                return
            for r in rows:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("✍️ پاسخ بده", callback_data=f"answer_{r['id']}")]])
                await update.message.reply_text(f"سوال #{r['id']} از {r['user_id']}:\n\n{r['question']}", reply_markup=kb)
            return

        if context.user_data.get("awaiting_edu_content"):
            add_education_content("text", text, None)
            n = await broadcast_to(context.bot, all_user_ids(status="approved"), "message", text=text)
            await update.message.reply_text(f"✅ متن ثبت و برای {n} کاربر ارسال شد.\nبرای پایان /done بزنید.")
            return

        if context.user_data.get("awaiting_broadcast"):
            context.user_data["awaiting_broadcast"] = False
            n = await broadcast_to(context.bot, all_user_ids(), "message", text=text)
            await update.message.reply_text(f"📢 پیام به {n} کاربر ارسال شد.")
            return

        reply_qid = context.user_data.get("awaiting_reply_to_qid")
        if reply_qid:
            context.user_data["awaiting_reply_to_qid"] = None
            row = answer_question(reply_qid, text)
            if row:
                await safe_send(context.bot, row["user_id"], "message",
                                 text=f"💬 پاسخ مشاور:\n\n«{row['question']}»\n\n{text}")
                await update.message.reply_text("✅ پاسخ ارسال شد.")
            return

    # ---- حالت مشاوره کاربر عادی (متن) ----
    if context.user_data.get("awaiting_question"):
        row = get_user(u.id)
        approved = bool(row and row["status"] == "approved")

        if not check_and_consume_quota(u.id, approved):
            await update.message.reply_text(
                f"⏳ شما سهمیه رایگان امروز ({FREE_DAILY_AI_LIMIT} بار) رو استفاده کردید. "
                "برای مشاوره نامحدود، اشتراک تهیه کنید یا فردا دوباره امتحان کنید."
            )
            context.user_data["awaiting_question"] = False
            return

        answer = await ask_ai(text)
        if answer:
            await update.message.reply_text(answer)
        else:
            add_pending_question(u.id, text)
            await update.message.reply_text("در حال حاضر پاسخ خودکار در دسترس نیست؛ سوال شما برای مدیر ارسال شد 🙏")
            note = (
                f"❓ سوال بی‌پاسخ\nاز: {u.first_name} (@{u.username or '-'})\nآیدی: <code>{u.id}</code>\n\n"
                f"سوال: {text}"
            )
            for admin_id in ADMIN_IDS:
                await safe_send(context.bot, admin_id, "message", text=note, parse_mode=ParseMode.HTML)

        if not approved:
            context.user_data["awaiting_question"] = False
        return

    await update.message.reply_text("از دکمه‌های منو استفاده کنید 🙂", reply_markup=user_main_keyboard())


async def done_command(update, context):
    if is_admin(update.effective_user.id):
        context.user_data["awaiting_edu_content"] = False
        await update.message.reply_text("✅ حالت افزودن محتوا بسته شد.", reply_markup=admin_menu_keyboard())


# ==================== پنل مدیریت (callback ها) ====================

async def admin_command(update, context):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("🛠 پنل مدیریت", reply_markup=admin_menu_keyboard())


async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u = update.effective_user
    data = query.data

    if data.startswith("apprv_") or data.startswith("rej_"):
        if not is_admin(u.id):
            await query.answer("دسترسی ندارید", show_alert=True)
            return
        await query.answer()
        receipt_id = int(data.split("_", 1)[1])
        receipt = get_receipt(receipt_id)
        if not receipt:
            await query.edit_message_caption(caption="این رسید یافت نشد.")
            return
        if data.startswith("apprv_"):
            set_receipt_status(receipt_id, "approved")
            await approve_user_subscription(
                context, receipt["user_id"],
                "🎉 پرداخت شما تایید شد! به دوره خوش اومدید.\nمحتوای آموزشی ارسال می‌شود...",
            )
            await query.edit_message_caption(caption=(query.message.caption or "") + "\n\n✅ تایید شد.")
        else:
            set_receipt_status(receipt_id, "rejected")
            set_user_status(receipt["user_id"], "rejected")
            await safe_send(context.bot, receipt["user_id"], "message",
                             text="❌ رسید شما تایید نشد. دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.")
            await query.edit_message_caption(caption=(query.message.caption or "") + "\n\n❌ رد شد.")
        return

    if data.startswith("wd_apprv_") or data.startswith("wd_rej_"):
        if not is_admin(u.id):
            await query.answer("دسترسی ندارید", show_alert=True)
            return
        await query.answer()
        wid = int(data.rsplit("_", 1)[1])
        w = get_withdrawal(wid)
        if not w or w["status"] != "pending":
            await query.message.reply_text("این درخواست قبلاً پردازش شده.")
            return
        if data.startswith("wd_apprv_"):
            set_withdrawal_status(wid, "approved")
            await safe_send(context.bot, w["user_id"], "message",
                             text=f"✅ درخواست برداشت {w['amount']:.2f}$ شما تایید و پرداخت شد.")
            await query.message.reply_text(f"✅ برداشت #{wid} تایید شد. (پرداخت واقعی رو دستی انجام بدید اگه هنوز نداده‌اید)")
        else:
            set_withdrawal_status(wid, "rejected")
            add_balance(w["user_id"], w["amount"])
            await safe_send(context.bot, w["user_id"], "message",
                             text=f"❌ درخواست برداشت شما رد شد و {w['amount']:.2f}$ به موجودی شما بازگشت.")
            await query.message.reply_text(f"❌ برداشت #{wid} رد شد و موجودی به کاربر بازگشت.")
        return

    if not is_admin(u.id):
        await query.answer("دسترسی ندارید", show_alert=True)
        return
    await query.answer()

    if data.startswith("answer_"):
        qid = int(data.split("_", 1)[1])
        context.user_data["awaiting_reply_to_qid"] = qid
        await query.message.reply_text("پاسخ رو بنویس، برای کاربر ارسال می‌شه:")


# ==================== main ====================

def main():
    init_db()
    persistence = PicklePersistence(filepath=PERSISTENCE_PATH)
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("done", done_command))

    app.add_handler(CallbackQueryHandler(send_receipt_callback, pattern="^send_receipt$"))
    app.add_handler(CallbackQueryHandler(use_balance_callback, pattern="^use_balance_purchase$"))
    app.add_handler(CallbackQueryHandler(admin_callback_router))

    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    logger.info("Bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
