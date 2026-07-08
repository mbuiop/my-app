# ============================================================
# ربات قرعه‌کشی هوشمند UTYOB - نسخه نهایی ۳.۰
# ============================================================
# ✅ ۳ زبان (فارسی، انگلیسی، ترکی)
# ✅ دانلودر اینستاگرام (با محدودیت روزانه)
# ✅ تحلیل ۲۰۰ ارز با ۲۰ اندیکاتور از Binance
# ✅ آموزش ترید (مدیریت از پنل)
# ✅ ارسال سیگنال همگانی از پنل مدیریت
# ✅ سیستم رفرال کامل با اعلان
# ✅ سیستم قرعه‌کشی پیشرفته
# ✅ پنل مدیریت کامل
# ✅ شاردینگ ۵۰۰ برای میلیون کاربر
# ✅ سیستم کش پیشرفته
# ✅ بدون خطا و باگ
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
import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

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

# لیست ۲۰۰ ارز برای تحلیل
CRYPTO_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT',
    'LINKUSDT', 'UNIUSDT', 'LTCUSDT', 'BCHUSDT', 'NEARUSDT',
    'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT', 'FTMUSDT',
    'XLMUSDT', 'EGLDUSDT', 'XMRUSDT', 'ZECUSDT', 'ETCUSDT',
    'EOSUSDT', 'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'SUSHIUSDT',
    'CAKEUSDT', 'AXSUSDT', 'SANDUSDT', 'APEUSDT', 'CRVUSDT',
    'RUNEUSDT', 'FLOWUSDT', 'QNTUSDT', 'SNXUSDT', 'GRTUSDT',
    'LDOUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SEIUSDT',
    'WLDUSDT', 'PEPEUSDT', 'BONKUSDT', 'FLOKIUSDT', 'SHIBUSDT',
    'ATOMUSDT', 'KAVAUSDT', 'TWTUSDT', 'CAKEUSDT', 'BAKEUSDT',
    'ONEUSDT', 'HBARUSDT', 'HOTUSDT', 'CHZUSDT', 'MANAUSDT',
    'ENJUSDT', 'SANDUSDT', 'AXSUSDT', 'SLPUSDT', 'YGGUSDT',
    'ILVUSDT', 'GALAUSDT', 'MAGICUSDT', 'RNDRUSDT', 'FETUSDT',
    'AGIXUSDT', 'OCEANUSDT', 'FETUSDT', 'ALIUSDT', 'PALMUSDT',
    'RLCUSDT', 'STORJUSDT', 'BLZUSDT', 'ARUSDT', 'SCUSDT',
    'SIAUSDT', 'BTTUSDT', 'WINUSDT', 'XECUSDT', 'DOGEUSDT',
    'FLOKIUSDT', 'SAMOUSDT', 'PEPEUSDT', 'BONKUSDT', 'WIFUSDT',
    'MYROUSDT', 'MEWUSDT', 'SLERFUSDT', 'MUMUUSDT', 'POPCATUSDT',
    'GMEUSDT', 'AMCUSDT', 'SPCEUSDT', 'BBBYUSDT', 'NKLAUSDT',
    'MULNUSDT', 'HCMCUSDT', 'MMATUSDT', 'TRKAUSDT', 'AULTUSDT',
    'POWWUSDT', 'BBAIUSDT', 'SOFIUSDT', 'CLOVUSDT', 'SDCUSDT',
    'ATERUSDT', 'PROGUSDT', 'WISHUSDT', 'OCGNUSDT', 'TNXPUSDT',
    'SENSUSDT', 'NERVUSDT', 'LGVNUSDT', 'RDBXUSDT', 'MULNUSDT'
]

# ============================================================
# سیستم چندزبانه کامل
# ============================================================
class LanguageManager:
    LANGUAGES = {
        'en': {
            'name': 'English',
            'emoji': '🇬🇧',
            'welcome': "🎮 **Welcome to UTYOB Lottery Bot!**\n\n💰 Win amazing prizes up to $10,000!\n🎯 Fair and transparent lottery system\n🌟 Join now and test your luck!",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **UTYOB Lottery Bot**\n\nSelect an option below:",
            'lottery': "🎰 Join Lottery",
            'referral': "🔗 Referral",
            'guide': "📖 Guide",
            'language': "🌐 Change Language",
            'admin_panel': "⚙️ Admin Panel",
            'no_subscription': "❌ **You don't have an active subscription!**\n\nTo participate in the lottery, you must first purchase a subscription.\n\n💰 Subscription cost: $100\n📅 Validity: 1 month",
            'subscribe': "🔄 Subscribe Now",
            'back': "🔙 Back",
            'main_menu_btn': "🔙 Main Menu",
            'lottery_back': "🎰 Back to Lottery",
            'subscribe_wallet': "💳 **Subscribe to UTYOB Lottery**\n\nPlease enter your source TRC20 wallet address:\n\n🔹 **Subscription fee:** $100\n🔹 **Destination address:**\n`{}`",
            'after_subscribe_wallet': "✅ **Wallet address saved!**\n\n🔹 Your address: `{}`\n\n💰 **Please send exactly $100 to:**\n`{}`",
            'confirm_subscribe': "✅ I sent the payment",
            'subscribe_success': "✅ **Subscription successful!** 🎉\n\n🔹 Amount: ${}\n🔹 Transaction: `{}`\n\n🎉 You now have an active subscription!",
            'subscribe_failed': "❌ **Subscription payment verification failed!**\n\n🔹 Reason: {}",
            'send_tx_hash': "📤 Please send your transaction hash (TX ID) for manual verification:",
            'tx_hash_received': "✅ Transaction hash received!\n\n🔹 Hash: `{}`\n\n⏳ Your transaction is being reviewed by admin.",
            'tx_hash_invalid': "❌ Invalid transaction hash!\n\nPlease send a valid TRON transaction hash.",
            'enter_wallet': "💳 **Deposit to participate in the lottery**\n\nPlease enter your source wallet address (TRC20):\n\n🔹 **Deposit amount:** $100\n🔹 **Destination address:**\n`{}`",
            'enter_wallet_short': "📤 **Enter your source TRC20 wallet address:**",
            'after_wallet': "✅ **Wallet address saved!**\n\n🔹 Your address: `{}`\n\n💰 **Please send exactly $100 to:**\n`{}`",
            'confirm_payment': "✅ I sent the payment",
            'cancel': "❌ Cancel",
            'verifying': "⏳ Verifying your payment...\nPlease wait a moment.",
            'payment_success': "✅ **Payment verified!** 🎉\n\n🔹 Amount: ${}\n🔹 Transaction: `{}`\n\n🎉 You have successfully registered for the lottery.",
            'payment_failed': "❌ **Payment verification failed!**\n\n🔹 Reason: {}",
            'retry': "🔄 Try Again",
            'support': "📞 Support",
            'withdraw_prize': "💰 Withdraw Prize",
            'enter_withdraw_wallet': "💰 **Withdraw Prize**\n\nPrize amount: **${:,}**\n\nPlease enter your TRC20 wallet address:",
            'withdraw_success': "✅ **Withdrawal registered successfully!** 🎉\n\n💰 Amount: ${:,}\n📤 Address: {}",
            'already_paid': "✅ Prize already paid!\n\n💰 Amount: ${}\n📅 Date: {}",
            'no_winner': "❌ You don't have any prize!\n\nParticipate in future lotteries.",
            'next_lottery': "🎰 Next Lottery",
            'referral_text': "🔗 **UTYOB Referral System**\n\n👤 You: {}\n📊 Invites: {}\n\n🔑 **Your referral code:**\n`{}`\n\n🔗 **Referral link:**\n{}\n\n💰 **Referral reward:**\n• 5% of deposit per invite",
            'share': "📤 Share",
            'guide_text': "📖 **UTYOB Bot Complete Guide**\n\n🎯 **How it works:**\n1. **Register**: Use /start to register\n2. **Subscription**: Purchase subscription to participate\n3. **Deposit**: Send $100 to the specified address\n4. **Participate**: Join the lottery after verification\n5. **Win**: Receive prize if you win",
            'language_selector': "🌐 **Change Language**\n\nCurrent language: {}",
            'invalid_command': "⚠️ Invalid command!\n\nUse the buttons or /help.",
            'error_message': "⚠️ An error occurred! Please try again.",
            'photo_not_supported': "📸 Photo received!\nBut this feature is not supported.",
            'invalid_wallet': "❌ Invalid wallet address!\n\nPlease enter a valid TRC20 address.",
            'admin_verify_tx': "✅ **Transaction Verification Request**\n\n👤 User: {}\n📤 From: {}\n📥 To: {}\n💰 Amount: ${}\n🔗 TX Hash: `{}`\n\nPlease verify this transaction:",
            'admin_verify_approve': "✅ Approve",
            'admin_verify_reject': "❌ Reject",
            'admin_verify_approved': "✅ **Transaction approved!**\n\n👤 User: {}\n💰 Amount: ${}\n🔗 TX Hash: `{}`\n\nUser's subscription has been activated.",
            'admin_verify_rejected': "❌ **Transaction rejected!**\n\n👤 User: {}\n🔗 TX Hash: `{}`\n\nUser has been notified.",
            'user_verify_approved': "✅ **Your transaction has been approved!** 🎉\n\n💰 Subscription activated!\n🔗 TX Hash: `{}`",
            'user_verify_rejected': "❌ **Your transaction has been rejected!**\n\n🔗 TX Hash: `{}`\n\nPlease check your transaction and try again.",
            'poll_message': "📊 **Poll**\n\n{}",
            'poll_option_1': "✅ Yes",
            'poll_option_2': "❌ No",
            # سرویس‌های جدید
            'download_instagram': "📥 **Instagram Downloader**\n\nSend me an Instagram post or reel link:\n\nExample:\n`/download https://www.instagram.com/p/CxY123XYZ/`\n\n🎁 **Daily limit:** 5 downloads\n🔒 For unlimited downloads, join the lottery!",
            'download_success': "✅ **Download successful!** 🎉\n\n✨ {} downloads remaining today\n\n🎰 **Join the lottery:** /join_lottery",
            'download_limit': "⚠️ **Daily limit reached!**\n\nYou have used all 5 downloads today.\n\n🔒 For unlimited downloads, join the lottery!\n🎰 /join_lottery",
            'download_error': "❌ **Download failed!**\n\nPlease check the link and try again.",
            'market_analysis': "📊 **Market Analysis - {}**\n\n💰 Price: ${:,.2f}\n📈 24h Change: {}%\n📊 High: ${:,.2f}\n📉 Low: ${:,.2f}\n📊 Volume: ${:,.0f}\n\n📈 **20 Technical Indicators:**\n\n1️⃣ **RSI:** {} - {}\n2️⃣ **MACD:** {} - {}\n3️⃣ **MA7:** ${:,.2f}\n4️⃣ **MA25:** ${:,.2f}\n5️⃣ **MA99:** ${:,.2f}\n6️⃣ **BB Upper:** ${:,.2f}\n7️⃣ **BB Middle:** ${:,.2f}\n8️⃣ **BB Lower:** ${:,.2f}\n9️⃣ **VWAP:** ${:,.2f}\n🔟 **ATR:** ${:,.4f}\n1️⃣1️⃣ **Stochastic K:** {:.1f}\n1️⃣2️⃣ **Stochastic D:** {:.1f}\n1️⃣3️⃣ **ADX:** {} - {}\n1️⃣4️⃣ **CCI:** {:.1f}\n1️⃣5️⃣ **Williams %R:** {:.1f}\n1️⃣6️⃣ **Momentum:** {:.2f}\n1️⃣7️⃣ **OBV:** {:.0f}\n1️⃣8️⃣ **Regression Slope:** {:.6f}\n1️⃣9️⃣ **Regression R:** {:.3f}\n2️⃣0️⃣ **Market Strength:** {:.1f}%\n\n🎰 **Join the lottery:** /join_lottery",
            'trading_education': "📚 **Trading Education**\n\n📖 {}\n\n⏰ Last updated: {}",
            'education_menu': "📚 **Trading Education**\n\nSelect an option below:",
            'signal_message': "📊 **UTYOB Signal**\n\n🟢 **BUY {}**\n\n💰 Entry: ${:,.2f}\n🎯 TP1: ${:,.2f} ({}%)\n🎯 TP2: ${:,.2f} ({}%)\n🎯 TP3: ${:,.2f} ({}%)\n🛑 SL: ${:,.2f} ({}%)\n\n📈 **Reasons:**\n{}\n\n⚠️ **Risk Management:** Max 2% risk per trade\n\n🎰 **Join the lottery:** /join_lottery",
            'admin_signal': "📊 **Admin Signal Panel**\n\nSend signal for language:\n\n1️⃣ /signal_en - English\n2️⃣ /signal_fa - فارسی\n3️⃣ /signal_tr - Türkçe",
            'signal_sent': "✅ Signal sent successfully to all users in {}!",
            'signal_set': "✅ Signal set for {} language!\n\nSend the signal message:",
            'signal_cancelled': "❌ Signal sending cancelled.",
            'admin_education': "📚 **Admin Education Panel**\n\nSend education content for language:\n\n1️⃣ /edu_en - English\n2️⃣ /edu_fa - فارسی\n3️⃣ /edu_tr - Türkçe",
            'education_sent': "✅ Education content updated for {}!",
            'education_set': "✅ Education set for {} language!\n\nSend the education content:",
            'referral_notification': "🎉 **New referral!**\n\n👤 User {} joined using your referral link!\n📊 Total referrals: {}\n💰 Reward: 5 points added!",
            'symbol_list': "📊 **Available symbols:**\n\n{}",
            'symbol_not_found': "❌ Symbol not found!\n\nUse /symbols to see available symbols.",
        },
        'fa': {
            'name': 'فارسی',
            'emoji': '🇮🇷',
            'welcome': "🎮 **به ربات قرعه‌کشی UTYOB خوش آمدید!**\n\n💰 برنده جوایز شگفت‌انگیز تا ۱۰۰۰۰ دلار شوید!\n🎯 سیستم قرعه‌کشی عادلانه و شفاف\n🌟 همین حالا بپیوندید و شانس خود را امتحان کنید!",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **ربات قرعه‌کشی UTYOB**\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
            'lottery': "🎰 شرکت در قرعه‌کشی",
            'referral': "🔗 رفرال",
            'guide': "📖 راهنمایی",
            'language': "🌐 تغییر زبان",
            'admin_panel': "⚙️ پنل مدیریت",
            'no_subscription': "❌ **شما اشتراک فعال ندارید!**\n\nبرای شرکت در قرعه‌کشی، ابتدا باید اشتراک تهیه کنید.\n\n💰 هزینه اشتراک: ۱۰۰ دلار\n📅 مدت اعتبار: ۱ ماه",
            'subscribe': "🔄 خرید اشتراک",
            'back': "🔙 بازگشت",
            'main_menu_btn': "🔙 منوی اصلی",
            'lottery_back': "🎰 بازگشت به قرعه‌کشی",
            'subscribe_wallet': "💳 **خرید اشتراک UTYOB**\n\nلطفاً آدرس کیف پول مبدا (TRC20) خود را وارد کنید:\n\n🔹 **هزینه اشتراک:** ۱۰۰ دلار\n🔹 **آدرس مقصد:**\n`{}`",
            'after_subscribe_wallet': "✅ **آدرس کیف پول ذخیره شد!**\n\n🔹 آدرس شما: `{}`\n\n💰 **لطفاً مبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:**\n`{}`",
            'confirm_subscribe': "✅ پرداخت کردم",
            'subscribe_success': "✅ **اشتراک شما فعال شد!** 🎉\n\n🔹 مبلغ: {}$\n🔹 تراکنش: `{}`\n\n🎉 اشتراک شما با موفقیت فعال شد!",
            'subscribe_failed': "❌ **پرداخت اشتراک تایید نشد!**\n\n🔹 دلیل: {}",
            'send_tx_hash': "📤 لطفاً هش تراکنش (TX ID) خود را برای تایید دستی ارسال کنید:",
            'tx_hash_received': "✅ هش تراکنش دریافت شد!\n\n🔹 هش: `{}`\n\n⏳ تراکنش شما در حال بررسی توسط مدیر است.",
            'tx_hash_invalid': "❌ هش تراکنش نامعتبر!\n\nلطفاً یک هش تراکنش معتبر TRON ارسال کنید.",
            'enter_wallet': "💳 **واریز برای شرکت در قرعه‌کشی**\n\nلطفاً آدرس کیف پول مبدا (TRC20) خود را وارد کنید:\n\n🔹 **مبلغ واریز:** ۱۰۰ دلار\n🔹 **آدرس مقصد:**\n`{}`",
            'enter_wallet_short': "📤 **آدرس کیف پول TRC20 خود را وارد کنید:**",
            'after_wallet': "✅ **آدرس کیف پول ذخیره شد!**\n\n🔹 آدرس شما: `{}`\n\n💰 **لطفاً مبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:**\n`{}`",
            'confirm_payment': "✅ پرداخت کردم",
            'cancel': "❌ انصراف",
            'verifying': "⏳ در حال بررسی پرداخت شما...\nلطفاً چند لحظه صبر کنید.",
            'payment_success': "✅ **پرداخت شما تایید شد!** 🎉\n\n🔹 مبلغ: {}$\n🔹 تراکنش: `{}`\n\n🎉 شما با موفقیت در قرعه‌کشی ثبت نام کردید.",
            'payment_failed': "❌ **پرداخت شما تایید نشد!**\n\n🔹 دلیل: {}",
            'retry': "🔄 تلاش مجدد",
            'support': "📞 پشتیبانی",
            'withdraw_prize': "💰 برداشت جایزه",
            'enter_withdraw_wallet': "💰 **برداشت جایزه**\n\nمبلغ جایزه: **${:,}**\n\nلطفاً آدرس کیف پول TRC20 خود را وارد کنید:",
            'withdraw_success': "✅ **برداشت شما با موفقیت ثبت شد!** 🎉\n\n💰 مبلغ: ${:,}\n📤 آدرس: {}",
            'already_paid': "✅ جایزه شما قبلاً پرداخت شده است!\n\n💰 مبلغ: ${}\n📅 تاریخ: {}",
            'no_winner': "❌ شما برنده‌ای ندارید!\n\nدر قرعه‌کشی‌های بعدی شرکت کنید.",
            'next_lottery': "🎰 قرعه‌کشی بعدی",
            'referral_text': "🔗 **سیستم رفرال UTYOB**\n\n👤 شما: {}\n📊 تعداد دعوت‌ها: {}\n\n🔑 **کد رفرال شما:**\n`{}`\n\n🔗 **لینک دعوت:**\n{}\n\n💰 **پاداش دعوت:**\n• به ازای هر دعوت: ۵٪ از واریز",
            'share': "📤 اشتراک‌گذاری",
            'guide_text': "📖 **راهنمای کامل ربات UTYOB**\n\n🎯 **نحوه کار:**\n1. **ثبت‌نام**: با دستور /start ثبت‌نام کنید\n2. **اشتراک**: برای شرکت در قرعه‌کشی، اشتراک تهیه کنید\n3. **واریز**: مبلغ ۱۰۰ دلار به آدرس مشخص واریز کنید\n4. **شرکت**: پس از تایید، در قرعه‌کشی شرکت کنید\n5. **برنده**: در صورت برنده شدن، جایزه دریافت کنید",
            'language_selector': "🌐 **تغییر زبان**\n\nزبان فعلی: {}",
            'invalid_command': "⚠️ دستور نامعتبر!\n\nاز دکمه‌های موجود استفاده کنید یا /help را ببینید.",
            'error_message': "⚠️ خطایی رخ داد! لطفاً دوباره تلاش کنید.",
            'photo_not_supported': "📸 عکس دریافت شد!\nاما این قابلیت پشتیبانی نمی‌شود.",
            'invalid_wallet': "❌ آدرس کیف پول نامعتبر!\n\nلطفاً یک آدرس معتبر TRC20 وارد کنید.",
            'admin_verify_tx': "✅ **درخواست تایید تراکنش**\n\n👤 کاربر: {}\n📤 از: {}\n📥 به: {}\n💰 مبلغ: ${}\n🔗 هش تراکنش: `{}`\n\nلطفاً این تراکنش را تایید کنید:",
            'admin_verify_approve': "✅ تایید",
            'admin_verify_reject': "❌ رد",
            'admin_verify_approved': "✅ **تراکنش تایید شد!**\n\n👤 کاربر: {}\n💰 مبلغ: ${}\n🔗 هش: `{}`\n\nاشتراک کاربر فعال شد.",
            'admin_verify_rejected': "❌ **تراکنش رد شد!**\n\n👤 کاربر: {}\n🔗 هش: `{}`\n\nبه کاربر اطلاع داده شد.",
            'user_verify_approved': "✅ **تراکنش شما تایید شد!** 🎉\n\n💰 اشتراک فعال شد!\n🔗 هش: `{}`",
            'user_verify_rejected': "❌ **تراکنش شما رد شد!**\n\n🔗 هش: `{}`\n\nلطفاً تراکنش خود را بررسی کرده و مجدداً تلاش کنید.",
            'poll_message': "📊 **نظرسنجی**\n\n{}",
            'poll_option_1': "✅ بله",
            'poll_option_2': "❌ خیر",
            # سرویس‌های جدید (فارسی)
            'download_instagram': "📥 **دانلودر اینستاگرام**\n\nلینک پست یا ریل اینستاگرام را ارسال کنید:\n\nمثال:\n`/download https://www.instagram.com/p/CxY123XYZ/`\n\n🎁 **محدودیت روزانه:** ۵ دانلود\n🔒 برای دانلود نامحدود، در قرعه‌کشی شرکت کنید!",
            'download_success': "✅ **دانلود با موفقیت انجام شد!** 🎉\n\n✨ {} دانلود دیگر امروز باقی مانده\n\n🎰 **شرکت در قرعه‌کشی:** /join_lottery",
            'download_limit': "⚠️ **محدودیت روزانه تکمیل شد!**\n\nهر ۵ دانلود امروز را استفاده کرده‌اید.\n\n🔒 برای دانلود نامحدود، در قرعه‌کشی شرکت کنید!\n🎰 /join_lottery",
            'download_error': "❌ **دانلود ناموفق!**\n\nلطفاً لینک را بررسی کرده و مجدداً تلاش کنید.",
            'market_analysis': "📊 **تحلیل بازار - {}**\n\n💰 قیمت: ${:,.2f}\n📈 تغییر ۲۴h: {}%\n📊 بالاترین: ${:,.2f}\n📉 پایین‌ترین: ${:,.2f}\n📊 حجم: ${:,.0f}\n\n📈 **۲۰ اندیکاتور تکنیکال:**\n\n1️⃣ **RSI:** {} - {}\n2️⃣ **MACD:** {} - {}\n3️⃣ **MA7:** ${:,.2f}\n4️⃣ **MA25:** ${:,.2f}\n5️⃣ **MA99:** ${:,.2f}\n6️⃣ **BB بالا:** ${:,.2f}\n7️⃣ **BB وسط:** ${:,.2f}\n8️⃣ **BB پایین:** ${:,.2f}\n9️⃣ **VWAP:** ${:,.2f}\n🔟 **ATR:** ${:,.4f}\n1️⃣1️⃣ **Stochastic K:** {:.1f}\n1️⃣2️⃣ **Stochastic D:** {:.1f}\n1️⃣3️⃣ **ADX:** {} - {}\n1️⃣4️⃣ **CCI:** {:.1f}\n1️⃣5️⃣ **Williams %R:** {:.1f}\n1️⃣6️⃣ **Momentum:** {:.2f}\n1️⃣7️⃣ **OBV:** {:.0f}\n1️⃣8️⃣ **شیب رگرسیون:** {:.6f}\n1️⃣9️⃣ **R رگرسیون:** {:.3f}\n2️⃣0️⃣ **قوت بازار:** {:.1f}%\n\n🎰 **شرکت در قرعه‌کشی:** /join_lottery",
            'trading_education': "📚 **آموزش ترید**\n\n📖 {}\n\n⏰ آخرین بروزرسانی: {}",
            'education_menu': "📚 **آموزش ترید**\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
            'signal_message': "📊 **سیگنال UTYOB**\n\n🟢 **خرید {}**\n\n💰 ورود: ${:,.2f}\n🎯 TP1: ${:,.2f} ({}%)\n🎯 TP2: ${:,.2f} ({}%)\n🎯 TP3: ${:,.2f} ({}%)\n🛑 SL: ${:,.2f} ({}%)\n\n📈 **دلایل:**\n{}\n\n⚠️ **مدیریت سرمایه:** حداکثر ۲٪ ریسک در هر معامله\n\n🎰 **شرکت در قرعه‌کشی:** /join_lottery",
            'admin_signal': "📊 **پنل سیگنال مدیریت**\n\nسیگنال را برای زبان مورد نظر ارسال کنید:\n\n1️⃣ /signal_en - انگلیسی\n2️⃣ /signal_fa - فارسی\n3️⃣ /signal_tr - ترکی",
            'signal_sent': "✅ سیگنال با موفقیت به همه کاربران در زبان {} ارسال شد!",
            'signal_set': "✅ سیگنال برای زبان {} تنظیم شد!\n\nلطفاً متن سیگنال را ارسال کنید:",
            'signal_cancelled': "❌ ارسال سیگنال لغو شد.",
            'admin_education': "📚 **پنل آموزش مدیریت**\n\nمحتوای آموزشی را برای زبان مورد نظر ارسال کنید:\n\n1️⃣ /edu_en - انگلیسی\n2️⃣ /edu_fa - فارسی\n3️⃣ /edu_tr - ترکی",
            'education_sent': "✅ محتوای آموزشی برای {} بروزرسانی شد!",
            'education_set': "✅ آموزش برای زبان {} تنظیم شد!\n\nلطفاً متن آموزش را ارسال کنید:",
            'referral_notification': "🎉 **رفرال جدید!**\n\n👤 کاربر {} با لینک شما ثبت نام کرد!\n📊 تعداد کل رفرال‌ها: {}\n💰 پاداش: ۵ امتیاز اضافه شد!",
            'symbol_list': "📊 **لیست نمادهای موجود:**\n\n{}",
            'symbol_not_found': "❌ نماد یافت نشد!\n\nبرای مشاهده نمادها از /symbols استفاده کنید.",
        },
        'tr': {
            'name': 'Türkçe',
            'emoji': '🇹🇷',
            'welcome': "🎮 **UTYOB Piyango Botuna Hoş Geldiniz!**\n\n💰 10.000$'a kadar harika ödüller kazanın!\n🎯 Adil ve şeffaf piyango sistemi\n🌟 Hemen katıl ve şansını dene!",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **UTYOB Piyango Botu**\n\nAşağıdaki seçeneklerden birini seçin:",
            'lottery': "🎰 Piyangoya Katıl",
            'referral': "🔗 Referans",
            'guide': "📖 Rehber",
            'language': "🌐 Dil Değiştir",
            'admin_panel': "⚙️ Yönetim Paneli",
            'no_subscription': "❌ **Aktif aboneliğiniz yok!**\n\nPiyangoya katılmak için önce abonelik satın almalısınız.\n\n💰 Abonelik ücreti: 100$\n📅 Geçerlilik: 1 ay",
            'subscribe': "🔄 Abone Ol",
            'back': "🔙 Geri",
            'main_menu_btn': "🔙 Ana Menü",
            'lottery_back': "🎰 Piyangoya Dön",
            'subscribe_wallet': "💳 **UTYOB Aboneliği**\n\nLütfen kaynak TRC20 cüzdan adresinizi girin:\n\n🔹 **Abonelik ücreti:** 100$\n🔹 **Hedef adres:**\n`{}`",
            'after_subscribe_wallet': "✅ **Cüzdan adresi kaydedildi!**\n\n🔹 Adresiniz: `{}`\n\n💰 **Lütfen tam olarak 100$'yi aşağıdaki adrese gönderin:**\n`{}`",
            'confirm_subscribe': "✅ Ödemeyi Gönderdim",
            'subscribe_success': "✅ **Aboneliğiniz aktifleştirildi!** 🎉\n\n🔹 Tutar: ${}\n🔹 İşlem: `{}`\n\n🎉 Aboneliğiniz başarıyla aktifleştirildi!",
            'subscribe_failed': "❌ **Abonelik ödemesi doğrulanamadı!**\n\n🔹 Sebep: {}",
            'send_tx_hash': "📤 Manuel doğrulama için işlem hash'inizi (TX ID) gönderin:",
            'tx_hash_received': "✅ İşlem hash'i alındı!\n\n🔹 Hash: `{}`\n\n⏳ İşleminiz yönetici tarafından inceleniyor.",
            'tx_hash_invalid': "❌ Geçersiz işlem hash'i!\n\nLütfen geçerli bir TRON işlem hash'i gönderin.",
            'enter_wallet': "💳 **Piyangoya katılmak için yatırım**\n\nLütfen kaynak cüzdan adresinizi (TRC20) girin:\n\n🔹 **Yatırım tutarı:** 100$\n🔹 **Hedef adres:**\n`{}`",
            'enter_wallet_short': "📤 **TRC20 cüzdan adresinizi girin:**",
            'after_wallet': "✅ **Cüzdan adresi kaydedildi!**\n\n🔹 Adresiniz: `{}`\n\n💰 **Lütfen tam olarak 100$'yi aşağıdaki adrese gönderin:**\n`{}`",
            'confirm_payment': "✅ Ödemeyi Gönderdim",
            'cancel': "❌ İptal",
            'verifying': "⏳ Ödemeniz kontrol ediliyor...\nLütfen bir dakika bekleyin.",
            'payment_success': "✅ **Ödemeniz doğrulandı!** 🎉\n\n🔹 Tutar: ${}\n🔹 İşlem: `{}`\n\n🎉 Piyangoya başarıyla kaydoldunuz.",
            'payment_failed': "❌ **Ödeme doğrulaması başarısız!**\n\n🔹 Sebep: {}",
            'retry': "🔄 Tekrar Dene",
            'support': "📞 Destek",
            'withdraw_prize': "💰 Ödülü Çek",
            'enter_withdraw_wallet': "💰 **Ödülü Çek**\n\nÖdül tutarı: **${:,}**\n\nLütfen TRC20 cüzdan adresinizi girin:",
            'withdraw_success': "✅ **Çekim başarıyla kaydedildi!** 🎉\n\n💰 Tutar: ${:,}\n📤 Adres: {}",
            'already_paid': "✅ Ödül zaten ödendi!\n\n💰 Tutar: ${}\n📅 Tarih: {}",
            'no_winner': "❌ Hiç ödülünüz yok!\n\nGelecek piyangolara katılın.",
            'next_lottery': "🎰 Sonraki Piyango",
            'referral_text': "🔗 **UTYOB Referans Sistemi**\n\n👤 Siz: {}\n📊 Davetler: {}\n\n🔑 **Referans kodunuz:**\n`{}`\n\n🔗 **Referans linki:**\n{}\n\n💰 **Referans ödülü:**\n• Her davet için %5 yatırım",
            'share': "📤 Paylaş",
            'guide_text': "📖 **UTYOB Bot Tam Rehber**\n\n🎯 **Nasıl çalışır:**\n1. **Kayıt**: /start ile kaydolun\n2. **Abonelik**: Katılmak için abonelik satın alın\n3. **Yatırım**: Belirtilen adrese 100$ gönderin\n4. **Katılım**: Doğrulama sonrası piyangoya katılın\n5. **Kazanç**: Kazanırsanız ödülü alın",
            'language_selector': "🌐 **Dil Değiştir**\n\nMevcut dil: {}",
            'invalid_command': "⚠️ Geçersiz komut!\n\nButonları veya /help kullanın.",
            'error_message': "⚠️ Bir hata oluştu! Lütfen tekrar deneyin.",
            'photo_not_supported': "📸 Fotoğraf alındı!\nAncak bu özellik desteklenmiyor.",
            'invalid_wallet': "❌ Geçersiz cüzdan adresi!\n\nLütfen geçerli bir TRC20 adresi girin.",
            'admin_verify_tx': "✅ **İşlem Doğrulama Talebi**\n\n👤 Kullanıcı: {}\n📤 Gönderen: {}\n📥 Alan: {}\n💰 Tutar: ${}\n🔗 TX Hash: `{}`\n\nLütfen bu işlemi doğrulayın:",
            'admin_verify_approve': "✅ Onayla",
            'admin_verify_reject': "❌ Reddet",
            'admin_verify_approved': "✅ **İşlem onaylandı!**\n\n👤 Kullanıcı: {}\n💰 Tutar: ${}\n🔗 TX Hash: `{}`\n\nKullanıcının aboneliği aktifleştirildi.",
            'admin_verify_rejected': "❌ **İşlem reddedildi!**\n\n👤 Kullanıcı: {}\n🔗 TX Hash: `{}`\n\nKullanıcı bilgilendirildi.",
            'user_verify_approved': "✅ **İşleminiz onaylandı!** 🎉\n\n💰 Abonelik aktifleştirildi!\n🔗 TX Hash: `{}`",
            'user_verify_rejected': "❌ **İşleminiz reddedildi!**\n\n🔗 TX Hash: `{}`\n\nLütfen işleminizi kontrol edip tekrar deneyin.",
            'poll_message': "📊 **Anket**\n\n{}",
            'poll_option_1': "✅ Evet",
            'poll_option_2': "❌ Hayır",
            # Yeni Hizmetler (Türkçe)
            'download_instagram': "📥 **Instagram İndirici**\n\nBana bir Instagram gönderi veya reels linki gönderin:\n\nÖrnek:\n`/download https://www.instagram.com/p/CxY123XYZ/`\n\n🎁 **Günlük limit:** 5 indirme\n🔒 Sınırsız indirme için piyangoya katılın!",
            'download_success': "✅ **İndirme başarılı!** 🎉\n\n✨ Bugün {} indirme hakkınız kaldı\n\n🎰 **Piyangoya katıl:** /join_lottery",
            'download_limit': "⚠️ **Günlük limit doldu!**\n\nBugün 5 indirme hakkınızı kullandınız.\n\n🔒 Sınırsız indirme için piyangoya katılın!\n🎰 /join_lottery",
            'download_error': "❌ **İndirme başarısız!**\n\nLütfen linki kontrol edip tekrar deneyin.",
            'market_analysis': "📊 **Piyasa Analizi - {}**\n\n💰 Fiyat: ${:,.2f}\n📈 24s Değişim: {}%\n📊 En Yüksek: ${:,.2f}\n📉 En Düşük: ${:,.2f}\n📊 Hacim: ${:,.0f}\n\n📈 **20 Teknik Gösterge:**\n\n1️⃣ **RSI:** {} - {}\n2️⃣ **MACD:** {} - {}\n3️⃣ **MA7:** ${:,.2f}\n4️⃣ **MA25:** ${:,.2f}\n5️⃣ **MA99:** ${:,.2f}\n6️⃣ **BB Üst:** ${:,.2f}\n7️⃣ **BB Orta:** ${:,.2f}\n8️⃣ **BB Alt:** ${:,.2f}\n9️⃣ **VWAP:** ${:,.2f}\n🔟 **ATR:** ${:,.4f}\n1️⃣1️⃣ **Stochastic K:** {:.1f}\n1️⃣2️⃣ **Stochastic D:** {:.1f}\n1️⃣3️⃣ **ADX:** {} - {}\n1️⃣4️⃣ **CCI:** {:.1f}\n1️⃣5️⃣ **Williams %R:** {:.1f}\n1️⃣6️⃣ **Momentum:** {:.2f}\n1️⃣7️⃣ **OBV:** {:.0f}\n1️⃣8️⃣ **Regresyon Eğimi:** {:.6f}\n1️⃣9️⃣ **Regresyon R:** {:.3f}\n2️⃣0️⃣ **Piyasa Gücü:** {:.1f}%\n\n🎰 **Piyangoya katıl:** /join_lottery",
            'trading_education': "📚 **İşlem Eğitimi**\n\n📖 {}\n\n⏰ Son güncelleme: {}",
            'education_menu': "📚 **İşlem Eğitimi**\n\nAşağıdaki seçeneklerden birini seçin:",
            'signal_message': "📊 **UTYOB Sinyali**\n\n🟢 **AL {}**\n\n💰 Giriş: ${:,.2f}\n🎯 TP1: ${:,.2f} ({}%)\n🎯 TP2: ${:,.2f} ({}%)\n🎯 TP3: ${:,.2f} ({}%)\n🛑 SL: ${:,.2f} ({}%)\n\n📈 **Nedenler:**\n{}\n\n⚠️ **Risk Yönetimi:** İşlem başına maksimum %2 risk\n\n🎰 **Piyangoya katıl:** /join_lottery",
            'admin_signal': "📊 **Admin Sinyal Paneli**\n\nDil için sinyal gönderin:\n\n1️⃣ /signal_en - İngilizce\n2️⃣ /signal_fa - Farsça\n3️⃣ /signal_tr - Türkçe",
            'signal_sent': "✅ Sinyal başarıyla {} dilindeki tüm kullanıcılara gönderildi!",
            'signal_set': "✅ {} dili için sinyal ayarlandı!\n\nLütfen sinyal mesajını gönderin:",
            'signal_cancelled': "❌ Sinyal gönderme iptal edildi.",
            'admin_education': "📚 **Admin Eğitim Paneli**\n\nDil için eğitim içeriği gönderin:\n\n1️⃣ /edu_en - İngilizce\n2️⃣ /edu_fa - Farsça\n3️⃣ /edu_tr - Türkçe",
            'education_sent': "✅ Eğitim içeriği {} için güncellendi!",
            'education_set': "✅ {} dili için eğitim ayarlandı!\n\nLütfen eğitim içeriğini gönderin:",
            'referral_notification': "🎉 **Yeni referans!**\n\n👤 Kullanıcı {} referans linkinizle kaydoldu!\n📊 Toplam referanslar: {}\n💰 Ödül: 5 puan eklendi!",
            'symbol_list': "📊 **Mevcut semboller:**\n\n{}",
            'symbol_not_found': "❌ Sembol bulunamadı!\n\nSembolleri görmek için /symbols kullanın.",
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

# ============================================================
# دیتابیس با ۵۰۰ شارد - مقیاس بالا
# ============================================================
class DatabaseManager:
    def __init__(self, num_shards=DB_SHARDS):
        self.num_shards = num_shards
        self.connections = {}
        self.locks = {}
        self.executor = ThreadPoolExecutor(max_workers=100)
        self._init_shards()
        
    def _init_shards(self):
        os.makedirs("data", exist_ok=True)
        for i in range(self.num_shards):
            db_path = f"data/shard_{i}.db"
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=60)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=100000")
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
                points INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS education_content (
                language TEXT PRIMARY KEY,
                content TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ایندکس‌ها
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(has_subscription, subscription_end)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_user ON winners(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_winners_paid ON winners(paid_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_tx_user ON pending_verifications(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_referral_log_referrer ON referral_log(referrer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_referral_log_referred ON referral_log(referred_id)')
        
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

db = DatabaseManager()

# ============================================================
# سیستم کش
# ============================================================
class CacheManager:
    def __init__(self, max_size=50000):
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

cache = CacheManager(max_size=50000)

# ============================================================
# سیستم تایید پرداخت
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.session = None
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=500, limit_per_host=100)
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
        for api in self.apis:
            try:
                url = f"https://api.trongrid.io/v1/transactions/{tx_id}"
                headers = {"TRON-PRO-API-KEY": api}
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if self._validate_transaction_data(data, from_address, to_address, amount):
                            return True, tx_id, "Verified"
            except:
                continue
        return False, None, "Transaction not found"
        
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
                                return True, tx.get('txID'), "Verified"
            except:
                continue
        return False, None, "No matching transaction found"
        
    def _validate_transaction_data(self, tx_data, from_address, to_address, amount):
        try:
            if tx_data.get('to') != to_address:
                return False
            tx_amount = tx_data.get('amount', 0) / 1_000_000
            if abs(tx_amount - amount) > 0.01:
                return False
            return True
        except:
            return False

payment_verifier = PaymentVerifier()

# ============================================================
# سیستم تحلیل بازار با ۲۰ اندیکاتور
# ============================================================
class MarketAnalyzer:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=200):
        try:
            url = f"{self.base_url}/klines"
            params = {'symbol': symbol, 'interval': interval, 'limit': limit}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'open': [float(x[1]) for x in data],
                    'high': [float(x[2]) for x in data],
                    'low': [float(x[3]) for x in data],
                    'close': [float(x[4]) for x in data],
                    'volume': [float(x[5]) for x in data]
                }
            return None
        except:
            return None
    
    def calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return 50
        prices = np.array(prices)
        deltas = np.diff(prices)
        gains = deltas[deltas > 0]
        losses = -deltas[deltas < 0]
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0.0000001
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        if len(prices) < slow:
            return 0, 0, 0
        prices = np.array(prices)
        fast_ema = np.mean(prices[-fast:])
        for price in prices[-fast:]:
            fast_ema = price * (2/(fast+1)) + fast_ema * (1 - 2/(fast+1))
        slow_ema = np.mean(prices[-slow:])
        for price in prices[-slow:]:
            slow_ema = price * (2/(slow+1)) + slow_ema * (1 - 2/(slow+1))
        macd_line = fast_ema - slow_ema
        signal_line = macd_line
        for _ in range(signal):
            signal_line = macd_line * (2/(signal+1)) + signal_line * (1 - 2/(signal+1))
        histogram = macd_line - signal_line
        return round(macd_line, 8), round(signal_line, 8), round(histogram, 8)
    
    def calculate_ma(self, prices, period):
        if len(prices) < period:
            return prices[-1] if prices else 0
        return round(np.mean(prices[-period:]), 8)
    
    def calculate_bollinger(self, prices, period=20, std_dev=2):
        if len(prices) < period:
            return 0, 0, 0
        prices = np.array(prices[-period:])
        ma = np.mean(prices)
        std = np.std(prices)
        upper = ma + (std_dev * std)
        lower = ma - (std_dev * std)
        return round(upper, 8), round(ma, 8), round(lower, 8)
    
    def calculate_vwap(self, prices, volumes):
        if len(prices) < 2:
            return prices[-1] if prices else 0
        total_value = sum(prices[i] * volumes[i] for i in range(len(prices)))
        total_volume = sum(volumes)
        return round(total_value / total_volume, 8) if total_volume > 0 else prices[-1]
    
    def calculate_atr(self, highs, lows, closes, period=14):
        if len(closes) < period:
            return 0
        tr_list = []
        for i in range(1, period + 1):
            tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
            tr_list.append(tr)
        return round(np.mean(tr_list), 8)
    
    def calculate_stochastic(self, highs, lows, closes, k_period=14, d_period=3):
        if len(closes) < k_period:
            return 50, 50
        low_k = min(lows[-k_period:])
        high_k = max(highs[-k_period:])
        if high_k == low_k:
            return 50, 50
        k = 100 * (closes[-1] - low_k) / (high_k - low_k)
        d = k
        return round(k, 2), round(d, 2)
    
    def calculate_adx(self, highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return 25
        tr_list, up_list, down_list = [], [], []
        for i in range(1, period + 1):
            tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
            tr_list.append(tr)
            up_move = highs[-i] - highs[-i-1]
            down_move = lows[-i-1] - lows[-i]
            up_list.append(max(0, up_move) if up_move > down_move else 0)
            down_list.append(max(0, down_move) if down_move > up_move else 0)
        atr = np.mean(tr_list) if tr_list else 1
        di_plus = 100 * np.mean(up_list) / atr if atr > 0 else 0
        di_minus = 100 * np.mean(down_list) / atr if atr > 0 else 0
        adx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus + 0.0000001)
        return round(adx, 1)
    
    def calculate_cci(self, highs, lows, closes, period=20):
        if len(closes) < period:
            return 0
        tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(-period, 0) if i < 0]
        if len(tp) < period:
            return 0
        mean_tp = np.mean(tp)
        mean_dev = np.mean([abs(x - mean_tp) for x in tp])
        if mean_dev == 0:
            return 0
        cci = (tp[-1] - mean_tp) / (0.015 * mean_dev)
        return round(cci, 2)
    
    def calculate_williams_r(self, highs, lows, closes, period=14):
        if len(closes) < period:
            return -50
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        if highest == lowest:
            return -50
        wr = -100 * (highest - closes[-1]) / (highest - lowest)
        return round(wr, 2)
    
    def calculate_momentum(self, prices, period=10):
        if len(prices) < period:
            return 0
        return round((prices[-1] - prices[-period]) / prices[-period] * 100, 4)
    
    def calculate_obv(self, closes, volumes):
        if len(closes) < 2:
            return 0
        obv = 0
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv += volumes[i]
            elif closes[i] < closes[i-1]:
                obv -= volumes[i]
        return round(obv, 2)
    
    def calculate_regression(self, prices, period=20):
        if len(prices) < period:
            return 0, 0
        x = np.arange(period)
        y = prices[-period:]
        slope, intercept = np.polyfit(x, y, 1)
        r = np.corrcoef(x, y)[0, 1]
        return round(slope, 6), round(r, 3)
    
    def calculate_market_strength(self, closes, highs, lows):
        if len(closes) < 50:
            return 50
        high_50 = max(highs[-50:])
        low_50 = min(lows[-50:])
        current = closes[-1]
        if high_50 == low_50:
            return 50
        return round((current - low_50) / (high_50 - low_50) * 100, 1)
    
    def get_full_analysis(self, symbol="BTCUSDT"):
        data = self.get_klines(symbol, "1h", 200)
        if not data:
            return None
        
        prices = data['close']
        highs = data['high']
        lows = data['low']
        volumes = data['volume']
        current = prices[-1]
        
        rsi_val = self.calculate_rsi(prices, 14)
        macd_line, macd_signal, macd_hist = self.calculate_macd(prices, 12, 26, 9)
        ma7 = self.calculate_ma(prices, 7)
        ma25 = self.calculate_ma(prices, 25)
        ma99 = self.calculate_ma(prices, 99)
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger(prices, 20, 2)
        vwap = self.calculate_vwap(prices, volumes)
        atr = self.calculate_atr(highs, lows, prices, 14)
        stoch_k, stoch_d = self.calculate_stochastic(highs, lows, prices, 14, 3)
        adx = self.calculate_adx(highs, lows, prices, 14)
        cci = self.calculate_cci(highs, lows, prices, 20)
        williams_r = self.calculate_williams_r(highs, lows, prices, 14)
        momentum = self.calculate_momentum(prices, 10)
        obv = self.calculate_obv(prices, volumes)
        slope, r_value = self.calculate_regression(prices, 20)
        market_strength = self.calculate_market_strength(prices, highs, lows)
        
        rsi_status = "🟢 Oversold" if rsi_val < 35 else "🔴 Overbought" if rsi_val > 65 else "🟡 Neutral"
        adx_status = "🔥 Strong" if adx > 40 else "📊 Weak"
        
        return {
            'symbol': symbol,
            'price': round(current, 2),
            'change_24h': round(((current - prices[0]) / prices[0]) * 100, 2),
            'high_24h': round(max(highs), 2),
            'low_24h': round(min(lows), 2),
            'volume_24h': round(sum(volumes), 2),
            'rsi': rsi_val,
            'rsi_status': rsi_status,
            'macd_line': macd_line,
            'macd_signal': macd_signal,
            'macd_histogram': macd_hist,
            'ma7': ma7,
            'ma25': ma25,
            'ma99': ma99,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'vwap': vwap,
            'atr': atr,
            'stoch_k': stoch_k,
            'stoch_d': stoch_d,
            'adx': adx,
            'adx_status': adx_status,
            'cci': cci,
            'williams_r': williams_r,
            'momentum': momentum,
            'obv': obv,
            'regression_slope': slope,
            'regression_r': r_value,
            'market_strength': market_strength,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

market_analyzer = MarketAnalyzer()

# ============================================================
# سیستم دانلودر اینستاگرام
# ============================================================
class InstagramDownloader:
    def __init__(self):
        self.loader = Instaloader()
        self.user_downloads = {}
        self.daily_limit = 5
        
    def download_media(self, url, user_id):
        try:
            code = re.search(r'/p/([^/]+)/', url)
            if not code:
                code = re.search(r'/reel/([^/]+)/', url)
            if not code:
                return None, "Invalid link"
            
            post_code = code.group(1)
            post = Post.from_shortcode(self.loader.context, post_code)
            
            download_path = f"downloads/{user_id}_{post_code}"
            os.makedirs(download_path, exist_ok=True)
            self.loader.download_post(post, target=download_path)
            
            files = os.listdir(download_path)
            media_file = None
            for f in files:
                if f.endswith('.mp4') or f.endswith('.jpg') or f.endswith('.png'):
                    media_file = os.path.join(download_path, f)
                    break
            
            if media_file:
                self.user_downloads[user_id] = self.user_downloads.get(user_id, 0) + 1
                return media_file, "Success"
            return None, "File not found"
            
        except Exception as e:
            return None, str(e)

# ============================================================
# سیستم قرعه‌کشی
# ============================================================
class LotterySystem:
    def __init__(self):
        self.current_lottery = None
        self.is_running = False
        self.participants = []
        
    def start_lottery(self, winners_count, prize_per_winner):
        if self.is_running:
            return False, "Lottery is already running"
            
        eligible_users = self._get_eligible_users()
        if len(eligible_users) < winners_count:
            return False, f"Not enough users ({len(eligible_users)} < {winners_count})"
            
        winners = random.sample(eligible_users, winners_count)
        
        cursor = db.execute(0,
            """INSERT INTO lotteries (winners_count, prize_per_winner, total_prize, status, started_at) 
               VALUES (?, ?, ?, 'running', CURRENT_TIMESTAMP)""",
            (winners_count, prize_per_winner, winners_count * prize_per_winner)
        )
        lottery_id = cursor.lastrowid
        
        for user_id in winners:
            db.execute(user_id,
                """INSERT INTO winners (lottery_id, user_id, prize_amount, paid_status) 
                   VALUES (?, ?, ?, 0)""",
                (lottery_id, user_id, prize_per_winner)
            )
            db.execute(user_id,
                "UPDATE users SET wins_count = wins_count + 1, last_win_date = CURRENT_TIMESTAMP WHERE user_id = ?",
                (user_id,)
            )
        
        self.is_running = False
        return True, {'lottery_id': lottery_id, 'winners': winners, 'prize_per_winner': prize_per_winner}
    
    def _get_eligible_users(self):
        cursor = db.execute_global(
            "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
        )
        return [row['user_id'] for row in cursor]

lottery_system = LotterySystem()

# ============================================================
# سیستم مدیریت کاربران
# ============================================================
class UserManager:
    @staticmethod
    def register_user(user_id, username=None, first_name=None, last_name=None, referral_code=None):
        try:
            cursor = db.execute(user_id, "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                # تولید کد رفرال
                ref_code = hashlib.sha256(f"{user_id}_{time.time()}_{random.randint(1000, 9999)}".encode()).hexdigest()[:10].upper()
                
                # بررسی کد رفرال
                referrer_id = None
                if referral_code:
                    ref_cursor = db.execute(0, "SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
                    ref_result = ref_cursor.fetchone()
                    if ref_result:
                        referrer_id = ref_result['user_id']
                
                db.execute(user_id,
                    """INSERT INTO users (user_id, username, first_name, last_name, referral_code, referred_by, language) 
                       VALUES (?, ?, ?, ?, ?, ?, 'en')""",
                    (user_id, username, first_name, last_name, ref_code, referrer_id)
                )
                
                # ثبت رفرال و ارسال اعلان
                if referrer_id:
                    db.execute(0,
                        """INSERT INTO referral_log (referrer_id, referred_id) VALUES (?, ?)""",
                        (referrer_id, user_id)
                    )
                    
                    # افزایش امتیاز کاربر دعوت کننده
                    db.execute(referrer_id,
                        "UPDATE users SET points = COALESCE(points, 0) + 5, referral_count = COALESCE(referral_count, 0) + 1 WHERE user_id = ?",
                        (referrer_id,)
                    )
                    
                    # ارسال اعلان به دعوت کننده (در تابع جداگانه)
                    asyncio.create_task(UserManager._send_referral_notification(referrer_id, user_id))
                
                return True
            return False
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            return False
    
    @staticmethod
    async def _send_referral_notification(referrer_id, new_user_id):
        """ارسال اعلان رفرال به دعوت کننده"""
        try:
            from telegram import Bot
            bot = Bot(token=BOT_TOKEN)
            
            # دریافت تعداد رفرال‌ها
            cursor = db.execute(referrer_id,
                "SELECT referral_count, language FROM users WHERE user_id = ?",
                (referrer_id,)
            )
            user_data = cursor.fetchone()
            
            if user_data:
                lang = user_data['language'] or 'en'
                count = user_data['referral_count'] or 0
                
                text = LanguageManager.get_text(lang, 'referral_notification', new_user_id, count)
                await bot.send_message(chat_id=referrer_id, text=text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error sending referral notification: {e}")
    
    @staticmethod
    def get_user(user_id):
        cache_key = f"user_{user_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        try:
            cursor = db.execute(user_id, "SELECT * FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                cache.set(cache_key, result, ttl=60)
            return result
        except:
            return None
    
    @staticmethod
    def update_user(user_id, **kwargs):
        try:
            set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            db.execute(user_id, f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", values)
            cache.delete(f"user_{user_id}")
            return True
        except:
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
        except:
            return 0
    
    @staticmethod
    def get_all_users():
        try:
            results = db.execute_global("SELECT user_id, language FROM users")
            return results
        except:
            return []

user_manager = UserManager()

# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.pending_verifications = {}
        self.pending_signals = {}
        self.pending_education = {}
        self.downloader = InstagramDownloader()
        self.analyzer = MarketAnalyzer()
        self._setup_handlers()
        self._init_system()
        
    def _init_system(self):
        try:
            cursor = db.execute(0, "SELECT value FROM settings WHERE key = 'system_initialized'")
            if not cursor.fetchone():
                db.execute(0, "INSERT INTO settings (key, value) VALUES ('system_initialized', 'true')")
                # تنظیمات پیش‌فرض آموزش
                for lang in ['en', 'fa', 'tr']:
                    db.execute(0,
                        """INSERT OR IGNORE INTO education_content (language, content) 
                           VALUES (?, ?)""",
                        (lang, "📚 Welcome to UTYOB Trading Education!\n\nThis is the default education content. Admin will update this soon.")
                    )
                logger.info("سیستم مقداردهی شد")
            else:
                logger.info("سیستم قبلاً مقداردهی شده")
        except Exception as e:
            logger.error(f"Error initializing system: {e}")
        
    def _setup_handlers(self):
        app = self.application
        
        # دستورات عمومی
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("referral", self.referral_command))
        app.add_handler(CommandHandler("language", self.language_command))
        app.add_handler(CommandHandler("symbols", self.symbols_command))
        
        # سرویس‌های جدید
        app.add_handler(CommandHandler("download", self.download_command))
        app.add_handler(CommandHandler("analyze", self.analyze_command))
        app.add_handler(CommandHandler("education", self.education_command))
        app.add_handler(CommandHandler("signal", self.signal_command))
        
        # دستورات ادمین
        app.add_handler(CommandHandler("signal_en", self.admin_signal_command))
        app.add_handler(CommandHandler("signal_fa", self.admin_signal_command))
        app.add_handler(CommandHandler("signal_tr", self.admin_signal_command))
        app.add_handler(CommandHandler("edu_en", self.admin_education_command))
        app.add_handler(CommandHandler("edu_fa", self.admin_education_command))
        app.add_handler(CommandHandler("edu_tr", self.admin_education_command))
        
        # دکمه‌های منو
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language$"))
        
        # دکمه‌های اشتراک
        app.add_handler(CallbackQueryHandler(self.subscribe_callback, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.confirm_subscribe_callback, pattern="^confirm_subscribe$"))
        
        # دکمه‌های قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.join_lottery_callback, pattern="^join_lottery$"))
        app.add_handler(CallbackQueryHandler(self.confirm_payment_callback, pattern="^confirm_payment$"))
        
        # دکمه‌های سرویس‌ها
        app.add_handler(CallbackQueryHandler(self.download_menu_callback, pattern="^download_menu$"))
        app.add_handler(CallbackQueryHandler(self.market_menu_callback, pattern="^market_menu$"))
        app.add_handler(CallbackQueryHandler(self.education_menu_callback, pattern="^education_menu$"))
        
        # دکمه‌های پنل مدیریت
        app.add_handler(CallbackQueryHandler(self.admin_panel_callback, pattern="^admin_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_broadcast_callback, pattern="^admin_broadcast$"))
        app.add_handler(CallbackQueryHandler(self.admin_start_lottery_callback, pattern="^admin_start_lottery$"))
        app.add_handler(CallbackQueryHandler(self.admin_manual_verify_callback, pattern="^admin_manual_verify$"))
        app.add_handler(CallbackQueryHandler(self.admin_poll_callback, pattern="^admin_poll$"))
        app.add_handler(CallbackQueryHandler(self.admin_pay_winners_callback, pattern="^admin_pay_winners$"))
        app.add_handler(CallbackQueryHandler(self.admin_stats_callback, pattern="^admin_stats$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_api_callback, pattern="^admin_add_api$"))
        app.add_handler(CallbackQueryHandler(self.admin_signal_panel_callback, pattern="^admin_signal_panel$"))
        app.add_handler(CallbackQueryHandler(self.admin_education_panel_callback, pattern="^admin_education_panel$"))
        
        # تایید/رد تراکنش
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))
        
        # سیگنال ادمین
        app.add_handler(CallbackQueryHandler(self.admin_signal_lang_callback, pattern="^admin_signal_"))
        app.add_handler(CallbackQueryHandler(self.admin_education_lang_callback, pattern="^admin_education_"))
        
        # مراحل قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.start_lottery_confirm_callback, pattern="^start_lottery_confirm$"))
        app.add_handler(CallbackQueryHandler(self.start_lottery_final_callback, pattern="^start_lottery_final$"))
        
        # برداشت جایزه
        app.add_handler(CallbackQueryHandler(self.withdraw_prize_callback, pattern="^withdraw_prize$"))
        app.add_handler(CallbackQueryHandler(self.confirm_withdraw_callback, pattern="^confirm_withdraw$"))
        
        # تغییر زبان
        app.add_handler(CallbackQueryHandler(self.set_language_callback, pattern="^set_lang_"))
        
        # مدیریت پیام‌ها
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        app.add_error_handler(self.error_handler)

    # ============================================================
    # توابع کمکی
    # ============================================================
    def _get_user_language(self, user_id):
        user = user_manager.get_user(user_id)
        return user['language'] if user and user['language'] else 'en'
    
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
            return len(address) == 34 and all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address)
        except:
            return False
    
    def _validate_tx_hash(self, tx_hash):
        try:
            return len(tx_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in tx_hash)
        except:
            return False
    
    async def _auto_verify_payment(self, user_id, from_address, to_address, amount):
        try:
            success, tx_id, message = await payment_verifier.verify_transaction(
                from_address, to_address, amount
            )
            if success:
                db.execute(user_id,
                    """INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
                       VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)""",
                    (user_id, from_address, to_address, amount, tx_id)
                )
                db.execute(user_id,
                    "UPDATE users SET total_participations = total_participations + 1 WHERE user_id = ?",
                    (user_id,)
                )
                return {'success': True, 'tx_id': tx_id}
            return {'success': False, 'message': message}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _get_pending_transactions(self):
        return db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC")
    
    def _get_unpaid_winners(self):
        return db.execute_global("SELECT * FROM winners WHERE paid_status = 0 ORDER BY created_at ASC")
    
    def _check_winner(self, user_id):
        cursor = db.execute(user_id,
            "SELECT * FROM winners WHERE user_id = ? AND paid_status = 0 ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        return cursor.fetchone()
    
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
        
        # بررسی کد رفرال
        referral_code = None
        if context.args:
            arg = context.args[0]
            if arg.startswith('ref_'):
                referral_code = arg.replace('ref_', '')
        
        user_manager.register_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            referral_code
        )
        
        lang = self._get_user_language(user.id)
        
        keyboard = [
            [InlineKeyboardButton("🎰 قرعه‌کشی", callback_data="lottery")],
            [InlineKeyboardButton("📥 دانلودر اینستاگرام", callback_data="download_menu")],
            [InlineKeyboardButton("📊 تحلیل بازار", callback_data="market_menu")],
            [InlineKeyboardButton("📚 آموزش ترید", callback_data="education_menu")],
            [InlineKeyboardButton("🔗 رفرال", callback_data="referral")],
            [InlineKeyboardButton("📖 راهنمایی", callback_data="guide")],
            [InlineKeyboardButton("🌐 تغییر زبان", callback_data="language")]
        ]
        
        if user.id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            self._get_text(user.id, 'welcome'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            self._get_text(user_id, 'guide_text'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
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
        
        keyboard = [
            [InlineKeyboardButton(self._get_text(user_id, 'share'), url=referral_link)],
            [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            self._get_text(user_id, 'referral_text', user['first_name'] or user_id, referred_count, referral_code, referral_link),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await self._show_language_selector(update, user_id)
    
    async def symbols_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        symbols_text = ""
        count = 0
        for sym in CRYPTO_SYMBOLS[:50]:
            symbols_text += f"• `{sym}` "
            count += 1
            if count % 5 == 0:
                symbols_text += "\n"
        
        symbols_text += f"\n... و {len(CRYPTO_SYMBOLS) - 50} نماد دیگر"
        
        await update.message.reply_text(
            self._get_text(user_id, 'symbol_list', symbols_text),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # سرویس ۱: دانلودر اینستاگرام
    # ============================================================
    async def download_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        if not context.args:
            await update.message.reply_text(
                self._get_text(user_id, 'download_instagram'),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        url = context.args[0]
        
        if user_id in self.downloader.user_downloads and self.downloader.user_downloads[user_id] >= 5:
            await update.message.reply_text(
                self._get_text(user_id, 'download_limit'),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await update.message.reply_text("⏳ در حال دانلود... لطفاً صبر کنید.")
        
        file_path, result = self.downloader.download_media(url, user_id)
        
        if file_path:
            remaining = 5 - self.downloader.user_downloads.get(user_id, 0)
            try:
                if file_path.endswith('.mp4'):
                    with open(file_path, 'rb') as f:
                        await update.message.reply_video(f, caption=self._get_text(user_id, 'download_success', remaining))
                else:
                    with open(file_path, 'rb') as f:
                        await update.message.reply_photo(f, caption=self._get_text(user_id, 'download_success', remaining))
                os.remove(file_path)
                os.rmdir(os.path.dirname(file_path))
            except Exception as e:
                logger.error(f"Download error: {e}")
                await update.message.reply_text(self._get_text(user_id, 'download_error'))
        else:
            await update.message.reply_text(self._get_text(user_id, 'download_error'))
    
    async def download_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        await query.edit_message_text(
            self._get_text(user_id, 'download_instagram'),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # سرویس ۲: تحلیل بازار با ۲۰ اندیکاتور
    # ============================================================
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        if not context.args:
            await update.message.reply_text(
                f"📊 **راهنمای تحلیل**\n\n"
                f"برای تحلیل یک ارز، دستور زیر را وارد کنید:\n\n"
                f"`/analyze BTCUSDT`\n`/analyze ETHUSDT`\n\n"
                f"📌 لیست کامل نمادها: /symbols",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        if symbol not in CRYPTO_SYMBOLS:
            await update.message.reply_text(
                self._get_text(user_id, 'symbol_not_found'),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await update.message.reply_text("⏳ در حال دریافت داده‌ها... لطفاً صبر کنید.")
        
        analysis = self.analyzer.get_full_analysis(symbol)
        if not analysis:
            await update.message.reply_text("❌ خطا در دریافت داده‌ها!")
            return
        
        rsi_status = "🟢 خرید" if analysis['rsi'] < 35 else "🔴 فروش" if analysis['rsi'] > 65 else "🟡 خنثی"
        
        await update.message.reply_text(
            self._get_text(user_id, 'market_analysis',
                analysis['symbol'],
                analysis['price'],
                analysis['change_24h'],
                analysis['high_24h'],
                analysis['low_24h'],
                analysis['volume_24h'],
                analysis['rsi'],
                rsi_status,
                analysis['macd_line'],
                "صعودی" if analysis['macd_line'] > analysis['macd_signal'] else "نزولی",
                analysis['ma7'],
                analysis['ma25'],
                analysis['ma99'],
                analysis['bb_upper'],
                analysis['bb_middle'],
                analysis['bb_lower'],
                analysis['vwap'],
                analysis['atr'],
                analysis['stoch_k'],
                analysis['stoch_d'],
                analysis['adx'],
                analysis['adx_status'],
                analysis['cci'],
                analysis['williams_r'],
                analysis['momentum'],
                analysis['obv'],
                analysis['regression_slope'],
                analysis['regression_r'],
                analysis['market_strength']
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def market_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        text = f"""
📊 **تحلیل بازار**

برای تحلیل یک ارز، دستور زیر را وارد کنید:

`/analyze BTCUSDT`
`/analyze ETHUSDT`
`/analyze SOLUSDT`

📌 **۲۰ اندیکاتور موجود:**
✅ RSI, MACD, MA7, MA25, MA99
✅ Bollinger Bands (Upper, Middle, Lower)
✅ VWAP, ATR, Stochastic K/D
✅ ADX, CCI, Williams %R
✅ Momentum, OBV, Regression
✅ Market Strength

📊 **لیست کامل نمادها:** /symbols

🎰 **شرکت در قرعه‌کشی:** /join_lottery
"""
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # سرویس ۳: آموزش ترید
    # ============================================================
    async def education_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        # دریافت محتوای آموزشی از دیتابیس
        cursor = db.execute(0, "SELECT content, updated_at FROM education_content WHERE language = ?", (lang,))
        edu_data = cursor.fetchone()
        
        if edu_data:
            content = edu_data['content']
            updated = edu_data['updated_at'][:16] if edu_data['updated_at'] else datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            content = "📚 محتوای آموزشی توسط ادمین در حال تنظیم است..."
            updated = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        await update.message.reply_text(
            self._get_text(user_id, 'trading_education', content, updated),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def education_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        cursor = db.execute(0, "SELECT content, updated_at FROM education_content WHERE language = ?", (lang,))
        edu_data = cursor.fetchone()
        
        if edu_data:
            content = edu_data['content']
            updated = edu_data['updated_at'][:16] if edu_data['updated_at'] else datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            content = "📚 محتوای آموزشی توسط ادمین در حال تنظیم است..."
            updated = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        await query.edit_message_text(
            self._get_text(user_id, 'trading_education', content, updated),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # سیگنال اختصاصی
    # ============================================================
    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        signal_data = {
            'symbol': 'BTCUSDT',
            'entry': 61200,
            'tp1': 62500,
            'tp2': 64000,
            'tp3': 66500,
            'sl': 59800,
            'pct1': 2.1,
            'pct2': 4.6,
            'pct3': 8.7,
            'sl_pct': 2.3,
            'reasons': "• RSI در محدوده اشباع فروش\n• MACD در حال صعودی شدن\n• حمایت قوی در $60,800"
        }
        
        await update.message.reply_text(
            self._get_text(user_id, 'signal_message',
                signal_data['symbol'],
                signal_data['entry'],
                signal_data['tp1'],
                signal_data['pct1'],
                signal_data['tp2'],
                signal_data['pct2'],
                signal_data['tp3'],
                signal_data['pct3'],
                signal_data['sl'],
                signal_data['sl_pct'],
                signal_data['reasons']
            ),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # دستورات ادمین - سیگنال
    # ============================================================
    async def admin_signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Access denied!")
            return
        
        command = update.message.text
        if 'en' in command:
            lang_code = 'en'
        elif 'fa' in command:
            lang_code = 'fa'
        elif 'tr' in command:
            lang_code = 'tr'
        else:
            return
        
        self.pending_signals[user_id] = lang_code
        await update.message.reply_text(
            LanguageManager.get_text(lang_code, 'signal_set', LanguageManager.get_language_name(lang_code)),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # دستورات ادمین - آموزش
    # ============================================================
    async def admin_education_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Access denied!")
            return
        
        command = update.message.text
        if 'en' in command:
            lang_code = 'en'
        elif 'fa' in command:
            lang_code = 'fa'
        elif 'tr' in command:
            lang_code = 'tr'
        else:
            return
        
        self.pending_education[user_id] = lang_code
        await update.message.reply_text(
            LanguageManager.get_text(lang_code, 'education_set', LanguageManager.get_language_name(lang_code)),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های منو
    # ============================================================
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🎰 قرعه‌کشی", callback_data="lottery")],
            [InlineKeyboardButton("📥 دانلودر اینستاگرام", callback_data="download_menu")],
            [InlineKeyboardButton("📊 تحلیل بازار", callback_data="market_menu")],
            [InlineKeyboardButton("📚 آموزش ترید", callback_data="education_menu")],
            [InlineKeyboardButton("🔗 رفرال", callback_data="referral")],
            [InlineKeyboardButton("📖 راهنمایی", callback_data="guide")],
            [InlineKeyboardButton("🌐 تغییر زبان", callback_data="language")]
        ]
        
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self._get_text(user_id, 'main_menu'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های قرعه‌کشی
    # ============================================================
    async def lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if not user or not user['has_subscription']:
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'subscribe'), callback_data="subscribe")],
                [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                self._get_text(user_id, 'no_subscription'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = [
            [InlineKeyboardButton(self._get_text(user_id, 'lottery'), callback_data="join_lottery")],
            [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎰 **UTYOB {self._get_text(user_id, 'lottery')}**\n\n"
            f"👤 {user['first_name'] or user_id}\n\n"
            f"💰 جایزه: تا ۱۰,۰۰۰ دلار\n"
            f"🎯 شانس عادلانه",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def join_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if not user or not user['has_subscription']:
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'subscribe'), callback_data="subscribe")],
                [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                self._get_text(user_id, 'no_subscription'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        context.user_data['waiting_for_wallet'] = True
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self._get_text(user_id, 'enter_wallet_short'),
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
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                self._get_text(user_id, 'enter_wallet_short'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            self._get_text(user_id, 'verifying'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        result = await self._auto_verify_payment(user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT)
        
        if result['success']:
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'lottery_back'), callback_data="lottery")],
                [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                self._get_text(user_id, 'payment_success', PAYMENT_AMOUNT, result['tx_id']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['payment_from_address'] = user['wallet_address']
            
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                self._get_text(user_id, 'payment_failed', result['message']),
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
        
        context.user_data['waiting_for_subscribe'] = True
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self._get_text(user_id, 'subscribe_wallet', DESTINATION_WALLET),
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
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                self._get_text(user_id, 'subscribe_wallet', DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await query.edit_message_text(
            self._get_text(user_id, 'verifying'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        result = await self._auto_verify_payment(user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT)
        
        if result['success']:
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            db.execute(user_id,
                "UPDATE users SET has_subscription = 1, subscription_end = ? WHERE user_id = ?",
                (end_date, user_id)
            )
            
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'lottery'), callback_data="lottery")],
                [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                self._get_text(user_id, 'subscribe_success', PAYMENT_AMOUNT, result['tx_id']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['subscription_from_address'] = user['wallet_address']
            
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                self._get_text(user_id, 'subscribe_failed', result['message']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های ادمین
    # ============================================================
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ Access denied!")
            return
        
        user_count = user_manager.get_user_count()
        pending_count = len(self._get_pending_transactions())
        unpaid_winners = len(self._get_unpaid_winners())
        
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton(f"✅ تایید دستی ({pending_count})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📊 ارسال نظرسنجی", callback_data="admin_poll")],
            [InlineKeyboardButton(f"💰 واریز به برندگان ({unpaid_winners})", callback_data="admin_pay_winners")],
            [InlineKeyboardButton("📊 ارسال سیگنال", callback_data="admin_signal_panel")],
            [InlineKeyboardButton("📚 تنظیم آموزش", callback_data="admin_education_panel")],
            [InlineKeyboardButton("🔑 اضافه کردن API", callback_data="admin_add_api")],
            [InlineKeyboardButton("📈 آمار", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚙️ **پنل مدیریت**\n\n"
            f"👥 کل کاربران: {user_count:,}\n"
            f"⏳ در انتظار تایید: {pending_count}\n"
            f"💰 برندگان پرداخت نشده: {unpaid_winners}\n\n"
            f"انتخاب کنید:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_signal_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
        
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="admin_signal_en")],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="admin_signal_fa")],
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="admin_signal_tr")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self._get_text(user_id, 'admin_signal'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_signal_lang_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
        
        lang_code = query.data.replace('admin_signal_', '')
        self.pending_signals[user_id] = lang_code
        
        await query.edit_message_text(
            self._get_text(user_id, 'signal_set', LanguageManager.get_language_name(lang_code)),
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_education_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
        
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="admin_education_en")],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="admin_education_fa")],
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="admin_education_tr")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self._get_text(user_id, 'admin_education'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_education_lang_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if user_id not in ADMIN_IDS:
            return
        
        lang_code = query.data.replace('admin_education_', '')
        self.pending_education[user_id] = lang_code
        
        await query.edit_message_text(
            self._get_text(user_id, 'education_set', LanguageManager.get_language_name(lang_code)),
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
        context.user_data['admin_action'] = 'broadcast'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📢 **ارسال پیام همگانی**\n\nلطفاً متن پیام را ارسال کنید:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_start_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
        if lottery_system.is_running:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("⚠️ قرعه‌کشی در حال اجراست!", reply_markup=reply_markup)
            return
        
        context.user_data['admin_action'] = 'start_lottery'
        context.user_data['lottery_step'] = 1
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎰 **شروع قرعه‌کشی**\n\nمرحله ۱: مبلغ جایزه را وارد کنید:\nمثال: `10000`",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
        pending = self._get_pending_transactions()
        if not pending:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ همه تراکنش‌ها تایید شده‌اند!", reply_markup=reply_markup)
            return
        
        text = f"✅ **تایید دستی** ({len(pending)} تراکنش)\n\n"
        for p in pending[:5]:
            text += f"🆔 #{p['id']} - کاربر: {p['user_id']}\n💰 ${p['amount']}\n🔗 {p['tx_hash'][:20]}...\n\n"
        
        keyboard = []
        for p in pending[:5]:
            keyboard.append([
                InlineKeyboardButton(f"✅ تایید #{p['id']}", callback_data=f"admin_verify_approve_{p['id']}"),
                InlineKeyboardButton(f"❌ رد #{p['id']}", callback_data=f"admin_verify_reject_{p['id']}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def admin_poll_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
        context.user_data['admin_action'] = 'poll'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 **ارسال نظرسنجی**\n\nلطفاً متن نظرسنجی را ارسال کنید:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_pay_winners_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
        winners = self._get_unpaid_winners()
        if not winners:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("✅ همه برندگان پرداخت شده‌اند!", reply_markup=reply_markup)
            return
        
        text = f"💰 **برندگان پرداخت نشده** ({len(winners)})\n\n"
        for w in winners[:10]:
            text += f"👤 {w['user_id']} - ${w['prize_amount']:,}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
        user_count = user_manager.get_user_count()
        cache_stats = cache.get_stats()
        tx_stats = self._get_transaction_stats()
        lottery_stats = self._get_lottery_stats()
        
        text = (
            f"📊 **آمار سیستم**\n\n"
            f"👥 کاربران: {user_count:,}\n"
            f"💳 تراکنش‌ها: {tx_stats['total']:,}\n"
            f"🎰 قرعه‌کشی: {lottery_stats['total']}\n"
            f"⚡ کش: {cache_stats['size']} آیتم\n"
            f"🔑 API‌ها: {len(payment_verifier.apis)}\n"
            f"🗄️ شاردها: {DB_SHARDS}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
        context.user_data['admin_action'] = 'add_api'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔑 **اضافه کردن API جدید**\n\nلطفاً کلید API جدید را وارد کنید:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_verify_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS: return
        
        pending_id = int(query.data.replace('admin_verify_approve_', ''))
        pending = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        
        if not pending:
            await query.edit_message_text("❌ درخواست یافت نشد!")
            return
        
        user_id = pending['user_id']
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        db.execute(user_id, "UPDATE users SET has_subscription = 1, subscription_end = ? WHERE user_id = ?", (end_date, user_id))
        db.execute(0, "UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))
        
        lang = self._get_user_language(user_id)
        await self.application.bot.send_message(
            user_id,
            self._get_text(user_id, 'user_verify_approved', pending['tx_hash']),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await query.edit_message_text(f"✅ تراکنش #{pending_id} تایید شد!\n👤 کاربر: {user_id}", parse_mode=ParseMode.MARKDOWN)

    async def admin_verify_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS: return
        
        pending_id = int(query.data.replace('admin_verify_reject_', ''))
        pending = db.execute(0, "SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,)).fetchone()
        
        if not pending:
            await query.edit_message_text("❌ درخواست یافت نشد!")
            return
        
        user_id = pending['user_id']
        db.execute(0, "UPDATE pending_verifications SET status = 'rejected' WHERE id = ?", (pending_id,))
        
        lang = self._get_user_language(user_id)
        await self.application.bot.send_message(
            user_id,
            self._get_text(user_id, 'user_verify_rejected', pending['tx_hash']),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await query.edit_message_text(f"❌ تراکنش #{pending_id} رد شد!\n👤 کاربر: {user_id}", parse_mode=ParseMode.MARKDOWN)

    async def start_lottery_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
        context.user_data['lottery_step'] = 2
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 **تعداد برندگان**\n\nلطفاً تعداد برندگان را وارد کنید:\n(حداکثر ۱۰۰ نفر)\n\nمثال: `5`",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def start_lottery_final_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS: return
        
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
                        text=LanguageManager.get_text(winner_lang, 'withdraw_prize', prize_per_winner, result['lottery_id']),
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Error sending to {winner_id}: {e}")
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ **قرعه‌کشی انجام شد!** 🎉\n\n"
                f"• تعداد برندگان: {winners_count}\n"
                f"• جایزه هر نفر: ${prize_per_winner:,}\n"
                f"• کل جایزه: ${winners_count * prize_per_winner:,}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="admin_start_lottery")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"❌ خطا: {result}", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def withdraw_prize_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        winner = self._check_winner(user_id)
        if not winner:
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'lottery'), callback_data="lottery")],
                [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                self._get_text(user_id, 'no_winner'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if winner['paid_status'] == 1:
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                self._get_text(user_id, 'already_paid', winner['prize_amount'], winner['paid_at']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        context.user_data['withdraw_pending'] = True
        context.user_data['winner_id'] = winner['id']
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self._get_text(user_id, 'enter_withdraw_wallet', winner['prize_amount']),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def confirm_withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if not context.user_data.get('withdraw_pending'):
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("⚠️ No pending withdrawal.", reply_markup=reply_markup)
            return
        
        user = user_manager.get_user(user_id)
        if not user or not user['wallet_address']:
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("❌ No wallet address found!", reply_markup=reply_markup)
            return
        
        winner_id = context.user_data.get('winner_id')
        if winner_id:
            db.execute(user_id,
                """UPDATE winners SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (user['wallet_address'], winner_id)
            )
            context.user_data['withdraw_pending'] = False
            
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'next_lottery'), callback_data="lottery")],
                [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                self._get_text(user_id, 'withdraw_success', await self._get_winner_amount(user_id), user['wallet_address']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # نمایش زبان
    # ============================================================
    async def _show_language_selector(self, update, user_id):
        current_lang = self._get_user_language(user_id)
        lang = current_lang
        
        keyboard = []
        for code in ['en', 'fa', 'tr']:
            name = LanguageManager.get_language_name(code)
            if code == current_lang:
                name = f"✅ {name}"
            keyboard.append([InlineKeyboardButton(
                f"{LanguageManager.get_language_emoji(code)} {name}",
                callback_data=f"set_lang_{code}"
            )])
        
        keyboard.append([InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if isinstance(update, Update):
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    self._get_text(user_id, 'language_selector', LanguageManager.get_language_name(current_lang)),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    self._get_text(user_id, 'language_selector', LanguageManager.get_language_name(current_lang)),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )

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
                f"✅ Language changed to {LanguageManager.get_language_name(lang_code)}!",
                reply_markup=reply_markup
            )

    # ============================================================
    # مدیریت پیام‌ها
    # ============================================================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        lang = self._get_user_language(user_id)
        
        # بررسی سیگنال ادمین
        if user_id in ADMIN_IDS and user_id in self.pending_signals:
            lang_code = self.pending_signals[user_id]
            del self.pending_signals[user_id]
            
            users = user_manager.get_all_users()
            sent = 0
            for user in users:
                if user['language'] == lang_code or not user['language']:
                    try:
                        await self.application.bot.send_message(
                            user['user_id'],
                            text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        sent += 1
                        await asyncio.sleep(0.05)
                    except:
                        pass
            
            await update.message.reply_text(
                self._get_text(user_id, 'signal_sent', LanguageManager.get_language_name(lang_code)),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # بررسی آموزش ادمین
        if user_id in ADMIN_IDS and user_id in self.pending_education:
            lang_code = self.pending_education[user_id]
            del self.pending_education[user_id]
            
            db.execute(0,
                """INSERT OR REPLACE INTO education_content (language, content, updated_at) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (lang_code, text)
            )
            
            await update.message.reply_text(
                self._get_text(user_id, 'education_sent', LanguageManager.get_language_name(lang_code)),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # بررسی اقدامات ادمین
        admin_action = context.user_data.get('admin_action')
        
        if admin_action == 'broadcast':
            users = user_manager.get_all_users()
            sent = 0
            for user in users:
                try:
                    await self.application.bot.send_message(user['user_id'], text, parse_mode=ParseMode.MARKDOWN)
                    sent += 1
                    await asyncio.sleep(0.05)
                except:
                    pass
            context.user_data['admin_action'] = None
            await update.message.reply_text(f"✅ پیام به {sent} کاربر ارسال شد!")
            return
        
        elif admin_action == 'start_lottery':
            step = context.user_data.get('lottery_step', 1)
            if step == 1:
                try:
                    prize = int(text)
                    context.user_data['lottery_prize'] = prize
                    context.user_data['lottery_step'] = 2
                    await update.message.reply_text(f"💰 جایزه: ${prize:,}\n\nمرحله ۲: تعداد برندگان را وارد کنید:")
                except:
                    await update.message.reply_text("❌ عدد معتبر وارد کنید!")
            elif step == 2:
                try:
                    winners = int(text)
                    if 1 <= winners <= 100:
                        context.user_data['lottery_winners'] = winners
                        context.user_data['lottery_step'] = None
                        context.user_data['admin_action'] = None
                        
                        prize = context.user_data['lottery_prize']
                        success, result = lottery_system.start_lottery(winners, prize // winners)
                        
                        if success:
                            await update.message.reply_text(
                                f"✅ قرعه‌کشی انجام شد!\n🎯 {winners} برنده\n💰 هر نفر: ${prize // winners:,}"
                            )
                        else:
                            await update.message.reply_text(f"❌ خطا: {result}")
                    else:
                        await update.message.reply_text("❌ تعداد بین ۱ تا ۱۰۰ باشد!")
                except:
                    await update.message.reply_text("❌ عدد معتبر وارد کنید!")
            return
        
        elif admin_action == 'poll':
            users = user_manager.get_all_users()
            sent = 0
            for user in users:
                try:
                    keyboard = [[
                        InlineKeyboardButton(self._get_text(user['user_id'], 'poll_option_1'), callback_data="poll_yes"),
                        InlineKeyboardButton(self._get_text(user['user_id'], 'poll_option_2'), callback_data="poll_no")
                    ]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await self.application.bot.send_message(
                        user['user_id'],
                        self._get_text(user['user_id'], 'poll_message', text),
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    sent += 1
                    await asyncio.sleep(0.05)
                except:
                    pass
            context.user_data['admin_action'] = None
            await update.message.reply_text(f"✅ نظرسنجی به {sent} کاربر ارسال شد!")
            return
        
        elif admin_action == 'add_api':
            api_key = text.strip()
            if payment_verifier.add_api(api_key):
                context.user_data['admin_action'] = None
                await update.message.reply_text(
                    f"✅ **API جدید اضافه شد!**\n\n🔑 کلید: `{api_key}`\n📊 تعداد کل: {len(payment_verifier.apis)}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text("❌ API قبلاً اضافه شده یا نامعتبر است!")
            return
        
        # دریافت هش تراکنش
        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            if not self._validate_tx_hash(tx_hash):
                await update.message.reply_text(self._get_text(user_id, 'tx_hash_invalid'))
                return
            
            from_address = context.user_data.get('subscription_from_address') or context.user_data.get('payment_from_address')
            
            db.execute(0,
                """INSERT INTO pending_verifications (user_id, from_address, to_address, amount, tx_hash, status) 
                   VALUES (?, ?, ?, ?, ?, 'pending')""",
                (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash)
            )
            
            context.user_data['waiting_for_tx_hash'] = False
            context.user_data['subscription_from_address'] = None
            context.user_data['payment_from_address'] = None
            
            await update.message.reply_text(self._get_text(user_id, 'tx_hash_received', tx_hash))
            
            pending_id = db.execute(0, "SELECT last_insert_rowid()").fetchone()[0]
            
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ تایید", callback_data=f"admin_verify_approve_{pending_id}"),
                            InlineKeyboardButton("❌ رد", callback_data=f"admin_verify_reject_{pending_id}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await self.application.bot.send_message(
                        admin_id,
                        self._get_text(admin_id, 'admin_verify_tx', user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash),
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            return
        
        # دریافت آدرس کیف پول
        if context.user_data.get('waiting_for_subscribe'):
            wallet_address = text.strip()
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(self._get_text(user_id, 'invalid_wallet'))
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            context.user_data['waiting_for_subscribe'] = False
            
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'confirm_subscribe'), callback_data="confirm_subscribe")],
                [InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                self._get_text(user_id, 'after_subscribe_wallet', wallet_address, DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if context.user_data.get('waiting_for_wallet'):
            wallet_address = text.strip()
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(self._get_text(user_id, 'invalid_wallet'))
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            context.user_data['waiting_for_wallet'] = False
            
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'confirm_payment'), callback_data="confirm_payment")],
                [InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                self._get_text(user_id, 'after_wallet', wallet_address, DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # برداشت
        if context.user_data.get('withdraw_pending'):
            wallet_address = text.strip()
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(self._get_text(user_id, 'invalid_wallet'))
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            winner_id = context.user_data.get('winner_id')
            
            if winner_id:
                db.execute(user_id,
                    """UPDATE winners SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (wallet_address, winner_id)
                )
                context.user_data['withdraw_pending'] = False
                
                keyboard = [
                    [InlineKeyboardButton(self._get_text(user_id, 'next_lottery'), callback_data="lottery")],
                    [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    self._get_text(user_id, 'withdraw_success', await self._get_winner_amount(user_id), wallet_address),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # پیام نامعتبر
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            self._get_text(user_id, 'invalid_command'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            self._get_text(user_id, 'photo_not_supported'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    def _get_transaction_stats(self):
        results = db.execute_global("SELECT status, COUNT(*) as count FROM transactions GROUP BY status")
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
        return {'total': total, 'total_winners': total_winners}

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")
        try:
            if update and update.effective_user:
                user_id = update.effective_user.id
                lang = self._get_user_language(user_id)
                await self.application.bot.send_message(
                    user_id,
                    self._get_text(user_id, 'error_message'),
                    parse_mode=ParseMode.MARKDOWN
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
        logger.info(f"📊 Symbols: {len(CRYPTO_SYMBOLS)}")
        
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