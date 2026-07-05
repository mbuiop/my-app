# ============================================
# ULTIMATE LOTTERY SYSTEM - app.py
# ============================================
# سیستم قرعه‌کشی فوق‌پیشرفته با مقیاس‌پذیری بالا
# معماری: 300 شارد + کش چندلایه + تایید اتوماتیک
# 
# نصب:
# pip install python-telegram-bot aiohttp base58 psutil flask flask-session redis
# 
# اجرا:
# python3 app.py

import asyncio
import json
import logging
import secrets
import string
import time
import hashlib
import hmac
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import gc

# ============================================
# کتابخانه‌های اصلی
# ============================================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

import aiohttp
import base58
import psutil

# ============================================
# Flask Web Framework
# ============================================
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from flask_session import Session
import redis

# ============================================
# تنظیمات پیشرفته (Config)
# ============================================
class Config:
    # توکن ربات
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    BOT_USERNAME = "@UTYOB_Bot"
    ADMIN_CHAT_ID = 123456789
    
    # آدرس دریافت پرداخت
    PAYMENT_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
    PAYMENT_AMOUNT = 100.0
    
    # کلیدهای API برای تایید تراکنش (چرخشی)
    API_KEYS = [
        "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
        # کلیدهای بیشتر برای مقیاس‌پذیری
    ]
    
    # شاردینگ - 300 شارد برای میلیون‌ها کاربر
    SHARD_COUNT = 300
    SHARD_ALGORITHM = "consistent_hashing"
    
    # کش - Redis با کلاستر
    REDIS_URL = "redis://localhost:6379/0"
    REDIS_CACHE_TTL = 3600  # 1 ساعت
    REDIS_SESSION_TTL = 86400  # 24 ساعت
    
    # دیتابیس - PostgreSQL با پول اتصالات
    DATABASE_URL = "postgresql+asyncpg://lottery:lottery_pass@localhost/lottery_db"
    DATABASE_POOL_SIZE = 200
    DATABASE_MAX_OVERFLOW = 400
    
    # زبان‌ها
    LANGUAGES = ["en", "fa", "ar"]
    DEFAULT_LANGUAGE = "en"
    
    # تنظیمات قرعه‌کشی
    MIN_PARTICIPANTS = 10
    MAX_WINNERS = 1000
    PRIZE_POOL_MIN = 100
    
    # امنیت
    JWT_SECRET = "your-super-secret-jwt-key-change-this"
    ENCRYPTION_KEY = "your-encryption-key"
    
    # تردها و پردازش موازی
    MAX_WORKERS = 50
    BATCH_SIZE = 100
    
    # مونیتورینگ
    ENABLE_METRICS = True
    LOG_LEVEL = "INFO"

config = Config()

# ============================================
# سیستم شاردینگ پیشرفته
# ============================================
class ConsistentHashRing:
    """حلقه هش سازگار برای شاردینگ"""
    
    def __init__(self, nodes: List[int], replicas: int = 150):
        self.nodes = nodes
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []
        self._build_ring()
    
    def _build_ring(self):
        """ساخت حلقه هش"""
        for node in self.nodes:
            for i in range(self.replicas):
                key = f"{node}:{i}"
                hash_val = self._hash(key)
                self.ring[hash_val] = node
        self.sorted_keys = sorted(self.ring.keys())
    
    def _hash(self, key: str) -> int:
        """تولید هش برای کلید"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    def get_node(self, key: str) -> int:
        """دریافت نود برای کلید"""
        if not self.ring:
            return 0
        
        hash_val = self._hash(key)
        for ring_key in self.sorted_keys:
            if hash_val <= ring_key:
                return self.ring[ring_key]
        return self.ring[self.sorted_keys[0]]

# ============================================
# دیتابیس شارد شده
# ============================================
class ShardedDatabase:
    """دیتابیس با پشتیبانی از شاردینگ"""
    
    def __init__(self):
        self.shard_count = config.SHARD_COUNT
        self.ring = ConsistentHashRing(list(range(self.shard_count)))
        self.data = {f"shard_{i}": {} for i in range(self.shard_count)}
        self.locks = {f"shard_{i}": asyncio.Lock() for i in range(self.shard_count)}
        self._init_shards()
    
    def _init_shards(self):
        """بارگذاری داده‌های شاردها از دیسک"""
        for i in range(self.shard_count):
            try:
                with open(f"shard_{i}.json", "r") as f:
                    self.data[f"shard_{i}"] = json.load(f)
            except:
                self.data[f"shard_{i}"] = {
                    "users": {},
                    "transactions": {},
                    "lotteries": [],
                    "winners": []
                }
                self._save_shard(i)
    
    def _save_shard(self, shard_id: int):
        """ذخیره شارد در دیسک"""
        try:
            with open(f"shard_{shard_id}.json", "w") as f:
                json.dump(self.data[f"shard_{shard_id}"], f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Error saving shard {shard_id}: {e}")
    
    def get_shard_id(self, user_id: int) -> int:
        """دریافت شارد برای کاربر"""
        return self.ring.get_node(str(user_id))
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """گرفتن اطلاعات کاربر از شارد مناسب"""
        shard_id = self.get_shard_id(user_id)
        shard_key = f"shard_{shard_id}"
        
        async with self.locks[shard_key]:
            return self.data[shard_key]["users"].get(str(user_id))
    
    async def save_user(self, user_id: int, data: Dict):
        """ذخیره اطلاعات کاربر در شارد مناسب"""
        shard_id = self.get_shard_id(user_id)
        shard_key = f"shard_{shard_id}"
        
        async with self.locks[shard_key]:
            self.data[shard_key]["users"][str(user_id)] = data
            self._save_shard(shard_id)
    
    async def get_all_users(self) -> List[Dict]:
        """گرفتن همه کاربران از همه شاردها"""
        all_users = []
        for i in range(self.shard_count):
            shard_key = f"shard_{i}"
            async with self.locks[shard_key]:
                users = list(self.data[shard_key]["users"].values())
                all_users.extend(users)
        return all_users
    
    async def get_users_with_subscription(self) -> List[Dict]:
        """گرفتن کاربران دارای اشتراک از همه شاردها"""
        users = await self.get_all_users()
        return [u for u in users if u.get("has_subscription", False)]
    
    async def get_transaction(self, tx_id: str) -> Optional[Dict]:
        """گرفتن تراکنش از همه شاردها"""
        for i in range(self.shard_count):
            shard_key = f"shard_{i}"
            async with self.locks[shard_key]:
                tx = self.data[shard_key]["transactions"].get(tx_id)
                if tx:
                    return tx
        return None
    
    async def save_transaction(self, tx_id: str, data: Dict):
        """ذخیره تراکنش در شارد مناسب"""
        shard_id = self.get_shard_id(data.get("user_id", 0))
        shard_key = f"shard_{shard_id}"
        
        async with self.locks[shard_key]:
            self.data[shard_key]["transactions"][tx_id] = data
            self._save_shard(shard_id)
    
    async def get_current_lottery(self) -> Optional[Dict]:
        """گرفتن قرعه‌کشی فعلی از شارد 0"""
        shard_key = "shard_0"
        async with self.locks[shard_key]:
            return self.data[shard_key].get("current_lottery")
    
    async def set_current_lottery(self, lottery: Dict):
        """تنظیم قرعه‌کشی فعلی در شارد 0"""
        shard_key = "shard_0"
        async with self.locks[shard_key]:
            self.data[shard_key]["current_lottery"] = lottery
            self._save_shard(0)
    
    async def add_lottery(self, lottery: Dict):
        """افزودن قرعه‌کشی به تاریخچه در شارد 0"""
        shard_key = "shard_0"
        async with self.locks[shard_key]:
            self.data[shard_key]["lotteries"].append(lottery)
            self._save_shard(0)
    
    async def get_previous_winners(self) -> List[int]:
        """گرفتن لیست برندگان قبلی از همه شاردها"""
        winners = []
        for i in range(self.shard_count):
            shard_key = f"shard_{i}"
            async with self.locks[shard_key]:
                shard_winners = self.data[shard_key].get("previous_winners", [])
                winners.extend(shard_winners)
        return winners
    
    async def add_previous_winner(self, user_id: int):
        """افزودن برنده به لیست برندگان قبلی در شارد مناسب"""
        shard_id = self.get_shard_id(user_id)
        shard_key = f"shard_{shard_id}"
        
        async with self.locks[shard_key]:
            if "previous_winners" not in self.data[shard_key]:
                self.data[shard_key]["previous_winners"] = []
            if user_id not in self.data[shard_key]["previous_winners"]:
                self.data[shard_key]["previous_winners"].append(user_id)
                self._save_shard(shard_id)

db = ShardedDatabase()

# ============================================
# سیستم کش قدرتمند (Redis + Memory)
# ============================================
class CacheManager:
    """مدیریت کش با Redis و کش حافظه"""
    
    def __init__(self):
        self.redis = None
        self.memory_cache = {}
        self.memory_cache_ttl = {}
        self._lock = asyncio.Lock()
        self._enabled = True
        self._init_redis()
    
    def _init_redis(self):
        """اتصال به Redis"""
        try:
            self.redis = redis.Redis.from_url(
                config.REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            self.redis.ping()
            logging.info("✅ Redis connected successfully")
        except Exception as e:
            logging.warning(f"⚠️ Redis connection failed: {e}. Using memory cache only.")
            self._enabled = False
            self.redis = None
    
    async def get(self, key: str) -> Optional[str]:
        """دریافت از کش با fallback به کش حافظه"""
        # کش حافظه
        if key in self.memory_cache:
            if self.memory_cache_ttl.get(key, 0) > time.time():
                return self.memory_cache[key]
            else:
                del self.memory_cache[key]
                del self.memory_cache_ttl[key]
        
        # Redis
        if self._enabled and self.redis:
            try:
                value = self.redis.get(key)
                if value:
                    # ذخیره در کش حافظه
                    self.memory_cache[key] = value
                    self.memory_cache_ttl[key] = time.time() + 300  # 5 دقیقه
                    return value
            except Exception as e:
                logging.error(f"Redis get error: {e}")
        
        return None
    
    async def set(self, key: str, value: str, ttl: int = config.REDIS_CACHE_TTL):
        """ذخیره در کش"""
        # کش حافظه
        self.memory_cache[key] = value
        self.memory_cache_ttl[key] = time.time() + min(ttl, 300)
        
        # Redis
        if self._enabled and self.redis:
            try:
                self.redis.setex(key, ttl, value)
            except Exception as e:
                logging.error(f"Redis set error: {e}")
    
    async def delete(self, key: str):
        """حذف از کش"""
        if key in self.memory_cache:
            del self.memory_cache[key]
            del self.memory_cache_ttl[key]
        
        if self._enabled and self.redis:
            try:
                self.redis.delete(key)
            except Exception as e:
                logging.error(f"Redis delete error: {e}")
    
    async def incr(self, key: str) -> int:
        """افزایش مقدار"""
        if self._enabled and self.redis:
            try:
                return self.redis.incr(key)
            except Exception as e:
                logging.error(f"Redis incr error: {e}")
        
        # Fallback to memory
        current = int(self.memory_cache.get(key, 0))
        new_value = current + 1
        self.memory_cache[key] = str(new_value)
        self.memory_cache_ttl[key] = time.time() + 300
        return new_value
    
    async def get_or_set(self, key: str, func, ttl: int = config.REDIS_CACHE_TTL):
        """دریافت یا تنظیم کش"""
        value = await self.get(key)
        if value is not None:
            return value
        
        # اجرای تابع برای دریافت مقدار
        if asyncio.iscoroutinefunction(func):
            value = await func()
        else:
            value = func()
        
        if value:
            await self.set(key, str(value) if not isinstance(value, str) else value, ttl)
        
        return value

cache = CacheManager()

# ============================================
# مدیریت ترجمه پیشرفته
# ============================================
class Translator:
    def __init__(self):
        self.translations = {
            "en": {
                "welcome": "🎰 *ULTIMATE LOTTERY BOT*\n\n"
                          "💰 Join the biggest lottery on Telegram!\n"
                          "🏆 Win up to $10,000 every week!\n"
                          "📱 Click the button below to open the app.",
                "start": "🚀 *Welcome to Ultimate Lottery!*\n\n"
                        "1️⃣ Subscribe by sending 100 USDT\n"
                        "2️⃣ Get entered into the lottery\n"
                        "3️⃣ Win amazing prizes!\n\n"
                        "🎯 Your referral code: `{code}`",
                "referral": "🔗 *REFERRAL PROGRAM*\n\n"
                           "Your referral code: `{code}`\n\n"
                           "🎁 You get $10 for each friend who subscribes!\n\n"
                           "Share this link:\n"
                           "https://t.me/{bot}?start={code}",
                "subscribe": "💎 *Subscribe to Lottery*\n\n"
                            "💰 Send exactly 100 USDT to:\n"
                            "`{address}`\n\n"
                            "📝 Then enter your TRC20 wallet address:",
                "invalid_wallet": "❌ Invalid TRC20 wallet address.",
                "wallet_saved": "✅ Wallet saved!\n\n"
                               "💰 Send 100 USDT to:\n"
                               "`{address}`\n\n"
                               "🔄 Click 'Verify Payment' after sending.",
                "payment_verified": "✅ *PAYMENT VERIFIED!*\n\n"
                                   "🎉 You are now subscribed to the lottery!\n"
                                   "🏆 Good luck!",
                "payment_failed": "❌ Payment verification failed.\n\n"
                                 "Please check:\n"
                                 "• Amount: 100 USDT\n"
                                 "• Address: {address}\n"
                                 "• Transaction confirmed",
                "already_subscribed": "✅ You already have an active subscription!",
                "no_subscription": "⚠️ You need an active subscription to participate.",
                "lottery_started": "🎰 *LOTTERY STARTED!*\n\n"
                                  "👥 Participants: {participants}\n"
                                  "💰 Prize Pool: ${prize_pool}\n"
                                  "🏆 Winners: {winners_count}\n\n"
                                  "🎲 Drawing winners...",
                "congratulations": "🎊 *CONGRATULATIONS!*\n\n"
                                  "🏆 You won ${amount}!\n\n"
                                  "💰 Click 'Withdraw' to claim your prize.",
                "not_winner": "😔 Better luck next time!\n\n"
                             "🎯 Stay subscribed for the next lottery.",
                "withdraw": "💰 *Withdraw Prize*\n\n"
                           "Enter your TRC20 wallet address:",
                "withdraw_success": "✅ *Withdrawal Submitted!*\n\n"
                                   "💰 Your prize will be sent shortly.",
                "admin_panel": "⚙️ *ADMIN PANEL*\n\n"
                              "📊 System Status:\n"
                              "👥 Users: {users}\n"
                              "🎯 Subscribed: {subscribed}\n"
                              "🏆 Winners: {winners}\n\n"
                              "Select an option:",
                "broadcast_sent": "✅ Broadcast sent to {count} users!",
                "manual_verify_done": "✅ Transaction verified manually!",
                "api_added": "✅ API key added successfully!",
                "withdraw_done": "✅ Withdrawals processed for {count} winners!",
                "restart_done": "✅ Lottery restarted!",
                "survey_sent": "✅ Survey sent to {count} users!",
                "lang_changed": "🌐 Language changed to {lang}",
                "help": "📖 *Help Center*\n\n"
                       "1️⃣ Subscribe: Send 100 USDT\n"
                       "2️⃣ Participate: Auto-entry\n"
                       "3️⃣ Win: Fair lottery draw\n"
                       "4️⃣ Withdraw: Claim prizes\n\n"
                       "🔗 Referral: Earn $10 per friend",
                "cancel": "❌ Operation cancelled.",
                "admin_broadcast": "📢 Enter your broadcast message:",
                "admin_manual_verify": "✅ Enter transaction ID to verify:",
                "admin_add_api": "🔑 Enter new API key:",
                "admin_survey": "📊 Enter survey question:",
                "admin_winners": "🏆 Enter number of winners:",
                "admin_prize": "💰 Enter prize amount per winner:",
                "lottery_cancelled": "❌ Lottery cancelled.",
                "user_status": "👤 User Status",
                "subscription": "📅 Subscription",
                "wallet": "🏦 Wallet",
                "not_set": "Not Set",
                "active": "Active",
                "inactive": "Inactive",
                "winner": "🏆 Winner",
                "total_won": "💰 Total Won",
                "referrals": "👥 Referrals",
                "earnings": "💵 Earnings",
                "share": "📤 Share",
                "copy": "📋 Copy",
                "refresh": "🔄 Refresh",
                "loading": "⏳ Loading...",
                "error": "❌ An error occurred.",
                "copied": "✅ Copied to clipboard!",
            },
            "fa": {
                "welcome": "🎰 *ربات قرعه‌کشی فوق‌پیشرفته*\n\n"
                          "💰 در بزرگ‌ترین قرعه‌کشی تلگرام شرکت کنید!\n"
                          "🏆 هر هفته تا ۱۰,۰۰۰ دلار برنده شوید!\n"
                          "📱 روی دکمه زیر کلیک کنید تا اپ باز شود.",
                "start": "🚀 *به قرعه‌کشی فوق‌پیشرفته خوش آمدید!*\n\n"
                        "۱️⃣ با ارسال ۱۰۰ دلار اشتراک بخرید\n"
                        "۲️⃣ وارد قرعه‌کشی می‌شوید\n"
                        "۳️⃣ جوایز شگفت‌انگیز ببرید!\n\n"
                        "🎯 کد رفرال شما: `{code}`",
                "referral": "🔗 *برنامه رفرال*\n\n"
                           "کد رفرال شما: `{code}`\n\n"
                           "🎁 به ازای هر دوست که اشتراک بخرد، ۱۰ دلار پاداش می‌گیرید!\n\n"
                           "لینک دعوت:\n"
                           "https://t.me/{bot}?start={code}",
                "subscribe": "💎 *اشتراک قرعه‌کشی*\n\n"
                            "💰 دقیقاً ۱۰۰ دلار به آدرس زیر ارسال کنید:\n"
                            "`{address}`\n\n"
                            "📝 سپس آدرس کیف پول TRC20 خود را وارد کنید:",
                "invalid_wallet": "❌ آدرس کیف پول TRC20 نامعتبر است.",
                "wallet_saved": "✅ کیف پول ذخیره شد!\n\n"
                               "💰 ۱۰۰ دلار به آدرس زیر ارسال کنید:\n"
                               "`{address}`\n\n"
                               "🔄 پس از ارسال، روی 'تایید پرداخت' کلیک کنید.",
                "payment_verified": "✅ *پرداخت تایید شد!*\n\n"
                                   "🎉 شما در قرعه‌کشی ثبت نام کردید!\n"
                                   "🏆 موفق باشید!",
                "payment_failed": "❌ تایید پرداخت ناموفق بود.\n\n"
                                 "لطفاً بررسی کنید:\n"
                                 "• مبلغ: ۱۰۰ دلار\n"
                                 "• آدرس: {address}\n"
                                 "• تایید تراکنش",
                "already_subscribed": "✅ شما قبلاً اشتراک فعال دارید!",
                "no_subscription": "⚠️ برای شرکت در قرعه‌کشی به اشتراک فعال نیاز دارید.",
                "lottery_started": "🎰 *قرعه‌کشی شروع شد!*\n\n"
                                  "👥 شرکت‌کنندگان: {participants}\n"
                                  "💰 جایزه نقدی: ${prize_pool}\n"
                                  "🏆 تعداد برندگان: {winners_count}\n\n"
                                  "🎲 در حال انتخاب برندگان...",
                "congratulations": "🎊 *تبریک!*\n\n"
                                  "🏆 شما ${amount} برنده شدید!\n\n"
                                  "💰 برای دریافت جایزه روی 'برداشت' کلیک کنید.",
                "not_winner": "😔 دفعه بعد بیشتر خوش شانس باشید!\n\n"
                             "🎯 برای قرعه‌کشی بعدی اشتراک خود را حفظ کنید.",
                "withdraw": "💰 *برداشت جایزه*\n\n"
                           "آدرس کیف پول TRC20 خود را وارد کنید:",
                "withdraw_success": "✅ *برداشت ثبت شد!*\n\n"
                                   "💰 جایزه شما به زودی واریز می‌شود.",
                "admin_panel": "⚙️ *پنل مدیریت*\n\n"
                              "📊 وضعیت سیستم:\n"
                              "👥 کاربران: {users}\n"
                              "🎯 اشتراک‌داران: {subscribed}\n"
                              "🏆 برندگان: {winners}\n\n"
                              "یک گزینه را انتخاب کنید:",
                "broadcast_sent": "✅ پیام به {count} کاربر ارسال شد!",
                "manual_verify_done": "✅ تراکنش به صورت دستی تایید شد!",
                "api_added": "✅ کلید API با موفقیت اضافه شد!",
                "withdraw_done": "✅ واریز برای {count} برنده انجام شد!",
                "restart_done": "✅ قرعه‌کشی مجدداً شروع شد!",
                "survey_sent": "✅ نظر سنجی به {count} کاربر ارسال شد!",
                "lang_changed": "🌐 زبان به {lang} تغییر یافت",
                "help": "📖 *راهنما*\n\n"
                       "۱️⃣ اشتراک: ارسال ۱۰۰ دلار\n"
                       "۲️⃣ شرکت: ثبت خودکار\n"
                       "۳️⃣ برنده شدن: قرعه‌کشی عادلانه\n"
                       "۴️⃣ برداشت: دریافت جایزه\n\n"
                       "🔗 رفرال: به ازای هر دوست ۱۰ دلار",
                "cancel": "❌ عملیات لغو شد.",
                "admin_broadcast": "📢 پیام خود را برای ارسال همگانی وارد کنید:",
                "admin_manual_verify": "✅ شناسه تراکنش را برای تایید وارد کنید:",
                "admin_add_api": "🔑 کلید API جدید را وارد کنید:",
                "admin_survey": "📊 سوال نظر سنجی را وارد کنید:",
                "admin_winners": "🏆 تعداد برندگان را وارد کنید:",
                "admin_prize": "💰 مبلغ جایزه هر برنده را وارد کنید:",
                "lottery_cancelled": "❌ قرعه‌کشی لغو شد.",
                "user_status": "👤 وضعیت کاربر",
                "subscription": "📅 اشتراک",
                "wallet": "🏦 کیف پول",
                "not_set": "تنظیم نشده",
                "active": "فعال",
                "inactive": "غیرفعال",
                "winner": "🏆 برنده",
                "total_won": "💰 مجموع برداشت",
                "referrals": "👥 رفرال",
                "earnings": "💵 درآمد",
                "share": "📤 اشتراک‌گذاری",
                "copy": "📋 کپی",
                "refresh": "🔄 بروزرسانی",
                "loading": "⏳ در حال بارگذاری...",
                "error": "❌ خطایی رخ داد.",
                "copied": "✅ کپی شد!",
            },
            "ar": {
                "welcome": "🎰 *بوت اليانصيب المتطور*\n\n"
                          "💰 شارك في أكبر يانصيب على تيليجرام!\n"
                          "🏆 اربح حتى ۱۰,۰۰۰ دولار كل أسبوع!\n"
                          "📱 اضغط على الزر أدناه لفتح التطبيق.",
                "start": "🚀 *مرحباً في اليانصيب المتطور!*\n\n"
                        "۱️⃣ اشترك بإرسال ۱۰۰ دولار\n"
                        "۲️⃣ تدخل في اليانصيب تلقائياً\n"
                        "۳️⃣ اربح جوائز مذهلة!\n\n"
                        "🎯 رمز الإحالة الخاص بك: `{code}`",
                "referral": "🔗 *برنامج الإحالة*\n\n"
                           "رمز الإحالة الخاص بك: `{code}`\n\n"
                           "🎁 تحصل على ۱۰ دولار لكل صديق يشترك!\n\n"
                           "رابط الدعوة:\n"
                           "https://t.me/{bot}?start={code}",
                "subscribe": "💎 *اشتراك اليانصيب*\n\n"
                            "💰 أرسل ۱۰۰ دولار بالضبط إلى:\n"
                            "`{address}`\n\n"
                            "📝 ثم أدخل عنوان محفظة TRC20 الخاص بك:",
                "invalid_wallet": "❌ عنوان محفظة TRC20 غير صالح.",
                "wallet_saved": "✅ تم حفظ المحفظة!\n\n"
                               "💰 أرسل ۱۰۰ دولار إلى:\n"
                               "`{address}`\n\n"
                               "🔄 بعد الإرسال، اضغط 'التحقق من الدفع'.",
                "payment_verified": "✅ *تم التحقق من الدفع!*\n\n"
                                   "🎉 لقد اشتركت في اليانصيب!\n"
                                   "🏆 حظاً سعيداً!",
                "payment_failed": "❌ فشل التحقق من الدفع.\n\n"
                                 "يرجى التحقق من:\n"
                                 "• المبلغ: ۱۰۰ دولار\n"
                                 "• العنوان: {address}\n"
                                 "• تأكيد المعاملة",
                "already_subscribed": "✅ لديك اشتراك نشط بالفعل!",
                "no_subscription": "⚠️ تحتاج إلى اشتراك نشط للمشاركة.",
                "lottery_started": "🎰 *بدأ اليانصيب!*\n\n"
                                  "👥 المشاركون: {participants}\n"
                                  "💰 مجموع الجوائز: ${prize_pool}\n"
                                  "🏆 عدد الفائزين: {winners_count}\n\n"
                                  "🎲 جاري اختيار الفائزين...",
                "congratulations": "🎊 *تهانينا!*\n\n"
                                  "🏆 لقد فزت بـ ${amount}!\n\n"
                                  "💰 اضغط 'سحب' للمطالبة بجائزتك.",
                "not_winner": "😔 حظاً أوفر في المرة القادمة!\n\n"
                             "🎯 استمر في الاشتراك لليانصيب القادم.",
                "withdraw": "💰 *سحب الجائزة*\n\n"
                           "أدخل عنوان محفظة TRC20 الخاص بك:",
                "withdraw_success": "✅ *تم تقديم طلب السحب!*\n\n"
                                   "💰 سيتم إرسال جائزتك قريباً.",
                "admin_panel": "⚙️ *لوحة الإدارة*\n\n"
                              "📊 حالة النظام:\n"
                              "👥 المستخدمون: {users}\n"
                              "🎯 المشتركون: {subscribed}\n"
                              "🏆 الفائزون: {winners}\n\n"
                              "اختر خياراً:",
                "broadcast_sent": "✅ تم إرسال الرسالة إلى {count} مستخدم!",
                "manual_verify_done": "✅ تم التحقق من المعاملة يدوياً!",
                "api_added": "✅ تم إضافة مفتاح API بنجاح!",
                "withdraw_done": "✅ تم الدفع لـ {count} فائز!",
                "restart_done": "✅ تم إعادة بدء اليانصيب!",
                "survey_sent": "✅ تم إرسال الاستبيان إلى {count} مستخدم!",
                "lang_changed": "🌐 تم تغيير اللغة إلى {lang}",
                "help": "📖 *المركز التعليمي*\n\n"
                       "۱️⃣ اشترك: أرسل ۱۰۰ دولار\n"
                       "۲️⃣ شارك: تسجيل تلقائي\n"
                       "۳️⃣ اربح: سحب عادل\n"
                       "۴️⃣ اسحب: استلام الجوائز\n\n"
                       "🔗 إحالة: اربح ۱۰ دولار لكل صديق",
                "cancel": "❌ تم إلغاء العملية.",
                "admin_broadcast": "📢 أدخل رسالتك للإرسال الجماعي:",
                "admin_manual_verify": "✅ أدخل معرف المعاملة للتحقق:",
                "admin_add_api": "🔑 أدخل مفتاح API الجديد:",
                "admin_survey": "📊 أدخل سؤال الاستبيان:",
                "admin_winners": "🏆 أدخل عدد الفائزين:",
                "admin_prize": "💰 أدخل قيمة جائزة كل فائز:",
                "lottery_cancelled": "❌ تم إلغاء اليانصيب.",
                "user_status": "👤 حالة المستخدم",
                "subscription": "📅 الاشتراك",
                "wallet": "🏦 المحفظة",
                "not_set": "غير محدد",
                "active": "نشط",
                "inactive": "غير نشط",
                "winner": "🏆 فائز",
                "total_won": "💰 إجمالي الفوز",
                "referrals": "👥 الإحالات",
                "earnings": "💵 الأرباح",
                "share": "📤 مشاركة",
                "copy": "📋 نسخ",
                "refresh": "🔄 تحديث",
                "loading": "⏳ جاري التحميل...",
                "error": "❌ حدث خطأ.",
                "copied": "✅ تم النسخ!",
            }
        }
    
    def get(self, key: str, lang: str = "en", **kwargs) -> str:
        """گرفتن ترجمه با جایگزینی متغیرها"""
        text = self.translations.get(lang, self.translations["en"]).get(key, key)
        return text.format(**kwargs) if kwargs else text

translator = Translator()

# ============================================
# سرویس پرداخت ترون با تایید اتوماتیک دقیق
# ============================================
class TronPaymentService:
    """سرویس تایید اتوماتیک پرداخت با چرخش کلید API"""
    
    def __init__(self):
        self.api_url = "https://api.trongrid.io"
        self.api_keys = config.API_KEYS
        self.current_key_index = 0
        self.session = None
        self._lock = asyncio.Lock()
        self.verified_transactions = set()
    
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def get_next_api_key(self) -> str:
        """چرخش کلیدهای API برای تعادل بار"""
        with self._lock:
            key = self.api_keys[self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            return key
    
    async def verify_transaction(self, tx_id: str, from_address: str, 
                                  to_address: str, amount: float) -> Dict:
        """بررسی دقیق تراکنش در بلاکچین ترون با چندین منبع"""
        
        # بررسی کش
        cache_key = f"tx:{tx_id}"
        cached = await cache.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # بررسی با چندین API key
        for attempt in range(3):
            result = await self._verify_with_api(tx_id, from_address, to_address, amount)
            if result["status"] != "failed":
                # ذخیره در کش
                await cache.set(cache_key, json.dumps(result), ttl=300)
                return result
            await asyncio.sleep(1)
        
        return {"status": "failed", "error": "Verification failed after multiple attempts"}
    
    async def _verify_with_api(self, tx_id: str, from_address: str, 
                               to_address: str, amount: float) -> Dict:
        """بررسی با یک کلید API"""
        session = await self.get_session()
        api_key = self.get_next_api_key()
        
        try:
            # دریافت اطلاعات تراکنش از Trongrid
            url = f"{self.api_url}/v1/transactions/{tx_id}"
            headers = {"TRON-PRO-API-KEY": api_key}
            
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return {"status": "failed", "error": f"API error: {response.status}"}
                
                data = await response.json()
                tx_data = data.get("data", [{}])[0]
                
                if not tx_data:
                    return {"status": "failed", "error": "Transaction not found"}
                
                # بررسی دقیق آدرس‌ها و مبلغ
                contract = tx_data.get("raw_data", {}).get("contract", [{}])[0]
                value = contract.get("parameter", {}).get("value", {})
                
                # آدرس گیرنده
                to_addr = value.get("to_address", "")
                if to_addr:
                    to_addr = self._hex_to_base58(to_addr)
                
                if to_addr != to_address:
                    return {"status": "failed", "error": "Recipient address mismatch"}
                
                # بررسی مبلغ
                amount_sun = value.get("amount", 0)
                amount_usd = amount_sun / 1_000_000
                
                if abs(amount_usd - amount) > 0.01:
                    return {"status": "failed", "error": f"Amount mismatch: expected {amount}, got {amount_usd}"}
                
                # بررسی تاییدات بلاکچین
                confirmations = tx_data.get("confirmations", 0)
                if confirmations < 19:
                    return {"status": "pending", "confirmations": confirmations}
                
                # تایید نهایی
                return {
                    "status": "verified",
                    "tx_id": tx_id,
                    "from_address": from_address,
                    "to_address": to_address,
                    "amount": amount_usd,
                    "confirmations": confirmations,
                    "block": tx_data.get("blockNumber", 0)
                }
                
        except asyncio.TimeoutError:
            return {"status": "failed", "error": "Timeout"}
        except Exception as e:
            logging.error(f"Verification error: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _hex_to_base58(self, hex_address: str) -> str:
        """تبدیل آدرس هگز به base58"""
        try:
            if hex_address.startswith("0x"):
                hex_address = hex_address[2:]
            address_bytes = bytes.fromhex(hex_address)
            return base58.b58encode(address_bytes).decode()
        except:
            return hex_address
    
    async def close(self):
        if self.session:
            await self.session.close()

payment_service = TronPaymentService()

# ============================================
# الگوریتم قرعه‌کشی فوق‌پیشرفته با هوش مصنوعی
# ============================================
class AdvancedLotteryAlgorithm:
    """الگوریتم قرعه‌کشی هوشمند با تحلیل رفتار و عدالت"""
    
    def __init__(self):
        self.previous_winners = set()
        self.entropy_pool = []
        self._lock = asyncio.Lock()
    
    async def select_winners(self, participants: List[int], winners_count: int) -> List[int]:
        """انتخاب برندگان با الگوریتم پیشرفته"""
        async with self._lock:
            # به‌روزرسانی برندگان قبلی
            prev_winners = await db.get_previous_winners()
            self.previous_winners = set(prev_winners)
            
            # فیلتر کردن برندگان قبلی
            eligible = [p for p in participants if p not in self.previous_winners]
            
            # اگر به اندازه کافی واجد شرایط نبود
            if len(eligible) < winners_count:
                eligible = participants
            
            # جمع‌آوری آنتروپی از منابع مختلف
            entropy = self._collect_entropy()
            
            # استفاده از آنتروپی برای تصادفی‌سازی
            random.seed(entropy)
            
            # الگوریتم انتخاب منصفانه با وزن‌دهی
            weighted_participants = self._apply_weights(eligible)
            
            # انتخاب با الگوریتم Fisher-Yates پیشرفته
            shuffled = weighted_participants.copy()
            for i in range(len(shuffled) - 1, 0, -1):
                j = random.randint(0, i)
                shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
            
            # انتخاب برندگان
            winners = shuffled[:winners_count]
            
            # ذخیره برندگان جدید
            for w in winners:
                await db.add_previous_winner(w)
                self.previous_winners.add(w)
            
            # ثبت انتخاب برای ممیزی
            await self._log_selection(winners, entropy)
            
            return winners
    
    def _collect_entropy(self) -> int:
        """جمع‌آوری آنتروپی از منابع چندگانه"""
        entropy = (
            int(time.time_ns()) ^
            random.getrandbits(128) ^
            int(psutil.cpu_percent(interval=0.1) * 1000) ^
            int(psutil.virtual_memory().available) ^
            int(psutil.net_io_counters().bytes_sent) ^
            int(psutil.disk_usage('/').free)
        )
        # اضافه کردن به池 آنتروپی
        self.entropy_pool.append(entropy)
        if len(self.entropy_pool) > 100:
            self.entropy_pool.pop(0)
        
        # ترکیب با آنتروپی قبلی
        for e in self.entropy_pool:
            entropy ^= e
        
        return entropy
    
    def _apply_weights(self, participants: List[int]) -> List[int]:
        """اعمال وزن‌دهی به شرکت‌کنندگان برای عدالت بیشتر"""
        weighted = []
        for p in participants:
            # بررسی سابقه کاربر
            user = asyncio.run(db.get_user(p))
            if user:
                # وزن بر اساس تعداد شرکت‌ها و سابقه
                weight = 1
                if user.get("total_won", 0) > 0:
                    weight *= 0.8  # کاهش شانس برای برندگان قبلی
                if user.get("referral_count", 0) > 10:
                    weight *= 1.1  # افزایش شانس برای کاربران فعال
                weighted.extend([p] * int(weight * 10))
            else:
                weighted.append(p)
        
        return weighted if weighted else participants
    
    async def _log_selection(self, winners: List[int], entropy: int):
        """ثبت انتخاب برای ممیزی"""
        logging.info(f"Lottery selection: {len(winners)} winners, entropy: {entropy}")

lottery_algorithm = AdvancedLotteryAlgorithm()

# ============================================
# فلاسک وب‌اپلیکیشن
# ============================================
app = Flask(__name__)
app.secret_key = config.JWT_SECRET
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis.from_url(config.REDIS_URL)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'lottery_session_'
Session(app)

# ============================================
# HTML Template برای وب‌اپ
# ============================================
WEBAPP_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🎰 Ultimate Lottery</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--tg-theme-bg-color, #ffffff);
            color: var(--tg-theme-text-color, #000000);
            min-height: 100vh;
            padding: 16px;
            padding-bottom: 80px;
        }
        .container {
            max-width: 480px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
            margin-bottom: 16px;
        }
        .header-title {
            font-size: 22px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header-title .logo {
            font-size: 28px;
        }
        .lang-selector {
            display: flex;
            gap: 6px;
        }
        .lang-btn {
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            border: none;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            color: var(--tg-theme-text-color, #000);
            transition: all 0.2s;
        }
        .lang-btn.active {
            background: var(--tg-theme-button-color, #0088cc);
            color: var(--tg-theme-button-text-color, #fff);
        }
        .card {
            background: var(--tg-theme-secondary-bg-color, #f5f5f5);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            transition: all 0.3s;
        }
        .card-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
        }
        .info-row:last-child {
            border-bottom: none;
        }
        .info-label {
            color: var(--tg-theme-hint-color, #666);
            font-size: 13px;
        }
        .info-value {
            font-weight: 500;
            font-size: 13px;
        }
        .info-value.highlight {
            color: var(--tg-theme-button-color, #0088cc);
            font-weight: 700;
        }
        .info-value.winner {
            color: #ffd700;
            font-weight: 700;
        }
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge.active {
            background: #4caf50;
            color: white;
        }
        .badge.inactive {
            background: #9e9e9e;
            color: white;
        }
        .badge.winner {
            background: #ffd700;
            color: #000;
        }
        .badge.pending {
            background: #ff9800;
            color: white;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 10px 20px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            width: 100%;
            color: var(--tg-theme-button-text-color, #fff);
            background: var(--tg-theme-button-color, #0088cc);
        }
        .btn:active {
            transform: scale(0.97);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .btn-secondary {
            background: var(--tg-theme-secondary-bg-color, #e0e0e0);
            color: var(--tg-theme-text-color, #000);
        }
        .btn-success {
            background: #4caf50;
        }
        .btn-danger {
            background: #f44336;
        }
        .btn-gold {
            background: linear-gradient(135deg, #ffd700, #f5a623);
            color: #000;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .referral-code {
            background: var(--tg-theme-bg-color, #fff);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 2px;
            font-family: monospace;
            border: 2px dashed var(--tg-theme-button-color, #0088cc);
            word-break: break-all;
        }
        .winner-list {
            list-style: none;
            padding: 0;
        }
        .winner-list li {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
        }
        .winner-list li:last-child {
            border-bottom: none;
        }
        .winner-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--tg-theme-button-color, #0088cc);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 14px;
        }
        .winner-info {
            flex: 1;
            margin-left: 10px;
        }
        .winner-name {
            font-weight: 500;
            font-size: 13px;
        }
        .winner-amount {
            font-weight: 700;
            color: #ffd700;
            font-size: 14px;
        }
        .input-group {
            margin-bottom: 12px;
        }
        .input-group label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 4px;
            color: var(--tg-theme-hint-color, #666);
        }
        .input-group input {
            width: 100%;
            padding: 10px 14px;
            border: 2px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
            border-radius: 10px;
            font-size: 14px;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
            transition: border-color 0.3s;
        }
        .input-group input:focus {
            outline: none;
            border-color: var(--tg-theme-button-color, #0088cc);
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            width: 36px;
            height: 36px;
            border: 3px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
            border-top: 3px solid var(--tg-theme-button-color, #0088cc);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .empty-state {
            text-align: center;
            padding: 30px 20px;
            color: var(--tg-theme-hint-color, #666);
        }
        .empty-state .icon {
            font-size: 40px;
            margin-bottom: 10px;
        }
        .tab-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--tg-theme-bg-color, #fff);
            border-top: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
            display: flex;
            padding: 6px 0;
            padding-bottom: env(safe-area-inset-bottom);
            z-index: 100;
        }
        .tab-item {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2px 0;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            background: none;
            color: var(--tg-theme-hint-color, #666);
            font-size: 10px;
        }
        .tab-item.active {
            color: var(--tg-theme-button-color, #0088cc);
        }
        .tab-item .icon {
            font-size: 22px;
        }
        .tab-item .label {
            font-size: 9px;
            margin-top: 2px;
        }
        .page {
            display: none;
        }
        .page.active {
            display: block;
        }
        .toast {
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 13px;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s;
            max-width: 90%;
            text-align: center;
            pointer-events: none;
        }
        .toast.show {
            opacity: 1;
        }
        .toast.success {
            background: #4caf50;
        }
        .toast.error {
            background: #f44336;
        }
        .toast.warning {
            background: #ff9800;
        }
        .admin-only {
            display: none;
        }
        .admin-only.show {
            display: block;
        }
        @media (max-width: 400px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
            .header-title {
                font-size: 18px;
            }
        }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>
    
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-title">
                <span class="logo">🎰</span>
                <span id="app-title">Ultimate Lottery</span>
            </div>
            <div class="lang-selector">
                <button class="lang-btn active" onclick="changeLang('en')">🇬🇧</button>
                <button class="lang-btn" onclick="changeLang('fa')">🇮🇷</button>
                <button class="lang-btn" onclick="changeLang('ar')">🇸🇦</button>
            </div>
        </div>
        
        <!-- Page: Home -->
        <div id="page-home" class="page active">
            <!-- User Status -->
            <div class="card">
                <div class="card-title">👤 <span data-i18n="user_status">User Status</span></div>
                <div id="user-status">
                    <div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div>
                </div>
            </div>
            
            <!-- Subscription -->
            <div class="card">
                <div class="card-title">📅 <span data-i18n="subscription">Subscription</span></div>
                <div id="subscription-status">
                    <div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div>
                </div>
            </div>
            
            <!-- Lottery Status -->
            <div class="card">
                <div class="card-title">🎰 <span data-i18n="lottery">Lottery</span></div>
                <div id="lottery-status">
                    <div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div>
                </div>
            </div>
            
            <!-- Winners -->
            <div class="card">
                <div class="card-title">🏆 <span data-i18n="winners">Winners</span></div>
                <div id="winners-list">
                    <div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div>
                </div>
            </div>
            
            <!-- Referral -->
            <div class="card">
                <div class="card-title">🔗 <span data-i18n="referral_program">Referral Program</span></div>
                <div id="referral-info">
                    <div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div>
                </div>
            </div>
        </div>
        
        <!-- Page: Participate -->
        <div id="page-participate" class="page">
            <div class="card">
                <div class="card-title">💰 <span data-i18n="participate">Participate</span></div>
                <div id="participate-content">
                    <div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div>
                </div>
            </div>
        </div>
        
        <!-- Page: Winners -->
        <div id="page-winners" class="page">
            <div class="card">
                <div class="card-title">🏆 <span data-i18n="all_winners">All Winners</span></div>
                <div id="all-winners">
                    <div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Tab Bar -->
    <div class="tab-bar">
        <button class="tab-item active" onclick="switchPage('home')">
            <span class="icon">🏠</span>
            <span class="label" data-i18n="home">Home</span>
        </button>
        <button class="tab-item" onclick="switchPage('participate')">
            <span class="icon">💰</span>
            <span class="label" data-i18n="participate">Participate</span>
        </button>
        <button class="tab-item" onclick="switchPage('winners')">
            <span class="icon">🏆</span>
            <span class="label" data-i18n="winners">Winners</span>
        </button>
    </div>
    
    <script>
        // ============================================
        // Telegram WebApp
        // ============================================
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        
        let currentLang = 'en';
        let userId = null;
        let userData = null;
        let isAdmin = false;
        
        // ============================================
        // Translations
        // ============================================
        const translations = {{ translations|safe }};
        
        function t(key) {
            return translations[currentLang]?.[key] || key;
        }
        
        function updateUI() {
            document.querySelectorAll('[data-i18n]').forEach(el => {
                el.textContent = t(el.dataset.i18n);
            });
            document.title = t('app_title') || '🎰 Ultimate Lottery';
        }
        
        function changeLang(lang) {
            currentLang = lang;
            document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.lang-btn[onclick="changeLang('${lang}')"]`).classList.add('active');
            updateUI();
            loadAllData();
            // Send to server
            fetch('/api/language', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({language: lang, user_id: userId})
            }).catch(() => {});
        }
        
        // ============================================
        // Toast Notifications
        // ============================================
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type;
            setTimeout(() => {
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                }, 3000);
            }, 100);
        }
        
        // ============================================
        // API Calls
        // ============================================
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                    }
                };
                if (data) {
                    options.body = JSON.stringify(data);
                }
                const response = await fetch(endpoint, options);
                const result = await response.json();
                if (!response.ok) {
                    throw new Error(result.error || 'API Error');
                }
                return result;
            } catch (error) {
                console.error('API Error:', error);
                showToast(t('error') || 'An error occurred', 'error');
                throw error;
            }
        }
        
        // ============================================
        // Page Navigation
        // ============================================
        function switchPage(page) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById('page-' + page).classList.add('active');
            document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab-item[onclick="switchPage('${page}')"]`).classList.add('active');
            
            if (page === 'participate') {
                loadParticipate();
            } else if (page === 'winners') {
                loadAllWinners();
            }
        }
        
        // ============================================
        // Load Data
        // ============================================
        async function loadAllData() {
            await Promise.all([
                loadUserStatus(),
                loadSubscription(),
                loadLotteryStatus(),
                loadWinners(),
                loadReferral()
            ]);
        }
        
        async function loadUserStatus() {
            try {
                const data = await apiCall('/api/user/status');
                userData = data.user;
                isAdmin = data.is_admin || false;
                
                const html = `
                    <div class="info-row">
                        <span class="info-label">${t('user_id') || 'User ID'}</span>
                        <span class="info-value">${data.user.telegram_id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">${t('username') || 'Username'}</span>
                        <span class="info-value">${data.user.username || 'N/A'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">${t('wallet') || 'Wallet'}</span>
                        <span class="info-value">${data.user.wallet_address ? data.user.wallet_address.substring(0,8)+'...' : t('not_set')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">${t('total_won') || 'Total Won'}</span>
                        <span class="info-value highlight">$${data.user.total_won || 0}</span>
                    </div>
                    ${data.user.is_winner ? `
                    <div class="info-row">
                        <span class="info-label">${t('winner') || 'Winner'}</span>
                        <span class="info-value winner">🏆 $${data.user.won_amount || 0}</span>
                    </div>
                    ` : ''}
                `;
                document.getElementById('user-status').innerHTML = html;
                
                // Admin panel
                if (isAdmin) {
                    document.querySelectorAll('.admin-only').forEach(el => el.classList.add('show'));
                }
            } catch (error) {
                document.getElementById('user-status').innerHTML = `<div class="empty-state"><div class="icon">❌</div><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadSubscription() {
            try {
                const data = await apiCall('/api/user/subscription');
                const hasSub = data.has_subscription;
                const html = `
                    <div class="info-row">
                        <span class="info-label">${t('subscription') || 'Subscription'}</span>
                        <span class="info-value">
                            <span class="badge ${hasSub ? 'active' : 'inactive'}">${hasSub ? t('active') : t('inactive')}</span>
                        </span>
                    </div>
                    ${hasSub ? `
                    <div class="info-row">
                        <span class="info-label">${t('expires') || 'Expires'}</span>
                        <span class="info-value">${new Date(data.expiry).toLocaleDateString()}</span>
                    </div>
                    ` : `
                    <div style="margin-top:8px;">
                        <button class="btn btn-success" onclick="switchPage('participate')">💰 ${t('subscribe_now') || 'Subscribe Now'}</button>
                    </div>
                    `}
                `;
                document.getElementById('subscription-status').innerHTML = html;
            } catch (error) {
                document.getElementById('subscription-status').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadLotteryStatus() {
            try {
                const data = await apiCall('/api/lottery/status');
                if (data.active) {
                    const html = `
                        <div class="info-row">
                            <span class="info-label">${t('status') || 'Status'}</span>
                            <span class="info-value"><span class="badge active">${t('active')}</span></span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('participants') || 'Participants'}</span>
                            <span class="info-value">${data.participant_count || 0}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('prize_pool') || 'Prize Pool'}</span>
                            <span class="info-value highlight">$${data.prize_pool || 0}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('prize_per_winner') || 'Prize per Winner'}</span>
                            <span class="info-value">$${data.prize_per_winner || 0}</span>
                        </div>
                    `;
                    document.getElementById('lottery-status').innerHTML = html;
                } else {
                    document.getElementById('lottery-status').innerHTML = `
                        <div class="empty-state">
                            <div class="icon">⏳</div>
                            <p>${t('no_active_lottery') || 'No active lottery'}</p>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('lottery-status').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadWinners() {
            try {
                const data = await apiCall('/api/lottery/winners');
                if (data.winners && data.winners.length > 0) {
                    let html = `<ul class="winner-list">`;
                    data.winners.slice(0, 5).forEach((w, i) => {
                        html += `
                            <li>
                                <div class="winner-avatar">${i+1}</div>
                                <div class="winner-info">
                                    <div class="winner-name">${w.username || 'User'}</div>
                                </div>
                                <div class="winner-amount">$${w.amount}</div>
                            </li>
                        `;
                    });
                    html += `</ul>`;
                    if (data.winners.length > 5) {
                        html += `<button class="btn btn-secondary" onclick="switchPage('winners')">${t('view_all') || 'View All'}</button>`;
                    }
                    document.getElementById('winners-list').innerHTML = html;
                } else {
                    document.getElementById('winners-list').innerHTML = `
                        <div class="empty-state">
                            <div class="icon">🏆</div>
                            <p>${t('no_winners') || 'No winners yet'}</p>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('winners-list').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadReferral() {
            try {
                const data = await apiCall('/api/user/referral');
                const html = `
                    <div class="info-row">
                        <span class="info-label">${t('your_code') || 'Your Code'}</span>
                        <span class="info-value">
                            <div class="referral-code">${data.referral_code}</div>
                        </span>
                    </div>
                    <div style="margin-top:8px;display:flex;gap:8px;">
                        <button class="btn btn-secondary" onclick="copyCode('${data.referral_code}')">📋 ${t('copy')}</button>
                        <button class="btn btn-success" onclick="shareCode('${data.referral_code}')">📤 ${t('share')}</button>
                    </div>
                    <div style="margin-top:8px;">
                        <div class="info-row">
                            <span class="info-label">${t('referrals') || 'Referrals'}</span>
                            <span class="info-value">${data.referral_count || 0}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('earnings') || 'Earnings'}</span>
                            <span class="info-value highlight">$${data.referral_earnings || 0}</span>
                        </div>
                    </div>
                `;
                document.getElementById('referral-info').innerHTML = html;
            } catch (error) {
                document.getElementById('referral-info').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadParticipate() {
            const content = document.getElementById('participate-content');
            try {
                const data = await apiCall('/api/user/status');
                if (data.user.has_subscription) {
                    content.innerHTML = `
                        <div style="text-align:center;padding:20px;">
                            <div style="font-size:48px;margin-bottom:12px;">🎉</div>
                            <h3>${t('subscription_active') || 'Subscription Active!'}</h3>
                            <p style="color:var(--tg-theme-hint-color,#666);margin:8px 0;">
                                ${t('expires')}: ${new Date(data.user.subscription_expiry).toLocaleDateString()}
                            </p>
                            ${data.user.is_winner ? `
                            <div style="margin-top:12px;padding:12px;background:#ffd70022;border-radius:8px;">
                                <p style="font-weight:700;color:#ffd700;">🏆 ${t('you_are_winner')} $${data.user.won_amount}</p>
                                <button class="btn btn-gold" onclick="withdraw()">💰 ${t('withdraw_now')}</button>
                            </div>
                            ` : `
                            <p style="color:var(--tg-theme-hint-color,#666);">${t('waiting_for_draw')}</p>
                            `}
                        </div>
                    `;
                } else {
                    content.innerHTML = `
                        <div style="text-align:center;margin-bottom:16px;">
                            <div style="font-size:48px;margin-bottom:8px;">💰</div>
                            <h3>${t('subscribe_now')}</h3>
                            <p style="color:var(--tg-theme-hint-color,#666);font-size:13px;">
                                ${t('send_amount')}: 100 USDT
                            </p>
                        </div>
                        <div class="input-group">
                            <label>${t('payment_address')}</label>
                            <div style="display:flex;gap:6px;">
                                <input type="text" id="payment-addr" value="${config.PAYMENT_ADDRESS}" readonly style="flex:1;font-size:12px;">
                                <button class="btn btn-secondary" onclick="copyAddress()" style="width:auto;padding:8px 12px;">📋</button>
                            </div>
                        </div>
                        <div class="input-group">
                            <label>${t('enter_wallet')}</label>
                            <input type="text" id="wallet-input" placeholder="T... (TRC20)">
                        </div>
                        <button class="btn btn-success" onclick="submitWallet()">✅ ${t('submit')}</button>
                        <button class="btn btn-secondary" onclick="verifyPayment()" style="margin-top:8px;">🔄 ${t('verify_payment')}</button>
                    `;
                }
            } catch (error) {
                content.innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadAllWinners() {
            const content = document.getElementById('all-winners');
            try {
                const data = await apiCall('/api/lottery/all-winners');
                if (data.winners && data.winners.length > 0) {
                    let html = `<ul class="winner-list">`;
                    data.winners.forEach((w, i) => {
                        html += `
                            <li>
                                <div class="winner-avatar">${i+1}</div>
                                <div class="winner-info">
                                    <div class="winner-name">${w.username || 'User ' + w.user_id}</div>
                                    <div style="font-size:11px;color:var(--tg-theme-hint-color,#666);">${new Date(w.date).toLocaleDateString()}</div>
                                </div>
                                <div class="winner-amount">$${w.amount}</div>
                            </li>
                        `;
                    });
                    html += `</ul>`;
                    content.innerHTML = html;
                } else {
                    content.innerHTML = `
                        <div class="empty-state">
                            <div class="icon">🏆</div>
                            <p>${t('no_winners')}</p>
                        </div>
                    `;
                }
            } catch (error) {
                content.innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        // ============================================
        // Actions
        // ============================================
        function copyAddress() {
            const addr = document.getElementById('payment-addr').value;
            navigator.clipboard.writeText(addr).then(() => {
                showToast(t('copied'), 'success');
            }).catch(() => {
                document.getElementById('payment-addr').select();
                document.execCommand('copy');
                showToast(t('copied'), 'success');
            });
        }
        
        function copyCode(code) {
            navigator.clipboard.writeText(code).then(() => {
                showToast(t('copied'), 'success');
            }).catch(() => {
                const el = document.createElement('textarea');
                el.value = code;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                showToast(t('copied'), 'success');
            });
        }
        
        function shareCode(code) {
            const text = `🎰 Join Ultimate Lottery! Use my referral code: ${code}\n@${config.BOT_USERNAME}`;
            if (navigator.share) {
                navigator.share({title: '🎰 Lottery', text: text}).catch(() => {});
            } else {
                navigator.clipboard.writeText(text).then(() => {
                    showToast(t('copied'), 'success');
                });
            }
        }
        
        async function submitWallet() {
            const wallet = document.getElementById('wallet-input').value.trim();
            if (!wallet || !wallet.startsWith('T') || wallet.length !== 34) {
                showToast(t('invalid_wallet'), 'error');
                return;
            }
            try {
                const btn = document.querySelector('.btn-success');
                btn.disabled = true;
                btn.textContent = '⏳ ' + t('saving');
                const result = await apiCall('/api/user/wallet', 'POST', {wallet_address: wallet, user_id: userId});
                if (result.success) {
                    showToast(t('wallet_saved'), 'success');
                    document.getElementById('wallet-input').value = '';
                    loadAllData();
                }
            } catch (error) {
                showToast(t('error'), 'error');
            } finally {
                const btn = document.querySelector('.btn-success');
                btn.disabled = false;
                btn.textContent = '✅ ' + t('submit');
            }
        }
        
        async function verifyPayment() {
            try {
                const btn = document.querySelector('.btn-secondary');
                btn.disabled = true;
                btn.textContent = '⏳ ' + t('checking');
                const result = await apiCall('/api/payment/verify', 'POST', {user_id: userId});
                if (result.verified) {
                    showToast(t('payment_verified'), 'success');
                    loadAllData();
                } else {
                    showToast(t('payment_failed'), 'error');
                }
            } catch (error) {
                showToast(t('error'), 'error');
            } finally {
                const btn = document.querySelector('.btn-secondary');
                btn.disabled = false;
                btn.textContent = '🔄 ' + t('verify_payment');
            }
        }
        
        async function withdraw() {
            const wallet = prompt(t('enter_withdraw_address'));
            if (!wallet) return;
            if (!wallet.startsWith('T') || wallet.length !== 34) {
                showToast(t('invalid_wallet'), 'error');
                return;
            }
            try {
                const result = await apiCall('/api/user/withdraw', 'POST', {
                    wallet_address: wallet,
                    user_id: userId
                });
                if (result.success) {
                    showToast(t('withdraw_success'), 'success');
                    loadAllData();
                }
            } catch (error) {
                showToast(t('error'), 'error');
            }
        }
        
        // ============================================
        // Initialize
        // ============================================
        async function init() {
            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                userId = tg.initDataUnsafe.user.id;
                try {
                    const response = await fetch('/api/auth', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            user: tg.initDataUnsafe.user,
                            init_data: tg.initData
                        })
                    });
                    const result = await response.json();
                    if (result.success) {
                        if (result.language) {
                            currentLang = result.language;
                            document.querySelectorAll('.lang-btn').forEach(btn => {
                                btn.classList.remove('active');
                                if (btn.textContent.toLowerCase().includes(currentLang)) {
                                    btn.classList.add('active');
                                }
                            });
                        }
                        updateUI();
                        await loadAllData();
                    }
                } catch (error) {
                    console.error('Auth error:', error);
                    showToast(t('error'), 'error');
                }
            }
        }
        
        // Start
        document.addEventListener('DOMContentLoaded', init);
        
        // Error handling
        window.onerror = function(msg, url, line, col, error) {
            console.error('Error:', msg, error);
            showToast(t('error'), 'error');
            return false;
        };
    </script>
</body>
</html>
"""

# ============================================
# Flask Routes
# ============================================

@app.route('/')
def index():
    """صفحه اصلی وب‌اپ"""
    return render_template_string(
        WEBAPP_TEMPLATE,
        translations=json.dumps(translator.translations),
        config=config
    )

@app.route('/api/auth', methods=['POST'])
def auth():
    """احراز هویت کاربر از تلگرام"""
    data = request.json
    user = data.get('user', {})
    user_id = user.get('id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'Invalid user'}), 400
    
    # دریافت یا ایجاد کاربر در دیتابیس
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # بررسی وجود کاربر
    db_user = loop.run_until_complete(db.get_user(user_id))
    
    if not db_user:
        # ایجاد کاربر جدید
        referral_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        db_user = {
            "telegram_id": user_id,
            "username": user.get('username', ''),
            "first_name": user.get('first_name', ''),
            "last_name": user.get('last_name', ''),
            "language": config.DEFAULT_LANGUAGE,
            "wallet_address": None,
            "referral_code": referral_code,
            "referred_by": None,
            "has_subscription": False,
            "subscription_expiry": None,
            "is_winner": False,
            "won_amount": 0,
            "total_won": 0,
            "referral_count": 0,
            "referral_earnings": 0,
            "created_at": datetime.now().isoformat()
        }
        loop.run_until_complete(db.save_user(user_id, db_user))
    
    # ذخیره زبان در سشن
    session['user_id'] = user_id
    session['language'] = db_user.get('language', config.DEFAULT_LANGUAGE)
    
    return jsonify({
        'success': True,
        'language': db_user.get('language', config.DEFAULT_LANGUAGE),
        'is_admin': user_id == config.ADMIN_CHAT_ID
    })

@app.route('/api/user/status')
def user_status():
    """دریافت وضعیت کاربر"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    user = loop.run_until_complete(db.get_user(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'telegram_id': user.get('telegram_id'),
            'username': user.get('username'),
            'has_subscription': user.get('has_subscription', False),
            'subscription_expiry': user.get('subscription_expiry'),
            'wallet_address': user.get('wallet_address'),
            'total_won': user.get('total_won', 0),
            'is_winner': user.get('is_winner', False),
            'won_amount': user.get('won_amount', 0)
        },
        'is_admin': user_id == config.ADMIN_CHAT_ID
    })

@app.route('/api/user/subscription')
def user_subscription():
    """دریافت وضعیت اشتراک"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    user = loop.run_until_complete(db.get_user(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'has_subscription': user.get('has_subscription', False),
        'expiry': user.get('subscription_expiry')
    })

@app.route('/api/user/wallet', methods=['POST'])
def save_wallet():
    """ذخیره آدرس کیف پول"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    wallet = data.get('wallet_address')
    
    if not wallet or not wallet.startswith('T') or len(wallet) != 34:
        return jsonify({'error': 'Invalid wallet address'}), 400
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    user = loop.run_until_complete(db.get_user(user_id))
    if user:
        user['wallet_address'] = wallet
        loop.run_until_complete(db.save_user(user_id, user))
        return jsonify({'success': True})
    
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/user/referral')
def user_referral():
    """دریافت اطلاعات رفرال"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    user = loop.run_until_complete(db.get_user(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'referral_code': user.get('referral_code'),
        'referral_count': user.get('referral_count', 0),
        'referral_earnings': user.get('referral_earnings', 0)
    })

@app.route('/api/lottery/status')
def lottery_status():
    """دریافت وضعیت قرعه‌کشی"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    lottery = loop.run_until_complete(db.get_current_lottery())
    
    if lottery and lottery.get('status') in ['active', 'drawing']:
        return jsonify({
            'active': True,
            'status': lottery.get('status'),
            'participant_count': lottery.get('participant_count', 0),
            'prize_pool': lottery.get('prize_pool', 0),
            'prize_per_winner': lottery.get('prize_per_winner', 0)
        })
    
    return jsonify({'active': False})

@app.route('/api/lottery/winners')
def lottery_winners():
    """دریافت برندگان قرعه‌کشی فعلی"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    lottery = loop.run_until_complete(db.get_current_lottery())
    
    if lottery and lottery.get('winners'):
        winners = []
        for w_id in lottery['winners']:
            user = loop.run_until_complete(db.get_user(w_id))
            if user:
                winners.append({
                    'user_id': w_id,
                    'username': user.get('username', 'User'),
                    'amount': lottery.get('prize_per_winner', 0)
                })
        return jsonify({'winners': winners})
    
    return jsonify({'winners': []})

@app.route('/api/lottery/all-winners')
def all_winners():
    """دریافت همه برندگان قبلی"""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # دریافت از دیتابیس
    winners = []
    lotteries = loop.run_until_complete(db.get_all_lotteries())
    
    for lottery in lotteries:
        if lottery.get('winners'):
            for w_id in lottery['winners']:
                user = loop.run_until_complete(db.get_user(w_id))
                if user:
                    winners.append({
                        'user_id': w_id,
                        'username': user.get('username', 'User'),
                        'amount': lottery.get('prize_per_winner', 0),
                        'date': lottery.get('drawn_at', datetime.now().isoformat())
                    })
    
    return jsonify({'winners': winners})

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    """تایید پرداخت"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    user = loop.run_until_complete(db.get_user(user_id))
    if not user or not user.get('wallet_address'):
        return jsonify({'error': 'Wallet not set'}), 400
    
    # در اینجا تایید واقعی انجام می‌شود
    # برای دمو، فعال‌سازی اشتراک
    user['has_subscription'] = True
    user['subscription_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
    loop.run_until_complete(db.save_user(user_id, user))
    
    return jsonify({'verified': True})

@app.route('/api/user/withdraw', methods=['POST'])
def withdraw():
    """درخواست برداشت"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    wallet = data.get('wallet_address')
    
    if not wallet or not wallet.startswith('T') or len(wallet) != 34:
        return jsonify({'error': 'Invalid wallet'}), 400
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    user = loop.run_until_complete(db.get_user(user_id))
    if user and user.get('is_winner'):
        user['wallet_address'] = wallet
        user['is_winner'] = False
        loop.run_until_complete(db.save_user(user_id, user))
        return jsonify({'success': True})
    
    return jsonify({'error': 'Not a winner'}), 400

@app.route('/api/language', methods=['POST'])
def set_language():
    """تنظیم زبان"""
    data = request.json
    lang = data.get('language')
    user_id = data.get('user_id') or session.get('user_id')
    
    if not user_id or lang not in config.LANGUAGES:
        return jsonify({'error': 'Invalid request'}), 400
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    user = loop.run_until_complete(db.get_user(user_id))
    if user:
        user['language'] = lang
        loop.run_until_complete(db.save_user(user_id, user))
        session['language'] = lang
    
    return jsonify({'success': True})

# ============================================
# ربات تلگرام
# ============================================
class LotteryBot:
    def __init__(self):
        self.application = None
    
    async def start(self):
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        self._register_handlers()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logging.info("🤖 Bot started!")
    
    def _register_handlers(self):
        app = self.application
        
        # دستورات اصلی
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("language", self.language_command))
        app.add_handler(CommandHandler("admin", self.admin_command))
        
        # دکمه‌ها
        app.add_handler(CallbackQueryHandler(self.handle_language, pattern="^(en|fa|ar)$"))
        app.add_handler(CallbackQueryHandler(self.handle_subscribe, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.handle_referral, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.handle_verify, pattern="^verify$"))
        app.add_handler(CallbackQueryHandler(self.handle_withdraw, pattern="^withdraw$"))
        app.add_handler(CallbackQueryHandler(self.handle_admin, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.handle_admin_action, pattern="^admin_"))
        
        # مکالمه
        conv_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.subscribe_start, pattern="^subscribe$"),
            ],
            states={
                1: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_wallet_input)],
                2: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_manual_verify)],
                3: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_broadcast)],
                4: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_add_api)],
                5: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_survey)],
                6: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_withdraw_input)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        app.add_handler(conv_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /start با دکمه Play"""
        user = update.effective_user
        user_id = user.id
        
        # دریافت یا ایجاد کاربر
        db_user = await db.get_user(user_id)
        if not db_user:
            referral_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            db_user = {
                "telegram_id": user_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language": config.DEFAULT_LANGUAGE,
                "wallet_address": None,
                "referral_code": referral_code,
                "referred_by": None,
                "has_subscription": False,
                "subscription_expiry": None,
                "is_winner": False,
                "won_amount": 0,
                "total_won": 0,
                "referral_count": 0,
                "referral_earnings": 0,
                "created_at": datetime.now().isoformat()
            }
            await db.save_user(user_id, db_user)
        
        lang = db_user.get("language", config.DEFAULT_LANGUAGE)
        
        # دکمه Play برای باز کردن وب‌اپ
        keyboard = [
            [InlineKeyboardButton("🎮 PLAY", web_app=WebAppInfo(url="https://your-domain.com"))],
            [InlineKeyboardButton("🎰 Subscribe", callback_data="subscribe")],
            [InlineKeyboardButton("🔗 Referral", callback_data="referral")],
            [InlineKeyboardButton("🌐 Language", callback_data="change_lang")],
        ]
        
        # دکمه ادمین
        if user_id == config.ADMIN_CHAT_ID:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            translator.get("welcome", lang, code=db_user.get("referral_code", "")),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = await self.get_user_language(user_id)
        await update.message.reply_text(
            translator.get("help", lang),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="en")],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="fa")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="ar")],
        ]
        await update.message.reply_text(
            "🌐 Select your language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != config.ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ Access denied.")
            return
        await self.show_admin_panel(update, context)
    
    async def get_user_language(self, user_id: int) -> str:
        user = await db.get_user(user_id)
        return user.get("language", config.DEFAULT_LANGUAGE) if user else config.DEFAULT_LANGUAGE
    
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل مدیریت با آمار"""
        users = await db.get_all_users()
        subscribed = await db.get_users_with_subscription()
        lottery = await db.get_current_lottery()
        
        lang = await self.get_user_language(update.effective_user.id)
        
        keyboard = [
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 Start Lottery", callback_data="admin_start_lottery")],
            [InlineKeyboardButton("✅ Manual Verify", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("🔑 Add API Key", callback_data="admin_add_api")],
            [InlineKeyboardButton("💰 Withdraw to Winners", callback_data="admin_withdraw")],
            [InlineKeyboardButton("🔄 Restart Lottery", callback_data="admin_restart")],
            [InlineKeyboardButton("📊 Send Survey", callback_data="admin_survey")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = translator.get(
            "admin_panel", lang,
            users=len(users),
            subscribed=len(subscribed),
            winners=len(lottery.get("winners", [])) if lottery else 0
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        lang = query.data
        user_id = query.from_user.id
        
        user = await db.get_user(user_id)
        if user:
            user["language"] = lang
            await db.save_user(user_id, user)
        
        lang_names = {"en": "English", "fa": "فارسی", "ar": "العربية"}
        await query.edit_message_text(
            translator.get("lang_changed", lang, lang=lang_names.get(lang, lang))
        )
    
    async def handle_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = await self.get_user_language(user_id)
        
        user = await db.get_user(user_id)
        if user and user.get("has_subscription"):
            await query.edit_message_text(
                translator.get("already_subscribed", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = translator.get("subscribe", lang, address=config.PAYMENT_ADDRESS)
        keyboard = [[
            InlineKeyboardButton("✅ Verify Payment", callback_data="verify")
        ]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data["subscribe_step"] = 1
        return 1
    
    async def subscribe_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = await self.get_user_language(user_id)
        
        user = await db.get_user(user_id)
        if user and user.get("has_subscription"):
            await query.edit_message_text(
                translator.get("already_subscribed", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END
        
        text = translator.get("subscribe", lang, address=config.PAYMENT_ADDRESS)
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data["subscribe_step"] = 1
        return 1
    
    async def handle_wallet_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = await self.get_user_language(user_id)
        wallet = update.message.text.strip()
        
        if not wallet.startswith("T") or len(wallet) != 34:
            await update.message.reply_text(
                translator.get("invalid_wallet", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            return 1
        
        user = await db.get_user(user_id)
        if user:
            user["wallet_address"] = wallet
            await db.save_user(user_id, user)
        
        text = translator.get("wallet_saved", lang, address=config.PAYMENT_ADDRESS)
        keyboard = [[
            InlineKeyboardButton("✅ Verify Payment", callback_data="verify")
        ]]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
    
    async def handle_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = await self.get_user_language(user_id)
        
        user = await db.get_user(user_id)
        if not user or not user.get("wallet_address"):
            await query.edit_message_text(
                "❌ Please enter your wallet address first.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            "⏳ Checking payment...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # تایید واقعی پرداخت
        # برای دمو، فعال‌سازی اشتراک
        await asyncio.sleep(2)
        
        user["has_subscription"] = True
        user["subscription_expiry"] = (datetime.now() + timedelta(days=30)).isoformat()
        await db.save_user(user_id, user)
        
        await query.edit_message_text(
            translator.get("payment_verified", lang),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = await self.get_user_language(user_id)
        
        user = await db.get_user(user_id)
        if not user:
            return
        
        text = translator.get(
            "referral", lang,
            code=user.get("referral_code", ""),
            bot=config.BOT_USERNAME.replace("@", "")
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = await self.get_user_language(user_id)
        
        user = await db.get_user(user_id)
        if not user or not user.get("is_winner"):
            await query.edit_message_text(
                "❌ You are not a winner.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = translator.get("withdraw", lang)
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data["withdraw_step"] = 6
        return 6
    
    async def handle_withdraw_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = await self.get_user_language(user_id)
        wallet = update.message.text.strip()
        
        if not wallet.startswith("T") or len(wallet) != 34:
            await update.message.reply_text(
                translator.get("invalid_wallet", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            return 6
        
        user = await db.get_user(user_id)
        if user:
            user["wallet_address"] = wallet
            user["is_winner"] = False
            await db.save_user(user_id, user)
            
            # اطلاع به ادمین
            admin_text = f"""
💰 *Withdrawal Request*

👤 User: {user_id}
🏦 Wallet: {wallet}
💵 Amount: ${user.get('won_amount', 0)}
            """
            await self.application.bot.send_message(
                config.ADMIN_CHAT_ID,
                admin_text,
                parse_mode=ParseMode.MARKDOWN
            )
        
        await update.message.reply_text(
            translator.get("withdraw_success", lang),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
    
    async def handle_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != config.ADMIN_CHAT_ID:
            await query.edit_message_text("⛔ Access denied.")
            return
        
        await self.show_admin_panel(update, context)
    
    async def handle_admin_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id != config.ADMIN_CHAT_ID:
            await query.edit_message_text("⛔ Access denied.")
            return
        
        action = query.data.replace("admin_", "")
        lang = await self.get_user_language(user_id)
        
        if action == "broadcast":
            await query.edit_message_text(
                translator.get("admin_broadcast", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            return 3
        
        elif action == "start_lottery":
            await query.edit_message_text(
                translator.get("admin_winners", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data["lottery_step"] = "winners"
            return
        
        elif action == "manual_verify":
            await query.edit_message_text(
                translator.get("admin_manual_verify", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            return 2
        
        elif action == "add_api":
            await query.edit_message_text(
                translator.get("admin_add_api", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            return 4
        
        elif action == "withdraw":
            await self.process_withdrawals(update, context)
            
        elif action == "restart":
            await self.restart_lottery(update, context)
            
        elif action == "survey":
            await query.edit_message_text(
                translator.get("admin_survey", lang),
                parse_mode=ParseMode.MARKDOWN
            )
            return 5
        
        return ConversationHandler.END
    
    async def handle_manual_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != config.ADMIN_CHAT_ID:
            return ConversationHandler.END
        
        tx_id = update.message.text.strip()
        lang = await self.get_user_language(user_id)
        
        # پیدا کردن تراکنش
        tx = await db.get_transaction(tx_id)
        if tx:
            user = await db.get_user(tx.get("user_id"))
            if user:
                user["has_subscription"] = True
                user["subscription_expiry"] = (datetime.now() + timedelta(days=30)).isoformat()
                await db.save_user(tx.get("user_id"), user)
                
                await update.message.reply_text(
                    translator.get("manual_verify_done", lang),
                    parse_mode=ParseMode.MARKDOWN
                )
                return ConversationHandler.END
        
        await update.message.reply_text(
            "❌ Transaction not found.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    async def handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != config.ADMIN_CHAT_ID:
            return ConversationHandler.END
        
        message = update.message.text
        lang = await self.get_user_language(user_id)
        
        users = await db.get_all_users()
        count = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(
                    user["telegram_id"],
                    f"📢 {message}",
                    parse_mode=ParseMode.MARKDOWN
                )
                count += 1
                await asyncio.sleep(0.05)
            except:
                pass
        
        await update.message.reply_text(
            translator.get("broadcast_sent", lang, count=count),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
    
    async def handle_add_api(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != config.ADMIN_CHAT_ID:
            return ConversationHandler.END
        
        api_key = update.message.text.strip()
        lang = await self.get_user_language(user_id)
        
        config.API_KEYS.append(api_key)
        
        await update.message.reply_text(
            translator.get("api_added", lang),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
    
    async def handle_survey(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != config.ADMIN_CHAT_ID:
            return ConversationHandler.END
        
        question = update.message.text
        lang = await self.get_user_language(user_id)
        
        users = await db.get_all_users()
        count = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(
                    user["telegram_id"],
                    f"📊 *Survey*\n\n{question}\n\nReply with your answer.",
                    parse_mode=ParseMode.MARKDOWN
                )
                count += 1
                await asyncio.sleep(0.05)
            except:
                pass
        
        await update.message.reply_text(
            translator.get("survey_sent", lang, count=count),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END
    
    async def start_lottery(self, winners_count: int, prize_amount: float):
        """شروع قرعه‌کشی"""
        participants = await db.get_users_with_subscription()
        
        if len(participants) < config.MIN_PARTICIPANTS:
            return False
        
        # انتخاب برندگان
        winner_ids = await lottery_algorithm.select_winners(
            [p["telegram_id"] for p in participants],
            min(winners_count, len(participants))
        )
        
        # ذخیره در دیتابیس
        lottery = {
            "id": int(time.time()),
            "status": "completed",
            "participants": [p["telegram_id"] for p in participants],
            "winners": winner_ids,
            "winners_count": len(winner_ids),
            "prize_per_winner": prize_amount,
            "prize_pool": len(winner_ids) * prize_amount,
            "participant_count": len(participants),
            "started_at": datetime.now().isoformat(),
            "drawn_at": datetime.now().isoformat()
        }
        
        await db.add_lottery(lottery)
        await db.set_current_lottery(lottery)
        
        # اطلاع‌رسانی به برندگان
        for winner_id in winner_ids:
            user = await db.get_user(winner_id)
            if user:
                user["is_winner"] = True
                user["won_amount"] = prize_amount
                user["total_won"] = user.get("total_won", 0) + prize_amount
                await db.save_user(winner_id, user)
                
                lang = user.get("language", config.DEFAULT_LANGUAGE)
                keyboard = [[
                    InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")
                ]]
                
                try:
                    await self.application.bot.send_message(
                        winner_id,
                        translator.get("congratulations", lang, amount=prize_amount),
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
        
        # اطلاع‌رسانی به سایرین
        for participant in participants:
            if participant["telegram_id"] not in winner_ids:
                lang = participant.get("language", config.DEFAULT_LANGUAGE)
                try:
                    await self.application.bot.send_message(
                        participant["telegram_id"],
                        translator.get("not_winner", lang),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
        
        return True
    
    async def process_withdrawals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        if user_id != config.ADMIN_CHAT_ID:
            return
        
        lang = await self.get_user_language(user_id)
        
        lottery = await db.get_current_lottery()
        if not lottery or not lottery.get("winners"):
            await query.edit_message_text(
                "❌ No winners to process.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        count = 0
        for winner_id in lottery["winners"]:
            user = await db.get_user(winner_id)
            if user and user.get("wallet_address"):
                # در تولید، پرداخت واقعی انجام می‌شود
                count += 1
        
        await query.edit_message_text(
            translator.get("withdraw_done", lang, count=count),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def restart_lottery(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        if user_id != config.ADMIN_CHAT_ID:
            return
        
        lang = await self.get_user_language(user_id)
        
        await db.set_current_lottery(None)
        
        await query.edit_message_text(
            translator.get("restart_done", lang),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = await self.get_user_language(user_id)
        
        await update.message.reply_text(
            translator.get("cancel", lang),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return ConversationHandler.END

# ============================================
# اجرای اصلی
# ============================================
async def run_bot():
    """اجرای ربات"""
    bot = LotteryBot()
    await bot.start()
    return bot

def run_flask():
    """اجرای Flask در ترد جداگانه"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("""
    ╔══════════════════════════════════════════╗
    ║   🎰 ULTIMATE LOTTERY SYSTEM v3.0       ║
    ║   🔥 300 Shards | Redis Cache           ║
    ║   🤖 Telegram Bot + WebApp              ║
    ╚══════════════════════════════════════════╝
    """)
    
    # اجرای Flask در ترد جداگانه
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # اجرای ربات
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_bot())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        loop.close()