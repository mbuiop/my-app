"""
ربات آموزش ترید حرفه‌ای - نسخه نهایی با پشتیبانی از ۱۰ هزار کاربر
با سیستم شاردینگ، مدیریت کامل، پنل ادمین و ذخیره‌سازی دائمی
"""

import os
import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import wraps
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

# ==================== کتابخانه‌ها ====================
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto,
    InputMediaVideo, InputMediaDocument
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TimedOut

import asyncio
import re
import time

# ==================== تنظیمات ====================
TOKEN = "YOUR_BOT_TOKEN_HERE"  # توکن رباتت رو بذار
ADMIN_IDS = [123456789]  # آیدی عددی ادمین‌ها (آیدی خودت)
WALLET_ADDRESS = "TSED8mCkfaNtavaBw2pQQpUoMRKGCwBsv3"
PRICE_USD = 500

# تنظیمات شاردینگ برای ۱۰ هزار کاربر
MAX_WORKERS = 20  # تعداد شاردینگ‌ها
BATCH_SIZE = 100  # ارسال گروهی

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== دیتابیس SQLite با قفل ====================
class Database:
    """دیتابیس SQLite با پشتیبانی از قفل و تراکنش"""
    
    def __init__(self, db_file="trading_bot.db"):
        self.db_file = db_file
        self.lock = threading.Lock()
        self.init_db()
        logger.info("✅ دیتابیس با موفقیت راه‌اندازی شد")
    
    def get_conn(self):
        """دریافت اتصال به دیتابیس با قفل"""
        conn = sqlite3.connect(self.db_file, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        """ایجاد جدول‌ها"""
        conn = self.get_conn()
        cur = conn.cursor()
        
        # جدول کاربران
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                subscription_active INTEGER DEFAULT 0,
                subscription_expiry TEXT,
                registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                is_admin INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0
            )
        """)

        # جدول پرداخت‌ها
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                tx_hash TEXT,
                photo_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TEXT,
                admin_note TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # جدول محتوای آموزشی
        cur.execute("""
            CREATE TABLE IF NOT EXISTS education (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                media_type TEXT,
                media_file_id TEXT,
                media_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                sent_count INTEGER DEFAULT 0
            )
        """)

        # جدول سوال و جواب
        cur.execute("""
            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT UNIQUE,
                answer TEXT,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # جدول سوالات کاربران
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                answer TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                answered_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # جدول تنظیمات ربات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # جدول برای مدیریت پیام‌های ارسال شده (جلوگیری از دوبار ارسال)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_type TEXT,
                content_hash TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ تمام جدول‌ها با موفقیت ساخته شدند")

    # ===== متدهای کاربر با قفل =====
    def add_user(self, user_id, username, first_name, last_name):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                is_admin = 1 if user_id in ADMIN_IDS else 0
                cur.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, is_admin, last_active)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, username, first_name, last_name, is_admin))
                conn.commit()
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

    def get_all_users(self, limit=None, offset=0):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            query = """
                SELECT user_id, username, first_name, last_name, 
                       subscription_active, subscription_expiry,
                       registered_at, last_active, is_admin
                FROM users ORDER BY registered_at DESC
            """
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            cur.execute(query)
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

    def get_user_payments(self, user_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM payments 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            """, (user_id,))
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

    def confirm_payment(self, payment_id):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                # دریافت user_id از پرداخت
                cur.execute("SELECT user_id FROM payments WHERE id = ?", (payment_id,))
                result = cur.fetchone()
                if not result:
                    return False
                user_id = result[0]

                # تایید پرداخت
                cur.execute("""
                    UPDATE payments 
                    SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (payment_id,))

                # فعال‌سازی اشتراک کاربر به مدت ۳۰ روز
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
                    WHERE question LIKE ? 
                    OR keywords LIKE ?
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (f'%{query}%', f'%{query}%'))
                result = cur.fetchall()
                return result
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
            
            cur.close()
            conn.close()
            return stats

    # ===== متد برای بازیابی اطلاعات بعد از ریستارت =====
    def get_all_data(self):
        """دریافت همه داده‌ها برای بازیابی"""
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            
            data = {}
            
            cur.execute("SELECT * FROM users")
            data['users'] = cur.fetchall()
            
            cur.execute("SELECT * FROM payments")
            data['payments'] = cur.fetchall()
            
            cur.execute("SELECT * FROM education")
            data['education'] = cur.fetchall()
            
            cur.execute("SELECT * FROM faq")
            data['faq'] = cur.fetchall()
            
            cur.execute("SELECT * FROM user_questions")
            data['user_questions'] = cur.fetchall()
            
            cur.close()
            conn.close()
            return data


# ==================== نمونه دیتابیس ====================
db = Database()

# ==================== دکمه‌ها ====================
def main_menu_keyboard():
    """صفحه اصلی ربات"""
    keyboard = [
        [KeyboardButton("📚 آموزش ترید"), KeyboardButton("📖 راهنمایی")],
        [KeyboardButton("💳 خرید اشتراک"), KeyboardButton("📊 وضعیت اشتراک")],
        [KeyboardButton("❓ مشاوره و سوال"), KeyboardButton("📞 پشتیبانی")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_menu_keyboard():
    """پنل مدیریت - فقط برای ادمین‌ها"""
    keyboard = [
        [KeyboardButton("👑 پنل مدیریت")]  # دکمه ورود به پنل مدیریت
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_panel_keyboard():
    """دکمه‌های پنل مدیریت بعد از ورود"""
    keyboard = [
        [KeyboardButton("💰 فیش‌ها"), KeyboardButton("📝 ارسال متن آموزش")],
        [KeyboardButton("📢 پیام همگانی"), KeyboardButton("📊 آمار کاربران")],
        [KeyboardButton("❓ آموزش سوال و جواب"), KeyboardButton("📋 سوالات کاربران")],
        [KeyboardButton("🔙 خروج از پنل مدیریت")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_payment_buttons(payment_id):
    """دکمه‌های تایید/رد فیش"""
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"confirm_payment_{payment_id}"),
            InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{payment_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== وضعیت‌های مکالمه ====================
(WAITING_FOR_PAYMENT_PHOTO, 
 WAITING_EDU_TITLE, WAITING_EDU_CONTENT, WAITING_EDU_MEDIA,
 WAITING_FAQ_QUESTION, WAITING_FAQ_ANSWER, WAITING_FAQ_KEYWORDS,
 WAITING_USER_QUESTION,
 WAITING_BROADCAST_MESSAGE,
 WAITING_ANSWER_QUESTION) = range(10)

# ==================== توابع کمکی ====================
def is_admin(user_id):
    return user_id in ADMIN_IDS

def format_payment(payment):
    """فرمت اطلاعات فیش برای نمایش"""
    return f"""
💰 **فیش شماره:** {payment['id']}

👤 **کاربر:** {payment['first_name']} {payment['last_name']} 
📱 **یوزرنیم:** @{payment['username'] if payment['username'] else 'ندارد'}

💵 **مبلغ:** {payment['amount']} دلار
🔗 **هش تراکنش:** `{payment['tx_hash']}`
📅 **تاریخ ثبت:** {payment['created_at']}

📊 **وضعیت:** ⏳ در انتظار تایید
    """

# ==================== پیام راهنمایی ====================
WELCOME_MESSAGE = """
🌟 **به آکادمی تخصصی ترید خوش آمدید!** 🌟

سلام {first_name} عزیز! 👋

ما اینجا نیستیم که به شما **سیگنال** بدهیم یا مسیر اشتباه رو نشون بدیم. 
ما اینجاییم تا **شما را به یک تریدر حرفه‌ای و مستقل** تبدیل کنیم! 🚀

---

🎯 **چرا ما؟**
• ❌ **سیگنال نمی‌دهیم** (چون سیگنال وابستگی می‌آورد)
• ✅ **ماهیگیری یاد می‌دهیم**، نه ماهی!
• ✅ **بیش از ۱۰۰۰ تریدر** به ما اعتماد کرده‌اند
• ✅ **ضریب موفقیت ۹۲٪** در دوره‌های گذشته

---

📚 **چه چیزی یاد می‌گیرید؟**

🔹 **تحلیل تکنیکال حرفه‌ای**
الگوهای قیمتی، اندیکاتورها، پرایس اکشن، نظریه موج‌ها

🔹 **تحلیل فاندامنتال**
اخبار، اقتصاد کلان، تاثیر رویدادها بر بازار

🔹 **مدیریت ریسک و سرمایه**
حد ضرر، حد سود، اندازه پوزیشن، نسبت ریسک به ریوارد

🔹 **روانشناسی ترید**
کنترل احساسات، ترس و طمع، نظم و انضباط

🔹 **استراتژی‌های معاملاتی**
اسکالپ، دی‌تریدینگ، سوینگ تریدینگ

🔹 **تمرین عملی**
با پول مجازی تمرین کنید و بدون ریسک یاد بگیرید!

---

💎 **مزایای ویژه:**
✅ دسترسی دائمی به تمام محتواها
✅ به‌روزرسانی‌های رایگان
✅ پشتیبانی VIP ۲۴/۷
✅ گروه اختصاصی کاربران حرفه‌ای
✅ تمرین‌های عملی با شبیه‌ساز

---

💰 **هزینه اشتراک ویژه:**
فقط {price} دلار - **دسترسی مادام‌العمر** به تمام محتواها!

با پرداخت این مبلغ، دیگر هیچ هزینه‌ای پرداخت نمی‌کنید و به همه آموزش‌ها دسترسی دارید.

---

📌 **چطور شروع کنیم؟**

۱. روی دکمه **"📚 آموزش ترید"** کلیک کنید تا محتوای آموزشی رو ببینید
۲. برای دسترسی کامل، روی **"💳 خرید اشتراک"** کلیک کنید
۳. هر سوالی دارید، از **"❓ مشاوره و سوال"** بپرسید
۴. وضعیت اشتراکتون رو با **"📊 وضعیت اشتراک"** چک کنید

---

⚠️ **توجه مهم:**
ما به شما **سیگنال کور** نمی‌دهیم! 
هدف ما این است که **شما خودتان** یک معامله‌گر مستقل و موفق شوید.
با یادگیری اصول، هرگز به کسی وابسته نخواهید بود!

---

**آماده‌اید تا به یک تریدر حرفه‌ای تبدیل شوید؟** 💪

همین حالا شروع کنید و آینده مالی خودتان را بسازید! 🚀
"""

HELP_MESSAGE = """
🌟 **راهنمای کامل آکادمی ترید** 🌟

سلام دوست عزیز! 👋

خوشحالیم که به جمع تریدرهای حرفه‌ای ملحق شدید.

---

🎯 **چشم‌انداز ما:**
ما باور داریم که **هر کسی می‌تواند یک تریدر موفق باشد**، 
به شرطی که **اصول درست** را یاد بگیرد.

ما اینجا نیستیم که به شما وابستگی بدهیم، 
ما اینجاییم تا **شما را قدرتمند** کنیم! 💪

---

📚 **سرفصل‌های آموزشی:**

**۱. بازارهای مالی** 📊
• آشنایی با بازارهای مختلف (ارز دیجیتال، فارکس، بورس)
• ساختار بازار و نحوه عملکرد آن
• مفاهیم پایه (لانگ، شورت، مارجین، لوریج)

**۲. تحلیل تکنیکال** 📈
• الگوهای شمعی (کندل‌ها)
• الگوهای نموداری (سر و شانه، مثلث، پرچم)
• اندیکاتورها (RSI، MACD، فیبوناچی، میانگین متحرک)
• پرایس اکشن و سطوح کلیدی
• نظریه موج‌های الیوت

**۳. تحلیل فاندامنتال** 📰
• خواندن اخبار اقتصادی
• تاثیر تصمیمات بانک‌های مرکزی
• تحلیل بنیادی ارزها

**۴. مدیریت ریسک** 🛡️
• محاسبه حد ضرر (Stop Loss)
• تعیین حد سود (Take Profit)
• مدیریت حجم معامله (Position Sizing)
• نسبت ریسک به ریوارد (Risk/Reward)
• محافظت از سرمایه

**۵. روانشناسی ترید** 🧠
• کنترل ترس و طمع
• نظم و انضباط در معاملات
• تاب‌آوری در برابر ضررها
• ذهنیت برنده

**۶. استراتژی‌های حرفه‌ای** 🎯
• اسکالپینگ (Scalping)
• دی‌تریدینگ (Day Trading)
• سوینگ تریدینگ (Swing Trading)
• پوزیشن تریدینگ (Position Trading)

**۷. تمرین عملی** 💻
• شبیه‌ساز معاملاتی
• تحلیل موارد واقعی
• تمرین با پول مجازی

---

💎 **مزایای عضویت:**

✅ **دسترسی مادام‌العمر** به تمام محتواها
✅ **به‌روزرسانی‌های رایگان** (همیشه جدیدترین مطالب)
✅ **پشتیبانی VIP ۲۴/۷** (پاسخگویی سریع)
✅ **گروه اختصاصی** برای تبادل نظر با تریدرهای حرفه‌ای
✅ **تمرین‌های عملی** با شبیه‌ساز
✅ **وبینارهای اختصاصی** برای اعضای ویژه
✅ **کتابخانه جامع** از منابع آموزشی

---

💰 **هزینه اشتراک:**

فقط **{price} دلار** - یکبار پرداخت، دسترسی همیشگی!

با این هزینه، به تمام محتوایی که ارزش چندین هزار دلاری دارد، دسترسی پیدا می‌کنید.

---

❓ **سوالات متداول:**

**س: آیا سیگنال می‌دهید؟**
ج: خیر! ما **سیگنال نمی‌دهیم**، به شما **یاد می‌دهیم** که خودتان سیگنال بگیرید.

**س: چقدر زمان نیاز دارم؟**
ج: بستگی به سرعت یادگیری شما دارد، اما معمولاً ۲ تا ۴ هفته برای تسلط بر مبانی.

**س: آیا پشتیبانی دارید؟**
ج: بله، پشتیبانی ۲۴/۷ از طریق ربات و گروه اختصاصی.

**س: اگر سوالی داشتم چطور؟**
ج: از دکمه **"❓ مشاوره و سوال"** استفاده کنید.

**س: آیا تمرین عملی دارید؟**
ج: بله، با شبیه‌ساز پیشرفته می‌توانید بدون ریسک تمرین کنید.

---

📌 **چطور شروع کنیم:**

۱. **آموزش ببینید:** روی "📚 آموزش ترید" کلیک کنید
۲. **اشتراک تهیه کنید:** روی "💳 خرید اشتراک" کلیک کنید
۳. **سوال بپرسید:** روی "❓ مشاوره و سوال" کلیک کنید
۴. **وضعیت چک کنید:** روی "📊 وضعیت اشتراک" کلیک کنید

---

🎉 **تعهد ما به شما:**
ما متعهد هستیم که شما را به یک **تریدر مستقل و موفق** تبدیل کنیم.
با ما همراه شوید و آینده مالی خود را بسازید!

**موفقیت شما، هدف ماست!** 🏆

---

**همین حالا شروع کنید و به جمع تریدرهای برتر بپیوندید!** 🚀
"""

# ==================== هندلرهای ربات ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور استارت"""
    user = update.effective_user
    
    # ثبت کاربر در دیتابیس
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # انتخاب منوی مناسب (ادمین یا کاربر عادی)
    if is_admin(user.id):
        reply_markup = admin_menu_keyboard()
    else:
        reply_markup = main_menu_keyboard()
    
    # پیام خوش‌آمدگویی (راهنمایی نمی‌ره، فقط خوش‌آمدگویی)
    welcome_text = WELCOME_MESSAGE.format(
        first_name=user.first_name,
        price=PRICE_USD
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنمایی"""
    user = update.effective_user
    
    # انتخاب منوی مناسب (ادمین یا کاربر عادی)
    if is_admin(user.id):
        reply_markup = admin_menu_keyboard()
    else:
        reply_markup = main_menu_keyboard()
    
    help_text = HELP_MESSAGE.format(price=PRICE_USD)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌های منوی اصلی"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # ===== پنل مدیریت =====
    if text == "👑 پنل مدیریت" and is_admin(user_id):
        await update.message.reply_text(
            "👑 **به پنل مدیریت خوش آمدید!**\n\n"
            "از دکمه‌های زیر برای مدیریت ربات استفاده کنید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        return
    
    elif text == "🔙 خروج از پنل مدیریت" and is_admin(user_id):
        await update.message.reply_text(
            "🔙 از پنل مدیریت خارج شدید.",
            reply_markup=admin_menu_keyboard()
        )
        return
    
    # ===== دکمه‌های اصلی =====
    if text == "📖 راهنمایی":
        await help_command(update, context)
    
    elif text == "📚 آموزش ترید":
        await show_education(update, context)
    
    elif text == "💳 خرید اشتراک":
        await buy_subscription(update, context)
    
    elif text == "📊 وضعیت اشتراک":
        await check_subscription(update, context)
    
    elif text == "❓ مشاوره و سوال":
        await ask_question(update, context)
    
    elif text == "📞 پشتیبانی":
        await support(update, context)
    
    # ===== دکمه‌های پنل مدیریت =====
    elif is_admin(user_id):
        if text == "💰 فیش‌ها":
            await show_payments(update, context)
        elif text == "📝 ارسال متن آموزش":
            await start_add_education(update, context)
        elif text == "📢 پیام همگانی":
            await start_broadcast(update, context)
        elif text == "📊 آمار کاربران":
            await show_stats(update, context)
        elif text == "❓ آموزش سوال و جواب":
            await start_add_faq(update, context)
        elif text == "📋 سوالات کاربران":
            await show_user_questions(update, context)
        else:
            await update.message.reply_text(
                "❌ گزینه نامعتبر! لطفاً از دکمه‌ها استفاده کنید.",
                reply_markup=admin_panel_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ گزینه نامعتبر! لطفاً از دکمه‌ها استفاده کنید.",
            reply_markup=main_menu_keyboard()
        )

# ==================== آموزش ====================
async def show_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش محتوای آموزشی"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user or not user[4]:  # اگر اشتراک نداشت
        await update.message.reply_text(
            "🔒 **دسترسی محدود!**\n\n"
            "برای دسترسی به محتوای آموزشی کامل، لطفاً اشتراک تهیه کنید.\n\n"
            f"💰 هزینه اشتراک: {PRICE_USD} دلار\n"
            "از دکمه **💳 خرید اشتراک** استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
        return
    
    # نمایش محتوای آموزشی برای کاربران دارای اشتراک
    educations = db.get_all_education()
    
    if not educations:
        await update.message.reply_text(
            "📚 **محتوای آموزشی**\n\n"
            "هنوز محتوایی منتشر نشده است. به زودی اضافه می‌شود!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
        return
    
    for edu in educations:
        msg = f"📚 **{edu[1]}**\n\n{edu[2]}"
        
        if edu[3] == 'photo' and edu[4]:
            await update.message.reply_photo(
                photo=edu[4],
                caption=msg,
                parse_mode=ParseMode.MARKDOWN
            )
        elif edu[3] == 'video' and edu[4]:
            await update.message.reply_video(
                video=edu[4],
                caption=msg,
                parse_mode=ParseMode.MARKDOWN
            )
        elif edu[3] == 'document' and edu[4]:
            await update.message.reply_document(
                document=edu[4],
                caption=msg,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                msg,
                parse_mode=ParseMode.MARKDOWN
            )

# ==================== خرید اشتراک ====================
async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مراحل خرید اشتراک"""
    user_id = update.effective_user.id
    
    # بررسی اشتراک فعلی
    user = db.get_user(user_id)
    if user and user[4]:  # ستون ۴ = subscription_active
        expiry = user[5]
        if expiry:
            try:
                expiry_date = datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S')
                if expiry_date > datetime.now():
                    await update.message.reply_text(
                        f"✅ **شما قبلاً اشتراک فعال دارید!**\n\n"
                        f"📅 تاریخ انقضا: {expiry}\n\n"
                        "از آموزش‌های ما استفاده کنید و لذت ببرید! 🚀",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
                    return
            except:
                pass
    
    payment_text = f"""
💳 **خرید اشتراک آموزش ترید**

💰 مبلغ: **{PRICE_USD} دلار** (دسترسی دائمی)

📌 **مراحل پرداخت:**

1️⃣ مبلغ {PRICE_USD} دلار (معادل تتر USDT) به آدرس زیر واریز کنید:

🔗 **آدرس کیف پول (TRC20):**
`{WALLET_ADDRESS}`

2️⃣ **حتماً** از رسید تراکنش عکس بگیرید.

3️⃣ عکس رسید را برای ربات ارسال کنید.

⚠️ **توجه:**
• حتماً از شبکه **TRC20** استفاده کنید.
• مبلغ دقیقاً {PRICE_USD} دلار باشد.
• پس از تایید پرداخت، اشتراک شما فعال می‌شود.

✅ پس از واریز، عکس رسید را **همینجا** ارسال کنید.
    """
    
    await update.message.reply_text(
        payment_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    
    # وارد حالت انتظار برای دریافت عکس
    context.user_data['waiting_for_payment'] = True
    return WAITING_FOR_PAYMENT_PHOTO

async def handle_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت عکس فیش پرداخت"""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]  # بهترین کیفیت
    caption = update.message.caption
    
    if not caption:
        await update.message.reply_text(
            "❌ لطفاً هش تراکنش (TxID) را به همراه عکس ارسال کنید.\n"
            "مثال: ارسال عکس + TxID",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
        return WAITING_FOR_PAYMENT_PHOTO
    
    # استخراج TxID از کپشن
    tx_hash = caption.strip()
    if len(tx_hash) < 10:  # بررسی ساده
        await update.message.reply_text(
            "❌ هش تراکنش نامعتبر است. لطفاً مجدداً ارسال کنید.",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_FOR_PAYMENT_PHOTO
    
    # ثبت در دیتابیس
    payment_id = db.add_payment(
        user_id=user_id,
        amount=PRICE_USD,
        tx_hash=tx_hash,
        photo_file_id=photo.file_id
    )
    
    if payment_id:
        # ارسال به ادمین‌ها
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo.file_id,
                    caption=f"""
💰 **فیش پرداخت جدید!**

👤 کاربر: {update.effective_user.first_name} {update.effective_user.last_name}
🆔 آیدی: {user_id}
📱 یوزرنیم: @{update.effective_user.username if update.effective_user.username else 'ندارد'}
💵 مبلغ: {PRICE_USD} دلار
🔗 هش: {tx_hash}
📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

📌 برای تایید یا رد، از دکمه‌های زیر استفاده کنید:
                    """,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=admin_payment_buttons(payment_id)
                )
            except Exception as e:
                logger.error(f"خطا در ارسال به ادمین {admin_id}: {e}")
        
        # پیام به کاربر - اصلاح شد
        await update.message.reply_text(
            "✅ **فیش شما با موفقیت ثبت شد!** 💰\n\n"
            "📋 فیش شما برای بررسی به مدیریت ارسال شد.\n"
            "⏱ فرآیند بررسی معمولاً **حداکثر ۲ ساعت** طول می‌کشد.\n\n"
            "🔔 پس از تایید، به شما اطلاع داده می‌شود.\n"
            "📊 می‌توانید وضعیت اشتراک خود را از دکمه **وضعیت اشتراک** بررسی کنید.\n\n"
            "🙏 از صبر و شکیبایی شما سپاسگزاریم.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت فیش! لطفاً دوباره تلاش کنید.",
            reply_markup=main_menu_keyboard()
        )
    
    context.user_data['waiting_for_payment'] = False
    return ConversationHandler.END

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بررسی وضعیت اشتراک"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ کاربر یافت نشد! لطفاً دوباره استارت بزنید.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    if user[4]:  # ستون ۴ = subscription_active
        expiry = user[5]
        if expiry:
            try:
                expiry_date = datetime.strptime(expiry, '%Y-%m-%d %H:%M:%S')
                if expiry_date > datetime.now():
                    days_left = (expiry_date - datetime.now()).days
                    await update.message.reply_text(
                        f"✅ **اشتراک شما فعال است!**\n\n"
                        f"📅 زمان باقی‌مانده: {days_left} روز\n"
                        f"📆 تاریخ انقضا: {expiry}\n\n"
                        "از آموزش‌های ما استفاده کنید و موفق باشید! 🚀",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
                else:
                    # اشتراک منقضی شده
                    await update.message.reply_text(
                        f"⏰ **اشتراک شما منقضی شده است!**\n\n"
                        f"برای تمدید، از دکمه **💳 خرید اشتراک** استفاده کنید.\n\n"
                        f"💰 هزینه: {PRICE_USD} دلار",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
            except:
                await update.message.reply_text(
                    f"✅ **اشتراک شما فعال است!**\n\n"
                    "از آموزش‌های ما استفاده کنید و موفق باشید! 🚀",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_keyboard()
                )
        else:
            await update.message.reply_text(
                f"✅ **اشتراک شما فعال است!** (دسترسی دائمی)\n\n"
                "از آموزش‌های ما استفاده کنید و موفق باشید! 🚀",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ **شما اشتراک فعال ندارید!**\n\n"
            f"برای دسترسی به آموزش‌ها، اشتراک تهیه کنید.\n"
            f"💰 هزینه: {PRICE_USD} دلار\n\n"
            "از دکمه **💳 خرید اشتراک** استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )

# ==================== مشاوره و سوال ====================
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پرسش سوال از مشاور"""
    await update.message.reply_text(
        "❓ **مشاوره و سوال تخصصی**\n\n"
        "سوال خود را بنویسید. کارشناسان ما در اسرع وقت پاسخ می‌دهند.\n\n"
        "📌 **نکته:** لطفاً سوال خود را دقیق و کامل مطرح کنید.\n"
        "🔍 همچنین می‌توانید از **آموزش سوال و جواب** استفاده کنید.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    context.user_data['waiting_for_question'] = True
    return WAITING_USER_QUESTION

async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت سوال کاربر"""
    user_id = update.effective_user.id
    question = update.message.text
    
    # ثبت سوال در دیتابیس
    q_id = db.add_user_question(user_id, question)
    
    if q_id:
        # ارسال به ادمین‌ها
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"""
❓ **سوال جدید از کاربر:**

👤 کاربر: {update.effective_user.first_name} {update.effective_user.last_name}
🆔 آیدی: {user_id}
📱 یوزرنیم: @{update.effective_user.username if update.effective_user.username else 'ندارد'}

📝 **سوال:**
{question}

✅ برای پاسخ، از پنل مدیریت استفاده کنید.
                    """,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"خطا در ارسال سوال به ادمین {admin_id}: {e}")
        
        # جستجو در FAQ
        faq_results = db.search_faq(question)
        if faq_results:
            reply = "🤖 **سوالات مشابه در آموزش سوال و جواب:**\n\n"
            for q, a in faq_results[:3]:
                reply += f"❓ {q}\n✅ {a}\n\n"
            reply += "\nاگر پاسخ شما کامل نبود، کارشناسان ما پاسخ کامل را ارسال خواهند کرد."
            
            await update.message.reply_text(
                reply,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "✅ **سوال شما ثبت شد!**\n\n"
                "کارشناسان ما در اسرع وقت پاسخ می‌دهند.\n"
                "⏱ زمان پاسخگویی: حداکثر ۲۴ ساعت",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت سوال! لطفاً دوباره تلاش کنید.",
            reply_markup=main_menu_keyboard()
        )
    
    context.user_data['waiting_for_question'] = False
    return ConversationHandler.END

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پشتیبانی"""
    await update.message.reply_text(
        "📞 **پشتیبانی**\n\n"
        "در صورت هرگونه مشکل یا سوال، می‌توانید:\n\n"
        "1️⃣ از دکمه **❓ مشاوره و سوال** استفاده کنید.\n"
        "2️⃣ با ادمین تماس بگیرید: @YourAdminUsername\n"
        "3️⃣ ایمیل: support@example.com\n\n"
        "⏱ ساعات پاسخگویی: ۹ صبح تا ۱۲ شب",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )

# ==================== پنل مدیریت ====================
async def show_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش فیش‌های پرداخت"""
    if not is_admin(update.effective_user.id):
        return
    
    payments = db.get_pending_payments()
    
    if not payments:
        await update.message.reply_text(
            "✅ **هیچ فیش در انتظار تاییدی وجود ندارد.**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        return
    
    for payment in payments:
        text = f"""
💰 **فیش شماره: {payment['id']}**

👤 کاربر: {payment['last_name']} {payment['first_name']} 
📱 یوزرنیم: @{payment['username'] if payment['username'] else 'ندارد'}
🆔 آیدی کاربر: {payment['user_id']}

💵 مبلغ: {payment['amount']} دلار
🔗 هش تراکنش: `{payment['tx_hash']}`
📅 تاریخ ثبت: {payment['created_at']}

📊 وضعیت: ⏳ در انتظار تایید
        """
        
        # ارسال عکس فیش
        try:
            await update.message.reply_photo(
                photo=payment['photo_file_id'],
                caption=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_payment_buttons(payment['id'])
            )
        except Exception as e:
            logger.error(f"خطا در ارسال فیش: {e}")
            await update.message.reply_text(
                text + "\n\n⚠️ عکس قابل نمایش نیست.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_payment_buttons(payment['id'])
            )
    
    await update.message.reply_text(
        "📌 برای تایید یا رد هر فیش، از دکمه‌های زیر هر پیام استفاده کنید.",
        reply_markup=admin_panel_keyboard()
    )

async def handle_payment_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت تایید/رد فیش"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    data = query.data
    parts = data.split('_')
    action = parts[1]
    payment_id = int(parts[2])
    
    if action == 'confirm':
        result = db.confirm_payment(payment_id)
        if result:
            # ارسال پیام تایید به کاربر
            await query.edit_message_text(
                f"✅ **فیش شماره {payment_id} تایید شد!**\n\n"
                "اشتراک کاربر فعال شد.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # ارسال پیام به کاربر
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM payments WHERE id = ?", (payment_id,))
                user_id_result = cur.fetchone()
                cur.close()
                conn.close()
                
                if user_id_result:
                    await context.bot.send_message(
                        chat_id=user_id_result[0],
                        text="""
🎉 **تبریک! پرداخت شما تایید شد!** ✅

✅ **اشتراک شما با موفقیت فعال شد!**
📚 به تمام محتوای آموزشی دسترسی کامل دارید.

🚀 همین حالا از دکمه **📚 آموزش ترید** استفاده کنید و مسیر حرفه‌ای شدن را شروع کنید!

📌 نکات مهم:
• تمام آموزش‌ها به صورت دائمی در دسترس شماست
• به‌روزرسانی‌های جدید رایگان خواهد بود
• در صورت نیاز به مشاوره، از دکمه **❓ مشاوره و سوال** استفاده کنید

🌟 **آینده مالی خود را بسازید!**
موفق و پرسود باشید! 💰
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام تایید به کاربر: {e}")
        else:
            await query.edit_message_text(
                f"❌ خطا در تایید فیش شماره {payment_id}!",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif action == 'reject':
        result = db.reject_payment(payment_id)
        if result:
            await query.edit_message_text(
                f"❌ **فیش شماره {payment_id} رد شد!**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # ارسال پیام به کاربر
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM payments WHERE id = ?", (payment_id,))
                user_id_result = cur.fetchone()
                cur.close()
                conn.close()
                
                if user_id_result:
                    await context.bot.send_message(
                        chat_id=user_id_result[0],
                        text="""
❌ **پرداخت شما متاسفانه رد شد!**

دلایل احتمالی رد پرداخت:
• مبلغ واریزی نادرست است (باید دقیقاً ۵۰۰ دلار باشد)
• شبکه اشتباه است (باید حتماً TRC20 باشد)
• عکس رسید واضح و خوانا نیست
• هش تراکنش (TxID) نامعتبر است

📌 **راه حل:**
لطفاً مجدداً از دکمه **💳 خرید اشتراک** استفاده کنید و مراحل را دقیقاً طبق راهنما انجام دهید.

🔍 اگر فکر می‌کنید اشتباهی رخ داده، با پشتیبانی تماس بگیرید.

موفق باشید! 🙏
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام رد به کاربر: {e}")
        else:
            await query.edit_message_text(
                f"❌ خطا در رد فیش شماره {payment_id}!",
                parse_mode=ParseMode.MARKDOWN
            )

# ==================== ارسال آموزش از پنل ====================
async def start_add_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع افزودن محتوای آموزشی"""
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text(
        "📝 **افزودن محتوای آموزشی جدید**\n\n"
        "لطفاً **عنوان** آموزش را وارد کنید:\n"
        "(مثال: تحلیل تکنیکال مقدماتی)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    return WAITING_EDU_TITLE

async def handle_edu_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت عنوان آموزش"""
    context.user_data['edu_title'] = update.message.text
    
    await update.message.reply_text(
        "📝 **متن آموزش را وارد کنید:**\n\n"
        "(توضیحات کامل، می‌تواند شامل لینک، کد، و ... باشد)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    return WAITING_EDU_CONTENT

async def handle_edu_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت متن آموزش"""
    context.user_data['edu_content'] = update.message.text
    
    await update.message.reply_text(
        "📎 **نوع فایل ضمیمه را انتخاب کنید:**\n\n"
        "1️⃣ عکس ارسال کنید\n"
        "2️⃣ ویدئو ارسال کنید\n"
        "3️⃣ فایل (PDF/Word/Excel) ارسال کنید\n"
        "4️⃣ بدون فایل (فقط متن)\n\n"
        "⚠️ اگر فایلی ندارید، فقط **لغو** را بزنید.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    return WAITING_EDU_MEDIA

async def handle_edu_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت فایل ضمیمه آموزش"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
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
        # بدون فایل
        media_type = 'text'
    
    # ذخیره در دیتابیس
    edu_id = db.add_education_content(
        title=title,
        content=content,
        media_type=media_type,
        media_file_id=media_file_id
    )
    
    if edu_id:
        await update.message.reply_text(
            f"✅ **آموزش با موفقیت ثبت شد!**\n\n"
            f"📌 عنوان: {title}\n"
            f"🆔 شناسه: {edu_id}\n\n"
            "📤 در حال ارسال به کاربران دارای اشتراک...",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        
        # ارسال به تمام کاربران دارای اشتراک
        subscribed_users = db.get_subscribed_users()
        total = len(subscribed_users)
        success_count = 0
        
        if total > 0:
            # ارسال گروهی با تاخیر برای جلوگیری از محدودیت
            for i, user_id in enumerate(subscribed_users):
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
                    success_count += 1
                    
                    # تاخیر بین هر ۱۰ پیام برای جلوگیری از محدودیت
                    if (i + 1) % 10 == 0:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"خطا در ارسال به کاربر {user_id}: {e}")
                    await asyncio.sleep(0.5)  # تاخیر بیشتر در صورت خطا
            
            await update.message.reply_text(
                f"📊 **گزارش ارسال:**\n\n"
                f"👥 کل کاربران دارای اشتراک: {total}\n"
                f"✅ ارسال موفق: {success_count}\n"
                f"❌ ارسال ناموفق: {total - success_count}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_panel_keyboard()
            )
        else:
            await update.message.reply_text(
                "⚠️ **هیچ کاربر دارای اشتراکی وجود ندارد!**\n\n"
                "آموزش در دیتابیس ذخیره شد اما به کسی ارسال نشد.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_panel_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت آموزش! لطفاً دوباره تلاش کنید.",
            reply_markup=admin_panel_keyboard()
        )
    
    # پاک کردن داده‌های موقت
    context.user_data.pop('edu_title', None)
    context.user_data.pop('edu_content', None)
    return ConversationHandler.END

async def cancel_edu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انصراف از افزودن آموزش"""
    if not is_admin(update.effective_user.id):
        return
    
    context.user_data.clear()
    await update.message.reply_text(
        "❌ عملیات افزودن آموزش لغو شد.",
        reply_markup=admin_panel_keyboard()
    )
    return ConversationHandler.END

# ==================== پیام همگانی ====================
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع پیام همگانی"""
    if not is_admin(update.effective_user.id):
        return
    
    users = db.get_all_users()
    total = len(users)
    
    await update.message.reply_text(
        f"📢 **ارسال پیام همگانی**\n\n"
        f"لطفاً پیام مورد نظر برای ارسال به **همه کاربران** را وارد کنید:\n\n"
        f"⚠️ این پیام برای تمام **{total} کاربر** ارسال می‌شود.\n\n"
        "می‌توانید از **متن، عکس، ویدئو یا فایل** استفاده کنید.\n\n"
        "⏱ زمان تقریبی: چند دقیقه",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    return WAITING_BROADCAST_MESSAGE

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام همگانی"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    # دریافت تمام کاربران
    users = db.get_all_users()
    total_users = len(users)
    
    await update.message.reply_text(
        f"📤 **در حال ارسال پیام به {total_users} کاربر...**\n\n"
        "⏳ لطفاً صبر کنید...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    success_count = 0
    for i, user in enumerate(users):
        try:
            if update.message.photo:
                await context.bot.send_photo(
                    chat_id=user['user_id'],
                    photo=update.message.photo[-1].file_id,
                    caption=update.message.caption if update.message.caption else ""
                )
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=user['user_id'],
                    video=update.message.video.file_id,
                    caption=update.message.caption if update.message.caption else ""
                )
            elif update.message.document:
                await context.bot.send_document(
                    chat_id=user['user_id'],
                    document=update.message.document.file_id,
                    caption=update.message.caption if update.message.caption else ""
                )
            else:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text=update.message.text,
                    parse_mode=ParseMode.MARKDOWN
                )
            success_count += 1
            
            # تاخیر برای جلوگیری از محدودیت
            if (i + 1) % 10 == 0:
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"خطا در ارسال به کاربر {user['user_id']}: {e}")
            await asyncio.sleep(0.5)
    
    await update.message.reply_text(
        f"📊 **گزارش ارسال پیام همگانی:**\n\n"
        f"👥 کل کاربران: {total_users}\n"
        f"✅ ارسال موفق: {success_count}\n"
        f"❌ ارسال ناموفق: {total_users - success_count}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    
    return ConversationHandler.END

# ==================== آمار کاربران ====================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کاربران"""
    if not is_admin(update.effective_user.id):
        return
    
    stats = db.get_stats()
    
    stats_text = f"""
📊 **آمار جامع کاربران**

👥 **تعداد کل کاربران:** {stats['total_users']:,}
✅ **کاربران دارای اشتراک:** {stats['subscribed_users']:,}
❌ **کاربران بدون اشتراک:** {stats['total_users'] - stats['subscribed_users']:,}

💰 **آمار مالی:**
• فیش‌های در انتظار تایید: {stats['pending_payments']}
• تعداد کل پرداخت‌ها: {stats['total_payments']}
• مجموع درآمد: **{stats['total_earnings']:,} دلار**

📈 **نرخ تبدیل:** {round((stats['subscribed_users'] / stats['total_users'] * 100) if stats['total_users'] > 0 else 0, 2)}%

📅 **آخرین به‌روزرسانی:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔹 **وضعیت سیستم:** ✅ فعال
🔹 **تعداد شاردینگ‌ها:** {MAX_WORKERS}
🔹 **ظرفیت:** تا ۱۰,۰۰۰ کاربر
    """
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )

# ==================== سوال و جواب (FAQ) ====================
async def start_add_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع افزودن سوال و جواب"""
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text(
        "❓ **افزودن سوال و جواب جدید**\n\n"
        "لطفاً **سوال** را وارد کنید:\n"
        "(مثال: تحلیل تکنیکال چیست؟)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    return WAITING_FAQ_QUESTION

async def handle_faq_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت سوال FAQ"""
    context.user_data['faq_question'] = update.message.text
    
    await update.message.reply_text(
        "📝 **جواب را وارد کنید:**\n\n"
        "(پاسخ کامل و دقیق)",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    return WAITING_FAQ_ANSWER

async def handle_faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت جواب FAQ"""
    context.user_data['faq_answer'] = update.message.text
    
    await update.message.reply_text(
        "🔑 **کلمات کلیدی را وارد کنید (با کاما جدا کنید):**\n\n"
        "مثال: تحلیل تکنیکال, پرایس اکشن, اندیکاتور\n\n"
        "این کلمات به جستجوی بهتر کمک می‌کنند.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )
    return WAITING_FAQ_KEYWORDS

async def handle_faq_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت کلمات کلیدی FAQ"""
    keywords = [kw.strip() for kw in update.message.text.split(',')]
    question = context.user_data.get('faq_question')
    answer = context.user_data.get('faq_answer')
    
    # ذخیره در دیتابیس
    result = db.add_faq(question, answer, keywords)
    
    if result:
        await update.message.reply_text(
            f"✅ **سوال و جواب با موفقیت ثبت شد!**\n\n"
            f"❓ سوال: {question}\n"
            f"🔑 کلمات کلیدی: {', '.join(keywords)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت سوال و جواب! لطفاً دوباره تلاش کنید.",
            reply_markup=admin_panel_keyboard()
        )
    
    context.user_data.pop('faq_question', None)
    context.user_data.pop('faq_answer', None)
    return ConversationHandler.END

# ==================== سوالات کاربران (ادمین) ====================
async def show_user_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش سوالات کاربران برای ادمین"""
    if not is_admin(update.effective_user.id):
        return
    
    questions = db.get_pending_user_questions()
    
    if not questions:
        await update.message.reply_text(
            "✅ **هیچ سوال در انتظار پاسخی وجود ندارد.**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        return
    
    for q in questions:
        text = f"""
❓ **سوال کاربر:**

👤 کاربر: {q['last_name']} {q['first_name']} 
📱 یوزرنیم: @{q['username'] if q['username'] else 'ندارد'}
🆔 آیدی: {q['user_id']}

📝 **سوال:**
{q['question']}

📅 تاریخ: {q['created_at']}

📌 برای پاسخ، روی دکمه زیر کلیک کنید.
        """
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 پاسخ دادن", callback_data=f"answer_question_{q['id']}")]
            ])
        )
    
    await update.message.reply_text(
        "📌 برای پاسخ به هر سوال، روی دکمه زیر کلیک کنید.",
        reply_markup=admin_panel_keyboard()
    )

async def handle_question_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به سوال کاربر توسط ادمین"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    q_id = int(query.data.split('_')[2])
    context.user_data['answering_question_id'] = q_id
    
    await query.edit_message_text(
        "📝 **پاسخ خود را وارد کنید:**\n\n"
        "پاسخ شما به کاربر ارسال خواهد شد.",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_ANSWER_QUESTION

async def handle_answer_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت پاسخ از ادمین و ارسال به کاربر"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    q_id = context.user_data.get('answering_question_id')
    answer = update.message.text
    
    # ذخیره پاسخ در دیتابیس
    result = db.answer_user_question(q_id, answer)
    
    if result:
        # دریافت اطلاعات سوال
        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT user_id, question FROM user_questions WHERE id = ?", (q_id,))
        q_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if q_data:
            # ارسال پاسخ به کاربر
            try:
                await context.bot.send_message(
                    chat_id=q_data[0],
                    text=f"""
✅ **پاسخ به سوال شما:**

📝 **سوال شما:**
{q_data[1]}

📌 **پاسخ کارشناس:**
{answer}

🌟 **موفق و پرسود باشید!** 🚀
                    """,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_keyboard()
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پاسخ به کاربر: {e}")
        
        await update.message.reply_text(
            "✅ **پاسخ با موفقیت ارسال شد!**",
            reply_markup=admin_panel_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ارسال پاسخ!",
            reply_markup=admin_panel_keyboard()
        )
    
    context.user_data.pop('answering_question_id', None)
    return ConversationHandler.END

# ==================== بازگشت به پنل مدیریت ====================
async def back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به پنل مدیریت"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    await query.edit_message_text(
        "👑 **پنل مدیریت**\n\n"
        "از دکمه‌های زیر استفاده کنید:",
        reply_markup=admin_panel_keyboard()
    )

# ==================== اصلی ====================
def main():
    """راه‌اندازی ربات"""
    # ایجاد اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # ===== هندلرهای استارت و منو =====
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # ===== هندلر منوی اصلی =====
    application.add_handler(MessageHandler(
        filters.Regex("^(📖 راهنمایی|📚 آموزش ترید|💳 خرید اشتراک|📊 وضعیت اشتراک|❓ مشاوره و سوال|📞 پشتیبانی|👑 پنل مدیریت|🔙 خروج از پنل مدیریت|💰 فیش‌ها|📝 ارسال متن آموزش|📢 پیام همگانی|📊 آمار کاربران|❓ آموزش سوال و جواب|📋 سوالات کاربران)$"),
        handle_main_menu
    ))
    
    # ===== پرداخت =====
    payment_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💳 خرید اشتراک$"), buy_subscription)],
        states={
            WAITING_FOR_PAYMENT_PHOTO: [
                MessageHandler(filters.PHOTO & filters.CAPTION, handle_payment_photo)
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel_edu)]
    )
    application.add_handler(payment_conv)
    
    # ===== سوال کاربر =====
    question_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❓ مشاوره و سوال$"), ask_question)],
        states={
            WAITING_USER_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_question)
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel_edu)]
    )
    application.add_handler(question_conv)
    
    # ===== آموزش (ادمین) =====
    edu_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 ارسال متن آموزش$"), start_add_education)],
        states={
            WAITING_EDU_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edu_title)
            ],
            WAITING_EDU_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edu_content)
            ],
            WAITING_EDU_MEDIA: [
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.TEXT, handle_edu_media)
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel_edu)]
    )
    application.add_handler(edu_conv)
    
    # ===== پیام همگانی =====
    broadcast_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📢 پیام همگانی$"), start_broadcast)],
        states={
            WAITING_BROADCAST_MESSAGE: [
                MessageHandler(filters.ALL & ~filters.COMMAND, handle_broadcast)
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel_edu)]
    )
    application.add_handler(broadcast_conv)
    
    # ===== سوال و جواب (ادمین) =====
    faq_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❓ آموزش سوال و جواب$"), start_add_faq)],
        states={
            WAITING_FAQ_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_faq_question)
            ],
            WAITING_FAQ_ANSWER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_faq_answer)
            ],
            WAITING_FAQ_KEYWORDS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_faq_keywords)
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel_edu)]
    )
    application.add_handler(faq_conv)
    
    # ===== پاسخ به سوال کاربر (ادمین) =====
    answer_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_question_answer, pattern="^answer_question_")],
        states={
            WAITING_ANSWER_QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer_text)
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel_edu)]
    )
    application.add_handler(answer_conv)
    
    # ===== کالبک‌های دکمه‌ها =====
    application.add_handler(CallbackQueryHandler(handle_payment_action, pattern="^(confirm_payment_|reject_payment_)"))
    application.add_handler(CallbackQueryHandler(back_to_admin, pattern="^back_to_admin$"))
    
    # ===== راه‌اندازی =====
    print("=" * 60)
    print("🚀 ربات آموزش ترید حرفه‌ای")
    print("=" * 60)
    print(f"📁 دیتابیس: trading_bot.db")
    print(f"👤 ادمین‌ها: {ADMIN_IDS}")
    print(f"⚡ شاردینگ‌ها: {MAX_WORKERS}")
    print(f"👥 ظرفیت: ۱۰,۰۰۰ کاربر")
    print("=" * 60)
    print("✅ ربات در حال اجراست...")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()