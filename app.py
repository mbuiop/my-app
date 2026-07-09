# ============================================================
# ربات قرعه‌کشی هوشمند UTYOB - نسخه نهایی با دانلودر اینستاگرام و یوتیوب
# ============================================================

import asyncio
import logging
import random
import json
import sqlite3
import hashlib
import base58
import aiohttp
import threading
import time
import os
import sys
import re
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# کتابخانه‌های دانلودر
try:
    import yt_dlp
except ImportError:
    yt_dlp = None
try:
    from instaloader import Instaloader, Post
except ImportError:
    Instaloader = None
    Post = None

# ============================================================
# تنظیمات اولیه
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = [int(id) for id in os.environ.get('ADMIN_IDS', '123456789').split(',')]

TRONGRID_APIS = [
    "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
]

DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PAYMENT_AMOUNT = 100

DB_SHARDS = 500
CACHE_TTL = 300

# ============================================================
# سیستم چندزبانه کامل با دکمه‌های جدید
# ============================================================
class LanguageManager:
    LANGUAGES = {
        'en': {
            'name': 'English',
            'emoji': '🇬🇧',
            'welcome': "🎮 **Welcome to UTYOB Lottery Bot!**\n\n💰 Win amazing prizes up to $10,000!\n🎯 Fair and transparent lottery system\n🌟 Join now and test your luck!\n\nClick PLAY to enter the game.",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **UTYOB Lottery Bot**\n\nSelect an option below:\n👇👇👇",
            'lottery': "🎰 Join Lottery",
            'referral': "🔗 Referral",
            'guide': "📖 Guide",
            'language': "🌐 Change Language",
            'admin_panel': "⚙️ Admin Panel",
            'no_subscription': "❌ **You don't have an active subscription!**\n\nTo participate in the lottery, you must first purchase a subscription.\n\n💰 Subscription cost: $100\n📅 Validity: 1 month\n\nClick the button below to subscribe.",
            'subscribe': "🔄 Subscribe Now",
            'back': "🔙 Back",
            'main_menu_btn': "🔙 Main Menu",
            'lottery_back': "🎰 Back to Lottery",
            
            'subscribe_wallet': "💳 **Subscribe to UTYOB Lottery**\n\nPlease enter your source TRC20 wallet address:\n\n🔹 **Subscription fee:** $100\n🔹 **Destination address:**\n`{}`\n\n⚠️ **Important:**\n• Use TRC20 network only\n• Amount must be exactly $100\n• After sending, click the button below\n\n📤 **Enter your source wallet address:**",
            'after_subscribe_wallet': "✅ **Wallet address saved!**\n\n🔹 Your address: `{}`\n\n💰 **Please send exactly $100 to:**\n`{}`\n\n⚠️ **Important:**\n• Use TRC20 network only\n• Send exactly $100\n• After sending, click the button below\n\n✅ **Click after sending:**",
            'confirm_subscribe': "✅ I sent the payment",
            'subscribe_success': "✅ **Subscription successful!** 🎉\n\n🔹 Amount: ${}\n🔹 Transaction: `{}`\n\n🎉 You now have an active subscription!\n🙏 Welcome to UTYOB Lottery!",
            'subscribe_failed': "❌ **Subscription payment verification failed!**\n\n🔹 Reason: {}\n\n📌 **Solutions:**\n1. Amount must be exactly $100\n2. Destination address must be correct\n3. Transaction must be completed\n4. Use TRC20 network\n\n🔄 Try again after checking.\n\nIf you're sure about your payment, please send your transaction hash:",
            'send_tx_hash': "📤 Please send your transaction hash (TX ID) for manual verification:",
            'tx_hash_received': "✅ Transaction hash received!\n\n🔹 Hash: `{}`\n\n⏳ Your transaction is being reviewed by admin.\n📢 You will be notified when verified.",
            'tx_hash_invalid': "❌ Invalid transaction hash!\n\nPlease send a valid TRON transaction hash.\nExample: `abc123def456...`",
            
            'enter_wallet': "💳 **Deposit to participate in the lottery**\n\nPlease enter your source wallet address (TRC20):\n\n🔹 **Deposit amount:** $100\n🔹 **Destination address:**\n`{}`\n\n⚠️ **Important notes:**\n• Use only TRC20 network\n• Amount must be exactly $100\n• System will verify automatically\n• Save transaction ID for tracking\n\n📤 **Enter your source address:**",
            'enter_wallet_short': "📤 **Enter your source TRC20 wallet address:**",
            'after_wallet': "✅ **Wallet address saved!**\n\n🔹 Your address: `{}`\n\n💰 **Please send exactly $100 to:**\n`{}`\n\n⚠️ **Important:**\n• Use TRC20 network only\n• After sending, click the button below\n• System will verify automatically\n\n✅ **Click below after sending:**",
            'confirm_payment': "✅ I sent the payment",
            'cancel': "❌ Cancel",
            'verifying': "⏳ Verifying your payment...\nPlease wait a moment.",
            'payment_success': "✅ **Payment verified!** 🎉\n\n🔹 Amount: ${}\n🔹 Transaction: `{}`\n\n🎉 You have successfully registered for the lottery.\n🙏 Good luck!",
            'payment_failed': "❌ **Payment verification failed!**\n\n🔹 Reason: {}\n\n📌 **Solutions:**\n1. Amount must be exactly $100\n2. Destination address must be correct\n3. Transaction must be completed\n4. Use TRC20 network\n\n🔄 Try again after checking.\n\nIf you're sure about your payment, send your transaction hash:",
            'retry': "🔄 Try Again",
            'support': "📞 Support",
            
            'withdraw_prize': "💰 Withdraw Prize",
            'enter_withdraw_wallet': "💰 **Withdraw Prize**\n\nPrize amount: **${:,}**\n\nPlease enter your TRC20 wallet address:\n\n⚠️ **Important notes:**\n• Use only TRC20 network\n• Address must be correct\n• After confirmation, payment will be made\n\n📤 **Enter your wallet address:**",
            'withdraw_success': "✅ **Withdrawal registered successfully!** 🎉\n\n💰 Amount: ${:,}\n📤 Address: {}\n\n⏳ Amount will be sent to your account soon.\n🔔 You will be notified when sent.",
            'already_paid': "✅ Prize already paid!\n\n💰 Amount: ${}\n📅 Date: {}",
            'no_winner': "❌ You don't have any prize!\n\nParticipate in future lotteries.",
            'next_lottery': "🎰 Next Lottery",
            
            'referral_text': "🔗 **UTYOB Referral System**\n\n👤 You: {}\n📊 Invites: {}\n\n🔑 **Your referral code:**\n`{}`\n\n🔗 **Referral link:**\n{}\n\n💰 **Referral reward:**\n• 5% of deposit per invite\n• Instant reward after verification\n\n📤 Share this link with your friends!",
            'share': "📤 Share",
            
            'guide_text': "📖 **UTYOB Bot Complete Guide**\n\n🎯 **How it works:**\n1. **Register**: Use /start to register\n2. **Subscription**: Purchase subscription to participate\n3. **Deposit**: Send $100 to the specified address\n4. **Participate**: Join the lottery after verification\n5. **Win**: Receive prize if you win\n\n💰 **Deposit amount:**\n- Fixed amount: $100\n- Deposit address: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- Network: TRC20\n\n🎁 **Prizes:**\n- 1st prize: 50% of total\n- 2nd prize: 30% of total\n- 3rd prize: 20% of total\n\n🔗 **Referral system:**\n- Each user has unique referral code\n- 5% reward per invite\n\n⚠️ **Rules:**\n- One participation per lottery per user\n- Previous winners have lower chance\n- All transactions verified automatically\n\n📞 **Support:**\nContact admin for questions.",
            
            'language_selector': "🌐 **Change Language**\n\nCurrent language: {}",
            
            'invalid_command': "⚠️ Invalid command!\n\nUse the buttons or /help.",
            'error_message': "⚠️ An error occurred! Please try again.",
            'photo_not_supported': "📸 Photo received!\nBut this feature is not supported.",
            'invalid_wallet': "❌ Invalid wallet address!\n\nPlease enter a valid TRC20 address.\nExample: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
            
            'admin_verify_tx': "✅ **Transaction Verification Request**\n\n👤 User: {}\n📤 From: {}\n📥 To: {}\n💰 Amount: ${}\n🔗 TX Hash: `{}`\n\nPlease verify this transaction:",
            'admin_verify_approve': "✅ Approve",
            'admin_verify_reject': "❌ Reject",
            'admin_verify_approved': "✅ **Transaction approved!**\n\n👤 User: {}\n💰 Amount: ${}\n🔗 TX Hash: `{}`\n\nUser's subscription has been activated.",
            'admin_verify_rejected': "❌ **Transaction rejected!**\n\n👤 User: {}\n🔗 TX Hash: `{}`\n\nUser has been notified.",
            'user_verify_approved': "✅ **Your transaction has been approved!** 🎉\n\n💰 Subscription activated!\n🔗 TX Hash: `{}`\n\n🎉 You now have an active subscription!\n🙏 Welcome to UTYOB Lottery!",
            'user_verify_rejected': "❌ **Your transaction has been rejected!**\n\n🔗 TX Hash: `{}`\n\nPlease check your transaction and try again.\n\n📌 **Reasons:**\n• Amount may not be exactly $100\n• Address may be incorrect\n• Transaction may not be completed",
            
            'poll_message': "📊 **Poll**\n\n{}",
            'poll_option_1': "✅ Yes",
            'poll_option_2': "❌ No",
            
            # دکمه‌های جدید دانلودر و فاکتور
            'download_instagram': "📸 Download Instagram",
            'download_youtube': "🎬 Download YouTube",
            'instagram_downloader': "📸 Instagram Downloader",
            'youtube_downloader': "🎬 YouTube Downloader",
            'send_link_instagram': "📤 Please send the Instagram post/video link:\n\nExample: `https://www.instagram.com/p/ABC123/`",
            'send_link_youtube': "📤 Please send the YouTube video link:\n\nExample: `https://www.youtube.com/watch?v=ABC123`",
            'downloading': "⏳ Downloading... Please wait.",
            'download_success': "✅ Download successful! Here is your file:",
            'download_failed': "❌ Download failed! Please check the link and try again.",
            'invalid_link': "❌ Invalid link! Please send a valid Instagram or YouTube link.",
            'invoice': "📄 Create Invoice",
            'invoice_button': "📄 Create Invoice",
            'invoice_created': "✅ Invoice created successfully!",
            'open_invoice': "📄 Open Invoice",
            'invoice_description': "📄 **Create Invoice**\n\nPlease click the button below to open the invoice form.\n\n⚠️ Press back button twice to exit the site.",
        },
        'fa': {
            'name': 'فارسی',
            'emoji': '🇮🇷',
            'welcome': "🎮 **به ربات قرعه‌کشی UTYOB خوش آمدید!**\n\n💰 برنده جوایز شگفت‌انگیز تا ۱۰۰۰۰ دلار شوید!\n🎯 سیستم قرعه‌کشی عادلانه و شفاف\n🌟 همین حالا بپیوندید و شانس خود را امتحان کنید!\n\nبرای ورود به بازی، روی PLAY کلیک کنید.",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **ربات قرعه‌کشی UTYOB**\n\nیکی از گزینه‌های زیر را انتخاب کنید:\n👇👇👇",
            'lottery': "🎰 شرکت در قرعه‌کشی",
            'referral': "🔗 رفرال",
            'guide': "📖 راهنمایی",
            'language': "🌐 تغییر زبان",
            'admin_panel': "⚙️ پنل مدیریت",
            'no_subscription': "❌ **شما اشتراک فعال ندارید!**\n\nبرای شرکت در قرعه‌کشی، ابتدا باید اشتراک تهیه کنید.\n\n💰 هزینه اشتراک: ۱۰۰ دلار\n📅 مدت اعتبار: ۱ ماه\n\nبرای تهیه اشتراک، روی دکمه زیر کلیک کنید.",
            'subscribe': "🔄 خرید اشتراک",
            'back': "🔙 بازگشت",
            'main_menu_btn': "🔙 منوی اصلی",
            'lottery_back': "🎰 بازگشت به قرعه‌کشی",
            
            'subscribe_wallet': "💳 **خرید اشتراک UTYOB**\n\nلطفاً آدرس کیف پول مبدا (TRC20) خود را وارد کنید:\n\n🔹 **هزینه اشتراک:** ۱۰۰ دلار\n🔹 **آدرس مقصد:**\n`{}`\n\n⚠️ **نکات مهم:**\n• فقط از شبکه TRC20 استفاده کنید\n• مبلغ دقیقاً ۱۰۰ دلار باشد\n• پس از واریز، روی دکمه زیر کلیک کنید\n\n📤 **آدرس کیف پول خود را وارد کنید:**",
            'after_subscribe_wallet': "✅ **آدرس کیف پول ذخیره شد!**\n\n🔹 آدرس شما: `{}`\n\n💰 **لطفاً مبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:**\n`{}`\n\n⚠️ **نکات مهم:**\n• فقط از شبکه TRC20 استفاده کنید\n• مبلغ دقیقاً ۱۰۰ دلار باشد\n• پس از واریز، روی دکمه زیر کلیک کنید\n\n✅ **پس از واریز کلیک کنید:**",
            'confirm_subscribe': "✅ پرداخت کردم",
            'subscribe_success': "✅ **اشتراک شما فعال شد!** 🎉\n\n🔹 مبلغ: {}$\n🔹 تراکنش: `{}`\n\n🎉 اشتراک شما با موفقیت فعال شد!\n🙏 به UTYOB خوش آمدید!",
            'subscribe_failed': "❌ **پرداخت اشتراک تایید نشد!**\n\n🔹 دلیل: {}\n\n📌 **راهکارها:**\n1. مبلغ دقیقاً ۱۰۰ دلار باشد\n2. آدرس مقصد صحیح باشد\n3. تراکنش انجام شده باشد\n4. از شبکه TRC20 استفاده کنید\n\n🔄 پس از بررسی، مجدداً تلاش کنید.\n\nاگر از پرداخت خود مطمئن هستید، هش تراکنش خود را ارسال کنید:",
            'send_tx_hash': "📤 لطفاً هش تراکنش (TX ID) خود را برای تایید دستی ارسال کنید:",
            'tx_hash_received': "✅ هش تراکنش دریافت شد!\n\n🔹 هش: `{}`\n\n⏳ تراکنش شما در حال بررسی توسط مدیر است.\n📢 پس از تایید به شما اطلاع داده می‌شود.",
            'tx_hash_invalid': "❌ هش تراکنش نامعتبر!\n\nلطفاً یک هش تراکنش معتبر TRON ارسال کنید.\nمثال: `abc123def456...`",
            
            'enter_wallet': "💳 **واریز برای شرکت در قرعه‌کشی**\n\nلطفاً آدرس کیف پول مبدا (TRC20) خود را وارد کنید:\n\n🔹 **مبلغ واریز:** ۱۰۰ دلار\n🔹 **آدرس مقصد:**\n`{}`\n\n⚠️ **نکات مهم:**\n• فقط از شبکه TRC20 استفاده کنید\n• مبلغ دقیقاً ۱۰۰ دلار باشد\n• سیستم به صورت خودکار تایید می‌کند\n• کد تراکنش را برای پیگیری ذخیره کنید\n\n📤 **آدرس مبدا خود را وارد کنید:**",
            'enter_wallet_short': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
            'after_wallet': "✅ **آدرس کیف پول ذخیره شد!**\n\n🔹 آدرس شما: `{}`\n\n💰 **لطفاً مبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:**\n`{}`\n\n⚠️ **نکات مهم:**\n• فقط از شبکه TRC20 استفاده کنید\n• پس از واریز، روی دکمه زیر کلیک کنید\n• سیستم به صورت خودکار تایید می‌کند\n\n✅ **پس از واریز، کلیک کنید:**",
            'confirm_payment': "✅ پرداخت کردم",
            'cancel': "❌ انصراف",
            'verifying': "⏳ در حال بررسی پرداخت شما...\nلطفاً چند لحظه صبر کنید.",
            'payment_success': "✅ **پرداخت شما تایید شد!** 🎉\n\n🔹 مبلغ: {}$\n🔹 تراکنش: `{}`\n\n🎉 شما با موفقیت در قرعه‌کشی ثبت نام کردید.\n🙏 برای شما آرزوی موفقیت داریم!",
            'payment_failed': "❌ **پرداخت شما تایید نشد!**\n\n🔹 دلیل: {}\n\n📌 **راهکارها:**\n1. مبلغ دقیقاً ۱۰۰ دلار باشد\n2. آدرس مقصد صحیح باشد\n3. تراکنش انجام شده باشد\n4. از شبکه TRC20 استفاده کنید\n\n🔄 پس از بررسی، مجدداً تلاش کنید.\n\nاگر از پرداخت خود مطمئن هستید، هش تراکنش خود را ارسال کنید:",
            'retry': "🔄 تلاش مجدد",
            'support': "📞 پشتیبانی",
            
            'withdraw_prize': "💰 برداشت جایزه",
            'enter_withdraw_wallet': "💰 **برداشت جایزه**\n\nمبلغ جایزه: **${:,}**\n\nلطفاً آدرس کیف پول TRC20 خود را وارد کنید:\n\n⚠️ **نکات مهم:**\n• فقط از شبکه TRC20 استفاده کنید\n• آدرس باید دقیق و صحیح باشد\n• پس از تایید، واریز انجام می‌شود\n\n📤 **آدرس کیف پول خود را وارد کنید:**",
            'withdraw_success': "✅ **برداشت شما با موفقیت ثبت شد!** 🎉\n\n💰 مبلغ: ${:,}\n📤 آدرس: {}\n\n⏳ مبلغ به زودی به حساب شما واریز می‌شود.\n🔔 پس از واریز، به شما اطلاع داده می‌شود.",
            'already_paid': "✅ جایزه شما قبلاً پرداخت شده است!\n\n💰 مبلغ: ${}\n📅 تاریخ: {}",
            'no_winner': "❌ شما برنده‌ای ندارید!\n\nدر قرعه‌کشی‌های بعدی شرکت کنید.",
            'next_lottery': "🎰 قرعه‌کشی بعدی",
            
            'referral_text': "🔗 **سیستم رفرال UTYOB**\n\n👤 شما: {}\n📊 تعداد دعوت‌ها: {}\n\n🔑 **کد رفرال شما:**\n`{}`\n\n🔗 **لینک دعوت:**\n{}\n\n💰 **پاداش دعوت:**\n• به ازای هر دعوت: ۵٪ از واریز\n• پاداش فوری پس از تایید\n\n📤 لینک را برای دوستان خود ارسال کنید!",
            'share': "📤 اشتراک‌گذاری",
            
            'guide_text': "📖 **راهنمای کامل ربات UTYOB**\n\n🎯 **نحوه کار:**\n1. **ثبت‌نام**: با دستور /start ثبت‌نام کنید\n2. **اشتراک**: برای شرکت در قرعه‌کشی، اشتراک تهیه کنید\n3. **واریز**: مبلغ ۱۰۰ دلار به آدرس مشخص واریز کنید\n4. **شرکت**: پس از تایید، در قرعه‌کشی شرکت کنید\n5. **برنده**: در صورت برنده شدن، جایزه دریافت کنید\n\n💰 **مبلغ واریز:**\n- مبلغ ثابت: ۱۰۰ دلار\n- آدرس واریز: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- شبکه: TRC20\n\n🎁 **جوایز:**\n- جایزه اول: ۵۰٪ از کل مبلغ\n- جایزه دوم: ۳۰٪ از کل مبلغ\n- جایزه سوم: ۲۰٪ از کل مبلغ\n\n🔗 **سیستم رفرال:**\n- هر کاربر کد رفرال اختصاصی دارد\n- به ازای هر دعوت، ۵٪ پاداش دریافت کنید\n\n⚠️ **قوانین:**\n- هر کاربر فقط یک بار در هر قرعه‌کشی شرکت می‌کند\n- برندگان قبلی شانس کمتری در قرعه‌کشی‌های بعدی دارند\n- تمامی تراکنش‌ها به صورت خودکار تایید می‌شوند\n\n📞 **پشتیبانی:**\nبرای سوالات و مشکلات با مدیریت تماس بگیرید.",
            
            'language_selector': "🌐 **تغییر زبان**\n\nزبان فعلی: {}",
            
            'invalid_command': "⚠️ دستور نامعتبر!\n\nاز دکمه‌های موجود استفاده کنید یا /help را ببینید.",
            'error_message': "⚠️ خطایی رخ داد! لطفاً دوباره تلاش کنید.",
            'photo_not_supported': "📸 عکس دریافت شد!\nاما این قابلیت پشتیبانی نمی‌شود.",
            'invalid_wallet': "❌ آدرس کیف پول نامعتبر!\n\nلطفاً یک آدرس معتبر TRC20 وارد کنید.\nمثال: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
            
            'admin_verify_tx': "✅ **درخواست تایید تراکنش**\n\n👤 کاربر: {}\n📤 از: {}\n📥 به: {}\n💰 مبلغ: ${}\n🔗 هش تراکنش: `{}`\n\nلطفاً این تراکنش را تایید کنید:",
            'admin_verify_approve': "✅ تایید",
            'admin_verify_reject': "❌ رد",
            'admin_verify_approved': "✅ **تراکنش تایید شد!**\n\n👤 کاربر: {}\n💰 مبلغ: ${}\n🔗 هش: `{}`\n\nاشتراک کاربر فعال شد.",
            'admin_verify_rejected': "❌ **تراکنش رد شد!**\n\n👤 کاربر: {}\n🔗 هش: `{}`\n\nبه کاربر اطلاع داده شد.",
            'user_verify_approved': "✅ **تراکنش شما تایید شد!** 🎉\n\n💰 اشتراک فعال شد!\n🔗 هش: `{}`\n\n🎉 اشتراک شما با موفقیت فعال شد!\n🙏 به UTYOB خوش آمدید!",
            'user_verify_rejected': "❌ **تراکنش شما رد شد!**\n\n🔗 هش: `{}`\n\nلطفاً تراکنش خود را بررسی کرده و مجدداً تلاش کنید.\n\n📌 **دلایل احتمالی:**\n• مبلغ دقیقاً ۱۰۰ دلار نبوده\n• آدرس مقصد اشتباه بوده\n• تراکنش کامل نشده است",
            
            'poll_message': "📊 **نظرسنجی**\n\n{}",
            'poll_option_1': "✅ بله",
            'poll_option_2': "❌ خیر",
            
            # دکمه‌های جدید دانلودر و فاکتور - فارسی
            'download_instagram': "📸 دانلود اینستاگرام",
            'download_youtube': "🎬 دانلود یوتیوب",
            'instagram_downloader': "📸 دانلودر اینستاگرام",
            'youtube_downloader': "🎬 دانلودر یوتیوب",
            'send_link_instagram': "📤 لطفاً لینک پست یا ویدیوی اینستاگرام را ارسال کنید:\n\nمثال: `https://www.instagram.com/p/ABC123/`",
            'send_link_youtube': "📤 لطفاً لینک ویدیوی یوتیوب را ارسال کنید:\n\nمثال: `https://www.youtube.com/watch?v=ABC123`",
            'downloading': "⏳ در حال دانلود... لطفاً صبر کنید.",
            'download_success': "✅ دانلود با موفقیت انجام شد! فایل شما:",
            'download_failed': "❌ دانلود ناموفق! لطفاً لینک را بررسی کنید و مجدداً تلاش کنید.",
            'invalid_link': "❌ لینک نامعتبر! لطفاً یک لینک معتبر از اینستاگرام یا یوتیوب ارسال کنید.",
            'invoice': "📄 ساخت فاکتور",
            'invoice_button': "📄 ساخت فاکتور",
            'invoice_created': "✅ فاکتور با موفقیت ساخته شد!",
            'open_invoice': "📄 باز کردن فاکتور",
            'invoice_description': "📄 **ساخت فاکتور**\n\nلطفاً روی دکمه زیر کلیک کنید تا فرم فاکتور باز شود.\n\n⚠️ برای خروج از سایت، دو بار دکمه برگشت را بزنید.",
        },
        'tr': {
            'name': 'Türkçe',
            'emoji': '🇹🇷',
            'welcome': "🎮 **UTYOB Piyango Botuna Hoş Geldiniz!**\n\n💰 10.000$'a kadar harika ödüller kazanın!\n🎯 Adil ve şeffaf piyango sistemi\n🌟 Hemen katıl ve şansını dene!\n\nOyuna girmek için PLAY'a tıkla.",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **UTYOB Piyango Botu**\n\nAşağıdaki seçeneklerden birini seçin:\n👇👇👇",
            'lottery': "🎰 Piyangoya Katıl",
            'referral': "🔗 Referans",
            'guide': "📖 Rehber",
            'language': "🌐 Dil Değiştir",
            'admin_panel': "⚙️ Yönetim Paneli",
            'no_subscription': "❌ **Aktif aboneliğiniz yok!**\n\nPiyangoya katılmak için önce abonelik satın almalısınız.\n\n💰 Abonelik ücreti: 100$\n📅 Geçerlilik: 1 ay\n\nAbone olmak için aşağıdaki butona tıklayın.",
            'subscribe': "🔄 Abone Ol",
            'back': "🔙 Geri",
            'main_menu_btn': "🔙 Ana Menü",
            'lottery_back': "🎰 Piyangoya Dön",
            
            'subscribe_wallet': "💳 **UTYOB Aboneliği**\n\nLütfen kaynak TRC20 cüzdan adresinizi girin:\n\n🔹 **Abonelik ücreti:** 100$\n🔹 **Hedef adres:**\n`{}`\n\n⚠️ **Önemli:**\n• Sadece TRC20 ağını kullanın\n• Tutar tam olarak 100$ olmalı\n• Gönderdikten sonra aşağıdaki butona tıklayın\n\n📤 **Kaynak cüzdan adresinizi girin:**",
            'after_subscribe_wallet': "✅ **Cüzdan adresi kaydedildi!**\n\n🔹 Adresiniz: `{}`\n\n💰 **Lütfen tam olarak 100$'yi aşağıdaki adrese gönderin:**\n`{}`\n\n⚠️ **Önemli:**\n• Sadece TRC20 ağını kullanın\n• Tutar tam olarak 100$ olmalı\n• Gönderdikten sonra aşağıdaki butona tıklayın\n\n✅ **Gönderdikten sonra tıklayın:**",
            'confirm_subscribe': "✅ Ödemeyi Gönderdim",
            'subscribe_success': "✅ **Aboneliğiniz aktifleştirildi!** 🎉\n\n🔹 Tutar: ${}\n🔹 İşlem: `{}`\n\n🎉 Aboneliğiniz başarıyla aktifleştirildi!\n🙏 UTYOB'a hoş geldiniz!",
            'subscribe_failed': "❌ **Abonelik ödemesi doğrulanamadı!**\n\n🔹 Sebep: {}\n\n📌 **Çözümler:**\n1. Tutar tam olarak 100$ olmalı\n2. Hedef adres doğru olmalı\n3. İşlem tamamlanmış olmalı\n4. TRC20 ağını kullanın\n\n🔄 Kontrol ettikten sonra tekrar deneyin.\n\nÖdemenizden eminseniz, işlem hash'inizi gönderin:",
            'send_tx_hash': "📤 Manuel doğrulama için işlem hash'inizi (TX ID) gönderin:",
            'tx_hash_received': "✅ İşlem hash'i alındı!\n\n🔹 Hash: `{}`\n\n⏳ İşleminiz yönetici tarafından inceleniyor.\n📢 Onaylandığında bilgilendirileceksiniz.",
            'tx_hash_invalid': "❌ Geçersiz işlem hash'i!\n\nLütfen geçerli bir TRON işlem hash'i gönderin.\nÖrnek: `abc123def456...`",
            
            'enter_wallet': "💳 **Piyangoya katılmak için yatırım**\n\nLütfen kaynak cüzdan adresinizi (TRC20) girin:\n\n🔹 **Yatırım tutarı:** 100$\n🔹 **Hedef adres:**\n`{}`\n\n⚠️ **Önemli notlar:**\n• Sadece TRC20 ağını kullanın\n• Tutar tam olarak 100$ olmalı\n• Sistem otomatik olarak doğrulayacak\n• Takip için işlem kimliğini kaydedin\n\n📤 **Kaynak adresinizi girin:**",
            'enter_wallet_short': "📤 **TRC20 cüzdan adresinizi girin:**",
            'after_wallet': "✅ **Cüzdan adresi kaydedildi!**\n\n🔹 Adresiniz: `{}`\n\n💰 **Lütfen tam olarak 100$'yi aşağıdaki adrese gönderin:**\n`{}`\n\n⚠️ **Önemli:**\n• Sadece TRC20 ağını kullanın\n• Gönderdikten sonra aşağıdaki butona tıklayın\n• Sistem otomatik olarak doğrulayacak\n\n✅ **Gönderdikten sonra tıklayın:**",
            'confirm_payment': "✅ Ödemeyi Gönderdim",
            'cancel': "❌ İptal",
            'verifying': "⏳ Ödemeniz kontrol ediliyor...\nLütfen bir dakika bekleyin.",
            'payment_success': "✅ **Ödemeniz doğrulandı!** 🎉\n\n🔹 Tutar: ${}\n🔹 İşlem: `{}`\n\n🎉 Piyangoya başarıyla kaydoldunuz.\n🙏 İyi şanslar!",
            'payment_failed': "❌ **Ödeme doğrulaması başarısız!**\n\n🔹 Sebep: {}\n\n📌 **Çözümler:**\n1. Tutar tam olarak 100$ olmalı\n2. Hedef adres doğru olmalı\n3. İşlem tamamlanmış olmalı\n4. TRC20 ağını kullanın\n\n🔄 Kontrol ettikten sonra tekrar deneyin.\n\nÖdemenizden eminseniz, işlem hash'inizi gönderin:",
            'retry': "🔄 Tekrar Dene",
            'support': "📞 Destek",
            
            'withdraw_prize': "💰 Ödülü Çek",
            'enter_withdraw_wallet': "💰 **Ödülü Çek**\n\nÖdül tutarı: **${:,}**\n\nLütfen TRC20 cüzdan adresinizi girin:\n\n⚠️ **Önemli notlar:**\n• Sadece TRC20 ağını kullanın\n• Adres doğru ve tam olmalı\n• Onaydan sonra ödeme yapılacak\n\n📤 **Cüzdan adresinizi girin:**",
            'withdraw_success': "✅ **Çekim başarıyla kaydedildi!** 🎉\n\n💰 Tutar: ${:,}\n📤 Adres: {}\n\n⏳ Tutar yakında hesabınıza gönderilecek.\n🔔 Gönderildiğinde bilgilendirileceksiniz.",
            'already_paid': "✅ Ödül zaten ödendi!\n\n💰 Tutar: ${}\n📅 Tarih: {}",
            'no_winner': "❌ Hiç ödülünüz yok!\n\nGelecek piyangolara katılın.",
            'next_lottery': "🎰 Sonraki Piyango",
            
            'referral_text': "🔗 **UTYOB Referans Sistemi**\n\n👤 Siz: {}\n📊 Davetler: {}\n\n🔑 **Referans kodunuz:**\n`{}`\n\n🔗 **Referans linki:**\n{}\n\n💰 **Referans ödülü:**\n• Her davet için %5 yatırım\n• Doğrulama sonrası anında ödül\n\n📤 Bu linki arkadaşlarınızla paylaşın!",
            'share': "📤 Paylaş",
            
            'guide_text': "📖 **UTYOB Bot Tam Rehber**\n\n🎯 **Nasıl çalışır:**\n1. **Kayıt**: /start ile kaydolun\n2. **Abonelik**: Katılmak için abonelik satın alın\n3. **Yatırım**: Belirtilen adrese 100$ gönderin\n4. **Katılım**: Doğrulama sonrası piyangoya katılın\n5. **Kazanç**: Kazanırsanız ödülü alın\n\n💰 **Yatırım tutarı:**\n- Sabit tutar: 100$\n- Yatırım adresi: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- Ağ: TRC20\n\n🎁 **Ödüller:**\n- 1. ödül: Toplamın %50'si\n- 2. ödül: Toplamın %30'u\n- 3. ödül: Toplamın %20'si\n\n🔗 **Referans sistemi:**\n- Her kullanıcının benzersiz referans kodu vardır\n- Davet başına %5 ödül\n\n⚠️ **Kurallar:**\n- Her piyangoda kullanıcı başına bir katılım\n- Önceki kazananların şansı daha düşük\n- Tüm işlemler otomatik doğrulanır\n\n📞 **Destek:**\nSorularınız için yöneticiye başvurun.",
            
            'language_selector': "🌐 **Dil Değiştir**\n\nMevcut dil: {}",
            
            'invalid_command': "⚠️ Geçersiz komut!\n\nButonları veya /help kullanın.",
            'error_message': "⚠️ Bir hata oluştu! Lütfen tekrar deneyin.",
            'photo_not_supported': "📸 Fotoğraf alındı!\nAncak bu özellik desteklenmiyor.",
            'invalid_wallet': "❌ Geçersiz cüzdan adresi!\n\nLütfen geçerli bir TRC20 adresi girin.\nÖrnek: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
            
            'admin_verify_tx': "✅ **İşlem Doğrulama Talebi**\n\n👤 Kullanıcı: {}\n📤 Gönderen: {}\n📥 Alan: {}\n💰 Tutar: ${}\n🔗 TX Hash: `{}`\n\nLütfen bu işlemi doğrulayın:",
            'admin_verify_approve': "✅ Onayla",
            'admin_verify_reject': "❌ Reddet",
            'admin_verify_approved': "✅ **İşlem onaylandı!**\n\n👤 Kullanıcı: {}\n💰 Tutar: ${}\n🔗 TX Hash: `{}`\n\nKullanıcının aboneliği aktifleştirildi.",
            'admin_verify_rejected': "❌ **İşlem reddedildi!**\n\n👤 Kullanıcı: {}\n🔗 TX Hash: `{}`\n\nKullanıcı bilgilendirildi.",
            'user_verify_approved': "✅ **İşleminiz onaylandı!** 🎉\n\n💰 Abonelik aktifleştirildi!\n🔗 TX Hash: `{}`\n\n🎉 Aboneliğiniz başarıyla aktifleştirildi!\n🙏 UTYOB'a hoş geldiniz!",
            'user_verify_rejected': "❌ **İşleminiz reddedildi!**\n\n🔗 TX Hash: `{}`\n\nLütfen işleminizi kontrol edip tekrar deneyin.\n\n📌 **Olası nedenler:**\n• Tutar tam olarak 100$ değil\n• Hedef adres yanlış\n• İşlem tamamlanmamış",
            
            'poll_message': "📊 **Anket**\n\n{}",
            'poll_option_1': "✅ Evet",
            'poll_option_2': "❌ Hayır",
            
            # دکمه‌های جدید دانلودر و فاکتور - ترکی
            'download_instagram': "📸 Instagram İndir",
            'download_youtube': "🎬 YouTube İndir",
            'instagram_downloader': "📸 Instagram İndirici",
            'youtube_downloader': "🎬 YouTube İndirici",
            'send_link_instagram': "📤 Lütfen Instagram gönderi/video linkini gönderin:\n\nÖrnek: `https://www.instagram.com/p/ABC123/`",
            'send_link_youtube': "📤 Lütfen YouTube video linkini gönderin:\n\nÖrnek: `https://www.youtube.com/watch?v=ABC123`",
            'downloading': "⏳ İndiriliyor... Lütfen bekleyin.",
            'download_success': "✅ İndirme başarılı! Dosyanız:",
            'download_failed': "❌ İndirme başarısız! Lütfen linki kontrol edip tekrar deneyin.",
            'invalid_link': "❌ Geçersiz link! Lütfen geçerli bir Instagram veya YouTube linki gönderin.",
            'invoice': "📄 Fatura Oluştur",
            'invoice_button': "📄 Fatura Oluştur",
            'invoice_created': "✅ Fatura başarıyla oluşturuldu!",
            'open_invoice': "📄 Faturayı Aç",
            'invoice_description': "📄 **Fatura Oluştur**\n\nFatura formunu açmak için lütfen aşağıdaki butona tıklayın.\n\n⚠️ Siteden çıkmak için geri tuşuna iki kez basın.",
        }
    }
    
    DEFAULT_LANG = 'en'
    
    @classmethod
    def get_text(cls, lang_code: str, key: str, *args, **kwargs) -> str:
        if lang_code not in cls.LANGUAGES:
            lang_code = cls.DEFAULT_LANG
            
        text = cls.LANGUAGES[lang_code].get(key, cls.LANGUAGES[cls.DEFAULT_LANG].get(key, key))
        
        if args:
            try:
                return text.format(*args)
            except:
                return text
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text
    
    @classmethod
    def get_language_name(cls, lang_code: str) -> str:
        return cls.LANGUAGES.get(lang_code, {}).get('name', 'English')
    
    @classmethod
    def get_language_emoji(cls, lang_code: str) -> str:
        return cls.LANGUAGES.get(lang_code, {}).get('emoji', '🇬🇧')
    
    @classmethod
    def get_invoice_text(cls, lang_code: str) -> str:
        if lang_code not in cls.LANGUAGES:
            lang_code = cls.DEFAULT_LANG
        return cls.LANGUAGES[lang_code].get('invoice_button', '📄 Create Invoice')

# ============================================================
# دیتابیس با ۵۰۰ شارد برای مقیاس‌پذیری بالا
# ============================================================
class DatabaseManager:
    def __init__(self, num_shards=DB_SHARDS):
        self.num_shards = num_shards
        self.connections = {}
        self.locks = {}
        self.executor = ThreadPoolExecutor(max_workers=50)
        self._init_shards()
        
    def _init_shards(self):
        os.makedirs("data", exist_ok=True)
        for i in range(self.num_shards):
            db_path = f"data/shard_{i}.db"
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=60)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=50000")
            conn.execute("PRAGMA temp_store=MEMORY")
            self.connections[i] = conn
            self.locks[i] = threading.RLock()
            self._create_tables(conn, i)
            
    def _create_tables(self, conn, shard_id):
        cursor = conn.cursor()
        
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
                has_subscription INTEGER DEFAULT 0,
                subscription_end TEXT,
                total_participations INTEGER DEFAULT 0,
                wins_count INTEGER DEFAULT 0,
                last_win_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_id TEXT,
                status TEXT DEFAULT 'pending',
                verified_at TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_address TEXT,
                to_address TEXT,
                amount REAL,
                tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lotteries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winners_count INTEGER,
                prize_per_winner REAL,
                total_prize REAL,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                ended_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_id INTEGER,
                user_id INTEGER,
                prize_amount REAL,
                wallet_address TEXT,
                paid_status INTEGER DEFAULT 0,
                paid_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_user ON winners(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_paid ON winners(paid_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_tx_user ON pending_verifications(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_tx_status ON pending_verifications(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription_end ON users(subscription_end)')
        
        conn.commit()
        
    def get_shard(self, user_id):
        return hash(str(user_id)) % self.num_shards
        
    def get_connection(self, user_id):
        shard = self.get_shard(user_id)
        return self.connections[shard], self.locks[shard]
        
    def execute(self, user_id, query, params=(), commit=True):
        conn, lock = self.get_connection(user_id)
        with lock:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit:
                conn.commit()
            return cursor
            
    def execute_global(self, query, params=()):
        results = []
        for shard_id, conn in self.connections.items():
            with self.locks[shard_id]:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                results.extend(cursor.fetchall())
        return results
        
    def execute_parallel(self, query, params_list):
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for params in params_list:
                future = executor.submit(self._execute_single, query, params)
                futures.append(future)
            results = []
            for future in futures:
                results.extend(future.result())
            return results
            
    def _execute_single(self, query, params):
        results = []
        for shard_id, conn in self.connections.items():
            with self.locks[shard_id]:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                results.extend(cursor.fetchall())
        return results

db = DatabaseManager()

# ============================================================
# سیستم کش پیشرفته با TTL و LRU
# ============================================================
class CacheManager:
    def __init__(self, max_size=10000):
        self.cache = {}
        self.expiry = {}
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        self.max_size = max_size
        
    def set(self, key, value, ttl=CACHE_TTL):
        with self.lock:
            if len(self.cache) >= self.max_size:
                oldest = min(self.expiry, key=self.expiry.get)
                del self.cache[oldest]
                del self.expiry[oldest]
            self.cache[key] = value
            self.expiry[key] = time.time() + ttl
            
    def get(self, key):
        with self.lock:
            if key in self.cache and time.time() < self.expiry[key]:
                self.hits += 1
                return self.cache[key]
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]
            self.misses += 1
            return None
            
    def delete(self, key):
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.expiry[key]
                
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.expiry.clear()
            
    def get_stats(self):
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'size': len(self.cache),
                'max_size': self.max_size
            }

cache = CacheManager(max_size=20000)

# ============================================================
# سیستم تایید پرداخت با چندین API و کش
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.api_stats = {api: {'requests': 0, 'success': 0, 'errors': 0, 'last_reset': time.time()} for api in self.apis}
        self.lock = threading.RLock()
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=20)
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=200, limit_per_host=50, ttl_dns_cache=300)
            )
        return self.session
        
    async def verify_transaction(self, from_address, to_address, amount, tx_id=None):
        cache_key = f"verify_{from_address}_{to_address}_{amount}_{tx_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        session = await self.get_session()
        
        if tx_id:
            result = await self._verify_by_txid(session, tx_id, from_address, to_address, amount)
        else:
            result = await self._search_transactions(session, from_address, to_address, amount)
            
        cache.set(cache_key, result, ttl=60)
        return result
        
    async def _verify_by_txid(self, session, tx_id, from_address, to_address, amount):
        tasks = []
        for api in self.apis:
            tasks.append(self._check_api(session, api, tx_id, from_address, to_address, amount))
        
        results = await asyncio.gather(*tasks)
        
        for success, tx_id_result, message in results:
            if success:
                return True, tx_id_result, message
                
        return False, None, "Transaction not found or invalid"
        
    async def _check_api(self, session, api, tx_id, from_address, to_address, amount):
        try:
            url = f"https://api.trongrid.io/v1/transactions/{tx_id}"
            headers = {"TRON-PRO-API-KEY": api}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if self._validate_transaction_data(data, from_address, to_address, amount):
                        self._update_api_stats(api, True)
                        return True, tx_id, "Verified"
                self._update_api_stats(api, False)
        except Exception as e:
            logger.error(f"API error for {api}: {e}")
            self._update_api_stats(api, False)
        return False, None, "Failed"
        
    async def _search_transactions(self, session, from_address, to_address, amount):
        for api in self.apis:
            try:
                url = f"https://api.trongrid.io/v1/accounts/{from_address}/transactions"
                params = {"limit": 30, "order_by": "block_timestamp,desc"}
                headers = {"TRON-PRO-API-KEY": api}
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for tx in data.get('data', []):
                            if self._validate_transaction_data(tx, from_address, to_address, amount):
                                self._update_api_stats(api, True)
                                return True, tx.get('txID'), "Verified"
                    self._update_api_stats(api, False)
            except Exception as e:
                logger.error(f"API search error for {api}: {e}")
                self._update_api_stats(api, False)
        return False, None, "No matching transaction found"
        
    def _validate_transaction_data(self, tx_data, from_address, to_address, amount):
        try:
            if tx_data.get('to') != to_address:
                return False
            tx_amount = tx_data.get('amount', 0) / 1_000_000
            if abs(tx_amount - amount) > 0.01:
                return False
            status = tx_data.get('status', '')
            if status and status != 'SUCCESS':
                return False
            return True
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
            
    def _update_api_stats(self, api, success):
        with self.lock:
            if api in self.api_stats:
                self.api_stats[api]['requests'] += 1
                if success:
                    self.api_stats[api]['success'] += 1
                else:
                    self.api_stats[api]['errors'] += 1
                    
    def add_api(self, api_key):
        if api_key not in self.apis:
            self.apis.append(api_key)
            self.api_stats[api_key] = {'requests': 0, 'success': 0, 'errors': 0, 'last_reset': time.time()}
            return True
        return False

payment_verifier = PaymentVerifier()

# ============================================================
# سیستم قرعه‌کشی با الگوریتم هوش مصنوعی
# ============================================================
class LotterySystem:
    def __init__(self):
        self.current_lottery = None
        self.is_running = False
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    def start_lottery(self, winners_count, prize_per_winner):
        with self.lock:
            if self.is_running:
                return False, "Lottery is already running"
                
            eligible_users = self._get_eligible_users()
            
            if not eligible_users:
                return False, "No eligible users found"
                
            if len(eligible_users) < winners_count:
                return False, f"Eligible users ({len(eligible_users)}) less than winners ({winners_count})"
                
            winners = self._ai_smart_select(eligible_users, winners_count)
            
            if not winners or len(winners) < winners_count:
                return False, "Error selecting winners"
                
            lottery_id = self._save_lottery(winners_count, prize_per_winner, winners)
            
            if not lottery_id:
                return False, "Error saving lottery"
                
            self._save_winners(lottery_id, winners, prize_per_winner)
            
            for winner in winners:
                self._update_winner_stats(winner)
                
            self.current_lottery = {
                'id': lottery_id,
                'winners': winners,
                'prize_per_winner': prize_per_winner,
                'winners_count': winners_count,
                'timestamp': datetime.now()
            }
            
            self.is_running = False
            
            return True, {
                'lottery_id': lottery_id,
                'winners': winners,
                'prize_per_winner': prize_per_winner
            }
            
    def _get_eligible_users(self):
        cursor = db.execute_global(
            """SELECT user_id FROM users 
               WHERE has_subscription = 1 
               AND subscription_end >= date('now')"""
        )
        return [row['user_id'] for row in cursor]
        
    def _ai_smart_select(self, eligible_users, winners_count):
        if not eligible_users:
            return []
            
        user_scores = []
        for user_id in eligible_users:
            score = self._calculate_ai_score(user_id)
            if score > 0:
                user_scores.append((user_id, score))
                
        if not user_scores:
            return random.sample(eligible_users, min(winners_count, len(eligible_users)))
            
        user_scores.sort(key=lambda x: x[1], reverse=True)
        
        selected = []
        temp_users = user_scores.copy()
        
        for _ in range(min(winners_count, len(temp_users))):
            if not temp_users:
                break
                
            tournament_size = min(3, len(temp_users))
            tournament = random.sample(temp_users, tournament_size)
            winner = max(tournament, key=lambda x: x[1])
            
            temp_users = [u for u in temp_users if u[0] != winner[0]]
            selected.append(winner[0])
            
        return selected
        
    def _calculate_ai_score(self, user_id):
        try:
            cursor = db.execute(user_id,
                """SELECT total_participations, wins_count, last_win_date, created_at 
                   FROM users WHERE user_id = ?""",
                (user_id,)
            )
            user_data = cursor.fetchone()
            
            if not user_data:
                return 1
                
            score = 50
            
            if user_data['total_participations'] > 0:
                score += min(user_data['total_participations'] * 2, 30)
                
            if user_data['wins_count'] > 0:
                score -= user_data['wins_count'] * 15
                
            if user_data['last_win_date']:
                try:
                    last_win = datetime.strptime(user_data['last_win_date'], '%Y-%m-%d')
                    days_since_win = (datetime.now() - last_win).days
                    if days_since_win < 3:
                        score *= 0.2
                    elif days_since_win < 7:
                        score *= 0.5
                    elif days_since_win < 14:
                        score *= 0.7
                except:
                    pass
                    
            if user_data['created_at']:
                try:
                    created = datetime.strptime(user_data['created_at'], '%Y-%m-%d %H:%M:%S')
                    days_old = (datetime.now() - created).days
                    if days_old > 30:
                        score += min(days_old / 10, 20)
                except:
                    pass
                    
            return max(1, int(score))
            
        except Exception as e:
            logger.error(f"Error calculating AI score for {user_id}: {e}")
            return 1
            
    def _save_lottery(self, winners_count, prize_per_winner, winners):
        try:
            total_prize = winners_count * prize_per_winner
            cursor = db.execute(0,
                """INSERT INTO lotteries 
                   (winners_count, prize_per_winner, total_prize, status, started_at) 
                   VALUES (?, ?, ?, 'running', CURRENT_TIMESTAMP)""",
                (winners_count, prize_per_winner, total_prize)
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving lottery: {e}")
            return None
            
    def _save_winners(self, lottery_id, winners, prize_amount):
        try:
            for user_id in winners:
                cursor = db.execute(user_id,
                    "SELECT wallet_address FROM users WHERE user_id = ?",
                    (user_id,)
                )
                user_data = cursor.fetchone()
                wallet_address = user_data['wallet_address'] if user_data else None
                
                db.execute(user_id,
                    """INSERT INTO winners 
                       (lottery_id, user_id, prize_amount, wallet_address, paid_status) 
                       VALUES (?, ?, ?, ?, 0)""",
                    (lottery_id, user_id, prize_amount, wallet_address)
                )
            return True
        except Exception as e:
            logger.error(f"Error saving winners: {e}")
            return False
            
    def _update_winner_stats(self, user_id):
        try:
            db.execute(user_id,
                """UPDATE users 
                   SET wins_count = wins_count + 1, 
                       last_win_date = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP 
                   WHERE user_id = ?""",
                (user_id,)
            )
        except Exception as e:
            logger.error(f"Error updating winner stats for {user_id}: {e}")

lottery_system = LotterySystem()

# ============================================================
# سیستم مدیریت کاربران با پایداری بالا
# ============================================================
class UserManager:
    @staticmethod
    def register_user(user_id, username=None, first_name=None, last_name=None):
        try:
            cursor = db.execute(user_id,
                "SELECT user_id FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not cursor.fetchone():
                referral_code = UserManager._generate_referral_code(user_id)
                db.execute(user_id,
                    """INSERT INTO users 
                       (user_id, username, first_name, last_name, referral_code, language) 
                       VALUES (?, ?, ?, ?, ?, 'en')""",
                    (user_id, username, first_name, last_name, referral_code)
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            return False
            
    @staticmethod
    def _generate_referral_code(user_id):
        base = f"UTYOB_{user_id}_{time.time()}_{random.randint(1000, 9999)}"
        hash_obj = hashlib.sha256(base.encode())
        return hash_obj.hexdigest()[:10].upper()
        
    @staticmethod
    def get_user(user_id):
        cache_key = f"user_{user_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
            
        try:
            cursor = db.execute(user_id,
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            if result:
                cache.set(cache_key, result, ttl=60)
            return result
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
            
    @staticmethod
    def update_user(user_id, **kwargs):
        try:
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            db.execute(user_id,
                f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values
            )
            cache.delete(f"user_{user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
            
    @staticmethod
    def get_user_count():
        try:
            total = 0
            for conn in db.connections.values():
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM users")
                total += cursor.fetchone()['count']
            return total
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0
            
    @staticmethod
    def get_active_users():
        try:
            results = db.execute_global(
                """SELECT user_id FROM users 
                   WHERE has_subscription = 1 
                   AND subscription_end >= date('now')"""
            )
            return [row['user_id'] for row in results]
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
            
    @staticmethod
    def get_all_users():
        try:
            results = db.execute_global("SELECT user_id, username, first_name FROM users")
            return results
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

user_manager = UserManager()

# ============================================================
# مدیریت دانلود از اینستاگرام و یوتیوب
# ============================================================
class DownloadManager:
    """مدیریت دانلود از اینستاگرام و یوتیوب"""
    
    @staticmethod
    async def download_instagram(url: str) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """دانلود پست یا استوری اینستاگرام"""
        if Instaloader is None or Post is None:
            return False, None, "Instaloader not installed. Please install: pip install instaloader"
            
        try:
            temp_dir = tempfile.mkdtemp()
            
            loader = Instaloader(
                download_pictures=True,
                download_videos=True,
                download_video_thumbnails=False,
                compress_json=False,
                save_metadata=False,
                post_metadata_txt_pattern="",
                max_connection_attempts=3,
                dirname_pattern=temp_dir
            )
            
            shortcode = re.search(r'(?:p|reel|tv)/([^/?]+)', url)
            if not shortcode:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, None, "Invalid Instagram URL"
            
            post = Post.from_shortcode(loader.context, shortcode.group(1))
            
            loader.download_post(post, target=f"{temp_dir}/post")
            
            files = os.listdir(temp_dir)
            if not files:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, None, "No media found"
            
            media_file = None
            for f in files:
                if f.endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov')):
                    media_file = os.path.join(temp_dir, f)
                    break
            
            if not media_file:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, None, "No media file found"
            
            with open(media_file, 'rb') as f:
                file_data = f.read()
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True, file_data, os.path.basename(media_file)
            
        except Exception as e:
            logger.error(f"Instagram download error: {e}")
            return False, None, str(e)
    
    @staticmethod
    async def download_youtube(url: str) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """دانلود ویدیو از یوتیوب"""
        if yt_dlp is None:
            return False, None, "yt-dlp not installed. Please install: pip install yt-dlp"
            
        try:
            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, 'video.mp4')
            
            ydl_opts = {
                'outtmpl': output_path,
                'format': 'best[height<=720]',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if not os.path.exists(output_path):
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, None, "Download failed"
            
            with open(output_path, 'rb') as f:
                file_data = f.read()
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True, file_data, 'video.mp4'
            
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            return False, None, str(e)

# ============================================================
# کلاس اصلی ربات با سرعت بالا
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.pending_verifications = {}
        self.executor = ThreadPoolExecutor(max_workers=50)
        self._setup_handlers()
        self._init_system()
        
    def _init_system(self):
        try:
            cursor = db.execute(0, "SELECT value FROM settings WHERE key = 'system_initialized'")
            if not cursor.fetchone():
                db.execute(0, "INSERT INTO settings (key, value) VALUES ('system_initialized', 'true')")
                logger.info("سیستم برای اولین بار مقداردهی شد")
            else:
                logger.info("سیستم قبلاً مقداردهی شده - داده‌ها حفظ شدند")
        except Exception as e:
            logger.error(f"Error initializing system: {e}")
            
    def _setup_handlers(self):
        app = self.application
        
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("referral", self.referral_command))
        app.add_handler(CommandHandler("language", self.language_command))
        
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language$"))
        
        app.add_handler(CallbackQueryHandler(self.subscribe_callback, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.confirm_subscribe_callback, pattern="^confirm_subscribe$"))
        
        app.add_handler(CallbackQueryHandler(self.join_lottery_callback, pattern="^join_lottery$"))
        app.add_handler(CallbackQueryHandler(self.confirm_payment_callback, pattern="^confirm_payment$"))
        
        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_start_lottery_callback, pattern="^admin_start_lottery$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_poll_callback, pattern="^admin_poll$"))
        app.add_handler(CallbackQueryHandler(self.admin_pay_winners_callback, pattern="^admin_pay_winners$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api_callback, pattern="^admin_add_api$"))
        app.add_handler(CallbackQueryHandler(self.admin_stats_callback, pattern="^admin_stats$"))
        
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))
        
        app.add_handler(CallbackQueryHandler(self.start_lottery_confirm_callback, pattern="^start_lottery_confirm$"))
        app.add_handler(CallbackQueryHandler(self.start_lottery_final_callback, pattern="^start_lottery_final$"))
        
        app.add_handler(CallbackQueryHandler(self.withdraw_prize_callback, pattern="^withdraw_prize$"))
        app.add_handler(CallbackQueryHandler(self.confirm_withdraw_callback, pattern="^confirm_withdraw$"))
        
        app.add_handler(CallbackQueryHandler(self.set_language_callback, pattern="^set_lang_"))
        
        # دکمه‌های جدید دانلودر و فاکتور
        app.add_handler(CallbackQueryHandler(self.download_instagram_callback, pattern="^download_instagram$"))
        app.add_handler(CallbackQueryHandler(self.download_youtube_callback, pattern="^download_youtube$"))
        app.add_handler(CallbackQueryHandler(self.create_invoice_callback, pattern="^create_invoice$"))
        
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        app.add_error_handler(self.error_handler)

    # ============================================================
    # توابع کمکی
    # ============================================================
    
    def _get_user_language(self, user_id):
        user = user_manager.get_user(user_id)
        if user and user['language']:
            return user['language']
        return 'en'
    
    def _set_user_language(self, user_id, lang_code):
        if lang_code in LanguageManager.LANGUAGES:
            user_manager.update_user(user_id, language=lang_code)
            return True
        return False
    
    def _get_text(self, user_id, key, *args, **kwargs):
        lang = self._get_user_language(user_id)
        return LanguageManager.get_text(lang, key, *args, **kwargs)
    
    def _validate_wallet_address(self, address):
        try:
            if len(address) != 34:
                return False
            valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
            if not all(c in valid_chars for c in address):
                return False
            try:
                decoded = base58.b58decode(address)
                return True
            except:
                return False
        except Exception as e:
            logger.error(f"Error validating address: {e}")
            return False
    
    def _validate_tx_hash(self, tx_hash):
        try:
            if len(tx_hash) != 64:
                return False
            if not all(c in '0123456789abcdefABCDEF' for c in tx_hash):
                return False
            return True
        except:
            return False
    
    async def _auto_verify_payment(self, user_id, from_address, to_address, amount):
        try:
            cache_key = f"payment_{from_address}_{to_address}_{amount}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            success, tx_id, message = await payment_verifier.verify_transaction(
                from_address, to_address, amount
            )
            
            if success:
                db.execute(user_id,
                    """INSERT INTO transactions 
                       (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
                       VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)""",
                    (user_id, from_address, to_address, amount, tx_id)
                )
                
                db.execute(user_id,
                    "UPDATE users SET total_participations = total_participations + 1 WHERE user_id = ?",
                    (user_id,)
                )
                
                result = {'success': True, 'tx_id': tx_id, 'message': 'Verified'}
            else:
                db.execute(user_id,
                    """INSERT INTO transactions 
                       (user_id, from_address, to_address, amount, status) 
                       VALUES (?, ?, ?, ?, 'failed')""",
                    (user_id, from_address, to_address, amount)
                )
                
                result = {'success': False, 'tx_id': None, 'message': message or 'Verification failed'}
            
            cache.set(cache_key, result, ttl=60)
            return result
            
        except Exception as e:
            logger.error(f"Error in auto verify payment: {e}")
            return {'success': False, 'tx_id': None, 'message': str(e)}
    
    def _get_pending_transactions(self):
        results = db.execute_global(
            "SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC"
        )
        return results
    
    def _get_unpaid_winners(self):
        results = db.execute_global(
            "SELECT * FROM winners WHERE paid_status = 0 ORDER BY created_at ASC"
        )
        return results
    
    def _check_winner(self, user_id):
        cursor = db.execute(user_id,
            """SELECT * FROM winners 
               WHERE user_id = ? 
               AND paid_status = 0 
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,)
        )
        return cursor.fetchone()
    
    def _get_transaction_stats(self):
        results = db.execute_global(
            "SELECT status, COUNT(*) as count FROM transactions GROUP BY status"
        )
        stats = {'total': 0, 'verified': 0, 'pending': 0, 'failed': 0}
        for row in results:
            stats['total'] += row['count']
            if row['status'] == 'verified':
                stats['verified'] += row['count']
            elif row['status'] == 'pending':
                stats['pending'] += row['count']
            elif row['status'] == 'failed':
                stats['failed'] += row['count']
        return stats
    
    def _get_lottery_stats(self):
        cursor = db.execute(0, "SELECT COUNT(*) as total FROM lotteries")
        total = cursor.fetchone()['total']
        
        cursor = db.execute(0, "SELECT COUNT(*) as total_winners FROM winners")
        total_winners = cursor.fetchone()['total_winners']
        
        cursor = db.execute(0, "SELECT started_at FROM lotteries ORDER BY started_at DESC LIMIT 1")
        last = cursor.fetchone()
        
        return {
            'total': total,
            'total_winners': total_winners,
            'last': last['started_at'] if last else None
        }
    
    async def _get_winner_amount(self, user_id):
        cursor = db.execute(user_id,
            "SELECT prize_amount FROM winners WHERE user_id = ? AND paid_status = 0",
            (user_id,)
        )
        result = cursor.fetchone()
        return result['prize_amount'] if result else 0

    # ============================================================
    # دستورات عمومی
    # ============================================================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        user_manager.register_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name
        )
        
        lang = self._get_user_language(user.id)
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'play_button'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'welcome'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'guide_text'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await self._show_referral(update, user_id)
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await self._show_language_selector(update, user_id)

    # ============================================================
    # کالبک‌های منوی اصلی با دکمه‌های جدید
    # ============================================================
    
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'lottery'),
                callback_data="lottery"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'referral'),
                callback_data="referral"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'guide'),
                callback_data="guide"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'download_instagram'),
                callback_data="download_instagram"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'download_youtube'),
                callback_data="download_youtube"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'invoice_button'),
                callback_data="create_invoice"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'language'),
                callback_data="language"
            )]
        ]
        
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton(
                LanguageManager.get_text(lang, 'admin_panel'),
                callback_data="admin_panel"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'main_menu'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if not user or not user['has_subscription']:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'subscribe'),
                    callback_data="subscribe"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'back'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_subscription'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'lottery'),
                callback_data="join_lottery"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎰 **UTYOB {LanguageManager.get_text(lang, 'lottery')}**\n\n"
            f"👤 User: {user['first_name'] or user_id}\n\n"
            f"💰 Prize: Up to $10,000\n"
            f"🎯 Fair: Yes",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def referral_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        await self._show_referral(update, user_id)
    
    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'guide_text'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        await self._show_language_selector(update, user_id)
    
    async def set_language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang_code = query.data.replace('set_lang_', '')
        
        if self._set_user_language(user_id, lang_code):
            lang = self._get_user_language(user_id)
            
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'main_menu_btn'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Language changed to {LanguageManager.get_language_name(lang_code)}!\n\n"
                f"🌐 زبان به {LanguageManager.get_language_name(lang_code)} تغییر یافت!",
                reply_markup=reply_markup
            )

    # ============================================================
    # کالبک‌های دانلودر
    # ============================================================
    
    async def download_instagram_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """کالبک دانلود اینستاگرام"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        context.user_data['download_type'] = 'instagram'
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'send_link_instagram'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def download_youtube_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """کالبک دانلود یوتیوب"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        context.user_data['download_type'] = 'youtube'
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'send_link_youtube'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def create_invoice_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """کالبک ساخت فاکتور - باز کردن لینک مستقیم"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        invoice_url = "https://mbuiop.github.io/Tablikgram/"
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'open_invoice'),
                url=invoice_url
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'invoice_description'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های اشتراک
    # ============================================================
    
    async def subscribe_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if user and user['has_subscription']:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ شما قبلاً اشتراک فعال دارید!",
                reply_markup=reply_markup
            )
            return
        
        context.user_data['waiting_for_subscribe'] = True
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'cancel'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'subscribe_wallet', DESTINATION_WALLET),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def confirm_subscribe_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if not user or not user['wallet_address']:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'subscribe_wallet', DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'verifying'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        success, tx_id, message = await payment_verifier.verify_transaction(
            user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT
        )
        
        if success:
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            db.execute(user_id,
                "UPDATE users SET has_subscription = 1, subscription_end = ? WHERE user_id = ?",
                (end_date, user_id)
            )
            
            db.execute(user_id,
                """INSERT INTO transactions 
                   (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
                   VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)""",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'lottery'),
                    callback_data="lottery"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'main_menu_btn'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'subscribe_success', PAYMENT_AMOUNT, tx_id),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        chat_id=admin_id,
                        text=f"✅ New subscription!\nUser: {user_id}\nAmount: ${PAYMENT_AMOUNT}\nTx: {tx_id}"
                    )
                except:
                    pass
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['subscription_from_address'] = user['wallet_address']
            
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'cancel'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'subscribe_failed', message),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های شرکت در قرعه‌کشی
    # ============================================================
    
    async def join_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if not user or not user['has_subscription']:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'subscribe'),
                    callback_data="subscribe"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'back'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_subscription'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        context.user_data['waiting_for_wallet'] = True
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'cancel'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'enter_wallet_short'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def confirm_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if not user or not user['wallet_address']:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'enter_wallet_short'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'verifying'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        result = await self._auto_verify_payment(
            user_id,
            user['wallet_address'],
            DESTINATION_WALLET,
            PAYMENT_AMOUNT
        )
        
        if result['success']:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'lottery_back'),
                    callback_data="lottery"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'main_menu_btn'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'payment_success', PAYMENT_AMOUNT, result['tx_id']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['payment_from_address'] = user['wallet_address']
            
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'cancel'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'payment_failed', result['message']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های تایید/رد توسط ادمین
    # ============================================================
    
    async def admin_verify_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        
        data = query.data.split('_')
        pending_id = int(data[-1])
        
        cursor = db.execute(0,
            "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'",
            (pending_id,)
        )
        pending = cursor.fetchone()
        
        if not pending:
            await query.edit_message_text("❌ درخواست یافت نشد یا قبلاً بررسی شده است.")
            return
        
        user_id = pending['user_id']
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        db.execute(user_id,
            "UPDATE users SET has_subscription = 1, subscription_end = ? WHERE user_id = ?",
            (end_date, user_id)
        )
        
        db.execute(user_id,
            """INSERT INTO transactions 
               (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
               VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)""",
            (user_id, pending['from_address'], pending['to_address'], pending['amount'], pending['tx_hash'])
        )
        
        db.execute(0,
            "UPDATE pending_verifications SET status = 'approved' WHERE id = ?",
            (pending_id,)
        )
        
        user_lang = self._get_user_language(user_id)
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(user_lang, 'lottery'),
                callback_data="lottery"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(user_lang, 'main_menu_btn'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=LanguageManager.get_text(user_lang, 'user_verify_approved', pending['tx_hash']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error sending to user {user_id}: {e}")
        
        await query.edit_message_text(
            LanguageManager.get_text('fa', 'admin_verify_approved',
                user_id, pending['amount'], pending['tx_hash']
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        
        for admin in ADMIN_IDS:
            if admin != admin_id:
                try:
                    await self.application.bot.send_message(
                        chat_id=admin,
                        text=f"✅ تراکنش توسط ادمین {admin_id} تایید شد!\n👤 کاربر: {user_id}"
                    )
                except:
                    pass
    
    async def admin_verify_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        
        data = query.data.split('_')
        pending_id = int(data[-1])
        
        cursor = db.execute(0,
            "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'",
            (pending_id,)
        )
        pending = cursor.fetchone()
        
        if not pending:
            await query.edit_message_text("❌ درخواست یافت نشد یا قبلاً بررسی شده است.")
            return
        
        user_id = pending['user_id']
        
        db.execute(0,
            "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?",
            (pending_id,)
        )
        
        user_lang = self._get_user_language(user_id)
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(user_lang, 'retry'),
            callback_data="subscribe"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=LanguageManager.get_text(user_lang, 'user_verify_rejected', pending['tx_hash']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error sending to user {user_id}: {e}")
        
        await query.edit_message_text(
            LanguageManager.get_text('fa', 'admin_verify_rejected',
                user_id, pending['tx_hash']
            ),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های پنل مدیریت
    # ============================================================
    
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=reply_markup)
            return
        
        user_count = user_manager.get_user_count()
        active_users = len(user_manager.get_active_users())
        cache_stats = cache.get_stats()
        
        users_list = user_manager.get_all_users()
        users_text = ""
        for user in users_list[:10]:
            users_text += f"• {user['user_id']} - {user['first_name'] or user['username'] or 'Unknown'}\n"
        if len(users_list) > 10:
            users_text += f"... و {len(users_list) - 10} نفر دیگر"
        
        pending_count = len(self._get_pending_transactions())
        unpaid_winners = len(self._get_unpaid_winners())
        
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton(f"✅ تایید دستی ({pending_count})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📊 ارسال نظرسنجی", callback_data="admin_poll")],
            [InlineKeyboardButton(f"💰 واریز به برندگان ({unpaid_winners})", callback_data="admin_pay_winners")],
            [InlineKeyboardButton("🔑 اضافه کردن API", callback_data="admin_add_api")],
            [InlineKeyboardButton("📈 آمار و اطلاعات", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"⚙️ **پنل مدیریت**\n\n"
            f"📊 **آمار:**\n"
            f"👥 کل کاربران: {user_count:,}\n"
            f"✅ اشتراک فعال: {active_users:,}\n"
            f"⏳ در انتظار تایید: {pending_count}\n"
            f"💰 برندگان پرداخت نشده: {unpaid_winners}\n"
            f"🔑 کلیدهای API: {len(payment_verifier.apis)}\n\n"
            f"👥 **لیست کاربران:**\n{users_text}\n\n"
            f"انتخاب کنید:"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['admin_action'] = 'broadcast'
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📢 **ارسال پیام همگانی**\n\n"
            "لطفاً متن پیام را ارسال کنید:\n\n"
            "⚠️ این پیام به تمام کاربران ارسال می‌شود.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_start_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        if lottery_system.is_running:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("⚠️ قرعه‌کشی در حال اجراست!", reply_markup=reply_markup)
            return
        
        context.user_data['admin_action'] = 'start_lottery'
        context.user_data['lottery_step'] = 1
        
        eligible = lottery_system._get_eligible_users()
        
        keyboard = [
            [InlineKeyboardButton("✅ تایید شروع", callback_data="start_lottery_confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎰 **شروع قرعه‌کشی جدید**\n\n"
            f"👥 کاربران واجد شرایط: {len(eligible)} نفر\n\n"
            f"آیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟\n\n"
            f"⚠️ **توجه:**\n"
            f"• تمام کاربران دارای اشتراک شرکت می‌کنند\n"
            f"• برندگان قبلی شانس کمتری دارند\n"
            f"• قرعه‌کشی به صورت عادلانه انجام می‌شود",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        pending = self._get_pending_transactions()
        
        if not pending:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ همه تراکنش‌ها تایید شده‌اند!", reply_markup=reply_markup)
            return
        
        text = "✅ **تایید دستی تراکنش‌ها**\n\n"
        for p in pending[:5]:
            text += f"🆔 #{p['id']} - 👤 کاربر: {p['user_id']}\n"
            text += f"💰 مبلغ: ${p['amount']}\n"
            text += f"🔗 هش: `{p['tx_hash'][:20]}...`\n\n"
        
        text += f"📊 تعداد کل: {len(pending)}\n\n"
        text += "برای تایید یا رد هر تراکنش، از دکمه‌های زیر استفاده کنید:"
        
        keyboard = []
        for p in pending[:5]:
            keyboard.append([
                InlineKeyboardButton(
                    f"✅ تایید #{p['id']}",
                    callback_data=f"admin_verify_approve_{p['id']}"
                ),
                InlineKeyboardButton(
                    f"❌ رد #{p['id']}",
                    callback_data=f"admin_verify_reject_{p['id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_poll_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['admin_action'] = 'poll'
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 **ارسال نظرسنجی**\n\n"
            "لطفاً متن نظرسنجی را ارسال کنید:\n\n"
            "⚠️ این نظرسنجی به تمام کاربران ارسال می‌شود.\n"
            "✅ دو دکمه **بله** و **خیر** به آن اضافه می‌شود.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_pay_winners_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        winners = self._get_unpaid_winners()
        
        if not winners:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ همه برندگان پرداخت شده‌اند!", reply_markup=reply_markup)
            return
        
        text = "💰 **واریز به برندگان**\n\n"
        for winner in winners:
            text += f"👤 کاربر: {winner['user_id']}\n"
            text += f"💰 مبلغ: ${winner['prize_amount']}\n"
            text += f"📤 آدرس: {winner['wallet_address'] or 'نامشخص'}\n"
            text += f"🏆 قرعه‌کشی: #{winner['lottery_id']}\n\n"
        
        text += f"📊 تعداد کل: {len(winners)}\n\n"
        text += "برای پرداخت، از پنل مدیریت استفاده کنید."
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['admin_action'] = 'add_api'
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔑 **اضافه کردن API جدید**\n\n"
            "لطفاً کلید API جدید را وارد کنید:\n\n"
            "⚠️ **نکات:**\n"
            "• API برای تایید تراکنش‌ها استفاده می‌شود\n"
            "• هر API می‌تواند هزاران کاربر را پوشش دهد\n"
            "• API‌های بیشتر = سرعت بیشتر",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        user_count = user_manager.get_user_count()
        active_users = len(user_manager.get_active_users())
        cache_stats = cache.get_stats()
        tx_stats = self._get_transaction_stats()
        lottery_stats = self._get_lottery_stats()
        
        users_list = user_manager.get_all_users()
        users_text = ""
        for user in users_list[:10]:
            users_text += f"• {user['user_id']} - {user['first_name'] or user['username'] or 'Unknown'}\n"
        if len(users_list) > 10:
            users_text += f"... و {len(users_list) - 10} نفر دیگر"
        
        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"📊 **آمار کامل سیستم**\n\n"
            f"👥 **کاربران:**\n"
            f"• کل: {user_count:,}\n"
            f"• فعال: {active_users:,}\n"
            f"• درصد فعال: {(active_users/user_count*100) if user_count > 0 else 0:.1f}%\n\n"
            f"💳 **تراکنش‌ها:**\n"
            f"• کل: {tx_stats['total']:,}\n"
            f"• تایید شده: {tx_stats['verified']:,}\n"
            f"• در انتظار: {tx_stats['pending']:,}\n\n"
            f"🎰 **قرعه‌کشی:**\n"
            f"• تعداد: {lottery_stats['total']}\n"
            f"• برندگان کل: {lottery_stats['total_winners']}\n"
            f"• آخرین: {lottery_stats['last'] or 'ندارد'}\n\n"
            f"⚡ **سیستم:**\n"
            f"• کش: {cache_stats['size']} آیتم\n"
            f"• نرخ برخورد: {cache_stats['hit_rate']:.1f}%\n"
            f"• API‌ها: {len(payment_verifier.apis)}\n"
            f"• شاردها: {DB_SHARDS}\n"
            f"• رشته‌های اجرایی: ۵۰\n\n"
            f"👥 **لیست کاربران:**\n{users_text}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های مراحل قرعه‌کشی
    # ============================================================
    
    async def start_lottery_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['lottery_step'] = 2
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 **تعداد برندگان**\n\n"
            "لطفاً تعداد برندگان این قرعه‌کشی را وارد کنید:\n"
            "(حداکثر ۱۰۰ نفر)\n\n"
            "مثال: `5`",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def start_lottery_final_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        winners_count = context.user_data.get('lottery_winners', 1)
        prize_per_winner = context.user_data.get('lottery_prize', 100)
        
        success, result = lottery_system.start_lottery(winners_count, prize_per_winner)
        
        if success:
            for winner_id in result['winners']:
                winner_lang = self._get_user_language(winner_id)
                keyboard = [
                    [InlineKeyboardButton(
                        LanguageManager.get_text(winner_lang, 'withdraw_prize'),
                        callback_data="withdraw_prize"
                    )],
                    [InlineKeyboardButton(
                        LanguageManager.get_text(winner_lang, 'next_lottery'),
                        callback_data="main_menu"
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await self.application.bot.send_message(
                        chat_id=winner_id,
                        text=f"🎉 **تبریک! شما برنده قرعه‌کشی شدید!**\n\n💰 مبلغ جایزه: ${prize_per_winner:,}\n🏆 شماره قرعه‌کشی: {result['lottery_id']}\n\nبرای برداشت جایزه خود روی دکمه زیر کلیک کنید:",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Error sending to {winner_id}: {e}")
            
            winners_list = "\n".join([f"• کاربر {uid}" for uid in result['winners']])
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ **قرعه‌کشی با موفقیت انجام شد!** 🎉\n\n"
                f"📊 **جزئیات:**\n"
                f"• شماره قرعه‌کشی: {result['lottery_id']}\n"
                f"• تعداد برندگان: {winners_count}\n"
                f"• جایزه هر نفر: ${prize_per_winner:,}\n"
                f"• کل جایزه: ${winners_count * prize_per_winner:,}\n\n"
                f"👥 **برندگان:**\n{winners_list}\n\n"
                f"✅ پیام‌های تبریک به برندگان ارسال شد.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="admin_start_lottery")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"❌ **خطا در اجرای قرعه‌کشی**\n\n"
                f"🔹 دلیل: {result}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های برداشت جایزه
    # ============================================================
    
    async def withdraw_prize_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        winner = self._check_winner(user_id)
        if not winner:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'lottery'),
                    callback_data="lottery"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'main_menu_btn'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_winner'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if winner['paid_status'] == 1:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'main_menu_btn'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'already_paid',
                    winner['prize_amount'], winner['paid_at']
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        context.user_data['withdraw_pending'] = True
        context.user_data['winner_id'] = winner['id']
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'cancel'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'enter_withdraw_wallet', winner['prize_amount']),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def confirm_withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if not context.user_data.get('withdraw_pending'):
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'main_menu_btn'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⚠️ No pending withdrawal.",
                reply_markup=reply_markup
            )
            return
        
        user = user_manager.get_user(user_id)
        if not user or not user['wallet_address']:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ No wallet address found!",
                reply_markup=reply_markup
            )
            return
        
        winner_id = context.user_data.get('winner_id')
        if winner_id:
            db.execute(user_id,
                """UPDATE winners 
                   SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (user['wallet_address'], winner_id)
            )
            
            context.user_data['withdraw_pending'] = False
            
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'next_lottery'),
                    callback_data="lottery"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'main_menu_btn'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'withdraw_success',
                    await self._get_winner_amount(user_id),
                    user['wallet_address']
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        chat_id=admin_id,
                        text=f"💰 Withdrawal request\nUser: {user_id}\nAmount: ${await self._get_winner_amount(user_id)}\nAddress: {user['wallet_address']}"
                    )
                except:
                    pass

    # ============================================================
    # نمایش اطلاعات
    # ============================================================
    
    async def _show_referral(self, update, user_id):
        user = user_manager.get_user(user_id)
        if not user:
            return
        
        lang = self._get_user_language(user_id)
        referral_code = user['referral_code']
        bot_username = "UTYOB_Bot"
        referral_link = f"https://t.me/{bot_username}?start=ref_{referral_code}"
        
        referred_count = len(db.execute_global(
            "SELECT user_id FROM users WHERE referred_by = ?",
            (user_id,)
        ))
        
        text = LanguageManager.get_text(lang, 'referral_text',
            user['first_name'] or user_id,
            referred_count,
            referral_code,
            referral_link
        )
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'share'),
                url=f"https://t.me/share/url?url={referral_link}"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if isinstance(update, Update):
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
    
    async def _show_language_selector(self, update, user_id):
        current_lang = self._get_user_language(user_id)
        lang = current_lang
        
        languages = {
            'en': LanguageManager.get_text(lang, 'name', lang='en'),
            'fa': LanguageManager.get_text(lang, 'name', lang='fa'),
            'tr': LanguageManager.get_text(lang, 'name', lang='tr')
        }
        
        keyboard = []
        for code, name in languages.items():
            if code == current_lang:
                name = f"✅ {name}"
            keyboard.append([InlineKeyboardButton(
                f"{LanguageManager.get_language_emoji(code)} {name}",
                callback_data=f"set_lang_{code}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="main_menu"
        )])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = LanguageManager.get_text(lang, 'language_selector',
            LanguageManager.get_language_name(current_lang)
        )
        
        if isinstance(update, Update):
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

    # ============================================================
    # مدیریت پیام‌ها با پشتیبانی از دانلودر
    # ============================================================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        lang = self._get_user_language(user_id)
        
        # مدیریت دانلود
        download_type = context.user_data.get('download_type')
        if download_type:
            link = text.strip()
            
            is_valid = False
            if download_type == 'instagram':
                is_valid = re.match(r'https?://(www\.)?instagram\.com/(p|reel|tv)/[^/?]+', link) is not None
            elif download_type == 'youtube':
                is_valid = re.match(r'https?://(www\.)?(youtube\.com|youtu\.be)/.+', link) is not None
            
            if not is_valid:
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_link'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            status_msg = await update.message.reply_text(
                LanguageManager.get_text(lang, 'downloading'),
                parse_mode=ParseMode.MARKDOWN
            )
            
            if download_type == 'instagram':
                success, file_data, filename = await DownloadManager.download_instagram(link)
            else:
                success, file_data, filename = await DownloadManager.download_youtube(link)
            
            if success and file_data:
                try:
                    if filename and filename.endswith(('.jpg', '.jpeg', '.png')):
                        await update.message.reply_photo(
                            photo=file_data,
                            caption=f"✅ {LanguageManager.get_text(lang, 'download_success')}"
                        )
                    else:
                        await update.message.reply_video(
                            video=file_data,
                            caption=f"✅ {LanguageManager.get_text(lang, 'download_success')}"
                        )
                except Exception:
                    await update.message.reply_document(
                        document=file_data,
                        filename=filename or 'download',
                        caption=f"✅ {LanguageManager.get_text(lang, 'download_success')}"
                    )
                
                await status_msg.delete()
                context.user_data['download_type'] = None
                
                keyboard = [[InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'main_menu_btn'),
                    callback_data="main_menu"
                )]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'main_menu'),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await status_msg.delete()
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'download_failed'),
                    parse_mode=ParseMode.MARKDOWN
                )
                context.user_data['download_type'] = None
            
            return
        
        # بررسی اقدامات ادمین
        admin_action = context.user_data.get('admin_action')
        
        if admin_action == 'broadcast':
            await self._send_broadcast(update, text, context)
            return
        
        elif admin_action == 'start_lottery':
            await self._handle_lottery_steps(update, text, context)
            return
        
        elif admin_action == 'add_api':
            await self._handle_add_api(update, text, context)
            return
        
        elif admin_action == 'poll':
            await self._send_poll(update, text, context)
            return
        
        # دریافت هش تراکنش برای تایید دستی
        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            
            if not self._validate_tx_hash(tx_hash):
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'tx_hash_invalid'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            from_address = context.user_data.get('subscription_from_address') or context.user_data.get('payment_from_address')
            
            db.execute(0,
                """INSERT INTO pending_verifications 
                   (user_id, from_address, to_address, amount, tx_hash, status) 
                   VALUES (?, ?, ?, ?, ?, 'pending')""",
                (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash)
            )
            
            context.user_data['waiting_for_tx_hash'] = False
            context.user_data['subscription_from_address'] = None
            context.user_data['payment_from_address'] = None
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'tx_hash_received', tx_hash),
                parse_mode=ParseMode.MARKDOWN
            )
            
            pending_id = db.execute(0, "SELECT last_insert_rowid()").fetchone()[0]
            
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "✅ تایید",
                                callback_data=f"admin_verify_approve_{pending_id}"
                            ),
                            InlineKeyboardButton(
                                "❌ رد",
                                callback_data=f"admin_verify_reject_{pending_id}"
                            )
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await self.application.bot.send_message(
                        chat_id=admin_id,
                        text=LanguageManager.get_text('fa', 'admin_verify_tx',
                            user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash
                        ),
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Error sending to admin {admin_id}: {e}")
            
            return
        
        # مرحله 1: دریافت آدرس کیف پول برای اشتراک
        if context.user_data.get('waiting_for_subscribe'):
            wallet_address = text.strip()
            
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_wallet'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            context.user_data['waiting_for_subscribe'] = False
            
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'confirm_subscribe'),
                    callback_data="confirm_subscribe"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'cancel'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'after_subscribe_wallet', wallet_address, DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # مرحله 1: دریافت آدرس کیف پول برای شرکت در قرعه‌کشی
        if context.user_data.get('waiting_for_wallet'):
            wallet_address = text.strip()
            
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_wallet'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            context.user_data['waiting_for_wallet'] = False
            
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'confirm_payment'),
                    callback_data="confirm_payment"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'cancel'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'after_wallet', wallet_address, DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # مرحله برداشت: دریافت آدرس کیف پول
        if context.user_data.get('withdraw_pending'):
            wallet_address = text.strip()
            
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_wallet'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            
            winner_id = context.user_data.get('winner_id')
            if winner_id:
                db.execute(user_id,
                    """UPDATE winners 
                       SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP 
                       WHERE id = ?""",
                    (wallet_address, winner_id)
                )
                
                context.user_data['withdraw_pending'] = False
                
                keyboard = [
                    [InlineKeyboardButton(
                        LanguageManager.get_text(lang, 'next_lottery'),
                        callback_data="lottery"
                    )],
                    [InlineKeyboardButton(
                        LanguageManager.get_text(lang, 'main_menu_btn'),
                        callback_data="main_menu"
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'withdraw_success',
                        await self._get_winner_amount(user_id),
                        wallet_address
                    ),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                for admin_id in ADMIN_IDS:
                    try:
                        await self.application.bot.send_message(
                            chat_id=admin_id,
                            text=f"💰 Withdrawal request\nUser: {user_id}\nAmount: ${await self._get_winner_amount(user_id)}\nAddress: {wallet_address}"
                        )
                    except:
                        pass
            return
        
        # پیام معمولی
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'main_menu_btn'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'invalid_command'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _handle_lottery_steps(self, update, text, context):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        step = context.user_data.get('lottery_step', 1)
        
        if step == 2:
            try:
                winners_count = int(text)
                if 1 <= winners_count <= 100:
                    context.user_data['lottery_winners'] = winners_count
                    context.user_data['lottery_step'] = 3
                    
                    await update.message.reply_text(
                        f"✅ تعداد برندگان: {winners_count}\n\n"
                        f"💰 **مبلغ جایزه هر نفر**\n\n"
                        f"لطفاً مبلغ جایزه برای هر برنده را وارد کنید:\n"
                        f"(حداقل ۱۰ دلار)\n\n"
                        f"مثال: `100`",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        "❌ تعداد نامعتبر!\nلطفاً عددی بین ۱ تا ۱۰۰ وارد کنید."
                    )
            except ValueError:
                await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
        
        elif step == 3:
            try:
                prize = float(text)
                if prize >= 10:
                    context.user_data['lottery_prize'] = prize
                    context.user_data['lottery_step'] = 4
                    
                    winners = context.user_data['lottery_winners']
                    total_prize = winners * prize
                    
                    keyboard = [
                        [InlineKeyboardButton("✅ تایید نهایی", callback_data="start_lottery_final")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"✅ **اطلاعات قرعه‌کشی:**\n\n"
                        f"• تعداد برندگان: {winners}\n"
                        f"• جایزه هر نفر: ${prize:,}\n"
                        f"• کل جایزه: ${total_prize:,}\n\n"
                        f"⚠️ آیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟",
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text("❌ مبلغ جایزه باید حداقل ۱۰ دلار باشد!")
            except ValueError:
                await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
    
    async def _handle_add_api(self, update, text, context):
        user_id = update.effective_user.id
        api_key = text.strip()
        
        if payment_verifier.add_api(api_key):
            context.user_data['admin_action'] = None
            await update.message.reply_text(
                f"✅ **API جدید با موفقیت اضافه شد!**\n\n"
                f"🔑 کلید: `{api_key}`\n"
                f"📊 تعداد کل API‌ها: {len(payment_verifier.apis)}\n\n"
                f"این API برای تایید تراکنش‌ها استفاده می‌شود.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "❌ **خطا در اضافه کردن API!**\n\n"
                "این API قبلاً اضافه شده است یا نامعتبر است.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _send_poll(self, update, text, context):
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "⏳ در حال ارسال نظرسنجی به کاربران...\nلطفاً صبر کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        users = db.execute_global("SELECT user_id, language FROM users")
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                user_lang = user['language'] if user['language'] else 'en'
                
                keyboard = [
                    [
                        InlineKeyboardButton(
                            LanguageManager.get_text(user_lang, 'poll_option_1'),
                            callback_data="poll_yes"
                        ),
                        InlineKeyboardButton(
                            LanguageManager.get_text(user_lang, 'poll_option_2'),
                            callback_data="poll_no"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.application.bot.send_message(
                    chat_id=user['user_id'],
                    text=LanguageManager.get_text(user_lang, 'poll_message', text),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                if sent % 30 == 0:
                    await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Error sending poll to {user['user_id']}: {e}")
                failed += 1
        
        context.user_data['admin_action'] = None
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **ارسال نظرسنجی کامل شد!**\n\n"
            f"📤 ارسال شده: {sent:,}\n"
            f"❌ ناموفق: {failed:,}\n"
            f"📊 کل: {sent + failed:,}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _send_broadcast(self, update, text, context):
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "⏳ در حال ارسال پیام به کاربران...\nلطفاً صبر کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        users = db.execute_global("SELECT user_id FROM users")
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await self.application.bot.send_message(
                    chat_id=user['user_id'],
                    text=text,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                if sent % 30 == 0:
                    await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Error sending to {user['user_id']}: {e}")
                failed += 1
        
        context.user_data['admin_action'] = None
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **ارسال پیام همگانی کامل شد!**\n\n"
            f"📤 ارسال شده: {sent:,}\n"
            f"❌ ناموفق: {failed:,}\n"
            f"📊 کل: {sent + failed:,}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'main_menu_btn'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'photo_not_supported'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_user:
                user_id = update.effective_user.id
                lang = self._get_user_language(user_id)
                
                keyboard = [[InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'main_menu_btn'),
                    callback_data="main_menu"
                )]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=LanguageManager.get_text(lang, 'error_message'),
                    reply_markup=reply_markup
                )
        except:
            pass

# ============================================================
# اجرای ربات
# ============================================================

async def main():
    try:
        bot = UTYOBot()
        
        logger.info("🚀 UTYOB Bot starting...")
        logger.info(f"👥 Admins: {len(ADMIN_IDS)}")
        logger.info(f"🗄️ Shards: {DB_SHARDS}")
        logger.info(f"🔑 APIs: {len(TRONGRID_APIS)}")
        logger.info(f"⚡ Threads: 50")
        logger.info(f"💾 Cache size: 20,000 items")
        
        # بررسی نصب کتابخانه‌های دانلودر
        if yt_dlp is None:
            logger.warning("⚠️ yt-dlp not installed! YouTube download will not work.")
            logger.warning("   Install with: pip install yt-dlp")
        else:
            logger.info("✅ yt-dlp installed")
            
        if Instaloader is None:
            logger.warning("⚠️ instaloader not installed! Instagram download will not work.")
            logger.warning("   Install with: pip install instaloader")
        else:
            logger.info("✅ instaloader installed")
        
        await bot.application.initialize()
        await bot.application.start()
        await bot.application.updater.start_polling()
        
        logger.info("✅ Bot started successfully!")
        
        while True:
            await asyncio.sleep(3600)
            
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Program stopped")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")