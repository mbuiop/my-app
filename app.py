# ============================================================
# ربات قرعه‌کشی هوشمند UTYOB - نسخه نهایی با TTS فوق‌حرفه‌ای
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
import shutil
import time
import os
import sys
import re
import tempfile
import subprocess
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

BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
ADMIN_IDS = [327855654]

TRONGRID_APIS = [
    "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
]

DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PAYMENT_AMOUNT = 100

DB_SHARDS = 1000
CACHE_TTL = 300

# ============================================================
# سیستم چندزبانه کامل
# ============================================================
class LanguageManager:
    LANGUAGES = {
        'en': {
            'name': 'English',
            'emoji': '🇬🇧',
            'welcome': "🎮 **Welcome to UTYOB Lottery Bot!**\n\n💰 Win amazing prizes up to $10,000!\n🎯 Fair and transparent lottery system\n🌟 Join now and test your luck!",
            'main_menu': "🎯 **UTYOB Lottery Bot**\n\nSelect an option below:\n👇👇👇",
            'lottery': "🎰 Join Lottery",
            'referral': "🔗 Referral",
            'guide': "📖 Guide",
            'language': "🌐 Change Language",
            'admin_panel': "⚙️ Admin Panel",
            'youtube_download': "🎬 YouTube Downloader",
            'invoice_maker': "🧾 Invoice Maker",
            'text_to_speech': "🔊 Text to Speech",
            'no_subscription': "❌ **You don't have an active subscription!**\n\nTo participate in the lottery, you must first purchase a subscription.\n\n💰 Subscription cost: $100\n📅 Validity: 1 month\n\nClick the button below to subscribe.",
            'subscribe': "🔄 Subscribe Now",
            'back': "🔙 Back",
            'main_menu_btn': "🔙 Main Menu",
            'lottery_back': "🎰 Back to Lottery",
            'close': "❌ Close",
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
            'referral_text': "🔗 **UTYOB Referral System**\n\n👤 You: {}\n📊 Invites: {}\n💰 Rewards: ${}\n\n🔑 **Your referral code:**\n`{}`\n\n🔗 **Referral link:**\n{}\n\n💰 **Referral reward:**\n• 5% of deposit per invite\n• Instant reward after verification\n\n📤 Share this link with your friends!",
            'share': "📤 Share",
            'referral_joined': "🎉 **New referral joined!**\n\n👤 {}\n🔗 Referred by: {}\n💰 Your reward: ${:.2f}",
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
            'poll_thanks': "✅ Thank you for your vote!\n\nYou selected: {}\n📊 Your opinion matters!",
            'poll_result_admin': "📊 **Poll Result**\n\n👤 User: {}\n📝 Question: {}\n✅ Answer: {}\n🕐 Time: {}",
            'poll_yes': "Yes ✅",
            'poll_no': "No ❌",
            'youtube_downloader': "🎬 **YouTube Downloader**\n\nSend me a YouTube link and I'll download it for you!\n\n📌 Supported:\n• Videos (4K/1080p/720p/480p)\n• Audio only\n• Shorts\n\n📤 **Send the YouTube link:**",
            'invoice_maker_text': "🧾 **Invoice Maker**\n\nClick the **Open Invoice Maker** button below to open the tool:\n\n✨ Fast and simple!\n\n📌 After finishing, click **Close** to return.\n\n📥 Downloads are saved to your gallery.",
            'open_invoice_btn': "🧾 Open Invoice Maker",
            'downloading': "⏳ Downloading... Please wait.",
            'download_success': "✅ **Download completed!** 🎉\n\n📥 File ready for download.",
            'download_failed': "❌ **Download failed!**\n\n🔹 Reason: {}\n\n📌 Make sure the link is correct and the video is available.",
            'invalid_url': "❌ Invalid URL!\n\nPlease send a valid YouTube link.",
            'processing': "🔄 Processing your request...",
            'video_quality': "🎬 **Select Quality:**\n\nChoose the quality you want:",
            'quality_4k': "📱 4K Ultra HD",
            'quality_1080': "📱 1080p Full HD",
            'quality_720': "📱 720p HD",
            'quality_480': "📱 480p SD",
            'quality_audio': "🎵 Audio Only",
            'download_started': "⏳ Download started... This may take a few seconds.",
            'tts_title': "🔊 **Text to Speech Converter**\n\nSend me any text and I'll convert it to speech!\n\n📌 **Features:**\n• 30+ languages supported\n• Natural voice quality\n• Adjustable speed (4 levels)\n• Download as MP3 (320kbps)\n• High quality audio processing\n\n🌐 **Select your language:**",
            'tts_lang_select': "🌐 **Select Language:**\n\nChoose your preferred language from {}+ options:",
            'tts_speed_select': "⚡ **Select Speed:**\n\nChoose the speed you want:",
            'tts_speed_slow': "🐢 Slow",
            'tts_speed_normal': "⚡ Normal",
            'tts_speed_fast': "🚀 Fast",
            'tts_speed_very_fast': "🔥 Very Fast",
            'tts_waiting_text': "📝 **Send me the text to convert to speech:**\n\n💡 You can send long texts (up to 5000 characters).\n\n🎯 Supported languages:\n",
            'tts_text_too_long': "❌ **Text too long!**\n\n📝 Your text: {}\n📌 Maximum: 5000 characters\n\nPlease send a shorter text.",
            'tts_converting': "🔊 **Converting text to speech...**\n\n📝 Text length: {} characters\n⏳ This may take a few seconds...",
            'tts_success': "🔊 **Text-to-Speech Completed!** 🎉\n\n📝 Text: `{}`\n📊 Words: {}\n⏱️ Duration: ~{} seconds\n📦 Size: {} KB\n🔊 Language: {}\n⚡ Speed: {}\n🎧 Quality: 320 kbps\n\n💡 Listen and enjoy! 🎧",
            'tts_failed': "❌ **Conversion failed!**\n\n🔹 Reason: {}\n\n📌 Please check:\n• Text length (max 5000 chars)\n• Internet connection\n• Try again with shorter text",
            'tts_again': "🔄 Convert Another",
            'tts_installing': "⚠️ **ffmpeg not found!**\n\nPlease install ffmpeg to use this feature:\n\n📌 **Installation:**\n• Windows: https://ffmpeg.org/download.html\n• Linux: `sudo apt install ffmpeg`\n• macOS: `brew install ffmpeg`\n\nAfter installation, restart the bot.",
        },
        'fa': {
            'name': 'فارسی',
            'emoji': '🇮🇷',
            'welcome': "🎮 **به ربات قرعه‌کشی UTYOB خوش آمدید!**\n\n💰 برنده جوایز شگفت‌انگیز تا ۱۰۰۰۰ دلار شوید!\n🎯 سیستم قرعه‌کشی عادلانه و شفاف\n🌟 همین حالا بپیوندید و شانس خود را امتحان کنید!",
            'main_menu': "🎯 **ربات قرعه‌کشی UTYOB**\n\nیکی از گزینه‌های زیر را انتخاب کنید:\n👇👇👇",
            'lottery': "🎰 شرکت در قرعه‌کشی",
            'referral': "🔗 رفرال",
            'guide': "📖 راهنمایی",
            'language': "🌐 تغییر زبان",
            'admin_panel': "⚙️ پنل مدیریت",
            'youtube_download': "🎬 دانلودر یوتیوب",
            'invoice_maker': "🧾 فاکتور ساز",
            'text_to_speech': "🔊 تبدیل متن به گفتار",
            'no_subscription': "❌ **شما اشتراک فعال ندارید!**\n\nبرای شرکت در قرعه‌کشی، ابتدا باید اشتراک تهیه کنید.\n\n💰 هزینه اشتراک: ۱۰۰ دلار\n📅 مدت اعتبار: ۱ ماه\n\nبرای تهیه اشتراک، روی دکمه زیر کلیک کنید.",
            'subscribe': "🔄 خرید اشتراک",
            'back': "🔙 بازگشت",
            'main_menu_btn': "🔙 منوی اصلی",
            'lottery_back': "🎰 بازگشت به قرعه‌کشی",
            'close': "❌ بستن",
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
            'referral_text': "🔗 **سیستم رفرال UTYOB**\n\n👤 شما: {}\n📊 تعداد دعوت‌ها: {}\n💰 پاداش: ${}\n\n🔑 **کد رفرال شما:**\n`{}`\n\n🔗 **لینک دعوت:**\n{}\n\n💰 **پاداش دعوت:**\n• به ازای هر دعوت: ۵٪ از واریز\n• پاداش فوری پس از تایید\n\n📤 لینک را برای دوستان خود ارسال کنید!",
            'share': "📤 اشتراک‌گذاری",
            'referral_joined': "🎉 **دعوت جدید!**\n\n👤 {}\n🔗 دعوت کننده: {}\n💰 پاداش شما: ${:.2f}",
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
            'poll_thanks': "✅ از رای شما متشکریم!\n\nشما انتخاب کردید: {}\n📊 نظر شما برای ما مهم است!",
            'poll_result_admin': "📊 **نتیجه نظرسنجی**\n\n👤 کاربر: {}\n📝 سوال: {}\n✅ پاسخ: {}\n🕐 زمان: {}",
            'poll_yes': "بله ✅",
            'poll_no': "خیر ❌",
            'youtube_downloader': "🎬 **دانلودر یوتیوب**\n\nلینک یوتیوب خود را بفرستید تا دانلود کنم!\n\n📌 پشتیبانی:\n• ویدیو (۴K/۱۰۸۰p/۷۲۰p/۴۸۰p)\n• فقط صدا\n• Shorts\n\n📤 **لینک یوتیوب را بفرستید:**",
            'invoice_maker_text': "🧾 **فاکتور ساز**\n\nبرای باز کردن فاکتور ساز، روی دکمه زیر کلیک کنید:\n\n✨ سریع و ساده!\n\n📌 پس از اتمام، روی **بستن** کلیک کنید تا برگردید.\n\n📥 دانلودها در گالری شما ذخیره می‌شوند.",
            'open_invoice_btn': "🧾 باز کردن فاکتور ساز",
            'downloading': "⏳ در حال دانلود... لطفاً صبر کنید.",
            'download_success': "✅ **دانلود کامل شد!** 🎉\n\n📥 فایل آماده دانلود است.",
            'download_failed': "❌ **دانلود ناموفق!**\n\n🔹 دلیل: {}\n\n📌 مطمئن شوید لینک صحیح است و ویدیو در دسترس است.",
            'invalid_url': "❌ لینک نامعتبر!\n\nلطفاً یک لینک معتبر یوتیوب ارسال کنید.",
            'processing': "🔄 در حال پردازش درخواست شما...",
            'video_quality': "🎬 **کیفیت مورد نظر را انتخاب کنید:**",
            'quality_4k': "📱 4K فوق‌العاده",
            'quality_1080': "📱 1080p Full HD",
            'quality_720': "📱 720p HD",
            'quality_480': "📱 480p SD",
            'quality_audio': "🎵 فقط صدا",
            'download_started': "⏳ دانلود شروع شد... چند ثانیه طول می‌کشد.",
            'tts_title': "🔊 **تبدیل متن به گفتار حرفه‌ای**\n\nهر متنی را بفرستید تا به گفتار تبدیل کنم!\n\n📌 **ویژگی‌ها:**\n• پشتیبانی از ۳۰+ زبان\n• صدای طبیعی و با کیفیت\n• ۴ سطح سرعت قابل تنظیم\n• خروجی MP3 با کیفیت ۳۲۰kbps\n• پردازش حرفه‌ای صدا\n\n🌐 **زبان خود را انتخاب کنید:**",
            'tts_lang_select': "🌐 **انتخاب زبان:**\n\nزبان مورد نظر خود را از {}+ گزینه انتخاب کنید:",
            'tts_speed_select': "⚡ **انتخاب سرعت:**\n\nسرعت مورد نظر را انتخاب کنید:",
            'tts_speed_slow': "🐢 کند",
            'tts_speed_normal': "⚡ معمولی",
            'tts_speed_fast': "🚀 سریع",
            'tts_speed_very_fast': "🔥 خیلی سریع",
            'tts_waiting_text': "📝 **متن خود را برای تبدیل به گفتار بفرستید:**\n\n💡 می‌توانید متن‌های طولانی (تا ۵۰۰۰ کاراکتر) ارسال کنید.\n\n🎯 زبان‌های پشتیبانی شده:\n",
            'tts_text_too_long': "❌ **متن خیلی طولانی است!**\n\n📝 متن شما: {}\n📌 حداکثر: ۵۰۰۰ کاراکتر\n\nلطفاً متن کوتاه‌تری ارسال کنید.",
            'tts_converting': "🔊 **در حال تبدیل متن به گفتار...**\n\n📝 طول متن: {} کاراکتر\n⏳ چند ثانیه صبر کنید...",
            'tts_success': "🔊 **تبدیل متن به گفتار کامل شد!** 🎉\n\n📝 متن: `{}`\n📊 تعداد کلمات: {}\n⏱️ مدت زمان: ~{} ثانیه\n📦 حجم: {} KB\n🔊 زبان: {}\n⚡ سرعت: {}\n🎧 کیفیت: ۳۲۰ kbps\n\n💡 گوش کنید و لذت ببرید! 🎧",
            'tts_failed': "❌ **تبدیل ناموفق!**\n\n🔹 دلیل: {}\n\n📌 لطفاً بررسی کنید:\n• طول متن (حداکثر ۵۰۰۰ کاراکتر)\n• اتصال اینترنت\n• دوباره با متن کوتاه‌تر تلاش کنید",
            'tts_again': "🔄 تبدیل مجدد",
            'tts_installing': "⚠️ **ffmpeg پیدا نشد!**\n\nلطفاً برای استفاده از این قابلیت ffmpeg را نصب کنید:\n\n📌 **نصب:**\n• Windows: https://ffmpeg.org/download.html\n• Linux: `sudo apt install ffmpeg`\n• macOS: `brew install ffmpeg`\n\nپس از نصب، ربات را مجدداً راه‌اندازی کنید.",
        },
        'tr': {
            'name': 'Türkçe',
            'emoji': '🇹🇷',
            'welcome': "🎮 **UTYOB Piyango Botuna Hoş Geldiniz!**\n\n💰 10.000$'a kadar harika ödüller kazanın!\n🎯 Adil ve şeffaf piyango sistemi\n🌟 Hemen katıl ve şansını dene!",
            'main_menu': "🎯 **UTYOB Piyango Botu**\n\nAşağıdaki seçeneklerden birini seçin:\n👇👇👇",
            'lottery': "🎰 Piyangoya Katıl",
            'referral': "🔗 Referans",
            'guide': "📖 Rehber",
            'language': "🌐 Dil Değiştir",
            'admin_panel': "⚙️ Yönetim Paneli",
            'youtube_download': "🎬 YouTube İndirici",
            'invoice_maker': "🧾 Fatura Oluşturucu",
            'text_to_speech': "🔊 Metin Seslendirme",
            'no_subscription': "❌ **Aktif aboneliğiniz yok!**\n\nPiyangoya katılmak için önce abonelik satın almalısınız.\n\n💰 Abonelik ücreti: 100$\n📅 Geçerlilik: 1 ay\n\nAbone olmak için aşağıdaki butona tıklayın.",
            'subscribe': "🔄 Abone Ol",
            'back': "🔙 Geri",
            'main_menu_btn': "🔙 Ana Menü",
            'lottery_back': "🎰 Piyangoya Dön",
            'close': "❌ Kapat",
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
            'referral_text': "🔗 **UTYOB Referans Sistemi**\n\n👤 Siz: {}\n📊 Davetler: {}\n💰 Ödül: ${}\n\n🔑 **Referans kodunuz:**\n`{}`\n\n🔗 **Referans linki:**\n{}\n\n💰 **Referans ödülü:**\n• Her davet için %5 yatırım\n• Doğrulama sonrası anında ödül\n\n📤 Bu linki arkadaşlarınızla paylaşın!",
            'share': "📤 Paylaş",
            'referral_joined': "🎉 **Yeni referans katıldı!**\n\n👤 {}\n🔗 Davet eden: {}\n💰 Ödülünüz: ${:.2f}",
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
            'poll_thanks': "✅ Oyunuz için teşekkürler!\n\nSeçiminiz: {}\n📊 Görüşünüz bizim için önemli!",
            'poll_result_admin': "📊 **Anket Sonucu**\n\n👤 Kullanıcı: {}\n📝 Soru: {}\n✅ Cevap: {}\n🕐 Zaman: {}",
            'poll_yes': "Evet ✅",
            'poll_no': "Hayır ❌",
            'youtube_downloader': "🎬 **YouTube İndirici**\n\nYouTube linkini gönderin, sizin için indireyim!\n\n📌 Destek:\n• Videolar (4K/1080p/720p/480p)\n• Sadece Ses\n• Shorts\n\n📤 **YouTube linkini gönderin:**",
            'invoice_maker_text': "🧾 **Fatura Oluşturucu**\n\nFatura oluşturucuyu açmak için aşağıdaki düğmeye tıklayın:\n\n✨ Hızlı ve kolay!\n\n📌 Bitirdikten sonra **Kapat**'a tıklayarak geri dönün.\n\n📥 İndirmeler galerinize kaydedilir.",
            'open_invoice_btn': "🧾 Fatura Oluşturucuyu Aç",
            'downloading': "⏳ İndiriliyor... Lütfen bekleyin.",
            'download_success': "✅ **İndirme tamamlandı!** 🎉\n\n📥 Dosya indirilmeye hazır.",
            'download_failed': "❌ **İndirme başarısız!**\n\n🔹 Sebep: {}\n\n📌 Linkin doğru olduğundan ve videonun mevcut olduğundan emin olun.",
            'invalid_url': "❌ Geçersiz URL!\n\nLütfen geçerli bir YouTube linki gönderin.",
            'processing': "🔄 İsteğiniz işleniyor...",
            'video_quality': "🎬 **Kalite seçin:**",
            'quality_4k': "📱 4K Ultra HD",
            'quality_1080': "📱 1080p Full HD",
            'quality_720': "📱 720p HD",
            'quality_480': "📱 480p SD",
            'quality_audio': "🎵 Sadece Ses",
            'download_started': "⏳ İndirme başladı... Birkaç saniye sürebilir.",
            'tts_title': "🔊 **Profesyonel Metin Seslendirme**\n\nHerhangi bir metni gönderin, seslendireyim!\n\n📌 **Özellikler:**\n• 30+ dil desteği\n• Doğal ve kaliteli ses\n• 4 farklı hız seviyesi\n• 320kbps MP3 çıktısı\n• Profesyonel ses işleme\n\n🌐 **Dil seçin:**",
            'tts_lang_select': "🌐 **Dil Seçin:**\n\nTercih ettiğiniz dili {}+ seçenek arasından seçin:",
            'tts_speed_select': "⚡ **Hız Seçin:**\n\nİstediğiniz hızı seçin:",
            'tts_speed_slow': "🐢 Yavaş",
            'tts_speed_normal': "⚡ Normal",
            'tts_speed_fast': "🚀 Hızlı",
            'tts_speed_very_fast': "🔥 Çok Hızlı",
            'tts_waiting_text': "📝 **Seslendirilecek metni gönderin:**\n\n💡 Uzun metinler gönderebilirsiniz (5000 karaktere kadar).\n\n🎯 Desteklenen diller:\n",
            'tts_text_too_long': "❌ **Metin çok uzun!**\n\n📝 Metniniz: {}\n📌 Maksimum: 5000 karakter\n\nLütfen daha kısa bir metin gönderin.",
            'tts_converting': "🔊 **Metin seslendiriliyor...**\n\n📝 Metin uzunluğu: {} karakter\n⏳ Birkaç saniye sürebilir...",
            'tts_success': "🔊 **Metin Seslendirme Tamamlandı!** 🎉\n\n📝 Metin: `{}`\n📊 Kelime sayısı: {}\n⏱️ Süre: ~{} saniye\n📦 Boyut: {} KB\n🔊 Dil: {}\n⚡ Hız: {}\n🎧 Kalite: 320 kbps\n\n💡 Dinleyin ve keyfini çıkarın! 🎧",
            'tts_failed': "❌ **Seslendirme başarısız!**\n\n🔹 Sebep: {}\n\n📌 Lütfen kontrol edin:\n• Metin uzunluğu (max 5000 karakter)\n• İnternet bağlantısı\n• Daha kısa metinle tekrar deneyin",
            'tts_again': "🔄 Tekrar Dene",
            'tts_installing': "⚠️ **ffmpeg bulunamadı!**\n\nBu özelliği kullanmak için ffmpeg yükleyin:\n\n📌 **Yükleme:**\n• Windows: https://ffmpeg.org/download.html\n• Linux: `sudo apt install ffmpeg`\n• macOS: `brew install ffmpeg`\n\nYüklemeden sonra botu yeniden başlatın.",
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
# دیتابیس
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
                referral_rewards REAL DEFAULT 0,
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
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                url TEXT,
                media_type TEXT,
                file_path TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poll_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                poll_question TEXT,
                answer TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT,
                data TEXT,
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloads_user ON downloads(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_poll_user ON poll_responses(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_states ON user_states(user_id)')
        
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

cache = CacheManager(max_size=50000)

# ============================================================
# سیستم YouTube Downloader
# ============================================================
class YouTubeDownloader:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=30)
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs("downloads", exist_ok=True)
        
    async def download_youtube(self, url: str, quality: str = "best") -> Tuple[bool, str, str]:
        try:
            import yt_dlp
            
            output_template = os.path.join(self.temp_dir, "youtube_%(id)s.%(ext)s")
            
            if quality == "audio":
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
                    'outtmpl': output_template,
                    'quiet': True,
                    'no_warnings': True,
                    'continuedl': True,
                    'retries': 10,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'm4a',
                        'preferredquality': '192',
                    }],
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    },
                }
            else:
                has_ffmpeg = shutil.which('ffmpeg') is not None
                
                format_map = {
                    "4k": "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]",
                    "1080": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
                    "720": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
                    "480": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
                    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                }
                
                format_str = format_map.get(quality, format_map["best"])
                
                ydl_opts = {
                    'format': format_str,
                    'outtmpl': output_template,
                    'quiet': True,
                    'no_warnings': True,
                    'continuedl': True,
                    'retries': 10,
                    'fragment_retries': 10,
                    'skip_download': False,
                    'socket_timeout': 60,
                    'prefer_ffmpeg': has_ffmpeg,
                    'merge_output_format': 'mp4' if has_ffmpeg else None,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    },
                }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    return False, None, "No media information found"
                
                output_file = None
                file_id = info.get('id')
                
                if file_id:
                    extensions = ['.mp4', '.mkv', '.webm', '.m4a', '.mp3']
                    for ext in extensions:
                        candidate = os.path.join(self.temp_dir, f"youtube_{file_id}{ext}")
                        if os.path.exists(candidate):
                            output_file = candidate
                            break
                
                if output_file and os.path.exists(output_file):
                    return True, output_file, f"Downloaded: {info.get('title', 'Unknown')}"
                    
            return False, None, "Download failed"
            
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            return False, None, str(e)
    
    def validate_youtube_url(self, url: str) -> bool:
        patterns = [
            r'(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)',
            r'(m\.youtube\.com/watch\?v=)'
        ]
        return any(re.search(p, url) for p in patterns)

youtube_downloader = YouTubeDownloader()

# ============================================================
# سیستم Text-to-Speech فوق‌حرفه‌ای
# ============================================================
class TextToSpeech:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs("tts", exist_ok=True)
        self._check_ffmpeg()
        
    def _check_ffmpeg(self):
        """بررسی وجود ffmpeg"""
        if shutil.which('ffmpeg') is None:
            logger.error("❌ ffmpeg not found!")
            return False
        logger.info("✅ ffmpeg found")
        return True
        
    async def convert_to_speech(self, text: str, lang: str = "en", speed: str = "normal") -> Tuple[bool, str, dict]:
        try:
            from gtts import gTTS
            from pydub import AudioSegment
            import io
            
            # ============================================================
            # پشتیبانی کامل از 30+ زبان
            # ============================================================
            lang_map = {
                'en': 'en', 'fa': 'fa', 'tr': 'tr',
                'es': 'es', 'fr': 'fr', 'de': 'de',
                'it': 'it', 'pt': 'pt', 'ru': 'ru',
                'ja': 'ja', 'ko': 'ko', 'zh': 'zh-CN',
                'ar': 'ar', 'hi': 'hi', 'nl': 'nl',
                'el': 'el', 'he': 'he', 'id': 'id',
                'ms': 'ms', 'pl': 'pl', 'ro': 'ro',
                'sv': 'sv', 'th': 'th', 'uk': 'uk',
                'vi': 'vi', 'bg': 'bg', 'cs': 'cs',
                'da': 'da', 'fi': 'fi', 'hu': 'hu',
                'no': 'no', 'sk': 'sk', 'sl': 'sl'
            }
            
            tts_lang = lang_map.get(lang, 'en')
            
            # ============================================================
            # تنظیمات سرعت
            # ============================================================
            speed_map = {
                'slow': 0.7,
                'normal': 1.0,
                'fast': 1.3,
                'very_fast': 1.6
            }
            
            speed_factor = speed_map.get(speed, 1.0)
            is_slow = (speed == 'slow')
            
            # ============================================================
            # تولید فایل صوتی
            # ============================================================
            filename = f"tts_{int(time.time())}.mp3"
            filepath = os.path.join(self.temp_dir, filename)
            
            # تبدیل با gTTS
            tts = gTTS(text=text, lang=tts_lang, slow=is_slow)
            tts.save(filepath)
            
            # ============================================================
            # پردازش با pydub برای کیفیت بالا
            # ============================================================
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                try:
                    audio = AudioSegment.from_mp3(filepath)
                    
                    # تغییر سرعت
                    if speed_factor != 1.0 and not is_slow:
                        if speed_factor > 1.0:
                            audio = audio.speedup(playback_speed=speed_factor)
                        else:
                            audio = audio._spawn(audio.raw_data, overrides={
                                "frame_rate": int(audio.frame_rate * speed_factor)
                            })
                            audio = audio.set_frame_rate(audio.frame_rate)
                    
                    # افزایش کیفیت صدا
                    audio = audio.high_pass_filter(80)  # حذف نویز
                    audio = audio.normalize()  # عادی‌سازی
                    audio = audio + 3  # افزایش بلندی
                    
                    # خروجی با کیفیت بالا
                    audio.export(filepath, format="mp3", bitrate="320k")
                    
                except Exception as e:
                    logger.warning(f"Audio processing failed: {e}")
            
            # ============================================================
            # اطلاعات فایل
            # ============================================================
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                file_size = os.path.getsize(filepath) // 1024
                words = len(text.split())
                
                try:
                    audio = AudioSegment.from_mp3(filepath)
                    duration = len(audio) // 1000
                except:
                    duration = int(words / 2)
                
                info = {
                    'size': file_size,
                    'words': words,
                    'duration': duration,
                    'lang': tts_lang,
                    'speed': speed,
                    'text_preview': text[:100] + ('...' if len(text) > 100 else '')
                }
                
                return True, filepath, info
                
            return False, None, {"error": "Conversion failed - empty file"}
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False, None, {"error": str(e)}
    
    def get_supported_languages(self) -> List[Dict]:
        """لیست زبان‌های پشتیبانی شده"""
        return [
            {'code': 'en', 'name': '🇬🇧 English'},
            {'code': 'fa', 'name': '🇮🇷 فارسی'},
            {'code': 'tr', 'name': '🇹🇷 Türkçe'},
            {'code': 'es', 'name': '🇪🇸 Español'},
            {'code': 'fr', 'name': '🇫🇷 Français'},
            {'code': 'de', 'name': '🇩🇪 Deutsch'},
            {'code': 'it', 'name': '🇮🇹 Italiano'},
            {'code': 'pt', 'name': '🇵🇹 Português'},
            {'code': 'ru', 'name': '🇷🇺 Русский'},
            {'code': 'ja', 'name': '🇯🇵 日本語'},
            {'code': 'ko', 'name': '🇰🇷 한국어'},
            {'code': 'zh', 'name': '🇨🇳 中文'},
            {'code': 'ar', 'name': '🇸🇦 العربية'},
            {'code': 'hi', 'name': '🇮🇳 हिन्दी'},
            {'code': 'nl', 'name': '🇳🇱 Nederlands'},
            {'code': 'el', 'name': '🇬🇷 Ελληνικά'},
            {'code': 'he', 'name': '🇮🇱 עברית'},
            {'code': 'id', 'name': '🇮🇩 Bahasa Indonesia'},
            {'code': 'pl', 'name': '🇵🇱 Polski'},
            {'code': 'ro', 'name': '🇷🇴 Română'},
            {'code': 'sv', 'name': '🇸🇪 Svenska'},
            {'code': 'th', 'name': '🇹🇭 ไทย'},
            {'code': 'uk', 'name': '🇺🇦 Українська'},
            {'code': 'vi', 'name': '🇻🇳 Tiếng Việt'},
            {'code': 'bg', 'name': '🇧🇬 Български'},
            {'code': 'cs', 'name': '🇨🇿 Čeština'},
            {'code': 'da', 'name': '🇩🇰 Dansk'},
            {'code': 'fi', 'name': '🇫🇮 Suomi'},
            {'code': 'hu', 'name': '🇭🇺 Magyar'},
            {'code': 'no', 'name': '🇳🇴 Norsk'},
            {'code': 'sk', 'name': '🇸🇰 Slovenčina'},
            {'code': 'sl', 'name': '🇸🇮 Slovenščina'},
        ]

tts = TextToSpeech()

# ============================================================
# سیستم تایید پرداخت
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.api_stats = {api: {'requests': 0, 'success': 0, 'errors': 0, 'last_reset': time.time()} for api in self.apis}
        self.lock = threading.RLock()
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=30)
        
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
        for api in self.apis:
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
        return False, None, "Transaction not found or invalid"
        
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
# سیستم قرعه‌کشی
# ============================================================
class LotterySystem:
    def __init__(self):
        self.current_lottery = None
        self.is_running = False
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=20)
        
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
                
            tournament_size = min(5, len(temp_users))
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
                   (winners_count, prize_per_winner, total_prize, status) 
                   VALUES (?, ?, ?, 'completed')""",
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
# سیستم مدیریت کاربران
# ============================================================
class UserManager:
    @staticmethod
    def register_user(user_id, username=None, first_name=None, last_name=None, referred_by=None):
        try:
            cursor = db.execute(user_id,
                "SELECT user_id FROM users WHERE user_id = ?",
                (user_id,)
            )
            
            if not cursor.fetchone():
                referral_code = UserManager._generate_referral_code(user_id)
                
                if referred_by:
                    db.execute(user_id,
                        """INSERT INTO users 
                           (user_id, username, first_name, last_name, referral_code, referred_by, language) 
                           VALUES (?, ?, ?, ?, ?, ?, 'en')""",
                        (user_id, username, first_name, last_name, referral_code, referred_by)
                    )
                    UserManager._add_referral_reward(referred_by, user_id, first_name or username or str(user_id))
                else:
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
    def _add_referral_reward(referrer_id, new_user_id, new_user_name):
        try:
            reward_amount = 5.0
            db.execute(referrer_id,
                "UPDATE users SET referral_rewards = referral_rewards + ? WHERE user_id = ?",
                (reward_amount, referrer_id)
            )
            db.execute(referrer_id,
                """INSERT INTO transactions 
                   (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
                   VALUES (?, 'referral', 'reward', ?, ?, 'verified', CURRENT_TIMESTAMP)""",
                (referrer_id, reward_amount, f"REFERRAL_{new_user_id}_{int(time.time())}")
            )
            logger.info(f"Referral reward added: {reward_amount} for user {referrer_id}")
        except Exception as e:
            logger.error(f"Error adding referral reward: {e}")
            
    @staticmethod
    def _generate_referral_code(user_id):
        import hashlib
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
            results = db.execute_global("SELECT user_id, username, first_name, referral_rewards FROM users")
            return results
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

user_manager = UserManager()

# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.pending_verifications = {}
        self.executor = ThreadPoolExecutor(max_workers=100)
        self._setup_handlers()
        self._init_system()
        
    def _init_system(self):
        try:
            cursor = db.execute(0, "SELECT value FROM settings WHERE key = 'system_initialized'")
            if not cursor.fetchone():
                db.execute(0, "INSERT INTO settings (key, value) VALUES ('system_initialized', 'true')")
                logger.info("سیستم مقداردهی شد")
            else:
                logger.info("سیستم قبلاً مقداردهی شده")
        except Exception as e:
            logger.error(f"Error initializing system: {e}")
            
    def _setup_handlers(self):
        app = self.application
        
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("referral", self.referral_command))
        app.add_handler(CommandHandler("language", self.language_command))
        app.add_handler(CommandHandler("back", self.back_command))
        
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language$"))
        
        app.add_handler(CallbackQueryHandler(self.youtube_download_callback, pattern="^youtube_download$"))
        app.add_handler(CallbackQueryHandler(self.invoice_maker_callback, pattern="^invoice_maker$"))
        app.add_handler(CallbackQueryHandler(self.tts_callback, pattern="^tts$"))
        
        app.add_handler(CallbackQueryHandler(self.tts_lang_callback, pattern="^tts_lang_"))
        app.add_handler(CallbackQueryHandler(self.tts_speed_callback, pattern="^tts_speed_"))
        app.add_handler(CallbackQueryHandler(self.youtube_quality_callback, pattern="^youtube_quality_"))
        
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
        app.add_handler(CallbackQueryHandler(self.admin_user_list_callback, pattern="^admin_user_list$"))
        app.add_handler(CallbackQueryHandler(self.admin_reset_user_callback, pattern="^admin_reset_user$"))
        app.add_handler(CallbackQueryHandler(self.admin_subscribed_users_callback, pattern="^admin_subscribed_users$"))
        
        app.add_handler(CallbackQueryHandler(self.poll_response_callback, pattern="^poll_yes$"))
        app.add_handler(CallbackQueryHandler(self.poll_response_callback, pattern="^poll_no$"))
        
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))
        
        app.add_handler(CallbackQueryHandler(self.start_lottery_confirm_callback, pattern="^start_lottery_confirm$"))
        app.add_handler(CallbackQueryHandler(self.pay_winners_confirm_callback, pattern="^pay_winners_confirm$"))
        
        app.add_handler(CallbackQueryHandler(self.withdraw_prize_callback, pattern="^withdraw_prize$"))
        app.add_handler(CallbackQueryHandler(self.confirm_withdraw_callback, pattern="^confirm_withdraw$"))
        
        app.add_handler(CallbackQueryHandler(self.set_language_callback, pattern="^set_lang_"))
        
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
            return True
        except:
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
    
    def _get_user_state(self, user_id):
        cursor = db.execute(user_id,
            "SELECT state, data FROM user_states WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        if result:
            return result['state'], json.loads(result['data']) if result['data'] else {}
        return None, {}
    
    def _set_user_state(self, user_id, state, data=None):
        data_json = json.dumps(data) if data else '{}'
        db.execute(user_id,
            """INSERT INTO user_states (user_id, state, data, updated_at) 
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id) DO UPDATE SET 
               state = ?, data = ?, updated_at = CURRENT_TIMESTAMP""",
            (user_id, state, data_json, state, data_json)
        )
    
    def _clear_user_state(self, user_id):
        db.execute(user_id,
            "DELETE FROM user_states WHERE user_id = ?",
            (user_id,)
        )
    
    def _get_pending_transactions(self):
        return db.execute_global(
            "SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC"
        )
    
    def _get_unpaid_winners(self):
        return db.execute_global(
            "SELECT * FROM winners WHERE paid_status = 0 ORDER BY created_at ASC"
        )
    
    def _check_winner(self, user_id):
        cursor = db.execute(user_id,
            """SELECT * FROM winners 
               WHERE user_id = ? 
               AND paid_status = 0 
               ORDER BY created_at DESC LIMIT 1""",
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
        
        referred_by = None
        if context.args and context.args[0].startswith('ref_'):
            ref_code = context.args[0].replace('ref_', '')
            cursor = db.execute(0,
                "SELECT user_id FROM users WHERE referral_code = ?",
                (ref_code,)
            )
            ref_user = cursor.fetchone()
            if ref_user and ref_user['user_id'] != user.id:
                referred_by = ref_user['user_id']
        
        user_manager.register_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            referred_by
        )
        
        lang = self._get_user_language(user.id)
        
        if referred_by:
            try:
                referrer_lang = self._get_user_language(referred_by)
                await self.application.bot.send_message(
                    chat_id=referred_by,
                    text=LanguageManager.get_text(referrer_lang, 'referral_joined',
                        user.first_name or user.username or str(user.id),
                        str(user.id),
                        5.0
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error sending referral notification: {e}")
        
        keyboard = [
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'lottery'), callback_data="lottery")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'referral'), callback_data="referral")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'youtube_download'), callback_data="youtube_download")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'text_to_speech'), callback_data="tts")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'invoice_maker'), callback_data="invoice_maker")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'guide'), callback_data="guide")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'language'), callback_data="language")]
        ]
        
        if user.id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton(LanguageManager.get_text(lang, 'admin_panel'), callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'welcome') + "\n\n" + LanguageManager.get_text(lang, 'main_menu'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]]
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
    
    async def back_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        state, data = self._get_user_state(user_id)
        
        if state in ['youtube_quality', 'tts_lang_select', 'tts_speed_select', 'tts_waiting_text']:
            self._clear_user_state(user_id)
            await self.main_menu_callback(update, context)
        elif state == 'waiting_wallet':
            self._clear_user_state(user_id)
            await self.lottery_callback(update, context)
        elif state == 'waiting_subscribe_wallet':
            self._clear_user_state(user_id)
            await self.subscribe_callback(update, context)
        elif state == 'waiting_withdraw_wallet':
            self._clear_user_state(user_id)
            await self.main_menu_callback(update, context)
        else:
            self._clear_user_state(user_id)
            await self.main_menu_callback(update, context)

    # ============================================================
    # کالبک‌های منوی اصلی
    # ============================================================
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query:
            await query.answer()
            user_id = query.from_user.id
            from_msg = query
        else:
            user_id = update.effective_user.id
            from_msg = update
        
        self._clear_user_state(user_id)
        lang = self._get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'lottery'), callback_data="lottery")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'referral'), callback_data="referral")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'youtube_download'), callback_data="youtube_download")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'text_to_speech'), callback_data="tts")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'invoice_maker'), callback_data="invoice_maker")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'guide'), callback_data="guide")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'language'), callback_data="language")]
        ]
        
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton(LanguageManager.get_text(lang, 'admin_panel'), callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'main_menu'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
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
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'subscribe'), callback_data="subscribe")],
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_subscription'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = [
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'lottery'), callback_data="join_lottery")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎰 **UTYOB {LanguageManager.get_text(lang, 'lottery')}**\n\n"
            f"👤 {user['first_name'] or user_id}\n\n"
            f"💰 Up to $10,000\n"
            f"🎯 Fair lottery",
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
        
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]]
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
            
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ Language changed to {LanguageManager.get_language_name(lang_code)}!",
                reply_markup=reply_markup
            )

    # ============================================================
    # کالبک‌های YouTube Downloader
    # ============================================================
    async def youtube_download_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        self._clear_user_state(user_id)
        
        keyboard = [
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'quality_4k'), callback_data="youtube_quality_4k")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'quality_1080'), callback_data="youtube_quality_1080")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'quality_720'), callback_data="youtube_quality_720")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'quality_480'), callback_data="youtube_quality_480")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'quality_audio'), callback_data="youtube_quality_audio")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        self._set_user_state(user_id, 'youtube_quality')
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'youtube_downloader') + "\n\n" + 
            LanguageManager.get_text(lang, 'video_quality'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def youtube_quality_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        quality = query.data.replace('youtube_quality_', '')
        
        context.user_data['youtube_quality'] = quality
        self._set_user_state(user_id, 'youtube_waiting_link')
        
        quality_names = {
            '4k': '📱 4K Ultra HD',
            '1080': '📱 1080p Full HD',
            '720': '📱 720p HD',
            '480': '📱 480p SD',
            'audio': '🎵 Audio Only'
        }
        
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="youtube_download")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'youtube_downloader') + "\n\n" +
            f"🎬 **Selected Quality:** {quality_names.get(quality, quality)}\n\n" +
            "📤 **Send me the YouTube link:**",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _download_youtube(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        quality = context.user_data.get('youtube_quality', 'best')
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'download_started'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            success, filepath, message = await youtube_downloader.download_youtube(url, quality)
            
            if success and filepath and os.path.exists(filepath):
                file_size = os.path.getsize(filepath) // (1024 * 1024)
                
                with open(filepath, 'rb') as f:
                    if quality == 'audio':
                        await update.message.reply_audio(
                            audio=f,
                            caption=f"🎵 {LanguageManager.get_text(lang, 'download_success')}\n📦 Size: {file_size} MB"
                        )
                    else:
                        await update.message.reply_video(
                            video=f,
                            caption=f"🎬 {LanguageManager.get_text(lang, 'download_success')}\n📦 Size: {file_size} MB",
                            supports_streaming=True
                        )
                
                try:
                    os.remove(filepath)
                except:
                    pass
                
                self._clear_user_state(user_id)
                
                keyboard = [[InlineKeyboardButton("🎬 Download Another", callback_data="youtube_download")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🎬 " + LanguageManager.get_text(lang, 'youtube_downloader'),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'download_failed', message),
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'download_failed', str(e)),
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های Text-to-Speech فوق‌حرفه‌ای
    # ============================================================
    async def tts_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        # بررسی وجود ffmpeg
        if not tts._check_ffmpeg():
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'tts_installing'),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        self._clear_user_state(user_id)
        
        languages = tts.get_supported_languages()
        keyboard = []
        
        # نمایش زبان‌ها به صورت 2 ستونه
        for i in range(0, len(languages), 2):
            row = []
            row.append(InlineKeyboardButton(
                languages[i]['name'],
                callback_data=f"tts_lang_{languages[i]['code']}"
            ))
            if i + 1 < len(languages):
                row.append(InlineKeyboardButton(
                    languages[i+1]['name'],
                    callback_data=f"tts_lang_{languages[i+1]['code']}"
                ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        self._set_user_state(user_id, 'tts_lang_select')
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'tts_title'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def tts_lang_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        tts_lang = query.data.replace('tts_lang_', '')
        
        context.user_data['tts_lang'] = tts_lang
        self._set_user_state(user_id, 'tts_speed_select', {'lang': tts_lang})
        
        keyboard = [
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'tts_speed_slow'), callback_data="tts_speed_slow")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'tts_speed_normal'), callback_data="tts_speed_normal")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'tts_speed_fast'), callback_data="tts_speed_fast")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'tts_speed_very_fast'), callback_data="tts_speed_very_fast")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="tts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'tts_speed_select'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def tts_speed_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        speed = query.data.replace('tts_speed_', '')
        
        context.user_data['tts_speed'] = speed
        
        # لیست زبان‌های پشتیبانی شده برای نمایش
        languages = tts.get_supported_languages()
        lang_names = {l['code']: l['name'] for l in languages}
        selected_lang = context.user_data.get('tts_lang', 'en')
        
        self._set_user_state(user_id, 'tts_waiting_text', {
            'lang': selected_lang,
            'speed': speed
        })
        
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="tts")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = LanguageManager.get_text(lang, 'tts_waiting_text')
        text += f"\n\n🌐 **Selected:** {lang_names.get(selected_lang, selected_lang)}\n"
        text += f"⚡ **Speed:** {LanguageManager.get_text(lang, f'tts_speed_{speed}')}"
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _handle_tts_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        if len(text) > 5000:
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'tts_text_too_long', len(text)),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'tts_converting', len(text)),
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            tts_lang = context.user_data.get('tts_lang', 'en')
            tts_speed = context.user_data.get('tts_speed', 'normal')
            
            success, filepath, info = await tts.convert_to_speech(text, tts_lang, tts_speed)
            
            if success and filepath and os.path.exists(filepath):
                words = len(text.split())
                duration = info.get('duration', int(words / 2))
                
                with open(filepath, 'rb') as f:
                    await update.message.reply_audio(
                        audio=f,
                        caption=LanguageManager.get_text(lang, 'tts_success',
                            text[:100] + ('...' if len(text) > 100 else ''),
                            words,
                            duration,
                            info.get('size', 0),
                            tts_lang.upper(),
                            tts_speed
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                try:
                    os.remove(filepath)
                except:
                    pass
                
                keyboard = [
                    [InlineKeyboardButton(LanguageManager.get_text(lang, 'tts_again'), callback_data="tts")],
                    [InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🎯 **What would you like to do next?**",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                self._clear_user_state(user_id)
            else:
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'tts_failed', info.get('error', 'Unknown error')),
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"TTS error: {e}")
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'tts_failed', str(e)),
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های فاکتور ساز
    # ============================================================
    async def invoice_maker_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        self._clear_user_state(user_id)
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'open_invoice_btn'),
                web_app=WebAppInfo(url="https://mbuiop.github.io/Tablikgram/")
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'close'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'invoice_maker_text'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های نظرسنجی
    # ============================================================
    async def poll_response_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        answer = query.data
        poll_question = context.user_data.get('poll_question', 'Unknown question')
        
        if answer == 'poll_yes':
            display_answer = LanguageManager.get_text(lang, 'poll_yes')
        else:
            display_answer = LanguageManager.get_text(lang, 'poll_no')
        
        db.execute(user_id,
            "INSERT INTO poll_responses (user_id, poll_question, answer) VALUES (?, ?, ?)",
            (user_id, poll_question, display_answer)
        )
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'poll_thanks', display_answer),
            parse_mode=ParseMode.MARKDOWN
        )
        
        user = user_manager.get_user(user_id)
        user_name = user['first_name'] or user['username'] or str(user_id)
        
        for admin_id in ADMIN_IDS:
            try:
                admin_lang = self._get_user_language(admin_id)
                await self.application.bot.send_message(
                    chat_id=admin_id,
                    text=LanguageManager.get_text(admin_lang, 'poll_result_admin',
                        user_name, poll_question, display_answer, datetime.now().strftime('%Y-%m-%d %H:%M')
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error sending poll result to admin {admin_id}: {e}")

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
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "✅ شما قبلاً اشتراک فعال دارید!",
                reply_markup=reply_markup
            )
            return
        
        self._set_user_state(user_id, 'waiting_subscribe_wallet')
        
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'cancel'), callback_data="main_menu")]]
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
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]]
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
            
            self._clear_user_state(user_id)
            
            keyboard = [
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'lottery'), callback_data="lottery")],
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]
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
            
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'cancel'), callback_data="main_menu")]]
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
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'subscribe'), callback_data="subscribe")],
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_subscription'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        self._set_user_state(user_id, 'waiting_wallet')
        
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'cancel'), callback_data="main_menu")]]
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
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]]
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
            self._clear_user_state(user_id)
            
            keyboard = [
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'lottery_back'), callback_data="lottery")],
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]
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
            
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'cancel'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'payment_failed', result['message']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های تایید/رد ادمین
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
            [InlineKeyboardButton(LanguageManager.get_text(user_lang, 'lottery'), callback_data="lottery")],
            [InlineKeyboardButton(LanguageManager.get_text(user_lang, 'main_menu_btn'), callback_data="main_menu")]
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
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(user_lang, 'retry'), callback_data="subscribe")]]
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
    # پنل مدیریت
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
        
        pending_count = len(self._get_pending_transactions())
        unpaid_winners = len(self._get_unpaid_winners())
        
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton(f"✅ تایید دستی ({pending_count})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📊 ارسال نظرسنجی", callback_data="admin_poll")],
            [InlineKeyboardButton(f"💰 واریز به برندگان ({unpaid_winners})", callback_data="admin_pay_winners")],
            [InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_user_list")],
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
            f"انتخاب کنید:"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_subscribed_users_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        await query.edit_message_text("👥 مدیریت کاربران اشتراکی در حال توسعه...")

    async def admin_user_list_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        users = user_manager.get_all_users()
        
        if not users:
            text = "👥 هیچ کاربری ثبت نشده است!"
        else:
            text = "👥 **لیست کامل کاربران:**\n\n"
            for i, user in enumerate(users, 1):
                text += f"{i}. {user['user_id']} - {user['first_name'] or user['username'] or 'Unknown'}\n"
                text += f"   💰 پاداش رفرال: ${user['referral_rewards']:.2f}\n\n"
                if i >= 50:
                    text += f"... و {len(users) - 50} نفر دیگر"
                    break
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await query.message.reply_text(
                    part,
                    reply_markup=reply_markup if part == parts[-1] else None,
                    parse_mode=ParseMode.MARKDOWN
                )
            await query.delete_message()
        else:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    async def admin_reset_user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        await query.edit_message_text(
            "🔄 برای بازنشانی کاربر، از لیست کاربران استفاده کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
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
            f"آیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟",
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
                InlineKeyboardButton(f"✅ تایید #{p['id']}", callback_data=f"admin_verify_approve_{p['id']}"),
                InlineKeyboardButton(f"❌ رد #{p['id']}", callback_data=f"admin_verify_reject_{p['id']}")
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
            "⚠️ این نظرسنجی به تمام کاربران ارسال می‌شود.",
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
        
        total_prize = sum(w['prize_amount'] for w in winners)
        
        keyboard = [
            [InlineKeyboardButton("✅ تایید پرداخت", callback_data="pay_winners_confirm")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text('fa', 'pay_winners_confirm', len(winners), total_prize),
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
            "لطفاً کلید API جدید را وارد کنید:",
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
            f"⚡ **سیستم:**\n"
            f"• کش: {cache_stats['size']} آیتم\n"
            f"• نرخ برخورد: {cache_stats['hit_rate']:.1f}%\n"
            f"• API‌ها: {len(payment_verifier.apis)}\n"
            f"• شاردها: {DB_SHARDS}\n"
            f"• رشته‌های اجرایی: ۱۰۰"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های قرعه‌کشی
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

    async def pay_winners_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        winners = self._get_unpaid_winners()
        
        if not winners:
            await query.edit_message_text("❌ برنده‌ای برای پرداخت وجود ندارد!")
            return
        
        for winner in winners:
            db.execute(winner['user_id'],
                "UPDATE winners SET paid_status = 1, paid_at = CURRENT_TIMESTAMP WHERE id = ?",
                (winner['id'],)
            )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **برندگان پرداخت شدند!**\n\nتعداد: {len(winners)}\nمجموع جایزه: ${sum(w['prize_amount'] for w in winners)}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # برداشت جایزه
    # ============================================================
    async def withdraw_prize_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        winner = self._check_winner(user_id)
        if not winner:
            keyboard = [
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'lottery'), callback_data="lottery")],
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_winner'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if winner['paid_status'] == 1:
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'already_paid',
                    winner['prize_amount'], winner['paid_at']
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        self._set_user_state(user_id, 'waiting_withdraw_wallet', {'winner_id': winner['id']})
        
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'cancel'), callback_data="main_menu")]]
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
        
        state, data = self._get_user_state(user_id)
        if state != 'waiting_withdraw_wallet':
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⚠️ No pending withdrawal.",
                reply_markup=reply_markup
            )
            return
        
        user = user_manager.get_user(user_id)
        if not user or not user['wallet_address']:
            keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ No wallet address found!",
                reply_markup=reply_markup
            )
            return
        
        winner_id = data.get('winner_id')
        if winner_id:
            db.execute(user_id,
                """UPDATE winners 
                   SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (user['wallet_address'], winner_id)
            )
            
            self._clear_user_state(user_id)
            
            keyboard = [
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'next_lottery'), callback_data="lottery")],
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]
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
        
        rewards = user['referral_rewards'] or 0
        
        text = LanguageManager.get_text(lang, 'referral_text',
            user['first_name'] or user_id,
            referred_count,
            rewards,
            referral_code,
            referral_link
        )
        
        keyboard = [
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'share'), url=f"https://t.me/share/url?url={referral_link}")],
            [InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")]
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
        
        keyboard.append([InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")])
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
    # مدیریت پیام‌ها
    # ============================================================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        lang = self._get_user_language(user_id)
        
        state, data = self._get_user_state(user_id)
        
        # YouTube Downloader
        if state == 'youtube_waiting_link':
            if text.startswith('http://') or text.startswith('https://'):
                if youtube_downloader.validate_youtube_url(text):
                    await self._download_youtube(update, context, text)
                    return
                else:
                    await update.message.reply_text(
                        LanguageManager.get_text(lang, 'invalid_url'),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            else:
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_url'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # Text-to-Speech
        if state == 'tts_waiting_text':
            if text.strip():
                await self._handle_tts_text(update, context, text.strip())
                return
            else:
                await update.message.reply_text(
                    "❌ Please send a valid text!",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # مدیریت actions
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
            context.user_data['poll_question'] = text
            await self._send_poll(update, text, context)
            return
        
        # تایید هش تراکنش
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
            
            self._clear_user_state(user_id)
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'tx_hash_received', tx_hash),
                parse_mode=ParseMode.MARKDOWN
            )
            
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
        
        # اشتراک - وارد کردن کیف پول
        if state == 'waiting_subscribe_wallet':
            wallet_address = text.strip()
            
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_wallet'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            self._clear_user_state(user_id)
            
            keyboard = [
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'confirm_subscribe'), callback_data="confirm_subscribe")],
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'cancel'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'after_subscribe_wallet', wallet_address, DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # شرکت در قرعه‌کشی - وارد کردن کیف پول
        if state == 'waiting_wallet':
            wallet_address = text.strip()
            
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_wallet'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            self._clear_user_state(user_id)
            
            keyboard = [
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'confirm_payment'), callback_data="confirm_payment")],
                [InlineKeyboardButton(LanguageManager.get_text(lang, 'cancel'), callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'after_wallet', wallet_address, DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # برداشت جایزه - وارد کردن کیف پول
        if state == 'waiting_withdraw_wallet':
            wallet_address = text.strip()
            
            if not self._validate_wallet_address(wallet_address):
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_wallet'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            user_manager.update_user(user_id, wallet_address=wallet_address)
            
            winner_id = data.get('winner_id')
            if winner_id:
                db.execute(user_id,
                    """UPDATE winners 
                       SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP 
                       WHERE id = ?""",
                    (wallet_address, winner_id)
                )
                
                self._clear_user_state(user_id)
                
                keyboard = [
                    [InlineKeyboardButton(LanguageManager.get_text(lang, 'next_lottery'), callback_data="lottery")],
                    [InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]
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
            return
        
        # پیام نامعتبر
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'invalid_command'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # توابع کمکی مدیریت پیام
    # ============================================================
    async def _handle_lottery_steps(self, update, text, context):
        user_id = update.effective_user.id
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
                    await update.message.reply_text("❌ تعداد نامعتبر! لطفاً عددی بین ۱ تا ۱۰۰ وارد کنید.")
            except ValueError:
                await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
        
        elif step == 3:
            try:
                prize = float(text)
                if prize >= 10:
                    winners = context.user_data.get('lottery_winners', 1)
                    
                    await update.message.reply_text(
                        f"✅ **اطلاعات قرعه‌کشی:**\n\n"
                        f"• تعداد برندگان: {winners}\n"
                        f"• جایزه هر نفر: ${prize:,}\n"
                        f"• کل جایزه: ${winners * prize:,}\n\n"
                        f"⚠️ قرعه‌کشی در حال اجراست...",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    success, result = lottery_system.start_lottery(winners, prize)
                    
                    if success:
                        winners_list = "\n".join([f"• کاربر {uid}" for uid in result['winners']])
                        
                        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(
                            f"✅ **قرعه‌کشی با موفقیت انجام شد!** 🎉\n\n"
                            f"📊 **جزئیات:**\n"
                            f"• شماره قرعه‌کشی: {result['lottery_id']}\n"
                            f"• تعداد برندگان: {winners}\n"
                            f"• جایزه هر نفر: ${prize:,}\n"
                            f"• کل جایزه: ${winners * prize:,}\n\n"
                            f"👥 **برندگان:**\n{winners_list}",
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
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
                                    text=f"🎉 **تبریک! شما برنده شدید!**\n💰 جایزه: ${prize}\n🏆 قرعه‌کشی #{result['lottery_id']}",
                                    reply_markup=reply_markup,
                                    parse_mode=ParseMode.MARKDOWN
                                )
                            except Exception as e:
                                logger.error(f"Error sending to {winner_id}: {e}")
                        
                        context.user_data['admin_action'] = None
                    else:
                        await update.message.reply_text(
                            f"❌ **خطا در اجرای قرعه‌کشی**\n\n🔹 دلیل: {result}"
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
                f"📊 تعداد کل API‌ها: {len(payment_verifier.apis)}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "❌ **خطا در اضافه کردن API!**\n\nاین API قبلاً اضافه شده است یا نامعتبر است.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _send_poll(self, update, text, context):
        user_id = update.effective_user.id
        
        await update.message.reply_text("⏳ در حال ارسال نظرسنجی به کاربران...\nلطفاً صبر کنید.")
        
        users = db.execute_global("SELECT user_id, language FROM users")
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                user_lang = user['language'] if user['language'] else 'en'
                
                keyboard = [
                    [
                        InlineKeyboardButton(LanguageManager.get_text(user_lang, 'poll_option_1'), callback_data="poll_yes"),
                        InlineKeyboardButton(LanguageManager.get_text(user_lang, 'poll_option_2'), callback_data="poll_no")
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
            f"✅ **ارسال نظرسنجی کامل شد!**\n\n📤 ارسال شده: {sent:,}\n❌ ناموفق: {failed:,}\n📊 کل: {sent + failed:,}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _send_broadcast(self, update, text, context):
        user_id = update.effective_user.id
        
        await update.message.reply_text("⏳ در حال ارسال پیام به کاربران...\nلطفاً صبر کنید.")
        
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
            f"✅ **ارسال پیام همگانی کامل شد!**\n\n📤 ارسال شده: {sent:,}\n❌ ناموفق: {failed:,}\n📊 کل: {sent + failed:,}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]]
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
                
                keyboard = [[InlineKeyboardButton(LanguageManager.get_text(lang, 'main_menu_btn'), callback_data="main_menu")]]
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
def main():
    try:
        # بروزرسانی وابستگی‌ها
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "gTTS", "pydub"], 
                         capture_output=True, check=False)
            logger.info("✅ Dependencies updated")
        except:
            pass
        
        bot = UTYOBot()
        
        logger.info("🚀 UTYOB Bot starting...")
        logger.info(f"👥 Admins: {len(ADMIN_IDS)}")
        logger.info(f"🗄️ Shards: {DB_SHARDS}")
        logger.info(f"🔑 APIs: {len(TRONGRID_APIS)}")
        logger.info(f"⚡ Threads: 100")
        logger.info(f"💾 Cache size: 50,000 items")
        logger.info("🎬 YouTube Downloader: Ready (4K/1080p/720p/480p/Audio)")
        logger.info("🔊 Text-to-Speech: Ready (30+ Languages)")
        logger.info("🧾 Invoice Maker: Ready")
        logger.info("⚡ Polling started")

        bot.application.run_polling(
            poll_interval=0.0,
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )

    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Program stopped")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")