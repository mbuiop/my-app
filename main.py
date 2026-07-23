"""
ربات آموزش ترید حرفه‌ای - نسخه نهایی با سیستم رفرال و درآمدزایی
پشتیبانی از ۱۰۰,۰۰۰ کاربر با شاردینگ پیشرفته
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
BOT_USERNAME = "UTYOB_Bot"  # یوزرنیم ربات بدون @
ADMIN_IDS = [123456789]  # آیدی عددی ادمین‌ها
WALLET_ADDRESS = "TSED8mCkfaNtavaBw2pQQpUoMRKGCwBsv3"
PRICE_USD = 500
REFERRAL_BONUS = 50  # پاداش هر رفرال
MIN_WITHDRAW = 500  # حداقل مبلغ برای برداشت

# تنظیمات شاردینگ برای ۱۰۰,۰۰۰ کاربر
MAX_WORKERS = 50  # تعداد شاردینگ‌ها
BATCH_SIZE = 200  # ارسال گروهی
CACHE_SIZE = 1000  # کش کاربران

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
                referral_code TEXT UNIQUE,
                referrer_id INTEGER,
                balance REAL DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
                total_earnings REAL DEFAULT 0,
                total_withdrawn REAL DEFAULT 0,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id)
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

        # جدول رفرال‌ها
        cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                bonus_amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TEXT,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        """)

        # جدول درخواست‌های برداشت
        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                wallet_address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                admin_note TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # جدول تراکنش‌های مالی
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount REAL,
                description TEXT,
                balance_after REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ تمام جدول‌ها با موفقیت ساخته شدند")

    # ===== متدهای کاربر با قفل =====
    def add_user(self, user_id, username, first_name, last_name, referrer_id=None):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                is_admin = 1 if user_id in ADMIN_IDS else 0
                
                # تولید کد رفرال اختصاصی
                referral_code = self.generate_referral_code(user_id)
                
                cur.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, is_admin, referral_code, referrer_id, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, username, first_name, last_name, is_admin, referral_code, referrer_id))
                conn.commit()
                
                # اگر کاربر با رفرال آمده، پاداش بده
                if referrer_id:
                    self.add_referral_bonus(referrer_id, user_id)
                
                return True
            except Exception as e:
                logger.error(f"خطا در افزودن کاربر: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    def generate_referral_code(self, user_id):
        """تولید کد رفرال منحصر به فرد"""
        # ترکیبی از آیدی کاربر و کاراکترهای تصادفی
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{user_id}{random_part}"

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

    def get_all_users(self, limit=None, offset=0):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            query = """
                SELECT user_id, username, first_name, last_name, 
                       subscription_active, subscription_expiry,
                       registered_at, last_active, is_admin,
                       referral_code, referrer_id, balance,
                       total_referrals, total_earnings, total_withdrawn
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

    # ===== متدهای رفرال =====
    def add_referral_bonus(self, referrer_id, referred_id):
        """افزودن پاداش رفرال"""
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                # ثبت رفرال
                cur.execute("""
                    INSERT INTO referrals (referrer_id, referred_id, bonus_amount, status)
                    VALUES (?, ?, ?, 'pending')
                """, (referrer_id, referred_id, REFERRAL_BONUS))
                
                # افزایش موجودی کاربر
                cur.execute("""
                    UPDATE users 
                    SET balance = balance + ?,
                        total_referrals = total_referrals + 1,
                        total_earnings = total_earnings + ?
                    WHERE user_id = ?
                """, (REFERRAL_BONUS, REFERRAL_BONUS, referrer_id))
                
                # ثبت تراکنش
                cur.execute("""
                    INSERT INTO transactions (user_id, type, amount, description, balance_after)
                    SELECT ?, 'referral_bonus', ?, ?, balance
                    FROM users WHERE user_id = ?
                """, (referrer_id, REFERRAL_BONUS, f"پاداش رفرال کاربر {referred_id}", referrer_id))
                
                conn.commit()
                
                # تایید خودکار رفرال
                cur.execute("""
                    UPDATE referrals 
                    SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP
                    WHERE referrer_id = ? AND referred_id = ?
                """, (referrer_id, referred_id))
                conn.commit()
                
                return True
            except Exception as e:
                logger.error(f"خطا در افزودن پاداش رفرال: {e}")
                return False
            finally:
                cur.close()
                conn.close()

    def get_user_referrals(self, user_id):
        """دریافت لیست رفرال‌های کاربر"""
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT r.*, u.username, u.first_name, u.last_name, u.registered_at
                FROM referrals r
                JOIN users u ON r.referred_id = u.user_id
                WHERE r.referrer_id = ? AND r.status = 'confirmed'
                ORDER BY r.created_at DESC
            """, (user_id,))
            result = cur.fetchall()
            cur.close()
            conn.close()
            return result

    def get_top_referrers(self, limit=10):
        """دریافت برترین رفرال‌دهنده‌ها"""
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

    # ===== متدهای برداشت =====
    def add_withdraw_request(self, user_id, amount, wallet_address):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                # بررسی موجودی
                cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
                user = cur.fetchone()
                if not user or user['balance'] < amount:
                    return False, "موجودی کافی نیست"
                
                if amount < MIN_WITHDRAW:
                    return False, f"حداقل مبلغ برداشت {MIN_WITHDRAW} دلار است"
                
                # ثبت درخواست برداشت
                cur.execute("""
                    INSERT INTO withdraw_requests (user_id, amount, wallet_address)
                    VALUES (?, ?, ?)
                """, (user_id, amount, wallet_address))
                
                # کاهش موجودی
                cur.execute("""
                    UPDATE users 
                    SET balance = balance - ?,
                        total_withdrawn = total_withdrawn + ?
                    WHERE user_id = ?
                """, (amount, amount, user_id))
                
                # ثبت تراکنش
                cur.execute("""
                    INSERT INTO transactions (user_id, type, amount, description, balance_after)
                    SELECT ?, 'withdraw', -?, ?, balance
                    FROM users WHERE user_id = ?
                """, (user_id, amount, f"درخواست برداشت {amount} دلار", user_id))
                
                conn.commit()
                return True, "درخواست برداشت با موفقیت ثبت شد"
            except Exception as e:
                logger.error(f"خطا در ثبت درخواست برداشت: {e}")
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

    def process_withdraw(self, withdraw_id, status, admin_note=None):
        with self.lock:
            conn = self.get_conn()
            cur = conn.cursor()
            try:
                cur.execute("""
                    UPDATE withdraw_requests 
                    SET status = ?, processed_at = CURRENT_TIMESTAMP, admin_note = ?
                    WHERE id = ?
                """, (status, admin_note, withdraw_id))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"خطا در پردازش برداشت: {e}")
                return False
            finally:
                cur.close()
                conn.close()

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
            
            cur.execute("SELECT COUNT(*) FROM referrals WHERE status = 'confirmed'")
            stats['total_referrals'] = cur.fetchone()[0]
            
            cur.execute("SELECT SUM(bonus_amount) FROM referrals WHERE status = 'confirmed'")
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
def main_menu_keyboard():
    """صفحه اصلی ربات با دکمه‌های جدید"""
    keyboard = [
        [KeyboardButton("📚 آموزش ترید"), KeyboardButton("📖 راهنمایی")],
        [KeyboardButton("💳 خرید اشتراک"), KeyboardButton("📊 وضعیت اشتراک")],
        [KeyboardButton("❓ مشاوره و سوال"), KeyboardButton("🎯 رفرال و درآمد")],
        [KeyboardButton("💰 برداشت"), KeyboardButton("📞 پشتیبانی")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_menu_keyboard():
    """پنل مدیریت - فقط برای ادمین‌ها"""
    keyboard = [
        [KeyboardButton("👑 پنل مدیریت")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_panel_keyboard():
    """دکمه‌های پنل مدیریت بعد از ورود"""
    keyboard = [
        [KeyboardButton("💰 فیش‌ها"), KeyboardButton("📝 ارسال متن آموزش")],
        [KeyboardButton("📢 پیام همگانی"), KeyboardButton("📊 آمار کاربران")],
        [KeyboardButton("❓ آموزش سوال و جواب"), KeyboardButton("📋 سوالات کاربران")],
        [KeyboardButton("💳 درخواست‌های برداشت"), KeyboardButton("🏆 برترین رفرال‌ها")],
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

def admin_withdraw_buttons(withdraw_id):
    """دکمه‌های تایید/رد برداشت"""
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید برداشت", callback_data=f"confirm_withdraw_{withdraw_id}"),
            InlineKeyboardButton("❌ رد برداشت", callback_data=f"reject_withdraw_{withdraw_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== وضعیت‌های مکالمه ====================
(WAITING_FOR_PAYMENT_PHOTO, 
 WAITING_EDU_TITLE, WAITING_EDU_CONTENT, WAITING_EDU_MEDIA,
 WAITING_FAQ_QUESTION, WAITING_FAQ_ANSWER, WAITING_FAQ_KEYWORDS,
 WAITING_USER_QUESTION,
 WAITING_BROADCAST_MESSAGE,
 WAITING_ANSWER_QUESTION,
 WAITING_WITHDRAW_ADDRESS,
 WAITING_WITHDRAW_AMOUNT) = range(12)

# ==================== توابع کمکی ====================
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ==================== پیام‌ها ====================
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
🔹 **تحلیل فاندامنتال**
🔹 **مدیریت ریسک و سرمایه**
🔹 **روانشناسی ترید**
🔹 **استراتژی‌های معاملاتی**
🔹 **تمرین عملی**

---

💰 **هزینه اشتراک ویژه:**
فقط {price} دلار - **دسترسی مادام‌العمر** به تمام محتواها!

🎁 **سیستم رفرال فوق‌العاده:**
با دعوت از دوستان خود، **۵۰ دلار** پاداش بگیرید!
هر کاربری که با لینک شما ثبت‌نام کند و اشتراک بخرد، به حساب شما اضافه می‌شود.

---

📌 **چطور شروع کنیم؟**

۱. روی دکمه **"📚 آموزش ترید"** کلیک کنید
۲. برای دسترسی کامل، روی **"💳 خرید اشتراک"** کلیک کنید
۳. برای کسب درآمد، روی **"🎯 رفرال و درآمد"** کلیک کنید
۴. برای برداشت پول، روی **"💰 برداشت"** کلیک کنید

---

**آماده‌اید تا به یک تریدر حرفه‌ای تبدیل شوید؟** 💪
"""

HELP_MESSAGE = """
🌟 **راهنمای کامل آکادمی ترید** 🌟

سلام دوست عزیز! 👋

خوشحالیم که به جمع تریدرهای حرفه‌ای ملحق شدید.

---

🎯 **چشم‌انداز ما:**
ما باور داریم که **هر کسی می‌تواند یک تریدر موفق باشد**، 
به شرطی که **اصول درست** را یاد بگیرد.

---

📚 **سرفصل‌های آموزشی:**

**۱. بازارهای مالی** 📊
**۲. تحلیل تکنیکال** 📈
**۳. تحلیل فاندامنتال** 📰
**۴. مدیریت ریسک** 🛡️
**۵. روانشناسی ترید** 🧠
**۶. استراتژی‌های حرفه‌ای** 🎯
**۷. تمرین عملی** 💻

---

💰 **سیستم رفرال و درآمدزایی:**

🎁 **چگونه درآمد کسب کنیم؟**

۱. لینک رفرال اختصاصی خود را دریافت کنید
۲. لینک را با دوستان خود به اشتراک بگذارید
۳. به ازای هر دوست که ثبت‌نام کند و اشتراک بخرد:
   - **۵۰ دلار** به حساب شما واریز می‌شود
   - بدون محدودیت! هر تعداد که می‌توانید دعوت کنید

۴. پس از جمع‌آوری **۵۰۰ دلار**، می‌توانید برداشت کنید

📊 **آمار شما:**
• تعداد رفرال‌ها: {referrals}
• درآمد کل: {earnings} دلار
• موجودی قابل برداشت: {balance} دلار

---

💎 **مزایای عضویت:**

✅ **دسترسی مادام‌العمر** به تمام محتواها
✅ **به‌روزرسانی‌های رایگان**
✅ **پشتیبانی VIP ۲۴/۷**
✅ **گروه اختصاصی** کاربران حرفه‌ای
✅ **سیستم رفرال** با پاداش بالا
✅ **امکان برداشت** درآمد

---

❓ **سوالات متداول:**

**س: چگونه لینک رفرال خود را دریافت کنم؟**
ج: روی دکمه **"🎯 رفرال و درآمد"** کلیک کنید.

**س: پاداش رفرال چقدر است؟**
ج: به ازای هر کاربر فعال، **۵۰ دلار** پاداش دریافت می‌کنید.

**س: چگونه برداشت کنم؟**
ج: پس از جمع‌آوری ۵۰۰ دلار، از دکمه **"💰 برداشت"** استفاده کنید.

**س: آیا محدودیتی برای رفرال وجود دارد؟**
ج: خیر، هر تعداد که می‌توانید دعوت کنید!

---

🎉 **تعهد ما به شما:**
ما متعهد هستیم که شما را به یک **تریدر مستقل و موفق** تبدیل کنیم.
با ما همراه شوید و آینده مالی خود را بسازید!

**موفقیت شما، هدف ماست!** 🏆

---

**همین حالا شروع کنید و به جمع تریدرهای برتر بپیوندید!** 🚀
"""

REFERRAL_MESSAGE = """
🎯 **سیستم رفرال و درآمدزایی** 🎯

سلام {first_name} عزیز! 👋

با سیستم رفرال ما، **همزمان با یادگیری ترید، درآمد هم کسب کنید!**

---

📊 **آمار شما:**
• 👥 تعداد رفرال‌ها: {referrals}
• 💰 درآمد کل: {earnings} دلار
• 🏦 موجودی قابل برداشت: {balance} دلار
• 🎯 رتبه شما: {rank}

---

🔗 **لینک رفرال اختصاصی شما:**

`https://t.me/{bot_username}?start=ref_{referral_code}`

📌 **نحوه استفاده:**
۱. این لینک را کپی کنید
۲. برای دوستان خود ارسال کنید
۳. به ازای هر دوست که ثبت‌نام کند و اشتراک بخرد:
   - **۵۰ دلار** به حساب شما اضافه می‌شود
   - بدون محدودیت!

---

🏆 **برترین رفرال‌دهنده‌ها:**

{top_referrers}

---

💡 **نکات کلیدی برای موفقیت:**
• لینک خود را در شبکه‌های اجتماعی منتشر کنید
• به دوستان خود توضیح دهید که چه مزایایی دارند
• از گروه‌های مرتبط با ترید استفاده کنید

---

💰 **حداقل مبلغ برداشت:** {min_withdraw} دلار

موفق و پرسود باشید! 🚀
"""

# ==================== هندلرهای ربات ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور استارت با پشتیبانی از رفرال"""
    user = update.effective_user
    args = context.args
    
    # بررسی رفرال
    referrer_id = None
    if args and args[0].startswith('ref_'):
        referral_code = args[0].replace('ref_', '')
        referrer_id = db.get_user_by_referral(referral_code)
    
    # ثبت کاربر در دیتابیس
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        referrer_id=referrer_id
    )
    
    # انتخاب منوی مناسب
    if is_admin(user.id):
        reply_markup = admin_menu_keyboard()
    else:
        reply_markup = main_menu_keyboard()
    
    # پیام خوش‌آمدگویی
    welcome_text = WELCOME_MESSAGE.format(
        first_name=user.first_name,
        price=PRICE_USD
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    
    # اگر با رفرال آمده، پیام تبریک بفرست
    if referrer_id:
        await update.message.reply_text(
            f"🎉 **تبریک!**\n\n"
            f"شما با لینک رفرال ثبت‌نام کردید!\n"
            f"اگر اشتراک تهیه کنید، دوست شما {REFERRAL_BONUS} دلار پاداش می‌گیرد!",
            parse_mode=ParseMode.MARKDOWN
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنمایی"""
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    referrals = user_data['total_referrals'] if user_data else 0
    earnings = user_data['total_earnings'] if user_data else 0
    balance = user_data['balance'] if user_data else 0
    
    help_text = HELP_MESSAGE.format(
        referrals=referrals,
        earnings=earnings,
        balance=balance
    )
    
    if is_admin(user.id):
        reply_markup = admin_menu_keyboard()
    else:
        reply_markup = main_menu_keyboard()
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# ==================== سیستم رفرال ====================
async def referral_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش سیستم رفرال"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ کاربر یافت نشد! لطفاً دوباره استارت بزنید.",
            reply_markup=main_menu_keyboard()
        )
        return
    
    # دریافت رفرال‌ها
    referrals = db.get_user_referrals(user_id)
    top_referrers = db.get_top_referrers(5)
    
    # رتبه کاربر
    rank = 1
    for i, ref in enumerate(top_referrers, 1):
        if ref['user_id'] == user_id:
            rank = i
            break
    
    # ساخت لیست برترین‌ها
    top_text = ""
    for i, ref in enumerate(top_referrers[:5], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        top_text += f"{medal} @{ref['username'] or 'کاربر'} - {ref['total_referrals']} نفر\n"
    
    if not top_text:
        top_text = "هنوز کسی رفرال نداشته است.\nشما می‌توانید اولین نفر باشید! 🚀"
    
    referral_text = REFERRAL_MESSAGE.format(
        first_name=user['first_name'],
        referrals=user['total_referrals'],
        earnings=user['total_earnings'],
        balance=user['balance'],
        rank=f"#{rank}" if rank else "بدون رتبه",
        bot_username=BOT_USERNAME,
        referral_code=user['referral_code'],
        top_referrers=top_text,
        min_withdraw=MIN_WITHDRAW
    )
    
    await update.message.reply_text(
        referral_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )

# ==================== سیستم برداشت ====================
async def withdraw_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند برداشت"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ کاربر یافت نشد!",
            reply_markup=main_menu_keyboard()
        )
        return
    
    if user['balance'] < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ **موجودی شما کافی نیست!**\n\n"
            f"💰 موجودی فعلی: {user['balance']} دلار\n"
            f"📌 حداقل مبلغ برداشت: {MIN_WITHDRAW} دلار\n\n"
            f"برای افزایش موجودی، از سیستم رفرال استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
        return
    
    await update.message.reply_text(
        f"💰 **برداشت از حساب**\n\n"
        f"موجودی قابل برداشت: {user['balance']} دلار\n"
        f"حداقل برداشت: {MIN_WITHDRAW} دلار\n\n"
        f"📌 **لطفاً آدرس کیف پول (TRC20) خود را وارد کنید:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    context.user_data['withdraw_step'] = 'waiting_address'
    return WAITING_WITHDRAW_ADDRESS

async def handle_withdraw_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت آدرس کیف پول برای برداشت"""
    user_id = update.effective_user.id
    wallet_address = update.message.text.strip()
    
    # بررسی ساده آدرس
    if len(wallet_address) < 20:
        await update.message.reply_text(
            "❌ آدرس کیف پول نامعتبر است! لطفاً مجدداً ارسال کنید.",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_WITHDRAW_ADDRESS
    
    context.user_data['wallet_address'] = wallet_address
    
    user = db.get_user(user_id)
    await update.message.reply_text(
        f"💰 **تایید برداشت**\n\n"
        f"مبلغ قابل برداشت: {user['balance']} دلار\n"
        f"حداقل برداشت: {MIN_WITHDRAW} دلار\n\n"
        f"📌 **مبلغ مورد نظر را وارد کنید:**",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    context.user_data['withdraw_step'] = 'waiting_amount'
    return WAITING_WITHDRAW_AMOUNT

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مبلغ برداشت"""
    user_id = update.effective_user.id
    try:
        amount = float(update.message.text.strip())
    except:
        await update.message.reply_text(
            "❌ مبلغ نامعتبر! لطفاً عدد وارد کنید.",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_WITHDRAW_AMOUNT
    
    user = db.get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        await update.message.reply_text(
            f"❌ حداقل مبلغ برداشت {MIN_WITHDRAW} دلار است!",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_WITHDRAW_AMOUNT
    
    if amount > user['balance']:
        await update.message.reply_text(
            f"❌ موجودی شما کافی نیست! (موجودی: {user['balance']} دلار)",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_WITHDRAW_AMOUNT
    
    wallet_address = context.user_data.get('wallet_address')
    
    # ثبت درخواست برداشت
    success, message = db.add_withdraw_request(user_id, amount, wallet_address)
    
    if success:
        # ارسال به ادمین
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"""
💰 **درخواست برداشت جدید!**

👤 کاربر: {user['first_name']} {user['last_name']}
🆔 آیدی: {user_id}
📱 یوزرنیم: @{user['username'] if user['username'] else 'ندارد'}

💵 مبلغ: {amount} دلار
🔗 آدرس کیف پول: `{wallet_address}`
💰 موجودی: {user['balance']} دلار

📌 برای تایید یا رد، از دکمه‌های زیر استفاده کنید:
                    """,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=admin_withdraw_buttons(1)  # ID رو باید بگیریم
                )
            except Exception as e:
                logger.error(f"خطا در ارسال به ادمین: {e}")
        
        await update.message.reply_text(
            f"✅ **درخواست برداشت با موفقیت ثبت شد!**\n\n"
            f"💰 مبلغ: {amount} دلار\n"
            f"🔗 آدرس: `{wallet_address}`\n\n"
            f"⏱ درخواست شما در حال بررسی است.\n"
            f"پس از تایید، مبلغ به کیف پول شما واریز خواهد شد.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            f"❌ خطا: {message}",
            reply_markup=main_menu_keyboard()
        )
    
    context.user_data.pop('withdraw_step', None)
    context.user_data.pop('wallet_address', None)
    return ConversationHandler.END

# ==================== سایر هندلرها ====================
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
    
    elif text == "🎯 رفرال و درآمد":
        await referral_system(update, context)
    
    elif text == "💰 برداشت":
        await withdraw_system(update, context)
    
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
        elif text == "💳 درخواست‌های برداشت":
            await show_withdraw_requests(update, context)
        elif text == "🏆 برترین رفرال‌ها":
            await show_top_referrers(update, context)
        else:
            await update.message.reply_text(
                "❌ گزینه نامعتبر!",
                reply_markup=admin_panel_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ گزینه نامعتبر!",
            reply_markup=main_menu_keyboard()
        )

# ==================== نمایش برترین رفرال‌ها (ادمین) ====================
async def show_top_referrers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش برترین رفرال‌دهنده‌ها برای ادمین"""
    if not is_admin(update.effective_user.id):
        return
    
    top = db.get_top_referrers(20)
    
    if not top:
        await update.message.reply_text(
            "📊 **هیچ رفرالی ثبت نشده است.**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        return
    
    text = "🏆 **برترین رفرال‌دهنده‌ها:**\n\n"
    for i, ref in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} @{ref['username'] or 'کاربر'} - {ref['total_referrals']} نفر | {ref['total_earnings']} دلار\n"
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=admin_panel_keyboard()
    )

# ==================== نمایش درخواست‌های برداشت (ادمین) ====================
async def show_withdraw_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش درخواست‌های برداشت برای ادمین"""
    if not is_admin(update.effective_user.id):
        return
    
    withdraws = db.get_pending_withdraws()
    
    if not withdraws:
        await update.message.reply_text(
            "✅ **هیچ درخواست برداشتی در انتظار نیست.**",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_panel_keyboard()
        )
        return
    
    for w in withdraws:
        text = f"""
💰 **درخواست برداشت #{w['id']}**

👤 کاربر: {w['last_name']} {w['first_name']}
🆔 آیدی: {w['user_id']}
📱 یوزرنیم: @{w['username'] if w['username'] else 'ندارد'}

💵 مبلغ: {w['amount']} دلار
🔗 آدرس: `{w['wallet_address']}`
💰 موجودی کاربر: {w['balance']} دلار

📅 تاریخ: {w['created_at']}
        """
        
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_withdraw_buttons(w['id'])
        )
    
    await update.message.reply_text(
        "📌 برای تایید یا رد هر درخواست، از دکمه‌ها استفاده کنید.",
        reply_markup=admin_panel_keyboard()
    )

# ==================== مدیریت برداشت (ادمین) ====================
async def handle_withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت تایید/رد برداشت"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ شما دسترسی ادمین ندارید!")
        return
    
    data = query.data
    parts = data.split('_')
    action = parts[1]
    withdraw_id = int(parts[2])
    
    if action == 'confirm':
        result = db.process_withdraw(withdraw_id, 'confirmed', 'تایید شد')
        if result:
            await query.edit_message_text(
                f"✅ **برداشت #{withdraw_id} تایید شد!**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # ارسال پیام به کاربر
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM withdraw_requests WHERE id = ?", (withdraw_id,))
                result = cur.fetchone()
                cur.close()
                conn.close()
                
                if result:
                    await context.bot.send_message(
                        chat_id=result['user_id'],
                        text=f"""
✅ **درخواست برداشت شما تایید شد!** 🎉

💰 مبلغ: {amount} دلار به کیف پول شما واریز شد.

🙏 از اعتماد شما سپاسگزاریم.
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام تایید برداشت: {e}")
        else:
            await query.edit_message_text(
                f"❌ خطا در تایید برداشت!",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif action == 'reject':
        result = db.process_withdraw(withdraw_id, 'rejected', 'رد شد')
        if result:
            await query.edit_message_text(
                f"❌ **برداشت #{withdraw_id} رد شد!**",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # برگرداندن موجودی
            try:
                conn = db.get_conn()
                cur = conn.cursor()
                cur.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (withdraw_id,))
                result = cur.fetchone()
                cur.close()
                conn.close()
                
                if result:
                    # برگرداندن موجودی
                    db.add_user_balance(result['user_id'], result['amount'])
                    
                    await context.bot.send_message(
                        chat_id=result['user_id'],
                        text=f"""
❌ **درخواست برداشت شما رد شد!**

متاسفانه درخواست برداشت شما تایید نشد.

دلایل احتمالی:
• آدرس کیف پول نامعتبر
• اطلاعات ناقص

لطفاً مجدداً از دکمه **💰 برداشت** استفاده کنید.
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
            except Exception as e:
                logger.error(f"خطا در برگرداندن موجودی: {e}")
        else:
            await query.edit_message_text(
                f"❌ خطا در رد برداشت!",
                parse_mode=ParseMode.MARKDOWN
            )

# ==================== آموزش (ادمین) ====================
async def show_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش محتوای آموزشی"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user or not user['subscription_active']:
        await update.message.reply_text(
            "🔒 **دسترسی محدود!**\n\n"
            "برای دسترسی به محتوای آموزشی کامل، لطفاً اشتراک تهیه کنید.\n\n"
            f"💰 هزینه اشتراک: {PRICE_USD} دلار\n"
            "از دکمه **💳 خرید اشتراک** استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
        return
    
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
        msg = f"📚 **{edu['title']}**\n\n{edu['content']}"
        
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
            await update.message.reply_text(
                msg,
                parse_mode=ParseMode.MARKDOWN
            )

# ==================== خرید اشتراک ====================
async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مراحل خرید اشتراک"""
    user_id = update.effective_user.id
    
    user = db.get_user(user_id)
    if user and user['subscription_active']:
        expiry = user['subscription_expiry']
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
    
    context.user_data['waiting_for_payment'] = True
    return WAITING_FOR_PAYMENT_PHOTO

async def handle_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت عکس فیش پرداخت"""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    caption = update.message.caption
    
    if not caption:
        await update.message.reply_text(
            "❌ لطفاً هش تراکنش (TxID) را به همراه عکس ارسال کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
        return WAITING_FOR_PAYMENT_PHOTO
    
    tx_hash = caption.strip()
    if len(tx_hash) < 10:
        await update.message.reply_text(
            "❌ هش تراکنش نامعتبر است!",
            reply_markup=main_menu_keyboard()
        )
        return WAITING_FOR_PAYMENT_PHOTO
    
    payment_id = db.add_payment(user_id, PRICE_USD, tx_hash, photo.file_id)
    
    if payment_id:
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

📌 برای تایید یا رد، از دکمه‌های زیر استفاده کنید:
                    """,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=admin_payment_buttons(payment_id)
                )
            except Exception as e:
                logger.error(f"خطا در ارسال به ادمین: {e}")
        
        await update.message.reply_text(
            "✅ **فیش شما با موفقیت ثبت شد!** 💰\n\n"
            "📋 فیش شما برای بررسی به مدیریت ارسال شد.\n"
            "⏱ فرآیند بررسی معمولاً **حداکثر ۲ ساعت** طول می‌کشد.\n\n"
            "🔔 پس از تایید، به شما اطلاع داده می‌شود.\n"
            "📊 می‌توانید وضعیت اشتراک خود را از دکمه **وضعیت اشتراک** بررسی کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت فیش!",
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
            "❌ کاربر یافت نشد!",
            reply_markup=main_menu_keyboard()
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
                        f"✅ **اشتراک شما فعال است!**\n\n"
                        f"📅 زمان باقی‌مانده: {days_left} روز\n"
                        f"📆 تاریخ انقضا: {expiry}\n\n"
                        "از آموزش‌های ما استفاده کنید! 🚀",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        f"⏰ **اشتراک شما منقضی شده است!**\n\n"
                        f"برای تمدید، از دکمه **💳 خرید اشتراک** استفاده کنید.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
            except:
                await update.message.reply_text(
                    f"✅ **اشتراک شما فعال است!** (دسترسی دائمی)\n\n"
                    "از آموزش‌های ما استفاده کنید! 🚀",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu_keyboard()
                )
        else:
            await update.message.reply_text(
                f"✅ **اشتراک شما فعال است!** (دسترسی دائمی)\n\n"
                "از آموزش‌های ما استفاده کنید! 🚀",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ **شما اشتراک فعال ندارید!**\n\n"
            f"💰 هزینه: {PRICE_USD} دلار\n\n"
            "از دکمه **💳 خرید اشتراک** استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )

# ==================== سایر هندلرها ====================
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ **مشاوره و سوال تخصصی**\n\n"
        "سوال خود را بنویسید. کارشناسان ما در اسرع وقت پاسخ می‌دهند.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )
    context.user_data['waiting_for_question'] = True
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
📝 سوال: {question}

برای پاسخ، از پنل مدیریت استفاده کنید.
                    """,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        await update.message.reply_text(
            "✅ **سوال شما ثبت شد!**\n\n"
            "کارشناسان ما در اسرع وقت پاسخ می‌دهند.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت سوال!",
            reply_markup=main_menu_keyboard()
        )
    
    context.user_data['waiting_for_question'] = False
    return ConversationHandler.END

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 **پشتیبانی**\n\n"
        "برای ارتباط با پشتیبانی:\n"
        "1️⃣ از دکمه **❓ مشاوره و سوال** استفاده کنید\n"
        "2️⃣ با ادمین تماس بگیرید: @YourAdmin\n\n"
        "⏱ ساعات پاسخگویی: ۹ صبح تا ۱۲ شب",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard()
    )

# ==================== پنل مدیریت ====================
async def show_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    payments = db.get_pending_payments()
    
    if not payments:
        await update.message.reply_text(
            "✅ **هیچ فیش در انتظار تاییدی نیست.**",
            reply_markup=admin_panel_keyboard()
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
        
        await update.message.reply_photo(
            photo=payment['photo_file_id'],
            caption=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_payment_buttons(payment['id'])
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
        result = db.confirm_payment(payment_id)
        if result:
            await query.edit_message_text(f"✅ **فیش #{payment_id} تایید شد!**")
            
            # ارسال پیام به کاربر
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
🎉 **تبریک! پرداخت شما تایید شد!** ✅

✅ اشتراک شما فعال شد!
📚 به تمام محتوای آموزشی دسترسی دارید.

🚀 موفق و پرسود باشید!
                        """,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu_keyboard()
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام تایید: {e}")
        else:
            await query.edit_message_text(f"❌ خطا در تایید فیش!")
    
    elif action == 'reject':
        result = db.reject_payment(payment_id)
        if result:
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
                        reply_markup=main_menu_keyboard()
                    )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام رد: {e}")
        else:
            await query.edit_message_text(f"❌ خطا در رد فیش!")

# ==================== سایر توابع مدیریت ====================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    stats = db.get_stats()
    
    text = f"""
📊 **آمار جامع کاربران**

👥 کاربران کل: {stats['total_users']:,}
✅ اشتراک فعال: {stats['subscribed_users']:,}
📈 نرخ تبدیل: {round((stats['subscribed_users'] / stats['total_users'] * 100) if stats['total_users'] > 0 else 0, 2)}%

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
        reply_markup=admin_panel_keyboard()
    )

async def start_add_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text(
        "📝 **افزودن آموزش جدید**\n\n"
        "عنوان را وارد کنید:",
        reply_markup=admin_panel_keyboard()
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
            f"✅ **آموزش ثبت شد!**\n\n"
            f"در حال ارسال به {len(db.get_subscribed_users())} کاربر...",
            reply_markup=admin_panel_keyboard()
        )
        
        # ارسال به کاربران دارای اشتراک
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
                if (i + 1) % 10 == 0:
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"خطا در ارسال به {user_id}: {e}")
        
        await update.message.reply_text(
            f"📊 **گزارش ارسال:**\n"
            f"✅ موفق: {success}\n"
            f"❌ ناموفق: {len(subscribed) - success}",
            reply_markup=admin_panel_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت آموزش!",
            reply_markup=admin_panel_keyboard()
        )
    
    context.user_data.pop('edu_title', None)
    context.user_data.pop('edu_content', None)
    return ConversationHandler.END

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    users = db.get_all_users()
    await update.message.reply_text(
        f"📢 **پیام همگانی به {len(users)} کاربر**\n\n"
        "پیام خود را ارسال کنید:",
        reply_markup=admin_panel_keyboard()
    )
    return WAITING_BROADCAST_MESSAGE

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
            if (i + 1) % 10 == 0:
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"خطا در ارسال به {user['user_id']}: {e}")
    
    await update.message.reply_text(
        f"📊 **گزارش ارسال:**\n"
        f"✅ موفق: {success}\n"
        f"❌ ناموفق: {total - success}",
        reply_markup=admin_panel_keyboard()
    )
    return ConversationHandler.END

async def start_add_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text(
        "❓ **افزودن سوال و جواب**\n\n"
        "سوال را وارد کنید:",
        reply_markup=admin_panel_keyboard()
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
    
    result = db.add_faq(question, answer, keywords)
    
    if result:
        await update.message.reply_text(
            f"✅ **سوال و جواب ثبت شد!**\n\n"
            f"❓ {question}\n"
            f"🔑 {', '.join(keywords)}",
            reply_markup=admin_panel_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ثبت!",
            reply_markup=admin_panel_keyboard()
        )
    
    context.user_data.pop('faq_question', None)
    context.user_data.pop('faq_answer', None)
    return ConversationHandler.END

async def show_user_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    questions = db.get_pending_user_questions()
    
    if not questions:
        await update.message.reply_text(
            "✅ **هیچ سوالی در انتظار نیست.**",
            reply_markup=admin_panel_keyboard()
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
    
    result = db.answer_user_question(q_id, answer)
    
    if result:
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
                    reply_markup=main_menu_keyboard()
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پاسخ: {e}")
        
        await update.message.reply_text(
            "✅ **پاسخ ارسال شد!**",
            reply_markup=admin_panel_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ خطا در ارسال پاسخ!",
            reply_markup=admin_panel_keyboard()
        )
    
    context.user_data.pop('answering_question_id', None)
    return ConversationHandler.END

async def cancel_edu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ عملیات لغو شد.",
        reply_markup=admin_panel_keyboard()
    )
    return ConversationHandler.END

# ==================== اصلی ====================
def main():
    """راه‌اندازی ربات"""
    application = Application.builder().token(TOKEN).build()
    
    # ===== هندلرهای استارت =====
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # ===== منوی اصلی =====
    application.add_handler(MessageHandler(
        filters.Regex("^(📖 راهنمایی|📚 آموزش ترید|💳 خرید اشتراک|📊 وضعیت اشتراک|❓ مشاوره و سوال|🎯 رفرال و درآمد|💰 برداشت|📞 پشتیبانی|👑 پنل مدیریت|🔙 خروج از پنل مدیریت|💰 فیش‌ها|📝 ارسال متن آموزش|📢 پیام همگانی|📊 آمار کاربران|❓ آموزش سوال و جواب|📋 سوالات کاربران|💳 درخواست‌های برداشت|🏆 برترین رفرال‌ها)$"),
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
    
    # ===== سوال =====
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
    
    # ===== آموزش =====
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
    
    # ===== سوال و جواب =====
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
    
    # ===== پاسخ به سوال =====
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
    
    # ===== برداشت =====
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💰 برداشت$"), withdraw_system)],
        states={
            WAITING_WITHDRAW_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_address)
            ],
            WAITING_WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_amount)
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^🔙$"), cancel_edu)]
    )
    application.add_handler(withdraw_conv)
    
    # ===== کالبک‌ها =====
    application.add_handler(CallbackQueryHandler(handle_payment_action, pattern="^(confirm_payment_|reject_payment_)"))
    application.add_handler(CallbackQueryHandler(handle_withdraw_action, pattern="^(confirm_withdraw_|reject_withdraw_)"))
    
    # ===== راه‌اندازی =====
    print("=" * 60)
    print("🚀 ربات آموزش ترید حرفه‌ای با سیستم رفرال")
    print("=" * 60)
    print(f"📁 دیتابیس: trading_bot.db")
    print(f"👤 ادمین‌ها: {ADMIN_IDS}")
    print(f"⚡ شاردینگ‌ها: {MAX_WORKERS}")
    print(f"👥 ظرفیت: ۱۰۰,۰۰۰ کاربر")
    print(f"🎁 پاداش رفرال: {REFERRAL_BONUS} دلار")
    print(f"💰 حداقل برداشت: {MIN_WITHDRAW} دلار")
    print("=" * 60)
    print("✅ ربات در حال اجراست...")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()