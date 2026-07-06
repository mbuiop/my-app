# ========================================================================
# ربات سازنده ویدیو با هوش مصنوعی (نسخه سبک و عملی)
# ========================================================================

import os
import asyncio
import logging
import tempfile
import time
from typing import List
import warnings
warnings.filterwarnings("ignore")

# ===== کتابخانه‌های اصلی =====
import torch
import numpy as np
import imageio
from PIL import Image

# ===== کتابخانه‌های هوش مصنوعی =====
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from transformers import pipeline

# ===== کتابخانه‌های تلگرام =====
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===== تنظیمات =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات خود را وارد کنید
BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"

# ============================================================
# کلاس ساخت ویدیو با مدل سبک
# ============================================================

class LightVideoEngine:
    """
    موتور ساخت ویدیو با مدل‌های سبک
    بدون نیاز به GPU سنگین
    """
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipe = None
        self._load_model()
    
    def _load_model(self):
        """بارگذاری مدل سبک"""
        try:
            logger.info(f"🔄 بارگذاری مدل روی {self.device}...")
            
            # استفاده از مدل سبک Stable Diffusion
            self.pipe = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False
            )
            
            # تنظیمات سریع‌تر
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config,
                use_karras_sigmas=True
            )
            
            if self.device == "cuda":
                self.pipe.enable_attention_slicing()
                self.pipe.enable_xformers_memory_efficient_attention()
            
            self.pipe = self.pipe.to(self.device)
            
            logger.info(f"✅ مدل بارگذاری شد روی {self.device}")
            
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری مدل: {e}")
            raise
    
    def generate_video(self, prompt: str, duration: int = 3) -> str:
        """
        ساخت ویدیو از متن
        خروجی: مسیر فایل ویدیو
        """
        try:
            logger.info(f"🎬 ساخت ویدیو: {prompt[:50]}...")
            
            # تعداد فریم‌ها (۴ فریم در ثانیه)
            num_frames = duration * 4
            frames = []
            
            # ساخت هر فریم با کمی تغییر در پرامپت
            for i in range(num_frames):
                # تغییر جزئی پرامپت برای حرکت
                variation = ""
                if i % 4 == 0:
                    variation = " wide shot"
                elif i % 4 == 1:
                    variation = " close up"
                elif i % 4 == 2:
                    variation = " from left"
                else:
                    variation = " from right"
                
                frame_prompt = f"{prompt}, cinematic quality, 4K, detailed{variation}"
                
                # تولید تصویر
                with torch.no_grad():
                    result = self.pipe(
                        prompt=frame_prompt,
                        negative_prompt="blurry, low quality, distorted, ugly, deformed",
                        num_inference_steps=25,
                        guidance_scale=7.5,
                        height=512,
                        width=768
                    )
                
                img = result.images[0]
                frames.append(np.array(img))
                
                logger.info(f"  فریم {i+1}/{num_frames} ساخته شد")
            
            # ذخیره ویدیو
            video_path = self._save_video(frames, duration)
            
            logger.info(f"✅ ویدیو ساخته شد: {video_path}")
            return video_path
            
        except Exception as e:
            logger.error(f"❌ خطا: {e}")
            raise
    
    def _save_video(self, frames: List[np.ndarray], duration: int) -> str:
        """ذخیره ویدیو"""
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, f"video_{int(time.time())}.mp4")
        
        writer = imageio.get_writer(
            video_path,
            fps=4,
            codec='libx264',
            quality=8,
            pixel_format='yuv420p'
        )
        
        for frame in frames:
            writer.append_data(frame)
        
        writer.close()
        return video_path

# ============================================================
# ربات تلگرام
# ============================================================

class VideoStates(StatesGroup):
    waiting_for_text = State()

class VideoBot:
    """ربات سازنده ویدیو"""
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.engine = LightVideoEngine()
        self._register_handlers()
    
    def _register_handlers(self):
        """ثبت هندلرها"""
        
        @self.dp.message(Command("start"))
        async def start_cmd(message: types.Message, state: FSMContext):
            await state.set_state(VideoStates.waiting_for_text)
            await message.answer(
                "🎬 **ربات سازنده ویدیو**\n\n"
                "سلام! من یک ربات هوشمند هستم که متن شما را به ویدیو تبدیل می‌کند.\n\n"
                "📝 **چگونه کار می‌کند؟**\n"
                "۱. یک متن توصیفی بفرستید (ترجیحاً انگلیسی)\n"
                "۲. من یک ویدیوی ۳ ثانیه‌ای می‌سازم\n"
                "۳. ویدیو را برایتان ارسال می‌کنم\n\n"
                "✨ **مثال:**\n"
                "`A golden logo with blue neon lights in a futuristic city`\n\n"
                "⏱ زمان ساخت: حدود ۱-۲ دقیقه\n"
                "🎵 ویدیو بدون صدا است",
                parse_mode="Markdown"
            )
        
        @self.dp.message(VideoStates.waiting_for_text)
        async def handle_text(message: types.Message, state: FSMContext):
            """دریافت متن و ساخت ویدیو"""
            
            text = message.text
            
            if len(text) < 3:
                await message.answer("❌ لطفاً متن معتبری بفرستید.")
                return
            
            status = await message.answer(
                "🎥 **در حال ساخت ویدیو...**\n"
                "⏳ حدود ۱-۲ دقیقه زمان نیاز است.",
                parse_mode="Markdown"
            )
            
            try:
                # ساخت ویدیو
                video_path = self.engine.generate_video(text, duration=3)
                
                # ارسال ویدیو
                with open(video_path, 'rb') as f:
                    await message.answer_video(
                        video=types.BufferedInputFile(f.read(), filename="video.mp4"),
                        caption=(
                            "✅ **ویدیو ساخته شد!**\n\n"
                            "⏱ مدت: ۳ ثانیه\n"
                            "🎨 کیفیت: 720p\n"
                            "🎵 بدون صدا - صدای خود را اضافه کنید.\n\n"
                            "🔄 برای ویدیوی جدید، دوباره متن بفرستید."
                        ),
                        parse_mode="Markdown"
                    )
                
                # پاک کردن فایل
                os.remove(video_path)
                os.rmdir(os.path.dirname(video_path))
                
                await status.delete()
                
            except Exception as e:
                await status.edit_text(
                    f"❌ **خطا:**\n"
                    f"```\n{str(e)[:200]}\n```\n\n"
                    "لطفاً متن خود را کوتاه‌تر یا ساده‌تر بنویسید.",
                    parse_mode="Markdown"
                )
                logger.error(f"خطا: {e}")
            
            await state.set_state(VideoStates.waiting_for_text)
    
    async def start(self):
        """اجرای ربات"""
        print("=" * 50)
        print("🎬 ربات سازنده ویدیو")
        print("=" * 50)
        print(f"📱 Device: {self.engine.device}")
        print("🤖 ربات آماده است!")
        print("=" * 50)
        
        await self.dp.start_polling(self.bot)

# ============================================================
# اجرا
# ============================================================

async def main():
    bot = VideoBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())