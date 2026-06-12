import hashlib
import os
import time
import asyncio
from telebot import types
from core.database import Database
from core.config import Config
from texts import get_text

db = Database()

def register_payment_handlers(bot):
    
    @bot.message_handler(func=lambda m: m.text in ['💰 کیف پول و اشتراک', '💰 Wallet & Subscription'])
    def wallet(m):
        user_id = m.from_user.id
        user = asyncio.run(db.get_user(user_id))
        if not user:
            return
        
        lang = user.get('language', 'fa')
        is_subscribed = user.get('subscription_status') == 'active'
        
        if lang == 'fa':
            text = f"""💰 **کیف پول و اشتراک**

👤 {user.get('first_name', 'کاربر')}
💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}
💰 موجودی: {user.get('wallet_balance', 0):,} تومان
👥 دعوت‌ها: {user.get('referrals_count', 0)}

💳 برای فعالسازی {Config.SUBSCRIPTION_PRICE:,} تومان را به کارت زیر واریز:
`{Config.CARD_NUMBER}`
👤 {Config.CARD_HOLDER}
🏦 {Config.CARD_BANK}

📸 پس از واریز، تصویر تراکنش را ارسال کنید"""
        else:
            text = f"""💰 **Wallet & Subscription**

👤 {user.get('first_name', 'User')}
💳 Status: {'✅ Active' if is_subscribed else '❌ Inactive'}
💰 Balance: {user.get('wallet_balance', 0):,} Toman
👥 Referrals: {user.get('referrals_count', 0)}

💳 To activate, send {Config.SUBSCRIPTION_PRICE // 40000} USD to:
`{Config.TRC20_ADDRESS}`
🌐 Network: TRC20 (USDT)

📸 Send transaction screenshot after payment"""
        
        bot.send_message(m.chat.id, text, parse_mode='Markdown')
    
    @bot.message_handler(content_types=['photo'])
    def handle_receipt(m):
        user_id = m.from_user.id
        
        existing = asyncio.run(db.fetchrow("SELECT id FROM receipts WHERE user_id = $1 AND status = 'pending'", user_id))
        if existing:
            bot.reply_to(m, get_text(user_id, 'receipt_pending'))
            return
        
        try:
            file_info = bot.get_file(m.photo[-1].file_id)
            content = bot.download_file(file_info.file_path)
            
            tx_hash = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16].upper()
            receipt_path = f"receipts/{user_id}_{tx_hash}.jpg"
            
            os.makedirs("receipts", exist_ok=True)
            with open(receipt_path, 'wb') as f:
                f.write(content)
            
            receipt_id = asyncio.run(db.create_receipt(user_id, Config.SUBSCRIPTION_PRICE, receipt_path, tx_hash))
            
            bot.reply_to(m, get_text(user_id, 'receipt_received'))
            
            for admin_id in Config.ADMIN_IDS:
                try:
                    with open(receipt_path, 'rb') as f:
                        caption = f"📸 New Receipt\n👤 User: {m.from_user.first_name}\n🆔 ID: {user_id}\n💰 Amount: {Config.SUBSCRIPTION_PRICE:,} Toman"
                        bot.send_photo(admin_id, f, caption=caption)
                except:
                    pass
                    
        except Exception as e:
            bot.reply_to(m, get_text(user_id, 'error', error=str(e)[:50]))
    
    @bot.message_handler(func=lambda m: m.text in ['💸 درخواست برداشت', '💸 Withdraw'])
    def withdraw(m):
        user_id = m.from_user.id
        user = asyncio.run(db.get_user(user_id))
        if not user:
            bot.send_message(m.chat.id, get_text(user_id, 'error', error="Start with /start"))
            return
        
        balance = user.get('wallet_balance', 0)
        if balance < Config.MIN_WITHDRAW:
            text = f"❌ Minimum withdrawal is {Config.MIN_WITHDRAW:,} Toman\n💰 Your balance: {balance:,} Toman"
            bot.send_message(m.chat.id, text)
            return
        
        msg = bot.send_message(m.chat.id, "💳 Enter TRC20 address for withdrawal:")
        bot.register_next_step_handler(msg, process_withdraw, user)
    
    def process_withdraw(m, user):
        address = m.text.strip()
        amount = user.get('wallet_balance', 0)
        
        asyncio.run(db.create_withdraw(user['user_id'], amount, address))
        
        text = f"✅ Withdrawal request for {amount:,} Toman submitted!"
        bot.send_message(m.chat.id, text)
        
        for admin_id in Config.ADMIN_IDS:
            try:
                bot.send_message(admin_id, f"💰 Withdrawal Request\n👤 {user.get('first_name', 'Unknown')}\n🆔 {user['user_id']}\n💰 {amount:,} Toman\n💳 {address}")
            except:
                pass
    
    @bot.message_handler(func=lambda m: m.text in ['👥 دعوت دوستان', '👥 Invite Friends'])
    def invite(m):
        user_id = m.from_user.id
        user = asyncio.run(db.get_user(user_id))
        if not user:
            return
        
        link = f"https://t.me/{Config.BOT_USERNAME}?start={user['referral_code']}"
        
        text = f"""👥 **Referral System**

🎁 Referral Code: `{user['referral_code']}`
🔗 Invite Link: `{link}`
📊 Referrals: {user.get('referrals_count', 0)}
💰 Commission: {Config.WITHDRAW_PERCENT}% of each subscription
💎 Total Commission: {user.get('total_commission', 0):,} Toman"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{user['referral_code']}"))
        bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('copy_'))
    def copy_link(call):
        code = call.data.replace('copy_', '')
        link = f"https://t.me/{Config.BOT_USERNAME}?start={code}"
        bot.answer_callback_query(call.id, f"✅ Link copied!\n{link}", show_alert=True)
