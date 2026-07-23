# -*- coding: utf-8 -*-
"""
ربات آموزش ترید — نسخه بهبودیافته
====================================
تفاوت‌های این نسخه نسبت به نسخه‌های قبلی:

1. Persistence واقعی: با PicklePersistence، اگر ربات ری‌استارت بشه، حالت‌های
   نیمه‌کاره (مثلاً ادمین وسط وارد کردن سوال‌وجواب) از بین نمی‌ره.
2. Broadcast و ارسال محتوا "flood-safe" هستن: بین ارسال‌ها فاصله می‌ذاره و اگر
   تلگرام خطای RetryAfter بده، صبر می‌کنه و ادامه می‌ده؛ اگر کاربری ربات رو
   بلاک کرده باشه (Forbidden)، فقط همون یکی رد می‌شه و بقیه ارسال ادامه پیدا می‌کنه
   (و کاربر به‌عنوان بلاک‌شده در دیتابیس علامت می‌خوره تا دیگه سراغش نره).
3. دکمه «راهنما» (توضیح آموزش نه سیگنال) از دکمه «خرید و ثبت‌نام» (که مبلغ و
   آدرس واریز رو نشون می‌ده) جدا شده، به‌علاوه دکمه «وضعیت من».
4. ایندکس روی ستون status برای سرعت بیشتر در کوئری‌های آماری.
5. تشخیص سوال‌وجواب بر اساس چند کلمه‌کلیدی جدا‌شده با کاما، نه فقط یک عبارت.

نصب:
    pip install python-telegram-bot==21.4

اجرا:
    python trading_edu_bot_v2.py
"""

import logging
import sqlite3
import asyncio
from datetime import datetime
from contextlib import closing

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

# ==================== تنظیمات ====================
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
ADMIN_IDS = [111111111]          # آیدی عددی مدیر/مدیران (چند نفر مجازه)
WALLET_ADDRESS = "TSED8mCkfaNtavaBw2pQQpUoMRKGCwBsv3"
NETWORK_NAME = "TRC20 (Tron)"
PRICE_USD = 500

DB_PATH = "bot.db"
PERSISTENCE_PATH = "bot_state.pickle"
BROADCAST_DELAY = 0.05  # فاصله بین پیام‌ها؛ برای جلوگیری از Flood control تلگرام

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

GUIDE_TEXT = (
    "📖 <b>راهنمای ربات</b>\n\n"
    "اینجا یک <b>آکادمی آموزش ترید</b> است، نه یک کانال سیگنال.\n\n"
    "🔴 <b>سیگنال چیه و چرا نمی‌دیم؟</b>\n"
    "سیگنال یعنی یک نفر بهتون بگه «الان بخر، الان بفروش» بدون اینکه دلیلش رو "
    "بفهمید. این کار شما رو برای همیشه به یک نفر دیگه وابسته نگه می‌داره؛ روزی "
    "که اون شخص یا کانال از بین بره، شما دوباره دست‌خالی می‌مونید.\n\n"
    "🟢 <b>ما چیکار می‌کنیم؟</b>\n"
    "هدف ما اینه که <b>خودتون یک معامله‌گر مستقل بشید</b>:\n"
    "• تحلیل تکنیکال و فاندامنتال بازار\n"
    "• مدیریت ریسک و سرمایه\n"
    "• روانشناسی معامله‌گری و کنترل احساسات\n"
    "• ساختن یک استراتژی شخصی قابل تکرار\n\n"
    "محتوا به‌صورت متن، عکس و ویدیو و مرحله‌به‌مرحله در اختیارتون قرار می‌گیره.\n\n"
    "برای ثبت‌نام از دکمه «💳 خرید و ثبت‌نام» استفاده کنید."
)

BUY_TEXT = (
    "💳 <b>خرید و ثبت‌نام دوره</b>\n\n"
    f"💵 هزینه دوره: <b>{PRICE_USD} دلار</b>\n"
    f"🌐 شبکه واریز: <b>{NETWORK_NAME}</b>\n"
    f"📥 آدرس کیف‌پول:\n<code>{WALLET_ADDRESS}</code>\n\n"
    "⚠️ لطفاً فقط از طریق شبکه TRC20 واریز کنید و آدرس رو با دقت کپی کنید؛ "
    "واریزی به شبکه اشتباه غیرقابل بازگشت است.\n\n"
    "بعد از واریز، روی دکمه زیر بزنید و عکس رسید واریزی رو ارسال کنید."
)

# ==================== دیتابیس ====================

def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(db_conn()) as conn:
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                status TEXT DEFAULT 'new',       -- new, pending, approved, rejected
                blocked INTEGER DEFAULT 0,       -- 1 اگر کاربر ربات رو بلاک کرده
                joined_at TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")

        c.execute(
            """CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                file_id TEXT,
                status TEXT DEFAULT 'pending',   -- pending, approved, rejected
                created_at TEXT
            )"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)")

        c.execute(
            """CREATE TABLE IF NOT EXISTS education_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT,  -- text, photo, video
                text TEXT,
                file_id TEXT,
                created_at TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS qna (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keywords TEXT,   -- کاما جدا شده
                answer TEXT
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
        conn.commit()


def upsert_user(user_id, username, first_name):
    with closing(db_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if c.fetchone() is None:
            c.execute(
                "INSERT INTO users (user_id, username, first_name, status, joined_at) VALUES (?,?,?,?,?)",
                (user_id, username, first_name, "new", datetime.now().isoformat()),
            )
        else:
            c.execute(
                "UPDATE users SET username=?, first_name=?, blocked=0 WHERE user_id=?",
                (username, first_name, user_id),
            )
        conn.commit()


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
                SUM(CASE WHEN blocked=1 THEN 1 ELSE 0 END) AS blocked
               FROM users"""
        ).fetchone()
        return {k: (row[k] or 0) for k in row.keys()}


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


def add_qna(keywords_csv, answer):
    with closing(db_conn()) as conn:
        conn.execute(
            "INSERT INTO qna (keywords, answer) VALUES (?,?)",
            (keywords_csv.strip().lower(), answer),
        )
        conn.commit()


def find_qna_answer(question_text):
    q = question_text.strip().lower()
    with closing(db_conn()) as conn:
        rows = conn.execute("SELECT keywords, answer FROM qna").fetchall()
    for r in rows:
        keywords = [k.strip() for k in (r["keywords"] or "").split(",") if k.strip()]
        if any(k in q for k in keywords):
            return r["answer"]
    return None


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


# ==================== ارسال امن (flood-safe) ====================

async def safe_send(bot, user_id, kind, **kwargs):
    """
    ارسال پیام با محافظت در برابر Flood control و کاربرانی که ربات را بلاک کرده‌اند.
    kind: 'message' | 'photo' | 'video'
    برمی‌گرداند True در صورت موفقیت.
    """
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
    sent = 0
    for uid in user_ids:
        ok = await safe_send(bot, uid, kind, **kwargs)
        if ok:
            sent += 1
        await asyncio.sleep(BROADCAST_DELAY)
    return sent


# ==================== کیبوردها ====================

def user_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📖 راهنما", "💳 خرید و ثبت‌نام"],
            ["📊 وضعیت من", "💬 مشاوره (سوال و جواب)"],
        ],
        resize_keyboard=True,
    )


def buy_inline_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ رسید واریزی را ارسال کردم", callback_data="send_receipt")]]
    )


def admin_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🧾 فیش‌ها", "📝 ارسال متن آموزش"],
            ["📢 پیام همگانی", "📊 آمار کاربران"],
            ["❓ آموزش سوال و جواب", "📥 سوالات بی‌پاسخ"],
            ["🔙 بازگشت به منوی عادی"],
        ],
        resize_keyboard=True,
    )


def receipt_decision_keyboard(receipt_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ تایید", callback_data=f"apprv_{receipt_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"rej_{receipt_id}"),
            ]
        ]
    )


def is_admin(user_id):
    return user_id in ADMIN_IDS


STATUS_LABELS = {
    "new": "🆕 هنوز ثبت‌نام نکردید",
    "pending": "⏳ رسید شما در انتظار بررسی است",
    "approved": "✅ اشتراک شما فعال است",
    "rejected": "❌ رسید قبلی رد شد — می‌توانید دوباره تلاش کنید",
}


# ==================== هندلرهای کاربر عادی ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    upsert_user(u.id, u.username, u.first_name)
    context.user_data.clear()
    await update.message.reply_text(
        f"سلام {u.first_name} 👋\nبه ربات آموزش ترید خوش اومدید.\n\n"
        "از دکمه‌های پایین استفاده کنید:",
        reply_markup=user_main_keyboard(),
    )


async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(GUIDE_TEXT, parse_mode=ParseMode.HTML)


async def show_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        BUY_TEXT, parse_mode=ParseMode.HTML, reply_markup=buy_inline_keyboard()
    )


async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    row = get_user(u.id)
    status = row["status"] if row else "new"
    await update.message.reply_text(f"وضعیت شما: {STATUS_LABELS.get(status, status)}")


async def send_receipt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_receipt"] = True
    await query.message.reply_text("لطفاً عکس رسید واریزی خودتون رو همینجا ارسال کنید 📸")


async def consult_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_question"] = True
    await update.message.reply_text(
        "🟢 حالت مشاوره فعال شد. سوالتون رو بنویسید؛ اگه جواب آماده نداشتم "
        "برای مدیر ارسال می‌شه."
    )


# ==================== عکس / ویدیو ====================

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user

    if is_admin(u.id) and context.user_data.get("awaiting_edu_content"):
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        add_education_content("photo", caption, file_id)
        n = await broadcast_to(
            context.bot, all_user_ids(status="approved"), "photo", photo=file_id, caption=caption or None
        )
        await update.message.reply_text(
            f"✅ عکس ثبت شد و برای {n} کاربر دارای اشتراک ارسال شد.\nبرای پایان /done را بزنید."
        )
        return

    if context.user_data.get("awaiting_receipt"):
        file_id = update.message.photo[-1].file_id
        receipt_id = add_receipt(u.id, file_id)
        set_user_status(u.id, "pending")
        context.user_data["awaiting_receipt"] = False

        await update.message.reply_text(
            "✅ رسید شما دریافت شد و برای بررسی به مدیریت ارسال شد.\n"
            "لطفاً منتظر تایید بمونید."
        )

        caption = (
            f"🧾 رسید جدید\n"
            f"کاربر: {u.first_name} (@{u.username or '-'})\n"
            f"آیدی: <code>{u.id}</code>\n"
            f"شماره رسید: {receipt_id}"
        )
        for admin_id in ADMIN_IDS:
            await safe_send(
                context.bot,
                admin_id,
                "photo",
                photo=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=receipt_decision_keyboard(receipt_id),
            )
        return

    await update.message.reply_text("برای ارسال عکس، اول از منو گزینه مربوطه رو انتخاب کنید.")


async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if is_admin(u.id) and context.user_data.get("awaiting_edu_content"):
        file_id = update.message.video.file_id
        caption = update.message.caption or ""
        add_education_content("video", caption, file_id)
        n = await broadcast_to(
            context.bot, all_user_ids(status="approved"), "video", video=file_id, caption=caption or None
        )
        await update.message.reply_text(
            f"✅ ویدیو ثبت شد و برای {n} کاربر دارای اشتراک ارسال شد.\nبرای پایان /done را بزنید."
        )


async def send_all_education_to_user(context, user_id):
    for row in all_education_content():
        if row["content_type"] == "text":
            await safe_send(context.bot, user_id, "message", text=row["text"])
        elif row["content_type"] == "photo":
            await safe_send(context.bot, user_id, "photo", photo=row["file_id"], caption=row["text"] or None)
        elif row["content_type"] == "video":
            await safe_send(context.bot, user_id, "video", video=row["file_id"], caption=row["text"] or None)
        await asyncio.sleep(BROADCAST_DELAY)


# ==================== روتر متن ====================

MAIN_MENU_TEXTS = {"📖 راهنما", "💳 خرید و ثبت‌نام", "📊 وضعیت من", "💬 مشاوره (سوال و جواب)"}
ADMIN_MENU_TEXTS = {
    "🧾 فیش‌ها", "📝 ارسال متن آموزش", "📢 پیام همگانی",
    "📊 آمار کاربران", "❓ آموزش سوال و جواب", "📥 سوالات بی‌پاسخ",
    "🔙 بازگشت به منوی عادی",
}


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    text = update.message.text.strip()

    # ---- دکمه‌های منوی اصلی (اولویت با دکمه‌ها، حتی اگر کاربر در یک حالت باشه) ----
    if text == "📖 راهنما":
        return await show_guide(update, context)
    if text == "💳 خرید و ثبت‌نام":
        return await show_buy(update, context)
    if text == "📊 وضعیت من":
        return await show_status(update, context)
    if text == "💬 مشاوره (سوال و جواب)":
        return await consult_button(update, context)

    # ---- دکمه‌های پنل مدیریت ----
    if is_admin(u.id):
        if text == "🔙 بازگشت به منوی عادی":
            context.user_data.clear()
            await update.message.reply_text("بازگشتید.", reply_markup=user_main_keyboard())
            return

        if text == "🧾 فیش‌ها":
            rows = pending_receipts()
            if not rows:
                await update.message.reply_text("در حال حاضر فیشی در انتظار بررسی نیست.")
                return
            for r in rows:
                await context.bot.send_photo(
                    chat_id=u.id,
                    photo=r["file_id"],
                    caption=f"فیش #{r['id']} — کاربر: {r['user_id']}",
                    reply_markup=receipt_decision_keyboard(r["id"]),
                )
            return

        if text == "📝 ارسال متن آموزش":
            context.user_data["awaiting_edu_content"] = True
            await update.message.reply_text(
                "📝 هر متن/عکس/ویدیو که بفرستید ذخیره و فوراً برای اعضای دارای اشتراک "
                "ارسال می‌شه (و برای اعضای بعدی هم باقی می‌مونه).\nبرای پایان /done را بفرستید."
            )
            return

        if text == "📢 پیام همگانی":
            context.user_data["awaiting_broadcast"] = True
            await update.message.reply_text("متن پیام همگانی رو بفرستید (برای همه کاربران ارسال می‌شه):")
            return

        if text == "📊 آمار کاربران":
            s = user_stats()
            msg = (
                "📊 <b>آمار کاربران</b>\n"
                f"👥 کل: {s['total']}\n"
                f"🆕 جدید: {s['new_']}\n"
                f"⏳ در انتظار بررسی: {s['pending']}\n"
                f"✅ دارای اشتراک: {s['approved']}\n"
                f"❌ رد شده: {s['rejected']}\n"
                f"🚫 بلاک‌کرده‌های ربات: {s['blocked']}\n"
                f"💰 درآمد تقریبی: {s['approved'] * PRICE_USD} دلار"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            return

        if text == "❓ آموزش سوال و جواب":
            context.user_data["awaiting_qna_keywords"] = True
            await update.message.reply_text(
                "کلمات کلیدی این سوال رو با کاما جدا و بفرست (مثلاً: حد ضرر, استاپ لاس, ریسک):"
            )
            return

        if text == "📥 سوالات بی‌پاسخ":
            rows = unanswered_questions()
            if not rows:
                await update.message.reply_text("سوال بی‌پاسخی وجود ندارد. 👍")
                return
            for r in rows:
                kb = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("✍️ پاسخ بده", callback_data=f"answer_{r['id']}")]]
                )
                await update.message.reply_text(
                    f"سوال #{r['id']} از کاربر {r['user_id']}:\n\n{r['question']}", reply_markup=kb
                )
            return

        # ---- حالت‌های در انتظار ورودی متن از ادمین ----
        if context.user_data.get("awaiting_edu_content"):
            add_education_content("text", text, None)
            n = await broadcast_to(context.bot, all_user_ids(status="approved"), "message", text=text)
            await update.message.reply_text(f"✅ متن ثبت و برای {n} کاربر ارسال شد.\nبرای پایان /done را بزنید.")
            return

        if context.user_data.get("awaiting_broadcast"):
            context.user_data["awaiting_broadcast"] = False
            n = await broadcast_to(context.bot, all_user_ids(), "message", text=text)
            await update.message.reply_text(f"📢 پیام به {n} کاربر ارسال شد.")
            return

        if context.user_data.get("awaiting_qna_keywords"):
            context.user_data["qna_keywords_temp"] = text
            context.user_data["awaiting_qna_keywords"] = False
            context.user_data["awaiting_qna_answer"] = True
            await update.message.reply_text("جواب مربوط به این کلمات کلیدی رو بفرست:")
            return

        if context.user_data.get("awaiting_qna_answer"):
            keywords = context.user_data.pop("qna_keywords_temp", "")
            context.user_data["awaiting_qna_answer"] = False
            add_qna(keywords, text)
            await update.message.reply_text(f"✅ ثبت شد.\nکلمات کلیدی: {keywords}")
            return

        reply_qid = context.user_data.get("awaiting_reply_to_qid")
        if reply_qid:
            context.user_data["awaiting_reply_to_qid"] = None
            row = answer_question(reply_qid, text)
            if row:
                await safe_send(
                    context.bot,
                    row["user_id"],
                    "message",
                    text=f"💬 پاسخ مشاور به سوال شما:\n\n«{row['question']}»\n\n{text}",
                )
                await update.message.reply_text("✅ پاسخ برای کاربر ارسال شد.")
            return

    # ---- حالت مشاوره کاربر عادی ----
    if context.user_data.get("awaiting_question"):
        answer = find_qna_answer(text)
        if answer:
            await update.message.reply_text(answer)
        else:
            add_pending_question(u.id, text)
            await update.message.reply_text(
                "سوال شما ثبت شد و برای مدیر ارسال شد؛ به‌زودی پاسخ داده می‌شه 🙏"
            )
            note = (
                f"❓ سوال بی‌پاسخ جدید\n"
                f"از: {u.first_name} (@{u.username or '-'})\nآیدی: <code>{u.id}</code>\n\n"
                f"سوال: {text}\n\nبرای پاسخ، از پنل مدیریت گزینه «سوالات بی‌پاسخ» را بزنید."
            )
            for admin_id in ADMIN_IDS:
                await safe_send(context.bot, admin_id, "message", text=note, parse_mode=ParseMode.HTML)
        return

    await update.message.reply_text("از دکمه‌های منو استفاده کنید 🙂", reply_markup=user_main_keyboard())


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        context.user_data["awaiting_edu_content"] = False
        await update.message.reply_text("✅ حالت افزودن محتوای آموزشی بسته شد.", reply_markup=admin_menu_keyboard())


# ==================== پنل مدیریت ====================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            set_user_status(receipt["user_id"], "approved")
            await safe_send(
                context.bot,
                receipt["user_id"],
                "message",
                text="🎉 پرداخت شما تایید شد! به دوره خوش اومدید.\nمحتوای آموزشی رو براتون ارسال می‌کنم...",
            )
            await send_all_education_to_user(context, receipt["user_id"])
            await query.edit_message_caption(caption=(query.message.caption or "") + "\n\n✅ تایید شد.")
        else:
            set_receipt_status(receipt_id, "rejected")
            set_user_status(receipt["user_id"], "rejected")
            await safe_send(
                context.bot,
                receipt["user_id"],
                "message",
                text="❌ رسید شما تایید نشد. از صحت واریزی مطمئن شوید و دوباره تلاش کنید "
                "یا با پشتیبانی تماس بگیرید.",
            )
            await query.edit_message_caption(caption=(query.message.caption or "") + "\n\n❌ رد شد.")
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
    app.add_handler(CallbackQueryHandler(admin_callback_router))

    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    logger.info("Bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
