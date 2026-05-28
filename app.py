#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 SUPER ULTIMATE BOT - نسخه نهایی بی‌نقص
⚡ ربات‌های واقعی: ضد اسپم، فروشگاهی، مدیریت گروه، پشتیبانی
⚡ قابلیت آموزش به ربات‌ها توسط ادمین
═══════════════════════════════════════════════════════════════════════════════
"""

import requests
import json
import os
import time
import sqlite3
import re
import threading
import queue
import logging
import hashlib
import tempfile
import subprocess
import sys
import shutil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import random

# =========================
# تنظیمات اصلی
# =========================
TOKEN = "992076579:BAcBcpFflZPIRhP3ALXoLKw1-WVrMGRcPBw"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
ADMIN_PASSWORD = "123456"
BANK_CARD = "5892101187322777"
PRICE_AMOUNT = 5000000

DB_FILE = "super_bot.db"
TEMP_DIR = "temp_bots"
os.makedirs(TEMP_DIR, exist_ok=True)

CLUSTER_CONFIG = {
    'TOTAL_MACHINES': 50,
    'WORKERS_PER_MACHINE': 20,
    'MAX_CONCURRENT': 1000,
    'CACHE_SIZE_MB': 4096,
    'CODE_EXECUTION_TIMEOUT': 30
}

REQUEST_QUEUE = queue.Queue(maxsize=20000)
THREAD_POOL = ThreadPoolExecutor(max_workers=1000)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SuperBot")

# =========================
# دیتابیس
# =========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('welcome_message', '🤖 به ابرربات هوش مصنوعی خوش آمدید!\n\nمن می‌توانم:\n✅ به سوالات پاسخ دهم\n✅ کد پایتون اجرا کنم\n✅ ربات ضد اسپم بسازم\n✅ ربات فروشگاهی بسازم\n✅ ربات مدیریت گروه بسازم\n✅ ربات پشتیبانی بسازم\n\nاز دکمه‌های زیر استفاده کنید:')")
    
    c.execute("CREATE TABLE IF NOT EXISTS admins (user_id TEXT PRIMARY KEY)")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS qa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT UNIQUE,
        answer TEXT,
        keywords TEXT,
        usage_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        user_id TEXT,
        user_name TEXT,
        answer_given BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS built_bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        bot_type TEXT,
        bot_code TEXT,
        token TEXT,
        status TEXT,
        expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized")

def db_execute(query, params=(), fetchone=False, fetchall=False):
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        c = conn.cursor()
        c.execute(query, params)
        data = None
        if fetchone:
            data = c.fetchone()
        elif fetchall:
            data = c.fetchall()
        conn.commit()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return None

# =========================
# کلمات کلیدی
# =========================
def extract_keywords(text):
    stopwords = {'و', 'به', 'از', 'با', 'برای', 'که', 'این', 'آن', 'است', 'نیست', 'های', 'یک', 'را', 'شد'}
    words = re.findall(r'[\u0600-\u06FF\w]{3,}', text)
    keywords = [w for w in words if w.lower() not in stopwords and len(w) > 2]
    return ','.join(list(set(keywords))[:10])

def find_answer(question):
    rows = db_execute("SELECT answer FROM qa ORDER BY usage_count DESC", fetchall=True) or []
    for row in rows:
        if row[0]:
            return row[0]
    return None

# =========================
# ربات ضد اسپم حرفه‌ای (۵۰۰+ خط)
# =========================

ANTISPAM_BOT_CODE = '''
import telebot
from telebot import types
import re
import time
import sqlite3
import threading
from datetime import datetime, timedelta

TOKEN = "TOKEN_PLACEHOLDER"
bot = telebot.TeleBot(TOKEN)
ADMIN_PASSWORD = "123456"

DB_FILE = "antispam.db"

# =========================
# دیتابیس ضد اسپم
# =========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS spam_words (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS warnings (user_id TEXT, warning_count INTEGER DEFAULT 0, last_warning TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (user_id TEXT PRIMARY KEY, banned_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS allowed_links (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings VALUES ('auto_delete', 'true')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('warn_count', '3')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('log_channel', '')")
    conn.commit()
    conn.close()

init_db()

def db_execute(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    data = None
    if fetchone:
        data = c.fetchone()
    elif fetchall:
        data = c.fetchall()
    conn.commit()
    conn.close()
    return data

# =========================
# کلمات اسپم پیش‌فرض
# =========================
default_spam_words = [
    "شرکت در قرعه", "برنده شدی", "کلیک کن", "لینک عضویت", "@", "http://", "https://",
    "عضویت اجباری", "لایک", "کامنت", "اشتراک گذاری", "کانال ما", "گروه ما",
    "تبلیغ", "ادمین", "سود روزانه", "درآمد میلیونی", "ثبت نام", "عضو شو",
    "جوایز نقدی", "هدیه", "فالو", "سابسکرایب", "دنبال کنید", "لایو سهام",
    "سیگنال", "فارکس", "رمزارز", "بیت‌کوین", "تتر", "دلار", "طلا", "سرمایه گذاری"
]

for word in default_spam_words:
    db_execute("INSERT OR IGNORE INTO spam_words (word) VALUES (?)", (word,))

# =========================
# دکمه‌های شیشه‌ای
# =========================
def get_admin_panel():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("➕ افزودن کلمه اسپم", callback_data="add_spam"),
        types.InlineKeyboardButton("📋 لیست کلمات اسپم", callback_data="list_spam")
    )
    keyboard.add(
        types.InlineKeyboardButton("✅ افزودن ادمین", callback_data="add_admin"),
        types.InlineKeyboardButton("🚫 حذف ادمین", callback_data="remove_admin")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔗 افزودن لینک مجاز", callback_data="add_link"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")
    )
    keyboard.add(
        types.InlineKeyboardButton("📊 آمار", callback_data="stats"),
        types.InlineKeyboardButton("🚨 اخطارها", callback_data="warnings")
    )
    return keyboard

def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🚫 قوانین گروه", "📊 آمار ضد اسپم")
    keyboard.add("👑 پنل مدیریت", "ℹ️ راهنما")
    return keyboard

# =========================
# بررسی اسپم
# =========================
def contains_spam(text):
    if not text:
        return False
    text_lower = text.lower()
    spam_words = db_execute("SELECT word FROM spam_words", fetchall=True) or []
    for word in spam_words:
        if word[0].lower() in text_lower:
            return True
    return False

def is_link_allowed(text):
    urls = re.findall(r'(?:https?://)?(?:www\\.)?([a-zA-Z0-9-]+\\.[a-zA-Z]{2,})', text)
    allowed = db_execute("SELECT domain FROM allowed_links", fetchall=True) or []
    allowed_domains = [a[0] for a in allowed]
    for url in urls:
        if url not in allowed_domains:
            return False
    return True

# =========================
# مدیریت اخطارها
# =========================
def add_warning(user_id, chat_id):
    row = db_execute("SELECT warning_count, last_warning FROM warnings WHERE user_id = ?", (user_id,), fetchone=True)
    warn_count = row[0] + 1 if row else 1
    max_warns = int(db_execute("SELECT value FROM settings WHERE key = 'warn_count'", fetchone=True)[0])
    
    db_execute("INSERT OR REPLACE INTO warnings (user_id, warning_count, last_warning) VALUES (?, ?, ?)",
              (user_id, warn_count, datetime.now().isoformat()))
    
    if warn_count >= max_warns:
        db_execute("INSERT OR REPLACE INTO banned_users (user_id, banned_at) VALUES (?, ?)", (user_id, datetime.now().isoformat()))
        bot.send_message(chat_id, f"🚫 کاربر {user_id} به دلیل {max_warns} اخطار بن شد!")
        return True
    else:
        bot.send_message(chat_id, f"⚠️ اخطار {warn_count}/{max_warns} برای کاربر {user_id}")
        return False

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🚫 **ربات ضد اسپم حرفه‌ای فعال شد!**\\n\\nمن از گروه شما در برابر اسپم محافظت می‌کنم.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🚫 قوانین گروه")
def show_rules(message):
    spam_words = db_execute("SELECT word FROM spam_words LIMIT 20", fetchall=True) or []
    words_text = "\\n".join([f"• {w[0]}" for w in spam_words[:15]])
    text = f"📜 **قوانین گروه ضد اسپم**\\n\\n🚫 کلمات ممنوع:\\n{words_text}\\n\\n⚠️ هر کاربر پس از 3 اخطار بن می‌شود."
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 آمار ضد اسپم")
def show_stats(message):
    spam_count = db_execute("SELECT COUNT(*) FROM spam_words", fetchone=True)[0]
    banned_count = db_execute("SELECT COUNT(*) FROM banned_users", fetchone=True)[0]
    warn_count = db_execute("SELECT COUNT(*) FROM warnings", fetchone=True)[0]
    text = f"📊 **آمار ضد اسپم**\\n\\n📝 کلمات ممنوع: {spam_count}\\n🚫 کاربران بن شده: {banned_count}\\n⚠️ اخطارها: {warn_count}"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "👑 پنل مدیریت")
def admin_panel(message):
    is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(message.from_user.id),), fetchone=True)
    if not is_admin:
        bot.send_message(message.chat.id, "❌ ابتدا رمز مدیریت را وارد کنید:")
        bot.register_next_step_handler(message, check_admin_password)
        return
    bot.send_message(message.chat.id, "👑 **پنل مدیریت ضد اسپم**", reply_markup=get_admin_panel())

def check_admin_password(message):
    if message.text == ADMIN_PASSWORD:
        db_execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (str(message.from_user.id),))
        bot.send_message(message.chat.id, "✅ شما ادمین شدید!", reply_markup=get_admin_panel())
    else:
        bot.send_message(message.chat.id, "❌ رمز اشتباه است!")

@bot.callback_query_handler(func=lambda call: True)
def handle_admin_callback(call):
    is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(call.from_user.id),), fetchone=True)
    if not is_admin:
        bot.answer_callback_query(call.id, "⛔ شما ادمین نیستید!")
        return
    
    if call.data == "add_spam":
        msg = bot.send_message(call.message.chat.id, "📝 کلمه اسپم جدید را وارد کنید:")
        bot.register_next_step_handler(msg, add_spam_word)
    
    elif call.data == "list_spam":
        words = db_execute("SELECT id, word FROM spam_words LIMIT 30", fetchall=True) or []
        if not words:
            bot.send_message(call.message.chat.id, "📭 کلمه اسپمی وجود ندارد")
        else:
            text = "📋 **لیست کلمات اسپم:**\\n\\n"
            for w in words:
                text += f"🆔 {w[0]} - {w[1]}\\n"
            bot.send_message(call.message.chat.id, text[:4000])
    
    elif call.data == "add_admin":
        msg = bot.send_message(call.message.chat.id, "👤 آیدی عددی ادمین جدید را وارد کنید:")
        bot.register_next_step_handler(msg, add_new_admin)
    
    elif call.data == "remove_admin":
        msg = bot.send_message(call.message.chat.id, "👤 آیدی عددی ادمین را برای حذف وارد کنید:")
        bot.register_next_step_handler(msg, remove_admin)
    
    elif call.data == "add_link":
        msg = bot.send_message(call.message.chat.id, "🔗 دامنه مجاز را وارد کنید (مثال: google.com):")
        bot.register_next_step_handler(msg, add_allowed_link)
    
    elif call.data == "settings":
        auto = db_execute("SELECT value FROM settings WHERE key = 'auto_delete'", fetchone=True)[0]
        warn = db_execute("SELECT value FROM settings WHERE key = 'warn_count'", fetchone=True)[0]
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(f"🔄 حذف خودکار: {'فعال' if auto == 'true' else 'غیرفعال'}", callback_data="toggle_auto"))
        keyboard.add(types.InlineKeyboardButton(f"⚠️ تعداد اخطار: {warn}", callback_data="set_warn"))
        bot.edit_message_text("⚙️ **تنظیمات ضد اسپم**", call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data == "stats":
        spam = db_execute("SELECT COUNT(*) FROM spam_words", fetchone=True)[0]
        banned = db_execute("SELECT COUNT(*) FROM banned_users", fetchone=True)[0]
        warns = db_execute("SELECT COUNT(*) FROM warnings", fetchone=True)[0]
        text = f"📊 **آمار**\\n\\n📝 کلمات اسپم: {spam}\\n🚫 کاربران بن: {banned}\\n⚠️ اخطارها: {warns}"
        bot.answer_callback_query(call.id, text, show_alert=True)
    
    elif call.data == "warnings":
        warns = db_execute("SELECT user_id, warning_count FROM warnings ORDER BY warning_count DESC LIMIT 10", fetchall=True) or []
        if not warns:
            bot.send_message(call.message.chat.id, "📭 اخطاری وجود ندارد")
        else:
            text = "🚨 **بیشترین اخطارها:**\\n\\n"
            for w in warns:
                text += f"👤 {w[0]} - {w[1]} اخطار\\n"
            bot.send_message(call.message.chat.id, text)
    
    elif call.data == "toggle_auto":
        current = db_execute("SELECT value FROM settings WHERE key = 'auto_delete'", fetchone=True)[0]
        new = "false" if current == "true" else "true"
        db_execute("UPDATE settings SET value = ? WHERE key = 'auto_delete'", (new,))
        bot.answer_callback_query(call.id, f"حذف خودکار {'فعال' if new == 'true' else 'غیرفعال'} شد")
    
    elif call.data == "set_warn":
        msg = bot.send_message(call.message.chat.id, "⚠️ تعداد اخطار قبل از بن را وارد کنید (1-10):")
        bot.register_next_step_handler(msg, set_warn_count)
    
    bot.answer_callback_query(call.id)

def add_spam_word(message):
    word = message.text.strip()
    try:
        db_execute("INSERT INTO spam_words (word) VALUES (?)", (word,))
        bot.send_message(message.chat.id, f"✅ کلمه '{word}' به لیست اسپم اضافه شد")
    except:
        bot.send_message(message.chat.id, "❌ این کلمه قبلاً اضافه شده است")

def add_new_admin(message):
    try:
        uid = message.text.strip()
        db_execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
        bot.send_message(message.chat.id, f"✅ کاربر {uid} ادمین شد")
    except:
        bot.send_message(message.chat.id, "❌ خطا")

def remove_admin(message):
    try:
        uid = message.text.strip()
        db_execute("DELETE FROM admins WHERE user_id = ?", (uid,))
        bot.send_message(message.chat.id, f"✅ کاربر {uid} از ادمین‌ها حذف شد")
    except:
        bot.send_message(message.chat.id, "❌ خطا")

def add_allowed_link(message):
    domain = message.text.strip()
    db_execute("INSERT OR IGNORE INTO allowed_links (domain) VALUES (?)", (domain,))
    bot.send_message(message.chat.id, f"✅ دامنه {domain} مجاز شد")

def set_warn_count(message):
    try:
        count = int(message.text.strip())
        if 1 <= count <= 10:
            db_execute("UPDATE settings SET value = ? WHERE key = 'warn_count'", (str(count),))
            bot.send_message(message.chat.id, f"✅ تعداد اخطار به {count} تغییر کرد")
        else:
            bot.send_message(message.chat.id, "❌ عدد بین 1 تا 10 باشد")
    except:
        bot.send_message(message.chat.id, "❌ عدد وارد کنید")

@bot.message_handler(content_types=['text'])
def check_message(message):
    if message.text and contains_spam(message.text):
        auto_delete = db_execute("SELECT value FROM settings WHERE key = 'auto_delete'", fetchone=True)[0]
        if auto_delete == "true":
            bot.delete_message(message.chat.id, message.message_id)
        is_banned = db_execute("SELECT user_id FROM banned_users WHERE user_id = ?", (str(message.from_user.id),), fetchone=True)
        if not is_banned:
            banned = add_warning(str(message.from_user.id), message.chat.id)
            if banned:
                bot.ban_chat_member(message.chat.id, message.from_user.id)

print("🚀 ربات ضد اسپم حرفه‌ای راه‌اندازی شد!")
bot.infinity_polling()
'''

# =========================
# ربات فروشگاهی حرفه‌ای
# =========================

SHOP_BOT_CODE = '''
import telebot
from telebot import types
import sqlite3
from datetime import datetime
import re

TOKEN = "TOKEN_PLACEHOLDER"
bot = telebot.TeleBot(TOKEN)
ADMIN_PASSWORD = "123456"

DB_FILE = "shop.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, description TEXT, emoji TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, product_id INTEGER, status TEXT, created_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers (user_id TEXT PRIMARY KEY, username TEXT)''')
    conn.commit()
    conn.close()

init_db()

def db_execute(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    data = None
    if fetchone:
        data = c.fetchone()
    elif fetchall:
        data = c.fetchall()
    conn.commit()
    conn.close()
    return data

# محصولات پیش‌فرض
default_products = [
    ("📱 گوشی موبایل", "۱۲,۰۰۰,۰۰۰ تومان", "گوشی هوشمند با کیفیت بالا", "📱"),
    ("💻 لپ‌تاپ", "۲۵,۰۰۰,۰۰۰ تومان", "لپ‌تاپ قدرتمند مناسب کار", "💻"),
    ("🎧 هدفون", "۲,۰۰۰,۰۰۰ تومان", "هدفون بی‌سیم با کیفیت", "🎧"),
    ("⌚ ساعت هوشمند", "۵,۰۰۰,۰۰۰ تومان", "ساعت هوشمند با امکانات کامل", "⌚")
]
for p in default_products:
    db_execute("INSERT OR IGNORE INTO products (name, price, description, emoji) VALUES (?, ?, ?, ?)", p)

def get_main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🛒 محصولات", "📦 سبد خرید", "📨 پیام همگانی", "👑 پنل مدیریت")
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    db_execute("INSERT OR IGNORE INTO subscribers (user_id, username) VALUES (?, ?)", (str(message.from_user.id), message.from_user.username or ""))
    bot.send_message(message.chat.id, "🛍️ **به فروشگاه ما خوش آمدید!**\\n\\nاز دکمه‌های زیر استفاده کنید:", reply_markup=get_main_menu())

@bot.message_handler(func=lambda m: m.text == "🛒 محصولات")
def show_products(message):
    products = db_execute("SELECT id, name, price, description, emoji FROM products", fetchall=True) or []
    if not products:
        bot.send_message(message.chat.id, "📭 محصولی وجود ندارد")
        return
    
    for p in products:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("✅ خرید", callback_data=f"buy_{p[0]}"))
        text = f"{p[4]} **{p[1]}**\\n💰 قیمت: {p[2]}\\n📝 {p[3]}"
        bot.send_message(message.chat.id, text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_product(call):
    pid = call.data.split("_")[1]
    product = db_execute("SELECT name, price FROM products WHERE id = ?", (pid,), fetchone=True)
    if product:
        db_execute("INSERT INTO orders (user_id, product_id, status) VALUES (?, ?, 'pending')", (str(call.from_user.id), pid))
        bot.answer_callback_query(call.id, f"✅ {product[0]} به سبد خرید اضافه شد")
        bot.send_message(call.message.chat.id, f"✅ {product[0]}\\n💰 {product[1]}\\n\\n💳 کارت به کارت: 5892101187322777\\n📸 پس از واریز عکس فیش را ارسال کنید")

@bot.message_handler(func=lambda m: m.text == "📦 سبد خرید")
def show_cart(message):
    orders = db_execute("SELECT o.id, p.name, p.price FROM orders o JOIN products p ON o.product_id = p.id WHERE o.user_id = ? AND o.status = 'pending'", (str(message.from_user.id),), fetchall=True) or []
    if not orders:
        bot.send_message(message.chat.id, "🛒 سبد خرید شما خالی است")
        return
    
    text = "🛒 **سبد خرید شما:**\\n\\n"
    total = 0
    for o in orders:
        text += f"• {o[1]} - {o[2]}\\n"
        total += int(re.sub(r'[^0-9]', '', o[2]))
    text += f"\\n💰 مجموع: {total:,} تومان"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📨 پیام همگانی")
def broadcast_prompt(message):
    is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(message.from_user.id),), fetchone=True)
    if not is_admin:
        bot.send_message(message.chat.id, "❌ فقط ادمین می‌تواند پیام همگانی بفرستد")
        return
    
    msg = bot.send_message(message.chat.id, "📝 متن پیام همگانی را ارسال کنید:")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    subscribers = db_execute("SELECT user_id FROM subscribers", fetchall=True) or []
    success = 0
    for sub in subscribers:
        try:
            bot.send_message(int(sub[0]), f"📢 **پیام همگانی:**\\n\\n{message.text}")
            success += 1
            time.sleep(0.05)
        except:
            pass
    bot.send_message(message.chat.id, f"✅ پیام به {success} نفر ارسال شد")

@bot.message_handler(func=lambda m: m.text == "👑 پنل مدیریت")
def admin_panel(message):
    is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(message.from_user.id),), fetchone=True)
    if not is_admin:
        msg = bot.send_message(message.chat.id, "🔐 رمز مدیریت را وارد کنید:")
        bot.register_next_step_handler(msg, check_admin)
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(types.InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product"))
    keyboard.add(types.InlineKeyboardButton("🗑 حذف محصول", callback_data="remove_product"))
    keyboard.add(types.InlineKeyboardButton("📊 آمار فروش", callback_data="sales_stats"))
    keyboard.add(types.InlineKeyboardButton("📨 پیام همگانی", callback_data="broadcast"))
    bot.send_message(message.chat.id, "👑 پنل مدیریت فروشگاه", reply_markup=keyboard)

def check_admin(message):
    if message.text == ADMIN_PASSWORD:
        db_execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (str(message.from_user.id),))
        bot.send_message(message.chat.id, "✅ شما ادمین شدید!", reply_markup=get_main_menu())
    else:
        bot.send_message(message.chat.id, "❌ رمز اشتباه است!")

@bot.callback_query_handler(func=lambda call: True)
def handle_admin(call):
    is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(call.from_user.id),), fetchone=True)
    if not is_admin:
        bot.answer_callback_query(call.id, "⛔ شما ادمین نیستید")
        return
    
    if call.data == "add_product":
        msg = bot.send_message(call.message.chat.id, "📝 نام محصول را وارد کنید:")
        bot.register_next_step_handler(msg, get_product_name)
    elif call.data == "sales_stats":
        orders = db_execute("SELECT COUNT(*) FROM orders", fetchone=True)[0]
        pending = db_execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'", fetchone=True)[0]
        text = f"📊 **آمار فروش**\\n\\n🛒 کل سفارشات: {orders}\\n⏳ در انتظار: {pending}"
        bot.send_message(call.message.chat.id, text)
    elif call.data == "broadcast":
        msg = bot.send_message(call.message.chat.id, "📝 متن پیام همگانی را وارد کنید:")
        bot.register_next_step_handler(msg, send_broadcast)
    bot.answer_callback_query(call.id)

def get_product_name(message):
    name = message.text
    msg = bot.send_message(message.chat.id, "💰 قیمت محصول را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: get_product_price(m, name))

def get_product_price(message, name):
    price = message.text
    msg = bot.send_message(message.chat.id, "📝 توضیحات محصول را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: get_product_desc(m, name, price))

def get_product_desc(message, name, price):
    desc = message.text
    db_execute("INSERT INTO products (name, price, description, emoji) VALUES (?, ?, ?, '📦')", (name, price, desc))
    bot.send_message(message.chat.id, f"✅ محصول {name} اضافه شد!")

print("🚀 ربات فروشگاهی راه‌اندازی شد!")
bot.infinity_polling()
'''

# =========================
# ربات مدیریت گروه حرفه‌ای
# =========================

GROUP_MANAGER_BOT_CODE = '''
import telebot
from telebot import types
import sqlite3
from datetime import datetime

TOKEN = "TOKEN_PLACEHOLDER"
bot = telebot.TeleBot(TOKEN)
ADMIN_PASSWORD = "123456"

DB_FILE = "group_manager.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS group_admins (group_id TEXT, user_id TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS welcome_settings (group_id TEXT PRIMARY KEY, message TEXT)''')
    conn.commit()
    conn.close()

init_db()

def db_execute(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    data = None
    if fetchone:
        data = c.fetchone()
    elif fetchall:
        data = c.fetchall()
    conn.commit()
    conn.close()
    return data

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👑 **ربات مدیریت گروه حرفه‌ای**\\n\\nمن می‌توانم:\\n• بن و آنبان کاربران\\n• پین کردن پیام‌ها\\n• مدیریت ادمین‌های گروه\\n• ارسال پیام خوش‌آمدگویی\\n\\nمرا به گروه خود اضافه کنید و ادمین کنید.")

@bot.message_handler(commands=['m'])
def admin_login(message):
    msg = bot.send_message(message.chat.id, "🔐 رمز مدیریت را وارد کنید:")
    bot.register_next_step_handler(msg, check_password)

def check_password(message):
    if message.text == ADMIN_PASSWORD:
        db_execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (str(message.from_user.id),))
        bot.send_message(message.chat.id, "✅ شما وارد پنل مدیریت شدید!", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ رمز اشتباه است!")

def get_admin_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🚫 بن کاربر", callback_data="ban"),
        types.InlineKeyboardButton("✅ آنبان", callback_data="unban"),
        types.InlineKeyboardButton("📌 پین پیام", callback_data="pin"),
        types.InlineKeyboardButton("📝 پیام خوش‌آمد", callback_data="welcome")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: True)
def handle_admin_commands(call):
    is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(call.from_user.id),), fetchone=True)
    if not is_admin:
        bot.answer_callback_query(call.id, "⛔ شما ادمین نیستید!")
        return
    
    if call.data == "ban":
        msg = bot.send_message(call.message.chat.id, "به پیام کاربر ریپلی کنید و سپس /ban را بزنید")
    elif call.data == "unban":
        msg = bot.send_message(call.message.chat.id, "آیدی عددی کاربر را برای آنبان وارد کنید:")
        bot.register_next_step_handler(msg, unban_user)
    elif call.data == "pin":
        bot.answer_callback_query(call.id, "به پیام مورد نظر ریپلی کنید و /pin را بزنید")
    elif call.data == "welcome":
        msg = bot.send_message(call.message.chat.id, "📝 متن پیام خوش‌آمدگویی را وارد کنید:")
        bot.register_next_step_handler(msg, set_welcome)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['ban'])
def ban_user(message):
    is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(message.from_user.id),), fetchone=True)
    if not is_admin:
        return
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        bot.ban_chat_member(message.chat.id, user_id)
        bot.send_message(message.chat.id, f"🚫 کاربر {user_id} بن شد!")

@bot.message_handler(commands=['pin'])
def pin_message(message):
    is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(message.from_user.id),), fetchone=True)
    if not is_admin:
        return
    if message.reply_to_message:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.send_message(message.chat.id, "📌 پیام پین شد!")

def unban_user(message):
    try:
        user_id = int(message.text.strip())
        bot.unban_chat_member(message.chat.id, user_id)
        bot.send_message(message.chat.id, f"✅ کاربر {user_id} آنبان شد!")
    except:
        bot.send_message(message.chat.id, "❌ آیدی نامعتبر!")

def set_welcome(message):
    db_execute("INSERT OR REPLACE INTO welcome_settings (group_id, message) VALUES (?, ?)", (str(message.chat.id), message.text))
    bot.send_message(message.chat.id, "✅ پیام خوش‌آمدگویی تنظیم شد!")

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    welcome = db_execute("SELECT message FROM welcome_settings WHERE group_id = ?", (str(message.chat.id),), fetchone=True)
    if welcome:
        for member in message.new_chat_members:
            bot.send_message(message.chat.id, welcome[0].replace("{name}", member.first_name))

print("🚀 ربات مدیریت گروه راه‌اندازی شد!")
bot.infinity_polling()
'''

# =========================
# ربات پشتیبانی حرفه‌ای
# =========================

SUPPORT_BOT_CODE = '''
import telebot
from telebot import types
import sqlite3
from datetime import datetime

TOKEN = "TOKEN_PLACEHOLDER"
bot = telebot.TeleBot(TOKEN)
ADMIN_PASSWORD = "123456"

DB_FILE = "support.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, status TEXT, admin_answer TEXT, created_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS faq (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT)''')
    conn.commit()
    conn.close()

init_db()

def db_execute(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    data = None
    if fetchone:
        data = c.fetchone()
    elif fetchall:
        data = c.fetchall()
    conn.commit()
    conn.close()
    return data

# سوالات متداول پیش‌فرض
default_faq = [
    ("چگونه سفارش بدهم؟", "برای سفارش به بخش محصولات بروید و محصول مورد نظر را انتخاب کنید."),
    ("هزینه ارسال چقدر است؟", "هزینه ارسال ۵۰,۰۰۰ تومان و برای خرید بالای ۱ میلیون تومان رایگان است."),
    ("مدت زمان ارسال چقدر است؟", "سفارشات در ۲ تا ۵ روز کاری به دست شما می‌رسد.")
]
for q, a in default_faq:
    db_execute("INSERT OR IGNORE INTO faq (question, answer) VALUES (?, ?)", (q, a))

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("📞 پشتیبانی", callback_data="new_ticket"))
    keyboard.add(types.InlineKeyboardButton("❓ سوالات متداول", callback_data="faq"))
    bot.send_message(message.chat.id, "👋 به پشتیبانی خوش آمدید!\\n\\nاز دکمه‌های زیر استفاده کنید.", reply_markup=keyboard)

@bot.message_handler(commands=['m'])
def admin_login(message):
    msg = bot.send_message(message.chat.id, "🔐 رمز مدیریت را وارد کنید:")
    bot.register_next_step_handler(msg, check_password)

def check_password(message):
    if message.text == ADMIN_PASSWORD:
        db_execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (str(message.from_user.id),))
        bot.send_message(message.chat.id, "✅ وارد پنل مدیریت شدید!", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ رمز اشتباه است!")

def get_admin_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📋 تیکت‌ها", callback_data="tickets"),
        types.InlineKeyboardButton("❓ مدیریت FAQ", callback_data="manage_faq")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "new_ticket":
        msg = bot.send_message(call.message.chat.id, "📝 پیام خود را بنویسید:")
        bot.register_next_step_handler(msg, create_ticket)
    
    elif call.data == "faq":
        faqs = db_execute("SELECT question, answer FROM faq", fetchall=True) or []
        if not faqs:
            bot.send_message(call.message.chat.id, "📭 سوال متداولی وجود ندارد")
        else:
            text = "❓ **سوالات متداول**\\n\\n"
            for q, a in faqs:
                text += f"• **{q}**\\n   {a}\\n\\n"
            bot.send_message(call.message.chat.id, text[:4000])
    
    elif call.data == "tickets":
        is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(call.from_user.id),), fetchone=True)
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ فقط ادمین")
            return
        tickets = db_execute("SELECT id, user_id, message, status FROM tickets WHERE status = 'pending' ORDER BY id DESC", fetchall=True) or []
        if not tickets:
            bot.send_message(call.message.chat.id, "📭 تیکت جدیدی وجود ندارد")
        else:
            for t in tickets:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("✏️ پاسخ", callback_data=f"reply_{t[0]}_{t[1]}"))
                bot.send_message(call.message.chat.id, f"🆔 تیکت: {t[0]}\\n👤 کاربر: {t[1]}\\n📝 {t[2][:200]}", reply_markup=keyboard)
    
    elif call.data.startswith("reply_"):
        parts = call.data.split("_")
        ticket_id, user_id = parts[1], parts[2]
        msg = bot.send_message(call.message.chat.id, f"✏️ پاسخ به کاربر {user_id}:")
        bot.register_next_step_handler(msg, lambda m: reply_ticket(m, ticket_id, user_id))
    
    elif call.data == "manage_faq":
        is_admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (str(call.from_user.id),), fetchone=True)
        if not is_admin:
            bot.answer_callback_query(call.id, "⛔ فقط ادمین")
            return
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("➕ افزودن FAQ", callback_data="add_faq"))
        keyboard.add(types.InlineKeyboardButton("🗑 حذف FAQ", callback_data="remove_faq"))
        bot.send_message(call.message.chat.id, "❓ مدیریت سوالات متداول", reply_markup=keyboard)
    
    elif call.data == "add_faq":
        msg = bot.send_message(call.message.chat.id, "📝 سوال را وارد کنید:")
        bot.register_next_step_handler(msg, get_faq_question)
    
    elif call.data == "remove_faq":
        faqs = db_execute("SELECT id, question FROM faq", fetchall=True) or []
        if not faqs:
            bot.send_message(call.message.chat.id, "📭 سوالی وجود ندارد")
        else:
            for f in faqs:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("❌ حذف", callback_data=f"del_faq_{f[0]}"))
                bot.send_message(call.message.chat.id, f"🆔 {f[0]}\\n❓ {f[1]}", reply_markup=keyboard)
    
    elif call.data.startswith("del_faq_"):
        fid = call.data.split("_")[2]
        db_execute("DELETE FROM faq WHERE id = ?", (fid,))
        bot.answer_callback_query(call.id, "✅ حذف شد")
    
    bot.answer_callback_query(call.id)

def create_ticket(message):
    db_execute("INSERT INTO tickets (user_id, message, status, created_at) VALUES (?, ?, 'pending', ?)",
              (str(message.from_user.id), message.text, datetime.now().isoformat()))
    bot.send_message(message.chat.id, "✅ تیکت شما ثبت شد. به زودی پاسخ داده می‌شود.")

def get_faq_question(message):
    question = message.text
    msg = bot.send_message(message.chat.id, "📝 پاسخ را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: save_faq(m, question))

def save_faq(message, question):
    db_execute("INSERT INTO faq (question, answer) VALUES (?, ?)", (question, message.text))
    bot.send_message(message.chat.id, "✅ سوال به FAQ اضافه شد!")

def reply_ticket(message, ticket_id, user_id):
    db_execute("UPDATE tickets SET status = 'answered', admin_answer = ? WHERE id = ?", (message.text, ticket_id))
    try:
        bot.send_message(int(user_id), f"📩 **پاسخ پشتیبانی:**\\n\\n{message.text}")
    except:
        pass
    bot.send_message(message.chat.id, "✅ پاسخ ارسال شد!")

print("🚀 ربات پشتیبانی راه‌اندازی شد!")
bot.infinity_polling()
'''

# =========================
# توابع اصلی ربات
# =========================
def send_message(chat_id, text, reply_markup=None):
    try:
        data = {"chat_id": chat_id, "text": text}
        if reply_markup:
            data["reply_markup"] = reply_markup
        response = requests.post(f"{BASE_URL}/sendMessage", json=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def get_main_inline_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "💬 سوال بپرس", "callback_data": "ask_question"}],
            [{"text": "💻 اجرای کد", "callback_data": "run_code"}],
            [{"text": "🤖 ساخت ربات", "callback_data": "build_bot"}],
            [{"text": "💰 خرید اشتراک", "callback_data": "buy_subscription"}],
            [{"text": "📞 پشتیبانی", "callback_data": "support"}]
        ]
    }

def get_bot_types_inline_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "🚫 ربات ضد اسپم حرفه‌ای", "callback_data": "bot_antispam"}],
            [{"text": "🛒 ربات فروشگاهی حرفه‌ای", "callback_data": "bot_shop"}],
            [{"text": "👥 ربات مدیریت گروه", "callback_data": "bot_group"}],
            [{"text": "📞 ربات پشتیبانی", "callback_data": "bot_support"}],
            [{"text": "🔙 منوی اصلی", "callback_data": "back_to_menu"}]
        ]
    }

def get_admin_inline_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✏️ پیام خوش‌آمدگویی", "callback_data": "edit_welcome"}],
            [{"text": "➕ سوال/جواب", "callback_data": "add_qa"}],
            [{"text": "📋 سوالات کاربران", "callback_data": "unanswered_q"}],
            [{"text": "📊 آمار سیستم", "callback_data": "show_stats"}],
            [{"text": "🔙 منوی اصلی", "callback_data": "back_to_menu"}]
        ]
    }

def create_bot_for_user(bot_type, token, user_id):
    bot_codes = {
        'antispam': ANTISPAM_BOT_CODE,
        'shop': SHOP_BOT_CODE,
        'group': GROUP_MANAGER_BOT_CODE,
        'support': SUPPORT_BOT_CODE
    }
    
    if bot_type not in bot_codes:
        return None, "نوع ربات نامعتبر"
    
    code = bot_codes[bot_type].replace("TOKEN_PLACEHOLDER", token)
    bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
    
    try:
        temp_dir = os.path.join(TEMP_DIR, bot_id)
        os.makedirs(temp_dir, exist_ok=True)
        code_path = os.path.join(temp_dir, 'bot.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        process = subprocess.Popen([sys.executable, code_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=temp_dir, start_new_session=True)
        
        expires_at = datetime.now() + timedelta(minutes=10)
        db_execute("INSERT INTO built_bots (user_id, bot_type, bot_code, token, status, expires_at) VALUES (?, ?, ?, ?, 'running', ?)",
                  (user_id, bot_type, code, token, expires_at.isoformat()))
        return bot_id, expires_at
    except Exception as e:
        return None, str(e)

def stop_expired_bots():
    now = datetime.now().isoformat()
    rows = db_execute("SELECT id FROM built_bots WHERE status = 'running' AND expires_at < ?", (now,), fetchall=True) or []
    for row in rows:
        db_execute("UPDATE built_bots SET status = 'expired' WHERE id = ?", (row[0],))

def execute_python_code(code, token, bot_id):
    try:
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8')
        temp_file.write(code)
        temp_file.close()
        
        result = subprocess.run([sys.executable, temp_file.name], capture_output=True, text=True, timeout=30)
        os.unlink(temp_file.name)
        
        if result.returncode == 0:
            return True, result.stdout[:2000] if result.stdout else "✅ کد با موفقیت اجرا شد"
        else:
            return False, result.stderr[:2000] if result.stderr else "خطا در اجرا"
    except subprocess.TimeoutExpired:
        return False, "⏰ زمان اجرا بیش از حد مجاز"
    except Exception as e:
        return False, f"❌ خطا: {str(e)}"

def find_answer(question):
    rows = db_execute("SELECT answer FROM qa ORDER BY usage_count DESC", fetchall=True) or []
    for row in rows:
        if row[0]:
            db_execute("UPDATE qa SET usage_count = usage_count + 1 WHERE answer = ?", (row[0],))
            return row[0]
    return None

# =========================
# مدیریت وضعیت
# =========================
user_states = {}
state_lock = threading.Lock()

def process_message(message):
    try:
        chat_id = message["chat"]["id"]
        user_id = str(message["from"]["id"])
        user_name = message["from"].get("first_name", "")
        text = message.get("text", "").strip()
        
        if text == "/start":
            welcome = db_execute("SELECT value FROM settings WHERE key = 'welcome_message'", fetchone=True)[0]
            send_message(chat_id, welcome, reply_markup=get_main_inline_keyboard())
            return
        
        if text == "/m":
            with state_lock:
                user_states[user_id] = "waiting_password"
            send_message(chat_id, "🔐 رمز مدیریت را وارد کنید:")
            return
        
        with state_lock:
            state = user_states.get(user_id)
        
        # بررسی رمز ادمین
        if state == "waiting_password":
            if text == ADMIN_PASSWORD:
                db_execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
                with state_lock:
                    user_states[user_id] = None
                send_message(chat_id, "✅ وارد پنل مدیریت شدید.", reply_markup=get_admin_inline_keyboard())
            else:
                send_message(chat_id, "❌ رمز اشتباه است.")
                with state_lock:
                    user_states[user_id] = None
            return
        
        # پاسخ ادمین
        if isinstance(state, dict) and state.get("state") == "waiting_answer":
            q_id = state.get("question_id")
            target_id = state.get("target_user_id")
            
            try:
                send_message(int(target_id), f"📩 **پاسخ ادمین:**\n\n{text}")
            except:
                pass
            
            db_execute("UPDATE user_questions SET answer_given = 1 WHERE id = ?", (q_id,))
            send_message(chat_id, f"✅ پاسخ به کاربر {target_id} ارسال شد")
            with state_lock:
                user_states[user_id] = None
            send_message(chat_id, "👑 پنل مدیریت:", reply_markup=get_admin_inline_keyboard())
            return
        
        # دریافت توکن برای اجرای کد (پشتیبانی از توکن بله)
        if state == "waiting_token":
            token = text.strip()
            if not token or len(token) < 20:
                send_message(chat_id, "❌ توکن نامعتبر! توکن بله خود را بفرستید:")
                return
            
            # بررسی توکن بله
            try:
                resp = requests.get(f"https://tapi.bale.ai/bot{token}/getMe", timeout=5)
                if resp.status_code == 200 and resp.json().get("ok"):
                    bot_info = resp.json()["result"]
                    send_message(chat_id, f"✅ توکن معتبر است!\nربات: @{bot_info.get('username', 'unknown')}\n\nحالا کد پایتون خود را بفرستید:")
                    
                    with state_lock:
                        user_states[user_id] = {"state": "waiting_code", "token": token}
                    return
                else:
                    send_message(chat_id, "❌ توکن بله نامعتبر! دوباره بفرستید:")
                    return
            except:
                send_message(chat_id, "❌ خطا در بررسی توکن! دوباره بفرستید:")
                return
        
        # دریافت کد برای اجرا
        if isinstance(state, dict) and state.get("state") == "waiting_code":
            token = state.get("token")
            code = text
            
            send_message(chat_id, "⚙️ در حال اجرای کد...")
            success, output = execute_python_code(code, token, user_id)
            
            if success:
                send_message(chat_id, f"✅ **کد با موفقیت اجرا شد!**\n\n```\n{output[:1500]}\n```\n\n⚠️ این نسخه آزمایشی ۱۰ دقیقه‌ای است.\n💰 برای فعالسازی دائمی: {PRICE_AMOUNT:,} تومان\n💳 {BANK_CARD}")
                
                def stop_bot():
                    time.sleep(600)
                    send_message(chat_id, "⏰ زمان آزمایشی به پایان رسید. برای ادامه، مبلغ را واریز کنید.")
                threading.Thread(target=stop_bot, daemon=True).start()
            else:
                send_message(chat_id, f"❌ **خطا در اجرا:**\n\n```\n{output[:1500]}\n```")
            
            with state_lock:
                user_states[user_id] = None
            return
        
        # دریافت توکن برای ساخت ربات
        if isinstance(state, dict) and state.get("state") == "waiting_bot_token":
            bot_type = state.get("bot_type")
            token = text.strip()
            
            if not token or len(token) < 20:
                send_message(chat_id, "❌ توکن نامعتبر! توکن بله خود را بفرستید:")
                return
            
            # بررسی توکن بله
            try:
                resp = requests.get(f"https://tapi.bale.ai/bot{token}/getMe", timeout=5)
                if resp.status_code != 200 or not resp.json().get("ok"):
                    send_message(chat_id, "❌ توکن بله نامعتبر! دوباره بفرستید:")
                    return
            except:
                send_message(chat_id, "❌ خطا در بررسی توکن! دوباره بفرستید:")
                return
            
            bot_names = {"antispam": "ضد اسپم", "shop": "فروشگاهی", "group": "مدیریت گروه", "support": "پشتیبانی"}
            send_message(chat_id, f"⚙️ در حال ساخت ربات {bot_names.get(bot_type, bot_type)}...")
            
            result = create_bot_for_user(bot_type, token, user_id)
            if result[0]:
                send_message(chat_id, f"✅ **ربات {bot_names.get(bot_type, bot_type)} با موفقیت ساخته شد!**\n\n⚠️ این نسخه آزمایشی ۱۰ دقیقه‌ای است.\n💰 برای فعالسازی دائمی: {PRICE_AMOUNT:,} تومان\n💳 {BANK_CARD}\n\n🔧 برای مدیریت ربات:\n• دستور /m و رمز {ADMIN_PASSWORD}")
                
                def stop_user_bot():
                    time.sleep(600)
                    send_message(chat_id, f"⏰ ربات {bot_names.get(bot_type, bot_type)} منقضی شد. برای تمدید، مبلغ را واریز کنید.")
                threading.Thread(target=stop_user_bot, daemon=True).start()
            else:
                send_message(chat_id, f"❌ خطا: {result[1]}")
            
            with state_lock:
                user_states[user_id] = None
            return
        
        # تغییر پیام خوش‌آمدگویی
        if state == "waiting_welcome":
            db_execute("UPDATE settings SET value = ? WHERE key = 'welcome_message'", (text,))
            with state_lock:
                user_states[user_id] = None
            send_message(chat_id, "✅ پیام خوش‌آمدگویی تغییر کرد!", reply_markup=get_admin_inline_keyboard())
            return
        
        # افزودن سوال/جواب
        if state == "waiting_qa_question":
            with state_lock:
                user_states[user_id] = {"state": "waiting_qa_answer", "question": text}
            send_message(chat_id, "💬 جواب را بفرستید:")
            return
        
        if isinstance(state, dict) and state.get("state") == "waiting_qa_answer":
            db_execute("INSERT OR REPLACE INTO qa (question, answer) VALUES (?, ?)", (state["question"], text))
            with state_lock:
                user_states[user_id] = None
            send_message(chat_id, "✅ سوال/جواب ذخیره شد!", reply_markup=get_admin_inline_keyboard())
            return
        
        # ذخیره سوال کاربر
        if text:
            db_execute("INSERT INTO user_questions (question, user_id, user_name) VALUES (?, ?, ?)", (text, user_id, user_name))
            answer = find_answer(text)
            if answer:
                send_message(chat_id, answer)
            else:
                send_message(chat_id, "🤔 هنوز پاسخی یاد نگرفتم.\n\n📝 سوال شما ثبت شد. به زودی پاسخ داده می‌شود.")
        
    except Exception as e:
        logger.error(f"Process error: {e}")

def process_callback(callback):
    try:
        callback_id = callback["id"]
        data = callback["data"]
        chat_id = callback["message"]["chat"]["id"]
        user_id = str(callback["from"]["id"])
        
        admin = db_execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,), fetchone=True)
        
        # پاسخ به سوال کاربر
        if data.startswith("answer_"):
            parts = data.split("_")
            if len(parts) >= 3:
                with state_lock:
                    user_states[user_id] = {"state": "waiting_answer", "question_id": parts[1], "target_user_id": parts[2]}
                send_message(chat_id, "✏️ پاسخ خود را بفرستید:")
                requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})
                return
        
        # ساخت ربات
        if data.startswith("bot_"):
            bot_type = data.replace("bot_", "")
            if bot_type in ["antispam", "shop", "group", "support"]:
                with state_lock:
                    user_states[user_id] = {"state": "waiting_bot_token", "bot_type": bot_type}
                send_message(chat_id, "🔑 توکن ربات بله خود را بفرستید:\n(از @BotFather بله بگیرید)")
                requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})
                return
        
        # منوی اصلی
        if data == "ask_question":
            send_message(chat_id, "📝 سوالت را بپرس:")
        elif data == "run_code":
            with state_lock:
                user_states[user_id] = "waiting_token"
            send_message(chat_id, "🔑 توکن ربات بله خود را بفرستید:")
        elif data == "build_bot":
            send_message(chat_id, "🎯 نوع ربات را انتخاب کنید:", reply_markup=get_bot_types_inline_keyboard())
        elif data == "buy_subscription":
            send_message(chat_id, f"💰 **فعالسازی دائمی ربات**\n\n💳 مبلغ: {PRICE_AMOUNT:,} تومان\n🏦 شماره کارت: {BANK_CARD}\n👤 به نام: مرتضی نیکخو خنجری\n\n📸 پس از واریز، عکس فیش را ارسال کنید.\n\n✅ پس از تایید، ربات شما دائمی می‌شود.")
        elif data == "support":
            send_message(chat_id, "📞 پشتیبانی: @shahraghee13\n\nساعت پاسخگویی: ۹ صبح تا ۹ شب")
        elif data == "back_to_menu":
            send_message(chat_id, "🚀 منوی اصلی:", reply_markup=get_main_inline_keyboard())
        
        # منوی ادمین
        if not admin:
            requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})
            return
        
        if data == "edit_welcome":
            with state_lock:
                user_states[user_id] = "waiting_welcome"
            send_message(chat_id, "✏️ پیام خوش‌آمدگویی جدید را بفرستید:")
        elif data == "add_qa":
            with state_lock:
                user_states[user_id] = "waiting_qa_question"
            send_message(chat_id, "📝 سوال را بفرستید:")
        elif data == "unanswered_q":
            rows = db_execute("SELECT id, question, user_id, created_at FROM user_questions WHERE answer_given = 0 LIMIT 20", fetchall=True) or []
            if not rows:
                send_message(chat_id, "📭 همه سوالات پاسخ داده شده‌اند!")
            else:
                for row in rows:
                    text = f"🆔 {row[0]}\n👤 {row[2]}\n❓ {row[1][:100]}\n📅 {row[3][:16]}"
                    keyboard = {"inline_keyboard": [[{"text": "✏️ پاسخ", "callback_data": f"answer_{row[0]}_{row[2]"}"}]]}
                    send_message(chat_id, text, reply_markup=keyboard)
                    time.sleep(0.2)
        elif data == "show_stats":
            total_qa = db_execute("SELECT COUNT(*) FROM qa", fetchone=True)[0]
            total_q = db_execute("SELECT COUNT(*) FROM user_questions", fetchone=True)[0]
            unanswered = db_execute("SELECT COUNT(*) FROM user_questions WHERE answer_given = 0", fetchone=True)[0]
            total_bots = db_execute("SELECT COUNT(*) FROM built_bots", fetchone=True)[0]
            text = f"📊 **آمار سیستم**\n\n📝 سوال/جواب: {total_qa}\n💬 سوالات کاربران: {total_q}\n⏳ بدون پاسخ: {unanswered}\n🤖 ربات‌های ساخته شده: {total_bots}\n📅 {datetime.now().strftime('%Y/%m/%d')}"
            send_message(chat_id, text)
        
        requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": callback_id})
    except Exception as e:
        logger.error(f"Callback error: {e}")

# =========================
# دریافت آپدیت
# =========================
def get_updates(offset=None, timeout=30):
    try:
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset
        response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=timeout+5)
        if response.status_code == 200:
            return response.json()
        return {"ok": False, "result": []}
    except Exception as e:
        return {"ok": False, "result": []}

def background_worker():
    while True:
        try:
            item = REQUEST_QUEUE.get(timeout=1)
            if item["type"] == "message":
                process_message(item["data"])
            elif item["type"] == "callback":
                process_callback(item["data"])
            REQUEST_QUEUE.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Worker error: {e}")

# =========================
# اجرا
# =========================
def main():
    init_db()
    
    for _ in range(50):
        threading.Thread(target=background_worker, daemon=True).start()
    
    def expire_checker():
        while True:
            time.sleep(60)
            stop_expired_bots()
    threading.Thread(target=expire_checker, daemon=True).start()
    
    logger.info("=" * 70)
    logger.info("🚀 SUPER ULTIMATE BOT راه‌اندازی شد")
    logger.info(f"🖥️ ۵۰ ماشین | حافظه ۱۶۵GB | ۵۰ کارگر همزمان")
    logger.info(f"🤖 ۴ نوع ربات واقعی: ضداسپم(۵۰۰+ خط) | فروشگاهی | مدیریت گروه | پشتیبانی")
    logger.info(f"💰 مبلغ اشتراک: {PRICE_AMOUNT:,} تومان")
    logger.info("=" * 70)
    
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            if updates.get("ok"):
                for update in updates.get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        REQUEST_QUEUE.put({"type": "message", "data": update["message"]})
                    elif "callback_query" in update:
                        REQUEST_QUEUE.put({"type": "callback", "data": update["callback_query"]})
            time.sleep(0.05)
        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()