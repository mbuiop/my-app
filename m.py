#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
🚀 m.py - فایل اصلی - راه‌اندازی همه ماژول‌ها
═══════════════════════════════════════════════════════════════════
"""

import asyncio
import os
import sys
import signal
from dotenv import load_dotenv
from loguru import logger

# بارگذاری متغیرهای محیطی
load_dotenv()

# ایمپورت ماژول‌ها
from m1 import db
from m2 import isolator, k8s_manager
from m3 import build_queue, bot_manager
from m4 import setup_admin_handlers, ADMIN_IDS

import telebot
from telebot import types
import requests
import hashlib
import time
import zipfile
import re
import shutil
from datetime import datetime, timedelta
from functools import wraps

# ==================== تنظیمات اولیه ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8266270866:AAF6m1x4weSUEvzIj1gkbIS_j0yAdxCSs78")
BOT_USERNAME = "ROBTTSAZE_bot"

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
bot.delete_webhook()

# ==================== دکوریتور Rate Limit ====================
rate_limit_cache = {}

def rate_limit(limit_per_second=5):
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            now = time.time()
            
            if user_id not in rate_limit_cache:
                rate_limit_cache[user_id] = []
            
            rate_limit_cache[user_id] = [t for t in rate_limit_cache[user_id] if now - t < 1]
            
            if len(rate_limit_cache[user_id]) >= limit_per_second:
                bot.reply_to(message, "🚫 Please wait... / لطفاً صبر کنید...")
                return
            
            rate_limit_cache[user_id].append(now)
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

# ==================== منوی اصلی دوزبانه ====================
async def get_main_menu(user_id: int):
    """دریافت منو بر اساس زبان کاربر"""
    user = await db.get_user(user_id)
    lang = user.get('language', 'fa') if user else 'fa'
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    if lang == 'fa':
        buttons = [
            '🤖 ساخت ربات جدید', '📋 ربات‌های من',
            '🔄 فعال/غیرفعال', '🗑 حذف ربات',
            '💰 کیف پول و اشتراک', '📚 راهنما',
            '👥 دعوت دوستان', '💸 درخواست برداشت',
            '📦 کتابخانه', '📊 آمار', '📞 پشتیبانی'
        ]
    else:
        buttons = [
            '🤖 New Bot', '📋 My Bots',
            '🔄 Start/Stop', '🗑 Delete Bot',
            '💰 Wallet', '📚 Guide',
            '👥 Invite', '💸 Withdraw',
            '📦 Library', '📊 Stats', '📞 Support'
        ]
    
    user_data = await db.get_user(user_id)
    is_admin = user_id in ADMIN_IDS if user_data else False
    
    if is_admin:
        buttons.extend(['👑 Admin Panel', '📢 Broadcast'])
    
    markup.add(*buttons)
    return markup

# ==================== هندلر استارت ====================
@bot.message_handler(commands=['start'])
@rate_limit(3)
def cmd_start(message):
    user_id = message.from_user.id
    
    # پردازش رفرال
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        code = args[1]
        # پیدا کردن کاربر با کد رفرال
        import asyncio
        # TODO: پیدا کردن کاربر از دیتابیس
    
    # ایجاد کاربر
    import asyncio
    asyncio.run(db.create_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
        message.from_user.last_name or "",
        referred_by
    ))
    
    # ارسال پیام خوش‌آمدگویی
    text = f"🚀 خوش آمدید {message.from_user.first_name}!\n\n"
    text += f"👤 ID: {user_id}\n"
    text += "✅ می‌توانید با پرداخت اشتراک ماهانه، ۲ ربات بسازید"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 راهنما", callback_data="guide"))
    
    # منوی اصلی را به صورت async اجرا کنید
    import asyncio
    loop = asyncio.new_event_loop()
    menu = loop.run_until_complete(get_main_menu(user_id))
    loop.close()
    
    bot.send_message(message.chat.id, text, reply_markup=menu)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text in ['🤖 ساخت ربات جدید', '🤖 New Bot'])
@rate_limit(3)
def new_bot(message):
    user_id = message.from_user.id
    
    import asyncio
    loop = asyncio.new_event_loop()
    
    # بررسی حالت تعمیرات
    maintenance_mode = loop.run_until_complete(db.get_setting('maintenance_mode'))
    if maintenance_mode == 'true':
        msg = loop.run_until_complete(db.get_setting('maintenance_message'))
        bot.reply_to(message, msg)
        loop.close()
        return
    
    # بررسی اشتراک
    has_subscription = loop.run_until_complete(db.check_subscription(user_id))
    if not has_subscription:
        price = loop.run_until_complete(db.get_setting('subscription_price_str'))
        card = loop.run_until_complete(db.get_setting('card_number_display'))
        holder = loop.run_until_complete(db.get_setting('card_holder'))
        bank = loop.run_until_complete(db.get_setting('card_bank'))
        
        text = f"🚫 اشتراک فعال نیست!\n\n💰 مبلغ: {price}\n💳 کارت: {card}\n👤 {holder}\n🏦 {bank}\n\n📸 پس از واریز، فیش را ارسال کنید"
        bot.send_message(message.chat.id, text)
        loop.close()
        return
    
    # بررسی محدودیت (حداکثر 2 ربات)
    user = loop.run_until_complete(db.get_user(user_id))
    bots_count = user.get('bots_count', 0) if user else 0
    
    if bots_count >= 2:
        bot.send_message(message.chat.id, "❌ شما فقط می‌توانید ۲ ربات بسازید!\nبرای ساخت ربات جدید، یکی را حذف کنید.")
        loop.close()
        return
    
    bot.send_message(message.chat.id, "📤 فایل .py یا .zip ربات خود را ارسال کنید")
    loop.close()

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های .py یا .zip")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش...")
    
    import asyncio
    loop = asyncio.new_event_loop()
    
    try:
        # دانلود فایل
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        # استخراج کد
        code = ""
        if file_name.endswith('.zip'):
            # پردازش zip
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                tmp.write(downloaded)
                tmp_path = tmp.name
            
            extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as cf:
                            code = cf.read()
                            break
                if code:
                    break
            
            shutil.rmtree(extract_dir, ignore_errors=True)
            os.unlink(tmp_path)
        else:
            code = downloaded.decode('utf-8', errors='ignore')
        
        # استخراج توکن
        token_match = re.search(r'token\s*=\s*["\']([^"\']+)["\']', code, re.IGNORECASE)
        if not token_match:
            bot.edit_message_text("❌ توکن در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        token = token_match.group(1)
        
        # بررسی توکن
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            bot.edit_message_text("❌ توکن نامعتبر!", message.chat.id, status_msg.message_id)
            return
        
        bot_info = resp.json()['result']
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        # اضافه کردن به صف ساخت
        bot.edit_message_text(f"🔄 اضافه شد به صف...", message.chat.id, status_msg.message_id)
        
        # اجرا در صف
        async def add_to_queue():
            pos = await build_queue.add_build(user_id, bot_id, code, token, message.chat.id)
            return pos
        
        position = loop.run_until_complete(add_to_queue())
        bot.edit_message_text(f"✅ در صف قرار گرفت. موقعیت: {position}", message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)
        logger.error(f"Build error: {e}")
    finally:
        loop.close()

# ==================== کیف پول و اشتراک ====================
@bot.message_handler(func=lambda m: m.text in ['💰 کیف پول و اشتراک', '💰 Wallet'])
def wallet(message):
    user_id = message.from_user.id
    
    import asyncio
    loop = asyncio.new_event_loop()
    
    user = loop.run_until_complete(db.get_user(user_id))
    if not user:
        bot.send_message(message.chat.id, "❌ /start بزنید")
        loop.close()
        return
    
    has_sub = loop.run_until_complete(db.check_subscription(user_id))
    
    text = f"💰 **کیف پول**\n\n"
    text += f"👤 {user['first_name']}\n"
    text += f"💳 اشتراک: {'✅ فعال' if has_sub else '❌ غیرفعال'}\n"
    text += f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
    text += f"🤖 ربات‌ها: {user['bots_count']}/2\n"
    text += f"👥 دعوت‌ها: {user['referrals_count']}\n"
    text += f"🎁 کمیسیون کل: {user['total_commission_earned']:,} تومان"
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')
    loop.close()

# ==================== فیش واریزی ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    import asyncio
    loop = asyncio.new_event_loop()
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = f"/tmp/{user_id}_{payment_code}.jpg"
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        price = int(loop.run_until_complete(db.get_setting('subscription_price')))
        
        loop.run_until_complete(db.add_receipt(user_id, price, receipt_path, payment_code))
        
        bot.reply_to(message, f"✅ فیش دریافت شد\n💰 {price:,} تومان\n🆔 {payment_code}")
        
        # اطلاع به ادمین
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {user_id}\n💰 {price:,} تومان")
            except:
                pass
    
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")
    finally:
        loop.close()

# ==================== راه‌اندازی ====================
async def main():
    """راه‌اندازی اصلی"""
    logger.info("=" * 60)
    logger.info("🚀 Mother Bot - Ultimate Enterprise Edition")
    logger.info("=" * 60)
    
    # راه‌اندازی دیتابیس
    await db.init_db()
    await db.warmup_cache()
    logger.info("✅ Database initialized")
    
    # راه‌اندازی پردازش صف
    asyncio.create_task(build_queue.process_builds(bot, db))
    logger.info("✅ Build queue processor started")
    
    # راه‌اندازی Flask برای health check
    from flask import Flask, jsonify
    flask_app = Flask(__name__)
    
    @flask_app.route('/health')
    def health():
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'active_builds': len(build_queue.active_builds),
            'queue_size': build_queue.queue.qsize()
        })
    
    def run_flask():
        flask_app.run(host='0.0.0.0', port=5000)
    
    import threading
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("✅ Health check endpoint: http://localhost:5000/health")
    
    # تنظیم هندلرهای ادمین
    await setup_admin_handlers(bot, db)
    
    # راه‌اندازی ربات
    logger.info("✅ Starting bot polling...")
    logger.info(f"👑 Admin: {ADMIN_IDS}")
    logger.info(f"🤖 Bot: @{BOT_USERNAME}")
    logger.info("=" * 60)
    
    # تابع سیگنال برای shutdown
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # اجرای ربات (polling در ترد جداگانه)
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
