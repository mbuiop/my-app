import hashlib
import time
import asyncio
import requests
from telebot import types
from core.database import Database
from core.redis_client import RedisClient
from core.docker_manager import DockerManager
from core.security import SecurityManager
from core.logging_config import setup_logging
from texts import get_text

logger = setup_logging()
db = Database()
redis = RedisClient()
docker = DockerManager()
security = SecurityManager()

def register_bot_handlers(bot):
    
    @bot.message_handler(func=lambda m: m.text in ['🤖 ساخت ربات جدید', '🤖 New Bot'])
    def new_bot(m):
        bot.send_message(m.chat.id, get_text(m.from_user.id, 'send_file'))
    
    @bot.message_handler(content_types=['document'])
    def handle_file(m):
        user_id = m.from_user.id
        file_name = m.document.file_name
        
        allowed = any(file_name.endswith(ext) for ext in security.ALLOWED_EXTENSIONS)
        if not allowed and not file_name.endswith('.zip'):
            bot.reply_to(m, get_text(user_id, 'invalid_file'))
            return
        
        if m.document.file_size > 50 * 1024 * 1024:
            bot.reply_to(m, get_text(user_id, 'file_too_large'))
            return
        
        status_msg = bot.reply_to(m, get_text(user_id, 'processing'))
        
        try:
            file_info = bot.get_file(m.document.file_id)
            content = bot.download_file(file_info.file_path)
            
            is_valid, err = security.validate_file(content)
            if not is_valid:
                bot.edit_message_text(get_text(user_id, 'error', error=err), m.chat.id, status_msg.message_id)
                return
            
            safe_name = security.sanitize_filename(file_name, user_id)
            file_path = security.save_secure(content, safe_name, user_id)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            
            token = security.extract_token(code)
            if not token:
                bot.edit_message_text(get_text(user_id, 'token_not_found'), m.chat.id, status_msg.message_id)
                return
            
            try:
                resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
                if resp.status_code != 200:
                    bot.edit_message_text(get_text(user_id, 'invalid_token'), m.chat.id, status_msg.message_id)
                    return
                bot_info = resp.json()['result']
            except:
                bot.edit_message_text(get_text(user_id, 'invalid_token'), m.chat.id, status_msg.message_id)
                return
            
            builds_today = asyncio.run(redis.get_builds_today(user_id))
            if builds_today >= 10:
                bot.edit_message_text(get_text(user_id, 'error', error="Daily limit reached"), m.chat.id, status_msg.message_id)
                return
            
            bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
            
            result = docker.run_bot_safe(bot_id, code)
            
            if result['success']:
                asyncio.run(db.create_bot(bot_id, user_id, token, bot_info['first_name'], bot_info['username'], file_path))
                asyncio.run(redis.increment_builds(user_id))
                bot.edit_message_text(get_text(user_id, 'build_success', name=bot_info['first_name']), m.chat.id, status_msg.message_id)
            else:
                bot.edit_message_text(get_text(user_id, 'build_failed', error=result.get('error', 'Unknown')), m.chat.id, status_msg.message_id)
                
        except Exception as e:
            bot.edit_message_text(get_text(user_id, 'error', error=str(e)[:100]), m.chat.id, status_msg.message_id)
    
    @bot.message_handler(func=lambda m: m.text in ['📋 ربات‌های من', '📋 My Bots'])
    def my_bots(m):
        user_id = m.from_user.id
        bots = asyncio.run(db.get_user_bots(user_id))
        if not bots:
            bot.send_message(m.chat.id, get_text(user_id, 'no_bots'))
            return
        
        text = get_text(user_id, 'bot_list') + "\n\n"
        for b in bots:
            status_emoji = "🟢" if b['status'] == 'running' else "🔴"
            text += f"{status_emoji} {b['name']}\n🔗 t.me/{b['username']}\n\n"
        bot.send_message(m.chat.id, text)
    
    @bot.message_handler(func=lambda m: m.text in ['🔄 فعال/غیرفعال', '🔄 Start/Stop'])
    def toggle_prompt(m):
        user_id = m.from_user.id
        bots = asyncio.run(db.get_user_bots(user_id))
        if not bots:
            bot.send_message(m.chat.id, get_text(user_id, 'no_bots'))
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots:
            status_emoji = "🟢" if b['status'] == 'running' else "🔴"
            markup.add(types.InlineKeyboardButton(f"{status_emoji} {b['name']}", callback_data=f"toggle_{b['id']}"))
        bot.send_message(m.chat.id, get_text(user_id, 'select_bot'), reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
    def toggle_bot(call):
        bot_id = call.data.replace('toggle_', '')
        current = asyncio.run(db.get_bot(bot_id))
        if not current or current['user_id'] != call.from_user.id:
            bot.answer_callback_query(call.id, get_text(call.from_user.id, 'error', error="Not found"))
            return
        
        new_status = 'stopped' if current['status'] == 'running' else 'running'
        asyncio.run(db.update_bot_status(bot_id, new_status))
        
        msg = get_text(call.from_user.id, 'started' if new_status == 'running' else 'stopped')
        bot.answer_callback_query(call.id, msg)
    
    @bot.message_handler(func=lambda m: m.text in ['🗑 حذف ربات', '🗑 Delete Bot'])
    def delete_prompt(m):
        user_id = m.from_user.id
        bots = asyncio.run(db.get_user_bots(user_id))
        if not bots:
            bot.send_message(m.chat.id, get_text(user_id, 'no_bots'))
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for b in bots:
            markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
        bot.send_message(m.chat.id, get_text(user_id, 'select_bot'), reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
    def confirm_delete(call):
        bot_id = call.data.replace('delete_', '')
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"))
        markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
        bot.edit_message_text(get_text(call.from_user.id, 'confirm_delete'), call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
    def do_delete(call):
        bot_id = call.data.replace('confirm_del_', '')
        asyncio.run(db.delete_bot(bot_id, call.from_user.id))
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'deleted'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
    def cancel_delete(call):
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    @bot.message_handler(func=lambda m: m.text in ['📈 مصرف من', '📈 My Usage'])
    def my_usage(m):
        user_id = m.from_user.id
        builds = asyncio.run(redis.get_builds_today(user_id))
        bots = len(asyncio.run(db.get_user_bots(user_id)))
        text = f"📊 **Your Usage**\n\n🤖 Today's builds: {builds}/10\n📋 Total bots: {bots}/3"
        bot.send_message(m.chat.id, text, parse_mode='Markdown')
    
    @bot.message_handler(func=lambda m: m.text in ['⚡ وضعیت صف', '⚡ Queue Status'])
    def queue_status(m):
        queue_len = asyncio.run(redis.get_queue_length("build_queue"))
        text = f"⚡ **Queue Status**\n\n📊 In queue: {queue_len}\n⚙️ Max concurrent: 5"
        bot.send_message(m.chat.id, text, parse_mode='Markdown')
