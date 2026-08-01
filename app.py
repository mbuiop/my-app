# ============================================================
# UTYOB Bot - نسخه نهایی حرفه‌ای
# با OpenAI، تشخیص گفتار، رفرال دقیق، زبان کامل
# ============================================================

import asyncio
import logging
import sqlite3
import base58
import aiohttp
import threading
import time
import os
import json
import re
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

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

BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
ADMIN_IDS = [327855654]  # آیدی عددی ادمین

TRONGRID_APIS = ["اینجا کلید API را بگذار"]
DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"

# کلیدهای OpenAI
OPENAI_KEYS = [
    "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",
    # کلیدهای بیشتر...
]

PAYMENT_AMOUNT = 100
SUBSCRIPTION_DAYS = 30
DB_SHARDS = 200
CACHE_TTL = 600

# استیکر خوش‌آمدگویی
WELCOME_STICKER = "CAACAgIAAxkBAA..."  # آیدی استیکر

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
                language TEXT DEFAULT 'en',
                wallet_address TEXT,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                has_subscription INTEGER DEFAULT 0,
                subscription_end TEXT,
                referral_points INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        
        # مغز آموزشی (سوال/جواب)
        c.execute('''
            CREATE TABLE IF NOT EXISTS brain_qa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keywords TEXT,
                question TEXT,
                answer TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # تاریخچه تحلیل چارت
        c.execute('''
            CREATE TABLE IF NOT EXISTS chart_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chart_file_id TEXT,
                analysis TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # تنظیمات
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_verifications(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_brain_keywords ON brain_qa(keywords)')
        
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
# کش
# ============================================================
class Cache:
    def __init__(self, ttl=CACHE_TTL):
        self.cache = {}
        self.expiry = {}
        self.lock = threading.RLock()
        self.ttl = ttl

    def get(self, key):
        with self.lock:
            if key in self.cache and time.time() < self.expiry.get(key, 0):
                return self.cache[key]
            self.cache.pop(key, None)
            self.expiry.pop(key, None)
            return None

    def set(self, key, value, ttl=None):
        with self.lock:
            self.cache[key] = value
            self.expiry[key] = time.time() + (ttl or self.ttl)

    def delete(self, key):
        with self.lock:
            self.cache.pop(key, None)
            self.expiry.pop(key, None)

cache = Cache()

# ============================================================
# زبان‌ها (کامل فارسی و انگلیسی)
# ============================================================
TEXTS = {
    'en': {
        'welcome': "🎓 **Welcome to UTYOB Trading Academy!**\n\nWe teach you to trade independently with AI-powered analysis.\n\n🚀 No signals, no dependency.\n📚 Learn, analyze, trade smart.",
        'main_menu': "🎯 **Main Menu**",
        'education': "📚 Trading Course",
        'ai_chart': "🤖 AI Chart Analysis",
        'ai_chat': "💬 AI Assistant",
        'referral': "🔗 Referral",
        'guide': "📖 Guide",
        'language': "🌐 Language",
        'withdraw': "💰 Withdraw",
        'back': "🔙 Back",
        'main_menu_btn': "🏠 Main Menu",
        'cancel': "❌ Cancel",
        'retry': "🔄 Retry",
        'education_title': "📚 **Trading Course**\n\n💰 Price: ${}\n📅 Access: {} days",
        'education_buy': "💳 Buy Access",
        'education_active': "✅ Active until: {}",
        'enter_wallet': "📤 **Enter your TRC20 wallet address:**",
        'invalid_wallet': "❌ Invalid wallet address.",
        'after_wallet': "✅ Address saved.\n\n💰 Send ${} to:\n`{}`\n\n⚠️ Then tap **✅ I paid**.",
        'confirm_payment': "✅ I paid",
        'verifying': "⏳ Verifying on-chain...",
        'verify_success': "✅ **Payment verified!**\n\n🔗 TX: `{}`\n\n📚 {} items sent.",
        'verify_failed': "❌ Auto-verification failed.\n\nReason: {}\n\n📤 Send TX hash or photo:",
        'tx_hash_invalid': "❌ Invalid TX hash (64 chars).",
        'tx_hash_received': "✅ TX hash received. Admin will review.",
        'photo_received': "✅ Photo received. Admin will review.",
        'guide_text': "📖 **Guide**\n\n1️⃣ Tap 'Trading Course'\n2️⃣ Enter TRC20 wallet\n3️⃣ Send ${}\n4️⃣ Access unlocked!\n\n🤖 AI features:\n• Chart analysis\n• AI assistant\n• 2 free charts/day\n\n📞 Support: Contact admin.",
        'invalid_command': "⚠️ Invalid input. Use buttons.",
        'error_message': "⚠️ Error occurred. Try again.",
        'admin_only': "⛔ Unauthorized.",
        'admin_panel_title': "⚙️ **Admin Panel**\n\n👥 Users: {}\n⏳ Pending: {}\n📚 Course: {}\n🧠 Brain: {}",
        'admin_broadcast': "📢 Broadcast",
        'admin_manual_verify': "✅ Manual Verify ({})",
        'admin_send_course': "📚 Send Course",
        'admin_add_content': "📝 Add Content",
        'admin_add_api': "🔑 Add API Key",
        'admin_stats': "📊 Stats",
        'admin_train_brain': "🧠 Train AI Brain",
        'admin_back': "🔙 Back",
        'admin_cancel': "🔙 Cancel",
        'admin_broadcast_prompt': "📢 Send message:",
        'admin_no_pending': "✅ No pending.",
        'admin_pending_header': "✅ **Manual Review**\n\n",
        'admin_approve': "✅ Approve #{}",
        'admin_reject': "❌ Reject #{}",
        'admin_send_course_prompt': "📚 Send to User ID or `ALL`:",
        'admin_add_content_step1': "📝 Step 1/3: Send title:",
        'admin_add_content_step2': "📝 Step 2/3: Send description:",
        'admin_add_content_step3': "📝 Step 3/3: Send file or /skip:",
        'admin_content_added': "✅ Content added! ID: {}",
        'admin_add_api_prompt': "🔑 Send API key:",
        'admin_api_added': "✅ API added! Total: {}",
        'admin_api_duplicate': "❌ Already exists.",
        'admin_stats_title': "📊 **Stats**\n\n👥 Users: {}\n✅ Active: {}\n📚 Course: {}\n⏳ Pending: {}\n🧠 Brain: {}\n🔑 APIs: {}\n⚡ Cache: {} items",
        'admin_approved_note': "✅ Approved!\n👤 User: {}",
        'admin_rejected_note': "❌ Rejected!\n👤 User: {}",
        'admin_approved_user_msg': "✅ Payment verified! Access activated.",
        'admin_rejected_user_msg': "❌ Transaction rejected. Contact support.",
        'admin_broadcast_sent': "✅ Sent to {} users!",
        'admin_send_course_done': "✅ Sent to {} users!",
        'admin_send_course_done_one': "✅ {} items sent to user {}!",
        'admin_invalid_id': "❌ Invalid ID.",
        'admin_train_brain_prompt': "🧠 **Train AI Brain**\n\nSend:\n`question ❓ answer`\n\nOr:\n`keyword1,keyword2: question ❓ answer`",
        'admin_brain_trained': "✅ Trained! Total: {}",
        'admin_brain_invalid': "❌ Invalid format. Use `question ❓ answer`",
        'ai_chart_no_subscription': "❌ Active subscription required.",
        'ai_chart_limit': "❌ Daily limit reached (2/2). Try tomorrow!",
        'ai_chart_send_photo': "📤 Send chart screenshot:",
        'ai_chart_analyzing': "🤖 Analyzing chart with AI...\n⏳ Please wait 30-60 seconds.",
        'ai_chart_result': "📊 **AI Chart Analysis**\n\n{}\n\n📅 Analysis #{}",
        'ai_chart_error': "⚠️ AI analysis failed. Try again.",
        'ai_chat_no_subscription': "❌ Active subscription required.",
        'ai_chat_thinking': "🤖 Thinking...",
        'ai_chat_response': "🤖 **AI Assistant:**\n\n{}",
        'ai_chat_error': "⚠️ AI error. Try again.",
        'withdraw_title': "💰 **Withdraw Points**\n\n📊 Points: {}\n💵 1,000 points = $50",
        'withdraw_enter_wallet': "📤 Enter TRC20 wallet:",
        'withdraw_success': "✅ Withdrawal submitted!\n💰 {} points (${})\n📤 To: {}",
        'withdraw_no_points': "❌ Insufficient points. Minimum: 1,000",
        'withdraw_invalid': "❌ Invalid wallet.",
        'referral_text': "🔗 **Referral**\n\n👤 Code: `{}`\n📊 Invites: {}\n🌟 Points: {}\n\n💰 10 points/invite\n💵 1,000 points = $50\n\n🔗 Share:\n{}",
        'referral_link': "https://t.me/{}?start=ref_{}",
        'share': "📤 Share",
        'no_subscription': "❌ No active subscription.",
        'ai_chart_title': "🤖 **AI Chart Analysis**\n\n📊 Today: {}/2\n🔒 Requires subscription",
        'admin_new_manual_request': "✅ Manual review needed\n\n👤 User: {}\n💰 Amount: {}$\n📤 From: {}\n🔗 Hash: `{}`",
        'payment_confirmed_admin_note': "✅ Payment verified\n👤 User: {}\n💰 Amount: {}$",
        'withdraw_pending_admin': "💰 Withdrawal request\n👤 User: {}\n📊 Points: {}\n💵 Value: {}$\n📤 Wallet: {}",
    },
    'fa': {
        'welcome': "🎓 **به آکادمی ترید UTYOB خوش آمدید!**\n\nما با هوش مصنوعی به شما تحلیل و آموزش مستقل می‌دهیم.\n\n🚀 بدون سیگنال فروشی، بدون وابستگی.\n📚 یاد بگیر، تحلیل کن، حرفه‌ای ترید کن.",
        'main_menu': "🎯 **منوی اصلی**",
        'education': "📚 دوره آموزش ترید",
        'ai_chart': "🤖 تحلیل چارت با هوش مصنوعی",
        'ai_chat': "💬 دستیار هوش مصنوعی",
        'referral': "🔗 رفرال",
        'guide': "📖 راهنما",
        'language': "🌐 زبان",
        'withdraw': "💰 برداشت",
        'back': "🔙 بازگشت",
        'main_menu_btn': "🏠 منوی اصلی",
        'cancel': "❌ انصراف",
        'retry': "🔄 تلاش مجدد",
        'education_title': "📚 **دوره آموزش ترید**\n\n💰 هزینه: {}$\n📅 مدت: {} روز",
        'education_buy': "💳 خرید دسترسی",
        'education_active': "✅ فعال تا تاریخ: {}",
        'enter_wallet': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
        'invalid_wallet': "❌ آدرس کیف پول نامعتبر است.",
        'after_wallet': "✅ آدرس ذخیره شد.\n\n💰 مبلغ {}$ را به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ سپس دکمه **✅ پرداخت کردم** را بزنید.",
        'confirm_payment': "✅ پرداخت کردم",
        'verifying': "⏳ در حال بررسی تراکنش...",
        'verify_success': "✅ **پرداخت تایید شد!**\n\n🔗 هش: `{}`\n\n📚 {} محتوا ارسال شد.",
        'verify_failed': "❌ تایید خودکار انجام نشد.\n\nدلیل: {}\n\n📤 هش تراکنش یا عکس واریز را ارسال کنید:",
        'tx_hash_invalid': "❌ هش تراکنش نامعتبر (۶۴ کاراکتر).",
        'tx_hash_received': "✅ هش تراکنش دریافت شد. مدیر بررسی می‌کند.",
        'photo_received': "✅ عکس دریافت شد. مدیر بررسی می‌کند.",
        'guide_text': "📖 **راهنما**\n\n۱️⃣ روی 'دوره آموزش ترید' بزنید\n۲️⃣ آدرس کیف پول TRC20 را وارد کنید\n۳️⃣ مبلغ {}$ را واریز کنید\n۴️⃣ دسترسی شما فعال می‌شود!\n\n🤖 امکانات هوش مصنوعی:\n• تحلیل چارت\n• دستیار هوش مصنوعی\n• ۲ تحلیل رایگان در روز\n\n📞 پشتیبانی: با مدیریت تماس بگیرید.",
        'invalid_command': "⚠️ ورودی نامعتبر. از دکمه‌ها استفاده کنید.",
        'error_message': "⚠️ خطا رخ داد. دوباره تلاش کنید.",
        'admin_only': "⛔ دسترسی غیرمجاز.",
        'admin_panel_title': "⚙️ **پنل مدیریت**\n\n👥 کاربران: {}\n⏳ در انتظار: {}\n📚 محتوا: {}\n🧠 مغز: {}",
        'admin_broadcast': "📢 ارسال همگانی",
        'admin_manual_verify': "✅ تایید دستی ({})",
        'admin_send_course': "📚 ارسال محتوا",
        'admin_add_content': "📝 افزودن محتوا",
        'admin_add_api': "🔑 افزودن کلید API",
        'admin_stats': "📊 آمار",
        'admin_train_brain': "🧠 آموزش مغز هوش مصنوعی",
        'admin_back': "🔙 بازگشت",
        'admin_cancel': "🔙 انصراف",
        'admin_broadcast_prompt': "📢 متن پیام را ارسال کنید:",
        'admin_no_pending': "✅ موردی در انتظار نیست.",
        'admin_pending_header': "✅ **بررسی دستی**\n\n",
        'admin_approve': "✅ تایید #{}",
        'admin_reject': "❌ رد #{}",
        'admin_send_course_prompt': "📚 آیدی کاربر یا `ALL`:",
        'admin_add_content_step1': "📝 مرحله ۱/۳: عنوان را وارد کنید:",
        'admin_add_content_step2': "📝 مرحله ۲/۳: توضیحات را وارد کنید:",
        'admin_add_content_step3': "📝 مرحله ۳/۳: فایل را ارسال کنید یا /skip:",
        'admin_content_added': "✅ محتوا اضافه شد! ID: {}",
        'admin_add_api_prompt': "🔑 کلید API را ارسال کنید:",
        'admin_api_added': "✅ کلید اضافه شد! تعداد: {}",
        'admin_api_duplicate': "❌ قبلاً اضافه شده.",
        'admin_stats_title': "📊 **آمار**\n\n👥 کاربران: {}\n✅ اشتراک فعال: {}\n📚 محتوا: {}\n⏳ در انتظار: {}\n🧠 مغز: {}\n🔑 کلیدهای API: {}\n⚡ کش: {} آیتم",
        'admin_approved_note': "✅ تایید شد!\n👤 کاربر: {}",
        'admin_rejected_note': "❌ رد شد!\n👤 کاربر: {}",
        'admin_approved_user_msg': "✅ پرداخت شما تایید شد! دسترسی فعال شد.",
        'admin_rejected_user_msg': "❌ تراکنش رد شد. با پشتیبانی تماس بگیرید.",
        'admin_broadcast_sent': "✅ به {} کاربر ارسال شد!",
        'admin_send_course_done': "✅ به {} کاربر ارسال شد!",
        'admin_send_course_done_one': "✅ {} محتوا به کاربر {} ارسال شد!",
        'admin_invalid_id': "❌ آیدی نامعتبر.",
        'admin_train_brain_prompt': "🧠 **آموزش مغز هوش مصنوعی**\n\nارسال کنید:\n`سوال ❓ جواب`\n\nیا:\n`keyword1,keyword2: سوال ❓ جواب`\n\nمثال:\n`rsi,اندیکاتور: RSI چیست ❓ شاخص قدرت نسبی...`",
        'admin_brain_trained': "✅ آموزش داده شد! تعداد کل: {}",
        'admin_brain_invalid': "❌ فرمت نامعتبر. از `سوال ❓ جواب` استفاده کنید.",
        'ai_chart_no_subscription': "❌ برای تحلیل چارت به اشتراک فعال نیاز دارید.",
        'ai_chart_limit': "❌ سهمیه روزانه تمام شد (۲/۲). فردا تلاش کنید!",
        'ai_chart_send_photo': "📤 عکس چارت خود را ارسال کنید:",
        'ai_chart_analyzing': "🤖 در حال تحلیل چارت با هوش مصنوعی...\n⏳ ۳۰-۶۰ ثانیه زمان نیاز است.",
        'ai_chart_result': "📊 **تحلیل چارت با هوش مصنوعی**\n\n{}\n\n📅 تحلیل #{}",
        'ai_chart_error': "⚠️ تحلیل هوش مصنوعی ناموفق بود. دوباره تلاش کنید.",
        'ai_chat_no_subscription': "❌ برای استفاده از دستیار هوش مصنوعی به اشتراک فعال نیاز دارید.",
        'ai_chat_thinking': "🤖 در حال فکر کردن...",
        'ai_chat_response': "🤖 **دستیار هوش مصنوعی:**\n\n{}",
        'ai_chat_error': "⚠️ خطا در هوش مصنوعی. دوباره تلاش کنید.",
        'withdraw_title': "💰 **برداشت امتیاز**\n\n📊 امتیاز شما: {}\n💵 هر ۱,۰۰۰ امتیاز = ۵۰ دلار",
        'withdraw_enter_wallet': "📤 آدرس کیف پول TRC20 خود را وارد کنید:",
        'withdraw_success': "✅ درخواست برداشت ثبت شد!\n💰 {} امتیاز ({} دلار)\n📤 به: {}",
        'withdraw_no_points': "❌ امتیاز کافی نیست. حداقل: ۱,۰۰۰",
        'withdraw_invalid': "❌ آدرس نامعتبر.",
        'referral_text': "🔗 **رفرال**\n\n👤 کد: `{}`\n📊 دعوت‌ها: {}\n🌟 امتیاز: {}\n\n💰 هر دعوت ۱۰ امتیاز\n💵 هر ۱,۰۰۰ امتیاز = ۵۰ دلار\n\n🔗 اشتراک‌گذاری:\n{}",
        'referral_link': "https://t.me/{}?start=ref_{}",
        'share': "📤 اشتراک‌گذاری",
        'no_subscription': "❌ اشتراک فعال ندارید.",
        'ai_chart_title': "🤖 **تحلیل چارت با هوش مصنوعی**\n\n📊 امروز: {}/۲\n🔒 نیاز به اشتراک",
        'admin_new_manual_request': "✅ درخواست بررسی دستی جدید\n\n👤 کاربر: {}\n💰 مبلغ: {}$\n📤 از: {}\n🔗 هش: `{}`",
        'payment_confirmed_admin_note': "✅ پرداخت تایید شد\n👤 کاربر: {}\n💰 مبلغ: {}$",
        'withdraw_pending_admin': "💰 درخواست برداشت\n👤 کاربر: {}\n📊 امتیاز: {}\n💵 ارزش: {} دلار\n📤 کیف پول: {}",
    }
}

def get_text(user_id, key, *args):
    """دریافت متن به زبان کاربر"""
    user = db.execute(user_id, "SELECT language FROM users WHERE user_id = ?", (user_id,)).fetchone()
    lang = user['language'] if user and user['language'] in TEXTS else 'en'
    text = TEXTS[lang].get(key, TEXTS['en'].get(key, key))
    if args:
        try:
            return text.format(*args)
        except:
            return text
    return text

# ============================================================
# OpenAI Client
# ============================================================
class OpenAIClient:
    def __init__(self, api_keys):
        self.api_keys = api_keys
        self.current_index = 0
        self.lock = asyncio.Lock()
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                connector=aiohttp.TCPConnector(limit=100)
            )
        return self.session

    async def _next_key(self):
        async with self.lock:
            key = self.api_keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            return key

    async def chat_completion(self, messages, model="gpt-4o-mini", max_tokens=1500):
        session = await self.get_session()
        url = "https://api.openai.com/v1/chat/completions"

        for attempt in range(len(self.api_keys) * 2):
            api_key = await self._next_key()
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": max_tokens}

            try:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content']
                    elif resp.status == 429:
                        await asyncio.sleep(0.5)
                        continue
            except:
                continue

        return None

    async def analyze_chart(self, description, context=""):
        prompt = f"""
You are a professional crypto trading analyst. Analyze this chart.

Context: {context}
Chart: {description}

Provide:
1. Trend analysis with reasoning
2. Key support/resistance levels
3. Technical indicators
4. Entry/exit suggestions
5. Risk management
"""
        messages = [
            {"role": "system", "content": "You are an expert crypto analyst and educator."},
            {"role": "user", "content": prompt}
        ]
        return await self.chat_completion(messages)

    async def brain_response(self, question, brain_data):
        """پاسخ با مغز یا OpenAI"""
        question_lower = question.lower()
        
        # جستجوی مغز با کلمات کلیدی
        for item in brain_data:
            keywords = item['keywords'].lower().split(',')
            for kw in keywords:
                if kw.strip() and kw.strip() in question_lower:
                    return item['answer']
            if item['question'].lower() in question_lower:
                return item['answer']
        
        # اگر مغز جواب نداشت، از OpenAI بپرس
        messages = [
            {"role": "system", "content": "You are a helpful trading assistant."},
            {"role": "user", "content": question}
        ]
        return await self.chat_completion(messages)

openai_client = OpenAIClient(OPENAI_KEYS)

# ============================================================
# تایید پرداخت
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.current = 0
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=200)
            )
        return self.session

    def _next_api(self):
        api = self.apis[self.current]
        self.current = (self.current + 1) % len(self.apis)
        return api

    def add_api(self, key):
        if key not in self.apis:
            self.apis.append(key)
            return True
        return False

    async def verify(self, from_addr, to_addr, amount, tx_id=None):
        session = await self.get_session()
        for _ in range(len(self.apis) * 2):
            api = self._next_api()
            try:
                if tx_id:
                    ok, result = await self._by_txid(session, api, tx_id, to_addr, amount)
                else:
                    ok, result = await self._search(session, api, from_addr, to_addr, amount)
                if ok:
                    return True, result
            except:
                continue
        return False, None

    async def _by_txid(self, session, api, tx_id, to_addr, amount):
        url = f"https://api.trongrid.io/v1/transactions/{tx_id}"
        headers = {"TRON-PRO-API-KEY": api}
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                if self._validate(data, to_addr, amount):
                    return True, tx_id
        return False, None

    async def _search(self, session, api, from_addr, to_addr, amount):
        url = f"https://api.trongrid.io/v1/accounts/{from_addr}/transactions"
        params = {"limit": 50, "order_by": "block_timestamp,desc"}
        headers = {"TRON-PRO-API-KEY": api}
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                for tx in data.get('data', []):
                    if self._validate(tx, to_addr, amount):
                        return True, tx.get('txID')
        return False, None

    def _validate(self, tx, to_addr, amount):
        try:
            if tx.get('to') != to_addr:
                return False
            tx_amount = tx.get('amount', 0) / 1_000_000
            if abs(tx_amount - amount) > 0.01:
                return False
            status = tx.get('status', '')
            if status and status != 'SUCCESS':
                return False
            return True
        except:
            return False

payment_verifier = PaymentVerifier()

# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()
        self.chart_usage = {}

    def _setup_handlers(self):
        app = self.application
        
        # دستورات
        app.add_handler(CommandHandler("start", self.start_command))
        
        # منو (callback_dataهای منحصر‌به‌فرد)
        app.add_handler(CallbackQueryHandler(self.main_menu, pattern="^mm$"))
        app.add_handler(CallbackQueryHandler(self.education_menu, pattern="^edu$"))
        app.add_handler(CallbackQueryHandler(self.education_buy, pattern="^edu_buy$"))
        app.add_handler(CallbackQueryHandler(self.education_confirm, pattern="^edu_confirm$"))
        app.add_handler(CallbackQueryHandler(self.ai_chart_menu, pattern="^ai_chart$"))
        app.add_handler(CallbackQueryHandler(self.ai_chat_menu, pattern="^ai_chat$"))
        app.add_handler(CallbackQueryHandler(self.referral_menu, pattern="^ref$"))
        app.add_handler(CallbackQueryHandler(self.guide_menu, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_menu, pattern="^lang$"))
        app.add_handler(CallbackQueryHandler(self.set_language, pattern="^setlang_"))
        app.add_handler(CallbackQueryHandler(self.withdraw_menu, pattern="^wd$"))
        app.add_handler(CallbackQueryHandler(self.withdraw_confirm, pattern="^wd_confirm$"))
        
        # پنل مدیریت (فارسی)
        app.add_handler(CallbackQueryHandler(self.admin_panel, pattern="^admin$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast, pattern="^admin_bc$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify, pattern="^admin_mv$"))
        app.add_handler(CallbackQueryHandler(self.admin_send_course, pattern="^admin_sc$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_content, pattern="^admin_ac$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api, pattern="^admin_aa$"))
        app.add_handler(CallbackQueryHandler(self.admin_stats, pattern="^admin_st$"))
        app.add_handler(CallbackQueryHandler(self.admin_train_brain, pattern="^admin_tb$"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve, pattern="^admin_va_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject, pattern="^admin_vr_"))
        
        # پیام‌ها
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        app.add_error_handler(self.error_handler)

    # ============================================================
    # توابع کمکی
    # ============================================================
    def _get_lang(self, user_id):
        user = db.execute(user_id, "SELECT language FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return user['language'] if user and user['language'] in TEXTS else 'en'

    def _t(self, user_id, key, *args):
        lang = self._get_lang(user_id)
        text = TEXTS[lang].get(key, TEXTS['en'].get(key, key))
        if args:
            try:
                return text.format(*args)
            except:
                return text
        return text

    def _validate_wallet(self, addr):
        try:
            if len(addr) != 34 or not addr.startswith('T'):
                return False
            base58.b58decode(addr)
            return True
        except:
            return False

    def _validate_tx(self, tx):
        return len(tx) == 64 and all(c in '0123456789abcdefABCDEF' for c in tx)

    def _main_keyboard(self, user_id):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(self._t(user_id, 'education'), callback_data="edu")],
            [InlineKeyboardButton(self._t(user_id, 'ai_chart'), callback_data="ai_chart"),
             InlineKeyboardButton(self._t(user_id, 'ai_chat'), callback_data="ai_chat")],
            [InlineKeyboardButton(self._t(user_id, 'referral'), callback_data="ref"),
             InlineKeyboardButton(self._t(user_id, 'withdraw'), callback_data="wd")],
            [InlineKeyboardButton(self._t(user_id, 'guide'), callback_data="guide"),
             InlineKeyboardButton(self._t(user_id, 'language'), callback_data="lang")],
        ] + ([ [InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin")] ] if user_id in ADMIN_IDS else []))

    async def _send_course(self, user_id):
        contents = db.execute_global("SELECT * FROM course_content ORDER BY created_at ASC")
        sent = 0
        for c in contents:
            if not db.execute(user_id, "SELECT 1 FROM content_sent WHERE user_id = ? AND content_id = ?", (user_id, c['id'])).fetchone():
                try:
                    caption = f"📚 **{c['title']}**\n\n{c['content'] or ''}"
                    if c['content_type'] == 'text':
                        await self.application.bot.send_message(user_id, caption, parse_mode=ParseMode.MARKDOWN)
                    elif c['content_type'] == 'photo':
                        await self.application.bot.send_photo(user_id, c['file_id'], caption=caption, parse_mode=ParseMode.MARKDOWN)
                    elif c['content_type'] == 'video':
                        await self.application.bot.send_video(user_id, c['file_id'], caption=caption, parse_mode=ParseMode.MARKDOWN)
                    elif c['content_type'] == 'document':
                        await self.application.bot.send_document(user_id, c['file_id'], caption=caption, parse_mode=ParseMode.MARKDOWN)
                    db.execute(user_id, "INSERT INTO content_sent (user_id, content_id) VALUES (?, ?)", (user_id, c['id']))
                    sent += 1
                    await asyncio.sleep(0.15)
                except:
                    pass
        return sent

    async def _broadcast(self, text):
        users = db.execute_global("SELECT user_id FROM users")
        sent = 0
        for u in users:
            try:
                await self.application.bot.send_message(u['user_id'], text, parse_mode=ParseMode.MARKDOWN)
                sent += 1
                if sent % 50 == 0:
                    await asyncio.sleep(0.3)
            except:
                pass
        return sent

    async def _activate(self, user_id, from_addr, tx_id):
        end = (datetime.now() + timedelta(days=SUBSCRIPTION_DAYS)).strftime('%Y-%m-%d')
        db.execute(user_id, "UPDATE users SET has_subscription = 1, subscription_end = ? WHERE user_id = ?", (end, user_id))
        db.execute(user_id,
            "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
            (user_id, from_addr, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
        )
        await self._send_course(user_id)

    # ============================================================
    # /start
    # ============================================================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        # ثبت کاربر
        cur = db.execute(user.id, "SELECT user_id FROM users WHERE user_id = ?", (user.id,))
        if not cur.fetchone():
            ref_code = hashlib.sha256(f"UTYOB_{user.id}_{time.time()}_{random.randint(1000,9999)}".encode()).hexdigest()[:10].upper()
            db.execute(user.id,
                "INSERT INTO users (user_id, username, first_name, last_name, referral_code, language) VALUES (?, ?, ?, ?, ?, ?)",
                (user.id, user.username, user.first_name, user.last_name, ref_code, 'en')
            )
        
        # رفرال
        if context.args and context.args[0].startswith('ref_'):
            ref_code = context.args[0][4:]
            ref = db.execute(0, "SELECT user_id FROM users WHERE referral_code = ?", (ref_code,)).fetchone()
            if ref and ref['user_id'] != user.id:
                db.execute(user.id, "UPDATE users SET referred_by = ? WHERE user_id = ?", (ref['user_id'], user.id))
                # ۱۰ امتیاز به دعوت‌کننده
                referrer = db.execute(ref['user_id'], "SELECT referral_points FROM users WHERE user_id = ?", (ref['user_id'],)).fetchone()
                points = (referrer['referral_points'] or 0) + 10
                db.execute(ref['user_id'], "UPDATE users SET referral_points = ? WHERE user_id = ?", (points, ref['user_id']))
        
        # استیکر
        try:
            await update.message.reply_sticker(WELCOME_STICKER)
        except:
            pass
        
        await update.message.reply_text(
            self._t(user.id, 'welcome'),
            reply_markup=self._main_keyboard(user.id),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # منوی اصلی
    # ============================================================
    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            self._t(query.from_user.id, 'main_menu'),
            reply_markup=self._main_keyboard(query.from_user.id),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # دوره آموزش
    # ============================================================
    async def education_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if user and user['has_subscription'] and user['subscription_end'] >= datetime.now().strftime('%Y-%m-%d'):
            sent = await self._send_course(user_id)
            total = len(db.execute_global("SELECT id FROM course_content"))
            await query.edit_message_text(
                self._t(user_id, 'education_active', user['subscription_end']) + f"\n\n📚 {sent}/{total} ارسال شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            self._t(user_id, 'education_title', PAYMENT_AMOUNT, SUBSCRIPTION_DAYS),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(self._t(user_id, 'education_buy'), callback_data="edu_buy")],
                [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )

    async def education_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        context.user_data['waiting_wallet'] = True
        await query.edit_message_text(
            self._t(user_id, 'enter_wallet'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'cancel'), callback_data="edu")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    async def education_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = db.execute(user_id, "SELECT wallet_address FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if not user or not user['wallet_address']:
            await query.edit_message_text(self._t(user_id, 'enter_wallet'), parse_mode=ParseMode.MARKDOWN)
            return
        
        await query.edit_message_text(self._t(user_id, 'verifying'), parse_mode=ParseMode.MARKDOWN)
        
        ok, tx_id = await payment_verifier.verify(user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT)
        
        if ok:
            await self._activate(user_id, user['wallet_address'], tx_id)
            sent = await self._send_course(user_id)
            await query.edit_message_text(
                self._t(user_id, 'verify_success', tx_id, sent),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="mm")]]),
                parse_mode=ParseMode.MARKDOWN
            )
            for admin in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(admin, self._t(admin, 'payment_confirmed_admin_note', user_id, PAYMENT_AMOUNT))
                except:
                    pass
        else:
            context.user_data['waiting_tx'] = True
            context.user_data['tx_from'] = user['wallet_address']
            await query.edit_message_text(
                self._t(user_id, 'verify_failed', "تراکنش یافت نشد"),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self._t(user_id, 'retry'), callback_data="edu_confirm")],
                    [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="edu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # هوش مصنوعی - تحلیل چارت
    # ============================================================
    async def ai_chart_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if not user or not user['has_subscription'] or user['subscription_end'] < datetime.now().strftime('%Y-%m-%d'):
            await query.edit_message_text(
                self._t(user_id, 'ai_chart_no_subscription'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        today = datetime.now().strftime('%Y-%m-%d')
        used = self.chart_usage.get(f"{user_id}_{today}", 0)
        
        if used >= 2:
            await query.edit_message_text(
                self._t(user_id, 'ai_chart_limit'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            self._t(user_id, 'ai_chart_title', used),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]]),
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['waiting_chart'] = True
        await query.message.reply_text(self._t(user_id, 'ai_chart_send_photo'))

    # ============================================================
    # هوش مصنوعی - چت
    # ============================================================
    async def ai_chat_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if not user or not user['has_subscription'] or user['subscription_end'] < datetime.now().strftime('%Y-%m-%d'):
            await query.edit_message_text(
                self._t(user_id, 'ai_chat_no_subscription'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        context.user_data['waiting_chat'] = True
        await query.edit_message_text(
            self._t(user_id, 'ai_chat_title'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # رفرال
    # ============================================================
    async def referral_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if not user:
            return
        
        ref_count = len(db.execute_global("SELECT user_id FROM users WHERE referred_by = ?", (user_id,)))
        points = user['referral_points'] or 0
        bot_username = self.application.bot.username
        link = f"https://t.me/{bot_username}?start=ref_{user['referral_code']}"
        
        await query.edit_message_text(
            self._t(user_id, 'referral_text', user['referral_code'], ref_count, points, link),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(self._t(user_id, 'share'), url=f"https://t.me/share/url?url={link}")],
                [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # برداشت
    # ============================================================
    async def withdraw_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = db.execute(user_id, "SELECT referral_points FROM users WHERE user_id = ?", (user_id,)).fetchone()
        points = user['referral_points'] if user else 0
        
        if points < 1000:
            await query.edit_message_text(
                self._t(user_id, 'withdraw_no_points'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        context.user_data['waiting_wd_wallet'] = True
        await query.edit_message_text(
            self._t(user_id, 'withdraw_title', points),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'cancel'), callback_data="mm")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    async def withdraw_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = db.execute(user_id, "SELECT wallet_address, referral_points FROM users WHERE user_id = ?", (user_id,)).fetchone()
        
        if not user or not user['wallet_address']:
            await query.edit_message_text(self._t(user_id, 'withdraw_invalid'), parse_mode=ParseMode.MARKDOWN)
            return
        
        points = user['referral_points'] or 0
        if points < 1000:
            await query.edit_message_text(self._t(user_id, 'withdraw_no_points'), parse_mode=ParseMode.MARKDOWN)
            return
        
        amount = (points // 1000) * 50
        deduct = (points // 1000) * 1000
        
        db.execute(user_id, "UPDATE users SET referral_points = referral_points - ? WHERE user_id = ?", (deduct, user_id))
        
        for admin in ADMIN_IDS:
            try:
                await self.application.bot.send_message(admin, self._t(admin, 'withdraw_pending_admin', user_id, deduct, amount, user['wallet_address']))
            except:
                pass
        
        await query.edit_message_text(
            self._t(user_id, 'withdraw_success', deduct, amount, user['wallet_address']),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="mm")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # راهنما و زبان
    # ============================================================
    async def guide_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        await query.edit_message_text(
            self._t(user_id, 'guide_text', PAYMENT_AMOUNT),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="mm")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    async def language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "🌐 Select Language:\n\n🇬🇧 English\n🇮🇷 فارسی",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
                 InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa")],
                [InlineKeyboardButton("🔙 Back", callback_data="mm")]
            ])
        )

    async def set_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = query.data.split('_')[1]
        if lang in TEXTS:
            db.execute(user_id, "UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
        await query.edit_message_text(
            self._t(user_id, 'welcome'),
            reply_markup=self._main_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # پنل مدیریت (کاملاً فارسی)
    # ============================================================
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            await query.edit_message_text(self._t(user_id, 'admin_only'))
            return
        
        user_count = len(db.execute_global("SELECT user_id FROM users"))
        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        course_count = len(db.execute_global("SELECT id FROM course_content"))
        brain_count = len(db.execute_global("SELECT id FROM brain_qa"))
        
        await query.edit_message_text(
            self._t(user_id, 'admin_panel_title', user_count, pending, course_count, brain_count),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 ارسال همگانی", callback_data="admin_bc")],
                [InlineKeyboardButton(f"✅ تایید دستی ({pending})", callback_data="admin_mv")],
                [InlineKeyboardButton("📚 ارسال محتوا", callback_data="admin_sc"),
                 InlineKeyboardButton("📝 افزودن محتوا", callback_data="admin_ac")],
                [InlineKeyboardButton("🔑 افزودن کلید API", callback_data="admin_aa"),
                 InlineKeyboardButton("📊 آمار", callback_data="admin_st")],
                [InlineKeyboardButton(f"🧠 آموزش مغز ({brain_count})", callback_data="admin_tb")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="mm")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - آموزش مغز (سوال/جواب)
    # ============================================================
    async def admin_train_brain(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'train_brain'
        await query.edit_message_text(
            self._t(user_id, 'admin_train_brain_prompt'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - تایید دستی
    # ============================================================
    async def admin_manual_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        pending = db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC LIMIT 5")
        if not pending:
            await query.edit_message_text(
                self._t(user_id, 'admin_no_pending'),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]])
            )
            return
        
        text = self._t(user_id, 'admin_pending_header')
        keyboard = []
        for p in pending:
            text += f"👤 کاربر: {p['user_id']}\n💰 مبلغ: ${p['amount']}\n📤 از: `{p['from_address']}`\n"
            if p['tx_hash']:
                text += f"🔗 هش: `{p['tx_hash']}`\n"
            if p['photo_file_id']:
                text += f"📷 عکس: دارد\n"
            text += "\n"
            keyboard.append([
                InlineKeyboardButton(f"✅ تایید #{p['id']}", callback_data=f"admin_va_{p['id']}"),
                InlineKeyboardButton(f"❌ رد #{p['id']}", callback_data=f"admin_vr_{p['id']}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ============================================================
    # مدیریت - تایید/رد
    # ============================================================
    async def admin_verify_approve(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            return
        
        pending_id = int(query.data.split('_')[2])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text(self._t(admin_id, 'admin_not_found'))
            return
        
        await self._activate(p['user_id'], p['from_address'], p['tx_hash'] or "manual_approved")
        db.execute(0, "UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))
        
        try:
            await self.application.bot.send_message(p['user_id'], self._t(p['user_id'], 'admin_approved_user_msg'), parse_mode=ParseMode.MARKDOWN)
        except:
            pass
        
        await query.edit_message_text(self._t(admin_id, 'admin_approved_note', p['user_id']), parse_mode=ParseMode.MARKDOWN)

    async def admin_verify_reject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            return
        
        pending_id = int(query.data.split('_')[2])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text(self._t(admin_id, 'admin_not_found'))
            return
        
        db.execute(0, "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?", (pending_id,))
        
        try:
            await self.application.bot.send_message(p['user_id'], self._t(p['user_id'], 'admin_rejected_user_msg'), parse_mode=ParseMode.MARKDOWN)
        except:
            pass
        
        await query.edit_message_text(self._t(admin_id, 'admin_rejected_note', p['user_id']), parse_mode=ParseMode.MARKDOWN)

    # ============================================================
    # مدیریت - ارسال همگانی
    # ============================================================
    async def admin_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'broadcast'
        await query.edit_message_text(
            self._t(user_id, 'admin_broadcast_prompt'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - ارسال محتوا
    # ============================================================
    async def admin_send_course(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'send_course'
        await query.edit_message_text(
            self._t(user_id, 'admin_send_course_prompt'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - افزودن محتوا
    # ============================================================
    async def admin_add_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_content'
        context.user_data['content_step'] = 1
        await query.edit_message_text(
            self._t(user_id, 'admin_add_content_step1'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - افزودن کلید API
    # ============================================================
    async def admin_add_api(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_api'
        await query.edit_message_text(
            self._t(user_id, 'admin_add_api_prompt'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - آمار
    # ============================================================
    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        user_count = len(db.execute_global("SELECT user_id FROM users"))
        active = len(db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"))
        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        course_count = len(db.execute_global("SELECT id FROM course_content"))
        brain_count = len(db.execute_global("SELECT id FROM brain_qa"))
        
        await query.edit_message_text(
            self._t(user_id, 'admin_stats_title', user_count, active, course_count, pending, brain_count, len(TRONGRID_APIS), cache.cache.__len__()),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="admin_st")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت پیام‌ها
    # ============================================================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        lang = self._get_lang(user_id)
        
        # ثبت کاربر
        cur = db.execute(user_id, "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cur.fetchone():
            ref_code = hashlib.sha256(f"UTYOB_{user_id}_{time.time()}".encode()).hexdigest()[:10].upper()
            db.execute(user_id,
                "INSERT INTO users (user_id, username, first_name, last_name, referral_code, language) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name, ref_code, 'en')
            )
        
        admin_action = context.user_data.get('admin_action')
        
        # ===== ارسال همگانی =====
        if admin_action == 'broadcast':
            sent = await self._broadcast(text)
            context.user_data['admin_action'] = None
            await update.message.reply_text(
                self._t(user_id, 'admin_broadcast_sent', sent),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]])
            )
            return
        
        # ===== ارسال محتوا =====
        if admin_action == 'send_course':
            if text.strip().upper() == 'ALL':
                users = db.execute_global("SELECT user_id FROM users")
                sent = 0
                for u in users:
                    if await self._send_course(u['user_id']) > 0:
                        sent += 1
                    await asyncio.sleep(0.15)
                context.user_data['admin_action'] = None
                await update.message.reply_text(
                    self._t(user_id, 'admin_send_course_done', sent),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]])
                )
            else:
                try:
                    target = int(text.strip())
                    count = await self._send_course(target)
                    context.user_data['admin_action'] = None
                    await update.message.reply_text(
                        self._t(user_id, 'admin_send_course_done_one', count, target),
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]])
                    )
                except:
                    await update.message.reply_text(self._t(user_id, 'admin_invalid_id'))
            return
        
        # ===== افزودن محتوا =====
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
                title = context.user_data.get('content_title', 'بدون عنوان')
                content = context.user_data.get('content_text', '')
                db.execute(0,
                    "INSERT INTO course_content (content_type, title, content) VALUES ('text', ?, ?)",
                    (title, content)
                )
                context.user_data['admin_action'] = None
                context.user_data['content_step'] = None
                await update.message.reply_text(
                    self._t(user_id, 'admin_content_added', db.execute(0, "SELECT last_insert_rowid()").fetchone()[0]),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]])
                )
            return
        
        # ===== افزودن کلید API =====
        if admin_action == 'add_api':
            if payment_verifier.add_api(text.strip()):
                context.user_data['admin_action'] = None
                await update.message.reply_text(
                    self._t(user_id, 'admin_api_added', len(payment_verifier.apis)),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]])
                )
            else:
                await update.message.reply_text(self._t(user_id, 'admin_api_duplicate'))
            return
        
        # ===== آموزش مغز (سوال/جواب) =====
        if admin_action == 'train_brain':
            if '❓' in text:
                parts = text.split('❓')
                if len(parts) == 2:
                    q_part = parts[0].strip()
                    answer = parts[1].strip()
                    
                    keywords = ''
                    question = q_part
                    if ':' in q_part:
                        kw_part, question = q_part.split(':', 1)
                        keywords = kw_part.strip()
                        question = question.strip()
                    
                    if question and answer:
                        db.execute(0,
                            "INSERT INTO brain_qa (keywords, question, answer) VALUES (?, ?, ?)",
                            (keywords, question, answer)
                        )
                        total = len(db.execute_global("SELECT id FROM brain_qa"))
                        context.user_data['admin_action'] = None
                        await update.message.reply_text(
                            self._t(user_id, 'admin_brain_trained', total),
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]])
                        )
                        return
            
            await update.message.reply_text(self._t(user_id, 'admin_brain_invalid'))
            return
        
        # ===== دریافت هش یا عکس برای تایید =====
        if context.user_data.get('waiting_tx'):
            tx_hash = text.strip()
            if not self._validate_tx(tx_hash):
                await update.message.reply_text(self._t(user_id, 'tx_hash_invalid'), parse_mode=ParseMode.MARKDOWN)
                return
            
            from_addr = context.user_data.get('tx_from')
            db.execute(0,
                "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, tx_hash, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (user_id, from_addr, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash)
            )
            context.user_data['waiting_tx'] = False
            context.user_data['tx_from'] = None
            
            await update.message.reply_text(self._t(user_id, 'tx_hash_received'), parse_mode=ParseMode.MARKDOWN)
            
            pid = db.execute(0, "SELECT last_insert_rowid()").fetchone()[0]
            for admin in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        admin,
                        self._t(admin, 'admin_new_manual_request', user_id, PAYMENT_AMOUNT, from_addr, tx_hash),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("✅ تایید", callback_data=f"admin_va_{pid}"),
                             InlineKeyboardButton("❌ رد", callback_data=f"admin_vr_{pid}")]
                        ]),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            return
        
        # ===== دریافت آدرس کیف پول =====
        if context.user_data.get('waiting_wallet'):
            wallet = text.strip()
            if not self._validate_wallet(wallet):
                await update.message.reply_text(self._t(user_id, 'invalid_wallet'), parse_mode=ParseMode.MARKDOWN)
                return
            
            db.execute(user_id, "UPDATE users SET wallet_address = ? WHERE user_id = ?", (wallet, user_id))
            context.user_data['waiting_wallet'] = False
            
            await update.message.reply_text(
                self._t(user_id, 'after_wallet', PAYMENT_AMOUNT, DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self._t(user_id, 'confirm_payment'), callback_data="edu_confirm")],
                    [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="edu")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # ===== دریافت آدرس برای برداشت =====
        if context.user_data.get('waiting_wd_wallet'):
            wallet = text.strip()
            if not self._validate_wallet(wallet):
                await update.message.reply_text(self._t(user_id, 'withdraw_invalid'), parse_mode=ParseMode.MARKDOWN)
                return
            
            db.execute(user_id, "UPDATE users SET wallet_address = ? WHERE user_id = ?", (wallet, user_id))
            context.user_data['waiting_wd_wallet'] = False
            
            user = db.execute(user_id, "SELECT referral_points FROM users WHERE user_id = ?", (user_id,)).fetchone()
            points = user['referral_points'] or 0
            
            await update.message.reply_text(
                self._t(user_id, 'withdraw_title', points),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ تایید برداشت", callback_data="wd_confirm")],
                    [InlineKeyboardButton("🔙 انصراف", callback_data="mm")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # ===== چت با هوش مصنوعی (تشخیص گفتار با کلمات کلیدی) =====
        if context.user_data.get('waiting_chat'):
            user = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not user or not user['has_subscription'] or user['subscription_end'] < datetime.now().strftime('%Y-%m-%d'):
                await update.message.reply_text(self._t(user_id, 'ai_chat_no_subscription'))
                return
            
            await update.message.reply_text(self._t(user_id, 'ai_chat_thinking'))
            
            # جستجوی مغز (با تشخیص کلمات کلیدی)
            brain_data = db.execute_global("SELECT * FROM brain_qa")
            answer = None
            
            text_lower = text.lower()
            for item in brain_data:
                # چک کلمات کلیدی
                keywords = item['keywords'].lower().split(',')
                for kw in keywords:
                    if kw.strip() and kw.strip() in text_lower:
                        answer = item['answer']
                        break
                if answer:
                    break
                # چک سوال
                if item['question'].lower() in text_lower:
                    answer = item['answer']
                    break
            
            if answer:
                await update.message.reply_text(
                    self._t(user_id, 'ai_chat_response', answer),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # استفاده از OpenAI
                response = await openai_client.brain_response(text, brain_data)
                if response:
                    await update.message.reply_text(
                        self._t(user_id, 'ai_chat_response', response),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(self._t(user_id, 'ai_chat_error'))
            return
        
        # ===== دستور نامعتبر =====
        await update.message.reply_text(
            self._t(user_id, 'invalid_command'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="mm")]]),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت عکس‌ها (تحلیل چارت + تایید دستی)
    # ============================================================
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # ===== تحلیل چارت =====
        if context.user_data.get('waiting_chart'):
            user = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not user or not user['has_subscription'] or user['subscription_end'] < datetime.now().strftime('%Y-%m-%d'):
                await update.message.reply_text(self._t(user_id, 'ai_chart_no_subscription'))
                return
            
            today = datetime.now().strftime('%Y-%m-%d')
            used = self.chart_usage.get(f"{user_id}_{today}", 0)
            if used >= 2:
                await update.message.reply_text(self._t(user_id, 'ai_chart_limit'))
                return
            
            context.user_data['waiting_chart'] = False
            photo = update.message.photo[-1]
            file_id = photo.file_id
            
            await update.message.reply_text(self._t(user_id, 'ai_chart_analyzing'))
            
            # تحلیل با OpenAI
            analysis = await openai_client.analyze_chart(
                "چارت ارسال شده توسط کاربر",
                f"User ID: {user_id}"
            )
            
            if analysis:
                self.chart_usage[f"{user_id}_{today}"] = used + 1
                count = self.chart_usage.get(f"{user_id}_{today}", 0)
                await update.message.reply_text(
                    self._t(user_id, 'ai_chart_result', analysis, count),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(self._t(user_id, 'ai_chart_error'))
            return
        
        # ===== تایید دستی با عکس =====
        if context.user_data.get('waiting_tx'):
            photo = update.message.photo[-1]
            file_id = photo.file_id
            from_addr = context.user_data.get('tx_from')
            
            db.execute(0,
                "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, photo_file_id, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (user_id, from_addr, DESTINATION_WALLET, PAYMENT_AMOUNT, file_id)
            )
            context.user_data['waiting_tx'] = False
            context.user_data['tx_from'] = None
            
            await update.message.reply_text(self._t(user_id, 'photo_received'), parse_mode=ParseMode.MARKDOWN)
            
            pid = db.execute(0, "SELECT last_insert_rowid()").fetchone()[0]
            for admin in ADMIN_IDS:
                try:
                    await self.application.bot.send_photo(
                        admin,
                        file_id,
                        caption=self._t(admin, 'admin_new_manual_request', user_id, PAYMENT_AMOUNT, from_addr, "عکس واریز"),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("✅ تایید", callback_data=f"admin_va_{pid}"),
                             InlineKeyboardButton("❌ رد", callback_data=f"admin_vr_{pid}")]
                        ])
                    )
                except:
                    pass
            return
        
        # ===== افزودن محتوا توسط ادمین =====
        if user_id in ADMIN_IDS and context.user_data.get('admin_action') == 'add_content':
            if context.user_data.get('content_step') != 3:
                return
            
            title = context.user_data.get('content_title', 'بدون عنوان')
            content = context.user_data.get('content_text', '')
            photo = update.message.photo[-1]
            
            db.execute(0,
                "INSERT INTO course_content (content_type, title, content, file_id, file_name) VALUES ('photo', ?, ?, ?, ?)",
                (title, content, photo.file_id, f"{title}.jpg")
            )
            context.user_data['admin_action'] = None
            context.user_data['content_step'] = None
            
            await update.message.reply_text(
                self._t(user_id, 'admin_content_added', db.execute(0, "SELECT last_insert_rowid()").fetchone()[0]),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin")]])
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
                    self._t(update.effective_user.id, 'error_message'),
                    parse_mode=ParseMode.MARKDOWN
                )
        except:
            pass


# ============================================================
# اجرا
# ============================================================
async def main():
    bot = UTYOBot()
    logger.info("🚀 UTYOB Bot با هوش مصنوعی در حال اجراست...")
    logger.info(f"👥 مدیران: {ADMIN_IDS}")
    logger.info(f"🔑 کلیدهای API: {len(TRONGRID_APIS)}")
    logger.info(f"🗄️ شاردها: {DB_SHARDS}")
    
    await bot.application.initialize()
    await bot.application.start()
    await bot.application.updater.start_polling()
    logger.info("✅ ربات با موفقیت اجرا شد!")
    
    # ارسال خودکار محتوا
    while True:
        try:
            users = db.execute_global(
                "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
            )
            for u in users:
                await bot._send_course(u['user_id'])
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Auto-send error: {e}")
        await asyncio.sleep(3600)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 ربات متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")
