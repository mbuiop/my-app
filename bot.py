# ===================================================================
# ربات کاریابی حرفه‌ای - نسخه یکپارچه با معماری ۱۰ میلیون کاربر
# ===================================================================
# این فایل شامل: ربات تلگرام + دیتابیس PostgreSQL + Redis Cache +
# پنل مدیریت تحت وب (FastAPI) + صفحه‌بندی + آمار + سیستم معرف + اشتراک
# ===================================================================

import asyncio
import logging
import datetime
import random
import string
import json
import hashlib
import zlib
import pickle
import os
from typing import Dict, List, Optional, Any, Tuple
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
import threading
import uvicorn

# ===================== وابستگی‌ها =====================
# pip install python-telegram-bot fastapi uvicorn sqlalchemy asyncpg redis aiosqlite python-dotenv pytz ujson orjin

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, AIORateLimiter
)
from telegram.request import HTTPXRequest

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean, DateTime,
    Text, Float, Index, ForeignKey, func, select, update, delete, and_, or_, desc, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

import redis.asyncio as redis
from redis.asyncio import Redis

import jwt
from passlib.context import CryptContext

# ===================== تنظیمات =====================
TOKEN = "توکن_ربات_خود_را_اینجا_قرار_دهید"
ADMIN_ID = 123456789  # از @userinfobot بگیرید

DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/jobbot"
REDIS_URL = "redis://localhost:6379/0"
SECRET_KEY = "your-super-secret-key-change-this"

# ===================== دیتابیس =====================
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_username', 'username'),
        Index('idx_subscribed', 'is_subscribed'),
        Index('idx_referral_code', 'referral_code'),
        Index('idx_created_at_user', 'created_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    
    is_admin = Column(Boolean, default=False)
    is_subscribed = Column(Boolean, default=False)
    subscription_end = Column(DateTime)
    subscription_type = Column(String(20))
    balance = Column(BigInteger, default=0)
    
    referral_code = Column(String(8), unique=True)
    referred_by = Column(BigInteger)
    referral_count = Column(Integer, default=0)
    referral_earnings = Column(BigInteger, default=0)
    
    notification_settings = Column(Text, default='{}')
    preferences = Column(Text, default='{}')
    
    is_blocked = Column(Boolean, default=False)
    block_reason = Column(Text)
    login_attempts = Column(Integer, default=0)
    last_ip = Column(String(45))
    
    created_at = Column(DateTime, default=datetime.datetime.now)
    last_active = Column(DateTime, default=datetime.datetime.now)
    last_notification = Column(DateTime)

class JobAd(Base):
    __tablename__ = 'job_ads'
    __table_args__ = (
        Index('idx_user_id_ad', 'user_id'),
        Index('idx_category_ad', 'category'),
        Index('idx_status_ad', 'is_active', 'is_approved'),
        Index('idx_created_at_ad', 'created_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    ad_type = Column(String(20))
    category = Column(String(50))
    sub_category = Column(String(50))
    
    title = Column(String(200))
    description = Column(Text)
    short_description = Column(String(500))
    
    contact = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    telegram = Column(String(50))
    website = Column(String(200))
    
    salary_min = Column(BigInteger)
    salary_max = Column(BigInteger)
    salary_type = Column(String(20))
    location = Column(String(100))
    location_lat = Column(Float)
    location_lng = Column(Float)
    remote = Column(Boolean, default=False)
    experience_min = Column(Integer)
    experience_max = Column(Integer)
    education = Column(String(50))
    gender = Column(String(20))
    age_min = Column(Integer)
    age_max = Column(Integer)
    
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    views = Column(BigInteger, default=0)
    clicks = Column(BigInteger, default=0)
    applications = Column(BigInteger, default=0)
    
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    expires_at = Column(DateTime)
    approved_at = Column(DateTime)

class Payment(Base):
    __tablename__ = 'payments'
    __table_args__ = (
        Index('idx_user_id_pay', 'user_id'),
        Index('idx_status_pay', 'status'),
        Index('idx_created_at_pay', 'created_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    amount = Column(BigInteger)
    type = Column(String(20))
    status = Column(String(20))
    method = Column(String(20))
    reference = Column(String(100))
    description = Column(Text)
    card_number = Column(String(20))
    wallet_address = Column(String(100))
    transaction_hash = Column(String(100))
    created_at = Column(DateTime, default=datetime.datetime.now)
    paid_at = Column(DateTime)

class PaymentSetting(Base):
    __tablename__ = 'payment_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    card_number = Column(String(50), default='شماره کارت ثبت نشده')
    price = Column(Integer, default=50000)
    wallet_address = Column(String(100))
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

class Broadcast(Base):
    __tablename__ = 'broadcasts'
    __table_args__ = (
        Index('idx_status_bc', 'status'),
        Index('idx_created_at_bc', 'created_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(200))
    message = Column(Text)
    media_type = Column(String(20))
    media_id = Column(String(200))
    target = Column(Text)
    sent_count = Column(BigInteger, default=0)
    total_count = Column(BigInteger, default=0)
    status = Column(String(20))
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.datetime.now)
    sent_at = Column(DateTime)

class AdminLog(Base):
    __tablename__ = 'admin_logs'
    __table_args__ = (
        Index('idx_admin_id_log', 'admin_id'),
        Index('idx_created_at_log', 'created_at'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    admin_id = Column(BigInteger)
    action = Column(String(50))
    target_type = Column(String(50))
    target_id = Column(String(100))
    details = Column(Text)
    ip = Column(String(45))
    created_at = Column(DateTime, default=datetime.datetime.now)

# ===================== اتصال دیتابیس =====================
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=50,
    max_overflow=100,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True
)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@asynccontextmanager
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with get_db() as db:
        settings = await db.execute(select(PaymentSetting))
        if not settings.scalar_one_or_none():
            db.add(PaymentSetting(card_number="شماره کارت خود را وارد کنید", price=50000, wallet_address="آدرس کیف پول"))
            await db.commit()

# ===================== Redis Cache =====================
class RedisCache:
    def __init__(self, url: str):
        self.url = url
        self._client: Optional[Redis] = None
        self._prefix = "jobbot:"
    
    async def connect(self):
        self._client = redis.from_url(
            self.url,
            decode_responses=True,
            max_connections=100,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        await self._client.ping()
        return self
    
    async def close(self):
        if self._client:
            await self._client.close()
    
    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"
    
    async def get(self, key: str, default: Any = None) -> Any:
        if not self._client:
            return default
        try:
            data = await self._client.get(self._key(key))
            if data:
                return json.loads(data)
            return default
        except:
            return default
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        if not self._client:
            return
        try:
            await self._client.setex(self._key(key), ttl, json.dumps(value, default=str))
        except:
            pass
    
    async def delete(self, key: str):
        if not self._client:
            return
        try:
            await self._client.delete(self._key(key))
        except:
            pass
    
    async def delete_pattern(self, pattern: str):
        if not self._client:
            return
        try:
            keys = await self._client.keys(self._key(pattern))
            if keys:
                await self._client.delete(*keys)
        except:
            pass
    
    async def incr(self, key: str, amount: int = 1) -> int:
        if not self._client:
            return 0
        try:
            return await self._client.incrby(self._key(key), amount)
        except:
            return 0
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        return await self.get(f"user:{user_id}")
    
    async def set_user(self, user_id: int, data: Dict, ttl: int = 600):
        await self.set(f"user:{user_id}", data, ttl)
    
    async def invalidate_user(self, user_id: int):
        await self.delete(f"user:{user_id}")
    
    async def get_ads_page(self, category: str = None, page: int = 1) -> Optional[List[Dict]]:
        key = f"ads:{category or 'all'}:page:{page}"
        return await self.get(key)
    
    async def set_ads_page(self, ads: List[Dict], category: str = None, page: int = 1, ttl: int = 300):
        key = f"ads:{category or 'all'}:page:{page}"
        await self.set(key, ads, ttl)
    
    async def invalidate_ads_cache(self, category: str = None):
        pattern = f"ads:{category or '*'}:*"
        await self.delete_pattern(pattern)
    
    async def get_stats(self) -> Dict:
        stats = {}
        if self._client:
            keys = await self._client.keys(self._key("stats:*"))
            for key in keys:
                name = key.replace(self._key("stats:"), "")
                val = await self._client.get(key)
                if val:
                    stats[name] = int(val)
        return stats
    
    async def incr_stat(self, name: str):
        await self.incr(f"stats:{name}")

cache = None

async def init_cache():
    global cache
    cache = RedisCache(REDIS_URL)
    await cache.connect()
    return cache

def get_cache() -> RedisCache:
    return cache

# ===================== دکمه‌ها =====================
CATEGORIES = [
    "برنامه‌نویسی", "طراحی گرافیک", "بازاریابی", "فروش",
    "مدیریت", "حسابداری", "حقوقی", "آموزش",
    "پزشکی", "مهندسی عمران", "مهندسی برق", "مهندسی مکانیک",
    "صنایع غذایی", "کشاورزی", "خدمات مشتریان", "منابع انسانی",
    "تولید محتوا", "ترجمه", "عکاسی", "موسیقی",
    "ورزش", "گردشگری", "حمل و نقل", "تعمیرات", "سایر"
]

def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📝 ثبت آگهی استخدام", callback_data="post_employer")],
        [InlineKeyboardButton("🔍 ثبت آگهی کاریابی", callback_data="post_job_seeker")],
        [InlineKeyboardButton("📋 مشاهده آگهی‌ها", callback_data="view_ads")],
        [InlineKeyboardButton("👤 آگهی‌های من", callback_data="my_ads")],
        [InlineKeyboardButton("💎 خرید اشتراک", callback_data="buy_subscription")],
        [InlineKeyboardButton("👥 سیستم معرف", callback_data="referral")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("🔐 پنل مدیریت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def admin_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💰 تنظیم قیمت", callback_data="admin_set_price")],
        [InlineKeyboardButton("💳 تنظیم کارت", callback_data="admin_set_card")],
        [InlineKeyboardButton("🪙 تنظیم کیف پول", callback_data="admin_set_wallet")],
        [InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats")],
        [InlineKeyboardButton("📋 مدیریت کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("🗑 حذف آگهی", callback_data="admin_delete_ad")],
        [InlineKeyboardButton("✅ تایید آگهی", callback_data="admin_approve_ad")],
        [InlineKeyboardButton("📊 گزارشات", callback_data="admin_reports")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def category_menu() -> InlineKeyboardMarkup:
    keyboard = []
    for i in range(0, len(CATEGORIES), 2):
        row = [InlineKeyboardButton(CATEGORIES[i], callback_data=f"cat_{i}")]
        if i + 1 < len(CATEGORIES):
            row.append(InlineKeyboardButton(CATEGORIES[i + 1], callback_data=f"cat_{i+1}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def pagination_buttons(page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    if page > 1:
        row.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"{prefix}_page_{page-1}"))
    row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data=f"{prefix}_current"))
    if page < total_pages:
        row.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"{prefix}_page_{page+1}"))
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

# ===================== ربات اصلی =====================
class JobBot:
    def __init__(self):
        self.user_steps = {}
        self.broadcast_running = False
    
    async def _is_admin(self, user_id: int) -> bool:
        cached = await get_cache().get_user(user_id)
        if cached:
            return cached.get('is_admin', False)
        
        async with get_db() as db:
            user = await db.execute(select(User).where(User.user_id == user_id))
            user = user.scalar_one_or_none()
            if user:
                await get_cache().set_user(user_id, {
                    'user_id': user.user_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_admin': user.is_admin,
                    'is_subscribed': user.is_subscribed,
                    'balance': user.balance,
                    'referral_code': user.referral_code
                }, 600)
                return user.is_admin
        return False
    
    async def _get_user_data(self, user_id: int) -> Optional[Dict]:
        cached = await get_cache().get_user(user_id)
        if cached:
            return cached
        
        async with get_db() as db:
            user = await db.execute(select(User).where(User.user_id == user_id))
            user = user.scalar_one_or_none()
            if user:
                data = {
                    'user_id': user.user_id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'is_admin': user.is_admin,
                    'is_subscribed': user.is_subscribed,
                    'balance': user.balance,
                    'referral_code': user.referral_code,
                    'phone': user.phone,
                    'email': user.email
                }
                await get_cache().set_user(user_id, data, 600)
                return data
        return None
    
    async def _create_user(self, user_id: int, username: str = None, full_name: str = None, ref_code: str = None):
        async with get_db() as db:
            existing = await db.execute(select(User).where(User.user_id == user_id))
            if existing.scalar_one_or_none():
                return
            
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            new_user = User(
                user_id=user_id,
                username=username,
                full_name=full_name or "کاربر",
                referral_code=code
            )
            
            if ref_code:
                referrer = await db.execute(select(User).where(User.referral_code == ref_code))
                referrer = referrer.scalar_one_or_none()
                if referrer and referrer.user_id != user_id:
                    new_user.referred_by = referrer.user_id
                    referrer.referral_count += 1
                    referrer.referral_earnings += 10000
                    referrer.balance += 10000
                    await db.commit()
            
            db.add(new_user)
            await db.commit()
            
            # کش کردن
            await get_cache().set_user(user_id, {
                'user_id': user_id,
                'username': username,
                'full_name': full_name or "کاربر",
                'is_admin': False,
                'is_subscribed': False,
                'balance': 0,
                'referral_code': code
            }, 600)

    # ===================== هندلر start =====================
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        ref = context.args[0] if context.args else None
        
        await self._create_user(user.id, user.username, user.full_name, ref)
        is_admin = await self._is_admin(user.id)
        
        text = f"""
🌟 **به ربات کاریابی حرفه‌ای خوش آمدید!** 🌟

سلام {user.full_name} عزیز! 👋

🚀 **بیش از ۱۰۰۰ آگهی فعال** در ۲۵ دسته‌بندی مختلف

💡 با خرید اشتراک، آگهی شما در بالای نتایج نمایش داده می‌شود!

**لطفاً یکی از گزینه‌های زیر را انتخاب کنید:**
"""
        await update.message.reply_text(text, reply_markup=main_menu(is_admin), parse_mode='Markdown')

    # ===================== هندلر Callback =====================
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        data = query.data
        
        # ===== منوی اصلی =====
        if data == "back_to_main":
            is_admin = await self._is_admin(user_id)
            await query.edit_message_text("🔙 بازگشت به منوی اصلی", reply_markup=main_menu(is_admin))
            return
        
        elif data == "post_employer":
            self.user_steps[user_id] = {'ad_type': 'employer', 'step': 'category'}
            await query.edit_message_text("📝 ثبت آگهی استخدام\n\nدسته‌بندی را انتخاب کنید:", reply_markup=category_menu())
            return
        
        elif data == "post_job_seeker":
            self.user_steps[user_id] = {'ad_type': 'job_seeker', 'step': 'category'}
            await query.edit_message_text("🔍 ثبت آگهی کاریابی\n\nدسته‌بندی را انتخاب کنید:", reply_markup=category_menu())
            return
        
        elif data.startswith("cat_"):
            cat_index = int(data.split("_")[1])
            cat = CATEGORIES[cat_index]
            if user_id not in self.user_steps:
                self.user_steps[user_id] = {}
            self.user_steps[user_id]['category'] = cat
            self.user_steps[user_id]['step'] = 'title'
            await query.edit_message_text(f"📌 دسته: {cat}\n\nعنوان آگهی را وارد کنید:")
            return
        
        # ===== مشاهده آگهی‌ها =====
        elif data == "view_ads":
            context.user_data['ads_page'] = 1
            context.user_data['ads_category'] = None
            await self._show_ads_page(query, context)
            return
        
        elif data.startswith("ads_page_"):
            page = int(data.split("_")[2])
            if page < 1:
                page = 1
            context.user_data['ads_page'] = page
            await self._show_ads_page(query, context)
            return
        
        # ===== آگهی‌های من =====
        elif data == "my_ads":
            context.user_data['my_ads_page'] = 1
            await self._show_my_ads(query, context)
            return
        
        elif data.startswith("myads_page_"):
            page = int(data.split("_")[2])
            if page < 1:
                page = 1
            context.user_data['my_ads_page'] = page
            await self._show_my_ads(query, context)
            return
        
        # ===== اشتراک =====
        elif data == "buy_subscription":
            async with get_db() as db:
                settings = await db.execute(select(PaymentSetting))
                settings = settings.scalar_one_or_none()
            
            if not settings:
                settings = PaymentSetting(card_number="ثبت نشده", price=50000)
            
            text = f"""
💎 **خرید اشتراک ویژه**

💰 **قیمت:** {settings.price:,} تومان

💳 **شماره کارت:** `{settings.card_number}`

🪙 **کیف پول:** `{settings.wallet_address or 'ثبت نشده'}`

✅ پس از واریز، رسید را به پشتیبانی ارسال کنید.
📞 پشتیبانی: @YourSupportBot
"""
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_menu(await self._is_admin(user_id)))
            return
        
        # ===== سیستم معرف =====
        elif data == "referral":
            user_data = await self._get_user_data(user_id)
            if not user_data:
                return
            
            text = f"""
👥 **سیستم معرف**

🆔 **کد شما:** `{user_data['referral_code']}`

📤 **لینک دعوت:**
`https://t.me/YourBotUsername?start={user_data['referral_code']}`

🎁 **پاداش هر دعوت:** ۱۰,۰۰۰ تومان

💰 **اعتبار شما:** {user_data.get('balance', 0):,} تومان
"""
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=main_menu(await self._is_admin(user_id)))
            return
        
        # ===== پشتیبانی =====
        elif data == "support":
            await query.edit_message_text(
                "📞 **پشتیبانی**\n\n@YourSupportBot\n\n⏰ ۹ صبح تا ۹ شب",
                reply_markup=main_menu(await self._is_admin(user_id))
            )
            return
        
        # ===== پنل مدیریت =====
        elif data == "admin_panel":
            if not await self._is_admin(user_id):
                await query.edit_message_text("⛔ دسترسی ندارید.")
                return
            await query.edit_message_text("🔐 **پنل مدیریت**", reply_markup=admin_menu())
            return
        
        elif data == "admin_stats":
            if not await self._is_admin(user_id):
                return
            
            # از کش
            stats = await get_cache().get_stats()
            
            async with get_db() as db:
                total_users = await db.scalar(select(func.count()).select_from(User))
                subscribed = await db.scalar(select(func.count()).select_from(User).where(User.is_subscribed == True))
                total_ads = await db.scalar(select(func.count()).select_from(JobAd).where(JobAd.is_active == True))
                pending = await db.scalar(select(func.count()).select_from(JobAd).where(JobAd.is_approved == False, JobAd.is_active == True))
                
                # درآمد امروز
                today = datetime.datetime.now().date()
                today_revenue = await db.scalar(
                    select(func.sum(Payment.amount))
                    .where(
                        Payment.paid_at >= today,
                        Payment.status == 'paid'
                    )
                )
            
            text = f"""
📊 **آمار پیشرفته**

👥 **کاربران:**
   کل: {total_users:,}
   اشتراک: {subscribed:,}
   جدید امروز: {stats.get('new_users_today', 0):,}

📝 **آگهی‌ها:**
   کل: {total_ads:,}
   در انتظار: {pending:,}

💰 **درآمد:**
   امروز: {today_revenue or 0:,} تومان

📈 **بازدید امروز:** {stats.get('views_today', 0):,}
"""
            await query.edit_message_text(text, parse_mode='Markdown')
            return
        
        elif data == "admin_users":
            if not await self._is_admin(user_id):
                return
            
            async with get_db() as db:
                users = await db.execute(select(User).limit(50).order_by(desc(User.created_at)))
                users = users.scalars().all()
            
            text = "📋 **کاربران اخیر:**\n\n"
            for i, u in enumerate(users[:20], 1):
                status = "👑 ادمین" if u.is_admin else "💎 اشتراک" if u.is_subscribed else "🆓 رایگان"
                text += f"{i}. {u.full_name[:20]} - {status}\n"
            
            await query.edit_message_text(text)
            return
        
        elif data == "admin_broadcast":
            if not await self._is_admin(user_id):
                return
            self.user_steps[user_id] = {'step': 'broadcast'}
            await query.edit_message_text("📢 پیام همگانی را ارسال کنید:\n(متن، عکس، فیلم یا فایل)")
            return
        
        elif data == "admin_set_price":
            if not await self._is_admin(user_id):
                return
            self.user_steps[user_id] = {'step': 'set_price'}
            await query.edit_message_text("💰 قیمت جدید را وارد کنید (مثال: 50000):")
            return
        
        elif data == "admin_set_card":
            if not await self._is_admin(user_id):
                return
            self.user_steps[user_id] = {'step': 'set_card'}
            await query.edit_message_text("💳 شماره کارت جدید را وارد کنید:")
            return
        
        elif data == "admin_set_wallet":
            if not await self._is_admin(user_id):
                return
            self.user_steps[user_id] = {'step': 'set_wallet'}
            await query.edit_message_text("🪙 آدرس کیف پول جدید را وارد کنید:")
            return
        
        elif data == "admin_delete_ad":
            if not await self._is_admin(user_id):
                return
            self.user_steps[user_id] = {'step': 'delete_ad'}
            await query.edit_message_text("🗑 شناسه آگهی را وارد کنید:")
            return
        
        elif data == "admin_approve_ad":
            if not await self._is_admin(user_id):
                return
            self.user_steps[user_id] = {'step': 'approve_ad'}
            await query.edit_message_text("✅ شناسه آگهی را برای تایید وارد کنید:")
            return
        
        elif data == "admin_reports":
            if not await self._is_admin(user_id):
                return
            await query.edit_message_text("📊 **گزارشات در حال توسعه**")
            return
        
        else:
            await query.edit_message_text("❌ گزینه نامعتبر.", reply_markup=main_menu(await self._is_admin(user_id)))
    
    # ===================== نمایش آگهی‌ها با صفحه‌بندی =====================
    async def _show_ads_page(self, query, context):
        page = context.user_data.get('ads_page', 1)
        category = context.user_data.get('ads_category')
        
        # تلاش از کش
        cached = await get_cache().get_ads_page(category, page)
        if cached:
            await self._render_ads_list(query, cached, page, context)
            return
        
        async with get_db() as db:
            query_db = select(JobAd).where(
                JobAd.is_active == True,
                JobAd.is_approved == True
            )
            if category:
                query_db = query_db.where(JobAd.category == category)
            
            # تعداد کل
            count_q = select(func.count()).select_from(query_db.subquery())
            total = await db.scalar(count_q)
            
            query_db = query_db.order_by(desc(JobAd.is_premium), desc(JobAd.created_at))
            query_db = query_db.offset((page - 1) * 20).limit(20)
            result = await db.execute(query_db)
            ads = result.scalars().all()
        
        # ذخیره در کش
        if ads:
            ad_list = [{
                'id': a.id,
                'title': a.title,
                'category': a.category,
                'ad_type': a.ad_type,
                'description': a.short_description or a.description[:100],
                'contact': a.contact,
                'salary_min': a.salary_min,
                'salary_max': a.salary_max,
                'views': a.views,
                'is_premium': a.is_premium
            } for a in ads]
            await get_cache().set_ads_page(ad_list, category, page)
            await self._render_ads_list(query, ad_list, page, context)
        else:
            await query.edit_message_text("❌ هیچ آگهی فعالی یافت نشد.", reply_markup=main_menu(await self._is_admin(query.from_user.id)))
    
    async def _render_ads_list(self, query, ads, page, context):
        if not ads:
            await query.edit_message_text("❌ هیچ آگهی فعالی یافت نشد.")
            return
        
        text = "📋 **آگهی‌های شغلی:**\n\n"
        for ad in ads:
            premium = "⭐ " if ad.get('is_premium') else ""
            text += f"{premium}🔹 *{ad['title']}*\n"
            text += f"   📂 {ad['category']} | {ad['ad_type']}\n"
            text += f"   📝 {ad['description'][:80]}...\n"
            text += f"   📞 {ad['contact']}\n"
            if ad.get('salary_min'):
                text += f"   💰 {ad['salary_min']:,} - {ad['salary_max'] or ''}\n"
            text += f"   👁️ {ad['views']} بازدید\n\n"
        
        # تعداد کل صفحات
        total_ads = await get_cache().get(f"ads_total:{context.user_data.get('ads_category') or 'all'}")
        if not total_ads:
            async with get_db() as db:
                q = select(func.count()).select_from(JobAd).where(
                    JobAd.is_active == True,
                    JobAd.is_approved == True
                )
                if context.user_data.get('ads_category'):
                    q = q.where(JobAd.category == context.user_data['ads_category'])
                total_ads = await db.scalar(q)
                await get_cache().set(f"ads_total:{context.user_data.get('ads_category') or 'all'}", total_ads, 300)
        
        total_pages = (total_ads + 19) // 20 if total_ads else 1
        
        keyboard = []
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"ads_page_{page-1}"))
        nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="ads_current"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"ads_page_{page+1}"))
        keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===================== نمایش آگهی‌های من =====================
    async def _show_my_ads(self, query, context):
        user_id = query.from_user.id
        page = context.user_data.get('my_ads_page', 1)
        
        async with get_db() as db:
            q = select(JobAd).where(JobAd.user_id == user_id)
            total = await db.scalar(select(func.count()).select_from(q.subquery()))
            q = q.order_by(desc(JobAd.created_at)).offset((page - 1) * 20).limit(20)
            result = await db.execute(q)
            ads = result.scalars().all()
        
        if not ads:
            await query.edit_message_text("📭 شما هیچ آگهی ثبت نکرده‌اید.", reply_markup=main_menu(await self._is_admin(user_id)))
            return
        
        text = "👤 **آگهی‌های من:**\n\n"
        for ad in ads:
            status = "✅ فعال" if ad.is_active and ad.is_approved else "⏳ در انتظار" if ad.is_active else "❌ غیرفعال"
            text += f"🔹 *{ad.title}* - {status}\n"
            text += f"   📂 {ad.category} | 👁️ {ad.views}\n\n"
        
        total_pages = (total + 19) // 20 if total else 1
        keyboard = []
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"myads_page_{page-1}"))
        nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="myads_current"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"myads_page_{page+1}"))
        keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ===================== هندلر پیام =====================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        
        if user_id not in self.user_steps:
            await update.message.reply_text("لطفاً از دکمه‌ها استفاده کنید.", reply_markup=main_menu(await self._is_admin(user_id)))
            return
        
        step_data = self.user_steps[user_id]
        step = step_data.get('step')
        
        # ===== ثبت آگهی =====
        if step == 'title':
            if len(text) < 5:
                await update.message.reply_text("❌ عنوان حداقل ۵ حرف باشد.")
                return
            step_data['title'] = text
            step_data['step'] = 'description'
            await update.message.reply_text("✅ عنوان ثبت شد.\n\nتوضیحات را وارد کنید (حداقل ۳۰ کلمه):")
            return
        
        elif step == 'description':
            if len(text.split()) < 30:
                await update.message.reply_text("❌ توضیحات حداقل ۳۰ کلمه باشد.")
                return
            step_data['description'] = text
            step_data['step'] = 'contact'
            await update.message.reply_text("✅ توضیحات ثبت شد.\n\nاطلاعات تماس را وارد کنید:")
            return
        
        elif step == 'contact':
            step_data['contact'] = text
            step_data['step'] = 'salary'
            await update.message.reply_text("✅ تماس ثبت شد.\n\nحقوق پیشنهادی را وارد کنید (یا «ندارد»):")
            return
        
        elif step == 'salary':
            step_data['salary'] = text if text != 'ندارد' else None
            step_data['step'] = 'location'
            await update.message.reply_text("✅ حقوق ثبت شد.\n\nموقعیت مکانی را وارد کنید (یا «ندارد»):")
            return
        
        elif step == 'location':
            location = text if text != 'ندارد' else None
            
            async with get_db() as db:
                ad = JobAd(
                    user_id=user_id,
                    ad_type=step_data.get('ad_type', 'job_seeker'),
                    category=step_data.get('category', 'سایر'),
                    title=step_data.get('title'),
                    description=step_data.get('description'),
                    short_description=step_data.get('description', '')[:500],
                    contact=step_data.get('contact'),
                    salary_min=int(step_data.get('salary', 0)) if step_data.get('salary') and step_data.get('salary').isdigit() else None,
                    location=location
                )
                db.add(ad)
                await db.commit()
                ad_id = ad.id
            
            # پاک کردن کش آگهی‌ها
            await get_cache().invalidate_ads_cache()
            
            del self.user_steps[user_id]
            
            await update.message.reply_text(
                f"✅ **آگهی ثبت شد!** (شناسه: {ad_id})\n\n⏳ پس از تایید ادمین نمایش داده می‌شود.",
                reply_markup=main_menu(await self._is_admin(user_id)),
                parse_mode='Markdown'
            )
            return
        
        # ===== مدیریت ادمین =====
        elif step == 'broadcast':
            if not await self._is_admin(user_id):
                del self.user_steps[user_id]
                return
            
            await update.message.reply_text("🔄 در حال ارسال پیام همگانی...")
            
            async with get_db() as db:
                users = await db.execute(select(User.user_id))
                users = [u[0] for u in users.all()]
            
            success = 0
            total = len(users)
            
            for i, uid in enumerate(users):
                try:
                    if update.message.photo:
                        await context.bot.send_photo(chat_id=uid, photo=update.message.photo[-1].file_id, caption=update.message.caption)
                    elif update.message.document:
                        await context.bot.send_document(chat_id=uid, document=update.message.document.file_id, caption=update.message.caption)
                    elif update.message.video:
                        await context.bot.send_video(chat_id=uid, video=update.message.video.file_id, caption=update.message.caption)
                    else:
                        await context.bot.send_message(chat_id=uid, text=text)
                    success += 1
                except:
                    pass
                
                if i % 10 == 0:
                    await asyncio.sleep(0.1)
            
            await update.message.reply_text(f"✅ پیام به {success} از {total} کاربر ارسال شد.")
            del self.user_steps[user_id]
            return
        
        elif step == 'set_price':
            if not await self._is_admin(user_id):
                del self.user_steps[user_id]
                return
            try:
                price = int(text.replace(',', '').replace(' ', ''))
                async with get_db() as db:
                    settings = await db.execute(select(PaymentSetting))
                    settings = settings.scalar_one_or_none()
                    if settings:
                        settings.price = price
                    else:
                        db.add(PaymentSetting(price=price, card_number="ثبت نشده"))
                    await db.commit()
                await update.message.reply_text(f"✅ قیمت به {price:,} تومان تغییر یافت.")
            except:
                await update.message.reply_text("❌ عدد معتبر وارد کنید.")
            del self.user_steps[user_id]
            return
        
        elif step == 'set_card':
            if not await self._is_admin(user_id):
                del self.user_steps[user_id]
                return
            async with get_db() as db:
                settings = await db.execute(select(PaymentSetting))
                settings = settings.scalar_one_or_none()
                if settings:
                    settings.card_number = text
                else:
                    db.add(PaymentSetting(card_number=text, price=50000))
                await db.commit()
            await update.message.reply_text(f"✅ شماره کارت به `{text}` تغییر یافت.", parse_mode='Markdown')
            del self.user_steps[user_id]
            return
        
        elif step == 'set_wallet':
            if not await self._is_admin(user_id):
                del self.user_steps[user_id]
                return
            async with get_db() as db:
                settings = await db.execute(select(PaymentSetting))
                settings = settings.scalar_one_or_none()
                if settings:
                    settings.wallet_address = text
                else:
                    db.add(PaymentSetting(wallet_address=text, card_number="ثبت نشده", price=50000))
                await db.commit()
            await update.message.reply_text(f"✅ آدرس کیف پول به `{text}` تغییر یافت.", parse_mode='Markdown')
            del self.user_steps[user_id]
            return
        
        elif step == 'delete_ad':
            if not await self._is_admin(user_id):
                del self.user_steps[user_id]
                return
            try:
                ad_id = int(text)
                async with get_db() as db:
                    ad = await db.execute(select(JobAd).where(JobAd.id == ad_id))
                    ad = ad.scalar_one_or_none()
                    if ad:
                        ad.is_active = False
                        await db.commit()
                        await get_cache().invalidate_ads_cache()
                        await update.message.reply_text(f"✅ آگهی {ad_id} حذف شد.")
                    else:
                        await update.message.reply_text("❌ یافت نشد.")
            except:
                await update.message.reply_text("❌ شناسه عددی وارد کنید.")
            del self.user_steps[user_id]
            return
        
        elif step == 'approve_ad':
            if not await self._is_admin(user_id):
                del self.user_steps[user_id]
                return
            try:
                ad_id = int(text)
                async with get_db() as db:
                    ad = await db.execute(select(JobAd).where(JobAd.id == ad_id))
                    ad = ad.scalar_one_or_none()
                    if ad:
                        ad.is_approved = True
                        ad.approved_at = datetime.datetime.now()
                        await db.commit()
                        await get_cache().invalidate_ads_cache()
                        await update.message.reply_text(f"✅ آگهی {ad_id} تایید شد.")
                    else:
                        await update.message.reply_text("❌ یافت نشد.")
            except:
                await update.message.reply_text("❌ شناسه عددی وارد کنید.")
            del self.user_steps[user_id]
            return
        
        else:
            await update.message.reply_text("❌ گزینه نامعتبر.", reply_markup=main_menu(await self._is_admin(user_id)))
            del self.user_steps[user_id]
            return

# ===================== FastAPI پنل مدیریت =====================
app = FastAPI(title="ربات کاریابی - پنل مدیریت", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer()

class AdminLogin(BaseModel):
    username: str
    password: str

class BroadcastRequest(BaseModel):
    message: str
    target: str = "all"

@app.post("/api/admin/login")
async def admin_login(login: AdminLogin):
    if login.username == "admin" and login.password == "admin123":
        token = jwt.encode({
            "user_id": ADMIN_ID,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
        }, SECRET_KEY, algorithm="HS256")
        return {"token": token}
    raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه")

@app.get("/api/admin/stats")
async def get_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    async with get_db() as db:
        total_users = await db.scalar(select(func.count()).select_from(User))
        subscribed = await db.scalar(select(func.count()).select_from(User).where(User.is_subscribed == True))
        total_ads = await db.scalar(select(func.count()).select_from(JobAd).where(JobAd.is_active == True))
        pending = await db.scalar(select(func.count()).select_from(JobAd).where(JobAd.is_approved == False, JobAd.is_active == True))
        
        today = datetime.datetime.now().date()
        today_revenue = await db.scalar(
            select(func.sum(Payment.amount))
            .where(Payment.paid_at >= today, Payment.status == 'paid')
        )
        
        category_stats = await db.execute(
            select(JobAd.category, func.count())
            .where(JobAd.is_active == True, JobAd.is_approved == True)
            .group_by(JobAd.category)
            .order_by(desc(func.count()))
            .limit(10)
        )
    
    return {
        "users": {"total": total_users or 0, "subscribed": subscribed or 0},
        "ads": {"total": total_ads or 0, "pending": pending or 0},
        "payments": {"today_revenue": today_revenue or 0},
        "categories": [{"name": row[0], "count": row[1]} for row in category_stats]
    }

@app.get("/api/admin/users")
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    async with get_db() as db:
        q = select(User).order_by(desc(User.created_at))
        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.offset((page - 1) * limit).limit(limit)
        result = await db.execute(q)
        users = result.scalars().all()
        
        return {
            "users": [{
                "id": u.id,
                "user_id": u.user_id,
                "full_name": u.full_name,
                "username": u.username,
                "phone": u.phone,
                "is_admin": u.is_admin,
                "is_subscribed": u.is_subscribed,
                "balance": u.balance,
                "created_at": u.created_at.isoformat()
            } for u in users],
            "total": total,
            "page": page,
            "limit": limit
        }

@app.get("/api/admin/ads")
async def get_ads(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    pending: bool = Query(False),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    async with get_db() as db:
        q = select(JobAd)
        if pending:
            q = q.where(JobAd.is_approved == False, JobAd.is_active == True)
        q = q.order_by(desc(JobAd.created_at))
        
        total = await db.scalar(select(func.count()).select_from(q.subquery()))
        q = q.offset((page - 1) * limit).limit(limit)
        result = await db.execute(q)
        ads = result.scalars().all()
        
        return {
            "ads": [{
                "id": a.id,
                "user_id": a.user_id,
                "title": a.title,
                "category": a.category,
                "ad_type": a.ad_type,
                "is_active": a.is_active,
                "is_approved": a.is_approved,
                "views": a.views,
                "created_at": a.created_at.isoformat()
            } for a in ads],
            "total": total,
            "page": page,
            "limit": limit
        }

@app.put("/api/admin/ads/{ad_id}/approve")
async def approve_ad(ad_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    async with get_db() as db:
        ad = await db.get(JobAd, ad_id)
        if not ad:
            raise HTTPException(status_code=404, detail="آگهی یافت نشد")
        ad.is_approved = True
        ad.approved_at = datetime.datetime.now()
        await db.commit()
        
        await get_cache().invalidate_ads_cache()
        return {"message": "آگهی تایید شد"}

@app.delete("/api/admin/ads/{ad_id}")
async def delete_ad(ad_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    async with get_db() as db:
        ad = await db.get(JobAd, ad_id)
        if not ad:
            raise HTTPException(status_code=404, detail="آگهی یافت نشد")
        ad.is_active = False
        await db.commit()
        
        await get_cache().invalidate_ads_cache()
        return {"message": "آگهی حذف شد"}

@app.post("/api/admin/broadcast")
async def send_broadcast_api(
    req: BroadcastRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="توکن نامعتبر")
    
    # ارسال در پس‌زمینه
    asyncio.create_task(_send_broadcast_async(req.message))
    return {"message": "پیام همگانی در حال ارسال است"}

async def _send_broadcast_async(message: str):
    # این تابع در پس‌زمینه اجرا می‌شود
    pass

# ===================== صفحه اصلی HTML =====================
@app.get("/", response_class=HTMLResponse)
async def admin_panel():
    return """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پنل مدیریت - ربات کاریابی</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Yekan&display=swap');
        body { font-family: 'Yekan', sans-serif; background: #f5f7fa; }
        .card { transition: all 0.3s ease; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div id="app">
        <!-- هدر -->
        <nav class="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 text-white shadow-lg">
            <div class="container mx-auto flex justify-between items-center">
                <h1 class="text-2xl font-bold">🔐 پنل مدیریت ربات کاریابی</h1>
                <div>
                    <span id="admin_name" class="ml-4">مدیر</span>
                    <button onclick="logout()" class="bg-red-500 hover:bg-red-600 px-4 py-2 rounded-lg transition">🚪 خروج</button>
                </div>
            </div>
        </nav>
        
        <div class="container mx-auto p-4">
            <!-- فرم ورود -->
            <div id="login_form" class="hidden max-w-md mx-auto bg-white p-8 rounded-2xl shadow-xl mt-10">
                <h2 class="text-2xl font-bold mb-6 text-center">🔑 ورود به پنل مدیریت</h2>
                <input id="username" class="w-full p-3 border rounded-lg mb-3 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="نام کاربری">
                <input id="password" type="password" class="w-full p-3 border rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="رمز عبور">
                <button onclick="login()" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white p-3 rounded-lg transition">ورود</button>
            </div>
            
            <!-- داشبورد -->
            <div id="dashboard" class="hidden">
                <!-- کارت‌های آمار -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div class="card bg-white p-6 rounded-2xl shadow">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500">👥 کاربران</p>
                                <p class="text-2xl font-bold" id="total_users">0</p>
                            </div>
                            <div class="bg-blue-100 p-3 rounded-full"><span class="text-blue-600 text-2xl">👥</span></div>
                        </div>
                    </div>
                    <div class="card bg-white p-6 rounded-2xl shadow">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500">📝 آگهی‌ها</p>
                                <p class="text-2xl font-bold" id="total_ads">0</p>
                            </div>
                            <div class="bg-green-100 p-3 rounded-full"><span class="text-green-600 text-2xl">📝</span></div>
                        </div>
                    </div>
                    <div class="card bg-white p-6 rounded-2xl shadow">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500">💰 درآمد امروز</p>
                                <p class="text-2xl font-bold" id="today_revenue">0</p>
                            </div>
                            <div class="bg-yellow-100 p-3 rounded-full"><span class="text-yellow-600 text-2xl">💰</span></div>
                        </div>
                    </div>
                    <div class="card bg-white p-6 rounded-2xl shadow">
                        <div class="flex items-center justify-between">
                            <div>
                                <p class="text-gray-500">⏳ در انتظار تایید</p>
                                <p class="text-2xl font-bold" id="pending_ads">0</p>
                            </div>
                            <div class="bg-red-100 p-3 rounded-full"><span class="text-red-600 text-2xl">⏳</span></div>
                        </div>
                    </div>
                </div>
                
                <!-- تب‌ها -->
                <div class="bg-white rounded-2xl shadow">
                    <div class="border-b p-2">
                        <button class="px-4 py-2 text-indigo-600 border-b-2 border-indigo-600 font-medium" onclick="showTab('users')">👥 کاربران</button>
                        <button class="px-4 py-2 text-gray-500 hover:text-gray-700" onclick="showTab('ads')">📝 آگهی‌ها</button>
                        <button class="px-4 py-2 text-gray-500 hover:text-gray-700" onclick="showTab('pending')">⏳ در انتظار</button>
                        <button class="px-4 py-2 text-gray-500 hover:text-gray-700" onclick="showTab('broadcast')">📢 پیام همگانی</button>
                    </div>
                    <div id="tab_content" class="p-4 min-h-[400px]">
                        <p class="text-gray-500">یک تب را انتخاب کنید...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let token = localStorage.getItem('admin_token');
        
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            try {
                const resp = await fetch('/api/admin/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await resp.json();
                if (data.token) {
                    localStorage.setItem('admin_token', data.token);
                    location.reload();
                } else {
                    alert('نام کاربری یا رمز عبور اشتباه است');
                }
            } catch {
                alert('خطا در ارتباط با سرور');
            }
        }
        
        async function loadStats() {
            if (!token) return;
            try {
                const resp = await fetch('/api/admin/stats', {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                if (resp.status === 401) {
                    localStorage.removeItem('admin_token');
                    location.reload();
                    return;
                }
                const data = await resp.json();
                document.getElementById('total_users').textContent = (data.users.total || 0).toLocaleString();
                document.getElementById('total_ads').textContent = (data.ads.total || 0).toLocaleString();
                document.getElementById('today_revenue').textContent = (data.payments.today_revenue || 0).toLocaleString() + ' تومان';
                document.getElementById('pending_ads').textContent = (data.ads.pending || 0).toLocaleString();
            } catch(e) {
                console.error(e);
            }
        }
        
        async function loadUsers(page = 1) {
            if (!token) return;
            try {
                const resp = await fetch(`/api/admin/users?page=${page}`, {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                const data = await resp.json();
                let html = `<div class="overflow-x-auto"><table class="w-full">
                    <thead><tr class="bg-gray-100"><th class="p-2 text-right">#</th><th class="p-2 text-right">نام</th><th class="p-2 text-right">شناسه</th><th class="p-2 text-right">وضعیت</th><th class="p-2 text-right">تاریخ</th></tr></thead><tbody>`;
                data.users.forEach((u, i) => {
                    const status = u.is_admin ? '👑 ادمین' : u.is_subscribed ? '💎 اشتراک' : '🆓 رایگان';
                    html += `<tr class="border-b"><td class="p-2">${i+1}</td><td class="p-2">${u.full_name || 'نامشخص'}</td><td class="p-2">${u.user_id}</td><td class="p-2">${status}</td><td class="p-2">${new Date(u.created_at).toLocaleDateString('fa-IR')}</td></tr>`;
                });
                html += `</tbody></table></div>
                    <div class="mt-4 flex justify-between items-center">
                        <span>صفحه ${data.page} از ${Math.ceil(data.total / data.limit)}</span>
                        <div>
                            <button onclick="loadUsers(${data.page-1})" class="px-3 py-1 bg-gray-200 rounded" ${data.page<=1?'disabled':''}>قبلی</button>
                            <button onclick="loadUsers(${data.page+1})" class="px-3 py-1 bg-gray-200 rounded" ${data.page>=Math.ceil(data.total/data.limit)?'disabled':''}>بعدی</button>
                        </div>
                    </div>`;
                document.getElementById('tab_content').innerHTML = html;
            } catch(e) {
                document.getElementById('tab_content').innerHTML = '<p class="text-red-500">خطا در بارگذاری</p>';
            }
        }
        
        async function loadAds(page = 1, pending = false) {
            if (!token) return;
            try {
                const resp = await fetch(`/api/admin/ads?page=${page}&pending=${pending}`, {
                    headers: {'Authorization': 'Bearer ' + token}
                });
                const data = await resp.json();
                let html = `<div class="overflow-x-auto"><table class="w-full">
                    <thead><tr class="bg-gray-100"><th class="p-2 text-right">#</th><th class="p-2 text-right">عنوان</th><th class="p-2 text-right">دسته</th><th class="p-2 text-right">نوع</th><th class="p-2 text-right">وضعیت</th><th class="p-2 text-right">عملیات</th></tr></thead><tbody>`;
                data.ads.forEach((a, i) => {
                    const status = a.is_approved ? '✅ تایید شده' : '⏳ در انتظار';
                    html += `<tr class="border-b"><td class="p-2">${i+1}</td><td class="p-2">${a.title}</td><td class="p-2">${a.category}</td><td class="p-2">${a.ad_type}</td><td class="p-2">${status}</td>
                        <td class="p-2">
                            ${!a.is_approved ? `<button onclick="approveAd(${a.id})" class="bg-green-500 text-white px-2 py-1 rounded text-sm">تایید</button>` : ''}
                            <button onclick="deleteAd(${a.id})" class="bg-red-500 text-white px-2 py-1 rounded text-sm">حذف</button>
                        </td></tr>`;
                });
                html += `</tbody></table></div>`;
                document.getElementById('tab_content').innerHTML = html;
            } catch(e) {
                document.getElementById('tab_content').innerHTML = '<p class="text-red-500">خطا در بارگذاری</p>';
            }
        }
        
        async function approveAd(id) {
            if (!confirm('تایید آگهی؟')) return;
            try {
                await fetch(`/api/admin/ads/${id}/approve`, {
                    method: 'PUT',
                    headers: {'Authorization': 'Bearer ' + token}
                });
                alert('آگهی تایید شد');
                loadAds(1, true);
            } catch(e) {
                alert('خطا');
            }
        }
        
        async function deleteAd(id) {
            if (!confirm('حذف آگهی؟')) return;
            try {
                await fetch(`/api/admin/ads/${id}`, {
                    method: 'DELETE',
                    headers: {'Authorization': 'Bearer ' + token}
                });
                alert('آگهی حذف شد');
                loadAds(1);
            } catch(e) {
                alert('خطا');
            }
        }
        
        function showBroadcast() {
            document.getElementById('tab_content').innerHTML = `
                <div class="max-w-2xl">
                    <h3 class="text-lg font-bold mb-4">📢 ارسال پیام همگانی</h3>
                    <textarea id="broadcast_msg" class="w-full p-3 border rounded-lg h-32" placeholder="متن پیام..."></textarea>
                    <div class="mt-4 flex gap-2">
                        <button onclick="sendBroadcast()" class="bg-indigo-600 text-white px-6 py-2 rounded-lg">ارسال</button>
                        <button onclick="sendBroadcast('all')" class="bg-blue-600 text-white px-6 py-2 rounded-lg">ارسال به همه</button>
                    </div>
                    <div id="broadcast_result" class="mt-4"></div>
                </div>
            `;
        }
        
        async function sendBroadcast(target = 'all') {
            const msg = document.getElementById('broadcast_msg').value;
            if (!msg) { alert('پیام را وارد کنید'); return; }
            try {
                const resp = await fetch('/api/admin/broadcast', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({message: msg, target})
                });
                const data = await resp.json();
                document.getElementById('broadcast_result').innerHTML = `<div class="bg-green-100 p-3 rounded">${data.message}</div>`;
            } catch(e) {
                alert('خطا در ارسال');
            }
        }
        
        function showTab(tab) {
            if (tab === 'users') loadUsers();
            else if (tab === 'ads') loadAds(1, false);
            else if (tab === 'pending') loadAds(1, true);
            else if (tab === 'broadcast') showBroadcast();
        }
        
        function logout() {
            localStorage.removeItem('admin_token');
            location.reload();
        }
        
        // بارگذاری اولیه
        if (token) {
            document.getElementById('login_form').classList.add('hidden');
            document.getElementById('dashboard').classList.remove('hidden');
            loadStats();
            showTab('users');
        } else {
            document.getElementById('login_form').classList.remove('hidden');
            document.getElementById('dashboard').classList.add('hidden');
        }
    </script>
</body>
</html>
    """

# ===================== اجرا =====================
async def run_bot():
    await init_db()
    await init_cache()
    
    request = HTTPXRequest(connection_pool_size=200, connect_timeout=30, read_timeout=30)
    application = Application.builder().token(TOKEN).request(request).rate_limiter(AIORateLimiter(max_retries=5)).build()
    
    bot = JobBot()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | filters.VIDEO, bot.handle_message))
    
    logging.info("🤖 ربات راه‌اندازی شد!")
    await application.run_polling()

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # اجرای همزمان ربات + API
    loop = asyncio.get_event_loop()
    
    # اجرای ربات
    bot_task = loop.create_task(run_bot())
    
    # اجرای API در یک ترد جداگانه
    import threading
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    try:
        loop.run_until_complete(bot_task)
    except KeyboardInterrupt:
        print("🛑 ربات متوقف شد")