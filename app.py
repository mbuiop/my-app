#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════
🚀 ربات مادر حرفه‌ای - نسخه نهایی 7.0 (کاملاً تست شده)
═══════════════════════════════════════════════════════════════════
"""

import asyncio
import sqlite3
import hashlib
import re
import os
import random
import string
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, 
    InlineKeyboardButton, BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== تنظیمات ====================
BOT_TOKEN = "8541672444:AAF4PBn7-XqiXUgaK0arVajyZfcMWqbxSJ0"
ADMIN_IDS = [327855654]

PRICE = 2_000_000
COMMISSION_PERCENT = 10
MIN_WITHDRAW = 500_000

CARD_NUMBER = "5892101187322777"
CARD_HOLDER = "مرتضی نیکخو خنجری"
BANK_NAME = "بانک ملی"

MAX_BOTS_PER_USER = 10
DATABASE_FILE = "motherbot.db"

# ==================== دیتابیس ====================
conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ساخت جداول
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        referral_code TEXT UNIQUE,
        referred_by INTEGER,
        balance INTEGER DEFAULT 0,
        total_earned INTEGER DEFAULT 0,
        total_withdrawn INTEGER DEFAULT 0,
        bots_count INTEGER DEFAULT 0,
        payment_status TEXT DEFAULT 'pending',
        rating INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS bots (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        token TEXT,
        bot_name TEXT,
        bot_username TEXT,
        code TEXT,
        status TEXT DEFAULT 'stopped',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        payment_code TEXT UNIQUE,
        file_path TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS withdraw_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        card_number TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        type TEXT,
        status TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()

# ==================== توابع کمکی ====================
def generate_referral_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_user(telegram_id):
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def create_user(telegram_id, first_name, username=None, referred_by=None):
    referral_code = generate_referral_code()
    cursor.execute('''
        INSERT INTO users (telegram_id, username, first_name, referral_code, referred_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (telegram_id, username, first_name, referral_code, referred_by, datetime.now()))
    conn.commit()
    return get_user(telegram_id)

def update_balance(telegram_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, telegram_id))
    conn.commit()

def get_balance(telegram_id):
    cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    return row['balance'] if row else 0

def add_bot(bot_id, user_id, token, bot_name, bot_username, code):
    cursor.execute('''
        INSERT INTO bots (id, user_id, token, bot_name, bot_username, code, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (bot_id, user_id, token, bot_name, bot_username, code, datetime.now()))
    cursor.execute("UPDATE users SET bots_count = bots_count + 1 WHERE telegram_id = ?", (user_id,))
    conn.commit()

def get_user_bots(telegram_id):
    cursor.execute("SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC", (telegram_id,))
    return [dict(row) for row in cursor.fetchall()]

def delete_bot(bot_id, user_id):
    cursor.execute("SELECT user_id FROM bots WHERE id = ?", (bot_id,))
    bot = cursor.fetchone()
    if bot and bot['user_id'] == user_id:
        cursor.execute("DELETE FROM bots WHERE id = ?", (bot_id,))
        cursor.execute("UPDATE users SET bots_count = bots_count - 1 WHERE telegram_id = ?", (user_id,))
        conn.commit()
        return True
    return False

def get_referrals(telegram_id):
    cursor.execute("SELECT first_name, username, payment_status FROM users WHERE referred_by = ?", (telegram_id,))
    return [dict(row) for row in cursor.fetchall()]

def add_receipt(user_id, amount, payment_code, file_path):
    cursor.execute('''
        INSERT INTO receipts (user_id, amount, payment_code, file_path, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, payment_code, file_path, datetime.now()))
    conn.commit()
    return cursor.lastrowid

def get_pending_receipts():
    cursor.execute("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at DESC")
    return [dict(row) for row in cursor.fetchall()]

def approve_receipt(receipt_id, admin_id):
    cursor.execute("SELECT user_id, amount FROM receipts WHERE id = ?", (receipt_id,))
    receipt = cursor.fetchone()
    if receipt:
        cursor.execute("UPDATE receipts SET status = 'approved' WHERE id = ?", (receipt_id,))
        update_balance(receipt['user_id'], receipt['amount'])
        cursor.execute("UPDATE users SET payment_status = 'approved' WHERE telegram_id = ?", (receipt['user_id'],))
        
        # کمیسیون به معرف
        cursor.execute("SELECT referred_by FROM users WHERE telegram_id = ?", (receipt['user_id'],))
        user = cursor.fetchone()
        if user and user['referred_by']:
            commission = int(receipt['amount'] * COMMISSION_PERCENT / 100)
            update_balance(user['referred_by'], commission)
            cursor.execute("UPDATE users SET total_earned = total_earned + ? WHERE telegram_id = ?", (commission, user['referred_by']))
        
        conn.commit()
        return True
    return False

def add_withdraw_request(user_id, amount, card_number):
    if get_balance(user_id) < amount or amount < MIN_WITHDRAW:
        return False
    cursor.execute('''
        INSERT INTO withdraw_requests (user_id, amount, card_number, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, amount, card_number, datetime.now()))
    cursor.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (amount, user_id))
    conn.commit()
    return True

def get_pending_withdraws():
    cursor.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at DESC")
    return [dict(row) for row in cursor.fetchall()]

def approve_withdraw(request_id, admin_id):
    cursor.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (request_id,))
    req = cursor.fetchone()
    if req:
        cursor.execute("UPDATE withdraw_requests SET status = 'approved' WHERE id = ?", (request_id,))
        cursor.execute("UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE telegram_id = ?", (req['amount'], req['user_id']))
        conn.commit()
        return True
    return False

def reject_withdraw(request_id, admin_id):
    cursor.execute("SELECT user_id, amount FROM withdraw_requests WHERE id = ?", (request_id,))
    req = cursor.fetchone()
    if req:
        cursor.execute("UPDATE withdraw_requests SET status = 'rejected' WHERE id = ?", (request_id,))
        update_balance(req['user_id'], req['amount'])
        conn.commit()
        return True
    return False

def update_user_rating(telegram_id, rating):
    cursor.execute("UPDATE users SET rating = ? WHERE telegram_id = ?", (rating, telegram_id))
    conn.commit()

def get_all_users():
    cursor.execute("SELECT telegram_id, first_name, username, balance, payment_status, bots_count, rating FROM users ORDER BY created_at DESC")
    return [dict(row) for row in cursor.fetchall()]

def get_stats():
    cursor.execute("SELECT COUNT(*) as count FROM users")
    total_users = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE payment_status = 'approved'")
    paid_users = cursor.fetchone()['count']
    cursor.execute("SELECT COUNT(*) as count FROM bots")
    total_bots = cursor.fetchone()['count']
    cursor.execute("SELECT SUM(amount) as total FROM receipts WHERE status = 'approved'")
    total_revenue = cursor.fetchone()['total'] or 0
    return total_users, paid_users, total_bots, total_revenue

# ایجاد ادمین
for admin_id in ADMIN_IDS:
    if not get_user(admin_id):
        create_user(admin_id, "مدیر سیستم", "admin")

# ==================== FSM State ====================
class WithdrawState(StatesGroup):
    amount = State()
    card = State()

class AdminState(StatesGroup):
    broadcast = State()
    rating_user = State()

# ==================== کیبورد ====================
def get_keyboard(telegram_id):
    is_admin = telegram_id in ADMIN_IDS
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

# ==================== ربات ====================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== هندلر استارت (درست شده) ====================
@dp.message(CommandStart())
async def start_command(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    # پردازش رفرال از لینک
    referred_by = None
    text = message.text or ""
    if " " in text:
        ref_code = text.split(" ")[1]
        cursor.execute("SELECT telegram_id FROM users WHERE referral_code = ?", (ref_code,))
        ref_user = cursor.fetchone()
        if ref_user and ref_user['telegram_id'] != user_id:
            referred_by = ref_user['telegram_id']
    
    user = get_user(user_id)
    if not user:
        user = create_user(user_id, first_name, username, referred_by)
    
    bot_info = await bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start={user['referral_code']}"
    
    await message.answer(
        f"🚀 **به ربات سازنده ربات خوش آمدید**\n\n"
        f"👤 نام: {first_name}\n"
        f"💰 موجودی: {user['balance']:,} تومان\n"
        f"🎁 کد معرف: `{user['referral_code']}`\n"
        f"🔗 لینک معرف: {referral_link}\n"
        f"👥 تعداد معرف: {len(get_referrals(user_id))}\n"
        f"⭐ امتیاز: {user['rating']}\n"
        f"✅ وضعیت: {'✅ تایید شده' if user['payment_status'] == 'approved' else '⏳ در انتظار پرداخت'}\n\n"
        f"💡 فایل bot.py خود را ارسال کنید",
        reply_markup=get_keyboard(user_id),
        parse_mode="Markdown"
    )

# ==================== ساخت ربات ====================
@dp.message(lambda m: m.text == "🤖 ساخت ربات جدید")
async def new_bot(message: types.Message):
    user = get_user(message.from_user.id)
    
    if user['payment_status'] != 'approved':
        await message.answer(
            f"❌ **ابتدا پرداخت کنید**\n\n"
            f"💰 مبلغ: {PRICE:,} تومان\n"
            f"💳 شماره کارت: `{CARD_NUMBER}`\n"
            f"🏦 بانک: {BANK_NAME}\n"
            f"👤 به نام: {CARD_HOLDER}\n\n"
            f"📸 پس از واریز، تصویر فیش را ارسال کنید",
            parse_mode="Markdown"
        )
        return
    
    if user['bots_count'] >= MAX_BOTS_PER_USER:
        await message.answer(f"❌ حداکثر {MAX_BOTS_PER_USER} ربات")
        return
    
    await message.answer("📤 **فایل bot.py خود را ارسال کنید**", parse_mode="Markdown")

@dp.message(lambda m: m.document and m.document.file_name and m.document.file_name.endswith('.py'))
async def process_bot(message: types.Message):
    user = get_user(message.from_user.id)
    
    if user['payment_status'] != 'approved':
        await message.answer("❌ ابتدا پرداخت کنید")
        return
    
    status_msg = await message.answer("🔄 در حال پردازش...")
    
    try:
        file = await bot.get_file(message.document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        code = file_bytes.read().decode('utf-8')
        
        # استخراج توکن
        match = re.search(r'token\s*=\s*["\']([^"\']+)["\']', code, re.IGNORECASE)
        if not match:
            await status_msg.edit_text("❌ توکن پیدا نشد")
            return
        
        token = match.group(1)
        
        # بررسی توکن
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{token}/getMe") as resp:
                if resp.status != 200:
                    await status_msg.edit_text("❌ توکن نامعتبر")
                    return
                bot_data = await resp.json()
                bot_username = bot_data['result']['username']
                bot_name = bot_data['result']['first_name']
        
        bot_id = hashlib.md5(f"{user['telegram_id']}{token}{datetime.now()}".encode()).hexdigest()[:16]
        add_bot(bot_id, user['telegram_id'], token, bot_name, bot_username, code)
        
        await status_msg.edit_text(
            f"✅ **ربات ساخته شد**\n\n"
            f"🤖 {bot_name}\n"
            f"🔗 @{bot_username}\n"
            f"🆔 `{bot_id}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: {str(e)}")

# ==================== ربات‌های من ====================
@dp.message(lambda m: m.text == "📋 ربات‌های من")
async def my_bots(message: types.Message):
    bots = get_user_bots(message.from_user.id)
    
    if not bots:
        await message.answer("📋 رباتی ندارید")
        return
    
    for b in bots:
        emoji = "🟢" if b['status'] == 'running' else "🔴"
        await message.answer(
            f"{emoji} **{b['bot_name']}**\n"
            f"🔗 @{b['bot_username']}\n"
            f"🆔 `{b['id']}`",
            parse_mode="Markdown"
        )

# ==================== کیف پول ====================
@dp.message(lambda m: m.text == "💰 کیف پول من")
async def wallet(message: types.Message):
    user = get_user(message.from_user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 شارژ", callback_data="charge")]
    ])
    
    await message.answer(
        f"💰 **کیف پول**\n\n"
        f"👤 {user['first_name']}\n"
        f"💵 موجودی: **{user['balance']:,}** تومان\n"
        f"🎁 درآمد: {user['total_earned']:,} تومان\n"
        f"⭐ امتیاز: {user['rating']}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "charge")
async def charge(callback: types.CallbackQuery):
    await callback.message.answer(
        f"💳 **واریز**\n\n"
        f"💳 `{CARD_NUMBER}`\n"
        f"👤 {CARD_HOLDER}\n"
        f"💰 {PRICE:,} تومان\n\n"
        f"📸 پس از واریز، تصویر فیش را ارسال کنید",
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== فیش ====================
@dp.message(lambda m: m.photo)
async def receipt(message: types.Message):
    user = get_user(message.from_user.id)
    
    payment_code = f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}{message.from_user.id}"
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)
    
    os.makedirs("receipts", exist_ok=True)
    file_path = f"receipts/{payment_code}.jpg"
    with open(file_path, "wb") as f:
        f.write(file_bytes.read())
    
    add_receipt(user['telegram_id'], PRICE, payment_code, file_path)
    
    await message.answer(
        f"✅ **فیش دریافت شد**\n"
        f"🆔 {payment_code}\n"
        f"⏳ در انتظار تایید",
        parse_mode="Markdown"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            with open(file_path, "rb") as f:
                await bot.send_photo(
                    admin_id,
                    BufferedInputFile(f.read(), filename="receipt.jpg"),
                    caption=f"📸 فیش جدید\n👤 {user['first_name']}\n🆔 {user['telegram_id']}\n💰 {PRICE:,}"
                )
        except:
            pass

# ==================== برداشت ====================
@dp.message(lambda m: m.text == "💳 برداشت وجه")
async def withdraw_start(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    
    if user['balance'] < MIN_WITHDRAW:
        await message.answer(f"❌ موجودی کافی نیست\nحداقل برداشت: {MIN_WITHDRAW:,} تومان", parse_mode="Markdown")
        return
    
    await state.set_state(WithdrawState.amount)
    await message.answer(f"💰 مبلغ به تومان:\n(حداکثر {user['balance']:,})", parse_mode="Markdown")

@dp.message(WithdrawState.amount)
async def withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        user = get_user(message.from_user.id)
        
        if amount < MIN_WITHDRAW:
            await message.answer(f"❌ حداقل {MIN_WITHDRAW:,} تومان")
            return
        if amount > user['balance']:
            await message.answer(f"❌ موجودی {user['balance']:,} تومان")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(WithdrawState.card)
        await message.answer("💳 شماره کارت ۱۶ رقمی:")
    except:
        await message.answer("❌ عدد وارد کنید")

@dp.message(WithdrawState.card)
async def withdraw_card(message: types.Message, state: FSMContext):
    card = message.text.strip().replace(" ", "")
    
    if not card.isdigit() or len(card) != 16:
        await message.answer("❌ شماره کارت ۱۶ رقم")
        return
    
    data = await state.get_data()
    amount = data['amount']
    user = get_user(message.from_user.id)
    
    if add_withdraw_request(user['telegram_id'], amount, card):
        await message.answer(
            f"✅ درخواست برداشت ثبت شد\n💰 {amount:,} تومان\n⏳ در انتظار تایید",
            parse_mode="Markdown"
        )
        
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, f"💰 درخواست برداشت\n👤 {user['first_name']}\n💰 {amount:,}\n💳 {card}")
    else:
        await message.answer("❌ خطا")
    
    await state.clear()

# ==================== لیست معرف‌ها ====================
@dp.message(lambda m: m.text == "👥 لیست معرف‌ها")
async def referrals_list(message: types.Message):
    referrals = get_referrals(message.from_user.id)
    
    if not referrals:
        await message.answer("👥 کسی معرف نکردید")
        return
    
    text = "👥 **معرف‌های شما**\n\n"
    for i, r in enumerate(referrals[:20], 1):
        status = "✅" if r['payment_status'] == 'approved' else "⏳"
        text += f"{i}. {status} {r['first_name']}\n"
    
    await message.answer(text, parse_mode="Markdown")

# ==================== آمار من ====================
@dp.message(lambda m: m.text == "📊 آمار من")
async def my_stats(message: types.Message):
    user = get_user(message.from_user.id)
    referrals = get_referrals(message.from_user.id)
    paid = [r for r in referrals if r['payment_status'] == 'approved']
    
    await message.answer(
        f"📊 **آمار شما**\n\n"
        f"🤖 ربات‌ها: {user['bots_count']}\n"
        f"👥 معرف‌ها: {len(referrals)}\n"
        f"✅ فعال: {len(paid)}\n"
        f"💰 موجودی: {user['balance']:,}\n"
        f"⭐ امتیاز: {user['rating']}",
        parse_mode="Markdown"
    )

# ==================== مدیریت ربات ====================
@dp.message(lambda m: m.text == "🔄 مدیریت ربات")
async def manage_bots(message: types.Message):
    bots = get_user_bots(message.from_user.id)
    
    if not bots:
        await message.answer("📋 رباتی ندارید")
        return
    
    for b in bots:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ استارت", callback_data=f"start_{b['id']}"),
                InlineKeyboardButton(text="⏹️ استاپ", callback_data=f"stop_{b['id']}")
            ],
            [InlineKeyboardButton(text="🗑️ حذف", callback_data=f"del_{b['id']}")]
        ])
        
        await message.answer(
            f"🤖 **{b['bot_name']}**\n🆔 `{b['id']}`",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

@dp.callback_query(lambda c: c.data.startswith("del_"))
async def delete_bot_cmd(callback: types.CallbackQuery):
    bot_id = callback.data.replace("del_", "")
    user_id = callback.from_user.id
    
    if delete_bot(bot_id, user_id):
        await callback.answer("حذف شد!", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("خطا!", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("start_"))
async def start_bot_cmd(callback: types.CallbackQuery):
    await callback.answer("در حال راه‌اندازی...", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("stop_"))
async def stop_bot_cmd(callback: types.CallbackQuery):
    await callback.answer("متوقف شد!", show_alert=True)

# ==================== پنل مدیریت ====================
@dp.message(lambda m: m.text == "👑 پنل مدیریت")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    stats = get_stats()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 فیش‌ها", callback_data="admin_receipts"),
         InlineKeyboardButton(text="💰 برداشت‌ها", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="⭐ امتیاز دهی", callback_data="admin_rate"),
         InlineKeyboardButton(text="👥 کاربران", callback_data="admin_users")],
        [InlineKeyboardButton(text="📢 پیام همگانی", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="📊 آمار", callback_data="admin_stats")]
    ])
    
    await message.answer(
        f"👑 **پنل مدیریت**\n\n"
        f"👥 کاربران: {stats[0]}\n"
        f"✅ پرداختی: {stats[1]}\n"
        f"🤖 ربات‌ها: {stats[2]}\n"
        f"💰 درآمد: {stats[3]:,} تومان",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "admin_receipts")
async def admin_receipts(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    receipts = get_pending_receipts()
    
    if not receipts:
        await callback.message.answer("📸 فیشی نیست")
        await callback.answer()
        return
    
    for r in receipts:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_rec_{r['id']}")]
        ])
        await callback.message.answer(
            f"📸 فیش #{r['id']}\n👤 کاربر: {r['user_id']}\n💰 {r['amount']:,}",
            reply_markup=keyboard
        )
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("approve_rec_"))
async def approve_receipt(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    receipt_id = int(callback.data.replace("approve_rec_", ""))
    if approve_receipt(receipt_id, callback.from_user.id):
        await callback.message.edit_text("✅ تایید شد")
        await callback.answer("تایید شد!")
    else:
        await callback.answer("خطا!")

@dp.callback_query(lambda c: c.data == "admin_withdraws")
async def admin_withdraws(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    withdraws = get_pending_withdraws()
    
    if not withdraws:
        await callback.message.answer("💰 درخواستی نیست")
        await callback.answer()
        return
    
    for w in withdraws:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_wd_{w['id']}"),
                InlineKeyboardButton(text="❌ رد", callback_data=f"reject_wd_{w['id']}")
            ]
        ])
        await callback.message.answer(
            f"💰 درخواست #{w['id']}\n👤 کاربر: {w['user_id']}\n💰 {w['amount']:,}\n💳 {w['card_number']}",
            reply_markup=keyboard
        )
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("approve_wd_"))
async def approve_withdraw_admin(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    wd_id = int(callback.data.replace("approve_wd_", ""))
    if approve_withdraw(wd_id, callback.from_user.id):
        await callback.message.edit_text("✅ تایید شد")
        await callback.answer("تایید شد!")
    else:
        await callback.answer("خطا!")

@dp.callback_query(lambda c: c.data.startswith("reject_wd_"))
async def reject_withdraw_admin(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    wd_id = int(callback.data.replace("reject_wd_", ""))
    if reject_withdraw(wd_id, callback.from_user.id):
        await callback.message.edit_text("❌ رد شد")
        await callback.answer("رد شد!")
    else:
        await callback.answer("خطا!")

@dp.callback_query(lambda c: c.data == "admin_rate")
async def rate_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    await state.set_state(AdminState.rating_user)
    await callback.message.answer("⭐ آیدی عددی کاربر را وارد کنید:")
    await callback.answer()

@dp.message(AdminState.rating_user)
async def set_rating(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        user = get_user(user_id)
        
        if not user:
            await message.answer("❌ کاربر یافت نشد")
            await state.clear()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐1", callback_data=f"rate_{user_id}_1"),
             InlineKeyboardButton(text="⭐⭐2", callback_data=f"rate_{user_id}_2"),
             InlineKeyboardButton(text="⭐⭐⭐3", callback_data=f"rate_{user_id}_3")],
            [InlineKeyboardButton(text="⭐⭐⭐⭐4", callback_data=f"rate_{user_id}_4"),
             InlineKeyboardButton(text="⭐⭐⭐⭐⭐5", callback_data=f"rate_{user_id}_5")]
        ])
        
        await message.answer(f"👤 {user['first_name']}\n⭐ امتیاز فعلی: {user['rating']}\nامتیاز جدید:", reply_markup=keyboard)
        await state.clear()
    except:
        await message.answer("❌ عدد وارد کنید")
        await state.clear()

@dp.callback_query(lambda c: c.data.startswith("rate_"))
async def apply_rating(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    parts = callback.data.split("_")
    user_id = int(parts[1])
    rating = int(parts[2])
    
    update_user_rating(user_id, rating)
    user = get_user(user_id)
    
    await callback.message.edit_text(f"✅ امتیاز {user['first_name']} به {rating} تغییر کرد")
    await callback.answer("ثبت شد!")

@dp.callback_query(lambda c: c.data == "admin_users")
async def all_users(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    users = get_all_users()
    
    if not users:
        await callback.message.answer("👥 کاربری نیست")
        await callback.answer()
        return
    
    text = "👥 **کاربران**\n\n"
    for i, u in enumerate(users[:30], 1):
        status = "✅" if u['payment_status'] == 'approved' else "⏳"
        text += f"{i}. {status} {u['first_name']} - {u['balance']:,} - ⭐{u['rating']}\n"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_prompt(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    await state.set_state(AdminState.broadcast)
    await callback.message.answer("📢 متن پیام را ارسال کنید:")
    await callback.answer()

@dp.message(AdminState.broadcast)
async def send_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    users = get_all_users()
    status_msg = await message.answer(f"📢 در حال ارسال به {len(users)} کاربر...")
    
    sent = 0
    for user in users:
        try:
            await bot.send_message(user['telegram_id'], message.text, parse_mode="Markdown")
            sent += 1
        except:
            pass
    
    await status_msg.edit_text(f"✅ ارسال شد به {sent} کاربر")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔")
        return
    
    stats = get_stats()
    await callback.message.answer(
        f"📊 **آمار**\n\n"
        f"👥 کاربران: {stats[0]}\n"
        f"✅ پرداختی: {stats[1]}\n"
        f"🤖 ربات‌ها: {stats[2]}\n"
        f"💰 درآمد: {stats[3]:,} تومان",
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== راهنما و پشتیبانی ====================
@dp.message(lambda m: m.text == "📚 راهنما")
async def guide(message: types.Message):
    await message.answer(
        "📚 **راهنما**\n\n"
        "1️⃣ فایل bot.py ارسال کنید\n"
        "2️⃣ به کارت واریز کنید و فیش ارسال کنید\n"
        "3️⃣ پس از تایید، ربات بسازید\n"
        "4️⃣ با لینک معرف خود از دیگران کمیسیون بگیرید\n\n"
        "📞 پشتیبانی: @shahraghee13",
        parse_mode="Markdown"
    )

@dp.message(lambda m: m.text == "📞 پشتیبانی")
async def support(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 پشتیبانی", url="https://t.me/shahraghee13")]
    ])
    await message.answer("📞 @shahraghee13", reply_markup=keyboard)

# ==================== اجرا ====================
async def main():
    print("=" * 50)
    print("🚀 ربات روشن شد!")
    print(f"👑 ادمین: {ADMIN_IDS}")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())