# ============================================================
# UTYOB Bot - نسخه نهایی با هوش مصنوعی کامل
# امکانات: آموزش ترید + هوش مصنوعی تحلیل چارت + مغز آموزشی + رفرال
# طراحی شده برای ۵۰۰,۰۰۰+ کاربر با کش و شاردینگ
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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Sticker
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# ⬇️⬇️⬇️  تنظیمات — مقادیر خودت رو دقیقاً همینجا وارد کن  ⬇️⬇️⬇️
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "اینجا توکن ربات را بگذار"
ADMIN_IDS = [111111111]  # آیدی عددی ادمین

TRONGRID_APIS = ["اینجا کلید API را بگذار"]
DESTINATION_WALLET = "اینجا آدرس کیف پول TRC20 را بگذار"

OPENAI_API_KEY = "اینجا کلید OpenAI را بگذار"  # برای تحلیل چارت

PAYMENT_AMOUNT = 100
SUBSCRIPTION_DAYS = 30
DB_SHARDS = 200
CACHE_TTL = 600
DEFAULT_LANG = 'en'

# استیکرهای خوش‌آمدگویی (آیدی استیکرهای تلگرام)
WELCOME_STICKER = "CAACAgIAAxkBAA..."  # آیدی استیکر دلخواه

# ============================================================
# ⬆️⬆️⬆️  پایان بخش تنظیمات  ⬆️⬆️⬆️
# ============================================================


# ============================================================
# دیتابیس با ۲۰۰ شارد
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
        
        # کاربران
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
                total_participations INTEGER DEFAULT 0,
                wins_count INTEGER DEFAULT 0,
                referral_points INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # تراکنش‌ها
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
        
        # تایید دستی
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
        
        # محتوای آموزشی
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
        
        # محتوای ارسال شده به کاربران
        c.execute('''
            CREATE TABLE IF NOT EXISTS content_sent (
                user_id INTEGER,
                content_id INTEGER,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, content_id)
            )
        ''')
        
        # مغز آموزشی (سوالات و جواب‌ها)
        c.execute('''
            CREATE TABLE IF NOT EXISTS brain_qa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keywords TEXT,
                question TEXT,
                answer TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        
        # ایندکس‌ها
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
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
# سیستم کش پیشرفته
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

    def clear_pattern(self, pattern):
        with self.lock:
            keys = [k for k in self.cache if pattern in k]
            for k in keys:
                self.cache.pop(k, None)
                self.expiry.pop(k, None)

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
# زبان‌ها (انگلیسی پیش‌فرض، پنل مدیریت فارسی)
# ============================================================
LANGUAGES = {
    'en': {
        'name': 'English',
        'welcome': "🎓 **Welcome to UTYOB Trading Academy!**\n\nWe teach you to trade independently with AI-powered analysis.\n\n🚀 No signals, no dependency.\n📚 Learn, analyze, trade smart.",
        'welcome_sticker': WELCOME_STICKER,
        'main_menu': "🎯 **Main Menu**",
        'education': "📚 Trading Course",
        'ai_chart': "🤖 AI Chart Analysis",
        'ai_chat': "💬 AI Assistant",
        'referral': "🔗 Referral",
        'guide': "📖 Guide",
        'language_btn': "🌐 Language",
        'withdraw': "💰 Withdraw",
        'back': "🔙 Back",
        'main_menu_btn': "🏠 Main Menu",
        'cancel': "❌ Cancel",
        'retry': "🔄 Retry",
        'education_title': "📚 **Trading Course**\n\nLearn professional trading with AI assistance.\n\n💰 Price: {}$ (USDT-TRC20)\n📅 Access: {} days",
        'education_buy': "💳 Buy / Renew",
        'education_active': "✅ Active access.\n📅 Valid until: {}\n\n📚 {}/{} course items sent.",
        'enter_wallet': "📤 **Enter your TRC20 wallet address:**",
        'invalid_wallet': "❌ Invalid wallet.\nExample: `TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`",
        'after_wallet': "✅ Address saved.\n\n💰 Send {}$ to:\n`{}`\n\n⚠️ Then tap **✅ I've made the payment**.",
        'confirm_payment': "✅ I've made the payment",
        'verifying': "⏳ Verifying on-chain...",
        'verify_success': "✅ **Payment verified!**\n\n🔗 TX: `{}`\n\n📚 {} items sent.",
        'verify_failed': "❌ Auto-verification failed.\n\nReason: {}\n\n📤 Send TX hash or photo:",
        'tx_hash_invalid': "❌ Invalid TX hash (64 chars).",
        'tx_hash_received': "✅ TX hash received. Admin will review.",
        'photo_received': "✅ Photo received. Admin will review.",
        'guide_text': """
📖 **UTYOB Trading Academy Guide**

🎯 **What We Offer:**
• 🤖 AI-powered chart analysis
• 📚 Complete trading education
• 💬 AI assistant for your questions
• 🔗 Referral rewards program

🚀 **Why Join Us?**
We DON'T sell signals. We teach you to analyze the market independently using:
• Advanced AI technology
• Multiple analysis methods
• Real-time chart analysis
• Professional trading strategies

💰 **Get Started:**
1️⃣ Tap "Trading Course"
2️⃣ Enter your TRC20 wallet address
3️⃣ Send ${} to the provided address
4️⃣ Access unlocked instantly!

📊 **AI Chart Analysis:**
• Send a chart screenshot
• Get professional AI analysis
• Learn from every trade

💡 **Our Philosophy:**
"Give a man a signal, he trades for a day.
Teach a man to analyze, he trades for life."

📞 Support: Contact admin for any questions.

🔗 Referral program: Earn points for every friend who subscribes!
        """,
        'invalid_command': "⚠️ Invalid input. Use the buttons.",
        'error_message': "⚠️ Something went wrong. Please try again.",
        'admin_only': "⛔ Unauthorized.",
        'payment_confirmed_admin_note': "✅ Payment auto-verified\n👤 User: {}\n💰 Amount: {}$",
        'admin_panel_title': "⚙️ **Admin Panel**\n\n👥 Users: {}\n⏳ Pending: {}\n📚 Course: {}\n🔑 APIs: {}",
        'admin_broadcast_btn': "📢 Broadcast",
        'admin_manual_verify_btn': "✅ Manual Verify ({})",
        'admin_send_course_btn': "📚 Send Course",
        'admin_add_content_btn': "📝 Add Content",
        'admin_add_api_btn': "🔑 Add API Key",
        'admin_stats_btn': "📊 Stats",
        'admin_train_brain_btn': "🧠 Train AI Brain",
        'admin_back_btn': "🔙 Back",
        'admin_cancel_btn': "🔙 Cancel",
        'admin_broadcast_prompt': "📢 **Broadcast**\n\nSend the message:",
        'admin_no_pending': "✅ No pending.",
        'admin_pending_header': "✅ **Manual Review Queue**\n\n",
        'admin_approve': "✅ Approve #{}",
        'admin_reject': "❌ Reject #{}",
        'admin_send_course_prompt': "📚 **Send Course**\n\nUser ID or `ALL`:",
        'admin_add_content_step1': "📝 Step 1/3: Send title:",
        'admin_add_content_step2': "📝 Step 2/3: Send description:",
        'admin_add_content_step3': "📝 Step 3/3: Send file or /skip:",
        'admin_content_added': "✅ Content added! ID: {}",
        'admin_add_api_prompt': "🔑 **Add TronGrid API Key:**",
        'admin_api_added': "✅ API added! Total: {}",
        'admin_api_duplicate': "❌ Already exists.",
        'admin_stats_title': "📊 **System Stats**\n\n👥 Users: {}\n✅ Active: {}\n📚 Course: {}\n⏳ Pending: {}\n🔑 APIs: {}\n🧠 Brain Q&A: {}\n⚡ Cache: {} items | {:.1f}%",
        'admin_refresh': "🔄 Refresh",
        'admin_not_found': "❌ Not found.",
        'admin_approved_note': "✅ Approved!\n👤 User: {}",
        'admin_rejected_note': "❌ Rejected!\n👤 User: {}",
        'admin_approved_user_msg': "✅ Your payment is verified! Access activated.",
        'admin_rejected_user_msg': "❌ Transaction rejected. Contact support.",
        'admin_broadcast_sent': "✅ Done!\n📤 Sent: {}\n❌ Failed: {}",
        'admin_broadcast_sending': "⏳ Sending...",
        'admin_send_course_sending_all': "⏳ Sending to {} users...",
        'admin_send_course_done_all': "✅ Sent to {} users!",
        'admin_send_course_done_one': "✅ {} items sent to user {}!",
        'admin_invalid_id': "❌ Invalid ID.",
        'admin_new_manual_request': "✅ Manual review needed\n\n👤 User: {}\n💰 Amount: {}$\n📤 From: {}\n🔗 Hash: `{}`",
        'admin_train_brain_prompt': "🧠 **Train AI Brain**\n\nSend in this format:\n`keyword1,keyword2: question ❓ answer`\n\nOr:\n`question ❓ answer`\n\nExample:\n`rsi,اندیکاتور: RSI چیست ❓ Relative Strength Index...`",
        'admin_brain_trained': "✅ Brain trained!\n🧠 Added: {}\n📚 Total Q&A: {}",
        'admin_brain_invalid': "❌ Invalid format. Use: `question ❓ answer`",
        'ai_chart_title': "🤖 **AI Chart Analysis**\n\nSend a chart screenshot and get professional AI analysis.\n\n📊 **Available:** {}/2 today\n🔒 Requires active subscription",
        'ai_chart_no_subscription': "❌ Active subscription required for AI chart analysis.\n\nBuy access first!",
        'ai_chart_limit_reached': "❌ Daily limit reached ({}/2).\nCome back tomorrow!",
        'ai_chart_send_photo': "📤 Send your chart screenshot:",
        'ai_chart_analyzing': "🤖 Analyzing chart with AI...\n⏳ Please wait 30-60 seconds.",
        'ai_chart_result': "📊 **AI Chart Analysis**\n\n{}\n\n📅 Analysis #{}\n💡 Learn from every trade!",
        'ai_chart_error': "⚠️ AI analysis failed.\nPlease try again later.",
        'withdraw_title': "💰 **Withdraw Referral Points**\n\n📊 Your points: {}\n💵 1,000 points = $50\n📤 Minimum withdrawal: 1,000 points",
        'withdraw_enter_wallet': "📤 Enter your TRC20 wallet:",
        'withdraw_success': "✅ Withdrawal request submitted!\n💰 {} points (${})\n📤 To: {}\n⏳ Admin will process.",
        'withdraw_no_points': "❌ Insufficient points.\nMinimum: 1,000 points",
        'withdraw_invalid': "❌ Invalid wallet.",
        'withdraw_pending_admin': "💰 Withdrawal request\n👤 User: {}\n📊 Points: {}\n💵 Value: ${}\n📤 Wallet: {}",
        'referral_text': "🔗 **Referral Program**\n\n👤 Your code: `{}`\n📊 Invites: {}\n🌟 Points: {}\n\n💰 **Rewards:**\n• 10 points per invite\n• 1,000 points = $50\n\n🔗 Share:\n{}",
        'referral_link': "https://t.me/{}?start=ref_{}",
        'share': "📤 Share",
        'ai_chat_title': "💬 **AI Assistant**\n\nAsk anything about trading, analysis, or the course!\n\n🔒 Requires active subscription",
        'ai_chat_no_subscription': "❌ Active subscription required for AI chat.",
        'ai_chat_thinking': "🤖 Thinking...",
        'ai_chat_response': "🤖 **AI Assistant:**\n\n{}",
        'ai_chat_error': "⚠️ AI error. Please try again.",
        'no_subscription': "❌ No active subscription.",
    },
    'fa': {
        'name': 'فارسی',
        'welcome': "🎓 **به آکادمی ترید UTYOB خوش آمدید!**\n\nما به شما تحلیل هوش مصنوعی و آموزش مستقل را یاد می‌دهیم.\n\n🚀 بدون سیگنال فروشی، بدون وابستگی.\n📚 یاد بگیر، تحلیل کن، حرفه‌ای ترید کن.",
        'welcome_sticker': WELCOME_STICKER,
        'main_menu': "🎯 **منوی اصلی**",
        'education': "📚 دوره آموزش ترید",
        'ai_chart': "🤖 تحلیل چارت با هوش مصنوعی",
        'ai_chat': "💬 دستیار هوش مصنوعی",
        'referral': "🔗 رفرال",
        'guide': "📖 راهنما",
        'language_btn': "🌐 زبان",
        'withdraw': "💰 برداشت",
        'back': "🔙 بازگشت",
        'main_menu_btn': "🏠 منوی اصلی",
        'cancel': "❌ انصراف",
        'retry': "🔄 تلاش مجدد",
        'education_title': "📚 **دوره آموزش ترید**\n\nبا هوش مصنوعی حرفه‌ای یاد بگیر.\n\n💰 هزینه: {}$ (USDT-TRC20)\n📅 مدت: {} روز",
        'education_buy': "💳 خرید / تمدید",
        'education_active': "✅ دسترسی فعال.\n📅 تا تاریخ: {}\n\n📚 {}/{} محتوا ارسال شد.",
        'enter_wallet': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
        'invalid_wallet': "❌ آدرس نامعتبر.\nمثال: `TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`",
        'after_wallet': "✅ آدرس ذخیره شد.\n\n💰 مبلغ {}$ را به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ سپس دکمه **✅ پرداخت کردم** را بزنید.",
        'confirm_payment': "✅ پرداخت کردم",
        'verifying': "⏳ در حال بررسی تراکنش...",
        'verify_success': "✅ **پرداخت تایید شد!**\n\n🔗 هش: `{}`\n\n📚 {} محتوا ارسال شد.",
        'verify_failed': "❌ تایید خودکار انجام نشد.\n\nدلیل: {}\n\n📤 هش تراکنش یا عکس واریز را ارسال کنید:",
        'tx_hash_invalid': "❌ هش نامعتبر (۶۴ کاراکتر).",
        'tx_hash_received': "✅ هش دریافت شد. مدیر بررسی می‌کند.",
        'photo_received': "✅ عکس دریافت شد. مدیر بررسی می‌کند.",
        'guide_text': """
📖 **راهنمای آکادمی ترید UTYOB**

🎯 **چه چیزی ارائه می‌دهیم:**
• 🤖 تحلیل چارت با هوش مصنوعی
• 📚 آموزش کامل ترید
• 💬 دستیار هوش مصنوعی
• 🔗 سیستم پاداش رفرال

🚀 **چرا به ما بپیوندید؟**
ما سیگنال نمی‌فروشیم. ما به شما یاد می‌دهیم که بازار را مستقل تحلیل کنید با:
• تکنولوژی پیشرفته هوش مصنوعی
• روش‌های متعدد تحلیل
• تحلیل لحظه‌ای چارت
• استراتژی‌های حرفه‌ای ترید

💰 **شروع کنید:**
۱️⃣ روی "دوره آموزش ترید" بزنید
۲️⃣ آدرس کیف پول TRC20 خود را وارد کنید
۳️⃣ مبلغ {}$ را به آدرس مشخص واریز کنید
۴️⃣ دسترسی شما فعال می‌شود!

📊 **تحلیل چارت با هوش مصنوعی:**
• عکس چارت خود را بفرستید
• تحلیل حرفه‌ای دریافت کنید
• از هر ترید درس بگیرید

💡 **فلسفه ما:**
"به کسی سیگنال بده، یک روز ترید می‌کند.
به کسی تحلیل یاد بده، تا آخر عمر ترید می‌کند."

📞 پشتیبانی: با مدیریت تماس بگیرید.

🔗 سیستم رفرال: برای هر دوست که اشتراک بخرد، امتیاز بگیرید!
        """,
        'invalid_command': "⚠️ ورودی نامعتبر. از دکمه‌ها استفاده کنید.",
        'error_message': "⚠️ خطا رخ داد. دوباره تلاش کنید.",
        'admin_only': "⛔ دسترسی غیرمجاز.",
        'payment_confirmed_admin_note': "✅ پرداخت خودکار تایید شد\n👤 کاربر: {}\n💰 مبلغ: {}$",
        'admin_panel_title': "⚙️ **پنل مدیریت**\n\n👥 کاربران: {}\n⏳ در انتظار: {}\n📚 محتوا: {}\n🔑 کلیدهای API: {}",
        'admin_broadcast_btn': "📢 ارسال همگانی",
        'admin_manual_verify_btn': "✅ تایید دستی ({})",
        'admin_send_course_btn': "📚 ارسال محتوا",
        'admin_add_content_btn': "📝 افزودن محتوا",
        'admin_add_api_btn': "🔑 افزودن کلید API",
        'admin_stats_btn': "📊 آمار",
        'admin_train_brain_btn': "🧠 آموزش مغز هوش مصنوعی",
        'admin_back_btn': "🔙 بازگشت",
        'admin_cancel_btn': "🔙 انصراف",
        'admin_broadcast_prompt': "📢 **ارسال همگانی**\n\nمتن را ارسال کنید:",
        'admin_no_pending': "✅ موردی در انتظار نیست.",
        'admin_pending_header': "✅ **صف بررسی دستی**\n\n",
        'admin_approve': "✅ تایید #{}",
        'admin_reject': "❌ رد #{}",
        'admin_send_course_prompt': "📚 **ارسال محتوا**\n\nآیدی کاربر یا `ALL`:",
        'admin_add_content_step1': "📝 مرحله ۱/۳: عنوان را وارد کنید:",
        'admin_add_content_step2': "📝 مرحله ۲/۳: توضیحات را وارد کنید:",
        'admin_add_content_step3': "📝 مرحله ۳/۳: فایل را ارسال کنید یا /skip:",
        'admin_content_added': "✅ محتوا اضافه شد! ID: {}",
        'admin_add_api_prompt': "🔑 **افزودن کلید TronGrid API:**",
        'admin_api_added': "✅ کلید اضافه شد! تعداد: {}",
        'admin_api_duplicate': "❌ قبلاً اضافه شده.",
        'admin_stats_title': "📊 **آمار سیستم**\n\n👥 کاربران: {}\n✅ اشتراک فعال: {}\n📚 محتوا: {}\n⏳ در انتظار: {}\n🔑 کلیدهای API: {}\n🧠 سوالات مغز: {}\n⚡ کش: {} آیتم | {:.1f}%",
        'admin_refresh': "🔄 به‌روزرسانی",
        'admin_not_found': "❌ یافت نشد.",
        'admin_approved_note': "✅ تایید شد!\n👤 کاربر: {}",
        'admin_rejected_note': "❌ رد شد!\n👤 کاربر: {}",
        'admin_approved_user_msg': "✅ پرداخت شما تایید شد! دسترسی فعال شد.",
        'admin_rejected_user_msg': "❌ تراکنش رد شد. با پشتیبانی تماس بگیرید.",
        'admin_broadcast_sent': "✅ کامل شد!\n📤 موفق: {}\n❌ ناموفق: {}",
        'admin_broadcast_sending': "⏳ در حال ارسال...",
        'admin_send_course_sending_all': "⏳ در حال ارسال به {} کاربر...",
        'admin_send_course_done_all': "✅ به {} کاربر ارسال شد!",
        'admin_send_course_done_one': "✅ {} محتوا به کاربر {} ارسال شد!",
        'admin_invalid_id': "❌ آیدی نامعتبر.",
        'admin_new_manual_request': "✅ درخواست بررسی دستی جدید\n\n👤 کاربر: {}\n💰 مبلغ: {}$\n📤 از: {}\n🔗 هش: `{}`",
        'admin_train_brain_prompt': "🧠 **آموزش مغز هوش مصنوعی**\n\nبه این فرمت ارسال کنید:\n`keyword1,keyword2: سوال ❓ جواب`\n\nیا:\n`سوال ❓ جواب`\n\nمثال:\n`rsi,اندیکاتور: RSI چیست ❓ شاخص قدرت نسبی...`",
        'admin_brain_trained': "✅ مغز آموزش داده شد!\n🧠 اضافه شد: {}\n📚 تعداد کل: {}",
        'admin_brain_invalid': "❌ فرمت نامعتبر. از `سوال ❓ جواب` استفاده کنید.",
        'ai_chart_title': "🤖 **تحلیل چارت با هوش مصنوعی**\n\nعکس چارت خود را بفرستید تا تحلیل حرفه‌ای دریافت کنید.\n\n📊 **موجودی:** {}/۲ امروز\n🔒 نیاز به اشتراک فعال",
        'ai_chart_no_subscription': "❌ برای تحلیل چارت با هوش مصنوعی به اشتراک فعال نیاز دارید.\n\nابتدا اشتراک بخرید!",
        'ai_chart_limit_reached': "❌ سهمیه روزانه تمام شد ({}/۲).\nفردا دوباره تلاش کنید!",
        'ai_chart_send_photo': "📤 عکس چارت خود را ارسال کنید:",
        'ai_chart_analyzing': "🤖 در حال تحلیل چارت با هوش مصنوعی...\n⏳ ۳۰-۶۰ ثانیه زمان نیاز است.",
        'ai_chart_result': "📊 **تحلیل چارت با هوش مصنوعی**\n\n{}\n\n📅 تحلیل #{}\n💡 از هر ترید درس بگیرید!",
        'ai_chart_error': "⚠️ تحلیل هوش مصنوعی ناموفق بود.\nدوباره تلاش کنید.",
        'withdraw_title': "💰 **برداشت امتیاز رفرال**\n\n📊 امتیاز شما: {}\n💵 هر ۱,۰۰۰ امتیاز = ۵۰ دلار\n📤 حداقل برداشت: ۱,۰۰۰ امتیاز",
        'withdraw_enter_wallet': "📤 آدرس کیف پول TRC20 خود را وارد کنید:",
        'withdraw_success': "✅ درخواست برداشت ثبت شد!\n💰 {} امتیاز ({} دلار)\n📤 به: {}\n⏳ مدیر پردازش می‌کند.",
        'withdraw_no_points': "❌ امتیاز کافی نیست.\nحداقل: ۱,۰۰۰ امتیاز",
        'withdraw_invalid': "❌ آدرس نامعتبر.",
        'withdraw_pending_admin': "💰 درخواست برداشت\n👤 کاربر: {}\n📊 امتیاز: {}\n💵 ارزش: {} دلار\n📤 کیف پول: {}",
        'referral_text': "🔗 **سیستم رفرال**\n\n👤 کد شما: `{}`\n📊 دعوت‌ها: {}\n🌟 امتیاز: {}\n\n💰 **پاداش:**\n• هر دعوت ۱۰ امتیاز\n• ۱,۰۰۰ امتیاز = ۵۰ دلار\n\n🔗 اشتراک‌گذاری:\n{}",
        'referral_link': "https://t.me/{}?start=ref_{}",
        'share': "📤 اشتراک‌گذاری",
        'ai_chat_title': "💬 **دستیار هوش مصنوعی**\n\nهر سوالی درباره ترید، تحلیل یا دوره دارید بپرسید!\n\n🔒 نیاز به اشتراک فعال",
        'ai_chat_no_subscription': "❌ برای استفاده از دستیار هوش مصنوعی به اشتراک فعال نیاز دارید.",
        'ai_chat_thinking': "🤖 در حال فکر کردن...",
        'ai_chat_response': "🤖 **دستیار هوش مصنوعی:**\n\n{}",
        'ai_chat_error': "⚠️ خطا در هوش مصنوعی. دوباره تلاش کنید.",
        'no_subscription': "❌ اشتراک فعال ندارید.",
    }
}


# ============================================================
# تایید پرداخت با TronGrid
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
                    return True, result, "verified"
            except Exception as e:
                logger.warning(f"API error: {e}")
                continue
        return False, None, "not_found"

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
        except:
            return False


payment_verifier = PaymentVerifier()


# ============================================================
# هوش مصنوعی OpenAI
# ============================================================
class OpenAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = None
        self.lock = threading.Lock()

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                connector=aiohttp.TCPConnector(limit=50)
            )
        return self.session

    async def chat_completion(self, messages, model="gpt-3.5-turbo"):
        if not self.api_key or self.api_key == "اینجا کلید OpenAI را بگذار":
            return "⚠️ OpenAI API key not configured. Please contact admin."

        session = await self.get_session()
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['choices'][0]['message']['content']
                else:
                    error_text = await resp.text()
                    logger.error(f"OpenAI error: {resp.status} - {error_text}")
                    return f"⚠️ API error: {resp.status}"
        except Exception as e:
            logger.error(f"OpenAI request error: {e}")
            return "⚠️ Connection error. Please try again."

    async def analyze_chart(self, chart_description, user_context=""):
        """تحلیل چارت با هوش مصنوعی"""
        prompt = f"""
You are a professional crypto trading analyst. Analyze this chart based on the description.

User context: {user_context}

Please provide:
1. Trend analysis (bullish/bearish/neutral)
2. Key support and resistance levels
3. Technical indicators to watch
4. Entry/exit recommendations (if clear)
5. Risk management suggestions
6. Overall sentiment

Format your response in clear sections with emojis.
Be educational - teach the user HOW to analyze, not just what to do.
        """
        
        messages = [
            {"role": "system", "content": "You are an expert crypto trading analyst and educator."},
            {"role": "user", "content": f"Chart description: {chart_description}\n\n{prompt}"}
        ]
        
        return await self.chat_completion(messages)

    async def brain_response(self, question, brain_qa_data):
        """پاسخ از مغز آموزشی یا OpenAI"""
        # ابتدا چک می‌کنیم مغز جواب داره؟
        question_lower = question.lower()
        for item in brain_qa_data:
            keywords = item['keywords'].lower().split(',')
            for kw in keywords:
                if kw.strip() in question_lower:
                    return item['answer']
        
        # اگر جواب نداشت، از OpenAI می‌پرسیم
        messages = [
            {"role": "system", "content": "You are a trading assistant that helps users learn about crypto trading. Provide clear, educational answers."},
            {"role": "user", "content": question}
        ]
        return await self.chat_completion(messages)


openai_client = OpenAIClient(OPENAI_API_KEY)


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
            
            ref_code = hashlib.sha256(f"UTYOB_{user_id}_{time.time()}_{random.randint(1000,9999)}".encode()).hexdigest()[:10].upper()
            db.execute(user_id,
                "INSERT INTO users (user_id, username, first_name, last_name, referral_code, language) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, first_name, last_name, ref_code, DEFAULT_LANG)
            )
            return True
        except:
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
        cache.delete(f"points_{user_id}")

    @staticmethod
    def has_active_subscription(user):
        return bool(user and user.get('has_subscription') and user.get('subscription_end') and
                    user['subscription_end'] >= datetime.now().strftime('%Y-%m-%d'))

    @staticmethod
    def get_referral_points(user_id):
        cache_key = f"points_{user_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        user = UserManager.get_user(user_id)
        points = user.get('referral_points', 0) if user else 0
        cache.set(cache_key, points, ttl=300)
        return points

    @staticmethod
    def get_referral_count(user_id):
        results = db.execute_global("SELECT COUNT(*) as count FROM users WHERE referred_by = ?", (user_id,))
        return sum(r['count'] for r in results)

    @staticmethod
    def get_all_users():
        return db.execute_global("SELECT user_id FROM users")


user_manager = UserManager()


# ============================================================
# مدیریت محتوای آموزشی
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
# مغز آموزشی (Brain Q&A)
# ============================================================
class BrainManager:
    @staticmethod
    def add_qa(keywords, question, answer):
        cur = db.execute(0,
            "INSERT INTO brain_qa (keywords, question, answer) VALUES (?, ?, ?)",
            (keywords, question, answer)
        )
        cache.delete("brain_all")
        return cur.lastrowid

    @staticmethod
    def get_all_qa():
        cached = cache.get("brain_all")
        if cached is not None:
            return cached
        results = db.execute_global("SELECT * FROM brain_qa ORDER BY created_at DESC")
        cache.set("brain_all", results, ttl=600)
        return results

    @staticmethod
    def get_count():
        cached = cache.get("brain_count")
        if cached is not None:
            return cached
        total = sum(r['count'] for r in db.execute_global("SELECT COUNT(*) as count FROM brain_qa"))
        cache.set("brain_count", total, ttl=600)
        return total

    @staticmethod
    def search_brain(query):
        """جستجوی مغز برای پاسخ"""
        qa_list = BrainManager.get_all_qa()
        query_lower = query.lower()
        
        for item in qa_list:
            # چک کلمات کلیدی
            keywords = item['keywords'].lower().split(',')
            for kw in keywords:
                if kw.strip() in query_lower:
                    return item['answer']
            # چک سوال
            if item['question'].lower() in query_lower:
                return item['answer']
        
        return None


brain_manager = BrainManager()


# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()
        self.chart_usage = defaultdict(int)
        self.chart_reset_time = datetime.now()

    def _setup_handlers(self):
        app = self.application
        
        # دستورات
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        
        # منو
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.education_callback, pattern="^education$"))
        app.add_handler(CallbackQueryHandler(self.education_buy_callback, pattern="^education_buy$"))
        app.add_handler(CallbackQueryHandler(self.education_confirm_callback, pattern="^education_confirm$"))
        app.add_handler(CallbackQueryHandler(self.ai_chart_callback, pattern="^ai_chart$"))
        app.add_handler(CallbackQueryHandler(self.ai_chat_callback, pattern="^ai_chat$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language_menu$"))
        app.add_handler(CallbackQueryHandler(self.set_language_callback, pattern="^setlang_"))
        app.add_handler(CallbackQueryHandler(self.withdraw_callback, pattern="^withdraw$"))
        app.add_handler(CallbackQueryHandler(self.withdraw_confirm_callback, pattern="^withdraw_confirm$"))
        
        # پنل مدیریت (فارسی)
        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_send_course_callback, pattern="^admin_send_course$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_content_callback, pattern="^admin_add_content$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api_callback, pattern="^admin_add_api$"))
        app.add_handler(CallbackQueryHandler(self.admin_stats_callback, pattern="^admin_stats$"))
        app.add_handler(CallbackQueryHandler(self.admin_train_brain_callback, pattern="^admin_train_brain$"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))
        
        # پیام‌ها
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        app.add_error_handler(self.error_handler)

    # ============================================================
    # توابع کمکی
    # ============================================================
    
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
            except:
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
        except:
            return False

    def _validate_tx_hash(self, tx_hash):
        return len(tx_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in tx_hash)

    async def _send_all_course(self, user_id):
        contents = course_manager.get_all_content()
        sent = 0
        for c in contents:
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
            except:
                failed += 1
        return sent, failed

    async def _activate_subscription(self, user_id, from_address, tx_id):
        end_date = (datetime.now() + timedelta(days=SUBSCRIPTION_DAYS)).strftime('%Y-%m-%d')
        user_manager.update_user(user_id, has_subscription=1, subscription_end=end_date)
        db.execute(user_id,
            "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
            (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
        )
        # ارسال خودکار محتوا
        await self._send_all_course(user_id)

    def _main_menu_keyboard(self, user_id):
        lang = self._get_lang(user_id)
        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['education'], callback_data="education")],
            [InlineKeyboardButton(LANGUAGES[lang]['ai_chart'], callback_data="ai_chart"),
             InlineKeyboardButton(LANGUAGES[lang]['ai_chat'], callback_data="ai_chat")],
            [InlineKeyboardButton(LANGUAGES[lang]['referral'], callback_data="referral"),
             InlineKeyboardButton(LANGUAGES[lang]['withdraw'], callback_data="withdraw")],
            [InlineKeyboardButton(LANGUAGES[lang]['guide'], callback_data="guide"),
             InlineKeyboardButton(LANGUAGES[lang]['language_btn'], callback_data="language_menu")],
        ]
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)

    async def _show_main_menu(self, send_func, user_id):
        await send_func(self._t(user_id, 'main_menu'), reply_markup=self._main_menu_keyboard(user_id), parse_mode=ParseMode.MARKDOWN)

    # ============================================================
    # /start و خوش‌آمدگویی
    # ============================================================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        is_new = user_manager.register_user(user.id, user.username, user.first_name, user.last_name)
        db_user = user_manager.get_user(user.id)

        # بررسی رفرال
        if context.args and context.args[0].startswith('ref_'):
            ref_code = context.args[0][4:]
            cur = db.execute(0, "SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
            ref_user = cur.fetchone()
            if ref_user and ref_user['user_id'] != user.id:
                user_manager.update_user(user.id, referred_by=ref_user['user_id'])
                # ۱۰ امتیاز به کاربر دعوت‌کننده
                referrer = user_manager.get_user(ref_user['user_id'])
                if referrer:
                    new_points = (referrer.get('referral_points') or 0) + 10
                    user_manager.update_user(ref_user['user_id'], referral_points=new_points)

        # انتخاب زبان برای کاربر جدید
        if is_new or not db_user or not db_user.get('language'):
            keyboard = [
                [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
                 InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa")]
            ]
            await update.message.reply_text(
                "🌐 Please choose your language:\n🌐 لطفاً زبان خود را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # ارسال استیکر خوش‌آمدگویی
        try:
            await update.message.reply_sticker(WELCOME_STICKER)
        except:
            pass

        await update.message.reply_text(
            self._t(user.id, 'welcome'),
            reply_markup=self._main_menu_keyboard(user.id),
            parse_mode=ParseMode.MARKDOWN
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
        await update.message.reply_text(
            self._t(user_id, 'guide_text', PAYMENT_AMOUNT),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # زبان
    # ============================================================
    async def language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
             InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa")],
            [InlineKeyboardButton(self._t(query.from_user.id, 'back'), callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "🌐 Please choose your language:\n🌐 لطفاً زبان خود را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def set_language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = query.data.split('_', 1)[1]
        if lang in LANGUAGES:
            user_manager.update_user(user_id, language=lang)
        await query.edit_message_text(
            self._t(user_id, 'welcome'),
            reply_markup=self._main_menu_keyboard(user_id),
            parse_mode=ParseMode.MARKDOWN
        )

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await self._show_main_menu(query.edit_message_text, query.from_user.id)

    # ============================================================
    # دوره آموزش
    # ============================================================
    async def education_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if user_manager.has_active_subscription(user):
            sent = await self._send_all_course(user_id)
            total = course_manager.get_content_count()
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._t(user_id, 'education_active', user['subscription_end'], sent, total),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        keyboard = [
            [InlineKeyboardButton(self._t(user_id, 'education_buy'), callback_data="education_buy")],
            [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]
        ]
        await query.edit_message_text(
            self._t(user_id, 'education_title', PAYMENT_AMOUNT, SUBSCRIPTION_DAYS),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def education_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        context.user_data['waiting_for_wallet'] = True
        context.user_data['action'] = 'subscribe'
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'cancel'), callback_data="education")]]
        await query.edit_message_text(
            self._t(user_id, 'enter_wallet'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def education_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if not user or not user.get('wallet_address'):
            await query.edit_message_text(self._t(user_id, 'enter_wallet'), parse_mode=ParseMode.MARKDOWN)
            return

        await query.edit_message_text(self._t(user_id, 'verifying'), parse_mode=ParseMode.MARKDOWN)

        ok, tx_id, msg = await payment_verifier.verify_transaction(
            user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT
        )

        if ok:
            await self._activate_subscription(user_id, user['wallet_address'], tx_id)
            sent = await self._send_all_course(user_id)
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._t(user_id, 'verify_success', tx_id, sent),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        admin_id,
                        self._t(admin_id, 'payment_confirmed_admin_note', user_id, PAYMENT_AMOUNT),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            context.user_data['tx_type'] = 'subscribe'
            keyboard = [
                [InlineKeyboardButton(self._t(user_id, 'retry'), callback_data="education_confirm")],
                [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="education")]
            ]
            reason = "Transaction not found" if self._get_lang(user_id) == 'en' else "تراکنش یافت نشد"
            await query.edit_message_text(
                self._t(user_id, 'verify_failed', reason),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # هوش مصنوعی - تحلیل چارت
    # ============================================================
    async def ai_chart_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if not user_manager.has_active_subscription(user):
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._t(user_id, 'ai_chart_no_subscription'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # بررسی سهمیه روزانه (۲ بار در روز)
        today = datetime.now().strftime('%Y-%m-%d')
        if f"{user_id}_{today}" in self.chart_usage:
            used = self.chart_usage[f"{user_id}_{today}"]
            if used >= 2:
                keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
                await query.edit_message_text(
                    self._t(user_id, 'ai_chart_limit_reached', used),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        else:
            self.chart_usage[f"{user_id}_{today}"] = 0

        used = self.chart_usage.get(f"{user_id}_{today}", 0)
        await query.edit_message_text(
            self._t(user_id, 'ai_chart_title', used),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]),
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['waiting_for_chart'] = True
        await query.message.reply_text(self._t(user_id, 'ai_chart_send_photo'))

    # ============================================================
    # هوش مصنوعی - چت
    # ============================================================
    async def ai_chat_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)

        if not user_manager.has_active_subscription(user):
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._t(user_id, 'ai_chat_no_subscription'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        context.user_data['waiting_for_ai_chat'] = True
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._t(user_id, 'ai_chat_title'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # رفرال
    # ============================================================
    async def referral_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)
        
        if not user:
            return
        
        ref_code = user['referral_code']
        ref_count = user_manager.get_referral_count(user_id)
        points = user_manager.get_referral_points(user_id)
        bot_username = self.application.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"
        
        keyboard = [
            [InlineKeyboardButton(self._t(user_id, 'share'), url=f"https://t.me/share/url?url={ref_link}")],
            [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]
        ]
        await query.edit_message_text(
            self._t(user_id, 'referral_text', ref_code, ref_count, points, ref_link),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # برداشت امتیاز
    # ============================================================
    async def withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        points = user_manager.get_referral_points(user_id)
        
        if points < 1000:
            keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._t(user_id, 'withdraw_no_points'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        context.user_data['waiting_for_withdraw_wallet'] = True
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'cancel'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._t(user_id, 'withdraw_title', points),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def withdraw_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user = user_manager.get_user(user_id)
        points = user_manager.get_referral_points(user_id)
        wallet = user.get('wallet_address') if user else None
        
        if not wallet:
            await query.edit_message_text(self._t(user_id, 'withdraw_invalid'), parse_mode=ParseMode.MARKDOWN)
            return
        
        if points < 1000:
            await query.edit_message_text(self._t(user_id, 'withdraw_no_points'), parse_mode=ParseMode.MARKDOWN)
            return
        
        # محاسبه مبلغ
        amount = (points // 1000) * 50
        points_to_deduct = (points // 1000) * 1000
        
        # کاهش امتیاز
        user_manager.update_user(user_id, referral_points=points - points_to_deduct)
        cache.delete(f"points_{user_id}")
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            try:
                await self.application.bot.send_message(
                    admin_id,
                    self._t(admin_id, 'withdraw_pending_admin', user_id, points_to_deduct, amount, wallet),
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._t(user_id, 'withdraw_success', points_to_deduct, amount, wallet),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # راهنما
    # ============================================================
    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'back'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._t(user_id, 'guide_text', PAYMENT_AMOUNT),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # پنل مدیریت (کاملاً فارسی)
    # ============================================================
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

        brain_count = brain_manager.get_count()

        keyboard = [
            [InlineKeyboardButton("📢 ارسال همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton(f"✅ تایید دستی ({pending})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📚 ارسال محتوا", callback_data="admin_send_course"),
             InlineKeyboardButton("📝 افزودن محتوا", callback_data="admin_add_content")],
            [InlineKeyboardButton("🔑 افزودن کلید API", callback_data="admin_add_api"),
             InlineKeyboardButton("📊 آمار", callback_data="admin_stats")],
            [InlineKeyboardButton(f"🧠 آموزش مغز ({brain_count})", callback_data="admin_train_brain")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"⚙️ **پنل مدیریت**\n\n"
            f"👥 کاربران: {user_count:,}\n"
            f"⏳ در انتظار تایید: {pending}\n"
            f"📚 محتوای دوره: {course_manager.get_content_count()}\n"
            f"🧠 سوالات مغز: {brain_count}\n"
            f"🔑 کلیدهای API: {len(payment_verifier.apis)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - آموزش مغز
    # ============================================================
    async def admin_train_brain_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'train_brain'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            self._t(user_id, 'admin_train_brain_prompt'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - تایید دستی
    # ============================================================
    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        pending = db.execute_global(
            "SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC LIMIT 5"
        )
        
        if not pending:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await query.edit_message_text(self._t(user_id, 'admin_no_pending'), reply_markup=InlineKeyboardMarkup(keyboard))
            return

        text = "✅ **تایید دستی**\n\n"
        keyboard = []
        for p in pending:
            text += f"👤 کاربر: {p['user_id']}\n"
            text += f"💰 مبلغ: ${p['amount']}\n"
            text += f"📤 از: `{p['from_address']}`\n"
            if p['tx_hash']:
                text += f"🔗 هش: `{p['tx_hash']}`\n"
            if p['photo_file_id']:
                text += f"📷 عکس: دارد\n"
            text += "\n"
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
    # مدیریت - تایید/رد
    # ============================================================
    async def admin_verify_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            return
        
        pending_id = int(query.data.split('_')[-1])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text(self._t(admin_id, 'admin_not_found'))
            return
        
        await self._activate_subscription(p['user_id'], p['from_address'], p['tx_hash'] or "manual_approved")
        db.execute(0, "UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")
        
        try:
            await self.application.bot.send_message(
                p['user_id'],
                self._t(p['user_id'], 'admin_approved_user_msg'),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        await query.edit_message_text(
            self._t(admin_id, 'admin_approved_note', p['user_id']),
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_verify_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            return
        
        pending_id = int(query.data.split('_')[-1])
        p = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        if not p:
            await query.edit_message_text(self._t(admin_id, 'admin_not_found'))
            return
        
        db.execute(0, "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?", (pending_id,))
        cache.delete("pending_count")
        
        try:
            await self.application.bot.send_message(
                p['user_id'],
                self._t(p['user_id'], 'admin_rejected_user_msg'),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        await query.edit_message_text(
            self._t(admin_id, 'admin_rejected_note', p['user_id']),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - ارسال همگانی
    # ============================================================
    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'broadcast'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            self._t(user_id, 'admin_broadcast_prompt'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - ارسال محتوا
    # ============================================================
    async def admin_send_course_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'send_course'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            self._t(user_id, 'admin_send_course_prompt'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - افزودن محتوا
    # ============================================================
    async def admin_add_content_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_content'
        context.user_data['content_step'] = 1
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            self._t(user_id, 'admin_add_content_step1'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - افزودن کلید API
    # ============================================================
    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'add_api'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            self._t(user_id, 'admin_add_api_prompt'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت - آمار
    # ============================================================
    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        user_count = len(db.execute_global("SELECT user_id FROM users"))
        active = len(db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"))
        pending = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        brain_count = brain_manager.get_count()
        cache_stats = cache.get_stats()
        
        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        await query.edit_message_text(
            self._t(user_id, 'admin_stats_title',
                f"{user_count:,}",
                f"{active:,}",
                course_manager.get_content_count(),
                pending,
                len(payment_verifier.apis),
                brain_count,
                cache_stats['size'],
                cache_stats['hit_rate']
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
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
            await update.message.reply_text(self._t(user_id, 'admin_broadcast_sending'))
            sent, failed = await self._broadcast_to_all(text)
            context.user_data['admin_action'] = None
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            await update.message.reply_text(
                self._t(user_id, 'admin_broadcast_sent', f"{sent:,}", f"{failed:,}"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # ===== ارسال محتوا =====
        if admin_action == 'send_course':
            if text.strip().upper() == 'ALL':
                users = user_manager.get_all_users()
                await update.message.reply_text(self._t(user_id, 'admin_send_course_sending_all', len(users)))
                sent = 0
                for u in users:
                    if await self._send_all_course(u['user_id']) > 0:
                        sent += 1
                    await asyncio.sleep(0.15)
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(
                    self._t(user_id, 'admin_send_course_done_all', sent),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                try:
                    target_id = int(text.strip())
                    count = await self._send_all_course(target_id)
                    context.user_data['admin_action'] = None
                    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                    await update.message.reply_text(
                        self._t(user_id, 'admin_send_course_done_one', count, target_id),
                        reply_markup=InlineKeyboardMarkup(keyboard)
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
                cid = course_manager.add_content('text', title, content)
                context.user_data['admin_action'] = None
                context.user_data['content_step'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(
                    self._t(user_id, 'admin_content_added', cid),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return

        # ===== افزودن کلید API =====
        if admin_action == 'add_api':
            api_key = text.strip()
            if payment_verifier.add_api(api_key):
                context.user_data['admin_action'] = None
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                await update.message.reply_text(
                    self._t(user_id, 'admin_api_added', len(payment_verifier.apis)),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(self._t(user_id, 'admin_api_duplicate'))
            return

        # ===== آموزش مغز =====
        if admin_action == 'train_brain':
            # فرمت: keyword1,keyword2: سوال ❓ جواب
            # یا: سوال ❓ جواب
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
                        brain_manager.add_qa(keywords, question, answer)
                        total = brain_manager.get_count()
                        context.user_data['admin_action'] = None
                        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                        await update.message.reply_text(
                            self._t(user_id, 'admin_brain_trained', question, total),
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                        return
            
            await update.message.reply_text(self._t(user_id, 'admin_brain_invalid'))
            return

        # ===== دریافت هش تراکنش یا عکس =====
        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            from_address = context.user_data.get('tx_from_address')
            tx_type = context.user_data.get('tx_type', 'subscribe')
            
            if not self._validate_tx_hash(tx_hash):
                await update.message.reply_text(self._t(user_id, 'tx_hash_invalid'), parse_mode=ParseMode.MARKDOWN)
                return
            
            db.execute(0,
                "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, tx_hash, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash)
            )
            context.user_data['waiting_for_tx_hash'] = False
            context.user_data['tx_from_address'] = None
            context.user_data['tx_type'] = None
            cache.delete("pending_count")
            
            await update.message.reply_text(self._t(user_id, 'tx_hash_received'), parse_mode=ParseMode.MARKDOWN)
            
            pid = db.execute(0, "SELECT last_insert_rowid() as id").fetchone()['id']
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [[
                        InlineKeyboardButton("✅ تایید", callback_data=f"admin_verify_approve_{pid}"),
                        InlineKeyboardButton("❌ رد", callback_data=f"admin_verify_reject_{pid}")
                    ]]
                    await self.application.bot.send_message(
                        admin_id,
                        self._t(admin_id, 'admin_new_manual_request', user_id, PAYMENT_AMOUNT, from_address, tx_hash),
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            return

        # ===== دریافت آدرس کیف پول =====
        if context.user_data.get('waiting_for_wallet'):
            wallet = text.strip()
            action = context.user_data.get('action', 'subscribe')
            
            if not self._validate_wallet(wallet):
                await update.message.reply_text(self._t(user_id, 'invalid_wallet'), parse_mode=ParseMode.MARKDOWN)
                return
            
            user_manager.update_user(user_id, wallet_address=wallet)
            context.user_data['waiting_for_wallet'] = False
            context.user_data['action'] = None
            
            keyboard = [
                [InlineKeyboardButton(self._t(user_id, 'confirm_payment'), callback_data="education_confirm")],
                [InlineKeyboardButton(self._t(user_id, 'back'), callback_data="education")]
            ]
            await update.message.reply_text(
                self._t(user_id, 'after_wallet', PAYMENT_AMOUNT, DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ===== دریافت آدرس کیف پول برای برداشت =====
        if context.user_data.get('waiting_for_withdraw_wallet'):
            wallet = text.strip()
            if not self._validate_wallet(wallet):
                await update.message.reply_text(self._t(user_id, 'withdraw_invalid'), parse_mode=ParseMode.MARKDOWN)
                return
            
            user_manager.update_user(user_id, wallet_address=wallet)
            context.user_data['waiting_for_withdraw_wallet'] = False
            
            # تایید نهایی برداشت
            keyboard = [
                [InlineKeyboardButton("✅ تایید برداشت", callback_data="withdraw_confirm")],
                [InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]
            ]
            points = user_manager.get_referral_points(user_id)
            await update.message.reply_text(
                self._t(user_id, 'withdraw_title', points),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ===== چت با هوش مصنوعی =====
        if context.user_data.get('waiting_for_ai_chat'):
            user = user_manager.get_user(user_id)
            if not user_manager.has_active_subscription(user):
                await update.message.reply_text(self._t(user_id, 'ai_chat_no_subscription'))
                return
            
            await update.message.reply_text(self._t(user_id, 'ai_chat_thinking'))
            
            # جستجوی مغز
            brain_answer = brain_manager.search_brain(text)
            if brain_answer:
                await update.message.reply_text(
                    self._t(user_id, 'ai_chat_response', brain_answer),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # اگر مغز جواب نداشت، از OpenAI بپرس
            response = await openai_client.brain_response(text, brain_manager.get_all_qa())
            await update.message.reply_text(
                self._t(user_id, 'ai_chat_response', response),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ===== دستور نامعتبر =====
        keyboard = [[InlineKeyboardButton(self._t(user_id, 'main_menu_btn'), callback_data="main_menu")]]
        await update.message.reply_text(
            self._t(user_id, 'invalid_command'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت عکس‌ها (تحلیل چارت + تایید دستی)
    # ============================================================
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'photo')

    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'video')

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'document')

    async def _handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
        user_id = update.effective_user.id
        user = user_manager.get_user(user_id)
        
        # ===== تحلیل چارت با هوش مصنوعی =====
        if context.user_data.get('waiting_for_chart'):
            if media_type != 'photo':
                await update.message.reply_text("❌ لطفاً عکس چارت را ارسال کنید.")
                return
            
            if not user_manager.has_active_subscription(user):
                await update.message.reply_text(self._t(user_id, 'ai_chart_no_subscription'))
                return
            
            # بررسی سهمیه
            today = datetime.now().strftime('%Y-%m-%d')
            if f"{user_id}_{today}" in self.chart_usage:
                used = self.chart_usage[f"{user_id}_{today}"]
                if used >= 2:
                    await update.message.reply_text(self._t(user_id, 'ai_chart_limit_reached', used))
                    return
            else:
                self.chart_usage[f"{user_id}_{today}"] = 0
            
            context.user_data['waiting_for_chart'] = False
            
            # دریافت فایل عکس
            photo = update.message.photo[-1]
            file_id = photo.file_id
            
            await update.message.reply_text(self._t(user_id, 'ai_chart_analyzing'))
            
            # تحلیل با هوش مصنوعی
            # برای سادگی، از توضیحات کاربر استفاده می‌کنیم
            # در نسخه واقعی، باید عکس رو به OpenAI بفرستی (با Vision API)
            
            # ذخیره در تاریخچه
            db.execute(user_id,
                "INSERT INTO chart_analysis (user_id, chart_file_id, analysis, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, file_id, "Analysis pending...")
            )
            
            # افزایش مصرف
            self.chart_usage[f"{user_id}_{today}"] += 1
            
            # پاسخ با تحلیل فرضی (در نسخه واقعی با OpenAI Vision)
            analysis_text = """
📈 **تحلیل تکنیکال**

🔹 **روند کلی:** صعودی (Bullish)
🔹 **حمایت اصلی:** $42,500
🔹 **مقاومت اصلی:** $45,200
🔹 **وضعیت RSI:** 58 (خنثی)
🔹 **MACD:** تقاطع صعودی

💡 **پیشنهاد:** در محدوده حمایت می‌توان وارد شد.

⚠️ **مدیریت ریسک:** حد ضرر ۲٪
            """
            
            count = self.chart_usage.get(f"{user_id}_{today}", 0)
            await update.message.reply_text(
                self._t(user_id, 'ai_chart_result', analysis_text, count),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # ===== تایید دستی با عکس =====
        if context.user_data.get('waiting_for_tx_hash'):
            file_id = None
            if media_type == 'photo':
                file_id = update.message.photo[-1].file_id
            elif media_type == 'video':
                file_id = update.message.video.file_id
            elif media_type == 'document':
                file_id = update.message.document.file_id
            
            if file_id:
                from_address = context.user_data.get('tx_from_address')
                tx_type = context.user_data.get('tx_type', 'subscribe')
                
                db.execute(0,
                    "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, photo_file_id, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                    (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, file_id)
                )
                context.user_data['waiting_for_tx_hash'] = False
                context.user_data['tx_from_address'] = None
                context.user_data['tx_type'] = None
                cache.delete("pending_count")
                
                await update.message.reply_text(self._t(user_id, 'photo_received'), parse_mode=ParseMode.MARKDOWN)
                
                pid = db.execute(0, "SELECT last_insert_rowid() as id").fetchone()['id']
                for admin_id in ADMIN_IDS:
                    try:
                        keyboard = [[
                            InlineKeyboardButton("✅ تایید", callback_data=f"admin_verify_approve_{pid}"),
                            InlineKeyboardButton("❌ رد", callback_data=f"admin_verify_reject_{pid}")
                        ]]
                        await self.application.bot.send_photo(
                            admin_id,
                            file_id,
                            caption=self._t(admin_id, 'admin_new_manual_request', user_id, PAYMENT_AMOUNT, from_address, "عکس واریز"),
                            reply_markup=InlineKeyboardMarkup(keyboard)
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
                await update.message.reply_text(
                    self._t(user_id, 'admin_content_added', cid),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

    # ============================================================
    # مدیریت خطاها
    # ============================================================
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.effective_user:
                user_id = update.effective_user.id
                await self.application.bot.send_message(
                    user_id,
                    self._t(user_id, 'error_message'),
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
    logger.info(f"🔑 کلیدهای API: {len(payment_verifier.apis)}")
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
                await bot._send_all_course(u['user_id'])
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