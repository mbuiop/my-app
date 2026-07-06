# ============================================================
# ربات با کلید HeyGen (کلید شما)
# ============================================================

import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===== تنظیمات =====
TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
HEYGEN_API_KEY = "sk_V2_hgu_kJHEhaemD1l_ou2ZGBKET0jsW7ONhqHgG4NUx06xlpbl"

logging.basicConfig(level=logging.INFO)

# ===== ربات =====
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    waiting_text = State()

# ============================================================
# ساخت ویدیو با کلید شما
# ============================================================

async def create_video(text: str) -> str:
    """ساخت ویدیو با کلید HeyGen"""
    
    url = "https://api.heygen.com/v1/video.generate"
    
    headers = {
        "x-api-key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "avatar_id": "default",
        "script": text,
        "duration": 30,
        "background": {"type": "color", "value": "#1a1a2e"}
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=60) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"خطا: {response.status} - {error}")
            
            data = await response.json()
            task_id = data.get("data", {}).get("task_id")
            
            if not task_id:
                raise Exception("شناسه کار دریافت نشد")
            
            # بررسی وضعیت
            for i in range(30):
                await asyncio.sleep(2)
                
                status_url = f"https://api.heygen.com/v1/video.status?task_id={task_id}"
                async with session.get(status_url, headers=headers) as status_resp:
                    status_data = await status_resp.json()
                    status = status_data.get("data", {}).get("status")
                    
                    if status == "completed":
                        video_url = status_data.get("data", {}).get("video_url")
                        return video_url
                    
                    elif status == "failed":
                        raise Exception("ساخت ویدیو ناموفق بود")
            
            raise Exception("زمان ساخت ویدیو تمام شد")

# ============================================================
# هندلرهای ربات
# ============================================================

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(Form.waiting_text)
    await message.answer(
        "🎬 **ربات سازنده ویدیو با HeyGen**\n\n"
        "سلام! متن خود را بفرستید تا ویدیو بسازم.\n\n"
        "📝 **مثال:**\n"
        "`یک ویدیوی تبلیغاتی برای محصول جدید`\n\n"
        "⏱ زمان ساخت: ~۳۰-۶۰ ثانیه",
        parse_mode="Markdown"
    )

@dp.message(Form.waiting_text)
async def make_video(message: types.Message, state: FSMContext):
    text = message.text
    
    if len(text) < 5:
        await message.answer("❌ حداقل ۵ کلمه بفرستید.")
        return
    
    status = await message.answer("🎬 در حال ساخت ویدیو... ⏳")
    
    try:
        video_url = await create_video(text)
        
        await message.answer_video(
            video=video_url,
            caption=f"✅ **ویدیو ساخته شد!**\n\n📝 {text[:100]}..."
        )
        
        await status.delete()
        
    except Exception as e:
        await status.edit_text(f"❌ خطا: {str(e)[:150]}")

# ============================================================
# اجرا
# ============================================================

async def main():
    print("=" * 50)
    print("🎬 ربات با کلید HeyGen")
    print("=" * 50)
    print("✅ کلید تنظیم شد")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())