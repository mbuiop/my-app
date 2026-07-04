import asyncio
import logging
import sqlite3
import json
import hashlib
import secrets
import aiohttp
import time
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Set, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections import OrderedDict
from heapq import heappush, heappop
import base58
import random
from threading import Lock
import zlib
import pickle
import os
import gc
import psutil
import resource
import string

# ==================== تنظیمات سیستم ====================
try:
    resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
except:
    pass

# ==================== importهای telegram ====================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
# =========================================================

# ==================== تنظیمات لاگینگ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== تنظیمات اصلی ====================
BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
ADMIN_ID = 327855654
OWNER_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"

TRON_API_KEYS = [
    "7ae83b63-fdf3-47e4-ac69-56f960a34f5b",
]

TRON_API_URL = "https://api.trongrid.io"
SUBSCRIPTION_PRICE_USD = 50
MAX_YOUTUBE_LINKS_PER_WEEK = 1  # هفته ای ۱ لینک
DAILY_INTERACTIONS_REQUIRED_MIN = 5  # حداقل ۵ تعامل
DAILY_INTERACTIONS_REQUIRED_MAX = 10  # حداکثر ۱۰ تعامل
PAYMENT_TIMEOUT_MINUTES = 10
REFERRAL_CHALLENGE_REWARD = 100
REFERRAL_CHALLENGE_TOP_USERS = 10
MAX_CONCURRENT_TASKS = 1000
CACHE_TTL = 300
CACHE_MAX_SIZE = 5_000_000
REFERRAL_BOOST_THRESHOLD = 100
REFERRAL_BOOST_MULTIPLIER = 2

# ==================== تنظیمات برند ====================
BRAND_NAME = ""  # اسم برند (خالی = بدون برند)
BRAND_PREFIX = "@UTYOB_Bot"  # پیشوند ربات

# ==================== تنظیمات الگوریتم چرخشی ====================
DAILY_PROMOTION_RATIO = 0.1  # ۱۰٪ از لینک‌ها روزانه تبلیغ می‌شوند
MIN_PROMOTION_PER_DAY = 100  # حداقل ۱۰۰ لینک در روز
MAX_PROMOTION_PER_DAY = 100000  # حداکثر ۱۰۰,۰۰۰ لینک در روز

# ==================== تنظیمات کد یکتا ====================
UNIQUE_CODE_LENGTH = 12
UNIQUE_CODE_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits

# ==================== ۵ زبان پشتیبانی شده ====================
SUPPORTED_LANGUAGES = {
    'fa': 'فارسی',
    'en': 'English',
    'ar': 'العربية',
    'ru': 'Русский',
    'tr': 'Türkçe'
}

# ==================== متون کامل ۵ زبان ====================
TEXTS = {
    'fa': {
        'welcome': "👋 خوش آمدید <b>{first_name}</b>!\n\n🎯 ربات تبادل بازدید و لایک یوتیوب\n📌 لینک ویدیوهای خود را ثبت کنید و درآمد کسب کنید",
        'register_link': "📝 ثبت لینک یوتیوب",
        'my_stats': "📊 آمار من",
        'referral': "👥 سیستم رفرال",
        'change_language': "🌐 تغییر زبان",
        'view_links': "👀 مشاهده لینک‌های دیگران",
        'register_link_prompt': "📤 لطفا لینک ویدیو یوتیوب خود را ارسال کنید:\n\n⚠️ هفته‌ای فقط <b>۱</b> لینک می‌توانید ثبت کنید\n🔑 کد یکتا هفته: <code>{unique_code}</code>\n\n📌 این کد را روی ویدیو خود بنویسید و بعد از آپلود، لینک را ارسال کنید",
        'link_registered': "✅ لینک شما با موفقیت ثبت شد!\n\n📌 لطفا <b>{count}</b> لینک دیگران را بازدید و لایک کنید\n🔑 برای هر لینک، کد یکتا آن را وارد کنید",
        'interaction_prompt': "👀 لطفا این {count} لینک را بازدید و لایک کنید:\n\n{links}\n\n🔑 کدهای یکتا هر لینک را بعد از بازدید وارد کنید:",
        'enter_unique_code': "📤 لطفا کد یکتای ویدیویی که بازدید کردید را وارد کنید:",
        'unique_code_invalid': "❌ کد یکتا نامعتبر است!\nلطفا کد صحیح را وارد کنید.",
        'unique_code_success': "✅ بازدید با موفقیت ثبت شد!\n🎉 شما ۱ تعامل انجام دادید.",
        'interaction_complete': "✅ شما {count}/{required} تعامل امروز را انجام دادید!\n🎉 لینک‌های شما در تبادل ثبت شدند",
        'not_enough_interactions': "❌ شما امروز {count} تعامل از {required} تعامل مورد نیاز را انجام داده‌اید.\nلطفا ابتدا تعاملات خود را کامل کنید.",
        'referral_info': "👥 **سیستم رفرال شما**\n\n🔗 **کد رفرال شما:**\n<code>{ref_code}</code>\n\n👤 **تعداد رفرال‌ها:** {ref_count} کاربر\n🎯 **رفرال مورد نیاز:** {required_ref}\n\n📋 **لینک دعوت:**\n<code>{ref_link}</code>\n\n📤 روی دکمه زیر کلیک کنید تا کپی شود:",
        'referral_link': "https://t.me/SEGNALF_bot?start={ref_code}",
        'referral_copied': "✅ کد رفرال کپی شد!\n\n📋 کد: <code>{ref_code}</code>\n\n📤 این کد را با دوستان خود به اشتراک بگذارید",
        'referral_success': "🎉 **تبریک!**\n\nشما توسط <b>{ref_name}</b> دعوت شدید!\n✅ رفرال شما با موفقیت ثبت شد\n🎁 هر دو نفر شما از این دعوت سود می‌برید",
        'referral_not_found': "❌ کد رفرال نامعتبر است",
        'subscribed': "✅ اشتراک شما تا تاریخ {expiry} فعال است",
        'not_subscribed': "❌ اشتراک فعالی ندارید\n💳 لطفا مبلغ ۵۰ دلار را پرداخت کنید",
        'payment_info': "💳 لطفا مبلغ <b>۵۰ دلار</b> USDT (TRC20) را به این آدرس ارسال کنید:\n\n<code>{wallet}</code>\n\n📌 ابتدا آدرس مبدا (کیف پول خود) را وارد کنید:",
        'enter_source_address': "📤 لطفا آدرس مبدا (کیف پول خود) را وارد کنید:",
        'source_address_saved': "✅ آدرس مبدا شما ثبت شد!\n\n💳 لطفا مبلغ <b>۵۰ دلار</b> USDT (TRC20) را به آدرس زیر ارسال کنید:\n\n<code>{wallet}</code>\n\n📌 پس از واریز، دکمه زیر را بزنید",
        'payment_confirmed': "✅ تایید پرداخت دریافت شد!\n⏳ در حال بررسی بلاکچین... (حداکثر ۱۰ دقیقه)",
        'payment_success': "✅ پرداخت با موفقیت تایید شد!\n🎉 اشتراک شما فعال شد",
        'payment_failed': "❌ تایید پرداخت ناموفق!\nلطفا دوباره تلاش کنید یا از دکمه ارسال هش استفاده کنید",
        'payment_timeout': "⏰ زمان تایید پرداخت به پایان رسید\nلطفا از دکمه ارسال هش استفاده کنید",
        'send_hash_button': "📤 ارسال هش تراکنش",
        'enter_tx_hash': "📤 لطفا هش تراکنش خود را ارسال کنید:",
        'hash_received': "✅ هش تراکنش شما دریافت شد!\n⏳ فرایند تایید تا ۲۴ ساعت طول می‌کشد",
        'admin_panel': "🛠 پنل مدیریت",
        'make_paid': "💰 پولی کردن ربات",
        'make_free': "🆓 رایگان کردن ربات",
        'broadcast': "📢 ارسال پیام همگانی",
        'verify_payments': "✅ تایید پرداخت‌ها",
        'manage_keys': "🔑 مدیریت کلیدهای API",
        'db_stats': "📊 آمار دیتابیس",
        'brand_settings': "🏷️ تنظیمات برند",
        'set_brand': "✏️ ثبت برند",
        'remove_brand': "🗑️ حذف برند",
        'brand_set': "✅ برند با موفقیت ثبت شد!\n\n🏷️ برند: {brand}\n📌 نمونه کد: <code>{brand} {code}</code>",
        'brand_removed': "✅ برند با موفقیت حذف شد",
        'paid_mode': "💰 ربات به حالت پولی تغییر کرد\nکاربران برای ثبت لینک باید اشتراک خریداری کنند",
        'free_mode': "🆓 ربات به حالت رایگان تغییر کرد\nهمه کاربران می‌توانند بدون اشتراک لینک ثبت کنند",
        'stats_info': "📊 **آمار شما:**\n\n📝 لینک‌های ثبت شده: {total_links}\n👀 تعاملات امروز: {interactions}/{required}\n👥 تعداد رفرال‌ها: {referrals}\n📌 لینک‌های فعال: {active_links}\n🚀 ضریب بازدید: {boost}x\n🔑 کد یکتا هفته: <code>{unique_code}</code>",
        'no_links_to_view': "✅ شما تمام تعاملات امروز را تکمیل کرده‌اید!",
        'interaction_links': "👀 **لینک‌های برای بازدید:**\n\n{links}\n\n🔑 پس از بازدید هر ویدیو، کد یکتا آن را وارد کنید:",
        'view_links_empty': "❌ هیچ لینکی برای بازدید وجود ندارد.",
        'free_register': "✅ در حالت رایگان، می‌توانید بدون اشتراک لینک ثبت کنید",
        'payment_manual_review': "📤 هش شما برای بررسی دستی به ادمین ارسال شد\n⏳ فرایند تایید تا ۲۴ ساعت طول می‌کشد",
        'key_added': "✅ کلید جدید با موفقیت ثبت و فعال شد!",
        'key_add_failed': "❌ ثبت کلید ناموفق! لطفا کلید معتبر ارسال کنید",
        'key_list': "📋 **لیست کلیدهای API**",
        'no_keys': "❌ هیچ کلیدی ثبت نشده است",
        'copy_code': "📋 کپی کد",
        'copy_link': "📋 کپی لینک",
        'referral_challenge': "🏆 **چالش رفرال**\n\nبهترین کاربران با بیشترین رفرال جایزه می‌گیرند!\n🎁 جایزه: {reward} USDT\n👥 تعداد برندگان: {top_users} نفر\n⏳ زمان باقی‌مانده: {time_left}\n\n📊 برای مشاهده رتبه خود روی دکمه زیر کلیک کنید:",
        'referral_rank': "📊 **رتبه شما در چالش رفرال**\n\n👤 شما: {user_ref} رفرال\n🏅 رتبه: #{rank}\n🥇 نفر اول: {first_name} با {first_ref} رفرال\n🥈 نفر دوم: {second_name} با {second_ref} رفرال\n🥉 نفر سوم: {third_name} با {third_ref} رفرال\n\n⏳ زمان باقی‌مانده: {time_left}",
        'you_won': "🎉 **تبریک! شما برنده چالش رفرال شدید!**\n\n🏆 شما جزو {top_users} نفر برتر با {ref_count} رفرال هستید!\n🎁 جایزه شما: {reward} USDT\n\n📤 لطفا آدرس کیف پول TRC20 خود را ارسال کنید:",
        'address_received': "✅ آدرس کیف پول شما دریافت شد!\n⏳ در حال پردازش...\n\n🔗 آدرس: <code>{address}</code>\n💰 مبلغ: {reward} USDT\n\n📌 پس از واریز، ادمین تایید می‌کند.",
        'reward_sent': "✅ **جایزه شما واریز شد!**\n\n💰 مبلغ: {reward} USDT\n🔗 آدرس: <code>{address}</code>\n\n🎉 تبریک می‌گوییم!",
        'challenge_ended': "⏰ **چالش رفرال به پایان رسید!**\n\n🏆 برندگان:\n{winners}\n\n🎁 هر کدام {reward} USDT دریافت می‌کنند.",
        'no_challenge': "❌ در حال حاضر هیچ چالش رفرالی فعال نیست",
        'challenge_started': "🏆 **چالش رفرال شروع شد!**\n\nمدت زمان: {duration} روز\n🎁 جایزه: {reward} USDT\n👥 تعداد برندگان: {top_users} نفر\n\nهر کس رفرال بیشتری بیاورد، برنده می‌شود!",
        'challenge_stopped': "⏹️ چالش رفرال متوقف شد",
        'manage_challenge': "🏆 مدیریت چالش رفرال",
        'start_challenge': "▶️ شروع چالش",
        'stop_challenge': "⏹️ توقف چالش",
        'challenge_status': "📊 وضعیت چالش",
        'reward_winners': "💰 اعلام برندگان و پرداخت",
        'enter_duration': "⏱️ لطفا مدت زمان چالش را به روز وارد کنید (مثلاً 7):",
        'invalid_duration': "❌ عدد نامعتبر! لطفا یک عدد مثبت وارد کنید.",
        'challenge_already_active': "⚠️ چالش رفرال در حال حاضر فعال است!",
        'challenge_not_active': "⚠️ چالش رفرال فعال نیست!",
        'winners_announced': "🏆 **برندگان چالش رفرال اعلام شدند!**\n\n{winners}\n\n🎁 هر کدام {reward} USDT دریافت می‌کنند.\n\n📤 برندگان می‌توانند آدرس کیف پول خود را ارسال کنند.",
        'no_winners': "❌ هیچ برنده‌ای وجود ندارد!",
        'reward_paid': "✅ **جایزه به {count} نفر پرداخت شد!**",
        'challenge_reward_set': "💰 مبلغ جایزه به {amount} USDT تنظیم شد",
        'challenge_top_users_set': "👥 تعداد برندگان به {count} نفر تنظیم شد",
        'new_referral_notification': "🎉 رفرال جدید!\n👤 {name}\n📊 تعداد کل رفرال‌های شما: {count}\n🚀 ضریب بازدید شما: {boost}x",
        'boost_info': "🚀 **ضریب بازدید شما**\n\n👥 تعداد رفرال‌های شما: {ref_count}\n📈 ضریب بازدید: {boost}x\n\n💡 اگر رفرال‌های شما از {threshold} نفر بیشتر شود، ضریب بازدید شما افزایش می‌یابد!"
    },
    'en': {
        'welcome': "👋 Welcome <b>{first_name}</b>!\n\n🎯 YouTube Views & Likes Exchange Bot\n📌 Register your video links and earn",
        'register_link': "📝 Register YouTube Link",
        'my_stats': "📊 My Stats",
        'referral': "👥 Referral System",
        'change_language': "🌐 Change Language",
        'view_links': "👀 View Others' Links",
        'register_link_prompt': "📤 Please send your YouTube video link:\n\n⚠️ You can register <b>1</b> link per week\n🔑 Weekly unique code: <code>{unique_code}</code>\n\n📌 Write this code on your video before uploading",
        'link_registered': "✅ Your link has been successfully registered!\n\n📌 Now view and like <b>{count}</b> other users' links\n🔑 Enter the unique code for each link after viewing",
        'interaction_prompt': "👀 Please view and like these {count} links:\n\n{links}\n\n🔑 Enter the unique code for each link after viewing:",
        'enter_unique_code': "📤 Please enter the unique code of the video you viewed:",
        'unique_code_invalid': "❌ Invalid unique code!\nPlease enter the correct code.",
        'unique_code_success': "✅ View registered successfully!\n🎉 You completed 1 interaction.",
        'interaction_complete': "✅ You completed {count}/{required} interactions today!\n🎉 Your links are now registered in the exchange",
        'not_enough_interactions': "❌ You have {count} interactions out of {required} required today.\nPlease complete your interactions first.",
        'referral_info': "👥 **Your Referral System**\n\n🔗 **Your Referral Code:**\n<code>{ref_code}</code>\n\n👤 **Referrals:** {ref_count} users\n🎯 **Required Referrals:** {required_ref}\n\n📋 **Invite Link:**\n<code>{ref_link}</code>\n\n📤 Click the button below to copy:",
        'referral_link': "https://t.me/SEGNALF_bot?start={ref_code}",
        'referral_copied': "✅ Referral code copied!\n\n📋 Code: <code>{ref_code}</code>\n\n📤 Share this code with your friends",
        'referral_success': "🎉 **Congratulations!**\n\nYou were invited by <b>{ref_name}</b>!\n✅ Your referral has been successfully registered\n🎁 Both of you will benefit from this invitation",
        'referral_not_found': "❌ Invalid referral code",
        'subscribed': "✅ Your subscription is active until {expiry}",
        'not_subscribed': "❌ You don't have an active subscription\n💳 Please pay $50 to activate",
        'payment_info': "💳 Please send <b>$50</b> USDT (TRC20) to this address:\n\n<code>{wallet}</code>\n\n📌 First enter your source wallet address:",
        'enter_source_address': "📤 Please enter your source wallet address:",
        'source_address_saved': "✅ Your source address saved!\n\n💳 Please send <b>$50</b> USDT (TRC20) to this address:\n\n<code>{wallet}</code>\n\n📌 After payment, click the button below",
        'payment_confirmed': "✅ Payment confirmation received!\n⏳ Checking blockchain... (max 10 minutes)",
        'payment_success': "✅ Payment verified successfully!\n🎉 Your subscription is now active",
        'payment_failed': "❌ Payment verification failed!\nPlease try again or use the send hash button",
        'payment_timeout': "⏰ Payment verification timeout\nPlease use the send hash button",
        'send_hash_button': "📤 Send Transaction Hash",
        'enter_tx_hash': "📤 Please send your transaction hash:",
        'hash_received': "✅ Your transaction hash received!\n⏳ Verification process takes up to 24 hours",
        'admin_panel': "🛠 Admin Panel",
        'make_paid': "💰 Make Paid",
        'make_free': "🆓 Make Free",
        'broadcast': "📢 Broadcast",
        'verify_payments': "✅ Verify Payments",
        'manage_keys': "🔑 Manage API Keys",
        'db_stats': "📊 Database Stats",
        'brand_settings': "🏷️ Brand Settings",
        'set_brand': "✏️ Set Brand",
        'remove_brand': "🗑️ Remove Brand",
        'brand_set': "✅ Brand set successfully!\n\n🏷️ Brand: {brand}\n📌 Code example: <code>{brand} {code}</code>",
        'brand_removed': "✅ Brand removed successfully",
        'paid_mode': "💰 Bot changed to paid mode\nUsers must purchase subscription to register links",
        'free_mode': "🆓 Bot changed to free mode\nAll users can register links without subscription",
        'stats_info': "📊 **Your Statistics:**\n\n📝 Registered links: {total_links}\n👀 Today's interactions: {interactions}/{required}\n👥 Referrals: {referrals}\n📌 Active links: {active_links}\n🚀 View boost: {boost}x\n🔑 Weekly code: <code>{unique_code}</code>",
        'no_links_to_view': "✅ You have completed all required interactions for today!",
        'interaction_links': "👀 **Links to view:**\n\n{links}\n\n🔑 After viewing each video, enter its unique code:",
        'view_links_empty': "❌ No links available to view.",
        'free_register': "✅ In free mode, you can register links without subscription",
        'payment_manual_review': "📤 Your hash sent for manual review to admin\n⏳ Verification process takes up to 24 hours",
        'key_added': "✅ New API key successfully registered and activated!",
        'key_add_failed': "❌ Key registration failed! Please send a valid key",
        'key_list': "📋 **API Keys List**",
        'no_keys': "❌ No keys registered",
        'copy_code': "📋 Copy Code",
        'copy_link': "📋 Copy Link",
        'referral_challenge': "🏆 **Referral Challenge**\n\nTop users with most referrals win!\n🎁 Prize: {reward} USDT\n👥 Winners: {top_users}\n⏳ Time left: {time_left}\n\n📊 Click below to see your rank:",
        'referral_rank': "📊 **Your Challenge Rank**\n\n👤 You: {user_ref} referrals\n🏅 Rank: #{rank}\n🥇 1st: {first_name} with {first_ref} referrals\n🥈 2nd: {second_name} with {second_ref} referrals\n🥉 3rd: {third_name} with {third_ref} referrals\n\n⏳ Time left: {time_left}",
        'you_won': "🎉 **Congratulations! You won the Referral Challenge!**\n\n🏆 You are among top {top_users} with {ref_count} referrals!\n🎁 Prize: {reward} USDT\n\n📤 Please send your TRC20 wallet address:",
        'address_received': "✅ Wallet address received!\n⏳ Processing...\n\n🔗 Address: <code>{address}</code>\n💰 Amount: {reward} USDT\n\n📌 Admin will confirm after sending.",
        'reward_sent': "✅ **Reward sent!**\n\n💰 Amount: {reward} USDT\n🔗 Address: <code>{address}</code>\n\n🎉 Congratulations!",
        'challenge_ended': "⏰ **Referral Challenge ended!**\n\n🏆 Winners:\n{winners}\n\n🎁 Each gets {reward} USDT.",
        'no_challenge': "❌ No active referral challenge",
        'challenge_started': "🏆 **Referral Challenge started!**\n\nDuration: {duration} days\n🎁 Prize: {reward} USDT\n👥 Winners: {top_users}\n\nWhoever brings more referrals wins!",
        'challenge_stopped': "⏹️ Referral Challenge stopped",
        'manage_challenge': "🏆 Manage Referral Challenge",
        'start_challenge': "▶️ Start Challenge",
        'stop_challenge': "⏹️ Stop Challenge",
        'challenge_status': "📊 Challenge Status",
        'reward_winners': "💰 Announce & Pay Winners",
        'enter_duration': "⏱️ Please enter challenge duration in days (e.g. 7):",
        'invalid_duration': "❌ Invalid number! Please enter a positive number.",
        'challenge_already_active': "⚠️ Referral challenge is already active!",
        'challenge_not_active': "⚠️ Referral challenge is not active!",
        'winners_announced': "🏆 **Referral Challenge Winners announced!**\n\n{winners}\n\n🎁 Each gets {reward} USDT.\n\n📤 Winners can send their wallet address.",
        'no_winners': "❌ No winners found!",
        'reward_paid': "✅ **Reward paid to {count} users!**",
        'challenge_reward_set': "💰 Prize amount set to {amount} USDT",
        'challenge_top_users_set': "👥 Winners count set to {count}",
        'new_referral_notification': "🎉 New referral!\n👤 {name}\n📊 Total referrals: {count}\n🚀 Your view boost: {boost}x",
        'boost_info': "🚀 **Your View Boost**\n\n👥 Your referrals: {ref_count}\n📈 View boost: {boost}x\n\n💡 If your referrals exceed {threshold}, your boost will increase!"
    },
    'ar': {
        'welcome': "👋 مرحباً <b>{first_name}</b>!\n\n🎯 بوت تبادل مشاهدات وإعجابات يوتيوب\n📌 سجل روابط فيديوهاتك واربح",
        'register_link': "📝 تسجيل رابط يوتيوب",
        'my_stats': "📊 إحصائياتي",
        'referral': "👥 نظام الإحالة",
        'change_language': "🌐 تغيير اللغة",
        'view_links': "👀 مشاهدة روابط الآخرين",
        'register_link_prompt': "📤 الرجاء إرسال رابط فيديو يوتيوب الخاص بك:\n\n⚠️ يمكنك تسجيل <b>1</b> رابط في الأسبوع\n🔑 الكود الأسبوعي: <code>{unique_code}</code>\n\n📌 اكتب هذا الكود على الفيديو قبل الرفع",
        'link_registered': "✅ تم تسجيل رابطك بنجاح!\n\n📌 قم بمشاهدة وإعجاب <b>{count}</b> روابط للمستخدمين الآخرين\n🔑 أدخل الكود الفريد لكل رابط بعد المشاهدة",
        'interaction_prompt': "👀 الرجاء مشاهدة وإعجاب هذه الروابط {count}:\n\n{links}\n\n🔑 أدخل الكود الفريد لكل رابط بعد المشاهدة:",
        'enter_unique_code': "📤 الرجاء إدخال الكود الفريد للفيديو الذي شاهدته:",
        'unique_code_invalid': "❌ كود فريد غير صالح!\nالرجاء إدخال الكود الصحيح.",
        'unique_code_success': "✅ تم تسجيل المشاهدة بنجاح!\n🎉 أكملت تفاعل واحد.",
        'interaction_complete': "✅ أكملت {count}/{required} تفاعل اليوم!\n🎉 تم تسجيل روابطك في التبادل",
        'not_enough_interactions': "❌ لديك {count} تفاعل من {required} المطلوبة اليوم.\nالرجاء إكمال تفاعلاتك أولاً.",
        'referral_info': "👥 **نظام الإحالة الخاص بك**\n\n🔗 **رمز الإحالة الخاص بك:**\n<code>{ref_code}</code>\n\n👤 **عدد الإحالات:** {ref_count} مستخدم\n🎯 **الإحالات المطلوبة:** {required_ref}\n\n📋 **رابط الدعوة:**\n<code>{ref_link}</code>\n\n📤 انقر على الزر أدناه للنسخ:",
        'referral_link': "https://t.me/SEGNALF_bot?start={ref_code}",
        'referral_copied': "✅ تم نسخ رمز الإحالة!\n\n📋 الرمز: <code>{ref_code}</code>\n\n📤 شارك هذا الرمز مع أصدقائك",
        'referral_success': "🎉 **تهانينا!**\n\nتمت دعوتك بواسطة <b>{ref_name}</b>!\n✅ تم تسجيل إحالتك بنجاح\n🎁 كلاكما ستستفيدان من هذه الدعوة",
        'referral_not_found': "❌ رمز الإحالة غير صالح",
        'subscribed': "✅ اشتراكك نشط حتى {expiry}",
        'not_subscribed': "❌ ليس لديك اشتراك نشط\n💳 الرجاء دفع 50 دولاراً للتفعيل",
        'payment_info': "💳 الرجاء إرسال <b>50 دولار</b> USDT (TRC20) إلى هذا العنوان:\n\n<code>{wallet}</code>\n\n📌 أولاً أدخل عنوان محفظتك المصدر:",
        'enter_source_address': "📤 الرجاء إدخال عنوان محفظتك المصدر:",
        'source_address_saved': "✅ تم حفظ عنوانك المصدر!\n\n💳 الرجاء إرسال <b>50 دولار</b> USDT (TRC20) إلى هذا العنوان:\n\n<code>{wallet}</code>\n\n📌 بعد الدفع، انقر على الزر أدناه",
        'payment_confirmed': "✅ تم استلام تأكيد الدفع!\n⏳ جاري التحقق من البلوكتشين... (حد أقصى 10 دقائق)",
        'payment_success': "✅ تم التحقق من الدفع بنجاح!\n🎉 اشتراكك نشط الآن",
        'payment_failed': "❌ فشل التحقق من الدفع!\nالرجاء المحاولة مرة أخرى أو استخدام زر إرسال التجزئة",
        'payment_timeout': "⏰ انتهت مهلة التحقق من الدفع\nالرجاء استخدام زر إرسال التجزئة",
        'send_hash_button': "📤 إرسال تجزئة المعاملة",
        'enter_tx_hash': "📤 الرجاء إرسال تجزئة المعاملة الخاصة بك:",
        'hash_received': "✅ تم استلام تجزئة المعاملة الخاصة بك!\n⏳ تستغرق عملية التحقق حتى 24 ساعة",
        'admin_panel': "🛠 لوحة التحكم",
        'make_paid': "💰 جعل مدفوع",
        'make_free': "🆓 جعل مجاني",
        'broadcast': "📢 بث",
        'verify_payments': "✅ التحقق من المدفوعات",
        'manage_keys': "🔑 إدارة مفاتيح API",
        'db_stats': "📊 إحصائيات قاعدة البيانات",
        'brand_settings': "🏷️ إعدادات العلامة التجارية",
        'set_brand': "✏️ تعيين العلامة",
        'remove_brand': "🗑️ حذف العلامة",
        'brand_set': "✅ تم تعيين العلامة التجارية بنجاح!\n\n🏷️ العلامة: {brand}\n📌 مثال الكود: <code>{brand} {code}</code>",
        'brand_removed': "✅ تم حذف العلامة التجارية بنجاح",
        'paid_mode': "💰 تم تغيير البوت إلى وضع الدفع\nيجب على المستخدمين شراء اشتراك لتسجيل الروابط",
        'free_mode': "🆓 تم تغيير البوت إلى وضع مجاني\nيمكن لجميع المستخدمين تسجيل الروابط بدون اشتراك",
        'stats_info': "📊 **إحصائياتك:**\n\n📝 الروابط المسجلة: {total_links}\n👀 تفاعلات اليوم: {interactions}/{required}\n👥 الإحالات: {referrals}\n📌 الروابط النشطة: {active_links}\n🚀 مضاعف المشاهدات: {boost}x\n🔑 الكود الأسبوعي: <code>{unique_code}</code>",
        'no_links_to_view': "✅ لقد أكملت جميع التفاعلات المطلوبة لهذا اليوم!",
        'interaction_links': "👀 **روابط للمشاهدة:**\n\n{links}\n\n🔑 بعد مشاهدة كل فيديو، أدخل الكود الفريد الخاص به:",
        'view_links_empty': "❌ لا توجد روابط للمشاهدة.",
        'free_register': "✅ في الوضع المجاني، يمكنك تسجيل الروابط بدون اشتراك",
        'payment_manual_review': "📤 تم إرسال التجزئة الخاصة بك للمراجعة اليدوية\n⏳ تستغرق عملية التحقق حتى 24 ساعة",
        'key_added': "✅ تم تسجيل وتفعيل مفتاح API الجديد بنجاح!",
        'key_add_failed': "❌ فشل تسجيل المفتاح! الرجاء إرسال مفتاح صالح",
        'key_list': "📋 **قائمة مفاتيح API**",
        'no_keys': "❌ لم يتم تسجيل أي مفاتيح",
        'copy_code': "📋 نسخ الرمز",
        'copy_link': "📋 نسخ الرابط",
        'referral_challenge': "🏆 **تحدي الإحالة**\n\nأفضل المستخدمين مع أكثر الإحالات يفوزون!\n🎁 الجائزة: {reward} USDT\n👥 عدد الفائزين: {top_users}\n⏳ الوقت المتبقي: {time_left}\n\n📊 انقر أدناه لمعرفة ترتيبك:",
        'referral_rank': "📊 **ترتيبك في التحدي**\n\n👤 أنت: {user_ref} إحالة\n🏅 الترتيب: #{rank}\n🥇 الأول: {first_name} مع {first_ref} إحالة\n🥈 الثاني: {second_name} مع {second_ref} إحالة\n🥉 الثالث: {third_name} مع {third_ref} إحالة\n\n⏳ الوقت المتبقي: {time_left}",
        'you_won': "🎉 **تهانينا! لقد فزت بتحدي الإحالة!**\n\n🏆 أنت من بين {top_users} الأوائل مع {ref_count} إحالة!\n🎁 جائزتك: {reward} USDT\n\n📤 الرجاء إرسال عنوان محفظتك TRC20:",
        'address_received': "✅ تم استلام عنوان المحفظة!\n⏳ جاري المعالجة...\n\n🔗 العنوان: <code>{address}</code>\n💰 المبلغ: {reward} USDT\n\n📌 سيقوم المدير بالتأكيد بعد الإرسال.",
        'reward_sent': "✅ **تم إرسال الجائزة!**\n\n💰 المبلغ: {reward} USDT\n🔗 العنوان: <code>{address}</code>\n\n🎉 تهانينا!",
        'challenge_ended': "⏰ **انتهى تحدي الإحالة!**\n\n🏆 الفائزون:\n{winners}\n\n🎁 كل واحد يحصل على {reward} USDT.",
        'no_challenge': "❌ لا يوجد تحدي إحالة نشط",
        'challenge_started': "🏆 **بدأ تحدي الإحالة!**\n\nالمدة: {duration} أيام\n🎁 الجائزة: {reward} USDT\n👥 عدد الفائزين: {top_users}\n\nمن يجلب أكثر إحالات يفوز!",
        'challenge_stopped': "⏹️ تم إيقاف تحدي الإحالة",
        'manage_challenge': "🏆 إدارة تحدي الإحالة",
        'start_challenge': "▶️ بدء التحدي",
        'stop_challenge': "⏹️ إيقاف التحدي",
        'challenge_status': "📊 حالة التحدي",
        'reward_winners': "💰 الإعلان عن الفائزين والدفع",
        'enter_duration': "⏱️ الرجاء إدخال مدة التحدي بالأيام (مثال: 7):",
        'invalid_duration': "❌ رقم غير صالح! الرجاء إدخال رقم موجب.",
        'challenge_already_active': "⚠️ تحدي الإحالة نشط بالفعل!",
        'challenge_not_active': "⚠️ تحدي الإحالة غير نشط!",
        'winners_announced': "🏆 **تم الإعلان عن الفائزين بتحدي الإحالة!**\n\n{winners}\n\n🎁 كل واحد يحصل على {reward} USDT.\n\n📤 يمكن للفائزين إرسال عنوان محفظتهم.",
        'no_winners': "❌ لا يوجد فائزون!",
        'reward_paid': "✅ **تم دفع الجائزة لـ {count} مستخدم!**",
        'challenge_reward_set': "💰 تم تعيين مبلغ الجائزة إلى {amount} USDT",
        'challenge_top_users_set': "👥 تم تعيين عدد الفائزين إلى {count}",
        'new_referral_notification': "🎉 إحالة جديدة!\n👤 {name}\n📊 إجمالي الإحالات: {count}\n🚀 مضاعف المشاهدات: {boost}x",
        'boost_info': "🚀 **مضاعف المشاهدات الخاص بك**\n\n👥 إحالاتك: {ref_count}\n📈 مضاعف المشاهدات: {boost}x\n\n💡 إذا تجاوزت إحالاتك {threshold}، سيزيد مضاعفك!"
    },
    'ru': {
        'welcome': "👋 Добро пожаловать <b>{first_name}</b>!\n\n🎯 Бот обмена просмотров и лайков YouTube\n📌 Зарегистрируйте свои ссылки и зарабатывайте",
        'register_link': "📝 Зарегистрировать ссылку YouTube",
        'my_stats': "📊 Моя статистика",
        'referral': "👥 Реферальная система",
        'change_language': "🌐 Сменить язык",
        'view_links': "👀 Просмотреть ссылки других",
        'register_link_prompt': "📤 Пожалуйста, отправьте ссылку на видео YouTube:\n\n⚠️ Вы можете зарегистрировать <b>1</b> ссылку в неделю\n🔑 Еженедельный код: <code>{unique_code}</code>\n\n📌 Напишите этот код на видео перед загрузкой",
        'link_registered': "✅ Ваша ссылка успешно зарегистрирована!\n\n📌 Теперь просмотрите и поставьте лайки <b>{count}</b> ссылкам других пользователей\n🔑 Введите уникальный код для каждой ссылки после просмотра",
        'interaction_prompt': "👀 Пожалуйста, просмотрите и поставьте лайки этим {count} ссылкам:\n\n{links}\n\n🔑 Введите уникальный код для каждой ссылки после просмотра:",
        'enter_unique_code': "📤 Пожалуйста, введите уникальный код просмотренного видео:",
        'unique_code_invalid': "❌ Неверный уникальный код!\nПожалуйста, введите правильный код.",
        'unique_code_success': "✅ Просмотр зарегистрирован успешно!\n🎉 Вы выполнили 1 взаимодействие.",
        'interaction_complete': "✅ Вы выполнили {count}/{required} взаимодействий сегодня!\n🎉 Ваши ссылки зарегистрированы в обмене",
        'not_enough_interactions': "❌ У вас {count} взаимодействий из {required} требуемых сегодня.\nПожалуйста, сначала выполните взаимодействия.",
        'referral_info': "👥 **Ваша реферальная система**\n\n🔗 **Ваш реферальный код:**\n<code>{ref_code}</code>\n\n👤 **Рефералов:** {ref_count} пользователей\n🎯 **Требуется рефералов:** {required_ref}\n\n📋 **Ссылка для приглашения:**\n<code>{ref_link}</code>\n\n📤 Нажмите кнопку ниже для копирования:",
        'referral_link': "https://t.me/SEGNALF_bot?start={ref_code}",
        'referral_copied': "✅ Реферальный код скопирован!\n\n📋 Код: <code>{ref_code}</code>\n\n📤 Поделитесь этим кодом с друзьями",
        'referral_success': "🎉 **Поздравляем!**\n\nВы были приглашены <b>{ref_name}</b>!\n✅ Ваш реферал успешно зарегистрирован\n🎁 Оба вы получите выгоду от этого приглашения",
        'referral_not_found': "❌ Неверный реферальный код",
        'subscribed': "✅ Ваша подписка активна до {expiry}",
        'not_subscribed': "❌ У вас нет активной подписки\n💳 Пожалуйста, оплатите 50 долларов для активации",
        'payment_info': "💳 Пожалуйста, отправьте <b>50 USD</b> USDT (TRC20) на этот адрес:\n\n<code>{wallet}</code>\n\n📌 Сначала введите адрес вашего кошелька:",
        'enter_source_address': "📤 Пожалуйста, введите адрес вашего кошелька:",
        'source_address_saved': "✅ Ваш адрес сохранен!\n\n💳 Пожалуйста, отправьте <b>50 USD</b> USDT (TRC20) на этот адрес:\n\n<code>{wallet}</code>\n\n📌 После оплаты нажмите кнопку ниже",
        'payment_confirmed': "✅ Подтверждение оплаты получено!\n⏳ Проверка блокчейна... (максимум 10 минут)",
        'payment_success': "✅ Платеж успешно подтвержден!\n🎉 Ваша подписка активна",
        'payment_failed': "❌ Ошибка проверки платежа!\nПожалуйста, попробуйте снова или используйте кнопку отправки хэша",
        'payment_timeout': "⏰ Время проверки платежа истекло\nИспользуйте кнопку отправки хэша",
        'send_hash_button': "📤 Отправить хэш транзакции",
        'enter_tx_hash': "📤 Пожалуйста, отправьте хэш вашей транзакции:",
        'hash_received': "✅ Ваш хэш транзакции получен!\n⏳ Процесс проверки занимает до 24 часов",
        'admin_panel': "🛠 Панель управления",
        'make_paid': "💰 Сделать платным",
        'make_free': "🆓 Сделать бесплатным",
        'broadcast': "📢 Рассылка",
        'verify_payments': "✅ Проверить платежи",
        'manage_keys': "🔑 Управление ключами API",
        'db_stats': "📊 Статистика базы данных",
        'brand_settings': "🏷️ Настройки бренда",
        'set_brand': "✏️ Установить бренд",
        'remove_brand': "🗑️ Удалить бренд",
        'brand_set': "✅ Бренд успешно установлен!\n\n🏷️ Бренд: {brand}\n📌 Пример кода: <code>{brand} {code}</code>",
        'brand_removed': "✅ Бренд успешно удален",
        'paid_mode': "💰 Бот переведен в платный режим\nПользователи должны купить подписку для регистрации ссылок",
        'free_mode': "🆓 Бот переведен в бесплатный режим\nВсе пользователи могут регистрировать ссылки без подписки",
        'stats_info': "📊 **Ваша статистика:**\n\n📝 Зарегистрированных ссылок: {total_links}\n👀 Взаимодействий сегодня: {interactions}/{required}\n👥 Рефералов: {referrals}\n📌 Активных ссылок: {active_links}\n🚀 Множитель просмотров: {boost}x\n🔑 Еженедельный код: <code>{unique_code}</code>",
        'no_links_to_view': "✅ Вы выполнили все необходимые взаимодействия на сегодня!",
        'interaction_links': "👀 **Ссылки для просмотра:**\n\n{links}\n\n🔑 После просмотра каждого видео введите его уникальный код:",
        'view_links_empty': "❌ Нет доступных ссылок для просмотра.",
        'free_register': "✅ В бесплатном режиме вы можете регистрировать ссылки без подписки",
        'payment_manual_review': "📤 Ваш хэш отправлен на ручную проверку\n⏳ Процесс проверки занимает до 24 часов",
        'key_added': "✅ Новый API ключ успешно зарегистрирован и активирован!",
        'key_add_failed': "❌ Ошибка регистрации ключа! Пожалуйста, отправьте действительный ключ",
        'key_list': "📋 **Список API ключей**",
        'no_keys': "❌ Ключи не зарегистрированы",
        'copy_code': "📋 Копировать код",
        'copy_link': "📋 Копировать ссылку",
        'referral_challenge': "🏆 **Реферальный вызов**\n\nЛучшие пользователи с наибольшим количеством рефералов выигрывают!\n🎁 Приз: {reward} USDT\n👥 Количество победителей: {top_users}\n⏳ Осталось времени: {time_left}\n\n📊 Нажмите ниже, чтобы увидеть ваш рейтинг:",
        'referral_rank': "📊 **Ваш рейтинг в вызове**\n\n👤 Вы: {user_ref} рефералов\n🏅 Рейтинг: #{rank}\n🥇 1-й: {first_name} с {first_ref} рефералами\n🥈 2-й: {second_name} с {second_ref} рефералами\n🥉 3-й: {third_name} с {third_ref} рефералами\n\n⏳ Осталось времени: {time_left}",
        'you_won': "🎉 **Поздравляем! Вы выиграли реферальный вызов!**\n\n🏆 Вы среди {top_users} лучших с {ref_count} рефералами!\n🎁 Ваш приз: {reward} USDT\n\n📤 Пожалуйста, отправьте адрес вашего кошелька TRC20:",
        'address_received': "✅ Адрес кошелька получен!\n⏳ Обработка...\n\n🔗 Адрес: <code>{address}</code>\n💰 Сумма: {reward} USDT\n\n📌 Админ подтвердит после отправки.",
        'reward_sent': "✅ **Приз отправлен!**\n\n💰 Сумма: {reward} USDT\n🔗 Адрес: <code>{address}</code>\n\n🎉 Поздравляем!",
        'challenge_ended': "⏰ **Реферальный вызов завершен!**\n\n🏆 Победители:\n{winners}\n\n🎁 Каждый получает {reward} USDT.",
        'no_challenge': "❌ Нет активного реферального вызова",
        'challenge_started': "🏆 **Реферальный вызов начался!**\n\nДлительность: {duration} дней\n🎁 Приз: {reward} USDT\n👥 Победителей: {top_users}\n\nКто приведет больше рефералов, тот победит!",
        'challenge_stopped': "⏹️ Реферальный вызов остановлен",
        'manage_challenge': "🏆 Управление реферальным вызовом",
        'start_challenge': "▶️ Начать вызов",
        'stop_challenge': "⏹️ Остановить вызов",
        'challenge_status': "📊 Статус вызова",
        'reward_winners': "💰 Объявить победителей и оплатить",
        'enter_duration': "⏱️ Пожалуйста, введите длительность вызова в днях (например: 7):",
        'invalid_duration': "❌ Неверное число! Пожалуйста, введите положительное число.",
        'challenge_already_active': "⚠️ Реферальный вызов уже активен!",
        'challenge_not_active': "⚠️ Реферальный вызов не активен!",
        'winners_announced': "🏆 **Объявлены победители реферального вызова!**\n\n{winners}\n\n🎁 Каждый получает {reward} USDT.\n\n📤 Победители могут отправить адрес своего кошелька.",
        'no_winners': "❌ Нет победителей!",
        'reward_paid': "✅ **Приз выплачен {count} пользователям!**",
        'challenge_reward_set': "💰 Сумма приза установлена на {amount} USDT",
        'challenge_top_users_set': "👥 Количество победителей установлено на {count}",
        'new_referral_notification': "🎉 Новый реферал!\n👤 {name}\n📊 Всего рефералов: {count}\n🚀 Множитель просмотров: {boost}x",
        'boost_info': "🚀 **Ваш множитель просмотров**\n\n👥 Ваши рефералы: {ref_count}\n📈 Множитель просмотров: {boost}x\n\n💡 Если ваши рефералы превысят {threshold}, множитель увеличится!"
    },
    'tr': {
        'welcome': "👋 Hoş geldin <b>{first_name}</b>!\n\n🎯 YouTube Görüntülenme ve Beğeni Takas Botu\n📌 Video linklerini kaydet ve kazan",
        'register_link': "📝 YouTube Linki Kaydet",
        'my_stats': "📊 İstatistiklerim",
        'referral': "👥 Referans Sistemi",
        'change_language': "🌐 Dili Değiştir",
        'view_links': "👀 Diğerlerinin Linklerini Gör",
        'register_link_prompt': "📤 Lütfen YouTube video linkinizi gönderin:\n\n⚠️ Haftada <b>1</b> link kaydedebilirsiniz\n🔑 Haftalık kod: <code>{unique_code}</code>\n\n📌 Bu kodu videonuza yazın ve yükledikten sonra linki gönderin",
        'link_registered': "✅ Linkiniz başarıyla kaydedildi!\n\n📌 Şimdi <b>{count}</b> başka kullanıcının linkini görüntüleyin ve beğenin\n🔑 Her link için benzersiz kodu girin",
        'interaction_prompt': "👀 Lütfen bu {count} linki görüntüleyin ve beğenin:\n\n{links}\n\n🔑 Her linkin benzersiz kodunu görüntüledikten sonra girin:",
        'enter_unique_code': "📤 Lütfen görüntülediğiniz videonun benzersiz kodunu girin:",
        'unique_code_invalid': "❌ Geçersiz benzersiz kod!\nLütfen doğru kodu girin.",
        'unique_code_success': "✅ Görüntülenme başarıyla kaydedildi!\n🎉 1 etkileşim tamamladınız.",
        'interaction_complete': "✅ Bugün {count}/{required} etkileşim tamamladınız!\n🎉 Linkleriniz takasa kaydedildi",
        'not_enough_interactions': "❌ Bugün {count}/{required} etkileşiminiz var.\nLütfen önce etkileşimlerinizi tamamlayın.",
        'referral_info': "👥 **Referans Sisteminiz**\n\n🔗 **Referans Kodunuz:**\n<code>{ref_code}</code>\n\n👤 **Referans Sayısı:** {ref_count} kullanıcı\n🎯 **Gerekli Referans:** {required_ref}\n\n📋 **Davet Linki:**\n<code>{ref_link}</code>\n\n📤 Kopyalamak için aşağıdaki butona tıklayın:",
        'referral_link': "https://t.me/SEGNALF_bot?start={ref_code}",
        'referral_copied': "✅ Referans kodu kopyalandı!\n\n📋 Kod: <code>{ref_code}</code>\n\n📤 Bu kodu arkadaşlarınızla paylaşın",
        'referral_success': "🎉 **Tebrikler!**\n\n<b>{ref_name}</b> tarafından davet edildiniz!\n✅ Referansınız başarıyla kaydedildi\n🎁 Bu davetten ikiniz de faydalanacaksınız",
        'referral_not_found': "❌ Geçersiz referans kodu",
        'subscribed': "✅ Aboneliğiniz {expiry} tarihine kadar aktif",
        'not_subscribed': "❌ Aktif aboneliğiniz yok\n💳 Aktifleştirmek için 50 dolar ödeyin",
        'payment_info': "💳 Lütfen <b>50 USD</b> USDT (TRC20) gönderin:\n\n<code>{wallet}</code>\n\n📌 Önce kaynak cüzdan adresinizi girin:",
        'enter_source_address': "📤 Lütfen kaynak cüzdan adresinizi girin:",
        'source_address_saved': "✅ Kaynak adresiniz kaydedildi!\n\n💳 Lütfen <b>50 USD</b> USDT (TRC20) gönderin:\n\n<code>{wallet}</code>\n\n📌 Ödemeden sonra aşağıdaki butona tıklayın",
        'payment_confirmed': "✅ Ödeme onayı alındı!\n⏳ Blockchain kontrol ediliyor... (maksimum 10 dakika)",
        'payment_success': "✅ Ödeme başarıyla doğrulandı!\n🎉 Aboneliğiniz aktif",
        'payment_failed': "❌ Ödeme doğrulaması başarısız!\nLütfen tekrar deneyin veya hash gönderme butonunu kullanın",
        'payment_timeout': "⏰ Ödeme doğrulama süresi doldu\nHash gönderme butonunu kullanın",
        'send_hash_button': "📤 İşlem Hash'i Gönder",
        'enter_tx_hash': "📤 Lütfen işlem hash'inizi gönderin:",
        'hash_received': "✅ İşlem hash'iniz alındı!\n⏳ Doğrulama işlemi 24 saate kadar sürer",
        'admin_panel': "🛠 Yönetim Paneli",
        'make_paid': "💰 Ücretli Yap",
        'make_free': "🆓 Ücretsiz Yap",
        'broadcast': "📢 Yayın",
        'verify_payments': "✅ Ödemeleri Doğrula",
        'manage_keys': "🔑 API Anahtarlarını Yönet",
        'db_stats': "📊 Veritabanı İstatistikleri",
        'brand_settings': "🏷️ Marka Ayarları",
        'set_brand': "✏️ Marka Ekle",
        'remove_brand': "🗑️ Markayı Kaldır",
        'brand_set': "✅ Marka başarıyla eklendi!\n\n🏷️ Marka: {brand}\n📌 Kod örneği: <code>{brand} {code}</code>",
        'brand_removed': "✅ Marka başarıyla kaldırıldı",
        'paid_mode': "💰 Bot ücretli moda geçti\nKullanıcılar link kaydetmek için abonelik satın almalı",
        'free_mode': "🆓 Bot ücretsiz moda geçti\nTüm kullanıcılar aboneliksiz link kaydedebilir",
        'stats_info': "📊 **İstatistikleriniz:**\n\n📝 Kaydedilen linkler: {total_links}\n👀 Bugünkü etkileşimler: {interactions}/{required}\n👥 Referanslar: {referrals}\n📌 Aktif linkler: {active_links}\n🚀 Görüntülenme çarpanı: {boost}x\n🔑 Haftalık kod: <code>{unique_code}</code>",
        'no_links_to_view': "✅ Bugün için tüm gerekli etkileşimleri tamamladınız!",
        'interaction_links': "👀 **Görüntülenecek Linkler:**\n\n{links}\n\n🔑 Her videoyu görüntüledikten sonra benzersiz kodunu girin:",
        'view_links_empty': "❌ Görüntülenecek link yok.",
        'free_register': "✅ Ücretsiz modda, aboneliksiz link kaydedebilirsiniz",
        'payment_manual_review': "📤 Hash'iniz manuel inceleme için gönderildi\n⏳ Doğrulama işlemi 24 saate kadar sürer",
        'key_added': "✅ Yeni API anahtarı başarıyla kaydedildi ve etkinleştirildi!",
        'key_add_failed': "❌ Anahtar kaydı başarısız! Lütfen geçerli bir anahtar gönderin",
        'key_list': "📋 **API Anahtarları Listesi**",
        'no_keys': "❌ Hiç anahtar kaydedilmedi",
        'copy_code': "📋 Kodu Kopyala",
        'copy_link': "📋 Linki Kopyala",
        'referral_challenge': "🏆 **Referans Yarışması**\n\nEn çok referansı olan kullanıcılar kazanır!\n🎁 Ödül: {reward} USDT\n👥 Kazanan sayısı: {top_users}\n⏳ Kalan süre: {time_left}\n\n📊 Sıralamanızı görmek için aşağıya tıklayın:",
        'referral_rank': "📊 **Yarışmadaki Sıralamanız**\n\n👤 Siz: {user_ref} referans\n🏅 Sıra: #{rank}\n🥇 1.: {first_name} ile {first_ref} referans\n🥈 2.: {second_name} ile {second_ref} referans\n🥉 3.: {third_name} ile {third_ref} referans\n\n⏳ Kalan süre: {time_left}",
        'you_won': "🎉 **Tebrikler! Referans Yarışmasını kazandınız!**\n\n🏆 En iyi {top_users} arasındasınız {ref_count} referansla!\n🎁 Ödülünüz: {reward} USDT\n\n📤 Lütfen TRC20 cüzdan adresinizi gönderin:",
        'address_received': "✅ Cüzdan adresi alındı!\n⏳ İşleniyor...\n\n🔗 Adres: <code>{address}</code>\n💰 Miktar: {reward} USDT\n\n📌 Yönetici gönderimden sonra onaylayacak.",
        'reward_sent': "✅ **Ödül gönderildi!**\n\n💰 Miktar: {reward} USDT\n🔗 Adres: <code>{address}</code>\n\n🎉 Tebrikler!",
        'challenge_ended': "⏰ **Referans Yarışması sona erdi!**\n\n🏆 Kazananlar:\n{winners}\n\n🎁 Her biri {reward} USDT alır.",
        'no_challenge': "❌ Aktif referans yarışması yok",
        'challenge_started': "🏆 **Referans Yarışması başladı!**\n\nSüre: {duration} gün\n🎁 Ödül: {reward} USDT\n👥 Kazanan sayısı: {top_users}\n\nEn çok referans getiren kazanır!",
        'challenge_stopped': "⏹️ Referans Yarışması durduruldu",
        'manage_challenge': "🏆 Referans Yarışmasını Yönet",
        'start_challenge': "▶️ Yarışmayı Başlat",
        'stop_challenge': "⏹️ Yarışmayı Durdur",
        'challenge_status': "📊 Yarışma Durumu",
        'reward_winners': "💰 Kazananları Duyur ve Öde",
        'enter_duration': "⏱️ Lütfen yarışma süresini gün olarak girin (örnek: 7):",
        'invalid_duration': "❌ Geçersiz sayı! Lütfen pozitif bir sayı girin.",
        'challenge_already_active': "⚠️ Referans yarışması zaten aktif!",
        'challenge_not_active': "⚠️ Referans yarışması aktif değil!",
        'winners_announced': "🏆 **Referans Yarışması Kazananları açıklandı!**\n\n{winners}\n\n🎁 Her biri {reward} USDT alır.\n\n📤 Kazananlar cüzdan adreslerini gönderebilir.",
        'no_winners': "❌ Kazanan bulunamadı!",
        'reward_paid': "✅ **Ödül {count} kullanıcıya ödendi!**",
        'challenge_reward_set': "💰 Ödül miktarı {amount} USDT olarak ayarlandı",
        'challenge_top_users_set': "👥 Kazanan sayısı {count} olarak ayarlandı",
        'new_referral_notification': "🎉 Yeni referans!\n👤 {name}\n📊 Toplam referans: {count}\n🚀 Görüntülenme çarpanı: {boost}x",
        'boost_info': "🚀 **Görüntülenme Çarpanınız**\n\n👥 Referanslarınız: {ref_count}\n📈 Görüntülenme çarpanı: {boost}x\n\n💡 Referanslarınız {threshold} kişiyi geçerse, çarpanınız artacak!"
    }
}

# ==================== ادامه کد در پیام بعدی به دلیل طولانی بودن ====================
# ==================== ادامه کد از قسمت قبل ====================

# ==================== کش فوق‌مقیاس با ۱۰۰۰ شارد ====================
class DistributedUltraCache:
    def __init__(self, max_size=10_000_000, ttl_seconds=600, shard_count=1000):
        self.shard_count = shard_count
        self.shards = [OrderedDict() for _ in range(shard_count)]
        self.shard_locks = [asyncio.Lock() for _ in range(shard_count)]
        self.max_size_per_shard = max_size // shard_count
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        logger.info(f"🚀 کش فوق‌مقیاس با {shard_count} شارد و {self.max_size_per_shard:,} ظرفیت هر شارد راه‌اندازی شد")
    
    def _get_shard(self, key: str) -> int:
        return zlib.crc32(key.encode()) % self.shard_count
    
    async def get(self, key: str):
        shard_idx = self._get_shard(key)
        async with self.shard_locks[shard_idx]:
            cache = self.shards[shard_idx]
            if key in cache:
                value, timestamp = cache[key]
                if time.time() - timestamp < self.ttl:
                    cache.move_to_end(key)
                    self.hits += 1
                    return value
                else:
                    del cache[key]
                    self.evictions += 1
            self.misses += 1
            return None
    
    async def set(self, key: str, value, ttl: int = None):
        shard_idx = self._get_shard(key)
        async with self.shard_locks[shard_idx]:
            cache = self.shards[shard_idx]
            if key in cache:
                cache.move_to_end(key)
            else:
                if len(cache) >= self.max_size_per_shard:
                    cache.popitem(last=False)
                    self.evictions += 1
            actual_ttl = ttl if ttl else self.ttl
            cache[key] = (value, time.time() + actual_ttl)
    
    async def delete(self, key: str):
        shard_idx = self._get_shard(key)
        async with self.shard_locks[shard_idx]:
            cache = self.shards[shard_idx]
            if key in cache:
                del cache[key]
                return True
            return False
    
    async def get_stats(self) -> Dict:
        total_items = sum(len(shard) for shard in self.shards)
        return {
            'total_items': total_items,
            'shard_count': self.shard_count,
            'max_size': self.shard_count * self.max_size_per_shard,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': (self.hits / max(1, self.hits + self.misses)) * 100,
            'evictions': self.evictions,
            'ttl': self.ttl
        }


# ==================== دیتابیس فوق‌مقیاس با ۱۰۰۰ شارد ====================
class UltraScalableDatabase:
    def __init__(self, db_path="bot_database.db", shard_count=1000):
        self.db_path = db_path
        self.shard_count = shard_count
        self.cache = DistributedUltraCache(max_size=10_000_000, ttl_seconds=600, shard_count=1000)
        
        self.shard_paths = []
        for i in range(shard_count):
            shard_dir = f"shards_{i // 100}"
            os.makedirs(shard_dir, exist_ok=True)
            shard_path = f"{shard_dir}/db_{i}.db"
            self.shard_paths.append(shard_path)
        
        self._init_all_shards()
        logger.info(f"🗄️ دیتابیس فوق‌مقیاس با {shard_count} شارد راه‌اندازی شد")
    
    def _get_shard(self, user_id: int) -> int:
        return abs(user_id) % self.shard_count
    
    def _get_shard_path(self, shard_idx: int) -> str:
        return self.shard_paths[shard_idx]
    
    def _init_all_shards(self):
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            self._init_shard_tables(shard_path)
    
    def _init_shard_tables(self, shard_path: str):
        with sqlite3.connect(shard_path, timeout=60) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=500000")
            conn.execute("PRAGMA mmap_size=30000000000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA page_size=8192")
            
            cursor = conn.cursor()
            
            # ===== جدول کاربران با فیلدهای جدید =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'fa',
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    is_subscribed INTEGER DEFAULT 0,
                    subscription_expiry TEXT,
                    wallet_address TEXT,
                    daily_link_count INTEGER DEFAULT 0,
                    last_link_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    payment_address TEXT,
                    referral_reward_address TEXT,
                    referral_reward_received INTEGER DEFAULT 0,
                    last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                    total_referrals INTEGER DEFAULT 0,
                    total_views_received INTEGER DEFAULT 0,
                    total_likes_received INTEGER DEFAULT 0,
                    weekly_unique_code TEXT,
                    weekly_code_generated_at TEXT,
                    daily_interactions INTEGER DEFAULT 0,
                    last_interaction_date TEXT,
                    weekly_link_count INTEGER DEFAULT 0,
                    last_weekly_link_date TEXT
                )
            """)
            
            # ===== جدول لینک‌های یوتیوب با فیلدهای جدید =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS youtube_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    video_url TEXT UNIQUE,
                    video_id TEXT,
                    unique_code TEXT UNIQUE,
                    views_count INTEGER DEFAULT 0,
                    likes_count INTEGER DEFAULT 0,
                    daily_views INTEGER DEFAULT 0,
                    daily_likes INTEGER DEFAULT 0,
                    last_interaction_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    boost_multiplier INTEGER DEFAULT 1,
                    view_priority INTEGER DEFAULT 0,
                    is_promoted INTEGER DEFAULT 0,
                    promoted_at TEXT,
                    week_number INTEGER DEFAULT 0
                )
            """)
            
            # ===== جدول تعاملات با کد یکتا =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_user INTEGER,
                    to_link_id INTEGER,
                    type TEXT CHECK(type IN ('view', 'like')),
                    unique_code TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== جدول توزیع لینک‌ها =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS link_distribution (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    link_id INTEGER,
                    assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    viewed INTEGER DEFAULT 0,
                    liked INTEGER DEFAULT 0,
                    unique_code_entered TEXT
                )
            """)
            
            # ===== جدول تراکنش‌ها =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    tx_hash TEXT UNIQUE,
                    from_address TEXT,
                    amount REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    verified_at TEXT,
                    payment_timeout TEXT,
                    manual_review INTEGER DEFAULT 0,
                    is_reward INTEGER DEFAULT 0
                )
            """)
            
            # ===== جدول کلیدهای API =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_value TEXT UNIQUE,
                    is_active INTEGER DEFAULT 1,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_used TEXT,
                    requests_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    notes TEXT
                )
            """)
            
            # ===== جدول تنظیمات سیستم =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== جدول چالش رفرال =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_challenge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    is_active INTEGER DEFAULT 0,
                    start_date TEXT,
                    end_date TEXT,
                    reward_amount INTEGER DEFAULT 100,
                    top_users INTEGER DEFAULT 10,
                    winners_declared INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== جدول برندگان چالش =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_challenge_winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    referral_count INTEGER,
                    reward_amount INTEGER,
                    wallet_address TEXT,
                    paid INTEGER DEFAULT 0,
                    paid_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ===== جدول لینک‌های تبلیغ شده (چرخشی) =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promoted_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_id INTEGER UNIQUE,
                    promoted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    views_generated INTEGER DEFAULT 0
                )
            """)
            
            # ===== تنظیمات اولیه =====
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('is_paid', '0')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('challenge_active', '0')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('challenge_end_date', '')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('challenge_reward', '100')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('challenge_top_users', '10')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('challenge_duration', '7')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('brand_name', '')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('weekly_code', '')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('weekly_code_date', '')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('promotion_cursor', '0')")
            
            # ===== ایندکس‌ها =====
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_ref_code ON users(referral_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_referred_by ON users(referred_by)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(is_subscribed, subscription_expiry)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_user ON youtube_links(user_id, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_video_id ON youtube_links(video_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_unique_code ON youtube_links(unique_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_winners_user ON referral_challenge_winners(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_winners_paid ON referral_challenge_winners(paid)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_distribution_user ON link_distribution(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_distribution_link ON link_distribution(link_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_from ON interactions(from_user)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_to ON interactions(to_link_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_total_ref ON users(total_referrals)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_priority ON youtube_links(view_priority, views_count)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_promoted ON youtube_links(is_promoted, promoted_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_links_week ON youtube_links(week_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_promoted_links ON promoted_links(link_id, promoted_at)")
            
            conn.commit()
    
    @asynccontextmanager
    async def get_connection(self, user_id: int = None):
        if user_id is not None:
            shard_idx = self._get_shard(user_id)
            shard_path = self._get_shard_path(shard_idx)
        else:
            shard_path = self._get_shard_path(0)
        
        conn = sqlite3.connect(shard_path, timeout=60, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=500000")
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    # ===== توابع کمکی =====
    def get_boost_multiplier(self, referral_count: int) -> int:
        if referral_count >= REFERRAL_BOOST_THRESHOLD * 10:
            return REFERRAL_BOOST_MULTIPLIER * 5
        elif referral_count >= REFERRAL_BOOST_THRESHOLD * 5:
            return REFERRAL_BOOST_MULTIPLIER * 3
        elif referral_count >= REFERRAL_BOOST_THRESHOLD * 2:
            return REFERRAL_BOOST_MULTIPLIER * 2
        elif referral_count >= REFERRAL_BOOST_THRESHOLD:
            return REFERRAL_BOOST_MULTIPLIER
        else:
            return 1
    
    def generate_unique_code(self, length: int = UNIQUE_CODE_LENGTH) -> str:
        """تولید کد یکتا با کاراکترهای تصادفی"""
        return ''.join(random.choice(UNIQUE_CODE_ALPHABET) for _ in range(length))
    
    def get_brand(self) -> str:
        """دریافت نام برند از تنظیمات"""
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = 'brand_name'")
            result = cursor.fetchone()
            return result['value'] if result else ""
    
    def get_full_unique_code(self, code: str) -> str:
        """دریافت کد کامل با برند"""
        brand = self.get_brand()
        if brand:
            return f"{brand} {code}"
        return code
    
    def extract_unique_code(self, full_code: str) -> str:
        """استخراج کد یکتا از متن ارسالی (حذف برند)"""
        brand = self.get_brand()
        if brand and full_code.startswith(brand):
            # حذف برند از ابتدا
            remaining = full_code[len(brand):].strip()
            # اگر با فاصله شروع می‌شود، حذف کن
            if remaining.startswith(' '):
                remaining = remaining[1:]
            return remaining
        return full_code.strip()
    
    def get_weekly_code(self) -> Tuple[str, str]:
        """دریافت یا تولید کد هفتگی"""
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM system_settings WHERE key = 'weekly_code'")
            code_result = cursor.fetchone()
            cursor.execute("SELECT value FROM system_settings WHERE key = 'weekly_code_date'")
            date_result = cursor.fetchone()
            
            current_week = datetime.now().strftime('%Y-%W')
            
            if code_result and date_result and date_result['value'] == current_week:
                return code_result['value'], current_week
            else:
                # تولید کد جدید
                new_code = self.generate_unique_code(UNIQUE_CODE_LENGTH)
                cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('weekly_code', ?)", (new_code,))
                cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('weekly_code_date', ?)", (current_week,))
                conn.commit()
                return new_code, current_week
    
    def get_daily_required_interactions(self) -> int:
        """محاسبه تعداد تعاملات مورد نیاز روزانه بر اساس تعداد کاربران"""
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']
        
        # محاسبه بر اساس تعداد کاربران
        if total_users < 100:
            return DAILY_INTERACTIONS_REQUIRED_MIN  # 5
        elif total_users < 1000:
            return 6
        elif total_users < 5000:
            return 7
        elif total_users < 10000:
            return 8
        elif total_users < 50000:
            return 9
        else:
            return DAILY_INTERACTIONS_REQUIRED_MAX  # 10
    
    def get_daily_promotion_count(self) -> int:
        """محاسبه تعداد لینک‌های تبلیغ شده روزانه"""
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM youtube_links WHERE is_active = 1")
            total_links = cursor.fetchone()['count']
        
        # محاسبه بر اساس تعداد کل لینک‌ها
        promotion_count = int(total_links * DAILY_PROMOTION_RATIO)
        
        # محدودیت‌ها
        if promotion_count < MIN_PROMOTION_PER_DAY:
            promotion_count = min(MIN_PROMOTION_PER_DAY, total_links)
        if promotion_count > MAX_PROMOTION_PER_DAY:
            promotion_count = MAX_PROMOTION_PER_DAY
        
        return max(1, promotion_count)
    
    # ===== متدهای کاربر =====
    async def get_user(self, user_id: int) -> Optional[Dict]:
        cache_key = f"user_{user_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user = dict(row)
                await self.cache.set(cache_key, user, ttl=600)
                return user
        return None
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None, 
                         last_name: str = None, referred_by: int = None) -> Dict:
        referral_code = secrets.token_urlsafe(8)
        weekly_code, _ = self.get_weekly_code()
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (
                    user_id, username, first_name, last_name, 
                    referral_code, referred_by, last_active,
                    weekly_unique_code, weekly_code_generated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """, (user_id, username, first_name, last_name, referral_code, referred_by, weekly_code, datetime.now().isoformat()))
            conn.commit()
            
            await self.cache.delete(f"user_{user_id}")
            await self.cache.delete(f"ref_count_{user_id}")
            
            if referred_by:
                await self.cache.delete(f"ref_count_{referred_by}")
                await self.cache.delete(f"user_{referred_by}")
                
                async with self.get_connection(referred_by) as conn2:
                    cursor2 = conn2.cursor()
                    cursor2.execute("SELECT COUNT(*) as count FROM users WHERE referred_by = ?", (referred_by,))
                    new_count = cursor2.fetchone()['count']
                    await self.cache.set(f"ref_count_{referred_by}", new_count, ttl=120)
                    
                    cursor2.execute("UPDATE users SET total_referrals = ? WHERE user_id = ?", (new_count, referred_by))
                    conn2.commit()
        
        return await self.get_user(user_id)
    
    async def get_user_referrals_count(self, user_id: int) -> int:
        cache_key = f"ref_count_{user_id}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE referred_by = ?", (user_id,))
            count = cursor.fetchone()['count']
            await self.cache.set(cache_key, count, ttl=120)
            return count
    
    async def get_user_by_referral_code(self, referral_code: str) -> Optional[Dict]:
        cache_key = f"ref_user_{referral_code}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id, first_name FROM users WHERE referral_code = ?", (referral_code,))
                    row = cursor.fetchone()
                    if row:
                        user = dict(row)
                        await self.cache.set(cache_key, user, ttl=3600)
                        return user
            except:
                pass
        return None
    
    async def update_user_language(self, user_id: int, language: str):
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET language = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?", (language, user_id))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    async def update_user_subscription(self, user_id: int, months: int = 1):
        expiry = datetime.now() + timedelta(days=30*months)
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_subscribed = 1, subscription_expiry = ? WHERE user_id = ?", (expiry.isoformat(), user_id))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    async def set_user_payment_address(self, user_id: int, address: str):
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET payment_address = ? WHERE user_id = ?", (address, user_id))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    async def set_user_reward_address(self, user_id: int, address: str):
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET referral_reward_address = ? WHERE user_id = ?", (address, user_id))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    async def mark_reward_received(self, user_id: int):
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET referral_reward_received = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    async def update_user_weekly_code(self, user_id: int):
        """به‌روزرسانی کد هفتگی کاربر"""
        weekly_code, _ = self.get_weekly_code()
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET weekly_unique_code = ?, weekly_code_generated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            """, (weekly_code, user_id))
            conn.commit()
            await self.cache.delete(f"user_{user_id}")
    
    async def reset_daily_interactions(self):
        """بازنشانی تعاملات روزانه همه کاربران"""
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=30) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users 
                        SET daily_interactions = 0, last_interaction_date = CURRENT_TIMESTAMP 
                        WHERE last_interaction_date < date('now')
                    """)
                    conn.commit()
            except Exception as e:
                logger.error(f"خطا در بازنشانی تعاملات شارد {shard_idx}: {e}")
    
    # ===== متدهای لینک =====
    def _extract_video_id(self, url: str) -> Optional[str]:
        patterns = [
            r'(?:youtube\.com\/watch\?v=)([\w-]+)',
            r'(?:youtu\.be\/)([\w-]+)',
            r'(?:youtube\.com\/embed\/)([\w-]+)',
            r'(?:youtube\.com\/shorts\/)([\w-]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def can_register_link(self, user_id: int) -> Tuple[bool, str]:
        """بررسی آیا کاربر می‌تواند لینک ثبت کند"""
        user = await self.get_user(user_id)
        if not user:
            return False, "کاربر یافت نشد"
        
        # ===== بررسی تعاملات روزانه =====
        today = datetime.now().date().isoformat()
        daily_interactions = user.get('daily_interactions', 0)
        required = self.get_daily_required_interactions()
        
        if daily_interactions < required:
            return False, f"شما امروز {daily_interactions} تعامل از {required} مورد نیاز انجام داده‌اید. لطفا ابتدا تعاملات خود را کامل کنید."
        
        # ===== بررسی ثبت لینک هفتگی =====
        last_weekly = user.get('last_weekly_link_date')
        if last_weekly:
            try:
                last_date = datetime.fromisoformat(last_weekly)
                if datetime.now() - last_date < timedelta(days=7):
                    return False, "شما این هفته قبلاً لینک ثبت کرده‌اید. هفته آینده می‌توانید لینک جدید ثبت کنید."
            except:
                pass
        
        # ===== بررسی کد هفتگی =====
        weekly_code, _ = self.get_weekly_code()
        user_code = user.get('weekly_unique_code')
        if user_code != weekly_code:
            await self.update_user_weekly_code(user_id)
        
        return True, "امکان ثبت لینک وجود دارد"
    
    async def add_youtube_link(self, user_id: int, video_url: str) -> Tuple[bool, str]:
        """ثبت لینک یوتیوب با کد یکتا"""
        # بررسی قابلیت ثبت
        can_register, msg = await self.can_register_link(user_id)
        if not can_register:
            return False, msg
        
        video_id = self._extract_video_id(video_url)
        if not video_id:
            return False, "لینک یوتیوب نامعتبر است"
        
        cache_key = f"video_{video_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return False, "این ویدیو قبلاً ثبت شده است"
        
        # بررسی تکراری بودن ویدیو
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM youtube_links WHERE video_id = ?", (video_id,))
            if cursor.fetchone():
                await self.cache.set(cache_key, True, ttl=3600)
                return False, "این ویدیو قبلاً ثبت شده است"
        
        # تولید کد یکتا
        unique_code = self.generate_unique_code(UNIQUE_CODE_LENGTH)
        full_code = self.get_full_unique_code(unique_code)
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            
            # محاسبه ضریب بازدید
            ref_count = await self.get_user_referrals_count(user_id)
            boost = self.get_boost_multiplier(ref_count)
            
            # شماره هفته
            week_number = datetime.now().isocalendar()[1]
            
            cursor.execute("""
                INSERT INTO youtube_links (
                    user_id, video_url, video_id, 
                    unique_code, boost_multiplier, 
                    week_number, view_priority
                )
                VALUES (?, ?, ?, ?, ?, ?, (SELECT COUNT(*) + 1 FROM youtube_links))
            """, (user_id, video_url, video_id, unique_code, boost, week_number))
            
            link_id = cursor.lastrowid
            
            # بروزرسانی اطلاعات کاربر
            cursor.execute("""
                UPDATE users 
                SET weekly_link_count = weekly_link_count + 1,
                    last_weekly_link_date = CURRENT_TIMESTAMP,
                    daily_interactions = 0
                WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
            await self.cache.set(cache_key, True, ttl=3600)
            await self.cache.delete(f"user_{user_id}")
            
            return True, full_code
    
    async def get_user_links(self, user_id: int, limit: int = 10) -> List[Dict]:
        cache_key = f"user_links_{user_id}_{limit}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM youtube_links 
                WHERE user_id = ? AND is_active = 1 
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            links = [dict(row) for row in cursor.fetchall()]
            await self.cache.set(cache_key, links, ttl=300)
            return links
    
    # =====================================================
    # ===== الگوریتم چرخشی توزیع لینک (پیشرفته) =====
    # =====================================================
    async def distribute_links(self, user_id: int) -> List[Dict]:
        """
        الگوریتم چرخشی پیشرفته برای توزیع لینک‌ها:
        1. لینک‌هایی که امروز تبلیغ شده‌اند (is_promoted = 1) نمایش داده نمی‌شوند
        2. لینک‌هایی که کمترین بازدید را دارند اولویت دارند
        3. از هر کاربر حداکثر ۱ لینک نمایش داده می‌شود
        4. تعداد لینک‌ها بر اساس تعداد کاربران محاسبه می‌شود (۵ تا ۱۰)
        """
        today = datetime.now().date().isoformat()
        cache_key = f"distribute_{user_id}_{today}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        required_count = self.get_daily_required_interactions()
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            
            # ===== دریافت لینک‌های قابل نمایش =====
            cursor.execute("""
                SELECT yl.*, u.username, u.first_name,
                       CASE WHEN ld.id IS NOT NULL THEN 1 ELSE 0 END as already_viewed
                FROM youtube_links yl
                JOIN users u ON yl.user_id = u.user_id
                LEFT JOIN link_distribution ld ON yl.id = ld.link_id 
                    AND ld.user_id = ? 
                    AND DATE(ld.assigned_at) = ?
                WHERE yl.user_id != ? 
                  AND yl.is_active = 1
                  AND yl.is_promoted = 0  -- فقط لینک‌های تبلیغ نشده
                GROUP BY yl.id
                ORDER BY 
                    already_viewed ASC,
                    yl.view_priority ASC,
                    yl.views_count ASC,
                    yl.created_at ASC
                LIMIT ?
            """, (user_id, today, user_id, required_count * 5))
            
            all_links = [dict(row) for row in cursor.fetchall()]
            
            if not all_links:
                # اگر لینک تبلیغ نشده وجود نداشت، از همه لینک‌ها استفاده کن
                cursor.execute("""
                    SELECT yl.*, u.username, u.first_name,
                           CASE WHEN ld.id IS NOT NULL THEN 1 ELSE 0 END as already_viewed
                    FROM youtube_links yl
                    JOIN users u ON yl.user_id = u.user_id
                    LEFT JOIN link_distribution ld ON yl.id = ld.link_id 
                        AND ld.user_id = ? 
                        AND DATE(ld.assigned_at) = ?
                    WHERE yl.user_id != ? 
                      AND yl.is_active = 1
                    GROUP BY yl.id
                    ORDER BY 
                        already_viewed ASC,
                        yl.views_count ASC,
                        yl.created_at ASC
                    LIMIT ?
                """, (user_id, today, user_id, required_count * 5))
                all_links = [dict(row) for row in cursor.fetchall()]
            
            if not all_links:
                return []
            
            # ===== انتخاب لینک‌ها =====
            selected_links = []
            used_users = set()
            
            # اولویت 1: لینک‌های دیده نشده از کاربران مختلف
            for link in all_links:
                if link['already_viewed'] == 0 and link['user_id'] not in used_users:
                    if len(selected_links) < required_count:
                        selected_links.append(link)
                        used_users.add(link['user_id'])
            
            # اولویت 2: لینک‌های دیده شده از کاربران مختلف
            if len(selected_links) < required_count:
                for link in all_links:
                    if link['user_id'] not in used_users and len(selected_links) < required_count:
                        selected_links.append(link)
                        used_users.add(link['user_id'])
            
            # اولویت 3: هر لینک دیگری
            if len(selected_links) < required_count:
                for link in all_links:
                    if len(selected_links) >= required_count:
                        break
                    if link not in selected_links:
                        selected_links.append(link)
            
            # ===== ثبت توزیع =====
            for link in selected_links:
                cursor.execute("""
                    INSERT OR IGNORE INTO link_distribution (user_id, link_id, assigned_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (user_id, link['id']))
            
            conn.commit()
            await self.cache.set(cache_key, selected_links, ttl=1800)
            return selected_links
    
    async def get_links_for_view(self, user_id: int) -> List[Dict]:
        """دریافت لینک‌ها برای دکمه مشاهده لینک‌ها"""
        return await self.distribute_links(user_id)
    
    # ===== متد تعامل با کد یکتا =====
    async def verify_unique_code(self, user_id: int, code: str) -> Tuple[bool, str, Optional[Dict]]:
        """بررسی کد یکتا و ثبت تعامل"""
        # استخراج کد خالص (حذف برند)
        clean_code = self.extract_unique_code(code)
        
        if len(clean_code) != UNIQUE_CODE_LENGTH:
            return False, "کد یکتا نامعتبر است (طول کد باید {} کاراکتر باشد)".format(UNIQUE_CODE_LENGTH), None
        
        # جستجوی لینک با این کد
        found_link = None
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT yl.*, u.user_id as owner_id, u.first_name
                        FROM youtube_links yl
                        JOIN users u ON yl.user_id = u.user_id
                        WHERE yl.unique_code = ? AND yl.is_active = 1
                    """, (clean_code,))
                    row = cursor.fetchone()
                    if row:
                        found_link = dict(row)
                        break
            except:
                pass
        
        if not found_link:
            return False, "کد یکتا یافت نشد! لطفا کد صحیح را وارد کنید.", None
        
        # بررسی اینکه کاربر خودش لینک خودش رو نبینه
        if found_link['user_id'] == user_id:
            return False, "شما نمی‌توانید لینک خودتان را بازدید کنید!", None
        
        # بررسی اینکه امروز این لینک رو دیده
        today = datetime.now().date().isoformat()
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM interactions 
                WHERE from_user = ? AND to_link_id = ? AND DATE(created_at) = ?
            """, (user_id, found_link['id'], today))
            if cursor.fetchone():
                return False, "شما امروز این لینک را قبلاً بازدید کرده‌اید!", None
            
            # ثبت تعامل
            cursor.execute("""
                INSERT INTO interactions (from_user, to_link_id, type, unique_code)
                VALUES (?, ?, 'view', ?)
            """, (user_id, found_link['id'], clean_code))
            
            # بروزرسانی آمار لینک
            boost = found_link.get('boost_multiplier', 1)
            cursor.execute("""
                UPDATE youtube_links 
                SET views_count = views_count + ?, 
                    daily_views = daily_views + ?
                WHERE id = ?
            """, (boost, boost, found_link['id']))
            
            # بروزرسانی تعاملات روزانه کاربر
            cursor.execute("""
                UPDATE users 
                SET daily_interactions = daily_interactions + 1,
                    last_interaction_date = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
            
            # پاک کردن کش
            await self.cache.delete(f"distribute_{user_id}_{today}")
            await self.cache.delete(f"user_{user_id}")
            
            return True, f"✅ بازدید با موفقیت ثبت شد! (+{boost} بازدید)", found_link
    
    async def get_user_daily_stats(self, user_id: int) -> Dict:
        today = datetime.now().date().isoformat()
        cache_key = f"daily_stats_{user_id}_{today}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        async with self.get_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT daily_interactions FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            interactions = result['daily_interactions'] if result else 0
            
            required = self.get_daily_required_interactions()
            
            stats = {'interactions': interactions, 'required': required}
            await self.cache.set(cache_key, stats, ttl=1800)
            return stats
    
    # ===== متدهای چرخش لینک‌ها (سیستم تبلیغ روزانه) =====
    async def run_daily_promotion(self):
        """اجرای روزانه چرخش لینک‌ها - فقط لینک‌های جدید تبلیغ می‌شوند"""
        try:
            # ===== مرحله 1: پاک کردن لینک‌های تبلیغ شده قبلی =====
            for shard_idx in range(self.shard_count):
                shard_path = self._get_shard_path(shard_idx)
                try:
                    with sqlite3.connect(shard_path, timeout=30) as conn:
                        cursor = conn.cursor()
                        # لینک‌هایی که دیروز تبلیغ شده‌اند را غیرفعال کن
                        cursor.execute("""
                            UPDATE youtube_links 
                            SET is_promoted = 0 
                            WHERE is_promoted = 1 
                              AND DATE(promoted_at) < date('now')
                        """)
                        conn.commit()
                except Exception as e:
                    logger.error(f"خطا در پاک کردن لینک‌های تبلیغ شده شارد {shard_idx}: {e}")
            
            # ===== مرحله 2: انتخاب لینک‌های جدید برای تبلیغ =====
            promotion_count = self.get_daily_promotion_count()
            
            for shard_idx in range(self.shard_count):
                shard_path = self._get_shard_path(shard_idx)
                try:
                    with sqlite3.connect(shard_path, timeout=30) as conn:
                        cursor = conn.cursor()
                        
                        # انتخاب لینک‌هایی که کمترین بازدید را دارند و تبلیغ نشده‌اند
                        cursor.execute("""
                            SELECT id FROM youtube_links 
                            WHERE is_active = 1 
                              AND is_promoted = 0
                              AND id NOT IN (SELECT link_id FROM promoted_links WHERE DATE(promoted_at) = date('now'))
                            ORDER BY views_count ASC, created_at ASC
                            LIMIT ?
                        """, (promotion_count // self.shard_count + 1,))
                        
                        links = cursor.fetchall()
                        
                        for link in links:
                            cursor.execute("""
                                UPDATE youtube_links 
                                SET is_promoted = 1, promoted_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (link['id'],))
                            
                            cursor.execute("""
                                INSERT INTO promoted_links (link_id, promoted_at)
                                VALUES (?, CURRENT_TIMESTAMP)
                            """, (link['id'],))
                        
                        conn.commit()
                        
                        if links:
                            logger.info(f"✅ {len(links)} لینک جدید در شارد {shard_idx} تبلیغ شد")
                            
                except Exception as e:
                    logger.error(f"خطا در تبلیغ لینک‌های شارد {shard_idx}: {e}")
            
            logger.info(f"✅ چرخش روزانه لینک‌ها با موفقیت انجام شد! تعداد تبلیغ: {promotion_count}")
            
        except Exception as e:
            logger.error(f"خطا در اجرای چرخش روزانه: {e}")
    
    # ===== متدهای سیستمی =====
    async def get_system_setting(self, key: str) -> Optional[str]:
        cache_key = f"system_{key}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            if result:
                value = result['value']
                await self.cache.set(cache_key, value, ttl=3600)
                return value
        return None
    
    async def set_system_setting(self, key: str, value: str):
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (key, value))
            conn.commit()
            await self.cache.set(f"system_{key}", value, ttl=3600)
    
    async def set_brand(self, brand_name: str):
        """تنظیم نام برند"""
        await self.set_system_setting('brand_name', brand_name.strip())
    
    async def remove_brand(self):
        """حذف نام برند"""
        await self.set_system_setting('brand_name', '')
    
    async def is_paid_mode(self) -> bool:
        value = await self.get_system_setting('is_paid')
        return value == '1'
    
    async def save_api_key(self, key_value: str, notes: str = ""):
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO api_keys (key_value, notes) VALUES (?, ?)", (key_value, notes))
            conn.commit()
    
    async def get_all_users(self) -> List[int]:
        all_users = []
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM users")
                    all_users.extend([row['user_id'] for row in cursor.fetchall()])
            except Exception as e:
                logger.error(f"خطا در دریافت کاربران از شارد {shard_idx}: {e}")
        
        logger.info(f"📊 تعداد کل کاربران دریافت شده: {len(all_users)}")
        return all_users
    
    async def get_db_stats(self) -> Dict:
        total_users = 0
        total_links = 0
        total_transactions = 0
        
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=5) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) as count FROM users")
                    total_users += cursor.fetchone()['count']
                    cursor.execute("SELECT COUNT(*) as count FROM youtube_links")
                    total_links += cursor.fetchone()['count']
                    cursor.execute("SELECT COUNT(*) as count FROM transactions")
                    total_transactions += cursor.fetchone()['count']
            except:
                pass
        
        cache_stats = await self.cache.get_stats()
        return {
            'shard_count': self.shard_count,
            'total_users': total_users,
            'total_links': total_links,
            'total_transactions': total_transactions,
            'cache': cache_stats
        }
    
    # ===== متدهای چالش رفرال =====
    async def start_referral_challenge(self, duration_days: int, reward: int = 100, top_users: int = 10):
        challenge_active = await self.get_system_setting('challenge_active')
        if challenge_active == '1':
            return False, "چالش در حال حاضر فعال است"
        
        end_date = (datetime.now() + timedelta(days=duration_days)).isoformat()
        
        await self.set_system_setting('challenge_active', '1')
        await self.set_system_setting('challenge_end_date', end_date)
        await self.set_system_setting('challenge_reward', str(reward))
        await self.set_system_setting('challenge_top_users', str(top_users))
        await self.set_system_setting('challenge_duration', str(duration_days))
        
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO referral_challenge (is_active, start_date, end_date, reward_amount, top_users) VALUES (1, CURRENT_TIMESTAMP, ?, ?, ?)", (end_date, reward, top_users))
            conn.commit()
        
        return True, f"چالش رفرال با جایزه {reward} USDT برای {top_users} نفر شروع شد"
    
    async def stop_referral_challenge(self):
        challenge_active = await self.get_system_setting('challenge_active')
        if challenge_active != '1':
            return False, "چالش فعال نیست"
        
        await self.set_system_setting('challenge_active', '0')
        
        shard_path = self._get_shard_path(0)
        with sqlite3.connect(shard_path, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE referral_challenge SET is_active = 0 WHERE is_active = 1")
            conn.commit()
        
        return True, "چالش متوقف شد"
    
    async def get_challenge_status(self) -> Dict:
        is_active = await self.get_system_setting('challenge_active') == '1'
        end_date_str = await self.get_system_setting('challenge_end_date') or ''
        reward = int(await self.get_system_setting('challenge_reward') or '100')
        top_users = int(await self.get_system_setting('challenge_top_users') or '10')
        duration = int(await self.get_system_setting('challenge_duration') or '7')
        
        time_left = "نامشخص"
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
                if datetime.now() < end_date:
                    remaining = end_date - datetime.now()
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    time_left = f"{days} روز و {hours} ساعت"
                else:
                    time_left = "به پایان رسیده"
            except:
                time_left = "نامشخص"
        
        top_users_list = await self.get_challenge_top_users(limit=top_users)
        
        return {
            'is_active': is_active,
            'end_date': end_date_str,
            'time_left': time_left,
            'reward': reward,
            'top_users': top_users,
            'duration': duration,
            'top_users_list': top_users_list
        }
    
    async def get_challenge_top_users(self, limit: int = 10) -> List[Dict]:
        all_users_refs = []
        
        for shard_idx in range(self.shard_count):
            shard_path = self._get_shard_path(shard_idx)
            try:
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT u.user_id, u.first_name, u.username, u.total_referrals,
                               (SELECT COUNT(*) FROM users WHERE referred_by = u.user_id) as referral_count
                        FROM users u
                        WHERE u.user_id != 0
                        ORDER BY referral_count DESC
                        LIMIT ?
                    """, (limit * 2,))
                    for row in cursor.fetchall():
                        all_users_refs.append(dict(row))
            except:
                pass
        
        all_users_refs.sort(key=lambda x: x.get('referral_count', 0), reverse=True)
        return all_users_refs[:limit]
    
    async def declare_challenge_winners(self) -> List[Dict]:
        challenge_active = await self.get_system_setting('challenge_active')
        if challenge_active == '1':
            return None, "چالش هنوز فعال است"
        
        top_users = int(await self.get_system_setting('challenge_top_users') or '10')
        reward = int(await self.get_system_setting('challenge_reward') or '100')
        
        top_users_list = await self.get_challenge_top_users(limit=top_users)
        
        if not top_users_list:
            return None, "هیچ کاربری یافت نشد"
        
        winners = []
        for user in top_users_list:
            if user.get('referral_count', 0) > 0:
                winners.append({
                    'user_id': user['user_id'],
                    'first_name': user.get('first_name', 'کاربر'),
                    'referral_count': user.get('referral_count', 0),
                    'reward_amount': reward
                })
                
                shard_path = self._get_shard_path(self._get_shard(user['user_id']))
                with sqlite3.connect(shard_path, timeout=10) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO referral_challenge_winners (user_id, referral_count, reward_amount) VALUES (?, ?, ?)", (user['user_id'], user.get('referral_count', 0), reward))
                    conn.commit()
        
        await self.set_system_setting('challenge_winners_declared', '1')
        
        return winners, "برندگان با موفقیت اعلام شدند"
    
    async def get_challenge_winner_by_user(self, user_id: int) -> Optional[Dict]:
        shard_idx = self._get_shard(user_id)
        shard_path = self._get_shard_path(shard_idx)
        try:
            with sqlite3.connect(shard_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM referral_challenge_winners WHERE user_id = ? AND paid = 0 ORDER BY created_at DESC LIMIT 1", (user_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
        except:
            pass
        return None
    
    async def mark_winner_paid(self, user_id: int):
        shard_idx = self._get_shard(user_id)
        shard_path = self._get_shard_path(shard_idx)
        try:
            with sqlite3.connect(shard_path, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE referral_challenge_winners SET paid = 1, paid_at = CURRENT_TIMESTAMP WHERE user_id = ? AND paid = 0", (user_id,))
                conn.commit()
                await self.mark_reward_received(user_id)
                return True
        except:
            pass
        return False


# ==================== مدیریت کلیدهای API ====================
class AdvancedAPIManager:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.key_stats = {}
        self.lock = asyncio.Lock()
        self.global_requests = 0
        self.global_errors = 0
        self.global_success = 0
        self.start_time = time.time()
        
        for key in api_keys:
            self.key_stats[key] = {
                'requests': 0, 'errors': 0, 'success': 0,
                'rate_limits': 0, 'last_used': 0, 'cooldown_until': 0,
                'weight': 1.0, 'active': True,
                'response_times': [], 'consecutive_errors': 0,
                'total_requests': 0, 'error_rate': 0.0,
                'added_at': time.time()
            }
    
    async def get_best_key(self) -> Tuple[str, Dict]:
        async with self.lock:
            current_time = time.time()
            available_keys = []
            
            for key in self.api_keys:
                stats = self.key_stats[key]
                if not stats['active'] or current_time < stats['cooldown_until']:
                    continue
                
                score = (
                    stats['error_rate'] * 5000 +
                    (sum(stats['response_times']) / max(1, len(stats['response_times']))) * 20 if stats['response_times'] else 0 +
                    stats['requests'] * 0.1 -
                    stats['weight'] * 100 +
                    (current_time - stats['last_used']) * 0.01
                )
                available_keys.append((score, key, stats))
            
            if not available_keys:
                return self.api_keys[0], self.key_stats[self.api_keys[0]]
            
            available_keys.sort(key=lambda x: x[0])
            best_key = available_keys[0][1]
            best_stats = available_keys[0][2]
            
            best_stats['requests'] += 1
            best_stats['total_requests'] += 1
            best_stats['last_used'] = current_time
            self.global_requests += 1
            
            return best_key, best_stats
    
    async def report_success(self, api_key: str, response_time: float = 0):
        async with self.lock:
            if api_key in self.key_stats:
                stats = self.key_stats[api_key]
                stats['success'] += 1
                stats['consecutive_errors'] = 0
                self.global_success += 1
                if response_time > 0:
                    stats['response_times'].append(response_time)
                    if len(stats['response_times']) > 100:
                        stats['response_times'] = stats['response_times'][-50:]
                if stats['errors'] > 0:
                    stats['errors'] = max(0, stats['errors'] - 1)
    
    async def report_error(self, api_key: str, error_type: str = 'unknown'):
        async with self.lock:
            if api_key in self.key_stats:
                stats = self.key_stats[api_key]
                stats['errors'] += 1
                stats['consecutive_errors'] += 1
                self.global_errors += 1
                
                if error_type == 'rate_limit':
                    stats['rate_limits'] += 1
                    if stats['rate_limits'] > 3:
                        stats['cooldown_until'] = time.time() + 180
                        stats['weight'] *= 0.5
                elif error_type == 'timeout':
                    stats['weight'] *= 0.8
                    if stats['consecutive_errors'] > 3:
                        stats['cooldown_until'] = time.time() + 60
                elif error_type == 'invalid':
                    stats['active'] = False
                    stats['weight'] = 0
                    stats['cooldown_until'] = time.time() + 3600
                
                if stats['consecutive_errors'] > 5:
                    stats['cooldown_until'] = time.time() + 120
                    stats['weight'] *= 0.5
                if stats['weight'] < 0.01:
                    stats['active'] = False
    
    async def add_api_key(self, new_key: str) -> bool:
        async with self.lock:
            if new_key in self.api_keys:
                return False
            self.api_keys.append(new_key)
            self.key_stats[new_key] = {
                'requests': 0, 'errors': 0, 'success': 0,
                'rate_limits': 0, 'last_used': 0, 'cooldown_until': 0,
                'weight': 1.0, 'active': True,
                'response_times': [], 'consecutive_errors': 0,
                'total_requests': 0, 'error_rate': 0.0,
                'added_at': time.time()
            }
            return True
    
    async def remove_api_key(self, api_key: str) -> bool:
        async with self.lock:
            if api_key in self.api_keys:
                self.api_keys.remove(api_key)
                del self.key_stats[api_key]
                return True
            return False
    
    async def toggle_api_key(self, api_key: str) -> bool:
        async with self.lock:
            if api_key in self.key_stats:
                self.key_stats[api_key]['active'] = not self.key_stats[api_key]['active']
                return True
            return False
    
    async def get_stats(self) -> Dict:
        async with self.lock:
            stats = {
                'total_keys': len(self.api_keys),
                'active_keys': len([k for k in self.key_stats if self.key_stats[k]['active']]),
                'total_requests': self.global_requests,
                'total_errors': self.global_errors,
                'total_success': self.global_success,
                'success_rate': (self.global_success / max(1, self.global_requests)) * 100,
                'uptime_seconds': time.time() - self.start_time,
                'keys': {}
            }
            for key in self.api_keys:
                key_stats = self.key_stats[key].copy()
                key_stats['key_preview'] = f"{key[:8]}...{key[-4:]}"
                key_stats['response_time_avg'] = (
                    sum(key_stats['response_times']) / len(key_stats['response_times'])
                    if key_stats['response_times'] else 0
                )
                stats['keys'][key] = key_stats
            return stats


# ==================== API ترون ====================
class TronAPI:
    def __init__(self, api_keys: List[str]):
        self.api_manager = AdvancedAPIManager(api_keys)
        self.base_url = TRON_API_URL
        self.sessions = {}
        self.cache = DistributedUltraCache(max_size=100_000, ttl_seconds=300, shard_count=50)
    
    async def get_session(self, api_key: str):
        if api_key not in self.sessions:
            self.sessions[api_key] = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"TRON-PRO-API-KEY": api_key}
            )
        return self.sessions[api_key]
    
    async def verify_transaction(self, tx_hash: str, user_id: int, owner_wallet: str, from_address: str = None) -> bool:
        cache_key = f"tx_{tx_hash}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        for attempt in range(3):
            try:
                api_key, stats = await self.api_manager.get_best_key()
                if not api_key:
                    await asyncio.sleep(2 ** attempt)
                    continue
                
                start_time = time.time()
                session = await self.get_session(api_key)
                url = f"{self.base_url}/v1/transactions/{tx_hash}"
                
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 429:
                        await self.api_manager.report_error(api_key, 'rate_limit')
                        await asyncio.sleep(min(2 ** attempt * 5, 60))
                        continue
                    if response.status == 403:
                        await self.api_manager.report_error(api_key, 'invalid')
                        continue
                    if response.status != 200:
                        await self.api_manager.report_error(api_key, 'unknown')
                        continue
                    
                    data = await response.json()
                    if not data.get('data'):
                        await self.cache.set(cache_key, False, ttl=300)
                        return False
                    
                    tx_data = data['data'][0]
                    contracts = tx_data.get('raw_data', {}).get('contract', [])
                    
                    for contract in contracts:
                        value = contract.get('parameter', {}).get('value', {})
                        to_address = value.get('to_address')
                        if to_address and to_address == owner_wallet:
                            amount = value.get('amount', 0) / 1e6
                            if amount >= SUBSCRIPTION_PRICE_USD - 1:
                                if from_address:
                                    owner_addr = value.get('owner_address')
                                    if owner_addr and owner_addr == from_address:
                                        await self.api_manager.report_success(api_key, response_time)
                                        await self.cache.set(cache_key, True, ttl=3600)
                                        return True
                                else:
                                    await self.api_manager.report_success(api_key, response_time)
                                    await self.cache.set(cache_key, True, ttl=3600)
                                    return True
                    
                    await self.cache.set(cache_key, False, ttl=300)
                    return False
                    
            except Exception as e:
                logger.error(f"خطا در بررسی تراکنش (تلاش {attempt+1}): {e}")
                await asyncio.sleep(2 ** attempt)
        
        await self.cache.set(cache_key, False, ttl=60)
        return False
    
    async def test_api_key(self, api_key: str) -> Tuple[bool, str]:
        try:
            session = await self.get_session(api_key)
            url = f"{self.base_url}/v1/accounts/{OWNER_WALLET}"
            async with session.get(url) as response:
                if response.status == 200:
                    return True, "✅ کلید معتبر است"
                elif response.status == 403:
                    return False, "❌ کلید نامعتبر است"
                else:
                    return False, f"❌ خطا: {response.status}"
        except Exception as e:
            return False, f"❌ خطا: {str(e)[:50]}"
    
    async def add_api_key(self, new_key: str) -> Tuple[bool, str]:
        is_valid, message = await self.test_api_key(new_key)
        if not is_valid:
            return False, message
        success = await self.api_manager.add_api_key(new_key)
        if success:
            return True, "✅ کلید با موفقیت اضافه شد"
        return False, "❌ این کلید قبلاً اضافه شده است"
    
    async def remove_api_key(self, api_key: str) -> Tuple[bool, str]:
        success = await self.api_manager.remove_api_key(api_key)
        if success:
            return True, "✅ کلید با موفقیت حذف شد"
        return False, "❌ کلید یافت نشد"
    
    async def toggle_api_key(self, api_key: str) -> Tuple[bool, str]:
        success = await self.api_manager.toggle_api_key(api_key)
        if success:
            stats = await self.api_manager.get_stats()
            status = "فعال" if stats['keys'][api_key]['active'] else "غیرفعال"
            return True, f"✅ وضعیت کلید به {status} تغییر کرد"
        return False, "❌ کلید یافت نشد"
    
    async def get_api_stats(self) -> Dict:
        return await self.api_manager.get_stats()
    
    async def close(self):
        for session in self.sessions.values():
            await session.close()
        self.sessions.clear()


# ==================== کلاس اصلی ربات ====================
class YouTubeEarningBot:
    def __init__(self, token: str):
        self.token = token
        self.db = UltraScalableDatabase(shard_count=1000)
        self.tron_api = TronAPI(TRON_API_KEYS)
        self.user_states = {}
        self.priority_update_task = None
        
        asyncio.create_task(self._show_stats())
        asyncio.create_task(self._challenge_monitor())
        asyncio.create_task(self._cache_cleaner())
        asyncio.create_task(self._daily_rotation())
        asyncio.create_task(self._weekly_code_updater())
        asyncio.create_task(self._daily_reset())
        
        logger.info("🚀 ربات با معماری میکروسرویس و ۱۰۰۰ شارد راه‌اندازی شد")
    
    def get_texts(self, lang: str) -> Dict:
        return TEXTS.get(lang, TEXTS['fa'])
    
    async def _show_stats(self):
        await asyncio.sleep(5)
        stats = await self.db.get_db_stats()
        weekly_code, _ = self.db.get_weekly_code()
        brand = self.db.get_brand()
        
        logger.info(f"📊 **آمار دیتابیس:**")
        logger.info(f"   🗄️ تعداد شاردها: {stats['shard_count']}")
        logger.info(f"   👥 کل کاربران: {stats['total_users']:,}")
        logger.info(f"   🔗 کل لینک‌ها: {stats['total_links']:,}")
        logger.info(f"   💳 کل تراکنش‌ها: {stats['total_transactions']:,}")
        logger.info(f"   💾 کش: {stats['cache']['total_items']:,} آیتم")
        logger.info(f"   📈 نرخ موفقیت کش: {stats['cache']['hit_rate']:.2f}%")
        logger.info(f"   🔑 کد هفتگی: {weekly_code}")
        logger.info(f"   🏷️ برند: {brand or 'بدون برند'}")
        logger.info(f"   📊 تعاملات مورد نیاز روزانه: {self.db.get_daily_required_interactions()}")
        logger.info(f"   📊 تعداد تبلیغ روزانه: {self.db.get_daily_promotion_count()}")
    
    async def _challenge_monitor(self):
        while True:
            try:
                challenge_active = await self.db.get_system_setting('challenge_active')
                if challenge_active == '1':
                    end_date_str = await self.db.get_system_setting('challenge_end_date') or ''
                    if end_date_str:
                        try:
                            end_date = datetime.fromisoformat(end_date_str)
                            if datetime.now() >= end_date:
                                await self.db.set_system_setting('challenge_active', '0')
                                winners, msg = await self.db.declare_challenge_winners()
                                if winners:
                                    logger.info(f"🏆 چالش رفرال به پایان رسید! {len(winners)} برنده")
                        except:
                            pass
            except Exception as e:
                logger.error(f"خطا در مانیتورینگ چالش: {e}")
            await asyncio.sleep(30)
    
    async def _cache_cleaner(self):
        while True:
            try:
                stats = await self.db.cache.get_stats()
                if stats['total_items'] > stats['max_size'] * 0.9:
                    logger.info("🧹 پاک‌سازی خودکار کش در حال اجرا...")
                    for shard in self.db.cache.shards:
                        keys_to_delete = []
                        for key, (value, timestamp) in shard.items():
                            if time.time() - timestamp > self.db.cache.ttl:
                                keys_to_delete.append(key)
                        for key in keys_to_delete:
                            del shard[key]
            except Exception as e:
                logger.error(f"خطا در پاک‌سازی کش: {e}")
            await asyncio.sleep(300)
    
    async def _daily_rotation(self):
        """اجرای چرخش روزانه لینک‌ها در نیمه‌شب"""
        while True:
            now = datetime.now()
            # محاسبه زمان تا نیمه‌شب
            midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            wait_seconds = (midnight - now).total_seconds()
            
            await asyncio.sleep(wait_seconds)
            await self.db.run_daily_promotion()
    
    async def _weekly_code_updater(self):
        """بروزرسانی کد هفتگی هر هفته"""
        while True:
            await asyncio.sleep(3600)  # هر ساعت چک کن
            try:
                _, current_week = self.db.get_weekly_code()
                # کدها خودکار بروزرسانی می‌شوند
            except Exception as e:
                logger.error(f"خطا در بروزرسانی کد هفتگی: {e}")
    
    async def _daily_reset(self):
        """بازنشانی روزانه تعاملات"""
        while True:
            now = datetime.now()
            midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            wait_seconds = (midnight - now).total_seconds()
            
            await asyncio.sleep(wait_seconds)
            await self.db.reset_daily_interactions()
            logger.info("🔄 تعاملات روزانه کاربران بازنشانی شد")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        db_user = await self.db.get_user(user_id)
        if not db_user:
            referred_by = None
            if context.args:
                ref_code = context.args[0]
                ref_user = await self.db.get_user_by_referral_code(ref_code)
                if ref_user:
                    referred_by = ref_user['user_id']
                    await update.message.reply_text(
                        self.get_texts('fa')['referral_success'].format(ref_name=ref_user.get('first_name', 'کاربر')),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await update.message.reply_text(
                        self.get_texts('fa')['referral_not_found'],
                        parse_mode=ParseMode.HTML
                    )
            
            db_user = await self.db.create_user(
                user_id, user.username, user.first_name, user.last_name, referred_by
            )
            
            if referred_by:
                ref_count = await self.db.get_user_referrals_count(referred_by)
                boost = self.db.get_boost_multiplier(ref_count)
                try:
                    ref_user = await self.db.get_user(referred_by)
                    ref_lang = ref_user.get('language', 'fa') if ref_user else 'fa'
                    ref_texts = self.get_texts(ref_lang)
                    await context.bot.send_message(
                        referred_by,
                        ref_texts['new_referral_notification'].format(
                            name=user.first_name or 'کاربر',
                            count=ref_count,
                            boost=boost
                        ),
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"خطا در ارسال پیام رفرال: {e}")
        
        lang = db_user.get('language', 'fa')
        texts = self.get_texts(lang)
        
        keyboard = [
            [InlineKeyboardButton(texts['register_link'], callback_data='register_link')],
            [InlineKeyboardButton(texts['view_links'], callback_data='view_links')],
            [InlineKeyboardButton(texts['my_stats'], callback_data='my_stats')],
            [InlineKeyboardButton(texts['referral'], callback_data='referral')],
            [InlineKeyboardButton(texts['change_language'], callback_data='change_language')],
            [InlineKeyboardButton("🚀 ضریب بازدید", callback_data='boost_info')]
        ]
        
        challenge_active = await self.db.get_system_setting('challenge_active')
        if challenge_active == '1':
            keyboard.append([InlineKeyboardButton("🏆 چالش رفرال", callback_data='referral_challenge')])
        
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data='admin_panel')])
        
        await update.message.reply_text(
            texts['welcome'].format(first_name=user.first_name or 'کاربر'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        db_user = await self.db.get_user(user_id)
        
        if not db_user:
            await query.edit_message_text("⚠️ لطفا مجددا /start را بزنید")
            return
        
        lang = db_user.get('language', 'fa')
        texts = self.get_texts(lang)
        data = query.data
        
        if data == 'change_language':
            keyboard = []
            for code, name in SUPPORTED_LANGUAGES.items():
                keyboard.append([InlineKeyboardButton(f"🌐 {name}", callback_data=f"set_lang_{code}")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='back')])
            await query.edit_message_text("🌐 انتخاب زبان / Select Language:", reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data.startswith('set_lang_'):
            new_lang = data.split('_')[2]
            await self.db.update_user_language(user_id, new_lang)
            texts = self.get_texts(new_lang)
            keyboard = [
                [InlineKeyboardButton(texts['register_link'], callback_data='register_link')],
                [InlineKeyboardButton(texts['view_links'], callback_data='view_links')],
                [InlineKeyboardButton(texts['my_stats'], callback_data='my_stats')],
                [InlineKeyboardButton(texts['referral'], callback_data='referral')],
                [InlineKeyboardButton(texts['change_language'], callback_data='change_language')],
                [InlineKeyboardButton("🚀 ضریب بازدید", callback_data='boost_info')]
            ]
            challenge_active = await self.db.get_system_setting('challenge_active')
            if challenge_active == '1':
                keyboard.append([InlineKeyboardButton("🏆 چالش رفرال", callback_data='referral_challenge')])
            if user_id == ADMIN_ID:
                keyboard.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data='admin_panel')])
            await query.edit_message_text(
                f"✅ زبان به {SUPPORTED_LANGUAGES[new_lang]} تغییر یافت",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data == 'boost_info':
            ref_count = await self.db.get_user_referrals_count(user_id)
            boost = self.db.get_boost_multiplier(ref_count)
            
            await query.edit_message_text(
                texts['boost_info'].format(
                    ref_count=ref_count,
                    boost=boost,
                    threshold=REFERRAL_BOOST_THRESHOLD
                ),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back')]]),
                parse_mode=ParseMode.HTML
            )
        
        elif data == 'view_links':
            # نمایش لینک‌های دیگران برای بازدید
            links = await self.db.get_links_for_view(user_id)
            
            if links:
                link_text = ""
                for i, link in enumerate(links, 1):
                    full_code = self.db.get_full_unique_code(link['unique_code'])
                    link_text += f"{i}. 🎬 {link['video_url']}\n   👤 {link.get('first_name', 'کاربر')}\n   🔑 کد: <code>{full_code}</code>\n\n"
                
                await query.edit_message_text(
                    texts['interaction_links'].format(links=link_text),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ کد یکتا را وارد کردم", callback_data='enter_unique_code')],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ]),
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text(
                    texts['view_links_empty'],
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back')]])
                )
        
        elif data == 'enter_unique_code':
            await query.edit_message_text(
                texts['enter_unique_code'],
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'waiting_for_unique_code'
        
        elif data == 'referral_challenge':
            status = await self.db.get_challenge_status()
            if not status['is_active']:
                await query.edit_message_text(texts['no_challenge'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back')]]))
                return
            
            top_users = await self.db.get_challenge_top_users(limit=status['top_users'])
            user_refs = await self.db.get_user_referrals_count(user_id)
            user_rank = None
            
            for idx, u in enumerate(top_users, 1):
                if u['user_id'] == user_id:
                    user_rank = idx
                    break
            
            if user_rank:
                first = top_users[0] if len(top_users) > 0 else None
                second = top_users[1] if len(top_users) > 1 else None
                third = top_users[2] if len(top_users) > 2 else None
                await query.edit_message_text(
                    texts['referral_rank'].format(
                        user_ref=user_refs, rank=user_rank,
                        first_name=first['first_name'] if first else '-',
                        first_ref=first['referral_count'] if first else 0,
                        second_name=second['first_name'] if second else '-',
                        second_ref=second['referral_count'] if second else 0,
                        third_name=third['first_name'] if third else '-',
                        third_ref=third['referral_count'] if third else 0,
                        time_left=status['time_left']
                    ),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back')]]),
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text(
                    texts['referral_challenge'].format(reward=status['reward'], top_users=status['top_users'], time_left=status['time_left']),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📊 مشاهده رتبه برترین‌ها", callback_data='challenge_top')],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ]),
                    parse_mode=ParseMode.HTML
                )
        
        elif data == 'challenge_top':
            status = await self.db.get_challenge_status()
            top_users = status['top_users_list']
            
            if not top_users:
                await query.edit_message_text("❌ هنوز کاربری ثبت نشده است", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='referral_challenge')]]))
                return
            
            text = "🏆 **برترین‌های چالش رفرال**\n\n"
            for idx, u in enumerate(top_users[:10], 1):
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
                text += f"{medal} {u.get('first_name', 'کاربر')} - {u.get('referral_count', 0)} رفرال\n"
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='referral_challenge')]]), parse_mode=ParseMode.HTML)
        
        elif data == 'my_stats':
            ref_count = await self.db.get_user_referrals_count(user_id)
            user_links = await self.db.get_user_links(user_id)
            stats = await self.db.get_user_daily_stats(user_id)
            boost = self.db.get_boost_multiplier(ref_count)
            
            user = await self.db.get_user(user_id)
            weekly_code = self.db.get_full_unique_code(user.get('weekly_unique_code', ''))
            
            await query.edit_message_text(
                texts['stats_info'].format(
                    total_links=len(user_links),
                    interactions=stats['interactions'],
                    required=stats['required'],
                    referrals=ref_count,
                    active_links=len(user_links),
                    boost=boost,
                    unique_code=weekly_code
                ),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back')]]),
                parse_mode=ParseMode.HTML
            )
        
        elif data == 'register_link':
            # ===== بررسی حالت پولی/رایگان =====
            is_paid = await self.db.is_paid_mode()
            
            if is_paid and not db_user.get('is_subscribed'):
                await query.edit_message_text(
                    texts['not_subscribed'],
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💰 پرداخت", callback_data='payment')],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ]),
                    parse_mode=ParseMode.HTML
                )
                return
            
            # ===== بررسی قابلیت ثبت لینک =====
            can_register, msg = await self.db.can_register_link(user_id)
            if not can_register:
                await query.edit_message_text(
                    f"⚠️ {msg}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("👀 مشاهده لینک‌ها", callback_data='view_links')],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ])
                )
                return
            
            # ===== دریافت کد یکتا =====
            weekly_code, _ = self.db.get_weekly_code()
            full_code = self.db.get_full_unique_code(weekly_code)
            
            await query.edit_message_text(
                texts['register_link_prompt'].format(unique_code=full_code),
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'waiting_for_link'
        
        elif data == 'referral':
            ref_code = db_user.get('referral_code')
            ref_count = await self.db.get_user_referrals_count(user_id)
            ref_link = f"https://t.me/SEGNALF_bot?start={ref_code}"
            
            await query.edit_message_text(
                texts['referral_info'].format(ref_code=ref_code, ref_count=ref_count, required_ref=0, ref_link=ref_link),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 کپی کد", callback_data=f"copy_ref_{ref_code}")],
                    [InlineKeyboardButton("📤 اشتراک‌گذاری", switch_inline_query=f"🌟 به ربات یوتیوب بپیوندید!\n{ref_link}")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ]),
                parse_mode=ParseMode.HTML
            )
        
        elif data.startswith('copy_ref_'):
            ref_code = data.split('_')[2]
            await query.edit_message_text(
                texts['referral_copied'].format(ref_code=ref_code),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 اشتراک‌گذاری", switch_inline_query=f"🌟 به ربات یوتیوب بپیوندید!\nhttps://t.me/SEGNALF_bot?start={ref_code}")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='referral')]
                ]),
                parse_mode=ParseMode.HTML
            )
        
        elif data == 'payment':
            await query.edit_message_text(texts['enter_source_address'], parse_mode=ParseMode.HTML)
            self.user_states[user_id] = 'waiting_for_source_address'
        
        elif data == 'confirm_payment':
            await query.edit_message_text(texts['payment_confirmed'], parse_mode=ParseMode.HTML)
            
            user_txs = await self.db.get_user_transactions(user_id)
            if user_txs:
                latest_tx = user_txs[0]
                is_valid = await self.tron_api.verify_transaction(latest_tx['tx_hash'], user_id, OWNER_WALLET, latest_tx.get('from_address'))
                
                if is_valid:
                    await self.db.verify_transaction(latest_tx['tx_hash'], 'approved')
                    await self.db.update_user_subscription(user_id)
                    await query.edit_message_text(
                        texts['payment_success'],
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='back')]]),
                        parse_mode=ParseMode.HTML
                    )
                else:
                    tx_time = datetime.fromisoformat(latest_tx['created_at'])
                    if datetime.now() - tx_time > timedelta(minutes=PAYMENT_TIMEOUT_MINUTES):
                        await query.edit_message_text(
                            texts['payment_timeout'],
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton(texts['send_hash_button'], callback_data='send_hash')],
                                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                            ]),
                            parse_mode=ParseMode.HTML
                        )
                    else:
                        await query.edit_message_text(
                            texts['payment_failed'],
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton(texts['send_hash_button'], callback_data='send_hash')],
                                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                            ]),
                            parse_mode=ParseMode.HTML
                        )
            else:
                await query.edit_message_text(
                    "❌ هیچ تراکنشی یافت نشد",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(texts['send_hash_button'], callback_data='send_hash')],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ])
                )
        
        elif data == 'send_hash':
            await query.edit_message_text(texts['enter_tx_hash'], parse_mode=ParseMode.HTML)
            self.user_states[user_id] = 'waiting_for_manual_hash'
        
        elif data == 'admin_panel' and user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("💰 پولی کردن", callback_data='make_paid')],
                [InlineKeyboardButton("🆓 رایگان کردن", callback_data='make_free')],
                [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data='broadcast')],
                [InlineKeyboardButton("✅ تایید پرداخت‌ها", callback_data='verify_payments')],
                [InlineKeyboardButton("🔑 مدیریت کلیدهای API", callback_data='manage_keys')],
                [InlineKeyboardButton("📊 آمار دیتابیس", callback_data='db_stats')],
                [InlineKeyboardButton("🏆 مدیریت چالش رفرال", callback_data='manage_challenge')],
                [InlineKeyboardButton("🏷️ تنظیمات برند", callback_data='brand_settings')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
            ]
            await query.edit_message_text("🛠 **پنل مدیریت**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        
        # ===== بخش تنظیمات برند =====
        elif data == 'brand_settings' and user_id == ADMIN_ID:
            current_brand = await self.db.get_system_setting('brand_name') or ''
            keyboard = [
                [InlineKeyboardButton("✏️ ثبت برند جدید", callback_data='set_brand')],
                [InlineKeyboardButton("🗑️ حذف برند", callback_data='remove_brand')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
            ]
            
            await query.edit_message_text(
                f"🏷️ **تنظیمات برند**\n\n"
                f"📌 برند فعلی: <code>{current_brand or 'خالی'}</code>\n\n"
                f"💡 برند قبل از کد یکتا قرار می‌گیرد.\n"
                f"📝 نمونه: <code>{current_brand} AbCdEfGhIjKl</code>\n\n"
                f"⚠️ اگر برند خالی باشد، فقط کد یکتا نمایش داده می‌شود.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        
        elif data == 'set_brand' and user_id == ADMIN_ID:
            await query.edit_message_text(
                "✏️ **ثبت برند جدید**\n\n"
                "لطفا نام برند خود را وارد کنید:\n\n"
                "📌 مثال: MyBrand\n"
                "📝 نمونه کد: <code>MyBrand AbCdEfGhIjKl</code>\n\n"
                "⚠️ برای لغو /cancel را بزنید",
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'waiting_for_brand'
        
        elif data == 'remove_brand' and user_id == ADMIN_ID:
            await self.db.remove_brand()
            await query.edit_message_text(
                texts['brand_removed'],
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='brand_settings')]])
            )
        
        # ===== بخش مدیریت چالش =====
        elif data == 'manage_challenge' and user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("▶️ شروع چالش جدید", callback_data='start_challenge')],
                [InlineKeyboardButton("⏹️ توقف چالش", callback_data='stop_challenge')],
                [InlineKeyboardButton("📊 وضعیت چالش", callback_data='challenge_status')],
                [InlineKeyboardButton("💰 اعلام برندگان", callback_data='declare_winners')],
                [InlineKeyboardButton("🎁 تنظیم مبلغ جایزه", callback_data='set_reward')],
                [InlineKeyboardButton("👥 تنظیم تعداد برندگان", callback_data='set_top_users')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
            ]
            await query.edit_message_text(
                "🏆 **مدیریت چالش رفرال**\n\n"
                "• ▶️ شروع چالش جدید با مدت زمان مشخص\n"
                "• ⏹️ توقف چالش فعال\n"
                "• 📊 مشاهده وضعیت فعلی چالش\n"
                "• 💰 اعلام برندگان و شروع پرداخت\n"
                "• 🎁 تنظیم مبلغ جایزه (پیش‌فرض ۱۰۰ دلار)\n"
                "• 👥 تنظیم تعداد برندگان (پیش‌فرض ۱۰ نفر)",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == 'start_challenge' and user_id == ADMIN_ID:
            challenge_active = await self.db.get_system_setting('challenge_active')
            if challenge_active == '1':
                await query.edit_message_text(texts['challenge_already_active'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]))
                return
            
            await query.edit_message_text(texts['enter_duration'], parse_mode=ParseMode.HTML)
            self.user_states[user_id] = 'waiting_for_challenge_duration'
        
        elif data == 'stop_challenge' and user_id == ADMIN_ID:
            success, msg = await self.db.stop_referral_challenge()
            await query.edit_message_text(msg if success else f"❌ {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]))
        
        elif data == 'challenge_status' and user_id == ADMIN_ID:
            status = await self.db.get_challenge_status()
            
            text = f"📊 **وضعیت چالش رفرال**\n\n"
            text += f"📌 وضعیت: {'✅ فعال' if status['is_active'] else '❌ غیرفعال'}\n"
            text += f"⏳ زمان باقی‌مانده: {status['time_left']}\n"
            text += f"🎁 مبلغ جایزه: {status['reward']} USDT\n"
            text += f"👥 تعداد برندگان: {status['top_users']}\n"
            text += f"📅 مدت زمان: {status['duration']} روز\n\n"
            
            if status['top_users_list']:
                text += "🏆 **برترین‌ها:**\n"
                for idx, u in enumerate(status['top_users_list'][:5], 1):
                    text += f"{idx}. {u.get('first_name', 'کاربر')} - {u.get('referral_count', 0)} رفرال\n"
            else:
                text += "❌ هنوز کاربری ثبت نشده است"
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'declare_winners' and user_id == ADMIN_ID:
            challenge_active = await self.db.get_system_setting('challenge_active')
            if challenge_active == '1':
                await query.edit_message_text(texts['challenge_not_active'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]))
                return
            
            winners, msg = await self.db.declare_challenge_winners()
            
            if not winners:
                await query.edit_message_text(texts['no_winners'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]))
                return
            
            for winner in winners:
                try:
                    await context.bot.send_message(winner['user_id'], TEXTS['fa']['you_won'].format(top_users=len(winners), ref_count=winner['referral_count'], reward=winner['reward_amount']), parse_mode=ParseMode.HTML)
                except:
                    pass
            
            winners_text = ""
            for idx, w in enumerate(winners, 1):
                winners_text += f"{idx}. {w['first_name']} - {w['referral_count']} رفرال - {w['reward_amount']} USDT\n"
            
            await query.edit_message_text(
                TEXTS['fa']['winners_announced'].format(winners=winners_text, reward=winners[0]['reward_amount'] if winners else 0),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 تایید پرداخت جایزه", callback_data='confirm_reward_payment')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]
                ]),
                parse_mode=ParseMode.HTML
            )
        
        elif data == 'confirm_reward_payment' and user_id == ADMIN_ID:
            await query.edit_message_text(
                "💰 **تایید پرداخت جایزه**\n\nلطفا پس از واریز جایزه به برندگان، دکمه زیر را بزنید:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ همه برندگان دریافت کردند", callback_data='mark_all_paid')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == 'mark_all_paid' and user_id == ADMIN_ID:
            winners = await self.db.get_challenge_top_users(limit=10)
            paid_count = 0
            
            for w in winners:
                if await self.db.mark_winner_paid(w['user_id']):
                    paid_count += 1
                    try:
                        await context.bot.send_message(w['user_id'], TEXTS['fa']['reward_sent'].format(reward=100, address="ثبت شده"), parse_mode=ParseMode.HTML)
                    except:
                        pass
            
            await query.edit_message_text(TEXTS['fa']['reward_paid'].format(count=paid_count), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]))
        
        elif data == 'set_reward' and user_id == ADMIN_ID:
            await query.edit_message_text("🎁 **تنظیم مبلغ جایزه**\n\nلطفا مبلغ جایزه را به دلار وارد کنید (پیش‌فرض ۱۰۰):", parse_mode=ParseMode.MARKDOWN)
            self.user_states[user_id] = 'waiting_for_reward_amount'
        
        elif data == 'set_top_users' and user_id == ADMIN_ID:
            await query.edit_message_text("👥 **تنظیم تعداد برندگان**\n\nلطفا تعداد برندگان را وارد کنید (پیش‌فرض ۱۰):", parse_mode=ParseMode.MARKDOWN)
            self.user_states[user_id] = 'waiting_for_top_users'
        
        # ===== بخش مدیریت کلیدهای API =====
        elif data == 'manage_keys' and user_id == ADMIN_ID:
            keyboard = [
                [InlineKeyboardButton("➕ ثبت کلید جدید", callback_data='add_new_key')],
                [InlineKeyboardButton("📋 لیست کلیدها", callback_data='list_keys')],
                [InlineKeyboardButton("🔄 فعال/غیرفعال کردن", callback_data='toggle_key')],
                [InlineKeyboardButton("🗑️ حذف کلید", callback_data='delete_key')],
                [InlineKeyboardButton("📊 آمار کلیدها", callback_data='api_stats')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
            ]
            await query.edit_message_text(
                "🔑 **مدیریت کلیدهای API**\n\n"
                "• ➕ ثبت کلید جدید با تست خودکار\n"
                "• 📋 مشاهده لیست کلیدها\n"
                "• 🔄 فعال/غیرفعال کردن کلیدها\n"
                "• 🗑️ حذف کلیدها\n"
                "• 📊 آمار عملکرد کلیدها",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == 'add_new_key' and user_id == ADMIN_ID:
            await query.edit_message_text(
                "🔑 **ثبت کلید جدید API**\n\n"
                "لطفا کلید API ترون را ارسال کنید:\n\n"
                "⚠️ کلید به صورت خودکار تست می‌شود\n"
                "📌 برای لغو /cancel را بزنید",
                parse_mode=ParseMode.MARKDOWN
            )
            self.user_states[user_id] = 'waiting_for_new_api_key'
        
        elif data == 'list_keys' and user_id == ADMIN_ID:
            await query.edit_message_text("⏳ در حال دریافت لیست...")
            stats = await self.tron_api.get_api_stats()
            
            if stats['total_keys'] == 0:
                text = texts['no_keys']
            else:
                text = f"{texts['key_list']} ({stats['active_keys']}/{stats['total_keys']} فعال)\n\n"
                for key, data in stats['keys'].items():
                    status = "🟢 فعال" if data['active'] else "🔴 غیرفعال"
                    text += f"🔑 `{data['key_preview']}` - {status}\n"
                    text += f"   📥{data['requests']} ✅{data['success']} ❌{data['errors']} ⚖️{data['weight']:.1f}\n"
                    text += f"   ⏱️ {data['response_time_avg']:.2f}s\n\n"
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]]), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'api_stats' and user_id == ADMIN_ID:
            stats = await self.tron_api.get_api_stats()
            text = f"📊 **آمار کلیدها**\n\n"
            text += f"📌 کل کلیدها: {stats['total_keys']}\n"
            text += f"✅ فعال: {stats['active_keys']}\n"
            text += f"📥 درخواست‌ها: {stats['total_requests']:,}\n"
            text += f"✅ موفقیت: {stats['total_success']:,}\n"
            text += f"❌ خطاها: {stats['total_errors']:,}\n"
            text += f"📈 نرخ موفقیت: {stats['success_rate']:.2f}%\n"
            text += f"⏱️ زمان فعالیت: {int(stats['uptime_seconds'] // 3600)} ساعت"
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]]), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'toggle_key' and user_id == ADMIN_ID:
            await query.edit_message_text(
                "🔄 **فعال/غیرفعال کردن کلید**\n\n"
                "لطفا کلید مورد نظر را ارسال کنید:",
                parse_mode=ParseMode.MARKDOWN
            )
            self.user_states[user_id] = 'waiting_for_toggle_key'
        
        elif data == 'delete_key' and user_id == ADMIN_ID:
            await query.edit_message_text(
                "🗑️ **حذف کلید**\n\n"
                "⚠️ این عمل غیرقابل بازگشت است!\n\n"
                "لطفا کلید مورد نظر را ارسال کنید:",
                parse_mode=ParseMode.MARKDOWN
            )
            self.user_states[user_id] = 'waiting_for_delete_key'
        
        elif data == 'db_stats' and user_id == ADMIN_ID:
            await query.edit_message_text("⏳ در حال دریافت آمار...")
            stats = await self.db.get_db_stats()
            
            text = f"📊 **آمار دیتابیس و کش**\n\n"
            text += f"🗄️ **ساختار:**\n"
            text += f"• تعداد شاردها: {stats['shard_count']}\n"
            text += f"• کل کاربران: {stats['total_users']:,}\n"
            text += f"• کل لینک‌ها: {stats['total_links']:,}\n"
            text += f"• کل تراکنش‌ها: {stats['total_transactions']:,}\n\n"
            text += f"💾 **کش:**\n"
            text += f"• آیتم‌های کش: {stats['cache']['total_items']:,}\n"
            text += f"• ظرفیت کش: {stats['cache']['max_size']:,}\n"
            text += f"• نرخ موفقیت: {stats['cache']['hit_rate']:.2f}%\n"
            text += f"• تعداد بازدید: {stats['cache']['hits']:,}\n"
            text += f"• تعداد عدم موفقیت: {stats['cache']['misses']:,}"
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data='db_stats')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
            ]), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'make_paid' and user_id == ADMIN_ID:
            await self.db.set_system_setting('is_paid', '1')
            await query.edit_message_text(
                texts['paid_mode'],
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]])
            )
        
        elif data == 'make_free' and user_id == ADMIN_ID:
            await self.db.set_system_setting('is_paid', '0')
            await query.edit_message_text(
                texts['free_mode'],
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]])
            )
        
        elif data == 'broadcast' and user_id == ADMIN_ID:
            await query.edit_message_text(
                "📢 **ارسال پیام همگانی**\n\n"
                "لطفا پیام خود را ارسال کنید (متن، عکس یا ویدیو):\n\n"
                "⚠️ پیام به **همه کاربران** ربات ارسال خواهد شد.",
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'waiting_for_broadcast'
        
        elif data == 'verify_payments' and user_id == ADMIN_ID:
            pending_txs = await self.db.get_pending_manual_transactions()
            
            if not pending_txs:
                await query.edit_message_text(
                    "✅ هیچ پرداخت در انتظار تاییدی وجود ندارد",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]])
                )
                return
            
            text = "📋 **پرداخت‌های نیازمند بررسی:**\n\n"
            for tx in pending_txs[:10]:
                text += f"👤 {tx['first_name']} (@{tx['username']})\n"
                text += f"💰 {tx['amount']} USDT\n"
                text += f"🔗 `{tx['tx_hash'][:20]}...`\n"
                text += f"📅 {tx['created_at'][:16]}\n\n"
            
            buttons = []
            for tx in pending_txs[:10]:
                buttons.append([
                    InlineKeyboardButton(f"✅ {tx['first_name']}", callback_data=f"approve_manual_{tx['tx_hash']}"),
                    InlineKeyboardButton(f"❌ {tx['first_name']}", callback_data=f"reject_manual_{tx['tx_hash']}")
                ])
            buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.MARKDOWN)
        
        elif data.startswith('approve_manual_') or data.startswith('reject_manual_'):
            if user_id != ADMIN_ID:
                await query.edit_message_text("⛔ دسترسی غیرمجاز")
                return
            
            parts = data.split('_')
            action = parts[0]
            tx_hash = parts[2]
            
            if action == 'approve':
                await self.db.verify_transaction(tx_hash, 'approved')
                async with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT user_id FROM transactions WHERE tx_hash = ?", (tx_hash,))
                    result = cursor.fetchone()
                    if result:
                        await self.db.update_user_subscription(result['user_id'])
                        await context.bot.send_message(result['user_id'], "✅ اشتراک شما فعال شد! 🎉")
                await query.edit_message_text(
                    f"✅ تراکنش {tx_hash[:20]}... تایید شد",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='verify_payments')]])
                )
            else:
                await self.db.verify_transaction(tx_hash, 'rejected')
                await query.edit_message_text(
                    f"❌ تراکنش {tx_hash[:20]}... رد شد",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='verify_payments')]])
                )
        
        elif data == 'back':
            texts = self.get_texts(lang)
            keyboard = [
                [InlineKeyboardButton(texts['register_link'], callback_data='register_link')],
                [InlineKeyboardButton(texts['view_links'], callback_data='view_links')],
                [InlineKeyboardButton(texts['my_stats'], callback_data='my_stats')],
                [InlineKeyboardButton(texts['referral'], callback_data='referral')],
                [InlineKeyboardButton(texts['change_language'], callback_data='change_language')],
                [InlineKeyboardButton("🚀 ضریب بازدید", callback_data='boost_info')]
            ]
            challenge_active = await self.db.get_system_setting('challenge_active')
            if challenge_active == '1':
                keyboard.append([InlineKeyboardButton("🏆 چالش رفرال", callback_data='referral_challenge')])
            if user_id == ADMIN_ID:
                keyboard.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data='admin_panel')])
            
            await query.edit_message_text(
                texts['welcome'].format(first_name=db_user.get('first_name', 'کاربر')),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
    
    # ===== بخش مدیریت پیام‌ها =====
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text
        state = self.user_states.get(user_id)
        
        # ===== ثبت برند =====
        if state == 'waiting_for_brand' and user_id == ADMIN_ID:
            if text == '/cancel':
                await update.message.reply_text(
                    "✅ عملیات لغو شد",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='brand_settings')]])
                )
                self.user_states[user_id] = None
                return
            
            brand_name = text.strip()
            if len(brand_name) < 2:
                await update.message.reply_text(
                    "❌ نام برند باید حداقل ۲ کاراکتر باشد!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='brand_settings')]])
                )
                return
            
            await self.db.set_brand(brand_name)
            
            # تولید یک نمونه کد
            sample_code = self.db.generate_unique_code(8)
            full_sample = self.db.get_full_unique_code(sample_code)
            
            await update.message.reply_text(
                TEXTS['fa']['brand_set'].format(brand=brand_name, code=full_sample),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='brand_settings')]]),
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = None
        
        # ===== چالش رفرال =====
        elif state == 'waiting_for_challenge_duration' and user_id == ADMIN_ID:
            if text == '/cancel':
                await update.message.reply_text("✅ عملیات لغو شد", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]))
                self.user_states[user_id] = None
                return
            
            try:
                duration = int(text.strip())
                if duration <= 0:
                    raise ValueError
                
                reward = int(await self.db.get_system_setting('challenge_reward') or '100')
                top_users = int(await self.db.get_system_setting('challenge_top_users') or '10')
                
                success, msg = await self.db.start_referral_challenge(duration, reward, top_users)
                
                if success:
                    users = await self.db.get_all_users()
                    for uid in users[:100]:
                        try:
                            user_lang = (await self.db.get_user(uid))['language'] if await self.db.get_user(uid) else 'fa'
                            u_texts = self.get_texts(user_lang)
                            await context.bot.send_message(uid, u_texts['challenge_started'].format(duration=duration, reward=reward, top_users=top_users), parse_mode=ParseMode.HTML)
                            await asyncio.sleep(0.05)
                        except:
                            pass
                    
                    await update.message.reply_text(
                        f"✅ **چالش رفرال شروع شد!**\n\n📅 مدت: {duration} روز\n🎁 جایزه: {reward} USDT\n👥 برندگان: {top_users} نفر\n\n📢 پیام به کاربران ارسال شد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]),
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        f"❌ {msg}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]])
                    )
            except ValueError:
                await update.message.reply_text(
                    TEXTS['fa']['invalid_duration'],
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]])
                )
            
            self.user_states[user_id] = None
        
        elif state == 'waiting_for_reward_amount' and user_id == ADMIN_ID:
            if text == '/cancel':
                await update.message.reply_text("✅ لغو شد", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]))
                self.user_states[user_id] = None
                return
            
            try:
                amount = int(text.strip())
                if amount <= 0:
                    raise ValueError
                
                await self.db.set_system_setting('challenge_reward', str(amount))
                await update.message.reply_text(
                    TEXTS['fa']['challenge_reward_set'].format(amount=amount),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]),
                    parse_mode=ParseMode.HTML
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ لطفا یک عدد معتبر وارد کنید",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]])
                )
            
            self.user_states[user_id] = None
        
        elif state == 'waiting_for_top_users' and user_id == ADMIN_ID:
            if text == '/cancel':
                await update.message.reply_text("✅ لغو شد", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]))
                self.user_states[user_id] = None
                return
            
            try:
                count = int(text.strip())
                if count <= 0:
                    raise ValueError
                
                await self.db.set_system_setting('challenge_top_users', str(count))
                await update.message.reply_text(
                    TEXTS['fa']['challenge_top_users_set'].format(count=count),
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]]),
                    parse_mode=ParseMode.HTML
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ لطفا یک عدد معتبر وارد کنید",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_challenge')]])
                )
            
            self.user_states[user_id] = None
        
        # ===== مدیریت کلیدهای API =====
        elif state == 'waiting_for_new_api_key' and user_id == ADMIN_ID:
            if text == '/cancel':
                await update.message.reply_text("✅ عملیات لغو شد", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]]))
                self.user_states[user_id] = None
                return
            
            await update.message.reply_text("⏳ در حال تست کلید...")
            
            success, message = await self.tron_api.add_api_key(text.strip())
            
            if success:
                await self.db.save_api_key(text.strip(), f"اضافه شده در {datetime.now()}")
                await update.message.reply_text(
                    f"✅ **کلید جدید با موفقیت ثبت شد!**\n\n🔑 کلید: `{text.strip()[:20]}...`\n📊 وضعیت: فعال",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]]),
                    parse_mode=ParseMode.MARKDOWN
                )
                
                stats = await self.tron_api.get_api_stats()
                await update.message.reply_text(
                    f"📊 **آمار کلیدها:**\n📌 کل کلیدها: {stats['total_keys']}\n✅ کلیدهای فعال: {stats['active_keys']}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]]),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    f"❌ **خطا:** {message}\n\nلطفا کلید معتبر دیگری ارسال کنید.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            self.user_states[user_id] = None
        
        elif state == 'waiting_for_toggle_key' and user_id == ADMIN_ID:
            if text == '/cancel':
                await update.message.reply_text("✅ لغو شد", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]]))
                self.user_states[user_id] = None
                return
            
            success, message = await self.tron_api.toggle_api_key(text.strip())
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]])
            )
            self.user_states[user_id] = None
        
        elif state == 'waiting_for_delete_key' and user_id == ADMIN_ID:
            if text == '/cancel':
                await update.message.reply_text("✅ لغو شد", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]]))
                self.user_states[user_id] = None
                return
            
            success, message = await self.tron_api.remove_api_key(text.strip())
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='manage_keys')]])
            )
            self.user_states[user_id] = None
        
        # ===== آدرس مبدا پرداخت =====
        elif state == 'waiting_for_source_address':
            address = text.strip()
            if len(address) < 30 or len(address) > 50:
                await update.message.reply_text("❌ آدرس نامعتبر است")
                return
            
            await self.db.set_user_payment_address(user_id, address)
            lang = (await self.db.get_user(user_id))['language']
            texts = self.get_texts(lang)
            
            await update.message.reply_text(
                texts['source_address_saved'].format(wallet=OWNER_WALLET),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ پرداخت کردم", callback_data='confirm_payment')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ]),
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = None
        
        # ===== ثبت لینک یوتیوب با کد یکتا =====
        elif state == 'waiting_for_link':
            if not text.startswith('http') or ('youtube.com' not in text and 'youtu.be' not in text):
                await update.message.reply_text("❌ لطفا یک لینک معتبر یوتیوب ارسال کنید")
                return
            
            # بررسی مجدد قابلیت ثبت
            can_register, msg = await self.db.can_register_link(user_id)
            if not can_register:
                await update.message.reply_text(f"⚠️ {msg}")
                self.user_states[user_id] = None
                return
            
            success, result = await self.db.add_youtube_link(user_id, text)
            
            if not success:
                await update.message.reply_text(f"❌ {result}")
                self.user_states[user_id] = None
                return
            
            # ===== ثبت موفق =====
            full_code = result  # کد کامل با برند
            required = self.db.get_daily_required_interactions()
            
            await update.message.reply_text(
                f"✅ **لینک شما با موفقیت ثبت شد!**\n\n"
                f"🔑 کد یکتا: <code>{full_code}</code>\n\n"
                f"📌 این کد را روی ویدیو خود بنویسید.\n"
                f"📌 کاربران برای بازدید باید این کد را وارد کنند.\n\n"
                f"📊 برای تکمیل ثبت، {required} لینک دیگران را بازدید کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👀 مشاهده لینک‌ها", callback_data='view_links')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ]),
                parse_mode=ParseMode.HTML
            )
            
            self.user_states[user_id] = None
        
        # ===== وارد کردن کد یکتا برای بازدید =====
        elif state == 'waiting_for_unique_code':
            # استخراج کد
            code = text.strip()
            
            # بررسی کد
            success, msg, link_data = await self.db.verify_unique_code(user_id, code)
            
            if not success:
                await update.message.reply_text(
                    f"❌ {msg}\n\n"
                    "📌 لطفا کد را دقیق وارد کنید.\n"
                    "🔑 کدها به صورت زیر هستند:\n"
                    "• <code>AbCdEfGhIjKl</code> (بدون برند)\n"
                    f"• <code>{self.db.get_full_unique_code('AbCdEfGhIjKl')}</code> (با برند)",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # ثبت موفق
            stats = await self.db.get_user_daily_stats(user_id)
            required = stats['required']
            interactions = stats['interactions']
            
            await update.message.reply_text(
                f"✅ {msg}\n\n"
                f"📊 شما {interactions}/{required} تعامل امروز را انجام داده‌اید.\n"
                f"🎬 ویدیو: {link_data.get('video_url', '')[:50]}...\n"
                f"👤 صاحب ویدیو: {link_data.get('first_name', 'کاربر')}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👀 ادامه بازدید", callback_data='view_links')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ]),
                parse_mode=ParseMode.HTML
            )
            
            self.user_states[user_id] = None
        
        # ===== هش تراکنش دستی =====
        elif state == 'waiting_for_manual_hash':
            tx_hash = text.strip()
            if len(tx_hash) != 64:
                await update.message.reply_text("❌ هش نامعتبر است")
                return
            
            async with self.db.get_connection(user_id) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO transactions (user_id, tx_hash, amount, manual_review) VALUES (?, ?, ?, 1)", (user_id, tx_hash, SUBSCRIPTION_PRICE_USD))
                conn.commit()
            
            lang = (await self.db.get_user(user_id))['language']
            texts = self.get_texts(lang)
            
            await update.message.reply_text(texts['hash_received'], parse_mode=ParseMode.HTML)
            await context.bot.send_message(ADMIN_ID, f"🔔 درخواست بررسی دستی:\n👤 {update.effective_user.first_name}\n🆔 {user_id}\n🔗 `{tx_hash[:20]}...`", parse_mode=ParseMode.MARKDOWN)
            self.user_states[user_id] = None
        
        # ===== پیام همگانی =====
        elif state == 'waiting_for_broadcast' and user_id == ADMIN_ID:
            await update.message.reply_text("⏳ در حال ارسال پیام همگانی...")
            
            users = await self.db.get_all_users()
            
            if not users:
                await update.message.reply_text(
                    "❌ هیچ کاربری برای ارسال پیام وجود ندارد!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]])
                )
                self.user_states[user_id] = None
                return
            
            await update.message.reply_text(f"📊 تعداد کل کاربران: {len(users)} نفر\n⏳ در حال ارسال...")
            
            success_count = 0
            fail_count = 0
            
            for i, uid in enumerate(users):
                try:
                    if update.message.photo:
                        await context.bot.send_photo(
                            uid, 
                            update.message.photo[-1].file_id, 
                            caption=update.message.caption or ""
                        )
                    elif update.message.video:
                        await context.bot.send_video(
                            uid, 
                            update.message.video.file_id, 
                            caption=update.message.caption or ""
                        )
                    else:
                        await context.bot.send_message(
                            uid, 
                            update.message.text or "", 
                            parse_mode=ParseMode.HTML
                        )
                    success_count += 1
                    
                    if i % 30 == 0 and i > 0:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"خطا در ارسال به {uid}: {e}")
                    fail_count += 1
                
                if (i + 1) % 100 == 0:
                    await update.message.reply_text(f"📊 {i+1}/{len(users)} ارسال شد...")
            
            await update.message.reply_text(
                f"✅ **پیام همگانی با موفقیت ارسال شد!**\n\n"
                f"👤 موفق: {success_count} نفر\n"
                f"❌ ناموفق: {fail_count} نفر\n"
                f"📊 مجموع: {len(users)} نفر",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]])
            )
            
            logger.info(f"📢 پیام همگانی ارسال شد: {success_count} موفق، {fail_count} ناموفق")
            self.user_states[user_id] = None
        
        else:
            # بررسی اگر کاربر برنده چالش است
            winner = await self.db.get_challenge_winner_by_user(user_id)
            if winner:
                address = text.strip()
                if len(address) >= 30 and len(address) <= 50:
                    await self.db.set_user_reward_address(user_id, address)
                    
                    lang = (await self.db.get_user(user_id))['language']
                    texts = self.get_texts(lang)
                    
                    await update.message.reply_text(
                        texts['address_received'].format(address=address, reward=winner['reward_amount']),
                        parse_mode=ParseMode.HTML
                    )
                    
                    await context.bot.send_message(
                        ADMIN_ID,
                        f"💰 **درخواست دریافت جایزه**\n\n"
                        f"👤 {update.effective_user.first_name}\n"
                        f"🆔 {user_id}\n"
                        f"🔗 آدرس: `{address}`\n"
                        f"💰 مبلغ: {winner['reward_amount']} USDT\n\n"
                        f"📌 برای تایید پرداخت به پنل مدیریت بروید.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text("❌ آدرس نامعتبر است. لطفا آدرس TRC20 معتبر ارسال کنید.")
                return
            
            await update.message.reply_text("برای شروع /start را بزنید")


# ==================== اجرای ربات ====================
async def main():
    bot = YouTubeEarningBot(BOT_TOKEN)
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, bot.handle_message))
    
    await application.initialize()
    await application.start()
    
    logger.info("✅ ربات با موفقیت راه‌اندازی شد!")
    
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await bot.tron_api.close()


if __name__ == "__main__":
    asyncio.run(main())
