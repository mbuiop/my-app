import asyncio
import json
import logging
import random
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3
import aiosqlite
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify
import threading
import base58
import psutil
import os
import sys
from collections import defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

# تنظیمات لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== کانفیگ سیستم ====================
class Config:
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    ADMIN_ID = ["YOUR_ADMIN_ID"]  # لیست ادمین‌ها
    DEFAULT_LANG = "en"
    SUPPORTED_LANGS = ["en", "fa", "tr"]
    TRONGRID_API = "https://api.trongrid.io"
    WALLET_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
    AMOUNT_USD = 100
    API_KEYS = ["7ae83b63-fdf3-47e4-ac69-56f960a34f5b"]
    MAX_SHARDS = 100
    SHARD_COUNT = 10  # تعداد شاردها
    
    # تنظیمات میکروسرویس‌ها
    MICROSERVICES = {
        "auth": {"port": 5001, "workers": 4},
        "payment": {"port": 5002, "workers": 4},
        "lottery": {"port": 5003, "workers": 4},
        "notification": {"port": 5004, "workers": 4}
    }

# ==================== سیستم دیتابیس شارد شده ====================
class ShardedDatabase:
    def __init__(self):
        self.shards = {}
        self.shard_count = Config.SHARD_COUNT
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.cache = {}
        self.cache_timeout = 300  # 5 دقیقه
        
        # ایجاد شاردها
        for i in range(self.shard_count):
            db_path = f"shard_{i}.db"
            self.shards[i] = sqlite3.connect(db_path, check_same_thread=False)
            self._init_shard(i)
    
    def _init_shard(self, shard_id):
        cursor = self.shards[shard_id].cursor()
        
        # جدول کاربران
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
                created_at INTEGER,
                language TEXT DEFAULT 'en',
                is_winner BOOLEAN DEFAULT 0,
                won_amount INTEGER DEFAULT 0,
                total_participations INTEGER DEFAULT 0
            )
        ''')
        
        # جدول تراکنش‌ها
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
                api_key_used TEXT
            )
        ''')
        
        # جدول قرعه‌کشی‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lotteries (
                lottery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER,
                winners_count INTEGER,
                prize_amount INTEGER,
                status TEXT,
                winner_ids TEXT,
                ended_at INTEGER
            )
        ''')
        
        # جدول شرکت‌کنندگان در قرعه‌کشی
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_participants (
                lottery_id INTEGER,
                user_id INTEGER,
                participated_at INTEGER,
                PRIMARY KEY (lottery_id, user_id)
            )
        ''')
        
        # جدول برندگان قبلی
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS previous_winners (
                user_id INTEGER PRIMARY KEY,
                last_win_time INTEGER,
                win_count INTEGER DEFAULT 1
            )
        ''')
        
        # ایندکس‌ها برای عملکرد بهتر
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_wallet ON users(wallet_address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_end)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_participants_lottery ON lottery_participants(lottery_id)')
        
        self.shards[shard_id].commit()
    
    def _get_shard(self, user_id: int) -> int:
        """تعیین شارد بر اساس user_id"""
        return user_id % self.shard_count
    
    async def execute_query(self, user_id: int, query: str, params: tuple = (), fetch: bool = False):
        """اجرای کوئری روی شارد مربوطه"""
        shard_id = self._get_shard(user_id)
        cursor = self.shards[shard_id].cursor()
        
        try:
            cursor.execute(query, params)
            if fetch:
                result = cursor.fetchall()
                return result
            self.shards[shard_id].commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Database error on shard {shard_id}: {e}")
            self.shards[shard_id].rollback()
            raise
    
    async def get_user(self, user_id: int):
        """دریافت اطلاعات کاربر"""
        cache_key = f"user_{user_id}"
        if cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_timeout:
                return data
        
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
                "created_at": result[0][8],
                "language": result[0][9] if len(result[0]) > 9 else "en",
                "is_winner": result[0][10] if len(result[0]) > 10 else False,
                "won_amount": result[0][11] if len(result[0]) > 11 else 0,
                "total_participations": result[0][12] if len(result[0]) > 12 else 0
            }
            self.cache[cache_key] = (time.time(), user_data)
            return user_data
        return None
    
    async def create_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        """ایجاد کاربر جدید"""
        referral_code = self._generate_referral_code(user_id)
        
        await self.execute_query(
            user_id,
            """INSERT INTO users 
               (user_id, username, first_name, last_name, referral_code, created_at, language) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, first_name, last_name, referral_code, int(time.time()), "en")
        )
        
        self.cache[f"user_{user_id}"] = (time.time(), {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "wallet_address": None,
            "subscription_end": 0,
            "referral_code": referral_code,
            "referred_by": None,
            "created_at": int(time.time()),
            "language": "en",
            "is_winner": False,
            "won_amount": 0,
            "total_participations": 0
        })
        
        return referral_code
    
    def _generate_referral_code(self, user_id: int) -> str:
        """تولید کد رفرال"""
        return base58.b58encode(hashlib.sha256(f"{user_id}{time.time()}".encode()).digest()[:8]).decode()

# ==================== سیستم ترجمه ====================
class TranslationSystem:
    def __init__(self):
        self.translations = {
            "en": {
                "welcome": "Welcome to {bot_name}! 🎉\nPlease select an option:",
                "join_lottery": "🎰 Join Lottery",
                "referral": "👥 Referral",
                "guidance": "📖 Guidance",
                "change_language": "🌐 Change Language",
                "lottery_join": "Please enter your source wallet address (TRC20):",
                "wallet_saved": "✅ Wallet address saved successfully!\nPlease send exactly $100 USDT to:\n`{wallet}`\n\nWe will automatically verify your payment.",
                "payment_verified": "✅ Payment verified! You are now registered for the lottery.\nGood luck! 🍀",
                "payment_failed": "❌ Payment verification failed. Please try again or contact support.",
                "already_paid": "You have already registered for the current lottery.",
                "not_subscribed": "❌ You need an active subscription to participate in the lottery.",
                "winner_announce": "🎉 Congratulations! You won ${amount} in the lottery! 🎉\nPlease click the button below to withdraw your prize.",
                "withdraw": "💰 Withdraw Prize",
                "enter_withdraw_wallet": "Please enter your TRC20 wallet address to receive your prize:",
                "withdraw_success": "✅ Prize successfully sent to your wallet!\nCongratulations again! 🎉",
                "withdraw_pending": "⏳ Your withdrawal request has been sent to admin for processing.",
                "admin_panel": "🔧 Admin Panel",
                "broadcast": "📢 Broadcast Message",
                "start_lottery": "🎰 Start Lottery",
                "manual_verify": "✅ Manual Verify",
                "poll": "📊 Poll",
                "restart_lottery": "🔄 Restart Lottery",
                "pay_winners": "💰 Pay Winners",
                "add_api": "🔑 Add API Key",
                "confirm_start": "Are you sure you want to start the lottery?",
                "enter_winners_count": "How many winners do you want to select?",
                "enter_prize_amount": "What is the prize amount for each winner? (in USD)",
                "lottery_started": "🎰 Lottery started! Selecting winners...",
                "lottery_complete": "✅ Lottery completed! Winners have been notified.",
                "no_participants": "❌ No participants with active subscriptions found.",
                "winner_selected": "🏆 Winner selected: {user} - ${amount}",
                "language_changed": "🌐 Language changed to {lang}",
                "invalid_wallet": "❌ Invalid wallet address. Please enter a valid TRC20 address.",
                "referral_text": "🔗 Your referral link:\n`https://t.me/{bot_username}?start=ref_{code}`\n\nShare this link with your friends!",
                "guidance_text": "📚 **Guidance**\n\n1. Join the lottery by clicking 'Join Lottery'\n2. Enter your TRC20 wallet address\n3. Send $100 USDT to the provided address\n4. Wait for automatic verification\n5. If you win, withdraw your prize!\n\nGood luck! 🍀"
            },
            "fa": {
                "welcome": "به ربات {bot_name} خوش آمدید! 🎉\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
                "join_lottery": "🎰 شرکت در قرعه‌کشی",
                "referral": "👥 رفرال",
                "guidance": "📖 راهنمایی",
                "change_language": "🌐 تغییر زبان",
                "lottery_join": "لطفاً آدرس کیف پول مبدا خود را وارد کنید (TRC20):",
                "wallet_saved": "✅ آدرس کیف پول با موفقیت ذخیره شد!\nلطفاً دقیقاً ۱۰۰ دلار USDT به آدرس زیر ارسال کنید:\n`{wallet}`\n\nما به صورت خودکار پرداخت شما را تایید می‌کنیم.",
                "payment_verified": "✅ پرداخت تایید شد! شما در قرعه‌کشی ثبت نام کردید.\nموفق باشید! 🍀",
                "payment_failed": "❌ تایید پرداخت ناموفق بود. لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                "already_paid": "شما قبلاً در قرعه‌کشی فعلی ثبت نام کرده‌اید.",
                "not_subscribed": "❌ برای شرکت در قرعه‌کشی به اشتراک فعال نیاز دارید.",
                "winner_announce": "🎉 تبریک! شما برنده {amount} دلار در قرعه‌کشی شدید! 🎉\nبرای برداشت جایزه خود روی دکمه زیر کلیک کنید:",
                "withdraw": "💰 برداشت جایزه",
                "enter_withdraw_wallet": "لطفاً آدرس کیف پول TRC20 خود را برای دریافت جایزه وارد کنید:",
                "withdraw_success": "✅ جایزه با موفقیت به کیف پول شما ارسال شد!\nدوباره تبریک! 🎉",
                "withdraw_pending": "⏳ درخواست برداشت شما برای پردازش به ادمین ارسال شد.",
                "admin_panel": "🔧 پنل مدیریت",
                "broadcast": "📢 ارسال پیام همگانی",
                "start_lottery": "🎰 شروع قرعه‌کشی",
                "manual_verify": "✅ تایید دستی",
                "poll": "📊 نظر سنجی",
                "restart_lottery": "🔄 شروع مجدد قرعه‌کشی",
                "pay_winners": "💰 واریز به برندگان",
                "add_api": "🔑 اضافه کردن API جدید",
                "confirm_start": "مطمئن هستید می‌خواهید قرعه‌کشی را شروع کنید؟",
                "enter_winners_count": "چند نفر را می‌خواهید در این قرعه‌کشی برنده شوند؟",
                "enter_prize_amount": "مبلغ جایزه برای هر برنده چقدر باشد؟ (به دلار)",
                "lottery_started": "🎰 قرعه‌کشی شروع شد! در حال انتخاب برندگان...",
                "lottery_complete": "✅ قرعه‌کشی کامل شد! برندگان مطلع شدند.",
                "no_participants": "❌ هیچ شرکت‌کننده با اشتراک فعال یافت نشد.",
                "winner_selected": "🏆 برنده انتخاب شد: {user} - ${amount}",
                "language_changed": "🌐 زبان به {lang} تغییر یافت",
                "invalid_wallet": "❌ آدرس کیف پول نامعتبر است. لطفاً یک آدرس TRC20 معتبر وارد کنید.",
                "referral_text": "🔗 لینک رفرال شما:\n`https://t.me/{bot_username}?start=ref_{code}`\n\nاین لینک را با دوستان خود به اشتراک بگذارید!",
                "guidance_text": "📚 **راهنمایی**\n\n۱. با کلیک روی 'شرکت در قرعه‌کشی' ثبت نام کنید\n۲. آدرس کیف پول TRC20 خود را وارد کنید\n۳. ۱۰۰ دلار USDT به آدرس ارائه شده ارسال کنید\n۴. منتظر تایید خودکار باشید\n۵. اگر برنده شدید، جایزه خود را برداشت کنید!\n\nموفق باشید! 🍀"
            },
            "tr": {
                "welcome": "{bot_name} hoş geldiniz! 🎉\nLütfen bir seçenek seçin:",
                "join_lottery": "🎰 Piyangoya Katıl",
                "referral": "👥 Davet",
                "guidance": "📖 Rehber",
                "change_language": "🌐 Dil Değiştir",
                "lottery_join": "Lütfen kaynak cüzdan adresinizi girin (TRC20):",
                "wallet_saved": "✅ Cüzdan adresi başarıyla kaydedildi!\nLütfen aşağıdaki adrese tam olarak 100$ USDT gönderin:\n`{wallet}`\n\nÖdemenizi otomatik olarak doğrulayacağız.",
                "payment_verified": "✅ Ödeme doğrulandı! Piyangoya kaydoldunuz.\nİyi şanslar! 🍀",
                "payment_failed": "❌ Ödeme doğrulaması başarısız. Lütfen tekrar deneyin veya destek ile iletişime geçin.",
                "already_paid": "Zaten mevcut piyangoya kaydoldunuz.",
                "not_subscribed": "❌ Piyangoya katılmak için aktif bir aboneliğiniz olmalı.",
                "winner_announce": "🎉 Tebrikler! Piyangoda ${amount} kazandınız! 🎉\nÖdülünüzü çekmek için aşağıdaki butona tıklayın:",
                "withdraw": "💰 Ödülü Çek",
                "enter_withdraw_wallet": "Ödülünüzü almak için TRC20 cüzdan adresinizi girin:",
                "withdraw_success": "✅ Ödül başarıyla cüzdanınıza gönderildi!\nTekrar tebrikler! 🎉",
                "withdraw_pending": "⏳ Çekim talebiniz işleme alınmak üzere yöneticiye gönderildi.",
                "admin_panel": "🔧 Yönetim Paneli",
                "broadcast": "📢 Toplu Mesaj",
                "start_lottery": "🎰 Piyangoyu Başlat",
                "manual_verify": "✅ Manuel Doğrula",
                "poll": "📊 Anket",
                "restart_lottery": "🔄 Piyangoyu Yeniden Başlat",
                "pay_winners": "💰 Kazananlara Öde",
                "add_api": "🔑 API Anahtarı Ekle",
                "confirm_start": "Piyangoyu başlatmak istediğinizden emin misiniz?",
                "enter_winners_count": "Bu piyangoda kaç kazanan olmasını istiyorsunuz?",
                "enter_prize_amount": "Her kazanan için ödül miktarı ne olsun? (USD)",
                "lottery_started": "🎰 Piyango başladı! Kazananlar seçiliyor...",
                "lottery_complete": "✅ Piyango tamamlandı! Kazananlar bilgilendirildi.",
                "no_participants": "❌ Aktif aboneliği olan katılımcı bulunamadı.",
                "winner_selected": "🏆 Kazanan seçildi: {user} - ${amount}",
                "language_changed": "🌐 Dil {lang} olarak değiştirildi",
                "invalid_wallet": "❌ Geçersiz cüzdan adresi. Lütfen geçerli bir TRC20 adresi girin.",
                "referral_text": "🔗 Davet bağlantınız:\n`https://t.me/{bot_username}?start=ref_{code}`\n\nBu bağlantıyı arkadaşlarınızla paylaşın!",
                "guidance_text": "📚 **Rehber**\n\n1. 'Piyangoya Katıl' butonuna tıklayın\n2. TRC20 cüzdan adresinizi girin\n3. Belirtilen adrese 100$ USDT gönderin\n4. Otomatik doğrulamayı bekleyin\n5. Kazanırsanız, ödülünüzü çekin!\n\nİyi şanslar! 🍀"
            }
        }
    
    def get_text(self, lang: str, key: str, **kwargs) -> str:
        """دریافت متن ترجمه شده"""
        if lang not in self.translations:
            lang = "en"
        
        text = self.translations[lang].get(key, self.translations["en"].get(key, key))
        
        # جایگزینی متغیرها
        for k, v in kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))
        
        return text

# ==================== سیستم پرداخت ====================
class PaymentSystem:
    def __init__(self, db: ShardedDatabase):
        self.db = db
        self.api_keys = Config.API_KEYS.copy()
        self.api_key_index = 0
        self.verification_queue = asyncio.Queue()
        self.is_verifying = False
        self.session = None
    
    async def initialize(self):
        """راه‌اندازی session"""
        self.session = aiohttp.ClientSession()
        asyncio.create_task(self._process_verification_queue())
    
    async def verify_payment(self, user_id: int, from_address: str, to_address: str, amount: int) -> bool:
        """بررسی و تایید پرداخت با استفاده از API"""
        try:
            # اضافه کردن به صف تایید
            await self.verification_queue.put((user_id, from_address, to_address, amount))
            
            if not self.is_verifying:
                asyncio.create_task(self._process_verification_queue())
            
            return True
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False
    
    async def _process_verification_queue(self):
        """پردازش صف تایید تراکنش‌ها"""
        if self.is_verifying:
            return
        
        self.is_verifying = True
        try:
            while not self.verification_queue.empty():
                user_id, from_address, to_address, amount = await self.verification_queue.get()
                
                # انتخاب API Key به صورت round-robin
                api_key = self.api_keys[self.api_key_index % len(self.api_keys)]
                self.api_key_index += 1
                
                # تایید پرداخت با API
                verified = await self._verify_transaction_with_api(
                    from_address, to_address, amount, api_key
                )
                
                if verified:
                    # ثبت در دیتابیس
                    await self.db.execute_query(
                        user_id,
                        """UPDATE users SET is_winner = 1, won_amount = ? WHERE user_id = ?""",
                        (amount, user_id)
                    )
                    
                    # ثبت تراکنش
                    await self.db.execute_query(
                        user_id,
                        """INSERT INTO transactions (user_id, from_address, to_address, amount, status, created_at, verified_at, api_key_used)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, from_address, to_address, amount, "verified", int(time.time()), int(time.time()), api_key)
                    )
                    
                    logger.info(f"Payment verified for user {user_id} using API key {api_key}")
                
                await asyncio.sleep(0.1)  # جلوگیری از overload
        except Exception as e:
            logger.error(f"Queue processing error: {e}")
        finally:
            self.is_verifying = False
    
    async def _verify_transaction_with_api(self, from_address: str, to_address: str, 
                                         amount: int, api_key: str) -> bool:
        """تایید تراکنش با استفاده از API Trongrid"""
        try:
            # 1. دریافت تاریخچه تراکنش‌ها از آدرس مبدا
            url = f"{Config.TRONGRID_API}/v1/accounts/{from_address}/transactions"
            headers = {"TRON-PRO-API-KEY": api_key}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 2. بررسی تراکنش‌ها برای تطابق
                    for tx in data.get("data", []):
                        # بررسی آدرس مقصد و مبلغ
                        if self._check_transaction_match(tx, to_address, amount):
                            return True
                    
                    # 3. اگر تراکنش پیدا نشد، بررسی با API دوم
                    return await self._verify_with_secondary_api(from_address, to_address, amount)
                
                return False
        except Exception as e:
            logger.error(f"API verification error: {e}")
            return False
    
    async def _verify_with_secondary_api(self, from_address: str, to_address: str, amount: int) -> bool:
        """بررسی با API ثانویه (پشتیبان)"""
        try:
            # استفاده از API ثانویه برای تایید
            url = f"https://api.tronscan.org/api/transaction"
            params = {
                "address": from_address,
                "limit": 50,
                "sort": "-timestamp"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for tx in data.get("data", []):
                        if self._check_transaction_match(tx, to_address, amount):
                            return True
                
                return False
        except Exception as e:
            logger.error(f"Secondary API verification error: {e}")
            return False
    
    def _check_transaction_match(self, tx: dict, to_address: str, amount: int) -> bool:
        """بررسی تطابق تراکنش"""
        try:
            # بررسی آدرس مقصد
            tx_to = tx.get("to", "")
            if tx_to.lower() != to_address.lower():
                return False
            
            # بررسی مبلغ (با تبدیل از SUN به USDT)
            tx_amount = tx.get("amount", 0) / 1_000_000  # تبدیل SUN به USDT
            
            # محدوده مبلغ با 5% خطا
            min_amount = amount * 0.95
            max_amount = amount * 1.05
            
            return min_amount <= tx_amount <= max_amount
            
        except Exception as e:
            logger.error(f"Transaction check error: {e}")
            return False
    
    async def add_api_key(self, api_key: str):
        """اضافه کردن API Key جدید"""
        if api_key not in self.api_keys:
            self.api_keys.append(api_key)
            logger.info(f"New API key added: {api_key}")
            return True
        return False
    
    async def close(self):
        """بستن session"""
        if self.session:
            await self.session.close()

# ==================== سیستم قرعه‌کشی ====================
class LotterySystem:
    def __init__(self, db: ShardedDatabase, payment: PaymentSystem):
        self.db = db
        self.payment = payment
        self.is_running = False
        self.current_lottery = None
        self.participants = []
        self.winners = []
        self.lottery_lock = asyncio.Lock()
    
    async def start_lottery(self, winners_count: int, prize_amount: int) -> List[Dict]:
        """شروع قرعه‌کشی با الگوریتم هوشمند"""
        async with self.lottery_lock:
            if self.is_running:
                return []
            
            self.is_running = True
            try:
                # 1. دریافت شرکت‌کنندگان با اشتراک فعال
                participants = await self._get_participants()
                
                if not participants:
                    logger.warning("No participants found")
                    return []
                
                # 2. الگوریتم هوشمند انتخاب برندگان
                winners = await self._select_winners(participants, winners_count)
                
                # 3. ذخیره نتایج
                await self._save_lottery_results(winners, prize_amount)
                
                # 4. اعلام برندگان
                for winner in winners:
                    await self._notify_winner(winner, prize_amount)
                
                self.winners = winners
                self.is_running = False
                return winners
                
            except Exception as e:
                logger.error(f"Lottery error: {e}")
                self.is_running = False
                return []
    
    async def _get_participants(self) -> List[Dict]:
        """دریافت شرکت‌کنندگان با اشتراک فعال"""
        participants = []
        current_time = int(time.time())
        
        # دریافت کاربران از همه شاردها
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, total_participations, 
                       subscription_end, wallet_address 
                FROM users 
                WHERE subscription_end > ? 
                AND wallet_address IS NOT NULL
            """, (current_time,))
            
            users = cursor.fetchall()
            for user in users:
                participants.append({
                    "user_id": user[0],
                    "username": user[1] or f"User_{user[0]}",
                    "first_name": user[2] or "",
                    "total_participations": user[3] or 0,
                    "subscription_end": user[4],
                    "wallet_address": user[5]
                })
        
        return participants
    
    async def _select_winners(self, participants: List[Dict], count: int) -> List[Dict]:
        """الگوریتم هوشمند انتخاب برندگان با استفاده از شانس وزنی و حذف برندگان قبلی"""
        if not participants:
            return []
        
        # محدود کردن تعداد برندگان
        count = min(count, len(participants))
        
        # 1. دریافت برندگان قبلی
        previous_winners = await self._get_previous_winners()
        
        # 2. محاسبه شانس وزنی برای هر شرکت‌کننده
        weighted_participants = []
        for participant in participants:
            user_id = participant["user_id"]
            
            # شانس پایه
            weight = 1.0
            
            # کاهش شانس برای برندگان قبلی (حداکثر 80% کاهش)
            if user_id in previous_winners:
                win_count = previous_winners[user_id]
                weight *= max(0.2, 1.0 - (win_count * 0.3))
            
            # افزایش شانس برای کاربرانی که بیشتر شرکت کرده‌اند
            participation_count = participant["total_participations"]
            if participation_count > 0:
                weight *= (1 + min(0.5, participation_count * 0.05))
            
            # شانس تصادفی برای حفظ عدالت
            weight *= random.uniform(0.8, 1.2)
            
            weighted_participants.append({
                **participant,
                "weight": weight
            })
        
        # 3. انتخاب برندگان با استفاده از روش رولت وزنی
        selected_winners = []
        available = weighted_participants.copy()
        
        for _ in range(count):
            if not available:
                break
            
            # محاسبه مجموع وزنی
            total_weight = sum(p["weight"] for p in available)
            
            # انتخاب تصادفی با وزن
            r = random.random() * total_weight
            cumulative = 0
            
            for i, participant in enumerate(available):
                cumulative += participant["weight"]
                if r <= cumulative:
                    selected = available.pop(i)
                    selected_winners.append(selected)
                    break
        
        return selected_winners
    
    async def _get_previous_winners(self) -> Dict[int, int]:
        """دریافت برندگان قبلی"""
        previous_winners = {}
        
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            cursor.execute("SELECT user_id, win_count FROM previous_winners")
            
            rows = cursor.fetchall()
            for row in rows:
                previous_winners[row[0]] = row[1]
        
        return previous_winners
    
    async def _save_lottery_results(self, winners: List[Dict], prize_amount: int):
        """ذخیره نتایج قرعه‌کشی"""
        lottery_id = int(time.time())
        winner_ids = [w["user_id"] for w in winners]
        
        # ذخیره در دیتابیس
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            
            # ذخیره قرعه‌کشی
            cursor.execute("""
                INSERT INTO lotteries (lottery_id, created_at, winners_count, prize_amount, status, winner_ids, ended_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (lottery_id, int(time.time()), len(winners), prize_amount, "completed", 
                  json.dumps(winner_ids), int(time.time())))
            
            # به‌روزرسانی برندگان
            for winner in winners:
                if winner["user_id"] % Config.SHARD_COUNT == shard_id:
                    cursor.execute("""
                        UPDATE users SET is_winner = 1, won_amount = ? WHERE user_id = ?
                    """, (prize_amount, winner["user_id"]))
                    
                    # ذخیره در جدول برندگان قبلی
                    cursor.execute("""
                        INSERT INTO previous_winners (user_id, last_win_time, win_count)
                        VALUES (?, ?, 1)
                        ON CONFLICT(user_id) DO UPDATE SET 
                            last_win_time = excluded.last_win_time,
                            win_count = win_count + 1
                    """, (winner["user_id"], int(time.time())))
            
            self.db.shards[shard_id].commit()
    
    async def _notify_winner(self, winner: Dict, prize_amount: int):
        """اعلام برنده"""
        # این تابع توسط ربات اصلی فراخوانی می‌شود
        pass

# ==================== ربات اصلی ====================
class LotteryBot:
    def __init__(self):
        self.db = ShardedDatabase()
        self.translations = TranslationSystem()
        self.payment = PaymentSystem(self.db)
        self.lottery = LotterySystem(self.db, self.payment)
        self.application = None
        self.bot_username = "UTYOB_Bot"
        self.user_states = {}  # ذخیره وضعیت کاربران
        self.lottery_state = {}  # وضعیت قرعه‌کشی
        self.pending_withdrawals = {}  # درخواست‌های برداشت در انتظار
    
    async def start(self):
        """راه‌اندازی ربات"""
        # راه‌اندازی سیستم پرداخت
        await self.payment.initialize()
        
        # ایجاد اپلیکیشن
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        
        # ثبت هندلرها
        self._register_handlers()
        
        # شروع ربات
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Bot started successfully!")
        
        # راه‌اندازی Flask API برای میکروسرویس‌ها
        self._start_flask_server()
        
        # نگه داشتن ربات در حال اجرا
        while True:
            await asyncio.sleep(1)
    
    def _register_handlers(self):
        """ثبت هندلرها"""
        # هندلر استارت
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # هندلر دکمه‌ها
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # هندلر پیام‌های متنی
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
        
        # هندلر خطا
        self.application.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور استارت"""
        user = update.effective_user
        user_id = user.id
        
        # بررسی وجود کاربر در دیتابیس
        db_user = await self.db.get_user(user_id)
        if not db_user:
            # ایجاد کاربر جدید
            await self.db.create_user(
                user_id,
                user.username or "",
                user.first_name or "",
                user.last_name or ""
            )
        
        # دریافت زبان کاربر
        lang = db_user.get("language", "en") if db_user else "en"
        
        # ساخت صفحه اصلی با دکمه Play
        keyboard = [
            [KeyboardButton("🎮 PLAY")],
            [KeyboardButton("🎰 شرکت در قرعه‌کشی"), KeyboardButton("👥 رفرال")],
            [KeyboardButton("📖 راهنمایی"), KeyboardButton("🌐 تغییر زبان")]
        ]
        
        # دکمه پنل ادمین برای ادمین‌ها
        if str(user_id) in Config.ADMIN_ID:
            keyboard.append([KeyboardButton("🔧 پنل مدیریت")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = self.translations.get_text(
            lang, "welcome", bot_name="UTYOB Lottery Bot"
        )
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """هندلر پیام‌های متنی"""
        user = update.effective_user
        user_id = user.id
        text = update.message.text
        
        # دریافت اطلاعات کاربر
        db_user = await self.db.get_user(user_id)
        if not db_user:
            await self.start_command(update, context)
            return
        
        lang = db_user.get("language", "en")
        
        # بررسی وضعیت کاربر
        state = self.user_states.get(user_id, {})
        
        # پردازش پیام بر اساس وضعیت
        if state.get("awaiting_wallet"):
            await self._handle_wallet_input(update, context, user_id, text, lang)
            return
        
        if state.get("awaiting_withdraw_wallet"):
            await self._handle_withdraw_wallet(update, context, user_id, text, lang)
            return
        
        # منوهای اصلی
        if text == "🎮 PLAY":
            await self.show_main_menu(update, context, user_id, lang)
        
        elif text == "🎰 شرکت در قرعه‌کشی" or text == "🎰 Join Lottery":
            await self.handle_join_lottery(update, context, user_id, lang)
        
        elif text == "👥 رفرال" or text == "👥 Referral":
            await self.handle_referral(update, context, user_id, lang)
        
        elif text == "📖 راهنمایی" or text == "📖 Guidance":
            await self.handle_guidance(update, context, user_id, lang)
        
        elif text == "🌐 تغییر زبان" or text == "🌐 Change Language":
            await self.handle_language_change(update, context, user_id, lang)
        
        elif text == "🔧 پنل مدیریت" or text == "🔧 Admin Panel":
            if str(user_id) in Config.ADMIN_ID:
                await self.show_admin_panel(update, context, user_id, lang)
            else:
                await update.message.reply_text("⛔ Access Denied!")
        
        else:
            await update.message.reply_text("❌ Invalid option. Please use the buttons.")
    
    async def _handle_wallet_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  user_id: int, wallet: str, lang: str):
        """پردازش آدرس کیف پول"""
        # اعتبارسنجی آدرس TRC20
        if not self._validate_tron_address(wallet):
            await update.message.reply_text(
                self.translations.get_text(lang, "invalid_wallet")
            )
            return
        
        # ذخیره آدرس کیف پول
        await self.db.execute_query(
            user_id,
            "UPDATE users SET wallet_address = ? WHERE user_id = ?",
            (wallet, user_id)
        )
        
        # حذف وضعیت انتظار
        self.user_states.pop(user_id, None)
        
        # ارسال آدرس واریز
        await update.message.reply_text(
            self.translations.get_text(
                lang, "wallet_saved", wallet=Config.WALLET_ADDRESS
            ),
            parse_mode="Markdown"
        )
        
        # شروع فرآیند تایید خودکار
        asyncio.create_task(self._auto_verify_payment(user_id, wallet, lang))
    
    async def _auto_verify_payment(self, user_id: int, wallet: str, lang: str):
        """تایید خودکار پرداخت"""
        # بررسی پرداخت هر 30 ثانیه به مدت 10 دقیقه
        for _ in range(20):  # 20 * 30 = 600 ثانیه = 10 دقیقه
            await asyncio.sleep(30)
            
            verified = await self.payment.verify_payment(
                user_id, wallet, Config.WALLET_ADDRESS, Config.AMOUNT_USD
            )
            
            if verified:
                # ارسال پیام تایید
                try:
                    await self.application.bot.send_message(
                        user_id,
                        self.translations.get_text(lang, "payment_verified")
                    )
                except:
                    pass
                return
        
        # در صورت عدم تایید
        try:
            await self.application.bot.send_message(
                user_id,
                self.translations.get_text(lang, "payment_failed")
            )
        except:
            pass
    
    def _validate_tron_address(self, address: str) -> bool:
        """اعتبارسنجی آدرس TRON"""
        if not address:
            return False
        
        # بررسی طول آدرس
        if len(address) != 34:
            return False
        
        # بررسی base58
        try:
            decoded = base58.b58decode(address)
            # بررسی checksum (ساده شده)
            return len(decoded) == 21
        except:
            return False
    
    async def handle_join_lottery(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 user_id: int, lang: str):
        """شرکت در قرعه‌کشی"""
        db_user = await self.db.get_user(user_id)
        
        # بررسی اشتراک
        if db_user.get("subscription_end", 0) < int(time.time()):
            await update.message.reply_text(
                self.translations.get_text(lang, "not_subscribed")
            )
            return
        
        # بررسی ثبت‌نام قبلی
        cursor = self.db.shards[user_id % Config.SHARD_COUNT].cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM lottery_participants 
            WHERE user_id = ? AND lottery_id IN (
                SELECT lottery_id FROM lotteries WHERE status = 'active'
            )
        """, (user_id,))
        
        if cursor.fetchone()[0] > 0:
            await update.message.reply_text(
                self.translations.get_text(lang, "already_paid")
            )
            return
        
        # درخواست آدرس کیف پول
        self.user_states[user_id] = {"awaiting_wallet": True}
        
        await update.message.reply_text(
            self.translations.get_text(lang, "lottery_join")
        )
    
    async def handle_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                             user_id: int, lang: str):
        """نمایش لینک رفرال"""
        db_user = await self.db.get_user(user_id)
        if not db_user:
            return
        
        code = db_user.get("referral_code", "")
        
        await update.message.reply_text(
            self.translations.get_text(
                lang, "referral_text",
                bot_username=self.bot_username,
                code=code
            ),
            parse_mode="Markdown"
        )
    
    async def handle_guidance(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                             user_id: int, lang: str):
        """نمایش راهنمایی"""
        await update.message.reply_text(
            self.translations.get_text(lang, "guidance_text"),
            parse_mode="Markdown"
        )
    
    async def handle_language_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    user_id: int, lang: str):
        """تغییر زبان"""
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
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                            user_id: int, lang: str):
        """نمایش منوی اصلی"""
        keyboard = [
            [KeyboardButton("🎰 شرکت در قرعه‌کشی"), KeyboardButton("👥 رفرال")],
            [KeyboardButton("📖 راهنمایی"), KeyboardButton("🌐 تغییر زبان")]
        ]
        
        if str(user_id) in Config.ADMIN_ID:
            keyboard.append([KeyboardButton("🔧 پنل مدیریت")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            self.translations.get_text(lang, "welcome", bot_name="UTYOB Lottery Bot"),
            reply_markup=reply_markup
        )
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                              user_id: int, lang: str):
        """نمایش پنل مدیریت"""
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton("✅ تایید دستی", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📊 نظر سنجی", callback_data="admin_poll")],
            [InlineKeyboardButton("🔄 شروع مجدد قرعه‌کشی", callback_data="admin_restart_lottery")],
            [InlineKeyboardButton("💰 واریز به برندگان", callback_data="admin_pay_winners")],
            [InlineKeyboardButton("🔑 اضافه کردن API", callback_data="admin_add_api")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **Admin Panel** / پنل مدیریت",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """هندلر دکمه‌های inline"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_id = user.id
        data = query.data
        
        # دریافت زبان کاربر
        db_user = await self.db.get_user(user_id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        # پردازش دکمه‌ها
        if data == "lang_en":
            await self._change_language(user_id, "en", query)
        elif data == "lang_fa":
            await self._change_language(user_id, "fa", query)
        elif data == "lang_tr":
            await self._change_language(user_id, "tr", query)
        
        elif data == "admin_start_lottery":
            if str(user_id) in Config.ADMIN_ID:
                await self._admin_start_lottery(query, user_id, lang)
        
        elif data == "admin_broadcast":
            if str(user_id) in Config.ADMIN_ID:
                self.user_states[user_id] = {"awaiting_broadcast": True}
                await query.edit_message_text("📢 Enter your broadcast message:")
        
        elif data == "admin_manual_verify":
            if str(user_id) in Config.ADMIN_ID:
                self.user_states[user_id] = {"awaiting_manual_verify": True}
                await query.edit_message_text("✅ Enter the user ID to verify manually:")
        
        elif data == "admin_add_api":
            if str(user_id) in Config.ADMIN_ID:
                self.user_states[user_id] = {"awaiting_api_key": True}
                await query.edit_message_text("🔑 Enter the new API key:")
        
        elif data == "admin_pay_winners":
            if str(user_id) in Config.ADMIN_ID:
                await self._admin_pay_winners(query, user_id, lang)
        
        elif data == "admin_restart_lottery":
            if str(user_id) in Config.ADMIN_ID:
                await self._admin_restart_lottery(query, user_id, lang)
        
        elif data.startswith("lottery_confirm_"):
            if str(user_id) in Config.ADMIN_ID:
                parts = data.split("_")
                if len(parts) == 4:
                    winners_count = int(parts[2])
                    prize_amount = int(parts[3])
                    await self._execute_lottery(query, user_id, lang, winners_count, prize_amount)
        
        elif data.startswith("winner_withdraw_"):
            # پردازش برداشت برنده
            winner_id = int(data.split("_")[2])
            if winner_id == user_id:
                self.user_states[user_id] = {"awaiting_withdraw_wallet": True}
                await query.edit_message_text(
                    self.translations.get_text(lang, "enter_withdraw_wallet")
                )
    
    async def _change_language(self, user_id: int, lang: str, query):
        """تغییر زبان کاربر"""
        await self.db.execute_query(
            user_id,
            "UPDATE users SET language = ? WHERE user_id = ?",
            (lang, user_id)
        )
        
        # حذف از کش
        cache_key = f"user_{user_id}"
        if cache_key in self.db.cache:
            del self.db.cache[cache_key]
        
        await query.edit_message_text(
            self.translations.get_text(lang, "language_changed", lang=lang)
        )
    
    async def _admin_start_lottery(self, query, admin_id: int, lang: str):
        """شروع قرعه‌کشی توسط ادمین"""
        # تایید شروع
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data="admin_confirm_start"),
                InlineKeyboardButton("❌ No", callback_data="admin_cancel_start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self.translations.get_text(lang, "confirm_start"),
            reply_markup=reply_markup
        )
        
        # ذخیره وضعیت برای مرحله بعد
        self.lottery_state[admin_id] = {"step": "confirm_start"}
    
    async def _admin_confirm_start(self, query, admin_id: int, lang: str):
        """تایید شروع قرعه‌کشی"""
        # دریافت تعداد برندگان
        self.lottery_state[admin_id] = {"step": "get_winners_count"}
        
        keyboard = [
            [InlineKeyboardButton("1", callback_data="lottery_winners_1"),
             InlineKeyboardButton("2", callback_data="lottery_winners_2"),
             InlineKeyboardButton("3", callback_data="lottery_winners_3")],
            [InlineKeyboardButton("5", callback_data="lottery_winners_5"),
             InlineKeyboardButton("10", callback_data="lottery_winners_10"),
             InlineKeyboardButton("20", callback_data="lottery_winners_20")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self.translations.get_text(lang, "enter_winners_count"),
            reply_markup=reply_markup
        )
    
    async def _execute_lottery(self, query, admin_id: int, lang: str, 
                              winners_count: int, prize_amount: int):
        """اجرای قرعه‌کشی"""
        await query.edit_message_text(
            self.translations.get_text(lang, "lottery_started")
        )
        
        # اجرای قرعه‌کشی
        winners = await self.lottery.start_lottery(winners_count, prize_amount)
        
        if not winners:
            await query.message.reply_text(
                self.translations.get_text(lang, "no_participants")
            )
            return
        
        # اعلام برندگان
        for winner in winners:
            winner_text = self.translations.get_text(
                lang, "winner_selected",
                user=winner.get("username") or winner.get("first_name") or f"User_{winner['user_id']}",
                amount=prize_amount
            )
            await query.message.reply_text(winner_text)
            
            # ارسال پیام به برنده
            try:
                await self.application.bot.send_message(
                    winner["user_id"],
                    self.translations.get_text(
                        "en", "winner_announce", amount=prize_amount
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            self.translations.get_text("en", "withdraw"),
                            callback_data=f"winner_withdraw_{winner['user_id']}"
                        )]
                    ])
                )
            except Exception as e:
                logger.error(f"Error notifying winner {winner['user_id']}: {e}")
        
        # اعلام پایان قرعه‌کشی
        await query.message.reply_text(
            self.translations.get_text(lang, "lottery_complete")
        )
    
    async def _admin_pay_winners(self, query, admin_id: int, lang: str):
        """واریز به برندگان"""
        await query.edit_message_text("💰 Sending payments to winners...")
        
        # دریافت لیست برندگان تایید نشده
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            cursor.execute("""
                SELECT user_id, wallet_address, won_amount 
                FROM users 
                WHERE is_winner = 1 AND won_amount > 0
            """)
            
            winners = cursor.fetchall()
            for winner in winners:
                # اینجا کد واریز واقعی قرار می‌گیرد
                await query.message.reply_text(
                    f"✅ Winner {winner[0]}: ${winner[2]} will be sent to {winner[1]}"
                )
                
                # بروزرسانی وضعیت
                cursor.execute("""
                    UPDATE users SET is_winner = 0, won_amount = 0 
                    WHERE user_id = ?
                """, (winner[0],))
                self.db.shards[shard_id].commit()
        
        await query.message.reply_text("✅ All payments processed!")
    
    async def _admin_restart_lottery(self, query, admin_id: int, lang: str):
        """شروع مجدد قرعه‌کشی"""
        # پاک کردن داده‌های قرعه‌کشی قبلی
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            cursor.execute("DELETE FROM lottery_participants")
            self.db.shards[shard_id].commit()
        
        await query.edit_message_text("🔄 Lottery reset successfully!")
    
    async def _handle_withdraw_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                     user_id: int, wallet: str, lang: str):
        """پردازش آدرس برداشت برنده"""
        if not self._validate_tron_address(wallet):
            await update.message.reply_text(
                self.translations.get_text(lang, "invalid_wallet")
            )
            return
        
        # ذخیره آدرس برداشت و ارسال به ادمین
        await self.db.execute_query(
            user_id,
            "UPDATE users SET wallet_address = ? WHERE user_id = ?",
            (wallet, user_id)
        )
        
        # حذف وضعیت
        self.user_states.pop(user_id, None)
        
        # ارسال به ادمین‌ها
        for admin_id in Config.ADMIN_ID:
            try:
                await self.application.bot.send_message(
                    admin_id,
                    f"💰 Withdrawal request from User {user_id}\n"
                    f"Wallet: {wallet}\n"
                    f"Amount: ${await self._get_user_won_amount(user_id)}"
                )
            except:
                pass
        
        await update.message.reply_text(
            self.translations.get_text(lang, "withdraw_pending")
        )
    
    async def _get_user_won_amount(self, user_id: int) -> int:
        """دریافت مبلغ جایزه کاربر"""
        db_user = await self.db.get_user(user_id)
        return db_user.get("won_amount", 0) if db_user else 0
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """هندلر خطا"""
        logger.error(f"Update {update} caused error {context.error}")
    
    def _start_flask_server(self):
        """راه‌اندازی سرور Flask برای میکروسرویس‌ها"""
        app = Flask(__name__)
        
        @app.route('/verify', methods=['POST'])
        async def verify_endpoint():
            data = request.json
            user_id = data.get('user_id')
            from_address = data.get('from_address')
            to_address = data.get('to_address')
            amount = data.get('amount')
            
            if not all([user_id, from_address, to_address, amount]):
                return jsonify({"status": "error", "message": "Missing parameters"}), 400
            
            verified = await self.payment.verify_payment(
                user_id, from_address, to_address, amount
            )
            
            return jsonify({"status": "success", "verified": verified})
        
        @app.route('/lottery/status', methods=['GET'])
        def lottery_status():
            return jsonify({
                "is_running": self.lottery.is_running,
                "winners": len(self.lottery.winners)
            })
        
        @app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                "status": "healthy",
                "shards": Config.SHARD_COUNT,
                "api_keys": len(self.payment.api_keys),
                "queue_size": self.payment.verification_queue.qsize()
            })
        
        # اجرای Flask در ترد جداگانه
        def run_flask():
            app.run(host='0.0.0.0', port=5000, debug=False)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

# ==================== اجرای اصلی ====================
async def main():
    bot = LotteryBot()
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")