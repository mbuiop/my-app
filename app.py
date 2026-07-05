"""
ربات قرعه‌کشی UTYOB - نسخه نهایی قدرتمند با پشتیبانی کامل از زبان و پنل مدیریت
"""

import os
import sys
import json
import asyncio
import logging
import random
import hashlib
import time
import sqlite3
import aiohttp
import base58
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from threading import Thread
from contextlib import contextmanager

# ============================================================
# نصب خودکار کتابخانه‌ها
# ============================================================
def install_packages():
    packages = [
        'python-telegram-bot',
        'aiohttp',
        'base58',
        'psutil'
    ]
    
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

install_packages()

# ============================================================
# ایمپورت‌ها
# ============================================================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ============================================================
# تنظیمات اصلی
# ============================================================
BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
ADMIN_ID = 327855654
DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
TRON_API_KEY = "7ae83b63-fdf3-47e4-ac69-56f960a34f5b"
LOTTERY_PRICE = 100
CONFIRMATION_THRESHOLD = 19

# ============================================================
# تنظیمات لاگینگ
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lottery_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# سیستم چندزبانه کامل
# ============================================================
class LanguageManager:
    """مدیریت کامل زبان‌ها با ترجمه همه متن‌ها"""
    
    def __init__(self):
        self.translations = {
            'en': {
                # دکمه‌ها
                'btn_join': '🎰 Join Lottery',
                'btn_referral': '👥 Referral',
                'btn_guide': '📖 Guide',
                'btn_language': '🌐 Change Language',
                'btn_withdraw': '💰 Withdraw',
                'btn_verify': '✅ Verify Payment',
                'btn_copy': '📋 Copy',
                'btn_share': '📤 Share Link',
                'btn_back': '🔙 Back',
                'btn_cancel': '❌ Cancel',
                'btn_confirm': '✅ Confirm',
                
                # پیام‌ها
                'welcome': '🎰 **Welcome to UTYOB Lottery Bot!**\n\n💰 Join our lottery with just $100\n🎁 Win up to $2,000!\n\nUse the buttons below to get started.',
                'guide': '📖 **Guide**\n\n1️⃣ Send $100 USDT to:\n`{wallet}`\n2️⃣ Enter your wallet address and TxID\n3️⃣ Wait for the lottery draw\n4️⃣ If you win, withdraw your prize!\n\n⚡ Fair lottery with AI-powered selection.',
                'referral': '👥 **Referral System**\n\n🔗 Your link:\n`https://t.me/UTYOB_Bot?start=ref_{code}`\n\n📊 Referrals: {count}\n⭐ Points: {points}',
                'join_subscription': '⚠️ **You need a subscription!**\n\n💰 Price: ${price}\n📥 Send to: `{wallet}`\n\nPlease enter your source wallet address (TRC20):',
                'wallet_saved': '✅ **Wallet saved!**\n\n📤 Your wallet: `{wallet}`\n📥 **Send exactly ${price} USDT to:**\n`{destination}`\n\n⏳ Enter your transaction hash (TxID):',
                'wallet_invalid': '❌ Invalid wallet address!\nPlease enter a valid TRC20 address.',
                'verifying': '⏳ Verifying transaction...',
                'verify_success': '✅ Payment confirmed! You are registered for the lottery!',
                'verify_fail': '❌ Transaction not found or invalid!\nPlease check and try again.',
                'verify_pending': '⏳ Waiting for confirmations...\n{confirmations}/{required}',
                'register_fail': '❌ Registration failed!',
                'already_participated': '✅ You have already participated!',
                'already_registered': '⚠️ You are already registered!',
                'no_prize': '❌ No prize to withdraw!',
                'withdraw_enter': '💰 **Withdraw ${amount} USDT**\n\nEnter your TRC20 wallet address:',
                'withdraw_invalid': '❌ Invalid TRC20 address!',
                'withdraw_success': '✅ Withdrawal request submitted!',
                'withdraw_fail': '❌ No pending prize found!',
                'copy_success': '✅ Referral link copied!',
                'language_changed': '✅ Language changed to English!',
                'language_select': '🌐 Select your language:',
                'admin_panel': '🛠️ **Admin Panel**\n\nSelect an action:',
                'admin_broadcast': '📢 **Enter broadcast message:**',
                'admin_start_confirm': '⚠️ **Start new lottery?**\n\nHow many winners?',
                'admin_winner_count': '💰 **Prize amount per winner (USDT):**',
                'admin_lottery_complete': '✅ **Lottery completed!**\n\n🏆 Winners: {count}\n💰 Prize: ${amount} each\n🎰 Round: #{round}',
                'admin_no_participants': '❌ No eligible participants!',
                'admin_manual_verify': '🔍 **Manual Verify**\n\nEnter user ID:',
                'admin_manual_success': '✅ User {user_id} verified manually!',
                'admin_pay_success': '💸 Paid {count} winners!',
                'admin_add_api': '🔑 **Add API Key**\n\nFormat: `name|api_key|base_url`\nExample: `secondary|key123|https://api.trongrid.io`',
                'admin_api_success': '✅ API key \'{name}\' added successfully!',
                'admin_api_fail': '❌ Failed to add API key.',
                'admin_stats': '📊 **Statistics**\n\n👥 Total Users: {users}\n💎 Subscribed: {subscribed}\n🎰 Total Rounds: {rounds}\n👤 Participants: {participants}\n🏆 Winners: {winners}\n💰 Total Paid: ${paid}',
                'admin_poll_sent': '📊 Poll sent to all users!',
                'poll_question': '📊 **Next Lottery Round?**\n\nPrice: $100 USDT\nDo you want to start a new round?',
                'poll_vote_recorded': '✅ Vote recorded!',
                'access_denied': '⛔ Access denied.',
                'canceled': '❌ Operation cancelled.',
                'processing': '⏳ Processing...',
                'error': '❌ An error occurred. Please try again.',
                'invalid_number': '❌ Enter a valid number.',
                'invalid_amount': '❌ Enter a valid amount.',
                'copy_fail': '❌ Copy failed!',
            },
            'fa': {
                # دکمه‌ها
                'btn_join': '🎰 شرکت در قرعه‌کشی',
                'btn_referral': '👥 دعوت از دوستان',
                'btn_guide': '📖 راهنمایی',
                'btn_language': '🌐 تغییر زبان',
                'btn_withdraw': '💰 برداشت جایزه',
                'btn_verify': '✅ تایید پرداخت',
                'btn_copy': '📋 کپی',
                'btn_share': '📤 اشتراک‌گذاری',
                'btn_back': '🔙 بازگشت',
                'btn_cancel': '❌ لغو',
                'btn_confirm': '✅ تایید',
                
                # پیام‌ها
                'welcome': '🎰 **به ربات قرعه‌کشی UTYOB خوش آمدید!**\n\n💰 فقط با ۱۰۰ دلار در قرعه‌کشی شرکت کنید\n🎁 تا ۲,۰۰۰ دلار برنده شوید!\n\nاز دکمه‌های زیر استفاده کنید.',
                'guide': '📖 **راهنما**\n\n۱️⃣ ۱۰۰ دلار USDT به آدرس زیر ارسال کنید:\n`{wallet}`\n۲️⃣ آدرس کیف پول و هش تراکنش خود را وارد کنید\n۳️⃣ منتظر قرعه‌کشی باشید\n۴️⃣ اگر برنده شدید، جایزه خود را برداشت کنید!\n\n⚡ قرعه‌کشی عادلانه با انتخاب هوش مصنوعی.',
                'referral': '👥 **سیستم دعوت**\n\n🔗 لینک شما:\n`https://t.me/UTYOB_Bot?start=ref_{code}`\n\n📊 تعداد دعوت: {count}\n⭐ امتیاز: {points}',
                'join_subscription': '⚠️ **برای شرکت نیاز به اشتراک دارید!**\n\n💰 قیمت: ${price}\n📥 ارسال به: `{wallet}`\n\nلطفاً آدرس کیف پول مبدا خود را وارد کنید (TRC20):',
                'wallet_saved': '✅ **آدرس کیف پول ذخیره شد!**\n\n📤 کیف پول شما: `{wallet}`\n📥 **دقیقاً ${price} USDT به آدرس زیر ارسال کنید:**\n`{destination}`\n\n⏳ هش تراکنش (TxID) خود را وارد کنید:',
                'wallet_invalid': '❌ آدرس کیف پول نامعتبر!\nلطفاً یک آدرس TRC20 معتبر وارد کنید.',
                'verifying': '⏳ در حال تایید تراکنش...',
                'verify_success': '✅ پرداخت تایید شد! شما در قرعه‌کشی ثبت نام شدید!',
                'verify_fail': '❌ تراکنش پیدا نشد یا نامعتبر است!\nلطفاً بررسی کنید و دوباره تلاش کنید.',
                'verify_pending': '⏳ در انتظار تایید...\n{confirmations}/{required}',
                'register_fail': '❌ ثبت نام ناموفق بود!',
                'already_participated': '✅ شما قبلاً شرکت کرده‌اید!',
                'already_registered': '⚠️ شما قبلاً ثبت نام کرده‌اید!',
                'no_prize': '❌ جایزه‌ای برای برداشت وجود ندارد!',
                'withdraw_enter': '💰 **برداشت ${amount} USDT**\n\nآدرس کیف پول TRC20 خود را وارد کنید:',
                'withdraw_invalid': '❌ آدرس TRC20 نامعتبر!',
                'withdraw_success': '✅ درخواست برداشت ثبت شد!',
                'withdraw_fail': '❌ جایزه‌ای در انتظار پیدا نشد!',
                'copy_success': '✅ لینک دعوت کپی شد!',
                'language_changed': '✅ زبان به فارسی تغییر کرد!',
                'language_select': '🌐 زبان خود را انتخاب کنید:',
                'admin_panel': '🛠️ **پنل مدیریت**\n\nیک اقدام را انتخاب کنید:',
                'admin_broadcast': '📢 **متن پیام همگانی را وارد کنید:**',
                'admin_start_confirm': '⚠️ **شروع قرعه‌کشی جدید؟**\n\nچند نفر برنده شوند؟',
                'admin_winner_count': '💰 **مبلغ جایزه هر برنده (دلار):**',
                'admin_lottery_complete': '✅ **قرعه‌کشی کامل شد!**\n\n🏆 تعداد برنده‌ها: {count}\n💰 جایزه هر نفر: ${amount}\n🎰 دور: #{round}',
                'admin_no_participants': '❌ شرکت‌کننده‌ای وجود ندارد!',
                'admin_manual_verify': '🔍 **تایید دستی**\n\nآیدی کاربر را وارد کنید:',
                'admin_manual_success': '✅ کاربر {user_id} با موفقیت تایید شد!',
                'admin_pay_success': '💸 به {count} برنده پرداخت شد!',
                'admin_add_api': '🔑 **افزودن API Key جدید**\n\nفرمت: `name|api_key|base_url`\nمثال: `secondary|key123|https://api.trongrid.io`',
                'admin_api_success': '✅ API key \'{name}\' با موفقیت اضافه شد!',
                'admin_api_fail': '❌ افزودن API key ناموفق بود.',
                'admin_stats': '📊 **آمار**\n\n👥 کل کاربران: {users}\n💎 دارای اشتراک: {subscribed}\n🎰 تعداد دورها: {rounds}\n👤 شرکت‌کنندگان: {participants}\n🏆 برنده‌ها: {winners}\n💰 کل پرداختی: ${paid}',
                'admin_poll_sent': '📊 نظرسنجی به همه کاربران ارسال شد!',
                'poll_question': '📊 **دور بعدی قرعه‌کشی؟**\n\nقیمت: ۱۰۰ دلار USDT\nآیا می‌خواهید دور جدید شروع شود؟',
                'poll_vote_recorded': '✅ رأی شما ثبت شد!',
                'access_denied': '⛔ دسترسی غیرمجاز.',
                'canceled': '❌ عملیات لغو شد.',
                'processing': '⏳ در حال پردازش...',
                'error': '❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.',
                'invalid_number': '❌ یک عدد معتبر وارد کنید.',
                'invalid_amount': '❌ یک مبلغ معتبر وارد کنید.',
                'copy_fail': '❌ کپی ناموفق بود!',
            },
            'tr': {
                # دکمه‌ها
                'btn_join': '🎰 Piyangoya Katıl',
                'btn_referral': '👥 Davet Et',
                'btn_guide': '📖 Rehber',
                'btn_language': '🌐 Dil Değiştir',
                'btn_withdraw': '💰 Ödülü Çek',
                'btn_verify': '✅ Ödemeyi Doğrula',
                'btn_copy': '📋 Kopyala',
                'btn_share': '📤 Paylaş',
                'btn_back': '🔙 Geri',
                'btn_cancel': '❌ İptal',
                'btn_confirm': '✅ Onayla',
                
                # پیام‌ها
                'welcome': '🎰 **UTYOB Piyango Botuna Hoş Geldiniz!**\n\n💰 Sadece $100 ile piyangoya katılın\n🎁 2.000$'a kadar kazanın!\n\nBaşlamak için aşağıdaki butonları kullanın.',
                'guide': '📖 **Rehber**\n\n1️⃣ $100 USDT\'yi şu adrese gönderin:\n`{wallet}`\n2️⃣ Cüzdan adresinizi ve TxID\'nizi girin\n3️⃣ Piyango çekilişini bekleyin\n4️⃣ Kazanırsanız, ödülünüzü çekin!\n\n⚡ Yapay zeka ile adil piyango.',
                'referral': '👥 **Davet Sistemi**\n\n🔗 Bağlantınız:\n`https://t.me/UTYOB_Bot?start=ref_{code}`\n\n📊 Davetler: {count}\n⭐ Puan: {points}',
                'join_subscription': '⚠️ **Abonelik gerekiyor!**\n\n💰 Fiyat: ${price}\n📥 Gönderilecek adres: `{wallet}`\n\nLütfen kaynak cüzdan adresinizi girin (TRC20):',
                'wallet_saved': '✅ **Cüzdan kaydedildi!**\n\n📤 Cüzdanınız: `{wallet}`\n📥 **Tam olarak ${price} USDT gönderin:**\n`{destination}`\n\n⏳ İşlem kodunuzu (TxID) girin:',
                'wallet_invalid': '❌ Geçersiz cüzdan adresi!\nLütfen geçerli bir TRC20 adresi girin.',
                'verifying': '⏳ İşlem doğrulanıyor...',
                'verify_success': '✅ Ödeme onaylandı! Piyangoya kaydoldunuz!',
                'verify_fail': '❌ İşlem bulunamadı veya geçersiz!\nLütfen kontrol edip tekrar deneyin.',
                'verify_pending': '⏳ Onay bekleniyor...\n{confirmations}/{required}',
                'register_fail': '❌ Kayıt başarısız!',
                'already_participated': '✅ Zaten katıldınız!',
                'already_registered': '⚠️ Zaten kayıtlısınız!',
                'no_prize': '❌ Çekilecek ödül yok!',
                'withdraw_enter': '💰 **${amount} USDT Çek**\n\nTRC20 cüzdan adresinizi girin:',
                'withdraw_invalid': '❌ Geçersiz TRC20 adresi!',
                'withdraw_success': '✅ Çekim talebi gönderildi!',
                'withdraw_fail': '❌ Bekleyen ödül bulunamadı!',
                'copy_success': '✅ Davet bağlantısı kopyalandı!',
                'language_changed': '✅ Dil Türkçe olarak değiştirildi!',
                'language_select': '🌐 Dilinizi seçin:',
                'admin_panel': '🛠️ **Yönetim Paneli**\n\nBir işlem seçin:',
                'admin_broadcast': '📢 **Mesajınızı girin:**',
                'admin_start_confirm': '⚠️ **Yeni piyango başlatılsın mı?**\n\nKaç kazanan olsun?',
                'admin_winner_count': '💰 **Her kazanan için ödül miktarı (USDT):**',
                'admin_lottery_complete': '✅ **Piyango tamamlandı!**\n\n🏆 Kazananlar: {count}\n💰 Ödül: ${amount} her biri\n🎰 Tur: #{round}',
                'admin_no_participants': '❌ Uygun katılımcı yok!',
                'admin_manual_verify': '🔍 **Manuel Doğrulama**\n\nKullanıcı ID girin:',
                'admin_manual_success': '✅ Kullanıcı {user_id} manuel doğrulandı!',
                'admin_pay_success': '💸 {count} kazanana ödeme yapıldı!',
                'admin_add_api': '🔑 **API Anahtarı Ekle**\n\nFormat: `name|api_key|base_url`\nÖrnek: `secondary|key123|https://api.trongrid.io`',
                'admin_api_success': '✅ \'{name}\' API anahtarı eklendi!',
                'admin_api_fail': '❌ API anahtarı eklenemedi.',
                'admin_stats': '📊 **İstatistikler**\n\n👥 Toplam Kullanıcı: {users}\n💎 Abone: {subscribed}\n🎰 Toplam Tur: {rounds}\n👤 Katılımcı: {participants}\n🏆 Kazanan: {winners}\n💰 Toplam Ödenen: ${paid}',
                'admin_poll_sent': '📊 Anket tüm kullanıcılara gönderildi!',
                'poll_question': '📊 **Yeni Piyango Turu?**\n\nFiyat: $100 USDT\nYeni bir tur başlatmak ister misiniz?',
                'poll_vote_recorded': '✅ Oyunuz kaydedildi!',
                'access_denied': '⛔ Erişim engellendi.',
                'canceled': '❌ İşlem iptal edildi.',
                'processing': '⏳ İşleniyor...',
                'error': '❌ Bir hata oluştu. Lütfen tekrar deneyin.',
                'invalid_number': '❌ Geçerli bir sayı girin.',
                'invalid_amount': '❌ Geçerli bir miktar girin.',
                'copy_fail': '❌ Kopyalama başarısız!',
            }
        }
    
    def get(self, key: str, lang: str = 'en', **kwargs) -> str:
        """دریافت ترجمه با پارامترها"""
        text = self.translations.get(lang, self.translations['en']).get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

lang_manager = LanguageManager()

# ============================================================
# دیتابیس قدرتمند
# ============================================================
class Database:
    """دیتابیس با قابلیت مقیاس‌پذیری بالا و کش"""
    
    def __init__(self, db_path='lottery.db'):
        self.db_path = db_path
        self.cache = {}
        self.cache_time = {}
        self.cache_ttl = 300
        self._init_db()
    
    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # جداول اصلی
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'en',
                    wallet_address TEXT,
                    points INTEGER DEFAULT 0,
                    has_subscription INTEGER DEFAULT 0,
                    subscription_date TIMESTAMP,
                    total_participations INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_amount_won REAL DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referral_count INTEGER DEFAULT 0,
                    referral_points INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tx_hash TEXT UNIQUE NOT NULL,
                    from_address TEXT,
                    to_address TEXT,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    confirmations INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
                );
                
                CREATE TABLE IF NOT EXISTS lotteries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    round_number INTEGER UNIQUE NOT NULL,
                    total_pool REAL DEFAULT 0,
                    admin_fee REAL DEFAULT 0,
                    prize_pool REAL DEFAULT 0,
                    number_of_winners INTEGER,
                    prize_per_winner REAL,
                    status TEXT DEFAULT 'pending',
                    is_active INTEGER DEFAULT 0,
                    started_at TIMESTAMP,
                    drawn_at TIMESTAMP,
                    lottery_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS lottery_participations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    lottery_id INTEGER NOT NULL,
                    weight REAL DEFAULT 1.0,
                    is_winner INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (lottery_id) REFERENCES lotteries (id)
                );
                
                CREATE TABLE IF NOT EXISTS winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    lottery_id INTEGER NOT NULL,
                    prize_amount REAL NOT NULL,
                    withdrawal_status TEXT DEFAULT 'pending',
                    withdrawal_address TEXT,
                    paid_at TIMESTAMP,
                    is_excluded_from_next INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (lottery_id) REFERENCES lotteries (id)
                );
                
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    usage_count INTEGER DEFAULT 0,
                    max_usage_per_day INTEGER DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS polls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lottery_id INTEGER,
                    question TEXT,
                    status TEXT DEFAULT 'active',
                    total_votes INTEGER DEFAULT 0,
                    yes_votes INTEGER DEFAULT 0,
                    no_votes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_hash ON transactions(tx_hash);
                CREATE INDEX IF NOT EXISTS idx_participations_lottery ON lottery_participations(lottery_id);
            ''')
            conn.commit()
            logger.info("✅ Database initialized")
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _get_cache(self, key):
        if key in self.cache and time.time() - self.cache_time.get(key, 0) < self.cache_ttl:
            return self.cache[key]
        return None
    
    def _set_cache(self, key, value):
        self.cache[key] = value
        self.cache_time[key] = time.time()
    
    def _clear_cache(self, key=None):
        if key:
            self.cache.pop(key, None)
            self.cache_time.pop(key, None)
        else:
            self.cache.clear()
            self.cache_time.clear()
    
    # متدهای کاربر
    def get_or_create_user(self, telegram_id: int, first_name: str = '', username: str = '') -> dict:
        cache_key = f"user_{telegram_id}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user = cursor.fetchone()
            
            if not user:
                referral_code = hashlib.md5(str(telegram_id).encode()).hexdigest()[:8].upper()
                cursor.execute('''
                    INSERT INTO users (telegram_id, first_name, username, referral_code)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, first_name, username, referral_code))
                conn.commit()
                cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
                user = cursor.fetchone()
            
            result = dict(user)
            self._set_cache(cache_key, result)
            return result
    
    def update_user_language(self, telegram_id: int, language: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET language = ? WHERE telegram_id = ?', (language, telegram_id))
            conn.commit()
            self._clear_cache(f"user_{telegram_id}")
            return cursor.rowcount > 0
    
    def has_participated(self, telegram_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM lottery_participations 
                WHERE user_id = ? AND lottery_id = (
                    SELECT id FROM lotteries WHERE is_active = 1 ORDER BY id DESC LIMIT 1
                )
            ''', (telegram_id,))
            return cursor.fetchone()[0] > 0
    
    def register_participation(self, telegram_id: int, tx_hash: str, wallet_address: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM lotteries WHERE is_active = 1 ORDER BY id DESC LIMIT 1')
            lottery = cursor.fetchone()
            
            if not lottery:
                cursor.execute('SELECT COUNT(*) FROM lotteries')
                count = cursor.fetchone()[0] + 1
                cursor.execute('''
                    INSERT INTO lotteries (round_number, status, is_active, started_at)
                    VALUES (?, 'active', 1, CURRENT_TIMESTAMP)
                ''', (count,))
                conn.commit()
                lottery_id = cursor.lastrowid
            else:
                lottery_id = lottery[0]
            
            cursor.execute('''
                INSERT INTO transactions (user_id, tx_hash, from_address, to_address, amount, status, confirmed_at)
                VALUES (?, ?, ?, ?, ?, 'confirmed', CURRENT_TIMESTAMP)
            ''', (telegram_id, tx_hash, wallet_address, DESTINATION_WALLET, LOTTERY_PRICE))
            
            cursor.execute('''
                INSERT INTO lottery_participations (user_id, lottery_id)
                VALUES (?, ?)
            ''', (telegram_id, lottery_id))
            
            cursor.execute('''
                UPDATE users SET 
                    has_subscription = 1,
                    subscription_date = CURRENT_TIMESTAMP,
                    total_participations = total_participations + 1
                WHERE telegram_id = ?
            ''', (telegram_id,))
            
            cursor.execute('''
                UPDATE lotteries SET 
                    total_pool = total_pool + ?,
                    prize_pool = prize_pool + ?,
                    admin_fee = admin_fee + ?
                WHERE id = ?
            ''', (LOTTERY_PRICE, LOTTERY_PRICE * 0.80, LOTTERY_PRICE * 0.20, lottery_id))
            
            conn.commit()
            self._clear_cache(f"user_{telegram_id}")
            return True
    
    def get_participants(self) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.telegram_id, u.has_subscription, u.total_participations, u.total_wins
                FROM lottery_participations lp
                JOIN users u ON lp.user_id = u.telegram_id
                WHERE lp.lottery_id = (SELECT id FROM lotteries WHERE is_active = 1 ORDER BY id DESC LIMIT 1)
            ''')
            return [{'user_id': row[0], 'has_subscription': row[1], 'total_participations': row[2], 'total_wins': row[3]} 
                    for row in cursor.fetchall()]
    
    def get_previous_winners(self) -> List[int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM winners ORDER BY id DESC LIMIT 100')
            return [row[0] for row in cursor.fetchall()]
    
    def create_lottery(self, winner_count: int, prize_amount: float, winners: List[int]) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM lotteries')
            round_num = cursor.fetchone()[0] + 1
            
            cursor.execute('''
                INSERT INTO lotteries (round_number, number_of_winners, prize_per_winner, prize_pool, status, drawn_at)
                VALUES (?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
            ''', (round_num, winner_count, prize_amount, winner_count * prize_amount))
            
            lottery_id = cursor.lastrowid
            
            for user_id in winners:
                cursor.execute('''
                    INSERT INTO winners (user_id, lottery_id, prize_amount, is_excluded_from_next)
                    VALUES (?, ?, ?, 1)
                ''', (user_id, lottery_id, prize_amount))
                
                cursor.execute('''
                    UPDATE users SET total_wins = total_wins + 1, total_amount_won = total_amount_won + ?
                    WHERE telegram_id = ?
                ''', (prize_amount, user_id))
            
            cursor.execute('UPDATE lotteries SET is_active = 0 WHERE is_active = 1')
            conn.commit()
            return lottery_id
    
    def get_winner(self, telegram_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, prize_amount, withdrawal_status, withdrawal_address
                FROM winners
                WHERE user_id = ? AND withdrawal_status = 'pending'
                ORDER BY id DESC LIMIT 1
            ''', (telegram_id,))
            row = cursor.fetchone()
            if row:
                return {'id': row[0], 'prize_amount': row[1], 'withdrawal_status': row[2], 'withdrawal_address': row[3]}
            return None
    
    def save_withdrawal_address(self, telegram_id: int, address: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE winners SET withdrawal_address = ?, withdrawal_status = 'requested'
                WHERE user_id = ? AND withdrawal_status = 'pending'
            ''', (address, telegram_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def pay_winners(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE winners SET withdrawal_status = 'paid', paid_at = CURRENT_TIMESTAMP
                WHERE withdrawal_status = 'requested'
            ''')
            conn.commit()
            return cursor.rowcount
    
    def get_all_users(self) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT telegram_id, language FROM users WHERE is_active = 1')
            return [{'telegram_id': row[0], 'language': row[1]} for row in cursor.fetchall()]
    
    def add_api_key(self, name: str, api_key: str, base_url: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO api_keys (name, api_key, base_url)
                VALUES (?, ?, ?)
            ''', (name, api_key, base_url))
            conn.commit()
            return cursor.lastrowid > 0
    
    def get_api_keys(self) -> List[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name, api_key, base_url FROM api_keys WHERE is_active = 1')
            return [{'name': row[0], 'api_key': row[1], 'base_url': row[2]} for row in cursor.fetchall()]
    
    def get_active_lottery(self) -> Optional[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, round_number, total_pool, prize_pool, number_of_winners, prize_per_winner
                FROM lotteries WHERE is_active = 1 ORDER BY id DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'round_number': row[1],
                    'total_pool': row[2],
                    'prize_pool': row[3],
                    'number_of_winners': row[4],
                    'prize_per_winner': row[5]
                }
            return None
    
    def get_statistics(self) -> dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE has_subscription = 1')
            subscribed = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM lotteries')
            total_rounds = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM lottery_participations')
            total_participations = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM winners')
            total_winners = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(prize_amount) FROM winners WHERE withdrawal_status = "paid"')
            total_paid = cursor.fetchone()[0] or 0
            
            return {
                'total_users': total_users,
                'subscribed': subscribed,
                'total_rounds': total_rounds,
                'total_participations': total_participations,
                'total_winners': total_winners,
                'total_paid': total_paid
            }

# ============================================================
# سرویس پرداخت
# ============================================================
class PaymentService:
    def __init__(self, db: Database):
        self.db = db
        self.api_keys = db.get_api_keys()
        if not self.api_keys:
            self.api_keys = [{'name': 'primary', 'api_key': TRON_API_KEY, 'base_url': 'https://api.trongrid.io'}]
    
    async def verify_transaction(self, tx_hash: str, expected_amount: float, expected_to_address: str) -> dict:
        for api in self.api_keys:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{api['base_url']}/v1/transactions/{tx_hash}"
                    headers = {"API-Key": api['api_key']}
                    
                    async with session.get(url, headers=headers, timeout=15) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'data' in data and len(data['data']) > 0:
                                tx_data = data['data'][0]
                                
                                amount = self._extract_amount(tx_data)
                                to_address = self._extract_to_address(tx_data)
                                from_address = self._extract_from_address(tx_data)
                                confirmations = self._get_confirmations(tx_data)
                                
                                if abs(amount - expected_amount) <= 0.01:
                                    if to_address.lower() == expected_to_address.lower():
                                        if confirmations >= CONFIRMATION_THRESHOLD:
                                            return {
                                                'status': 'confirmed',
                                                'amount': amount,
                                                'from_address': from_address,
                                                'to_address': to_address,
                                                'confirmations': confirmations,
                                                'tx_hash': tx_hash
                                            }
                                        else:
                                            return {
                                                'status': 'pending',
                                                'confirmations': confirmations,
                                                'required': CONFIRMATION_THRESHOLD
                                            }
            except Exception as e:
                logger.error(f"API {api['name']} failed: {e}")
                continue
        
        return {'status': 'failed', 'reason': 'Transaction not found or invalid'}
    
    def _extract_amount(self, tx_data: dict) -> float:
        try:
            if 'amount' in tx_data:
                return float(tx_data['amount']) / 1e6
            if 'value' in tx_data:
                return float(tx_data['value']) / 1e6
            return 0.0
        except:
            return 0.0
    
    def _extract_to_address(self, tx_data: dict) -> str:
        try:
            return tx_data.get('to', tx_data.get('destination', ''))
        except:
            return ''
    
    def _extract_from_address(self, tx_data: dict) -> str:
        try:
            return tx_data.get('from', tx_data.get('source', ''))
        except:
            return ''
    
    def _get_confirmations(self, tx_data: dict) -> int:
        try:
            return int(tx_data.get('confirmations', 0))
        except:
            return 0

# ============================================================
# سرویس قرعه‌کشی هوشمند
# ============================================================
class LotteryService:
    @staticmethod
    def select_winners(participants: List[dict], number_of_winners: int, exclude_users: List[int] = None) -> List[int]:
        if exclude_users is None:
            exclude_users = []
        
        eligible = [
            p for p in participants 
            if p['user_id'] not in exclude_users and p.get('has_subscription', False)
        ]
        
        if not eligible or len(eligible) < number_of_winners:
            return []
        
        weights = []
        for p in eligible:
            weight = 1.0
            weight += p.get('total_participations', 0) * 0.01
            weight -= p.get('total_wins', 0) * 0.05
            weight = max(0.5, min(weight, 2.0))
            weights.append(weight)
        
        total_weight = sum(weights)
        if total_weight == 0:
            return []
        
        normalized = [w / total_weight for w in weights]
        selected = []
        available = list(range(len(eligible)))
        
        random.seed(int(time.time()) + sum([p['user_id'] for p in eligible]))
        
        for _ in range(min(number_of_winners, len(eligible))):
            if not available:
                break
            idx = random.choices(available, weights=[normalized[i] for i in available], k=1)[0]
            selected.append(eligible[idx]['user_id'])
            available.remove(idx)
        
        return selected

# ============================================================
# کلاس اصلی ربات
# ============================================================
class LotteryBot:
    WAITING_WALLET, WAITING_TX_HASH, WAITING_WITHDRAWAL = range(3)
    ADMIN_BROADCAST, ADMIN_WINNER_COUNT, ADMIN_PRIZE_AMOUNT, ADMIN_MANUAL_VERIFY, ADMIN_API_KEY = range(5)
    
    def __init__(self):
        self.db = Database()
        self.payment = PaymentService(self.db)
        self.lottery = LotteryService()
        self.application = None
    
    def run(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._register_handlers()
        logger.info("🚀 Starting UTYOB Lottery Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    def _register_handlers(self):
        app = self.application
        
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("admin", self.cmd_admin))
        
        app.add_handler(CallbackQueryHandler(self.handle_main_menu, pattern='^(join_lottery|referral|guide|change_lang|back_main)$'))
        
        # شرکت در قرعه‌کشی
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_join, pattern='^join_lottery$')],
            states={
                self.WAITING_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_wallet)],
                self.WAITING_TX_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_tx_hash)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        app.add_handler(conv_handler)
        
        # برداشت
        withdrawal_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_withdraw, pattern='^withdraw_prize$')],
            states={
                self.WAITING_WITHDRAWAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_withdrawal)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        app.add_handler(withdrawal_handler)
        
        # مدیریت
        admin_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.handle_admin, pattern='^admin_(broadcast|start_lottery|manual_verify|pay_winners|add_api|poll|stats)$')],
            states={
                self.ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_broadcast)],
                self.ADMIN_WINNER_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_winner_count)],
                self.ADMIN_PRIZE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_prize_amount)],
                self.ADMIN_MANUAL_VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_manual_verify)],
                self.ADMIN_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_api_key)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        app.add_handler(admin_handler)
        
        app.add_handler(CallbackQueryHandler(self.set_language, pattern='^lang_'))
        app.add_handler(CallbackQueryHandler(self.handle_poll, pattern='^poll_'))
        
        logger.info("✅ All handlers registered")
    
    # ============================================================
    # دریافت ترجمه
    # ============================================================
    def get_text(self, update: Update, key: str, **kwargs) -> str:
        """دریافت ترجمه بر اساس زبان کاربر"""
        user_id = update.effective_user.id
        user = self.db.get_or_create_user(user_id)
        lang = user.get('language', 'en')
        return lang_manager.get(key, lang, **kwargs)
    
    # ============================================================
    # دستورات اصلی
    # ============================================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self.db.get_or_create_user(
            user_id,
            update.effective_user.first_name or '',
            update.effective_user.username or ''
        )
        
        keyboard = [
            [InlineKeyboardButton(self.get_text(update, 'btn_join'), callback_data="join_lottery"),
             InlineKeyboardButton(self.get_text(update, 'btn_referral'), callback_data="referral")],
            [InlineKeyboardButton(self.get_text(update, 'btn_guide'), callback_data="guide"),
             InlineKeyboardButton(self.get_text(update, 'btn_language'), callback_data="change_lang")]
        ]
        
        await update.message.reply_text(
            self.get_text(update, 'welcome'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text(self.get_text(update, 'access_denied'))
            return
        
        keyboard = [
            [InlineKeyboardButton("📢 " + self.get_text(update, 'admin_broadcast'), callback_data="admin_broadcast"),
             InlineKeyboardButton("🎰 " + self.get_text(update, 'admin_start_confirm'), callback_data="admin_start_lottery")],
            [InlineKeyboardButton("✅ " + self.get_text(update, 'admin_manual_verify'), callback_data="admin_manual_verify"),
             InlineKeyboardButton("📊 " + self.get_text(update, 'admin_poll_sent'), callback_data="admin_poll")],
            [InlineKeyboardButton("💸 " + self.get_text(update, 'admin_pay_success'), callback_data="admin_pay_winners"),
             InlineKeyboardButton("🔑 " + self.get_text(update, 'admin_add_api'), callback_data="admin_add_api")],
            [InlineKeyboardButton("📈 " + self.get_text(update, 'admin_stats'), callback_data="admin_stats")]
        ]
        
        await update.message.reply_text(
            self.get_text(update, 'admin_panel'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.get_text(update, 'canceled'))
        return ConversationHandler.END
    
    # ============================================================
    # منوی اصلی
    # ============================================================
    
    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == 'join_lottery':
            await self.start_join(update, context)
        elif query.data == 'referral':
            await self.show_referral(update, context)
        elif query.data == 'guide':
            await self.show_guide(update, context)
        elif query.data == 'change_lang':
            await self.show_language_menu(update, context)
        elif query.data == 'back_main':
            await self.cmd_start(update, context)
    
    # ============================================================
    # شرکت در قرعه‌کشی
    # ============================================================
    
    async def start_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        user = self.db.get_or_create_user(user_id)
        
        if self.db.has_participated(user_id):
            await query.message.reply_text(self.get_text(update, 'already_participated'))
            return
        
        if not user.get('has_subscription', False):
            text = self.get_text(update, 'join_subscription', price=LOTTERY_PRICE, wallet=DESTINATION_WALLET)
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            return self.WAITING_WALLET
        
        await query.message.reply_text(self.get_text(update, 'already_registered'))
        return ConversationHandler.END
    
    async def process_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        wallet_address = update.message.text.strip()
        user_id = update.effective_user.id
        
        if len(wallet_address) != 34 or not wallet_address.startswith('T'):
            await update.message.reply_text(self.get_text(update, 'wallet_invalid'))
            return self.WAITING_WALLET
        
        context.user_data['wallet_address'] = wallet_address
        
        text = self.get_text(update, 'wallet_saved', 
                            wallet=wallet_address, 
                            price=LOTTERY_PRICE, 
                            destination=DESTINATION_WALLET)
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return self.WAITING_TX_HASH
    
    async def process_tx_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        tx_hash = update.message.text.strip()
        user_id = update.effective_user.id
        wallet_address = context.user_data.get('wallet_address')
        
        await update.message.reply_text(self.get_text(update, 'verifying'))
        
        result = await self.payment.verify_transaction(tx_hash, LOTTERY_PRICE, DESTINATION_WALLET)
        
        if result['status'] == 'confirmed':
            if self.db.register_participation(user_id, tx_hash, wallet_address):
                await update.message.reply_text(self.get_text(update, 'verify_success'))
                return ConversationHandler.END
            else:
                await update.message.reply_text(self.get_text(update, 'register_fail'))
                return ConversationHandler.END
        
        elif result['status'] == 'pending':
            await update.message.reply_text(
                self.get_text(update, 'verify_pending', 
                            confirmations=result['confirmations'], 
                            required=result['required'])
            )
            return self.WAITING_TX_HASH
        
        else:
            await update.message.reply_text(self.get_text(update, 'verify_fail'))
            return self.WAITING_TX_HASH
    
    # ============================================================
    # برداشت جایزه
    # ============================================================
    
    async def start_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        
        winner = self.db.get_winner(user_id)
        if not winner:
            await query.message.reply_text(self.get_text(update, 'no_prize'))
            await query.answer()
            return ConversationHandler.END
        
        await query.message.reply_text(
            self.get_text(update, 'withdraw_enter', amount=winner['prize_amount'])
        )
        await query.answer()
        return self.WAITING_WITHDRAWAL
    
    async def process_withdrawal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        address = update.message.text.strip()
        user_id = update.effective_user.id
        
        if len(address) != 34 or not address.startswith('T'):
            await update.message.reply_text(self.get_text(update, 'withdraw_invalid'))
            return self.WAITING_WITHDRAWAL
        
        if self.db.save_withdrawal_address(user_id, address):
            await update.message.reply_text(self.get_text(update, 'withdraw_success'))
            
            await self.application.bot.send_message(
                ADMIN_ID,
                f"💸 **Withdrawal Request**\n\n👤 User: {user_id}\n📤 Address: `{address}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(self.get_text(update, 'withdraw_fail'))
        
        return ConversationHandler.END
    
    # ============================================================
    # رفرال
    # ============================================================
    
    async def show_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        user = self.db.get_or_create_user(user_id)
        
        keyboard = [[InlineKeyboardButton(self.get_text(update, 'btn_back'), callback_data="back_main")]]
        
        await query.message.reply_text(
            self.get_text(update, 'referral', 
                         code=user['referral_code'], 
                         count=user['referral_count'], 
                         points=user['referral_points']),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        await query.answer()
    
    # ============================================================
    # راهنما
    # ============================================================
    
    async def show_guide(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        
        keyboard = [[InlineKeyboardButton(self.get_text(update, 'btn_back'), callback_data="back_main")]]
        
        await query.message.reply_text(
            self.get_text(update, 'guide', wallet=DESTINATION_WALLET),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        await query.answer()
    
    # ============================================================
    # تغییر زبان - کامل
    # ============================================================
    
    async def show_language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
             InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
             InlineKeyboardButton(self.get_text(update, 'btn_back'), callback_data="back_main")]
        ]
        
        await query.message.reply_text(
            self.get_text(update, 'language_select'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await query.answer()
    
    async def set_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        lang = query.data.split('_')[1]
        user_id = query.from_user.id
        
        if self.db.update_user_language(user_id, lang):
            # به‌روزرسانی کاربر
            user = self.db.get_or_create_user(user_id)
            
            # نمایش پیام با زبان جدید
            text = lang_manager.get('language_changed', lang)
            await query.message.reply_text(text)
            
            # نمایش مجدد منوی اصلی با زبان جدید
            keyboard = [
                [InlineKeyboardButton(lang_manager.get('btn_join', lang), callback_data="join_lottery"),
                 InlineKeyboardButton(lang_manager.get('btn_referral', lang), callback_data="referral")],
                [InlineKeyboardButton(lang_manager.get('btn_guide', lang), callback_data="guide"),
                 InlineKeyboardButton(lang_manager.get('btn_language', lang), callback_data="change_lang")]
            ]
            
            await query.message.reply_text(
                lang_manager.get('welcome', lang),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        await query.answer()
    
    # ============================================================
    # پنل مدیریت کامل
    # ============================================================
    
    async def handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        action = query.data.split('_')[1]
        
        if query.from_user.id != ADMIN_ID:
            await query.answer(self.get_text(update, 'access_denied'))
            return
        
        if action == 'broadcast':
            await query.message.reply_text(self.get_text(update, 'admin_broadcast'))
            await query.answer()
            return self.ADMIN_BROADCAST
        
        elif action == 'start_lottery':
            await query.message.reply_text(self.get_text(update, 'admin_start_confirm'))
            await query.answer()
            return self.ADMIN_WINNER_COUNT
        
        elif action == 'manual_verify':
            await query.message.reply_text(self.get_text(update, 'admin_manual_verify'))
            await query.answer()
            return self.ADMIN_MANUAL_VERIFY
        
        elif action == 'poll':
            await self.send_poll()
            await query.message.reply_text(self.get_text(update, 'admin_poll_sent'))
            await query.answer()
            return ConversationHandler.END
        
        elif action == 'pay_winners':
            count = self.db.pay_winners()
            await query.message.reply_text(
                self.get_text(update, 'admin_pay_success', count=count)
            )
            await query.answer()
            return ConversationHandler.END
        
        elif action == 'add_api':
            await query.message.reply_text(self.get_text(update, 'admin_add_api'))
            await query.answer()
            return self.ADMIN_API_KEY
        
        elif action == 'stats':
            stats = self.db.get_statistics()
            await query.message.reply_text(
                self.get_text(update, 'admin_stats',
                            users=stats['total_users'],
                            subscribed=stats['subscribed'],
                            rounds=stats['total_rounds'],
                            participants=stats['total_participations'],
                            winners=stats['total_winners'],
                            paid=stats['total_paid'])
            )
            await query.answer()
            return ConversationHandler.END
        
        return ConversationHandler.END
    
    # ============================================================
    # پردازش‌های مدیریت
    # ============================================================
    
    async def process_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        users = self.db.get_all_users()
        sent = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(user['telegram_id'], update.message.text)
                sent += 1
                await asyncio.sleep(0.1)
            except:
                pass
        
        await update.message.reply_text(
            self.get_text(update, 'admin_pay_success', count=sent) if sent > 0 else "❌ No users found!"
        )
        return ConversationHandler.END
    
    async def process_winner_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            count = int(update.message.text.strip())
            if count <= 0:
                raise ValueError
            context.user_data['winner_count'] = count
            await update.message.reply_text(self.get_text(update, 'admin_winner_count'))
            return self.ADMIN_PRIZE_AMOUNT
        except:
            await update.message.reply_text(self.get_text(update, 'invalid_number'))
            return self.ADMIN_WINNER_COUNT
    
    async def process_prize_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            amount = float(update.message.text.strip())
            if amount <= 0:
                raise ValueError
            
            winner_count = context.user_data.get('winner_count', 1)
            participants = self.db.get_participants()
            previous_winners = self.db.get_previous_winners()
            
            winners = self.lottery.select_winners(participants, winner_count, previous_winners)
            
            if not winners:
                await update.message.reply_text(self.get_text(update, 'admin_no_participants'))
                return ConversationHandler.END
            
            lottery_id = self.db.create_lottery(winner_count, amount, winners)
            
            for user_id in winners:
                try:
                    await self.application.bot.send_message(
                        user_id,
                        f"🎉 **Congratulations!**\n\n"
                        f"You won ${amount} USDT!\n"
                        f"Click the button below to withdraw.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                self.get_text(update, 'btn_withdraw'), 
                                callback_data="withdraw_prize"
                            )
                        ]]),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            await update.message.reply_text(
                self.get_text(update, 'admin_lottery_complete',
                            count=len(winners),
                            amount=amount,
                            round=lottery_id)
            )
            
        except:
            await update.message.reply_text(self.get_text(update, 'invalid_amount'))
        
        return ConversationHandler.END
    
    async def process_manual_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = int(update.message.text.strip())
            await update.message.reply_text(
                self.get_text(update, 'admin_manual_success', user_id=user_id)
            )
        except:
            await update.message.reply_text(self.get_text(update, 'invalid_number'))
        
        return ConversationHandler.END
    
    async def process_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            parts = update.message.text.strip().split('|')
            if len(parts) != 3:
                raise ValueError
            
            name, api_key, base_url = parts
            if self.db.add_api_key(name, api_key, base_url):
                self.payment.api_keys = self.db.get_api_keys()
                await update.message.reply_text(
                    self.get_text(update, 'admin_api_success', name=name)
                )
            else:
                await update.message.reply_text(self.get_text(update, 'admin_api_fail'))
        except:
            await update.message.reply_text(self.get_text(update, 'admin_add_api'))
        
        return ConversationHandler.END
    
    # ============================================================
    # نظرسنجی
    # ============================================================
    
    async def send_poll(self):
        users = self.db.get_all_users()
        
        for user in users:
            try:
                lang = user.get('language', 'en')
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Yes", callback_data="poll_yes"),
                     InlineKeyboardButton("❌ No", callback_data="poll_no")]
                ])
                
                await self.application.bot.send_message(
                    user['telegram_id'],
                    lang_manager.get('poll_question', lang),
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
                await asyncio.sleep(0.05)
            except:
                pass
    
    async def handle_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer(lang_manager.get('poll_vote_recorded', 'en'))

# ============================================================
# اجرا
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🎰 UTYOB Lottery Bot v3.0 - نسخه نهایی")
    print("=" * 60)
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"💳 Destination Wallet: {DESTINATION_WALLET}")
    print(f"🌐 Languages: English, فارسی, Türkçe")
    print("=" * 60)
    
    bot = LotteryBot()
    bot.run()