# ============================================================
# ربات قرعه‌کشی هوشمند UTYOB - نسخه نهایی با سیستم آگهی‌های شغلی
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
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template_string

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
BOT_USERNAME = "UTYOB_Bot"

TRONGRID_APIS = ["7ae83b63-fdf3-47e4-ac69-56f960a34f5b"]
DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
PAYMENT_AMOUNT = 100

DB_SHARDS = 500
CACHE_TTL = 300

# ============================================================
# Flask App برای سایت و API
# ============================================================
flask_app = Flask(__name__)

# ============================================================
# سیستم چندزبانه کامل
# ============================================================
class LanguageManager:
    LANGUAGES = {
        'en': {
            'name': 'English', 'emoji': '🇬🇧',
            'welcome': "🎮 **Welcome to UTYOB Lottery Bot!**\n\n💰 Win amazing prizes up to $10,000!\n🎯 Fair and transparent lottery system\n🌟 Join now and test your luck!",
            'main_menu': "🎯 **UTYOB Lottery Bot**\n\nSelect an option below:\n👇👇👇",
            'lottery': "🎰 Join Lottery",
            'referral': "🔗 Referral",
            'guide': "📖 Guide",
            'language': "🌐 Change Language",
            'admin_panel': "⚙️ Admin Panel",
            'instagram_download': "📸 Instagram Downloader",
            'invoice_maker': "🧾 Invoice Maker",
            'jobs': "💼 Job Board",
            'add_job': "➕ Add Job",
            'view_jobs': "📋 View Jobs",
            'my_jobs': "📊 My Jobs",
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
            'download_failed': "❌ **Download failed!**\n\n🔹 Reason: {}\n\n📌 Make sure the link is correct and the video is available.",
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
            'job_added': "✅ **Job posted successfully!** 🎉\n\n📋 Title: {}\n🏢 Company: {}\n📍 City: {}\n\n🌐 View on website: https://mbuiop.github.io/Tablikgram/",
            'job_title': "📝 **Enter job title:**\nExample: Senior Python Developer",
            'job_company': "🏢 **Enter company name:**\nExample: Parsian Tech",
            'job_city': "📍 **Enter city:**\nExample: Tehran",
            'job_description': "📝 **Enter job description:**\nExample: Django, React, Docker\nMinimum 3 years experience",
            'job_phone': "📞 **Enter phone number (optional):**\nType 'skip' to skip",
            'job_list_empty': "📋 No jobs found.\n\n💼 Be the first to post a job!",
            'job_list_title': "📋 **Job Listings**\n\n",
            'job_item': "💼 **{title}**\n🏢 {company}\n📍 {city}\n📝 {description}\n👤 {name}\n📅 {date}\n",
            'contact_job': "💬 Contact Employer",
            'job_contact_message': "📩 **Message to {name}**\n\n📋 Job: {title}\n\n✏️ Write your message below:",
            'job_message_sent': "✅ **Message sent!**\n\n📩 Your message has been sent to {name}.\n⏳ They will reply soon.",
            'job_message_received': "📩 **New message about your job!**\n\n📋 Job: {title}\n👤 From: {name}\n📝 Message:\n{message}\n\n💬 Reply in chat to respond.",
            'my_jobs_title': "📊 **My Job Listings**\n\n",
            'my_jobs_empty': "📊 You haven't posted any jobs yet.",
            'delete_job': "🗑️ Delete",
            'job_deleted': "✅ Job deleted successfully!",
            'view_on_web': "🌐 View on Website",
            'chat_with_employer': "💬 Chat with Employer",
        },
        'fa': {
            'name': 'فارسی', 'emoji': '🇮🇷',
            'welcome': "🎮 **به ربات قرعه‌کشی UTYOB خوش آمدید!**\n\n💰 برنده جوایز شگفت‌انگیز تا ۱۰۰۰۰ دلار شوید!\n🎯 سیستم قرعه‌کشی عادلانه و شفاف\n🌟 همین حالا بپیوندید و شانس خود را امتحان کنید!",
            'main_menu': "🎯 **ربات قرعه‌کشی UTYOB**\n\nیکی از گزینه‌های زیر را انتخاب کنید:\n👇👇👇",
            'lottery': "🎰 شرکت در قرعه‌کشی",
            'referral': "🔗 رفرال",
            'guide': "📖 راهنمایی",
            'language': "🌐 تغییر زبان",
            'admin_panel': "⚙️ پنل مدیریت",
            'instagram_download': "📸 دانلودر اینستاگرام",
            'invoice_maker': "🧾 فاکتور ساز",
            'jobs': "💼 آگهی‌های شغلی",
            'add_job': "➕ ثبت آگهی",
            'view_jobs': "📋 مشاهده آگهی‌ها",
            'my_jobs': "📊 آگهی‌های من",
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
            'download_failed': "❌ **دانلود ناموفق!**\n\n🔹 دلیل: {}\n\n📌 مطمئن شوید لینک صحیح است و ویدیو در دسترس است.",
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
            'job_added': "✅ **آگهی شما با موفقیت ثبت شد!** 🎉\n\n📋 {}\n🏢 {}\n📍 {}\n\n🌐 مشاهده در سایت: https://mbuiop.github.io/Tablikgram/",
            'job_title': "📝 **عنوان شغل را وارد کنید:**\nمثال: برنامه‌نویس ارشد پایتون",
            'job_company': "🏢 **نام شرکت را وارد کنید:**\nمثال: شرکت دانش‌بنیان پارس",
            'job_city': "📍 **شهر را وارد کنید:**\nمثال: تهران",
            'job_description': "📝 **توضیحات شغل را وارد کنید:**\nمثال: Django، React، Docker\nحداقل ۳ سال سابقه",
            'job_phone': "📞 **شماره تماس (اختیاری):**\nبرای رد کردن 'skip' را بزنید",
            'job_list_empty': "📋 هیچ آگهی شغلی وجود ندارد.\n\n💼 اولین آگهی را ثبت کنید!",
            'job_list_title': "📋 **لیست آگهی‌های شغلی**\n\n",
            'job_item': "💼 **{title}**\n🏢 {company}\n📍 {city}\n📝 {description}\n👤 {name}\n📅 {date}\n",
            'contact_job': "💬 تماس با کارفرما",
            'job_contact_message': "📩 **پیام به {name}**\n\n📋 آگهی: {title}\n\n✏️ پیام خود را بنویسید:",
            'job_message_sent': "✅ **پیام ارسال شد!**\n\n📩 پیام شما به {name} ارسال شد.\n⏳ به زودی پاسخ می‌دهند.",
            'job_message_received': "📩 **پیام جدید درباره آگهی شما!**\n\n📋 آگهی: {title}\n👤 از: {name}\n📝 پیام:\n{message}\n\n💬 برای پاسخ، در چت پاسخ دهید.",
            'my_jobs_title': "📊 **آگهی‌های من**\n\n",
            'my_jobs_empty': "📊 شما هنوز آگهی ثبت نکرده‌اید.",
            'delete_job': "🗑️ حذف",
            'job_deleted': "✅ آگهی با موفقیت حذف شد!",
            'view_on_web': "🌐 مشاهده در سایت",
            'chat_with_employer': "💬 چت با کارفرما",
        },
        'tr': {
            'name': 'Türkçe', 'emoji': '🇹🇷',
            'welcome': "🎮 **UTYOB Piyango Botuna Hoş Geldiniz!**\n\n💰 10.000$'a kadar harika ödüller kazanın!\n🎯 Adil ve şeffaf piyango sistemi\n🌟 Hemen katıl ve şansını dene!",
            'main_menu': "🎯 **UTYOB Piyango Botu**\n\nAşağıdaki seçeneklerden birini seçin:\n👇👇👇",
            'lottery': "🎰 Piyangoya Katıl",
            'referral': "🔗 Referans",
            'guide': "📖 Rehber",
            'language': "🌐 Dil Değiştir",
            'admin_panel': "⚙️ Yönetim Paneli",
            'instagram_download': "📸 Instagram İndirici",
            'invoice_maker': "🧾 Fatura Oluşturucu",
            'jobs': "💼 İş İlanları",
            'add_job': "➕ İlan Ekle",
            'view_jobs': "📋 İlanları Gör",
            'my_jobs': "📊 İlanlarım",
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
            'download_failed': "❌ **İndirme başarısız!**\n\n🔹 Sebep: {}\n\n📌 Linkin doğru olduğundan ve videonun mevcut olduğundan emin olun.",
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
            'job_added': "✅ **İlan başarıyla eklendi!** 🎉\n\n📋 {}\n🏢 {}\n📍 {}\n\n🌐 Web sitesinde görüntüle: https://mbuiop.github.io/Tablikgram/",
            'job_title': "📝 **İş başlığını girin:**\nÖrnek: Kıdemli Python Geliştirici",
            'job_company': "🏢 **Şirket adını girin:**\nÖrnek: Parsian Tech",
            'job_city': "📍 **Şehri girin:**\nÖrnek: İstanbul",
            'job_description': "📝 **İş tanımını girin:**\nÖrnek: Django, React, Docker\nEn az 3 yıl deneyim",
            'job_phone': "📞 **Telefon numarası (isteğe bağlı):**\nAtlamak için 'skip' yazın",
            'job_list_empty': "📋 Hiç ilan yok.\n\n💼 İlk ilanı siz ekleyin!",
            'job_list_title': "📋 **İş İlanları**\n\n",
            'job_item': "💼 **{title}**\n🏢 {company}\n📍 {city}\n📝 {description}\n👤 {name}\n📅 {date}\n",
            'contact_job': "💬 İşverenle İletişim",
            'job_contact_message': "📩 **{name} için mesaj**\n\n📋 İlan: {title}\n\n✏️ Mesajınızı yazın:",
            'job_message_sent': "✅ **Mesaj gönderildi!**\n\n📩 Mesajınız {name} kişisine gönderildi.\n⏳ Yakında cevap verecekler.",
            'job_message_received': "📩 **İlanınız hakkında yeni mesaj!**\n\n📋 İlan: {title}\n👤 Gönderen: {name}\n📝 Mesaj:\n{message}\n\n💬 Cevap vermek için sohbette yanıtlayın.",
            'my_jobs_title': "📊 **İlanlarım**\n\n",
            'my_jobs_empty': "📊 Henüz ilan eklemediniz.",
            'delete_job': "🗑️ Sil",
            'job_deleted': "✅ İlan başarıyla silindi!",
            'view_on_web': "🌐 Web'de Görüntüle",
            'chat_with_employer': "💬 İşverenle Sohbet Et",
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

# ============================================================
# دیتابیس با ۵۰۰ شارد
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
            self._create_tables(conn)
            
    def _create_tables(self, conn):
        cursor = conn.cursor()
        
        # جدول کاربران
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
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
        )''')
        
        # جدول آگهی‌های شغلی
        cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            company TEXT,
            description TEXT,
            city TEXT,
            contact_phone TEXT,
            contact_telegram TEXT,
            first_name TEXT,
            username TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT
        )''')
        
        # جدول پیام‌های شغلی
        cursor.execute('''CREATE TABLE IF NOT EXISTS job_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            from_user_id INTEGER,
            to_user_id INTEGER,
            message TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # جدول‌های قبلی
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
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
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS pending_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            from_address TEXT,
            to_address TEXT,
            amount REAL,
            tx_hash TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS lotteries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lottery_date TEXT,
            prize_per_winner REAL,
            winners_count INTEGER,
            total_prize REAL,
            status TEXT DEFAULT 'pending',
            winners_list TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            ended_at TEXT
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lottery_id INTEGER,
            user_id INTEGER,
            prize_amount REAL,
            wallet_address TEXT,
            paid_status INTEGER DEFAULT 0,
            paid_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT,
            media_type TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS poll_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            poll_question TEXT,
            answer TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # ایندکس‌ها
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_messages_user ON job_messages(from_user_id, to_user_id)')
        
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

cache = CacheManager(max_size=20000)

# ============================================================
# سیستم مدیریت آگهی‌های شغلی
# ============================================================
class JobManager:
    
    @staticmethod
    def add_job(user_id, title, company, description, city, phone=None, telegram=None):
        """ثبت آگهی جدید"""
        try:
            cursor = db.execute(user_id,
                "SELECT first_name, username FROM users WHERE user_id = ?",
                (user_id,)
            )
            user = cursor.fetchone()
            
            db.execute(user_id,
                """INSERT INTO jobs 
                   (user_id, title, company, description, city, contact_phone, contact_telegram,
                    first_name, username, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
                (user_id, title, company, description, city, phone, telegram,
                 user['first_name'] if user else None,
                 user['username'] if user else None)
            )
            return True
        except Exception as e:
            logger.error(f"Error adding job: {e}")
            return False
    
    @staticmethod
    def get_jobs(page=1, per_page=10):
        """دریافت آگهی‌ها با صفحه‌بندی"""
        offset = (page - 1) * per_page
        return db.execute_global(
            """SELECT id, user_id, title, company, description, city, 
                      contact_phone, contact_telegram, first_name, username, created_at 
               FROM jobs 
               WHERE status = 'active' 
               ORDER BY created_at DESC 
               LIMIT ? OFFSET ?""",
            (per_page, offset)
        )
    
    @staticmethod
    def get_jobs_count():
        """تعداد کل آگهی‌ها"""
        cursor = db.execute_global(
            "SELECT COUNT(*) as count FROM jobs WHERE status = 'active'"
        )
        total = 0
        for row in cursor:
            total += row['count']
        return total
    
    @staticmethod
    def get_user_jobs(user_id):
        """دریافت آگهی‌های یک کاربر"""
        return db.execute(user_id,
            "SELECT * FROM jobs WHERE user_id = ? AND status = 'active' ORDER BY created_at DESC",
            (user_id,)
        )
    
    @staticmethod
    def delete_job(job_id, user_id):
        """حذف آگهی"""
        db.execute(user_id,
            "UPDATE jobs SET status = 'deleted' WHERE id = ? AND user_id = ?",
            (job_id, user_id)
        )
        return True
    
    @staticmethod
    def get_job(job_id):
        """دریافت یک آگهی"""
        cursor = db.execute_global(
            "SELECT * FROM jobs WHERE id = ? AND status = 'active'",
            (job_id,)
        )
        return cursor.fetchone() if cursor else None
    
    @staticmethod
    def send_message(job_id, from_user_id, message):
        """ارسال پیام به صاحب آگهی"""
        job = JobManager.get_job(job_id)
        if not job:
            return False, "Job not found"
        
        to_user_id = job['user_id']
        
        db.execute(from_user_id,
            """INSERT INTO job_messages 
               (job_id, from_user_id, to_user_id, message, is_read) 
               VALUES (?, ?, ?, ?, 0)""",
            (job_id, from_user_id, to_user_id, message)
        )
        
        return True, to_user_id
    
    @staticmethod
    def get_messages(user_id, limit=20):
        """دریافت پیام‌های کاربر"""
        return db.execute(user_id,
            """SELECT m.*, j.title, u.first_name as sender_name, u.username as sender_username 
               FROM job_messages m
               LEFT JOIN jobs j ON m.job_id = j.id
               LEFT JOIN users u ON m.from_user_id = u.user_id
               WHERE m.to_user_id = ? OR m.from_user_id = ?
               ORDER BY m.created_at DESC
               LIMIT ?""",
            (user_id, user_id, limit)
        )

# ============================================================
# Flask Routes - تبدیل منو به لینک و نمایش آگهی‌ها
# ============================================================

@flask_app.route('/')
def index():
    """صفحه اصلی با منوی تبدیل شده به لینک"""
    html = '''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UTYOB - پنل کاربری</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Vazirmatn', 'Tahoma', sans-serif;
                background: linear-gradient(135deg, #0f172a, #1e293b);
                min-height: 100vh;
                color: #f8fafc;
                padding: 20px;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                padding: 30px 0;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            .header h1 {
                font-size: 2rem;
                font-weight: 800;
                background: linear-gradient(135deg, #facc15, #f59e0b);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .header p {
                color: #94a3b8;
                margin-top: 8px;
            }
            .menu-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 16px;
                margin: 30px 0;
            }
            .menu-card {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 16px;
                padding: 24px 20px;
                text-align: center;
                transition: all 0.3s ease;
                cursor: pointer;
                text-decoration: none;
                color: #f8fafc;
            }
            .menu-card:hover {
                transform: translateY(-4px);
                background: rgba(255,255,255,0.08);
                border-color: #facc15;
            }
            .menu-card .icon {
                font-size: 2.4rem;
                margin-bottom: 10px;
            }
            .menu-card .title {
                font-weight: 700;
                font-size: 0.95rem;
            }
            .menu-card .desc {
                font-size: 0.7rem;
                color: #94a3b8;
                margin-top: 4px;
            }
            .jobs-section {
                background: rgba(255,255,255,0.03);
                border-radius: 16px;
                padding: 20px;
                margin-top: 20px;
                border: 1px solid rgba(255,255,255,0.04);
            }
            .jobs-section h2 {
                font-size: 1.2rem;
                margin-bottom: 16px;
                color: #facc15;
            }
            .job-item {
                background: rgba(255,255,255,0.03);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                border: 1px solid rgba(255,255,255,0.04);
                transition: all 0.3s ease;
            }
            .job-item:hover {
                background: rgba(255,255,255,0.06);
            }
            .job-item .title {
                font-weight: 700;
                font-size: 1rem;
                color: #f8fafc;
            }
            .job-item .company {
                color: #94a3b8;
                font-size: 0.85rem;
            }
            .job-item .city {
                color: #64748b;
                font-size: 0.75rem;
            }
            .job-item .desc {
                color: #cbd5e1;
                font-size: 0.85rem;
                margin: 6px 0;
            }
            .job-item .meta {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                margin-top: 8px;
                font-size: 0.7rem;
                color: #64748b;
            }
            .job-item .meta span {
                background: rgba(255,255,255,0.04);
                padding: 2px 10px;
                border-radius: 20px;
            }
            .btn {
                display: inline-block;
                padding: 8px 20px;
                border-radius: 8px;
                border: none;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                font-size: 0.8rem;
            }
            .btn-primary {
                background: linear-gradient(135deg, #facc15, #f59e0b);
                color: #0f172a;
            }
            .btn-primary:hover {
                transform: scale(1.02);
            }
            .btn-outline {
                background: transparent;
                border: 1px solid rgba(255,255,255,0.1);
                color: #f8fafc;
            }
            .btn-outline:hover {
                background: rgba(255,255,255,0.05);
            }
            .btn-telegram {
                background: #0088cc;
                color: white;
            }
            .btn-telegram:hover {
                background: #006699;
            }
            .pagination {
                display: flex;
                justify-content: center;
                gap: 8px;
                margin-top: 16px;
            }
            .pagination button {
                padding: 6px 14px;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                background: rgba(255,255,255,0.03);
                color: #f8fafc;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .pagination button:hover {
                background: rgba(255,255,255,0.08);
            }
            .pagination button.active {
                background: #facc15;
                color: #0f172a;
                border-color: #facc15;
            }
            .pagination button:disabled {
                opacity: 0.3;
                cursor: not-allowed;
            }
            .toast {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 24px;
                border-radius: 12px;
                background: rgba(0,0,0,0.9);
                color: white;
                font-weight: 600;
                backdrop-filter: blur(10px);
                z-index: 1000;
                display: none;
                animation: toastIn 0.4s ease;
            }
            @keyframes toastIn {
                from { opacity:0; transform:translateX(-50%) translateY(20px); }
                to { opacity:1; transform:translateX(-50%) translateY(0); }
            }
            .toast.success { border: 1px solid #22c55e; }
            .toast.error { border: 1px solid #ef4444; }
            @media (max-width: 600px) {
                .menu-grid { grid-template-columns: 1fr 1fr; gap: 10px; }
                .menu-card { padding: 16px 12px; }
                .menu-card .icon { font-size: 1.8rem; }
                .menu-card .title { font-size: 0.8rem; }
                .header h1 { font-size: 1.4rem; }
                .jobs-section { padding: 12px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚡ UTYOB</h1>
                <p>ربات قرعه‌کشی هوشمند · پنل کاربری</p>
                <div style="margin-top:12px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap;">
                    <a href="https://t.me/UTYOB_Bot" target="_blank" class="btn btn-telegram">📱 باز کردن ربات</a>
                </div>
            </div>

            <!-- منوی اصلی به صورت لینک -->
            <div class="menu-grid">
                <a href="https://t.me/UTYOB_Bot" class="menu-card">
                    <div class="icon">🎰</div>
                    <div class="title">قرعه‌کشی</div>
                    <div class="desc">شرکت در قرعه‌کشی</div>
                </a>
                <a href="https://t.me/UTYOB_Bot" class="menu-card">
                    <div class="icon">🔗</div>
                    <div class="title">رفرال</div>
                    <div class="desc">دعوت از دوستان</div>
                </a>
                <a href="https://t.me/UTYOB_Bot" class="menu-card">
                    <div class="icon">📸</div>
                    <div class="title">دانلودر</div>
                    <div class="desc">دانلود اینستاگرام</div>
                </a>
                <a href="https://t.me/UTYOB_Bot" class="menu-card">
                    <div class="icon">🧾</div>
                    <div class="title">فاکتور ساز</div>
                    <div class="desc">ساخت فاکتور حرفه‌ای</div>
                </a>
                <a href="https://t.me/UTYOB_Bot" class="menu-card">
                    <div class="icon">💼</div>
                    <div class="title">آگهی‌های شغلی</div>
                    <div class="desc">ثبت و مشاهده آگهی</div>
                </a>
                <a href="https://t.me/UTYOB_Bot" class="menu-card">
                    <div class="icon">🌐</div>
                    <div class="title">تغییر زبان</div>
                    <div class="desc">English · فارسی · Türkçe</div>
                </a>
            </div>

            <!-- بخش آگهی‌های شغلی -->
            <div class="jobs-section">
                <h2>💼 آخرین آگهی‌های شغلی</h2>
                <div id="jobsContainer">
                    <div style="text-align:center; padding:30px; color:#64748b;">
                        <i class="fas fa-spinner fa-spin" style="font-size:24px;"></i>
                        <p>در حال بارگذاری...</p>
                    </div>
                </div>
                <div class="pagination" id="pagination"></div>
                <div style="text-align:center; margin-top:16px;">
                    <a href="https://t.me/UTYOB_Bot" class="btn btn-primary">➕ ثبت آگهی جدید</a>
                </div>
            </div>
        </div>

        <div class="toast" id="toast"></div>

        <script>
            // ============================================================
            //  دریافت و نمایش آگهی‌ها از API
            // ============================================================
            let currentPage = 1;
            let totalPages = 1;

            async function loadJobs(page = 1) {
                currentPage = page;
                try {
                    const response = await fetch(`/api/jobs?page=${page}&limit=10`);
                    const data = await response.json();
                    
                    if (data.success) {
                        renderJobs(data.jobs);
                        renderPagination(data.total, page, data.limit);
                    }
                } catch(e) {
                    document.getElementById('jobsContainer').innerHTML = `
                        <div style="text-align:center; padding:30px; color:#ef4444;">
                            ❌ خطا در دریافت آگهی‌ها
                        </div>
                    `;
                }
            }

            function renderJobs(jobs) {
                const container = document.getElementById('jobsContainer');
                
                if (!jobs || jobs.length === 0) {
                    container.innerHTML = `
                        <div style="text-align:center; padding:30px; color:#64748b;">
                            <div style="font-size:3rem;">📋</div>
                            <p>هیچ آگهی شغلی وجود ندارد</p>
                            <p style="font-size:0.8rem;">اولین آگهی را در ربات ثبت کنید</p>
                        </div>
                    `;
                    return;
                }

                container.innerHTML = jobs.map(job => `
                    <div class="job-item">
                        <div class="title">💼 ${escapeHtml(job.title)}</div>
                        <div class="company">🏢 ${escapeHtml(job.company)}</div>
                        <div class="city">📍 ${escapeHtml(job.city)}</div>
                        <div class="desc">${escapeHtml(job.description)}</div>
                        <div class="meta">
                            <span>👤 ${escapeHtml(job.first_name || 'کاربر')}</span>
                            ${job.contact_phone ? `<span>📞 ${escapeHtml(job.contact_phone)}</span>` : ''}
                            ${job.contact_telegram ? `<span>🆔 @${escapeHtml(job.contact_telegram)}</span>` : ''}
                            <span>📅 ${new Date(job.created_at).toLocaleDateString('fa-IR')}</span>
                        </div>
                        <div style="margin-top:10px;">
                            <a href="https://t.me/UTYOB_Bot" class="btn btn-primary" style="font-size:0.7rem; padding:4px 14px;">
                                💬 تماس با کارفرما
                            </a>
                        </div>
                    </div>
                `).join('');
            }

            function renderPagination(total, page, limit) {
                totalPages = Math.ceil(total / limit) || 1;
                const pagination = document.getElementById('pagination');
                
                let html = '';
                html += `<button onclick="loadJobs(${page-1})" ${page <= 1 ? 'disabled' : ''}>◀️ قبلی</button>`;
                html += `<span style="padding:6px 14px; color:#94a3b8;">صفحه ${page} از ${totalPages}</span>`;
                html += `<button onclick="loadJobs(${page+1})" ${page >= totalPages ? 'disabled' : ''}>بعدی ▶️</button>`;
                
                pagination.innerHTML = html;
            }

            function escapeHtml(text) {
                if (!text) return '';
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            // بارگذاری اولیه
            loadJobs(1);

            // Toast
            function showToast(msg, type = 'success') {
                const toast = document.getElementById('toast');
                toast.textContent = msg;
                toast.className = `toast ${type}`;
                toast.style.display = 'block';
                clearTimeout(toast.timeout);
                toast.timeout = setTimeout(() => {
                    toast.style.display = 'none';
                }, 3000);
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)


@flask_app.route('/api/jobs', methods=['GET'])
def api_get_jobs():
    """API دریافت آگهی‌ها"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    
    jobs = JobManager.get_jobs(page, limit)
    total = JobManager.get_jobs_count()
    
    jobs_list = []
    for row in jobs:
        jobs_list.append({
            'id': row['id'],
            'user_id': row['user_id'],
            'title': row['title'],
            'company': row['company'],
            'description': row['description'],
            'city': row['city'],
            'contact_phone': row['contact_phone'],
            'contact_telegram': row['contact_telegram'],
            'first_name': row['first_name'],
            'username': row['username'],
            'created_at': row['created_at']
        })
    
    return jsonify({
        'success': True,
        'jobs': jobs_list,
        'total': total,
        'page': page,
        'limit': limit
    })

# ============================================================
# سیستم دانلودر
# ============================================================
class DownloadManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs("downloads", exist_ok=True)
        
    async def download_instagram(self, url: str) -> Tuple[bool, str, str]:
        try:
            import yt_dlp
            output_template = os.path.join(self.temp_dir, "instagram_%(id)s.%(ext)s")
            has_ffmpeg = shutil.which('ffmpeg') is not None
            format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]/best[ext=mp4]/best' if has_ffmpeg else 'best[ext=mp4]/best'
            ydl_opts = {
                'format': format_str,
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'continuedl': True,
                'retries': 3,
                'socket_timeout': 30,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
                },
            }
            if has_ffmpeg:
                ydl_opts['merge_output_format'] = 'mp4'
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                output_file = None
                if info:
                    file_id = info.get('id')
                    for prefix in ['instagram_', '']:
                        for ext in ['.mp4', '.mkv', '.webm']:
                            candidate = os.path.join(self.temp_dir, f"{prefix}{file_id}{ext}") if prefix else os.path.join(self.temp_dir, f"{file_id}{ext}")
                            if os.path.exists(candidate):
                                output_file = candidate
                                break
                        if output_file:
                            break
                if not output_file:
                    try:
                        files = [os.path.join(self.temp_dir, f) for f in os.listdir(self.temp_dir) if f.startswith('instagram_') or f.endswith(('.mp4', '.mkv', '.webm'))]
                        if files:
                            files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                            output_file = files[0]
                    except Exception:
                        output_file = None
                if output_file and os.path.exists(output_file):
                    return True, output_file, "Downloaded successfully"
            return False, None, "Download failed"
        except Exception as e:
            return False, None, str(e)

    def validate_instagram_url(self, url: str) -> bool:
        patterns = [r'instagram\.com/(p|reel|tv)/[^/?]+', r'instagr\.am/p/[^/?]+']
        return any(re.search(p, url) for p in patterns)

download_manager = DownloadManager()

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
# سیستم قرعه‌کشی
# ============================================================
class LotterySystem:
    def __init__(self):
        self.current_lottery = None
        self.is_running = False
        self.lock = threading.RLock()
        
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
               FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"""
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
                db.execute(user_id,
                    """INSERT INTO winners 
                       (lottery_id, user_id, prize_amount, wallet_address, paid_status) 
                       VALUES (?, ?, ?, ?, 0)""",
                    (lottery_id, user_id, prize_amount, wallet_address)
                )
            return True
        except Exception as e:
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
        except:
            pass

lottery_system = LotterySystem()

# ============================================================
# سیستم مدیریت کاربران
# ============================================================
class UserManager:
    @staticmethod
    def register_user(user_id, username=None, first_name=None, last_name=None, referred_by=None):
        try:
            cursor = db.execute(user_id, "SELECT user_id FROM users WHERE user_id = ?", (user_id,))
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
        except:
            pass
            
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
    def get_active_users():
        try:
            results = db.execute_global(
                "SELECT user_id FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"
            )
            return [row['user_id'] for row in results]
        except:
            return []
            
    @staticmethod
    def get_all_users():
        try:
            return db.execute_global("SELECT user_id, username, first_name, referral_rewards, has_subscription FROM users")
        except:
            return []
            
    @staticmethod
    def get_subscribed_users():
        try:
            return db.execute_global(
                """SELECT user_id, username, first_name, wallet_address, subscription_end, country 
                   FROM users WHERE has_subscription = 1 AND subscription_end >= date('now')"""
            )
        except:
            return []

user_manager = UserManager()

# ============================================================
# کلاس اصلی ربات
# ============================================================
class UTYOBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()
        
    def _setup_handlers(self):
        app = self.application
        
        # دستورات
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("referral", self.referral_command))
        app.add_handler(CommandHandler("language", self.language_command))
        
        # دکمه‌های منو
        app.add_handler(CallbackQueryHandler(self.main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(self.lottery_callback, pattern="^lottery$"))
        app.add_handler(CallbackQueryHandler(self.referral_callback, pattern="^referral$"))
        app.add_handler(CallbackQueryHandler(self.guide_callback, pattern="^guide$"))
        app.add_handler(CallbackQueryHandler(self.language_callback, pattern="^language$"))
        
        # دکمه‌های دانلودر
        app.add_handler(CallbackQueryHandler(self.instagram_download_callback, pattern="^instagram_download$"))
        app.add_handler(CallbackQueryHandler(self.invoice_maker_callback, pattern="^invoice_maker$"))
        
        # دکمه‌های آگهی‌های شغلی
        app.add_handler(CallbackQueryHandler(self.jobs_menu_callback, pattern="^jobs_menu$"))
        app.add_handler(CallbackQueryHandler(self.add_job_callback, pattern="^add_job$"))
        app.add_handler(CallbackQueryHandler(self.view_jobs_callback, pattern="^view_jobs$"))
        app.add_handler(CallbackQueryHandler(self.my_jobs_callback, pattern="^my_jobs$"))
        app.add_handler(CallbackQueryHandler(self.view_job_detail_callback, pattern="^view_job_"))
        app.add_handler(CallbackQueryHandler(self.delete_job_callback, pattern="^delete_job_"))
        app.add_handler(CallbackQueryHandler(self.contact_job_callback, pattern="^contact_job_"))
        
        # دکمه‌های اشتراک
        app.add_handler(CallbackQueryHandler(self.subscribe_callback, pattern="^subscribe$"))
        app.add_handler(CallbackQueryHandler(self.confirm_subscribe_callback, pattern="^confirm_subscribe$"))
        
        # دکمه‌های قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.join_lottery_callback, pattern="^join_lottery$"))
        app.add_handler(CallbackQueryHandler(self.confirm_payment_callback, pattern="^confirm_payment$"))
        
        # دکمه‌های پنل مدیریت
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
        
        # نظرسنجی
        app.add_handler(CallbackQueryHandler(self.poll_response_callback, pattern="^poll_yes$"))
        app.add_handler(CallbackQueryHandler(self.poll_response_callback, pattern="^poll_no$"))
        
        # تایید/رد
        app.add_handler(CallbackQueryHandler(self.admin_verify_approve_callback, pattern="^admin_verify_approve_"))
        app.add_handler(CallbackQueryHandler(self.admin_verify_reject_callback, pattern="^admin_verify_reject_"))
        
        # قرعه‌کشی
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
        
        # خطاها
        app.add_error_handler(self.error_handler)

    # ============================================================
    # توابع کمکی
    # ============================================================
    
    def _get_user_language(self, user_id):
        user = user_manager.get_user(user_id)
        return user['language'] if user and user['language'] else 'en'
    
    def _get_text(self, user_id, key, *args, **kwargs):
        lang = self._get_user_language(user_id)
        return LanguageManager.get_text(lang, key, *args, **kwargs)
    
    def _get_main_menu_keyboard(self, user_id):
        lang = self._get_user_language(user_id)
        keyboard = [
            [InlineKeyboardButton(self._get_text(user_id, 'lottery'), callback_data="lottery")],
            [InlineKeyboardButton(self._get_text(user_id, 'referral'), callback_data="referral")],
            [InlineKeyboardButton(self._get_text(user_id, 'instagram_download'), callback_data="instagram_download")],
            [InlineKeyboardButton(self._get_text(user_id, 'invoice_maker'), callback_data="invoice_maker")],
            [InlineKeyboardButton(self._get_text(user_id, 'jobs'), callback_data="jobs_menu")],
            [InlineKeyboardButton(self._get_text(user_id, 'guide'), callback_data="guide")],
            [InlineKeyboardButton(self._get_text(user_id, 'language'), callback_data="language")]
        ]
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton(self._get_text(user_id, 'admin_panel'), callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)

    # ============================================================
    # دستورات
    # ============================================================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        referred_by = None
        if context.args and context.args[0].startswith('ref_'):
            ref_code = context.args[0].replace('ref_', '')
            cursor = db.execute_global("SELECT user_id FROM users WHERE referral_code = ?", (ref_code,))
            if cursor:
                for row in cursor:
                    if row['user_id'] != user.id:
                        referred_by = row['user_id']
                        break
        
        user_manager.register_user(user.id, user.username, user.first_name, user.last_name, referred_by)
        lang = self._get_user_language(user.id)
        
        if referred_by:
            try:
                referrer_lang = self._get_user_language(referred_by)
                await self.application.bot.send_message(
                    chat_id=referred_by,
                    text=LanguageManager.get_text(referrer_lang, 'referral_joined',
                        user.first_name or user.username or str(user.id), str(user.id)
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
                await update.message.reply_text(
                    LanguageManager.get_text(lang, 'referral_discount',
                        user.first_name or user.username or str(user.id), str(referred_by)
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        keyboard = self._get_main_menu_keyboard(user.id)
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'welcome') + "\n\n" + LanguageManager.get_text(lang, 'main_menu'),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]]
        await update.message.reply_text(
            self._get_text(user_id, 'guide_text'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await self._show_referral(update, user_id)
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        await self._show_language_selector(update, user_id)

    # ============================================================
    # کالبک‌های منوی اصلی
    # ============================================================
    
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        keyboard = self._get_main_menu_keyboard(user_id)
        await query.edit_message_text(
            self._get_text(user_id, 'main_menu'),
            reply_markup=keyboard,
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
                [InlineKeyboardButton(self._get_text(user_id, 'subscribe'), callback_data="subscribe")],
                [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]
            ]
            await query.edit_message_text(
                self._get_text(user_id, 'no_subscription'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        keyboard = [
            [InlineKeyboardButton(self._get_text(user_id, 'lottery'), callback_data="join_lottery")],
            [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"🎰 **UTYOB {self._get_text(user_id, 'lottery')}**\n\n"
            f"👤 {user['first_name'] or user_id}\n\n"
            f"💰 Up to $10,000\n"
            f"🎯 Fair lottery",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._get_text(user_id, 'guide_text'),
            reply_markup=InlineKeyboardMarkup(keyboard),
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
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]]
            await query.edit_message_text(
                f"✅ Language changed to {LanguageManager.get_language_name(lang_code)}!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # ============================================================
    # کالبک‌های آگهی‌های شغلی
    # ============================================================
    
    async def jobs_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton(self._get_text(user_id, 'add_job'), callback_data="add_job")],
            [InlineKeyboardButton(self._get_text(user_id, 'view_jobs'), callback_data="view_jobs")],
            [InlineKeyboardButton(self._get_text(user_id, 'my_jobs'), callback_data="my_jobs")],
            [InlineKeyboardButton(self._get_text(user_id, 'view_on_web'), url="https://mbuiop.github.io/Tablikgram/")],
            [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "💼 **سیستم آگهی‌های شغلی**\n\n"
            "📌 آگهی خود را ثبت کنید و به دیگران کمک کنید.\n"
            "🔍 آگهی‌های مورد نظر خود را جستجو کنید.\n"
            "🌐 همچنین می‌توانید در سایت نیز مشاهده کنید:\n"
            "https://mbuiop.github.io/Tablikgram/",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def add_job_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        context.user_data['job_step'] = 'title'
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._get_text(user_id, 'job_title'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def view_jobs_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        page = context.user_data.get('jobs_page', 1)
        jobs = JobManager.get_jobs(page, 5)
        total = JobManager.get_jobs_count()
        
        if not jobs:
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'add_job'), callback_data="add_job")],
                [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="jobs_menu")]
            ]
            await query.edit_message_text(
                self._get_text(user_id, 'job_list_empty'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = self._get_text(user_id, 'job_list_title')
        for job in jobs:
            text += self._get_text(user_id, 'job_item',
                title=job['title'],
                company=job['company'],
                city=job['city'],
                description=job['description'][:100] + ('...' if len(job['description']) > 100 else ''),
                name=job['first_name'] or 'کاربر',
                date=job['created_at'][:10]
            )
            text += "━━━━━━━━━━━━━━━━━━\n"
        
        keyboard = []
        nav_buttons = []
        total_pages = (total + 4) // 5
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"jobs_page_{page-1}"))
        nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="jobs_page_current"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"jobs_page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([
            InlineKeyboardButton(self._get_text(user_id, 'add_job'), callback_data="add_job"),
            InlineKeyboardButton(self._get_text(user_id, 'view_on_web'), url="https://mbuiop.github.io/Tablikgram/")
        ])
        keyboard.append([InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="jobs_menu")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def my_jobs_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        jobs = JobManager.get_user_jobs(user_id)
        
        if not jobs:
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'add_job'), callback_data="add_job")],
                [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="jobs_menu")]
            ]
            await query.edit_message_text(
                self._get_text(user_id, 'my_jobs_empty'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = self._get_text(user_id, 'my_jobs_title')
        for job in jobs:
            text += f"💼 **{job['title']}**\n"
            text += f"🏢 {job['company']} | 📍 {job['city']}\n"
            text += f"📅 {job['created_at'][:10]}\n"
            text += f"📝 {job['description'][:80]}...\n"
            text += f"🔗 [مشاهده در سایت](https://mbuiop.github.io/Tablikgram/)\n\n"
        
        keyboard = []
        for job in jobs:
            keyboard.append([
                InlineKeyboardButton(f"🗑️ {job['title'][:20]}", callback_data=f"delete_job_{job['id']}"),
                InlineKeyboardButton("📋", callback_data=f"view_job_{job['id']}")
            ])
        keyboard.append([InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="jobs_menu")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    
    async def view_job_detail_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        job_id = int(query.data.split('_')[2])
        job = JobManager.get_job(job_id)
        
        if not job:
            await query.edit_message_text("❌ آگهی یافت نشد!")
            return
        
        text = f"💼 **{job['title']}**\n\n"
        text += f"🏢 {job['company']}\n"
        text += f"📍 {job['city']}\n\n"
        text += f"📝 {job['description']}\n\n"
        if job['contact_phone']:
            text += f"📞 {job['contact_phone']}\n"
        if job['contact_telegram']:
            text += f"🆔 @{job['contact_telegram']}\n"
        text += f"👤 {job['first_name'] or 'کاربر'}\n"
        text += f"📅 {job['created_at'][:10]}\n"
        
        keyboard = [
            [InlineKeyboardButton(self._get_text(user_id, 'contact_job'), callback_data=f"contact_job_{job_id}")],
            [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="view_jobs")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def delete_job_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        job_id = int(query.data.split('_')[2])
        JobManager.delete_job(job_id, user_id)
        
        await query.edit_message_text(
            self._get_text(user_id, 'job_deleted'),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="my_jobs")]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def contact_job_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        job_id = int(query.data.split('_')[2])
        job = JobManager.get_job(job_id)
        
        if not job:
            await query.edit_message_text("❌ آگهی یافت نشد!")
            return
        
        context.user_data['contact_job_id'] = job_id
        context.user_data['contact_to_user'] = job['user_id']
        
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="view_jobs")]]
        await query.edit_message_text(
            self._get_text(user_id, 'job_contact_message',
                name=job['first_name'] or 'کاربر',
                title=job['title']
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های دانلودر و فاکتور ساز
    # ============================================================
    
    async def instagram_download_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        context.user_data['download_mode'] = 'instagram'
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._get_text(user_id, 'instagram_downloader'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def invoice_maker_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        keyboard = [
            [InlineKeyboardButton(self._get_text(user_id, 'open_invoice_btn'),
                web_app=WebAppInfo(url="https://mbuiop.github.io/Tablikgram/"))],
            [InlineKeyboardButton(self._get_text(user_id, 'close'), callback_data="main_menu")]
        ]
        await query.edit_message_text(
            self._get_text(user_id, 'invoice_maker_text'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _download_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, media_type: str):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        await update.message.reply_text(self._get_text(user_id, 'processing'), parse_mode=ParseMode.MARKDOWN)
        try:
            if media_type == 'instagram':
                success, file_path, message = await download_manager.download_instagram(url)
            else:
                success, file_path, message = False, None, "Unknown media type"
            if success and file_path and os.path.exists(file_path):
                await update.message.reply_text(self._get_text(user_id, 'downloading'), parse_mode=ParseMode.MARKDOWN)
                with open(file_path, 'rb') as f:
                    await update.message.reply_video(video=f, caption=self._get_text(user_id, 'download_success'))
                try:
                    os.remove(file_path)
                except:
                    pass
                db.execute(user_id,
                    "INSERT INTO downloads (user_id, url, media_type, file_path, status) VALUES (?, ?, ?, ?, 'completed')",
                    (user_id, url, media_type, file_path)
                )
            else:
                await update.message.reply_text(self._get_text(user_id, 'download_failed', message))
                db.execute(user_id,
                    "INSERT INTO downloads (user_id, url, media_type, status) VALUES (?, ?, ?, 'failed')",
                    (user_id, url, media_type)
                )
        except Exception as e:
            await update.message.reply_text(self._get_text(user_id, 'download_failed', str(e)))

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
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]]
            await query.edit_message_text("✅ شما قبلاً اشتراک فعال دارید!", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        context.user_data['waiting_for_subscribe'] = True
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._get_text(user_id, 'subscribe_wallet', DESTINATION_WALLET),
            reply_markup=InlineKeyboardMarkup(keyboard),
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
            await query.edit_message_text(
                self._get_text(user_id, 'subscribe_wallet', DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        await query.edit_message_text(self._get_text(user_id, 'verifying'), parse_mode=ParseMode.MARKDOWN)
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
                "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, tx_id)
            )
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'lottery'), callback_data="lottery")],
                [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
            ]
            await query.edit_message_text(
                self._get_text(user_id, 'subscribe_success', PAYMENT_AMOUNT, tx_id),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['subscription_from_address'] = user['wallet_address']
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._get_text(user_id, 'subscribe_failed', message),
                reply_markup=InlineKeyboardMarkup(keyboard),
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
                [InlineKeyboardButton(self._get_text(user_id, 'subscribe'), callback_data="subscribe")],
                [InlineKeyboardButton(self._get_text(user_id, 'back'), callback_data="main_menu")]
            ]
            await query.edit_message_text(
                self._get_text(user_id, 'no_subscription'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        context.user_data['waiting_for_wallet'] = True
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._get_text(user_id, 'enter_wallet_short'),
            reply_markup=InlineKeyboardMarkup(keyboard),
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
            await query.edit_message_text(
                self._get_text(user_id, 'enter_wallet_short'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        await query.edit_message_text(self._get_text(user_id, 'verifying'), parse_mode=ParseMode.MARKDOWN)
        result = await payment_verifier.verify_transaction(
            user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT
        )
        if result[0]:
            db.execute(user_id,
                "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
                (user_id, user['wallet_address'], DESTINATION_WALLET, PAYMENT_AMOUNT, result[1])
            )
            db.execute(user_id,
                "UPDATE users SET total_participations = total_participations + 1 WHERE user_id = ?",
                (user_id,)
            )
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'lottery_back'), callback_data="lottery")],
                [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
            ]
            await query.edit_message_text(
                self._get_text(user_id, 'payment_success', PAYMENT_AMOUNT, result[1]),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            context.user_data['waiting_for_tx_hash'] = True
            context.user_data['payment_from_address'] = user['wallet_address']
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._get_text(user_id, 'payment_failed', result[2]),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های تایید/رد
    # ============================================================
    
    async def admin_verify_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        pending_id = int(query.data.split('_')[-1])
        cursor = db.execute_global("SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,))
        pending = cursor.fetchone()
        if not pending:
            await query.edit_message_text("❌ درخواست یافت نشد!")
            return
        user_id = pending['user_id']
        end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        db.execute(user_id, "UPDATE users SET has_subscription = 1, subscription_end = ? WHERE user_id = ?", (end_date, user_id))
        db.execute(user_id,
            "INSERT INTO transactions (user_id, from_address, to_address, amount, tx_id, status, verified_at) VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)",
            (user_id, pending['from_address'], pending['to_address'], pending['amount'], pending['tx_hash'])
        )
        db.execute_global("UPDATE pending_verifications SET status = 'approved' WHERE id = ?", (pending_id,))
        user_lang = self._get_user_language(user_id)
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'lottery'), callback_data="lottery")]]
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=LanguageManager.get_text(user_lang, 'user_verify_approved', pending['tx_hash']),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        await query.edit_message_text(
            f"✅ تراکنش تایید شد!\n👤 کاربر: {user_id}\n💰 مبلغ: ${pending['amount']}",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_verify_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        admin_id = query.from_user.id
        if admin_id not in ADMIN_IDS:
            await query.edit_message_text("⛔ دسترسی غیرمجاز!")
            return
        pending_id = int(query.data.split('_')[-1])
        cursor = db.execute_global("SELECT * FROM pending_verifications WHERE id = ? AND status = 'pending'", (pending_id,))
        pending = cursor.fetchone()
        if not pending:
            await query.edit_message_text("❌ درخواست یافت نشد!")
            return
        user_id = pending['user_id']
        db.execute_global("UPDATE pending_verifications SET status = 'rejected' WHERE id = ?", (pending_id,))
        user_lang = self._get_user_language(user_id)
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'retry'), callback_data="subscribe")]]
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=LanguageManager.get_text(user_lang, 'user_verify_rejected', pending['tx_hash']),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        await query.edit_message_text(
            f"❌ تراکنش رد شد!\n👤 کاربر: {user_id}",
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
            await query.edit_message_text("⛔ دسترسی غیرمجاز!", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        user_count = user_manager.get_user_count()
        active_users = len(user_manager.get_active_users())
        pending_count = len(db.execute_global("SELECT id FROM pending_verifications WHERE status = 'pending'"))
        unpaid_winners = len(db.execute_global("SELECT id FROM winners WHERE paid_status = 0"))
        subscribed_count = len(user_manager.get_subscribed_users())
        
        keyboard = [
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🎰 شروع قرعه‌کشی", callback_data="admin_start_lottery")],
            [InlineKeyboardButton(f"✅ تایید دستی ({pending_count})", callback_data="admin_manual_verify")],
            [InlineKeyboardButton("📊 ارسال نظرسنجی", callback_data="admin_poll")],
            [InlineKeyboardButton(f"💰 واریز به برندگان ({unpaid_winners})", callback_data="admin_pay_winners")],
            [InlineKeyboardButton(f"👥 کاربران اشتراکی ({subscribed_count})", callback_data="admin_subscribed_users")],
            [InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_user_list")],
            [InlineKeyboardButton("🔑 اضافه کردن API", callback_data="admin_add_api")],
            [InlineKeyboardButton("📈 آمار", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"⚙️ **پنل مدیریت**\n\n"
            f"👥 کل کاربران: {user_count:,}\n"
            f"✅ اشتراک فعال: {active_users:,}\n"
            f"⏳ در انتظار تایید: {pending_count}\n"
            f"💰 برندگان پرداخت نشده: {unpaid_winners}\n",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_subscribed_users_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        subscribed_users = user_manager.get_subscribed_users()
        if not subscribed_users:
            text = "❌ کاربر اشتراکی یافت نشد."
        else:
            text = "👥 **کاربران اشتراکی**\n\n"
            for user in subscribed_users[:30]:
                text += f"👤 {user['user_id']} - {user['first_name'] or user['username'] or 'Unknown'}\n"
                text += f"📤 {user['wallet_address'] or 'Not set'}\n"
                text += f"📅 {user['subscription_end']}\n\n"
            if len(subscribed_users) > 30:
                text += f"... و {len(subscribed_users) - 30} نفر دیگر"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await query.message.reply_text(part, reply_markup=InlineKeyboardMarkup(keyboard) if part == parts[-1] else None)
            await query.delete_message()
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
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
            text = "👥 **لیست کاربران:**\n\n"
            for i, user in enumerate(users, 1):
                text += f"{i}. {user['user_id']} - {user['first_name'] or user['username'] or 'Unknown'}\n"
                text += f"   💰 پاداش: ${user['referral_rewards']:.2f}\n"
                if i >= 30:
                    text += f"\n... و {len(users) - 30} نفر دیگر"
                    break
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await query.message.reply_text(part, reply_markup=InlineKeyboardMarkup(keyboard) if part == parts[-1] else None)
            await query.delete_message()
        else:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def admin_reset_user_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        await query.edit_message_text(
            "❌ این قابلیت غیرفعال است. لطفاً از دیتابیس مدیریت کنید.",
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
        await query.edit_message_text(
            "📢 **ارسال پیام همگانی**\n\nلطفاً متن پیام را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_start_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        if lottery_system.is_running:
            await query.edit_message_text("⚠️ قرعه‌کشی در حال اجراست!")
            return
        context.user_data['admin_action'] = 'start_lottery'
        context.user_data['lottery_step'] = 1
        keyboard = [[InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "📅 **تاریخ قرعه‌کشی را وارد کنید:**\nمثال: 2024-12-31",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        pending = db.execute_global("SELECT * FROM pending_verifications WHERE status = 'pending' ORDER BY created_at ASC")
        if not pending:
            await query.edit_message_text("✅ همه تراکنش‌ها تایید شده‌اند!")
            return
        text = "✅ **تایید دستی تراکنش‌ها**\n\n"
        for p in pending[:5]:
            text += f"🆔 #{p['id']} - کاربر: {p['user_id']}\n💰 ${p['amount']}\n🔗 `{p['tx_hash'][:20]}...`\n\n"
        text += f"📊 تعداد: {len(pending)}"
        keyboard = []
        for p in pending[:5]:
            keyboard.append([
                InlineKeyboardButton(f"✅ تایید #{p['id']}", callback_data=f"admin_verify_approve_{p['id']}"),
                InlineKeyboardButton(f"❌ رد #{p['id']}", callback_data=f"admin_verify_reject_{p['id']}")
            ])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    async def admin_poll_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        context.user_data['admin_action'] = 'poll'
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]]
        await query.edit_message_text(
            "📊 **ارسال نظرسنجی**\n\nلطفاً متن نظرسنجی را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_pay_winners_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        winners = db.execute_global("SELECT * FROM winners WHERE paid_status = 0 ORDER BY created_at ASC")
        if not winners:
            await query.edit_message_text("✅ همه برندگان پرداخت شده‌اند!")
            return
        total_prize = sum(w['prize_amount'] for w in winners)
        keyboard = [
            [InlineKeyboardButton("✅ تایید پرداخت", callback_data="pay_winners_confirm")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]
        await query.edit_message_text(
            f"💰 **پرداخت به برندگان**\n\nتعداد: {len(winners)}\nمجموع جایزه: ${total_prize}\n\n⚠️ آیا مطمئن هستید؟",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def pay_winners_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if user_id not in ADMIN_IDS:
            return
        winners = db.execute_global("SELECT * FROM winners WHERE paid_status = 0 ORDER BY created_at ASC")
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
            keyboard = [[InlineKeyboardButton(self._get_text(winner['user_id'], 'main_menu_btn'), callback_data="main_menu")]]
            try:
                await self.application.bot.send_message(
                    chat_id=winner['user_id'],
                    text=f"🎉 **تبریک! شما برنده شدید!**\n💰 جایزه: ${winner['prize_amount']}\n📤 کیف پول: {winner['wallet_address'] or 'Unknown'}",
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        await query.edit_message_text(
            f"✅ **برندگان پرداخت شدند!**\nتعداد: {len(winners)}\nمجموع: ${sum(w['prize_amount'] for w in winners)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
        await query.edit_message_text(
            "🔑 **اضافه کردن API**\n\nلطفاً کلید API جدید را وارد کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        await query.edit_message_text(
            f"📊 **آمار سیستم**\n\n"
            f"👥 کل کاربران: {user_count:,}\n"
            f"✅ فعال: {active_users:,}\n"
            f"💾 کش: {cache_stats['size']} آیتم\n"
            f"🎯 نرخ برخورد: {cache_stats['hit_rate']:.1f}%\n",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
        
        lottery_date = context.user_data.get('lottery_date')
        prize_per_winner = context.user_data.get('lottery_prize')
        winners_count = context.user_data.get('lottery_winners')
        
        if not all([lottery_date, prize_per_winner, winners_count]):
            await query.edit_message_text("❌ اطلاعات قرعه‌کشی کامل نیست!")
            return
        
        success, result = lottery_system.start_lottery(lottery_date, prize_per_winner, winners_count)
        
        if success:
            users = db.execute_global("SELECT user_id, language FROM users")
            for user in users:
                try:
                    user_lang = user['language'] if user['language'] else 'en'
                    keyboard = [
                        [InlineKeyboardButton(LanguageManager.get_text(user_lang, 'lottery'), callback_data="join_lottery")],
                        [InlineKeyboardButton(LanguageManager.get_text(user_lang, 'subscribe'), callback_data="subscribe")]
                    ]
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text=LanguageManager.get_text(user_lang, 'lottery_announcement',
                            lottery_date, prize_per_winner, winners_count, DESTINATION_WALLET
                        ),
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            
            keyboard = [
                [InlineKeyboardButton("💰 پرداخت به برندگان", callback_data="admin_pay_winners")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ]
            await query.edit_message_text(
                f"✅ **قرعه‌کشی انجام شد!**\nتعداد برندگان: {winners_count}\nجایزه هر نفر: ${prize_per_winner}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 تلاش مجدد", callback_data="admin_start_lottery")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ]
            await query.edit_message_text(
                f"❌ **خطا:** {result}",
                reply_markup=InlineKeyboardMarkup(keyboard),
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
        winner = db.execute(user_id,
            "SELECT * FROM winners WHERE user_id = ? AND paid_status = 0 ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        if not winner:
            keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]]
            await query.edit_message_text(
                self._get_text(user_id, 'no_winner'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        context.user_data['withdraw_pending'] = True
        context.user_data['winner_id'] = winner['id']
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]]
        await query.edit_message_text(
            self._get_text(user_id, 'enter_withdraw_wallet', winner['prize_amount']),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def confirm_withdraw_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        if not context.user_data.get('withdraw_pending'):
            await query.edit_message_text("⚠️ درخواست برداشتی وجود ندارد!")
            return
        user = user_manager.get_user(user_id)
        if not user or not user['wallet_address']:
            await query.edit_message_text("❌ آدرس کیف پول یافت نشد!")
            return
        winner_id = context.user_data.get('winner_id')
        if winner_id:
            db.execute(user_id,
                "UPDATE winners SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP WHERE id = ?",
                (user['wallet_address'], winner_id)
            )
            context.user_data['withdraw_pending'] = False
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'next_lottery'), callback_data="lottery")],
                [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
            ]
            cursor = db.execute(user_id, "SELECT prize_amount FROM winners WHERE id = ?", (winner_id,))
            winner = cursor.fetchone()
            await query.edit_message_text(
                self._get_text(user_id, 'withdraw_success', winner['prize_amount'], user['wallet_address']),
                reply_markup=InlineKeyboardMarkup(keyboard),
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
        display_answer = LanguageManager.get_text(lang, 'poll_yes') if answer == 'poll_yes' else LanguageManager.get_text(lang, 'poll_no')
        db.execute(user_id,
            "INSERT INTO poll_responses (user_id, poll_question, answer) VALUES (?, ?, ?)",
            (user_id, poll_question, display_answer)
        )
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'poll_thanks', display_answer),
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
        bot = await self.application.bot.get_me()
        referral_link = f"https://t.me/{bot.username}?start=ref_{referral_code}"
        referred_count = len(db.execute_global("SELECT user_id FROM users WHERE referred_by = ?", (user_id,)))
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
        if isinstance(update, Update):
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    async def _show_language_selector(self, update, user_id):
        current_lang = self._get_user_language(user_id)
        lang = current_lang
        keyboard = []
        for code in ['en', 'fa', 'tr']:
            name = LanguageManager.get_text(lang, 'name', lang=code)
            if code == current_lang:
                name = f"✅ {name}"
            keyboard.append([InlineKeyboardButton(
                f"{LanguageManager.get_language_emoji(code)} {name}",
                callback_data=f"set_lang_{code}"
            )])
        keyboard.append([InlineKeyboardButton(LanguageManager.get_text(lang, 'back'), callback_data="main_menu")])
        text = LanguageManager.get_text(lang, 'language_selector', LanguageManager.get_language_name(current_lang))
        if isinstance(update, Update):
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    # ============================================================
    # مدیریت پیام‌ها
    # ============================================================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        lang = self._get_user_language(user_id)
        
        # حالت دانلودر
        download_mode = context.user_data.get('download_mode')
        if download_mode in ['instagram']:
            if text.startswith(('http://', 'https://')):
                if download_mode == 'instagram' and not download_manager.validate_instagram_url(text):
                    await update.message.reply_text(self._get_text(user_id, 'invalid_url'), parse_mode=ParseMode.MARKDOWN)
                    return
                await self._download_media(update, context, text, download_mode)
                context.user_data['download_mode'] = None
                return
            else:
                await update.message.reply_text(self._get_text(user_id, 'invalid_url'), parse_mode=ParseMode.MARKDOWN)
                return
        
        # ثبت آگهی شغلی
        job_step = context.user_data.get('job_step')
        if job_step:
            if text.lower() == '/cancel':
                context.user_data['job_step'] = None
                await update.message.reply_text("❌ ثبت آگهی لغو شد.", reply_markup=self._get_main_menu_keyboard(user_id))
                return
            
            if job_step == 'title':
                context.user_data['job_title'] = text
                context.user_data['job_step'] = 'company'
                await update.message.reply_text(self._get_text(user_id, 'job_company'), parse_mode=ParseMode.MARKDOWN)
            elif job_step == 'company':
                context.user_data['job_company'] = text
                context.user_data['job_step'] = 'city'
                await update.message.reply_text(self._get_text(user_id, 'job_city'), parse_mode=ParseMode.MARKDOWN)
            elif job_step == 'city':
                context.user_data['job_city'] = text
                context.user_data['job_step'] = 'description'
                await update.message.reply_text(self._get_text(user_id, 'job_description'), parse_mode=ParseMode.MARKDOWN)
            elif job_step == 'description':
                context.user_data['job_description'] = text
                context.user_data['job_step'] = 'phone'
                await update.message.reply_text(self._get_text(user_id, 'job_phone'), parse_mode=ParseMode.MARKDOWN)
            elif job_step == 'phone':
                phone = None if text.lower() == 'skip' else text
                success = JobManager.add_job(
                    user_id=user_id,
                    title=context.user_data.get('job_title'),
                    company=context.user_data.get('job_company'),
                    city=context.user_data.get('job_city'),
                    description=context.user_data.get('job_description'),
                    phone=phone
                )
                context.user_data['job_step'] = None
                if success:
                    keyboard = [
                        [InlineKeyboardButton(self._get_text(user_id, 'view_jobs'), callback_data="view_jobs")],
                        [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
                    ]
                    await update.message.reply_text(
                        self._get_text(user_id, 'job_added',
                            context.user_data.get('job_title'),
                            context.user_data.get('job_company'),
                            context.user_data.get('job_city')
                        ),
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text("❌ خطا در ثبت آگهی! لطفاً دوباره تلاش کنید.")
                # پاک کردن داده‌ها
                for key in ['job_title', 'job_company', 'job_city', 'job_description']:
                    context.user_data.pop(key, None)
                return
        
        # پیام چت با کارفرما
        contact_job_id = context.user_data.get('contact_job_id')
        if contact_job_id:
            to_user_id = context.user_data.get('contact_to_user')
            success, result = JobManager.send_message(contact_job_id, user_id, text)
            if success:
                # ارسال پیام به کارفرما
                job = JobManager.get_job(contact_job_id)
                user = user_manager.get_user(user_id)
                user_name = user['first_name'] or user['username'] or str(user_id)
                try:
                    await self.application.bot.send_message(
                        chat_id=to_user_id,
                        text=LanguageManager.get_text(self._get_user_language(to_user_id), 'job_message_received',
                            title=job['title'] if job else 'Unknown',
                            name=user_name,
                            message=text
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
                await update.message.reply_text(
                    self._get_text(user_id, 'job_message_sent',
                        job['first_name'] if job else 'کارفرما'
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
                context.user_data['contact_job_id'] = None
                context.user_data['contact_to_user'] = None
            else:
                await update.message.reply_text("❌ خطا در ارسال پیام!", parse_mode=ParseMode.MARKDOWN)
            return
        
        # اقدامات ادمین
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
        
        # دریافت هش تراکنش
        if context.user_data.get('waiting_for_tx_hash'):
            tx_hash = text.strip()
            if len(tx_hash) != 64:
                await update.message.reply_text(self._get_text(user_id, 'tx_hash_invalid'), parse_mode=ParseMode.MARKDOWN)
                return
            from_address = context.user_data.get('subscription_from_address') or context.user_data.get('payment_from_address')
            db.execute_global(
                "INSERT INTO pending_verifications (user_id, from_address, to_address, amount, tx_hash, status) VALUES (?, ?, ?, ?, ?, 'pending')",
                (user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash)
            )
            context.user_data['waiting_for_tx_hash'] = False
            await update.message.reply_text(self._get_text(user_id, 'tx_hash_received', tx_hash), parse_mode=ParseMode.MARKDOWN)
            pending_id = db.execute_global("SELECT last_insert_rowid()").fetchone()[0]
            for admin_id in ADMIN_IDS:
                try:
                    keyboard = [
                        [InlineKeyboardButton("✅ تایید", callback_data=f"admin_verify_approve_{pending_id}"),
                         InlineKeyboardButton("❌ رد", callback_data=f"admin_verify_reject_{pending_id}")]
                    ]
                    await self.application.bot.send_message(
                        chat_id=admin_id,
                        text=LanguageManager.get_text('fa', 'admin_verify_tx',
                            user_id, from_address, DESTINATION_WALLET, PAYMENT_AMOUNT, tx_hash
                        ),
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode=ParseMode.MARKDOWN
                    )
                except:
                    pass
            return
        
        # دریافت آدرس کیف پول
        if context.user_data.get('waiting_for_subscribe'):
            wallet_address = text.strip()
            if len(wallet_address) != 34:
                await update.message.reply_text(self._get_text(user_id, 'invalid_wallet'), parse_mode=ParseMode.MARKDOWN)
                return
            user_manager.update_user(user_id, wallet_address=wallet_address)
            context.user_data['waiting_for_subscribe'] = False
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'confirm_subscribe'), callback_data="confirm_subscribe")],
                [InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]
            ]
            await update.message.reply_text(
                self._get_text(user_id, 'after_subscribe_wallet', wallet_address, DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if context.user_data.get('waiting_for_wallet'):
            wallet_address = text.strip()
            if len(wallet_address) != 34:
                await update.message.reply_text(self._get_text(user_id, 'invalid_wallet'), parse_mode=ParseMode.MARKDOWN)
                return
            user_manager.update_user(user_id, wallet_address=wallet_address)
            context.user_data['waiting_for_wallet'] = False
            keyboard = [
                [InlineKeyboardButton(self._get_text(user_id, 'confirm_payment'), callback_data="confirm_payment")],
                [InlineKeyboardButton(self._get_text(user_id, 'cancel'), callback_data="main_menu")]
            ]
            await update.message.reply_text(
                self._get_text(user_id, 'after_wallet', wallet_address, DESTINATION_WALLET),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # برداشت جایزه
        if context.user_data.get('withdraw_pending'):
            wallet_address = text.strip()
            if len(wallet_address) != 34:
                await update.message.reply_text(self._get_text(user_id, 'invalid_wallet'), parse_mode=ParseMode.MARKDOWN)
                return
            user_manager.update_user(user_id, wallet_address=wallet_address)
            winner_id = context.user_data.get('winner_id')
            if winner_id:
                db.execute(user_id,
                    "UPDATE winners SET wallet_address = ?, paid_status = 1, paid_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (wallet_address, winner_id)
                )
                context.user_data['withdraw_pending'] = False
                keyboard = [
                    [InlineKeyboardButton(self._get_text(user_id, 'next_lottery'), callback_data="lottery")],
                    [InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]
                ]
                cursor = db.execute(user_id, "SELECT prize_amount FROM winners WHERE id = ?", (winner_id,))
                winner = cursor.fetchone()
                await update.message.reply_text(
                    self._get_text(user_id, 'withdraw_success', winner['prize_amount'], wallet_address),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # پیام معمولی
        keyboard = self._get_main_menu_keyboard(user_id)
        await update.message.reply_text(
            self._get_text(user_id, 'invalid_command'),
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _handle_lottery_steps(self, update, text, context):
        user_id = update.effective_user.id
        step = context.user_data.get('lottery_step', 1)
        
        if step == 1:
            try:
                context.user_data['lottery_date'] = text.strip()
                context.user_data['lottery_step'] = 2
                await update.message.reply_text(
                    "💰 **مبلغ جایزه هر برنده را وارد کنید:**\nمثال: 500",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await update.message.reply_text("❌ تاریخ نامعتبر!")
        elif step == 2:
            try:
                prize = float(text)
                if prize < 10:
                    await update.message.reply_text("❌ مبلغ باید حداقل ۱۰ دلار باشد!")
                    return
                context.user_data['lottery_prize'] = prize
                context.user_data['lottery_step'] = 3
                await update.message.reply_text(
                    "👥 **تعداد برندگان را وارد کنید:**\nمثال: 3",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await update.message.reply_text("❌ عدد معتبر وارد کنید!")
        elif step == 3:
            try:
                winners_count = int(text)
                if winners_count < 1 or winners_count > 100:
                    await update.message.reply_text("❌ تعداد بین ۱ تا ۱۰۰ باشد!")
                    return
                context.user_data['lottery_winners'] = winners_count
                context.user_data['lottery_step'] = 4
                keyboard = [
                    [InlineKeyboardButton("✅ تایید و شروع", callback_data="start_lottery_confirm")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="admin_panel")]
                ]
                await update.message.reply_text(
                    f"✅ **اطلاعات قرعه‌کشی:**\n\n"
                    f"📅 تاریخ: {context.user_data.get('lottery_date')}\n"
                    f"💰 جایزه هر نفر: ${context.user_data.get('lottery_prize')}\n"
                    f"👥 تعداد برندگان: {winners_count}\n\n"
                    f"⚠️ آیا مطمئن هستید؟",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await update.message.reply_text("❌ عدد معتبر وارد کنید!")
    
    async def _handle_add_api(self, update, text, context):
        api_key = text.strip()
        if payment_verifier.add_api(api_key):
            context.user_data['admin_action'] = None
            await update.message.reply_text(f"✅ **API اضافه شد!**\n🔑 کلید: `{api_key}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("❌ API قبلاً اضافه شده یا نامعتبر است!")
    
    async def _send_poll(self, update, text, context):
        await update.message.reply_text("⏳ در حال ارسال نظرسنجی...", parse_mode=ParseMode.MARKDOWN)
        users = db.execute_global("SELECT user_id, language FROM users")
        sent = 0
        for user in users:
            try:
                user_lang = user['language'] if user['language'] else 'en'
                keyboard = [[
                    InlineKeyboardButton(LanguageManager.get_text(user_lang, 'poll_option_1'), callback_data="poll_yes"),
                    InlineKeyboardButton(LanguageManager.get_text(user_lang, 'poll_option_2'), callback_data="poll_no")
                ]]
                await self.application.bot.send_message(
                    chat_id=user['user_id'],
                    text=LanguageManager.get_text(user_lang, 'poll_message', text),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                if sent % 30 == 0:
                    await asyncio.sleep(0.3)
            except:
                pass
        context.user_data['admin_action'] = None
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        await update.message.reply_text(
            f"✅ **نظرسنجی ارسال شد!**\n📤 {sent} کاربر",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _send_broadcast(self, update, text, context):
        await update.message.reply_text("⏳ در حال ارسال پیام...", parse_mode=ParseMode.MARKDOWN)
        users = db.execute_global("SELECT user_id FROM users")
        sent = 0
        for user in users:
            try:
                await self.application.bot.send_message(chat_id=user['user_id'], text=text, parse_mode=ParseMode.MARKDOWN)
                sent += 1
                if sent % 30 == 0:
                    await asyncio.sleep(0.3)
            except:
                pass
        context.user_data['admin_action'] = None
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]]
        await update.message.reply_text(
            f"✅ **پیام ارسال شد!**\n📤 {sent} کاربر",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        keyboard = [[InlineKeyboardButton(self._get_text(user_id, 'main_menu_btn'), callback_data="main_menu")]]
        await update.message.reply_text(
            self._get_text(user_id, 'photo_not_supported'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")
        try:
            if update and update.effective_user:
                user_id = update.effective_user.id
                keyboard = self._get_main_menu_keyboard(user_id)
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=self._get_text(user_id, 'error_message'),
                    reply_markup=keyboard
                )
        except:
            pass

# ============================================================
# اجرای ربات و سرور
# ============================================================

def run_flask():
    """اجرای سرور Flask در ترد جداگانه"""
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

async def main():
    try:
        # راه‌اندازی سرور Flask در ترد جداگانه
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        logger.info("🌐 Flask server started on http://0.0.0.0:5000")
        
        # راه‌اندازی ربات
        bot = UTYOBot()
        logger.info("🚀 UTYOB Bot starting...")
        logger.info(f"👥 Admins: {len(ADMIN_IDS)}")
        logger.info(f"🗄️ Shards: {DB_SHARDS}")
        logger.info(f"⚡ Threads: 50")
        
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