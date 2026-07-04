import asyncio
import logging
import sqlite3
import json
import hashlib
import secrets
import aiohttp
import time
import re
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Set, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections import OrderedDict
import random
import zlib
import gc
import psutil
from threading import Lock
import base58

# ==================== تنظیمات سیستم ====================
try:
    import resource
    resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
except:
    pass

# ==================== importهای telegram ====================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ==================== تنظیمات لاگینگ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== تنظیمات اصلی ====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 327855654

# ==================== تنظیمات کیف پول و پرداخت ====================
OWNER_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"  # آدرس کیف پول اصلی ربات
SUBSCRIPTION_PRICE_USD = 10  # قیمت اشتراک ماهانه
TRON_API_URL = "https://api.trongrid.io"
PAYMENT_TIMEOUT_MINUTES = 30

TRON_API_KEYS = [
    "YOUR_TRON_API_KEY_HERE",
]

# ==================== ۲ زبان پشتیبانی شده ====================
SUPPORTED_LANGUAGES = {
    'fa': 'فارسی',
    'en': 'English'
}

# ==================== متون کامل ۲ زبان ====================
TEXTS = {
    'fa': {
        'welcome': "👋 خوش آمدید <b>{first_name}</b>!\n\n🎯 ربات خدمات هوشمند\n📌 دانلود از اینستاگرام، یوتیوب، تیک تاک و خدمات ویژه",
        'download_instagram': "📥 دانلود از اینستاگرام",
        'download_youtube': "📥 دانلود از یوتیوب",
        'download_tiktok': "📥 دانلود از تیک تاک",
        'job_seeker': "👨‍💼 جویای کار",
        'employer': "👔 کارفرما",
        'language': "🌐 زبان",
        'admin_panel': "🛠 پنل مدیریت",
        'download_limit': "⚠️ روزانه فقط ۲ دانلود رایگان دارید!\nبرای دانلود بیشتر اشتراک بخرید.",
        'subscription_required': "❌ برای دانلود بیشتر نیاز به اشتراک دارید.\n💰 اشتراک VIP: ۱۰ دلار در ماه",
        'subscription_active': "✅ اشتراک شما فعال است!\n📅 تاریخ انقضا: {expiry}",
        'buy_subscription': "💳 خرید اشتراک VIP",
        'subscription_price': "💰 قیمت اشتراک: ۱۰ دلار در ماه",
        'payment_info': "💳 لطفا مبلغ <b>{price} دلار</b> USDT (TRC20) را به آدرس زیر ارسال کنید:\n\n<code>{wallet}</code>\n\n📌 پس از واریز، دکمه زیر را بزنید تا تراکنش به صورت خودکار تایید شود.",
        'payment_confirmed': "✅ تایید پرداخت دریافت شد!\n⏳ در حال بررسی بلاکچین... (حداکثر ۳۰ دقیقه)",
        'payment_success': "✅ پرداخت با موفقیت تایید شد!\n🎉 اشتراک شما فعال شد.\n📅 تاریخ انقضا: {expiry}",
        'payment_failed': "❌ تایید پرداخت ناموفق!\nلطفا دوباره تلاش کنید.",
        'payment_timeout': "⏰ زمان تایید پرداخت به پایان رسید\nلطفا دوباره تلاش کنید.",
        'job_list': "📋 **لیست مشاغل موجود:**\n\n{jobs}\n\nلطفاً شماره یا نام شغل مورد نظر را انتخاب کنید.",
        'job_detail': "📌 **{job_title}**\n\n📝 توضیحات: {description}\n💰 حقوق: {salary}\n📞 تماس: {contact}\n📍 آدرس: {address}\n\n✅ برای ارسال درخواست، دکمه زیر را بزنید.",
        'apply_job': "📤 ارسال درخواست",
        'employer_panel': "👔 **پنل کارفرما**\n\n📌 ثبت آگهی استخدام جدید\n📋 لیست آگهی‌های من\n📊 آمار آگهی‌ها",
        'new_job': "📝 ثبت آگهی جدید",
        'job_categories': "📂 **دسته‌بندی مشاغل:**\n\n1️⃣ برنامه‌نویسی و فناوری\n2️⃣ طراحی و گرافیک\n3️⃣ بازاریابی و فروش\n4️⃣ مدیریت و کسب‌وکار\n5️⃣ آموزش و تدریس\n6️⃣ خدمات مشتریان\n7️⃣ پزشکی و سلامت\n8️⃣ مهندسی و ساخت\n9️⃣ رستوران و آشپزی\n🔟 خیاطی و نساجی\n1️⃣1️⃣ آرایشگری و زیبایی\n1️⃣2️⃣ تعمیرات و نگهداری\n1️⃣3️⃣ حمل و نقل\n1️⃣4️⃣ کشاورزی و دامپروری\n1️⃣5️⃣ ساختمان و معماری\n1️⃣6️⃣ حقوق و وکالت\n1️⃣7️⃣ حسابداری و مالی\n1️⃣8️⃣ گردشگری و هتلداری\n1️⃣9️⃣ ورزش و تناسب اندام\n2️⃣0️⃣ هنر و سرگرمی",
        'admin_broadcast': "📢 ارسال پیام همگانی",
        'admin_delete_user': "🗑️ حذف کاربر",
        'admin_paid_mode': "💰 پولی کردن ربات",
        'admin_free_mode': "🆓 رایگان کردن ربات",
        'admin_verify_hash': "✅ تایید هش کاربران",
        'admin_add_api': "🔑 اضافه کردن API ترون",
        'admin_wallet': "💰 تنظیمات کیف پول",
        'admin_stats': "📊 آمار دیتابیس",
        'payment_success': "✅ پرداخت با موفقیت تایید شد!",
        'payment_failed': "❌ تایید پرداخت ناموفق!",
        'wallet_updated': "✅ آدرس کیف پول با موفقیت به‌روزرسانی شد:\n<code>{wallet}</code>",
        'price_updated': "✅ قیمت اشتراک با موفقیت به‌روزرسانی شد:\n💰 {price} دلار",
        'no_active_payments': "❌ هیچ پرداخت فعالی یافت نشد.",
    },
    'en': {
        'welcome': "👋 Welcome <b>{first_name}</b>!\n\n🎯 Smart Services Bot\n📌 Download from Instagram, YouTube, TikTok & Special Services",
        'download_instagram': "📥 Download from Instagram",
        'download_youtube': "📥 Download from YouTube",
        'download_tiktok': "📥 Download from TikTok",
        'job_seeker': "👨‍💼 Job Seeker",
        'employer': "👔 Employer",
        'language': "🌐 Language",
        'admin_panel': "🛠 Admin Panel",
        'download_limit': "⚠️ Only 2 free downloads per day!\nBuy subscription for more.",
        'subscription_required': "❌ Subscription required for more downloads.\n💰 VIP Subscription: $10/month",
        'subscription_active': "✅ Your subscription is active!\n📅 Expiry: {expiry}",
        'buy_subscription': "💳 Buy VIP Subscription",
        'subscription_price': "💰 Subscription Price: $10/month",
        'payment_info': "💳 Please send <b>{price} USDT</b> (TRC20) to this address:\n\n<code>{wallet}</code>\n\n📌 After payment, click the button below for automatic verification.",
        'payment_confirmed': "✅ Payment confirmation received!\n⏳ Checking blockchain... (max 30 minutes)",
        'payment_success': "✅ Payment verified successfully!\n🎉 Your subscription is active.\n📅 Expiry: {expiry}",
        'payment_failed': "❌ Payment verification failed!\nPlease try again.",
        'payment_timeout': "⏰ Payment verification timeout.\nPlease try again.",
        'job_list': "📋 **Available Jobs:**\n\n{jobs}\n\nPlease select job number or name.",
        'job_detail': "📌 **{job_title}**\n\n📝 Description: {description}\n💰 Salary: {salary}\n📞 Contact: {contact}\n📍 Address: {address}\n\n✅ Click below to apply.",
        'apply_job': "📤 Apply Now",
        'employer_panel': "👔 **Employer Panel**\n\n📌 Post New Job\n📋 My Job Listings\n📊 Job Statistics",
        'new_job': "📝 Post New Job",
        'job_categories': "📂 **Job Categories:**\n\n1️⃣ Programming & Tech\n2️⃣ Design & Graphics\n3️⃣ Marketing & Sales\n4️⃣ Management & Business\n5️⃣ Education & Teaching\n6️⃣ Customer Service\n7️⃣ Medical & Health\n8️⃣ Engineering & Manufacturing\n9️⃣ Restaurant & Culinary\n🔟 Tailoring & Textile\n1️⃣1️⃣ Beauty & Hairdressing\n1️⃣2️⃣ Repair & Maintenance\n1️⃣3️⃣ Transportation\n1️⃣4️⃣ Agriculture & Farming\n1️⃣5️⃣ Construction & Architecture\n1️⃣6️⃣ Law & Legal\n1️⃣7️⃣ Accounting & Finance\n1️⃣8️⃣ Tourism & Hospitality\n1️⃣9️⃣ Sports & Fitness\n2️⃣0️⃣ Arts & Entertainment",
        'admin_broadcast': "📢 Broadcast Message",
        'admin_delete_user': "🗑️ Delete User",
        'admin_paid_mode': "💰 Make Paid",
        'admin_free_mode': "🆓 Make Free",
        'admin_verify_hash': "✅ Verify User Hashes",
        'admin_add_api': "🔑 Add Tron API",
        'admin_wallet': "💰 Wallet Settings",
        'admin_stats': "📊 Database Stats",
        'payment_success': "✅ Payment verified successfully!",
        'payment_failed': "❌ Payment verification failed!",
        'wallet_updated': "✅ Wallet address updated successfully:\n<code>{wallet}</code>",
        'price_updated': "✅ Subscription price updated successfully:\n💰 {price} USDT",
        'no_active_payments': "❌ No active payments found.",
    }
}


# ==================== کش فوق‌مقیاس با ۱۰۰۰ شارد ====================
class DistributedUltraCache:
    def __init__(self, max_size=10_000_000, ttl_seconds=600, shard_count=1000):
        self.shard_count = shard_count
        self.shards = [OrderedDict() for _ in range(shard_count)]
        self.shard_locks = [asyncio.Lock() for _ in range(shard_count)]
        self.max_size_per_shard = max_size // shard_count
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        logger.info(f"🚀 کش فوق‌مقیاس با {shard_count} شارد راه‌اندازی شد")
    
    def _get_shard(self, key: str) -> int:
        return zlib.crc32(key.encode()) % self.shard_count
    
    async def get(self, key: str):
        shard_idx = self._get_shard(key)
        async with self.shard_locks[shard_idx]:
            cache = self.shards[shard_idx]
            if key in cache:
                value, timestamp = cache[key]
                if time.time() - timestamp < self.ttl:
                    cache.move_to_end(key)
                    self.hits += 1
                    return value
                else:
                    del cache[key]
                    self.evictions += 1
            self.misses += 1
            return None
    
    async def set(self, key: str, value, ttl: int = None):
        shard_idx = self._get_shard(key)
        async with self.shard_locks[shard_idx]:
            cache = self.shards[shard_idx]
            if key in cache:
                cache.move_to_end(key)
            else:
                if len(cache) >= self.max_size_per_shard:
                    cache.popitem(last=False)
                    self.evictions += 1
            actual_ttl = ttl if ttl else self.ttl
            cache[key] = (value, time.time() + actual_ttl)
    
    async def delete(self, key: str):
        shard_idx = self._get_shard(key)
        async with self.shard_locks[shard_idx]:
            cache = self.shards[shard_idx]
            if key in cache:
                del cache[key]
                return True
            return False
    
    async def get_stats(self) -> Dict:
        total_items = sum(len(shard) for shard in self.shards)
        return {
            'total_items': total_items,
            'shard_count': self.shard_count,
            'max_size': self.shard_count * self.max_size_per_shard,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': (self.hits / max(1, self.hits + self.misses)) * 100,
            'evictions': self.evictions,
            'ttl': self.ttl
        }


# ==================== مدیریت API ترون ====================
class TronAPIManager:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.key_stats = {}
        self.lock = asyncio.Lock()
        self.cache = DistributedUltraCache(max_size=100000, ttl_seconds=300, shard_count=50)
        
        for key in api_keys:
            self.key_stats[key] = {
                'requests': 0,
                'errors': 0,
                'success': 0,
                'active': True,
                'last_used': 0,
                'cooldown_until': 0,
                'consecutive_errors': 0
            }
    
    async def get_best_key(self) -> Tuple[str, Dict]:
        async with self.lock:
            current_time = time.time()
            available_keys = []
            
            for key in self.api_keys:
                stats = self.key_stats[key]
                if not stats['active'] or current_time < stats['cooldown_until']:
                    continue
                available_keys.append((stats['requests'] - stats['success'], key, stats))
            
            if not available_keys:
                return self.api_keys[0], self.key_stats[self.api_keys[0]]
            
            available_keys.sort(key=lambda x: x[0])
            best_key = available_keys[0][1]
            best_stats = available_keys[0][2]
            best_stats['requests'] += 1
            best_stats['last_used'] = current_time
            
            return best_key, best_stats
    
    async def report_success(self, api_key: str):
        async with self.lock:
            if api_key in self.key_stats:
                self.key_stats[api_key]['success'] += 1
                self.key_stats[api_key]['consecutive_errors'] = 0
    
    async def report_error(self, api_key: str):
        async with self.lock:
            if api_key in self.key_stats:
                self.key_stats[api_key]['errors'] += 1
                self.key_stats[api_key]['consecutive_errors'] += 1
                if self.key_stats[api_key]['consecutive_errors'] > 5:
                    self.key_stats[api_key]['cooldown_until'] = time.time() + 120
    
    async def add_api_key(self, new_key: str) -> bool:
        async with self.lock:
            if new_key in self.api_keys:
                return False
            self.api_keys.append(new_key)
            self.key_stats[new_key] = {
                'requests': 0,
                'errors': 0,
                'success': 0,
                'active': True,
                'last_used': 0,
                'cooldown_until': 0,
                'consecutive_errors': 0
            }
            return True
    
    async def remove_api_key(self, api_key: str) -> bool:
        async with self.lock:
            if api_key in self.api_keys:
                self.api_keys.remove(api_key)
                del self.key_stats[api_key]
                return True
            return False
    
    async def toggle_api_key(self, api_key: str) -> bool:
        async with self.lock:
            if api_key in self.key_stats:
                self.key_stats[api_key]['active'] = not self.key_stats[api_key]['active']
                return True
            return False


# ==================== کلاس پرداخت ترون ====================
class TronPaymentProcessor:
    def __init__(self, api_keys: List[str], owner_wallet: str):
        self.api_manager = TronAPIManager(api_keys)
        self.owner_wallet = owner_wallet
        self.base_url = TRON_API_URL
        self.sessions = {}
        self.cache = DistributedUltraCache(max_size=100000, ttl_seconds=300, shard_count=50)
    
    async def get_session(self, api_key: str):
        if api_key not in self.sessions:
            self.sessions[api_key] = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"TRON-PRO-API-KEY": api_key}
            )
        return self.sessions[api_key]
    
    async def verify_transaction(self, tx_hash: str, user_id: int, amount: float) -> bool:
        cache_key = f"tx_{tx_hash}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        for attempt in range(5):
            try:
                api_key, stats = await self.api_manager.get_best_key()
                if not api_key:
                    await asyncio.sleep(2 ** attempt)
                    continue
                
                start_time = time.time()
                session = await self.get_session(api_key)
                url = f"{self.base_url}/v1/transactions/{tx_hash}"
                
                async with session.get(url) as response:
                    if response.status == 429:
                        await self.api_manager.report_error(api_key)
                        await asyncio.sleep(min(2 ** attempt * 5, 60))
                        continue
                    if response.status != 200:
                        await self.api_manager.report_error(api_key)
                        continue
                    
                    data = await response.json()
                    if not data.get('data'):
                        await self.cache.set(cache_key, False, ttl=300)
                        return False
                    
                    tx_data = data['data'][0]
                    contracts = tx_data.get('raw_data', {}).get('contract', [])
                    
                    for contract in contracts:
                        value = contract.get('parameter', {}).get('value', {})
                        to_address = value.get('to_address')
                        
                        if to_address and to_address == self.owner_wallet:
                            tx_amount = value.get('amount', 0) / 1e6
                            if tx_amount >= amount - 1:
                                await self.api_manager.report_success(api_key)
                                await self.cache.set(cache_key, True, ttl=3600)
                                return True
                    
                    await self.cache.set(cache_key, False, ttl=300)
                    return False
                    
            except Exception as e:
                logger.error(f"خطا در بررسی تراکنش (تلاش {attempt+1}): {e}")
                await self.api_manager.report_error(api_key if 'api_key' in locals() else None)
                await asyncio.sleep(2 ** attempt)
        
        await self.cache.set(cache_key, False, ttl=60)
        return False
    
    async def close(self):
        for session in self.sessions.values():
            await session.close()
        self.sessions.clear()


# ==================== دیتابیس فوق‌مقیاس با ۱۰۰۰ شارد ====================
class UltraScalableDatabase:
    def __init__(self, db_path="bot_database.db", shard_count=1000):
        self.db_path = db_path
        self.shard_count = shard_count
        self.cache = DistributedUltraCache(max_size=10_000_000, ttl_seconds=600, shard_count=1000)
        
        self.shard_paths = []
        for i in range(shard_count):
            shard_dir = f"shards_{i // 100}"
            os.makedirs(shard_dir, exist_ok=True)
            shard_path = f"{shard_dir}/db_{i}.db"
            self.shard_paths.append(shard_path)
        
        self._init_all_shards()
        logger.info(f"🗄️ دیتابیس فوق‌مقیاس با {shard_count} شارد راه‌اندازی شد")
    
    def _get_shard(self, user_id: int) -> int:
        return abs(user_id) % self.shard_count
    
    def _get_shard_path(self, shard_idx: int) -> str:
        return self.shard_paths[shard_idx]
    
    def _init_all_shards(self):
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            self._init_shard_tables(shard_path)
    
    def _init_shard_tables(self, shard_path: str):
        with sqlite3.connect(shard_path, timeout=60) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=500000")
            conn.execute("PRAGMA mmap_size=30000000000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA page_size=8192")
            
            cursor = conn.cursor()
            
            # ===== جدول کاربران =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'fa',
                    is_subscribed INTEGER DEFAULT 0,
                    subscription_expiry TEXT,
                    daily_instagram_downloads INTEGER DEFAULT 0,
                    daily_youtube_downloads INTEGER DEFAULT 0,
                    daily_tiktok_downloads INTEGER DEFAULT 0,
                    last_download_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_employer INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    balance REAL DEFAULT 0,
                    wallet_address TEXT,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    total_referrals INTEGER DEFAULT 0,
                    last_active TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== جدول آگهی‌های استخدام =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employer_id INTEGER,
                    category TEXT,
                    title TEXT,
                    description TEXT,
                    salary TEXT,
                    contact TEXT,
                    address TEXT,
                    is_active INTEGER DEFAULT 1,
                    views INTEGER DEFAULT 0,
                    applications INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT
                )
            """)
            
            # ===== جدول درخواست‌های شغلی =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    applicant_id INTEGER,
                    message TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== جدول دانلودها =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    platform TEXT,
                    url TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== جدول تراکنش‌های پرداخت =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    tx_hash TEXT UNIQUE,
                    amount REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    verified_at TEXT,
                    payment_timeout TEXT,
                    is_subscription INTEGER DEFAULT 1
                )
            """)
            
            # ===== جدول سیستم =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== تنظیمات اولیه سیستم =====
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('is_paid', '0')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('download_limit', '2')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('owner_wallet', ?)", (OWNER_WALLET,))
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('subscription_price', '10')")
            
            # ===== ایندکس‌ها برای عملکرد بالا =====
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(is_subscribed, subscription_expiry)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_category ON job_posts(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_active ON job_posts(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_job ON job_applications(job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_user ON job_applications(applicant_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_downloads_user ON downloads(user_id, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active)")
            
            conn.commit()
    
    @asynccontextmanager
    async def get_connection(self, user_id: int = None):
        if user_id is not None:
            shard_idx = self._get_shard(user_id)
            shard_path = self._get_shard_path(shard_idx)
        else:
            shard_path = self._get_shard_path(0)
        
        conn = sqlite3.connect(shard_path, timeout=60, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=500000")
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    # ===== متدهای کاربران =====
    async def get_user(self, user_id: int) -> Optional[Dict]:
        cache_key = f"user_{user_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user = dict(row)
                await self.cache.set(cache_key, user, ttl=600)
                return user
        return None
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None, 
                         last_name: str = None, referred_by: int = None) -> Dict:
        referral_code = secrets.token_urlsafe(8)
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by, last_active)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, username, first_name, last_name, referral_code, referred_by))
            conn.commit()
            
            await self.cache.delete(f"user_{user_id}")
            
            if referred_by:
                await self.cache.delete(f"user_{referred_by}")
        
        return await self.get_user(user_id)
    
    async def update_user_language(self, user_id: int, language: str):
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    async def update_subscription(self, user_id: int, months: int = 1):
        expiry = datetime.now() + timedelta(days=30*months)
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_subscribed = 1, subscription_expiry = ? WHERE user_id = ?", 
                         (expiry.isoformat(), user_id))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    async def check_subscription(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False
        
        if not user.get('is_subscribed'):
            return False
        
        expiry = user.get('subscription_expiry')
        if not expiry:
            return False
        
        try:
            expiry_date = datetime.fromisoformat(expiry)
            if datetime.now() > expiry_date:
                # اشتراک منقضی شده
                async with self.get_connection(user_id) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET is_subscribed = 0 WHERE user_id = ?", (user_id,))
                    conn.commit()
                    await self.cache.delete(f"user_{user_id}")
                return False
            return True
        except:
            return False
    
    async def check_download_limit(self, user_id: int, platform: str) -> bool:
        # اگر کاربر اشتراک دارد
        if await self.check_subscription(user_id):
            return True
        
        today = datetime.now().date().isoformat()
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT daily_{platform}_downloads as count 
                FROM users 
                WHERE user_id = ? AND last_download_date = ?
            """, (user_id, today))
            
            row = cursor.fetchone()
            if row:
                return row['count'] < 2
            return True
    
    async def increment_download_count(self, user_id: int, platform: str):
        today = datetime.now().date().isoformat()
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE users 
                SET daily_{platform}_downloads = daily_{platform}_downloads + 1,
                    last_download_date = ?
                WHERE user_id = ?
            """, (today, user_id))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    # ===== متدهای مشاغل =====
    async def create_job(self, employer_id: int, data: Dict) -> int:
        async with self.get_connection(employer_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO job_posts (employer_id, category, title, description, salary, contact, address, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employer_id,
                data['category'],
                data['title'],
                data['description'],
                data['salary'],
                data['contact'],
                data['address'],
                (datetime.now() + timedelta(days=30)).isoformat()
            ))
            conn.commit()
            return cursor.lastrowid
    
    async def get_jobs(self, category: str = None) -> List[Dict]:
        jobs = []
        
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    if category:
                        cursor.execute("""
                            SELECT j.*, u.first_name, u.username
                            FROM job_posts j
                            JOIN users u ON j.employer_id = u.user_id
                            WHERE j.category = ? AND j.is_active = 1
                            ORDER BY j.created_at DESC
                        """, (category,))
                    else:
                        cursor.execute("""
                            SELECT j.*, u.first_name, u.username
                            FROM job_posts j
                            JOIN users u ON j.employer_id = u.user_id
                            WHERE j.is_active = 1
                            ORDER BY j.created_at DESC
                            LIMIT 50
                        """)
                    
                    jobs.extend([dict(row) for row in cursor.fetchall()])
            except Exception as e:
                logger.error(f"Error getting jobs from shard {shard_idx}: {e}")
        
        return jobs
    
    async def get_user_jobs(self, employer_id: int) -> List[Dict]:
        async with self.get_connection(employer_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM job_posts 
                WHERE employer_id = ? 
                ORDER BY created_at DESC
            """, (employer_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    async def apply_for_job(self, job_id: int, applicant_id: int, message: str) -> bool:
        async with self.get_connection(applicant_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO job_applications (job_id, applicant_id, message)
                VALUES (?, ?, ?)
            """, (job_id, applicant_id, message))
            
            cursor.execute("UPDATE job_posts SET applications = applications + 1 WHERE id = ?", (job_id,))
            conn.commit()
            return True
    
    # ===== متدهای پرداخت =====
    async def add_transaction(self, user_id: int, tx_hash: str, amount: float):
        timeout = (datetime.now() + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)).isoformat()
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (user_id, tx_hash, amount, payment_timeout)
                VALUES (?, ?, ?, ?)
            """, (user_id, tx_hash, amount, timeout))
            conn.commit()
            await self.cache.delete(f"transactions_{user_id}")
    
    async def get_transaction(self, tx_hash: str) -> Optional[Dict]:
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM transactions WHERE tx_hash = ?", (tx_hash,))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
            except:
                pass
        return None
    
    async def get_user_transactions(self, user_id: int) -> List[Dict]:
        cache_key = f"transactions_{user_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 10
            """, (user_id,))
            txs = [dict(row) for row in cursor.fetchall()]
            await self.cache.set(cache_key, txs, ttl=300)
            return txs
    
    async def verify_transaction(self, tx_hash: str) -> bool:
        tx = await self.get_transaction(tx_hash)
        if not tx:
            return False
        
        user_id = tx['user_id']
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE transactions 
                SET status = 'approved', verified_at = CURRENT_TIMESTAMP 
                WHERE tx_hash = ?
            """, (tx_hash,))
            conn.commit()
            
            if tx.get('is_subscription', 1):
                await self.update_subscription(user_id)
            
            await self.cache.delete(f"transactions_{user_id}")
            return True
    
    async def get_pending_transactions(self) -> List[Dict]:
        all_txs = []
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT t.*, u.first_name, u.username
                        FROM transactions t
                        JOIN users u ON t.user_id = u.user_id
                        WHERE t.status = 'pending'
                        ORDER BY t.created_at ASC
                        LIMIT 100
                    """)
                    all_txs.extend([dict(row) for row in cursor.fetchall()])
            except:
                pass
        return all_txs
    
    # ===== متدهای سیستم =====
    async def get_system_setting(self, key: str) -> Optional[str]:
        cache_key = f"system_{key}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            if result:
                value = result['value']
                await self.cache.set(cache_key, value, ttl=3600)
                return value
        return None
    
    async def set_system_setting(self, key: str, value: str):
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", 
                         (key, value))
            conn.commit()
            await self.cache.delete(f"system_{key}")
    
    async def get_owner_wallet(self) -> str:
        wallet = await self.get_system_setting('owner_wallet')
        return wallet or OWNER_WALLET
    
    async def get_subscription_price(self) -> int:
        price = await self.get_system_setting('subscription_price')
        return int(price) if price else SUBSCRIPTION_PRICE_USD
    
    async def is_paid_mode(self) -> bool:
        value = await self.get_system_setting('is_paid')
        return value == '1'
    
    async def get_all_users(self) -> List[int]:
        all_users = []
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM users")
                    all_users.extend([row['user_id'] for row in cursor.fetchall()])
            except:
                pass
        return all_users
    
    async def delete_user(self, user_id: int) -> bool:
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
            await self.cache.delete(f"transactions_{user_id}")
            return cursor.rowcount > 0
    
    async def get_db_stats(self) -> Dict:
        total_users = 0
        total_jobs = 0
        total_downloads = 0
        total_transactions = 0
        
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=5) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) as count FROM users")
                    total_users += cursor.fetchone()['count']
                    cursor.execute("SELECT COUNT(*) as count FROM job_posts")
                    total_jobs += cursor.fetchone()['count']
                    cursor.execute("SELECT COUNT(*) as count FROM downloads")
                    total_downloads += cursor.fetchone()['count']
                    cursor.execute("SELECT COUNT(*) as count FROM transactions")
                    total_transactions += cursor.fetchone()['count']
            except:
                pass
        
        cache_stats = await self.cache.get_stats()
        
        return {
            'shard_count': self.shard_count,
            'total_users': total_users,
            'total_jobs': total_jobs,
            'total_downloads': total_downloads,
            'total_transactions': total_transactions,
            'cache': cache_stats
        }


# ==================== کلاس اصلی ربات ====================
class SmartServiceBot:
    def __init__(self, token: str):
        self.token = token
        self.db = UltraScalableDatabase(shard_count=1000)
        self.tron_payment = TronPaymentProcessor(TRON_API_KEYS, OWNER_WALLET)
        self.user_states = {}
        self.payment_monitor_task = None
        
        # شروع مونیتورینگ پرداخت‌ها
        asyncio.create_task(self._payment_monitor())
        
        logger.info("🚀 ربات خدمات هوشمند با ۱۰۰۰ شارد راه‌اندازی شد")
    
    def get_texts(self, lang: str) -> Dict:
        return TEXTS.get(lang, TEXTS['fa'])
    
    # ===== مونیتورینگ خودکار پرداخت‌ها =====
    async def _payment_monitor(self):
        """بررسی خودکار تراکنش‌های پرداخت هر ۳۰ ثانیه"""
        while True:
            try:
                pending_txs = await self.db.get_pending_transactions()
                
                for tx in pending_txs[:50]:  # حداکثر ۵۰ تراکنش در هر بار
                    # چک کردن زمان اتمام
                    timeout = tx.get('payment_timeout')
                    if timeout:
                        try:
                            timeout_date = datetime.fromisoformat(timeout)
                            if datetime.now() > timeout_date:
                                # زمان به پایان رسیده
                                async with self.db.get_connection(tx['user_id']) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE transactions SET status = 'timeout' WHERE tx_hash = ?", (tx['tx_hash'],))
                                    conn.commit()
                                continue
                        except:
                            pass
                    
                    # بررسی تراکنش در بلاکچین
                    is_valid = await self.tron_payment.verify_transaction(
                        tx['tx_hash'], 
                        tx['user_id'], 
                        tx['amount']
                    )
                    
                    if is_valid:
                        # تایید و فعال‌سازی اشتراک
                        await self.db.verify_transaction(tx['tx_hash'])
                        user = await self.db.get_user(tx['user_id'])
                        if user:
                            lang = user.get('language', 'fa')
                            texts = self.get_texts(lang)
                            expiry = user.get('subscription_expiry', 'نامشخص')
                            try:
                                await self._send_message(
                                    tx['user_id'],
                                    texts['payment_success'].format(expiry=expiry[:10]),
                                    parse_mode=ParseMode.HTML
                                )
                            except:
                                pass
                        
                        logger.info(f"✅ تراکنش {tx['tx_hash']} تایید شد برای کاربر {tx['user_id']}")
                
                await asyncio.sleep(30)  # هر ۳۰ ثانیه
                
            except Exception as e:
                logger.error(f"خطا در مونیتورینگ پرداخت‌ها: {e}")
                await asyncio.sleep(60)
    
    async def _send_message(self, user_id: int, text: str, **kwargs):
        """ارسال پیام با مدیریت خطا"""
        try:
            # این متد باید توسط application.bot استفاده شود
            # در هندلرها از context.bot استفاده می‌شود
            pass
        except Exception as e:
            logger.error(f"خطا در ارسال پیام به {user_id}: {e}")
    
    # ===== هندلر استارت =====
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        db_user = await self.db.get_user(user_id)
        if not db_user:
            referred_by = None
            if context.args:
                ref_code = context.args[0]
                # پیدا کردن کاربر با کد رفرال
                for shard_idx in range(1000):
                    try:
                        shard_path = self.db._get_shard_path(shard_idx)
                        with sqlite3.connect(shard_path, timeout=10) as conn:
                            conn.row_factory = sqlite3.Row
                            cursor = conn.cursor()
                            cursor.execute("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
                            row = cursor.fetchone()
                            if row:
                                referred_by = row['user_id']
                                break
                    except:
                        pass
            
            db_user = await self.db.create_user(
                user_id, user.username, user.first_name, user.last_name, referred_by
            )
        
        lang = db_user.get('language', 'fa')
        texts = self.get_texts(lang)
        
        # بررسی اشتراک
        is_subscribed = await self.db.check_subscription(user_id)
        subscription_text = "✅ اشتراک فعال" if is_subscribed else "❌ بدون اشتراک"
        
        keyboard = [
            [InlineKeyboardButton(texts['download_instagram'], callback_data='download_instagram')],
            [InlineKeyboardButton(texts['download_youtube'], callback_data='download_youtube')],
            [InlineKeyboardButton(texts['download_tiktok'], callback_data='download_tiktok')],
            [InlineKeyboardButton(texts['job_seeker'], callback_data='job_seeker')],
            [InlineKeyboardButton(texts['employer'], callback_data='employer')],
            [InlineKeyboardButton("💳 خرید اشتراک", callback_data='buy_subscription')],
            [InlineKeyboardButton(texts['language'], callback_data='language')]
        ]
        
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data='admin_panel')])
        
        await update.message.reply_text(
            texts['welcome'].format(first_name=user.first_name or 'کاربر') + f"\n\n📊 وضعیت اشتراک: {subscription_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    # ===== هندلر کال‌بک =====
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        db_user = await self.db.get_user(user_id)
        
        if not db_user:
            await query.edit_message_text("⚠️ لطفا مجددا /start را بزنید")
            return
        
        lang = db_user.get('language', 'fa')
        texts = self.get_texts(lang)
        data = query.data
        
        # ===== دانلود از اینستاگرام =====
        if data == 'download_instagram':
            if not await self.db.check_download_limit(user_id, 'instagram'):
                await query.edit_message_text(
                    texts['download_limit'],
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 خرید اشتراک", callback_data='buy_subscription')],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ]),
                    parse_mode=ParseMode.HTML
                )
                return
            
            await query.edit_message_text("📥 لینک ویدیو/عکس اینستاگرام را ارسال کنید:")
            self.user_states[user_id] = 'waiting_instagram_download'
        
        # ===== دانلود از یوتیوب =====
        elif data == 'download_youtube':
            if not await self.db.check_download_limit(user_id, 'youtube'):
                await query.edit_message_text(
                    texts['download_limit'],
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 خرید اشتراک", callback_data='buy_subscription')],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ]),
                    parse_mode=ParseMode.HTML
                )
                return
            
            await query.edit_message_text("📥 لینک ویدیو یوتیوب را ارسال کنید:")
            self.user_states[user_id] = 'waiting_youtube_download'
        
        # ===== دانلود از تیک تاک =====
        elif data == 'download_tiktok':
            if not await self.db.check_download_limit(user_id, 'tiktok'):
                await query.edit_message_text(
                    texts['download_limit'],
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 خرید اشتراک", callback_data='buy_subscription')],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ]),
                    parse_mode=ParseMode.HTML
                )
                return
            
            await query.edit_message_text("📥 لینک ویدیو تیک تاک را ارسال کنید:")
            self.user_states[user_id] = 'waiting_tiktok_download'
        
        # ===== جویای کار =====
        elif data == 'job_seeker':
            keyboard = [
                [InlineKeyboardButton("📋 مشاهده همه آگهی‌ها", callback_data='view_all_jobs')],
                [InlineKeyboardButton("📂 دسته‌بندی مشاغل", callback_data='job_categories')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
            ]
            await query.edit_message_text(
                "👨‍💼 **جویای کار**\n\n"
                "📋 مشاهده آگهی‌های استخدام\n"
                "📂 جستجو بر اساس دسته‌بندی",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        
        # ===== کارفرما =====
        elif data == 'employer':
            keyboard = [
                [InlineKeyboardButton("📝 ثبت آگهی جدید", callback_data='new_job')],
                [InlineKeyboardButton("📋 آگهی‌های من", callback_data='my_jobs')],
                [InlineKeyboardButton("📊 آمار", callback_data='job_stats')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
            ]
            await query.edit_message_text(
                "👔 **پنل کارفرما**\n\n"
                "📝 ثبت آگهی استخدام جدید\n"
                "📋 مشاهده آگهی‌های ثبت شده\n"
                "📊 آمار و عملکرد",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        
        # ===== ثبت آگهی جدید =====
        elif data == 'new_job':
            await query.edit_message_text(
                texts['job_categories'],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='employer')]
                ]),
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'waiting_job_category'
        
        # ===== آگهی‌های من =====
        elif data == 'my_jobs':
            jobs = await self.db.get_user_jobs(user_id)
            
            if not jobs:
                await query.edit_message_text(
                    "❌ شما هیچ آگهی ثبت نکردید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='employer')]
                    ])
                )
                return
            
            text = "📋 **آگهی‌های شما:**\n\n"
            for job in jobs:
                status = "🟢 فعال" if job['is_active'] else "🔴 غیرفعال"
                text += f"📌 {job['title']}\n   💰 {job['salary']}\n   👁️ {job['views']} بازدید\n   📥 {job['applications']} درخواست\n   {status}\n\n"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='employer')]
                ]),
                parse_mode=ParseMode.HTML
            )
        
        # ===== آمار شغلی =====
        elif data == 'job_stats':
            jobs = await self.db.get_user_jobs(user_id)
            
            if not jobs:
                await query.edit_message_text(
                    "❌ شما هیچ آگهی ثبت نکردید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='employer')]
                    ])
                )
                return
            
            total_views = sum(job['views'] for job in jobs)
            total_applications = sum(job['applications'] for job in jobs)
            active_jobs = sum(1 for job in jobs if job['is_active'])
            
            text = f"📊 **آمار آگهی‌های شما:**\n\n"
            text += f"📋 کل آگهی‌ها: {len(jobs)}\n"
            text += f"🟢 آگهی‌های فعال: {active_jobs}\n"
            text += f"👁️ کل بازدیدها: {total_views}\n"
            text += f"📥 کل درخواست‌ها: {total_applications}\n"
            text += f"📈 نرخ تبدیل: {total_applications / max(1, total_views) * 100:.1f}%"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='employer')]
                ]),
                parse_mode=ParseMode.HTML
            )
        
        # ===== دسته‌بندی مشاغل =====
        elif data == 'job_categories':
            keyboard = [
                [InlineKeyboardButton("💻 برنامه‌نویسی", callback_data='job_cat_برنامه‌نویسی')],
                [InlineKeyboardButton("🎨 طراحی", callback_data='job_cat_طراحی')],
                [InlineKeyboardButton("📊 بازاریابی", callback_data='job_cat_بازاریابی')],
                [InlineKeyboardButton("🏢 مدیریت", callback_data='job_cat_مدیریت')],
                [InlineKeyboardButton("📚 آموزش", callback_data='job_cat_آموزش')],
                [InlineKeyboardButton("🏥 پزشکی", callback_data='job_cat_پزشکی')],
                [InlineKeyboardButton("🔧 تعمیرات", callback_data='job_cat_تعمیرات')],
                [InlineKeyboardButton("🍽️ رستوران", callback_data='job_cat_رستوران')],
                [InlineKeyboardButton("🧵 خیاطی", callback_data='job_cat_خیاطی')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='job_seeker')]
            ]
            await query.edit_message_text(
                "📂 **انتخاب دسته‌بندی:**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        
        # ===== مشاهده آگهی‌های یک دسته =====
        elif data.startswith('job_cat_'):
            category = data.replace('job_cat_', '')
            jobs = await self.db.get_jobs(category)
            
            if not jobs:
                await query.edit_message_text(
                    f"❌ هیچ آگهی در دسته '{category}' یافت نشد.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='job_categories')]
                    ])
                )
                return
            
            text = f"📋 **آگهی‌های {category}**\n\n"
            for i, job in enumerate(jobs[:10], 1):
                text += f"{i}. {job['title']}\n   💰 {job['salary']}\n   👤 {job.get('first_name', 'نامشخص')}\n\n"
            
            text += f"\n📊 {len(jobs)} آگهی موجود است."
            
            buttons = []
            for job in jobs[:5]:
                buttons.append([InlineKeyboardButton(f"📌 {job['title']}", callback_data=f"job_detail_{job['id']}")])
            buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data='job_categories')])
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )
        
        # ===== مشاهده همه آگهی‌ها =====
        elif data == 'view_all_jobs':
            jobs = await self.db.get_jobs()
            
            if not jobs:
                await query.edit_message_text(
                    "❌ هیچ آگهی فعالی یافت نشد.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='job_seeker')]
                    ])
                )
                return
            
            text = "📋 **همه آگهی‌های استخدام:**\n\n"
            for i, job in enumerate(jobs[:10], 1):
                text += f"{i}. {job['title']}\n   💰 {job['salary']}\n   📂 {job['category']}\n   👤 {job.get('first_name', 'نامشخص')}\n\n"
            
            text += f"\n📊 {len(jobs)} آگهی موجود است."
            
            buttons = []
            for job in jobs[:5]:
                buttons.append([InlineKeyboardButton(f"📌 {job['title']}", callback_data=f"job_detail_{job['id']}")])
            buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data='job_seeker')])
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )
        
        # ===== جزییات آگهی =====
        elif data.startswith('job_detail_'):
            job_id = int(data.replace('job_detail_', ''))
            
            async with self.db.get_connection(user_id) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT j.*, u.first_name, u.username, u.user_id as employer_id
                    FROM job_posts j
                    JOIN users u ON j.employer_id = u.user_id
                    WHERE j.id = ?
                """, (job_id,))
                job = cursor.fetchone()
            
            if not job:
                await query.edit_message_text("❌ آگهی یافت نشد")
                return
            
            # افزایش بازدید
            async with self.db.get_connection(user_id) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE job_posts SET views = views + 1 WHERE id = ?", (job_id,))
                conn.commit()
            
            text = texts['job_detail'].format(
                job_title=job['title'],
                description=job['description'],
                salary=job['salary'],
                contact=job['contact'],
                address=job['address']
            )
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(texts['apply_job'], callback_data=f"apply_{job_id}")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='job_seeker')]
                ]),
                parse_mode=ParseMode.HTML
            )
        
        # ===== درخواست شغل =====
        elif data.startswith('apply_'):
            job_id = int(data.replace('apply_', ''))
            await query.edit_message_text("📝 پیام خود را برای کارفرما ارسال کنید:")
            self.user_states[user_id] = f'apply_{job_id}'
        
        # ===== خرید اشتراک =====
        elif data == 'buy_subscription':
            wallet = await self.db.get_owner_wallet()
            price = await self.db.get_subscription_price()
            
            await query.edit_message_text(
                texts['payment_info'].format(price=price, wallet=wallet),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ پرداخت کردم", callback_data='confirm_payment')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ]),
                parse_mode=ParseMode.HTML
            )
        
        # ===== تایید پرداخت =====
        elif data == 'confirm_payment':
            await query.edit_message_text(
                "🔑 لطفا هش تراکنش (TX Hash) خود را وارد کنید:",
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'waiting_payment_hash'
        
        # ===== پنل مدیریت =====
        elif data == 'admin_panel' and user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton(texts['admin_broadcast'], callback_data='admin_broadcast')],
                [InlineKeyboardButton(texts['admin_delete_user'], callback_data='admin_delete_user')],
                [InlineKeyboardButton(texts['admin_paid_mode'], callback_data='admin_paid_mode')],
                [InlineKeyboardButton(texts['admin_free_mode'], callback_data='admin_free_mode')],
                [InlineKeyboardButton(texts['admin_verify_hash'], callback_data='admin_verify_hash')],
                [InlineKeyboardButton(texts['admin_add_api'], callback_data='admin_add_api')],
                [InlineKeyboardButton(texts['admin_wallet'], callback_data='admin_wallet')],
                [InlineKeyboardButton(texts['admin_stats'], callback_data='admin_stats')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
            ]
            await query.edit_message_text(
                "🛠 **پنل مدیریت**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        
        # ===== تنظیمات کیف پول =====
        elif data == 'admin_wallet' and user_id == ADMIN_ID:
            current_wallet = await self.db.get_owner_wallet()
            current_price = await self.db.get_subscription_price()
            
            await query.edit_message_text(
                f"💰 **تنظیمات کیف پول و قیمت**\n\n"
                f"📌 آدرس کیف پول فعلی:\n<code>{current_wallet}</code>\n\n"
                f"💰 قیمت اشتراک فعلی: {current_price} دلار\n\n"
                f"📤 برای تغییر آدرس کیف پول، دستور زیر را ارسال کنید:\n"
                f"<code>/setwallet آدرس_جدید</code>\n\n"
                f"📤 برای تغییر قیمت اشتراک:\n"
                f"<code>/setprice عدد_قیمت</code>",
                parse_mode=ParseMode.HTML
            )
        
        # ===== ارسال پیام همگانی =====
        elif data == 'admin_broadcast' and user_id == ADMIN_ID:
            await query.edit_message_text("📢 لطفا پیام خود را ارسال کنید:")
            self.user_states[user_id] = 'waiting_broadcast'
        
        # ===== حذف کاربر =====
        elif data == 'admin_delete_user' and user_id == ADMIN_ID:
            await query.edit_message_text("🗑️ لطفا آیدی کاربر را ارسال کنید:")
            self.user_states[user_id] = 'waiting_delete_user'
        
        # ===== پولی کردن ربات =====
        elif data == 'admin_paid_mode' and user_id == ADMIN_ID:
            await self.db.set_system_setting('is_paid', '1')
            await query.edit_message_text(
                "💰 ربات به حالت پولی تغییر کرد.\nکاربران برای دانلود بیشتر باید اشتراک بخرند.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                ])
            )
        
        # ===== رایگان کردن ربات =====
        elif data == 'admin_free_mode' and user_id == ADMIN_ID:
            await self.db.set_system_setting('is_paid', '0')
            await query.edit_message_text(
                "🆓 ربات به حالت رایگان تغییر کرد.\nهمه کاربران می‌توانند بدون محدودیت دانلود کنند.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                ])
            )
        
        # ===== تایید هش =====
        elif data == 'admin_verify_hash' and user_id == ADMIN_ID:
            pending_txs = await self.db.get_pending_transactions()
            
            if not pending_txs:
                await query.edit_message_text(
                    "✅ هیچ پرداخت در انتظار تاییدی وجود ندارد.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                    ])
                )
                return
            
            text = "📋 **پرداخت‌های در انتظار تایید:**\n\n"
            for tx in pending_txs[:10]:
                text += f"👤 {tx.get('first_name', 'نامشخص')}\n"
                text += f"🆔 {tx['user_id']}\n"
                text += f"💰 {tx['amount']} دلار\n"
                text += f"🔗 <code>{tx['tx_hash'][:20]}...</code>\n"
                text += f"📅 {tx['created_at'][:10]}\n\n"
            
            buttons = []
            for tx in pending_txs[:5]:
                buttons.append([
                    InlineKeyboardButton(
                        f"✅ {tx.get('first_name', 'کاربر')}", 
                        callback_data=f"approve_tx_{tx['tx_hash']}"
                    )
                ])
            buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')])
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML
            )
        
        # ===== تایید تراکنش =====
        elif data.startswith('approve_tx_') and user_id == ADMIN_ID:
            tx_hash = data.replace('approve_tx_', '')
            
            success = await self.db.verify_transaction(tx_hash)
            
            if success:
                await query.edit_message_text(
                    f"✅ تراکنش <code>{tx_hash[:20]}...</code> با موفقیت تایید شد!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_verify_hash')]
                    ]),
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text(
                    f"❌ خطا در تایید تراکنش",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_verify_hash')]
                    ])
                )
        
        # ===== اضافه کردن API =====
        elif data == 'admin_add_api' and user_id == ADMIN_ID:
            await query.edit_message_text(
                "🔑 لطفا کلید API ترون را ارسال کنید:\n\n"
                "📌 کلید باید از سایت TronGrid دریافت شده باشد.",
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'waiting_add_api'
        
        # ===== آمار دیتابیس =====
        elif data == 'admin_stats' and user_id == ADMIN_ID:
            await query.edit_message_text("⏳ در حال دریافت آمار...")
            
            stats = await self.db.get_db_stats()
            
            text = f"📊 **آمار دیتابیس و کش**\n\n"
            text += f"🗄️ **ساختار:**\n"
            text += f"• تعداد شاردها: {stats['shard_count']}\n"
            text += f"• کل کاربران: {stats['total_users']:,}\n"
            text += f"• کل آگهی‌ها: {stats['total_jobs']:,}\n"
            text += f"• کل دانلودها: {stats['total_downloads']:,}\n"
            text += f"• کل تراکنش‌ها: {stats['total_transactions']:,}\n\n"
            text += f"💾 **کش:**\n"
            text += f"• آیتم‌های کش: {stats['cache']['total_items']:,}\n"
            text += f"• نرخ موفقیت: {stats['cache']['hit_rate']:.2f}%"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 بروزرسانی", callback_data='admin_stats')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                ]),
                parse_mode=ParseMode.HTML
            )
        
        # ===== زبان =====
        elif data == 'language':
            keyboard = [
                [InlineKeyboardButton("🇮🇷 فارسی", callback_data='set_lang_fa')],
                [InlineKeyboardButton("🇬🇧 English", callback_data='set_lang_en')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
            ]
            await query.edit_message_text(
                "🌐 انتخاب زبان / Select Language:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data.startswith('set_lang_'):
            new_lang = data.replace('set_lang_', '')
            await self.db.update_user_language(user_id, new_lang)
            
            lang = new_lang
            texts = self.get_texts(lang)
            
            is_subscribed = await self.db.check_subscription(user_id)
            subscription_text = "✅ اشتراک فعال" if is_subscribed else "❌ بدون اشتراک"
            
            keyboard = [
                [InlineKeyboardButton(texts['download_instagram'], callback_data='download_instagram')],
                [InlineKeyboardButton(texts['download_youtube'], callback_data='download_youtube')],
                [InlineKeyboardButton(texts['download_tiktok'], callback_data='download_tiktok')],
                [InlineKeyboardButton(texts['job_seeker'], callback_data='job_seeker')],
                [InlineKeyboardButton(texts['employer'], callback_data='employer')],
                [InlineKeyboardButton("💳 خرید اشتراک", callback_data='buy_subscription')],
                [InlineKeyboardButton(texts['language'], callback_data='language')]
            ]
            
            if user_id == ADMIN_ID:
                keyboard.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data='admin_panel')])
            
            await query.edit_message_text(
                f"✅ زبان به {SUPPORTED_LANGUAGES[new_lang]} تغییر یافت\n\n📊 وضعیت اشتراک: {subscription_text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # ===== بازگشت =====
        elif data == 'back':
            lang = db_user.get('language', 'fa')
            texts = self.get_texts(lang)
            
            is_subscribed = await self.db.check_subscription(user_id)
            subscription_text = "✅ اشتراک فعال" if is_subscribed else "❌ بدون اشتراک"
            
            keyboard = [
                [InlineKeyboardButton(texts['download_instagram'], callback_data='download_instagram')],
                [InlineKeyboardButton(texts['download_youtube'], callback_data='download_youtube')],
                [InlineKeyboardButton(texts['download_tiktok'], callback_data='download_tiktok')],
                [InlineKeyboardButton(texts['job_seeker'], callback_data='job_seeker')],
                [InlineKeyboardButton(texts['employer'], callback_data='employer')],
                [InlineKeyboardButton("💳 خرید اشتراک", callback_data='buy_subscription')],
                [InlineKeyboardButton(texts['language'], callback_data='language')]
            ]
            
            if user_id == ADMIN_ID:
                keyboard.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data='admin_panel')])
            
            await query.edit_message_text(
                texts['welcome'].format(first_name=db_user.get('first_name', 'کاربر')) + f"\n\n📊 وضعیت اشتراک: {subscription_text}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
    
    # ===== هندلر پیام‌ها =====
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        state = self.user_states.get(user_id)
        
        if not text:
            return
        
        # ===== دستورات ادمین =====
        if text.startswith('/setwallet') and user_id == ADMIN_ID:
            parts = text.split(' ', 1)
            if len(parts) < 2:
                await update.message.reply_text("❌ لطفا آدرس کیف پول را وارد کنید:\n<code>/setwallet آدرس_جدید</code>", parse_mode=ParseMode.HTML)
                return
            
            new_wallet = parts[1].strip()
            if len(new_wallet) < 30:
                await update.message.reply_text("❌ آدرس کیف پول نامعتبر است")
                return
            
            await self.db.set_system_setting('owner_wallet', new_wallet)
            await update.message.reply_text(
                f"✅ آدرس کیف پول با موفقیت به‌روزرسانی شد:\n<code>{new_wallet}</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        if text.startswith('/setprice') and user_id == ADMIN_ID:
            parts = text.split(' ', 1)
            if len(parts) < 2:
                await update.message.reply_text("❌ لطفا قیمت را وارد کنید:\n<code>/setprice عدد_قیمت</code>", parse_mode=ParseMode.HTML)
                return
            
            try:
                new_price = int(parts[1].strip())
                if new_price <= 0:
                    raise ValueError
                
                await self.db.set_system_setting('subscription_price', str(new_price))
                await update.message.reply_text(
                    f"✅ قیمت اشتراک با موفقیت به‌روزرسانی شد:\n💰 {new_price} دلار",
                    parse_mode=ParseMode.HTML
                )
            except ValueError:
                await update.message.reply_text("❌ لطفا یک عدد معتبر وارد کنید")
            return
        
        if text.startswith('/') and user_id == ADMIN_ID:
            await update.message.reply_text("❌ دستور نامعتبر است.\nدستورات موجود:\n/setwallet آدرس_جدید\n/setprice عدد_قیمت")
            return
        
        if not state:
            await update.message.reply_text("❌ لطفا ابتدا یک گزینه را انتخاب کنید.\nبرای شروع /start را بزنید.")
            return
        
        # ===== دانلود از اینستاگرام =====
        if state == 'waiting_instagram_download':
            if not text.startswith('http'):
                await update.message.reply_text("❌ لطفا لینک معتبر ارسال کنید")
                return
            
            await update.message.reply_text("⏳ در حال دانلود از اینستاگرام...")
            
            try:
                import yt_dlp
                
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': f'downloads/{user_id}_instagram_%(title)s.%(ext)s',
                    'quiet': True,
                    'no_warnings': True,
                }
                
                os.makedirs('downloads', exist_ok=True)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(text, download=True)
                    filename = ydl.prepare_filename(info)
                
                # ارسال فایل به کاربر
                with open(filename, 'rb') as f:
                    await update.message.reply_video(f, caption="✅ دانلود از اینستاگرام با موفقیت انجام شد!")
                
                # حذف فایل
                os.remove(filename)
                
                # افزایش تعداد دانلود
                await self.db.increment_download_count(user_id, 'instagram')
                
                await update.message.reply_text(
                    "📊 امروز: ۱/۲ دانلود رایگان\n"
                    "💳 برای دانلود بیشتر اشتراک بخرید."
                )
                
            except Exception as e:
                logger.error(f"Instagram download error: {e}")
                await update.message.reply_text(f"❌ خطا در دانلود: {str(e)[:100]}")
            
            self.user_states[user_id] = None
        
        # ===== دانلود از یوتیوب =====
        elif state == 'waiting_youtube_download':
            if not text.startswith('http'):
                await update.message.reply_text("❌ لطفا لینک معتبر ارسال کنید")
                return
            
            await update.message.reply_text("⏳ در حال دانلود از یوتیوب...")
            
            try:
                import yt_dlp
                
                ydl_opts = {
                    'format': 'best[height<=1080]',
                    'outtmpl': f'downloads/{user_id}_youtube_%(title)s.%(ext)s',
                    'quiet': True,
                    'no_warnings': True,
                }
                
                os.makedirs('downloads', exist_ok=True)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(text, download=True)
                    filename = ydl.prepare_filename(info)
                
                with open(filename, 'rb') as f:
                    await update.message.reply_video(f, caption="✅ دانلود از یوتیوب با موفقیت انجام شد!")
                
                os.remove(filename)
                await self.db.increment_download_count(user_id, 'youtube')
                
                await update.message.reply_text(
                    "📊 امروز: ۱/۲ دانلود رایگان\n"
                    "💳 برای دانلود بیشتر اشتراک بخرید."
                )
                
            except Exception as e:
                logger.error(f"YouTube download error: {e}")
                await update.message.reply_text(f"❌ خطا در دانلود: {str(e)[:100]}")
            
            self.user_states[user_id] = None
        
        # ===== دانلود از تیک تاک =====
        elif state == 'waiting_tiktok_download':
            if not text.startswith('http'):
                await update.message.reply_text("❌ لطفا لینک معتبر ارسال کنید")
                return
            
            await update.message.reply_text("⏳ در حال دانلود از تیک تاک...")
            
            try:
                import yt_dlp
                
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': f'downloads/{user_id}_tiktok_%(title)s.%(ext)s',
                    'quiet': True,
                    'no_warnings': True,
                }
                
                os.makedirs('downloads', exist_ok=True)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(text, download=True)
                    filename = ydl.prepare_filename(info)
                
                with open(filename, 'rb') as f:
                    await update.message.reply_video(f, caption="✅ دانلود از تیک تاک با موفقیت انجام شد!")
                
                os.remove(filename)
                await self.db.increment_download_count(user_id, 'tiktok')
                
                await update.message.reply_text(
                    "📊 امروز: ۱/۲ دانلود رایگان\n"
                    "💳 برای دانلود بیشتر اشتراک بخرید."
                )
                
            except Exception as e:
                logger.error(f"TikTok download error: {e}")
                await update.message.reply_text(f"❌ خطا در دانلود: {str(e)[:100]}")
            
            self.user_states[user_id] = None
        
        # ===== ثبت آگهی جدید =====
        elif state == 'waiting_job_category':
            category = text.strip()
            
            # چک کردن اینکه دسته بندی معتبر است
            valid_categories = [
                'برنامه‌نویسی', 'طراحی', 'بازاریابی', 'مدیریت', 'آموزش',
                'پزشکی', 'تعمیرات', 'رستوران', 'خیاطی', 'آرایشگری',
                'حمل و نقل', 'کشاورزی', 'ساختمان', 'حقوق', 'حسابداری',
                'گردشگری', 'ورزش', 'هنر', 'خدمات مشتریان', 'مهندسی'
            ]
            
            if category not in valid_categories:
                await update.message.reply_text(
                    "❌ دسته بندی نامعتبر است.\n"
                    "لطفاً یکی از دسته‌های لیست شده را انتخاب کنید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='new_job')]
                    ])
                )
                return
            
            await update.message.reply_text("📌 عنوان شغل را وارد کنید:")
            self.user_states[user_id] = f'job_title_{category}'
        
        elif state and state.startswith('job_title_'):
            category = state.replace('job_title_', '')
            title = text.strip()
            await update.message.reply_text("📝 توضیحات شغل را وارد کنید:")
            self.user_states[user_id] = f'job_desc_{category}_{title}'
        
        elif state and state.startswith('job_desc_'):
            parts = state.split('_')
            category = parts[2]
            title = parts[3]
            description = text.strip()
            await update.message.reply_text("💰 حقوق/دستمزد را وارد کنید:")
            self.user_states[user_id] = f'job_salary_{category}_{title}_{description}'
        
        elif state and state.startswith('job_salary_'):
            parts = state.split('_')
            category = parts[2]
            title = parts[3]
            description = parts[4]
            salary = text.strip()
            await update.message.reply_text("📞 شماره تماس را وارد کنید:")
            self.user_states[user_id] = f'job_contact_{category}_{title}_{description}_{salary}'
        
        elif state and state.startswith('job_contact_'):
            parts = state.split('_')
            category = parts[2]
            title = parts[3]
            description = parts[4]
            salary = parts[5]
            contact = text.strip()
            await update.message.reply_text("📍 آدرس را وارد کنید:")
            self.user_states[user_id] = f'job_address_{category}_{title}_{description}_{salary}_{contact}'
        
        elif state and state.startswith('job_address_'):
            parts = state.split('_')
            category = parts[2]
            title = parts[3]
            description = parts[4]
            salary = parts[5]
            contact = parts[6]
            address = text.strip()
            
            job_data = {
                'category': category,
                'title': title,
                'description': description,
                'salary': salary,
                'contact': contact,
                'address': address
            }
            
            job_id = await self.db.create_job(user_id, job_data)
            
            await update.message.reply_text(
                f"✅ آگهی با موفقیت ثبت شد!\n\n"
                f"📌 عنوان: {title}\n"
                f"📂 دسته: {category}\n"
                f"💰 حقوق: {salary}\n"
                f"📞 تماس: {contact}\n"
                f"📍 آدرس: {address}\n\n"
                f"🆔 شناسه آگهی: {job_id}\n\n"
                f"📢 آگهی شما به زودی به کاربران نمایش داده می‌شود."
            )
            
            self.user_states[user_id] = None
        
        # ===== درخواست شغل =====
        elif state and state.startswith('apply_'):
            job_id = int(state.replace('apply_', ''))
            message = text.strip()
            
            if len(message) < 10:
                await update.message.reply_text("❌ لطفا پیام خود را با جزئیات بیشتر ارسال کنید (حداقل ۱۰ کاراکتر)")
                return
            
            success = await self.db.apply_for_job(job_id, user_id, message)
            
            if success:
                await update.message.reply_text(
                    "✅ درخواست شما با موفقیت ارسال شد!\n"
                    "📌 کارفرما به زودی با شما تماس می‌گیرد.\n\n"
                    "💡 برای مشاهده آگهی‌های بیشتر، به بخش جویای کار بروید."
                )
            else:
                await update.message.reply_text("❌ خطا در ارسال درخواست")
            
            self.user_states[user_id] = None
        
        # ===== پرداخت اشتراک =====
        elif state == 'waiting_payment_hash':
            tx_hash = text.strip()
            
            if len(tx_hash) != 64:
                await update.message.reply_text("❌ هش نامعتبر است (باید ۶۴ کاراکتر باشد)")
                return
            
            price = await self.db.get_subscription_price()
            
            await self.db.add_transaction(user_id, tx_hash, price)
            
            await update.message.reply_text(
                f"✅ هش شما با موفقیت ثبت شد!\n\n"
                f"🔗 هش: <code>{tx_hash}</code>\n"
                f"💰 مبلغ: {price} دلار\n\n"
                f"⏳ در حال بررسی بلاکچین...\n"
                f"📌 این فرآیند به صورت خودکار انجام می‌شود و حداکثر ۳۰ دقیقه زمان می‌برد.\n\n"
                f"✅ پس از تایید، اشتراک شما فعال می‌شود.",
                parse_mode=ParseMode.HTML
            )
            
            # اطلاع به ادمین
            await context.bot.send_message(
                ADMIN_ID,
                f"🔔 درخواست اشتراک جدید:\n"
                f"👤 {update.effective_user.first_name}\n"
                f"🆔 {user_id}\n"
                f"🔗 هش: <code>{tx_hash}</code>\n"
                f"💰 مبلغ: {price} دلار\n"
                f"📅 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                parse_mode=ParseMode.HTML
            )
            
            self.user_states[user_id] = None
        
        # ===== پیام همگانی (ادمین) =====
        elif state == 'waiting_broadcast' and user_id == ADMIN_ID:
            users = await self.db.get_all_users()
            
            if not users:
                await update.message.reply_text("❌ هیچ کاربری یافت نشد")
                self.user_states[user_id] = None
                return
            
            await update.message.reply_text(f"⏳ ارسال پیام به {len(users)} کاربر...")
            
            success_count = 0
            fail_count = 0
            
            for i, uid in enumerate(users):
                try:
                    await context.bot.send_message(uid, text, parse_mode=ParseMode.HTML)
                    success_count += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    fail_count += 1
                
                if i % 30 == 0 and i > 0:
                    await asyncio.sleep(0.5)
            
            await update.message.reply_text(
                f"✅ پیام با موفقیت ارسال شد!\n"
                f"👤 موفق: {success_count}\n"
                f"❌ ناموفق: {fail_count}"
            )
            
            self.user_states[user_id] = None
        
        # ===== حذف کاربر (ادمین) =====
        elif state == 'waiting_delete_user' and user_id == ADMIN_ID:
            try:
                target_id = int(text.strip())
                user_to_delete = await self.db.get_user(target_id)
                
                if not user_to_delete:
                    await update.message.reply_text(f"❌ کاربر {target_id} یافت نشد")
                    self.user_states[user_id] = None
                    return
                
                success = await self.db.delete_user(target_id)
                
                if success:
                    await update.message.reply_text(
                        f"✅ کاربر {target_id} با موفقیت حذف شد\n"
                        f"👤 نام: {user_to_delete.get('first_name', 'نامشخص')}"
                    )
                else:
                    await update.message.reply_text(f"❌ خطا در حذف کاربر {target_id}")
                    
            except ValueError:
                await update.message.reply_text("❌ لطفا یک آیدی عددی معتبر ارسال کنید")
            
            self.user_states[user_id] = None
        
        # ===== اضافه کردن API (ادمین) =====
        elif state == 'waiting_add_api' and user_id == ADMIN_ID:
            api_key = text.strip()
            
            if len(api_key) < 20:
                await update.message.reply_text("❌ کلید API نامعتبر است")
                self.user_states[user_id] = None
                return
            
            success = await self.tron_payment.api_manager.add_api_key(api_key)
            
            if success:
                await update.message.reply_text(
                    f"✅ کلید API با موفقیت اضافه شد:\n<code>{api_key[:20]}...</code>",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text("❌ این کلید قبلاً اضافه شده است")
            
            self.user_states[user_id] = None
        
        else:
            await update.message.reply_text("❌ دستور نامعتبر است.\nبرای شروع /start را بزنید.")


# ==================== اجرای ربات ====================
async def main():
    bot = SmartServiceBot(BOT_TOKEN)
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    await application.initialize()
    await application.start()
    
    logger.info("✅ ربات با موفقیت راه‌اندازی شد!")
    
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await bot.tron_payment.close()


if __name__ == "__main__":
    asyncio.run(main())