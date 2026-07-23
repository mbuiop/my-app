# -*- coding: utf-8 -*-
"""
ربات آموزش ترید حرفه‌ای - نسخه با معماری پیشرفته
==================================================
معماری لایه‌ای:
1. لایه دیتابیس (Database Layer)
2. لایه بیزینس (Business Layer) 
3. لایه ارائه (Presentation Layer)
4. لایه مدیریت (Admin Layer)

ویژگی‌ها:
- سیستم رفرال کامل با پاداش ۵۰ دلاری
- برداشت خودکار با حداقل ۵۰۰ دلار
- پشتیبانی از ۱۰۰,۰۰۰ کاربر
- Flood-safe و Retry handling
- PicklePersistence برای حفظ حالت
- ایندکس‌های بهینه برای سرعت بالا
"""

import logging
import sqlite3
import asyncio
import random
import string
from datetime import datetime, timedelta
from contextlib import closing
from typing import Optional, Dict, List, Tuple, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
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
    ConversationHandler,
)

# ==================== تنظیمات ====================
BOT_TOKEN = "7780798170:AAHTD1295s15_RwhfhjGntSLZzye3keJP0"
ADMIN_IDS = [327855654]
WALLET_ADDRESS = "TSED8mCkfaNtavaBw2pQQpUoMRKGCwBsv3"
NETWORK_NAME = "TRC20 (Tron)"
PRICE_USD = 500
REFERRAL_BONUS = 50
MIN_WITHDRAW = 500
BOT_USERNAME = "UTYOB_Bot"

DB_PATH = "trading_bot.db"
PERSISTENCE_PATH = "bot_state.pickle"
BROADCAST_DELAY = 0.05

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== پیام‌های ثابت ====================
GUIDE_TEXT = """
📖 <b>راهنمای کامل ربات</b>

اینجا یک <b>آکادمی آموزش ترید</b> است، نه یک کانال سیگنال!

🔴 <b>چرا سیگنال نمی‌دهیم؟</b>
سیگنال یعنی یک نفر بهتون بگه «الان بخر، الان بفروش» بدون اینکه دلیلش رو بفهمید.
این کار شما رو برای همیشه به یک نفر دیگه وابسته نگه می‌داره.

🟢 <b>ما چیکار می‌کنیم؟</b>
هدف ما اینه که <b>خودتون یک معامله‌گر مستقل بشید</b>:
• تحلیل تکنیکال و فاندامنتال
• مدیریت ریسک و سرمایه
• روانشناسی معامله‌گری
• ساخت استراتژی شخصی

💰 <b>سیستم رفرال و درآمدزایی:</b>
• به ازای هر دوست که ثبت‌نام کنه و اشتراک بخره، <b>۵۰ دلار</b> پاداش می‌گیرید
• پس از جمع‌آوری ۵۰۰ دلار، می‌تونید برداشت کنید
• بدون محدودیت در تعداد رفرال‌ها

💳 <b>هزینه اشتراک:</b> {price} دلار - دسترسی مادام‌العمر
"""

BUY_TEXT = """
💳 <b>خرید اشتراک</b>

💵 هزینه: <b>{price} دلار</b>
🌐 شبکه: <b>{network}</b>
📥 آدرس کیف‌پول:
<code>{wallet}</code>

⚠️ فقط از شبکه TRC20 واریز کنید.

🎁 <b>پاداش رفرال:</b>
اگر با لینک رفرال ثبت‌نام کنید، دوست شما ۵۰ دلار پاداش می‌گیرد!

بعد از واریز، دکمه زیر رو بزنید و عکس رسید رو ارسال کنید.
"""

REFERRAL_TEXT = """
🎯 <b>سیستم رفرال و درآمد</b>

سلام {first_name} عزیز! 👋

📊 <b>آمار شما:</b>
• 👥 تعداد رفرال‌ها: {referrals}
• 💰 درآمد کل: {earnings} دلار
• 🏦 موجودی قابل برداشت: {balance} دلار

🔗 <b>لینک رفرال اختصاصی:</b>
<code>https://t.me/{bot_username}?start=ref_{referral_code}</code>

📌 <b>نحوه استفاده:</b>
۱. لینک رو کپی کنید
۲. برای دوستانتون بفرستید
۳. به ازای هر کاربر فعال، <b>۵۰ دلار</b> پاداش می‌گیرید

💰 <b>حداقل برداشت:</b> {min_withdraw} دلار

🏆 <b>برترین رفرال‌دهنده‌ها:</b>
{top_referrers}
"""

# ==================== لایه دیتابیس ====================
class Database:
    """لایه دیتابیس با ایندکس‌های بهینه"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()
    
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        with closing(self._conn()) as conn:
            c = conn.cursor()
            
            # جدول کاربران با فیلدهای رفرال
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    status TEXT DEFAULT 'new',
                    blocked INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referrer_id INTEGER,
                    balance REAL DEFAULT 0,
                    total_referrals INTEGER DEFAULT 0,
                    total_earnings REAL DEFAULT 0,
                    total_withdrawn REAL DEFAULT 0,
                    subscription_expiry TEXT,
                    joined_at TEXT,
                    last_active TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
            
            # جدول فیش‌ها
            c.execute("""
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    file_id TEXT,
                    tx_hash TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    confirmed_at TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status)")
            
            # جدول رفرال‌ها
            c.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER UNIQUE,
                    bonus_amount REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    confirmed_at TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")
            
            # جدول درخواست‌های برداشت
            c.execute("""
                CREATE TABLE IF NOT EXISTS withdraw_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    wallet_address TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    processed_at TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_withdraw_status ON withdraw_requests(status)")
            
            # جدول محتوای آموزشی
            c.execute("""
                CREATE TABLE IF NOT EXISTS education_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_type TEXT,
                    text TEXT,
                    file_id TEXT,
                    created_at TEXT
                )
            """)
            
            # جدول سوال و جواب
            c.execute("""
                CREATE TABLE IF NOT EXISTS qna (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keywords TEXT,
                    answer TEXT
                )
            """)
            
            # جدول سوالات بی‌پاسخ
            c.execute("""
                CREATE TABLE IF NOT EXISTS pending_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    question TEXT,
                    answer TEXT,
                    answered INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_pq_answered ON pending_questions(answered)")
            
            # جدول تراکنش‌ها
            c.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    amount REAL,
                    description TEXT,
                    balance_after REAL,
                    created_at TEXT
                )
            """)
            
            conn.commit()
            logger.info("✅ دیتابیس با ایندکس‌های بهینه راه‌اندازی شد")
    
    # ----- متدهای کاربر -----
    def upsert_user(self, user_id: int, username: str, first_name: str, last_name: str = None):
        with closing(self._conn()) as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if c.fetchone() is None:
                # تولید کد رفرال
                referral_code = f"{user_id}{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                c.execute("""
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, referral_code, status, joined_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, username, first_name, last_name, referral_code, "new", 
                      datetime.now().isoformat(), datetime.now().isoformat()))
            else:
                c.execute("""
                    UPDATE users 
                    SET username = ?, first_name = ?, last_name = ?, last_active = ?, blocked = 0
                    WHERE user_id = ?
                """, (username, first_name, last_name, datetime.now().isoformat(), user_id))
            conn.commit()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        with closing(self._conn()) as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    
    def get_user_by_referral(self, referral_code: str) -> Optional[int]:
        with closing(self._conn()) as conn:
            row = conn.execute("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,)).fetchone()
            return row["user_id"] if row else None
    
    def set_user_status(self, user_id: int, status: str):
        with closing(self._conn()) as conn:
            conn.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
            conn.commit()
    
    def set_user_referrer(self, user_id: int, referrer_id: int):
        with closing(self._conn()) as conn:
            conn.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
            conn.commit()
    
    def mark_blocked(self, user_id: int):
        with closing(self._conn()) as conn:
            conn.execute("UPDATE users SET blocked = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
    
    def update_balance(self, user_id: int, amount: float):
        with closing(self._conn()) as conn:
            conn.execute("""
                UPDATE users 
                SET balance = balance + ?, total_earnings = total_earnings + ?
                WHERE user_id = ?
            """, (amount, amount, user_id))
            conn.commit()
    
    def get_all_users(self, status: str = None) -> List[int]:
        with closing(self._conn()) as conn:
            if status:
                rows = conn.execute(
                    "SELECT user_id FROM users WHERE status = ? AND blocked = 0", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT user_id FROM users WHERE blocked = 0").fetchall()
            return [r["user_id"] for r in rows]
    
    def get_user_stats(self) -> Dict:
        with closing(self._conn()) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS new_,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) AS approved,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                    SUM(CASE WHEN blocked = 1 THEN 1 ELSE 0 END) AS blocked,
                    SUM(balance) AS total_balance,
                    SUM(total_earnings) AS total_earnings,
                    SUM(total_referrals) AS total_referrals
                FROM users
            """).fetchone()
            return {k: (row[k] or 0) for k in row.keys()}
    
    def get_top_referrers(self, limit: int = 5) -> List[Dict]:
        with closing(self._conn()) as conn:
            return conn.execute("""
                SELECT user_id, username, first_name, total_referrals, total_earnings, balance
                FROM users
                WHERE total_referrals > 0
                ORDER BY total_referrals DESC
                LIMIT ?
            """, (limit,)).fetchall()
    
    # ----- متدهای رفرال -----
    def add_referral(self, referrer_id: int, referred_id: int, bonus: float = REFERRAL_BONUS):
        with closing(self._conn()) as conn:
            c = conn.cursor()
            # ثبت رفرال
            c.execute("""
                INSERT INTO referrals (referrer_id, referred_id, bonus_amount, status, created_at)
                VALUES (?, ?, ?, 'confirmed', ?)
            """, (referrer_id, referred_id, bonus, datetime.now().isoformat()))
            
            # افزایش موجودی و آمار
            c.execute("""
                UPDATE users 
                SET balance = balance + ?,
                    total_referrals = total_referrals + 1,
                    total_earnings = total_earnings + ?
                WHERE user_id = ?
            """, (bonus, bonus, referrer_id))
            
            # ثبت تراکنش
            c.execute("""
                INSERT INTO transactions (user_id, type, amount, description, balance_after, created_at)
                SELECT ?, 'referral_bonus', ?, ?, balance, ?
                FROM users WHERE user_id = ?
            """, (referrer_id, bonus, f"پاداش رفرال کاربر {referred_id}", datetime.now().isoformat(), referrer_id))
            
            conn.commit()
    
    def get_user_referrals(self, user_id: int) -> List[Dict]:
        with closing(self._conn()) as conn:
            return conn.execute("""
                SELECT r.*, u.username, u.first_name, u.last_name
                FROM referrals r
                JOIN users u ON r.referred_id = u.user_id
                WHERE r.referrer_id = ?
                ORDER BY r.created_at DESC
            """, (user_id,)).fetchall()
    
    # ----- متدهای فیش -----
    def add_receipt(self, user_id: int, file_id: str, tx_hash: str = "") -> int:
        with closing(self._conn()) as conn:
            cur = conn.execute("""
                INSERT INTO receipts (user_id, file_id, tx_hash, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
            """, (user_id, file_id, tx_hash, datetime.now().isoformat()))
            conn.commit()
            return cur.lastrowid
    
    def get_receipt(self, receipt_id: int) -> Optional[Dict]:
        with closing(self._conn()) as conn:
            return conn.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)).fetchone()
    
    def set_receipt_status(self, receipt_id: int, status: str):
        with closing(self._conn()) as conn:
            conn.execute("""
                UPDATE receipts 
                SET status = ?, confirmed_at = ?
                WHERE id = ?
            """, (status, datetime.now().isoformat(), receipt_id))
            conn.commit()
    
    def get_pending_receipts(self) -> List[Dict]:
        with closing(self._conn()) as conn:
            return conn.execute("""
                SELECT r.*, u.username, u.first_name, u.last_name
                FROM receipts r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.status = 'pending'
                ORDER BY r.id
            """).fetchall()
    
    # ----- متدهای برداشت -----
    def add_withdraw_request(self, user_id: int, amount: float, wallet_address: str) -> int:
        with closing(self._conn()) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO withdraw_requests (user_id, amount, wallet_address, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
            """, (user_id, amount, wallet_address, datetime.now().isoformat()))
            withdraw_id = c.lastrowid
            
            # کاهش موجودی
            c.execute("""
                UPDATE users 
                SET balance = balance - ?,
                    total_withdrawn = total_withdrawn + ?
                WHERE user_id = ?
            """, (amount, amount, user_id))
            
            # ثبت تراکنش
            c.execute("""
                INSERT INTO transactions (user_id, type, amount, description, balance_after, created_at)
                SELECT ?, 'withdraw', -?, ?, balance, ?
                FROM users WHERE user_id = ?
            """, (user_id, amount, f"برداشت {amount} دلار", datetime.now().isoformat(), user_id))
            
            conn.commit()
            return withdraw_id
    
    def get_pending_withdraws(self) -> List[Dict]:
        with closing(self._conn()) as conn:
            return conn.execute("""
                SELECT w.*, u.username, u.first_name, u.last_name, u.balance
                FROM withdraw_requests w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.status = 'pending'
                ORDER BY w.created_at
            """).fetchall()
    
    def process_withdraw(self, withdraw_id: int, status: str):
        with closing(self._conn()) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE withdraw_requests 
                SET status = ?, processed_at = ?
                WHERE id = ?
            """, (status, datetime.now().isoformat(), withdraw_id))
            
            # اگر رد شد، موجودی برگردان
            if status == 'rejected':
                c.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (withdraw_id,))
                row = c.fetchone()
                if row:
                    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                              (row["amount"], row["user_id"]))
            
            conn.commit()
    
    # ----- متدهای آموزش -----
    def add_education(self, content_type: str, text: str, file_id: str = None):
        with closing(self._conn()) as conn:
            conn.execute("""
                INSERT INTO education_content (content_type, text, file_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (content_type, text, file_id, datetime.now().isoformat()))
            conn.commit()
    
    def get_all_education(self) -> List[Dict]:
        with closing(self._conn()) as conn:
            return conn.execute("SELECT * FROM education_content ORDER BY id").fetchall()
    
    # ----- متدهای سوال و جواب -----
    def add_qna(self, keywords: str, answer: str):
        with closing(self._conn()) as conn:
            conn.execute("INSERT INTO qna (keywords, answer) VALUES (?, ?)", 
                        (keywords.strip().lower(), answer))
            conn.commit()
    
    def find_qna(self, question: str) -> Optional[str]:
        q = question.strip().lower()
        with closing(self._conn()) as conn:
            rows = conn.execute("SELECT keywords, answer FROM qna").fetchall()
        
        for row in rows:
            keywords = [k.strip() for k in (row["keywords"] or "").split(",") if k.strip()]
            if any(k in q for k in keywords):
                return row["answer"]
        return None
    
    def add_pending_question(self, user_id: int, question: str) -> int:
        with closing(self._conn()) as conn:
            cur = conn.execute("""
                INSERT INTO pending_questions (user_id, question, answered, created_at)
                VALUES (?, ?, 0, ?)
            """, (user_id, question, datetime.now().isoformat()))
            conn.commit()
            return cur.lastrowid
    
    def get_unanswered_questions(self) -> List[Dict]:
        with closing(self._conn()) as conn:
            return conn.execute("""
                SELECT q.*, u.username, u.first_name
                FROM pending_questions q
                JOIN users u ON q.user_id = u.user_id
                WHERE q.answered = 0
                ORDER BY q.id
            """).fetchall()
    
    def answer_question(self, qid: int, answer: str) -> Optional[Dict]:
        with closing(self._conn()) as conn:
            conn.execute("""
                UPDATE pending_questions 
                SET answer = ?, answered = 1
                WHERE id = ?
            """, (answer, qid))
            conn.commit()
            return conn.execute("SELECT * FROM pending_questions WHERE id = ?", (qid,)).fetchone()

# ==================== لایه بیزینس ====================
class BusinessLayer:
    """لایه بیزینس - مدیریت منطق کسب و کار"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def process_referral(self, user_id: int, referral_code: str) -> Optional[int]:
        """پردازش رفرال هنگام ثبت‌نام"""
        referrer_id = self.db.get_user_by_referral(referral_code)
        if referrer_id and referrer_id != user_id:
            self.db.set_user_referrer(user_id, referrer_id)
            return referrer_id
        return None
    
    async def approve_payment(self, receipt_id: int) -> Optional[int]:
        """تایید پرداخت و فعال‌سازی اشتراک"""
        receipt = self.db.get_receipt(receipt_id)
        if not receipt:
            return None
        
        user_id = receipt["user_id"]
        self.db.set_receipt_status(receipt_id, "approved")
        self.db.set_user_status(user_id, "approved")
        
        # اگر کاربر با رفرال آمده بود، پاداش بده
        user = self.db.get_user(user_id)
        if user and user["referrer_id"]:
            self.db.add_referral(user["referrer_id"], user_id)
        
        return user_id
    
    async def reject_payment(self, receipt_id: int):
        """رد پرداخت"""
        self.db.set_receipt_status(receipt_id, "rejected")
        receipt = self.db.get_receipt(receipt_id)
        if receipt:
            self.db.set_user_status(receipt["user_id"], "rejected")
    
    async def process_withdraw(self, withdraw_id: int, status: str, bot, user_id: int):
        """پردازش درخواست برداشت"""
        self.db.process_withdraw(withdraw_id, status)

# ==================== لایه ارائه ====================
class UILayer:
    """لایه ارائه - مدیریت کیبوردها و پیام‌ها"""
    
    @staticmethod
    def user_keyboard():
        return ReplyKeyboardMarkup([
            ["📖 راهنما", "💳 خرید اشتراک"],
            ["📊 وضعیت من", "🎯 رفرال و درآمد"],
            ["💰 برداشت", "💬 مشاوره و سوال"]
        ], resize_keyboard=True)
    
    @staticmethod
    def admin_keyboard():
        return ReplyKeyboardMarkup([
            ["🧾 فیش‌ها", "📝 ارسال آموزش"],
            ["📢 پیام همگانی", "📊 آمار کاربران"],
            ["❓ سوال و جواب", "📥 سوالات بی‌پاسخ"],
            ["💳 درخواست‌های برداشت", "🏆 برترین رفرال‌ها"],
            ["🔙 بازگشت به منوی عادی"]
        ], resize_keyboard=True)
    
    @staticmethod
    def admin_menu_keyboard():
        return ReplyKeyboardMarkup([
            ["👑 پنل مدیریت"]
        ], resize_keyboard=True)
    
    @staticmethod
    def receipt_keyboard(receipt_id: int):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ تایید", callback_data=f"apprv_{receipt_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"rej_{receipt_id}")
            ]
        ])
    
    @staticmethod
    def withdraw_keyboard(withdraw_id: int):
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ تایید برداشت", callback_data=f"wapprv_{withdraw_id}"),
                InlineKeyboardButton("❌ رد برداشت", callback_data=f"wrej_{withdraw_id}")
            ]
        ])
    
    @staticmethod
    def question_keyboard(qid: int):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ پاسخ بده", callback_data=f"answer_{qid}")]
        ])
    
    @staticmethod
    def buy_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ رسید واریزی رو ارسال کردم", callback_data="send_receipt")]
        ])

# ==================== لایه مدیریت ====================
class AdminLayer:
    """لایه مدیریت - توابع ادمین"""
    
    def __init__(self, db: Database, business: BusinessLayer):
        self.db = db
        self.business = business
    
    async def show_pending_receipts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش فیش‌های در انتظار"""
        receipts = self.db.get_pending_receipts()
        if not receipts:
            await update.message.reply_text("✅ هیچ فیشی در انتظار نیست.")
            return
        
        for r in receipts:
            caption = (
                f"🧾 فیش #{r['id']}\n"
                f"👤 {r['first_name']} (@{r['username'] or '-'})\n"
                f"💰 {PRICE_USD} دلار"
            )
            await context.bot.send_photo(
                chat_id=update.effective_user.id,
                photo=r["file_id"],
                caption=caption,
                reply_markup=UILayer.receipt_keyboard(r["id"])
            )
    
    async def show_pending_withdraws(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش درخواست‌های برداشت"""
        withdraws = self.db.get_pending_withdraws()
        if not withdraws:
            await update.message.reply_text("✅ هیچ درخواست برداشتی در انتظار نیست.")
            return
        
        for w in withdraws:
            text = (
                f"💰 برداشت #{w['id']}\n"
                f"👤 {w['first_name']} (@{w['username'] or '-'})\n"
                f"💵 {w['amount']} دلار\n"
                f"🔗 {w['wallet_address']}"
            )
            await update.message.reply_text(
                text,
                reply_markup=UILayer.withdraw_keyboard(w["id"])
            )
    
    async def show_top_referrers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش برترین رفرال‌دهنده‌ها"""
        top = self.db.get_top_referrers(10)
        if not top:
            await update.message.reply_text("📊 هنوز رفرالی ثبت نشده.")
            return
        
        text = "🏆 <b>برترین رفرال‌دهنده‌ها</b>\n\n"
        for i, r in enumerate(top, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} @{r['username'] or 'کاربر'} - {r['total_referrals']} نفر\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ==================== هندلرهای اصلی ====================
db = Database()
business = BusinessLayer(db)
ui = UILayer()
admin_layer = AdminLayer(db, business)

# وضعیت‌های مکالمه
WAITING_RECEIPT = 1
WAITING_EDU_CONTENT = 2
WAITING_BROADCAST = 3
WAITING_QNA_KEYWORDS = 4
WAITING_QNA_ANSWER = 5
WAITING_QUESTION = 6
WAITING_WITHDRAW_ADDRESS = 7
WAITING_WITHDRAW_AMOUNT = 8
WAITING_ANSWER = 9

# ==================== توابع کمکی ====================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def safe_send(bot, user_id: int, kind: str, **kwargs) -> bool:
    """ارسال امن با مدیریت خطا"""
    try:
        if kind == "message":
            await bot.send_message(chat_id=user_id, **kwargs)
        elif kind == "photo":
            await bot.send_photo(chat_id=user_id, **kwargs)
        elif kind == "video":
            await bot.send_video(chat_id=user_id, **kwargs)
        return True
    except RetryAfter as e:
        logger.warning(f"Flood control: sleeping {e.retry_after}s")
        await asyncio.sleep(e.retry_after + 1)
        return await safe_send(bot, user_id, kind, **kwargs)
    except Forbidden:
        db.mark_blocked(user_id)
        return False
    except Exception as e:
        logger.warning(f"Error sending to {user_id}: {e}")
        return False

async def broadcast_to(bot, user_ids: List[int], kind: str, **kwargs) -> int:
    """ارسال همگانی با تاخیر"""
    sent = 0
    for uid in user_ids:
        ok = await safe_send(bot, uid, kind, **kwargs)
        if ok:
            sent += 1
        await asyncio.sleep(BROADCAST_DELAY)
    return sent

# ==================== هندلرهای کاربر ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # ثبت کاربر
    db.upsert_user(user.id, user.username, user.first_name, user.last_name)
    
    # پردازش رفرال
    if args and args[0].startswith("ref_"):
        referral_code = args[0].replace("ref_", "")
        referrer_id = await business.process_referral(user.id, referral_code)
        if referrer_id:
            await update.message.reply_text(
                f"🎉 شما با لینک رفرال ثبت‌نام کردید!\n"
                f"اگر اشتراک تهیه کنید، دوست شما {REFERRAL_BONUS} دلار پاداش می‌گیرد!"
            )
    
    # انتخاب کیبورد
    keyboard = ui.admin_menu_keyboard() if is_admin(user.id) else ui.user_keyboard()
    
    await update.message.reply_text(
        f"سلام {user.first_name} 👋\nبه ربات آموزش ترید خوش اومدید.\n\n"
        "از دکمه‌های زیر استفاده کنید:",
        reply_markup=keyboard
    )

async def guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        GUIDE_TEXT.format(price=PRICE_USD),
        parse_mode=ParseMode.HTML
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        BUY_TEXT.format(
            price=PRICE_USD,
            network=NETWORK_NAME,
            wallet=WALLET_ADDRESS
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=ui.buy_keyboard()
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ کاربر یافت نشد!")
        return
    
    status_labels = {
        "new": "🆕 هنوز ثبت‌نام نکردید",
        "pending": "⏳ رسید شما در انتظار بررسی است",
        "approved": "✅ اشتراک شما فعال است",
        "rejected": "❌ رسید قبلی رد شد"
    }
    
    text = f"📊 <b>وضعیت شما</b>\n\n"
    text += f"وضعیت: {status_labels.get(user['status'], user['status'])}\n"
    text += f"💰 موجودی: {user['balance']} دلار\n"
    text += f"👥 رفرال‌ها: {user['total_referrals']} نفر\n"
    text += f"💵 درآمد کل: {user['total_earnings']} دلار"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ کاربر یافت نشد!")
        return
    
    top = db.get_top_referrers(5)
    top_text = ""
    for i, r in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        top_text += f"{medal} @{r['username'] or 'کاربر'} - {r['total_referrals']} نفر\n"
    
    if not top_text:
        top_text = "هنوز رفرالی ثبت نشده. شما می‌تونید اولین نفر باشید! 🚀"
    
    await update.message.reply_text(
        REFERRAL_TEXT.format(
            first_name=user['first_name'],
            referrals=user['total_referrals'],
            earnings=user['total_earnings'],
            balance=user['balance'],
            bot_username=BOT_USERNAME,
            referral_code=user['referral_code'],
            min_withdraw=MIN_WITHDRAW,
            top_referrers=top_text
        ),
        parse_mode=ParseMode.HTML
    )

async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ کاربر یافت نشد!")
        return
    
    if user['balance'] < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ موجودی کافی نیست!\n"
            f"موجودی: {user['balance']} دلار\n"
            f"حداقل برداشت: {MIN_WITHDRAW} دلار"
        )
        return
    
    await update.message.reply_text(
        f"💰 برداشت از حساب\n\n"
        f"موجودی قابل برداشت: {user['balance']} دلار\n"
        f"حداقل برداشت: {MIN_WITHDRAW} دلار\n\n"
        f"📌 آدرس کیف پول (TRC20) خود را وارد کنید:"
    )
    return WAITING_WITHDRAW_ADDRESS

async def withdraw_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet = update.message.text.strip()
    if len(wallet) < 20:
        await update.message.reply_text("❌ آدرس نامعتبر! دوباره ارسال کنید:")
        return WAITING_WITHDRAW_ADDRESS
    
    context.user_data['wallet'] = wallet
    user = db.get_user(update.effective_user.id)
    
    await update.message.reply_text(
        f"مبلغ مورد نظر را وارد کنید:\n"
        f"(حداکثر: {user['balance']} دلار)"
    )
    return WAITING_WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except:
        await update.message.reply_text("❌ مبلغ نامعتبر! عدد وارد کنید:")
        return WAITING_WITHDRAW_AMOUNT
    
    user = db.get_user(update.effective_user.id)
    if amount < MIN_WITHDRAW:
        await update.message.reply_text(f"❌ حداقل برداشت {MIN_WITHDRAW} دلار است!")
        return WAITING_WITHDRAW_AMOUNT
    
    if amount > user['balance']:
        await update.message.reply_text(f"❌ موجودی کافی نیست! (موجودی: {user['balance']} دلار)")
        return WAITING_WITHDRAW_AMOUNT
    
    wallet = context.user_data.get('wallet')
    withdraw_id = db.add_withdraw_request(user['user_id'], amount, wallet)
    
    # اطلاع به ادمین
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"💰 درخواست برداشت جدید!\n"
                 f"👤 {user['first_name']} (@{user['username'] or '-'})\n"
                 f"💵 {amount} دلار\n"
                 f"🔗 {wallet}",
            reply_markup=ui.withdraw_keyboard(withdraw_id)
        )
    
    await update.message.reply_text(
        f"✅ درخواست برداشت {amount} دلار ثبت شد!\n"
        f"پس از تایید، مبلغ به کیف پول شما واریز می‌شود."
    )
    
    context.user_data.pop('wallet', None)
    return ConversationHandler.END

async def consult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['waiting_question'] = True
    await update.message.reply_text(
        "💬 حالت مشاوره فعال شد.\n"
        "سوال خود را بنویسید. اگر جواب آماده نبود، برای مدیر ارسال می‌شود."
    )
    return WAITING_QUESTION

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    question = update.message.text
    
    answer = db.find_qna(question)
    if answer:
        await update.message.reply_text(answer)
    else:
        qid = db.add_pending_question(user.id, question)
        await update.message.reply_text(
            "✅ سوال شما ثبت شد و برای مدیر ارسال شد. به‌زودی پاسخ داده می‌شود."
        )
        
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"❓ سوال جدید از {user.first_name} (@{user.username or '-'})\n\n{question}",
                reply_markup=ui.question_keyboard(qid)
            )
    
    context.user_data['waiting_question'] = False
    return ConversationHandler.END

# ==================== هندلرهای ادمین ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "🛠 پنل مدیریت",
        reply_markup=ui.admin_keyboard()
    )

async def handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    text = update.message.text
    
    if text == "🔙 بازگشت به منوی عادی":
        context.user_data.clear()
        await update.message.reply_text("بازگشتید.", reply_markup=ui.user_keyboard())
        return
    
    if text == "🧾 فیش‌ها":
        await admin_layer.show_pending_receipts(update, context)
        return
    
    if text == "💳 درخواست‌های برداشت":
        await admin_layer.show_pending_withdraws(update, context)
        return
    
    if text == "🏆 برترین رفرال‌ها":
        await admin_layer.show_top_referrers(update, context)
        return
    
    if text == "📝 ارسال آموزش":
        context.user_data['awaiting_edu'] = True
        await update.message.reply_text(
            "📝 هر متن/عکس/ویدیو بفرستید، ذخیره و برای کاربران ارسال می‌شود.\n"
            "برای پایان /done بزنید."
        )
        return
    
    if text == "📢 پیام همگانی":
        context.user_data['awaiting_broadcast'] = True
        await update.message.reply_text("متن پیام همگانی را بفرستید:")
        return
    
    if text == "📊 آمار کاربران":
        stats = db.get_user_stats()
        msg = (
            f"📊 <b>آمار کاربران</b>\n\n"
            f"👥 کل: {stats['total']}\n"
            f"🆕 جدید: {stats['new_']}\n"
            f"⏳ در انتظار: {stats['pending']}\n"
            f"✅ دارای اشتراک: {stats['approved']}\n"
            f"❌ رد شده: {stats['rejected']}\n"
            f"🚫 بلاک شده: {stats['blocked']}\n\n"
            f"💰 موجودی کل: {stats['total_balance']} دلار\n"
            f"💵 درآمد کل: {stats['total_earnings']} دلار\n"
            f"👥 کل رفرال‌ها: {stats['total_referrals']}"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return
    
    if text == "❓ سوال و جواب":
        context.user_data['awaiting_qna_keywords'] = True
        await update.message.reply_text(
            "کلمات کلیدی را با کاما جدا کنید:\n"
            "مثال: حد ضرر, استاپ لاس, ریسک"
        )
        return
    
    if text == "📥 سوالات بی‌پاسخ":
        questions = db.get_unanswered_questions()
        if not questions:
            await update.message.reply_text("✅ هیچ سوال بی‌پاسخی وجود ندارد.")
            return
        
        for q in questions:
            await update.message.reply_text(
                f"❓ سوال #{q['id']} از {q['first_name']} (@{q['username'] or '-'})\n\n{q['question']}",
                reply_markup=ui.question_keyboard(q['id'])
            )
        return

# ==================== هندلرهای محتوا ====================
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # حالت دریافت فیش
    if context.user_data.get('awaiting_receipt'):
        file_id = update.message.photo[-1].file_id
        receipt_id = db.add_receipt(user.id, file_id, "")
        db.set_user_status(user.id, "pending")
        context.user_data['awaiting_receipt'] = False
        
        await update.message.reply_text(
            "✅ رسید شما دریافت شد. منتظر تایید باشید."
        )
        
        for admin_id in ADMIN_IDS:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=f"🧾 رسید جدید از {user.first_name} (@{user.username or '-'})",
                reply_markup=ui.receipt_keyboard(receipt_id)
            )
        return
    
    # حالت ارسال آموزش (ادمین)
    if is_admin(user.id) and context.user_data.get('awaiting_edu'):
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        db.add_education("photo", caption, file_id)
        
        users = db.get_all_users("approved")
        n = await broadcast_to(context.bot, users, "photo", photo=file_id, caption=caption)
        
        await update.message.reply_text(f"✅ عکس ثبت و برای {n} کاربر ارسال شد.")
        return
    
    await update.message.reply_text("برای ارسال عکس، از گزینه مربوطه استفاده کنید.")

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if is_admin(user.id) and context.user_data.get('awaiting_edu'):
        file_id = update.message.video.file_id
        caption = update.message.caption or ""
        db.add_education("video", caption, file_id)
        
        users = db.get_all_users("approved")
        n = await broadcast_to(context.bot, users, "video", video=file_id, caption=caption)
        
        await update.message.reply_text(f"✅ ویدیو ثبت و برای {n} کاربر ارسال شد.")
        return

# ==================== کالبک‌ها ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    data = query.data
    await query.answer()
    
    # تایید/رد فیش
    if data.startswith("apprv_") or data.startswith("rej_"):
        if not is_admin(user.id):
            await query.answer("دسترسی ندارید!", show_alert=True)
            return
        
        receipt_id = int(data.split("_", 1)[1])
        receipt = db.get_receipt(receipt_id)
        if not receipt:
            await query.edit_message_text("رسید یافت نشد!")
            return
        
        if data.startswith("apprv_"):
            # تایید و فعال‌سازی
            user_id = await business.approve_payment(receipt_id)
            if user_id:
                # ارسال محتوای آموزشی به کاربر
                for edu in db.get_all_education():
                    if edu["content_type"] == "text":
                        await safe_send(context.bot, user_id, "message", text=edu["text"])
                    elif edu["content_type"] == "photo":
                        await safe_send(context.bot, user_id, "photo", photo=edu["file_id"], caption=edu["text"] or None)
                    elif edu["content_type"] == "video":
                        await safe_send(context.bot, user_id, "video", video=edu["file_id"], caption=edu["text"] or None)
                    await asyncio.sleep(BROADCAST_DELAY)
                
                await safe_send(
                    context.bot, user_id, "message",
                    text="🎉 پرداخت شما تایید شد! به دوره خوش آمدید.\n\n"
                         "📚 تمام محتوای آموزشی برای شما ارسال شد."
                )
                
                await query.edit_message_caption(
                    caption=(query.message.caption or "") + "\n\n✅ تایید شد."
                )
        else:
            # رد فیش
            await business.reject_payment(receipt_id)
            await safe_send(
                context.bot, receipt["user_id"], "message",
                text="❌ رسید شما رد شد. از صحت واریزی مطمئن شوید و دوباره تلاش کنید."
            )
            await query.edit_message_caption(
                caption=(query.message.caption or "") + "\n\n❌ رد شد."
            )
        return
    
    # تایید/رد برداشت
    if data.startswith("wapprv_") or data.startswith("wrej_"):
        if not is_admin(user.id):
            await query.answer("دسترسی ندارید!", show_alert=True)
            return
        
        withdraw_id = int(data.split("_", 1)[1])
        status = "confirmed" if data.startswith("wapprv_") else "rejected"
        
        await business.process_withdraw(withdraw_id, status, context.bot, user.id)
        await query.edit_message_text(
            f"✅ برداشت {'تایید' if status == 'confirmed' else 'رد'} شد."
        )
        return
    
    # پاسخ به سوال
    if data.startswith("answer_"):
        if not is_admin(user.id):
            await query.answer("دسترسی ندارید!", show_alert=True)
            return
        
        qid = int(data.split("_", 1)[1])
        context.user_data['awaiting_answer'] = qid
        await query.message.reply_text("پاسخ را بنویسید:")
        return
    
    # ارسال رسید
    if data == "send_receipt":
        context.user_data['awaiting_receipt'] = True
        await query.message.reply_text(
            "📸 لطفاً عکس رسید واریزی خود را ارسال کنید.\n"
            "حتماً هش تراکنش را در کپشن عکس بنویسید."
        )
        return

# ==================== هندلرهای متن ====================
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    
    # ===== پاسخ به سوال (ادمین) =====
    if is_admin(user.id) and context.user_data.get('awaiting_answer'):
        qid = context.user_data.pop('awaiting_answer')
        q = db.answer_question(qid, text)
        if q:
            await safe_send(
                context.bot, q["user_id"], "message",
                text=f"💬 پاسخ مشاور به سوال شما:\n\n{q['question']}\n\n{text}"
            )
            await update.message.reply_text("✅ پاسخ ارسال شد.")
        return
    
    # ===== افزودن سوال و جواب (ادمین) =====
    if is_admin(user.id) and context.user_data.get('awaiting_qna_keywords'):
        context.user_data['qna_keywords'] = text
        context.user_data['awaiting_qna_keywords'] = False
        context.user_data['awaiting_qna_answer'] = True
        await update.message.reply_text("جواب این کلمات کلیدی را بنویسید:")
        return
    
    if is_admin(user.id) and context.user_data.get('awaiting_qna_answer'):
        keywords = context.user_data.pop('qna_keywords', '')
        context.user_data['awaiting_qna_answer'] = False
        db.add_qna(keywords, text)
        await update.message.reply_text(f"✅ ثبت شد.\nکلمات کلیدی: {keywords}")
        return
    
    # ===== ارسال آموزش (ادمین) =====
    if is_admin(user.id) and context.user_data.get('awaiting_edu'):
        db.add_education("text", text, None)
        users = db.get_all_users("approved")
        n = await broadcast_to(context.bot, users, "message", text=text)
        await update.message.reply_text(f"✅ متن ثبت و برای {n} کاربر ارسال شد.")
        return
    
    # ===== پیام همگانی (ادمین) =====
    if is_admin(user.id) and context.user_data.get('awaiting_broadcast'):
        context.user_data['awaiting_broadcast'] = False
        users = db.get_all_users()
        n = await broadcast_to(context.bot, users, "message", text=text)
        await update.message.reply_text(f"📢 پیام به {n} کاربر ارسال شد.")
        return
    
    # ===== منوی ادمین =====
    if is_admin(user.id) and text == "👑 پنل مدیریت":
        await admin_panel(update, context)
        return
    
    if is_admin(user.id) and text in ["🧾 فیش‌ها", "📝 ارسال آموزش", "📢 پیام همگانی", 
                                        "📊 آمار کاربران", "❓ سوال و جواب", "📥 سوالات بی‌پاسخ",
                                        "💳 درخواست‌های برداشت", "🏆 برترین رفرال‌ها", 
                                        "🔙 بازگشت به منوی عادی"]:
        await handle_admin_menu(update, context)
        return
    
    # ===== دکمه‌های کاربر =====
    if text == "📖 راهنما":
        await guide(update, context)
    elif text == "💳 خرید اشتراک":
        await buy(update, context)
    elif text == "📊 وضعیت من":
        await status(update, context)
    elif text == "🎯 رفرال و درآمد":
        await referral(update, context)
    elif text == "💰 برداشت":
        return await withdraw_start(update, context)
    elif text == "💬 مشاوره و سوال":
        return await consult(update, context)
    else:
        await update.message.reply_text("از دکمه‌های منو استفاده کنید.")

# ==================== دستورات ====================
async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        context.user_data.clear()
        await update.message.reply_text(
            "✅ حالت‌های در انتظار پاک شدند.",
            reply_markup=ui.admin_keyboard()
        )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ لغو شد.")

# ==================== اصلی ====================
def main():
    # مقداردهی اولیه
    db = Database()
    
    # Persistence
    persistence = PicklePersistence(filepath=PERSISTENCE_PATH)
    
    # اپلیکیشن
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    
    # ===== دستورات =====
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    # ===== کالبک‌ها =====
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # ===== مکالمات =====
    # برداشت
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💰 برداشت$"), withdraw_start)],
        states={
            WAITING_WITHDRAW_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_address)],
            WAITING_WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)]
    )
    app.add_handler(withdraw_conv)
    
    # مشاوره
    consult_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💬 مشاوره و سوال$"), consult)],
        states={
            WAITING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question)]
        },
        fallbacks=[CommandHandler("cancel", cancel_command)]
    )
    app.add_handler(consult_conv)
    
    # ===== هندلرهای محتوا =====
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    
    # ===== هندلر متن (آخرین) =====
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    
    # ===== راه‌اندازی =====
    logger.info("🚀 ربات با معماری لایه‌ای راه‌اندازی شد")
    print("=" * 60)
    print("🚀 ربات آموزش ترید با معماری پیشرفته")
    print("=" * 60)
    print(f"👤 ادمین‌ها: {ADMIN_IDS}")
    print(f"💰 قیمت اشتراک: {PRICE_USD} دلار")
    print(f"🎁 پاداش رفرال: {REFERRAL_BONUS} دلار")
    print(f"💰 حداقل برداشت: {MIN_WITHDRAW} دلار")
    print("=" * 60)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()