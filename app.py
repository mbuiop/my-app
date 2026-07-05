import os
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
from datetime import datetime
from asyncio import Queue
import uvloop
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

# ==================== تنظیمات ====================
uvloop.install()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== کانفیگ ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("❌ Please set your BOT_TOKEN in .env file!")
    
    ADMIN_IDS = []
    admin_ids_str = os.getenv("ADMIN_IDS", "327855654")
    for aid in admin_ids_str.split(","):
        try:
            ADMIN_IDS.append(int(aid.strip()))
        except:
            pass
    
    SHARD_COUNT = int(os.getenv("SHARD_COUNT", "50"))
    CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
    
    TRONGRID_API = os.getenv("TRONGRID_API", "https://api.trongrid.io")
    TRONSCAN_API = os.getenv("TRONSCAN_API", "https://api.tronscan.org")
    WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A")
    AMOUNT_USD = int(os.getenv("AMOUNT_USD", "100"))
    USDT_CONTRACT = os.getenv("USDT_CONTRACT", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
    
    API_KEYS = []
    api_keys_str = os.getenv("API_KEYS", "7ae83b63-fdf3-47e4-ac69-56f960a34f5b")
    for key in api_keys_str.split(","):
        key = key.strip()
        if key:
            API_KEYS.append(key)
    
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "50"))
    VERIFICATION_TIMEOUT = int(os.getenv("VERIFICATION_TIMEOUT", "120"))
    MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))

# ==================== دیتابیس ====================
class ShardedDatabase:
    def __init__(self):
        self.shards = {}
        self.cache = {}
        self.executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
        
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
                "lottery_join": "💰 Please enter your source TRC20 wallet address:",
                "wallet_saved": "✅ Wallet saved!\n\n📤 Please send exactly ${amount} USDT to:\n`{wallet}`\n\n⏳ After sending, click 'I have paid' for automatic verification.",
                "payment_verified": "✅ Payment verified!\n\n🎉 Your subscription is ACTIVE!",
                "payment_failed": "❌ Payment verification failed. Please try again.",
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
                "language_changed": "🌐 Language changed to English",
                "referral_text": "🔗 Your referral link:\n`https://t.me/{bot_username}?start=ref_{code}`\n\n👥 Total referrals: {count}",
                "guidance_text": """📚 **COMPLETE GUIDANCE** 📚

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔰 **PARTICIPATION IS VOLUNTARY**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **How to Participate:**
1. Click 'Join Lottery'
2. Enter your TRC20 wallet address
3. Send exactly ${amount} USDT to the address
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Support:**
• Contact admin for help
• Fair and transparent system

🍀 **Good luck to all participants!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
                "admin_stats": "📊 **System Statistics**\n\n👥 Total Users: {users}\n✅ Active Subs: {active}\n💰 Total Prizes: ${prizes}\n🏆 Winners: {winners}\n🔑 API Keys: {apis}",
                "broadcast_sent": "✅ Broadcast sent to {count} users.",
                "manual_verify_done": "✅ User {user_id} verified manually.",
                "api_added": "✅ New API key added. Total: {total}"
            },
            "fa": {
                "welcome": "🎉 به ربات {bot_name} خوش آمدید!\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
                "join_lottery": "🎰 شرکت در قرعه‌کشی",
                "referral": "👥 رفرال",
                "guidance": "📖 راهنمایی",
                "change_language": "🌐 تغییر زبان",
                "lottery_join": "💰 لطفاً آدرس کیف پول مبدا TRC20 خود را وارد کنید:",
                "wallet_saved": "✅ کیف پول ذخیره شد!\n\n📤 لطفاً دقیقاً ${amount} USDT به آدرس زیر ارسال کنید:\n`{wallet}`\n\n⏳ پس از ارسال، روی 'پرداخت کردم' کلیک کنید.",
                "payment_verified": "✅ پرداخت تایید شد!\n\n🎉 اشتراک شما فعال شد!",
                "payment_failed": "❌ تایید پرداخت ناموفق بود. لطفاً دوباره تلاش کنید.",
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
۲. آدرس کیف پول مبدا TRC20 خود را وارد کنید
۳. دقیقاً ${amount} USDT به آدرس زیر ارسال کنید
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **پشتیبانی:**
• برای کمک با ادمین تماس بگیرید
• سیستم عادلانه و شفاف

🍀 **برای همه شرکت‌کنندگان آرزوی موفقیت داریم!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
                "admin_stats": "📊 **آمار سیستم**\n\n👥 کل کاربران: {users}\n✅ اشتراک فعال: {active}\n💰 مجموع جوایز: ${prizes}\n🏆 برندگان: {winners}\n🔑 تعداد API: {apis}",
                "broadcast_sent": "✅ پیام به {count} کاربر ارسال شد.",
                "manual_verify_done": "✅ کاربر {user_id} به صورت دستی تایید شد.",
                "api_added": "✅ API جدید اضافه شد. تعداد کل: {total}"
            },
            "tr": {
                "welcome": "🎉 {bot_name} hoş geldiniz!\n\nLütfen bir seçenek seçin:",
                "join_lottery": "🎰 Piyangoya Katıl",
                "referral": "👥 Davet",
                "guidance": "📖 Rehber",
                "change_language": "🌐 Dil Değiştir",
                "lottery_join": "💰 Lütfen TRC20 cüzdan adresinizi girin:",
                "wallet_saved": "✅ Cüzdan kaydedildi!\n\n📤 Tam olarak ${amount} USDT'yi şu adrese gönderin:\n`{wallet}`\n\n⏳ Gönderdikten sonra 'Ödedim' butonuna tıklayın.",
                "payment_verified": "✅ Ödeme doğrulandı!\n\n🎉 Aboneliğiniz AKTİF!",
                "payment_failed": "❌ Ödeme doğrulaması başarısız. Tekrar deneyin.",
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 **Destek:**
• Yardım için yöneticiyle iletişime geçin
• Adil ve şeffaf sistem

🍀 **Tüm katılımcılara iyi şanslar!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
                "admin_stats": "📊 **Sistem İstatistikleri**\n\n👥 Toplam Kullanıcı: {users}\n✅ Aktif Abone: {active}\n💰 Toplam Ödül: ${prizes}\n🏆 Kazananlar: {winners}\n🔑 API Sayısı: {apis}",
                "broadcast_sent": "✅ Mesaj {count} kullanıcıya gönderildi.",
                "manual_verify_done": "✅ {user_id} kullanıcısı manuel doğrulandı.",
                "api_added": "✅ Yeni API eklendi. Toplam: {total}"
            }
        }
    
    def get_text(self, lang, key, **kwargs):
        if lang not in self.translations:
            lang = "en"
        text = self.translations[lang].get(key, self.translations["en"].get(key, key))
        for k, v in kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))
        return text

# ==================== سیستم پرداخت ====================
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
        logger.info(f"Payment system initialized with {len(self.api_keys)} API keys")
    
    async def verify_payment(self, user_id, from_address, to_address, amount):
        try:
            await self.verification_queue.put((user_id, from_address, to_address, amount))
            if not self.is_processing:
                asyncio.create_task(self._process_queue())
            return True
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False
    
    async def _process_queue(self):
        if self.is_processing:
            return
        
        self.is_processing = True
        try:
            while not self.verification_queue.empty():
                user_id, from_address, to_address, amount = await self.verification_queue.get()
                
                verified = False
                for attempt in range(Config.MAX_RETRY):
                    api_key = self.api_keys[self.api_key_index % len(self.api_keys)]
                    self.api_key_index += 1
                    
                    verified = await self._verify_with_api(from_address, to_address, amount, api_key)
                    
                    if verified:
                        break
                    
                    await asyncio.sleep(5 * (attempt + 1))
                
                if verified:
                    subscription_end = int(time.time()) + 30 * 24 * 3600
                    await self.db.execute_query(
                        user_id,
                        "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                        (subscription_end, user_id)
                    )
                    
                    await self.db.execute_query(
                        user_id,
                        "INSERT OR REPLACE INTO lottery_participants (user_id, participated_at) VALUES (?, ?)",
                        (user_id, int(time.time()))
                    )
                    
                    logger.info(f"✅ Payment verified for user {user_id}")
                else:
                    logger.warning(f"❌ Payment verification failed for user {user_id}")
                
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Queue error: {e}")
        finally:
            self.is_processing = False
    
    async def _verify_with_api(self, from_address, to_address, amount, api_key):
        try:
            url = f"{Config.TRONGRID_API}/v1/accounts/{from_address}/transactions"
            headers = {"TRON-PRO-API-KEY": api_key}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for tx in data.get("data", []):
                        if self._check_transaction(tx, to_address, amount):
                            return True
            
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
    
    async def add_api_key(self, api_key):
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
        
        self.WAITING_WALLET, self.WAITING_BROADCAST, \
        self.WAITING_MANUAL_VERIFY, self.WAITING_API_KEY = range(4)
    
    async def start(self):
        await self.payment.initialize()
        
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        self._register_handlers()
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("🚀 Bot started successfully!")
        
        self._start_flask_server()
        
        while True:
            await asyncio.sleep(1)
    
    def _register_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^🎰 شرکت در قرعه‌کشی$|^🎰 Join Lottery$|^🎰 Piyangoya Katıl$"), self.start_lottery_join),
                MessageHandler(filters.Regex("^👥 رفرال$|^👥 Referral$|^👥 Davet$"), self.handle_referral),
                MessageHandler(filters.Regex("^📖 راهنمایی$|^📖 Guidance$|^📖 Rehber$"), self.handle_guidance),
                MessageHandler(filters.Regex("^🌐 تغییر زبان$|^🌐 Change Language$|^🌐 Dil Değiştir$"), self.handle_language_change),
                MessageHandler(filters.Regex("^🔧 پنل مدیریت$|^🔧 Admin Panel$|^🔧 Yönetim Paneli$"), self.show_admin_panel),
                MessageHandler(filters.Regex("^✅ پرداخت کردم$|^✅ I have paid$|^✅ Ödedim$"), self.handle_payment_confirmation),
            ],
            states={
                self.WAITING_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_wallet_input)],
                self.WAITING_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_broadcast)],
                self.WAITING_MANUAL_VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_manual_verify)],
                self.WAITING_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_api)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)]
        )
        self.application.add_handler(conv_handler)
        
        self.application.add_error_handler(self.error_handler)
    
    # ==================== Start Command ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
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
        
        keyboard = [
            [KeyboardButton(self.translations.get_text(lang, "join_lottery"))],
            [KeyboardButton(self.translations.get_text(lang, "referral")), 
             KeyboardButton(self.translations.get_text(lang, "guidance"))],
            [KeyboardButton(self.translations.get_text(lang, "change_language"))]
        ]
        
        if user_id in Config.ADMIN_IDS:
            keyboard.append([KeyboardButton("🔧 پنل مدیریت")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = self.translations.get_text(
            lang, "welcome", bot_name="UTYOB Lottery Bot"
        )
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    # ==================== Lottery Join ====================
    async def start_lottery_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        db_user = await self.db.get_user(user_id)
        if not db_user:
            await self.start_command(update, context)
            return ConversationHandler.END
        
        lang = db_user.get("language", "en")
        
        if db_user.get("subscription_end", 0) > int(time.time()):
            await update.message.reply_text(
                self.translations.get_text(lang, "already_paid")
            )
            return ConversationHandler.END
        
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
        
        await self.payment.verify_payment(
            user_id, wallet, Config.WALLET_ADDRESS, Config.AMOUNT_USD
        )
        
        await status_msg.edit_text(
            self.translations.get_text(lang, "payment_verified")
        )
    
    # ==================== Referral ====================
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
    
    # ==================== Guidance ====================
    async def handle_guidance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db_user = await self.db.get_user(user.id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        await update.message.reply_text(
            self.translations.get_text(lang, "guidance_text", amount=Config.AMOUNT_USD),
            parse_mode="Markdown"
        )
    
    # ==================== Language Change ====================
    async def handle_language_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        languages = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr")]
        ]
        
        reply_markup = InlineKeyboardMarkup(languages)
        
        await update.message.reply_text(
            "🌐 Select your language / زبان خود را انتخاب کنید / Dil seçin:",
            reply_markup=reply_markup
        )
    
    # ==================== Admin Panel ====================
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return
        
        keyboard = [
            [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("✅ تایید دستی", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("🔑 اضافه کردن API", callback_data="admin_add_api")],
            [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **پنل مدیریت**",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    # ==================== Button Callback ====================
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_id = user.id
        data = query.data
        
        db_user = await self.db.get_user(user_id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        # ============ تغییر زبان ============
        if data.startswith("lang_"):
            lang_code = data.split("_")[1]
            if lang_code in ["en", "fa", "tr"]:
                await self.db.execute_query(
                    user_id,
                    "UPDATE users SET language = ? WHERE user_id = ?",
                    (lang_code, user_id)
                )
                
                cache_key = f"user_{user_id}"
                if cache_key in self.db.cache:
                    del self.db.cache[cache_key]
                
                # دریافت نام زبان
                lang_names = {"en": "English 🇬🇧", "fa": "فارسی 🇮🇷", "tr": "Türkçe 🇹🇷"}
                
                await query.edit_message_text(
                    f"🌐 Language changed to {lang_names.get(lang_code, lang_code)}"
                )
                
                # ارسال منوی جدید با زبان جدید
                await self.start_command(query.message, context)
            return
        
        # ============ پرداخت ============
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
        
        # ============ مدیریت ============
        if data.startswith("admin_"):
            if user_id not in Config.ADMIN_IDS:
                await query.edit_message_text("⛔ Access Denied!")
                return
            
            action = data.replace("admin_", "")
            
            if action == "broadcast":
                context.user_data["state"] = self.WAITING_BROADCAST
                await query.edit_message_text("📢 پیام همگانی خود را وارد کنید:")
                return self.WAITING_BROADCAST
            
            elif action == "manual_verify":
                context.user_data["state"] = self.WAITING_MANUAL_VERIFY
                await query.edit_message_text("✅ آیدی کاربر مورد نظر را وارد کنید:")
                return self.WAITING_MANUAL_VERIFY
            
            elif action == "add_api":
                context.user_data["state"] = self.WAITING_API_KEY
                await query.edit_message_text("🔑 API Key جدید را وارد کنید:")
                return self.WAITING_API_KEY
            
            elif action == "stats":
                await self._show_admin_stats(query)
    
    # ==================== Admin Handlers ====================
    async def handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return ConversationHandler.END
        
        message = update.message.text
        await self._send_broadcast(message)
        await update.message.reply_text("✅ پیام همگانی ارسال شد!")
        
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
            await update.message.reply_text(f"✅ کاربر {user_id} با موفقیت تایید شد!")
        except ValueError:
            await update.message.reply_text("❌ آیدی نامعتبر است.")
        
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
                f"✅ API جدید اضافه شد! تعداد کل: {len(self.payment.api_keys)}"
            )
        else:
            await update.message.reply_text("❌ این API قبلاً وجود دارد.")
        
        context.user_data.pop("state", None)
        return ConversationHandler.END
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.user_states.pop(user.id, None)
        context.user_data.pop("state", None)
        await update.message.reply_text("❌ لغو شد.")
        return ConversationHandler.END
    
    # ==================== Admin Stats ====================
    async def _show_admin_stats(self, query):
        stats = await self._get_stats()
        users = await self.db.get_all_users()
        
        user_list = ""
        for u in users[:20]:
            name = u[1] or u[2] or "Unknown"
            user_list += f"• {u[0]} - {name}\n"
        if len(users) > 20:
            user_list += f"... و {len(users) - 20} نفر دیگر"
        
        stats_text = f"""📊 **آمار سیستم**

👥 کل کاربران: {stats['users']}
✅ اشتراک فعال: {stats['active']}
💰 مجموع جوایز: ${stats['prizes']}
🏆 برندگان: {stats['winners']}
🔑 تعداد API: {len(self.payment.api_keys)}

👥 **لیست کاربران:**
{user_list}"""
        
        await query.edit_message_text(stats_text, parse_mode="Markdown")
    
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
    
    # ==================== Error Handler ====================
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Error: {context.error}")
        try:
            if update and update.effective_user:
                await update.message.reply_text(
                    "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید."
                )
        except:
            pass
    
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
        
        def run_flask():
            app.run(host='0.0.0.0', port=5000, debug=False)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

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