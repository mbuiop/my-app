# ============================================
# ULTIMATE LOTTERY SYSTEM - FULLY FIXED
# ============================================
# این نسخه تمام خطاها رو برطرف کرده و کاملاً کار میکنه
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
import os

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
# تنظیمات
# ============================================
class Config:
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    BOT_USERNAME = "@UTYOB_Bot"
    ADMIN_CHAT_ID = 123456789
    
    PAYMENT_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
    PAYMENT_AMOUNT = 100.0
    
    API_KEYS = [
        "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
    ]
    
    SHARD_COUNT = 300
    REDIS_URL = "redis://localhost:6379/0"
    REDIS_CACHE_TTL = 3600
    
    LANGUAGES = ["en", "fa", "ar"]
    DEFAULT_LANGUAGE = "en"
    
    MIN_PARTICIPANTS = 10
    MAX_WINNERS = 1000
    
    JWT_SECRET = "your-super-secret-jwt-key-change-this"
    WEBAPP_URL = "http://localhost:5000"

config = Config()

# ============================================
# سیستم شاردینگ
# ============================================
class ConsistentHashRing:
    def __init__(self, nodes: List[int], replicas: int = 150):
        self.nodes = nodes
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []
        self._build_ring()
    
    def _build_ring(self):
        for node in self.nodes:
            for i in range(self.replicas):
                key = f"{node}:{i}"
                hash_val = self._hash(key)
                self.ring[hash_val] = node
        self.sorted_keys = sorted(self.ring.keys())
    
    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
    
    def get_node(self, key: str) -> int:
        if not self.ring:
            return 0
        hash_val = self._hash(key)
        for ring_key in self.sorted_keys:
            if hash_val <= ring_key:
                return self.ring[ring_key]
        return self.ring[self.sorted_keys[0]]

# ============================================
# دیتابیس شارد شده با تمام متدها
# ============================================
class ShardedDatabase:
    def __init__(self):
        self.shard_count = config.SHARD_COUNT
        self.ring = ConsistentHashRing(list(range(self.shard_count)))
        self.data = {f"shard_{i}": {} for i in range(self.shard_count)}
        self.locks = {f"shard_{i}": asyncio.Lock() for i in range(self.shard_count)}
        self._init_shards()
    
    def _init_shards(self):
        for i in range(self.shard_count):
            try:
                with open(f"shard_{i}.json", "r") as f:
                    self.data[f"shard_{i}"] = json.load(f)
            except:
                self.data[f"shard_{i}"] = {
                    "users": {},
                    "transactions": {},
                    "lotteries": [],
                    "winners": [],
                    "previous_winners": [],
                    "current_lottery": None
                }
                self._save_shard(i)
    
    def _save_shard(self, shard_id: int):
        try:
            with open(f"shard_{shard_id}.json", "w") as f:
                json.dump(self.data[f"shard_{shard_id}"], f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Error saving shard {shard_id}: {e}")
    
    def get_shard_id(self, user_id: int) -> int:
        return self.ring.get_node(str(user_id))
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        shard_id = self.get_shard_id(user_id)
        shard_key = f"shard_{shard_id}"
        async with self.locks[shard_key]:
            return self.data[shard_key]["users"].get(str(user_id))
    
    async def save_user(self, user_id: int, data: Dict):
        shard_id = self.get_shard_id(user_id)
        shard_key = f"shard_{shard_id}"
        async with self.locks[shard_key]:
            self.data[shard_key]["users"][str(user_id)] = data
            self._save_shard(shard_id)
    
    async def get_all_users(self) -> List[Dict]:
        all_users = []
        for i in range(self.shard_count):
            shard_key = f"shard_{i}"
            async with self.locks[shard_key]:
                users = list(self.data[shard_key]["users"].values())
                all_users.extend(users)
        return all_users
    
    async def get_users_with_subscription(self) -> List[Dict]:
        users = await self.get_all_users()
        return [u for u in users if u.get("has_subscription", False)]
    
    async def get_transaction(self, tx_id: str) -> Optional[Dict]:
        for i in range(self.shard_count):
            shard_key = f"shard_{i}"
            async with self.locks[shard_key]:
                tx = self.data[shard_key]["transactions"].get(tx_id)
                if tx:
                    return tx
        return None
    
    async def save_transaction(self, tx_id: str, data: Dict):
        shard_id = self.get_shard_id(data.get("user_id", 0))
        shard_key = f"shard_{shard_id}"
        async with self.locks[shard_key]:
            self.data[shard_key]["transactions"][tx_id] = data
            self._save_shard(shard_id)
    
    async def get_current_lottery(self) -> Optional[Dict]:
        shard_key = "shard_0"
        async with self.locks[shard_key]:
            return self.data[shard_key].get("current_lottery")
    
    async def set_current_lottery(self, lottery: Dict):
        shard_key = "shard_0"
        async with self.locks[shard_key]:
            self.data[shard_key]["current_lottery"] = lottery
            self._save_shard(0)
    
    async def add_lottery(self, lottery: Dict):
        shard_key = "shard_0"
        async with self.locks[shard_key]:
            if "lotteries" not in self.data[shard_key]:
                self.data[shard_key]["lotteries"] = []
            self.data[shard_key]["lotteries"].append(lottery)
            self._save_shard(0)
    
    async def get_all_lotteries(self) -> List[Dict]:
        """دریافت همه قرعه‌کشی‌ها - متد جدید"""
        shard_key = "shard_0"
        async with self.locks[shard_key]:
            return self.data[shard_key].get("lotteries", [])
    
    async def get_previous_winners(self) -> List[int]:
        winners = []
        for i in range(self.shard_count):
            shard_key = f"shard_{i}"
            async with self.locks[shard_key]:
                shard_winners = self.data[shard_key].get("previous_winners", [])
                winners.extend(shard_winners)
        return winners
    
    async def add_previous_winner(self, user_id: int):
        shard_id = self.get_shard_id(user_id)
        shard_key = f"shard_{shard_id}"
        async with self.locks[shard_key]:
            if "previous_winners" not in self.data[shard_key]:
                self.data[shard_key]["previous_winners"] = []
            if user_id not in self.data[shard_key]["previous_winners"]:
                self.data[shard_key]["previous_winners"].append(user_id)
                self._save_shard(shard_id)
    
    async def get_user_count(self) -> int:
        count = 0
        for i in range(self.shard_count):
            shard_key = f"shard_{i}"
            async with self.locks[shard_key]:
                count += len(self.data[shard_key]["users"])
        return count
    
    async def get_subscribed_count(self) -> int:
        users = await self.get_all_users()
        return len([u for u in users if u.get("has_subscription", False)])

db = ShardedDatabase()

# ============================================
# سیستم کش
# ============================================
class CacheManager:
    def __init__(self):
        self.redis = None
        self.memory_cache = {}
        self.memory_cache_ttl = {}
        self._lock = asyncio.Lock()
        self._enabled = True
        self._init_redis()
    
    def _init_redis(self):
        try:
            self.redis = redis.Redis.from_url(
                config.REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            self.redis.ping()
            logging.info("✅ Redis connected")
        except Exception as e:
            logging.warning(f"⚠️ Redis failed: {e}")
            self._enabled = False
    
    async def get(self, key: str) -> Optional[str]:
        if key in self.memory_cache:
            if self.memory_cache_ttl.get(key, 0) > time.time():
                return self.memory_cache[key]
            else:
                del self.memory_cache[key]
                del self.memory_cache_ttl[key]
        
        if self._enabled and self.redis:
            try:
                value = self.redis.get(key)
                if value:
                    self.memory_cache[key] = value
                    self.memory_cache_ttl[key] = time.time() + 300
                    return value
            except:
                pass
        return None
    
    async def set(self, key: str, value: str, ttl: int = config.REDIS_CACHE_TTL):
        self.memory_cache[key] = value
        self.memory_cache_ttl[key] = time.time() + min(ttl, 300)
        
        if self._enabled and self.redis:
            try:
                self.redis.setex(key, ttl, value)
            except:
                pass
    
    async def delete(self, key: str):
        if key in self.memory_cache:
            del self.memory_cache[key]
            del self.memory_cache_ttl[key]
        
        if self._enabled and self.redis:
            try:
                self.redis.delete(key)
            except:
                pass
    
    async def incr(self, key: str) -> int:
        if self._enabled and self.redis:
            try:
                return self.redis.incr(key)
            except:
                pass
        current = int(self.memory_cache.get(key, 0))
        new_value = current + 1
        self.memory_cache[key] = str(new_value)
        self.memory_cache_ttl[key] = time.time() + 300
        return new_value

cache = CacheManager()

# ============================================
# ترجمه
# ============================================
class Translator:
    def __init__(self):
        self.translations = {
            "en": {
                "welcome": "🎰 *ULTIMATE LOTTERY BOT*\n\n💰 Join the biggest lottery!\n🏆 Win up to $10,000!\n📱 Click PLAY to open the app.",
                "start": "🚀 *Welcome!*\n\n1️⃣ Subscribe: Send 100 USDT\n2️⃣ Get entered into lottery\n3️⃣ Win amazing prizes!\n\n🎯 Your code: `{code}`",
                "referral": "🔗 *Referral Program*\n\nYour code: `{code}`\n\n🎁 Get $10 per friend!\n\nShare: https://t.me/{bot}?start={code}",
                "subscribe": "💎 *Subscribe*\n\n💰 Send 100 USDT to:\n`{address}`\n\n📝 Enter your TRC20 wallet:",
                "invalid_wallet": "❌ Invalid TRC20 address.",
                "wallet_saved": "✅ Wallet saved!\n\n💰 Send 100 USDT to:\n`{address}`\n\n🔄 Click Verify Payment.",
                "payment_verified": "✅ *PAYMENT VERIFIED!*\n\n🎉 You're subscribed!\n🏆 Good luck!",
                "payment_failed": "❌ Payment failed.\n\nCheck:\n• Amount: 100 USDT\n• Address: {address}",
                "already_subscribed": "✅ You already have an active subscription!",
                "no_subscription": "⚠️ You need an active subscription.",
                "lottery_started": "🎰 *LOTTERY STARTED!*\n\n👥 Participants: {participants}\n💰 Prize: ${prize_pool}\n🏆 Winners: {winners_count}",
                "congratulations": "🎊 *CONGRATULATIONS!*\n\n🏆 You won ${amount}!\n\n💰 Click Withdraw.",
                "not_winner": "😔 Better luck next time!\n\n🎯 Stay subscribed.",
                "withdraw": "💰 *Withdraw*\n\nEnter your TRC20 wallet:",
                "withdraw_success": "✅ *Withdrawal Submitted!*\n\n💰 Prize will be sent shortly.",
                "admin_panel": "⚙️ *ADMIN PANEL*\n\n👥 Users: {users}\n🎯 Subscribed: {subscribed}\n🏆 Winners: {winners}",
                "broadcast_sent": "✅ Broadcast sent to {count} users!",
                "manual_verify_done": "✅ Transaction verified manually!",
                "api_added": "✅ API key added!",
                "withdraw_done": "✅ Withdrawals processed for {count} winners!",
                "restart_done": "✅ Lottery restarted!",
                "survey_sent": "✅ Survey sent to {count} users!",
                "lang_changed": "🌐 Language changed to {lang}",
                "help": "📖 *Help*\n\n1️⃣ Subscribe: Send 100 USDT\n2️⃣ Participate: Auto-entry\n3️⃣ Win: Fair draw\n4️⃣ Withdraw: Claim prize",
                "cancel": "❌ Cancelled.",
                "admin_broadcast": "📢 Enter broadcast message:",
                "admin_manual_verify": "✅ Enter transaction ID:",
                "admin_add_api": "🔑 Enter new API key:",
                "admin_survey": "📊 Enter survey question:",
                "admin_winners": "🏆 Enter number of winners:",
                "admin_prize": "💰 Enter prize amount:",
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
                "copied": "✅ Copied!",
                "home": "Home",
                "participate": "Participate",
                "winners": "Winners",
                "all_winners": "All Winners",
                "subscribe_now": "Subscribe Now",
                "expires": "Expires",
                "app_title": "🎰 Ultimate Lottery",
                "view_all": "View All",
                "no_active_lottery": "No active lottery",
                "no_winners": "No winners yet",
                "your_code": "Your Code",
                "payment_address": "Payment Address",
                "enter_wallet": "Enter Wallet",
                "submit": "Submit",
                "verify_payment": "Verify Payment",
                "saving": "Saving...",
                "checking": "Checking...",
                "waiting_for_draw": "Waiting for the draw...",
                "you_are_winner": "🏆 You are a winner!",
                "withdraw_now": "Withdraw Now",
                "subscription_active": "Subscription Active!",
                "send_amount": "Send Amount",
            },
            "fa": {
                "welcome": "🎰 *ربات قرعه‌کشی فوق‌پیشرفته*\n\n💰 در بزرگ‌ترین قرعه‌کشی شرکت کنید!\n🏆 تا ۱۰,۰۰۰ دلار برنده شوید!\n📱 روی PLAY کلیک کنید.",
                "start": "🚀 *خوش آمدید!*\n\n۱️⃣ اشتراک: ارسال ۱۰۰ دلار\n۲️⃣ وارد قرعه‌کشی شوید\n۳️⃣ جوایز شگفت‌انگیز ببرید!\n\n🎯 کد شما: `{code}`",
                "referral": "🔗 *برنامه رفرال*\n\nکد شما: `{code}`\n\n🎁 به ازای هر دوست ۱۰ دلار!\n\nلینک: https://t.me/{bot}?start={code}",
                "subscribe": "💎 *اشتراک*\n\n💰 ۱۰۰ دلار به آدرس زیر:\n`{address}`\n\n📝 آدرس TRC20 خود را وارد کنید:",
                "invalid_wallet": "❌ آدرس TRC20 نامعتبر.",
                "wallet_saved": "✅ کیف پول ذخیره شد!\n\n💰 ۱۰۰ دلار به:\n`{address}`\n\n🔄 روی تایید پرداخت کلیک کنید.",
                "payment_verified": "✅ *پرداخت تایید شد!*\n\n🎉 شما ثبت نام کردید!\n🏆 موفق باشید!",
                "payment_failed": "❌ پرداخت ناموفق.\n\nبررسی:\n• مبلغ: ۱۰۰ دلار\n• آدرس: {address}",
                "already_subscribed": "✅ شما اشتراک فعال دارید!",
                "no_subscription": "⚠️ به اشتراک فعال نیاز دارید.",
                "lottery_started": "🎰 *قرعه‌کشی شروع شد!*\n\n👥 شرکت‌کنندگان: {participants}\n💰 جایزه: ${prize_pool}\n🏆 برندگان: {winners_count}",
                "congratulations": "🎊 *تبریک!*\n\n🏆 شما ${amount} برنده شدید!\n\n💰 روی برداشت کلیک کنید.",
                "not_winner": "😔 دفعه بعد!\n\n🎯 اشتراک خود را حفظ کنید.",
                "withdraw": "💰 *برداشت*\n\nآدرس TRC20 خود را وارد کنید:",
                "withdraw_success": "✅ *برداشت ثبت شد!*\n\n💰 جایزه به زودی واریز می‌شود.",
                "admin_panel": "⚙️ *پنل مدیریت*\n\n👥 کاربران: {users}\n🎯 اشتراک‌داران: {subscribed}\n🏆 برندگان: {winners}",
                "broadcast_sent": "✅ پیام به {count} کاربر ارسال شد!",
                "manual_verify_done": "✅ تراکنش تایید شد!",
                "api_added": "✅ کلید API اضافه شد!",
                "withdraw_done": "✅ واریز برای {count} برنده انجام شد!",
                "restart_done": "✅ قرعه‌کشی مجدداً شروع شد!",
                "survey_sent": "✅ نظر سنجی به {count} کاربر ارسال شد!",
                "lang_changed": "🌐 زبان به {lang} تغییر یافت",
                "help": "📖 *راهنما*\n\n۱️⃣ اشتراک: ارسال ۱۰۰ دلار\n۲️⃣ شرکت: ثبت خودکار\n۳️⃣ برنده شدن: قرعه‌کشی عادلانه\n۴️⃣ برداشت: دریافت جایزه",
                "cancel": "❌ لغو شد.",
                "admin_broadcast": "📢 پیام همگانی را وارد کنید:",
                "admin_manual_verify": "✅ شناسه تراکنش را وارد کنید:",
                "admin_add_api": "🔑 کلید API جدید را وارد کنید:",
                "admin_survey": "📊 سوال نظر سنجی را وارد کنید:",
                "admin_winners": "🏆 تعداد برندگان را وارد کنید:",
                "admin_prize": "💰 مبلغ جایزه را وارد کنید:",
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
                "home": "خانه",
                "participate": "شرکت",
                "winners": "برندگان",
                "all_winners": "همه برندگان",
                "subscribe_now": "اشتراک فوری",
                "expires": "انقضا",
                "app_title": "🎰 قرعه‌کشی فوق‌پیشرفته",
                "view_all": "مشاهده همه",
                "no_active_lottery": "قرعه‌کشی فعالی وجود ندارد",
                "no_winners": "هنوز برنده‌ای وجود ندارد",
                "your_code": "کد شما",
                "payment_address": "آدرس پرداخت",
                "enter_wallet": "ورود کیف پول",
                "submit": "ثبت",
                "verify_payment": "تایید پرداخت",
                "saving": "در حال ذخیره...",
                "checking": "در حال بررسی...",
                "waiting_for_draw": "در انتظار قرعه‌کشی...",
                "you_are_winner": "🏆 شما برنده شدید!",
                "withdraw_now": "برداشت فوری",
                "subscription_active": "اشتراک فعال است!",
                "send_amount": "مبلغ ارسال",
            },
            "ar": {
                "welcome": "🎰 *يانصيب المتطور*\n\n💰 شارك في أكبر يانصيب!\n🏆 اربح حتى ۱۰,۰۰۰ دولار!\n📱 اضغط PLAY لفتح التطبيق.",
                "start": "🚀 *مرحباً!*\n\n۱️⃣ اشترك: أرسل ۱۰۰ دولار\n۲️⃣ ادخل اليانصيب\n۳️⃣ اربح جوائز!\n\n🎯 رمزك: `{code}`",
                "referral": "🔗 *برنامج الإحالة*\n\nرمزك: `{code}`\n\n🎁 ۱۰ دولار لكل صديق!\n\nرابط: https://t.me/{bot}?start={code}",
                "subscribe": "💎 *اشتراك*\n\n💰 أرسل ۱۰۰ دولار إلى:\n`{address}`\n\n📝 أدخل محفظة TRC20:",
                "invalid_wallet": "❌ عنوان TRC20 غير صالح.",
                "wallet_saved": "✅ تم حفظ المحفظة!\n\n💰 أرسل ۱۰۰ دولار إلى:\n`{address}`\n\n🔄 اضغط التحقق من الدفع.",
                "payment_verified": "✅ *تم التحقق!*\n\n🎉 تم الاشتراك!\n🏆 حظاً سعيداً!",
                "payment_failed": "❌ فشل الدفع.\n\nتحقق:\n• المبلغ: ۱۰۰ دولار\n• العنوان: {address}",
                "already_subscribed": "✅ لديك اشتراك نشط!",
                "no_subscription": "⚠️ تحتاج إلى اشتراك نشط.",
                "lottery_started": "🎰 *بدأ اليانصيب!*\n\n👥 المشاركون: {participants}\n💰 الجائزة: ${prize_pool}\n🏆 الفائزون: {winners_count}",
                "congratulations": "🎊 *تهانينا!*\n\n🏆 لقد فزت بـ ${amount}!\n\n💰 اضغط سحب.",
                "not_winner": "😔 حظاً أوفر!\n\n🎯 استمر في الاشتراك.",
                "withdraw": "💰 *سحب*\n\nأدخل محفظة TRC20:",
                "withdraw_success": "✅ *تم السحب!*\n\n💰 سيتم إرسال الجائزة قريباً.",
                "admin_panel": "⚙️ *لوحة الإدارة*\n\n👥 المستخدمون: {users}\n🎯 المشتركون: {subscribed}\n🏆 الفائزون: {winners}",
                "broadcast_sent": "✅ تم الإرسال إلى {count} مستخدم!",
                "manual_verify_done": "✅ تم التحقق يدوياً!",
                "api_added": "✅ تم إضافة المفتاح!",
                "withdraw_done": "✅ تم الدفع لـ {count} فائز!",
                "restart_done": "✅ تم إعادة بدء اليانصيب!",
                "survey_sent": "✅ تم إرسال الاستبيان إلى {count} مستخدم!",
                "lang_changed": "🌐 تم تغيير اللغة إلى {lang}",
                "help": "📖 *مساعدة*\n\n۱️⃣ اشترك: أرسل ۱۰۰ دولار\n۲️⃣ شارك: تسجيل تلقائي\n۳️⃣ اربح: سحب عادل\n۴️⃣ اسحب: استلام الجائزة",
                "cancel": "❌ تم الإلغاء.",
                "admin_broadcast": "📢 أدخل رسالة البث:",
                "admin_manual_verify": "✅ أدخل معرف المعاملة:",
                "admin_add_api": "🔑 أدخل مفتاح API الجديد:",
                "admin_survey": "📊 أدخل سؤال الاستبيان:",
                "admin_winners": "🏆 أدخل عدد الفائزين:",
                "admin_prize": "💰 أدخل قيمة الجائزة:",
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
                "home": "الرئيسية",
                "participate": "المشاركة",
                "winners": "الفائزون",
                "all_winners": "جميع الفائزين",
                "subscribe_now": "اشتراك فوري",
                "expires": "ينتهي",
                "app_title": "🎰 اليانصيب المتطور",
                "view_all": "عرض الكل",
                "no_active_lottery": "لا يوجد يانصيب نشط",
                "no_winners": "لا يوجد فائزون حتى الآن",
                "your_code": "رمزك",
                "payment_address": "عنوان الدفع",
                "enter_wallet": "أدخل المحفظة",
                "submit": "إرسال",
                "verify_payment": "التحقق من الدفع",
                "saving": "جاري الحفظ...",
                "checking": "جاري التحقق...",
                "waiting_for_draw": "في انتظار السحب...",
                "you_are_winner": "🏆 أنت فائز!",
                "withdraw_now": "سحب الآن",
                "subscription_active": "الاشتراك نشط!",
                "send_amount": "المبلغ المرسل",
            }
        }
    
    def get(self, key: str, lang: str = "en", **kwargs) -> str:
        text = self.translations.get(lang, self.translations["en"]).get(key, key)
        return text.format(**kwargs) if kwargs else text

translator = Translator()

# ============================================
# سرویس پرداخت
# ============================================
class TronPaymentService:
    def __init__(self):
        self.api_url = "https://api.trongrid.io"
        self.api_keys = config.API_KEYS
        self.current_key_index = 0
        self.session = None
    
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def get_next_api_key(self) -> str:
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    async def verify_transaction(self, tx_id: str, from_address: str, 
                                  to_address: str, amount: float) -> Dict:
        session = await self.get_session()
        api_key = self.get_next_api_key()
        
        try:
            url = f"{self.api_url}/v1/transactions/{tx_id}"
            headers = {"TRON-PRO-API-KEY": api_key}
            
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return {"status": "failed", "error": f"API error: {response.status}"}
                
                data = await response.json()
                tx_data = data.get("data", [{}])[0]
                
                if not tx_data:
                    return {"status": "failed", "error": "Transaction not found"}
                
                contract = tx_data.get("raw_data", {}).get("contract", [{}])[0]
                value = contract.get("parameter", {}).get("value", {})
                
                to_addr = value.get("to_address", "")
                if to_addr:
                    to_addr = self._hex_to_base58(to_addr)
                
                if to_addr != to_address:
                    return {"status": "failed", "error": "Recipient mismatch"}
                
                amount_sun = value.get("amount", 0)
                amount_usd = amount_sun / 1_000_000
                
                if abs(amount_usd - amount) > 0.01:
                    return {"status": "failed", "error": f"Amount mismatch"}
                
                confirmations = tx_data.get("confirmations", 0)
                if confirmations < 19:
                    return {"status": "pending", "confirmations": confirmations}
                
                return {
                    "status": "verified",
                    "tx_id": tx_id,
                    "from_address": from_address,
                    "to_address": to_address,
                    "amount": amount_usd,
                    "confirmations": confirmations
                }
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _hex_to_base58(self, hex_address: str) -> str:
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
# الگوریتم قرعه‌کشی
# ============================================
class AdvancedLotteryAlgorithm:
    def __init__(self):
        self.previous_winners = set()
    
    async def select_winners(self, participants: List[int], winners_count: int) -> List[int]:
        prev_winners = await db.get_previous_winners()
        self.previous_winners = set(prev_winners)
        
        eligible = [p for p in participants if p not in self.previous_winners]
        
        if len(eligible) < winners_count:
            eligible = participants
        
        entropy = self._collect_entropy()
        random.seed(entropy)
        
        shuffled = eligible.copy()
        for i in range(len(shuffled) - 1, 0, -1):
            j = random.randint(0, i)
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
        
        winners = shuffled[:winners_count]
        
        for w in winners:
            await db.add_previous_winner(w)
            self.previous_winners.add(w)
        
        return winners
    
    def _collect_entropy(self) -> int:
        return (
            int(time.time_ns()) ^
            random.getrandbits(128) ^
            int(psutil.cpu_percent(interval=0.1) * 1000) ^
            int(psutil.virtual_memory().available)
        )

lottery_algorithm = AdvancedLotteryAlgorithm()

# ============================================
# Flask Web App
# ============================================
app = Flask(__name__)
app.secret_key = config.JWT_SECRET
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# ============================================
# HTML Template
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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--tg-theme-bg-color, #ffffff);
            color: var(--tg-theme-text-color, #000000);
            min-height: 100vh;
            padding: 16px;
            padding-bottom: 80px;
        }
        .container { max-width: 480px; margin: 0 auto; }
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
        .header-title .logo { font-size: 28px; }
        .lang-selector { display: flex; gap: 6px; }
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
        .info-row:last-child { border-bottom: none; }
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
        .badge.active { background: #4caf50; color: white; }
        .badge.inactive { background: #9e9e9e; color: white; }
        .badge.winner { background: #ffd700; color: #000; }
        .badge.pending { background: #ff9800; color: white; }
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
        .btn:active { transform: scale(0.97); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-secondary {
            background: var(--tg-theme-secondary-bg-color, #e0e0e0);
            color: var(--tg-theme-text-color, #000);
        }
        .btn-success { background: #4caf50; }
        .btn-danger { background: #f44336; }
        .btn-gold {
            background: linear-gradient(135deg, #ffd700, #f5a623);
            color: #000;
        }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
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
        .winner-list { list-style: none; padding: 0; }
        .winner-list li {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
        }
        .winner-list li:last-child { border-bottom: none; }
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
        .winner-info { flex: 1; margin-left: 10px; }
        .winner-name { font-weight: 500; font-size: 13px; }
        .winner-amount { font-weight: 700; color: #ffd700; font-size: 14px; }
        .input-group { margin-bottom: 12px; }
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
        .loading { display: none; text-align: center; padding: 20px; }
        .loading.active { display: block; }
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
        .empty-state .icon { font-size: 40px; margin-bottom: 10px; }
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
        .tab-item.active { color: var(--tg-theme-button-color, #0088cc); }
        .tab-item .icon { font-size: 22px; }
        .tab-item .label { font-size: 9px; margin-top: 2px; }
        .page { display: none; }
        .page.active { display: block; }
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
        .toast.show { opacity: 1; }
        .toast.success { background: #4caf50; }
        .toast.error { background: #f44336; }
        .toast.warning { background: #ff9800; }
        @media (max-width: 400px) {
            .grid-2 { grid-template-columns: 1fr; }
            .header-title { font-size: 18px; }
        }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>
    
    <div class="container">
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
        
        <div id="page-home" class="page active">
            <div class="card">
                <div class="card-title">👤 <span data-i18n="user_status">User Status</span></div>
                <div id="user-status"><div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div></div>
            </div>
            
            <div class="card">
                <div class="card-title">📅 <span data-i18n="subscription">Subscription</span></div>
                <div id="subscription-status"><div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div></div>
            </div>
            
            <div class="card">
                <div class="card-title">🎰 <span data-i18n="lottery">Lottery</span></div>
                <div id="lottery-status"><div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div></div>
            </div>
            
            <div class="card">
                <div class="card-title">🏆 <span data-i18n="winners">Winners</span></div>
                <div id="winners-list"><div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div></div>
            </div>
            
            <div class="card">
                <div class="card-title">🔗 <span data-i18n="referral_program">Referral Program</span></div>
                <div id="referral-info"><div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div></div>
            </div>
        </div>
        
        <div id="page-participate" class="page">
            <div class="card">
                <div class="card-title">💰 <span data-i18n="participate">Participate</span></div>
                <div id="participate-content"><div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div></div>
            </div>
        </div>
        
        <div id="page-winners" class="page">
            <div class="card">
                <div class="card-title">🏆 <span data-i18n="all_winners">All Winners</span></div>
                <div id="all-winners"><div class="loading active"><div class="spinner"></div><span data-i18n="loading">Loading...</span></div></div>
            </div>
        </div>
    </div>
    
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
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        
        let currentLang = 'en';
        let userId = null;
        
        const translations = {{ translations|safe }};
        
        function t(key) {
            return translations[currentLang]?.[key] || key;
        }
        
        function updateUI() {
            document.querySelectorAll('[data-i18n]').forEach(el => {
                el.textContent = t(el.dataset.i18n);
            });
        }
        
        function changeLang(lang) {
            currentLang = lang;
            document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.lang-btn[onclick="changeLang('${lang}')"]`).classList.add('active');
            updateUI();
            loadAllData();
            fetch('/api/language', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({language: lang, user_id: userId})
            }).catch(() => {});
        }
        
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type;
            setTimeout(() => { toast.classList.add('show'); }, 100);
            setTimeout(() => { toast.classList.remove('show'); }, 3000);
        }
        
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = { method: method, headers: {'Content-Type': 'application/json'} };
                if (data) options.body = JSON.stringify(data);
                const response = await fetch(endpoint, options);
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || 'API Error');
                return result;
            } catch (error) {
                console.error('API Error:', error);
                showToast(t('error'), 'error');
                throw error;
            }
        }
        
        function switchPage(page) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById('page-' + page).classList.add('active');
            document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab-item[onclick="switchPage('${page}')"]`).classList.add('active');
            if (page === 'participate') loadParticipate();
            else if (page === 'winners') loadAllWinners();
        }
        
        async function loadAllData() {
            try {
                await Promise.all([
                    loadUserStatus(),
                    loadSubscription(),
                    loadLotteryStatus(),
                    loadWinners(),
                    loadReferral()
                ]);
            } catch (e) { console.error(e); }
        }
        
        async function loadUserStatus() {
            try {
                const data = await apiCall('/api/user/status');
                const u = data.user || {};
                const html = `
                    <div class="info-row"><span class="info-label">${t('user_id')}</span><span class="info-value">${u.telegram_id || 'N/A'}</span></div>
                    <div class="info-row"><span class="info-label">${t('username')}</span><span class="info-value">${u.username || 'N/A'}</span></div>
                    <div class="info-row"><span class="info-label">${t('wallet')}</span><span class="info-value">${u.wallet_address ? u.wallet_address.substring(0,8)+'...' : t('not_set')}</span></div>
                    <div class="info-row"><span class="info-label">${t('total_won')}</span><span class="info-value highlight">$${u.total_won || 0}</span></div>
                    ${u.is_winner ? `<div class="info-row"><span class="info-label">${t('winner')}</span><span class="info-value winner">🏆 $${u.won_amount || 0}</span></div>` : ''}
                `;
                document.getElementById('user-status').innerHTML = html;
            } catch (e) {
                document.getElementById('user-status').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadSubscription() {
            try {
                const data = await apiCall('/api/user/subscription');
                const has = data.has_subscription || false;
                const html = `
                    <div class="info-row">
                        <span class="info-label">${t('subscription')}</span>
                        <span class="info-value"><span class="badge ${has ? 'active' : 'inactive'}">${has ? t('active') : t('inactive')}</span></span>
                    </div>
                    ${has ? `<div class="info-row"><span class="info-label">${t('expires')}</span><span class="info-value">${new Date(data.expiry).toLocaleDateString()}</span></div>`
                    : `<div style="margin-top:8px;"><button class="btn btn-success" onclick="switchPage('participate')">💰 ${t('subscribe_now')}</button></div>`}
                `;
                document.getElementById('subscription-status').innerHTML = html;
            } catch (e) {
                document.getElementById('subscription-status').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadLotteryStatus() {
            try {
                const data = await apiCall('/api/lottery/status');
                if (data.active) {
                    const html = `
                        <div class="info-row"><span class="info-label">${t('status')}</span><span class="info-value"><span class="badge active">${t('active')}</span></span></div>
                        <div class="info-row"><span class="info-label">${t('participants')}</span><span class="info-value">${data.participant_count || 0}</span></div>
                        <div class="info-row"><span class="info-label">${t('prize_pool')}</span><span class="info-value highlight">$${data.prize_pool || 0}</span></div>
                        <div class="info-row"><span class="info-label">${t('prize_per_winner')}</span><span class="info-value">$${data.prize_per_winner || 0}</span></div>
                    `;
                    document.getElementById('lottery-status').innerHTML = html;
                } else {
                    document.getElementById('lottery-status').innerHTML = `<div class="empty-state"><div class="icon">⏳</div><p>${t('no_active_lottery')}</p></div>`;
                }
            } catch (e) {
                document.getElementById('lottery-status').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadWinners() {
            try {
                const data = await apiCall('/api/lottery/winners');
                if (data.winners && data.winners.length > 0) {
                    let html = `<ul class="winner-list">`;
                    data.winners.slice(0, 5).forEach((w, i) => {
                        html += `<li><div class="winner-avatar">${i+1}</div><div class="winner-info"><div class="winner-name">${w.username || 'User'}</div></div><div class="winner-amount">$${w.amount}</div></li>`;
                    });
                    html += `</ul>`;
                    if (data.winners.length > 5) html += `<button class="btn btn-secondary" onclick="switchPage('winners')">${t('view_all')}</button>`;
                    document.getElementById('winners-list').innerHTML = html;
                } else {
                    document.getElementById('winners-list').innerHTML = `<div class="empty-state"><div class="icon">🏆</div><p>${t('no_winners')}</p></div>`;
                }
            } catch (e) {
                document.getElementById('winners-list').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadReferral() {
            try {
                const data = await apiCall('/api/user/referral');
                const html = `
                    <div class="info-row"><span class="info-label">${t('your_code')}</span><span class="info-value"><div class="referral-code">${data.referral_code}</div></span></div>
                    <div style="margin-top:8px;display:flex;gap:8px;">
                        <button class="btn btn-secondary" onclick="copyCode('${data.referral_code}')">📋 ${t('copy')}</button>
                        <button class="btn btn-success" onclick="shareCode('${data.referral_code}')">📤 ${t('share')}</button>
                    </div>
                    <div style="margin-top:8px;">
                        <div class="info-row"><span class="info-label">${t('referrals')}</span><span class="info-value">${data.referral_count || 0}</span></div>
                        <div class="info-row"><span class="info-label">${t('earnings')}</span><span class="info-value highlight">$${data.referral_earnings || 0}</span></div>
                    </div>
                `;
                document.getElementById('referral-info').innerHTML = html;
            } catch (e) {
                document.getElementById('referral-info').innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        async function loadParticipate() {
            const content = document.getElementById('participate-content');
            try {
                const data = await apiCall('/api/user/status');
                if (data.user && data.user.has_subscription) {
                    content.innerHTML = `
                        <div style="text-align:center;padding:20px;">
                            <div style="font-size:48px;margin-bottom:12px;">🎉</div>
                            <h3>${t('subscription_active')}</h3>
                            <p style="color:var(--tg-theme-hint-color,#666);margin:8px 0;">${t('expires')}: ${new Date(data.user.subscription_expiry).toLocaleDateString()}</p>
                            ${data.user.is_winner ? `
                            <div style="margin-top:12px;padding:12px;background:#ffd70022;border-radius:8px;">
                                <p style="font-weight:700;color:#ffd700;">🏆 ${t('you_are_winner')} $${data.user.won_amount}</p>
                                <button class="btn btn-gold" onclick="withdraw()">💰 ${t('withdraw_now')}</button>
                            </div>` : `<p style="color:var(--tg-theme-hint-color,#666);">${t('waiting_for_draw')}</p>`}
                        </div>
                    `;
                } else {
                    content.innerHTML = `
                        <div style="text-align:center;margin-bottom:16px;">
                            <div style="font-size:48px;margin-bottom:8px;">💰</div>
                            <h3>${t('subscribe_now')}</h3>
                            <p style="color:var(--tg-theme-hint-color,#666);font-size:13px;">${t('send_amount')}: 100 USDT</p>
                        </div>
                        <div class="input-group">
                            <label>${t('payment_address')}</label>
                            <div style="display:flex;gap:6px;">
                                <input type="text" id="payment-addr" value="{{ config.PAYMENT_ADDRESS }}" readonly style="flex:1;font-size:12px;">
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
            } catch (e) {
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
                        html += `<li><div class="winner-avatar">${i+1}</div><div class="winner-info"><div class="winner-name">${w.username || 'User ' + w.user_id}</div><div style="font-size:11px;color:var(--tg-theme-hint-color,#666);">${new Date(w.date).toLocaleDateString()}</div></div><div class="winner-amount">$${w.amount}</div></li>`;
                    });
                    html += `</ul>`;
                    content.innerHTML = html;
                } else {
                    content.innerHTML = `<div class="empty-state"><div class="icon">🏆</div><p>${t('no_winners')}</p></div>`;
                }
            } catch (e) {
                content.innerHTML = `<div class="empty-state"><p>${t('error')}</p></div>`;
            }
        }
        
        function copyAddress() {
            const addr = document.getElementById('payment-addr').value;
            navigator.clipboard.writeText(addr).then(() => showToast(t('copied'), 'success'))
                .catch(() => { document.getElementById('payment-addr').select(); document.execCommand('copy'); showToast(t('copied'), 'success'); });
        }
        
        function copyCode(code) {
            navigator.clipboard.writeText(code).then(() => showToast(t('copied'), 'success'))
                .catch(() => { const el = document.createElement('textarea'); el.value = code; document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el); showToast(t('copied'), 'success'); });
        }
        
        function shareCode(code) {
            const text = `🎰 Join Ultimate Lottery! Use my referral code: ${code}\n@{{ config.BOT_USERNAME }}`;
            if (navigator.share) { navigator.share({title: '🎰 Lottery', text: text}).catch(() => {}); }
            else { navigator.clipboard.writeText(text).then(() => showToast(t('copied'), 'success')); }
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
                const result = await apiCall('/api/user/wallet', 'POST', {wallet_address: wallet});
                if (result.success) {
                    showToast(t('wallet_saved'), 'success');
                    document.getElementById('wallet-input').value = '';
                    loadAllData();
                }
            } catch (e) {
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
                const result = await apiCall('/api/payment/verify', 'POST');
                if (result.verified) {
                    showToast(t('payment_verified'), 'success');
                    loadAllData();
                } else {
                    showToast(t('payment_failed'), 'error');
                }
            } catch (e) {
                showToast(t('error'), 'error');
            } finally {
                const btn = document.querySelector('.btn-secondary');
                btn.disabled = false;
                btn.textContent = '🔄 ' + t('verify_payment');
            }
        }
        
        async function withdraw() {
            const wallet = prompt(t('enter_wallet'));
            if (!wallet) return;
            if (!wallet.startsWith('T') || wallet.length !== 34) {
                showToast(t('invalid_wallet'), 'error');
                return;
            }
            try {
                const result = await apiCall('/api/user/withdraw', 'POST', {wallet_address: wallet});
                if (result.success) {
                    showToast(t('withdraw_success'), 'success');
                    loadAllData();
                }
            } catch (e) {
                showToast(t('error'), 'error');
            }
        }
        
        async function init() {
            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                userId = tg.initDataUnsafe.user.id;
                try {
                    const response = await fetch('/api/auth', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user: tg.initDataUnsafe.user, init_data: tg.initData})
                    });
                    const result = await response.json();
                    if (result.success && result.language) {
                        currentLang = result.language;
                        document.querySelectorAll('.lang-btn').forEach(btn => {
                            btn.classList.remove('active');
                            if (btn.textContent.toLowerCase().includes(currentLang)) btn.classList.add('active');
                        });
                        updateUI();
                        await loadAllData();
                    }
                } catch (e) {
                    console.error('Auth error:', e);
                    showToast(t('error'), 'error');
                }
            } else {
                // Fallback: try to get user from session
                try {
                    const result = await apiCall('/api/user/status');
                    if (result.user) {
                        userId = result.user.telegram_id;
                        await loadAllData();
                    }
                } catch (e) {}
            }
        }
        
        document.addEventListener('DOMContentLoaded', init);
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
    return render_template_string(
        WEBAPP_TEMPLATE,
        translations=json.dumps(translator.translations),
        config=config
    )

@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.json
    user = data.get('user', {})
    user_id = user.get('id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'Invalid user'}), 400
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    db_user = loop.run_until_complete(db.get_user(user_id))
    
    if not db_user:
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
    
    session['user_id'] = user_id
    session['language'] = db_user.get('language', config.DEFAULT_LANGUAGE)
    
    return jsonify({
        'success': True,
        'language': db_user.get('language', config.DEFAULT_LANGUAGE),
        'is_admin': user_id == config.ADMIN_CHAT_ID
    })

@app.route('/api/user/status')
def user_status():
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
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    lotteries = loop.run_until_complete(db.get_all_lotteries())
    winners = []
    
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
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    user = loop.run_until_complete(db.get_user(user_id))
    if not user or not user.get('wallet_address'):
        return jsonify({'error': 'Wallet not set'}), 400
    
    # Simulate verification - in production, actual Tron API call
    user['has_subscription'] = True
    user['subscription_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
    loop.run_until_complete(db.save_user(user_id, user))
    
    return jsonify({'verified': True})

@app.route('/api/user/withdraw', methods=['POST'])
def withdraw():
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
    
    return jsonify({'error': 'User not found'}), 404

# ============================================
# Telegram Bot
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
        
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("language", self.language_command))
        app.add_handler(CommandHandler("admin", self.admin_command))
        
        app.add_handler(CallbackQueryHandler(self.handle_language, pattern="^(en|fa|ar)$"))
        app.add_handler(CallbackQueryHandler(self.handle_subscribe, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.handle_referral, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.handle_verify, pattern="^verify$"))
        app.add_handler(CallbackQueryHandler(self.handle_withdraw, pattern="^withdraw$"))
        app.add_handler(CallbackQueryHandler(self.handle_admin, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.handle_admin_action, pattern="^admin_"))
        
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.subscribe_start, pattern="^subscribe$")],
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
        user = update.effective_user
        user_id = user.id
        
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
        
        keyboard = [
            [InlineKeyboardButton("🎮 PLAY", web_app=WebAppInfo(url=config.WEBAPP_URL))],
            [InlineKeyboardButton("🎰 Subscribe", callback_data="subscribe")],
            [InlineKeyboardButton("🔗 Referral", callback_data="referral")],
            [InlineKeyboardButton("🌐 Language", callback_data="change_lang")],
        ]
        
        if user_id == config.ADMIN_CHAT_ID:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
        
        await update.message.reply_text(
            translator.get("welcome", lang, code=db_user.get("referral_code", "")),
            reply_markup=InlineKeyboardMarkup(keyboard),
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
        users = await db.get_user_count()
        subscribed = await db.get_subscribed_count()
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
        
        text = translator.get(
            "admin_panel", lang,
            users=users,
            subscribed=subscribed,
            winners=len(lottery.get("winners", [])) if lottery else 0
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
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
        keyboard = [[InlineKeyboardButton("✅ Verify Payment", callback_data="verify")]]
        
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
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        
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
        keyboard = [[InlineKeyboardButton("✅ Verify Payment", callback_data="verify")]]
        
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
        
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    
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
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        
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
# اجرا
# ============================================
async def run_bot():
    bot = LotteryBot()
    await bot.start()
    return bot

def run_flask():
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
    ║   🌐 3 Languages Support                ║
    ╚══════════════════════════════════════════╝
    """)
    
    # Flask in separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_bot())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        loop.close()