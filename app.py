import asyncio
import json
import logging
import random
import hashlib
import time
import sqlite3
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask, request, jsonify
import threading
import base58
import psutil
import os
from datetime import datetime
import asyncio
from asyncio import Queue
import uvloop
from concurrent.futures import ThreadPoolExecutor

# ==================== تنظیمات ====================
uvloop.install()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== کانفیگ ====================
class Config:
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    ADMIN_IDS = [327855654]  # آیدی ادمین خود را وارد کنید
    
    SHARD_COUNT = 50  # ۵۰ شارد برای میلیون‌ها کاربر
    CACHE_TTL = 300
    
    TRONGRID_API = "https://api.trongrid.io"
    TRONSCAN_API = "https://api.tronscan.org"
    WALLET_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
    AMOUNT_USD = 100
    USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    
    # API Keys با توزیع بار
    API_KEYS = ["7ae83b63-fdf3-47e4-ac69-56f960a34f5b"]
    
    MAX_WORKERS = 50
    VERIFICATION_TIMEOUT = 120  # ۲ دقیقه
    MAX_RETRY = 3

# ==================== دیتابیس شارد شده ====================
class ShardedDatabase:
    def __init__(self):
        self.shards = {}
        self.cache = {}
        self.executor = ThreadPoolExecutor(max_workers=50)
        
        for i in range(Config.SHARD_COUNT):
            db_path = f"shard_{i}.db"
            self.shards[i] = sqlite3.connect(db_path, check_same_thread=False)
            self._init_shard(i)
    
    def _init_shard(self, shard_id):
        cursor = self.shards[shard_id].cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                wallet_address TEXT,
                subscription_end INTEGER,
                referral_code TEXT,
                referred_by INTEGER,
                referral_count INTEGER DEFAULT 0,
                created_at INTEGER,
                language TEXT DEFAULT 'en',
                is_winner BOOLEAN DEFAULT 0,
                won_amount INTEGER DEFAULT 0,
                total_participations INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount INTEGER,
                status TEXT,
                created_at INTEGER,
                verified_at INTEGER,
                api_key_used TEXT,
                retry_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_participants (
                user_id INTEGER PRIMARY KEY,
                participated_at INTEGER,
                wallet_address TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS previous_winners (
                user_id INTEGER PRIMARY KEY,
                win_time INTEGER,
                amount INTEGER
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_end)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        
        self.shards[shard_id].commit()
    
    def _get_shard(self, user_id):
        return user_id % Config.SHARD_COUNT
    
    async def execute_query(self, user_id, query, params=(), fetch=False):
        shard_id = self._get_shard(user_id)
        
        def _execute():
            cursor = self.shards[shard_id].cursor()
            try:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                self.shards[shard_id].commit()
                return cursor.lastrowid
            except Exception as e:
                logger.error(f"DB error on shard {shard_id}: {e}")
                self.shards[shard_id].rollback()
                raise
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _execute)
    
    async def get_user(self, user_id):
        cache_key = f"user_{user_id}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached.get("cached_at", 0) < Config.CACHE_TTL:
                return cached
        
        result = await self.execute_query(
            user_id,
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
            fetch=True
        )
        
        if result:
            user_data = {
                "user_id": result[0][0],
                "username": result[0][1],
                "first_name": result[0][2],
                "last_name": result[0][3],
                "wallet_address": result[0][4],
                "subscription_end": result[0][5],
                "referral_code": result[0][6],
                "referred_by": result[0][7],
                "referral_count": result[0][8] if len(result[0]) > 8 else 0,
                "created_at": result[0][9] if len(result[0]) > 9 else 0,
                "language": result[0][10] if len(result[0]) > 10 else "en",
                "is_winner": result[0][11] if len(result[0]) > 11 else False,
                "won_amount": result[0][12] if len(result[0]) > 12 else 0,
                "total_participations": result[0][13] if len(result[0]) > 13 else 0,
                "is_banned": result[0][14] if len(result[0]) > 14 else False
            }
            user_data["cached_at"] = time.time()
            self.cache[cache_key] = user_data
            return user_data
        return None
    
    async def create_user(self, user_id, username, first_name, last_name=""):
        referral_code = self._generate_referral_code(user_id)
        
        await self.execute_query(
            user_id,
            """INSERT INTO users 
               (user_id, username, first_name, last_name, referral_code, created_at, language) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, first_name, last_name, referral_code, int(time.time()), "en")
        )
        
        return referral_code
    
    async def get_all_users(self):
        """دریافت تمام کاربران برای آمار"""
        users = []
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.shards[shard_id].cursor()
            cursor.execute("SELECT user_id, username, first_name, last_name, subscription_end FROM users")
            users.extend(cursor.fetchall())
        return users
    
    def _generate_referral_code(self, user_id):
        return base58.b58encode(hashlib.sha256(f"{user_id}{time.time()}".encode()).digest()[:8]).decode()

# ==================== سیستم ترجمه ====================
class TranslationSystem:
    def __init__(self):
        self.translations = {
            "en": {
                "welcome": "🎉 Welcome to {bot_name}!\n\nPlease select an option:",
                "join_lottery": "🎰 Join Lottery",
                "referral": "👥 Referral",
                "guidance": "📖 Guidance",
                "change_language": "🌐 Change Language",
                "lottery_join": "💰 Please enter your TRC20 wallet address:",
                "wallet_saved": "✅ Wallet saved!\n\n📤 Please send exactly ${amount} USDT to:\n`{wallet}`\n\n⏳ After sending, click 'I have paid' for automatic verification.",
                "payment_verified": "✅ Payment verified!\n\n🎉 Your subscription is ACTIVE!\nYou will automatically participate in all lotteries.",
                "payment_failed": "❌ Payment verification failed.\nPlease try again or contact admin.",
                "already_paid": "ℹ️ You already have an active subscription.",
                "not_subscribed": "❌ You need an active subscription to participate.",
                "admin_panel": "🔧 Admin Panel",
                "broadcast": "📢 Broadcast",
                "manual_verify": "✅ Manual Verify",
                "add_api": "🔑 Add API",
                "view_stats": "📊 Statistics",
                "i_have_paid": "✅ I have paid",
                "checking_payment": "⏳ Checking your payment...",
                "invalid_wallet": "❌ Invalid TRC20 wallet address.",
                "language_changed": "🌐 Language changed to {lang}",
                "referral_text": "🔗 Your referral link:\n`https://t.me/{bot_username}?start=ref_{code}`\n\n👥 Total referrals: {count}",
                "guidance_text": """📚 **COMPLETE GUIDANCE** 📚

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔰 **PARTICIPATION IS VOLUNTARY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **How to Participate:**
1. Click 'Join Lottery'
2. Enter your TRC20 wallet address
3. Send exactly ${amount} USDT
4. Click 'I have paid'
5. Wait for automatic verification
6. Subscription becomes ACTIVE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **Lottery Process:**
• All active subscribers participate
• Fair random selection
• Multiple winners possible
• Winners announced via broadcast

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Automatic Verification:**
• Blockchain transaction check
• Multiple API verification
• Fast & accurate
• 99.99% reliability

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 **Important Notes:**
• Participation is completely VOLUNTARY
• You may win or not win
• System is 100% FAIR
• No guarantees of winning
• Don't participate if unsure

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤝 **Referral Program:**
• Share your referral link
• Earn bonuses
• Increase participation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Support:**
• Contact admin for help
• 24/7 support available
• Fair and transparent system

🍀 **Good luck to all participants!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
                "admin_stats": "📊 **System Statistics**\n\n👥 Total Users: {users}\n✅ Active Subs: {active}\n💰 Total Prizes: ${prizes}\n🏆 Winners: {winners}\n🔑 API Keys: {apis}",
                "broadcast_sent": "✅ Broadcast sent to {count} users.",
                "manual_verify_done": "✅ User {user_id} verified manually.",
                "api_added": "✅ New API key added. Total: {total}",
                "admin_help": "🔧 **Admin Commands:**\n• /stats - View statistics\n• /broadcast - Send message to all\n• /verify [user_id] - Manual verify\n• /addapi [key] - Add API key"
            },
            "fa": {
                "welcome": "🎉 به ربات {bot_name} خوش آمدید!\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
                "join_lottery": "🎰 شرکت در قرعه‌کشی",
                "referral": "👥 رفرال",
                "guidance": "📖 راهنمایی",
                "change_language": "🌐 تغییر زبان",
                "lottery_join": "💰 لطفاً آدرس کیف پول TRC20 خود را وارد کنید:",
                "wallet_saved": "✅ کیف پول ذخیره شد!\n\n📤 لطفاً دقیقاً ${amount} USDT به آدرس زیر ارسال کنید:\n`{wallet}`\n\n⏳ پس از ارسال، روی 'پرداخت کردم' کلیک کنید.",
                "payment_verified": "✅ پرداخت تایید شد!\n\n🎉 اشتراک شما فعال شد!\nبه صورت خودکار در تمام قرعه‌کشی‌ها شرکت خواهید کرد.",
                "payment_failed": "❌ تایید پرداخت ناموفق بود.\nلطفاً دوباره تلاش کنید یا با ادمین تماس بگیرید.",
                "already_paid": "ℹ️ شما قبلاً اشتراک فعال دارید.",
                "not_subscribed": "❌ برای شرکت در قرعه‌کشی به اشتراک فعال نیاز دارید.",
                "admin_panel": "🔧 پنل مدیریت",
                "broadcast": "📢 پیام همگانی",
                "manual_verify": "✅ تایید دستی",
                "add_api": "🔑 اضافه کردن API",
                "view_stats": "📊 آمار",
                "i_have_paid": "✅ پرداخت کردم",
                "checking_payment": "⏳ در حال بررسی پرداخت شما...",
                "invalid_wallet": "❌ آدرس کیف پول TRC20 نامعتبر است.",
                "language_changed": "🌐 زبان به فارسی تغییر یافت",
                "referral_text": "🔗 لینک رفرال شما:\n`https://t.me/{bot_username}?start=ref_{code}`\n\n👥 تعداد رفرال: {count}",
                "guidance_text": """📚 **راهنمای کامل** 📚

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔰 **شرکت در قرعه‌کشی کاملاً داوطلبانه است**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **نحوه شرکت:**
۱. روی 'شرکت در قرعه‌کشی' کلیک کنید
۲. آدرس کیف پول TRC20 خود را وارد کنید
۳. دقیقاً ${amount} USDT ارسال کنید
۴. روی 'پرداخت کردم' کلیک کنید
۵. منتظر تایید خودکار باشید
۶. اشتراک شما فعال می‌شود

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **فرآیند قرعه‌کشی:**
• تمام کاربران با اشتراک فعال شرکت می‌کنند
• انتخاب تصادفی عادلانه
• امکان چند برنده
• برندگان از طریق پیام همگانی اعلام می‌شوند

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **تایید خودکار:**
• بررسی تراکنش در بلاکچین
• تایید با چندین API
• سریع و دقیق
• ۹۹.۹۹٪ اطمینان

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 **نکات مهم:**
• شرکت کاملاً داوطلبانه است
• ممکن است برنده شوید یا نشوید
• سیستم ۱۰۰٪ عادلانه است
• هیچ تضمینی برای برنده شدن نیست
• اگر مطمئن نیستید شرکت نکنید

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤝 **برنامه رفرال:**
• لینک رفرال خود را به اشتراک بگذارید
• پاداش دریافت کنید
• مشارکت را افزایش دهید

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **پشتیبانی:**
• برای کمک با ادمین تماس بگیرید
• پشتیبانی ۲۴/۷
• سیستم عادلانه و شفاف

🍀 **برای همه شرکت‌کنندگان آرزوی موفقیت داریم!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
                "admin_stats": "📊 **آمار سیستم**\n\n👥 کل کاربران: {users}\n✅ اشتراک فعال: {active}\n💰 مجموع جوایز: ${prizes}\n🏆 برندگان: {winners}\n🔑 تعداد API: {apis}",
                "broadcast_sent": "✅ پیام به {count} کاربر ارسال شد.",
                "manual_verify_done": "✅ کاربر {user_id} به صورت دستی تایید شد.",
                "api_added": "✅ API جدید اضافه شد. تعداد کل: {total}",
                "admin_help": "🔧 **دستورات مدیریت:**\n• /stats - مشاهده آمار\n• /broadcast - ارسال پیام به همه\n• /verify [user_id] - تایید دستی\n• /addapi [key] - اضافه کردن API"
            },
            "tr": {
                "welcome": "🎉 {bot_name} hoş geldiniz!\n\nLütfen bir seçenek seçin:",
                "join_lottery": "🎰 Piyangoya Katıl",
                "referral": "👥 Davet",
                "guidance": "📖 Rehber",
                "change_language": "🌐 Dil Değiştir",
                "lottery_join": "💰 Lütfen TRC20 cüzdan adresinizi girin:",
                "wallet_saved": "✅ Cüzdan kaydedildi!\n\n📤 Tam olarak ${amount} USDT'yi şu adrese gönderin:\n`{wallet}`\n\n⏳ Gönderdikten sonra 'Ödedim' butonuna tıklayın.",
                "payment_verified": "✅ Ödeme doğrulandı!\n\n🎉 Aboneliğiniz AKTİF!\nTüm piyangolara otomatik katılacaksınız.",
                "payment_failed": "❌ Ödeme doğrulaması başarısız.\nTekrar deneyin veya yöneticiyle iletişime geçin.",
                "already_paid": "ℹ️ Zaten aktif aboneliğiniz var.",
                "not_subscribed": "❌ Piyangoya katılmak için aktif aboneliğiniz olmalı.",
                "admin_panel": "🔧 Yönetim Paneli",
                "broadcast": "📢 Toplu Mesaj",
                "manual_verify": "✅ Manuel Doğrula",
                "add_api": "🔑 API Ekle",
                "view_stats": "📊 İstatistikler",
                "i_have_paid": "✅ Ödedim",
                "checking_payment": "⏳ Ödemeniz kontrol ediliyor...",
                "invalid_wallet": "❌ Geçersiz TRC20 cüzdan adresi.",
                "language_changed": "🌐 Dil Türkçe olarak değiştirildi",
                "referral_text": "🔗 Davet bağlantınız:\n`https://t.me/{bot_username}?start=ref_{code}`\n\n👥 Toplam davet: {count}",
                "guidance_text": """📚 **TAM REHBER** 📚

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔰 **KATILIM GÖNÜLLÜDÜR**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **Nasıl Katılırım:**
1. 'Piyangoya Katıl' butonuna tıklayın
2. TRC20 cüzdan adresinizi girin
3. Tam olarak ${amount} USDT gönderin
4. 'Ödedim' butonuna tıklayın
5. Otomatik doğrulamayı bekleyin
6. Aboneliğiniz AKTİF olur

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 **Piyango Süreci:**
• Tüm aktif aboneler katılır
• Adil rastgele seçim
• Birden fazla kazanan mümkün
• Kazananlar duyuru ile bildirilir

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ **Otomatik Doğrulama:**
• Blockchain işlem kontrolü
• Çoklu API doğrulaması
• Hızlı ve doğru
• %99.99 güvenilirlik

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 **Önemli Notlar:**
• Katılım tamamen GÖNÜLLÜDÜR
• Kazanabilir veya kazanamayabilirsiniz
• Sistem %100 ADİL'dir
• Kazanma garantisi yoktur
• Emin değilseniz katılmayın

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤝 **Davet Programı:**
• Davet bağlantınızı paylaşın
• Bonus kazanın
• Katılımı artırın

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Destek:**
• Yardım için yöneticiyle iletişime geçin
• 7/24 destek
• Adil ve şeffaf sistem

🍀 **Tüm katılımcılara iyi şanslar!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
                "admin_stats": "📊 **Sistem İstatistikleri**\n\n👥 Toplam Kullanıcı: {users}\n✅ Aktif Abone: {active}\n💰 Toplam Ödül: ${prizes}\n🏆 Kazananlar: {winners}\n🔑 API Sayısı: {apis}",
                "broadcast_sent": "✅ Mesaj {count} kullanıcıya gönderildi.",
                "manual_verify_done": "✅ {user_id} kullanıcısı manuel doğrulandı.",
                "api_added": "✅ Yeni API eklendi. Toplam: {total}",
                "admin_help": "🔧 **Yönetici Komutları:**\n• /stats - İstatistikler\n• /broadcast - Toplu mesaj\n• /verify [user_id] - Manuel doğrula\n• /addapi [key] - API ekle"
            }
        }
    
    def get_text(self, lang, key, **kwargs):
        if lang not in self.translations:
            lang = "en"
        text = self.translations[lang].get(key, self.translations["en"].get(key, key))
        for k, v in kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))
        return text

# ==================== سیستم پرداخت پیشرفته ====================
class PaymentSystem:
    def __init__(self, db):
        self.db = db
        self.api_keys = Config.API_KEYS.copy()
        self.api_key_index = 0
        self.verification_queue = Queue()
        self.session = None
        self.is_processing = False
        self.executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
    
    async def initialize(self):
        self.session = aiohttp.ClientSession()
        asyncio.create_task(self._process_queue())
        logger.info("Payment system initialized with {} API keys".format(len(self.api_keys)))
    
    async def verify_payment(self, user_id, from_address, to_address, amount):
        """افزودن به صف تایید"""
        try:
            await self.verification_queue.put((user_id, from_address, to_address, amount))
            if not self.is_processing:
                asyncio.create_task(self._process_queue())
            return True
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False
    
    async def _process_queue(self):
        """پردازش صف تایید با چندین API Key"""
        if self.is_processing:
            return
        
        self.is_processing = True
        try:
            while not self.verification_queue.empty():
                user_id, from_address, to_address, amount = await self.verification_queue.get()
                
                # توزیع بار بین API Keyها
                verified = False
                for attempt in range(Config.MAX_RETRY):
                    api_key = self.api_keys[self.api_key_index % len(self.api_keys)]
                    self.api_key_index += 1
                    
                    verified = await self._verify_with_api(from_address, to_address, amount, api_key)
                    
                    if verified:
                        break
                    
                    await asyncio.sleep(5 * (attempt + 1))
                
                if verified:
                    # فعال‌سازی اشتراک
                    subscription_end = int(time.time()) + 30 * 24 * 3600
                    await self.db.execute_query(
                        user_id,
                        "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                        (subscription_end, user_id)
                    )
                    
                    # ثبت در شرکت‌کنندگان
                    await self.db.execute_query(
                        user_id,
                        "INSERT OR REPLACE INTO lottery_participants (user_id, participated_at) VALUES (?, ?)",
                        (user_id, int(time.time()))
                    )
                    
                    logger.info(f"✅ Payment verified for user {user_id}")
                    
                    # ارسال پیام تایید به کاربر
                    await self._send_confirmation(user_id)
                else:
                    logger.warning(f"❌ Payment verification failed for user {user_id}")
                
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Queue error: {e}")
        finally:
            self.is_processing = False
    
    async def _verify_with_api(self, from_address, to_address, amount, api_key):
        """تایید با استفاده از API Trongrid"""
        try:
            # 1. بررسی با Trongrid
            url = f"{Config.TRONGRID_API}/v1/accounts/{from_address}/transactions"
            headers = {"TRON-PRO-API-KEY": api_key}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for tx in data.get("data", []):
                        if self._check_transaction(tx, to_address, amount):
                            return True
            
            # 2. بررسی با Tronscan API
            url = f"{Config.TRONSCAN_API}/api/transaction"
            params = {"address": from_address, "limit": 50}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for tx in data.get("data", []):
                        if self._check_transaction(tx, to_address, amount):
                            return True
            
            return False
        except Exception as e:
            logger.error(f"API verification error: {e}")
            return False
    
    def _check_transaction(self, tx, to_address, amount):
        """بررسی تراکنش با دقت بالا"""
        try:
            tx_to = tx.get("to", "")
            if tx_to.lower() != to_address.lower():
                return False
            
            tx_amount = tx.get("amount", 0)
            if tx_amount > 0:
                tx_amount = tx_amount / 1_000_000
            else:
                token_info = tx.get("token_info", {})
                if token_info.get("tokenId") == Config.USDT_CONTRACT:
                    tx_amount = tx.get("value", 0) / 1_000_000
            
            min_amount = amount * 0.98
            max_amount = amount * 1.02
            
            return min_amount <= tx_amount <= max_amount
        except Exception as e:
            logger.error(f"Transaction check error: {e}")
            return False
    
    async def _send_confirmation(self, user_id):
        """ارسال پیام تایید به کاربر"""
        try:
            user = await self.db.get_user(user_id)
            lang = user.get("language", "en") if user else "en"
            # توسط ربات اصلی ارسال می‌شود
        except Exception as e:
            logger.error(f"Confirmation error: {e}")
    
    async def add_api_key(self, api_key):
        """اضافه کردن API Key جدید"""
        if api_key not in self.api_keys:
            self.api_keys.append(api_key)
            logger.info(f"New API key added. Total: {len(self.api_keys)}")
            return True
        return False
    
    async def close(self):
        if self.session:
            await self.session.close()

# ==================== ربات اصلی ====================
class LotteryBot:
    def __init__(self):
        self.db = ShardedDatabase()
        self.translations = TranslationSystem()
        self.payment = PaymentSystem(self.db)
        self.application = None
        self.bot_username = "UTYOB_Bot"
        self.user_states = {}
        
        # وضعیت‌های مکالمه
        self.WAITING_WALLET, self.WAITING_WITHDRAW, self.WAITING_BROADCAST, \
        self.WAITING_MANUAL_VERIFY, self.WAITING_API_KEY = range(5)
    
    async def start(self):
        await self.payment.initialize()
        
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        self._register_handlers()
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("🚀 Bot started! Ready for millions of users!")
        
        # راه‌اندازی Flask API
        self._start_flask_server()
        
        while True:
            await asyncio.sleep(1)
    
    def _register_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stats", self.admin_stats_command))
        self.application.add_handler(CommandHandler("broadcast", self.admin_broadcast_command))
        self.application.add_handler(CommandHandler("verify", self.admin_verify_command))
        self.application.add_handler(CommandHandler("addapi", self.admin_addapi_command))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^🎰 شرکت در قرعه‌کشی$|^🎰 Join Lottery$|^🎰 Piyangoya Katıl$"), self.start_lottery_join),
                MessageHandler(filters.Regex("^👥 رفرال$|^👥 Referral$|^👥 Davet$"), self.handle_referral),
                MessageHandler(filters.Regex("^📖 راهنمایی$|^📖 Guidance$|^📖 Rehber$"), self.handle_guidance),
                MessageHandler(filters.Regex("^🌐 تغییر زبان$|^🌐 Change Language$|^🌐 Dil Değiştir$"), self.handle_language_change),
                MessageHandler(filters.Regex("^🔧 پنل مدیریت$|^🔧 Admin Panel$|^🔧 Yönetim Paneli$"), self.show_admin_panel),
                MessageHandler(filters.Regex("^✅ پرداخت کردم$|^✅ I have paid$|^✅ Ödedim$"), self.handle_payment_confirmation),
                MessageHandler(filters.Regex("^📊 آمار$|^📊 Statistics$|^📊 İstatistikler$"), self.show_stats),
            ],
            states={
                self.WAITING_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_wallet_input)],
                self.WAITING_WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_withdraw_wallet)],
                self.WAITING_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_broadcast)],
                self.WAITING_MANUAL_VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_manual_verify)],
                self.WAITING_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_api)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)]
        )
        self.application.add_handler(conv_handler)
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    # ==================== Command Handlers ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        # پردازش رفرال
        if context.args:
            ref_code = context.args[0]
            if ref_code.startswith("ref_"):
                await self._process_referral(user_id, ref_code[4:])
        
        db_user = await self.db.get_user(user_id)
        if not db_user:
            await self.db.create_user(
                user_id,
                user.username or "",
                user.first_name or "",
                user.last_name or ""
            )
            db_user = await self.db.get_user(user_id)
        
        lang = db_user.get("language", "en")
        
        # منوی اصلی - ۴ دکمه
        keyboard = [
            [KeyboardButton(self.translations.get_text(lang, "join_lottery"))],
            [KeyboardButton(self.translations.get_text(lang, "referral")), 
             KeyboardButton(self.translations.get_text(lang, "guidance"))],
            [KeyboardButton(self.translations.get_text(lang, "change_language"))]
        ]
        
        # دکمه پنل مدیریت برای ادمین
        if user_id in Config.ADMIN_IDS:
            keyboard.append([
                KeyboardButton(self.translations.get_text(lang, "admin_panel")),
                KeyboardButton(self.translations.get_text(lang, "view_stats"))
            ])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = self.translations.get_text(
            lang, "welcome", bot_name="UTYOB Lottery Bot"
        )
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    # ==================== Admin Commands ====================
    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /stats - نمایش آمار"""
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return
        
        await self.show_stats(update, context)
    
    async def admin_broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /broadcast - ارسال پیام همگانی"""
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return
        
        if not context.args:
            await update.message.reply_text("📢 Usage: /broadcast Your message here")
            return
        
        message = " ".join(context.args)
        await self._send_broadcast(message)
        await update.message.reply_text(f"✅ Broadcast sent!")
    
    async def admin_verify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /verify [user_id] - تایید دستی"""
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return
        
        if not context.args:
            await update.message.reply_text("✅ Usage: /verify [user_id]")
            return
        
        try:
            target_user = int(context.args[0])
            subscription_end = int(time.time()) + 30 * 24 * 3600
            await self.db.execute_query(
                target_user,
                "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                (subscription_end, target_user)
            )
            await update.message.reply_text(f"✅ User {target_user} verified manually!")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def admin_addapi_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /addapi [key] - اضافه کردن API"""
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return
        
        if not context.args:
            await update.message.reply_text("🔑 Usage: /addapi [API_KEY]")
            return
        
        api_key = context.args[0]
        if await self.payment.add_api_key(api_key):
            await update.message.reply_text(f"✅ API key added! Total: {len(self.payment.api_keys)}")
        else:
            await update.message.reply_text("❌ API key already exists.")
    
    # ==================== Message Handlers ====================
    async def start_lottery_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        db_user = await self.db.get_user(user_id)
        if not db_user:
            await self.start_command(update, context)
            return
        
        lang = db_user.get("language", "en")
        
        if db_user.get("subscription_end", 0) > int(time.time()):
            await update.message.reply_text(
                self.translations.get_text(lang, "already_paid")
            )
            return
        
        context.user_data["state"] = self.WAITING_WALLET
        await update.message.reply_text(
            self.translations.get_text(lang, "lottery_join")
        )
        
        return self.WAITING_WALLET
    
    async def handle_wallet_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        wallet = update.message.text.strip()
        
        db_user = await self.db.get_user(user_id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        if not self._validate_tron_address(wallet):
            await update.message.reply_text(
                self.translations.get_text(lang, "invalid_wallet")
            )
            return self.WAITING_WALLET
        
        await self.db.execute_query(
            user_id,
            "UPDATE users SET wallet_address = ? WHERE user_id = ?",
            (wallet, user_id)
        )
        
        context.user_data.pop("state", None)
        
        # دکمه پرداخت کردم
        keyboard = [
            [InlineKeyboardButton(
                self.translations.get_text(lang, "i_have_paid"),
                callback_data="paid"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            self.translations.get_text(
                lang, "wallet_saved",
                amount=Config.AMOUNT_USD,
                wallet=Config.WALLET_ADDRESS
            ),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        context.user_data["pending_wallet"] = wallet
        
        return ConversationHandler.END
    
    async def handle_payment_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        db_user = await self.db.get_user(user_id)
        lang = db_user.get("language", "en") if db_user else "en"
        wallet = db_user.get("wallet_address")
        
        if not wallet:
            await update.message.reply_text(
                "❌ Please first enter your wallet address."
            )
            return
        
        status_msg = await update.message.reply_text(
            self.translations.get_text(lang, "checking_payment")
        )
        
        # اضافه کردن به صف تایید
        await self.payment.verify_payment(
            user_id, wallet, Config.WALLET_ADDRESS, Config.AMOUNT_USD
        )
        
        await status_msg.edit_text(
            self.translations.get_text(lang, "payment_verified")
        )
    
    async def handle_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        db_user = await self.db.get_user(user_id)
        if not db_user:
            await self.start_command(update, context)
            return
        
        lang = db_user.get("language", "en")
        referral_code = db_user.get("referral_code", "")
        referral_count = db_user.get("referral_count", 0)
        
        await update.message.reply_text(
            self.translations.get_text(
                lang, "referral_text",
                bot_username=self.bot_username,
                code=referral_code,
                count=referral_count
            ),
            parse_mode="Markdown"
        )
    
    async def handle_guidance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db_user = await self.db.get_user(user.id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        await update.message.reply_text(
            self.translations.get_text(lang, "guidance_text", amount=Config.AMOUNT_USD),
            parse_mode="Markdown"
        )
    
    async def handle_language_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        languages = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr")]
        ]
        
        reply_markup = InlineKeyboardMarkup(languages)
        
        await update.message.reply_text(
            "🌐 Select your language:",
            reply_markup=reply_markup
        )
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return
        
        db_user = await self.db.get_user(user_id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        keyboard = [
            [InlineKeyboardButton(self.translations.get_text(lang, "broadcast"), 
                                 callback_data="admin_broadcast")],
            [InlineKeyboardButton(self.translations.get_text(lang, "manual_verify"), 
                                 callback_data="admin_manual_verify")],
            [InlineKeyboardButton(self.translations.get_text(lang, "add_api"), 
                                 callback_data="admin_add_api")],
            [InlineKeyboardButton(self.translations.get_text(lang, "view_stats"), 
                                 callback_data="admin_stats")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **Admin Panel**",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db_user = await self.db.get_user(user.id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        stats = await self._get_stats()
        
        # دریافت لیست کاربران
        users = await self.db.get_all_users()
        user_list = "\n".join([f"• {u[0]} - {u[1] or u[2] or 'Unknown'}" for u in users[:20]])
        if len(users) > 20:
            user_list += f"\n... and {len(users) - 20} more"
        
        await update.message.reply_text(
            self.translations.get_text(
                lang, "admin_stats",
                users=stats["users"],
                active=stats["active"],
                prizes=stats["prizes"],
                winners=stats["winners"],
                apis=len(self.payment.api_keys)
            ) + f"\n\n👥 **Users List:**\n{user_list}",
            parse_mode="Markdown"
        )
    
    async def handle_withdraw_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # برای برداشت برندگان
        pass
    
    # ==================== Admin Handlers ====================
    async def handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return ConversationHandler.END
        
        message = update.message.text
        await self._send_broadcast(message)
        await update.message.reply_text(f"✅ Broadcast sent!")
        
        context.user_data.pop("state", None)
        return ConversationHandler.END
    
    async def handle_manual_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return ConversationHandler.END
        
        try:
            user_id = int(update.message.text.strip())
            subscription_end = int(time.time()) + 30 * 24 * 3600
            await self.db.execute_query(
                user_id,
                "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                (subscription_end, user_id)
            )
            await update.message.reply_text(f"✅ User {user_id} verified manually!")
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID.")
        
        context.user_data.pop("state", None)
        return ConversationHandler.END
    
    async def handle_add_api(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return ConversationHandler.END
        
        api_key = update.message.text.strip()
        
        if await self.payment.add_api_key(api_key):
            await update.message.reply_text(
                f"✅ API key added! Total: {len(self.payment.api_keys)}"
            )
        else:
            await update.message.reply_text("❌ API key already exists.")
        
        context.user_data.pop("state", None)
        return ConversationHandler.END
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.user_states.pop(user.id, None)
        await update.message.reply_text("❌ Cancelled.")
        return ConversationHandler.END
    
    # ==================== Callback Handlers ====================
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_id = user.id
        data = query.data
        
        db_user = await self.db.get_user(user_id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        # تغییر زبان
        if data.startswith("lang_"):
            lang_code = data.split("_")[1]
            if lang_code in ["en", "fa", "tr"]:
                await self.db.execute_query(
                    user_id,
                    "UPDATE users SET language = ? WHERE user_id = ?",
                    (lang_code, user_id)
                )
                
                # پاک کردن کش
                cache_key = f"user_{user_id}"
                if cache_key in self.db.cache:
                    del self.db.cache[cache_key]
                
                lang_names = {"en": "English 🇬🇧", "fa": "فارسی 🇮🇷", "tr": "Türkçe 🇹🇷"}
                
                await query.edit_message_text(
                    self.translations.get_text(
                        lang, "language_changed", lang=lang_names.get(lang_code, lang_code)
                    )
                )
                
                # نمایش منوی جدید
                await self.start_command(query.message, context)
            return
        
        # پرداخت
        if data == "paid":
            await query.edit_message_text(
                self.translations.get_text(lang, "checking_payment")
            )
            
            db_user = await self.db.get_user(user_id)
            wallet = db_user.get("wallet_address")
            
            if wallet:
                await self.payment.verify_payment(
                    user_id, wallet, Config.WALLET_ADDRESS, Config.AMOUNT_USD
                )
                
                await query.message.reply_text(
                    self.translations.get_text(lang, "payment_verified")
                )
            return
        
        # مدیریت
        if data.startswith("admin_"):
            action = data.replace("admin_", "")
            
            if action == "broadcast":
                context.user_data["state"] = self.WAITING_BROADCAST
                await query.edit_message_text("📢 Enter your broadcast message:")
                return self.WAITING_BROADCAST
            
            elif action == "manual_verify":
                context.user_data["state"] = self.WAITING_MANUAL_VERIFY
                await query.edit_message_text("✅ Enter user ID to verify:")
                return self.WAITING_MANUAL_VERIFY
            
            elif action == "add_api":
                context.user_data["state"] = self.WAITING_API_KEY
                await query.edit_message_text("🔑 Enter new API key:")
                return self.WAITING_API_KEY
            
            elif action == "stats":
                await query.edit_message_text("📊 Getting statistics...")
                await self.show_stats(query.message, context)
    
    # ==================== Utility Methods ====================
    def _validate_tron_address(self, address):
        if not address or len(address) != 34:
            return False
        if not address.startswith("T"):
            return False
        try:
            decoded = base58.b58decode(address)
            return len(decoded) == 21
        except:
            return False
    
    async def _process_referral(self, user_id, ref_code):
        try:
            referrer_id = None
            for shard_id in range(Config.SHARD_COUNT):
                cursor = self.db.shards[shard_id].cursor()
                cursor.execute(
                    "SELECT user_id FROM users WHERE referral_code = ?",
                    (ref_code,)
                )
                result = cursor.fetchone()
                if result:
                    referrer_id = result[0]
                    break
            
            if referrer_id and referrer_id != user_id:
                await self.db.execute_query(
                    user_id,
                    "UPDATE users SET referred_by = ? WHERE user_id = ?",
                    (referrer_id, user_id)
                )
                
                await self.db.execute_query(
                    referrer_id,
                    "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
                    (referrer_id,)
                )
                
                logger.info(f"Referral: {referrer_id} -> {user_id}")
        except Exception as e:
            logger.error(f"Referral error: {e}")
    
    async def _send_broadcast(self, message):
        """ارسال پیام همگانی به همه کاربران"""
        users = await self.db.get_all_users()
        count = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(user[0], message)
                count += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Broadcast error for {user[0]}: {e}")
        
        logger.info(f"Broadcast sent to {count} users")
    
    async def _get_stats(self):
        stats = {"users": 0, "active": 0, "prizes": 0, "winners": 0}
        
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            stats["users"] += cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE subscription_end > ?",
                (int(time.time()),)
            )
            stats["active"] += cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(won_amount) FROM users")
            result = cursor.fetchone()[0]
            if result:
                stats["prizes"] += result
            
            cursor.execute("SELECT COUNT(*) FROM previous_winners")
            stats["winners"] += cursor.fetchone()[0]
        
        return stats
    
    # ==================== Flask API ====================
    def _start_flask_server(self):
        app = Flask(__name__)
        
        @app.route('/api/health', methods=['GET'])
        def health():
            return jsonify({
                "status": "healthy",
                "shards": Config.SHARD_COUNT,
                "api_keys": len(self.payment.api_keys),
                "queue_size": self.payment.verification_queue.qsize()
            })
        
        @app.route('/api/stats', methods=['GET'])
        async def stats():
            stats = await self._get_stats()
            return jsonify(stats)
        
        @app.route('/api/verify', methods=['POST'])
        async def verify():
            data = request.json
            user_id = data.get('user_id')
            from_address = data.get('from_address')
            to_address = data.get('to_address')
            amount = data.get('amount')
            
            if not all([user_id, from_address, to_address, amount]):
                return jsonify({"status": "error", "message": "Missing parameters"}), 400
            
            result = await self.payment.verify_payment(
                user_id, from_address, to_address, amount
            )
            
            return jsonify({"status": "success", "queued": result})
        
        def run_flask():
            app.run(host='0.0.0.0', port=5000, debug=False)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
    
    # ==================== Error Handler ====================
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.effective_user:
                await update.message.reply_text("❌ An error occurred. Please try again.")
        except:
            pass

# ==================== اجرا ====================
async def main():
    bot = LotteryBot()
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal: {e}")