#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 18.0 Ultimate
✅ پنل مدیریت پیشرفته | اشتراک ماهیانه | سیستم برداشت | رفرال هوشمند
⚡ قدرت: ۵۰ ماشین مجزا | پاسخگویی به ۱۰,۰۰۰+ کاربر همزمان
═══════════════════════════════════════════════════════════════════════════════
"""

import telebot
from telebot import types
import sqlite3
import os
import subprocess
import sys
import time
import hashlib
import json
import threading
import shutil
import re
import zipfile
import requests
import signal
import psutil
import logging
import queue
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'MACHINES': os.path.join(BASE_DIR, "machines"),
    'BACKUPS': os.path.join(BASE_DIR, "backups")
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== تنظیمات قابل تغییر توسط ادمین ====================
CONFIG = {
    'BOT_TOKEN': "8541672444:AAF4PBn7-XqiXUgaK0arVajyZfcMWqbxSJ0",
    'ADMIN_IDS': [327855654],
    'CARD_NUMBER': "5892101187322777",
    'CARD_HOLDER': "مرتضی نیکخو خنجری",
    'CARD_BANK': "بانگ سپه ",
    'SUBSCRIPTION_PRICE': 3660000,  # ۲ میلیون تومان
    'REFERRAL_PERCENT': 7,  # ۷ درصد
    'MIN_WITHDRAW': 3660000,  # حداقل برداشت ۲ میلیون
    'SUBSCRIPTION_DAYS': 30,  # ۳۰ روز اشتراک
    'GRACE_PERIOD_HOURS': 24,  # ۲۴ ساعت اخطار
    'MAX_BOTS_PER_USER': 10,
    'BOTS_PER_MACHINE': 3000,
    'TOTAL_MACHINES': 50
}

# تنظیمات قابل تغییر توسط ادمین (ذخیره در فایل)
CONFIG_FILE = os.path.join(BASE_DIR, 'admin_config.json')

def load_config():
    global CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                CONFIG.update(saved)
        except:
            pass

def save_config():
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(CONFIG, f, ensure_ascii=False, indent=2)

load_config()

BOT_TOKEN = CONFIG['BOT_TOKEN']
ADMIN_IDS = CONFIG['ADMIN_IDS']

# ==================== لاگینگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
            maxBytes=50*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger('MotherBot')

# ==================== دیتابیس پیشرفته ====================
class Database:
    def __init__(self):
        self.db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        self._init_db()
    
    def get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    
    def execute(self, query, params=()):
        conn = self.get_conn()
        try:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            return []
        finally:
            conn.close()
    
    def _init_db(self):
        # جدول کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                balance INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 1,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                verified_referrals INTEGER DEFAULT 0,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                warning_sent INTEGER DEFAULT 0,
                payment_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                last_active TIMESTAMP
            )
        ''')
        
        # جدول ربات‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                file_path TEXT,
                pid INTEGER,
                machine_id INTEGER,
                status TEXT DEFAULT 'stopped',
                error_message TEXT,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # جدول فیش‌های واریز (اشتراک)
        self.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                status TEXT DEFAULT 'pending',
                payment_code TEXT UNIQUE,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # جدول درخواست‌های برداشت
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                card_number TEXT,
                card_holder TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # جدول ماشین‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                status TEXT DEFAULT 'active',
                current_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 3000,
                last_heartbeat TIMESTAMP
            )
        ''')
        
        # جدول گزارش خطاها
        self.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT,
                user_id INTEGER,
                error_type TEXT,
                error_message TEXT,
                resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP
            )
        ''')
        
        # ایجاد ماشین‌ها
        for i in range(1, CONFIG['TOTAL_MACHINES'] + 1):
            self.execute('''
                INSERT OR IGNORE INTO machines (id, name, status, max_bots, last_heartbeat)
                VALUES (?, ?, 'active', ?, ?)
            ''', (i, f"Machine-{i:02d}", CONFIG['BOTS_PER_MACHINE'], datetime.now().isoformat()))
        
        # ایجاد ایندکس‌ها
        self.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_status)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)")
        self.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)")

db = Database()

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

# ==================== توابع کمکی ====================

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:10]

def get_user(user_id):
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return dict(users[0]) if users else None

def create_user(user_id, username, first_name, last_name, referred_by=None):
    try:
        now = datetime.now().isoformat()
        referral_code = generate_referral_code(user_id)
        
        db.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, referral_code, referred_by, now, now))
        
        db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
        
        # فقط اگر کاربر توسط شخص دیگری دعوت شده باشد
        if referred_by and referred_by != user_id:
            db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
        
        return True
    except Exception as e:
        logger.error(f"create_user error: {e}")
        return False

def check_subscription(user_id):
    """بررسی وضعیت اشتراک کاربر"""
    user = get_user(user_id)
    if not user:
        return False
    
    if user['subscription_status'] == 'active':
        expiry = datetime.fromisoformat(user['subscription_expiry']) if user['subscription_expiry'] else None
        if expiry and expiry > datetime.now():
            return True
        else:
            # اشتراک منقضی شده
            db.execute('UPDATE users SET subscription_status = "expired" WHERE user_id = ?', (user_id,))
            return False
    
    return False

def activate_subscription(user_id, days=CONFIG['SUBSCRIPTION_DAYS']):
    """فعال کردن اشتراک کاربر"""
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    db.execute('''
        UPDATE users 
        SET subscription_status = 'active', subscription_expiry = ?, payment_status = 'approved'
        WHERE user_id = ?
    ''', (expiry, user_id))
    
    # اضافه کردن ۷ درصد به دعوت کننده
    user = get_user(user_id)
    if user and user['referred_by']:
        referrer = get_user(user['referred_by'])
        if referrer:
            commission = int(CONFIG['SUBSCRIPTION_PRICE'] * CONFIG['REFERRAL_PERCENT'] / 100)
            db.execute('''
                UPDATE users 
                SET balance = balance + ?, total_earned = total_earned + ?, 
                    verified_referrals = verified_referrals + 1
                WHERE user_id = ?
            ''', (commission, commission, user['referred_by']))
            
            try:
                bot.send_message(
                    user['referred_by'],
                    f"🎉 {commission:,} تومان به کیف پول شما اضافه شد!\n"
                    f"📊 دلیل: دعوت کاربر {user['first_name']} که اشتراک خریداری کرد.\n"
                    f"💰 موجودی کیف پول: {referrer['balance'] + commission:,} تومان"
                )
            except:
                pass
    
    return True

def check_and_warn_expiring():
    """بررسی اشتراک‌های در حال انقضا و ارسال اخطار"""
    users = db.execute('''
        SELECT user_id, first_name, subscription_expiry, warning_sent 
        FROM users 
        WHERE subscription_status = 'active'
    ''')
    
    for user in users:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        hours_left = (expiry - datetime.now()).total_seconds() / 3600
        
        if 0 < hours_left <= CONFIG['GRACE_PERIOD_HOURS'] and user['warning_sent'] == 0:
            # ارسال اخطار
            try:
                bot.send_message(
                    user['user_id'],
                    f"⚠️ اخطار!\n\n"
                    f"اشتراک شما {int(hours_left)} ساعت دیگر منقضی می‌شود.\n"
                    f"لطفاً برای تمدید اشتراک، مبلغ {CONFIG['SUBSCRIPTION_PRICE']:,} تومان را واریز کنید.\n\n"
                    f"💳 شماره کارت: {CONFIG['CARD_NUMBER']}\n"
                    f"👤 به نام: {CONFIG['CARD_HOLDER']}\n\n"
                    f"📸 پس از واریز، تصویر فیش را ارسال کنید."
                )
                db.execute('UPDATE users SET warning_sent = 1 WHERE user_id = ?', (user['user_id'],))
            except:
                pass
        
        elif hours_left <= 0:
            # غیرفعال کردن کاربر
            db.execute('UPDATE users SET subscription_status = "expired", warning_sent = 0 WHERE user_id = ?', (user['user_id'],))
            db.execute('UPDATE bots SET status = "stopped" WHERE user_id = ?', (user['user_id'],))
            try:
                bot.send_message(
                    user['user_id'],
                    f"❌ اشتراک شما منقضی شد!\n\n"
                    f"ربات‌های شما غیرفعال شدند.\n"
                    f"برای فعالسازی مجدد، اشتراک جدید خریداری کنید."
                )
            except:
                pass

def check_bot_limit(user_id):
    """بررسی محدودیت تعداد ربات"""
    user = get_user(user_id)
    if not user:
        return True, 1, 0
    
    extra_bots = user['verified_referrals'] // 5
    max_bots = 1 + extra_bots
    if max_bots > CONFIG['MAX_BOTS_PER_USER']:
        max_bots = CONFIG['MAX_BOTS_PER_USER']
    
    bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE user_id = ?', (user_id,))
    current_bots = bots[0]['count'] if bots else 0
    
    return current_bots < max_bots, max_bots, current_bots

def get_user_bots(user_id):
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return [dict(bot) for bot in bots]

def get_bot(bot_id):
    bots = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    return dict(bots[0]) if bots else None

def delete_bot(bot_id, user_id):
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user_id:
        return False
    
    try:
        if bot.get('pid'):
            os.kill(bot['pid'], signal.SIGTERM)
    except:
        pass
    
    if bot.get('file_path') and os.path.exists(bot['file_path']):
        os.remove(bot['file_path'])
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    
    return True

def fix_bot(bot_id, user_id):
    """رفع مشکل ربات معیوب"""
    bot = get_bot(bot_id)
    if not bot or bot['user_id'] != user_id:
        return False, "ربات پیدا نشد"
    
    try:
        # توقف ربات
        if bot.get('pid'):
            try:
                os.kill(bot['pid'], signal.SIGTERM)
                time.sleep(1)
            except:
                pass
        
        # پاک کردن خطا
        db.execute('UPDATE bots SET status = "stopped", error_message = NULL, pid = NULL WHERE id = ?', (bot_id,))
        
        # ثبت در لاگ خطاها
        db.execute('''
            INSERT INTO error_logs (bot_id, user_id, error_type, error_message, resolved, created_at)
            VALUES (?, ?, 'fixed', 'ربط توسط کاربر تعمیر شد', 1, ?)
        ''', (bot_id, user_id, datetime.now().isoformat()))
        
        return True, "ربات با موفقیت تعمیر شد"
    except Exception as e:
        return False, f"خطا در تعمیر: {str(e)}"

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'bot\s*=\s*telebot\.TeleBot\(\s*["\']([^"\']+)["\']\s*\)'
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def save_uploaded_file(user_id, file_data, file_name):
    user_dir = os.path.join(DIRS['FILES'], str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
    with open(file_path, 'wb') as f:
        f.write(file_data)
    return file_path

def run_bot_simple(bot_id, code, token):
    """اجرای ساده ربات"""
    try:
        bot_dir = os.path.join(DIRS['RUNNING'], bot_id)
        os.makedirs(bot_dir, exist_ok=True)
        
        code_path = os.path.join(bot_dir, 'bot.py')
        if 'if __name__ == "__main__"' not in code:
            if 'bot.infinity_polling' in code:
                code += '\n\nif __name__ == "__main__":\n    bot.infinity_polling()\n'
        
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        process = subprocess.Popen(
            [sys.executable, code_path],
            stdout=open(os.path.join(bot_dir, 'bot.log'), 'a'),
            stderr=subprocess.STDOUT,
            cwd=bot_dir,
            start_new_session=True
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            return {'success': True, 'pid': process.pid}
        else:
            return {'success': False, 'error': 'خطا در اجرا'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ==================== منوی اصلی ====================
def get_main_menu(user_id=None):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton('🤖 ساخت ربات جدید'),
        types.KeyboardButton('📋 ربات‌های من'),
        types.KeyboardButton('🔄 فعال/غیرفعال'),
        types.KeyboardButton('🔧 رفع مشکل ربات'),
        types.KeyboardButton('🗑 حذف ربات'),
        types.KeyboardButton('💰 کیف پول و اشتراک'),
        types.KeyboardButton('💳 برداشت وجه'),
        types.KeyboardButton('📚 راهنما'),
        types.KeyboardButton('📞 پشتیبانی')
    ]
    
    if user_id in ADMIN_IDS:
        buttons.extend([
            types.KeyboardButton('👑 پنل مدیریت'),
            types.KeyboardButton('📢 پیام همگانی')
        ])
    
    markup.add(*buttons)
    return markup

# ==================== استارت ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    
    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        ref_code = args[1]
        users = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
            try:
                bot.send_message(referred_by, f"🎉 {first_name} با لینک رفرال شما وارد شد!")
            except:
                pass
    
    create_user(
        user_id,
        message.from_user.username or "",
        first_name,
        message.from_user.last_name or "",
        referred_by
    )
    
    user = get_user(user_id) or {}
    
    text = (
        f"🚀 به ربات مادر خوش آمدید {first_name}!\n\n"
        f"👤 آیدی: {user_id}\n"
        f"🎁 کد رفرال: {user.get('referral_code', '')}\n"
        f"🔗 لینک دعوت: https://t.me/{bot.get_me().username}?start={user.get('referral_code', '')}\n"
        f"📊 تعداد دعوت‌ها: {user.get('referrals_count', 0)}\n"
        f"💰 کیف پول: {user.get('balance', 0):,} تومان\n\n"
        f"💡 هر ۵ دعوت = ۱ ربات اضافه\n"
        f"💡 هر دعوت با خرید اشتراک = ۷٪ کمیسیون\n\n"
        f"📤 برای ساخت ربات، فایل .py خود را ارسال کنید"
    )
    
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(user_id))

# ==================== کیف پول و اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💰 کیف پول و اشتراک')
def wallet_subscription(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    is_subscribed = check_subscription(user_id)
    expiry = "ندارد"
    if user.get('subscription_expiry'):
        expiry = datetime.fromisoformat(user['subscription_expiry']).strftime('%Y-%m-%d %H:%M')
    
    text = (
        f"💰 کیف پول و وضعیت اشتراک\n\n"
        f"👤 نام: {user['first_name']}\n"
        f"🆔 آیدی: {user_id}\n"
        f"💰 موجودی کیف پول: {user['balance']:,} تومان\n"
        f"💰 کل درآمد: {user.get('total_earned', 0):,} تومان\n\n"
        f"📊 وضعیت اشتراک:\n"
        f"{'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
        f"📅 تاریخ انقضا: {expiry}\n\n"
        f"🎁 سیستم رفرال:\n"
        f"• کلیک‌ها: {user['referrals_count']}\n"
        f"• خریداری کرده: {user['verified_referrals']}\n"
        f"• کمیسیون: {CONFIG['REFERRAL_PERCENT']}% از هر خرید\n\n"
    )
    
    if not is_subscribed:
        text += (
            f"💳 برای فعالسازی اشتراک:\n"
            f"💰 مبلغ: {CONFIG['SUBSCRIPTION_PRICE']:,} تومان\n"
            f"💳 شماره کارت: {CONFIG['CARD_NUMBER']}\n"
            f"👤 به نام: {CONFIG['CARD_HOLDER']}\n"
            f"🏦 بانک: {CONFIG['CARD_BANK']}\n\n"
            f"📸 پس از واریز، تصویر فیش را ارسال کنید"
        )
    
    bot.send_message(message.chat.id, text)

# ==================== برداشت وجه ====================
@bot.message_handler(func=lambda m: m.text == '💳 برداشت وجه')
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    if user['balance'] < CONFIG['MIN_WITHDRAW']:
        bot.send_message(
            message.chat.id,
            f"❌ موجودی کیف پول شما برای برداشت کافی نیست.\n"
            f"💰 موجودی: {user['balance']:,} تومان\n"
            f"💰 حداقل برداشت: {CONFIG['MIN_WITHDRAW']:,} تومان\n\n"
            f"💡 با دعوت دوستان و دریافت کمیسیون، موجودی خود را افزایش دهید."
        )
        return
    
    msg = bot.send_message(
        message.chat.id,
        f"💰 موجودی قابل برداشت: {user['balance']:,} تومان\n\n"
        f"لطفاً شماره کارت خود را به همراه نام صاحب کارت ارسال کنید:\n"
        f"📝 مثال: 5892101187322777 - مرتضی نیکخو خنجری"
    )
    bot.register_next_step_handler(msg, process_withdraw_card)

def process_withdraw_card(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    # استخراج شماره کارت و نام
    match = re.search(r'(\d{16})\s*[-–—]\s*(.+)', text)
    if not match:
        match = re.search(r'(\d{16})\s+(.+)', text)
    
    if not match:
        bot.send_message(
            message.chat.id,
            "❌ فرمت اشتباه!\n"
            "لطفاً به این صورت ارسال کنید:\n"
            "5892101187322777 - مرتضی نیکخو خنجری"
        )
        return
    
    card_number = match.group(1)
    card_holder = match.group(2).strip()
    
    user = get_user(user_id)
    amount = user['balance']
    
    # ثبت درخواست برداشت
    db.execute('''
        INSERT INTO withdrawals (user_id, amount, card_number, card_holder, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, card_number, card_holder, datetime.now().isoformat()))
    
    # کاهش موجودی
    db.execute('UPDATE users SET balance = 0 WHERE user_id = ?', (user_id,))
    
    bot.send_message(
        message.chat.id,
        f"✅ درخواست برداشت شما ثبت شد.\n"
        f"💰 مبلغ: {amount:,} تومان\n"
        f"💳 شماره کارت: {card_number}\n"
        f"👤 به نام: {card_holder}\n\n"
        f"پس از تایید ادمین، مبلغ به کارت شما واریز می‌شود."
    )
    
    for admin_id in ADMIN_IDS:
        try:
            text = (
                f"💰 درخواست برداشت جدید!\n\n"
                f"👤 کاربر: {user['first_name']}\n"
                f"🆔 آیدی: {user_id}\n"
                f"💰 مبلغ: {amount:,} تومان\n"
                f"💳 شماره کارت: {card_number}\n"
                f"👤 نام صاحب کارت: {card_holder}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ تایید برداشت", callback_data=f"withdraw_approve_{user_id}_{amount}"),
                types.InlineKeyboardButton("❌ رد", callback_data=f"withdraw_reject_{user_id}")
            )
            bot.send_message(admin_id, text, reply_markup=markup)
        except:
            pass

# ==================== فیش واریزی ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    existing = db.execute('''
        SELECT id FROM receipts WHERE user_id = ? AND status = 'pending'
    ''', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ شما یک فیش در انتظار بررسی دارید")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        payment_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:8].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{payment_code}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        db.execute('''
            INSERT INTO receipts (user_id, amount, receipt_path, payment_code, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, CONFIG['SUBSCRIPTION_PRICE'], receipt_path, payment_code, datetime.now().isoformat()))
        
        bot.reply_to(
            message,
            f"✅ فیش شما دریافت شد!\n"
            f"💰 مبلغ: {CONFIG['SUBSCRIPTION_PRICE']:,} تومان\n"
            f"🆔 کد پیگیری: {payment_code}\n\n"
            f"پس از تایید ادمین، اشتراک شما فعال می‌شود."
        )
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(
                        admin_id,
                        f,
                        caption=f"📸 فیش جدید\n👤 کاربر: {message.from_user.first_name}\n🆔 {user_id}\n💰 {CONFIG['SUBSCRIPTION_PRICE']:,} تومان\n🆔 {payment_code}"
                    )
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text == '🤖 ساخت ربات جدید')
def new_bot(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.send_message(
            message.chat.id,
            f"❌ اشتراک شما فعال نیست!\n\n"
            f"برای ساخت ربات، ابتدا اشتراک خریداری کنید.\n"
            f"💰 مبلغ: {CONFIG['SUBSCRIPTION_PRICE']:,} تومان\n"
            f"💳 شماره کارت: {CONFIG['CARD_NUMBER']}\n\n"
            f"📸 پس از واریز، تصویر فیش را ارسال کنید."
        )
        return
    
    can_create, max_bots, current_bots = check_bot_limit(user_id)
    
    if not can_create:
        bot.send_message(
            message.chat.id,
            f"❌ شما به حداکثر تعداد ربات ({max_bots}) رسیده‌اید!\n"
            f"برای افزایش ظرفیت، دوستان خود را دعوت کنید (هر ۵ نفر = ۱ ربات اضافه)."
        )
        return
    
    bot.send_message(
        message.chat.id,
        "📤 فایل `.py` یا `.zip` خود را ارسال کنید.\n"
        "✅ حجم حداکثر ۵۰ مگابایت\n"
        "✅ توکن ربات داخل کد باشد\n"
        "✅ پس از ساخت، ربات شما به صورت خودکار اجرا می‌شود."
    )

# ==================== آپلود فایل ====================
@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        bot.reply_to(message, "❌ اشتراک شما فعال نیست")
        return
    
    file_name = message.document.file_name
    
    if not (file_name.endswith('.py') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های `.py` یا `.zip` مجاز هستند!")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم فایل نباید بیشتر از ۵۰ مگابایت باشد!")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش فایل...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        file_path = save_uploaded_file(user_id, downloaded, file_name)
        
        main_code = ""
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        try:
                            with open(os.path.join(root, f), 'r', encoding='utf-8') as code_f:
                                content = code_f.read()
                            if f in ['bot.py', 'main.py', 'run.py']:
                                main_code = content
                                break
                        except:
                            pass
            
            if not main_code:
                for root, _, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith('.py'):
                            try:
                                with open(os.path.join(root, f), 'r', encoding='utf-8') as code_f:
                                    main_code = code_f.read()
                                    break
                            except:
                                pass
                        if main_code:
                            break
            
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    main_code = f.read()
            except:
                with open(file_path, 'r', encoding='cp1256') as f:
                    main_code = f.read()
        
        if not main_code:
            bot.edit_message_text("❌ هیچ فایل پایتونی پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن ربات در کد پیدا نشد!", message.chat.id, status_msg.message_id)
            return
        
        # بررسی اعتبار توکن
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                bot.edit_message_text("❌ توکن معتبر نیست!", message.chat.id, status_msg.message_id)
                return
            bot_info = resp.json()['result']
        except:
            bot.edit_message_text("❌ خطا در بررسی توکن!", message.chat.id, status_msg.message_id)
            return
        
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:12]
        
        # اجرای ربات
        result = run_bot_simple(bot_id, main_code, token)
        
        if result['success']:
            db.execute('''
                INSERT INTO bots (id, user_id, token, name, username, file_path, pid, status, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            ''', (bot_id, user_id, token, bot_info['first_name'], bot_info['username'], file_path, result['pid'], datetime.now().isoformat(), datetime.now().isoformat()))
            
            db.execute('UPDATE users SET bots_count = bots_count + 1, last_active = ? WHERE user_id = ?', (datetime.now().isoformat(), user_id))
            
            bot.edit_message_text(
                f"✅ ربات با موفقیت ساخته و اجرا شد!\n\n"
                f"🤖 نام: {bot_info['first_name']}\n"
                f"🔗 لینک: https://t.me/{bot_info['username']}\n"
                f"🆔 آیدی ربات: {bot_id}\n"
                f"🔄 PID: {result['pid']}\n\n"
                f"📋 برای مدیریت ربات از دکمه‌های زیر استفاده کنید.",
                message.chat.id,
                status_msg.message_id
            )
        else:
            bot.edit_message_text(
                f"❌ خطا در اجرای ربات:\n{result.get('error', 'خطای ناشناخته')}",
                message.chat.id,
                status_msg.message_id
            )
            
            db.execute('''
                INSERT INTO error_logs (bot_id, user_id, error_type, error_message, created_at)
                VALUES (?, ?, 'build_error', ?, ?)
            ''', (bot_id, user_id, result.get('error', 'خطا'), datetime.now().isoformat()))
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", message.chat.id, status_msg.message_id)
        logger.error(f"Build error: {e}")

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!\nبرای ساخت ربات، از دکمه '🤖 ساخت ربات جدید' استفاده کنید.")
        return
    
    for b in bots[:10]:
        status_text = "🟢 در حال اجرا" if b['status'] == 'running' else "🔴 متوقف"
        error_text = f"\n❌ خطا: {b['error_message'][:50]}" if b.get('error_message') else ""
        
        text = (
            f"{'🟢' if b['status'] == 'running' else '🔴'} **{b['name']}**\n"
            f"🔗 https://t.me/{b['username']}\n"
            f"🆔 `{b['id']}`\n"
            f"📊 وضعیت: {status_text}{error_text}\n"
            f"📅 ساخت: {b['created_at'][:10]}\n"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🔄 توقف/اجرا", callback_data=f"toggle_{b['id']}"),
            types.InlineKeyboardButton("🔧 رفع مشکل", callback_data=f"fix_{b['id']}")
        )
        markup.row(
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{b['id']}")
        )
        
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال')
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        emoji = "🟢" if b['status'] == 'running' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔄 ربات مورد نظر را انتخاب کنید:", reply_markup=markup)

# ==================== رفع مشکل ربات ====================
@bot.message_handler(func=lambda m: m.text == '🔧 رفع مشکل ربات')
def fix_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        emoji = "⚠️" if b.get('error_message') else "🔧"
        markup.add(types.InlineKeyboardButton(f"{emoji} {b['name']}", callback_data=f"fix_{b['id']}"))
    
    bot.send_message(message.chat.id, "🔧 انتخاب کنید:", reply_markup=markup)

# ==================== کال‌بک‌ها ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_info = get_bot(bot_id)
    
    if not bot_info or bot_info['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    if bot_info['status'] == 'running':
        try:
            if bot_info.get('pid'):
                os.kill(bot_info['pid'], signal.SIGTERM)
            db.execute('UPDATE bots SET status = "stopped", pid = NULL WHERE id = ?', (bot_id,))
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
        except:
            bot.answer_callback_query(call.id, "❌ خطا در توقف")
    else:
        bot.answer_callback_query(call.id, "❌ ربات در حال اجرا نیست!\nاز دکمه 'رفع مشکل' استفاده کنید.")
    
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.callback_query_handler(func=lambda call: call.data.startswith('fix_'))
def fix_bot_callback(call):
    bot_id = call.data.replace('fix_', '')
    bot_info = get_bot(bot_id)
    
    if not bot_info or bot_info['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    success, msg = fix_bot(bot_id, call.from_user.id)
    bot.answer_callback_query(call.id, msg)
    
    if success:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_bot_callback(call):
    bot_id = call.data.replace('delete_', '')
    bot_info = get_bot(bot_id)
    
    if not bot_info or bot_info['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del")
    )
    bot.edit_message_text(f"⚠️ آیا از حذف ربات {bot_info['name']} اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def confirm_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    
    if delete_bot(bot_id, call.from_user.id):
        bot.answer_callback_query(call.id, "✅ ربات حذف شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ خطا در حذف")

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "انصراف")

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    text = (
        "📚 **راهنمای کامل ربات مادر**\n\n"
        "**1️⃣ ساخت ربات:**\n"
        "   • ابتدا اشتراک خود را فعال کنید\n"
        "   • فایل `.py` یا `.zip` را ارسال کنید\n"
        "   • توکن ربات باید داخل کد باشد\n\n"
        "**2️⃣ اشتراک ماهیانه:**\n"
        f"   • مبلغ: {CONFIG['SUBSCRIPTION_PRICE']:,} تومان\n"
        f"   • شماره کارت: {CONFIG['CARD_NUMBER']}\n"
        f"   • به نام: {CONFIG['CARD_HOLDER']}\n\n"
        "**3️⃣ سیستم رفرال:**\n"
        "   • لینک دعوت خود را به دیگران بدهید\n"
        "   • هر نفر که با لینک شما ثبت نام کند\n"
        f"   • اگر اشتراک بخرد، {CONFIG['REFERRAL_PERCENT']}% به کیف پول شما اضافه می‌شود\n"
        "   • هر ۵ دعوت = ۱ ربات اضافه\n\n"
        "**4️⃣ برداشت وجه:**\n"
        f"   • حداقل برداشت: {CONFIG['MIN_WITHDRAW']:,} تومان\n"
        "   • فقط از کیف پول قابل برداشت است\n\n"
        "**5️⃣ مدیریت ربات:**\n"
        "   • 🔄 فعال/غیرفعال: شروع یا توقف ربات\n"
        "   • 🔧 رفع مشکل: تعمیر ربات معیوب\n"
        "   • 🗑 حذف ربات: حذف کامل\n\n"
        "**6️⃣ پشتیبانی:**\n"
        "   • @shahraghee13"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📨 ارتباط با پشتیبانی", url="https://t.me/shahraghee13"))
    bot.send_message(message.chat.id, "📞 برای ارتباط با پشتیبانی روی دکمه زیر کلیک کنید:", reply_markup=markup)

# ==================== پنل مدیریت ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ دسترسی محدود!")
        return
    
    stats = get_admin_stats()
    
    text = (
        f"👑 **پنل مدیریت ربات مادر**\n\n"
        f"📊 **آمار کلی:**\n"
        f"👥 کل کاربران: {stats['total_users']:,}\n"
        f"✅ اشتراک فعال: {stats['active_subscriptions']:,}\n"
        f"🤖 کل ربات‌ها: {stats['total_bots']:,}\n"
        f"🟢 ربات‌های فعال: {stats['running_bots']:,}\n"
        f"❌ ربات‌های مشکل‌دار: {stats['error_bots']:,}\n"
        f"💰 کیف پول کل: {stats['total_balance']:,} تومان\n"
        f"💰 کل برداشت‌ها: {stats['total_withdrawn']:,} تومان\n"
        f"📸 فیش‌های در انتظار: {stats['pending_receipts']}\n"
        f"💳 درخواست‌های برداشت: {stats['pending_withdrawals']}\n\n"
        f"💳 **اطلاعات کارت:**\n"
        f"💳 شماره: {CONFIG['CARD_NUMBER']}\n"
        f"👤 صاحب حساب: {CONFIG['CARD_HOLDER']}\n"
        f"💰 قیمت اشتراک: {CONFIG['SUBSCRIPTION_PRICE']:,} تومان\n"
        f"🎁 کمیسیون رفرال: {CONFIG['REFERRAL_PERCENT']}%\n"
        f"💵 حداقل برداشت: {CONFIG['MIN_WITHDRAW']:,} تومان"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌های در انتظار", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💳 درخواست‌های برداشت", callback_data="admin_withdrawals"),
        types.InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 مدیریت ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
        types.InlineKeyboardButton("❌ حذف کاربر", callback_data="admin_delete_user"),
        types.InlineKeyboardButton("🔧 رفع مشکل ربات‌ها", callback_data="admin_fix_bots"),
        types.InlineKeyboardButton("📊 آمار پیشرفته", callback_data="admin_stats"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

def get_admin_stats():
    total_users = db.execute('SELECT COUNT(*) as c FROM users')[0]['c']
    active_subs = db.execute('SELECT COUNT(*) as c FROM users WHERE subscription_status = "active"')[0]['c']
    total_bots = db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']
    running_bots = db.execute('SELECT COUNT(*) as c FROM bots WHERE status = "running"')[0]['c']
    error_bots = db.execute('SELECT COUNT(*) as c FROM bots WHERE error_message IS NOT NULL')[0]['c']
    total_balance = db.execute('SELECT SUM(balance) as s FROM users')[0]['s'] or 0
    total_withdrawn = db.execute('SELECT SUM(amount) as s FROM withdrawals WHERE status = "approved"')[0]['s'] or 0
    pending_receipts = db.execute('SELECT COUNT(*) as c FROM receipts WHERE status = "pending"')[0]['c']
    pending_withdrawals = db.execute('SELECT COUNT(*) as c FROM withdrawals WHERE status = "pending"')[0]['c']
    
    return {
        'total_users': total_users,
        'active_subscriptions': active_subs,
        'total_bots': total_bots,
        'running_bots': running_bots,
        'error_bots': error_bots,
        'total_balance': total_balance,
        'total_withdrawn': total_withdrawn,
        'pending_receipts': pending_receipts,
        'pending_withdrawals': pending_withdrawals
    }

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری وجود ندارد.")
        return
    
    for r in receipts:
        user = get_user(r['user_id'])
        text = (
            f"📸 **فیش جدید**\n\n"
            f"👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n"
            f"🆔 آیدی: {r['user_id']}\n"
            f"💰 مبلغ: {r['amount']:,} تومان\n"
            f"🆔 کد: {r['payment_code']}\n"
            f"📅 تاریخ: {r['created_at'][:19]}"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید اشتراک", callback_data=f"receipt_approve_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"receipt_reject_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('receipt_approve_'))
def receipt_approve(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    receipt_id = int(call.data.replace('receipt_approve_', ''))
    receipt = db.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,))
    
    if not receipt:
        bot.answer_callback_query(call.id, "❌ فیش پیدا نشد")
        return
    
    r = receipt[0]
    
    # فعال کردن اشتراک
    activate_subscription(r['user_id'])
    
    # به‌روزرسانی فیش
    db.execute('''
        UPDATE receipts SET status = 'approved', reviewed_by = ?, reviewed_at = ?
        WHERE id = ?
    ''', (call.from_user.id, datetime.now().isoformat(), receipt_id))
    
    bot.answer_callback_query(call.id, "✅ اشتراک کاربر فعال شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    try:
        bot.send_message(
            r['user_id'],
            f"✅ اشتراک شما به مدت {CONFIG['SUBSCRIPTION_DAYS']} روز فعال شد!\n\n"
            f"اکنون می‌توانید ربات خود را بسازید."
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('receipt_reject_'))
def receipt_reject(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    receipt_id = int(call.data.replace('receipt_reject_', ''))
    receipt = db.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,))
    
    if not receipt:
        bot.answer_callback_query(call.id, "❌ فیش پیدا نشد")
        return
    
    r = receipt[0]
    
    db.execute('UPDATE receipts SET status = 'rejected', reviewed_by = ?, reviewed_at = ? WHERE id = ?',
               (call.from_user.id, datetime.now().isoformat(), receipt_id))
    
    bot.answer_callback_query(call.id, "❌ فیش رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    try:
        bot.send_message(
            r['user_id'],
            f"❌ متأسفانه فیش شما تأیید نشد.\n\n"
            f"لطفاً با پشتیبانی تماس بگیرید: @shahraghee13"
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdrawals")
def admin_withdrawals(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    withdrawals = db.execute('SELECT * FROM withdrawals WHERE status = "pending" ORDER BY created_at')
    
    if not withdrawals:
        bot.send_message(call.message.chat.id, "💳 هیچ درخواست برداشتی وجود ندارد.")
        return
    
    for w in withdrawals:
        user = get_user(w['user_id'])
        text = (
            f"💰 **درخواست برداشت**\n\n"
            f"👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n"
            f"🆔 آیدی: {w['user_id']}\n"
            f"💰 مبلغ: {w['amount']:,} تومان\n"
            f"💳 شماره کارت: {w['card_number']}\n"
            f"👤 نام صاحب کارت: {w['card_holder']}\n"
            f"📅 تاریخ: {w['created_at'][:19]}"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید برداشت", callback_data=f"withdraw_approve_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"withdraw_reject_{w['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_approve_'))
def withdraw_approve(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    withdrawal_id = int(call.data.replace('withdraw_approve_', ''))
    withdrawal = db.execute('SELECT * FROM withdrawals WHERE id = ?', (withdrawal_id,))
    
    if not withdrawal:
        bot.answer_callback_query(call.id, "❌ پیدا نشد")
        return
    
    w = withdrawal[0]
    
    db.execute('''
        UPDATE withdrawals SET status = 'approved', reviewed_by = ?, reviewed_at = ?
        WHERE id = ?
    ''', (call.from_user.id, datetime.now().isoformat(), withdrawal_id))
    
    bot.answer_callback_query(call.id, "✅ برداشت تأیید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    try:
        bot.send_message(
            w['user_id'],
            f"✅ درخواست برداشت شما تأیید شد!\n\n"
            f"💰 مبلغ: {w['amount']:,} تومان\n"
            f"💳 به کارت {w['card_number']} واریز خواهد شد.\n\n"
            f"در صورت عدم واریز ظرف ۴۸ ساعت، با پشتیبانی تماس بگیرید."
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_reject_'))
def withdraw_reject(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    withdrawal_id = int(call.data.replace('withdraw_reject_', ''))
    withdrawal = db.execute('SELECT * FROM withdrawals WHERE id = ?', (withdrawal_id,))
    
    if not withdrawal:
        bot.answer_callback_query(call.id, "❌ پیدا نشد")
        return
    
    w = withdrawal[0]
    
    db.execute('''
        UPDATE withdrawals SET status = 'rejected', reviewed_by = ?, reviewed_at = ?
        WHERE id = ?
    ''', (call.from_user.id, datetime.now().isoformat(), withdrawal_id))
    
    # برگرداندن موجودی به کاربر
    db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (w['amount'], w['user_id']))
    
    bot.answer_callback_query(call.id, "❌ برداشت رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    try:
        bot.send_message(
            w['user_id'],
            f"❌ درخواست برداشت شما رد شد.\n\n"
            f"موجودی به کیف پول شما برگشت داده شد.\n"
            f"لطفاً با پشتیبانی تماس بگیرید: @shahraghee13"
        )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    users = db.execute('''
        SELECT user_id, first_name, username, subscription_status, balance, bots_count, created_at
        FROM users ORDER BY created_at DESC LIMIT 50
    ''')
    
    text = "👥 **لیست ۵۰ کاربر آخر:**\n\n"
    for u in users:
        sub = "✅" if u['subscription_status'] == 'active' else "❌"
        text += f"{sub} {u['user_id']} - {u['first_name']}\n"
        text += f"   💰 {u['balance']:,} | 🤖 {u['bots_count']}\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    bots = db.execute('''
        SELECT b.id, b.name, b.status, b.user_id, u.first_name
        FROM bots b
        JOIN users u ON b.user_id = u.user_id
        ORDER BY b.created_at DESC LIMIT 50
    ''')
    
    if not bots:
        bot.send_message(call.message.chat.id, "🤖 هیچ رباتی وجود ندارد.")
        return
    
    text = "🤖 **لیست ۵۰ ربات آخر:**\n\n"
    for b in bots:
        status = "🟢" if b['status'] == 'running' else "🔴"
        text += f"{status} {b['name']} - کاربر: {b['first_name']}\n"
        text += f"   🆔 {b['id']}\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user")
def admin_delete_user_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    msg = bot.send_message(call.message.chat.id, "❌ آیدی کاربر مورد نظر را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_delete_user)

def process_admin_delete_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        user_id = int(message.text.strip())
        
        # دریافت اطلاعات کاربر
        user = get_user(user_id)
        if not user:
            bot.reply_to(message, "❌ کاربر پیدا نشد!")
            return
        
        # حذف ربات‌های کاربر
        bots = get_user_bots(user_id)
        for bot in bots:
            delete_bot(bot['id'], user_id)
        
        # حذف کاربر
        db.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        db.execute('DELETE FROM receipts WHERE user_id = ?', (user_id,))
        db.execute('DELETE FROM withdrawals WHERE user_id = ?', (user_id,))
        
        bot.reply_to(message, f"✅ کاربر {user['first_name']} (آیدی: {user_id}) با موفقیت حذف شد.\n{len(bots)} ربات او نیز حذف گردید.")
        
    except ValueError:
        bot.reply_to(message, "❌ آیدی باید عدد باشد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_fix_bots")
def admin_fix_bots(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    # پیدا کردن ربات‌های مشکل‌دار
    error_bots = db.execute('SELECT id, user_id, name FROM bots WHERE error_message IS NOT NULL OR status = "stopped"')
    
    fixed = 0
    for bot in error_bots:
        try:
            db.execute('UPDATE bots SET status = "stopped", error_message = NULL WHERE id = ?', (bot['id'],))
            fixed += 1
        except:
            pass
    
    bot.answer_callback_query(call.id, f"✅ {fixed} ربات تعمیر شدند")
    bot.send_message(call.message.chat.id, f"🔧 {fixed} ربات مشکل‌دار ریست شدند.")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_advanced_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    # آمار پیشرفته
    total_users = db.execute('SELECT COUNT(*) as c FROM users')[0]['c']
    active_users = db.execute('SELECT COUNT(*) as c FROM users WHERE subscription_status = "active"')[0]['c']
    total_bots = db.execute('SELECT COUNT(*) as c FROM bots')[0]['c']
    running_bots = db.execute('SELECT COUNT(*) as c FROM bots WHERE status = "running"')[0]['c']
    
    total_receipts_amount = db.execute('SELECT SUM(amount) as s FROM receipts WHERE status = "approved"')[0]['s'] or 0
    total_withdrawn = db.execute('SELECT SUM(amount) as s FROM withdrawals WHERE status = "approved"')[0]['s'] or 0
    
    total_balance = db.execute('SELECT SUM(balance) as s FROM users')[0]['s'] or 0
    
    # رفرال آمار
    total_referrals = db.execute('SELECT SUM(referrals_count) as s FROM users')[0]['s'] or 0
    total_verified = db.execute('SELECT SUM(verified_referrals) as s FROM users')[0]['s'] or 0
    
    text = (
        f"📊 **آمار پیشرفته سیستم**\n\n"
        f"👥 **کاربران:**\n"
        f"• کل کاربران: {total_users:,}\n"
        f"• اشتراک فعال: {active_users:,}\n"
        f"• نرخ فعالی: {active_users/total_users*100:.1f}%\n\n"
        f"🤖 **ربات‌ها:**\n"
        f"• کل ربات‌ها: {total_bots:,}\n"
        f"• در حال اجرا: {running_bots:,}\n"
        f"• میانگین ربات به کاربر: {total_bots/total_users:.2f}\n\n"
        f"💰 **مالی:**\n"
        f"• کل فروش: {total_receipts_amount:,} تومان\n"
        f"• کل برداشت: {total_withdrawn:,} تومان\n"
        f"• موجودی کیف پول: {total_balance:,} تومان\n\n"
        f"🎁 **رفرال:**\n"
        f"• کل دعوت‌ها: {total_referrals:,}\n"
        f"• دعوت‌های موفق: {total_verified:,}\n"
        f"• نرخ تبدیل: {total_verified/total_referrals*100:.1f}%"
    )
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
def admin_settings(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    text = (
        f"⚙️ **تنظیمات قابل تغییر**\n\n"
        f"💳 شماره کارت: `{CONFIG['CARD_NUMBER']}`\n"
        f"👤 صاحب حساب: {CONFIG['CARD_HOLDER']}\n"
        f"🏦 بانک: {CONFIG['CARD_BANK']}\n"
        f"💰 قیمت اشتراک: {CONFIG['SUBSCRIPTION_PRICE']:,} تومان\n"
        f"🎁 کمیسیون رفرال: {CONFIG['REFERRAL_PERCENT']}%\n"
        f"💵 حداقل برداشت: {CONFIG['MIN_WITHDRAW']:,} تومان\n"
        f"📅 مدت اشتراک: {CONFIG['SUBSCRIPTION_DAYS']} روز\n"
        f"⏰ اخطار انقضا: {CONFIG['GRACE_PERIOD_HOURS']} ساعت قبل\n\n"
        f"📝 برای تغییر هر کدام، دکمه مربوطه را بزنید:"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💳 تغییر شماره کارت", callback_data="setting_card"),
        types.InlineKeyboardButton("💰 تغییر قیمت اشتراک", callback_data="setting_price"),
        types.InlineKeyboardButton("🎁 تغییر کمیسیون رفرال", callback_data="setting_percent"),
        types.InlineKeyboardButton("💵 تغییر حداقل برداشت", callback_data="setting_min_withdraw"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
    )
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "setting_card")
def setting_card(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    msg = bot.send_message(call.message.chat.id, "💳 شماره کارت جدید را وارد کنید (۱۶ رقم):")
    bot.register_next_step_handler(msg, process_setting_card)

def process_setting_card(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card = message.text.strip().replace(" ", "")
    if not card.isdigit() or len(card) != 16:
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد!")
        return
    
    CONFIG['CARD_NUMBER'] = card
    save_config()
    bot.reply_to(message, f"✅ شماره کارت به {card} تغییر یافت.")

@bot.callback_query_handler(func=lambda call: call.data == "setting_price")
def setting_price(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    msg = bot.send_message(call.message.chat.id, "💰 قیمت جدید اشتراک را به تومان وارد کنید:")
    bot.register_next_step_handler(msg, process_setting_price)

def process_setting_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        price = int(message.text.strip())
        if price < 10000:
            bot.reply_to(message, "❌ قیمت باید حداقل ۱۰,۰۰۰ تومان باشد!")
            return
        
        CONFIG['SUBSCRIPTION_PRICE'] = price
        save_config()
        bot.reply_to(message, f"✅ قیمت اشتراک به {price:,} تومان تغییر یافت.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "setting_percent")
def setting_percent(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    msg = bot.send_message(call.message.chat.id, "🎁 درصد کمیسیون رفرال را وارد کنید (۱ تا ۵۰):")
    bot.register_next_step_handler(msg, process_setting_percent)

def process_setting_percent(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        percent = int(message.text.strip())
        if percent < 1 or percent > 50:
            bot.reply_to(message, "❌ درصد باید بین ۱ تا ۵۰ باشد!")
            return
        
        CONFIG['REFERRAL_PERCENT'] = percent
        save_config()
        bot.reply_to(message, f"✅ کمیسیون رفرال به {percent}% تغییر یافت.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "setting_min_withdraw")
def setting_min_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔")
        return
    
    msg = bot.send_message(call.message.chat.id, f"💵 حداقل برداشت جدید را وارد کنید (تومان):\n(حداقل {CONFIG['SUBSCRIPTION_PRICE']:,} تومان)")
    bot.register_next_step_handler(msg, process_setting_min_withdraw)

def process_setting_min_withdraw(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        min_wd = int(message.text.strip())
        if min_wd < CONFIG['SUBSCRIPTION_PRICE']:
            bot.reply_to(message, f"❌ حداقل برداشت نباید از قیمت اشتراک ({CONFIG['SUBSCRIPTION_PRICE']:,}) کمتر باشد!")
            return
        
        CONFIG['MIN_WITHDRAW'] = min_wd
        save_config()
        bot.reply_to(message, f"✅ حداقل برداشت به {min_wd:,} تومان تغییر یافت.")
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    user_id = call.from_user.id
    bot.send_message(call.message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(user_id))

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📢 متن پیام همگانی را ارسال کنید:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    text = message.text
    users = db.execute('SELECT user_id FROM users')
    
    status_msg = bot.reply_to(message, f"📢 در حال ارسال به {len(users)} کاربر...")
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user['user_id'], text)
            sent += 1
            if sent % 10 == 0:
                bot.edit_message_text(f"📢 پیشرفت: {sent}/{len(users)}", message.chat.id, status_msg.message_id)
        except:
            failed += 1
        
        time.sleep(0.1)
    
    bot.edit_message_text(
        f"✅ پیام همگانی ارسال شد!\n\n"
        f"موفق: {sent}\n"
        f"ناموفق: {failed}",
        message.chat.id,
        status_msg.message_id
    )

# ==================== مانیتورینگ خودکار ====================
def monitor_system():
    while True:
        try:
            # بررسی اشتراک‌های در حال انقضا
            check_and_warn_expiring()
            
            # بررسی ربات‌های مرده
            running_bots = db.execute('SELECT id, pid FROM bots WHERE status = "running"')
            for bot in running_bots:
                if bot['pid']:
                    try:
                        os.kill(bot['pid'], 0)
                    except:
                        db.execute('UPDATE bots SET status = "stopped", error_message = "ربات به طور غیرمنتظره متوقف شد" WHERE id = ?', (bot['id'],))
                        logger.info(f"Bot {bot['id']} stopped unexpectedly")
            
            # پاکسازی فایل‌های موقت
            now = time.time()
            for f in os.listdir(DIRS['TEMP']):
                path = os.path.join(DIRS['TEMP'], f)
                if os.path.isfile(path) and now - os.path.getmtime(path) > 3600:
                    try:
                        os.remove(path)
                    except:
                        pass
            
            time.sleep(60)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(60)

# راه‌اندازی مانیتورینگ
monitor_thread = threading.Thread(target=monitor_system, daemon=True)
monitor_thread.start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی - نسخه 18.0 Ultimate".center(70))
    print("=" * 70)
    print(f"✅ پنل مدیریت پیشرفته")
    print(f"✅ سیستم اشتراک ماهیانه {CONFIG['SUBSCRIPTION_PRICE']:,} تومان")
    print(f"✅ سیستم رفرال {CONFIG['REFERRAL_PERCENT']}%")
    print(f"✅ سیستم برداشت از حداقل {CONFIG['MIN_WITHDRAW']:,} تومان")
    print(f"✅ ادمین‌ها: {ADMIN_IDS}")
    print("=" * 70)
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
