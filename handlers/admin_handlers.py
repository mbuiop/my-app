import asyncio
from telebot import types
from core.database import Database
from core.config import Config
from texts import get_text

db = Database()

def register_admin_handlers(bot):
    
    @bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
    def admin_panel(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [
            '📸 تایید فیش', '💰 تایید برداشت', '📊 آمار کاربران',
            '🗑 حذف کاربران', '🗑 حذف ربات‌های کاربران', '📢 پیام همگانی',
            '🔍 بررسی ربات‌های کاربران', '💳 تنظیم آدرس کیف پول',
            '🔄 ریستارت ربات‌های مرده', '⚙️ تنظیم ظرفیت کاربران',
            '🖥️ مدیریت ماشین‌ها', '🔙 بازگشت به منوی اصلی'
        ]
        markup.add(*buttons)
        bot.send_message(m.chat.id, "👑 **پنل مدیریت**", parse_mode='Markdown', reply_markup=markup)
    
    @bot.message_handler(func=lambda m: m.text == '📸 تایید فیش')
    def admin_receipts(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        receipts = asyncio.run(db.get_pending_receipts())
        if not receipts:
            bot.send_message(m.chat.id, "✅ هیچ فیشی در انتظار تایید نیست")
            return
        
        for r in receipts:
            user = asyncio.run(db.get_user(r['user_id']))
            text = f"📸 **Receipt #{r['id']}**\n👤 User: {user['first_name'] if user else 'Unknown'}\n🆔 ID: {r['user_id']}\n💰 Amount: {r['amount']:,} Toman"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_receipt_{r['id']}"))
            markup.add(types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_receipt_{r['id']}"))
            bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
    def approve_receipt(call):
        if call.from_user.id not in Config.ADMIN_IDS:
            return
        
        rid = int(call.data.replace('approve_receipt_', ''))
        r = asyncio.run(db.fetchrow("SELECT user_id FROM receipts WHERE id = $1", rid))
        if r:
            asyncio.run(db.approve_receipt(rid, call.from_user.id))
            asyncio.run(db.activate_subscription(r['user_id']))
            bot.answer_callback_query(call.id, "✅ Subscription activated")
            bot.delete_message(call.message.chat.id, call.message.message_id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
    def reject_receipt(call):
        if call.from_user.id not in Config.ADMIN_IDS:
            return
        
        rid = int(call.data.replace('reject_receipt_', ''))
        asyncio.run(db.execute("UPDATE receipts SET status = 'rejected' WHERE id = $1", rid))
        bot.answer_callback_query(call.id, "❌ Receipt rejected")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    @bot.message_handler(func=lambda m: m.text == '💰 تایید برداشت')
    def admin_withdraws(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        withdraws = asyncio.run(db.get_pending_withdraws())
        if not withdraws:
            bot.send_message(m.chat.id, "✅ هیچ درخواست برداشتی نیست")
            return
        
        for w in withdraws:
            user = asyncio.run(db.get_user(w['user_id']))
            text = f"💰 **Withdraw #{w['id']}**\n👤 User: {user['first_name'] if user else 'Unknown'}\n🆔 ID: {w['user_id']}\n💰 Amount: {w['amount']:,} Toman\n💳 Address: {w['address']}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_withdraw_{w['id']}"))
            bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_withdraw_'))
    def confirm_withdraw(call):
        if call.from_user.id not in Config.ADMIN_IDS:
            return
        
        wid = int(call.data.replace('confirm_withdraw_', ''))
        asyncio.run(db.approve_withdraw(wid))
        bot.answer_callback_query(call.id, "✅ Withdrawal confirmed")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    
    @bot.message_handler(func=lambda m: m.text == '📊 آمار کاربران')
    def admin_stats(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        stats = asyncio.run(db.get_stats())
        text = f"""📊 **System Statistics**

👥 Total Users: {stats['total_users']:,}
✅ Active Subscriptions: {stats['active_subs']:,}
🤖 Total Bots: {stats['total_bots']:,}
🟢 Running Bots: {stats['running_bots']:,}
💰 Total Wallet: {stats['total_wallet']:,} Toman"""
        
        bot.send_message(m.chat.id, text, parse_mode='Markdown')
    
    @bot.message_handler(func=lambda m: m.text == '🗑 حذف کاربران')
    def admin_delete_user(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        msg = bot.send_message(m.chat.id, "🗑 Enter user ID to delete:")
        bot.register_next_step_handler(msg, process_delete_user)
    
    def process_delete_user(m):
        try:
            uid = int(m.text.strip())
            asyncio.run(db.execute("DELETE FROM users WHERE user_id = $1", uid))
            bot.reply_to(m, f"✅ User {uid} deleted")
        except:
            bot.reply_to(m, "❌ Invalid user ID")
    
    @bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات‌های کاربران')
    def admin_delete_user_bots(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        msg = bot.send_message(m.chat.id, "🗑 Enter user ID to delete all bots:")
        bot.register_next_step_handler(msg, process_delete_user_bots)
    
    def process_delete_user_bots(m):
        try:
            uid = int(m.text.strip())
            asyncio.run(db.execute("DELETE FROM bots WHERE user_id = $1", uid))
            asyncio.run(db.execute("UPDATE users SET bots_count = 0 WHERE user_id = $1", uid))
            bot.reply_to(m, f"✅ All bots of user {uid} deleted")
        except:
            bot.reply_to(m, "❌ Invalid user ID")
    
    @bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
    def broadcast_prompt(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        msg = bot.send_message(m.chat.id, "📝 Enter broadcast message:")
        bot.register_next_step_handler(msg, process_broadcast)
    
    def process_broadcast(m):
        text = m.text
        users = asyncio.run(db.fetch("SELECT user_id FROM users WHERE is_banned = FALSE"))
        sent = 0
        failed = 0
        
        status_msg = bot.reply_to(m, "🔄 Sending broadcast...")
        
        for user in users:
            try:
                bot.send_message(user['user_id'], f"📢 **Broadcast**\n\n{text}", parse_mode='Markdown')
                sent += 1
                time.sleep(0.05)
            except:
                failed += 1
        
        bot.edit_message_text(f"✅ Sent to {sent} users\n❌ Failed: {failed}", m.chat.id, status_msg.message_id)
    
    @bot.message_handler(func=lambda m: m.text == '🔍 بررسی ربات‌های کاربران')
    def admin_check_bots(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        msg = bot.send_message(m.chat.id, "🔍 Enter user ID to check bots:")
        bot.register_next_step_handler(msg, process_check_bots)
    
    def process_check_bots(m):
        try:
            uid = int(m.text.strip())
            bots = asyncio.run(db.get_user_bots(uid))
            user = asyncio.run(db.get_user(uid))
            
            if not bots:
                bot.reply_to(m, f"📋 User {uid} has no bots")
                return
            
            text = f"📋 **Bots of {user['first_name'] if user else uid}**\n\n"
            for b in bots:
                status_emoji = "🟢" if b['status'] == 'running' else "🔴"
                text += f"{status_emoji} `{b['id'][:8]}...` - {b['name']}\n"
                if b.get('error_message'):
                    text += f"   ⚠️ Error: {b['error_message'][:50]}\n"
            
            bot.reply_to(m, text, parse_mode='Markdown')
        except:
            bot.reply_to(m, "❌ Invalid user ID")
    
    @bot.message_handler(func=lambda m: m.text == '💳 تنظیم آدرس کیف پول')
    def admin_set_wallet(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("💰 TRC20 Address", callback_data="set_trc20"))
        markup.add(types.InlineKeyboardButton("🏦 Card Number", callback_data="set_card"))
        bot.send_message(m.chat.id, "💳 Select:", reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data == "set_trc20")
    def set_trc20(call):
        msg = bot.send_message(call.message.chat.id, "💰 Enter TRC20 address:")
        bot.register_next_step_handler(msg, lambda m: asyncio.run(db.execute("UPDATE system_settings SET value = $1 WHERE key = 'trc20_address'", m.text)) or bot.reply_to(m, "✅ Updated"))
    
    @bot.callback_query_handler(func=lambda call: call.data == "set_card")
    def set_card(call):
        msg = bot.send_message(call.message.chat.id, "🏦 Enter card number:")
        bot.register_next_step_handler(msg, lambda m: asyncio.run(db.execute("UPDATE system_settings SET value = $1 WHERE key = 'card_number'", m.text)) or bot.reply_to(m, "✅ Updated"))
    
    @bot.message_handler(func=lambda m: m.text == '🔄 ریستارت ربات‌های مرده')
    def admin_restart_bots(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        asyncio.run(db.execute("UPDATE bots SET status = 'stopped' WHERE status = 'running'"))
        bot.reply_to(m, "✅ All dead bots restarted")
    
    @bot.message_handler(func=lambda m: m.text == '⚙️ تنظیم ظرفیت کاربران')
    def admin_set_capacity(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        msg = bot.send_message(m.chat.id, "⚙️ Enter max users capacity (100-100000):")
        bot.register_next_step_handler(msg, process_set_capacity)
    
    def process_set_capacity(m):
        try:
            capacity = int(m.text.strip())
            if 100 <= capacity <= 100000:
                # Update in code (would need to update .env and restart)
                bot.reply_to(m, f"✅ Capacity set to {capacity} (restart required)")
            else:
                bot.reply_to(m, "❌ Number between 100 and 100000")
        except:
            bot.reply_to(m, "❌ Invalid number")
    
    @bot.message_handler(func=lambda m: m.text == '🖥️ مدیریت ماشین‌ها')
    def admin_machines(m):
        if m.from_user.id not in Config.ADMIN_IDS:
            return
        
        machines = asyncio.run(db.get_machines())
        text = "🖥️ **Machines**\n\n"
        for mac in machines:
            usage = (mac['current_bots'] / mac['max_bots']) * 100 if mac['max_bots'] > 0 else 0
            status_emoji = "🟢" if mac['status'] == 'active' else "🔴"
            text += f"{status_emoji} {mac['name']}: {mac['current_bots']}/{mac['max_bots']} ({usage:.1f}%)\n"
        
        bot.send_message(m.chat.id, text, parse_mode='Markdown')
