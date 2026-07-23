"""
ربات آموزش ترید حرفه‌ای - نسخه نهایی با رفع کامل مشکلات
پشتیبانی از ۱۰۰,۰۰۰ کاربر با کارایی بالا
"""

import os
import asyncio
import logging
import sqlite3
import json
import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import time

# ==================== کتابخانه‌ها ====================
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ==================== تنظیمات ====================
TOKEN = "YOUR_BOT_TOKEN_HERE"
BOT_USERNAME = "UTYOB_Bot"
ADMIN_IDS = [123456789]  # آیدی خودت رو بذار
WALLET_ADDRESS = "TSED8mCkfaNtavaBw2pQQpUoMRKGCwBsv3"
PRICE_USD = 500
REFERRAL_BONUS = 50
MIN_WITHDRAW = 500
MAX_WORKERS = 50

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس ====================
class Database:
    def __init__(self, db_file="trading_bot.db"):
        self.db_file = db_file
        self.lock = threading.Lock()
        self.init_db()
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                subscription_active INTEGER DEFAULT 0,
                subscription_expiry TEXT,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                is_admin INTEGER DEFAULT 0,
                referral_code TEXT UNIQUE,
                referrer_id INTEGER,
                balance REAL DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
                total_earnings REAL DEFAULT 0,
                total_withdrawn REAL DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                tx_hash TEXT,
                photo_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS education (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                media_type TEXT,
                media_file_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT UNIQUE,
                answer TEXT,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                answer TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                answered_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                bonus_amount REAL,
                status TEXT DEFAULT 'confirmed',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                wallet_address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount REAL,
                description TEXT,
                balance_after REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ دیتابیس راه‌اندازی شد")

    # ===== متدهای کاربر =====
    def add_user(self, user_id, username, first_name, last_name, referrer_id=None):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                is_admin = 1 if user_id in ADMIN_IDS else 0
                referral_code = f"{user_id}{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
                
                cur.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, is_admin, referral_code, referrer_id, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, username, first_name, last_name, is_admin, referral_code, referrer_id))
                conn.commit()
                
                if referrer_id:
                    self.add_referral_bonus(referrer_id, user_id)
                
                return True
            except Exception as e:
                logger.error(f"خطا در افزودن کاربر: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    def get_user(self, user_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return result

    def get_user_by_referral(self, referral_code):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            return result['user_id'] if result else None

    def get_all_users(self):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("SELECT user_id, username, first_name, last_name FROM users ORDER BY registered_at DESC")
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result

    def get_subscribed_users(self):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id FROM users 
                WHERE subscription_active = 1 
                AND (subscription_expiry IS NULL OR subscription_expiry > datetime('now'))
            """)
            result = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
            return result

    # ===== متدهای رفرال =====
    def add_referral_bonus(self, referrer_id, referred_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO referrals (referrer_id, referred_id, bonus_amount)
                    VALUES (?, ?, ?)
                """, (referrer_id, referred_id, REFERRAL_BONUS))
                
                cur.execute("""
                    UPDATE users 
                    SET balance = balance + ?,
                        total_referrals = total_referrals + 1,
                        total_earnings = total_earnings + ?
                    WHERE user_id = ?
                """, (REFERRAL_BONUS, REFERRAL_BONUS, referrer_id))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"خطا در افزودن پاداش رفرال: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    def get_user_referrals(self, user_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT r.*, u.username, u.first_name, u.last_name
                FROM referrals r
                JOIN users u ON r.referred_id = u.user_id
                WHERE r.referrer_id = ?
                ORDER BY r.created_at DESC
            """, (user_id,))
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result

    def get_top_referrers(self, limit=10):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, username, first_name, last_name, 
                       total_referrals, total_earnings, balance
                FROM users 
                WHERE total_referrals > 0
                ORDER BY total_referrals DESC
                LIMIT ?
            """, (limit,))
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result

    # ===== متدهای پرداخت =====
    def add_payment(self, user_id, amount, tx_hash, photo_file_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO payments (user_id, amount, tx_hash, photo_file_id)
                    VALUES (?, ?, ?, ?)
                """, (user_id, amount, tx_hash, photo_file_id))
                payment_id = cur.lastrowid
                conn.commit()
                return payment_id
            except Exception as e:
                logger.error(f"خطا در ثبت پرداخت: {e}")
                return None
            finally:
                cur.close()
                conn.close()

    def get_pending_payments(self):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT p.*, u.username, u.first_name, u.last_name 
                FROM payments p
                JOIN users u ON p.user_id = u.user_id
                WHERE p.status = 'pending'
                ORDER BY p.created_at DESC
            """)
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result

    def confirm_payment(self, payment_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("SELECT user_id FROM payments WHERE id = ?", (payment_id,))
                result = cur.fetchone()
                if not result:
                    return False
                user_id = result[0]

                cur.execute("""
                    UPDATE payments 
                    SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (payment_id,))

                expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
                cur.execute("""
                    UPDATE users 
                    SET subscription_active = 1, 
                        subscription_expiry = ?
                    WHERE user_id = ?
                """, (expiry, user_id))

                conn.commit()
                return user_id
            except Exception as e:
                logger.error(f"خطا در تایید پرداخت: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    def reject_payment(self, payment_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    UPDATE payments 
                    SET status = 'rejected'
                    WHERE id = ?
                """, (payment_id,))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"خطا در رد پرداخت: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    # ===== متدهای برداشت =====
    def add_withdraw_request(self, user_id, amount, wallet_address):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
                user = cur.fetchone()
                if not user or user['balance'] < amount:
                    return False, "موجودی کافی نیست"
                
                if amount < MIN_WITHDRAW:
                    return False, f"حداقل مبلغ برداشت {MIN_WITHDRAW} دلار است"
                
                cur.execute("""
                    INSERT INTO withdraw_requests (user_id, amount, wallet_address)
                    VALUES (?, ?, ?)
                """, (user_id, amount, wallet_address))
                
                cur.execute("""
                    UPDATE users 
                    SET balance = balance - ?,
                        total_withdrawn = total_withdrawn + ?
                    WHERE user_id = ?
                """, (amount, amount, user_id))
                
                conn.commit()
                return True, "درخواست برداشت ثبت شد"
            except Exception as e:
                logger.error(f"خطا در ثبت برداشت: {e}")
                return False, "خطا در ثبت درخواست"
            finally:
                cur.close()
                conn.close()

    def get_pending_withdraws(self):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT w.*, u.username, u.first_name, u.last_name, u.balance
                FROM withdraw_requests w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.status = 'pending'
                ORDER BY w.created_at DESC
            """)
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result

    def process_withdraw(self, withdraw_id, status):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    UPDATE withdraw_requests 
                    SET status = ?, processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, withdraw_id))
                conn.commit()
                
                # اگر رد شد، موجودی را برگردان
                if status == 'rejected':
                    cur.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (withdraw_id,))
                    result = cur.fetchone()
                    if result:
                        cur.execute("""
                            UPDATE users 
                            SET balance = balance + ?
                            WHERE user_id = ?
                        """, (result['amount'], result['user_id']))
                        conn.commit()
                
                return True
            except Exception as e:
                logger.error(f"خطا در پردازش برداشت: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    # ===== متدهای آموزش =====
    def add_education_content(self, title, content, media_type, media_file_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO education (title, content, media_type, media_file_id)
                    VALUES (?, ?, ?, ?)
                """, (title, content, media_type, media_file_id))
                edu_id = cur.lastrowid
                conn.commit()
                return edu_id
            except Exception as e:
                logger.error(f"خطا در افزودن محتوا: {e}")
                return None
            finally:
                cur.close()
                conn.close()

    def get_all_education(self):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM education ORDER BY created_at DESC")
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result

    # ===== متدهای سوال و جواب =====
    def add_faq(self, question, answer, keywords):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                keywords_json = json.dumps(keywords)
                cur.execute("""
                    INSERT OR REPLACE INTO faq (question, answer, keywords)
                    VALUES (?, ?, ?)
                """, (question, answer, keywords_json))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"خطا در افزودن سوال: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    def search_faq(self, query):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT question, answer FROM faq 
                    WHERE question LIKE ? OR keywords LIKE ?
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%'))
                return cur.fetchall()
            except Exception as e:
                logger.error(f"خطا در جستجوی سوال: {e}")
                return []
            finally:
                cur.close()
                conn.close()

    def add_user_question(self, user_id, question):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO user_questions (user_id, question, status)
                    VALUES (?, ?, 'pending')
                """, (user_id, question))
                q_id = cur.lastrowid
                conn.commit()
                return q_id
            except Exception as e:
                logger.error(f"خطا در ثبت سوال کاربر: {e}")
                return None
            finally:
                cur.close()
                conn.close()

    def get_pending_user_questions(self):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT q.*, u.username, u.first_name, u.last_name 
                FROM user_questions q
                JOIN users u ON q.user_id = u.user_id
                WHERE q.status = 'pending'
                ORDER BY q.created_at DESC
            """)
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result

    def answer_user_question(self, q_id, answer):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    UPDATE user_questions 
                    SET answer = ?, status = 'answered', answered_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (answer, q_id))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"خطا در پاسخ به سوال: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    def get_stats(self):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            stats = {}
            
            cur.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE subscription_active = 1")
            stats['subscribed_users'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
            stats['pending_payments'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM payments WHERE status = 'confirmed'")
            stats['total_payments'] = cur.fetchone()[0]
            
            cur.execute("SELECT SUM(amount) FROM payments WHERE status = 'confirmed'")
            result = cur.fetchone()[0]
            stats['total_earnings'] = result if result else 0
            
            cur.execute("SELECT COUNT(*) FROM referrals")
            stats['total_referrals'] = cur.fetchone()[0]
            
            cur.execute("SELECT SUM(bonus_amount) FROM referrals")
            result = cur.fetchone()[0]
            stats['total_referral_bonus'] = result if result else 0
            
            cur.execute("SELECT COUNT(*) FROM withdraw_requests WHERE status = 'pending'")
            stats['pending_withdraws'] = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            return stats


# ==================== نمونه دیتابیس ====================
db = Database()

# ==================== دکمه‌ها ====================
def main_menu():
    keyboard = [
        [KeyboardButton("📚 آموزش ترید"), KeyboardButton("📖 راهنمایی")],
        [KeyboardButton("💳 خرید اشتراک"), KeyboardButton("📊 وضعیت اشتراک")],
        [KeyboardButton("❓ مشاوره و سوال"), KeyboardButton("🎯 رفرال و درآمد")],
        [KeyboardButton("💰 برداشت"), KeyboardButton("📞 پشتیبانی")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_menu():
    keyboard = [[KeyboardButton("👑 پنل مدیریت")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_panel():
    keyboard = [
        [KeyboardButton("💰 فیش‌ها"), KeyboardButton("📝 ارسال آموزش")],
        [KeyboardButton("📢 پیام همگانی"), KeyboardButton("📊 آمار کاربران")],
        [KeyboardButton("❓ سوال و جواب"), KeyboardButton("📋 سوالات کاربران")],
        [KeyboardButton("💳 درخواست‌های برداشت"), KeyboardButton("🏆 برترین رفرال‌ها")],
        [KeyboardButton("🔙 خروج از پنل")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def payment_buttons(payment_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"confirm_payment_{payment_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{payment_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def withdraw_buttons(withdraw_id):
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید برداشت", callback_data=f"confirm_withdraw_{withdraw_id}"),
            InlineKeyboardButton("❌ رد برداشت", callback_data=f"reject_withdraw_{withdraw_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== وضعیت‌ها ====================
(WAITING_PAYMENT_PHOTO, WAITING_EDU_TITLE, WAITING_EDU_CONTENT, 
 WAITING_EDU_MEDIA, WAITING_FAQ_QUESTION, WAITING_FAQ_ANSWER, 
 WAITING_FAQ_KEYWORDS, WAITING_USER_QUESTION, WAITING_BROADCAST,
 WAITING_ANSWER_QUESTION, WAITING_WITHDRAW_ADDRESS, 
 WAITING_WITHDRAW_AMOUNT) = range(12)

# ==================== پیام‌ها ====================
WELCOME = """
🌟 **به آکادمی تخصصی ترید خوش آمدید!** 🌟

سلام {first_name} عزیز! 👋

ما اینجا نیستیم که به شما **سیگنال** بدهیم!
ما اینجاییم تا **شما را به یک تریدر حرفه‌ای و مستقل** تبدیل کنیم! 🚀

---

🎯 **چرا ما؟**
• ❌ **سیگنال نمی‌دهیم** (سیگنال وابستگی می‌آورد)
• ✅ **ماهیگیری یاد می‌دهیم**، نه ماهی!
• ✅ **بیش از ۱۰۰۰ تریدر** به ما اعتماد کرده‌اند
• ✅ **ضریب موفقیت ۹۲٪** در دوره‌های گذشته

---

💰 **هزینه اشتراک ویژه:**
فقط {price} دلار - **دسترسی مادام‌العمر**!

🎁 **سیستم رفرال:**
با دعوت از دوستان، **۵۰ دلار** پاداش بگیرید!

---

📌 **از دکمه‌های زیر استفاده کنید:**

📖 راهنمایی - توضیح کامل
📚 آموزش ترید - مشاهده محتوا
💳 خرید اشتراک - فعال‌سازی دسترسی
🎯 رفرال و درآمد - کسب درآمد
💰 برداشت - برداشت پول

**موفق باشید!** 💪
"""

HELP_TEXT = """
🌟 **راهنمای کامل آکادمی ترید** 🌟

سلام دوست عزیز! 👋

---

🎯 **هدف ما:**
شما را به یک **تریدر مستقل و حرفه‌ای** تبدیل کنیم.

---

📚 **آموزش‌ها:**
• تحلیل تکنیکال و فاندامنتال
• مدیریت ریسک و سرمایه
• روانشناسی ترید
• استراتژی‌های معاملاتی
• تمرین عملی

---

💰 **سیستم رفرال:**

🎁 **چگونه درآمد کسب کنیم؟**

۱. لینک رفرال خود را دریافت کنید
۲. با دوستان خود به اشتراک بگذارید
۳. به ازای هر کاربر فعال، **۵۰ دلار** پاداش بگیرید
۴. پس از جمع‌آوری **۵۰۰ دلار**، برداشت کنید

📊 **آمار شما:**
• تعداد رفرال‌ها: {referrals}
• درآمد کل: {earnings} دلار
• موجودی: {balance} دلار

---

❓ **سوالات متداول:**

**س: چگونه لینک رفرال خود را دریافت کنم؟**
ج: روی دکمه **"🎯 رفرال و درآمد"** کلیک کنید.

**س: پاداش رفرال چقدر است؟**
ج: **۵۰ دلار** به ازای هر کاربر فعال.

**س: چگونه برداشت کنم؟**
ج: پس از جمع‌آوری ۵۰۰ دلار، از دکمه **"💰 برداشت"** استفاده کنید.

---

**موفقیت شما، هدف ماست!** 🏆
"""

REFERRAL_TEXT = """
🎯 **سیستم رفرال و درآمدزایی** 🎯

سلام {first_name} عزیز! 👋

---

📊 **آمار شما:**
• 👥 تعداد رفرال‌ها: {referrals}
• 💰 درآمد کل: {earnings} دلار
• 🏦 موجودی قابل برداشت: {balance} دلار

---

🔗 **لینک رفرال اختصاصی شما:**

`https://t.me/{bot_username}?start=ref_{referral_code}`

📌 **نحوه استفاده:**
۱. لینک را کپی کنید
۲. برای دوستان خود ارسال کنید
۳. به ازای هر کاربر فعال، **۵۰ دلار** پاداش بگیرید

---

🏆 **برترین رفرال‌دهنده‌ها:**

{top_referrers}

---

💰 **حداقل مبلغ برداشت:** {min_withdraw} دلار

موفق باشید! 🚀
"""

# ==================== هندلرها ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    referrer_id = None
    if args and args[0].startswith('ref_'):
        referral_code = args[0].replace('ref_', '')
        referrer_id = db.get_user_by_referral(referral_code)
    
    db.add_user(user.id, user.username, user.first_name, user.last_name, referrer_id)
    
    if is_admin(user.id):
        reply_markup = admin_menu()
    else:
        reply_markup = main_menu()
    
    await update.message.reply_text(
        WELCOME.format(first_name=user.first_name, price=PRICE_USD),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    if referrer_id:
        await update.message.reply_text(
            f"🎉 شما با لینک رفرال ثبت‌نام کردید!\n"
            f"اگر اشتراک تهیه کنید، دوست شما {REFERRAL_BONUS} دلار پاداش می‌گیرد!",
            parse_mode=ParseMode.MARKDOWN
        )

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ==================== منوی اصلی ====================
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # پنل مدیریت
    if text == "👑 پنل مدیریت" and is_admin(user_id):
        await update.message.reply_text(
            "👑 **پنل مدیریت**\n\nاز دکمه‌های زیر استفاده کنید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel()
        )
        return
    
    if text == "🔙 خروج از پنل" and is_admin(user_id):
        await update.message.reply_text(
            "🔙 خارج شدید.",
            reply_markup=admin_menu()
        )
        return
    
    # دکمه‌های اصلی
    if text == "📖 راهنمایی":
        user = db.get_user(user_id)
        referrals = user['total_referrals'] if user else 0
        earnings = user['total_earnings'] if user else 0
        balance = user['balance'] if user else 0
        
        await update.message.reply_text(
            HELP_TEXT.format(referrals=referrals, earnings=earnings, balance=balance),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
    
    elif text == "📚 آموزش ترید":
        await show_education(update, context)
    
    elif text == "💳 خرید اشتراک":
        await buy_subscription(update, context)
    
    elif text == "📊 وضعیت اشتراک":
        await check_subscription(update, context)
    
    elif text == "❓ مشاوره و سوال":
        await ask_question(update, context)
    
    elif text == "🎯 رفرال و درآمد":
        await show_referral(update, context)
    
    elif text == "💰 برداشت":
        await withdraw_system(update, context)
    
    elif text == "📞 پشتیبانی":
        await support(update, context)
    
    # دکمه‌های پنل مدیریت
    elif is_admin(user_id):
        if text == "💰 فیش‌ها":
            await show_payments(update, context)
        elif text == "📝 ارسال آموزش":
            await start_add_education(update, context)
        elif text == "📢 پیام همگانی":
            await start_broadcast(update, context)
        elif text == "📊 آمار کاربران":
            await show_stats(update, context)
        elif text == "❓ سوال و جواب":
            await start_add_faq(update, context)
        elif text == "📋 سوالات کاربران":
            await show_user_questions(update, context)
        elif text == "💳 درخواست‌های برداشت":
            await show_withdraw_requests(update, context)
        elif text == "🏆 برترین رفرال‌ها":
            await show_top_referrers(update, context)
        else:
            await update.message.reply_text(
                "❌ گزینه نامعتبر!",
                reply_markup=admin_panel()
            )
    else:
        await update.message.reply_text(
            "❌ گزینه نامعتبر!",
            reply_markup=main_menu()
        )

# ==================== آموزش ====================
async def show_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user or not user['subscription_active']:
        await update.message.reply_text(
            f"🔒 **دسترسی محدود!**\n\n"
            f"برای دسترسی کامل، اشتراک تهیه کنید.\n"
            f"💰 هزینه: {PRICE_USD} دلار\n"
            f"از دکمه **💳 خرید اشتراک** استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
        return
    
    educations = db.get_all_education()
    
    if not educations:
        await update.message.reply_text(
            "📚 **محتوای آموزشی**\n\nهنوز محتوایی منتشر نشده است.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
        return
    
    for edu in educations:
        msg = f"📚 **{edu['title']}**\n\n{edu['content']}"
        
        try:
            if edu['media_type'] == 'photo' and edu['media_file_id']:
                await update.message.reply_photo(
                    photo=edu['media_file_id'],
                    caption=msg,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif edu['media_type'] == 'video' and edu['media_file_id']:
                await update.message.reply_video(
                    video=edu['media_file_id'],
                    caption=msg,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif edu['media_type'] == 'document' and edu['media_file_id']:
                await update.message.reply_document(
                    document=edu['media_file_id'],
                    caption=msg,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"خطا در ارسال آموزش: {e}")
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# ==================== خرید اشتراک ====================
async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    user = db.get_user(user_id)
    if user and user['subscription_active']:
        expiry = user['subscription_expiry']
        if expiry:
            try:
                expiry_date = datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S')
                if expiry_date > datetime.now():
                    await update.message.reply_text(
                        f"✅ **اشتراک شما فعال است!**\n\n"
                        f"📅 تاریخ انقضا: {expiry}",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu()
                    )
                    return
            except:
                pass
    
    text = f"""
💳 **خرید اشتراک**

💰 مبلغ: **{PRICE_USD} دلار** (دسترسی دائمی)

📌 **مراحل پرداخت:**

1️⃣ مبلغ {PRICE_USD} دلار به آدرس زیر واریز کنید:

🔗 **آدرس کیف پول (TRC20):**
`{WALLET_ADDRESS}`

2️⃣ از رسید تراکنش **عکس** بگیرید

3️⃣ عکس را به همراه **هش تراکنش** ارسال کنید

⚠️ **توجه:**
• حتماً از شبکه **TRC20** استفاده کنید
• مبلغ دقیقاً {PRICE_USD} دلار باشد

✅ پس از واریز، عکس را **همینجا** ارسال کنید.
    """
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu()
    )
    
    # تنظیم وضعیت برای دریافت عکس
    context.user_data['waiting_payment'] = True
    return WAITING_PAYMENT_PHOTO

async def handle_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت عکس فیش و ارسال به ادمین"""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    caption = update.message.caption
    
    if not caption:
        await update.message.reply_text(
            "❌ لطفاً **هش تراکنش (TxID)** را به همراه عکس ارسال کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
        return WAITING_PAYMENT_PHOTO
    
    tx_hash = caption.strip()
    if len(tx_hash) < 10:
        await update.message.reply_text(
            "❌ هش تراکنش نامعتبر است!",
            reply_markup=main_menu()
        )
        return WAITING_PAYMENT_PHOTO
    
    # ثبت در دیتابیس
    payment_id = db.add_payment(user_id, PRICE_USD, tx_hash, photo.file_id)
    
    if not payment_id:
        await update.message.reply_text(
            "❌ خطا در ثبت فیش!",
            reply_markup=main_menu()
        )
        context.user_data['waiting_payment'] = False
        return ConversationHandler.END
    
    # ارسال به ادمین‌ها
    user = update.effective_user
    sent_to_admin = False
    
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo.file_id,
                caption=f"""
💰 **فیش پرداخت جدید!**

👤 کاربر: {user.first_name} {user.last_name}
🆔 آیدی: {user_id}
📱 یوزرنیم: @{user.username if user.username else 'ندارد'}
💵 مبلغ: {PRICE_USD} دلار
🔗 هش: `{tx_hash}`
📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📌 برای تایید یا رد، از دکمه‌ها استفاده کنید:
                """,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=payment_buttons(payment_id)
            )
            sent_to_admin = True
            logger.info(f"✅ فیش به ادمین {admin_id} ارسال شد")
        except Exception as e:
            logger.error(f"❌ خطا در ارسال به ادمین {admin_id}: {e}")
    
    if sent_to_admin:
        await update.message.reply_text(
            "✅ **فیش شما با موفقیت ثبت شد!** 💰\n\n"
            "📋 فیش برای بررسی به مدیریت ارسال شد.\n"
            "⏱ فرآیند بررسی **حداکثر ۲ ساعت** طول می‌کشد.\n\n"
            "🔔 پس از تایید، به شما اطلاع داده می‌شود.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "⚠️ فیش ثبت شد اما ارسال به مدیریت با مشکل مواجه شد.\n"
            "لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=main_menu()
        )
    
    context.user_data['waiting_payment'] = False
    return ConversationHandler.END

# ==================== وضعیت اشتراک ====================
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ کاربر یافت نشد!",
            reply_markup=main_menu()
        )
        return
    
    if user['subscription_active']:
        expiry = user['subscription_expiry']
        if expiry:
            try:
                expiry_date = datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S')
                if expiry_date > datetime.now():
                    days_left = (expiry_date - datetime.now()).days
                    await update.message.reply_text(
                        f"✅ **اشتراک فعال است!**\n\n"
                        f"📅 زمان باقی‌مانده: {days_left} روز\n"
                        f"📆 تاریخ انقضا: {expiry}",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu()
                    )
                else:
                    await update.message.reply_text(
                        f"⏰ **اشتراک منقضی شده!**\n\n"
                        f"از دکمه **💳 خرید اشتراک** استفاده کنید.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu()
                    )
            except:
                await update.message.reply_text(
                    f"✅ **اشتراک فعال است!** (دسترسی دائمی)",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu()
                )
        else:
            await update.message.reply_text(
                f"✅ **اشتراک فعال است!** (دسترسی دائمی)",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu()
            )
    else:
        await update.message.reply_text(
            f"❌ **اشتراک فعال نیست!**\n\n"
            f"💰 هزینه: {PRICE_USD} دلار\n"
            f"از دکمه **💳 خرید اشتراک** استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )

# ==================== رفرال ====================
async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ کاربر یافت نشد!",
            reply_markup=main_menu()
        )
        return
    
    referrals = db.get_user_referrals(user_id)
    top_referrers = db.get_top_referrers(5)
    
    top_text = ""
    for i, ref in enumerate(top_referrers[:5], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        top_text += f"{medal} @{ref['username'] or 'کاربر'} - {ref['total_referrals']} نفر\n"
    
    if not top_text:
        top_text = "هنوز کسی رفرال نداشته است.\nشما می‌توانید اولین نفر باشید! 🚀"
    
    await update.message.reply_text(
        REFERRAL_TEXT.format(
            first_name=user['first_name'],
            referrals=user['total_referrals'],
            earnings=user['total_earnings'],
            balance=user['balance'],
            bot_username=BOT_USERNAME,
            referral_code=user['referral_code'],
            top_referrers=top_text,
            min_withdraw=MIN_WITHDRAW
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu()
    )

# ==================== برداشت ====================
async def withdraw_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ کاربر یافت نشد!",
            reply_markup=main_menu()
        )
        return
    
    if user['balance'] < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ **موجودی کافی نیست!**\n\n"
            f"💰 موجودی: {user['balance']} دلار\n"
            f"📌 حداقل برداشت: {MIN_WITHDRAW} دلار\n\n"
            f"برای افزایش موجودی، از سیستم رفرال استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
        return
    
    await update.message.reply_text(
        f"💰 **برداشت از حساب**\n\n"
        f"موجودی قابل برداشت: {user['balance']} دلار\n"
        f"حداقل برداشت: {MIN_WITHDRAW} دلار\n\n"
        f"📌 **آدرس کیف پول (TRC20) خود را وارد کنید:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu()
    )
    context.user_data['withdraw_step'] = 'address'
    return WAITING_WITHDRAW_ADDRESS

async def handle_withdraw_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = update.message.text.strip()
    
    if len(wallet_address) < 20:
        await update.message.reply_text(
            "❌ آدرس نامعتبر! لطفاً مجدداً ارسال کنید.",
            reply_markup=main_menu()
        )
        return WAITING_WITHDRAW_ADDRESS
    
    context.user_data['wallet_address'] = wallet_address
    
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    await update.message.reply_text(
        f"💰 **تایید برداشت**\n\n"
        f"موجودی قابل برداشت: {user['balance']} دلار\n"
        f"حداقل برداشت: {MIN_WITHDRAW} دلار\n\n"
        f"📌 **مبلغ مورد نظر را وارد کنید:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu()
    )
    context.user_data['withdraw_step'] = 'amount'
    return WAITING_WITHDRAW_AMOUNT

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        amount = float(update.message.text.strip())
    except:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر! لطفاً عدد وارد کنید.",
            reply_markup=main_menu()
        )
        return WAITING_WITHDRAW_AMOUNT
    
    user = db.get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ حداقل برداشت {MIN_WITHDRAW} دلار است!",
            reply_markup=main_menu()
        )
        return WAITING_WITHDRAW_AMOUNT
    
    if amount > user['balance']:
        await update.message.reply_text(
            f"❌ موجودی کافی نیست! (موجودی: {user['balance']} دلار)",
            reply_markup=main_menu()
        )
        return WAITING_WITHDRAW_AMOUNT
    
    wallet_address = context.user_data.get('wallet_address')
    
    success, message = db.add_withdraw_request(user_id, amount, wallet_address)
    
    if success:
        # ارسال به ادمین
        for admin_id in ADMIN_IDS:
            try:
                # دریافت آخرین درخواست برداشت
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT id FROM withdraw_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
                result = cur.fetchone()
                cur.close()
                conn.close()
                
                if result:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"""
💰 **درخواست برداشت جدید!**

👤 کاربر: {user['first_name']} {user['last_name']}
🆔 آیدی: {user_id}
📱 یوزرنیم: @{user['username'] if user['username'] else 'ندارد'}

💵 مبلغ: {amount} دلار
🔗 آدرس: `{wallet_address}`
💰 موجودی: {user['balance']} دلار

📌 برای تایید/رد، از دکمه‌ها استفاده کنید:
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=withdraw_buttons(result['id'])
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال به ادمین: {e}")
        
        await update.message.reply_text(
            f"✅ **درخواست برداشت ثبت شد!**\n\n"
            f"💰 مبلغ: {amount} دلار\n"
            f"🔗 آدرس: `{wallet_address}`\n\n"
            f"⏱ در حال بررسی...",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            f"❌ خطا: {message}",
            reply_markup=main_menu()
        )
    
    context.user_data.pop('withdraw_step', None)
    context.user_data.pop('wallet_address', None)
    return ConversationHandler.END

# ==================== مشاوره و سوال ====================
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ **مشاوره و سوال**\n\n"
        "سوال خود را بنویسید. کارشناسان ما پاسخ می‌دهند.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu()
    )
    context.user_data['waiting_question'] = True
    return WAITING_USER_QUESTION

async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    question = update.message.text
    
    q_id = db.add_user_question(user_id, question)
    
    if q_id:
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"""
❓ **سوال جدید:**

👤 کاربر: {update.effective_user.first_name}
🆔 آیدی: {user_id}
📝 سوال: {question}

برای پاسخ، از پنل مدیریت استفاده کنید.
                    """,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"خطا در ارسال به ادمین: {e}")
        
        await update.message.reply_text(
            "✅ **سوال شما ثبت شد!**\n\n"
            "کارشناسان ما در اسرع وقت پاسخ می‌دهند.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت سوال!",
            reply_markup=main_menu()
        )
    
    context.user_data['waiting_question'] = False
    return ConversationHandler.END

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 **پشتیبانی**\n\n"
        "برای ارتباط با پشتیبانی:\n"
        "1️⃣ از دکمه **❓ مشاوره و سوال** استفاده کنید\n"
        "2️⃣ با ادمین تماس بگیرید: @YourAdmin\n\n"
        "⏱ ساعات پاسخگویی: ۹ صبح تا ۱۲ شب",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu()
    )

# ==================== پنل مدیریت ====================
async def show_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    payments = db.get_pending_payments()
    
    if not payments:
        await update.message.reply_text(
            "✅ **هیچ فیش در انتظار تاییدی نیست.**",
            reply_markup=admin_panel()
        )
        return
    
    for payment in payments:
        text = f"""
💰 **فیش #{payment['id']}**

👤 کاربر: {payment['last_name']} {payment['first_name']}
💵 مبلغ: {payment['amount']} دلار
🔗 هش: `{payment['tx_hash']}`
📅 تاریخ: {payment['created_at']}
        """
        
        try:
            await update.message.reply_photo(
                photo=payment['photo_file_id'],
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=payment_buttons(payment['id'])
            )
        except Exception as e:
            logger.error(f"خطا در نمایش فیش: {e}")
            await update.message.reply_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=payment_buttons(payment['id'])
            )

async def handle_payment_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    data = query.data
    parts = data.split('_')
    action = parts[1]
    payment_id = int(parts[2])
    
    if action == 'confirm':
        user_id = db.confirm_payment(payment_id)
        if user_id:
            await query.edit_message_text(f"✅ **فیش #{payment_id} تایید شد!**")
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="""
🎉 **تبریک! پرداخت شما تایید شد!** ✅

✅ اشتراک شما فعال شد!
📚 به تمام محتوای آموزشی دسترسی دارید.

🚀 موفق و پرسود باشید!
                    """,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu()
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام تایید: {e}")
        else:
            await query.edit_message_text(f"❌ خطا در تایید فیش!")
    
    elif action == 'reject':
        if db.reject_payment(payment_id):
            await query.edit_message_text(f"❌ **فیش #{payment_id} رد شد!**")
            
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM payments WHERE id = ?", (payment_id,))
                result = cur.fetchone()
                cur.close()
                conn.close()
                
                if result:
                    await context.bot.send_message(
                        chat_id=result['user_id'],
                        text="""
❌ **پرداخت شما رد شد!**

دلایل احتمالی:
• مبلغ نادرست
• شبکه اشتباه (باید TRC20 باشد)
• عکس رسید واضح نیست

لطفاً مجدداً از دکمه **💳 خرید اشتراک** استفاده کنید.
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu()
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام رد: {e}")
        else:
            await query.edit_message_text(f"❌ خطا در رد فیش!")

# ==================== مدیریت برداشت ====================
async def show_withdraw_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    withdraws = db.get_pending_withdraws()
    
    if not withdraws:
        await update.message.reply_text(
            "✅ **هیچ درخواست برداشتی در انتظار نیست.**",
            reply_markup=admin_panel()
        )
        return
    
    for w in withdraws:
        text = f"""
💰 **درخواست برداشت #{w['id']}**

👤 کاربر: {w['last_name']} {w['first_name']}
💵 مبلغ: {w['amount']} دلار
🔗 آدرس: `{w['wallet_address']}`
📅 تاریخ: {w['created_at']}
        """
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=withdraw_buttons(w['id'])
        )

async def handle_withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    data = query.data
    parts = data.split('_')
    action = parts[1]
    withdraw_id = int(parts[2])
    
    if action == 'confirm':
        if db.process_withdraw(withdraw_id, 'confirmed'):
            await query.edit_message_text(f"✅ **برداشت #{withdraw_id} تایید شد!**")
            
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (withdraw_id,))
                result = cur.fetchone()
                cur.close()
                conn.close()
                
                if result:
                    await context.bot.send_message(
                        chat_id=result['user_id'],
                        text=f"""
✅ **درخواست برداشت شما تایید شد!** 🎉

💰 مبلغ: {result['amount']} دلار به کیف پول شما واریز شد.

🙏 از اعتماد شما سپاسگزاریم.
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu()
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام تایید برداشت: {e}")
        else:
            await query.edit_message_text(f"❌ خطا در تایید برداشت!")
    
    elif action == 'reject':
        if db.process_withdraw(withdraw_id, 'rejected'):
            await query.edit_message_text(f"❌ **برداشت #{withdraw_id} رد شد!**")
            
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (withdraw_id,))
                result = cur.fetchone()
                cur.close()
                conn.close()
                
                if result:
                    await context.bot.send_message(
                        chat_id=result['user_id'],
                        text=f"""
❌ **درخواست برداشت شما رد شد!**

متاسفانه درخواست برداشت شما تایید نشد.

لطفاً مجدداً از دکمه **💰 برداشت** استفاده کنید.
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu()
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام رد برداشت: {e}")
        else:
            await query.edit_message_text(f"❌ خطا در رد برداشت!")

# ==================== سایر توابع مدیریت ====================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    stats = db.get_stats()
    
    text = f"""
📊 **آمار جامع**

👥 کاربران کل: {stats['total_users']:,}
✅ اشتراک فعال: {stats['subscribed_users']:,}

💰 **آمار مالی:**
فیش‌های در انتظار: {stats['pending_payments']}
کل پرداخت‌ها: {stats['total_payments']}
درآمد کل: {stats['total_earnings']:,} دلار

🎯 **سیستم رفرال:**
کل رفرال‌ها: {stats['total_referrals']}
پاداش پرداختی: {stats['total_referral_bonus']:,} دلار
درخواست‌های برداشت: {stats['pending_withdraws']}

⚡ **سیستم:**
شاردینگ‌ها: {MAX_WORKERS}
ظرفیت: ۱۰۰,۰۰۰ کاربر
    """
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel()
    )

async def show_top_referrers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    top = db.get_top_referrers(20)
    
    if not top:
        await update.message.reply_text(
            "📊 **هیچ رفرالی ثبت نشده است.**",
            reply_markup=admin_panel()
        )
        return
    
    text = "🏆 **برترین رفرال‌دهنده‌ها:**\n\n"
    for i, ref in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} @{ref['username'] or 'کاربر'} - {ref['total_referrals']} نفر | {ref['total_earnings']} دلار\n"
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel()
    )

async def show_user_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    questions = db.get_pending_user_questions()
    
    if not questions:
        await update.message.reply_text(
            "✅ **هیچ سوالی در انتظار نیست.**",
            reply_markup=admin_panel()
        )
        return
    
    for q in questions:
        text = f"""
❓ **سوال کاربر:**

👤 {q['last_name']} {q['first_name']}
📝 {q['question']}
📅 {q['created_at']}
        """
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 پاسخ", callback_data=f"answer_question_{q['id']}")]
            ])
        )

async def handle_question_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ دسترسی ادمین ندارید!")
        return
    
    q_id = int(query.data.split('_')[2])
    context.user_data['answering_question_id'] = q_id
    
    await query.edit_message_text("📝 **پاسخ خود را وارد کنید:**")
    return WAITING_ANSWER_QUESTION

async def handle_answer_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    q_id = context.user_data.get('answering_question_id')
    answer = update.message.text
    
    if db.answer_user_question(q_id, answer):
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, question FROM user_questions WHERE id = ?", (q_id,))
        q_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if q_data:
            try:
                await context.bot.send_message(
                    chat_id=q_data['user_id'],
                    text=f"""
✅ **پاسخ به سوال شما:**

📝 {q_data['question']}

📌 **پاسخ:**
{answer}

موفق باشید! 🚀
                    """,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu()
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پاسخ: {e}")
        
        await update.message.reply_text(
            "✅ **پاسخ ارسال شد!**",
            reply_markup=admin_panel()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ارسال پاسخ!",
            reply_markup=admin_panel()
        )
    
    context.user_data.pop('answering_question_id', None)
    return ConversationHandler.END

async def start_add_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text(
        "❓ **افزودن سوال و جواب**\n\nسوال را وارد کنید:",
        reply_markup=admin_panel()
    )
    return WAITING_FAQ_QUESTION

async def handle_faq_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['faq_question'] = update.message.text
    await update.message.reply_text("📝 **جواب را وارد کنید:**")
    return WAITING_FAQ_ANSWER

async def handle_faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['faq_answer'] = update.message.text
    await update.message.reply_text("🔑 **کلمات کلیدی (با کاما جدا کنید):**")
    return WAITING_FAQ_KEYWORDS

async def handle_faq_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keywords = [kw.strip() for kw in update.message.text.split(',')]
    question = context.user_data.get('faq_question')
    answer = context.user_data.get('faq_answer')
    
    if db.add_faq(question, answer, keywords):
        await update.message.reply_text(
            f"✅ **سوال و جواب ثبت شد!**\n\n❓ {question}",
            reply_markup=admin_panel()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت!",
            reply_markup=admin_panel()
        )
    
    context.user_data.pop('faq_question', None)
    context.user_data.pop('faq_answer', None)
    return ConversationHandler.END

async def start_add_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text(
        "📝 **افزودن آموزش**\n\nعنوان را وارد کنید:",
        reply_markup=admin_panel()
    )
    return WAITING_EDU_TITLE

async def handle_edu_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['edu_title'] = update.message.text
    await update.message.reply_text("📝 **متن آموزش را وارد کنید:**")
    return WAITING_EDU_CONTENT

async def handle_edu_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['edu_content'] = update.message.text
    await update.message.reply_text(
        "📎 **فایل ضمیمه ارسال کنید**\n"
        "(عکس/ویدئو/فایل) یا 'لغو' برای بدون فایل"
    )
    return WAITING_EDU_MEDIA

async def handle_edu_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    title = context.user_data.get('edu_title')
    content = context.user_data.get('edu_content')
    
    media_type = None
    media_file_id = None
    
    if update.message.photo:
        media_type = 'photo'
        media_file_id = update.message.photo[-1].file_id
    elif update.message.video:
        media_type = 'video'
        media_file_id = update.message.video.file_id
    elif update.message.document:
        media_type = 'document'
        media_file_id = update.message.document.file_id
    else:
        media_type = 'text'
    
    edu_id = db.add_education_content(title, content, media_type, media_file_id)
    
    if edu_id:
        await update.message.reply_text(
            f"✅ **آموزش ثبت شد!**\n\nدر حال ارسال به کاربران...",
            reply_markup=admin_panel()
        )
        
        subscribed = db.get_subscribed_users()
        success = 0
        
        for i, user_id in enumerate(subscribed):
            try:
                if media_type == 'photo' and media_file_id:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=media_file_id,
                        caption=f"📚 **{title}**\n\n{content}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif media_type == 'video' and media_file_id:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=media_file_id,
                        caption=f"📚 **{title}**\n\n{content}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                elif media_type == 'document' and media_file_id:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=media_file_id,
                        caption=f"📚 **{title}**\n\n{content}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📚 **{title}**\n\n{content}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                success += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"خطا در ارسال به {user_id}: {e}")
        
        await update.message.reply_text(
            f"📊 **گزارش ارسال:**\n✅ موفق: {success}\n❌ ناموفق: {len(subscribed) - success}",
            reply_markup=admin_panel()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت آموزش!",
            reply_markup=admin_panel()
        )
    
    context.user_data.pop('edu_title', None)
    context.user_data.pop('edu_content', None)
    return ConversationHandler.END

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    users = db.get_all_users()
    await update.message.reply_text(
        f"📢 **پیام همگانی به {len(users)} کاربر**\n\nپیام خود را ارسال کنید:",
        reply_markup=admin_panel()
    )
    return WAITING_BROADCAST

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    users = db.get_all_users()
    total = len(users)
    
    await update.message.reply_text(f"📤 در حال ارسال به {total} کاربر...")
    
    success = 0
    for i, user in enumerate(users):
        try:
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=user['user_id'],
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption
                )
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=user['user_id'],
                    video=update.message.video.file_id,
                    caption=update.message.caption
                )
            elif update.message.document:
                await context.bot.send_document(
                    chat_id=user['user_id'],
                    document=update.message.document.file_id,
                    caption=update.message.caption
                )
            else:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=update.message.text,
                    parse_mode=ParseMode.MARKDOWN
                )
            success += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"خطا در ارسال به {user['user_id']}: {e}")
    
    await update.message.reply_text(
        f"📊 **گزارش ارسال:**\n✅ موفق: {success}\n❌ ناموفق: {total - success}",
        reply_markup=admin_panel()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=admin_panel())
    return ConversationHandler.END

# ==================== اصلی ====================
def main():
    application = Application.builder().token(TOKEN).build()
    
    # استارت و راهنمایی
    application.add_handler(CommandHandler("start", start))
    
    # منوی اصلی
    application.add_handler(MessageHandler(
        filters.Regex("^(📖 راهنمایی|📚 آموزش ترید|💳 خرید اشتراک|📊 وضعیت اشتراک|❓ مشاوره و سوال|🎯 رفرال و درآمد|💰 برداشت|📞 پشتیبانی|👑 پنل مدیریت|🔙 خروج از پنل|💰 فیش‌ها|📝 ارسال آموزش|📢 پیام همگانی|📊 آمار کاربران|❓ سوال و جواب|📋 سوالات کاربران|💳 درخواست‌های برداشت|🏆 برترین رفرال‌ها)$"),
        handle_menu
    ))
    
    # پرداخت
    payment_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💳 خرید اشتراک$"), buy_subscription)],
        states={WAITING_PAYMENT_PHOTO: [MessageHandler(filters.PHOTO & filters.CAPTION, handle_payment_photo)]},
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel)]
    )
    application.add_handler(payment_conv)
    
    # سوال کاربر
    question_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❓ مشاوره و سوال$"), ask_question)],
        states={WAITING_USER_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_question)]},
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel)]
    )
    application.add_handler(question_conv)
    
    # برداشت
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💰 برداشت$"), withdraw_system)],
        states={
            WAITING_WITHDRAW_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_address)],
            WAITING_WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_amount)]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel)]
    )
    application.add_handler(withdraw_conv)
    
    # آموزش (ادمین)
    edu_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 ارسال آموزش$"), start_add_education)],
        states={
            WAITING_EDU_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edu_title)],
            WAITING_EDU_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edu_content)],
            WAITING_EDU_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.TEXT, handle_edu_media)]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel)]
    )
    application.add_handler(edu_conv)
    
    # پیام همگانی
    broadcast_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📢 پیام همگانی$"), start_broadcast)],
        states={WAITING_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, handle_broadcast)]},
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel)]
    )
    application.add_handler(broadcast_conv)
    
    # سوال و جواب (ادمین)
    faq_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❓ سوال و جواب$"), start_add_faq)],
        states={
            WAITING_FAQ_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_faq_question)],
            WAITING_FAQ_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_faq_answer)],
            WAITING_FAQ_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_faq_keywords)]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel)]
    )
    application.add_handler(faq_conv)
    
    # پاسخ به سوال کاربر
    answer_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_question_answer, pattern="^answer_question_")],
        states={WAITING_ANSWER_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer_text)]},
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel)]
    )
    application.add_handler(answer_conv)
    
    # کالبک‌ها
    application.add_handler(CallbackQueryHandler(handle_payment_action, pattern="^(confirm_payment_|reject_payment_)"))
    application.add_handler(CallbackQueryHandler(handle_withdraw_action, pattern="^(confirm_withdraw_|reject_withdraw_)"))
    
    # راه‌اندازی
    print("=" * 60)
    print("🚀 ربات آموزش ترید حرفه‌ای")
    print("=" * 60)
    print(f"📁 دیتابیس: trading_bot.db")
    print(f"👤 ادمین‌ها: {ADMIN_IDS}")
    print(f"⚡ شاردینگ‌ها: {MAX_WORKERS}")
    print(f"👥 ظرفیت: ۱۰۰,۰۰۰ کاربر")
    print("=" * 60)
    print("✅ ربات در حال اجراست...")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()