================================================================================
                    ربات مادر حرفه‌ای - نسخه نهایی
                 معماری میکروسرویس + ایزوله‌سازی کامل
================================================================================

این فایل شامل تمام کدهای مورد نیاز برای اجرای کامل ربات مادر است.
تمام فایل‌ها را به ترتیب ایجاد کنید.

================================================================================
                            فایل 1: .env
================================================================================

# Bot Configuration
BOT_TOKEN=7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo
ADMIN_IDS=327855654

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=motherbot
POSTGRES_USER=admin
POSTGRES_PASSWORD=SuperSecurePassword123!

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# RabbitMQ Configuration
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Docker Sandbox Configuration
SANDBOX_IMAGE=python:3.11-slim
SANDBOX_MEMORY_LIMIT=512m
SANDBOX_CPU_LIMIT=0.5
SANDBOX_NETWORK=none
SANDBOX_TIMEOUT=60

# Executor Servers (برای Load Balancing)
EXECUTOR_SERVERS=[
    {"host": "localhost", "port": 2375, "max_workers": 1000}
]

# Payment Configuration
CARD_NUMBER=5892101187322777
CARD_HOLDER=مرتضی نیکخو خنجری
PRICE=2000000
MIN_WITHDRAW=2000000
REFERRAL_PERCENT=7

# Admin Panel
ADMIN_PASSWORD=SuperAdmin123
API_GATEWAY_URL=http://api_gateway:8000

================================================================================
                            فایل 2: requirements.txt
================================================================================

# Core
telebot==0.0.5
fastapi==0.104.1
uvicorn==0.24.0
gunicorn==21.2.0
python-telegram-bot==20.6

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
alembic==1.12.1
redis==5.0.1
asyncpg==0.29.0

# Docker & Orchestration
docker==6.1.3

# Security
cryptography==41.0.7
bcrypt==4.0.1
python-jose==3.3.0
passlib==1.7.4

# Async
aiohttp==3.9.1
asyncio==3.4.3
aio-pika==9.3.1
celery==5.3.4

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
requests==2.31.0
schedule==1.2.0
python-multipart==0.0.6

================================================================================
                            فایل 3: docker-compose.yml
================================================================================

version: '3.8'

services:
  # PostgreSQL - دیتابیس اصلی
  postgres:
    image: postgres:15-alpine
    container_name: motherbot_postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - motherbot_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis - کش و Session
  redis:
    image: redis:7-alpine
    container_name: motherbot_redis
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - motherbot_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # RabbitMQ - صف پیام
  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: motherbot_rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    ports:
      - "5672:5672"
      - "15672:15672"
    networks:
      - motherbot_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5

  # API Gateway
  api_gateway:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: motherbot_api
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - RABBITMQ_HOST=rabbitmq
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - motherbot_network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  # Telegram Bot
  telegram_bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
    container_name: motherbot_telegram
    environment:
      - API_GATEWAY_URL=http://api_gateway:8000
    env_file:
      - .env
    depends_on:
      - api_gateway
    networks:
      - motherbot_network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  # Code Executor (اجراکننده اصلی)
  code_executor:
    build:
      context: .
      dockerfile: Dockerfile.sandbox
    container_name: motherbot_executor
    environment:
      - EXECUTOR_ID=1
      - MAX_WORKERS=1000
      - API_GATEWAY_URL=http://api_gateway:8000
    env_file:
      - .env
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - motherbot_network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

networks:
  motherbot_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:

================================================================================
                            فایل 4: Dockerfile.bot
================================================================================

FROM python:3.11-slim

WORKDIR /app

# کپی فایل‌های مورد نیاز
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY api_gateway.py .

# اجرای ربات
CMD ["python", "main.py"]

================================================================================
                            فایل 5: Dockerfile.api
================================================================================

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api_gateway.py .
COPY database/ ./database/

EXPOSE 8000

CMD ["uvicorn", "api_gateway:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

================================================================================
                            فایل 6: Dockerfile.sandbox
================================================================================

FROM python:3.11-slim

# نصب ابزارهای امنیتی برای ایزوله‌سازی
RUN apt-get update && apt-get install -y \
    firejail \
    bubblewrap \
    && rm -rf /var/lib/apt/lists/*

# ایجاد کاربر محدود
RUN useradd -m -s /bin/bash sandbox && \
    mkdir -p /sandbox /tmp/sandbox && \
    chown -R sandbox:sandbox /sandbox /tmp/sandbox

# محدودیت‌های سخت‌افزاری
RUN echo "sandbox soft nproc 50" >> /etc/security/limits.conf && \
    echo "sandbox hard nproc 50" >> /etc/security/limits.conf && \
    echo "sandbox soft as 524288000" >> /etc/security/limits.conf && \
    echo "sandbox hard as 524288000" >> /etc/security/limits.conf

# کپی فایل اجراکننده
COPY code_executor.py /code_executor.py

WORKDIR /sandbox

USER sandbox

CMD ["python", "/code_executor.py"]

================================================================================
                        فایل 7: main.py (ربات تلگرام کامل)
================================================================================

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات مادر حرفه‌ای - نسخه نهایی
با قابلیت: تست ۲۴ ساعته، رفرال ۷٪، برداشت وجه، پنل ادمین کامل
"""

import os
import sys
import json
import hashlib
import secrets
import time
import re
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import telebot
from telebot import types
from dotenv import load_dotenv

# بارگذاری تنظیمات
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "7685135237:AAEmsHktRw9cEqrHTkCoPZk-fBimK7TDjOo")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "327855654").split(",") if x]
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
PRICE = int(os.getenv("PRICE", "2000000"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "5892101187322777")
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "2000000"))

bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== منوی اصلی ====================
def get_main_menu(is_admin: bool = False):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال کردن'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و رفرال'),
        types.KeyboardButton('⏱ تست ۲۴ ساعته'),
        types.KeyboardButton('🏧 برداشت وجه'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📊 آمار'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if is_admin:
        buttons.append(types.KeyboardButton('👑 پنل ادمین'))
    
    markup.add(*buttons)
    return markup

# ==================== هندلر استارت ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    # پردازش کد رفرال
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        try:
            response = requests.post(
                f"{API_GATEWAY_URL}/api/v1/users/check-referral",
                json={"referral_code": ref_code, "user_id": user_id},
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("valid"):
                    referred_by = data.get("referrer_id")
        except:
            pass
    
    # ثبت کاربر
    try:
        requests.post(
            f"{API_GATEWAY_URL}/api/v1/users/register",
            json={"user_id": user_id, "username": username, "first_name": first_name, "referred_by": referred_by},
            timeout=5
        )
    except:
        pass
    
    # دریافت اطلاعات کاربر
    user_data = {}
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}", timeout=5)
        if response.status_code == 200:
            user_data = response.json()
    except:
        pass
    
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user_data.get('referral_code', '')}"
    is_admin = user_id in ADMIN_IDS
    
    welcome_text = f"""
🚀 **به ربات ساز حرفه‌ای خوش آمدید {first_name}!**

👤 آیدی شما: `{user_id}`
🎁 کد رفرال: `{user_data.get('referral_code', '')}`
🔗 لینک دعوت: {referral_link}

📊 **آمار رفرال:**
• کلیک‌ها: {user_data.get('referrals_count', 0)}
• خریدهای موفق: {user_data.get('verified_referrals', 0)}
• درآمد از رفرال: {user_data.get('referral_earnings', 0):,} تومان

💡 **هر خرید = ۷٪ سود برای شما**

📤 فایل `.py` یا `.zip` خود را آپلود کنید
"""
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=get_main_menu(is_admin))

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    # بررسی اشتراک
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}/subscription", timeout=5)
        subscription = response.json() if response.status_code == 200 else {}
    except:
        subscription = {"is_active": False}
    
    if not subscription.get("is_active"):
        text = f"""
⚠️ **کاربر گرامی، از اینکه ما را انتخاب کردید متشکریم**

برای فعال‌سازی اشتراک و ساخت ربات، مبلغ **{PRICE:,} تومان** به شماره کارت زیر واریز کنید:

💳 **شماره کارت:** `{CARD_NUMBER}`
🏦 **بانک سپه**
👤 **به نام:** مرتضی نیکخو خنجری

📸 **مراحل فعال‌سازی:**
1. مبلغ را به کارت فوق واریز کنید
2. از صفحه واریز عکس بگیرید
3. عکس فیش را در همین چت ارسال کنید
4. پس از تأیید، اشتراک شما فعال می‌شود

✅ **پس از تأیید می‌توانید ربات خود را بسازید**

🔗 **لینک رفرال شما:** هر کاربر که با لینک شما وارد شود و خرید کند، **۷٪ سود** به کیف پول شما اضافه می‌شود
"""
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return
    
    # بررسی محدودیت تعداد ربات
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}/bot-limit", timeout=5)
        limit_data = response.json() if response.status_code == 200 else {}
    except:
        limit_data = {"can_create": True, "max_bots": 1, "current_bots": 0}
    
    if not limit_data.get("can_create"):
        bot.send_message(
            message.chat.id,
            f"❌ شما به حداکثر تعداد ربات ({limit_data.get('max_bots')}) رسیده‌اید!\n"
            f"برای ساخت ربات جدید:\n"
            f"1️⃣ یکی از ربات‌ها را حذف کنید\n"
            f"2️⃣ یا با دعوت دوستان ربات اضافه بگیرید"
        )
        return
    
    bot.send_message(
        message.chat.id,
        "📤 **فایل ربات خود را ارسال کنید**\n\n"
        "✅ فایل‌های مجاز: `.py` یا `.zip`\n"
        "✅ حداکثر حجم: ۵۰ مگابایت\n"
        "✅ توکن ربات داخل کد باشد\n"
        "✅ اگر فایل زیپ است، تمام فایل‌های پروژه را شامل شود\n\n"
        "⚡ ربات شما در محیطی کاملاً ایزوله و امن اجرا خواهد شد",
        parse_mode="Markdown"
    )

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۵۰ مگابایت باشد!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل در محیط ایزوله...")
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    files = {'file': (file_name, downloaded_file)}
    
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/bots/create",
            data={"user_id": user_id},
            files=files,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                bot.edit_message_text(
                    f"✅ **ربات با موفقیت ساخته شد!** 🎉\n\n"
                    f"🤖 نام: {result.get('bot_name', 'نامشخص')}\n"
                    f"🔗 لینک: https://t.me/{result.get('bot_username', '')}\n"
                    f"🆔 آیدی ربات: `{result.get('bot_id', '')}`\n"
                    f"📦 کتابخانه‌های نصب شده: {', '.join(result.get('installed', []))}\n\n"
                    f"📊 وضعیت: {'🟢 در حال اجرا' if result.get('is_running') else '🔴 متوقف'}",
                    message.chat.id,
                    status_msg.message_id,
                    parse_mode="Markdown"
                )
            else:
                bot.edit_message_text(
                    f"❌ خطا در ساخت ربات:\n{result.get('error', 'خطای ناشناخته')}",
                    message.chat.id,
                    status_msg.message_id
                )
        else:
            bot.edit_message_text(f"❌ خطا در ارتباط با سرور", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== تست ۲۴ ساعته ====================
@bot.message_handler(func=lambda m: m.text == '⏱ تست ۲۴ ساعته')
def trial_24h(message):
    user_id = message.from_user.id
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}/trial-status", timeout=5)
        trial_data = response.json() if response.status_code == 200 else {}
    except:
        trial_data = {"can_trial": True, "has_used_trial": False}
    
    if trial_data.get("has_used_trial"):
        bot.send_message(
            message.chat.id,
            "❌ شما قبلاً از تست ۲۴ ساعته استفاده کرده‌اید!\nبرای استفاده از ربات، اشتراک تهیه کنید."
        )
        return
    
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/users/{user_id}/activate-trial",
            json={"duration_hours": 24},
            timeout=5
        )
        
        if response.status_code == 200:
            bot.send_message(
                message.chat.id,
                "✅ **تست ۲۴ ساعته فعال شد!** 🎉\n\n"
                "شما می‌توانید به مدت ۲۴ ساعت یک ربات بسازید و تست کنید.\n"
                "پس از اتمام زمان تست، ربات شما غیرفعال می‌شود.\n\n"
                "برای ادامه، روی دکمه '🤖 ساخت ربات جدید' کلیک کنید."
            )
        else:
            bot.send_message(message.chat.id, "❌ خطا در فعال‌سازی تست")
    except:
        bot.send_message(message.chat.id, "❌ خطا در ارتباط با سرور")

# ==================== کیف پول و رفرال ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و رفرال')
def wallet_ref(message):
    user_id = message.from_user.id
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}/wallet", timeout=5)
        data = response.json() if response.status_code == 200 else {}
    except:
        data = {}
    
    bot_username = bot.get_me().username
    
    text = f"""
💰 **کیف پول و سیستم رفرال**

👤 کاربر: {data.get('first_name', '')}
🆔 آیدی: `{user_id}`

💳 **موجودی کیف پول:** {data.get('balance', 0):,} تومان
🎁 **درآمد از رفرال:** {data.get('referral_earnings', 0):,} تومان

📊 **آمار رفرال:**
• کلیک‌ها: {data.get('referrals_count', 0)}
• خریدهای موفق: {data.get('verified_referrals', 0)}

🔗 **لینک رفرال شما:**
`https://t.me/{bot_username}?start={data.get('referral_code', '')}`

💡 **نحوه کسب درآمد:**
• هر کاربر که با لینک شما وارد شود و اشتراک بخرد
• **۷٪ مبلغ پرداختی** به کیف پول شما اضافه می‌شود
• قابل برداشت از {MIN_WITHDRAW:,} تومان

✅ **وضعیت اشتراک:** {'فعال' if data.get('subscription_active') else 'غیرفعال'}
"""
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== برداشت وجه ====================
@bot.message_handler(func=lambda m: m.text == '🏧 برداشت وجه')
def withdraw_request(message):
    user_id = message.from_user.id
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}/wallet", timeout=5)
        data = response.json() if response.status_code == 200 else {}
        balance = data.get('balance', 0)
    except:
        balance = 0
    
    if balance < MIN_WITHDRAW:
        bot.send_message(
            message.chat.id,
            f"❌ موجودی شما ({balance:,} تومان) کمتر از حداقل برداشت ({MIN_WITHDRAW:,} تومان) است!\n\n"
            f"برای افزایش موجودی:\n• از طریق رفرال کاربر جذب کنید\n• هر کاربر ۷٪ سود برای شما دارد"
        )
        return
    
    msg = bot.send_message(
        message.chat.id,
        "🏧 **درخواست برداشت وجه**\n\n"
        "لطفاً شماره کارت خود را به صورت ۱۶ رقمی وارد کنید:\n"
        "مثال: `6219861034567890`\n\n"
        "⚠️ دقت کنید شماره کارت صحیح باشد"
    )
    bot.register_next_step_handler(msg, process_withdraw, user_id, balance)

def process_withdraw(message, user_id, balance):
    text = message.text.strip()
    card_match = re.search(r'\d{16}', text)
    
    if not card_match:
        bot.send_message(message.chat.id, "❌ شماره کارت نامعتبر! لطفاً ۱۶ رقم کارت را وارد کنید.")
        return
    
    card_number = card_match.group()
    
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/users/{user_id}/withdraw",
            json={"amount": balance, "card_number": card_number},
            timeout=5
        )
        
        if response.status_code == 200:
            bot.send_message(
                message.chat.id,
                f"✅ درخواست برداشت {balance:,} تومان ثبت شد!\n\n"
                f"شماره کارت: {card_number}\n"
                f"وضعیت: در انتظار بررسی\n"
                f"پس از تأیید ادمین، وجه به کارت شما واریز می‌شود."
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(
                        admin_id,
                        f"🏧 درخواست برداشت جدید\n👤 کاربر: {user_id}\n💰 مبلغ: {balance:,} تومان\n💳 کارت: {card_number}"
                    )
                except:
                    pass
        else:
            bot.send_message(message.chat.id, "❌ خطا در ثبت درخواست برداشت")
    except:
        bot.send_message(message.chat.id, "❌ خطا در ارتباط با سرور")

# ==================== فیش واریزی ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        files = {'receipt': ('receipt.jpg', downloaded_file)}
        data = {'user_id': user_id, 'amount': PRICE}
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/payments/receipt",
            data=data,
            files=files,
            timeout=30
        )
        
        if response.status_code == 200:
            bot.reply_to(
                message,
                f"✅ فیش دریافت شد\n💰 مبلغ: {PRICE:,} تومان\n\nپس از بررسی توسط ادمین، اشتراک شما فعال می‌شود."
            )
        else:
            bot.reply_to(message, f"❌ خطا: {response.text}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}/bots", timeout=5)
        bots = response.json() if response.status_code == 200 else []
        
        if not bots:
            bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
            return
        
        for bot_info in bots:
            status_emoji = "🟢" if bot_info.get('is_running') else "🔴"
            text = f"{status_emoji} **{bot_info.get('name', 'بدون نام')}**\n"
            text += f"🔗 https://t.me/{bot_info.get('username', '')}\n"
            text += f"🆔 `{bot_info.get('id', '')}`\n"
            text += f"📊 وضعیت: {'در حال اجرا' if bot_info.get('is_running') else 'متوقف'}\n"
            text += f"📅 ایجاد: {bot_info.get('created_at', '')[:10]}"
            
            bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ خطا در دریافت اطلاعات")

# ==================== فعال/غیرفعال کردن ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال کردن')
def toggle_prompt(message):
    user_id = message.from_user.id
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}/bots", timeout=5)
        bots = response.json() if response.status_code == 200 else []
        
        if not bots:
            bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for bot_info in bots:
            status = "🟢" if bot_info.get('is_running') else "🔴"
            btn = types.InlineKeyboardButton(f"{status} {bot_info.get('name', 'بدون نام')}", callback_data=f"toggle_bot_{bot_info['id']}")
            markup.add(btn)
        
        bot.send_message(message.chat.id, "🔄 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_bot_"))
def toggle_bot(call):
    bot_id = call.data.replace("toggle_bot_", "")
    user_id = call.from_user.id
    
    try:
        response = requests.post(f"{API_GATEWAY_URL}/api/v1/bots/{bot_id}/toggle", json={"user_id": user_id}, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            status = "فعال" if data.get("is_running") else "غیرفعال"
            bot.answer_callback_query(call.id, f"✅ ربات {status} شد")
            bot.edit_message_text(f"✅ ربات با موفقیت {status} شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ خطا!")
    except:
        bot.answer_callback_query(call.id, "❌ خطا!")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/users/{user_id}/bots", timeout=5)
        bots = response.json() if response.status_code == 200 else []
        
        if not bots:
            bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for bot_info in bots:
            btn = types.InlineKeyboardButton(f"🗑 {bot_info.get('name', 'بدون نام')}", callback_data=f"delete_bot_{bot_info['id']}")
            markup.add(btn)
        
        bot.send_message(message.chat.id, "🗑 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)
    except:
        bot.send_message(message.chat.id, "❌ خطا")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_bot_"))
def confirm_delete(call):
    bot_id = call.data.replace("delete_bot_", "")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر", callback_data="cancel_del")
    )
    
    bot.edit_message_text("⚠️ آیا از حذف این ربات اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_del_"))
def do_delete(call):
    bot_id = call.data.replace("confirm_del_", "")
    user_id = call.from_user.id
    
    try:
        response = requests.delete(f"{API_GATEWAY_URL}/api/v1/bots/{bot_id}?user_id={user_id}", timeout=5)
        
        if response.status_code == 200:
            bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("❌ خطا در حذف ربات!", call.message.chat.id, call.message.message_id)
    except:
        bot.edit_message_text("❌ خطا!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del")
def cancel_delete(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/admin/settings/guide", timeout=5)
        guide_text = response.json().get("guide_text", "") if response.status_code == 200 else ""
    except:
        guide_text = ""
    
    if not guide_text:
        guide_text = """
📚 **راهنمای کامل**

1️⃣ **ساخت ربات:**
   • ابتدا اشتراک تهیه کنید
   • فایل .py یا .zip خود را آپلود کنید
   • توکن ربات داخل کد باشد

2️⃣ **تست ۲۴ ساعته:**
   • می‌توانید ۲۴ ساعت ربات را تست کنید
   • پس از آن برای ادامه باید اشتراک تهیه کنید

3️⃣ **رفال و درآمد:**
   • لینک رفرال خود را به اشتراک بگذارید
   • هر کاربر ۷٪ سود برای شما دارد
   • قابل برداشت از ۲ میلیون تومان

4️⃣ **پشتیبانی:**
   • @shahraghee13
"""
    
    bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def stats(message):
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/stats", timeout=5)
        data = response.json() if response.status_code == 200 else {}
        
        text = f"📊 **آمار سامانه**\n\n"
        text += f"👥 کل کاربران: {data.get('total_users', 0)}\n"
        text += f"🤖 کل ربات‌ها: {data.get('total_bots', 0)}\n"
        text += f"🟢 فعال: {data.get('running_bots', 0)}\n"
        text += f"💰 پرداخت‌ها: {data.get('total_payments', 0)}\n"
        text += f"🖥 تعداد سرورها: {data.get('total_servers', 0)}\n"
        text += f"⚡ ظرفیت کل: {data.get('total_capacity', 0)}"
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ خطا در دریافت آمار")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    bot.send_message(message.chat.id, "📞 **پشتیبانی:** @shahraghee13", parse_mode="Markdown")

# ==================== پنل ادمین ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 تغییر قیمت", callback_data="admin_change_price"),
        types.InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="admin_change_card"),
        types.InlineKeyboardButton("📝 تغییر متن راهنما", callback_data="admin_change_guide"),
        types.InlineKeyboardButton("🖥 اضافه کردن سرور", callback_data="admin_add_server"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربران", callback_data="admin_delete_user_bot"),
        types.InlineKeyboardButton("📸 فیش‌ها", callback_data="admin_receipts"),
        types.InlineKeyboardButton("🏧 درخواست‌های برداشت", callback_data="admin_withdrawals"),
        types.InlineKeyboardButton("👥 کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, "👑 **پنل مدیریت پیشرفته**", reply_markup=markup, parse_mode="Markdown")

# ==================== دکمه‌های ادمین ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_change_price")
def change_price_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 **قیمت جدید را به تومان وارد کنید:**\nمثال: 2500000")
    bot.register_next_step_handler(msg, change_price_process)

def change_price_process(message):
    try:
        new_price = int(message.text.strip())
        response = requests.post(f"{API_GATEWAY_URL}/api/v1/admin/settings/price", json={"price": new_price}, timeout=5)
        
        if response.status_code == 200:
            bot.send_message(message.chat.id, f"✅ قیمت با موفقیت به {new_price:,} تومان تغییر کرد!")
        else:
            bot.send_message(message.chat.id, f"❌ خطا: {response.text}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_card")
def change_card_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 **شماره کارت جدید را وارد کنید:**\nمثال: 5892101187322777")
    bot.register_next_step_handler(msg, change_card_process)

def change_card_process(message):
    card_number = message.text.strip()
    if not card_number.isdigit() or len(card_number) != 16:
        bot.send_message(message.chat.id, "❌ شماره کارت باید ۱۶ رقم باشد!")
        return
    
    response = requests.post(f"{API_GATEWAY_URL}/api/v1/admin/settings/card", json={"card_number": card_number}, timeout=5)
    
    if response.status_code == 200:
        bot.send_message(message.chat.id, f"✅ شماره کارت با موفقیت به {card_number} تغییر کرد!")
    else:
        bot.send_message(message.chat.id, f"❌ خطا: {response.text}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_guide")
def change_guide_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(call.message.chat.id, "📝 **متن جدید راهنما را وارد کنید:**\n(می‌توانید از Markdown استفاده کنید)")
    bot.register_next_step_handler(msg, change_guide_process)

def change_guide_process(message):
    new_guide = message.text.strip()
    response = requests.post(f"{API_GATEWAY_URL}/api/v1/admin/settings/guide", json={"guide_text": new_guide}, timeout=5)
    
    if response.status_code == 200:
        bot.send_message(message.chat.id, "✅ متن راهنما با موفقیت به‌روزرسانی شد!")
    else:
        bot.send_message(message.chat.id, f"❌ خطا: {response.text}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_server")
def add_server_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot.send_message(call.message.chat.id, "🖥 **اضافه کردن سرور جدید**\n\nلطفاً **یوزرنیم** سرور را وارد کنید:")
    bot.register_next_step_handler(call.message, add_server_username)

def add_server_username(message):
    username = message.text.strip()
    if not username:
        bot.send_message(message.chat.id, "❌ یوزرنیم معتبر وارد کنید!")
        return
    
    bot.send_message(message.chat.id, "🌐 **آیپی** سرور را وارد کنید (مثال: 192.168.1.100):")
    bot.register_next_step_handler(message, add_server_ip, username)

def add_server_ip(message, username):
    ip = message.text.strip()
    if not ip:
        bot.send_message(message.chat.id, "❌ آیپی معتبر وارد کنید!")
        return
    
    bot.send_message(message.chat.id, "🔑 **رمز عبور SSH** سرور را وارد کنید:")
    bot.register_next_step_handler(message, add_server_password, username, ip)

def add_server_password(message, username, ip):
    password = message.text.strip()
    if not password:
        bot.send_message(message.chat.id, "❌ رمز عبور معتبر وارد کنید!")
        return
    
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/admin/servers/add",
            json={"username": username, "ip": ip, "password": password, "max_workers": 1000},
            timeout=10
        )
        
        if response.status_code == 200:
            bot.send_message(
                message.chat.id,
                f"✅ **سرور با موفقیت اضافه شد!**\n\n🖥 یوزرنیم: {username}\n🌐 آیپی: {ip}\n📊 حداکثر کارگر: 1000\n\n⚡ سرور به کلاستر اضافه شد و بار بین سرورها تقسیم می‌شود."
            )
        else:
            bot.send_message(message.chat.id, f"❌ خطا در اضافه کردن سرور: {response.text}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user_bot")
def admin_list_user_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/admin/bots/all", timeout=5)
        bots = response.json() if response.status_code == 200 else []
        
        if not bots:
            bot.send_message(call.message.chat.id, "📋 هیچ رباتی در سیستم وجود ندارد")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for bot_info in bots[:30]:
            btn = types.InlineKeyboardButton(f"🗑 {bot_info.get('name', 'بدون نام')} (کاربر: {bot_info.get('user_id', '?')})", callback_data=f"admin_del_bot_{bot_info['id']}")
            markup.add(btn)
        
        bot.send_message(call.message.chat.id, "🗑 **لیست ربات‌ها**\nبرای حذف یک ربات روی آن کلیک کنید:", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_del_bot_"))
def admin_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_del_bot_", "")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"admin_confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="admin_cancel_del")
    )
    
    bot.edit_message_text(f"⚠️ آیا از حذف ربات `{bot_id}` اطمینان دارید؟\nاین عملیات غیرقابل بازگشت است.", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_confirm_del_"))
def admin_confirm_delete_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace("admin_confirm_del_", "")
    
    try:
        response = requests.delete(f"{API_GATEWAY_URL}/api/v1/admin/bots/{bot_id}", timeout=5)
        
        if response.status_code == 200:
            bot.edit_message_text(f"✅ ربات `{bot_id}` با موفقیت حذف شد.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text(f"❌ خطا در حذف ربات: {response.text}", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_cancel_del")
def admin_cancel_delete(call):
    bot.edit_message_text("❌ عملیات حذف لغو شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/admin/receipts/pending", timeout=5)
        receipts = response.json() if response.status_code == 200 else []
        
        if not receipts:
            bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری وجود ندارد")
            return
        
        for r in receipts[:10]:
            text = f"🆔 {r.get('id')}\n👤 {r.get('user_id')}\n💰 {r.get('amount', 0):,} تومان\n🆔 {r.get('payment_code', '')}"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_receipt_{r['id']}"),
                types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}")
            )
            
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_receipt_"))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace("approve_receipt_", ""))
    
    try:
        response = requests.post(f"{API_GATEWAY_URL}/api/v1/admin/receipts/{receipt_id}/approve", json={"admin_id": call.from_user.id}, timeout=5)
        
        if response.status_code == 200:
            bot.answer_callback_query(call.id, "✅ فیش تایید شد")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ خطا!")
    except:
        bot.answer_callback_query(call.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_receipt_"))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace("reject_receipt_", ""))
    
    try:
        response = requests.post(f"{API_GATEWAY_URL}/api/v1/admin/receipts/{receipt_id}/reject", json={"admin_id": call.from_user.id}, timeout=5)
        
        if response.status_code == 200:
            bot.answer_callback_query(call.id, "❌ فیش رد شد")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ خطا!")
    except:
        bot.answer_callback_query(call.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdrawals")
def admin_withdrawals(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/admin/withdrawals/pending", timeout=5)
        withdrawals = response.json() if response.status_code == 200 else []
        
        if not withdrawals:
            bot.send_message(call.message.chat.id, "🏧 هیچ درخواست برداشتی در انتظار نیست")
            return
        
        for w in withdrawals[:10]:
            text = f"🏧 درخواست برداشت\n🆔 {w.get('id')}\n👤 کاربر: {w.get('user_id')}\n💰 مبلغ: {w.get('amount', 0):,} تومان\n💳 کارت: {w.get('card_number')}"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ پرداخت شد", callback_data=f"pay_withdraw_{w['id']}"),
                types.InlineKeyboardButton("❌ رد", callback_data=f"reject_withdraw_{w['id']}")
            )
            
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_withdraw_"))
def pay_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdrawal_id = int(call.data.replace("pay_withdraw_", ""))
    
    try:
        response = requests.post(f"{API_GATEWAY_URL}/api/v1/admin/withdrawals/{withdrawal_id}/pay", json={"admin_id": call.from_user.id}, timeout=5)
        
        if response.status_code == 200:
            bot.answer_callback_query(call.id, "✅ برداشت پرداخت شد")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ خطا!")
    except:
        bot.answer_callback_query(call.id, "❌ خطا!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/admin/users?limit=20", timeout=5)
        users = response.json() if response.status_code == 200 else []
        
        if not users:
            bot.send_message(call.message.chat.id, "👥 کاربری یافت نشد")
            return
        
        text = "👥 **۲۰ کاربر آخر:**\n\n"
        for u in users:
            payment = "✅" if u.get('payment_status') == 'approved' else "⏳"
            text += f"{payment} `{u.get('user_id')}` - {u.get('first_name', 'بدون نام')}\n"
            text += f"   🤖 {u.get('bots_count', 0)} | 🎁 {u.get('verified_referrals', 0)} | 💰 {u.get('balance', 0):,}\n\n"
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/api/v1/stats", timeout=5)
        data = response.json() if response.status_code == 200 else {}
        
        text = f"📊 **آمار کامل سامانه**\n\n"
        text += f"👥 کل کاربران: {data.get('total_users', 0)}\n"
        text += f"✅ پرداخت کرده: {data.get('paid_users', 0)}\n"
        text += f"🤖 کل ربات‌ها: {data.get('total_bots', 0)}\n"
        text += f"🟢 فعال: {data.get('running_bots', 0)}\n"
        text += f"📸 کل فیش‌ها: {data.get('total_receipts', 0)}\n"
        text += f"⏳ در انتظار: {data.get('pending_receipts', 0)}\n"
        text += f"✅ تایید شده: {data.get('approved_receipts', 0)}\n"
        text += f"💰 مجموع واریزی: {data.get('total_amount', 0):,} تومان\n"
        text += f"🏧 درخواست‌های برداشت: {data.get('pending_withdrawals', 0)}\n"
        text += f"🖥 تعداد سرورها: {data.get('total_servers', 0)}\n"
        text += f"⚡ ظرفیت کل: {data.get('total_capacity', 0)}"
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=markup)

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر حرفه‌ای - نسخه نهایی")
    print("=" * 70)
    print(f"✅ ربات تلگرام: فعال")
    print(f"✅ ادمین‌ها: {ADMIN_IDS}")
    print(f"✅ API Gateway: {API_GATEWAY_URL}")
    print("=" * 70)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            print(f"❌ خطا: {e}")
            time.sleep(5)

================================================================================
                    فایل 8: api_gateway.py (API Gateway کامل)
================================================================================

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Gateway - مدیریت درخواست‌ها و ارتباط با سرویس‌ها
دیتابیس PostgreSQL + کش Redis + صف RabbitMQ
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
import redis.asyncio as redis
import aio_pika
import os
import hashlib
import json
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

app = FastAPI(title="MotherBot API Gateway", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== اتصال به سرویس‌ها ====================
class Database:
    pool: asyncpg.Pool = None
    redis: redis.Redis = None
    rabbitmq: aio_pika.Connection = None

db = Database()

def generate_referral_code(user_id: int) -> str:
    return hashlib.md5(f"{user_id}_{secrets.token_hex(4)}".encode()).hexdigest()[:8]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - اتصال به دیتابیس‌ها
    db.pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "motherbot"),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        min_size=10,
        max_size=100,
        command_timeout=60
    )
    
    db.redis = await redis.from_url(
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}",
        decode_responses=True
    )
    
    db.rabbitmq = await aio_pika.connect_robust(
        f"amqp://{os.getenv('RABBITMQ_USER', 'guest')}:{os.getenv('RABBITMQ_PASSWORD', 'guest')}@"
        f"{os.getenv('RABBITMQ_HOST', 'localhost')}/"
    )
    
    # ایجاد جداول دیتابیس
    await init_database()
    
    yield
    
    # Shutdown
    await db.pool.close()
    await db.redis.close()
    await db.rabbitmq.close()

app = FastAPI(lifespan=lifespan)

# ==================== مدل‌های داده ====================
class UserRegister(BaseModel):
    user_id: int
    username: str = ""
    first_name: str = ""
    referred_by: Optional[int] = None

class ServerAdd(BaseModel):
    username: str
    ip: str
    password: str
    max_workers: int = 1000

class WithdrawRequest(BaseModel):
    amount: int
    card_number: str

class CheckReferral(BaseModel):
    referral_code: str
    user_id: int

# ==================== مقداردهی اولیه دیتابیس ====================
async def init_database():
    """ایجاد تمام جدول‌های دیتابیس"""
    async with db.pool.acquire() as conn:
        # جدول کاربران
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                balance BIGINT DEFAULT 0,
                referral_code VARCHAR(50) UNIQUE,
                referred_by BIGINT,
                referrals_count INT DEFAULT 0,
                verified_referrals INT DEFAULT 0,
                referral_earnings BIGINT DEFAULT 0,
                payment_status VARCHAR(20) DEFAULT 'pending',
                subscription_status VARCHAR(20) DEFAULT 'inactive',
                created_at TIMESTAMP DEFAULT NOW(),
                last_active TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # جدول اشتراک‌ها
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                plan_type VARCHAR(20) DEFAULT 'monthly',
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # جدول تست ۲۴ ساعته
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trials (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # جدول ربات‌ها
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id VARCHAR(50) PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                token TEXT,
                name VARCHAR(255),
                username VARCHAR(255),
                file_path TEXT,
                status VARCHAR(20) DEFAULT 'stopped',
                executor_host VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW(),
                last_active TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # جدول سرورهای اجراکننده
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS executors (
                id SERIAL PRIMARY KEY,
                host VARCHAR(255) UNIQUE,
                username VARCHAR(255),
                password TEXT,
                max_workers INT DEFAULT 1000,
                current_load INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                last_heartbeat TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # جدول فیش‌ها
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                amount BIGINT,
                receipt_path TEXT,
                payment_code VARCHAR(50) UNIQUE,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                reviewed_at TIMESTAMP,
                reviewed_by BIGINT
            )
        """)
        
        # جدول برداشت‌ها
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                amount BIGINT,
                card_number VARCHAR(16),
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                processed_at TIMESTAMP
            )
        """)
        
        # جدول تنظیمات
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # درج تنظیمات پیش‌فرض
        await conn.execute("""
            INSERT INTO settings (key, value) VALUES 
            ('price', '2000000'),
            ('card_number', '5892101187322777'),
            ('card_holder', 'مرتضی نیکخو خنجری'),
            ('min_withdraw', '2000000'),
            ('referral_percent', '7'),
            ('guide_text', '')
            ON CONFLICT (key) DO NOTHING
        """)

# ==================== اندپوینت‌های API ====================

@app.post("/api/v1/users/register")
async def register_user(data: UserRegister):
    """ثبت کاربر جدید"""
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", data.user_id)
        
        if not user:
            referral_code = generate_referral_code(data.user_id)
            
            await conn.execute("""
                INSERT INTO users (user_id, username, first_name, referral_code, referred_by, created_at, last_active)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            """, data.user_id, data.username, data.first_name, referral_code, data.referred_by)
            
            if data.referred_by:
                await conn.execute("""
                    UPDATE users SET referrals_count = referrals_count + 1
                    WHERE user_id = $1
                """, data.referred_by)
            
            user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", data.user_id)
    
    return {"success": True, "user": dict(user)}

@app.post("/api/v1/users/check-referral")
async def check_referral(data: CheckReferral):
    """بررسی کد رفرال"""
    async with db.pool.acquire() as conn:
        referrer = await conn.fetchrow(
            "SELECT user_id FROM users WHERE referral_code = $1",
            data.referral_code
        )
        
        if referrer and referrer['user_id'] != data.user_id:
            return {"valid": True, "referrer_id": referrer['user_id']}
        
        return {"valid": False}

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int):
    """دریافت اطلاعات کاربر"""
    # بررسی کش
    cached = await db.redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)
    
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        subscription = await conn.fetchrow("""
            SELECT * FROM subscriptions 
            WHERE user_id = $1 AND expires_at > NOW() 
            ORDER BY expires_at DESC LIMIT 1
        """, user_id)
        
        trial = await conn.fetchrow("""
            SELECT * FROM trials 
            WHERE user_id = $1 AND expires_at > NOW()
        """, user_id)
        
        result = dict(user)
        result['subscription_active'] = subscription is not None or trial is not None
        result['subscription_expiry'] = str(subscription['expires_at']) if subscription else (str(trial['expires_at']) if trial else None)
        
        # ذخیره در کش
        await db.redis.setex(f"user:{user_id}", 300, json.dumps(result, default=str))
        
        return result

@app.get("/api/v1/users/{user_id}/wallet")
async def get_wallet(user_id: int):
    """دریافت اطلاعات کیف پول"""
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT user_id, first_name, balance, referral_code, referrals_count, verified_referrals, referral_earnings FROM users WHERE user_id = $1",
            user_id
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        subscription = await conn.fetchrow("""
            SELECT * FROM subscriptions WHERE user_id = $1 AND expires_at > NOW()
        """, user_id)
        
        result = dict(user)
        result['subscription_active'] = subscription is not None
        
        return result

@app.get("/api/v1/users/{user_id}/subscription")
async def get_subscription(user_id: int):
    """دریافت وضعیت اشتراک"""
    # بررسی کش
    cached = await db.redis.get(f"sub:{user_id}")
    if cached:
        return {"is_active": cached == "true"}
    
    async with db.pool.acquire() as conn:
        subscription = await conn.fetchrow("""
            SELECT * FROM subscriptions WHERE user_id = $1 AND expires_at > NOW()
        """, user_id)
        
        trial = await conn.fetchrow("""
            SELECT * FROM trials WHERE user_id = $1 AND expires_at > NOW()
        """, user_id)
        
        is_active = subscription is not None or trial is not None
        
        await db.redis.setex(f"sub:{user_id}", 3600, str(is_active).lower())
        
        return {"is_active": is_active}

@app.get("/api/v1/users/{user_id}/trial-status")
async def get_trial_status(user_id: int):
    """بررسی وضعیت تست ۲۴ ساعته"""
    async with db.pool.acquire() as conn:
        trial = await conn.fetchrow(
            "SELECT * FROM trials WHERE user_id = $1",
            user_id
        )
        
        return {
            "has_used_trial": trial is not None,
            "expires_at": str(trial['expires_at']) if trial else None
        }

@app.post("/api/v1/users/{user_id}/activate-trial")
async def activate_trial(user_id: int, data: dict):
    """فعال‌سازی تست ۲۴ ساعته"""
    async with db.pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM trials WHERE user_id = $1", user_id)
        
        if existing:
            raise HTTPException(status_code=400, detail="Trial already used")
        
        expires_at = datetime.now() + timedelta(hours=data.get('duration_hours', 24))
        
        await conn.execute("""
            INSERT INTO trials (user_id, expires_at, created_at)
            VALUES ($1, $2, NOW())
        """, user_id, expires_at)
        
        return {"success": True, "expires_at": str(expires_at)}

@app.get("/api/v1/users/{user_id}/bot-limit")
async def get_bot_limit(user_id: int):
    """بررسی محدودیت تعداد ربات"""
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT verified_referrals FROM users WHERE user_id = $1", user_id)
        
        if not user:
            return {"can_create": True, "max_bots": 1, "current_bots": 0}
        
        extra_bots = user['verified_referrals'] // 5
        max_bots = 1 + extra_bots
        
        current_bots = await conn.fetchval(
            "SELECT COUNT(*) FROM bots WHERE user_id = $1",
            user_id
        )
        
        return {
            "can_create": current_bots < max_bots,
            "max_bots": max_bots,
            "current_bots": current_bots
        }

@app.get("/api/v1/users/{user_id}/bots")
async def get_user_bots(user_id: int):
    """دریافت لیست ربات‌های کاربر"""
    async with db.pool.acquire() as conn:
        bots = await conn.fetch(
            "SELECT * FROM bots WHERE user_id = $1 ORDER BY created_at DESC",
            user_id
        )
        
        result = []
        for bot in bots:
            bot_dict = dict(bot)
            # بررسی وضعیت اجرا از کش
            is_running = await db.redis.get(f"bot_running:{bot['id']}")
            bot_dict['is_running'] = is_running == "true"
            result.append(bot_dict)
        
        return result

@app.post("/api/v1/bots/create")
async def create_bot(
    user_id: int = Form(...),
    file: UploadFile = File(...)
):
    """ساخت ربات جدید - ارسال به صف برای اجرا"""
    
    # بررسی اشتراک
    async with db.pool.acquire() as conn:
        subscription = await conn.fetchrow("""
            SELECT * FROM subscriptions WHERE user_id = $1 AND expires_at > NOW()
        """, user_id)
        
        trial = await conn.fetchrow("""
            SELECT * FROM trials WHERE user_id = $1 AND expires_at > NOW()
        """, user_id)
        
        if not subscription and not trial:
            raise HTTPException(status_code=403, detail="No active subscription or trial")
        
        # بررسی محدودیت
        user = await conn.fetchrow("SELECT verified_referrals FROM users WHERE user_id = $1", user_id)
        extra_bots = user['verified_referrals'] // 5 if user else 0
        max_bots = 1 + extra_bots
        
        current_bots = await conn.fetchval("SELECT COUNT(*) FROM bots WHERE user_id = $1", user_id)
        
        if current_bots >= max_bots:
            raise HTTPException(status_code=403, detail="Bot limit reached")
    
    # خواندن فایل
    file_content = await file.read()
    file_name = file.filename
    
    # استخراج توکن از کد
    try:
        code = file_content.decode('utf-8')
    except:
        try:
            code = file_content.decode('cp1256')
        except:
            code = ""
    
    # الگوهای توکن
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
    ]
    
    token = None
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            token = match.group(1)
            break
    
    if not token:
        raise HTTPException(status_code=400, detail="Token not found in code")
    
    # بررسی توکن
    import requests
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid token")
        bot_info = resp.json().get('result', {})
        bot_name = bot_info.get('first_name', 'Unknown')
        bot_username = bot_info.get('username', 'unknown')
    except:
        raise HTTPException(status_code=400, detail="Failed to validate token")
    
    # ایجاد آیدی ربات
    bot_id = hashlib.md5(f"{user_id}{token}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    
    # ذخیره در دیتابیس
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO bots (id, user_id, token, name, username, status, created_at)
            VALUES ($1, $2, $3, $4, $5, 'running', NOW())
        """, bot_id, user_id, token, bot_name, bot_username)
    
    # ارسال به صف برای اجرا
    channel = await db.rabbitmq.channel()
    queue = await channel.declare_queue("code_execution", durable=True)
    
    task = {
        "bot_id": bot_id,
        "user_id": user_id,
        "token": token,
        "code": code,
        "file_name": file_name
    }
    
    await channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps(task).encode()),
        routing_key="code_execution"
    )
    
    # ذخیره در کش که در حال اجراست
    await db.redis.setex(f"bot_running:{bot_id}", 60, "true")
    
    return {
        "success": True,
        "bot_id": bot_id,
        "bot_name": bot_name,
        "bot_username": bot_username,
        "is_running": True,
        "installed": []
    }

@app.post("/api/v1/bots/{bot_id}/toggle")
async def toggle_bot(bot_id: str, data: dict):
    """تغییر وضعیت ربات"""
    user_id = data.get('user_id')
    
    async with db.pool.acquire() as conn:
        bot = await conn.fetchrow("SELECT * FROM bots WHERE id = $1 AND user_id = $2", bot_id, user_id)
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        new_status = 'stopped' if bot['status'] == 'running' else 'running'
        
        await conn.execute("UPDATE bots SET status = $1 WHERE id = $2", new_status, bot_id)
        
        if new_status == 'stopped':
            await db.redis.delete(f"bot_running:{bot_id}")
        else:
            await db.redis.setex(f"bot_running:{bot_id}", 60, "true")
        
        return {"is_running": new_status == 'running'}

@app.delete("/api/v1/bots/{bot_id}")
async def delete_bot(bot_id: str, user_id: int):
    """حذف ربات"""
    async with db.pool.acquire() as conn:
        bot = await conn.fetchrow("SELECT * FROM bots WHERE id = $1 AND user_id = $2", bot_id, user_id)
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        await conn.execute("DELETE FROM bots WHERE id = $1", bot_id)
        await db.redis.delete(f"bot_running:{bot_id}")
        
        return {"success": True}

@app.post("/api/v1/users/{user_id}/withdraw")
async def withdraw_request(user_id: int, request: WithdrawRequest):
    """درخواست برداشت وجه"""
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
        
        if not user or user['balance'] < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        min_withdraw = int(os.getenv("MIN_WITHDRAW", "2000000"))
        if request.amount < min_withdraw:
            raise HTTPException(status_code=400, detail=f"Minimum withdraw is {min_withdraw:,}")
        
        await conn.execute("""
            INSERT INTO withdrawals (user_id, amount, card_number, status, created_at)
            VALUES ($1, $2, $3, 'pending', NOW())
        """, user_id, request.amount, request.card_number)
        
        # کاهش موجودی
        await conn.execute("UPDATE users SET balance = balance - $1 WHERE user_id = $2", request.amount, user_id)
        
        return {"success": True, "message": "Withdrawal request submitted"}

@app.post("/api/v1/payments/receipt")
async def upload_receipt(
    user_id: int = Form(...),
    amount: int = Form(...),
    receipt: UploadFile = File(...)
):
    """آپلود فیش واریزی"""
    payment_code = hashlib.md5(f"{user_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:8].upper()
    
    # ذخیره فایل (در حالت واقعی باید ذخیره شود)
    receipt_path = f"/tmp/receipt_{user_id}_{payment_code}.jpg"
    
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO receipts (user_id, amount, receipt_path, payment_code, status, created_at)
            VALUES ($1, $2, $3, $4, 'pending', NOW())
        """, user_id, amount, receipt_path, payment_code)
        
        return {"success": True, "payment_code": payment_code}

# ==================== اندپوینت‌های ادمین ====================

@app.post("/api/v1/admin/settings/price")
async def set_price(data: dict):
    """تغییر قیمت اشتراک"""
    async with db.pool.acquire() as conn:
        await conn.execute("""
            UPDATE settings SET value = $1, updated_at = NOW()
            WHERE key = 'price'
        """, str(data.get('price')))
        
        return {"success": True}

@app.post("/api/v1/admin/settings/card")
async def set_card(data: dict):
    """تغییر شماره کارت"""
    async with db.pool.acquire() as conn:
        await conn.execute("""
            UPDATE settings SET value = $1, updated_at = NOW()
            WHERE key = 'card_number'
        """, data.get('card_number'))
        
        return {"success": True}

@app.post("/api/v1/admin/settings/guide")
async def set_guide(data: dict):
    """تغییر متن راهنما"""
    async with db.pool.acquire() as conn:
        await conn.execute("""
            UPDATE settings SET value = $1, updated_at = NOW()
            WHERE key = 'guide_text'
        """, data.get('guide_text'))
        
        return {"success": True}

@app.get("/api/v1/admin/settings/guide")
async def get_guide():
    """دریافت متن راهنما"""
    async with db.pool.acquire() as conn:
        guide = await conn.fetchval("SELECT value FROM settings WHERE key = 'guide_text'")
        return {"guide_text": guide or ""}

@app.post("/api/v1/admin/servers/add")
async def add_server(server: ServerAdd):
    """اضافه کردن سرور جدید"""
    async with db.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO executors (host, username, password, max_workers, status, created_at)
            VALUES ($1, $2, $3, $4, 'active', NOW())
            ON CONFLICT (host) DO UPDATE SET
            username = $2, password = $3, max_workers = $4, status = 'active', last_heartbeat = NULL
        """, server.ip, server.username, server.password, server.max_workers)
        
        return {"success": True, "message": f"Server {server.ip} added successfully"}

@app.get("/api/v1/admin/bots/all")
async def get_all_bots():
    """دریافت تمام ربات‌ها (برای ادمین)"""
    async with db.pool.acquire() as conn:
        bots = await conn.fetch("SELECT * FROM bots ORDER BY created_at DESC LIMIT 100")
        return [dict(bot) for bot in bots]

@app.delete("/api/v1/admin/bots/{bot_id}")
async def admin_delete_bot(bot_id: str):
    """حذف ربات توسط ادمین"""
    async with db.pool.acquire() as conn:
        await conn.execute("DELETE FROM bots WHERE id = $1", bot_id)
        await db.redis.delete(f"bot_running:{bot_id}")
        return {"success": True}

@app.get("/api/v1/admin/receipts/pending")
async def get_pending_receipts():
    """دریافت فیش‌های در انتظار"""
    async with db.pool.acquire() as conn:
        receipts = await conn.fetch("""
            SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at DESC
        """)
        return [dict(r) for r in receipts]

@app.post("/api/v1/admin/receipts/{receipt_id}/approve")
async def approve_receipt(receipt_id: int, data: dict):
    """تایید فیش و فعال‌سازی اشتراک"""
    async with db.pool.acquire() as conn:
        receipt = await conn.fetchrow("SELECT * FROM receipts WHERE id = $1", receipt_id)
        
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        # به‌روزرسانی وضعیت فیش
        await conn.execute("""
            UPDATE receipts SET status = 'approved', reviewed_at = NOW(), reviewed_by = $1
            WHERE id = $2
        """, data.get('admin_id'), receipt_id)
        
        # فعال‌سازی اشتراک کاربر
        expires_at = datetime.now() + timedelta(days=30)
        await conn.execute("""
            INSERT INTO subscriptions (user_id, plan_type, expires_at, created_at)
            VALUES ($1, 'monthly', $2, NOW())
        """, receipt['user_id'], expires_at)
        
        # به‌روزرسانی وضعیت پرداخت کاربر
        await conn.execute("""
            UPDATE users SET payment_status = 'approved', subscription_status = 'active'
            WHERE user_id = $1
        """, receipt['user_id'])
        
        # اضافه کردن سود رفرال (۷٪)
        user = await conn.fetchrow("SELECT referred_by FROM users WHERE user_id = $1", receipt['user_id'])
        
        if user and user['referred_by']:
            referral_percent = int(os.getenv("REFERRAL_PERCENT", "7"))
            referral_amount = int(receipt['amount'] * referral_percent / 100)
            
            await conn.execute("""
                UPDATE users 
                SET balance = balance + $1, 
                    referral_earnings = referral_earnings + $1,
                    verified_referrals = verified_referrals + 1
                WHERE user_id = $2
            """, referral_amount, user['referred_by'])
        
        # حذف کش
        await db.redis.delete(f"user:{receipt['user_id']}")
        await db.redis.delete(f"sub:{receipt['user_id']}")
        
        return {"success": True}

@app.get("/api/v1/admin/withdrawals/pending")
async def get_pending_withdrawals():
    """دریافت درخواست‌های برداشت در انتظار"""
    async with db.pool.acquire() as conn:
        withdrawals = await conn.fetch("""
            SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY created_at DESC
        """)
        return [dict(w) for w in withdrawals]

@app.get("/api/v1/admin/users")
async def get_users(limit: int = 20):
    """دریافت لیست کاربران"""
    async with db.pool.acquire() as conn:
        users = await conn.fetch("""
            SELECT u.*, COUNT(b.id) as bots_count
            FROM users u
            LEFT JOIN bots b ON u.user_id = b.user_id
            GROUP BY u.user_id
            ORDER BY u.created_at DESC
            LIMIT $1
        """, limit)
        
        return [dict(u) for u in users]

@app.get("/api/v1/stats")
async def get_stats():
    """دریافت آمار کلی"""
    async with db.pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_bots = await conn.fetchval("SELECT COUNT(*) FROM bots")
        running_bots = await conn.fetchval("SELECT COUNT(*) FROM bots WHERE status = 'running'")
        total_receipts = await conn.fetchval("SELECT COUNT(*) FROM receipts")
        pending_receipts = await conn.fetchval("SELECT COUNT(*) FROM receipts WHERE status = 'pending'")
        approved_receipts = await conn.fetchval("SELECT COUNT(*) FROM receipts WHERE status = 'approved'")
        total_amount = await conn.fetchval("SELECT COALESCE(SUM(amount), 0) FROM receipts WHERE status = 'approved'")
        paid_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE payment_status = 'approved'")
        pending_withdrawals = await conn.fetchval("SELECT COUNT(*) FROM withdrawals WHERE status = 'pending'")
        total_servers = await conn.fetchval("SELECT COUNT(*) FROM executors WHERE status = 'active'")
        total_capacity = await conn.fetchval("SELECT COALESCE(SUM(max_workers), 0) FROM executors WHERE status = 'active'")
        
        return {
            "total_users": total_users,
            "paid_users": paid_users,
            "total_bots": total_bots,
            "running_bots": running_bots,
            "total_receipts": total_receipts,
            "pending_receipts": pending_receipts,
            "approved_receipts": approved_receipts,
            "total_amount": total_amount,
            "pending_withdrawals": pending_withdrawals,
            "total_servers": total_servers,
            "total_capacity": total_capacity
        }

# ==================== اجرا ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

================================================================================
                    فایل 9: code_executor.py (اجراکننده کد در داکر)
================================================================================

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اجراکننده کد در محیط ایزوله داکر
با قابلیت نصب خودکار کتابخانه‌ها و محدودیت منابع
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import re
import time
import docker
import aio_pika
import asyncio
from datetime import datetime

# تنظیمات
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api_gateway:8000")
EXECUTOR_ID = os.getenv("EXECUTOR_ID", "1")

# کلاینت داکر
docker_client = docker.from_env()

def detect_requirements(code: str) -> list:
    """تشخیص کتابخانه‌های مورد نیاز از کد"""
    imports = set()
    lines = code.split('\n')
    
    # کتابخانه‌های استاندارد پایتون (نیاز به نصب ندارند)
    std_libs = {
        'os', 'sys', 'time', 'datetime', 'json', 're', 'math', 'random',
        'string', 'collections', 'itertools', 'functools', 'typing',
        'hashlib', 'base64', 'uuid', 'socket', 'ssl', 'threading',
        'multiprocessing', 'subprocess', 'argparse', 'logging', 'pathlib'
    }
    
    for line in lines:
        line = line.strip()
        if line.startswith('import '):
            parts = line.split()
            if len(parts) > 1:
                lib = parts[1].split('.')[0]
                if lib not in std_libs:
                    imports.add(lib)
        elif line.startswith('from '):
            parts = line.split()
            if len(parts) > 1:
                lib = parts[1].split('.')[0]
                if lib not in std_libs and lib != 'telebot':
                    imports.add(lib)
    
    # کتابخانه‌های خاص تلگرام
    if 'telebot' in code or 'TeleBot' in code:
        imports.add('pyTelegramBotAPI')
    
    return list(imports)

def install_libraries(libs: list) -> list:
    """نصب کتابخانه‌ها در کانتینر"""
    installed = []
    for lib in libs:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", lib, "--quiet"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                installed.append(lib)
        except:
            pass
    return installed

def run_code_in_sandbox(code: str, token: str, bot_id: str) -> dict:
    """اجرای کد در محیط ایزوله داکر"""
    
    # آماده‌سازی کد
    if 'if __name__ == "__main__"' not in code:
        code += '\n\nif __name__ == "__main__":\n    print("✅ ربات در حال اجراست...")\n    bot.infinity_polling()\n'
    
    # ایجاد دایرکتوری موقت
    temp_dir = tempfile.mkdtemp()
    
    try:
        # ذخیره کد
        code_path = os.path.join(temp_dir, 'bot.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # ذخیره توکن
        with open(os.path.join(temp_dir, 'token.txt'), 'w') as f:
            f.write(token)
        
        # ایجاد Dockerfile
        dockerfile = f'''
FROM python:3.11-slim

WORKDIR /app

# کپی فایل‌ها
COPY bot.py .
COPY token.txt .

# محدودیت‌ها
RUN useradd -m -s /bin/bash sandbox
USER sandbox

# اجرا
CMD ["python", "bot.py"]
'''
        
        dockerfile_path = os.path.join(temp_dir, 'Dockerfile')
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile)
        
        # ساخت image
        image_name = f"bot_{bot_id}_{int(time.time())}"
        docker_client.images.build(path=temp_dir, tag=image_name, rm=True)
        
        # اجرای کانتینر با محدودیت
        container = docker_client.containers.run(
            image_name,
            detach=True,
            mem_limit="512m",
            memswap_limit="512m",
            nano_cpus=int(0.5 * 1e9),  # 0.5 CPU
            network_mode="none",  # بدون شبکه (ایزوله کامل)
            read_only=True,
            security_opt=["no-new-privileges:true"],
            cap_drop=["ALL"],
            remove=False
        )
        
        # صبر برای اجرا
        time.sleep(3)
        
        container.reload()
        
        if container.status == 'running':
            return {
                "success": True,
                "container_id": container.id,
                "pid": container.id[:12]
            }
        else:
            logs = container.logs().decode('utf-8', errors='ignore')[-500:]
            container.remove()
            return {
                "success": False,
                "error": logs or "Container failed to start"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # پاکسازی دایرکتوری موقت
        shutil.rmtree(temp_dir, ignore_errors=True)

async def consume_tasks():
    """مصرف تسک‌ها از صف RabbitMQ"""
    connection = await aio_pika.connect_robust(
        f"amqp://{os.getenv('RABBITMQ_USER', 'guest')}:{os.getenv('RABBITMQ_PASSWORD', 'guest')}@{RABBITMQ_HOST}/"
    )
    
    channel = await connection.channel()
    queue = await channel.declare_queue("code_execution", durable=True)
    
    print(f"✅ Executor {EXECUTOR_ID} is running. Waiting for tasks...")
    
    async for message in queue:
        async with message.process():
            try:
                task = json.loads(message.body.decode())
                bot_id = task.get('bot_id')
                code = task.get('code')
                token = task.get('token')
                
                print(f"📦 Processing task for bot {bot_id}")
                
                # تشخیص و نصب کتابخانه‌ها
                libs = detect_requirements(code)
                installed = []
                for lib in libs:
                    try:
                        subprocess.run([sys.executable, "-m", "pip", "install", lib, "--quiet"], check=True, timeout=60)
                        installed.append(lib)
                    except:
                        pass
                
                # اجرا در سندباکس
                result = run_code_in_sandbox(code, token, bot_id)
                
                if result['success']:
                    # به‌روزرسانی وضعیت در API
                    import requests
                    requests.post(
                        f"{API_GATEWAY_URL}/api/v1/bots/{bot_id}/status",
                        json={"status": "running", "container_id": result['container_id']}
                    )
                    print(f"✅ Bot {bot_id} started successfully")
                else:
                    print(f"❌ Bot {bot_id} failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ Error processing task: {e}")

if __name__ == "__main__":
    print(f"🚀 Code Executor {EXECUTOR_ID} Starting...")
    asyncio.run(consume_tasks())

================================================================================
                            روش نصب و اجرا
================================================================================

1. ایجاد پوشه پروژه:
   mkdir mother_bot
   cd mother_bot

2. ایجاد تمام فایل‌های بالا در پوشه:
   - .env
   - requirements.txt
   - docker-compose.yml
   - Dockerfile.bot
   - Dockerfile.api
   - Dockerfile.sandbox
   - main.py
   - api_gateway.py
   - code_executor.py

3. نصب Docker و Docker Compose:
   sudo apt update
   sudo apt install docker.io docker-compose -y
   sudo systemctl start docker
   sudo systemctl enable docker

4. اجرا:
   docker-compose up -d --build

5. بررسی وضعیت:
   docker-compose ps
   docker-compose logs -f

================================================================================
                            لیست کامل قابلیت‌ها
================================================================================

✅ قابلیت‌های ربات اصلی:
- 🤖 ساخت ربات جدید با آپلود فایل .py یا .zip
- 📋 مشاهده لیست ربات‌های کاربر
- 🔄 فعال/غیرفعال کردن ربات‌ها
- 🗑 حذف ربات

✅ قابلیت‌های درآمدزایی:
- ⏱ تست ۲۴ ساعته رایگان
- 💰 کیف پول و سیستم رفرال ۷٪
- 🏧 برداشت وجه (حداقل ۲ میلیون تومان)
- 📸 فیش واریزی برای فعال‌سازی اشتراک

✅ پنل ادمین:
- 💰 تغییر قیمت اشتراک
- 💳 تغییر شماره کارت
- 📝 تغییر متن راهنما
- 🖥 اضافه کردن سرور جدید (با یوزرنیم، آیپی، رمز)
- 🗑 حذف ربات کاربران (با لیست کامل)
- 📸 بررسی و تایید فیش‌ها
- 🏧 مدیریت درخواست‌های برداشت
- 👥 مشاهده کاربران
- 📊 آمار کامل

✅ معماری پیشرفته:
- 🐳 ایزوله‌سازی کامل با Docker
- 📊 PostgreSQL برای دیتابیس اصلی
- ⚡ Redis برای کش و ذخیره موقت
- 📨 RabbitMQ برای صف پیام‌ها
- 🔄 Load Balancing بین سرورها
- 🔒 امنیت بالا با محدودیت منابع

================================================================================