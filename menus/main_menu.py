from telebot import types
from core.database import Database
from core.config import Config
import asyncio

db = Database()

MENU_FA = [
    '🤖 ساخت ربات جدید', '📋 ربات‌های من', '🔄 فعال/غیرفعال',
    '🗑 حذف ربات', '💰 کیف پول و اشتراک', '📚 راهنما',
    '👥 دعوت دوستان', '💸 درخواست برداشت', '📦 کتابخانه',
    '📊 آمار', '📞 پشتیبانی', '⚡ وضعیت صف',
    '📈 مصرف من', '🌐 زبان / Language'
]

MENU_EN = [
    '🤖 New Bot', '📋 My Bots', '🔄 Start/Stop',
    '🗑 Delete Bot', '💰 Wallet & Subscription', '📚 Guide',
    '👥 Invite Friends', '💸 Withdraw', '📦 Library',
    '📊 Stats', '📞 Support', '⚡ Queue Status',
    '📈 My Usage', '🌐 Language / زبان'
]

ADMIN_BUTTONS = [
    '👑 پنل مدیریت', '📸 تایید فیش', '💰 تایید برداشت',
    '⚙️ تنظیمات سیستم', '📊 آمار کاربران', '🗑 حذف کاربران',
    '🗑 حذف ربات‌های کاربران', '📢 پیام همگانی', '🔍 بررسی ربات‌های کاربران',
    '💳 تنظیم آدرس کیف پول', '📝 عوض کردن متن راهنما', '👋 عوض کردن متن خوش آمد گویی',
    '✅ عوض کردن متن فعالسازی اشتراک', '💸 عوض کردن متن خرید اشتراک',
    '🔄 ریستارت ربات‌های مرده', '🐛 مدیریت خطاهای ربات', '⚙️ تنظیم ظرفیت کاربران',
    '🖥️ مدیریت ماشین‌ها', '➕ اضافه کردن سرور جدید', '🔙 بازگشت به منوی اصلی'
]

def get_main_menu(user_id):
    user = asyncio.run(db.get_user(user_id))
    lang = user.get('language', 'fa') if user else 'fa'
    is_admin = user_id in Config.ADMIN_IDS
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = MENU_FA.copy() if lang == 'fa' else MENU_EN.copy()
    
    if is_admin:
        for btn in ADMIN_BUTTONS:
            buttons.append(btn)
    
    markup.add(*buttons)
    return markup
