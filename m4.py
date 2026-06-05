#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
🎛️ m4.py - پنل مدیریت پیشرفته + دوزبانه (فارسی/انگلیسی)
═══════════════════════════════════════════════════════════════════
"""

import telebot
from telebot import types
from typing import Dict
from loguru import logger
import os
import json
from datetime import datetime

# ==================== زبان‌ها ====================
LANGUAGES = {
    'fa': {
        'welcome': "🚀 خوش آمدید {name}!",
        'no_subscription': "❌ اشتراک فعال نیست",
        'subscription_price': "💰 قیمت اشتراک: {price}",
        'referral_link': "🔗 لینک دعوت: {link}",
        'build_success': "✅ ربات {name} ساخته شد!",
        'build_error': "❌ خطا: {error}",
        'server_full': "🚫 سرور پر است. لطفاً بعداً تلاش کنید.",
        'maintenance_mode': "🔧 سرور در حال تعمیر است. لطفاً بعداً تلاش کنید.",
        'admin_panel': "👑 پنل مدیریت",
        'receipts': "📸 فیش‌ها",
        'withdraws': "💰 برداشت‌ها",
        'settings': "⚙️ تنظیمات",
        'users': "👥 کاربران",
        'backup': "💾 بکاپ",
        'stats': "📊 آمار"
    },
    'en': {
        'welcome': "🚀 Welcome {name}!",
        'no_subscription': "❌ No active subscription",
        'subscription_price': "💰 Price: {price}",
        'referral_link': "🔗 Referral link: {link}",
        'build_success': "✅ Bot {name} created!",
        'build_error': "❌ Error: {error}",
        'server_full': "🚫 Server is full. Please try again later.",
        'maintenance_mode': "🔧 Server is under maintenance. Please try again later.",
        'admin_panel': "👑 Admin Panel",
        'receipts': "📸 Receipts",
        'withdraws': "💰 Withdrawals",
        'settings': "⚙️ Settings",
        'users': "👥 Users",
        'backup': "💾 Backup",
        'stats': "📊 Statistics"
    }
}

class AdminPanel:
    """پنل مدیریت پیشرفته"""
    
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """دریافت متن بر اساس زبان کاربر"""
        # TODO: دریافت زبان کاربر از دیتابیس
        lang = 'fa'
        text = LANGUAGES.get(lang, LANGUAGES['fa']).get(key, key)
        return text.format(**kwargs) if kwargs else text
    
    async def show_maintenance_settings(self, call, admin_id: int):
        """تنظیمات حالت تعمیرات"""
        if admin_id not in ADMIN_IDS:
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # دریافت وضعیت فعلی
        maintenance_mode = await self.db.get_setting('maintenance_mode')
        current_message = await self.db.get_setting('maintenance_message')
        
        status_text = "🟢 فعال" if maintenance_mode == 'true' else "🔴 غیرفعال"
        
        markup.add(
            types.InlineKeyboardButton(
                f"🔄 تغییر وضعیت ({status_text})", 
                callback_data="admin_toggle_maintenance"
            ),
            types.InlineKeyboardButton(
                "✏️ تغییر پیام", 
                callback_data="admin_edit_maintenance_msg"
            ),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        
        await self.bot.edit_message_text(
            f"🔧 **حالت تعمیرات سرور**\n\n"
            f"وضعیت: {status_text}\n"
            f"پیام فعلی:\n`{current_message}`\n\n"
            f"وقتی فعال باشد، کاربران جدید پیام زیر را می‌بینند:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
    
    async def toggle_maintenance_mode(self, call):
        """تغییر وضعیت حالت تعمیرات"""
        current = await self.db.get_setting('maintenance_mode')
        new_status = 'false' if current == 'true' else 'true'
        await self.db.set_setting('maintenance_mode', new_status)
        
        await self.bot.answer_callback_query(
            call.id, 
            f"✅ حالت تعمیرات {'فعال' if new_status == 'true' else 'غیرفعال'} شد"
        )
        
        # به‌روزرسانی منو
        await self.show_maintenance_settings(call, call.from_user.id)
    
    async def show_backup_panel(self, call, admin_id: int):
        """پنل بکاپ‌گیری"""
        if admin_id not in ADMIN_IDS:
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("💾 بکاپ فوری", callback_data="admin_backup_now"),
            types.InlineKeyboardButton("📋 لیست بکاپ‌ها", callback_data="admin_backup_list"),
            types.InlineKeyboardButton("🗑 حذف بکاپ قدیمی", callback_data="admin_backup_clean"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        
        await self.bot.edit_message_text(
            "💾 **سیستم بکاپ‌گیری خودکار**\n\n"
            "• بکاپ روزانه ساعت ۳ بامداد\n"
            "• نگهداری ۳۰ روز آخر\n"
            "• قابلیت بکاپ دستی\n"
            "• ذخیره در فضای ابری (اختیاری)",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
    
    async def backup_now(self, call):
        """بکاپ فوری"""
        await self.bot.edit_message_text(
            "🔄 در حال بکاپ‌گیری...",
            call.message.chat.id,
            call.message.message_id
        )
        
        # گرفتن بکاپ
        backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        import subprocess
        db_url = os.getenv("DATABASE_URL", "")
        
        if db_url:
            # PostgreSQL backup
            result = subprocess.run(
                ['pg_dump', db_url, '-f', f'/tmp/{backup_file}'],
                capture_output=True
            )
            
            if result.returncode == 0:
                # ذخیره در دیتابیس
                backup_path = f"/tmp/{backup_file}"
                size = os.path.getsize(backup_path)
                
                async with self.db.get_session() as session:
                    from m1 import Backup
                    backup = Backup(
                        filename=backup_file,
                        size=size,
                        location=backup_path
                    )
                    session.add(backup)
                
                # ارسال فایل
                with open(backup_path, 'rb') as f:
                    await self.bot.send_document(call.message.chat.id, f)
                
                await self.bot.edit_message_text(
                    f"✅ بکاپ با موفقیت گرفته شد!\n"
                    f"📁 {backup_file}\n"
                    f"💾 حجم: {size / 1024 / 1024:.2f} MB",
                    call.message.chat.id,
                    call.message.message_id
                )
            else:
                await self.bot.edit_message_text(
                    f"❌ خطا در بکاپ‌گیری: {result.stderr}",
                    call.message.chat.id,
                    call.message.message_id
                )
    
    async def show_language_settings(self, call, user_id: int):
        """تنظیمات زبان"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
            types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="settings_back")
        )
        
        current_lang = await self.db.get_setting('language')
        
        await self.bot.edit_message_text(
            "🌍 **انتخاب زبان / Choose Language**\n\n"
            f"زبان فعلی: {'فارسی' if current_lang == 'fa' else 'English'}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )

# ==================== ایجاد پنل ====================
ADMIN_IDS = [327855654]

async def setup_admin_handlers(bot, db):
    """تنظیم هندلرهای پنل مدیریت"""
    panel = AdminPanel(bot, db)
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_maintenance")
    async def maintenance_handler(call):
        await panel.show_maintenance_settings(call, call.from_user.id)
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_toggle_maintenance")
    async def toggle_handler(call):
        await panel.toggle_maintenance_mode(call)
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
    async def backup_handler(call):
        await panel.show_backup_panel(call, call.from_user.id)
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_backup_now")
    async def backup_now_handler(call):
        await panel.backup_now(call)
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_language")
    async def language_handler(call):
        await panel.show_language_settings(call, call.from_user.id)
    
    logger.info("✅ Admin handlers registered")
