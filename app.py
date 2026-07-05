# ============================================================
# ربات قرعه‌کشی هوشمند UTYOB - نسخه کامل با پشتیبانی چندزبان
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
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from flask import Flask, request, jsonify

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

DB_SHARDS = 100
CACHE_TTL = 300

# ============================================================
# سیستم چندزبانه (MULTI-LANGUAGE SYSTEM)
# ============================================================
class LanguageManager:
    """مدیریت زبان‌های ربات"""
    
    LANGUAGES = {
        'en': {
            'name': 'English',
            'emoji': '🇬🇧',
            'welcome': "🎮 **Welcome to UTYOB Lottery Bot!**\n\n💰 Win amazing prizes up to $10,000!\n🎯 Fair and transparent lottery system\n🌟 Join now and test your luck!\n\nClick PLAY to enter the game.",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **UTYOB Lottery Bot**\n\nSelect an option below:\n👇👇👇",
            'lottery': "🎰 Lottery",
            'referral': "🔗 Referral & Invite Friends",
            'guide': "📖 Guide & Rules",
            'language': "🌐 Change Language",
            'admin_panel': "⚙️ Admin Panel",
            'no_subscription': "❌ **You don't have an active subscription!**\n\nTo participate in the lottery, you must first purchase a subscription.\n\n💰 Subscription cost: $100\n📅 Validity: 1 month\n\nClick the button below to subscribe.",
            'renew_subscription': "🔄 Renew Subscription",
            'back': "🔙 Back",
            'enter_wallet': "💳 **Deposit to participate in the lottery**\n\nPlease enter your source wallet address (TRC20):\n\n🔹 **Deposit amount:** $100\n🔹 **Destination address:**\n`{}`\n\n⚠️ **Important notes:**\n• Use only TRC20 network\n• Amount must be exactly $100\n• System will verify automatically\n• Save transaction ID for tracking\n\n📤 **Enter your source address:**",
            'confirm_payment': "✅ Confirm Payment",
            'cancel': "❌ Cancel",
            'verifying': "⏳ Verifying your payment...\nPlease wait a moment.",
            'payment_success': "✅ **Payment verified!**\n\n🔹 Amount: ${}\n🔹 Transaction: `{}`\n\n🎉 You have successfully registered for the lottery.\n🙏 Good luck!",
            'payment_failed': "❌ **Payment verification failed!**\n\n🔹 Reason: {}\n\n📌 **Solutions:**\n1. Amount must be exactly $100\n2. Destination address must be correct\n3. Transaction must be completed\n4. Use TRC20 network\n\n🔄 Try again after checking.",
            'retry': "🔄 Retry",
            'support': "📞 Support",
            'main_menu_btn': "🔙 Main Menu",
            'lottery_back': "🎰 Back to Lottery",
            'withdraw_prize': "💰 Withdraw Prize",
            'next_lottery': "🎰 Next Lottery",
            'enter_withdraw_wallet': "💰 **Withdraw Prize**\n\nPrize amount: **${:,}**\n\nPlease enter your TRC20 wallet address:\n\n⚠️ **Important notes:**\n• Use only TRC20 network\n• Address must be correct\n• After confirmation, payment will be made\n\n📤 **Enter your wallet address:**",
            'withdraw_success': "✅ **Withdrawal registered successfully!** 🎉\n\n💰 Amount: ${:,}\n📤 Address: {}\n\n⏳ Amount will be sent to your account soon.\n🔔 You will be notified when sent.",
            'referral_text': "🔗 **UTYOB Referral System**\n\n👤 You: {}\n📊 Invites: {}\n\n🔑 **Your referral code:**\n`{}`\n\n🔗 **Referral link:**\n{}\n\n💰 **Referral reward:**\n• 5% of deposit per invite\n• Instant reward after verification\n\n📤 Share this link with your friends!",
            'share': "📤 Share",
            'guide_text': "📖 **UTYOB Bot Complete Guide**\n\n🎯 **How it works:**\n1. **Register**: Use /start to register\n2. **Subscription**: Purchase subscription to participate\n3. **Deposit**: Send $100 to the specified address\n4. **Participate**: Join the lottery after verification\n5. **Win**: Receive prize if you win\n\n💰 **Deposit amount:**\n- Fixed amount: $100\n- Deposit address: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- Network: TRC20\n\n🎁 **Prizes:**\n- 1st prize: 50% of total\n- 2nd prize: 30% of total\n- 3rd prize: 20% of total\n\n🔗 **Referral system:**\n- Each user has unique referral code\n- 5% reward per invite\n\n⚠️ **Rules:**\n- One participation per lottery per user\n- Previous winners have lower chance\n- All transactions verified automatically\n\n📞 **Support:**\nContact admin for questions.",
            'language_selector': "🌐 **Change Language**\n\nCurrent language: {}",
            'admin_stats': "📈 **System Statistics**\n\n👥 **Users:**\n• Total: {:,}\n• Active: {:,}\n• Active rate: {:.1f}%\n\n💳 **Transactions:**\n• Total: {:,}\n• Verified: {:,}\n• Pending: {:,}\n\n🎰 **Lottery:**\n• Total: {}\n• Total winners: {}\n• Last: {}\n\n⚡ **System:**\n• Cache: {} items\n• Hit rate: {:.1f}%\n• APIs: {}\n• Shards: {}",
            'refresh': "🔄 Refresh",
            'admin_panel_text': "⚙️ **Admin Panel**\n\n📊 **Statistics:**\n• Total users: {:,}\n• Active users: {:,}\n• Cache: {} items\n• APIs: {}\n\nSelect an option:",
            'broadcast': "📢 Send Broadcast",
            'start_lottery': "🎰 Start Lottery",
            'manual_verify': "✅ Manual Verify",
            'poll': "📊 Send Poll",
            'pay_winners': "💰 Pay Winners",
            'add_api': "🔑 Add New API",
            'stats': "📈 Statistics",
            'lottery_confirm': "🎰 **Start New Lottery**\n\n👥 Eligible users: {} users\n\nAre you sure you want to start the lottery?\n\n⚠️ **Note:**\n• All subscribed users participate\n• Previous winners have lower chance\n• Lottery is fair and transparent",
            'confirm': "✅ Confirm",
            'enter_winners': "🎯 **Number of Winners**\n\nPlease enter the number of winners for this lottery:\n(Max 100)\n\nExample: `5`",
            'enter_prize': "✅ Winners: {}\n\n💰 **Prize Amount per Winner**\n\nPlease enter the prize amount for each winner:\n(Minimum $10)\n\nExample: `100`",
            'lottery_final': "✅ **Lottery Information:**\n\n• Winners: {}\n• Prize per winner: ${:,}\n• Total prize: ${:,}\n\n⚠️ Are you sure you want to start the lottery?",
            'lottery_success': "✅ **Lottery completed successfully!** 🎉\n\n📊 **Details:**\n• Lottery ID: {}\n• Winners: {}\n• Prize per winner: ${:,}\n• Total prize: ${:,}\n\n👥 **Winners:**\n{}\n\n✅ Congratulations messages sent to winners.",
            'lottery_error': "❌ **Error starting lottery!**\n\n🔹 Reason: {}\n\nPlease check:\n• Eligible users count\n• Winners count entered\n• Database connection",
            'winner_message': "🎉 **Congratulations! You won!** 🎉\n\n💰 Prize amount: **${:,}**\n🏆 Lottery ID: {}\n\n✅ Click the button below to withdraw your prize:\n📌 Enter your wallet address",
            'already_paid': "✅ Prize already paid!\n\n💰 Amount: ${}\n📅 Date: {}",
            'no_winner': "❌ You don't have any prize!\n\nParticipate in future lotteries.",
            'manual_verify_text': "✅ **Manual Transaction Verification**\n\n{}\n📊 Total: {}\n\nUse admin panel to verify each user.",
            'no_pending': "✅ **All transactions verified!**\n\nNo pending transactions.",
            'poll_create': "📊 **Create New Poll**\n\nPlease send the poll question:\n\nExample: `What do you think about the lottery?`",
            'poll_options': "📊 **Poll Options**\n\nPlease enter poll options (one per line):\n\nExample:\nExcellent\nGood\nAverage\nPoor",
            'pay_winners_text': "💰 **Pay Winners**\n\n{}\n📊 Total: {}\n\nUse admin panel to process payments.",
            'no_winners': "✅ **All winners paid!**",
            'add_api_text': "🔑 **Add New API**\n\nPlease enter the new API key:\n\n⚠️ **Notes:**\n• API is used for transaction verification\n• Each API can handle thousands of users\n• More APIs = More speed",
            'api_added': "✅ **New API added successfully!**\n\n🔑 Key: `{}`\n📊 Total APIs: {}\n\nThis API will be used for transaction verification.",
            'api_error': "❌ **Error adding API!**\n\nThis API already exists or is invalid.",
            'invalid_command': "⚠️ Invalid command!\n\nUse the buttons or /help.",
            'photo_not_supported': "📸 Photo received!\nBut this feature is not supported.",
            'error_message': "⚠️ An error occurred! Please try again.",
        },
        'fa': {
            'name': 'فارسی',
            'emoji': '🇮🇷',
            'welcome': "🎮 **به ربات قرعه‌کشی UTYOB خوش آمدید!**\n\n💰 برنده جوایز شگفت‌انگیز تا ۱۰۰۰۰ دلار شوید!\n🎯 سیستم قرعه‌کشی عادلانه و شفاف\n🌟 همین حالا بپیوندید و شانس خود را امتحان کنید!\n\nبرای ورود به بازی، روی PLAY کلیک کنید.",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **ربات قرعه‌کشی UTYOB**\n\nیکی از گزینه‌های زیر را انتخاب کنید:\n👇👇👇",
            'lottery': "🎰 قرعه‌کشی",
            'referral': "🔗 رفرال و دعوت دوستان",
            'guide': "📖 راهنمایی و قوانین",
            'language': "🌐 تغییر زبان",
            'admin_panel': "⚙️ پنل مدیریت",
            'no_subscription': "❌ **شما اشتراک فعال ندارید!**\n\nبرای شرکت در قرعه‌کشی، ابتدا باید اشتراک تهیه کنید.\n\n💰 هزینه اشتراک: ۱۰۰ دلار\n📅 مدت اعتبار: ۱ ماه\n\nبرای تهیه اشتراک، روی دکمه زیر کلیک کنید.",
            'renew_subscription': "🔄 تمدید اشتراک",
            'back': "🔙 بازگشت",
            'enter_wallet': "💳 **واریز برای شرکت در قرعه‌کشی**\n\nلطفاً آدرس کیف پول مبدا (TRC20) خود را وارد کنید:\n\n🔹 **مبلغ واریز:** ۱۰۰ دلار\n🔹 **آدرس مقصد:**\n`{}`\n\n⚠️ **نکات مهم:**\n• فقط از شبکه TRC20 استفاده کنید\n• مبلغ دقیقاً ۱۰۰ دلار باشد\n• سیستم به صورت خودکار تایید می‌کند\n• کد تراکنش را برای پیگیری ذخیره کنید\n\n📤 **آدرس مبدا خود را وارد کنید:**",
            'confirm_payment': "✅ تایید واریز",
            'cancel': "❌ انصراف",
            'verifying': "⏳ در حال بررسی پرداخت شما...\nلطفاً چند لحظه صبر کنید.",
            'payment_success': "✅ **پرداخت شما تایید شد!**\n\n🔹 مبلغ: {}$\n🔹 تراکنش: `{}`\n\n🎉 شما با موفقیت در قرعه‌کشی ثبت نام کردید.\n🙏 برای شما آرزوی موفقیت داریم!",
            'payment_failed': "❌ **پرداخت شما تایید نشد!**\n\n🔹 دلیل: {}\n\n📌 **راهکارها:**\n1. مبلغ دقیقاً ۱۰۰ دلار باشد\n2. آدرس مقصد صحیح باشد\n3. تراکنش انجام شده باشد\n4. از شبکه TRC20 استفاده کنید\n\n🔄 پس از بررسی، مجدداً تلاش کنید.",
            'retry': "🔄 تلاش مجدد",
            'support': "📞 پشتیبانی",
            'main_menu_btn': "🔙 منوی اصلی",
            'lottery_back': "🎰 بازگشت به قرعه‌کشی",
            'withdraw_prize': "💰 برداشت جایزه",
            'next_lottery': "🎰 قرعه‌کشی بعدی",
            'enter_withdraw_wallet': "💰 **برداشت جایزه**\n\nمبلغ جایزه: **${:,}**\n\nلطفاً آدرس کیف پول TRC20 خود را وارد کنید:\n\n⚠️ **نکات مهم:**\n• فقط از شبکه TRC20 استفاده کنید\n• آدرس باید دقیق و صحیح باشد\n• پس از تایید، واریز انجام می‌شود\n\n📤 **آدرس کیف پول خود را وارد کنید:**",
            'withdraw_success': "✅ **برداشت شما با موفقیت ثبت شد!** 🎉\n\n💰 مبلغ: ${:,}\n📤 آدرس: {}\n\n⏳ مبلغ به زودی به حساب شما واریز می‌شود.\n🔔 پس از واریز، به شما اطلاع داده می‌شود.",
            'referral_text': "🔗 **سیستم رفرال UTYOB**\n\n👤 شما: {}\n📊 تعداد دعوت‌ها: {}\n\n🔑 **کد رفرال شما:**\n`{}`\n\n🔗 **لینک دعوت:**\n{}\n\n💰 **پاداش دعوت:**\n• به ازای هر دعوت: ۵٪ از واریز\n• پاداش فوری پس از تایید\n\n📤 لینک را برای دوستان خود ارسال کنید!",
            'share': "📤 اشتراک‌گذاری",
            'guide_text': "📖 **راهنمای کامل ربات UTYOB**\n\n🎯 **نحوه کار:**\n1. **ثبت‌نام**: با دستور /start ثبت‌نام کنید\n2. **اشتراک**: برای شرکت در قرعه‌کشی، اشتراک تهیه کنید\n3. **واریز**: مبلغ ۱۰۰ دلار به آدرس مشخص واریز کنید\n4. **شرکت**: پس از تایید، در قرعه‌کشی شرکت کنید\n5. **برنده**: در صورت برنده شدن، جایزه دریافت کنید\n\n💰 **مبلغ واریز:**\n- مبلغ ثابت: ۱۰۰ دلار\n- آدرس واریز: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- شبکه: TRC20\n\n🎁 **جوایز:**\n- جایزه اول: ۵۰٪ از کل مبلغ\n- جایزه دوم: ۳۰٪ از کل مبلغ\n- جایزه سوم: ۲۰٪ از کل مبلغ\n\n🔗 **سیستم رفرال:**\n- هر کاربر کد رفرال اختصاصی دارد\n- به ازای هر دعوت، ۵٪ پاداش دریافت کنید\n\n⚠️ **قوانین:**\n- هر کاربر فقط یک بار در هر قرعه‌کشی شرکت می‌کند\n- برندگان قبلی شانس کمتری در قرعه‌کشی‌های بعدی دارند\n- تمامی تراکنش‌ها به صورت خودکار تایید می‌شوند\n\n📞 **پشتیبانی:**\nبرای سوالات و مشکلات با مدیریت تماس بگیرید.",
            'language_selector': "🌐 **تغییر زبان**\n\nزبان فعلی: {}",
            'admin_stats': "📈 **آمار کامل سیستم**\n\n👥 **کاربران:**\n• کل: {:,}\n• فعال: {:,}\n• درصد فعال: {:.1f}%\n\n💳 **تراکنش‌ها:**\n• کل: {:,}\n• تایید شده: {:,}\n• در انتظار: {:,}\n\n🎰 **قرعه‌کشی:**\n• تعداد: {}\n• برندگان کل: {}\n• آخرین: {}\n\n⚡ **سیستم:**\n• کش: {} آیتم\n• نرخ برخورد: {:.1f}%\n• API‌ها: {}\n• شاردها: {}",
            'refresh': "🔄 به‌روزرسانی",
            'admin_panel_text': "⚙️ **پنل مدیریت**\n\n📊 **آمار:**\n• کل کاربران: {:,}\n• کاربران فعال: {:,}\n• کش: {} آیتم\n• API‌ها: {}\n\nانتخاب کنید:",
            'broadcast': "📢 ارسال پیام همگانی",
            'start_lottery': "🎰 شروع قرعه‌کشی",
            'manual_verify': "✅ تایید دستی",
            'poll': "📊 ارسال نظرسنجی",
            'pay_winners': "💰 واریز به برندگان",
            'add_api': "🔑 اضافه کردن API جدید",
            'stats': "📈 آمار و اطلاعات",
            'lottery_confirm': "🎰 **شروع قرعه‌کشی جدید**\n\n👥 کاربران واجد شرایط: {} نفر\n\nآیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟\n\n⚠️ **توجه:**\n• تمام کاربران دارای اشتراک شرکت می‌کنند\n• برندگان قبلی شانس کمتری دارند\n• قرعه‌کشی به صورت عادلانه انجام می‌شود",
            'confirm': "✅ تایید",
            'enter_winners': "🎯 **تعداد برندگان**\n\nلطفاً تعداد برندگان این قرعه‌کشی را وارد کنید:\n(حداکثر ۱۰۰ نفر)\n\nمثال: `5`",
            'enter_prize': "✅ تعداد برندگان: {}\n\n💰 **مبلغ جایزه هر نفر**\n\nلطفاً مبلغ جایزه برای هر برنده را وارد کنید:\n(حداقل ۱۰ دلار)\n\nمثال: `100`",
            'lottery_final': "✅ **اطلاعات قرعه‌کشی:**\n\n• تعداد برندگان: {}\n• جایزه هر نفر: ${:,}\n• کل جایزه: ${:,}\n\n⚠️ آیا مطمئن هستید که می‌خواهید قرعه‌کشی را شروع کنید؟",
            'lottery_success': "✅ **قرعه‌کشی با موفقیت انجام شد!** 🎉\n\n📊 **جزئیات:**\n• شماره قرعه‌کشی: {}\n• تعداد برندگان: {}\n• جایزه هر نفر: ${:,}\n• کل جایزه: ${:,}\n\n👥 **برندگان:**\n{}\n\n✅ پیام‌های تبریک به برندگان ارسال شد.",
            'lottery_error': "❌ **خطا در اجرای قرعه‌کشی!**\n\n🔹 دلیل: {}\n\nلطفاً موارد زیر را بررسی کنید:\n• تعداد کاربران واجد شرایط\n• تعداد برندگان وارد شده\n• اتصال به دیتابیس",
            'winner_message': "🎉 **تبریک! شما برنده شدید!** 🎉\n\n💰 مبلغ جایزه: **${:,}**\n🏆 شماره قرعه‌کشی: {}\n\n✅ برای برداشت جایزه، روی دکمه زیر کلیک کنید:\n📌 آدرس کیف پول خود را وارد کنید",
            'already_paid': "✅ جایزه شما قبلاً پرداخت شده است!\n\n💰 مبلغ: ${}\n📅 تاریخ: {}",
            'no_winner': "❌ شما برنده‌ای ندارید!\n\nدر قرعه‌کشی‌های بعدی شرکت کنید.",
            'manual_verify_text': "✅ **تایید دستی تراکنش‌ها**\n\n{}\n📊 تعداد کل: {}\n\nبرای تایید هر کاربر، از پنل مدیریت استفاده کنید.",
            'no_pending': "✅ **همه تراکنش‌ها تایید شده‌اند!**\n\nهیچ تراکنش تایید نشده‌ای وجود ندارد.",
            'poll_create': "📊 **ایجاد نظرسنجی جدید**\n\nلطفاً سوال نظرسنجی را ارسال کنید:\n\nمثال: `نظر شما درباره قرعه‌کشی چیست؟`",
            'poll_options': "📊 **گزینه‌های نظرسنجی**\n\nلطفاً گزینه‌های نظرسنجی را وارد کنید (هر گزینه در یک خط):\n\nمثال:\nعالی بود\nخوب بود\nمتوسط\nضعیف",
            'pay_winners_text': "💰 **واریز به برندگان**\n\n{}\n📊 تعداد کل: {}\n\nبرای پرداخت، از پنل مدیریت استفاده کنید.",
            'no_winners': "✅ **همه برندگان پرداخت شده‌اند!**",
            'add_api_text': "🔑 **اضافه کردن API جدید**\n\nلطفاً کلید API جدید را وارد کنید:\n\n⚠️ **نکات:**\n• API برای تایید تراکنش‌ها استفاده می‌شود\n• هر API می‌تواند هزاران کاربر را پوشش دهد\n• API‌های بیشتر = سرعت بیشتر",
            'api_added': "✅ **API جدید با موفقیت اضافه شد!**\n\n🔑 کلید: `{}`\n📊 تعداد کل API‌ها: {}\n\nاین API برای تایید تراکنش‌ها استفاده می‌شود.",
            'api_error': "❌ **خطا در اضافه کردن API!**\n\nاین API قبلاً اضافه شده است یا نامعتبر است.",
            'invalid_command': "⚠️ دستور نامعتبر!\n\nاز دکمه‌های موجود استفاده کنید یا /help را ببینید.",
            'photo_not_supported': "📸 عکس دریافت شد!\nاما این قابلیت پشتیبانی نمی‌شود.",
            'error_message': "⚠️ خطایی رخ داد! لطفاً دوباره تلاش کنید.",
        },
        'tr': {
            'name': 'Türkçe',
            'emoji': '🇹🇷',
            'welcome': "🎮 **UTYOB Piyango Botuna Hoş Geldiniz!**\n\n💰 10.000$'a kadar harika ödüller kazanın!\n🎯 Adil ve şeffaf piyango sistemi\n🌟 Hemen katıl ve şansını dene!\n\nOyuna girmek için PLAY'a tıkla.",
            'play_button': "▶️ PLAY",
            'main_menu': "🎯 **UTYOB Piyango Botu**\n\nAşağıdaki seçeneklerden birini seçin:\n👇👇👇",
            'lottery': "🎰 Piyango",
            'referral': "🔗 Referans ve Arkadaş Davet",
            'guide': "📖 Rehber ve Kurallar",
            'language': "🌐 Dil Değiştir",
            'admin_panel': "⚙️ Yönetim Paneli",
            'no_subscription': "❌ **Aktif aboneliğiniz yok!**\n\nPiyangoya katılmak için önce abonelik satın almalısınız.\n\n💰 Abonelik ücreti: 100$\n📅 Geçerlilik: 1 ay\n\nAbone olmak için aşağıdaki butona tıklayın.",
            'renew_subscription': "🔄 Aboneliği Yenile",
            'back': "🔙 Geri",
            'enter_wallet': "💳 **Piyangoya katılmak için yatırım**\n\nLütfen kaynak cüzdan adresinizi (TRC20) girin:\n\n🔹 **Yatırım tutarı:** 100$\n🔹 **Hedef adres:**\n`{}`\n\n⚠️ **Önemli notlar:**\n• Sadece TRC20 ağını kullanın\n• Tutar tam olarak 100$ olmalı\n• Sistem otomatik olarak doğrulayacak\n• Takip için işlem kimliğini kaydedin\n\n📤 **Kaynak adresinizi girin:**",
            'confirm_payment': "✅ Ödemeyi Onayla",
            'cancel': "❌ İptal",
            'verifying': "⏳ Ödemeniz kontrol ediliyor...\nLütfen bir dakika bekleyin.",
            'payment_success': "✅ **Ödemeniz doğrulandı!**\n\n🔹 Tutar: ${}\n🔹 İşlem: `{}`\n\n🎉 Piyangoya başarıyla kaydoldunuz.\n🙏 İyi şanslar!",
            'payment_failed': "❌ **Ödeme doğrulaması başarısız!**\n\n🔹 Sebep: {}\n\n📌 **Çözümler:**\n1. Tutar tam olarak 100$ olmalı\n2. Hedef adres doğru olmalı\n3. İşlem tamamlanmış olmalı\n4. TRC20 ağını kullanın\n\n🔄 Kontrol ettikten sonra tekrar deneyin.",
            'retry': "🔄 Tekrar Dene",
            'support': "📞 Destek",
            'main_menu_btn': "🔙 Ana Menü",
            'lottery_back': "🎰 Piyangoya Dön",
            'withdraw_prize': "💰 Ödülü Çek",
            'next_lottery': "🎰 Sonraki Piyango",
            'enter_withdraw_wallet': "💰 **Ödülü Çek**\n\nÖdül tutarı: **${:,}**\n\nLütfen TRC20 cüzdan adresinizi girin:\n\n⚠️ **Önemli notlar:**\n• Sadece TRC20 ağını kullanın\n• Adres doğru ve tam olmalı\n• Onaydan sonra ödeme yapılacak\n\n📤 **Cüzdan adresinizi girin:**",
            'withdraw_success': "✅ **Çekim başarıyla kaydedildi!** 🎉\n\n💰 Tutar: ${:,}\n📤 Adres: {}\n\n⏳ Tutar yakında hesabınıza gönderilecek.\n🔔 Gönderildiğinde bilgilendirileceksiniz.",
            'referral_text': "🔗 **UTYOB Referans Sistemi**\n\n👤 Siz: {}\n📊 Davetler: {}\n\n🔑 **Referans kodunuz:**\n`{}`\n\n🔗 **Referans linki:**\n{}\n\n💰 **Referans ödülü:**\n• Her davet için %5 yatırım\n• Doğrulama sonrası anında ödül\n\n📤 Bu linki arkadaşlarınızla paylaşın!",
            'share': "📤 Paylaş",
            'guide_text': "📖 **UTYOB Bot Tam Rehber**\n\n🎯 **Nasıl çalışır:**\n1. **Kayıt**: /start ile kaydolun\n2. **Abonelik**: Katılmak için abonelik satın alın\n3. **Yatırım**: Belirtilen adrese 100$ gönderin\n4. **Katılım**: Doğrulama sonrası piyangoya katılın\n5. **Kazanç**: Kazanırsanız ödülü alın\n\n💰 **Yatırım tutarı:**\n- Sabit tutar: 100$\n- Yatırım adresi: TV61aTh98MGqmteYzda5AaBzdXgGqreG6A\n- Ağ: TRC20\n\n🎁 **Ödüller:**\n- 1. ödül: Toplamın %50'si\n- 2. ödül: Toplamın %30'u\n- 3. ödül: Toplamın %20'si\n\n🔗 **Referans sistemi:**\n- Her kullanıcının benzersiz referans kodu vardır\n- Davet başına %5 ödül\n\n⚠️ **Kurallar:**\n- Her piyangoda kullanıcı başına bir katılım\n- Önceki kazananların şansı daha düşük\n- Tüm işlemler otomatik doğrulanır\n\n📞 **Destek:**\nSorularınız için yöneticiye başvurun.",
            'language_selector': "🌐 **Dil Değiştir**\n\nMevcut dil: {}",
            'admin_stats': "📈 **Sistem İstatistikleri**\n\n👥 **Kullanıcılar:**\n• Toplam: {:,}\n• Aktif: {:,}\n• Aktif oran: {:.1f}%\n\n💳 **İşlemler:**\n• Toplam: {:,}\n• Doğrulanan: {:,}\n• Bekleyen: {:,}\n\n🎰 **Piyango:**\n• Toplam: {}\n• Toplam kazanan: {}\n• Son: {}\n\n⚡ **Sistem:**\n• Önbellek: {} öğe\n• İsabet oranı: {:.1f}%\n• API'ler: {}\n• Parçalar: {}",
            'refresh': "🔄 Yenile",
            'admin_panel_text': "⚙️ **Yönetim Paneli**\n\n📊 **İstatistikler:**\n• Toplam kullanıcı: {:,}\n• Aktif kullanıcı: {:,}\n• Önbellek: {} öğe\n• API'ler: {}\n\nSeçenek seçin:",
            'broadcast': "📢 Toplu Mesaj Gönder",
            'start_lottery': "🎰 Piyangoyu Başlat",
            'manual_verify': "✅ Manuel Doğrula",
            'poll': "📊 Anket Gönder",
            'pay_winners': "💰 Kazananlara Öde",
            'add_api': "🔑 Yeni API Ekle",
            'stats': "📈 İstatistikler",
            'lottery_confirm': "🎰 **Yeni Piyango Başlat**\n\n👥 Uygun kullanıcılar: {} kullanıcı\n\nPiyangoyu başlatmak istediğinize emin misiniz?\n\n⚠️ **Not:**\n• Tüm abone kullanıcılar katılır\n• Önceki kazananların şansı daha düşük\n• Piyango adil ve şeffaftır",
            'confirm': "✅ Onayla",
            'enter_winners': "🎯 **Kazanan Sayısı**\n\nLütfen bu piyango için kazanan sayısını girin:\n(Maksimum 100)\n\nÖrnek: `5`",
            'enter_prize': "✅ Kazananlar: {}\n\n💰 **Kazanan Başına Ödül Tutarı**\n\nLütfen her kazanan için ödül tutarını girin:\n(Minimum 10$)\n\nÖrnek: `100`",
            'lottery_final': "✅ **Piyango Bilgileri:**\n\n• Kazananlar: {}\n• Kazanan başına ödül: ${:,}\n• Toplam ödül: ${:,}\n\n⚠️ Piyangoyu başlatmak istediğinize emin misiniz?",
            'lottery_success': "✅ **Piyango başarıyla tamamlandı!** 🎉\n\n📊 **Detaylar:**\n• Piyango ID: {}\n• Kazananlar: {}\n• Kazanan başına ödül: ${:,}\n• Toplam ödül: ${:,}\n\n👥 **Kazananlar:**\n{}\n\n✅ Kazananlara tebrik mesajları gönderildi.",
            'lottery_error': "❌ **Piyango başlatma hatası!**\n\n🔹 Sebep: {}\n\nLütfen kontrol edin:\n• Uygun kullanıcı sayısı\n• Girilen kazanan sayısı\n• Veritabanı bağlantısı",
            'winner_message': "🎉 **Tebrikler! Kazandınız!** 🎉\n\n💰 Ödül tutarı: **${:,}**\n🏆 Piyango ID: {}\n\n✅ Ödülünüzü çekmek için aşağıdaki butona tıklayın:\n📌 Cüzdan adresinizi girin",
            'already_paid': "✅ Ödül zaten ödendi!\n\n💰 Tutar: ${}\n📅 Tarih: {}",
            'no_winner': "❌ Hiç ödülünüz yok!\n\nGelecek piyangolara katılın.",
            'manual_verify_text': "✅ **Manuel İşlem Doğrulama**\n\n{}\n📊 Toplam: {}\n\nHer kullanıcıyı doğrulamak için yönetim panelini kullanın.",
            'no_pending': "✅ **Tüm işlemler doğrulandı!**\n\nBekleyen işlem yok.",
            'poll_create': "📊 **Yeni Anket Oluştur**\n\nLütfen anket sorusunu gönderin:\n\nÖrnek: `Piyango hakkında ne düşünüyorsunuz?`",
            'poll_options': "📊 **Anket Seçenekleri**\n\nLütfen anket seçeneklerini girin (her satıra bir seçenek):\n\nÖrnek:\nMükemmel\nİyi\nOrta\nKötü",
            'pay_winners_text': "💰 **Kazananlara Öde**\n\n{}\n📊 Toplam: {}\n\nÖdemeleri işlemek için yönetim panelini kullanın.",
            'no_winners': "✅ **Tüm kazananlara ödendi!**",
            'add_api_text': "🔑 **Yeni API Ekle**\n\nLütfen yeni API anahtarını girin:\n\n⚠️ **Notlar:**\n• API işlem doğrulama için kullanılır\n• Her API binlerce kullanıcıyı işleyebilir\n• Daha fazla API = Daha hızlı",
            'api_added': "✅ **Yeni API başarıyla eklendi!**\n\n🔑 Anahtar: `{}`\n📊 Toplam API'ler: {}\n\nBu API işlem doğrulama için kullanılacak.",
            'api_error': "❌ **API ekleme hatası!**\n\nBu API zaten mevcut veya geçersiz.",
            'invalid_command': "⚠️ Geçersiz komut!\n\nButonları veya /help kullanın.",
            'photo_not_supported': "📸 Fotoğraf alındı!\nAncak bu özellik desteklenmiyor.",
            'error_message': "⚠️ Bir hata oluştu! Lütfen tekrar deneyin.",
        }
    }
    
    DEFAULT_LANG = 'en'
    
    @classmethod
    def get_text(cls, lang_code: str, key: str, *args, **kwargs) -> str:
        """دریافت متن به زبان مورد نظر"""
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
        """دریافت نام زبان"""
        return cls.LANGUAGES.get(lang_code, {}).get('name', 'English')
    
    @classmethod
    def get_language_emoji(cls, lang_code: str) -> str:
        """دریافت ایموجی زبان"""
        return cls.LANGUAGES.get(lang_code, {}).get('emoji', '🇬🇧')

# ============================================================
# دیتابیس با ۱۰۰ شارد
# ============================================================
class DatabaseManager:
    def __init__(self, num_shards=DB_SHARDS):
        self.num_shards = num_shards
        self.connections = {}
        self.locks = {}
        self._init_shards()
        
    def _init_shards(self):
        os.makedirs("data", exist_ok=True)
        for i in range(self.num_shards):
            db_path = f"data/shard_{i}.db"
            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            self.connections[i] = conn
            self.locks[i] = threading.Lock()
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
    def __init__(self):
        self.cache = {}
        self.expiry = {}
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        
    def set(self, key, value, ttl=CACHE_TTL):
        with self.lock:
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
                
    def get_stats(self):
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'size': len(self.cache)
            }

cache = CacheManager()

# ============================================================
# سیستم تایید پرداخت
# ============================================================
class PaymentVerifier:
    def __init__(self):
        self.apis = TRONGRID_APIS.copy()
        self.api_stats = {api: {'requests': 0, 'success': 0, 'errors': 0, 'last_reset': time.time()} for api in self.apis}
        self.lock = threading.Lock()
        self.session = None
        
    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=100, limit_per_host=20)
            )
        return self.session
        
    async def verify_transaction(self, from_address, to_address, amount, tx_id=None):
        session = await self.get_session()
        
        if tx_id:
            return await self._verify_by_txid(session, tx_id, from_address, to_address, amount)
        return await self._search_transactions(session, from_address, to_address, amount)
        
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
                    else:
                        self._update_api_stats(api, False)
            except Exception as e:
                logger.error(f"API error for {api}: {e}")
                self._update_api_stats(api, False)
        return False, None, "Transaction not found or invalid"
        
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
                    else:
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
        self.lock = threading.Lock()
        
    def start_lottery(self, winners_count, prize_per_winner):
        with self.lock:
            if self.is_running:
                return False, "Lottery is already running"
                
            eligible_users = self._get_eligible_users()
            
            if not eligible_users:
                return False, "No eligible users found"
                
            if len(eligible_users) < winners_count:
                return False, f"Eligible users ({len(eligible_users)}) less than winners ({winners_count})"
                
            winners = self._smart_select_winners(eligible_users, winners_count)
            
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
        
    def _smart_select_winners(self, eligible_users, winners_count):
        weighted_users = []
        for user_id in eligible_users:
            weight = self._calculate_user_weight(user_id)
            if weight > 0:
                weighted_users.extend([user_id] * weight)
                
        if not weighted_users:
            return random.sample(eligible_users, min(winners_count, len(eligible_users)))
            
        if len(weighted_users) < winners_count:
            return random.sample(eligible_users, min(winners_count, len(eligible_users)))
            
        selected = []
        temp_users = weighted_users.copy()
        
        for _ in range(min(winners_count, len(set(temp_users)))):
            if not temp_users:
                break
            winner = random.choice(temp_users)
            temp_users = [u for u in temp_users if u != winner]
            selected.append(winner)
            
        return selected
        
    def _calculate_user_weight(self, user_id):
        try:
            cursor = db.execute(user_id,
                """SELECT total_participations, wins_count, last_win_date 
                   FROM users WHERE user_id = ?""",
                (user_id,)
            )
            user_data = cursor.fetchone()
            
            if not user_data:
                return 1
                
            weight = 1
            
            if user_data['total_participations'] > 0:
                weight += min(user_data['total_participations'] / 5, 3)
                
            if user_data['wins_count'] > 0:
                weight = max(1, weight - user_data['wins_count'] * 0.5)
                
            if user_data['last_win_date']:
                try:
                    last_win = datetime.strptime(user_data['last_win_date'], '%Y-%m-%d')
                    days_since_win = (datetime.now() - last_win).days
                    if days_since_win < 3:
                        weight *= 0.3
                    elif days_since_win < 7:
                        weight *= 0.6
                except:
                    pass
                    
            return max(1, int(weight))
            
        except Exception as e:
            logger.error(f"Error calculating weight for {user_id}: {e}")
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
# سیستم مدیریت کاربران
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
                       (user_id, username, first_name, last_name, referral_code) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, username, first_name, last_name, referral_code)
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error registering user {user_id}: {e}")
            return False
            
    @staticmethod
    def _generate_referral_code(user_id):
        import hashlib
        base = f"UTYOB_{user_id}_{time.time()}_{random.randint(1000, 9999)}"
        hash_obj = hashlib.sha256(base.encode())
        return hash_obj.hexdigest()[:10].upper()
        
    @staticmethod
    def get_user(user_id):
        try:
            cursor = db.execute(user_id,
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            return cursor.fetchone()
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
        
        # دستورات عمومی
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
        
        # دکمه‌های قرعه‌کشی
        app.add_handler(CallbackQueryHandler(self.join_lottery_callback, pattern="^join_lottery$"))
        app.add_handler(CallbackQueryHandler(self.verify_payment_callback, pattern="^verify_payment$"))
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
        
        # مدیریت خطاها
        app.add_error_handler(self.error_handler)

    # ============================================================
    # توابع کمکی
    # ============================================================
    
    def _get_user_language(self, user_id):
        """دریافت زبان کاربر از دیتابیس"""
        user = user_manager.get_user(user_id)
        if user and user['language']:
            return user['language']
        return 'en'
    
    def _set_user_language(self, user_id, lang_code):
        """تنظیم زبان کاربر"""
        if lang_code in LanguageManager.LANGUAGES:
            user_manager.update_user(user_id, language=lang_code)
            return True
        return False
    
    def _get_text(self, user_id, key, *args, **kwargs):
        """دریافت متن به زبان کاربر"""
        lang = self._get_user_language(user_id)
        return LanguageManager.get_text(lang, key, *args, **kwargs)
    
    def _validate_wallet_address(self, address):
        """اعتبارسنجی آدرس کیف پول TRC20"""
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
    
    async def _auto_verify_payment(self, user_id, from_address, to_address, amount):
        """تایید خودکار پرداخت"""
        try:
            # بررسی کش
            cache_key = f"payment_{from_address}_{to_address}_{amount}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # تایید با سیستم پرداخت
            success, tx_id, message = await payment_verifier.verify_transaction(
                from_address, to_address, amount
            )
            
            if success:
                # ثبت تراکنش موفق
                db.execute(user_id,
                    """INSERT INTO transactions 
                       (user_id, from_address, to_address, amount, tx_id, status, verified_at) 
                       VALUES (?, ?, ?, ?, ?, 'verified', CURRENT_TIMESTAMP)""",
                    (user_id, from_address, to_address, amount, tx_id)
                )
                
                # به‌روزرسانی کاربر
                db.execute(user_id,
                    "UPDATE users SET total_participations = total_participations + 1 WHERE user_id = ?",
                    (user_id,)
                )
                
                result = {
                    'success': True,
                    'tx_id': tx_id,
                    'message': 'Verified'
                }
            else:
                # ثبت تراکنش ناموفق
                db.execute(user_id,
                    """INSERT INTO transactions 
                       (user_id, from_address, to_address, amount, status) 
                       VALUES (?, ?, ?, ?, 'failed')""",
                    (user_id, from_address, to_address, amount)
                )
                
                result = {
                    'success': False,
                    'tx_id': None,
                    'message': message or 'Verification failed'
                }
            
            # ذخیره در کش
            cache.set(cache_key, result, ttl=60)
            return result
            
        except Exception as e:
            logger.error(f"Error in auto verify payment: {e}")
            return {
                'success': False,
                'tx_id': None,
                'message': str(e)
            }
    
    def _get_pending_transactions(self):
        """دریافت تراکنش‌های تایید نشده"""
        results = db.execute_global(
            "SELECT * FROM transactions WHERE status = 'pending' OR status = 'failed'"
        )
        return results
    
    def _get_unpaid_winners(self):
        """دریافت برندگان پرداخت نشده"""
        results = db.execute_global(
            "SELECT * FROM winners WHERE paid_status = 0"
        )
        return results
    
    def _check_winner(self, user_id):
        """بررسی برنده بودن کاربر"""
        cursor = db.execute(user_id,
            """SELECT * FROM winners 
               WHERE user_id = ? 
               AND paid_status = 0 
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,)
        )
        return cursor.fetchone()
    
    def _get_transaction_stats(self):
        """آمار تراکنش‌ها"""
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
        """آمار قرعه‌کشی"""
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
        """دریافت مبلغ جایزه برنده"""
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
        """دستور /start"""
        user = update.effective_user
        
        # ثبت کاربر
        user_manager.register_user(
            user.id,
            user.username,
            user.first_name,
            user.last_name
        )
        
        # زبان پیش‌فرض انگلیسی
        lang = self._get_user_language(user.id)
        
        # دکمه پلی
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
        """دستور /help"""
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
        """دستور /referral"""
        user_id = update.effective_user.id
        await self._show_referral(update, user_id)
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /language"""
        user_id = update.effective_user.id
        await self._show_language_selector(update, user_id)
    
    async def _show_referral(self, update, user_id):
        """نمایش اطلاعات رفرال"""
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
        """نمایش انتخابگر زبان"""
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
    
    async def set_language_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیم زبان کاربر"""
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
    # کالبک‌های منوی اصلی
    # ============================================================
    
    async def main_menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی اصلی"""
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
        """مدیریت قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if not user or not user['has_subscription']:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'renew_subscription'),
                    callback_data="main_menu"
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
            f"👤 {LanguageManager.get_text(lang, 'user', lang=lang)}: {user['first_name'] or user_id}\n\n"
            f"💰 {LanguageManager.get_text(lang, 'prize', lang=lang)}: Up to $10,000\n"
            f"🎯 {LanguageManager.get_text(lang, 'fair', lang=lang)}: Yes",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def referral_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش اطلاعات رفرال"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        await self._show_referral(update, user_id)
    
    async def guide_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش راهنمایی"""
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
        """تغییر زبان"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        await self._show_language_selector(update, user_id)

    # ============================================================
    # کالبک‌های شرکت در قرعه‌کشی
    # ============================================================
    
    async def join_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شرکت در قرعه‌کشی - دریافت آدرس کیف پول"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        user = user_manager.get_user(user_id)
        if not user or not user['has_subscription']:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_subscription'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # ذخیره وضعیت برای دریافت آدرس
        context.user_data['waiting_for_wallet'] = True
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'confirm_payment'),
                callback_data="verify_payment"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'cancel'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'enter_wallet', DESTINATION_WALLET),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def verify_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بررسی و تایید پرداخت"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if not context.user_data.get('waiting_for_wallet'):
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⚠️ " + LanguageManager.get_text(lang, 'enter_wallet', DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
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
                "❌ " + LanguageManager.get_text(lang, 'enter_wallet', DESTINATION_WALLET),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # نمایش پیام در حال بررسی
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'verifying'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # تایید خودکار پرداخت
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
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        chat_id=admin_id,
                        text=f"✅ Payment verified!\nUser: {user_id}\nAmount: ${PAYMENT_AMOUNT}\nTx: {result['tx_id']}"
                    )
                except:
                    pass
        else:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'retry'),
                    callback_data="join_lottery"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'support'),
                    callback_data="main_menu"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'main_menu_btn'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'payment_failed', result['message']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        chat_id=admin_id,
                        text=f"⚠️ Payment failed!\nUser: {user_id}\nFrom: {user['wallet_address']}\nReason: {result['message']}"
                    )
                except:
                    pass
    
    async def confirm_payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید نهایی پرداخت"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'verifying'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await self.verify_payment_callback(update, context)

    # ============================================================
    # کالبک‌های پنل مدیریت
    # ============================================================
    
    async def admin_panel_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل مدیریت"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⛔ Access Denied!",
                reply_markup=reply_markup
            )
            return
        
        user_count = user_manager.get_user_count()
        active_users = len(user_manager.get_active_users())
        cache_stats = cache.get_stats()
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'broadcast'),
                callback_data="admin_broadcast"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'start_lottery'),
                callback_data="admin_start_lottery"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'manual_verify'),
                callback_data="admin_manual_verify"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'poll'),
                callback_data="admin_poll"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'pay_winners'),
                callback_data="admin_pay_winners"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'add_api'),
                callback_data="admin_add_api"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'stats'),
                callback_data="admin_stats"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="main_menu"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'admin_panel_text',
                user_count, active_users, cache_stats['size'], len(payment_verifier.apis)
            ),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال پیام همگانی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['admin_action'] = 'broadcast'
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="admin_panel"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📢 **Send Broadcast Message**\n\n"
            "Please send the message text:\n\n"
            "⚠️ This will be sent to ALL users.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_start_lottery_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        if lottery_system.is_running:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="admin_panel"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⚠️ Lottery is already running!",
                reply_markup=reply_markup
            )
            return
        
        context.user_data['admin_action'] = 'start_lottery'
        context.user_data['lottery_step'] = 1
        
        eligible = lottery_system._get_eligible_users()
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'confirm'),
                callback_data="start_lottery_confirm"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'cancel'),
                callback_data="admin_panel"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'lottery_confirm', len(eligible)),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_manual_verify_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید دستی کاربران"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        transactions = self._get_pending_transactions()
        
        if not transactions:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="admin_panel"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_pending'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = ""
        for tx in transactions[:10]:
            text += f"👤 User: {tx['user_id']}\n"
            text += f"💰 Amount: ${tx['amount']}\n"
            text += f"📤 From: {tx['from_address']}\n\n"
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="admin_panel"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'manual_verify_text', text, len(transactions)),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_poll_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال نظرسنجی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['admin_action'] = 'create_poll'
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="admin_panel"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'poll_create'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_pay_winners_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """واریز به برندگان"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        winners = self._get_unpaid_winners()
        
        if not winners:
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="admin_panel"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'no_winners'),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        text = ""
        for winner in winners[:10]:
            text += f"👤 User: {winner['user_id']}\n"
            text += f"💰 Amount: ${winner['prize_amount']}\n"
            text += f"📤 Address: {winner['wallet_address'] or 'Unknown'}\n\n"
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="admin_panel"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'pay_winners_text', text, len(winners)),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_add_api_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اضافه کردن API جدید"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['admin_action'] = 'add_api'
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="admin_panel"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'add_api_text'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin_stats_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار کامل"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        user_count = user_manager.get_user_count()
        active_users = len(user_manager.get_active_users())
        cache_stats = cache.get_stats()
        tx_stats = self._get_transaction_stats()
        lottery_stats = self._get_lottery_stats()
        
        keyboard = [
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'refresh'),
                callback_data="admin_stats"
            )],
            [InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="admin_panel"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'admin_stats',
                user_count,
                active_users,
                (active_users/user_count*100) if user_count > 0 else 0,
                tx_stats['total'],
                tx_stats['verified'],
                tx_stats['pending'],
                lottery_stats['total'],
                lottery_stats['total_winners'],
                lottery_stats['last'] or 'None',
                cache_stats['size'],
                cache_stats['hit_rate'],
                len(payment_verifier.apis),
                DB_SHARDS
            ),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    # ============================================================
    # کالبک‌های مراحل قرعه‌کشی
    # ============================================================
    
    async def start_lottery_confirm_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تایید شروع قرعه‌کشی - دریافت تعداد برندگان"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        context.user_data['lottery_step'] = 2
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="admin_panel"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            LanguageManager.get_text(lang, 'enter_winners'),
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def start_lottery_final_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مرحله نهایی شروع قرعه‌کشی"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        lang = self._get_user_language(user_id)
        
        if user_id not in ADMIN_IDS:
            return
        
        winners_count = context.user_data.get('lottery_winners', 1)
        prize_per_winner = context.user_data.get('lottery_prize', 100)
        
        success, result = lottery_system.start_lottery(winners_count, prize_per_winner)
        
        if success:
            # ارسال پیام به برندگان
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
                        text=LanguageManager.get_text(winner_lang, 'winner_message',
                            prize_per_winner, result['lottery_id']
                        ),
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Error sending to {winner_id}: {e}")
            
            winners_list = "\n".join([f"• User {uid}" for uid in result['winners']])
            
            keyboard = [[InlineKeyboardButton(
                LanguageManager.get_text(lang, 'back'),
                callback_data="admin_panel"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'lottery_success',
                    result['lottery_id'],
                    winners_count,
                    prize_per_winner,
                    winners_count * prize_per_winner,
                    winners_list
                ),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'retry'),
                    callback_data="admin_start_lottery"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'back'),
                    callback_data="admin_panel"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                LanguageManager.get_text(lang, 'lottery_error', result),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

    # ============================================================
    # کالبک‌های برداشت جایزه
    # ============================================================
    
    async def withdraw_prize_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """برداشت جایزه"""
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
                LanguageManager.get_text(lang, 'confirm_payment'),
                callback_data="confirm_withdraw"
            )],
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
        """تایید برداشت"""
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
            
            # اطلاع به ادمین
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
        """مدیریت پیام‌های دریافتی"""
        user_id = update.effective_user.id
        text = update.message.text
        lang = self._get_user_language(user_id)
        
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
        
        elif admin_action == 'create_poll':
            await self._handle_create_poll(update, text, context)
            return
        
        # بررسی انتظار برای آدرس کیف پول
        if context.user_data.get('waiting_for_wallet'):
            await self._handle_wallet_address(update, text, context)
            return
        
        # بررسی انتظار برای آدرس برداشت
        if context.user_data.get('withdraw_pending'):
            await self._handle_withdraw_address(update, text, context)
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
    
    async def _handle_wallet_address(self, update, text, context):
        """مدیریت آدرس کیف پول برای شرکت در قرعه‌کشی"""
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        wallet_address = text.strip()
        
        if not self._validate_wallet_address(wallet_address):
            await update.message.reply_text(
                "❌ Invalid wallet address!\n\n"
                "Please enter a valid TRC20 address.\n"
                "Example: `TV61aTh98MGqmteYzda5AaBzdXgGqreG6A`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # ذخیره آدرس
        user_manager.update_user(user_id, wallet_address=wallet_address)
        context.user_data['waiting_for_wallet'] = False
        
        # نمایش پیام در حال بررسی
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'verifying'),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # تایید خودکار پرداخت
        result = await self._auto_verify_payment(
            user_id,
            wallet_address,
            DESTINATION_WALLET,
            PAYMENT_AMOUNT        )
        
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
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'payment_success', PAYMENT_AMOUNT, result['tx_id']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            keyboard = [
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'retry'),
                    callback_data="join_lottery"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'support'),
                    callback_data="main_menu"
                )],
                [InlineKeyboardButton(
                    LanguageManager.get_text(lang, 'main_menu_btn'),
                    callback_data="main_menu"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'payment_failed', result['message']),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_withdraw_address(self, update, text, context):
        """مدیریت آدرس برای برداشت جایزه"""
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        wallet_address = text.strip()
        
        if not self._validate_wallet_address(wallet_address):
            await update.message.reply_text(
                "❌ Invalid wallet address!\n\n"
                "Please enter a valid TRC20 address.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # ذخیره آدرس
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
            
            # اطلاع به ادمین
            for admin_id in ADMIN_IDS:
                try:
                    await self.application.bot.send_message(
                        chat_id=admin_id,
                        text=f"💰 Withdrawal request\nUser: {user_id}\nAmount: ${await self._get_winner_amount(user_id)}\nAddress: {wallet_address}"
                    )
                except:
                    pass
    
    async def _handle_lottery_steps(self, update, text, context):
        """مدیریت مراحل شروع قرعه‌کشی"""
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
                        LanguageManager.get_text(lang, 'enter_prize', winners_count),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        "❌ Invalid number!\nPlease enter a number between 1 and 100."
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ Please enter a valid number!"
                )
        
        elif step == 3:
            try:
                prize = float(text)
                if prize >= 10:
                    context.user_data['lottery_prize'] = prize
                    context.user_data['lottery_step'] = 4
                    
                    winners = context.user_data['lottery_winners']
                    total_prize = winners * prize
                    
                    keyboard = [
                        [InlineKeyboardButton(
                            LanguageManager.get_text(lang, 'confirm'),
                            callback_data="start_lottery_final"
                        )],
                        [InlineKeyboardButton(
                            LanguageManager.get_text(lang, 'cancel'),
                            callback_data="admin_panel"
                        )]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        LanguageManager.get_text(lang, 'lottery_final',
                            winners, prize, total_prize
                        ),
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        "❌ Prize amount must be at least $10!"
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ Please enter a valid number!"
                )
    
    async def _handle_add_api(self, update, text, context):
        """اضافه کردن API جدید"""
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        api_key = text.strip()
        
        if payment_verifier.add_api(api_key):
            context.user_data['admin_action'] = None
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'api_added',
                    api_key, len(payment_verifier.apis)
                ),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                LanguageManager.get_text(lang, 'api_error'),
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_create_poll(self, update, text, context):
        """ایجاد نظرسنجی"""
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        context.user_data['poll_question'] = text
        context.user_data['poll_step'] = 2
        
        await update.message.reply_text(
            LanguageManager.get_text(lang, 'poll_options'),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _send_broadcast(self, update, text, context):
        """ارسال پیام همگانی"""
        user_id = update.effective_user.id
        lang = self._get_user_language(user_id)
        
        await update.message.reply_text(
            "⏳ Sending broadcast...\nPlease wait.",
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
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error sending to {user['user_id']}: {e}")
                failed += 1
        
        context.user_data['admin_action'] = None
        
        keyboard = [[InlineKeyboardButton(
            LanguageManager.get_text(lang, 'back'),
            callback_data="admin_panel"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Broadcast complete!\n\n"
            f"📤 Sent: {sent:,}\n"
            f"❌ Failed: {failed:,}\n"
            f"📊 Total: {sent + failed:,}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت عکس‌ها"""
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
        """مدیریت خطاها"""
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