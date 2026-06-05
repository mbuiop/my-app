#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
💾 m1.py - دیتابیس مرکزی - پشتیبانی از ۱۰ میلیون کاربر
═══════════════════════════════════════════════════════════════════
"""

import os
import asyncio
import asyncpg
import redis
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from loguru import logger
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# ==================== تنظیمات ====================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/mother_bot")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ==================== اتصال به PostgreSQL ====================
engine = create_async_engine(
    DATABASE_URL,
    pool_size=100,           # 100 اتصال همزمان
    max_overflow=50,         # 50 اتصال اضافی
    pool_timeout=30,
    pool_recycle=3600,
    echo=False
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# ==================== اتصال به Redis ====================
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ==================== مدل‌های دیتابیس ====================
class User(Base):
    __tablename__ = "users"
    
    id = sa.Column(sa.BigInteger, primary_key=True)  # پشتیبانی از میلیون‌ها کاربر
    username = sa.Column(sa.String(255), nullable=True)
    first_name = sa.Column(sa.String(255), nullable=False)
    last_name = sa.Column(sa.String(255), nullable=True)
    language = sa.Column(sa.String(10), default="fa")
    
    # اشتراک
    subscription_status = sa.Column(sa.String(20), default="inactive")
    subscription_expiry = sa.Column(sa.DateTime, nullable=True)
    subscription_price_paid = sa.Column(sa.BigInteger, default=0)
    
    # ربات‌ها
    bots_count = sa.Column(sa.Integer, default=0)
    max_bots = sa.Column(sa.Integer, default=2)  # ✅ هر کاربر = 2 ربات
    
    # سیستم رفرال
    referral_code = sa.Column(sa.String(50), unique=True, nullable=False)
    referred_by = sa.Column(sa.BigInteger, nullable=True)
    referrals_count = sa.Column(sa.Integer, default=0)
    verified_referrals = sa.Column(sa.Integer, default=0)
    
    # کیف پول
    wallet_balance = sa.Column(sa.BigInteger, default=0)
    total_commission_earned = sa.Column(sa.BigInteger, default=0)
    
    # آمار
    total_builds = sa.Column(sa.Integer, default=0)
    last_build_at = sa.Column(sa.DateTime, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.now)
    last_active = sa.Column(sa.DateTime, default=datetime.now)
    
    # وضعیت
    is_banned = sa.Column(sa.Boolean, default=False)
    warning_sent = sa.Column(sa.Integer, default=0)

class Bot(Base):
    __tablename__ = "bots"
    
    id = sa.Column(sa.String(50), primary_key=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"))
    token_encrypted = sa.Column(sa.Text, nullable=False)
    name = sa.Column(sa.String(255), nullable=False)
    username = sa.Column(sa.String(255), nullable=False)
    file_path = sa.Column(sa.Text, nullable=True)
    
    # اجرا
    container_id = sa.Column(sa.String(100), nullable=True)  # Docker container ID
    machine_id = sa.Column(sa.Integer, default=1)
    status = sa.Column(sa.String(20), default="stopped")
    
    # مدیریت عضوگیری
    join_enabled = sa.Column(sa.Boolean, default=True)
    join_block_message = sa.Column(sa.Text, default="🚫 Server is full. Please try again later.")
    
    # آمار
    created_at = sa.Column(sa.DateTime, default=datetime.now)
    last_active = sa.Column(sa.DateTime, default=datetime.now)
    restart_count = sa.Column(sa.Integer, default=0)

class Receipt(Base):
    __tablename__ = "receipts"
    
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.id"))
    amount = sa.Column(sa.BigInteger, nullable=False)
    receipt_path = sa.Column(sa.Text, nullable=False)
    payment_code = sa.Column(sa.String(50), unique=True)
    status = sa.Column(sa.String(20), default="pending")
    created_at = sa.Column(sa.DateTime, default=datetime.now)

class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"
    
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.id"))
    amount = sa.Column(sa.BigInteger, nullable=False)
    card_number = sa.Column(sa.String(50), nullable=False)
    card_holder = sa.Column(sa.String(255), nullable=False)
    status = sa.Column(sa.String(20), default="pending")
    created_at = sa.Column(sa.DateTime, default=datetime.now)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    key = sa.Column(sa.String(100), primary_key=True)
    value = sa.Column(sa.Text, nullable=False)
    updated_at = sa.Column(sa.DateTime, default=datetime.now, onupdate=datetime.now)

class Backup(Base):
    __tablename__ = "backups"
    
    id = sa.Column(sa.Integer, primary_key=True)
    filename = sa.Column(sa.String(255), nullable=False)
    size = sa.Column(sa.BigInteger, default=0)
    location = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.now)

# ==================== کلاس دیتابیس اصلی ====================
class Database:
    """دیتابیس قدرتمند با کش هوشمند Redis"""
    
    def __init__(self):
        self.redis = redis_client
        self.cache_ttl = 3600  # 1 ساعت
    
    @asynccontextmanager
    async def get_session(self):
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def init_db(self):
        """ایجاد جداول"""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # تنظیمات پیش‌فرض
        default_settings = {
            'card_number': "5892101187322777",
            'card_number_display': "5892 1011 8732 2777",
            'card_holder': "مرتضی نیکخو خنجری",
            'card_bank': "بانک ملی - سپهر",
            'subscription_price': "2000000",
            'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
            'withdraw_percent': "7",
            'min_withdraw': "2000000",
            'guide_text_fa': "📚 راهنمای استفاده...",
            'guide_text_en': "📚 User Guide...",
            'max_builds_per_hour': "10",
            'maintenance_mode': "false",
            'maintenance_message': "🚫 Server is under maintenance. Please try again later.",
            'language': "fa"
        }
        
        async with self.get_session() as session:
            for key, value in default_settings.items():
                exists = await session.execute(
                    sa.select(SystemSetting).where(SystemSetting.key == key)
                )
                if not exists.scalar_one_or_none():
                    session.add(SystemSetting(key=key, value=value))
    
    # ========== کش ==========
    async def _get_cache(self, key: str):
        """دریافت از کش Redis"""
        data = self.redis.get(f"db:{key}")
        return json.loads(data) if data else None
    
    async def _set_cache(self, key: str, value, ttl: int = None):
        """ذخیره در کش"""
        ttl = ttl or self.cache_ttl
        self.redis.setex(f"db:{key}", ttl, json.dumps(value, default=str))
    
    async def _delete_cache(self, key: str):
        """حذف از کش"""
        self.redis.delete(f"db:{key}")
    
    # ========== کاربران ==========
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """دریافت کاربر با کش"""
        cached = await self._get_cache(f"user:{user_id}")
        if cached:
            return cached
        
        async with self.get_session() as session:
            user = await session.get(User, user_id)
            if user:
                data = {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'language': user.language,
                    'subscription_status': user.subscription_status,
                    'subscription_expiry': user.subscription_expiry.isoformat() if user.subscription_expiry else None,
                    'bots_count': user.bots_count,
                    'max_bots': user.max_bots,
                    'referral_code': user.referral_code,
                    'referred_by': user.referred_by,
                    'referrals_count': user.referrals_count,
                    'verified_referrals': user.verified_referrals,
                    'wallet_balance': user.wallet_balance,
                    'total_commission_earned': user.total_commission_earned,
                    'total_builds': user.total_builds,
                    'is_banned': user.is_banned,
                    'warning_sent': user.warning_sent
                }
                await self._set_cache(f"user:{user_id}", data, ttl=300)
                return data
        return None
    
    async def create_user(self, user_id: int, username: str, first_name: str, last_name: str, referred_by: int = None) -> bool:
        """ایجاد کاربر جدید"""
        async with self.get_session() as session:
            existing = await session.get(User, user_id)
            if existing:
                return True
            
            referral_code = hashlib.md5(f"{user_id}_{secrets.token_hex(8)}".encode()).hexdigest()[:12]
            
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                referral_code=referral_code,
                referred_by=referred_by,
                max_bots=2  # ✅ هر کاربر = 2 ربات
            )
            session.add(user)
            
            # پردازش رفرال
            if referred_by and referred_by != user_id:
                referrer = await session.get(User, referred_by)
                if referrer:
                    referrer.referrals_count += 1
                    
                    # ✅ اضافه شدن کمیسیون به کیف پول
                    subscription_price = int(await self.get_setting('subscription_price'))
                    commission_percent = int(await self.get_setting('withdraw_percent'))
                    commission = int(subscription_price * commission_percent / 100)
                    
                    referrer.wallet_balance += commission
                    referrer.total_commission_earned += commission
                    
                    logger.info(f"Commission {commission} added to user {referred_by} for referral {user_id}")
            
            await self._delete_cache(f"user:{user_id}")
            if referred_by:
                await self._delete_cache(f"user:{referred_by}")
            
            return True
    
    async def update_user(self, user_id: int, **kwargs):
        """به‌روزرسانی کاربر"""
        async with self.get_session() as session:
            user = await session.get(User, user_id)
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
            await self._delete_cache(f"user:{user_id}")
    
    # ========== اشتراک ==========
    async def check_subscription(self, user_id: int) -> bool:
        """بررسی اشتراک کاربر"""
        user = await self.get_user(user_id)
        if not user or user.get('is_banned'):
            return False
        
        if user['subscription_status'] == 'active' and user['subscription_expiry']:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry > datetime.now():
                return True
        
        return False
    
    async def activate_subscription(self, user_id: int, months: int = 1):
        """فعال‌سازی اشتراک - حداکثر 2 ربات"""
        user = await self.get_user(user_id)
        now = datetime.now()
        
        if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
            new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30*months)
        else:
            new_expiry = now + timedelta(days=30*months)
        
        await self.update_user(
            user_id,
            subscription_status='active',
            subscription_expiry=new_expiry,
            warning_sent=0,
            max_bots=2  # ✅ فقط 2 ربات
        )
        
        return new_expiry
    
    # ========== ربات‌ها ==========
    async def get_user_bots(self, user_id: int) -> List[Dict]:
        """دریافت ربات‌های کاربر"""
        async with self.get_session() as session:
            result = await session.execute(
                sa.select(Bot).where(Bot.user_id == user_id).order_by(Bot.created_at.desc())
            )
            bots = result.scalars().all()
            return [{'id': b.id, 'name': b.name, 'username': b.username, 'status': b.status, 'join_enabled': b.join_enabled} for b in bots]
    
    async def add_bot(self, bot_id: str, user_id: int, token_encrypted: str, name: str, username: str, container_id: str = None):
        """افزودن ربات جدید"""
        async with self.get_session() as session:
            bot = Bot(
                id=bot_id,
                user_id=user_id,
                token_encrypted=token_encrypted,
                name=name,
                username=username,
                container_id=container_id,
                status='running'
            )
            session.add(bot)
            
            user = await session.get(User, user_id)
            if user:
                user.bots_count += 1
                user.total_builds += 1
                user.last_build_at = datetime.now()
            
            await self._delete_cache(f"user:{user_id}")
    
    async def delete_bot(self, bot_id: str, user_id: int) -> bool:
        """حذف ربات"""
        async with self.get_session() as session:
            bot = await session.get(Bot, bot_id)
            if bot and bot.user_id == user_id:
                await session.delete(bot)
                
                user = await session.get(User, user_id)
                if user and user.bots_count > 0:
                    user.bots_count -= 1
                
                await self._delete_cache(f"user:{user_id}")
                return True
        return False
    
    async def update_bot_status(self, bot_id: str, status: str):
        """به‌روزرسانی وضعیت ربات"""
        async with self.get_session() as session:
            bot = await session.get(Bot, bot_id)
            if bot:
                bot.status = status
                bot.last_active = datetime.now()
    
    async def update_bot_join_status(self, bot_id: str, join_enabled: bool, block_message: str = None):
        """به‌روزرسانی وضعیت عضوگیری"""
        async with self.get_session() as session:
            bot = await session.get(Bot, bot_id)
            if bot:
                bot.join_enabled = join_enabled
                if block_message:
                    bot.join_block_message = block_message
    
    # ========== فیش و برداشت ==========
    async def add_receipt(self, user_id: int, amount: int, receipt_path: str, payment_code: str):
        """افزودن فیش"""
        async with self.get_session() as session:
            receipt = Receipt(
                user_id=user_id,
                amount=amount,
                receipt_path=receipt_path,
                payment_code=payment_code
            )
            session.add(receipt)
    
    async def approve_receipt(self, receipt_id: int, admin_id: int):
        """تایید فیش و فعال‌سازی اشتراک"""
        async with self.get_session() as session:
            receipt = await session.get(Receipt, receipt_id)
            if receipt and receipt.status == 'pending':
                receipt.status = 'approved'
                await self.activate_subscription(receipt.user_id)
                return receipt.user_id
        return None
    
    # ========== تنظیمات ==========
    async def get_setting(self, key: str) -> str:
        """دریافت تنظیمات"""
        cached = await self._get_cache(f"setting:{key}")
        if cached:
            return cached
        
        async with self.get_session() as session:
            setting = await session.get(SystemSetting, key)
            if setting:
                await self._set_cache(f"setting:{key}", setting.value, ttl=3600)
                return setting.value
        return None
    
    async def set_setting(self, key: str, value: str):
        """تنظیم مقدار"""
        async with self.get_session() as session:
            setting = await session.get(SystemSetting, key)
            if setting:
                setting.value = value
            else:
                session.add(SystemSetting(key=key, value=value))
            await self._delete_cache(f"setting:{key}")
    
    # ========== آماده‌سازی ==========
    async def warmup_cache(self):
        """گرم کردن کش"""
        settings = ['subscription_price', 'withdraw_percent', 'card_number_display', 'card_holder', 'card_bank']
        for key in settings:
            await self.get_setting(key)

# نمونه گلوبال
db = Database()
