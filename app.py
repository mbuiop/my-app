#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════
🚀 ربات مادر حرفه‌ای - نسخه 5.0 Enterprise
⚡ پشتیبانی از ۲,۰۰۰+ کاربر | سیستم رفرال | کمیسیون ۱۰٪
═══════════════════════════════════════════════════════════════════
"""

import asyncio
import sqlite3
import hashlib
import json
import re
import os
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
import aiohttp
from aiohttp import ClientSession
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery, Message, FSInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== تنظیمات ====================
class Config:
    BOT_TOKEN = "8541672444:AAF4PBn7-XqiXUgaK0arVajyZfcMWqbxSJ0"
    ADMIN_IDS = [327855654]
    BOT_USERNAME = "YourBotUsername"  # بدون @ بذار
    
    # مالی
    PRICE = 2_000_000  # تومان
    COMMISSION_PERCENT = 10  # ۱۰ درصد کمیسیون
    MIN_WITHDRAW = 500_000  # حداقل برداشت ۵۰۰ هزار تومان
    
    # کارت بانکی
    CARD_NUMBER = "5892101187322777"
    CARD_HOLDER = "مرتضی نیکخو خنجری"
    BANK_NAME = "بانک ملی"
    
    # محدودیت‌ها
    MAX_BOTS_PER_USER = 10
    MAX_CONCURRENT_BUILDS = 50
    
    # فایل‌ها
    DATABASE_FILE = "motherbot_advanced.db"

config = Config()

# ==================== دیتابیس پیشرفته ====================
class Database:
    def __init__(self):
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        self.conn = sqlite3.connect(config.DATABASE_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                referral_code TEXT UNIQUE NOT NULL,
                referred_by INTEGER,
                balance INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                total_withdrawn INTEGER DEFAULT 0,
                bots_count INTEGER DEFAULT 0,
                payment_status TEXT DEFAULT 'pending',
                is_banned BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referred_by) REFERENCES users (telegram_id)
            )
        ''')
        
        # جدول ربات‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL,
                bot_username TEXT,
                bot_name TEXT,
                code TEXT,
                status TEXT DEFAULT 'stopped',
                port INTEGER,
                pid INTEGER,
                last_started TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # جدول تراکنش‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                description TEXT,
                reference_code TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # جدول فیش‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                payment_code TEXT UNIQUE NOT NULL,
                file_path TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # جدول درخواست‌های برداشت
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                card_number TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
        ''')
        
        # جدول آمار سیستم
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY,
                total_users INTEGER DEFAULT 0,
                total_bots INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0,
                total_paid INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        
        # ایجاد کد رفرال برای ادمین‌ها
        for admin_id in config.ADMIN_IDS:
            self._ensure_user(admin_id, "Admin", "مدیر سیستم")
    
    def _ensure_user(self, telegram_id, first_name, username=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        if not cursor.fetchone():
            referral_code = self._generate_referral_code()
            cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, referral_code, payment_status)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, username, first_name, referral_code, 'approved'))
            self.conn.commit()
    
    def _generate_referral_code(self, length=8):
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=length))
    
    @asynccontextmanager
    async def get_cursor(self):
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cursor.close()
    
    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    async def create_user(self, telegram_id: int, first_name: str, username: str = None, referred_by: int = None) -> Dict:
        async with self.get_cursor() as cursor:
            referral_code = self._generate_referral_code()
            cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, referral_code, referred_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (telegram_id, username, first_name, referral_code, referred_by, datetime.now()))
            
            # اگر با رفرال آمده، به معرف کمیسیون تعلق میگیره
            if referred_by:
                await self._add_commission(referred_by, telegram_id)
            
            # به روز رسانی آمار
            cursor.execute("UPDATE system_stats SET total_users = total_users + 1 WHERE id = 1")
            if cursor.rowcount == 0:
                cursor.execute("INSERT INTO system_stats (id, total_users, total_bots) VALUES (1, 1, 0)")
            
            return await self.get_user(telegram_id)
    
    async def _add_commission(self, referrer_id: int, new_user_id: int):
        """ثبت کمیسیون برای معرف (زمانی که کاربر جدید ثبت نام کرد)"""
        # اینجا فقط ثبت میکنیم، پرداخت واقعی بعد از خرید کاربر جدید انجام میشه
        pass
    
    async def add_payment(self, user_id: int, amount: int, payment_code: str, file_path: str = None):
        async with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO receipts (user_id, amount, payment_code, file_path, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, amount, payment_code, file_path, datetime.now()))
            
            # ثبت تراکنش
            cursor.execute('''
                INSERT INTO transactions (user_id, amount, type, status, reference_code, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, amount, 'deposit', 'pending', payment_code, 'شارژ کیف پول'))
            
            return cursor.lastrowid
    
    async def approve_payment(self, receipt_id: int, admin_id: int) -> bool:
        async with self.get_cursor() as cursor:
            # دریافت اطلاعات فیش
            cursor.execute("SELECT user_id, amount, payment_code FROM receipts WHERE id = ?", (receipt_id,))
            receipt = cursor.fetchone()
            if not receipt:
                return False
            
            # آپدیت فیش
            cursor.execute('''
                UPDATE receipts SET status = 'approved', reviewed_by = ?, reviewed_at = ?
                WHERE id = ?
            ''', (admin_id, datetime.now(), receipt_id))
            
            # افزایش موجودی کاربر
            cursor.execute('''
                UPDATE users SET balance = balance + ?, payment_status = 'approved'
                WHERE telegram_id = ?
            ''', (receipt['amount'], receipt['user_id']))
            
            # آپدیت تراکنش
            cursor.execute('''
                UPDATE transactions SET status = 'completed' WHERE reference_code = ?
            ''', (receipt['payment_code'],))
            
            # اگر کاربر توسط کسی معرف شده، ۱۰٪ به معرف بده
            cursor.execute("SELECT referred_by FROM users WHERE telegram_id = ?", (receipt['user_id'],))
            user = cursor.fetchone()
            if user and user['referred_by']:
                commission = int(receipt['amount'] * config.COMMISSION_PERCENT / 100)
                cursor.execute('''
                    UPDATE users SET balance = balance + ?, total_earned = total_earned + ?
                    WHERE telegram_id = ?
                ''', (commission, commission, user['referred_by']))
                
                # ثبت تراکنش کمیسیون
                cursor.execute('''
                    INSERT INTO transactions (user_id, amount, type, status, description)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user['referred_by'], commission, 'commission', 'completed', f'کمیسیون معرفی کاربر {receipt["user_id"]}'))
            
            # به روز رسانی آمار
            cursor.execute("UPDATE system_stats SET total_revenue = total_revenue + ? WHERE id = 1", (receipt['amount'],))
            
            return True
    
    async def create_withdraw_request(self, user_id: int, amount: int, card_number: str) -> bool:
        async with self.get_cursor() as cursor:
            # بررسی موجودی
            cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (user_id,))
            user = cursor.fetchone()
            if not user or user['balance'] < amount or amount < config.MIN_WITHDRAW:
                return False
            
            # ایجاد درخواست
            cursor.execute('''
                INSERT INTO withdraw_requests (user_id, amount, card_number, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, card_number, datetime.now()))
            
            # کاهش موجودی
            cursor.execute('''
                UPDATE users SET balance = balance - ? WHERE telegram_id = ?
            ''', (amount, user_id))
            
            # ثبت تراکنش
            ref_code = f"WD{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id}"
            cursor.execute('''
                INSERT INTO transactions (user_id, amount, type, status, reference_code, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, amount, 'withdraw', 'pending', ref_code, 'درخواست برداشت'))
            
            return True
    
    async def approve_withdraw(self, request_id: int, admin_id: int) -> bool:
        async with self.get_cursor() as cursor:
            cursor.execute('''
                UPDATE withdraw_requests SET status = 'approved', reviewed_by = ?, reviewed_at = ?
                WHERE id = ?
            ''', (admin_id, datetime.now(), request_id))
            
            cursor.execute('''
                UPDATE transactions SET status = 'completed' 
                WHERE user_id = (SELECT user_id FROM withdraw_requests WHERE id = ?) 
                AND type = 'withdraw' AND status = 'pending'
            ''', (request_id,))
            
            return True
    
    async def add_bot(self, bot_id: str, user_id: int, token: str, bot_name: str, bot_username: str, code: str):
        async with self.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO bots (id, user_id, token, bot_name, bot_username, code, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bot_id, user_id, token, bot_name, bot_username, code, 'running', datetime.now()))
            
            cursor.execute('''
                UPDATE users SET bots_count = bots_count + 1 WHERE telegram_id = ?
            ''', (user_id,))
            
            cursor.execute("UPDATE system_stats SET total_bots = total_bots + 1 WHERE id = 1")
    
    async def get_user_bots(self, user_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    async def delete_bot(self, bot_id: str, user_id: int) -> bool:
        async with self.get_cursor() as cursor:
            cursor.execute("SELECT user_id FROM bots WHERE id = ?", (bot_id,))
            bot = cursor.fetchone()
            if not bot or bot['user_id'] != user_id:
                return False
            
            cursor.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
            cursor.execute("UPDATE users SET bots_count = bots_count - 1 WHERE telegram_id = ?", (user_id,))
            cursor.execute("UPDATE system_stats SET total_bots = total_bots - 1 WHERE id = 1")
            return True
    
    async def get_referrals_list(self, user_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT telegram_id, first_name, username, payment_status, created_at 
            FROM users WHERE referred_by = ? ORDER BY created_at DESC
        ''', (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    async def get_statistics(self) -> Dict:
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total_users = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE payment_status = 'approved'")
        paid_users = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM bots")
        total_bots = cursor.fetchone()['count']
        
        cursor.execute("SELECT SUM(amount) as total FROM transactions WHERE type = 'deposit' AND status = 'completed'")
        total_revenue = cursor.fetchone()['total'] or 0
        
        cursor.execute("SELECT SUM(amount) as total FROM transactions WHERE type = 'withdraw' AND status = 'completed'")
        total_paid = cursor.fetchone()['total'] or 0
        
        cursor.execute("SELECT SUM(balance) as total FROM users")
        total_balance = cursor.fetchone()['total'] or 0
        
        return {
            'total_users': total_users,
            'paid_users': paid_users,
            'total_bots': total_bots,
            'total_revenue': total_revenue,
            'total_paid': total_paid,
            'total_balance': total_balance
        }

db = Database()

# ==================== FSM State ها ====================
class WithdrawState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_card = State()

class AdminState(StatesGroup):
    broadcasting = State()
    setting_price = State()

# ==================== ربات ====================
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== کیبوردها ====================
def main_keyboard(user_id: int = None) -> ReplyKeyboardMarkup:
    is_admin = user_id in config.ADMIN_IDS if user_id else False
    
    keyboard = [
        [KeyboardButton(text="🤖 ساخت ربات جدید")],
        [KeyboardButton(text="📋 ربات‌های من"), KeyboardButton(text="🔄 مدیریت ربات")],
        [KeyboardButton(text="💰 کیف پول من"), KeyboardButton(text="👥 لیست معرف‌ها")],
        [KeyboardButton(text="💳 برداشت وجه"), KeyboardButton(text="📊 آمار من")],
        [KeyboardButton(text="📚 راهنما"), KeyboardButton(text="📞 پشتیبانی")]
    ]
    
    if is_admin:
        keyboard.append([KeyboardButton(text="👑 پنل مدیریت")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📸 فیش‌ها", callback_data="admin_receipts"),
        InlineKeyboardButton(text="💰 درخواست‌ها", callback_data="admin_withdraws")
    )
    builder.row(
        InlineKeyboardButton(text="📢 پیام همگانی", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="📊 آمار کل", callback_data="admin_stats"),
        InlineKeyboardButton(text="👥 لیست کاربران", callback_data="admin_users")
    )
    return builder.as_markup()

# ==================== هندلر استارت ====================
@dp.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    # پردازش رفرال
    referred_by = None
    if command.args:
        try:
            ref_code = command.args.strip()
            cursor = db.conn.cursor()
            cursor.execute("SELECT telegram_id FROM users WHERE referral_code = ?", (ref_code,))
            result = cursor.fetchone()
            if result and result['telegram_id'] != user_id:
                referred_by = result['telegram_id']
        except:
            pass
    
    # بررسی وجود کاربر
    user = await db.get_user(user_id)
    if not user:
        user = await db.create_user(user_id, first_name, username, referred_by)
        
        # اطلاع به معرف
        if referred_by:
            try:
                commission_note = f"🎉 کاربر جدید با لینک شما ثبت نام کرد!\n👤 {first_name}\n💰 پس از اولین خرید، ۱۰٪ کمیسیون دریافت خواهید کرد."
                await bot.send_message(referred_by, commission_note)
            except:
                pass
    
    # لینک رفرال
    bot_info = await bot.me()
    referral_link = f"https://t.me/{bot_info.username}?start={user['referral_code']}"
    
    await message.answer(
        f"🚀 **به ربات سازنده ربات تلگرام خوش آمدید**\n\n"
        f"👤 نام: {first_name}\n"
        f"💰 موجودی: {user['balance']:,} تومان\n"
        f"🎁 کد معرف: `{user['referral_code']}`\n"
        f"🔗 لینک معرف: {referral_link}\n"
        f"👥 تعداد معرف: {len(await db.get_referrals_list(user_id))}\n"
        f"✅ وضعیت: {'تایید شده' if user['payment_status'] == 'approved' else 'در انتظار پرداخت'}\n\n"
        f"💡 برای شروع، فایل `bot.py` خود را ارسال کنید یا از دکمه‌ها استفاده کنید.",
        reply_markup=main_keyboard(user_id),
        parse_mode="Markdown"
    )

# ==================== ساخت ربات ====================
@dp.message(lambda m: m.text == "🤖 ساخت ربات جدید")
async def create_new_bot(message: Message):
    user = await db.get_user(message.from_user.id)
    
    # بررسی پرداخت
    if user['payment_status'] != 'approved':
        await message.answer(
            f"❌ **ابتدا باید پرداخت کنید**\n\n"
            f"💰 مبلغ: {config.PRICE:,} تومان\n"
            f"💳 شماره کارت: `{config.CARD_NUMBER}`\n"
            f"🏦 بانک: {config.BANK_NAME}\n"
            f"👤 به نام: {config.CARD_HOLDER}\n\n"
            f"📸 پس از واریز، تصویر فیش را ارسال کنید.\n"
            f"💡 کد پیگیری خود را یادداشت کنید.",
            parse_mode="Markdown"
        )
        return
    
    # بررسی محدودیت
    if user['bots_count'] >= config.MAX_BOTS_PER_USER:
        await message.answer(f"❌ حداکثر {config.MAX_BOTS_PER_USER} ربات می‌توانید بسازید.")
        return
    
    await message.answer(
        "📤 **ارسال فایل ربات**\n\n"
        "لطفاً فایل `bot.py` خود را ارسال کنید.\n"
        "⚠️ فایل باید شامل توکن ربات باشد.\n\n"
        "مثال:\n```python\nTOKEN = 'your_bot_token_here'\n```",
        parse_mode="Markdown"
    )

@dp.message(lambda m: m.document and m.document.file_name.endswith('.py'))
async def process_bot_file(message: Message):
    user = await db.get_user(message.from_user.id)
    
    if user['payment_status'] != 'approved':
        await message.answer("❌ ابتدا پرداخت کنید.")
        return
    
    status_msg = await message.answer("🔄 **در حال پردازش فایل...**", parse_mode="Markdown")
    
    try:
        # دانلود فایل
        file = await bot.get_file(message.document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        code = file_bytes.read().decode('utf-8')
        
        # استخراج توکن
        token_patterns = [
            r"TOKEN\s*=\s*['\"]([^'\"]+)['\"]",
            r"BOT_TOKEN\s*=\s*['\"]([^'\"]+)['\"]",
            r"token\s*=\s*['\"]([^'\"]+)['\"]",
            r"api_token\s*=\s*['\"]([^'\"]+)['\"]"
        ]
        
        token = None
        for pattern in token_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                token = match.group(1)
                break
        
        if not token:
            await status_msg.edit_text("❌ **توکن ربات در فایل پیدا نشد!**\n\nلطفاً مطمئن شوید که توکن در کد وجود دارد.\nمثال:\n`TOKEN = 'your_token'`", parse_mode="Markdown")
            return
        
        # بررسی توکن
        async with ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{token}/getMe") as resp:
                if resp.status != 200:
                    await status_msg.edit_text("❌ **توکن نامعتبر است!**\n\nلطفاً توکن صحیح را وارد کنید.", parse_mode="Markdown")
                    return
                bot_info = await resp.json()
                bot_username = bot_info['result']['username']
                bot_name = bot_info['result']['first_name']
        
        # ذخیره ربات
        bot_id = hashlib.md5(f"{user['telegram_id']}{token}{datetime.now()}".encode()).hexdigest()[:16]
        await db.add_bot(bot_id, user['telegram_id'], token, bot_name, bot_username, code)
        
        await status_msg.edit_text(
            f"✅ **ربات با موفقیت ساخته شد!**\n\n"
            f"🤖 نام: {bot_name}\n"
            f"🔗 آیدی: @{bot_username}\n"
            f"🆔 شناسه: `{bot_id}`\n\n"
            f"📋 برای مدیریت ربات از دکمه «📋 ربات‌های من» استفاده کنید.",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **خطا در ساخت ربات:**\n`{str(e)}`", parse_mode="Markdown")

# ==================== لیست ربات‌ها ====================
@dp.message(lambda m: m.text == "📋 ربات‌های من")
async def list_my_bots(message: Message):
    user = await db.get_user(message.from_user.id)
    bots = await db.get_user_bots(user['telegram_id'])
    
    if not bots:
        await message.answer("📋 **شما هیچ رباتی ندارید**\n\nبرای ساخت ربات جدید از دکمه «🤖 ساخت ربات جدید» استفاده کنید.", parse_mode="Markdown")
        return
    
    for bot_item in bots:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 استارت", callback_data=f"start_bot_{bot_item['id']}"),
                InlineKeyboardButton(text="⏹ استاپ", callback_data=f"stop_bot_{bot_item['id']}")
            ],
            [InlineKeyboardButton(text="🗑 حذف", callback_data=f"delete_bot_{bot_item['id']}")]
        ])
        
        status_emoji = "🟢" if bot_item['status'] == 'running' else "🔴"
        
        await message.answer(
            f"{status_emoji} **{bot_item['bot_name']}**\n"
            f"🔗 @{bot_item['bot_username']}\n"
            f"🆔 `{bot_item['id']}`\n"
            f"📅 ایجاد: {bot_item['created_at']}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

# ==================== کیف پول ====================
@dp.message(lambda m: m.text == "💰 کیف پول من")
async def show_wallet(message: Message):
    user = await db.get_user(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton(text="📜 تاریخچه تراکنش‌ها", callback_data="transactions_history")]
    ])
    
    await message.answer(
        f"💰 **کیف پول شما**\n\n"
        f"👤 {user['first_name']}\n"
        f"💵 موجودی: **{user['balance']:,}** تومان\n"
        f"🎁 کل درآمد: {user['total_earned']:,} تومان\n"
        f"🏧 کل برداشت: {user['total_withdrawn']:,} تومان\n\n"
        f"💳 برای شارژ، روی دکمه زیر کلیک کنید.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "charge_wallet")
async def charge_wallet(callback: CallbackQuery):
    await callback.message.answer(
        f"💳 **اطلاعات واریز**\n\n"
        f"🏦 بانک: {config.BANK_NAME}\n"
        f"💳 شماره کارت: `{config.CARD_NUMBER}`\n"
        f"👤 به نام: {config.CARD_HOLDER}\n"
        f"💰 مبلغ: {config.PRICE:,} تومان\n\n"
        f"📸 پس از واریز، تصویر فیش را ارسال کنید.\n"
        f"💡 کد پیگیری خود را یادداشت کنید.\n\n"
        f"⚠️ فقط مبلغ دقیق {config.PRICE:,} تومان واریز شود.",
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== برداشت وجه ====================
@dp.message(lambda m: m.text == "💳 برداشت وجه")
async def withdraw_money(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    
    if user['balance'] < config.MIN_WITHDRAW:
        await message.answer(
            f"❌ **موجودی شما کافی نیست**\n\n"
            f"موجودی فعلی: {user['balance']:,} تومان\n"
            f"حداقل برداشت: {config.MIN_WITHDRAW:,} تومان",
            parse_mode="Markdown"
        )
        return
    
    await state.set_state(WithdrawState.waiting_for_amount)
    await message.answer(
        f"💰 **برداشت وجه**\n\n"
        f"موجودی قابل برداشت: {user['balance']:,} تومان\n"
        f"حداقل برداشت: {config.MIN_WITHDRAW:,} تومان\n\n"
        f"مبلغ مورد نظر را به تومان وارد کنید:",
        parse_mode="Markdown"
    )

@dp.message(WithdrawState.waiting_for_amount)
async def withdraw_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        user = await db.get_user(message.from_user.id)
        
        if amount < config.MIN_WITHDRAW:
            await message.answer(f"❌ حداقل برداشت {config.MIN_WITHDRAW:,} تومان است.", parse_mode="Markdown")
            return
        
        if amount > user['balance']:
            await message.answer(f"❌ موجودی شما {user['balance']:,} تومان است.", parse_mode="Markdown")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(WithdrawState.waiting_for_card)
        await message.answer(
            f"💳 **شماره کارت مقصد**\n\n"
            f"لطفاً شماره کارت ۱۶ رقمی خود را وارد کنید:\n"
            f"(کارت باید به نام خودتان باشد)",
            parse_mode="Markdown"
        )
    except ValueError:
        await message.answer("❌ لطفاً عدد صحیح وارد کنید.")

@dp.message(WithdrawState.waiting_for_card)
async def withdraw_card(message: Message, state: FSMContext):
    card_number = message.text.strip().replace(" ", "")
    
    if not card_number.isdigit() or len(card_number) != 16:
        await message.answer("❌ شماره کارت باید ۱۶ رقم باشد.")
        return
    
    data = await state.get_data()
    amount = data['amount']
    user = await db.get_user(message.from_user.id)
    
    # ایجاد درخواست برداشت
    success = await db.create_withdraw_request(user['telegram_id'], amount, card_number)
    
    if success:
        await message.answer(
            f"✅ **درخواست برداشت ثبت شد**\n\n"
            f"💰 مبلغ: {amount:,} تومان\n"
            f"💳 کارت: `{card_number}`\n\n"
            f"⏳ درخواست شما برای ادمین ارسال شد.\n"
            f"پس از تایید، وجه به کارت شما واریز خواهد شد.",
            parse_mode="Markdown"
        )
        
        # اطلاع به ادمین‌ها
        for admin_id in config.ADMIN_IDS:
            try:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_withdraw_{user['telegram_id']}_{amount}"),
                        InlineKeyboardButton(text="❌ رد", callback_data=f"reject_withdraw_{user['telegram_id']}")
                    ]
                ])
                await bot.send_message(
                    admin_id,
                    f"💰 **درخواست برداشت جدید**\n\n"
                    f"👤 کاربر: {user['first_name']}\n"
                    f"🆔 آیدی: {user['telegram_id']}\n"
                    f"💰 مبلغ: {amount:,} تومان\n"
                    f"💳 کارت: {card_number}",
                    reply_markup=keyboard
                )
            except:
                pass
    else:
        await message.answer("❌ خطا در ثبت درخواست. لطفاً دوباره تلاش کنید.")
    
    await state.clear()

# ==================== لیست معرف‌ها ====================
@dp.message(lambda m: m.text == "👥 لیست معرف‌ها")
async def list_referrals(message: Message):
    user = await db.get_user(message.from_user.id)
    referrals = await db.get_referrals_list(user['telegram_id'])
    
    if not referrals:
        await message.answer("👥 **شما هیچ کاربری معرف نکرده‌اید**\n\n🎁 لینک معرف خود را به اشتراک بگذارید:\nاز طریق دکمه «💰 کیف پول من» می‌توانید لینک خود را دریافت کنید.", parse_mode="Markdown")
        return
    
    text = f"👥 **لیست معرف‌های شما**\n\n"
    for i, ref in enumerate(referrals[:20], 1):
        status = "✅" if ref['payment_status'] == 'approved' else "⏳"
        text += f"{i}. {status} {ref['first_name']} (@{ref['username'] or 'ندارد'})\n"
    
    if len(referrals) > 20:
        text += f"\nو {len(referrals) - 20} نفر دیگر..."
    
    text += f"\n\n💰 هر کاربری که پرداخت کند، شما **{config.COMMISSION_PERCENT}٪** کمیسیون دریافت می‌کنید."
    
    await message.answer(text, parse_mode="Markdown")

# ==================== آمار من ====================
@dp.message(lambda m: m.text == "📊 آمار من")
async def my_stats(message: Message):
    user = await db.get_user(message.from_user.id)
    referrals = await db.get_referrals_list(user['telegram_id'])
    paid_referrals = [r for r in referrals if r['payment_status'] == 'approved']
    
    await message.answer(
        f"📊 **آمار شخصی شما**\n\n"
        f"👤 نام: {user['first_name']}\n"
        f"🆔 آیدی: {user['telegram_id']}\n"
        f"🤖 تعداد ربات‌ها: {user['bots_count']}\n"
        f"👥 تعداد معرف‌ها: {len(referrals)}\n"
        f"✅ معرف‌های فعال: {len(paid_referrals)}\n"
        f"💰 موجودی: {user['balance']:,} تومان\n"
        f"🎁 کل درآمد: {user['total_earned']:,} تومان\n"
        f"🏧 کل برداشت: {user['total_withdrawn']:,} تومان\n"
        f"📅 تاریخ عضویت: {user['created_at']}",
        parse_mode="Markdown"
    )

# ==================== فیش‌های پرداخت ====================
@dp.message(lambda m: m.photo)
async def handle_receipt(message: Message):
    user = await db.get_user(message.from_user.id)
    
    # ایجاد کد پیگیری
    payment_code = f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}{message.from_user.id}"
    
    # دریافت عکس
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    
    # ذخیره فایل
    os.makedirs("receipts", exist_ok=True)
    file_path = f"receipts/{payment_code}.jpg"
    with open(file_path, "wb") as f:
        f.write(file_bytes.read())
    
    # ثبت در دیتابیس
    await db.add_payment(user['telegram_id'], config.PRICE, payment_code, file_path)
    
    await message.answer(
        f"✅ **فیش شما دریافت شد**\n\n"
        f"🆔 کد پیگیری: `{payment_code}`\n"
        f"💰 مبلغ: {config.PRICE:,} تومان\n"
        f"⏳ وضعیت: در انتظار تایید\n\n"
        f"پس از تایید، موجودی کیف پول شما افزایش می‌یابد.",
        parse_mode="Markdown"
    )
    
    # اطلاع به ادمین‌ها
    for admin_id in config.ADMIN_IDS:
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_payment_{payment_code}")]
            ])
            with open(file_path, "rb") as f:
                await bot.send_photo(
                    admin_id,
                    types.BufferedInputFile(f.read(), filename=f"{payment_code}.jpg"),
                    caption=f"📸 **فیش جدید**\n\n👤 {user['first_name']}\n🆔 {user['telegram_id']}\n💰 {config.PRICE:,} تومان\n🆔 {payment_code}",
                    reply_markup=keyboard
                )
        except:
            pass

# ==================== پنل مدیریت ====================
@dp.message(lambda m: m.text == "👑 پنل مدیریت")
async def admin_panel(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ دسترسی محدود")
        return
    
    stats = await db.get_statistics()
    
    await message.answer(
        f"👑 **پنل مدیریت**\n\n"
        f"📊 آمار سریع:\n"
        f"👥 کاربران: {stats['total_users']}\n"
        f"✅ پرداختی: {stats['paid_users']}\n"
        f"🤖 ربات‌ها: {stats['total_bots']}\n"
        f"💰 درآمد کل: {stats['total_revenue']:,} تومان\n"
        f"🏧 پرداختی: {stats['total_paid']:,} تومان\n"
        f"💎 موجودی سیستم: {stats['total_balance']:,} تومان",
        reply_markup=admin_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_receipts")
async def admin_receipts(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at DESC")
    receipts = cursor.fetchall()
    
    if not receipts:
        await callback.message.answer("📸 هیچ فیش در انتظاری وجود ندارد.")
        return
    
    for receipt in receipts:
        user = await db.get_user(receipt['user_id'])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_payment_{receipt['payment_code']}")]
        ])
        await callback.message.answer(
            f"📸 **فیش #{receipt['id']}**\n\n"
            f"👤 کاربر: {user['first_name'] if user else receipt['user_id']}\n"
            f"🆔 آیدی: {receipt['user_id']}\n"
            f"💰 مبلغ: {receipt['amount']:,} تومان\n"
            f"🆕 کد: `{receipt['payment_code']}`\n"
            f"📅 تاریخ: {receipt['created_at']}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_withdraws")
async def admin_withdraws(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at DESC")
    withdraws = cursor.fetchall()
    
    if not withdraws:
        await callback.message.answer("💰 هیچ درخواست برداشتی در انتظار نیست.")
        return
    
    for wd in withdraws:
        user = await db.get_user(wd['user_id'])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_withdraw_{wd['id']}"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"reject_withdraw_{wd['id']}")
            ]
        ])
        await callback.message.answer(
            f"💰 **درخواست برداشت #{wd['id']}**\n\n"
            f"👤 کاربر: {user['first_name'] if user else wd['user_id']}\n"
            f"🆔 آیدی: {wd['user_id']}\n"
            f"💰 مبلغ: {wd['amount']:,} تومان\n"
            f"💳 کارت: `{wd['card_number']}`\n"
            f"📅 تاریخ: {wd['created_at']}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("approve_payment_"))
async def approve_payment(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    payment_code = callback.data.replace("approve_payment_", "")
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT id FROM receipts WHERE payment_code = ? AND status = 'pending'", (payment_code,))
    receipt = cursor.fetchone()
    
    if receipt:
        await db.approve_payment(receipt['id'], callback.from_user.id)
        await callback.message.edit_text(f"✅ فیش {payment_code} تایید شد.")
        await callback.answer("تایید شد!")
    else:
        await callback.answer("فیش یافت نشد یا قبلاً تایید شده!", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("approve_withdraw_"))
async def approve_withdraw(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    withdraw_id = int(callback.data.replace("approve_withdraw_", ""))
    await db.approve_withdraw(withdraw_id, callback.from_user.id)
    await callback.message.edit_text(f"✅ درخواست برداشت #{withdraw_id} تایید شد.")
    await callback.answer("تایید شد!")

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    stats = await db.get_statistics()
    
    await callback.message.answer(
        f"📊 **آمار کامل سیستم**\n\n"
        f"👥 کل کاربران: {stats['total_users']}\n"
        f"✅ کاربران فعال: {stats['paid_users']}\n"
        f"🤖 کل ربات‌ها: {stats['total_bots']}\n"
        f"💰 درآمد کل: {stats['total_revenue']:,} تومان\n"
        f"🏧 پرداختی به کاربران: {stats['total_paid']:,} تومان\n"
        f"💎 موجودی سیستم: {stats['total_balance']:,} تومان\n"
        f"📈 سود خالص: {stats['total_revenue'] - stats['total_paid']:,} تومان",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    await state.set_state(AdminState.broadcasting)
    await callback.message.answer("📢 **ارسال پیام همگانی**\n\nلطفاً متن پیام را ارسال کنید:", parse_mode="Markdown")
    await callback.answer()

@dp.message(AdminState.broadcasting)
async def admin_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    text = message.text
    cursor = db.conn.cursor()
    cursor.execute("SELECT telegram_id FROM users")
    users = cursor.fetchall()
    
    status_msg = await message.answer(f"📢 در حال ارسال به {len(users)} کاربر...")
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(user['telegram_id'], text, parse_mode="Markdown")
            sent += 1
            if sent % 10 == 0:
                await status_msg.edit_text(f"📢 پیشرفت: {sent}/{len(users)}")
        except:
            failed += 1
    
    await status_msg.edit_text(f"✅ **پیام همگانی ارسال شد**\n\nموفق: {sent}\nناموفق: {failed}")
    await state.clear()

# ==================== راهنما و پشتیبانی ====================
@dp.message(lambda m: m.text == "📚 راهنما")
async def guide(message: Message):
    await message.answer(
        "📚 **راهنمای کامل ربات**\n\n"
        "**1️⃣ ساخت ربات:**\n"
        "- فایل bot.py خود را آماده کنید\n"
        "- مطمئن شوید توکن در کد وجود دارد\n"
        "- از دکمه «ساخت ربات جدید» استفاده کنید\n\n"
        "**2️⃣ پرداخت:**\n"
        "- مبلغ را به کارت اعلام شده واریز کنید\n"
        "- تصویر فیش را ارسال کنید\n"
        "- پس از تایید، موجودی شما افزایش می‌یابد\n\n"
        "**3️⃣ سیستم رفرال:**\n"
        "- از لینک معرف خود استفاده کنید\n"
        "- به ازای هر کاربر که خرید کند، ۱۰٪ کمیسیون دریافت می‌کنید\n"
        "- از دکمه «برداشت وجه» می‌توانید موجودی خود را برداشت کنید\n\n"
        "**4️⃣ مدیریت ربات‌ها:**\n"
        "- از دکمه «ربات‌های من» می‌توانید ربات‌های خود را ببینید\n"
        "- می‌توانید ربات را استارت، استاپ یا حذف کنید\n\n"
        "📞 **پشتیبانی:** @shahraghee13",
        parse_mode="Markdown"
    )

@dp.message(lambda m: m.text == "📞 پشتیبانی")
async def support(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 پشتیبانی", url="https://t.me/shahraghee13")]
    ])
    await message.answer(
        "📞 **پشتیبانی**\n\n"
        "برای ارتباط با پشتیبانی روی دکمه زیر کلیک کنید:\n\n"
        "⏰ پاسخگویی: ۹ صبح تا ۱۲ شب",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# ==================== مدیریت ربات (استارت/استاپ) ====================
@dp.callback_query(lambda c: c.data.startswith("start_bot_"))
async def start_bot(callback: CallbackQuery):
    bot_id = callback.data.replace("start_bot_", "")
    await callback.answer("در حال راه‌اندازی...", show_alert=True)
    await callback.message.edit_text(f"🔄 ربات در حال راه‌اندازی...")
    # در اینجا کد اجرای واقعی ربات رو می‌ذاریم (با subprocess یا docker)

@dp.callback_query(lambda c: c.data.startswith("stop_bot_"))
async def stop_bot(callback: CallbackQuery):
    bot_id = callback.data.replace("stop_bot_", "")
    await callback.answer("ربات متوقف شد!", show_alert=True)
    await callback.message.edit_text(f"⏹ ربات متوقف شد")

@dp.callback_query(lambda c: c.data.startswith("delete_bot_"))
async def delete_bot(callback: CallbackQuery):
    bot_id = callback.data.replace("delete_bot_", "")
    user = await db.get_user(callback.from_user.id)
    
    if await db.delete_bot(bot_id, user['telegram_id']):
        await callback.answer("ربات حذف شد!", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("خطا در حذف!", show_alert=True)

# ==================== اجرا ====================
async def main():
    print("=" * 60)
    print("🚀 ربات مادر حرفه‌ای - نسخه 5.0 Enterprise".center(60))
    print("=" * 60)
    print(f"✅ کاربران هدف: ۲,۰۰۰+ نفر")
    print(f"✅ سیستم رفرال: {config.COMMISSION_PERCENT}% کمیسیون")
    print(f"✅ حداقل برداشت: {config.MIN_WITHDRAW:,} تومان")
    print(f"✅ ادمین‌ها: {config.ADMIN_IDS}")
    print("=" * 60)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())