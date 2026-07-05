import asyncio
import logging
import random
import json
import sqlite3
import hashlib
import base58
import aiohttp
import psutil
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, request, jsonify, render_template
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import threading
import time
import os

# --------------------------------------------------------------
# پیکربندی
# --------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "YOUR_BOT_TOKEN"  # توکن ربات خود را قرار دهید
ADMIN_IDS = [123456789]  # ایدی عددی مدیران

# API های ترون برای تایید تراکنش
TRONGRID_APIS = [
    "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
    # API های جدید اضافه می‌شوند
]

# --------------------------------------------------------------
# دیتابیس قوی با 100 شارد
# --------------------------------------------------------------
class ShardedDatabase:
    def __init__(self, num_shards=100):
        self.num_shards = num_shards
        self.connections = {}
        self._init_shards()
        
    def _init_shards(self):
        for i in range(self.num_shards):
            db_path = f"data/shard_{i}.db"
            os.makedirs("data", exist_ok=True)
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connections[i] = conn
            self._create_tables(conn, i)
            
    def _create_tables(self, conn, shard_id):
        cursor = conn.cursor()
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'en',
                wallet_address TEXT,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                has_subscription BOOLEAN DEFAULT 0,
                subscription_end DATE,
                total_participations INTEGER DEFAULT 0,
                wins_count INTEGER DEFAULT 0,
                last_win_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تراکنش‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_id TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول قرعه‌کشی‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lotteries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_prize REAL,
                winners_count INTEGER,
                prize_per_winner REAL,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP,
                ended_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول برندگان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_id INTEGER,
                user_id INTEGER,
                prize_amount REAL,
                wallet_address TEXT,
                paid_status BOOLEAN DEFAULT 0,
                paid_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تنظیمات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول نظرسنجی‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                options TEXT,
                votes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        
    def get_shard(self, user_id):
        return hash(user_id) % self.num_shards
        
    def get_connection(self, user_id):
        shard = self.get_shard(user_id)
        return self.connections[shard]
        
    def execute(self, user_id, query, params=()):
        conn = self.get_connection(user_id)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor
        
    def execute_global(self, query, params=()):
        results = []
        for conn in self.connections.values():
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            results.extend(cursor.fetchall())
        return results

db = ShardedDatabase()

# --------------------------------------------------------------
# سیستم کش قدرتمند
# --------------------------------------------------------------
class CacheManager:
    def __init__(self):
        self.cache = {}
        self.expiry = {}
        self.lock = threading.Lock()
        
    def set(self, key, value, ttl=300):
        with self.lock:
            self.cache[key] = value
            self.expiry[key] = time.time() + ttl
            
    def get(self, key):
        with self.lock:
            if key in self.cache and time.time() < self.expiry[key]:
                return self.cache[key]
            return None
            
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]

cache = CacheManager()

# --------------------------------------------------------------
# سیستم پرداخت با API های متعدد
# --------------------------------------------------------------
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS
        self.current_api_index = 0
        self.api_load = {api: 0 for api in self.apis}
        
    def get_next_api(self):
        # انتخاب API با کمترین بار
        min_load = min(self.api_load.values())
        for api, load in self.api_load.items():
            if load == min_load:
                self.api_load[api] += 1
                return api
        return self.apis[0]
        
    async def verify_transaction(self, from_address, to_address, amount, tx_id=None):
        """بررسی تراکنش با استفاده از API های مختلف"""
        api_key = self.get_next_api()
        
        # جستجوی تراکنش در چندین API برای دقت بالا
        async with aiohttp.ClientSession() as session:
            for api in self.apis:
                try:
                    url = f"https://api.trongrid.io/v1/accounts/{from_address}/transactions"
                    headers = {"TRON-PRO-API-KEY": api}
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            for tx in data.get('data', []):
                                if tx.get('to') == to_address and tx.get('amount', 0) >= amount * 1_000_000:
                                    # تایید با چندین API برای اطمینان بیشتر
                                    if await self._cross_verify(tx.get('txID'), api):
                                        self.api_load[api] -= 1
                                        return True, tx.get('txID')
                except Exception as e:
                    logger.error(f"API error: {e}")
                    
        return False, None
        
    async def _cross_verify(self, tx_id, api_key):
        """بررسی متقابل تراکنش با API های دیگر"""
        verify_count = 0
        async with aiohttp.ClientSession() as session:
            for api in self.apis:
                if api == api_key:
                    continue
                try:
                    url = f"https://api.trongrid.io/v1/transactions/{tx_id}"
                    headers = {"TRON-PRO-API-KEY": api}
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            verify_count += 1
                except:
                    continue
        return verify_count >= 2  # حداقل ۲ API تایید کنند

payment_verifier = PaymentVerifier()

# --------------------------------------------------------------
# سیستم قرعه‌کشی هوشمند با الگوریتم منصفانه
# --------------------------------------------------------------
class LotterySystem:
    def __init__(self):
        self.current_lottery = None
        self.is_running = False
        self.participants = {}
        self.winners_history = []
        self.lock = threading.Lock()
        
    def start_lottery(self, winners_count, prize_per_winner):
        with self.lock:
            if self.is_running:
                return False
                
            # دریافت کاربران دارای اشتراک
            eligible_users = self._get_eligible_users()
            
            # فیلتر کردن برندگان قبلی
            eligible_users = self._filter_previous_winners(eligible_users)
            
            if len(eligible_users) < winners_count:
                return False, "تعداد کاربران واجد شرایط کمتر از تعداد برندگان است"
                
            # الگوریتم پیشرفته انتخاب برندگان
            winners = self._select_winners(eligible_users, winners_count)
            
            self.current_lottery = {
                'winners': winners,
                'prize_per_winner': prize_per_winner,
                'timestamp': datetime.now()
            }
            
            # ثبت برندگان در دیتابیس
            lottery_id = self._save_lottery(winners_count, prize_per_winner)
            self._save_winners(lottery_id, winners, prize_per_winner)
            
            # به‌روزرسانی تاریخ برندگان
            for winner in winners:
                self._update_winner_history(winner)
                
            self.is_running = False
            return True, winners
            
    def _get_eligible_users(self):
        """دریافت کاربران دارای اشتراک فعال"""
        cursor = db.execute_global(
            "SELECT user_id FROM users WHERE has_subscription=1 AND subscription_end > date('now')"
        )
        return [row['user_id'] for row in cursor]
        
    def _filter_previous_winners(self, users):
        """فیلتر برندگان قبلی (تضمین تنوع)"""
        cursor = db.execute_global(
            "SELECT user_id FROM winners WHERE paid_status=1 AND user_id IN ({})".format(','.join(['?']*len(users))),
            users
        )
        previous_winners = [row['user_id'] for row in cursor]
        
        # کاربرانی که در ۳ قرعه‌کشی اخیر برنده شده‌اند را حذف می‌کنیم
        recent_winners = self._get_recent_winners(3)
        
        return [u for u in users if u not in previous_winners and u not in recent_winners]
        
    def _get_recent_winners(self, count):
        """دریافت برندگان قرعه‌کشی‌های اخیر"""
        cursor = db.execute_global(
            "SELECT user_id FROM winners ORDER BY created_at DESC LIMIT ?",
            (count * 10,)  # تعداد بیشتر برای اطمینان
        )
        return list(set([row['user_id'] for row in cursor]))
        
    def _select_winners(self, eligible_users, winners_count):
        """الگوریتم هوشمند انتخاب برندگان با استفاده از AI-like روش"""
        # وزن‌دهی به کاربران بر اساس فعالیت و سابقه
        weighted_users = []
        for user_id in eligible_users:
            weight = self._calculate_user_weight(user_id)
            weighted_users.extend([user_id] * weight)
            
        # انتخاب تصادفی با وزن
        selected_winners = []
        for _ in range(winners_count):
            if not weighted_users:
                break
            winner = random.choice(weighted_users)
            selected_winners.append(winner)
            # حذف برنده انتخاب شده برای عدم انتخاب مجدد
            weighted_users = [u for u in weighted_users if u != winner]
            
        return selected_winners
        
    def _calculate_user_weight(self, user_id):
        """محاسبه وزن کاربر بر اساس فعالیت و سابقه"""
        cursor = db.execute(user_id, 
            "SELECT total_participations, wins_count FROM users WHERE user_id=?",
            (user_id,)
        )
        user_data = cursor.fetchone()
        
        if not user_data:
            return 1
            
        # افزایش شانس برای کاربران فعال اما کمتر برنده شده
        participation_factor = min(user_data['total_participations'] / 10, 5)
        win_penalty = max(1, 10 - user_data['wins_count'] * 2)
        
        return max(1, int(participation_factor + win_penalty))
        
    def _save_lottery(self, winners_count, prize_per_winner):
        cursor = db.execute(0,  # استفاده از شارد ۰ برای داده‌های عمومی
            "INSERT INTO lotteries (winners_count, prize_per_winner, status, started_at) VALUES (?, ?, 'running', CURRENT_TIMESTAMP)",
            (winners_count, prize_per_winner)
        )
        return cursor.lastrowid
        
    def _save_winners(self, lottery_id, winners, prize_amount):
        for user_id in winners:
            cursor = db.execute(user_id,
                "INSERT INTO winners (lottery_id, user_id, prize_amount, paid_status) VALUES (?, ?, ?, 0)",
                (lottery_id, user_id, prize_amount)
            )
            
    def _update_winner_history(self, user_id):
        cursor = db.execute(user_id,
            "UPDATE users SET wins_count = wins_count + 1, last_win_date = CURRENT_TIMESTAMP WHERE user_id=?",
            (user_id,)
        )

lottery_system = LotterySystem()

# --------------------------------------------------------------
# سیستم مدیریت API ها
# --------------------------------------------------------------
class APIManager:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.api_usage = {api: {'requests': 0, 'success': 0, 'last_reset': time.time()} for api in self.apis}
        
    def add_api(self, api_key):
        if api_key not in self.apis:
            self.apis.append(api_key)
            self.api_usage[api_key] = {'requests': 0, 'success': 0, 'last_reset': time.time()}
            # به‌روزرسانی payment_verifier
            payment_verifier.apis.append(api_key)
            payment_verifier.api_load[api_key] = 0
            return True
        return False
        
    def get_best_api(self):
        """دریافت بهترین API بر اساس کارایی"""
        self._reset_usage_if_needed()
        
        best_api = None
        best_score = -1
        
        for api, usage in self.api_usage.items():
            if usage['requests'] == 0:
                score = 100
            else:
                success_rate = usage['success'] / usage['requests']
                score = success_rate * 100
                
            if score > best_score:
                best_score = score
                best_api = api
                
        return best_api or self.apis[0]
        
    def _reset_usage_if_needed(self):
        """بازنشانی آمار استفاده هر ساعت"""
        for api, usage in self.api_usage.items():
            if time.time() - usage['last_reset'] > 3600:
                usage['requests'] = 0
                usage['success'] = 0
                usage['last_reset'] = time.time()

api_manager = APIManager()

# --------------------------------------------------------------
# ربات تلگرام
# --------------------------------------------------------------
class LotteryBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()
        
    def _setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        app = self.application
        
        # دستورات عمومی
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        
        # دکمه‌های صفحه اصلی
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language$"))
        app.add_handler(CallbackQueryHandler(self.join_lottery_callback, pattern="^join_lottery$"))
        
        # مدیریت پیام‌ها
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # پنل مدیریت
        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_start_lottery_callback, pattern="^admin_start_lottery$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_poll_callback, pattern="^admin_poll$"))
        app.add_handler(CallbackQueryHandler(self.admin_pay_winners_callback, pattern="^admin_pay_winners$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api_callback, pattern="^admin_add_api$"))
        
        # شروع قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.start_lottery_confirm_callback, pattern="^start_lottery_confirm$"))
        app.add_handler(CallbackQueryHandler(self.start_lottery_final_callback, pattern="^start_lottery_final$"))
        
        # برداشت جایزه
        app.add_handler(CallbackQueryHandler(self.withdraw_prize_callback, pattern="^withdraw_prize$"))
        app.add_handler(CallbackQueryHandler(self.confirm_withdraw_callback, pattern="^confirm_withdraw$"))
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور استارت - نمایش دکمه پلی"""
        user = update.effective_user
        
        # ثبت کاربر در دیتابیس
        self._register_user(user)
        
        # زبان پیش‌فرض انگلیسی
        lang = self._get_user_language(user.id)
        
        # دکمه پلی
        keyboard = [[InlineKeyboardButton("▶️ PLAY", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 Welcome to UTYOB Lottery Bot!\n\n"
            "Click PLAY to enter the game and win amazing prizes!",
            reply_markup=reply_markup
        )
        
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی اصلی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🎰 شرکت در قرعه‌کشی", callback_data="lottery")],
            [InlineKeyboardButton("🔗 رفرال", callback_data="referral")],
            [InlineKeyboardButton("📖 راهنمایی", callback_data="guide")],
            [InlineKeyboardButton("🌐 تغییر زبان", callback_data="language")]
        ]
        
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 **Welcome to UTYOB Lottery Bot!**\n\n"
            "Select an option below:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    async def lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # بررسی اشتراک کاربر
        has_subscription = self._check_subscription(user_id)
        
        if not has_subscription:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ شما اشتراک فعال ندارید!\n\n"
                "برای شرکت در قرعه‌کشی، ابتدا اشتراک تهیه کنید.",
                reply_markup=reply_markup
            )
            return
            
        # نمایش دکمه شرکت در قرعه‌کشی
        keyboard = [
            [InlineKeyboardButton("✅ شرکت در قرعه‌کشی", callback_data="join_lottery")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎰 **قرعه‌کشی UTYOB**\n\n"
            "برای شرکت در قرعه‌کشی، روی دکمه زیر کلیک کنید.\n\n"
            "💰 جایزه: تا ۱۰۰۰ دلار\n"
            "📊 تعداد برندگان: متغیر",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    async def join_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شرکت در قرعه‌کشی - دریافت آدرس کیف پول"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # ذخیره وضعیت برای دریافت آدرس
        context.user_data['waiting_for_wallet'] = True
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💳 **واریز برای شرکت در قرعه‌کشی**\n\n"
            "لطفاً آدرس کیف پول مبدا (TRC20) خود را وارد کنید:\n\n"
            "مبلغ واریز: **۱۰۰ دلار**\n"
            "آدرس مقصد: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`\n\n"
            "⚠️ پس از واریز، سیستم به صورت خودکار تراکنش را تایید می‌کند.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت پیام‌های کاربران"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # بررسی انتظار برای آدرس کیف پول
        if context.user_data.get('waiting_for_wallet'):
            # ذخیره آدرس کیف پول
            wallet_address = text.strip()
            
            # بررسی معتبر بودن آدرس
            if self._validate_wallet_address(wallet_address):
                # ثبت در دیتابیس
                cursor = db.execute(user_id,
                    "UPDATE users SET wallet_address = ? WHERE user_id = ?",
                    (wallet_address, user_id)
                )
                
                # تایید خودکار پرداخت
                await self._auto_verify_payment(user_id, wallet_address)
                
                context.user_data['waiting_for_wallet'] = False
            else:
                await update.message.reply_text(
                    "❌ آدرس کیف پول نامعتبر است!\n"
                    "لطفاً یک آدرس معتبر TRC20 وارد کنید."
                )
            return
            
        # پیام‌های معمولی
        await update.message.reply_text(
            "از دستورات موجود استفاده کنید یا از دکمه‌ها استفاده نمایید."
        )
        
    async def _auto_verify_payment(self, user_id, from_address):
        """تایید خودکار پرداخت"""
        to_address = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
        amount = 100  # دلار
        
        # تایید تراکنش
        is_verified, tx_id = await payment_verifier.verify_transaction(
            from_address, to_address, amount
        )
        
        if is_verified:
            # ثبت تراکنش موفق
            cursor = db.execute(user_id,
                """INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
                   VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)""",
                (user_id, from_address, to_address, amount, tx_id)
            )
            
            # به‌روزرسانی کاربر
            cursor = db.execute(user_id,
                "UPDATE users SET total_participations = total_participations + 1 WHERE user_id = ?",
                (user_id,)
            )
            
            keyboard = [[InlineKeyboardButton("🎰 ورود به قرعه‌کشی", callback_data="lottery")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.application.bot.send_message(
                chat_id=user_id,
                text="✅ **پرداخت شما تایید شد!**\n\n"
                     "شما با موفقیت در قرعه‌کشی ثبت نام کردید.\n"
                     "برای مشاهده وضعیت قرعه‌کشی، روی دکمه زیر کلیک کنید.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # پیام به ادمین
            for admin_id in ADMIN_IDS:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=f"✅ پرداخت جدید تایید شد\n"
                         f"👤 کاربر: {user_id}\n"
                         f"💰 مبلغ: ${amount}\n"
                         f"🔗 تراکنش: {tx_id}"
                )
                
        else:
            # پرداخت تایید نشد
            cursor = db.execute(user_id,
                "INSERT INTO transactions (user_id, from_address, to_address, amount, status) VALUES (?, ?, ?, ?, 'failed')",
                (user_id, from_address, to_address, amount)
            )
            
            keyboard = [[InlineKeyboardButton("🔄 تلاش مجدد", callback_data="join_lottery")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.application.bot.send_message(
                chat_id=user_id,
                text="❌ **پرداخت شما تایید نشد!**\n\n"
                     "لطفاً موارد زیر را بررسی کنید:\n"
                     "1. مبلغ دقیقاً ۱۰۰ دلار باشد\n"
                     "2. آدرس مقصد صحیح باشد\n"
                     "3. تراکنش انجام شده باشد\n\n"
                     "پس از بررسی، مجدداً اقدام کنید.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # اطلاع به ادمین برای بررسی دستی
            for admin_id in ADMIN_IDS:
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ پرداخت تایید نشد - نیاز به بررسی دستی\n"
                         f"👤 کاربر: {user_id}\n"
                         f"📤 از: {from_address}\n"
                         f"📥 به: {to_address}\n"
                         f"💰 مبلغ: ${amount}"
                )
                
    def _validate_wallet_address(self, address):
        """بررسی معتبر بودن آدرس TRC20"""
        try:
            # بررسی طول آدرس
            if len(address) != 34:
                return False
                
            # بررسی کاراکترهای مجاز
            valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
            if not all(c in valid_chars for c in address):
                return False
                
            # بررسی Base58
            try:
                decoded = base58.b58decode(address)
                return True
            except:
                return False
                
        except:
            return False
            
    def _register_user(self, user):
        """ثبت کاربر جدید در دیتابیس"""
        cursor = db.execute(user.id,
            "SELECT user_id FROM users WHERE user_id = ?",
            (user.id,)
        )
        
        if not cursor.fetchone():
            # تولید کد رفرال اختصاصی
            referral_code = self._generate_referral_code(user.id)
            
            cursor = db.execute(user.id,
                """INSERT INTO users (user_id, username, first_name, last_name, referral_code) 
                   VALUES (?, ?, ?, ?, ?)""",
                (user.id, user.username, user.first_name, user.last_name, referral_code)
            )
            
    def _generate_referral_code(self, user_id):
        """تولید کد رفرال منحصر به فرد"""
        import hashlib
        base = f"UTYOB_{user_id}_{time.time()}"
        hash_obj = hashlib.sha256(base.encode())
        return hash_obj.hexdigest()[:10].upper()
        
    def _get_user_language(self, user_id):
        """دریافت زبان کاربر"""
        cursor = db.execute(user_id,
            "SELECT language FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        return result['language'] if result else 'en'
        
    def _check_subscription(self, user_id):
        """بررسی اشتراک کاربر"""
        cursor = db.execute(user_id,
            "SELECT has_subscription, subscription_end FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return False
            
        if result['has_subscription']:
            if result['subscription_end']:
                end_date = datetime.strptime(result['subscription_end'], '%Y-%m-%d')
                if end_date >= datetime.now():
                    return True
                    
        return False

# --------------------------------------------------------------
# پنل مدیریت
# --------------------------------------------------------------
class AdminPanel:
    def __init__(self, bot):
        self.bot = bot
        
    async def show_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل مدیریت"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton("✅ تایید دستی کاربران", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📊 ارسال نظرسنجی", callback_data="admin_poll")],
            [InlineKeyboardButton("💰 واریز به برندگان", callback_data="admin_pay_winners")],
            [InlineKeyboardButton("🔑 اضافه کردن API جدید", callback_data="admin_add_api")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ **پنل مدیریت**\n\n"
            "انتخاب کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    async def broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال پیام همگانی"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'broadcast'
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📢 **ارسال پیام همگانی**\n\n"
            "لطفاً متن پیام را ارسال کنید:\n"
            "⚠️ این پیام به تمام کاربران ارسال خواهد شد.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    async def start_lottery(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['admin_action'] = 'start_lottery'
        context.user_data['lottery_step'] = 1
        
        keyboard = [
            [InlineKeyboardButton("✅ تایید شروع", callback_data="start_lottery_confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎰 **شروع قرعه‌کشی جدید**\n\n"
            "آیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟\n\n"
            "⚠️ تمام کاربران دارای اشتراک در این قرعه‌کشی شرکت خواهند کرد.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    async def start_lottery_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید شروع قرعه‌کشی - دریافت تعداد برندگان"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['lottery_step'] = 2
        
        await query.edit_message_text(
            "🎯 **تعداد برندگان**\n\n"
            "لطفاً تعداد برندگان این قرعه‌کشی را وارد کنید:\n"
            "(عدد بین ۱ تا ۱۰۰)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]
            ]),
            parse_mode='Markdown'
        )
        
    async def start_lottery_final(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مرحله نهایی شروع قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        # دریافت اطلاعات از context
        winners_count = context.user_data.get('lottery_winners', 1)
        prize_per_winner = context.user_data.get('lottery_prize', 100)
        
        # اجرای قرعه‌کشی
        success, result = lottery_system.start_lottery(winners_count, prize_per_winner)
        
        if success:
            # ارسال پیام به برندگان
            for user_id in result:
                keyboard = [[InlineKeyboardButton("💰 برداشت جایزه", callback_data="withdraw_prize")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.bot.application.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 **تبریک! شما برنده شدید!**\n\n"
                         f"💰 مبلغ جایزه: ${prize_per_winner:,}\n\n"
                         f"برای برداشت جایزه، روی دکمه زیر کلیک کنید.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
            # گزارش به ادمین
            await query.edit_message_text(
                f"✅ **قرعه‌کشی با موفقیت انجام شد!**\n\n"
                f"👥 تعداد برندگان: {winners_count}\n"
                f"💰 جایزه هر نفر: ${prize_per_winner:,}\n"
                f"🆔 برندگان: {', '.join(map(str, result))}\n\n"
                f"✅ پیام‌های تبریک به برندگان ارسال شد.",
                parse_mode='Markdown'
            )
            
        else:
            await query.edit_message_text(
                f"❌ **خطا در اجرای قرعه‌کشی**\n\n"
                f"{result}",
                parse_mode='Markdown'
            )

# --------------------------------------------------------------
# شروع ربات
# --------------------------------------------------------------
async def main():
    bot = LotteryBot()
    admin_panel = AdminPanel(bot)
    
    # اضافه کردن هندلرهای پنل مدیریت
    # (ادامه در کد کامل)
    
    # شروع ربات
    await bot.application.run_polling()
    
if __name__ == '__main__':
    asyncio.run(main())