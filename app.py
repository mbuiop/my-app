# ============================================================
# ربات قرعه‌کشی هوشمند UTYOB - نسخه نهایی فوق‌پیشرفته با معماری میکروسرویس
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
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

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
            'instagram_download': "📸 Instagram Downloader",
            'invoice_maker': "🧾 Invoice Maker",
            'build_robot': "🤖 Build Robot",
            'my_robots': "📋 My Robots",
            'no_subscription': "❌ **You don't have an active subscription!**\n\nTo participate in the lottery, you must first purchase a subscription.\n\n💰 Subscription cost: $100\n📅 Validity: 1 month\n\nClick the button below to subscribe.",
            'subscribe': "🔄 Subscribe Now",
            'back': "🔙 Back",
            'main_menu_btn': "🔙 Main Menu",
            'lottery_back': "🎰 Back to Lottery",
            'close': "❌ Close",
            'subscribed_users': "👥 Subscribed Users",
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
            'referral_text': "🔗 **UTYOB Referral System**\n\n👤 You: {}\n📊 Invites: {}\n💰 Rewards: ${}\n\n🔑 **Your referral code:**\n`{}`\n\n🔗 **Referral link:**\n{}\n\n💰 **Referral reward:**\n• 5% discount for you\n• 5% discount for your friend\n• Instant reward after verification\n\n📤 Share this link with your friends!",
            'share': "📤 Share",
            'referral_joined': "🎉 **New referral joined!**\n\n👤 {}\n🔗 Referred by: {}\n💰 You both got 5% discount!",
            'referral_discount': "🎉 **You got 5% discount!**\n\n👤 {}\n🔗 Referred by: {}\n💰 5% discount applied to your subscription!",
            'guide_text': "📖 **UTYOB Bot Complete Guide**\n\n🎯 **How it works:**\n1. **Register**: Use /start to register\n2. **Subscription**: Purchase subscription to participate\n3. **Deposit**: Send $100 to the specified address\n4. **Participate**: Join the lottery after verification\n5. **Win**: Receive prize if you win\n\n💰 **Deposit amount:**\n- Fixed amount: $100\n- Deposit address: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- Network: TRC20\n\n🎁 **Prizes:**\n- 1st prize: 50% of total\n- 2nd prize: 30% of total\n- 3rd prize: 20% of total\n\n🔗 **Referral system:**\n- Each user has unique referral code\n- 5% discount for both you and your friend\n\n⚠️ **Rules:**\n- One participation per lottery per user\n- Previous winners have lower chance\n- All transactions verified automatically\n\n📞 **Support:**\nContact admin for questions.",
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
            'instagram_downloader': "📸 **Instagram Downloader**\n\nSend me an Instagram post/reel URL and I'll download it for you!\n\n📤 Send the link:",
            'invoice_maker_text': "🧾 **Invoice Maker**\n\nClick the button below to open the invoice maker tool:\n\n✨ Fast and simple!\n\n📌 After finishing, click **Close** to return.\n\n📥 Downloads are saved to your gallery.",
            'open_invoice_btn': "🧾 Open Invoice Maker",
            'downloading': "⏳ Downloading... Please wait.",
            'download_success': "✅ **Download completed!**\n\n📥 File ready for download.",
            'download_failed': "❌ **Download failed!**\n\n🔹 Reason: {}\n\n📌 Make sure the link is correct.",
            'invalid_url': "❌ Invalid URL!\n\nPlease send a valid Instagram link.",
            'processing': "🔄 Processing your request...",
            'lottery_announcement': "🎰 **Lottery Announcement**\n\n📅 Date: {}\n💰 Prize: ${}\n👥 Winners: {}\n\n📤 To participate, please send $100 to:\n`{}`\n\n⚠️ **Important:**\n• Use TRC20 network only\n• Enter your source wallet address\n• Make sure your subscription is active\n\n🎯 Good luck to everyone!",
            'lottery_winner_announcement': "🎉 **Lottery Winner!**\n\n🏆 Congratulations!\n👤 User: {}\n💰 Prize: ${}\n📤 Wallet: {}\n🌍 Country: {}\n\n✅ Prize has been sent to your wallet!\n🙏 Enjoy your winnings!",
            'lottery_winner_admin': "🏆 **Lottery Winners**\n\n📅 Date: {}\n💰 Total Prize: ${}\n👥 Winners:\n{}\n\n✅ All winners have been paid.",
            'lottery_no_winners': "❌ No eligible users for lottery.",
            'lottery_paid': "✅ Winners paid successfully!",
            'enter_lottery_date': "📅 **Enter Lottery Date**\n\nPlease enter the lottery date (YYYY-MM-DD):\nExample: `2024-12-31`",
            'enter_lottery_prize': "💰 **Enter Prize Amount**\n\nPlease enter the prize amount for each winner:\nExample: `500`",
            'enter_lottery_winners': "👥 **Enter Number of Winners**\n\nPlease enter the number of winners:\nExample: `3`",
            'lottery_confirm': "✅ **Lottery Confirmation**\n\n📅 Date: {}\n💰 Prize: ${}\n👥 Winners: {}\n\n⚠️ Are you sure you want to start the lottery?",
            'lottery_started': "🎰 **Lottery Started!**\n\n📅 Date: {}\n💰 Prize: ${}\n👥 Winners: {}\n\n🎯 Selecting winners...",
            'lottery_completed': "✅ **Lottery Completed!**\n\n📅 Date: {}\n💰 Prize: ${}\n👥 Winners: {}\n\n🏆 Winners have been selected and notified.",
            'pay_winners_confirm': "💰 **Pay Winners**\n\nTotal winners: {}\nTotal prize: ${}\n\n⚠️ Are you sure you want to pay all winners?",
            'pay_winners_success': "✅ **Winners Paid!**\n\nTotal winners: {}\nTotal prize: ${}\n\n📢 All winners have been notified.",
            'subscribed_users_list': "👥 **Subscribed Users**\n\nTotal: {}\n\n{}",
            'no_subscribed_users': "❌ No subscribed users found.",
            'build_robot_title': "🤖 **Build Your Robot**\n\nSend your bot token to create a robot.",
            'build_robot_help': "🔑 **How to get token:**\n1. Open @BotFather\n2. Send /newbot\n3. Choose a name\n4. Choose a username\n5. Copy the token",
            'build_robot_success': "✅ **Robot created successfully!** 🎉\n\n🔹 Robot ID: `{}`\n🔹 Admin ID: `{}`\n🔹 Language: {}\n\n📌 Your robot is ready to use!",
            'build_robot_failed': "❌ **Robot creation failed!**\n\n🔹 Reason: {}\n\nPlease try again.",
            'no_uploaded_files': "⚠️ **No robot files uploaded!**\n\nPlease contact admin to upload robot files.",
            'select_file': "📁 **Select a robot file:**\n\nChoose your preferred language:",
            'my_robots_title': "📋 **Your Robots**\n\nYou have {} robot(s).",
            'no_robots': "❌ No robots found.\n\nUse the button below to build one.",
            'robot_status': "🤖 Robot #{}\n🔹 Token: `{}...`\n🔹 Language: {}\n🔹 Status: {}\n🔹 Created: {}",
            'robot_delete_confirm': "⚠️ **Delete Robot?**\n\nRobot ID: {}\n\nAre you sure?",
            'robot_deleted': "✅ **Robot deleted successfully!**",
            'robot_delete_failed': "❌ **Failed to delete robot!**",
            'build_new_robot': "🤖 Build New Robot",
            'delete_robot': "🗑️ Delete",
            'cancel_delete': "❌ Cancel",
            'invoice_confirm': "🔗 **Open Invoice Maker**\n\nClick the button below to open the invoice maker tool.\n\n⚠️ After opening, you will be redirected to the tool.",
            'open_invoice_confirm': "✅ Open Invoice Maker",
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
            'instagram_download': "📸 دانلودر اینستاگرام",
            'invoice_maker': "🧾 فاکتور ساز",
            'build_robot': "🤖 ساخت ربات",
            'my_robots': "📋 ربات‌های من",
            'no_subscription': "❌ **شما اشتراک فعال ندارید!**\n\nبرای شرکت در قرعه‌کشی، ابتدا باید اشتراک تهیه کنید.\n\n💰 هزینه اشتراک: ۱۰۰ دلار\n📅 مدت اعتبار: ۱ ماه\n\nبرای تهیه اشتراک، روی دکمه زیر کلیک کنید.",
            'subscribe': "🔄 خرید اشتراک",
            'back': "🔙 بازگشت",
            'main_menu_btn': "🔙 منوی اصلی",
            'lottery_back': "🎰 بازگشت به قرعه‌کشی",
            'close': "❌ بستن",
            'subscribed_users': "👥 کاربران اشتراکی",
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
            'referral_text': "🔗 **سیستم رفرال UTYOB**\n\n👤 شما: {}\n📊 تعداد دعوت‌ها: {}\n💰 پاداش: ${}\n\n🔑 **کد رفرال شما:**\n`{}`\n\n🔗 **لینک دعوت:**\n{}\n\n💰 **پاداش دعوت:**\n• ۵٪ تخفیف برای شما\n• ۵٪ تخفیف برای دوست شما\n• پاداش فوری پس از تایید\n\n📤 لینک را برای دوستان خود ارسال کنید!",
            'share': "📤 اشتراک‌گذاری",
            'referral_joined': "🎉 **دعوت جدید!**\n\n👤 {}\n🔗 دعوت کننده: {}\n💰 هر دو ۵٪ تخفیف گرفتید!",
            'referral_discount': "🎉 **۵٪ تخفیف گرفتید!**\n\n👤 {}\n🔗 دعوت کننده: {}\n💰 ۵٪ تخفیف به اشتراک شما اعمال شد!",
            'guide_text': "📖 **راهنمای کامل ربات UTYOB**\n\n🎯 **نحوه کار:**\n1. **ثبت‌نام**: با دستور /start ثبت‌نام کنید\n2. **اشتراک**: برای شرکت در قرعه‌کشی، اشتراک تهیه کنید\n3. **واریز**: مبلغ ۱۰۰ دلار به آدرس مشخص واریز کنید\n4. **شرکت**: پس از تایید، در قرعه‌کشی شرکت کنید\n5. **برنده**: در صورت برنده شدن، جایزه دریافت کنید\n\n💰 **مبلغ واریز:**\n- مبلغ ثابت: ۱۰۰ دلار\n- آدرس واریز: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- شبکه: TRC20\n\n🎁 **جوایز:**\n- جایزه اول: ۵۰٪ از کل مبلغ\n- جایزه دوم: ۳۰٪ از کل مبلغ\n- جایزه سوم: ۲۰٪ از کل مبلغ\n\n🔗 **سیستم رفرال:**\n- هر کاربر کد رفرال اختصاصی دارد\n- ۵٪ تخفیف برای شما و دوستتان\n\n⚠️ **قوانین:**\n- هر کاربر فقط یک بار در هر قرعه‌کشی شرکت می‌کند\n- برندگان قبلی شانس کمتری در قرعه‌کشی‌های بعدی دارند\n- تمامی تراکنش‌ها به صورت خودکار تایید می‌شوند\n\n📞 **پشتیبانی:**\nبرای سوالات و مشکلات با مدیریت تماس بگیرید.",
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
            'instagram_downloader': "📸 **دانلودر اینستاگرام**\n\nلینک پست یا ریل اینستاگرام را ارسال کنید تا آن را دانلود کنم!\n\n📤 لینک را ارسال کنید:",
            'invoice_maker_text': "🧾 **فاکتور ساز**\n\nبرای ساخت فاکتور، روی دکمه زیر کلیک کنید:\n\n✨ سریع و ساده!\n\n📌 پس از اتمام، روی **بستن** کلیک کنید تا برگردید.\n\n📥 دانلودها در گالری شما ذخیره می‌شوند.",
            'open_invoice_btn': "🧾 باز کردن فاکتور ساز",
            'downloading': "⏳ در حال دانلود... لطفاً صبر کنید.",
            'download_success': "✅ **دانلود کامل شد!**\n\n📥 فایل آماده دانلود است.",
            'download_failed': "❌ **دانلود ناموفق!**\n\n🔹 دلیل: {}\n\n📌 مطمئن شوید لینک صحیح است.",
            'invalid_url': "❌ لینک نامعتبر!\n\nلطفاً یک لینک معتبر از اینستاگرام ارسال کنید.",
            'processing': "🔄 در حال پردازش درخواست شما...",
            'lottery_announcement': "🎰 **اطلاعیه قرعه‌کشی**\n\n📅 تاریخ: {}\n💰 جایزه: ${}\n👥 تعداد برندگان: {}\n\n📤 برای شرکت، لطفاً مبلغ ۱۰۰ دلار به آدرس زیر واریز کنید:\n`{}`\n\n⚠️ **نکات مهم:**\n• فقط از شبکه TRC20 استفاده کنید\n• آدرس کیف پول مبدا خود را وارد کنید\n• اشتراک شما باید فعال باشد\n\n🎯 برای همه آرزوی موفقیت داریم!",
            'lottery_winner_announcement': "🎉 **برنده قرعه‌کشی!**\n\n🏆 تبریک!\n👤 کاربر: {}\n💰 جایزه: ${}\n📤 کیف پول: {}\n🌍 کشور: {}\n\n✅ جایزه به کیف پول شما واریز شد!\n🙏 از برداشت خود لذت ببرید!",
            'lottery_winner_admin': "🏆 **برندگان قرعه‌کشی**\n\n📅 تاریخ: {}\n💰 کل جایزه: ${}\n👥 برندگان:\n{}\n\n✅ تمام برندگان پرداخت شدند.",
            'lottery_no_winners': "❌ کاربران واجد شرایطی برای قرعه‌کشی وجود ندارد.",
            'lottery_paid': "✅ برندگان با موفقیت پرداخت شدند!",
            'enter_lottery_date': "📅 **تاریخ قرعه‌کشی را وارد کنید**\n\nلطفاً تاریخ قرعه‌کشی را وارد کنید (YYYY-MM-DD):\nمثال: `1403-10-11`",
            'enter_lottery_prize': "💰 **مبلغ جایزه را وارد کنید**\n\nلطفاً مبلغ جایزه برای هر برنده را وارد کنید:\nمثال: `500`",
            'enter_lottery_winners': "👥 **تعداد برندگان را وارد کنید**\n\nلطفاً تعداد برندگان را وارد کنید:\nمثال: `3`",
            'lottery_confirm': "✅ **تایید قرعه‌کشی**\n\n📅 تاریخ: {}\n💰 جایزه: ${}\n👥 تعداد برندگان: {}\n\n⚠️ آیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟",
            'lottery_started': "🎰 **قرعه‌کشی شروع شد!**\n\n📅 تاریخ: {}\n💰 جایزه: ${}\n👥 تعداد برندگان: {}\n\n🎯 در حال انتخاب برندگان...",
            'lottery_completed': "✅ **قرعه‌کشی انجام شد!**\n\n📅 تاریخ: {}\n💰 جایزه: ${}\n👥 تعداد برندگان: {}\n\n🏆 برندگان انتخاب و مطلع شدند.",
            'pay_winners_confirm': "💰 **پرداخت به برندگان**\n\nتعداد برندگان: {}\nمجموع جایزه: ${}\n\n⚠️ آیا مطمئن هستید که می‌خواهید به همه برندگان پرداخت کنید؟",
            'pay_winners_success': "✅ **برندگان پرداخت شدند!**\n\nتعداد برندگان: {}\nمجموع جایزه: ${}\n\n📢 همه برندگان مطلع شدند.",
            'subscribed_users_list': "👥 **کاربران اشتراکی**\n\nتعداد: {}\n\n{}",
            'no_subscribed_users': "❌ کاربر اشتراکی یافت نشد.",
            'build_robot_title': "🤖 **ساخت ربات شما**\n\nبرای ساخت ربات، توکن آن را ارسال کنید.",
            'build_robot_help': "🔑 **نحوه دریافت توکن:**\n۱. @BotFather را باز کنید\n۲. /newbot را ارسال کنید\n۳. یک نام انتخاب کنید\n۴. یک نام کاربری انتخاب کنید\n۵. توکن را کپی کنید",
            'build_robot_success': "✅ **ربات با موفقیت ساخته شد!** 🎉\n\n🔹 شناسه ربات: `{}`\n🔹 شناسه ادمین: `{}`\n🔹 زبان: {}\n\n📌 ربات شما آماده استفاده است!",
            'build_robot_failed': "❌ **ساخت ربات ناموفق!**\n\n🔹 دلیل: {}\n\nلطفاً دوباره تلاش کنید.",
            'no_uploaded_files': "⚠️ **هیچ فایل رباتی آپلود نشده است!**\n\nلطفاً با مدیریت تماس بگیرید.",
            'select_file': "📁 **یک فایل ربات را انتخاب کنید:**\n\nزبان مورد نظر خود را انتخاب کنید:",
            'my_robots_title': "📋 **ربات‌های شما**\n\nشما {} ربات دارید.",
            'no_robots': "❌ هیچ رباتی یافت نشد.\n\nاز دکمه زیر برای ساخت ربات استفاده کنید.",
            'robot_status': "🤖 ربات #{}\n🔹 توکن: `{}...`\n🔹 زبان: {}\n🔹 وضعیت: {}\n🔹 ساخته شده: {}",
            'robot_delete_confirm': "⚠️ **حذف ربات؟**\n\nشناسه ربات: {}\n\nآیا مطمئن هستید؟",
            'robot_deleted': "✅ **ربات با موفقیت حذف شد!**",
            'robot_delete_failed': "❌ **حذف ربات ناموفق!**",
            'build_new_robot': "🤖 ساخت ربات جدید",
            'delete_robot': "🗑️ حذف",
            'cancel_delete': "❌ انصراف",
            'invoice_confirm': "🔗 **باز کردن فاکتور ساز**\n\nبرای باز کردن فاکتور ساز، روی دکمه زیر کلیک کنید.\n\n⚠️ پس از باز شدن، به صفحه فاکتور ساز هدایت می‌شوید.",
            'open_invoice_confirm': "✅ باز کردن فاکتور ساز",
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
            'instagram_download': "📸 Instagram İndirici",
            'invoice_maker': "🧾 Fatura Oluşturucu",
            'build_robot': "🤖 Bot Oluştur",
            'my_robots': "📋 Botlarım",
            'no_subscription': "❌ **Aktif aboneliğiniz yok!**\n\nPiyangoya katılmak için önce abonelik satın almalısınız.\n\n💰 Abonelik ücreti: 100$\n📅 Geçerlilik: 1 ay\n\nAbone olmak için aşağıdaki butona tıklayın.",
            'subscribe': "🔄 Abone Ol",
            'back': "🔙 Geri",
            'main_menu_btn': "🔙 Ana Menü",
            'lottery_back': "🎰 Piyangoya Dön",
            'close': "❌ Kapat",
            'subscribed_users': "👥 Abone Kullanıcılar",
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
            'referral_text': "🔗 **UTYOB Referans Sistemi**\n\n👤 Siz: {}\n📊 Davetler: {}\n💰 Ödül: ${}\n\n🔑 **Referans kodunuz:**\n`{}`\n\n🔗 **Referans linki:**\n{}\n\n💰 **Referans ödülü:**\n• Sizin için %5 indirim\n• Arkadaşınız için %5 indirim\n• Doğrulama sonrası anında ödül\n\n📤 Bu linki arkadaşlarınızla paylaşın!",
            'share': "📤 Paylaş",
            'referral_joined': "🎉 **Yeni referans katıldı!**\n\n👤 {}\n🔗 Davet eden: {}\n💰 İkiniz de %5 indirim kazandınız!",
            'referral_discount': "🎉 **%5 indirim kazandınız!**\n\n👤 {}\n🔗 Davet eden: {}\n💰 Aboneliğinize %5 indirim uygulandı!",
            'guide_text': "📖 **UTYOB Bot Tam Rehber**\n\n🎯 **Nasıl çalışır:**\n1. **Kayıt**: /start ile kaydolun\n2. **Abonelik**: Katılmak için abonelik satın alın\n3. **Yatırım**: Belirtilen adrese 100$ gönderin\n4. **Katılım**: Doğrulama sonrası piyangoya katılın\n5. **Kazanç**: Kazanırsanız ödülü alın\n\n💰 **Yatırım tutarı:**\n- Sabit tutar: 100$\n- Yatırım adresi: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- Ağ: TRC20\n\n🎁 **Ödüller:**\n- 1. ödül: Toplamın %50'si\n- 2. ödül: Toplamın %30'u\n- 3. ödül: Toplamın %20'si\n\n🔗 **Referans sistemi:**\n- Her kullanıcının benzersiz referans kodu vardır\n- Sizin ve arkadaşınız için %5 indirim\n\n⚠️ **Kurallar:**\n- Her piyangoda kullanıcı başına bir katılım\n- Önceki kazananların şansı daha düşük\n- Tüm işlemler otomatik doğrulanır\n\n📞 **Destek:**\nSorularınız için yöneticiye başvurun.",
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
            'instagram_downloader': "📸 **Instagram İndirici**\n\nBir Instagram gönderisi/reel URL'si gönderin, sizin için indireyim!\n\n📤 Linki gönder:",
            'invoice_maker_text': "🧾 **Fatura Oluşturucu**\n\nFatura oluşturmak için aşağıdaki düğmeye tıklayın:\n\n✨ Hızlı ve kolay!\n\n📌 Bitirdikten sonra **Kapat**'a tıklayarak geri dönün.\n\n📥 İndirmeler galerinize kaydedilir.",
            'open_invoice_btn': "🧾 Fatura Oluşturucuyu Aç",
            'downloading': "⏳ İndiriliyor... Lütfen bekleyin.",
            'download_success': "✅ **İndirme tamamlandı!**\n\n📥 Dosya indirilmeye hazır.",
            'download_failed': "❌ **İndirme başarısız!**\n\n🔹 Sebep: {}\n\n📌 Linkin doğru olduğundan emin olun.",
            'invalid_url': "❌ Geçersiz URL!\n\nLütfen geçerli bir Instagram linki gönderin.",
            'processing': "🔄 İsteğiniz işleniyor...",
            'lottery_announcement': "🎰 **Piyango Duyurusu**\n\n📅 Tarih: {}\n💰 Ödül: ${}\n👥 Kazananlar: {}\n\n📤 Katılmak için lütfen aşağıdaki adrese 100$ gönderin:\n`{}`\n\n⚠️ **Önemli:**\n• Sadece TRC20 ağını kullanın\n• Kaynak cüzdan adresinizi girin\n• Aboneliğiniz aktif olmalı\n\n🎯 Herkese iyi şanslar!",
            'lottery_winner_announcement': "🎉 **Piyango Kazananı!**\n\n🏆 Tebrikler!\n👤 Kullanıcı: {}\n💰 Ödül: ${}\n📤 Cüzdan: {}\n🌍 Ülke: {}\n\n✅ Ödül cüzdanınıza gönderildi!\n🙏 Kazancınızın tadını çıkarın!",
            'lottery_winner_admin': "🏆 **Piyango Kazananları**\n\n📅 Tarih: {}\n💰 Toplam Ödül: ${}\n👥 Kazananlar:\n{}\n\n✅ Tüm kazananlara ödeme yapıldı.",
            'lottery_no_winners': "❌ Piyango için uygun kullanıcı yok.",
            'lottery_paid': "✅ Kazananlara başarıyla ödeme yapıldı!",
            'enter_lottery_date': "📅 **Piyango Tarihi Girin**\n\nLütfen piyango tarihini girin (YYYY-MM-DD):\nÖrnek: `2024-12-31`",
            'enter_lottery_prize': "💰 **Ödül Miktarını Girin**\n\nLütfen her kazanan için ödül miktarını girin:\nÖrnek: `500`",
            'enter_lottery_winners': "👥 **Kazanan Sayısını Girin**\n\nLütfen kazanan sayısını girin:\nÖrnek: `3`",
            'lottery_confirm': "✅ **Piyango Onayı**\n\n📅 Tarih: {}\n💰 Ödül: ${}\n👥 Kazananlar: {}\n\n⚠️ Piyangoyu başlatmak istediğinize emin misiniz?",
            'lottery_started': "🎰 **Piyango Başladı!**\n\n📅 Tarih: {}\n💰 Ödül: ${}\n👥 Kazananlar: {}\n\n🎯 Kazananlar seçiliyor...",
            'lottery_completed': "✅ **Piyango Tamamlandı!**\n\n📅 Tarih: {}\n💰 Ödül: ${}\n👥 Kazananlar: {}\n\n🏆 Kazananlar seçildi ve bilgilendirildi.",
            'pay_winners_confirm': "💰 **Kazananlara Ödeme**\n\nKazanan sayısı: {}\nToplam ödül: ${}\n\n⚠️ Tüm kazananlara ödeme yapmak istediğinize emin misiniz?",
            'pay_winners_success': "✅ **Kazananlara Ödeme Yapıldı!**\n\nKazanan sayısı: {}\nToplam ödül: ${}\n\n📢 Tüm kazananlar bilgilendirildi.",
            'subscribed_users_list': "👥 **Abone Kullanıcılar**\n\nToplam: {}\n\n{}",
            'no_subscribed_users': "❌ Abone kullanıcı bulunamadı.",
            'build_robot_title': "🤖 **Botunuzu Oluşturun**\n\nBot oluşturmak için tokenini gönderin.",
            'build_robot_help': "🔑 **Token nasıl alınır:**\n1. @BotFather'ı açın\n2. /newbot gönderin\n3. Bir isim seçin\n4. Bir kullanıcı adı seçin\n5. Tokeni kopyalayın",
            'build_robot_success': "✅ **Bot başarıyla oluşturuldu!** 🎉\n\n🔹 Bot ID: `{}`\n🔹 Admin ID: `{}`\n🔹 Dil: {}\n\n📌 Botunuz kullanıma hazır!",
            'build_robot_failed': "❌ **Bot oluşturulamadı!**\n\n🔹 Sebep: {}\n\nLütfen tekrar deneyin.",
            'no_uploaded_files': "⚠️ **Hiç bot dosyası yüklenmedi!**\n\nLütfen yöneticiyle iletişime geçin.",
            'select_file': "📁 **Bir bot dosyası seçin:**\n\nTercih ettiğiniz dili seçin:",
            'my_robots_title': "📋 **Botlarınız**\n\n{} botunuz var.",
            'no_robots': "❌ Bot bulunamadı.\n\nYeni bot oluşturmak için aşağıdaki butonu kullanın.",
            'robot_status': "🤖 Bot #{}\n🔹 Token: `{}...`\n🔹 Dil: {}\n🔹 Durum: {}\n🔹 Oluşturulma: {}",
            'robot_delete_confirm': "⚠️ **Bot Silinsin mi?**\n\nBot ID: {}\n\nEmin misiniz?",
            'robot_deleted': "✅ **Bot başarıyla silindi!**",
            'robot_delete_failed': "❌ **Bot silinemedi!**",
            'build_new_robot': "🤖 Yeni Bot Oluştur",
            'delete_robot': "🗑️ Sil",
            'cancel_delete': "❌ İptal",
            'invoice_confirm': "🔗 **Fatura Oluşturucuyu Aç**\n\nFatura oluşturucuyu açmak için aşağıdaki butona tıklayın.\n\n⚠️ Açtıktan sonra fatura oluşturucu sayfasına yönlendirileceksiniz.",
            'open_invoice_confirm': "✅ Fatura Oluşturucuyu Aç",
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
# دیتابیس با ۱۰۰۰ شارد برای مقیاس‌پذیری بالا
# ============================================================
class DatabaseManager:
    def __init__(self, num_shards=DB_SHARDS):
        self.num_shards = num_shards
        self.connections = {}
        self.locks = {}
        self.executor = ThreadPoolExecutor(max_workers=200)
        self.process_pool = ProcessPoolExecutor(max_workers=50)
        self._init_shards()
        
    def _init_shards(self):
        os.makedirs("data", exist_ok=True)
        for i in range(self.num_shards):
            db_path = f"data/shard_{i}.db"
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=120)
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
                country TEXT DEFAULT 'Unknown',
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
                lottery_date TEXT,
                prize_per_winner REAL,
                winners_count INTEGER,
                total_prize REAL,
                status TEXT DEFAULT 'pending',
                winners_list TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT
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
            CREATE TABLE IF NOT EXISTS user_robots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_token TEXT,
                admin_id INTEGER,
                language TEXT DEFAULT 'en',
                status TEXT DEFAULT 'active',
                file_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploaded_bot_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                file_path TEXT,
                language TEXT,
                file_hash TEXT,
                uploaded_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                port INTEGER,
                username TEXT,
                password TEXT,
                ssh_key TEXT,
                status TEXT DEFAULT 'active',
                max_workers INTEGER DEFAULT 100,
                current_workers INTEGER DEFAULT 0,
                shards INTEGER DEFAULT 100,
                libraries TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_heartbeat TEXT
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lotteries_date ON lotteries(lottery_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lotteries_status ON lotteries(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_robots_user ON user_robots(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_robots_status ON user_robots(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_uploaded_files_language ON uploaded_bot_files(language)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status)')
        
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
        with ThreadPoolExecutor(max_workers=200) as executor:
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
# سیستم کش پیشرفته با Redis-like
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
# سیستم دانلودر فوق‌پیشرفته اینستاگرام
# ============================================================
class InstagramDownloader:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.session = None
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs("downloads", exist_ok=True)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        ]
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=120, connect=10)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=500, limit_per_host=100, ttl_dns_cache=300)
            )
        return self.session
        
    def _get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
    async def download_instagram(self, url: str) -> Tuple[bool, str, str]:
        try:
            # روش اول: استفاده از API GraphQL اینستاگرام
            result = await self._download_with_graphql(url)
            if result[0]:
                return result
            
            # روش دوم: استفاده از embed
            result = await self._download_with_embed(url)
            if result[0]:
                return result
            
            # روش سوم: استفاده از scraper ساده
            result = await self._download_with_scraper(url)
            if result[0]:
                return result
            
            return False, None, "محتوا یافت نشد. لطفاً لینک را بررسی کنید."
            
        except Exception as e:
            logger.error(f"Instagram download error: {e}")
            return False, None, str(e)
    
    async def _download_with_graphql(self, url: str) -> Tuple[bool, str, str]:
        try:
            import re
            import json
            
            session = await self.get_session()
            headers = self._get_headers()
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    return False, None, "Page not found"
                
                html = await response.text()
                
                # استخراج داده از script tag
                script_pattern = r'<script type="text/javascript">window\._sharedData\s*=\s*({.*?});</script>'
                script_match = re.search(script_pattern, html, re.DOTALL)
                
                if script_match:
                    data = json.loads(script_match.group(1))
                    entry_data = data.get('entry_data', {})
                    
                    # برای پست‌ها
                    if 'PostPage' in entry_data:
                        post = entry_data['PostPage'][0].get('graphql', {}).get('shortcode_media', {})
                        video_url = post.get('video_url')
                        if video_url:
                            return await self._download_file(video_url, 'video')
                        
                        display_url = post.get('display_url')
                        if display_url:
                            return await self._download_file(display_url, 'image')
                        
                        # برای چند تصویر
                        edge_sidecar = post.get('edge_sidecar_to_children', {})
                        edges = edge_sidecar.get('edges', [])
                        for edge in edges:
                            node = edge.get('node', {})
                            video_url = node.get('video_url')
                            if video_url:
                                return await self._download_file(video_url, 'video')
                            display_url = node.get('display_url')
                            if display_url:
                                return await self._download_file(display_url, 'image')
                    
                    # برای ریل‌ها
                    if 'ReelPage' in entry_data:
                        reel = entry_data['ReelPage'][0].get('graphql', {}).get('shortcode_media', {})
                        video_url = reel.get('video_url')
                        if video_url:
                            return await self._download_file(video_url, 'video')
            
            return False, None, "No media found"
            
        except Exception as e:
            logger.error(f"GraphQL download error: {e}")
            return False, None, str(e)
    
    async def _download_with_embed(self, url: str) -> Tuple[bool, str, str]:
        try:
            import re
            import json
            
            session = await self.get_session()
            embed_url = f"https://api.instagram.com/oembed?url={url}"
            
            async with session.get(embed_url, headers=self._get_headers(), timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    thumbnail = data.get('thumbnail_url')
                    if thumbnail:
                        return await self._download_file(thumbnail, 'image')
            
            return False, None, "No embed found"
            
        except Exception as e:
            logger.error(f"Embed download error: {e}")
            return False, None, str(e)
    
    async def _download_with_scraper(self, url: str) -> Tuple[bool, str, str]:
        try:
            import re
            
            session = await self.get_session()
            
            async with session.get(url, headers=self._get_headers(), timeout=30) as response:
                if response.status != 200:
                    return False, None, "Page not found"
                
                html = await response.text()
                
                # استخراج ویدیو
                video_patterns = [
                    r'"video_url":"([^"]+)"',
                    r'"videoUrl":"([^"]+)"',
                    r'src="([^"]+\.mp4)"',
                    r'"playbackUrl":"([^"]+)"',
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, html)
                    for match in matches:
                        video_url = match.replace('\\', '')
                        if video_url.startswith('http'):
                            return await self._download_file(video_url, 'video')
                
                # استخراج تصویر
                image_patterns = [
                    r'"display_url":"([^"]+)"',
                    r'"displayUrl":"([^"]+)"',
                    r'"src":"([^"]+\.(jpg|png|jpeg))"',
                ]
                
                for pattern in image_patterns:
                    matches = re.findall(pattern, html)
                    for match in matches:
                        if isinstance(match, tuple):
                            image_url = match[0]
                        else:
                            image_url = match
                        image_url = image_url.replace('\\', '')
                        if image_url.startswith('http'):
                            return await self._download_file(image_url, 'image')
            
            return False, None, "No media found in scraper"
            
        except Exception as e:
            logger.error(f"Scraper download error: {e}")
            return False, None, str(e)
    
    async def _download_file(self, url: str, media_type: str) -> Tuple[bool, str, str]:
        try:
            import aiohttp
            
            session = await self.get_session()
            extension = '.mp4' if media_type == 'video' else '.jpg'
            filename = f"instagram_{media_type}_{int(time.time())}{extension}"
            filepath = os.path.join(self.temp_dir, filename)
            
            headers = self._get_headers()
            
            async with session.get(url, headers=headers, timeout=60) as response:
                if response.status == 200:
                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    return True, filepath, "Downloaded successfully"
            
            return False, None, "Failed to download file"
            
        except Exception as e:
            logger.error(f"File download error: {e}")
            return False, None, str(e)

download_manager = InstagramDownloader()

# ============================================================
# سیستم تایید پرداخت
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.api_stats = {api: {'requests': 0, 'success': 0, 'errors': 0, 'last_reset': time.time()} for api in self.apis}
        self.lock = threading.RLock()
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=50)
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=500, limit_per_host=100, ttl_dns_cache=300)
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
                params = {"limit": 50, "order_by": "block_timestamp,desc"}
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
# سیستم قرعه‌کشی با الگوریتم هوش مصنوعی پیشرفته
# ============================================================
class LotterySystem:
    def __init__(self):
        self.current_lottery = None
        self.is_running = False
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=20)
        
    def start_lottery(self, lottery_date, prize_per_winner, winners_count):
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
                
            lottery_id = self._save_lottery(lottery_date, prize_per_winner, winners_count, winners)
            
            if not lottery_id:
                return False, "Error saving lottery"
                
            self._save_winners(lottery_id, winners, prize_per_winner)
            
            for winner in winners:
                self._update_winner_stats(winner)
                
            self.current_lottery = {
                'id': lottery_id,
                'date': lottery_date,
                'winners': winners,
                'prize_per_winner': prize_per_winner,
                'winners_count': winners_count,
                'timestamp': datetime.now()
            }
            
            self.is_running = False
            
            return True, {
                'lottery_id': lottery_id,
                'date': lottery_date,
                'winners': winners,
                'prize_per_winner': prize_per_winner,
                'winners_count': winners_count
            }
            
    def _get_eligible_users(self):
        cursor = db.execute_global(
            """SELECT user_id, wallet_address, first_name, username, country 
               FROM users 
               WHERE has_subscription = 1 
               AND subscription_end >= date('now')"""
        )
        return cursor
        
    def _ai_smart_select(self, eligible_users, winners_count):
        if not eligible_users:
            return []
            
        user_scores = []
        for user in eligible_users:
            user_id = user['user_id']
            score = self._calculate_ai_score(user_id)
            if score > 0:
                user_scores.append((user_id, score, user))
                
        if not user_scores:
            selected = random.sample([u['user_id'] for u in eligible_users], min(winners_count, len(eligible_users)))
            return selected
            
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
                """SELECT total_participations, wins_count, last_win_date, created_at, 
                          referral_rewards, has_subscription 
                   FROM users WHERE user_id = ?""",
                (user_id,)
            )
            user_data = cursor.fetchone()
            
            if not user_data:
                return 1
                
            score = 50
            
            if user_data['total_participations'] > 0:
                score += min(user_data['total_participations'] * 3, 30)
                
            if user_data['wins_count'] > 0:
                score -= user_data['wins_count'] * 20
                
            if user_data['last_win_date']:
                try:
                    last_win = datetime.strptime(user_data['last_win_date'], '%Y-%m-%d')
                    days_since_win = (datetime.now() - last_win).days
                    if days_since_win < 7:
                        score *= 0.1
                    elif days_since_win < 14:
                        score *= 0.3
                    elif days_since_win < 30:
                        score *= 0.6
                except:
                    pass
                    
            if user_data['created_at']:
                try:
                    created = datetime.strptime(user_data['created_at'], '%Y-%m-%d %H:%M:%S')
                    days_old = (datetime.now() - created).days
                    if days_old > 90:
                        score += min(days_old / 20, 25)
                    elif days_old > 30:
                        score += min(days_old / 30, 10)
                except:
                    pass
                    
            if user_data['referral_rewards'] > 0:
                score += min(user_data['referral_rewards'] * 2, 15)
                
            if user_data['has_subscription'] == 1:
                score += 10
                
            return max(1, min(100, int(score)))
            
        except Exception as e:
            logger.error(f"Error calculating AI score for {user_id}: {e}")
            return 1
            
    def _save_lottery(self, lottery_date, prize_per_winner, winners_count, winners):
        try:
            total_prize = winners_count * prize_per_winner
            winners_list = ",".join([str(w) for w in winners])
            cursor = db.execute(0,
                """INSERT INTO lotteries 
                   (lottery_date, prize_per_winner, winners_count, total_prize, status, winners_list, created_at) 
                   VALUES (?, ?, ?, ?, 'completed', ?, CURRENT_TIMESTAMP)""",
                (lottery_date, prize_per_winner, winners_count, total_prize, winners_list)
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving lottery: {e}")
            return None
            
    def _save_winners(self, lottery_id, winners, prize_amount):
        try:
            for user_id in winners:
                cursor = db.execute(user_id,
                    "SELECT wallet_address, first_name, country FROM users WHERE user_id = ?",
                    (user_id,)
                )
                user_data = cursor.fetchone()
                wallet_address = user_data['wallet_address'] if user_data else None
                country = user_data['country'] if user_data else 'Unknown'
                
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
            
    def get_lottery_winners(self, lottery_id):
        cursor = db.execute_global(
            """SELECT * FROM winners WHERE lottery_id = ? AND paid_status = 0""",
            (lottery_id,)
        )
        return cursor

lottery_system = LotterySystem()

# ============================================================
# سیستم مدیریت کاربران با پایداری بالا
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
                    UserManager._add_referral_rewards(referred_by, user_id, first_name or username or str(user_id))
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
    def _add_referral_rewards(referrer_id, new_user_id, new_user_name):
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
                (referrer_id, reward_amount, f"REFERRAL_REWARD_{new_user_id}_{int(time.time())}")
            )
            
            db.execute(new_user_id,
                "UPDATE users SET referral_rewards = referral_rewards + ? WHERE user_id = ?",
                (reward_amount, new_user_id)
            )
            db.execute(new_user_id,
                """INSERT INTO transactions 
                   (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
                   VALUES (?, 'referral', 'discount', ?, ?, 'verified', CURRENT_TIMESTAMP)""",
                (new_user_id, reward_amount, f"REFERRAL_DISCOUNT_{referrer_id}_{int(time.time())}")
            )
            
            logger.info(f"Referral rewards added: {reward_amount} for user {referrer_id} and {new_user_id}")
            
        except Exception as e:
            logger.error(f"Error adding referral rewards: {e}")
            
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
            results = db.execute_global("SELECT user_id, username, first_name, referral_rewards, has_subscription FROM users")
            return results
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
            
    @staticmethod
    def get_subscribed_users():
        try:
            results = db.execute_global(
                """SELECT user_id, username, first_name, wallet_address, subscription_end, country 
                   FROM users 
                   WHERE has_subscription = 1 
                   AND subscription_end >= date('now')"""
            )
            return results
        except Exception as e:
            logger.error(f"Error getting subscribed users: {e}")
            return []

user_manager = UserManager()

# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.pending_verifications = {}
        self.executor = ThreadPoolExecutor(max_workers=200)
        self.process_pool = ProcessPoolExecutor(max_workers=50)
        self._setup_handlers()
        self._init_system()
        self._init_robot_system()
        
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
            
    def _init_robot_system(self):
        try:
            os.makedirs("robot_files", exist_ok=True)
            logger.info("✅ Robot system initialized")
        except Exception as e:
            logger.error(f"Error initializing robot system: {e}")
            
    def _setup_handlers(self):
        app = self.application
        
        # دستورات
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("referral", self.referral_command))
        app.add_handler(CommandHandler("language", self.language_command))
        
        # منوی اصلی
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language$"))
        
        # دانلودر و فاکتور ساز
        app.add_handler(CallbackQueryHandler(self.instagram_download_callback, pattern="^instagram_download$"))
        app.add_handler(CallbackQueryHandler(self.invoice_maker_callback, pattern="^invoice_maker$"))
        app.add_handler(CallbackQueryHandler(self.invoice_confirm_callback, pattern="^invoice_confirm$"))
        
        # اشتراک و قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.subscribe_callback, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.confirm_subscribe_callback, pattern="^confirm_subscribe$"))
        app.add_handler(CallbackQueryHandler(self.join_lottery_callback, pattern="^join_lottery$"))
        app.add_handler(CallbackQueryHandler(self.confirm_payment_callback, pattern="^confirm_payment$"))
        
        # ساخت ربات
        app.add_handler(CallbackQueryHandler(self.build_robot_callback, pattern="^build_robot$"))
        app.add_handler(CallbackQueryHandler(self.my_robots_callback, pattern="^my_robots$"))
        app.add_handler(CallbackQueryHandler(self.robot_delete_callback, pattern="^robot_delete_"))
        app.add_handler(CallbackQueryHandler(self.robot_confirm_delete_callback, pattern="^robot_confirm_delete_"))
        app.add_handler(CallbackQueryHandler(self.robot_cancel_delete_callback, pattern="^robot_cancel_delete$"))
        app.add_handler(CallbackQueryHandler(self.robot_select_callback, pattern="^robot_select_"))
        
        # پنل مدیریت
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
        
        # دکمه‌های جدید مدیریت
        app.add_handler(CallbackQueryHandler(self.admin_upload_file_callback, pattern="^admin_upload_file$"))
        app.add_handler(CallbackQueryHandler(self.admin_add_server_callback, pattern="^admin_add_server$"))
        app.add_handler(CallbackQueryHandler(self.admin_manage_servers_callback, pattern="^admin_manage_servers$"))
        app.add_handler(CallbackQueryHandler(self.admin_server_delete_callback, pattern="^admin_server_delete_"))
        app.add_handler(CallbackQueryHandler(self.file_lang_callback, pattern="^file_lang_"))
        
        # نظرسنجی
        app.add_handler(CallbackQueryHandler(self.poll_response_callback, pattern="^poll_yes$"))
        app.add_handler(CallbackQueryHandler(self.poll_response_callback, pattern="^poll_no$"))
        
        # تایید تراکنش
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))
        
        # تایید قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.start_lottery_confirm_callback, pattern="^start_lottery_confirm$"))
        app.add_handler(CallbackQueryHandler(self.pay_winners_confirm_callback, pattern="^pay_winners_confirm$"))
        
        # برداشت جایزه
        app.add_handler(CallbackQueryHandler(self.withdraw_prize_callback, pattern="^withdraw_prize$"))
        app.add_handler(CallbackQueryHandler(self.confirm_withdraw_callback, pattern="^confirm_withdraw$"))
        
        # تغییر زبان
        app.add_handler(CallbackQueryHandler(self.set_language_callback, pattern="^set_lang_"))
        
        # پیام‌ها
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        
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
    
    def _validate_bot_token(self, token):
        if not token:
            return False
        parts = token.split(':')
        if len(parts) != 2:
            return False
        if not parts[0].isdigit():
            return False
        return len(parts[1]) >= 32
    
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
        
        cursor = db.execute(0, "SELECT created_at FROM lotteries ORDER BY created_at DESC LIMIT 1")
        last = cursor.fetchone()
        
        return {
            'total': total,
            'total_winners': total_winners,
            'last': last['created_at'] if last else None
        }
    
    async def _get_winner_amount(self, user_id):
        cursor = db.execute(user_id,
            "SELECT prize_amount FROM winners WHERE user_id = ? AND paid_status = 0",
            (user_id,)
        )
        result = cursor.fetchone()
        return result['prize_amount'] if result else 0

    # ============================================================
    # منوی اصلی
    # ============================================================
    def _get_main_keyboard(self, user_id, lang):
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
                LanguageManager.get_text(lang, 'build_robot'),
                callback_data="build_robot"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'my_robots'),
                callback_data="my_robots"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'instagram_download'),
                callback_data="instagram_download"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'invoice_maker'),
                callback_data="invoice_maker"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'guide'),
                callback_data="guide"
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
        
        return keyboard

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        referred_by = None
        if context.args and context.args[0].startswith('ref_'):
            ref_code = context.args[0].replace('ref_', '')
            cursor = db.execute_global(
                "SELECT user_id FROM users WHERE referral_code = ?",
                (ref_code,)
            )
            if cursor:
                for row in cursor:
                    if row['user_id'] != user.id:
                        referred_by = row['user_id']
                        break
        
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
                        str(user.id)
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'referral_discount',
                        user.first_name or user.username or str(user.id),
                        str(referred_by)
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error sending referral notification: {e}")
        
        keyboard = self._get_main_keyboard(user.id, lang)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'welcome') + "\n\n" + LanguageManager.get_text(lang, 'main_menu'),
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

    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = self._get_main_keyboard(user_id, lang)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'main_menu'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های قرعه‌کشی و رفرال
    # ============================================================
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

    # ============================================================
    # کالبک‌های زبان
    # ============================================================
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
                f"✅ Language changed to {LanguageManager.get_language_name(lang_code)}!",
                reply_markup=reply_markup
            )

    async def _show_referral(self, update, user_id):
        user = user_manager.get_user(user_id)
        if not user:
            return
        
        lang = self._get_user_language(user_id)
        referral_code = user['referral_code']
        bot = await self.application.bot.get_me()
        referral_link = f"https://t.me/{bot.username}?start=ref_{referral_code}"
        
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
    # دانلودر اینستاگرام
    # ============================================================
    async def instagram_download_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        context.user_data['download_mode'] = 'instagram'
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'instagram_downloader'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _download_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, media_type: str):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'processing'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            if media_type == 'instagram':
                success, file_path, message = await download_manager.download_instagram(url)
            else:
                success, file_path, message = False, None, "Unknown media type"
            
            if success and file_path and os.path.exists(file_path):
                # تعیین نوع فایل
                is_video = file_path.endswith('.mp4') or file_path.endswith('.mkv') or file_path.endswith('.webm')
                
                with open(file_path, 'rb') as f:
                    if is_video:
                        await update.message.reply_video(
                            video=f,
                            caption=LanguageManager.get_text(lang, 'download_success'),
                            supports_streaming=True
                        )
                    else:
                        await update.message.reply_photo(
                            photo=f,
                            caption=LanguageManager.get_text(lang, 'download_success')
                        )
                
                try:
                    os.remove(file_path)
                except:
                    pass
                
                db.execute(user_id,
                    """INSERT INTO downloads 
                       (user_id, url, media_type, file_path, status) 
                       VALUES (?, ?, ?, ?, 'completed')""",
                    (user_id, url, media_type, file_path)
                )
            else:
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'download_failed', message or "محتوا یافت نشد")
                )
                
                db.execute(user_id,
                    """INSERT INTO downloads 
                       (user_id, url, media_type, status) 
                       VALUES (?, ?, ?, 'failed')""",
                    (user_id, url, media_type)
                )
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'download_failed', str(e))
            )

    # ============================================================
    # فاکتور ساز با تایید قبل از باز شدن
    # ============================================================
    async def invoice_maker_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'open_invoice_confirm'),
                callback_data="invoice_confirm"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'invoice_confirm'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def invoice_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        # ارسال لینک با WebApp که وقتی کاربر برگشت، در ربات بماند
        keyboard = [
            [InlineKeyboardButton(
                "🧾 باز کردن فاکتور ساز",
                web_app=WebAppInfo(url="https://mbuiop.github.io/Tablikgram/")
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'close'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🧾 **فاکتور ساز**\n\n"
            "روی دکمه زیر کلیک کنید تا فاکتور ساز باز شود.\n\n"
            "📌 پس از اتمام، روی **بستن** کلیک کنید تا به منوی اصلی برگردید.\n\n"
            "⚠️ **نکته:** با زدن دکمه بازگشت گوشی، از صفحه سایت خارج نمی‌شوید و به ربات برمی‌گردید.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # ساخت ربات - کالبک‌ها
    # ============================================================
    async def build_robot_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        cursor = db.execute_global(
            "SELECT * FROM uploaded_bot_files ORDER BY created_at DESC"
        )
        uploaded_files = cursor
        
        if not uploaded_files:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_uploaded_files'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        keyboard = []
        for file in uploaded_files[:10]:
            lang_name = {'en': '🇬🇧 English', 'fa': '🇮🇷 فارسی', 'tr': '🇹🇷 Türkçe'}.get(file['language'], file['language'])
            keyboard.append([InlineKeyboardButton(
                f"📄 {file['file_name']} - {lang_name}",
                callback_data=f"robot_select_{file['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="main_menu"
        )])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'select_file'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def robot_select_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        file_id = int(query.data.replace('robot_select_', ''))
        cursor = db.execute_global(
            "SELECT * FROM uploaded_bot_files WHERE id = ?",
            (file_id,)
        )
        file_info = cursor[0] if cursor else None
        
        if not file_info:
            await query.edit_message_text("❌ فایل یافت نشد!")
            return
        
        context.user_data['selected_robot_file'] = file_id
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'cancel'),
            callback_data="main_menu"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'build_robot_title') + "\n\n" +
            LanguageManager.get_text(lang, 'build_robot_help') + "\n\n" +
            f"📄 فایل انتخاب شده: {file_info['file_name']}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['waiting_for_robot_token'] = True

    async def my_robots_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        cursor = db.execute(user_id,
            "SELECT * FROM user_robots WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        robots = cursor.fetchall()
        
        if not robots:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'build_new_robot'),
                    callback_data="build_robot"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'back'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_robots'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = LanguageManager.get_text(lang, 'my_robots_title', len(robots)) + "\n\n"
        
        for robot in robots:
            status_emoji = "🟢" if robot['status'] == 'active' else "🔴"
            text += f"{status_emoji} 🤖 ربات #{robot['id']}\n"
            text += f"   🔹 توکن: `{robot['bot_token'][:15]}...`\n"
            text += f"   🔹 زبان: {robot['language']}\n"
            text += f"   🔹 وضعیت: {robot['status']}\n"
            text += f"   🔹 ساخته شده: {robot['created_at'][:10]}\n\n"
        
        keyboard = []
        for robot in robots:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {LanguageManager.get_text(lang, 'delete_robot')} #{robot['id']}",
                callback_data=f"robot_delete_{robot['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            LanguageManager.get_text(lang, 'build_new_robot'),
            callback_data="build_robot"
        )])
        keyboard.append([InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="main_menu"
        )])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def robot_delete_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        robot_id = int(query.data.replace('robot_delete_', ''))
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ بله", callback_data=f"robot_confirm_delete_{robot_id}"),
                InlineKeyboardButton("❌ نه", callback_data="robot_cancel_delete")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'robot_delete_confirm', robot_id),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def robot_confirm_delete_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        robot_id = int(query.data.replace('robot_confirm_delete_', ''))
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        db.execute(user_id,
            "DELETE FROM user_robots WHERE id = ? AND user_id = ?",
            (robot_id, user_id)
        )
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'robot_deleted'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await self.my_robots_callback(update, context)

    async def robot_cancel_delete_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await self.my_robots_callback(update, context)

    # ============================================================
    # کالبک‌های اشتراک و قرعه‌کشی
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
        subscribed_count = len(user_manager.get_subscribed_users())
        
        cursor = db.execute_global("SELECT COUNT(*) as count FROM user_robots")
        total_robots = 0
        for row in cursor:
            total_robots += row['count']
        
        cursor = db.execute_global("SELECT COUNT(*) as count FROM uploaded_bot_files")
        total_files = 0
        for row in cursor:
            total_files += row['count']
        
        cursor = db.execute_global("SELECT COUNT(*) as count FROM servers WHERE status = 'active'")
        total_servers = 0
        for row in cursor:
            total_servers += row['count']
        
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton(f"✅ تایید دستی ({pending_count})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📊 ارسال نظرسنجی", callback_data="admin_poll")],
            [InlineKeyboardButton(f"💰 واریز به برندگان ({unpaid_winners})", callback_data="admin_pay_winners")],
            [InlineKeyboardButton(f"👥 کاربران اشتراکی ({subscribed_count})", callback_data="admin_subscribed_users")],
            [InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_user_list")],
            [InlineKeyboardButton("🔑 اضافه کردن API", callback_data="admin_add_api")],
            [InlineKeyboardButton("📈 آمار و اطلاعات", callback_data="admin_stats")],
            [InlineKeyboardButton(f"📤 آپلود فایل ربات ({total_files})", callback_data="admin_upload_file")],
            [InlineKeyboardButton(f"🌐 مدیریت سرورها ({total_servers})", callback_data="admin_manage_servers")],
            [InlineKeyboardButton("➕ افزودن سرور جدید", callback_data="admin_add_server")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"⚙️ **پنل مدیریت**\n\n"
            f"📊 **آمار:**\n"
            f"👥 کل کاربران: {user_count:,}\n"
            f"✅ اشتراک فعال: {active_users:,}\n"
            f"🤖 ربات‌های ساخته شده: {total_robots:,}\n"
            f"📄 فایل‌های آپلودی: {total_files}\n"
            f"🖥️ سرورهای فعال: {total_servers}\n"
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

    # ============================================================
    # آپلود فایل ربات
    # ============================================================
    async def admin_upload_file_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['admin_action'] = 'upload_robot_file'
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📤 **آپلود فایل ربات**\n\n"
            "لطفاً فایل کد ربات را ارسال کنید:\n\n"
            "📌 **نکات:**\n"
            "• فایل باید به صورت TEXT یا فایل .py باشد\n"
            "• از `{BOT_TOKEN}` برای توکن استفاده کنید\n"
            "• از `{ADMIN_ID}` برای ادمین استفاده کنید\n\n"
            "🌐 **زبان فایل را مشخص کنید:**\n"
            "پس از ارسال فایل، زبان را انتخاب کنید.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['waiting_for_robot_file'] = True

    async def file_lang_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        lang_code = query.data.replace('file_lang_', '')
        file_content = context.user_data.get('pending_file_content')
        file_name = context.user_data.get('pending_file_name')
        
        if not file_content or not file_name:
            await query.edit_message_text("❌ خطا! فایل یافت نشد.")
            return
        
        # ذخیره فایل
        file_hash = hashlib.sha256(file_content.encode()).hexdigest()
        file_path = os.path.join("robot_files", f"{file_hash}_{file_name}")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        db.execute(user_id,
            """INSERT INTO uploaded_bot_files 
               (file_name, file_path, language, file_hash, uploaded_by) 
               VALUES (?, ?, ?, ?, ?)""",
            (file_name, file_path, lang_code, file_hash, user_id)
        )
        
        context.user_data['waiting_for_file_lang'] = False
        context.user_data['pending_file_content'] = None
        context.user_data['pending_file_name'] = None
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **فایل با موفقیت آپلود شد!**\n\n"
            f"📁 نام: {file_name}\n"
            f"🌐 زبان: {lang_code}\n"
            f"🔑 هش: `{file_hash[:20]}...`\n\n"
            f"📌 کاربران می‌توانند از این فایل برای ساخت ربات استفاده کنند.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # مدیریت سرورها
    # ============================================================
    async def admin_manage_servers_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        cursor = db.execute_global(
            "SELECT * FROM servers ORDER BY created_at DESC"
        )
        servers = cursor
        
        text = "🌐 **مدیریت سرورها**\n\n"
        
        if not servers:
            text += "❌ هیچ سروری ثبت نشده است.\n"
        else:
            for server in servers:
                status_emoji = "🟢" if server['status'] == 'active' else "🔴"
                text += f"{status_emoji} **{server['name']}**\n"
                text += f"   📍 IP: {server['ip']}:{server['port']}\n"
                text += f"   📦 کارگرها: {server['current_workers']}/{server['max_workers']}\n"
                text += f"   🗂️ شاردها: {server['shards']}\n"
                text += f"   📅 ایجاد: {server['created_at'][:10]}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن سرور جدید", callback_data="admin_add_server")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        
        for server in servers:
            keyboard.insert(0, [InlineKeyboardButton(
                f"🗑️ حذف سرور {server['ip']}",
                callback_data=f"admin_server_delete_{server['id']}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_add_server_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['add_server_step'] = 1
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_manage_servers")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🌐 **افزودن سرور جدید**\n\n"
            "مرحله ۱: لطفاً IP سرور را وارد کنید:\n\n"
            "مثال: `192.168.1.100`",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def admin_server_delete_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        server_id = int(query.data.replace('admin_server_delete_', ''))
        
        db.execute(0,
            "DELETE FROM servers WHERE id = ?",
            (server_id,)
        )
        
        await query.edit_message_text("✅ سرور با موفقیت حذف شد!")
        await self.admin_manage_servers_callback(update, context)

    # ============================================================
    # سایر توابع مدیریت
    # ============================================================
    async def admin_subscribed_users_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        subscribed_users = user_manager.get_subscribed_users()
        
        if not subscribed_users:
            text = LanguageManager.get_text('fa', 'no_subscribed_users')
        else:
            users_text = ""
            for user in subscribed_users[:50]:
                users_text += f"👤 {user['user_id']} - {user['first_name'] or user['username'] or 'Unknown'}\n"
                users_text += f"📤 {user['wallet_address'] or 'Not set'}\n"
                users_text += f"📅 {user['subscription_end']}\n"
                users_text += f"🌍 {user['country'] or 'Unknown'}\n\n"
            
            if len(subscribed_users) > 50:
                users_text += f"... و {len(subscribed_users) - 50} نفر دیگر"
            
            text = LanguageManager.get_text('fa', 'subscribed_users_list', len(subscribed_users), users_text)
        
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
                text += f"   💰 پاداش رفرال: ${user['referral_rewards']:.2f}\n"
                text += f"   ✅ اشتراک: {'فعال' if user['has_subscription'] else 'غیرفعال'}\n\n"
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
        
        msg = query.message.text
        try:
            lines = msg.split('\n')
            for line in lines:
                if 'کاربر' in line or 'User' in line or 'user' in line:
                    parts = line.split('-')
                    if len(parts) >= 2:
                        target_id = int(parts[0].strip())
                        db.execute(target_id,
                            "UPDATE users SET has_subscription = 0, subscription_end = NULL WHERE user_id = ?",
                            (target_id,)
                        )
                        await query.edit_message_text(
                            f"✅ کاربر {target_id} با موفقیت بازنشانی شد!",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]])
                        )
                        return
        except:
            pass
        
        await query.edit_message_text(
            "❌ خطا در بازنشانی کاربر! لطفاً از لیست کاربران استفاده کنید.",
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
        
        keyboard = [
            [InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text('fa', 'enter_lottery_date'),
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
            
            user_lang = self._get_user_language(winner['user_id'])
            user = user_manager.get_user(winner['user_id'])
            user_name = user['first_name'] or user['username'] or str(winner['user_id'])
            
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(user_lang, 'main_menu_btn'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await self.application.bot.send_message(
                    chat_id=winner['user_id'],
                    text=LanguageManager.get_text(user_lang, 'lottery_winner_announcement',
                        user_name,
                        winner['prize_amount'],
                        winner['wallet_address'] or 'Unknown',
                        user['country'] if user else 'Unknown'
                    ),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error sending to winner {winner['user_id']}: {e}")
        
        users = db.execute_global("SELECT user_id, language FROM users")
        
        winners_list = ""
        for winner in winners:
            user = user_manager.get_user(winner['user_id'])
            user_name = user['first_name'] or user['username'] or str(winner['user_id'])
            winners_list += f"• {user_name} - ${winner['prize_amount']}\n"
        
        for user in users:
            try:
                user_lang = user['language'] if user['language'] else 'en'
                await self.application.bot.send_message(
                    chat_id=user['user_id'],
                    text=LanguageManager.get_text(user_lang, 'lottery_winner_admin',
                        datetime.now().strftime('%Y-%m-%d'),
                        sum(w['prize_amount'] for w in winners),
                        winners_list
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Error sending to user {user['user_id']}: {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text('fa', 'pay_winners_success', len(winners), sum(w['prize_amount'] for w in winners)),
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
        
        cursor = db.execute_global("SELECT COUNT(*) as count FROM user_robots")
        total_robots = 0
        for row in cursor:
            total_robots += row['count']
        
        cursor = db.execute_global("SELECT COUNT(*) as count FROM uploaded_bot_files")
        total_files = 0
        for row in cursor:
            total_files += row['count']
        
        cursor = db.execute_global("SELECT COUNT(*) as count FROM servers")
        total_servers = 0
        for row in cursor:
            total_servers += row['count']
        
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
            f"🤖 **ربات‌ها:**\n"
            f"• ساخته شده: {total_robots:,}\n"
            f"• فایل‌های آپلودی: {total_files}\n\n"
            f"🖥️ **سرورها:**\n"
            f"• کل: {total_servers}\n\n"
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
            f"• رشته‌های اجرایی: ۲۰۰\n\n"
            f"👥 **لیست کاربران:**\n{users_text}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # شروع قرعه‌کشی و برداشت جایزه
    # ============================================================
    async def start_lottery_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        
        lottery_date = context.user_data.get('lottery_date')
        prize_per_winner = context.user_data.get('lottery_prize')
        winners_count = context.user_data.get('lottery_winners')
        
        if not all([lottery_date, prize_per_winner, winners_count]):
            await query.edit_message_text("❌ اطلاعات قرعه‌کشی کامل نیست! لطفاً دوباره تلاش کنید.")
            return
        
        success, result = lottery_system.start_lottery(lottery_date, prize_per_winner, winners_count)
        
        if success:
            users = db.execute_global("SELECT user_id, language FROM users")
            
            for user in users:
                try:
                    user_lang = user['language'] if user['language'] else 'en'
                    
                    keyboard = [
                        [InlineKeyboardButton(
                            LanguageManager.get_text(user_lang, 'lottery'),
                            callback_data="join_lottery"
                        )],
                        [InlineKeyboardButton(
                            LanguageManager.get_text(user_lang, 'subscribe'),
                            callback_data="subscribe"
                        )]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=LanguageManager.get_text(user_lang, 'lottery_announcement',
                            lottery_date,
                            prize_per_winner,
                            winners_count,
                            DESTINATION_WALLET
                        ),
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Error sending to user {user['user_id']}: {e}")
            
            winners_list = ""
            for winner_id in result['winners']:
                user = user_manager.get_user(winner_id)
                user_name = user['first_name'] or user['username'] or str(winner_id)
                wallet = user['wallet_address'] if user else 'No wallet'
                winners_list += f"• {user_name} - {wallet}\n"
            
            keyboard = [
                [InlineKeyboardButton("💰 پرداخت به برندگان", callback_data="admin_pay_winners")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text('fa', 'lottery_winner_admin',
                    lottery_date,
                    winners_count * prize_per_winner,
                    winners_list
                ),
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
                f"❌ **خطا در اجرای قرعه‌کشی**\n\n🔹 دلیل: {result}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

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
    # مدیریت پیام‌ها
    # ============================================================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        lang = self._get_user_language(user_id)
        
        # دانلودر اینستاگرام
        download_mode = context.user_data.get('download_mode')
        if download_mode in ['instagram']:
            if text.startswith('http://') or text.startswith('https://'):
                if download_mode == 'instagram':
                    if not download_manager.validate_instagram_url(text):
                        await update.message.reply_text(
                            LanguageManager.get_text(lang, 'invalid_url'),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        return
                
                await self._download_media(update, context, text, download_mode)
                context.user_data['download_mode'] = None
                return
            else:
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'invalid_url'),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # دریافت توکن ربات
        if context.user_data.get('waiting_for_robot_token'):
            token = text.strip()
            
            if not self._validate_bot_token(token):
                await update.message.reply_text(
                    "❌ توکن نامعتبر!\n\n"
                    "لطفاً یک توکن معتبر از @BotFather ارسال کنید.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            file_id = context.user_data.get('selected_robot_file')
            if not file_id:
                await update.message.reply_text("❌ فایل ربات انتخاب نشده است!")
                return
            
            cursor = db.execute_global(
                "SELECT * FROM uploaded_bot_files WHERE id = ?",
                (file_id,)
            )
            file_info = cursor[0] if cursor else None
            
            if not file_info:
                await update.message.reply_text("❌ فایل ربات یافت نشد!")
                return
            
            # خواندن فایل
            file_content = None
            if os.path.exists(file_info['file_path']):
                with open(file_info['file_path'], 'r', encoding='utf-8') as f:
                    file_content = f.read()
            
            if not file_content:
                await update.message.reply_text("❌ خطا در خواندن فایل ربات!")
                return
            
            # جایگزینی توکن و ادمین
            file_content = file_content.replace('{BOT_TOKEN}', token)
            file_content = file_content.replace('{ADMIN_ID}', str(user_id))
            
            # ذخیره در دیتابیس
            file_hash = hashlib.sha256(file_content.encode()).hexdigest()
            
            db.execute(user_id,
                """INSERT INTO user_robots 
                   (user_id, bot_token, admin_id, language, status, file_hash) 
                   VALUES (?, ?, ?, ?, 'active', ?)""",
                (user_id, token, user_id, file_info['language'], file_hash)
            )
            
            context.user_data['waiting_for_robot_token'] = False
            context.user_data['selected_robot_file'] = None
            
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'my_robots'),
                    callback_data="my_robots"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'back'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'build_robot_success',
                    "جدید",
                    user_id,
                    file_info['language']
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # مدیریت اقدامات ادمین
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
        
        # مدیریت افزودن سرور
        step = context.user_data.get('add_server_step', 0)
        if step == 1:
            ip = text.strip()
            context.user_data['server_ip'] = ip
            context.user_data['add_server_step'] = 2
            await update.message.reply_text(
                f"✅ IP ذخیره شد: `{ip}`\n\n"
                "مرحله ۲: لطفاً نام کاربری سرور را وارد کنید:\n\n"
                "مثال: `root`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        elif step == 2:
            username = text.strip()
            context.user_data['server_username'] = username
            context.user_data['add_server_step'] = 3
            await update.message.reply_text(
                f"✅ نام کاربری ذخیره شد: `{username}`\n\n"
                "مرحله ۳: لطفاً رمز عبور سرور را وارد کنید:",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        elif step == 3:
            password = text.strip()
            context.user_data['server_password'] = password
            context.user_data['add_server_step'] = 4
            await update.message.reply_text(
                "✅ رمز عبور ذخیره شد!\n\n"
                "مرحله ۴: لطفاً تعداد شاردها را وارد کنید:\n\n"
                "مثال: `100`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        elif step == 4:
            try:
                shards = int(text.strip())
                if shards < 10:
                    await update.message.reply_text("❌ تعداد شاردها باید حداقل ۱۰ باشد!")
                    return
                
                ip = context.user_data.get('server_ip')
                username = context.user_data.get('server_username')
                password = context.user_data.get('server_password')
                
                if not all([ip, username, password]):
                    await update.message.reply_text("❌ اطلاعات ناقص است! لطفاً دوباره تلاش کنید.")
                    return
                
                db.execute(0,
                    """INSERT INTO servers 
                       (name, ip, port, username, password, status, max_workers, shards) 
                       VALUES (?, ?, ?, ?, ?, 'active', 100, ?)""",
                    (f"Server_{ip}", ip, 22, username, password, shards)
                )
                
                context.user_data['add_server_step'] = 0
                context.user_data['server_ip'] = None
                context.user_data['server_username'] = None
                context.user_data['server_password'] = None
                
                keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_manage_servers")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **سرور با موفقیت اضافه شد!**\n\n"
                    f"📍 IP: {ip}\n"
                    f"👤 کاربر: {username}\n"
                    f"📦 شاردها: {shards}\n\n"
                    f"🔄 سیستم به‌طور خودکار از این سرور استفاده خواهد کرد.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            except ValueError:
                await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
                return
        
        # مدیریت هش تراکنش
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
        
        # مدیریت اشتراک
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
        
        # مدیریت کیف پول برای قرعه‌کشی
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
        
        # مدیریت برداشت جایزه
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
        
        # دستور نامعتبر
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
        
        if step == 1:
            try:
                lottery_date = text.strip()
                context.user_data['lottery_date'] = lottery_date
                context.user_data['lottery_step'] = 2
                
                keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    LanguageManager.get_text('fa', 'enter_lottery_prize'),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                await update.message.reply_text("❌ فرمت تاریخ نامعتبر! لطفاً دوباره وارد کنید.")
                
        elif step == 2:
            try:
                prize = float(text)
                if prize < 10:
                    await update.message.reply_text("❌ مبلغ جایزه باید حداقل ۱۰ دلار باشد!")
                    return
                    
                context.user_data['lottery_prize'] = prize
                context.user_data['lottery_step'] = 3
                
                keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    LanguageManager.get_text('fa', 'enter_lottery_winners'),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except ValueError:
                await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
                
        elif step == 3:
            try:
                winners_count = int(text)
                if winners_count < 1 or winners_count > 100:
                    await update.message.reply_text("❌ تعداد برندگان باید بین ۱ تا ۱۰۰ باشد!")
                    return
                    
                context.user_data['lottery_winners'] = winners_count
                context.user_data['lottery_step'] = 4
                
                lottery_date = context.user_data.get('lottery_date')
                prize = context.user_data.get('lottery_prize')
                
                keyboard = [
                    [InlineKeyboardButton("✅ تایید و شروع", callback_data="start_lottery_confirm")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    LanguageManager.get_text('fa', 'lottery_confirm', lottery_date, prize, winners_count),
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
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

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if context.user_data.get('waiting_for_robot_file'):
            document = update.message.document
            
            if document.mime_type not in ['text/plain', 'application/x-python-code'] and not document.file_name.endswith('.py'):
                await update.message.reply_text(
                    "❌ لطفاً یک فایل متنی (.py یا .txt) آپلود کنید!"
                )
                return
            
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()
            text = file_content.decode('utf-8')
            
            context.user_data['pending_file_content'] = text
            context.user_data['pending_file_name'] = document.file_name
            
            keyboard = [
                [InlineKeyboardButton("🇬🇧 English", callback_data="file_lang_en")],
                [InlineKeyboardButton("🇮🇷 فارسی", callback_data="file_lang_fa")],
                [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="file_lang_tr")],
                [InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📄 **فایل دریافت شد!**\n\n"
                f"📁 نام: {document.file_name}\n"
                f"📦 حجم: {document.file_size:,} bytes\n\n"
                "🌐 **زبان فایل را انتخاب کنید:**",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            context.user_data['waiting_for_file_lang'] = True
            return

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
def main():
    try:
        bot = UTYOBot()
        
        logger.info("🚀 UTYOB Bot starting...")
        logger.info(f"👥 Admins: {len(ADMIN_IDS)}")
        logger.info(f"🗄️ Shards: {DB_SHARDS}")
        logger.info(f"🔑 APIs: {len(TRONGRID_APIS)}")
        logger.info(f"⚡ Threads: 200")
        logger.info(f"💾 Cache size: 50,000 items")
        logger.info(f"📥 Download Manager: Ready")
        logger.info(f"🤖 Robot System: Ready")
        logger.info("⚡ Polling with callback_query and message updates")

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