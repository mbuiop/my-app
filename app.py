import asyncio
import json
import logging
import random
import hashlib
import time
import sqlite3
import aiosqlite
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask, request, jsonify
import threading
import base58
import psutil
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import pickle
import redis
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio
from asyncio import Queue
import aiofiles
import uvloop
import sentry_sdk
from prometheus_client import Counter, Histogram, start_http_server
import structlog

# ==================== تنظیمات پیشرفته ====================
uvloop.install()
logger = structlog.get_logger()

# ==================== کانفیگ سیستم ====================
class Config:
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    ADMIN_IDS = [123456789, 987654321]  # لیست ادمین‌ها
    
    # دیتابیس
    REDIS_URL = "redis://localhost:6379/0"
    SHARD_COUNT = 100  # ۱۰۰ شارد برای میلیون‌ها کاربر
    CACHE_TTL = 300
    
    # سیستم پرداخت
    TRONGRID_API = "https://api.trongrid.io"
    TRONSCAN_API = "https://api.tronscan.org"
    WALLET_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
    AMOUNT_USD = 100
    USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT TRC20
    
    # API Keys با توزیع بار
    API_KEYS = [
        "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
        # API Key های بیشتر برای مقیاس‌پذیری
    ]
    
    # میکروسرویس‌ها
    MICROSERVICES = {
        "auth": {"port": 5001, "workers": 8},
        "payment": {"port": 5002, "workers": 12},
        "lottery": {"port": 5003, "workers": 10},
        "notification": {"port": 5004, "workers": 6},
        "analytics": {"port": 5005, "workers": 4}
    }
    
    # تنظیمات قرعه‌کشی
    MAX_WINNERS = 100
    MIN_PARTICIPANTS = 10
    AI_MODEL_PATH = "lottery_model.pkl"
    
    # سیستم رفرال
    REFERRAL_BONUS = 0.05  # ۵% افزایش شانس به ازای هر رفرال با اشتراک

# ==================== سیستم دیتابیس پیشرفته با کش ====================
class AdvancedDatabase:
    def __init__(self):
        self.shards = {}
        self.redis_client = redis.Redis.from_url(Config.REDIS_URL, decode_responses=True)
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.cache = {}
        self.cache_timeout = Config.CACHE_TTL
        
        # راه‌اندازی شاردها
        for i in range(Config.SHARD_COUNT):
            db_path = f"shard_{i}.db"
            self.shards[i] = sqlite3.connect(db_path, check_same_thread=False)
            self._init_shard(i)
        
        # راه‌اندازی کش داغ
        self._warm_up_cache()
    
    def _init_shard(self, shard_id):
        cursor = self.shards[shard_id].cursor()
        
        # جدول کاربران با فیلدهای جدید
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
                active_referrals INTEGER DEFAULT 0,
                created_at INTEGER,
                language TEXT DEFAULT 'en',
                is_winner BOOLEAN DEFAULT 0,
                won_amount INTEGER DEFAULT 0,
                total_participations INTEGER DEFAULT 0,
                win_count INTEGER DEFAULT 0,
                trust_score FLOAT DEFAULT 1.0,
                last_activity INTEGER,
                is_banned BOOLEAN DEFAULT 0,
                lottery_participation_count INTEGER DEFAULT 0
            )
        ''')
        
        # جدول تراکنش‌ها با ایندکس‌های بهینه
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
                retry_count INTEGER DEFAULT 0,
                block_number INTEGER
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
                participants_count INTEGER,
                ended_at INTEGER,
                ai_prediction FLOAT,
                execution_time FLOAT
            )
        ''')
        
        # جدول شرکت‌کنندگان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_participants (
                lottery_id INTEGER,
                user_id INTEGER,
                participated_at INTEGER,
                weight FLOAT DEFAULT 1.0,
                PRIMARY KEY (lottery_id, user_id)
            )
        ''')
        
        # جدول برندگان قبلی با آنالیز
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS previous_winners (
                user_id INTEGER PRIMARY KEY,
                last_win_time INTEGER,
                win_count INTEGER DEFAULT 1,
                total_prizes INTEGER DEFAULT 0,
                avg_prize FLOAT DEFAULT 0,
                streak INTEGER DEFAULT 0
            )
        ''')
        
        # جدول رفرال‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                referrer_id INTEGER,
                referred_id INTEGER,
                created_at INTEGER,
                is_active BOOLEAN DEFAULT 1,
                subscription_purchased BOOLEAN DEFAULT 0,
                PRIMARY KEY (referrer_id, referred_id)
            )
        ''')
        
        # جدول لاگ‌های سیستم
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER,
                level TEXT,
                component TEXT,
                message TEXT,
                details TEXT
            )
        ''')
        
        # ایندکس‌های پیشرفته
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_end)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_trust ON users(trust_score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user_status ON transactions(user_id, status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_time ON transactions(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lottery_status ON lotteries(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_participants_lottery ON lottery_participants(lottery_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)')
        
        self.shards[shard_id].commit()
    
    def _warm_up_cache(self):
        """گرم کردن کش با داده‌های پرکاربرد"""
        try:
            # کش کردن کاربران فعال
            for shard_id in range(Config.SHARD_COUNT):
                cursor = self.shards[shard_id].cursor()
                cursor.execute("""
                    SELECT user_id, language, subscription_end, trust_score 
                    FROM users 
                    WHERE subscription_end > ?
                """, (int(time.time()),))
                
                users = cursor.fetchall()
                for user in users:
                    cache_key = f"user_{user[0]}"
                    self.cache[cache_key] = {
                        "user_id": user[0],
                        "language": user[1],
                        "subscription_end": user[2],
                        "trust_score": user[3],
                        "cached_at": time.time()
                    }
        except Exception as e:
            logger.error(f"Cache warm-up error: {e}")
    
    def _get_shard(self, user_id: int) -> int:
        return user_id % Config.SHARD_COUNT
    
    async def execute_query(self, user_id: int, query: str, params: tuple = (), fetch: bool = False):
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
    
    async def get_user(self, user_id: int, use_cache: bool = True):
        cache_key = f"user_{user_id}"
        
        if use_cache and cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached.get("cached_at", 0) < self.cache_timeout:
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
                "active_referrals": result[0][9] if len(result[0]) > 9 else 0,
                "created_at": result[0][10] if len(result[0]) > 10 else 0,
                "language": result[0][11] if len(result[0]) > 11 else "en",
                "is_winner": result[0][12] if len(result[0]) > 12 else False,
                "won_amount": result[0][13] if len(result[0]) > 13 else 0,
                "total_participations": result[0][14] if len(result[0]) > 14 else 0,
                "win_count": result[0][15] if len(result[0]) > 15 else 0,
                "trust_score": result[0][16] if len(result[0]) > 16 else 1.0,
                "last_activity": result[0][17] if len(result[0]) > 17 else 0,
                "is_banned": result[0][18] if len(result[0]) > 18 else False,
                "lottery_participation_count": result[0][19] if len(result[0]) > 19 else 0
            }
            
            # ذخیره در کش
            user_data["cached_at"] = time.time()
            self.cache[cache_key] = user_data
            
            # ذخیره در Redis برای دسترسی سریع‌تر
            self.redis_client.setex(
                cache_key,
                self.cache_timeout,
                json.dumps(user_data)
            )
            
            return user_data
        return None
    
    async def create_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        referral_code = self._generate_referral_code(user_id)
        
        await self.execute_query(
            user_id,
            """INSERT INTO users 
               (user_id, username, first_name, last_name, referral_code, created_at, language) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, first_name, last_name, referral_code, int(time.time()), "en")
        )
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "wallet_address": None,
            "subscription_end": 0,
            "referral_code": referral_code,
            "referred_by": None,
            "referral_count": 0,
            "active_referrals": 0,
            "created_at": int(time.time()),
            "language": "en",
            "is_winner": False,
            "won_amount": 0,
            "total_participations": 0,
            "win_count": 0,
            "trust_score": 1.0,
            "last_activity": 0,
            "is_banned": False,
            "lottery_participation_count": 0,
            "cached_at": time.time()
        }
        
        self.cache[f"user_{user_id}"] = user_data
        return referral_code
    
    def _generate_referral_code(self, user_id: int) -> str:
        return base58.b58encode(hashlib.sha256(f"{user_id}{time.time()}{random.random()}".encode()).digest()[:8]).decode()

# ==================== سیستم ترجمه پیشرفته با پشتیبانی کامل ====================
class TranslationSystem:
    def __init__(self):
        self.translations = {
            "en": {
                "welcome": "🎉 Welcome to {bot_name}!\n\nPlease select an option from below:",
                "join_lottery": "🎰 Join Lottery",
                "referral": "👥 Referral",
                "guidance": "📖 Guidance",
                "change_language": "🌐 Change Language",
                "lottery_join": "💰 Please enter your TRC20 wallet address:\n\n(This address will be used to verify your payment)",
                "wallet_saved": "✅ Wallet saved!\n\n📤 Please send exactly ${amount} USDT to:\n`{wallet}`\n\n⏳ After sending, click 'I have paid' button below for automatic verification.",
                "payment_verified": "✅ Payment verified!\n\n🎉 Your subscription for the lottery is now ACTIVE!\n\nYou will automatically participate in all future lotteries.",
                "payment_failed": "❌ Payment verification failed.\n\nPlease check:\n• You sent exactly ${amount} USDT\n• Sent to correct address\n• Transaction confirmed on blockchain\n\nTry again or contact support.",
                "already_paid": "ℹ️ You already have an active subscription for the lottery.",
                "not_subscribed": "❌ You need an active subscription to participate in the lottery.\n\nPlease join the lottery first.",
                "winner_announce": "🎉🎉🎉 CONGRATULATIONS! 🎉🎉🎉\n\nYou won ${amount} in the lottery!\n\n💰 Click the button below to withdraw your prize.",
                "withdraw": "💰 Withdraw Prize",
                "enter_withdraw_wallet": "🏦 Please enter your TRC20 wallet address to receive your prize:",
                "withdraw_success": "✅ Prize successfully sent to your wallet!\n\n🎊 Congratulations again!",
                "withdraw_pending": "⏳ Withdrawal request sent to admin for processing.\n\nYou will be notified when completed.",
                "admin_panel": "🔧 Admin Panel",
                "broadcast": "📢 Broadcast Message",
                "start_lottery": "🎰 Start Lottery",
                "manual_verify": "✅ Manual Verify",
                "poll": "📊 Poll",
                "restart_lottery": "🔄 Restart Lottery",
                "pay_winners": "💰 Pay Winners",
                "add_api": "🔑 Add API Key",
                "view_stats": "📊 Statistics",
                "manage_users": "👥 Manage Users",
                "confirm_start": "⚠️ Are you sure you want to start the lottery?\n\nThis action cannot be undone.",
                "enter_winners_count": "🎯 How many winners do you want to select?\n\n(Choose from options below)",
                "enter_prize_amount": "💰 What is the prize amount for each winner? (in USD)",
                "lottery_started": "🎰 Lottery is starting...\n\n🎯 Selecting winners with AI algorithm...",
                "lottery_complete": "✅ Lottery completed!\n\n🏆 Winners have been notified.",
                "no_participants": "❌ No participants with active subscriptions found.\n\nPlease wait for more users to join.",
                "winner_selected": "🏆 Winner: {user} - ${amount}",
                "language_changed": "🌐 Language changed to {lang}",
                "invalid_wallet": "❌ Invalid TRC20 wallet address.\n\nPlease enter a valid address (34 characters, starting with 'T').",
                "referral_text": "🔗 Your referral link:\n`https://t.me/{bot_username}?start=ref_{code}`\n\n📊 Your referral stats:\n• Total referrals: {total}\n• Active referrals: {active}\n• Bonus multiplier: x{multiplier}\n\n🤝 Share this link with your friends and earn bonuses!",
                "guidance_text": "📚 **Complete Guidance**\n\n1️⃣ **How to Participate:**\n   • Click 'Join Lottery' button\n   • Enter your TRC20 wallet address\n   • Send ${amount} USDT to the provided address\n   • Click 'I have paid' for verification\n   • Your subscription will be activated\n\n2️⃣ **Lottery Process:**\n   • Lotteries are started by admins\n   • All active subscribers automatically participate\n   • Fair winners are selected using AI algorithm\n   • Winners are notified immediately\n\n3️⃣ **How to Win:**\n   • Maintain active subscription\n   • Refer friends (increases win chance)\n   • Participate regularly\n   • Higher trust score = better chances\n\n4️⃣ **Prize Withdrawal:**\n   • Winners click 'Withdraw Prize'\n   • Enter TRC20 wallet address\n   • Prize sent automatically\n\n5️⃣ **Important Notes:**\n   • All transactions are verified on blockchain\n   • Multiple API keys ensure reliability\n   • 100% fair and transparent\n   • Support available 24/7\n\n💡 **Tip:** Invite more friends to increase your winning chances!\n\n🍀 Good luck!",
                "guidance_short": "📚 For complete guidance, please use the /guidance command.",
                "i_have_paid": "✅ I have paid",
                "checking_payment": "⏳ Checking your payment...\n\nPlease wait while we verify the transaction.",
                "payment_retry": "🔄 Still checking... Payment may take a few minutes to confirm on blockchain.",
                "payment_not_found": "⏳ Payment not found yet.\n\n• Make sure you sent exactly ${amount} USDT\n• Check transaction on Tronscan\n• Wait for blockchain confirmation\n• Try again in a few minutes",
                "subscription_active": "✅ Your subscription is active until {date}",
                "subscription_expired": "⚠️ Your subscription has expired.\n\nPlease renew to continue participating.",
                "lottery_participants": "👥 Participants in current lottery: {count}",
                "lottery_status": "🎯 Lottery Status:\n• Status: {status}\n• Participants: {participants}\n• Winners: {winners}\n• Prize: ${prize}",
                "referral_success": "✅ Referral successful!\n\nYou earned {bonus}% bonus to your win chance!\n\nCurrent multiplier: x{multiplier}",
                "win_chance": "🎯 Your win chance: {chance}%\n\nMultiplier: x{multiplier}\nTrust score: {trust}",
                "admin_broadcast_sent": "✅ Broadcast sent to {count} users.",
                "admin_manual_verify": "✅ Manual verification completed for user {user_id}.",
                "admin_api_added": "✅ New API key added successfully.\n\nTotal API keys: {total}",
                "admin_payment_processed": "💰 Payment of ${amount} sent to {winners} winners.",
                "admin_lottery_reset": "🔄 Lottery system has been reset.",
                "admin_poll_created": "📊 Poll created successfully!",
                "admin_stats": "📊 System Statistics:\n\n👥 Total Users: {users}\n✅ Active Subscriptions: {active}\n💰 Total Prizes: ${prizes}\n🏆 Winners: {winners}\n🔄 Total Lotteries: {lotteries}\n📈 Referrals: {referrals}"
            },
            "fa": {
                "welcome": "🎉 به ربات {bot_name} خوش آمدید!\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                "join_lottery": "🎰 شرکت در قرعه‌کشی",
                "referral": "👥 رفرال",
                "guidance": "📖 راهنمایی",
                "change_language": "🌐 تغییر زبان",
                "lottery_join": "💰 لطفاً آدرس کیف پول TRC20 خود را وارد کنید:\n\n(این آدرس برای تایید پرداخت شما استفاده می‌شود)",
                "wallet_saved": "✅ کیف پول ذخیره شد!\n\n📤 لطفاً دقیقاً ${amount} USDT به آدرس زیر ارسال کنید:\n`{wallet}`\n\n⏳ پس از ارسال، دکمه 'پرداخت کردم' را برای تایید خودکار بزنید.",
                "payment_verified": "✅ پرداخت تایید شد!\n\n🎉 اشتراک شما برای قرعه‌کشی فعال شد!\n\nشما به صورت خودکار در تمام قرعه‌کشی‌های آینده شرکت خواهید کرد.",
                "payment_failed": "❌ تایید پرداخت ناموفق بود.\n\nلطفاً بررسی کنید:\n• دقیقاً ${amount} USDT ارسال شده باشد\n• به آدرس صحیح ارسال شده باشد\n• تراکنش در بلاکچین تایید شده باشد\n\nدوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                "already_paid": "ℹ️ شما قبلاً اشتراک فعال برای قرعه‌کشی دارید.",
                "not_subscribed": "❌ برای شرکت در قرعه‌کشی به اشتراک فعال نیاز دارید.\n\nلطفاً ابتدا در قرعه‌کشی ثبت نام کنید.",
                "winner_announce": "🎉🎉🎉 تبریک! 🎉🎉🎉\n\nشما برنده ${amount} دلار در قرعه‌کشی شدید!\n\n💰 برای برداشت جایزه روی دکمه زیر کلیک کنید.",
                "withdraw": "💰 برداشت جایزه",
                "enter_withdraw_wallet": "🏦 لطفاً آدرس کیف پول TRC20 خود را برای دریافت جایزه وارد کنید:",
                "withdraw_success": "✅ جایزه با موفقیت به کیف پول شما ارسال شد!\n\n🎊 دوباره تبریک!",
                "withdraw_pending": "⏳ درخواست برداشت برای پردازش به ادمین ارسال شد.\n\nپس از اتمام به شما اطلاع داده می‌شود.",
                "admin_panel": "🔧 پنل مدیریت",
                "broadcast": "📢 ارسال پیام همگانی",
                "start_lottery": "🎰 شروع قرعه‌کشی",
                "manual_verify": "✅ تایید دستی",
                "poll": "📊 نظر سنجی",
                "restart_lottery": "🔄 شروع مجدد قرعه‌کشی",
                "pay_winners": "💰 واریز به برندگان",
                "add_api": "🔑 اضافه کردن API جدید",
                "view_stats": "📊 آمار",
                "manage_users": "👥 مدیریت کاربران",
                "confirm_start": "⚠️ مطمئن هستید می‌خواهید قرعه‌کشی را شروع کنید؟\n\nاین عمل قابل بازگشت نیست.",
                "enter_winners_count": "🎯 چند نفر را می‌خواهید در این قرعه‌کشی برنده شوند؟\n\n(از گزینه‌های زیر انتخاب کنید)",
                "enter_prize_amount": "💰 مبلغ جایزه برای هر برنده چقدر باشد؟ (به دلار)",
                "lottery_started": "🎰 قرعه‌کشی در حال شروع...\n\n🎯 انتخاب برندگان با الگوریتم هوش مصنوعی...",
                "lottery_complete": "✅ قرعه‌کشی کامل شد!\n\n🏆 برندگان مطلع شدند.",
                "no_participants": "❌ هیچ شرکت‌کننده با اشتراک فعال یافت نشد.\n\nلطفاً منتظر بمانید تا کاربران بیشتری ثبت نام کنند.",
                "winner_selected": "🏆 برنده: {user} - ${amount}",
                "language_changed": "🌐 زبان به {lang} تغییر یافت",
                "invalid_wallet": "❌ آدرس کیف پول TRC20 نامعتبر است.\n\nلطفاً یک آدرس معتبر وارد کنید (۳۴ کاراکتر، شروع با 'T').",
                "referral_text": "🔗 لینک رفرال شما:\n`https://t.me/{bot_username}?start=ref_{code}`\n\n📊 آمار رفرال شما:\n• مجموع رفرال‌ها: {total}\n• رفرال‌های فعال: {active}\n• ضریب پاداش: x{multiplier}\n\n🤝 این لینک را با دوستان خود به اشتراک بگذارید و پاداش بگیرید!",
                "guidance_text": "📚 **راهنمای کامل**\n\n1️⃣ **نحوه شرکت:**\n   • روی دکمه 'شرکت در قرعه‌کشی' کلیک کنید\n   • آدرس کیف پول TRC20 خود را وارد کنید\n   • ${amount} USDT به آدرس ارائه شده ارسال کنید\n   • روی 'پرداخت کردم' کلیک کنید\n   • اشتراک شما فعال می‌شود\n\n2️⃣ **فرآیند قرعه‌کشی:**\n   • قرعه‌کشی توسط ادمین شروع می‌شود\n   • تمام کاربران با اشتراک فعال شرکت می‌کنند\n   • برندگان با الگوریتم هوش مصنوعی انتخاب می‌شوند\n   • برندگان بلافاصله مطلع می‌شوند\n\n3️⃣ **نحوه برنده شدن:**\n   • اشتراک فعال داشته باشید\n   • دوستان خود را معرفی کنید (شانس را افزایش می‌دهد)\n   • به طور منظم شرکت کنید\n   • امتیاز اعتماد بالاتر = شانس بهتر\n\n4️⃣ **برداشت جایزه:**\n   • برندگان روی 'برداشت جایزه' کلیک می‌کنند\n   • آدرس کیف پول TRC20 را وارد می‌کنند\n   • جایزه به صورت خودکار ارسال می‌شود\n\n5️⃣ **نکات مهم:**\n   • تمام تراکنش‌ها در بلاکچین تایید می‌شوند\n   • چندین API Key برای اطمینان بیشتر\n   • ۱۰۰٪ عادلانه و شفاف\n   • پشتیبانی ۲۴/۷ در دسترس\n\n💡 **نکته:** دوستان بیشتری دعوت کنید تا شانس برنده شدن خود را افزایش دهید!\n\n🍀 موفق باشید!",
                "guidance_short": "📚 برای راهنمای کامل از دستور /guidance استفاده کنید.",
                "i_have_paid": "✅ پرداخت کردم",
                "checking_payment": "⏳ در حال بررسی پرداخت شما...\n\nلطفاً منتظر بمانید تا تراکنش تایید شود.",
                "payment_retry": "🔄 هنوز در حال بررسی... پرداخت ممکن است چند دقیقه طول بکشد.",
                "payment_not_found": "⏳ پرداخت یافت نشد.\n\n• مطمئن شوید دقیقاً ${amount} USDT ارسال کرده‌اید\n• تراکنش را در Tronscan بررسی کنید\n• منتظر تایید بلاکچین باشید\n• چند دقیقه دیگر دوباره تلاش کنید",
                "subscription_active": "✅ اشتراک شما تا تاریخ {date} فعال است",
                "subscription_expired": "⚠️ اشتراک شما منقضی شده است.\n\nلطفاً برای ادامه شرکت، تمدید کنید.",
                "lottery_participants": "👥 شرکت‌کنندگان در قرعه‌کشی فعلی: {count}",
                "lottery_status": "🎯 وضعیت قرعه‌کشی:\n• وضعیت: {status}\n• شرکت‌کنندگان: {participants}\n• برندگان: {winners}\n• جایزه: ${prize}",
                "referral_success": "✅ معرفی با موفقیت انجام شد!\n\nشما {bonus}% پاداش به شانس برنده شدن خود دریافت کردید!\n\nضریب فعلی: x{multiplier}",
                "win_chance": "🎯 شانس برنده شدن شما: {chance}%\n\nضریب: x{multiplier}\nامتیاز اعتماد: {trust}",
                "admin_broadcast_sent": "✅ پیام به {count} کاربر ارسال شد.",
                "admin_manual_verify": "✅ تایید دستی برای کاربر {user_id} انجام شد.",
                "admin_api_added": "✅ API جدید با موفقیت اضافه شد.\n\nتعداد کل API: {total}",
                "admin_payment_processed": "💰 مبلغ ${amount} به {winners} برنده ارسال شد.",
                "admin_lottery_reset": "🔄 سیستم قرعه‌کشی بازنشانی شد.",
                "admin_poll_created": "📊 نظر سنجی با موفقیت ایجاد شد!",
                "admin_stats": "📊 آمار سیستم:\n\n👥 کل کاربران: {users}\n✅ اشتراک‌های فعال: {active}\n💰 مجموع جوایز: ${prizes}\n🏆 برندگان: {winners}\n🔄 تعداد قرعه‌کشی‌ها: {lotteries}\n📈 رفرال‌ها: {referrals}"
            },
            "tr": {
                "welcome": "🎉 {bot_name} botuna hoş geldiniz!\n\nLütfen aşağıdaki seçeneklerden birini seçin:",
                "join_lottery": "🎰 Piyangoya Katıl",
                "referral": "👥 Davet",
                "guidance": "📖 Rehber",
                "change_language": "🌐 Dil Değiştir",
                "lottery_join": "💰 Lütfen TRC20 cüzdan adresinizi girin:\n\n(Bu adres ödemenizi doğrulamak için kullanılacak)",
                "wallet_saved": "✅ Cüzdan kaydedildi!\n\n📤 Lütfen tam olarak ${amount} USDT'yi şu adrese gönderin:\n`{wallet}`\n\n⏳ Gönderdikten sonra otomatik doğrulama için 'Ödedim' butonuna tıklayın.",
                "payment_verified": "✅ Ödeme doğrulandı!\n\n🎉 Piyango aboneliğiniz AKTİF!\n\nTüm gelecek piyangolara otomatik olarak katılacaksınız.",
                "payment_failed": "❌ Ödeme doğrulaması başarısız.\n\nLütfen kontrol edin:\n• Tam olarak ${amount} USDT gönderdiniz\n• Doğru adrese gönderdiniz\n• İşlem blockchain'de onaylandı\n\nTekrar deneyin veya destek ile iletişime geçin.",
                "already_paid": "ℹ️ Zaten piyango için aktif aboneliğiniz var.",
                "not_subscribed": "❌ Piyangoya katılmak için aktif aboneliğiniz olmalı.\n\nLütfen önce piyangoya katılın.",
                "winner_announce": "🎉🎉🎉 TEBRİKLER! 🎉🎉🎉\n\nPiyangoda ${amount} kazandınız!\n\n💰 Ödülünüzü çekmek için aşağıdaki butona tıklayın.",
                "withdraw": "💰 Ödülü Çek",
                "enter_withdraw_wallet": "🏦 Ödülünüzü almak için TRC20 cüzdan adresinizi girin:",
                "withdraw_success": "✅ Ödül başarıyla cüzdanınıza gönderildi!\n\n🎊 Tekrar tebrikler!",
                "withdraw_pending": "⏳ Çekim talebi işleme alınmak üzere yöneticiye gönderildi.\n\nTamamlandığında bilgilendirileceksiniz.",
                "admin_panel": "🔧 Yönetim Paneli",
                "broadcast": "📢 Toplu Mesaj",
                "start_lottery": "🎰 Piyangoyu Başlat",
                "manual_verify": "✅ Manuel Doğrula",
                "poll": "📊 Anket",
                "restart_lottery": "🔄 Piyangoyu Yeniden Başlat",
                "pay_winners": "💰 Kazananlara Öde",
                "add_api": "🔑 API Anahtarı Ekle",
                "view_stats": "📊 İstatistikler",
                "manage_users": "👥 Kullanıcıları Yönet",
                "confirm_start": "⚠️ Piyangoyu başlatmak istediğinizden emin misiniz?\n\nBu işlem geri alınamaz.",
                "enter_winners_count": "🎯 Kaç kazanan seçmek istiyorsunuz?\n\n(Aşağıdaki seçeneklerden seçin)",
                "enter_prize_amount": "💰 Her kazanan için ödül miktarı ne olsun? (USD)",
                "lottery_started": "🎰 Piyango başlıyor...\n\n🎯 Kazananlar AI algoritması ile seçiliyor...",
                "lottery_complete": "✅ Piyango tamamlandı!\n\n🏆 Kazananlar bilgilendirildi.",
                "no_participants": "❌ Aktif aboneliği olan katılımcı bulunamadı.\n\nLütfen daha fazla kullanıcının katılmasını bekleyin.",
                "winner_selected": "🏆 Kazanan: {user} - ${amount}",
                "language_changed": "🌐 Dil {lang} olarak değiştirildi",
                "invalid_wallet": "❌ Geçersiz TRC20 cüzdan adresi.\n\nLütfen geçerli bir adres girin (34 karakter, 'T' ile başlayan).",
                "referral_text": "🔗 Davet bağlantınız:\n`https://t.me/{bot_username}?start=ref_{code}`\n\n📊 Davet istatistikleriniz:\n• Toplam davet: {total}\n• Aktif davet: {active}\n• Bonus çarpanı: x{multiplier}\n\n🤝 Bu bağlantıyı arkadaşlarınızla paylaşın ve bonus kazanın!",
                "guidance_text": "📚 **Tam Rehber**\n\n1️⃣ **Nasıl Katılırım:**\n   • 'Piyangoya Katıl' butonuna tıklayın\n   • TRC20 cüzdan adresinizi girin\n   • Belirtilen adrese ${amount} USDT gönderin\n   • 'Ödedim' butonuna tıklayın\n   • Aboneliğiniz aktifleşir\n\n2️⃣ **Piyango Süreci:**\n   • Piyangolar yöneticiler tarafından başlatılır\n   • Tüm aktif aboneler otomatik katılır\n   • Kazananlar AI algoritması ile seçilir\n   • Kazananlar hemen bilgilendirilir\n\n3️⃣ **Nasıl Kazanırım:**\n   • Aktif aboneliğinizi koruyun\n   • Arkadaşlarınızı davet edin (şansı artırır)\n   • Düzenli katılın\n   • Yüksek güven puanı = daha iyi şans\n\n4️⃣ **Ödül Çekme:**\n   • Kazananlar 'Ödülü Çek' butonuna tıklar\n   • TRC20 cüzdan adresini girer\n   • Ödül otomatik gönderilir\n\n5️⃣ **Önemli Notlar:**\n   • Tüm işlemler blockchain'de doğrulanır\n   • Birden fazla API anahtarı güvenilirliği artırır\n   • %100 adil ve şeffaf\n   • 7/24 destek mevcut\n\n💡 **İpucu:** Daha fazla arkadaş davet ederek kazanma şansınızı artırın!\n\n🍀 İyi şanslar!",
                "guidance_short": "📚 Tam rehber için /guidance komutunu kullanın.",
                "i_have_paid": "✅ Ödedim",
                "checking_payment": "⏳ Ödemeniz kontrol ediliyor...\n\nLütfen işlemin doğrulanmasını bekleyin.",
                "payment_retry": "🔄 Hala kontrol ediliyor... Ödeme blockchain'de onaylanması birkaç dakika sürebilir.",
                "payment_not_found": "⏳ Ödeme bulunamadı.\n\n• Tam olarak ${amount} USDT gönderdiğinizden emin olun\n• Tronscan'da işlemi kontrol edin\n• Blockchain onayını bekleyin\n• Birkaç dakika sonra tekrar deneyin",
                "subscription_active": "✅ Aboneliğiniz {date} tarihine kadar aktif",
                "subscription_expired": "⚠️ Aboneliğiniz sona erdi.\n\nKatılmaya devam etmek için yenileyin.",
                "lottery_participants": "👥 Mevcut piyangodaki katılımcılar: {count}",
                "lottery_status": "🎯 Piyango Durumu:\n• Durum: {status}\n• Katılımcılar: {participants}\n• Kazananlar: {winners}\n• Ödül: ${prize}",
                "referral_success": "✅ Davet başarılı!\n\nKazanma şansınıza {bonus}% bonus kazandınız!\n\nMevcut çarpan: x{multiplier}",
                "win_chance": "🎯 Kazanma şansınız: {chance}%\n\nÇarpan: x{multiplier}\nGüven puanı: {trust}",
                "admin_broadcast_sent": "✅ Mesaj {count} kullanıcıya gönderildi.",
                "admin_manual_verify": "✅ {user_id} kullanıcısı için manuel doğrulama tamamlandı.",
                "admin_api_added": "✅ Yeni API anahtarı başarıyla eklendi.\n\nToplam API: {total}",
                "admin_payment_processed": "💰 ${amount} ödeme {winners} kazanana gönderildi.",
                "admin_lottery_reset": "🔄 Piyango sistemi sıfırlandı.",
                "admin_poll_created": "📊 Anket başarıyla oluşturuldu!",
                "admin_stats": "📊 Sistem İstatistikleri:\n\n👥 Toplam Kullanıcı: {users}\n✅ Aktif Abonelik: {active}\n💰 Toplam Ödül: ${prizes}\n🏆 Kazananlar: {winners}\n🔄 Toplam Piyango: {lotteries}\n📈 Davetler: {referrals}"
            }
        }
    
    def get_text(self, lang: str, key: str, **kwargs) -> str:
        if lang not in self.translations:
            lang = "en"
        
        text = self.translations[lang].get(key, self.translations["en"].get(key, key))
        
        for k, v in kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))
        
        return text

# ==================== سیستم پرداخت پیشرفته با هوش مصنوعی ====================
class AdvancedPaymentSystem:
    def __init__(self, db: AdvancedDatabase):
        self.db = db
        self.api_keys = Config.API_KEYS.copy()
        self.api_key_index = 0
        self.verification_queue = Queue(maxsize=10000)
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.processor = ProcessPoolExecutor(max_workers=4)
        self.is_processing = False
        self.retry_count = 3
        self.confirmation_blocks = 3
        
    async def initialize(self):
        self.session = aiohttp.ClientSession()
        asyncio.create_task(self._process_verification_queue())
    
    async def verify_payment(self, user_id: int, from_address: str, to_address: str, amount: int) -> bool:
        try:
            await self.verification_queue.put((user_id, from_address, to_address, amount))
            
            if not self.is_processing:
                asyncio.create_task(self._process_verification_queue())
            
            return True
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False
    
    async def _process_verification_queue(self):
        if self.is_processing:
            return
        
        self.is_processing = True
        try:
            while not self.verification_queue.empty():
                user_id, from_address, to_address, amount = await self.verification_queue.get()
                
                # استفاده از چندین API Key
                for attempt in range(self.retry_count):
                    api_key = self.api_keys[self.api_key_index % len(self.api_keys)]
                    self.api_key_index += 1
                    
                    verified = await self._verify_with_multiple_apis(
                        from_address, to_address, amount, api_key
                    )
                    
                    if verified:
                        await self._process_verified_payment(user_id, from_address, amount, api_key)
                        break
                    
                    await asyncio.sleep(5 * (attempt + 1))
                
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Queue processing error: {e}")
        finally:
            self.is_processing = False
    
    async def _verify_with_multiple_apis(self, from_address: str, to_address: str, 
                                       amount: int, api_key: str) -> bool:
        """بررسی با چندین API برای دقت بیشتر"""
        try:
            # 1. Trongrid API
            trongrid_verified = await self._verify_trongrid(from_address, to_address, amount, api_key)
            
            if trongrid_verified:
                # 2. Tronscan API برای تایید دوم
                tronscan_verified = await self._verify_tronscan(from_address, to_address, amount)
                
                if tronscan_verified:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Multi-API verification error: {e}")
            return False
    
    async def _verify_trongrid(self, from_address: str, to_address: str, 
                              amount: int, api_key: str) -> bool:
        """بررسی با Trongrid API"""
        try:
            url = f"{Config.TRONGRID_API}/v1/accounts/{from_address}/transactions"
            headers = {"TRON-PRO-API-KEY": api_key}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for tx in data.get("data", []):
                        if self._check_transaction(tx, to_address, amount):
                            return True
            return False
        except Exception as e:
            logger.error(f"Trongrid verification error: {e}")
            return False
    
    async def _verify_tronscan(self, from_address: str, to_address: str, amount: int) -> bool:
        """بررسی با Tronscan API"""
        try:
            url = f"{Config.TRONSCAN_API}/api/transaction"
            params = {
                "address": from_address,
                "limit": 50,
                "sort": "-timestamp"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for tx in data.get("data", []):
                        if self._check_transaction(tx, to_address, amount):
                            return True
            return False
        except Exception as e:
            logger.error(f"Tronscan verification error: {e}")
            return False
    
    def _check_transaction(self, tx: dict, to_address: str, amount: int) -> bool:
        """بررسی تطابق تراکنش با دقت بالا"""
        try:
            # بررسی آدرس مقصد
            tx_to = tx.get("to", "")
            if tx_to.lower() != to_address.lower():
                return False
            
            # بررسی مبلغ با دقت بالا
            tx_amount = tx.get("amount", 0)
            if tx_amount > 0:
                tx_amount = tx_amount / 1_000_000  # تبدیل SUN به USDT
            else:
                # بررسی token transfers برای USDT
                token_info = tx.get("token_info", {})
                if token_info.get("tokenId") == Config.USDT_CONTRACT:
                    tx_amount = tx.get("value", 0) / 1_000_000
            
            # محدوده دقیق با 2% خطا
            min_amount = amount * 0.98
            max_amount = amount * 1.02
            
            return min_amount <= tx_amount <= max_amount
            
        except Exception as e:
            logger.error(f"Transaction check error: {e}")
            return False
    
    async def _process_verified_payment(self, user_id: int, from_address: str, 
                                      amount: int, api_key: str):
        """پردازش پرداخت تایید شده"""
        try:
            # ثبت تراکنش
            await self.db.execute_query(
                user_id,
                """INSERT INTO transactions 
                   (user_id, from_address, to_address, amount, status, created_at, verified_at, api_key_used)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, from_address, Config.WALLET_ADDRESS, amount, "verified", 
                 int(time.time()), int(time.time()), api_key)
            )
            
            # فعال‌سازی اشتراک (1 ماه)
            subscription_end = int(time.time()) + 30 * 24 * 3600
            
            await self.db.execute_query(
                user_id,
                "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                (subscription_end, user_id)
            )
            
            # ثبت در جدول شرکت‌کنندگان
            await self.db.execute_query(
                user_id,
                """INSERT INTO lottery_participants (lottery_id, user_id, participated_at)
                   VALUES (?, ?, ?)""",
                (0, user_id, int(time.time()))
            )
            
            logger.info(f"Payment verified for user {user_id}")
            
            # ارسال پیام تایید به کاربر
            await self._send_payment_confirmation(user_id)
            
        except Exception as e:
            logger.error(f"Payment processing error: {e}")
    
    async def _send_payment_confirmation(self, user_id: int):
        """ارسال پیام تایید پرداخت"""
        try:
            user = await self.db.get_user(user_id)
            lang = user.get("language", "en") if user else "en"
            
            # اینجا توسط ربات اصلی ارسال می‌شود
            pass
        except Exception as e:
            logger.error(f"Confirmation send error: {e}")
    
    async def add_api_key(self, api_key: str) -> bool:
        if api_key not in self.api_keys:
            self.api_keys.append(api_key)
            logger.info(f"New API key added: {api_key}")
            return True
        return False
    
    async def close(self):
        if self.session:
            await self.session.close()

# ==================== سیستم قرعه‌کشی با هوش مصنوعی ====================
class AILotterySystem:
    def __init__(self, db: AdvancedDatabase, payment: AdvancedPaymentSystem):
        self.db = db
        self.payment = payment
        self.is_running = False
        self.current_lottery = None
        self.winners = []
        self.ai_model = None
        self.lottery_lock = asyncio.Lock()
        self.participants_cache = {}
        
        # بارگذاری مدل AI
        self._load_ai_model()
    
    def _load_ai_model(self):
        """بارگذاری یا ایجاد مدل هوش مصنوعی"""
        try:
            if os.path.exists(Config.AI_MODEL_PATH):
                with open(Config.AI_MODEL_PATH, 'rb') as f:
                    self.ai_model = pickle.load(f)
                logger.info("AI model loaded successfully")
            else:
                # ایجاد مدل جدید
                self.ai_model = RandomForestClassifier(
                    n_estimators=200,
                    max_depth=20,
                    random_state=42
                )
                logger.info("New AI model created")
        except Exception as e:
            logger.error(f"AI model load error: {e}")
            self.ai_model = None
    
    async def start_lottery(self, winners_count: int, prize_amount: int) -> List[Dict]:
        """شروع قرعه‌کشی با الگوریتم هوش مصنوعی"""
        async with self.lottery_lock:
            if self.is_running:
                return []
            
            self.is_running = True
            start_time = time.time()
            
            try:
                # 1. دریافت شرکت‌کنندگان
                participants = await self._get_participants_with_weights()
                
                if len(participants) < Config.MIN_PARTICIPANTS:
                    logger.warning(f"Not enough participants: {len(participants)}")
                    return []
                
                # 2. انتخاب برندگان با AI
                winners = await self._select_winners_ai(participants, winners_count)
                
                # 3. ذخیره نتایج
                await self._save_lottery_results(winners, prize_amount, 
                                               len(participants), time.time() - start_time)
                
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
    
    async def _get_participants_with_weights(self) -> List[Dict]:
        """دریافت شرکت‌کنندگان با وزن‌های محاسبه شده"""
        participants = []
        current_time = int(time.time())
        
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            cursor.execute("""
                SELECT u.user_id, u.username, u.first_name, u.total_participations,
                       u.subscription_end, u.wallet_address, u.referral_count,
                       u.active_referrals, u.trust_score, u.win_count,
                       COUNT(r.referred_id) as total_refs,
                       SUM(CASE WHEN r.subscription_purchased = 1 THEN 1 ELSE 0 END) as active_refs
                FROM users u
                LEFT JOIN referrals r ON u.user_id = r.referrer_id
                WHERE u.subscription_end > ? 
                AND u.wallet_address IS NOT NULL
                AND u.is_banned = 0
                GROUP BY u.user_id
            """, (current_time,))
            
            users = cursor.fetchall()
            for user in users:
                # محاسبه وزن هوشمند
                weight = self._calculate_weight(user)
                
                participants.append({
                    "user_id": user[0],
                    "username": user[1] or f"User_{user[0]}",
                    "first_name": user[2] or "",
                    "total_participations": user[3] or 0,
                    "subscription_end": user[4],
                    "wallet_address": user[5],
                    "referral_count": user[6] or 0,
                    "active_referrals": user[7] or 0,
                    "trust_score": user[8] or 1.0,
                    "win_count": user[9] or 0,
                    "total_refs": user[10] or 0,
                    "active_refs": user[11] or 0,
                    "weight": weight
                })
        
        return participants
    
    def _calculate_weight(self, user_data: tuple) -> float:
        """محاسبه وزن با استفاده از فاکتورهای متعدد"""
        weight = 1.0
        
        # 1. فاکتور رفرال (حداکثر +50%)
        active_refs = user_data[11] if len(user_data) > 11 else 0
        if active_refs > 0:
            weight += min(0.5, active_refs * Config.REFERRAL_BONUS)
        
        # 2. فاکتور مشارکت (حداکثر +30%)
        participations = user_data[3] or 0
        if participations > 0:
            weight += min(0.3, participations * 0.01)
        
        # 3. فاکتور اعتماد (حداکثر +20%)
        trust_score = user_data[8] or 1.0
        weight += (trust_score - 1.0) * 0.2
        
        # 4. کاهش شانس برای برندگان قبلی (حداکثر -80%)
        win_count = user_data[9] or 0
        if win_count > 0:
            weight *= max(0.2, 1.0 - (win_count * 0.3))
        
        # 5. فاکتور تصادفی برای عدالت
        weight *= random.uniform(0.85, 1.15)
        
        return max(0.1, weight)
    
    async def _select_winners_ai(self, participants: List[Dict], count: int) -> List[Dict]:
        """انتخاب برندگان با استفاده از هوش مصنوعی و الگوریتم رولت"""
        if not participants:
            return []
        
        count = min(count, len(participants))
        
        # اگر مدل AI وجود دارد، از آن استفاده کنیم
        if self.ai_model is not None:
            try:
                # آماده‌سازی داده‌ها برای AI
                X = []
                for p in participants:
                    features = [
                        p.get("total_participations", 0),
                        p.get("referral_count", 0),
                        p.get("active_referrals", 0),
                        p.get("trust_score", 1.0),
                        p.get("win_count", 0),
                        p.get("weight", 1.0)
                    ]
                    X.append(features)
                
                # پیش‌بینی با AI
                predictions = self.ai_model.predict_proba(X)
                
                # ترکیب پیش‌بینی AI با وزن‌ها
                for i, p in enumerate(participants):
                    ai_score = predictions[i][1] if len(predictions[i]) > 1 else 0.5
                    p["weight"] = p.get("weight", 1.0) * (0.7 + 0.3 * ai_score)
            except Exception as e:
                logger.error(f"AI prediction error: {e}")
        
        # انتخاب با روش رولت وزنی
        selected_winners = []
        available = participants.copy()
        
        for _ in range(count):
            if not available:
                break
            
            total_weight = sum(p["weight"] for p in available)
            r = random.random() * total_weight
            cumulative = 0
            
            for i, participant in enumerate(available):
                cumulative += participant["weight"]
                if r <= cumulative:
                    selected = available.pop(i)
                    selected_winners.append(selected)
                    break
        
        return selected_winners
    
    async def _save_lottery_results(self, winners: List[Dict], prize_amount: int,
                                  participants_count: int, execution_time: float):
        """ذخیره نتایج قرعه‌کشی"""
        lottery_id = int(time.time())
        winner_ids = [w["user_id"] for w in winners]
        
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            
            # ذخیره قرعه‌کشی
            cursor.execute("""
                INSERT INTO lotteries 
                (lottery_id, created_at, winners_count, prize_amount, status, 
                 winner_ids, participants_count, ended_at, execution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (lottery_id, int(time.time()), len(winners), prize_amount, "completed",
                  json.dumps(winner_ids), participants_count, int(time.time()), execution_time))
            
            # به‌روزرسانی کاربران
            for winner in winners:
                if winner["user_id"] % Config.SHARD_COUNT == shard_id:
                    cursor.execute("""
                        UPDATE users 
                        SET is_winner = 1, 
                            won_amount = ?,
                            win_count = win_count + 1,
                            total_participations = total_participations + 1
                        WHERE user_id = ?
                    """, (prize_amount, winner["user_id"]))
                    
                    # بروزرسانی برندگان قبلی
                    cursor.execute("""
                        INSERT INTO previous_winners (user_id, last_win_time, win_count, total_prizes, avg_prize)
                        VALUES (?, ?, 1, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET 
                            last_win_time = excluded.last_win_time,
                            win_count = win_count + 1,
                            total_prizes = total_prizes + ?,
                            avg_prize = (total_prizes + ?) / (win_count + 1)
                    """, (winner["user_id"], int(time.time()), prize_amount, prize_amount,
                          prize_amount, prize_amount))
            
            self.db.shards[shard_id].commit()
        
        # به‌روزرسانی مدل AI با داده‌های جدید
        self._update_ai_model(winners, participants_count)
    
    def _update_ai_model(self, winners: List[Dict], participants_count: int):
        """به‌روزرسانی مدل AI با داده‌های جدید"""
        if self.ai_model is None:
            return
        
        try:
            # آماده‌سازی داده‌های آموزشی جدید
            X_train = []
            y_train = []
            
            # داده‌های برندگان
            for winner in winners:
                X_train.append([
                    winner.get("total_participations", 0),
                    winner.get("referral_count", 0),
                    winner.get("active_referrals", 0),
                    winner.get("trust_score", 1.0),
                    winner.get("win_count", 0),
                    winner.get("weight", 1.0)
                ])
                y_train.append(1)
            
            # داده‌های شرکت‌کنندگان غیربرنده (نمونه‌گیری)
            # اینجا می‌توان داده‌های بیشتری جمع‌آوری کرد
            
            # به‌روزرسانی مدل (در عمل نیاز به داده‌های بیشتر دارد)
            # self.ai_model.fit(X_train, y_train)
            
            # ذخیره مدل
            with open(Config.AI_MODEL_PATH, 'wb') as f:
                pickle.dump(self.ai_model, f)
            
            logger.info("AI model updated")
        except Exception as e:
            logger.error(f"AI model update error: {e}")
    
    async def _notify_winner(self, winner: Dict, prize_amount: int):
        """اعلام برنده"""
        # توسط ربات اصلی انجام می‌شود
        pass

# ==================== ربات اصلی نسخه ۲ ====================
class LotteryBotV2:
    def __init__(self):
        self.db = AdvancedDatabase()
        self.translations = TranslationSystem()
        self.payment = AdvancedPaymentSystem(self.db)
        self.lottery = AILotterySystem(self.db, self.payment)
        self.application = None
        self.bot_username = "UTYOB_Bot"
        self.user_states = {}
        self.lottery_state = {}
        self.pending_withdrawals = {}
        self.broadcast_queue = Queue()
        self.stats_cache = {}
        
        # وضعیت‌های مکالمه
        self.WAITING_WALLET, self.WAITING_WITHDRAW, self.WAITING_BROADCAST, \
        self.WAITING_MANUAL_VERIFY, self.WAITING_API_KEY, self.WAITING_POLL = range(6)
    
    async def start(self):
        """راه‌اندازی ربات"""
        await self.payment.initialize()
        
        # راه‌اندازی Prometheus metrics
        start_http_server(9090)
        
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        self._register_handlers()
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("🚀 Bot V2 started successfully!")
        
        # راه‌اندازی Flask API
        self._start_flask_server()
        
        # پردازش صف پیام‌ها
        asyncio.create_task(self._process_broadcast_queue())
        
        while True:
            await asyncio.sleep(1)
    
    def _register_handlers(self):
        """ثبت هندلرها"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("guidance", self.guidance_command))
        self.application.add_handler(CommandHandler("language", self.language_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Callback handlers
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Message handlers with conversation
        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^🎰 شرکت در قرعه‌کشی$|^🎰 Join Lottery$|^🎰 Piyangoya Katıl$"), self.start_lottery_join),
                MessageHandler(filters.Regex("^✅ پرداخت کردم$|^✅ I have paid$|^✅ Ödedim$"), self.handle_payment_confirmation),
                MessageHandler(filters.Regex("^👥 رفرال$|^👥 Referral$|^👥 Davet$"), self.handle_referral),
                MessageHandler(filters.Regex("^📖 راهنمایی$|^📖 Guidance$|^📖 Rehber$"), self.handle_guidance),
                MessageHandler(filters.Regex("^🌐 تغییر زبان$|^🌐 Change Language$|^🌐 Dil Değiştir$"), self.handle_language_change),
                MessageHandler(filters.Regex("^🔧 پنل مدیریت$|^🔧 Admin Panel$|^🔧 Yönetim Paneli$"), self.show_admin_panel),
                MessageHandler(filters.Regex("^📊 آمار$|^📊 Statistics$|^📊 İstatistikler$"), self.show_stats),
            ],
            states={
                self.WAITING_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_wallet_input)],
                self.WAITING_WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_withdraw_wallet)],
                self.WAITING_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_broadcast_message)],
                self.WAITING_MANUAL_VERIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_manual_verify)],
                self.WAITING_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_api_key)],
                self.WAITING_POLL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_poll_creation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)]
        )
        self.application.add_handler(conv_handler)
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    # ==================== Command Handlers ====================
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور استارت"""
        user = update.effective_user
        user_id = user.id
        
        # بررسی رفرال
        if context.args:
            ref_code = context.args[0]
            if ref_code.startswith("ref_"):
                await self._process_referral(user_id, ref_code[4:])
        
        # ایجاد/دریافت کاربر
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
        
        # منوی اصلی
        keyboard = [
            [KeyboardButton(self.translations.get_text(lang, "join_lottery"))],
            [KeyboardButton(self.translations.get_text(lang, "referral")), 
             KeyboardButton(self.translations.get_text(lang, "guidance"))],
            [KeyboardButton(self.translations.get_text(lang, "change_language"))]
        ]
        
        # دکمه پنل ادمین
        if str(user_id) in [str(a) for a in Config.ADMIN_IDS]:
            keyboard.append([
                KeyboardButton(self.translations.get_text(lang, "admin_panel")),
                KeyboardButton(self.translations.get_text(lang, "view_stats"))
            ])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = self.translations.get_text(
            lang, "welcome", bot_name="UTYOB Lottery Bot"
        )
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def guidance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور راهنمایی"""
        user = update.effective_user
        db_user = await self.db.get_user(user.id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        await update.message.reply_text(
            self.translations.get_text(lang, "guidance_text", amount=Config.AMOUNT_USD),
            parse_mode="Markdown"
        )
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور تغییر زبان"""
        await self.handle_language_change(update, context)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور وضعیت"""
        user = update.effective_user
        db_user = await self.db.get_user(user.id)
        if not db_user:
            await update.message.reply_text("Please start the bot first with /start")
            return
        
        lang = db_user.get("language", "en")
        
        # وضعیت اشتراک
        subscription_end = db_user.get("subscription_end", 0)
        if subscription_end > int(time.time()):
            status = self.translations.get_text(
                lang, "subscription_active",
                date=datetime.fromtimestamp(subscription_end).strftime("%Y-%m-%d %H:%M")
            )
        else:
            status = self.translations.get_text(lang, "subscription_expired")
        
        # وضعیت قرعه‌کشی
        lottery_status = self.translations.get_text(
            lang, "lottery_status",
            status="Active" if self.lottery.is_running else "Idle",
            participants=len(self.lottery.participants_cache) if self.lottery.is_running else 0,
            winners=len(self.lottery.winners),
            prize=db_user.get("won_amount", 0)
        )
        
        await update.message.reply_text(f"{status}\n\n{lottery_status}")
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو عملیات"""
        user = update.effective_user
        self.user_states.pop(user.id, None)
        await update.message.reply_text("❌ Operation cancelled.")
        return ConversationHandler.END
    
    # ==================== Message Handlers ====================
    async def start_lottery_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند ثبت‌نام در قرعه‌کشی"""
        user = update.effective_user
        user_id = user.id
        
        db_user = await self.db.get_user(user_id)
        if not db_user:
            await self.start_command(update, context)
            return
        
        lang = db_user.get("language", "en")
        
        # بررسی اشتراک
        if db_user.get("subscription_end", 0) > int(time.time()):
            await update.message.reply_text(
                self.translations.get_text(lang, "already_paid")
            )
            return
        
        # درخواست آدرس کیف پول
        context.user_data["state"] = self.WAITING_WALLET
        await update.message.reply_text(
            self.translations.get_text(lang, "lottery_join")
        )
        
        return self.WAITING_WALLET
    
    async def handle_wallet_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش آدرس کیف پول"""
        user = update.effective_user
        user_id = user.id
        wallet = update.message.text.strip()
        
        db_user = await self.db.get_user(user_id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        # اعتبارسنجی آدرس
        if not self._validate_tron_address(wallet):
            await update.message.reply_text(
                self.translations.get_text(lang, "invalid_wallet")
            )
            return self.WAITING_WALLET
        
        # ذخیره آدرس
        await self.db.execute_query(
            user_id,
            "UPDATE users SET wallet_address = ? WHERE user_id = ?",
            (wallet, user_id)
        )
        
        # پاک کردن وضعیت
        context.user_data.pop("state", None)
        
        # نمایش اطلاعات واریز با دکمه "پرداخت کردم"
        keyboard = [
            [InlineKeyboardButton(
                self.translations.get_text(lang, "i_have_paid"),
                callback_data=f"paid_{user_id}"
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
        
        # ذخیره آدرس برای بررسی بعدی
        context.user_data["pending_wallet"] = wallet
        
        return ConversationHandler.END
    
    async def handle_payment_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید پرداخت توسط کاربر"""
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
        
        # پیام در حال بررسی
        status_msg = await update.message.reply_text(
            self.translations.get_text(lang, "checking_payment")
        )
        
        # بررسی پرداخت
        verified = await self.payment.verify_payment(
            user_id, wallet, Config.WALLET_ADDRESS, Config.AMOUNT_USD
        )
        
        if verified:
            # تایید و فعال‌سازی
            subscription_end = int(time.time()) + 30 * 24 * 3600
            await self.db.execute_query(
                user_id,
                "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                (subscription_end, user_id)
            )
            
            await status_msg.edit_text(
                self.translations.get_text(lang, "payment_verified")
            )
        else:
            await status_msg.edit_text(
                self.translations.get_text(lang, "payment_not_found", amount=Config.AMOUNT_USD)
            )
            
            # دکمه تلاش مجدد
            keyboard = [[InlineKeyboardButton("🔄 Try Again", callback_data="retry_payment")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                self.translations.get_text(lang, "payment_failed", amount=Config.AMOUNT_USD),
                reply_markup=reply_markup
            )
    
    async def handle_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش اطلاعات رفرال"""
        user = update.effective_user
        user_id = user.id
        
        db_user = await self.db.get_user(user_id)
        if not db_user:
            await self.start_command(update, context)
            return
        
        lang = db_user.get("language", "en")
        
        referral_code = db_user.get("referral_code", "")
        total_refs = db_user.get("referral_count", 0)
        active_refs = db_user.get("active_referrals", 0)
        
        # محاسبه ضریب پاداش
        multiplier = 1.0 + (active_refs * Config.REFERRAL_BONUS)
        
        await update.message.reply_text(
            self.translations.get_text(
                lang, "referral_text",
                bot_username=self.bot_username,
                code=referral_code,
                total=total_refs,
                active=active_refs,
                multiplier=round(multiplier, 2)
            ),
            parse_mode="Markdown"
        )
    
    async def handle_guidance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش راهنمایی کامل"""
        user = update.effective_user
        db_user = await self.db.get_user(user.id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        await update.message.reply_text(
            self.translations.get_text(lang, "guidance_text", amount=Config.AMOUNT_USD),
            parse_mode="Markdown"
        )
    
    async def handle_language_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل مدیریت"""
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
            [InlineKeyboardButton(self.translations.get_text(lang, "start_lottery"), 
                                 callback_data="admin_start_lottery")],
            [InlineKeyboardButton(self.translations.get_text(lang, "manual_verify"), 
                                 callback_data="admin_manual_verify")],
            [InlineKeyboardButton(self.translations.get_text(lang, "poll"), 
                                 callback_data="admin_poll")],
            [InlineKeyboardButton(self.translations.get_text(lang, "restart_lottery"), 
                                 callback_data="admin_restart_lottery")],
            [InlineKeyboardButton(self.translations.get_text(lang, "pay_winners"), 
                                 callback_data="admin_pay_winners")],
            [InlineKeyboardButton(self.translations.get_text(lang, "add_api"), 
                                 callback_data="admin_add_api")],
            [InlineKeyboardButton(self.translations.get_text(lang, "view_stats"), 
                                 callback_data="admin_stats")],
            [InlineKeyboardButton("📊 Live Metrics", callback_data="admin_metrics")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **Admin Panel**\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار"""
        user = update.effective_user
        db_user = await self.db.get_user(user.id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        # دریافت آمار از دیتابیس
        stats = await self._get_system_stats()
        
        await update.message.reply_text(
            self.translations.get_text(
                lang, "admin_stats",
                users=stats["users"],
                active=stats["active_subscriptions"],
                prizes=stats["total_prizes"],
                winners=stats["total_winners"],
                lotteries=stats["total_lotteries"],
                referrals=stats["total_referrals"]
            )
        )
    
    # ==================== Callback Handlers ====================
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
        if data.startswith("lang_"):
            lang_code = data.split("_")[1]
            await self._change_language(user_id, lang_code, query, lang)
        
        elif data.startswith("paid_"):
            await self._handle_paid_button(query, user_id, lang)
        
        elif data == "retry_payment":
            await self._retry_payment(query, user_id, lang)
        
        elif data.startswith("admin_"):
            await self._handle_admin_actions(query, user_id, lang, data)
        
        elif data.startswith("lottery_confirm_"):
            parts = data.split("_")
            if len(parts) == 4:
                winners_count = int(parts[2])
                prize_amount = int(parts[3])
                await self._execute_lottery(query, user_id, lang, winners_count, prize_amount)
        
        elif data.startswith("winner_withdraw_"):
            winner_id = int(data.split("_")[2])
            if winner_id == user_id:
                context.user_data["state"] = self.WAITING_WITHDRAW
                await query.edit_message_text(
                    self.translations.get_text(lang, "enter_withdraw_wallet")
                )
                return self.WAITING_WITHDRAW
    
    # ==================== Helper Methods ====================
    async def _change_language(self, user_id: int, lang_code: str, query, current_lang: str):
        """تغییر زبان کاربر"""
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
            
            # دریافت نام زبان
            lang_names = {"en": "English 🇬🇧", "fa": "فارسی 🇮🇷", "tr": "Türkçe 🇹🇷"}
            
            await query.edit_message_text(
                self.translations.get_text(
                    current_lang, "language_changed", 
                    lang=lang_names.get(lang_code, lang_code)
                )
            )
            
            # نمایش منو با زبان جدید
            await self.start_command(query.message, None)
    
    async def _handle_paid_button(self, query, user_id: int, lang: str):
        """پردازش دکمه پرداخت کردم"""
        await query.edit_message_text(
            self.translations.get_text(lang, "checking_payment")
        )
        
        # بررسی پرداخت
        db_user = await self.db.get_user(user_id)
        wallet = db_user.get("wallet_address")
        
        if wallet:
            verified = await self.payment.verify_payment(
                user_id, wallet, Config.WALLET_ADDRESS, Config.AMOUNT_USD
            )
            
            if verified:
                subscription_end = int(time.time()) + 30 * 24 * 3600
                await self.db.execute_query(
                    user_id,
                    "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                    (subscription_end, user_id)
                )
                
                await query.message.reply_text(
                    self.translations.get_text(lang, "payment_verified")
                )
            else:
                await query.message.reply_text(
                    self.translations.get_text(lang, "payment_not_found", amount=Config.AMOUNT_USD)
                )
    
    async def _retry_payment(self, query, user_id: int, lang: str):
        """تلاش مجدد برای بررسی پرداخت"""
        await query.edit_message_text(
            self.translations.get_text(lang, "checking_payment")
        )
        
        db_user = await self.db.get_user(user_id)
        wallet = db_user.get("wallet_address")
        
        if wallet:
            verified = await self.payment.verify_payment(
                user_id, wallet, Config.WALLET_ADDRESS, Config.AMOUNT_USD
            )
            
            if verified:
                subscription_end = int(time.time()) + 30 * 24 * 3600
                await self.db.execute_query(
                    user_id,
                    "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                    (subscription_end, user_id)
                )
                
                await query.message.reply_text(
                    self.translations.get_text(lang, "payment_verified")
                )
            else:
                keyboard = [[InlineKeyboardButton("🔄 Try Again", callback_data="retry_payment")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    self.translations.get_text(lang, "payment_failed", amount=Config.AMOUNT_USD),
                    reply_markup=reply_markup
                )
    
    async def _handle_admin_actions(self, query, admin_id: int, lang: str, action: str):
        """پردازش اقدامات مدیریتی"""
        if admin_id not in Config.ADMIN_IDS:
            await query.edit_message_text("⛔ Access Denied!")
            return
        
        action_type = action.replace("admin_", "")
        
        if action_type == "start_lottery":
            await self._admin_start_lottery(query, admin_id, lang)
        elif action_type == "broadcast":
            self.user_states[admin_id] = {"awaiting_broadcast": True}
            await query.edit_message_text("📢 Enter your broadcast message:")
        elif action_type == "manual_verify":
            self.user_states[admin_id] = {"awaiting_manual_verify": True}
            await query.edit_message_text("✅ Enter the user ID to verify manually:")
        elif action_type == "add_api":
            self.user_states[admin_id] = {"awaiting_api_key": True}
            await query.edit_message_text("🔑 Enter the new API key:")
        elif action_type == "pay_winners":
            await self._admin_pay_winners(query, admin_id, lang)
        elif action_type == "restart_lottery":
            await self._admin_restart_lottery(query, admin_id, lang)
        elif action_type == "poll":
            self.user_states[admin_id] = {"awaiting_poll": True}
            await query.edit_message_text("📊 Enter your poll question and options (format: question|opt1|opt2|opt3):")
        elif action_type == "stats":
            await self._admin_stats(query, admin_id, lang)
        elif action_type == "metrics":
            await self._admin_metrics(query, admin_id, lang)
    
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
        
        self.lottery_state[admin_id] = {"step": "confirm_start"}
    
    async def _admin_pay_winners(self, query, admin_id: int, lang: str):
        """واریز به برندگان توسط ادمین"""
        await query.edit_message_text("💰 Processing payments to winners...")
        
        # دریافت برندگان
        winners = []
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            cursor.execute("""
                SELECT user_id, wallet_address, won_amount 
                FROM users 
                WHERE is_winner = 1 AND won_amount > 0
            """)
            
            winners.extend(cursor.fetchall())
        
        if not winners:
            await query.message.reply_text("❌ No winners to pay.")
            return
        
        # پردازش پرداخت‌ها
        total_amount = 0
        paid_count = 0
        
        for winner in winners:
            total_amount += winner[2]
            paid_count += 1
            
            # بروزرسانی وضعیت
            cursor = self.db.shards[winner[0] % Config.SHARD_COUNT].cursor()
            cursor.execute("""
                UPDATE users SET is_winner = 0, won_amount = 0 
                WHERE user_id = ?
            """, (winner[0],))
            self.db.shards[winner[0] % Config.SHARD_COUNT].commit()
        
        await query.message.reply_text(
            self.translations.get_text(
                lang, "admin_payment_processed",
                amount=total_amount,
                winners=paid_count
            )
        )
    
    async def _admin_restart_lottery(self, query, admin_id: int, lang: str):
        """شروع مجدد قرعه‌کشی"""
        for shard_id in range(Config.SHARD_COUNT):
            cursor = self.db.shards[shard_id].cursor()
            cursor.execute("""
                UPDATE lotteries SET status = 'reset' WHERE status = 'active'
            """)
            cursor.execute("DELETE FROM lottery_participants WHERE lottery_id = 0")
            self.db.shards[shard_id].commit()
        
        self.lottery.participants_cache = {}
        
        await query.edit_message_text(
            self.translations.get_text(lang, "admin_lottery_reset")
        )
    
    async def _admin_stats(self, query, admin_id: int, lang: str):
        """نمایش آمار سیستم"""
        stats = await self._get_system_stats()
        
        await query.edit_message_text(
            self.translations.get_text(
                lang, "admin_stats",
                users=stats["users"],
                active=stats["active_subscriptions"],
                prizes=stats["total_prizes"],
                winners=stats["total_winners"],
                lotteries=stats["total_lotteries"],
                referrals=stats["total_referrals"]
            )
        )
    
    async def _admin_metrics(self, query, admin_id: int, lang: str):
        """نمایش متریک‌های سیستم"""
        metrics = {
            "CPU": psutil.cpu_percent(),
            "Memory": psutil.virtual_memory().percent,
            "Disk": psutil.disk_usage('/').percent,
            "Queue Size": self.payment.verification_queue.qsize(),
            "API Keys": len(self.payment.api_keys),
            "Cache Size": len(self.db.cache)
        }
        
        metrics_text = "📊 **System Metrics**\n\n"
        for key, value in metrics.items():
            metrics_text += f"• {key}: {value}\n"
        
        await query.edit_message_text(metrics_text, parse_mode="Markdown")
    
    # ==================== Payment Handling ====================
    async def handle_withdraw_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش آدرس برداشت برنده"""
        user = update.effective_user
        user_id = user.id
        wallet = update.message.text.strip()
        
        db_user = await self.db.get_user(user_id)
        lang = db_user.get("language", "en") if db_user else "en"
        
        if not self._validate_tron_address(wallet):
            await update.message.reply_text(
                self.translations.get_text(lang, "invalid_wallet")
            )
            return self.WAITING_WITHDRAW
        
        # ذخیره آدرس
        await self.db.execute_query(
            user_id,
            "UPDATE users SET wallet_address = ? WHERE user_id = ?",
            (wallet, user_id)
        )
        
        context.user_data.pop("state", None)
        
        # ارسال به ادمین
        won_amount = db_user.get("won_amount", 0)
        for admin_id in Config.ADMIN_IDS:
            try:
                await self.application.bot.send_message(
                    admin_id,
                    f"💰 **Withdrawal Request**\n"
                    f"User: {user_id}\n"
                    f"Wallet: {wallet}\n"
                    f"Amount: ${won_amount}\n"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        await update.message.reply_text(
            self.translations.get_text(lang, "withdraw_pending")
        )
        
        return ConversationHandler.END
    
    # ==================== Admin Message Handlers ====================
    async def handle_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام همگانی"""
        user = update.effective_user
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return ConversationHandler.END
        
        message = update.message.text
        
        # اضافه کردن به صف
        await self.broadcast_queue.put(message)
        
        await update.message.reply_text("📢 Broadcast message added to queue. Sending to all users...")
        
        context.user_data.pop("state", None)
        return ConversationHandler.END
    
    async def handle_manual_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید دستی کاربر"""
        user = update.effective_user
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return ConversationHandler.END
        
        try:
            user_id_to_verify = int(update.message.text.strip())
            
            # فعال‌سازی اشتراک
            subscription_end = int(time.time()) + 30 * 24 * 3600
            await self.db.execute_query(
                user_id_to_verify,
                "UPDATE users SET subscription_end = ? WHERE user_id = ?",
                (subscription_end, user_id_to_verify)
            )
            
            await update.message.reply_text(
                f"✅ User {user_id_to_verify} verified manually."
            )
            
            # اطلاع به کاربر
            try:
                await self.application.bot.send_message(
                    user_id_to_verify,
                    "✅ Your subscription has been activated by admin."
                )
            except:
                pass
            
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please enter a number.")
        
        context.user_data.pop("state", None)
        return ConversationHandler.END
    
    async def handle_add_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اضافه کردن API Key جدید"""
        user = update.effective_user
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return ConversationHandler.END
        
        api_key = update.message.text.strip()
        
        if await self.payment.add_api_key(api_key):
            await update.message.reply_text(
                f"✅ New API key added successfully!\nTotal API keys: {len(self.payment.api_keys)}"
            )
        else:
            await update.message.reply_text("❌ API key already exists.")
        
        context.user_data.pop("state", None)
        return ConversationHandler.END
    
    async def handle_poll_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ایجاد نظر سنجی"""
        user = update.effective_user
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access Denied!")
            return ConversationHandler.END
        
        poll_data = update.message.text.split("|")
        
        if len(poll_data) < 3:
            await update.message.reply_text(
                "❌ Invalid format. Use: question|option1|option2|option3"
            )
            return self.WAITING_POLL
        
        question = poll_data[0]
        options = poll_data[1:]
        
        # ارسال نظر سنجی به همه کاربران
        await self._send_poll_to_all(question, options)
        
        await update.message.reply_text(
            f"✅ Poll created successfully!\nQuestion: {question}\nOptions: {', '.join(options)}"
        )
        
        context.user_data.pop("state", None)
        return ConversationHandler.END
    
    # ==================== Lottery Execution ====================
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
                # دریافت زبان برنده
                winner_db = await self.db.get_user(winner["user_id"])
                winner_lang = winner_db.get("language", "en") if winner_db else "en"
                
                await self.application.bot.send_message(
                    winner["user_id"],
                    self.translations.get_text(
                        winner_lang, "winner_announce", amount=prize_amount
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            self.translations.get_text(winner_lang, "withdraw"),
                            callback_data=f"winner_withdraw_{winner['user_id']}"
                        )]
                    ])
                )
            except Exception as e:
                logger.error(f"Error notifying winner {winner['user_id']}: {e}")
        
        await query.message.reply_text(
            self.translations.get_text(lang, "lottery_complete")
        )
    
    # ==================== Utility Methods ====================
    def _validate_tron_address(self, address: str) -> bool:
        """اعتبارسنجی آدرس TRC20"""
        if not address or len(address) != 34:
            return False
        
        if not address.startswith("T"):
            return False
        
        try:
            decoded = base58.b58decode(address)
            return len(decoded) == 21
        except:
            return False
    
    async def _process_referral(self, user_id: int, ref_code: str):
        """پردازش رفرال"""
        try:
            # پیدا کردن کاربر معرف
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
                # ثبت رفرال
                await self.db.execute_query(
                    user_id,
                    "INSERT INTO referrals (referrer_id, referred_id, created_at) VALUES (?, ?, ?)",
                    (referrer_id, user_id, int(time.time()))
                )
                
                # به‌روزرسانی آمار
                await self.db.execute_query(
                    referrer_id,
                    "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
                    (referrer_id,)
                )
                
                logger.info(f"Referral processed: {referrer_id} -> {user_id}")
        except Exception as e:
            logger.error(f"Referral processing error: {e}")
    
    async def _get_system_stats(self) -> Dict:
        """دریافت آمار سیستم"""
        try:
            stats = {
                "users": 0,
                "active_subscriptions": 0,
                "total_prizes": 0,
                "total_winners": 0,
                "total_lotteries": 0,
                "total_referrals": 0
            }
            
            for shard_id in range(Config.SHARD_COUNT):
                cursor = self.db.shards[shard_id].cursor()
                
                # تعداد کاربران
                cursor.execute("SELECT COUNT(*) FROM users")
                stats["users"] += cursor.fetchone()[0]
                
                # اشتراک‌های فعال
                cursor.execute(
                    "SELECT COUNT(*) FROM users WHERE subscription_end > ?",
                    (int(time.time()),)
                )
                stats["active_subscriptions"] += cursor.fetchone()[0]
                
                # جوایز کل
                cursor.execute("SELECT SUM(won_amount) FROM users")
                result = cursor.fetchone()[0]
                if result:
                    stats["total_prizes"] += result
                
                # برندگان
                cursor.execute("SELECT COUNT(DISTINCT user_id) FROM previous_winners")
                stats["total_winners"] += cursor.fetchone()[0]
                
                # قرعه‌کشی‌ها
                cursor.execute("SELECT COUNT(*) FROM lotteries")
                stats["total_lotteries"] += cursor.fetchone()[0]
                
                # رفرال‌ها
                cursor.execute("SELECT COUNT(*) FROM referrals")
                stats["total_referrals"] += cursor.fetchone()[0]
            
            return stats
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {k: 0 for k in stats.keys()}
    
    async def _process_broadcast_queue(self):
        """پردازش صف پیام‌های همگانی"""
        while True:
            try:
                message = await self.broadcast_queue.get()
                
                # دریافت همه کاربران
                users = []
                for shard_id in range(Config.SHARD_COUNT):
                    cursor = self.db.shards[shard_id].cursor()
                    cursor.execute("SELECT user_id FROM users")
                    users.extend([row[0] for row in cursor.fetchall()])
                
                # ارسال پیام
                sent_count = 0
                for user_id in users:
                    try:
                        await self.application.bot.send_message(user_id, message)
                        sent_count += 1
                        await asyncio.sleep(0.1)  # جلوگیری از محدودیت
                    except:
                        pass
                
                logger.info(f"Broadcast sent to {sent_count} users")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                await asyncio.sleep(5)
    
    async def _send_poll_to_all(self, question: str, options: List[str]):
        """ارسال نظر سنجی به همه کاربران"""
        try:
            # دریافت همه کاربران
            users = []
            for shard_id in range(Config.SHARD_COUNT):
                cursor = self.db.shards[shard_id].cursor()
                cursor.execute("SELECT user_id FROM users")
                users.extend([row[0] for row in cursor.fetchall()])
            
            # ارسال نظر سنجی
            for user_id in users:
                try:
                    await self.application.bot.send_poll(
                        user_id,
                        question,
                        options,
                        is_anonymous=True
                    )
                    await asyncio.sleep(0.1)
                except:
                    pass
        except Exception as e:
            logger.error(f"Poll send error: {e}")
    
    # ==================== Flask API Server ====================
    def _start_flask_server(self):
        """راه‌اندازی سرور Flask برای میکروسرویس‌ها"""
        app = Flask(__name__)
        
        @app.route('/api/verify', methods=['POST'])
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
        
        @app.route('/api/lottery/start', methods=['POST'])
        async def start_lottery_endpoint():
            data = request.json
            winners_count = data.get('winners_count', 1)
            prize_amount = data.get('prize_amount', 100)
            
            if not all([winners_count, prize_amount]):
                return jsonify({"status": "error", "message": "Missing parameters"}), 400
            
            winners = await self.lottery.start_lottery(winners_count, prize_amount)
            
            return jsonify({
                "status": "success",
                "winners": len(winners),
                "winner_ids": [w["user_id"] for w in winners]
            })
        
        @app.route('/api/lottery/status', methods=['GET'])
        def lottery_status():
            return jsonify({
                "is_running": self.lottery.is_running,
                "winners": len(self.lottery.winners),
                "participants": len(self.lottery.participants_cache)
            })
        
        @app.route('/api/stats', methods=['GET'])
        async def stats_endpoint():
            stats = await self._get_system_stats()
            return jsonify(stats)
        
        @app.route('/api/health', methods=['GET'])
        def health():
            return jsonify({
                "status": "healthy",
                "shards": Config.SHARD_COUNT,
                "api_keys": len(self.payment.api_keys),
                "queue_size": self.payment.verification_queue.qsize(),
                "cache_size": len(self.db.cache),
                "timestamp": time.time()
            })
        
        def run_flask():
            app.run(host='0.0.0.0', port=5000, debug=False)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
    
    # ==================== Error Handler ====================
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """هندلر خطا"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_user:
                await update.message.reply_text(
                    "❌ An error occurred. Please try again later."
                )
        except:
            pass

# ==================== اجرای اصلی ====================
async def main():
    bot = LotteryBotV2()
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")