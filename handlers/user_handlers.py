import hashlib
import time
from telebot import types
from core.database import Database
from core.redis_client import RedisClient
from core.docker_manager import DockerManager
from core.security import SecurityManager
from core.logging_config import setup_logging
from menus.main_menu import get_main_menu
from texts import get_text

logger = setup_logging()
db = Database()
redis = RedisClient()
docker = DockerManager()

def register_user_handlers(bot):
    
    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        user_id = message.from_user.id
        referral_code = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:12]
        
        import asyncio
        asyncio.run(db.create_user(
            user_id, 
            message.from_user.username or "",
            message.from_user.first_name or "",
            message.from_user.last_name or "",
            referral_code
        ))
        
        text = get_text(user_id, 'welcome', name=message.from_user.first_name)
        bot.send_message(message.chat.id, text, reply_markup=get_main_menu(user_id))
    
    @bot.message_handler(func=lambda m: m.text in ['🌐 زبان / Language', '🌐 Language / زبان'])
    def change_language(m):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"))
        markup.add(types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"))
        bot.send_message(m.chat.id, "Select language:", reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
    def set_language(call):
        lang = call.data.replace('lang_', '')
        import asyncio
        asyncio.run(db.update_user_language(call.from_user.id, lang))
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'language_changed' if lang == 'fa' else 'language_changed_en'))
        bot.edit_message_text("✅ Updated", call.message.chat.id, call.message.message_id)
    
    @bot.message_handler(func=lambda m: m.text in ['📚 راهنما', '📚 Guide'])
    def guide(m):
        text = """📚 **راهنمای استفاده**

1️⃣ فایل .py یا .zip خود را ارسال کنید
2️⃣ ربات شما در محیط امن داکر اجرا می‌شود
3️⃣ هر کاربر می‌تواند حداکثر ۳ ربات بسازد
4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید
5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید

🎯 زبان‌های پشتیبانی شده:
🐍 Python | 📜 JavaScript | ☕ Java | 🔷 C# | 🐘 PHP | 🐹 Go | 🦀 Rust"""
        bot.send_message(m.chat.id, text, parse_mode='Markdown')
    
    @bot.message_handler(func=lambda m: m.text in ['📞 پشتیبانی', '📞 Support'])
    def support(m):
        bot.send_message(m.chat.id, "📞 پشتیبانی: @shahraghee13")
    
    @bot.message_handler(func=lambda m: m.text == '🔙 بازگشت به منوی اصلی')
    def back_to_main(m):
        bot.send_message(m.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(m.from_user.id))
