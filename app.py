# ============================================================
# ربات کامل UTYOB - قرعه‌کشی + آموزش ترید
# نسخه نهایی - تمام قابلیت‌ها یکجا
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
from flask import Flask, request, jsonify

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ============================================================
# تنظیمات اولیه
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '123456789').split(',')]

TRONGRID_APIS = [
    "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
]

DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PAYMENT_AMOUNT = 100

DB_SHARDS = 100
CACHE_TTL = 300

# ============================================================
# دیتابیس با ۱۰۰ شارد
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
            conn.execute("PRAGMA cache_size=10000")
            self.connections[i] = conn
            self.locks[i] = threading.Lock()
            self._create_tables(conn, i)
            
    def _create_tables(self, conn, shard_id):
        cursor = conn.cursor()
        
        # ===== جدول کاربران =====
        cursor.execute('''
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
                last_win_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== جدول تراکنش‌ها (عمومی) =====
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
                retry_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== جدول تایید دستی =====
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
        
        # ===== جدول قرعه‌کشی =====
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
        
        # ===== جدول برندگان =====
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
        
        # ===== جدول تنظیمات =====
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== جدول محتوای آموزشی (جدید) =====
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS course_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT DEFAULT 'text',
                title TEXT,
                content TEXT,
                file_id TEXT,
                file_name TEXT,
                file_size INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ===== جدول ارسال خودکار به کاربران (برای جلوگیری از ارسال دوباره) =====
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_sent (
                user_id INTEGER,
                content_id INTEGER,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, content_id)
            )
        ''')
        
        # ایندکس‌ها
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(tx_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_user ON winners(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_paid ON winners(paid_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_user ON pending_verifications(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_verifications(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_type ON pending_verifications(tx_type)')
        
        conn.commit()
        
    def get_shard(self, user_id):
        return hash(str(user_id)) % self.num_shards
        
    def get_connection(self, user_id):
        shard = self.get_shard(user_id)
        return self.connections[shard], self.locks[shard]
        
    def execute(self, user_id, query, params=(), commit=True):
        conn, lock = self.get_connection(user_id)
        with lock:
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
    
    def execute_all_shards(self, query, params=()):
        """اجرای یک کوئری روی همه شاردها و برگرداندن همه نتایج"""
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
# سیستم کش
# ============================================================
class CacheManager:
    def __init__(self):
        self.cache = {}
        self.expiry = {}
        self.lock = threading.Lock()
        
    def set(self, key, value, ttl=CACHE_TTL):
        with self.lock:
            self.cache[key] = value
            self.expiry[key] = time.time() + ttl
            
    def get(self, key):
        with self.lock:
            if key in self.cache and time.time() < self.expiry[key]:
                return self.cache[key]
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]
            return None
            
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]

cache = CacheManager()

# ============================================================
# سیستم چندزبانه کامل
# ============================================================
LANGUAGES = {
    'en': {
        'name': 'English',
        'emoji': '🇬🇧',
        # منوی اصلی
        'welcome': "🎮 **Welcome to UTYOB Bot!**\n\nChoose an option:",
        'main_menu': "🎯 **UTYOB Bot**\n\nSelect an option:",
        'lottery': "🎰 Lottery",
        'education': "📚 Education",
        'referral': "🔗 Referral",
        'guide': "📖 Guide",
        'language': "🌐 Language",
        'admin_panel': "⚙️ Admin",
        'back': "🔙 Back",
        'main_menu_btn': "🏠 Main Menu",
        
        # قرعه‌کشی
        'lottery_title': "🎰 **Lottery**\n\n💰 Entry: $100\n🏆 Prize: Up to $10,000",
        'join_lottery': "🎯 Join Lottery",
        'lottery_enter_wallet': "📤 Enter your TRC20 wallet address:",
        'lottery_after_wallet': "✅ Wallet saved!\n\nSend $100 to:\n`{}`\n\nAfter sending, click Confirm.",
        'lottery_confirm': "✅ Confirm Payment",
        'lottery_cancel': "❌ Cancel",
        'lottery_verifying': "⏳ Verifying payment...",
        'lottery_success': "✅ Payment verified! 🎉\nTx: `{}`\n\nGood luck!",
        'lottery_failed': "❌ Payment verification failed!\nReason: {}\n\nSend your TX hash for manual verification:",
        'lottery_no_subscription': "❌ No active subscription!\n\nBuy a subscription first.",
        
        # آموزش
        'education_title': "📚 **Education & Signals**\n\nLearn professional trading!",
        'education_buy': "💰 Buy Course ($100)",
        'education_enter_wallet': "📤 Enter your TRC20 wallet address:",
        'education_after_wallet': "✅ Wallet saved!\n\nSend $100 to:\n`{}`\n\nAfter sending, click Confirm.",
        'education_confirm': "✅ Confirm Payment",
        'education_verifying': "⏳ Verifying payment...",
        'education_success': "✅ Payment verified! 🎉\nTx: `{}`\n\nAccess granted!",
        'education_failed': "❌ Payment verification failed!\nReason: {}\n\nSend your TX hash:",
        'education_already_purchased': "✅ You already have access!",
        
        # اشتراک
        'subscribe': "🔄 Subscribe",
        'subscribe_title': "💳 **Subscription**\n\n💰 $100/month\n📅 Valid for 30 days",
        'subscribe_enter_wallet': "📤 Enter your TRC20 wallet address:",
        'subscribe_after_wallet': "✅ Wallet saved!\n\nSend $100 to:\n`{}`",
        'subscribe_confirm': "✅ Confirm Subscription",
        'subscribe_success': "✅ Subscription activated! 🎉",
        'subscribe_failed': "❌ Subscription failed!",
        
        # رفرال
        'referral_text': "🔗 **Referral System**\n\nYour code: `{}`\n\nInvites: {}\n\nEarn 5% of each deposit!",
        'referral_link': "https://t.me/UTYOB_Bot?start=ref_{}",
        'share': "📤 Share",
        
        # راهنما
        'guide_text': "📖 **Guide**\n\n1. Subscribe ($100/month)\n2. Join lottery or buy education\n3. Win prizes!\n\nContact admin for support.",
        
        # زبان
        'language_selector': "🌐 **Select Language:**",
        
        # پیام‌های عمومی
        'invalid_command': "⚠️ Invalid command!",
        'error_message': "⚠️ Error occurred!",
        'invalid_wallet': "❌ Invalid TRC20 address!",
        'tx_hash_invalid': "❌ Invalid TX hash!",
        'tx_hash_received': "✅ TX hash received! Admin will verify.",
        'send_tx_hash': "📤 Send your transaction hash:",
        'no_subscription': "❌ No active subscription!",
        
        # پنل مدیریت
        'admin_panel_title': "⚙️ **Admin Panel**",
        'admin_broadcast': "📢 Broadcast",
        'admin_start_lottery': "🎰 Start Lottery",
        'admin_manual_verify': "✅ Manual Verify",
        'admin_send_course': "📚 Send Course Content",
        'admin_stats': "📊 Stats",
        'admin_add_content': "📝 Add Course Content",
        'admin_verify_approve': "✅ Approve",
        'admin_verify_reject': "❌ Reject",
        'admin_verify_approved': "✅ Transaction approved!",
        'admin_verify_rejected': "❌ Transaction rejected!",
        'user_verify_approved': "✅ Your transaction was approved! 🎉",
        'user_verify_rejected': "❌ Your transaction was rejected!",
        
        # دکمه‌های اضافی
        'share_link': "📤 Share Link",
        'support': "📞 Support",
        'retry': "🔄 Retry",
        'next_lottery': "🎰 Next Lottery",
        'withdraw_prize': "💰 Withdraw Prize",
        'no_winner': "❌ You have no prize!",
        'already_paid': "✅ Prize already paid!",
        'enter_withdraw_wallet': "💰 Enter your TRC20 wallet:",
        'withdraw_success': "✅ Withdrawal registered!",
    },
    'fa': {
        'name': 'فارسی',
        'emoji': '🇮🇷',
        'welcome': "🎮 **به ربات UTYOB خوش آمدید!**\n\nیکی از گزینه‌ها را انتخاب کنید:",
        'main_menu': "🎯 **ربات UTYOB**\n\nانتخاب کنید:",
        'lottery': "🎰 قرعه‌کشی",
        'education': "📚 آموزش ترید",
        'referral': "🔗 رفرال",
        'guide': "📖 راهنما",
        'language': "🌐 زبان",
        'admin_panel': "⚙️ مدیریت",
        'back': "🔙 بازگشت",
        'main_menu_btn': "🏠 منوی اصلی",
        
        'lottery_title': "🎰 **قرعه‌کشی**\n\n💰 هزینه شرکت: ۱۰۰ دلار\n🏆 جایزه: تا ۱۰,۰۰۰ دلار",
        'join_lottery': "🎯 شرکت در قرعه‌کشی",
        'lottery_enter_wallet': "📤 آدرس کیف پول TRC20 خود را وارد کنید:",
        'lottery_after_wallet': "✅ آدرس ذخیره شد!\n\nمبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:\n`{}`\n\nپس از واریز، دکمه تایید را بزنید.",
        'lottery_confirm': "✅ تایید پرداخت",
        'lottery_cancel': "❌ انصراف",
        'lottery_verifying': "⏳ در حال بررسی پرداخت...",
        'lottery_success': "✅ پرداخت تایید شد! 🎉\nهش: `{}`\n\nموفق باشید!",
        'lottery_failed': "❌ پرداخت تایید نشد!\nدلیل: {}\n\nهش تراکنش را برای تایید دستی ارسال کنید:",
        'lottery_no_subscription': "❌ اشتراک فعال ندارید!\n\nابتدا اشتراک بخرید.",
        
        'education_title': "📚 **آموزش ترید و سیگنال**\n\nترید حرفه‌ای را یاد بگیر!",
        'education_buy': "💰 خرید دوره (۱۰۰ دلار)",
        'education_enter_wallet': "📤 آدرس کیف پول TRC20 خود را وارد کنید:",
        'education_after_wallet': "✅ آدرس ذخیره شد!\n\nمبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:\n`{}`\n\nپس از واریز، دکمه تایید را بزنید.",
        'education_confirm': "✅ تایید پرداخت",
        'education_verifying': "⏳ در حال بررسی پرداخت...",
        'education_success': "✅ پرداخت تایید شد! 🎉\nهش: `{}`\n\nدسترسی به دوره فعال شد!",
        'education_failed': "❌ پرداخت تایید نشد!\nدلیل: {}\n\nهش تراکنش را ارسال کنید:",
        'education_already_purchased': "✅ شما قبلاً دوره را خریداری کرده‌اید!",
        
        'subscribe': "🔄 اشتراک",
        'subscribe_title': "💳 **اشتراک**\n\n💰 ۱۰۰ دلار در ماه\n📅 اعتبار: ۳۰ روز",
        'subscribe_enter_wallet': "📤 آدرس کیف پول TRC20 خود را وارد کنید:",
        'subscribe_after_wallet': "✅ آدرس ذخیره شد!\n\nمبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:\n`{}`",
        'subscribe_confirm': "✅ تایید اشتراک",
        'subscribe_success': "✅ اشتراک فعال شد! 🎉",
        'subscribe_failed': "❌ اشتراک فعال نشد!",
        
        'referral_text': "🔗 **سیستم رفرال**\n\nکد شما: `{}`\n\nتعداد دعوت‌ها: {}\n\nاز هر واریز ۵٪ پاداش بگیرید!",
        'referral_link': "https://t.me/UTYOB_Bot?start=ref_{}",
        'share': "📤 اشتراک‌گذاری",
        
        'guide_text': "📖 **راهنما**\n\n۱. اشتراک بگیرید (۱۰۰ دلار در ماه)\n۲. در قرعه‌کشی شرکت کنید یا دوره بخرید\n۳. برنده شوید!\n\nبرای پشتیبانی با مدیریت تماس بگیرید.",
        
        'language_selector': "🌐 **انتخاب زبان:**",
        
        'invalid_command': "⚠️ دستور نامعتبر!",
        'error_message': "⚠️ خطا رخ داد!",
        'invalid_wallet': "❌ آدرس TRC20 نامعتبر!",
        'tx_hash_invalid': "❌ هش تراکنش نامعتبر!",
        'tx_hash_received': "✅ هش تراکنش دریافت شد! مدیر بررسی می‌کند.",
        'send_tx_hash': "📤 هش تراکنش خود را ارسال کنید:",
        'no_subscription': "❌ اشتراک فعال ندارید!",
        
        'admin_panel_title': "⚙️ **پنل مدیریت**",
        'admin_broadcast': "📢 ارسال همگانی",
        'admin_start_lottery': "🎰 شروع قرعه‌کشی",
        'admin_manual_verify': "✅ تایید دستی",
        'admin_send_course': "📚 ارسال محتوای دوره",
        'admin_stats': "📊 آمار",
        'admin_add_content': "📝 افزودن محتوای دوره",
        'admin_verify_approve': "✅ تایید",
        'admin_verify_reject': "❌ رد",
        'admin_verify_approved': "✅ تراکنش تایید شد!",
        'admin_verify_rejected': "❌ تراکنش رد شد!",
        'user_verify_approved': "✅ تراکنش شما تایید شد! 🎉",
        'user_verify_rejected': "❌ تراکنش شما رد شد!",
        
        'share_link': "📤 اشتراک‌گذاری",
        'support': "📞 پشتیبانی",
        'retry': "🔄 تلاش مجدد",
        'next_lottery': "🎰 قرعه‌کشی بعدی",
        'withdraw_prize': "💰 برداشت جایزه",
        'no_winner': "❌ جایزه‌ای ندارید!",
        'already_paid': "✅ جایزه قبلاً پرداخت شده!",
        'enter_withdraw_wallet': "💰 آدرس کیف پول TRC20 خود را وارد کنید:",
        'withdraw_success': "✅ برداشت ثبت شد!",
    },
    'tr': {
        'name': 'Türkçe',
        'emoji': '🇹🇷',
        'welcome': "🎮 **UTYOB Bot'a Hoş Geldiniz!**\n\nBir seçenek seçin:",
        'main_menu': "🎯 **UTYOB Bot**\n\nSeçenekler:",
        'lottery': "🎰 Piyango",
        'education': "📚 Eğitim",
        'referral': "🔗 Referans",
        'guide': "📖 Rehber",
        'language': "🌐 Dil",
        'admin_panel': "⚙️ Yönetim",
        'back': "🔙 Geri",
        'main_menu_btn': "🏠 Ana Menü",
        
        'lottery_title': "🎰 **Piyango**\n\n💰 Giriş: 100$\n🏆 Ödül: 10.000$'a kadar",
        'join_lottery': "🎯 Piyangoya Katıl",
        'lottery_enter_wallet': "📤 TRC20 cüzdan adresinizi girin:",
        'lottery_after_wallet': "✅ Adres kaydedildi!\n\n100$'yi şu adrese gönderin:\n`{}`\n\nGönderdikten sonra Onayla'ya tıklayın.",
        'lottery_confirm': "✅ Ödemeyi Onayla",
        'lottery_cancel': "❌ İptal",
        'lottery_verifying': "⏳ Ödeme kontrol ediliyor...",
        'lottery_success': "✅ Ödeme onaylandı! 🎉\nTx: `{}`\n\nİyi şanslar!",
        'lottery_failed': "❌ Ödeme onaylanamadı!\nSebep: {}\n\nManuel doğrulama için TX hash gönderin:",
        'lottery_no_subscription': "❌ Aktif abonelik yok!\n\nÖnce abone olun.",
        
        'education_title': "📚 **Trading Eğitimi**\n\nProfesyonel trading öğrenin!",
        'education_buy': "💰 Kurs Satın Al (100$)",
        'education_enter_wallet': "📤 TRC20 cüzdan adresinizi girin:",
        'education_after_wallet': "✅ Adres kaydedildi!\n\n100$'yi şu adrese gönderin:\n`{}`\n\nGönderdikten sonra Onayla'ya tıklayın.",
        'education_confirm': "✅ Ödemeyi Onayla",
        'education_verifying': "⏳ Ödeme kontrol ediliyor...",
        'education_success': "✅ Ödeme onaylandı! 🎉\nTx: `{}`\n\nErişim aktif!",
        'education_failed': "❌ Ödeme onaylanamadı!\nSebep: {}\n\nTX hash gönderin:",
        'education_already_purchased': "✅ Zaten kursa erişiminiz var!",
        
        'subscribe': "🔄 Abone Ol",
        'subscribe_title': "💳 **Abonelik**\n\n💰 100$/ay\n📅 30 gün geçerli",
        'subscribe_enter_wallet': "📤 TRC20 cüzdan adresinizi girin:",
        'subscribe_after_wallet': "✅ Adres kaydedildi!\n\n100$'yi şu adrese gönderin:\n`{}`",
        'subscribe_confirm': "✅ Aboneliği Onayla",
        'subscribe_success': "✅ Abonelik aktif! 🎉",
        'subscribe_failed': "❌ Abonelik başarısız!",
        
        'referral_text': "🔗 **Referans Sistemi**\n\nKodunuz: `{}`\n\nDavetler: {}\n\nHer yatırımdan %5 kazanın!",
        'referral_link': "https://t.me/UTYOB_Bot?start=ref_{}",
        'share': "📤 Paylaş",
        
        'guide_text': "📖 **Rehber**\n\n1. Abone olun (100$/ay)\n2. Piyangoya katılın veya kurs alın\n3. Ödül kazanın!\n\nDestek için yöneticiyle iletişime geçin.",
        
        'language_selector': "🌐 **Dil Seçin:**",
        
        'invalid_command': "⚠️ Geçersiz komut!",
        'error_message': "⚠️ Hata oluştu!",
        'invalid_wallet': "❌ Geçersiz TRC20 adresi!",
        'tx_hash_invalid': "❌ Geçersiz TX hash!",
        'tx_hash_received': "✅ TX hash alındı! Yönetici kontrol edecek.",
        'send_tx_hash': "📤 İşlem hash'inizi gönderin:",
        'no_subscription': "❌ Aktif abonelik yok!",
        
        'admin_panel_title': "⚙️ **Yönetim Paneli**",
        'admin_broadcast': "📢 Toplu Mesaj",
        'admin_start_lottery': "🎰 Piyangoyu Başlat",
        'admin_manual_verify': "✅ Manuel Doğrulama",
        'admin_send_course': "📚 Kurs İçeriği Gönder",
        'admin_stats': "📊 İstatistikler",
        'admin_add_content': "📝 Kurs İçeriği Ekle",
        'admin_verify_approve': "✅ Onayla",
        'admin_verify_reject': "❌ Reddet",
        'admin_verify_approved': "✅ İşlem onaylandı!",
        'admin_verify_rejected': "❌ İşlem reddedildi!",
        'user_verify_approved': "✅ İşleminiz onaylandı! 🎉",
        'user_verify_rejected': "❌ İşleminiz reddedildi!",
        
        'share_link': "📤 Paylaş",
        'support': "📞 Destek",
        'retry': "🔄 Tekrar Dene",
        'next_lottery': "🎰 Sonraki Piyango",
        'withdraw_prize': "💰 Ödülü Çek",
        'no_winner': "❌ Ödülünüz yok!",
        'already_paid': "✅ Ödül zaten ödendi!",
        'enter_withdraw_wallet': "💰 TRC20 cüzdan adresinizi girin:",
        'withdraw_success': "✅ Çekim kaydedildi!",
    }
}

def get_text(user_id, key, *args, **kwargs):
    """دریافت متن به زبان کاربر"""
    lang = 'en'
    user = db.execute(user_id, "SELECT language FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if user and user['language'] in LANGUAGES:
        lang = user['language']
    
    text = LANGUAGES[lang].get(key, LANGUAGES['en'].get(key, key))
    
    if args:
        try:
            return text.format(*args)
        except:
            return text
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

# ============================================================
# سیستم تایید پرداخت
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.session = None
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=100)
            )
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
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if self._validate_transaction(data, from_address, to_address, amount):
                            return True, tx_id, "Verified"
            except Exception as e:
                logger.error(f"API error: {e}")
        return False, None, "Transaction not found"
        
    async def _search_transactions(self, session, from_address, to_address, amount):
        for api in self.apis:
            try:
                url = f"https://api.trongrid.io/v1/accounts/{from_address}/transactions"
                params = {"limit": 50, "order_by": "block_timestamp,desc"}
                headers = {"TRON-PRO-API-KEY": api}
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for tx in data.get('data', []):
                            if self._validate_transaction(tx, from_address, to_address, amount):
                                return True, tx.get('txID'), "Verified"
            except Exception as e:
                logger.error(f"API error: {e}")
        return False, None, "No matching transaction found"
        
    def _validate_transaction(self, tx_data, from_address, to_address, amount):
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
# سیستم مدیریت کاربران
# ============================================================
class UserManager:
    @staticmethod
    def register_user(user_id, username=None, first_name=None, last_name=None):
        try:
            cursor = db.execute(user_id, "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                return False
                
            referral_code = UserManager._generate_referral_code(user_id)
            db.execute(user_id,
                """INSERT INTO users 
                   (user_id, username, first_name, last_name, referral_code, language) 
                   VALUES (?, ?, ?, ?, ?, 'en')""",
                (user_id, username, first_name, last_name, referral_code)
            )
            return True
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
            
    @staticmethod
    def _generate_referral_code(user_id):
        base = f"UTYOB_{user_id}_{time.time()}_{random.randint(1000, 9999)}"
        return hashlib.sha256(base.encode()).hexdigest()[:10].upper()
        
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
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
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
            for row in results:
                total += row['count']
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
            return False, "Lottery is already running"
            
        eligible = self._get_eligible_users()
        if not eligible or len(eligible) < winners_count:
            return False, "Not enough eligible users"
            
        winners = self._select_winners(eligible, winners_count)
        if not winners:
            return False, "Error selecting winners"
            
        lottery_id = self._save_lottery(winners_count, prize_per_winner, winners)
        self._save_winners(lottery_id, winners, prize_per_winner)
        
        return True, {'lottery_id': lottery_id, 'winners': winners, 'prize_per_winner': prize_per_winner}
        
    def _get_eligible_users(self):
        results = db.execute_global(
            "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
        )
        return [row['user_id'] for row in results]
        
    def _select_winners(self, eligible, count):
        return random.sample(eligible, min(count, len(eligible)))
        
    def _save_lottery(self, winners_count, prize_per_winner, winners):
        total_prize = winners_count * prize_per_winner
        cursor = db.execute(0,
            "INSERT INTO lotteries (winners_count, prize_per_winner, total_prize, status, started_at) VALUES (?, ?, ?, 'running', CURRENT_TIMESTAMP)",
            (winners_count, prize_per_winner, total_prize)
        )
        return cursor.lastrowid
        
    def _save_winners(self, lottery_id, winners, prize_amount):
        for user_id in winners:
            user = user_manager.get_user(user_id)
            wallet = user['wallet_address'] if user else None
            db.execute(user_id,
                "INSERT INTO winners (lottery_id, user_id, prize_amount, wallet_address, paid_status) VALUES (?, ?, ?, ?, 0)",
                (lottery_id, user_id, prize_amount, wallet)
            )

lottery_system = LotterySystem()

# ============================================================
# سیستم مدیریت محتوای آموزشی
# ============================================================
class CourseManager:
    @staticmethod
    def add_content(content_type, title, content, file_id=None, file_name=None, file_size=None):
        cursor = db.execute(0,
            """INSERT INTO course_content 
               (content_type, title, content, file_id, file_name, file_size) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (content_type, title, content, file_id, file_name, file_size)
        )
        return cursor.lastrowid
        
    @staticmethod
    def get_all_content():
        results = db.execute_global("SELECT * FROM course_content ORDER BY created_at DESC")
        return results
        
    @staticmethod
    def get_content(content_id):
        cursor = db.execute(0, "SELECT * FROM course_content WHERE id = ?", (content_id,))
        return cursor.fetchone()
        
    @staticmethod
    def get_content_count():
        results = db.execute_global("SELECT COUNT(*) as count FROM course_content")
        total = 0
        for row in results:
            total += row['count']
        return total
        
    @staticmethod
    def has_user_received(user_id, content_id):
        cursor = db.execute(user_id,
            "SELECT * FROM content_sent WHERE user_id = ? AND content_id = ?",
            (user_id, content_id)
        )
        return cursor.fetchone() is not None
        
    @staticmethod
    def mark_as_sent(user_id, content_id):
        db.execute(user_id,
            "INSERT OR IGNORE INTO content_sent (user_id, content_id) VALUES (?, ?)",
            (user_id, content_id)
        )
        
    @staticmethod
    def send_content_to_user(bot, user_id, content):
        """ارسال محتوای آموزشی به کاربر"""
        try:
            if content['content_type'] == 'text':
                bot.send_message(
                    chat_id=user_id,
                    text=f"📚 **{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif content['content_type'] == 'photo':
                bot.send_photo(
                    chat_id=user_id,
                    photo=content['file_id'],
                    caption=f"📚 **{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif content['content_type'] == 'video':
                bot.send_video(
                    chat_id=user_id,
                    video=content['file_id'],
                    caption=f"📚 **{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif content['content_type'] == 'document':
                bot.send_document(
                    chat_id=user_id,
                    document=content['file_id'],
                    caption=f"📚 **{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                bot.send_message(
                    chat_id=user_id,
                    text=f"📚 **{content['title']}**\n\n{content['content']}",
                    parse_mode=ParseMode.MARKDOWN
                )
            return True
        except Exception as e:
            logger.error(f"Error sending content to {user_id}: {e}")
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
        
        # دستورات عمومی
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        
        # کالبک‌های منو
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.education_callback, pattern="^education$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language$"))
        
        # کالبک‌های اشتراک
        app.add_handler(CallbackQueryHandler(self.subscribe_callback, pattern="^subscribe$"))
        
        # کالبک‌های قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.lottery_join_callback, pattern="^lottery_join$"))
        app.add_handler(CallbackQueryHandler(self.lottery_confirm_callback, pattern="^lottery_confirm$"))
        
        # کالبک‌های آموزش
        app.add_handler(CallbackQueryHandler(self.education_buy_callback, pattern="^education_buy$"))
        app.add_handler(CallbackQueryHandler(self.education_confirm_callback, pattern="^education_confirm$"))
        
        # کالبک‌های پنل مدیریت
        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_start_lottery_callback, pattern="^admin_start_lottery$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_send_course_callback, pattern="^admin_send_course$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_content_callback, pattern="^admin_add_content$"))
        app.add_handler(CallbackQueryHandler(self.admin_stats_callback, pattern="^admin_stats$"))
        
        # تایید/رد تراکنش توسط ادمین
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))
        
        # تغییر زبان
        app.add_handler(CallbackQueryHandler(self.set_language_callback, pattern="^set_lang_"))
        
        # مدیریت پیام‌ها
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.VIDEO, self.handle_video))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
        # مدیریت خطاها
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
            try:
                base58.b58decode(address)
                return True
            except:
                return False
        except:
            return False
            
    def _validate_tx_hash(self, tx_hash):
        try:
            if len(tx_hash) != 64:
                return False
            if not all(c in '0123456789abcdefABCDEF' for c in tx_hash):
                return False
            return True
        except:
            return False
            
    async def _verify_payment(self, user_id, from_address, amount, tx_hash=None):
        """تایید پرداخت با TRONGRID"""
        success, tx_id, message = await payment_verifier.verify_transaction(
            from_address, DESTINATION_WALLET, amount, tx_hash
        )
        return success, tx_id, message
        
    async def _send_course_content_to_user(self, user_id):
        """ارسال تمام محتوای دوره به کاربر (برای کاربرانی که اشتراک خریدند)"""
        contents = course_manager.get_all_content()
        sent_count = 0
        
        for content in contents:
            if not course_manager.has_user_received(user_id, content['id']):
                if course_manager.send_content_to_user(self.application.bot, user_id, content):
                    course_manager.mark_as_sent(user_id, content['id'])
                    sent_count += 1
                    await asyncio.sleep(0.3)  # جلوگیری از ریت‌لیمیت
        
        return sent_count

    # ============================================================
    # دستورات عمومی
    # ============================================================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        # ثبت کاربر
        user_manager.register_user(user.id, user.username, user.first_name, user.last_name)
        
        # بررسی رفرال
        if context.args and context.args[0].startswith('ref_'):
            ref_code = context.args[0][4:]
            cursor = db.execute(0, "SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
            ref_user = cursor.fetchone()
            if ref_user and ref_user['user_id'] != user.id:
                user_manager.update_user(user.id, referred_by=ref_user['user_id'])
        
        lang = 'en'
        user_data = user_manager.get_user(user.id)
        if user_data and user_data['language']:
            lang = user_data['language']
        
        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['lottery'], callback_data="lottery")],
            [InlineKeyboardButton(LANGUAGES[lang]['education'], callback_data="education")],
            [InlineKeyboardButton(LANGUAGES[lang]['referral'], callback_data="referral")],
            [InlineKeyboardButton(LANGUAGES[lang]['guide'], callback_data="guide")],
            [InlineKeyboardButton(LANGUAGES[lang]['language'], callback_data="language")]
        ]
        
        if user.id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton(LANGUAGES[lang]['admin_panel'], callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LANGUAGES[lang]['welcome'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LANGUAGES[lang]['guide_text'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های منوی اصلی
    # ============================================================
    
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['lottery'], callback_data="lottery")],
            [InlineKeyboardButton(LANGUAGES[lang]['education'], callback_data="education")],
            [InlineKeyboardButton(LANGUAGES[lang]['referral'], callback_data="referral")],
            [InlineKeyboardButton(LANGUAGES[lang]['guide'], callback_data="guide")],
            [InlineKeyboardButton(LANGUAGES[lang]['language'], callback_data="language")]
        ]
        
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton(LANGUAGES[lang]['admin_panel'], callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LANGUAGES[lang]['main_menu'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ============================================================
    # کالبک‌های قرعه‌کشی
    # ============================================================
    
    async def lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        user = user_manager.get_user(user_id)
        
        if not user or not user['has_subscription']:
            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['subscribe'], callback_data="subscribe")],
                [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                LANGUAGES[lang]['lottery_no_subscription'],
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['join_lottery'], callback_data="lottery_join")],
            [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LANGUAGES[lang]['lottery_title'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def lottery_join_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        context.user_data['action'] = 'lottery'
        context.user_data['waiting_for_wallet'] = True
        
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['lottery_cancel'], callback_data="lottery")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LANGUAGES[lang]['lottery_enter_wallet'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def lottery_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        user = user_manager.get_user(user_id)
        
        if not user or not user['wallet_address']:
            await query.edit_message_text(
                LANGUAGES[lang]['lottery_enter_wallet'],
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            LANGUAGES[lang]['lottery_verifying'],
            parse_mode=ParseMode.MARKDOWN
        )
        
        success, tx_id, message = await self._verify_payment(
            user_id, user['wallet_address'], PAYMENT_AMOUNT
        )
        
        if success:
            # ثبت تراکنش
            db.execute(user_id,
                """INSERT INTO transactions 
                   (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) 
                   VALUES (?, ?, ?, ?, ?, 'lottery', 'verified', CURRENT_TIMESTAMP)""",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
            )
            
            # افزایش تعداد شرکت‌ها
            user_manager.update_user(user_id, total_participations=user['total_participations'] + 1)
            
            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['next_lottery'], callback_data="lottery")],
                [InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LANGUAGES[lang]['lottery_success'].format(tx_id),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # پرداخت ناموفق - درخواست هش
            context.user_data['action'] = 'lottery'
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            context.user_data['tx_type'] = 'lottery'
            
            keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="lottery")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LANGUAGES[lang]['lottery_failed'].format(message),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ============================================================
    # کالبک‌های آموزش
    # ============================================================
    
    async def education_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        user = user_manager.get_user(user_id)
        
        # بررسی اینکه کاربر قبلاً دوره رو خریده
        cursor = db.execute(user_id,
            "SELECT * FROM transactions WHERE user_id = ? AND tx_type = 'education' AND status = 'verified'",
            (user_id,)
        )
        has_purchased = cursor.fetchone()
        
        if has_purchased:
            keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LANGUAGES[lang]['education_already_purchased'],
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['education_buy'], callback_data="education_buy")],
            [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LANGUAGES[lang]['education_title'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def education_buy_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        context.user_data['action'] = 'education'
        context.user_data['waiting_for_wallet'] = True
        
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="education")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LANGUAGES[lang]['education_enter_wallet'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def education_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        user = user_manager.get_user(user_id)
        
        if not user or not user['wallet_address']:
            await query.edit_message_text(
                LANGUAGES[lang]['education_enter_wallet'],
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            LANGUAGES[lang]['education_verifying'],
            parse_mode=ParseMode.MARKDOWN
        )
        
        success, tx_id, message = await self._verify_payment(
            user_id, user['wallet_address'], PAYMENT_AMOUNT
        )
        
        if success:
            # ثبت تراکنش
            db.execute(user_id,
                """INSERT INTO transactions 
                   (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) 
                   VALUES (?, ?, ?, ?, ?, 'education', 'verified', CURRENT_TIMESTAMP)""",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
            )
            
            # ارسال محتوای دوره
            sent_count = await self._send_course_content_to_user(user_id)
            
            keyboard = [
                [InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LANGUAGES[lang]['education_success'].format(tx_id) + f"\n\n📚 تعداد محتواهای ارسال‌شده: {sent_count}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        admin_id,
                        f"✅ خرید دوره جدید!\n👤 کاربر: {user_id}\n💰 مبلغ: ${PAYMENT_AMOUNT}\n🔗 هش: {tx_id}"
                    )
                except:
                    pass
        else:
            # پرداخت ناموفق
            context.user_data['action'] = 'education'
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['tx_from_address'] = user['wallet_address']
            context.user_data['tx_type'] = 'education'
            
            keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="education")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LANGUAGES[lang]['education_failed'].format(message),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ============================================================
    # کالبک‌های اشتراک
    # ============================================================
    
    async def subscribe_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        user = user_manager.get_user(user_id)
        
        if user and user['has_subscription']:
            # ارسال محتوای دوره به کاربر
            sent_count = await self._send_course_content_to_user(user_id)
            
            keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ شما اشتراک فعال دارید!\n\n📚 {sent_count} محتوای آموزشی ارسال شد.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        context.user_data['action'] = 'subscribe'
        context.user_data['waiting_for_wallet'] = True
        
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LANGUAGES[lang]['subscribe_enter_wallet'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ============================================================
    # کالبک‌های رفرال، راهنما و زبان
    # ============================================================
    
    async def referral_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        user = user_manager.get_user(user_id)
        if not user:
            return
            
        ref_count = user_manager.get_referral_count(user_id)
        ref_code = user['referral_code']
        ref_link = f"https://t.me/{self.application.bot.username}?start=ref_{ref_code}"
        
        keyboard = [
            [InlineKeyboardButton(LANGUAGES[lang]['share'], url=f"https://t.me/share/url?url={ref_link}")],
            [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LANGUAGES[lang]['referral_text'].format(ref_code, ref_count),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LANGUAGES[lang]['guide_text'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_lang_fa")],
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="set_lang_tr")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🌐 Select Language:\n\n🇬🇧 English\n🇮🇷 فارسی\n🇹🇷 Türkçe",
            reply_markup=reply_markup
        )
    
    async def set_language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang_code = query.data.replace('set_lang_', '')
        
        if lang_code in LANGUAGES:
            user_manager.update_user(user_id, language=lang_code)
            
            keyboard = [[InlineKeyboardButton(LANGUAGES[lang_code]['main_menu_btn'], callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Language changed to {LANGUAGES[lang_code]['name']}!",
                reply_markup=reply_markup
            )
    
    # ============================================================
    # کالبک‌های پنل مدیریت
    # ============================================================
    
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ Access Denied!")
            return
        
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        # آمار
        user_count = len(db.execute_global("SELECT user_id FROM users"))
        active_users = len(db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"))
        pending_count = len(db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending'"))
        content_count = course_manager.get_content_count()
        
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 Start Lottery", callback_data="admin_start_lottery")],
            [InlineKeyboardButton(f"✅ Manual Verify ({pending_count})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📚 Send Course Content", callback_data="admin_send_course")],
            [InlineKeyboardButton("📝 Add Course Content", callback_data="admin_add_content")],
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚙️ **Admin Panel**\n\n"
            f"👥 Users: {user_count}\n"
            f"✅ Active: {active_users}\n"
            f"⏳ Pending: {pending_count}\n"
            f"📚 Content: {content_count}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
            
        context.user_data['admin_action'] = 'broadcast'
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📢 **Send Broadcast Message**\n\nSend the message you want to broadcast to all users:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_start_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
            
        if lottery_system.is_running:
            await query.edit_message_text("⚠️ Lottery is already running!")
            return
            
        context.user_data['admin_action'] = 'start_lottery'
        context.user_data['lottery_step'] = 1
        
        keyboard = [
            [InlineKeyboardButton("🔙 Cancel", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎰 **Start New Lottery**\n\nEnter number of winners (1-20):",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
            
        pending = db.execute_global(
            "SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC LIMIT 10"
        )
        
        if not pending:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ No pending verifications!", reply_markup=reply_markup)
            return
        
        text = "✅ **Manual Verification**\n\n"
        keyboard = []
        
        for p in pending[:5]:
            text += f"👤 User: {p['user_id']}\n"
            text += f"💰 Amount: ${p['amount']}\n"
            text += f"📤 From: `{p['from_address']}`\n"
            text += f"🔗 TX: `{p['tx_hash']}`\n"
            text += f"📂 Type: {p['tx_type']}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve #{p['id']}", callback_data=f"admin_verify_approve_{p['id']}"),
                InlineKeyboardButton(f"❌ Reject #{p['id']}", callback_data=f"admin_verify_reject_{p['id']}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_send_course_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
            
        context.user_data['admin_action'] = 'send_course'
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📚 **Send Course Content**\n\n"
            "Send the USER ID of the person you want to send the course to:\n\n"
            "Example: `123456789`\n\n"
            "Or send `ALL` to send to all users.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_add_content_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
            
        context.user_data['admin_action'] = 'add_content'
        context.user_data['content_step'] = 1
        
        keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📝 **Add Course Content**\n\n"
            "Step 1/3: Enter the **TITLE** of the content:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
            
        user_count = len(db.execute_global("SELECT user_id FROM users"))
        active_users = len(db.execute_global("SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"))
        
        tx_stats = db.execute_global(
            "SELECT tx_type, status, COUNT(*) as count FROM transactions GROUP BY tx_type, status"
        )
        tx_text = ""
        for row in tx_stats:
            tx_text += f"• {row['tx_type']} - {row['status']}: {row['count']}\n"
        
        content_count = course_manager.get_content_count()
        
        lottery_count = len(db.execute_global("SELECT id FROM lotteries"))
        winner_count = len(db.execute_global("SELECT id FROM winners WHERE paid_status = 0"))
        
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **Statistics**\n\n"
            f"👥 Users: {user_count}\n"
            f"✅ Active: {active_users}\n"
            f"📚 Content: {content_count}\n"
            f"🎰 Lotteries: {lottery_count}\n"
            f"🏆 Pending Winners: {winner_count}\n\n"
            f"💳 **Transactions:**\n{tx_text}",
            reply_markup=reply_markup,
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
            await query.edit_message_text("❌ Request not found or already processed.")
            return
        
        user_id = pending['user_id']
        
        # فعال‌سازی اشتراک یا دسترسی به دوره
        if pending['tx_type'] == 'subscribe':
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            db.execute(user_id,
                "UPDATE users SET has_subscription = 1, subscription_end = ? WHERE user_id = ?",
                (end_date, user_id)
            )
        elif pending['tx_type'] == 'lottery':
            # ثبت شرکت در قرعه‌کشی
            user = user_manager.get_user(user_id)
            if user:
                user_manager.update_user(user_id, total_participations=user['total_participations'] + 1)
        
        # ثبت تراکنش
        db.execute(user_id,
            """INSERT INTO transactions 
               (user_id, from_address, to_address, amount, tx_id, tx_type, status, verified_at) 
               VALUES (?, ?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)""",
            (user_id, pending['from_address'], pending['to_address'], pending['amount'], pending['tx_hash'], pending['tx_type'])
        )
        
        # به‌روزرسانی وضعیت
        db.execute(0,
            "UPDATE pending_verifications SET status = 'approved' WHERE id = ?",
            (pending_id,)
        )
        
        # اطلاع به کاربر
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        # ارسال محتوای دوره اگر اشتراک فعال شده
        if pending['tx_type'] == 'subscribe':
            await self._send_course_content_to_user(user_id)
        
        try:
            await self.application.bot.send_message(
                user_id,
                LANGUAGES[lang]['user_verify_approved'],
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        await query.edit_message_text(
            f"✅ Transaction approved!\n👤 User: {user_id}\n📂 Type: {pending['tx_type']}",
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
            await query.edit_message_text("❌ Request not found or already processed.")
            return
        
        user_id = pending['user_id']
        
        db.execute(0,
            "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?",
            (pending_id,)
        )
        
        # اطلاع به کاربر
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        try:
            await self.application.bot.send_message(
                user_id,
                LANGUAGES[lang]['user_verify_rejected'],
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        await query.edit_message_text(
            f"❌ Transaction rejected!\n👤 User: {user_id}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ============================================================
    # مدیریت پیام‌ها
    # ============================================================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
        
        # ثبت کاربر
        user_manager.register_user(user_id, update.effective_user.username, update.effective_user.first_name, update.effective_user.last_name)
        
        # ===== اقدامات ادمین =====
        admin_action = context.user_data.get('admin_action')
        
        if admin_action == 'broadcast':
            await self._handle_broadcast(update, text, context)
            return
            
        elif admin_action == 'start_lottery':
            await self._handle_lottery_steps(update, text, context)
            return
            
        elif admin_action == 'send_course':
            await self._handle_send_course(update, text, context)
            return
            
        elif admin_action == 'add_content':
            await self._handle_add_content(update, text, context)
            return
        
        # ===== دریافت هش تراکنش =====
        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            
            if not self._validate_tx_hash(tx_hash):
                await update.message.reply_text(
                    LANGUAGES[lang]['tx_hash_invalid'],
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            from_address = context.user_data.get('tx_from_address')
            tx_type = context.user_data.get('tx_type', 'lottery')
            
            # ذخیره در pending
            db.execute(0,
                """INSERT INTO pending_verifications 
                   (user_id, from_address, to_address, amount, tx_hash, tx_type, status) 
                   VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash, tx_type)
            )
            
            context.user_data['waiting_for_tx_hash'] = False
            context.user_data['tx_from_address'] = None
            context.user_data['tx_type'] = None
            
            await update.message.reply_text(
                LANGUAGES[lang]['tx_hash_received'],
                parse_mode=ParseMode.MARKDOWN
            )
            
            # اطلاع به ادمین‌ها
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Approve", callback_data=f"admin_verify_approve_{db.execute(0, 'SELECT last_insert_rowid()').fetchone()[0]}"),
                            InlineKeyboardButton("❌ Reject", callback_data=f"admin_verify_reject_{db.execute(0, 'SELECT last_insert_rowid()').fetchone()[0]}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await self.application.bot.send_message(
                        admin_id,
                        f"✅ New verification request!\n\n"
                        f"👤 User: {user_id}\n"
                        f"💰 Amount: ${PAYMENT_AMOUNT}\n"
                        f"📤 From: {from_address}\n"
                        f"📂 Type: {tx_type}\n"
                        f"🔗 TX: `{tx_hash}`",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            return
        
        # ===== دریافت آدرس کیف پول =====
        if context.user_data.get('waiting_for_wallet'):
            wallet_address = text.strip()
            
            if not self._validate_wallet(wallet_address):
                await update.message.reply_text(
                    LANGUAGES[lang]['invalid_wallet'],
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            context.user_data['waiting_for_wallet'] = False
            
            action = context.user_data.get('action', 'lottery')
            context.user_data['action'] = None
            
            # انتخاب دکمه تایید بر اساس نوع
            confirm_text = ""
            callback = ""
            back_callback = ""
            
            if action == 'lottery':
                confirm_text = LANGUAGES[lang]['lottery_confirm']
                callback = "lottery_confirm"
                back_callback = "lottery"
            elif action == 'education':
                confirm_text = LANGUAGES[lang]['education_confirm']
                callback = "education_confirm"
                back_callback = "education"
            elif action == 'subscribe':
                confirm_text = LANGUAGES[lang]['subscribe_confirm']
                callback = "subscribe_confirm"
                back_callback = "main_menu"
            
            keyboard = [
                [InlineKeyboardButton(confirm_text, callback_data=callback)],
                [InlineKeyboardButton(LANGUAGES[lang]['back'], callback_data=back_callback)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text_msg = LANGUAGES[lang]['lottery_after_wallet'].format(DESTINATION_WALLET)
            if action == 'education':
                text_msg = LANGUAGES[lang]['education_after_wallet'].format(DESTINATION_WALLET)
            elif action == 'subscribe':
                text_msg = LANGUAGES[lang]['subscribe_after_wallet'].format(DESTINATION_WALLET)
            
            await update.message.reply_text(
                text_msg,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # ===== پیام معمولی =====
        keyboard = [[InlineKeyboardButton(LANGUAGES[lang]['main_menu_btn'], callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LANGUAGES[lang]['invalid_command'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ============================================================
    # توابع کمکی برای مدیریت پیام‌ها
    # ============================================================
    
    async def _handle_broadcast(self, update, text, context):
        user_id = update.effective_user.id
        
        await update.message.reply_text("⏳ Sending broadcast...")
        
        users = db.execute_global("SELECT user_id FROM users")
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(
                    user['user_id'],
                    text,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                if sent % 30 == 0:
                    await asyncio.sleep(0.5)
            except:
                failed += 1
        
        context.user_data['admin_action'] = None
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Broadcast completed!\n\n"
            f"📤 Sent: {sent}\n"
            f"❌ Failed: {failed}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _handle_lottery_steps(self, update, text, context):
        step = context.user_data.get('lottery_step', 1)
        
        if step == 1:
            try:
                winners_count = int(text)
                if 1 <= winners_count <= 20:
                    context.user_data['lottery_winners'] = winners_count
                    context.user_data['lottery_step'] = 2
                    
                    await update.message.reply_text(
                        f"✅ Winners: {winners_count}\n\n"
                        f"💰 Enter prize amount per winner (minimum $10):"
                    )
                else:
                    await update.message.reply_text("❌ Enter a number between 1 and 20.")
            except:
                await update.message.reply_text("❌ Please enter a valid number.")
                
        elif step == 2:
            try:
                prize = float(text)
                if prize >= 10:
                    winners = context.user_data['lottery_winners']
                    context.user_data['lottery_step'] = None
                    context.user_data['admin_action'] = None
                    
                    success, result = lottery_system.start_lottery(winners, prize)
                    
                    if success:
                        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # اطلاع به برندگان
                        for winner_id in result['winners']:
                            try:
                                w_lang = user_manager.get_user(winner_id)['language'] if user_manager.get_user(winner_id) else 'en'
                                await self.application.bot.send_message(
                                    winner_id,
                                    f"🎉 **Congratulations!**\n\n"
                                    f"You won **${prize}** in lottery #{result['lottery_id']}!\n\n"
                                    f"Click the button below to withdraw your prize.",
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Withdraw Prize", callback_data="withdraw_prize")]]),
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except:
                                pass
                        
                        await update.message.reply_text(
                            f"✅ **Lottery completed!** 🎉\n\n"
                            f"📊 Winners: {len(result['winners'])}\n"
                            f"💰 Prize: ${prize} each\n"
                            f"🏆 Lottery ID: {result['lottery_id']}",
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    else:
                        await update.message.reply_text(f"❌ Error: {result}")
                else:
                    await update.message.reply_text("❌ Prize must be at least $10.")
            except:
                await update.message.reply_text("❌ Please enter a valid number.")
    
    async def _handle_send_course(self, update, text, context):
        user_id = update.effective_user.id
        target = text.strip()
        
        if target.upper() == 'ALL':
            # ارسال به همه کاربران
            users = db.execute_global("SELECT user_id FROM users")
            sent = 0
            
            await update.message.reply_text(f"⏳ Sending course to {len(users)} users...")
            
            for user in users:
                count = await self._send_course_content_to_user(user['user_id'])
                if count > 0:
                    sent += 1
                await asyncio.sleep(0.2)
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Course sent to {sent} users!",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        else:
            try:
                target_id = int(target)
                count = await self._send_course_content_to_user(target_id)
                
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ Course sent to user {target_id}!\n📚 {count} items sent.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await update.message.reply_text("❌ Invalid User ID. Send a number or 'ALL'.")
        
        context.user_data['admin_action'] = None
    
    async def _handle_add_content(self, update, text, context):
        step = context.user_data.get('content_step', 1)
        
        if step == 1:
            context.user_data['content_title'] = text.strip()
            context.user_data['content_step'] = 2
            
            await update.message.reply_text(
                "📝 Step 2/3: Enter the **CONTENT** (text description):"
            )
            
        elif step == 2:
            context.user_data['content_text'] = text.strip()
            context.user_data['content_step'] = 3
            
            await update.message.reply_text(
                "📝 Step 3/3: Send the **FILE** (optional)\n\n"
                "You can send:\n"
                "• 📷 Photo\n"
                "• 🎬 Video\n"
                "• 📄 Document (PDF, etc.)\n"
                "• Or send /skip to add text-only content"
            )
            
        elif step == 3:
            # اگر کاربر /skip زده باشد
            if text.lower() == '/skip':
                title = context.user_data.get('content_title', 'Untitled')
                content = context.user_data.get('content_text', '')
                
                content_id = course_manager.add_content('text', title, content)
                
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                context.user_data['admin_action'] = None
                context.user_data['content_step'] = None
                
                await update.message.reply_text(
                    f"✅ Content added successfully!\n"
                    f"📚 Title: {title}\n"
                    f"🆔 ID: {content_id}",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
    
    # ============================================================
    # مدیریت فایل‌ها (عکس، ویدیو، سند)
    # ============================================================
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'photo')
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'video')
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._handle_media(update, context, 'document')
    
    async def _handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE, media_type):
        user_id = update.effective_user.id
        
        # فقط برای ادمین‌ها (افزودن محتوا)
        if user_id not in ADMIN_IDS:
            return
        
        if context.user_data.get('admin_action') != 'add_content':
            return
        
        step = context.user_data.get('content_step')
        if step != 3:
            return
        
        title = context.user_data.get('content_title', 'Untitled')
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
            content_id = course_manager.add_content(
                media_type, title, content, file_id, file_name, file_size
            )
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            context.user_data['admin_action'] = None
            context.user_data['content_step'] = None
            
            await update.message.reply_text(
                f"✅ Content added successfully!\n"
                f"📚 Title: {title}\n"
                f"📂 Type: {media_type}\n"
                f"🆔 ID: {content_id}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ============================================================
    # مدیریت خطاها
    # ============================================================
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        
        try:
            if update and update.effective_user:
                user_id = update.effective_user.id
                lang = user_manager.get_user(user_id)['language'] if user_manager.get_user(user_id) else 'en'
                
                await self.application.bot.send_message(
                    user_id,
                    LANGUAGES[lang]['error_message'],
                    parse_mode=ParseMode.MARKDOWN
                )
        except:
            pass

# ============================================================
# اجرای ربات
# ============================================================

async def main():
    try:
        bot = UTYOBot()
        
        logger.info("🚀 UTYOB Bot starting...")
        logger.info(f"👥 Admins: {ADMIN_IDS}")
        
        await bot.application.initialize()
        await bot.application.start()
        await bot.application.updater.start_polling()
        
        logger.info("✅ Bot started successfully!")
        
        # بررسی منظم اشتراک‌ها و ارسال خودکار محتوا
        while True:
            try:
                # کاربرانی که اشتراک فعال دارند ولی محتوا دریافت نکرده‌اند
                users = db.execute_global(
                    "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
                )
                
                for user in users:
                    # ارسال محتواهای جدید
                    await bot._send_course_content_to_user(user['user_id'])
                    await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Auto-send error: {e}")
            
            await asyncio.sleep(3600)  # هر ۱ ساعت
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Program stopped")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")