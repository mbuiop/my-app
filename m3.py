#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
⚙️ m3.py - موتور اجرای ربات‌ها - مدیریت ۱۰۰,۰۰۰+ ربات
═══════════════════════════════════════════════════════════════════
"""

import asyncio
import hashlib
import os
import subprocess
import time
from typing import Dict, Optional
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
import aiofiles
import tempfile

# ==================== تنظیمات ====================
MAX_CONCURRENT_BUILDS = 50
BUILD_TIMEOUT = 60  # seconds
MAX_BOTS_PER_MACHINE = 10000

class BuildQueueManager:
    """مدیریت صف ساخت با قابلیت مقیاس بالا"""
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self.active_builds = {}
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BUILDS)
    
    async def add_build(self, user_id: int, bot_id: str, code: str, token: str, chat_id: int):
        """افزودن به صف"""
        build_item = {
            'user_id': user_id,
            'bot_id': bot_id,
            'code': code,
            'token': token,
            'chat_id': chat_id,
            'timestamp': time.time()
        }
        await self.queue.put(build_item)
        return len(self.active_builds) + self.queue.qsize()
    
    async def process_builds(self, bot_instance, db):
        """پردازش صف"""
        while True:
            try:
                build_item = await self.queue.get()
                self.active_builds[build_item['bot_id']] = build_item
                
                # اجرای در ترد جداگانه
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    self._execute_bot,
                    build_item['code'],
                    build_item['token'],
                    build_item['bot_id']
                )
                
                if result['success']:
                    # ذخیره در دیتابیس
                    await db.add_bot(
                        build_item['bot_id'],
                        build_item['user_id'],
                        result['encrypted_token'],
                        result['bot_name'],
                        result['bot_username'],
                        result['container_id']
                    )
                    
                    # ارسال پیام موفقیت
                    await bot_instance.send_message(
                        build_item['chat_id'],
                        f"✅ ربات {result['bot_name']} با موفقیت ساخته شد!"
                    )
                    
                    # اضافه کردن کمیسیون به معرف
                    user = await db.get_user(build_item['user_id'])
                    if user and user.get('referred_by'):
                        subscription_price = int(await db.get_setting('subscription_price'))
                        commission_percent = int(await db.get_setting('withdraw_percent'))
                        commission = int(subscription_price * commission_percent / 100)
                        
                        await db.update_user(
                            user['referred_by'],
                            wallet_balance=await db.get_user(user['referred_by']).wallet_balance + commission
                        )
                        
                        await bot_instance.send_message(
                            user['referred_by'],
                            f"🎉 کمیسیون {commission:,} تومان به کیف پول شما اضافه شد!"
                        )
                else:
                    await bot_instance.send_message(
                        build_item['chat_id'],
                        f"❌ خطا در ساخت ربات: {result['error']}"
                    )
                
                del self.active_builds[build_item['bot_id']]
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Build processing error: {e}")
    
    def _execute_bot(self, code: str, token: str, bot_id: str) -> Dict:
        """اجرای واقعی ربات (در ترد جداگانه)"""
        from m2 import isolator
        import requests
        import base64
        from cryptography.fernet import Fernet
        
        try:
            # بررسی توکن
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                return {'success': False, 'error': 'توکن نامعتبر'}
            
            bot_info = resp.json()['result']
            
            # رمزنگاری توکن
            key = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
            cipher = Fernet(key)
            encrypted_token = cipher.encrypt(token.encode()).decode()
            
            # ایجاد کانتینر
            container_id = asyncio.run(isolator.create_bot_container(
                bot_id, code, token, 0
            ))
            
            if container_id:
                return {
                    'success': True,
                    'encrypted_token': encrypted_token,
                    'bot_name': bot_info['first_name'],
                    'bot_username': bot_info['username'],
                    'container_id': container_id
                }
            else:
                return {'success': False, 'error': 'خطا در ایجاد کانتینر'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

class BotManager:
    """مدیریت ربات‌های در حال اجرا"""
    
    def __init__(self):
        self.active_bots = {}  # bot_id -> container_id
        
    async def stop_all_user_bots(self, user_id: int, db):
        """توقف همه ربات‌های یک کاربر (برای غیرفعال کردن مادر)"""
        bots = await db.get_user_bots(user_id)
        from m2 import isolator
        
        for bot in bots:
            if bot.get('container_id'):
                await isolator.stop_bot_container(bot['id'], bot['container_id'])
                await db.update_bot_status(bot['id'], 'stopped')
        
        return len(bots)
    
    async def start_all_user_bots(self, user_id: int, db):
        """راه‌اندازی مجدد همه ربات‌های کاربر (بعد از ریستارت مادر)"""
        # TODO: بازیابی ربات‌ها از دیتابیس
        pass

# نمونه گلوبال
build_queue = BuildQueueManager()
bot_manager = BotManager()
