# ========================================================================
# UTYOB ULTRA - ربات پیشرفته سازنده ویدیوهای تبلیغاتی
# ========================================================================
# سرعت بالا + کیفیت عالی + انیمیشن‌های متنوع
# ========================================================================

import os
import asyncio
import logging
import tempfile
import time
import random
import gc
import warnings
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

warnings.filterwarnings("ignore")

# ===== کتابخانه‌های اصلی =====
import torch
import numpy as np
import imageio
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import cv2
from moviepy.editor import *
from moviepy.video.fx import fadein, fadeout

# ===== کتابخانه‌های هوش مصنوعی =====
from diffusers import StableDiffusionPipeline, LCMScheduler, StableDiffusionXLPipeline
from transformers import pipeline

# ===== کتابخانه‌های تلگرام =====
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ===== تنظیمات =====
logging.basicConfig(level=logging.WARNING)

# توکن ربات
BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"

# تنظیمات سرعت و کیفیت
NUM_INFERENCE_STEPS = 6  # استپ کم برای سرعت بالا
NUM_FRAMES = 20  # ۲۰ فریم = ۵ ثانیه با ۴ فریم در ثانیه
FRAME_SIZE = (512, 384)  # سایز تصویر
VIDEO_FPS = 4

# ============================================================
# انواع انیمیشن‌های تبلیغاتی
# ============================================================

class AnimationStyles:
    """انواع انیمیشن‌های تبلیغاتی مدرن"""
    
    STYLES = {
        "cinematic": {
            "name": "🎬 سینمایی",
            "description": "حرکت آرام دوربین، نورپردازی دراماتیک",
            "variations": [
                "cinematic shot",
                "dramatic lighting",
                "slow camera movement",
                "depth of field",
                "film grain"
            ]
        },
        "product": {
            "name": "📦 محصول",
            "description": "نمایش ۳۶۰ درجه محصول",
            "variations": [
                "product showcase",
                "360 degree rotation",
                "studio lighting",
                "white background",
                "professional product photography"
            ]
        },
        "abstract": {
            "name": "🎨 انتزاعی",
            "description": "انیمیشن‌های گرافیکی مدرن",
            "variations": [
                "abstract motion graphics",
                "geometric shapes",
                "flowing particles",
                "modern design",
                "minimalist"
            ]
        },
        "fast": {
            "name": "⚡ سریع",
            "description": "حرکت تند و هیجان‌انگیز",
            "variations": [
                "fast motion",
                "dynamic movement",
                "action camera",
                "speed effect",
                "energetic"
            ]
        },
        "tech": {
            "name": "💻 تکنولوژی",
            "description": "سبک مدرن و دیجیتال",
            "variations": [
                "digital art",
                "cyberpunk style",
                "neon lights",
                "futuristic",
                "technology"
            ]
        },
        "luxury": {
            "name": "👑 لوکس",
            "description": "سبک طلایی و مجلل",
            "variations": [
                "golden color",
                "luxury style",
                "premium",
                "elegant design",
                "sophisticated"
            ]
        },
        "minimal": {
            "name": "✨ مینیمال",
            "description": "ساده و شیک",
            "variations": [
                "minimalist design",
                "clean background",
                "simple shapes",
                "elegant motion"
            ]
        },
        "colorful": {
            "name": "🌈 رنگارنگ",
            "description": "انیمیشن با رنگ‌های زنده",
            "variations": [
                "vibrant colors",
                "colorful animation",
                "rainbow effect",
                "bright palette"
            ]
        }
    }
    
    @classmethod
    def get_all_styles(cls) -> List[str]:
        return list(cls.STYLES.keys())
    
    @classmethod
    def get_style_info(cls, style: str) -> Dict:
        return cls.STYLES.get(style, cls.STYLES["cinematic"])
    
    @classmethod
    def get_random_style(cls) -> str:
        return random.choice(cls.get_all_styles())
    
    @classmethod
    def get_variation(cls, style: str, index: int) -> str:
        style_data = cls.get_style_info(style)
        variations = style_data["variations"]
        return variations[index % len(variations)]

# ============================================================
# کلاس پیشرفته ساخت ویدیو
# ============================================================

class AdvancedVideoEngine:
    """
    موتور پیشرفته ساخت ویدیو با انیمیشن‌های متنوع
    زمان ساخت: ~۴۰-۶۰ ثانیه
    """
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.pipe = None
        self.model_loaded = False
        self._load_model()
    
    def _load_model(self):
        """بارگذاری مدل هوش مصنوعی"""
        try:
            print(f"🔄 بارگذاری مدل روی {self.device}...")
            
            self.pipe = StableDiffusionPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False
            )
            
            self.pipe.scheduler = LCMScheduler.from_config(
                self.pipe.scheduler.config,
                use_karras_sigmas=True
            )
            
            if self.device == "cuda":
                self.pipe.enable_attention_slicing()
            
            self.pipe = self.pipe.to(self.device)
            
            # پیش‌گرم کردن
            print("🔥 پیش‌گرم کردن مدل...")
            with torch.no_grad():
                _ = self.pipe(
                    prompt="test",
                    num_inference_steps=2,
                    guidance_scale=1.0
                )
            
            self.model_loaded = True
            print(f"✅ مدل آماده است! (زمان ساخت: ~40-60 ثانیه)")
            
        except Exception as e:
            print(f"⚠️ مدل با خطا بارگذاری شد: {e}")
            self.model_loaded = False
    
    def generate_video(
        self, 
        prompt: str, 
        style: str = "cinematic",
        duration: int = 5,
        custom_animation: Optional[str] = None
    ) -> str:
        """
        ساخت ویدیو با انیمیشن دلخواه
        """
        start_time = time.time()
        print(f"🎬 ساخت ویدیو با سبک {style}...")
        
        # دریافت اطلاعات سبک
        style_info = AnimationStyles.get_style_info(style)
        variations = style_info["variations"]
        
        # تعداد فریم‌ها
        num_frames = duration * VIDEO_FPS
        
        # ساخت فریم‌ها
        frames = []
        
        for i in range(num_frames):
            # انتخاب تغییرات برای هر فریم
            variation = variations[i % len(variations)]
            
            # پرامپت کامل
            full_prompt = f"{prompt}, {variation}, high quality, 4k, professional"
            
            # ساخت تصویر
            with torch.no_grad():
                result = self.pipe(
                    prompt=full_prompt,
                    negative_prompt="blurry, low quality, ugly, deformed, bad composition",
                    num_inference_steps=NUM_INFERENCE_STEPS,
                    guidance_scale=2.0,
                    height=FRAME_SIZE[1],
                    width=FRAME_SIZE[0]
                )
            
            img = result.images[0]
            
            # اعمال افکت‌های اضافی بر اساس سبک
            img = self._apply_style_effects(img, style)
            
            frames.append(np.array(img))
            
            # آزادسازی حافظه
            gc.collect()
        
        # اعمال انیمیشن‌های پیشرفته
        if custom_animation:
            frames = self._apply_custom_animation(frames, custom_animation)
        
        # ذخیره ویدیو
        video_path = self._save_video(frames, duration)
        
        elapsed = time.time() - start_time
        print(f"✅ ویدیو در {elapsed:.1f} ثانیه ساخته شد!")
        
        return video_path
    
    def _apply_style_effects(self, image: Image, style: str) -> Image:
        """اعمال افکت‌های سبک روی تصویر"""
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.3)
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        if style == "luxury":
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.2)
            # افزودن رنگ طلایی ملایم
        
        elif style == "tech":
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.3)
        
        elif style == "colorful":
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.5)
        
        return image
    
    def _apply_custom_animation(self, frames: List[np.ndarray], animation_type: str) -> List[np.ndarray]:
        """اعمال انیمیشن‌های سفارشی"""
        
        if animation_type == "zoom":
            # انیمیشن زوم
            for i, frame in enumerate(frames):
                h, w = frame.shape[:2]
                scale = 1 + (i / len(frames)) * 0.3
                new_h, new_w = int(h * scale), int(w * scale)
                resized = cv2.resize(frame, (new_w, new_h))
                crop_h, crop_w = (new_h - h) // 2, (new_w - w) // 2
                frames[i] = resized[crop_h:crop_h+h, crop_w:crop_w+w]
        
        elif animation_type == "rotate":
            # چرخش ملایم
            for i, frame in enumerate(frames):
                angle = (i / len(frames)) * 10 - 5
                h, w = frame.shape[:2]
                center = (w//2, h//2)
                rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
                frames[i] = cv2.warpAffine(frame, rot_mat, (w, h))
        
        elif animation_type == "fade":
            # محو شدن
            for i, frame in enumerate(frames):
                alpha = (i + 1) / len(frames)
                frames[i] = (frame * alpha).astype(np.uint8)
        
        elif animation_type == "glitch":
            # افکت گلیچ
            for i, frame in enumerate(frames):
                if i % 3 == 0:
                    h, w = frame.shape[:2]
                    shift = random.randint(5, 20)
                    frames[i] = np.roll(frame, shift, axis=1)
        
        return frames
    
    def _save_video(self, frames: List[np.ndarray], duration: int) -> str:
        """ذخیره ویدیو"""
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, f"video_{int(time.time())}.mp4")
        
        writer = imageio.get_writer(
            video_path,
            fps=VIDEO_FPS,
            codec='libx264',
            quality=8,
            pixel_format='yuv420p',
            output_params=['-crf', '20', '-preset', 'fast']
        )
        
        for frame in frames:
            writer.append_data(frame)
        
        writer.close()
        return video_path

# ============================================================
# ربات تلگرام با دکمه‌های انتخاب انیمیشن
# ============================================================

class VideoStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_style = State()

class UTYOBUltraBot:
    """ربات پیشرفته سازنده ویدیو"""
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.engine = AdvancedVideoEngine()
        self.user_style = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """ثبت هندلرها"""
        
        @self.dp.message(Command("start"))
        async def start_cmd(message: types.Message, state: FSMContext):
            # دکمه‌های انتخاب انیمیشن
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🎬 سینمایی", callback_data="style_cinematic")],
                [types.InlineKeyboardButton(text="📦 محصول", callback_data="style_product")],
                [types.InlineKeyboardButton(text="🎨 انتزاعی", callback_data="style_abstract")],
                [types.InlineKeyboardButton(text="⚡ سریع", callback_data="style_fast")],
                [types.InlineKeyboardButton(text="💻 تکنولوژی", callback_data="style_tech")],
                [types.InlineKeyboardButton(text="👑 لوکس", callback_data="style_luxury")],
                [types.InlineKeyboardButton(text="✨ مینیمال", callback_data="style_minimal")],
                [types.InlineKeyboardButton(text="🌈 رنگارنگ", callback_data="style_colorful")]
            ])
            
            await message.answer(
                "🚀 **ربات پیشرفته سازنده ویدیوهای تبلیغاتی**\n\n"
                "🔥 در کمتر از ۱ دقیقه ویدیو بسازید!\n\n"
                "📝 **چگونه کار می‌کند:**\n"
                "۱. سبک انیمیشن را انتخاب کنید\n"
                "۲. متن خود را بفرستید\n"
                "۳. ویدیو را دریافت کنید\n\n"
                "✨ **قابلیت‌ها:**\n"
                "• ۸ سبک انیمیشن مختلف\n"
                "• کیفیت سینمایی\n"
                "• ساخت سریع (< ۱ دقیقه)\n"
                "• کاملاً رایگان",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        
        @self.dp.callback_query(lambda c: c.data.startswith("style_"))
        async def handle_style(callback: types.CallbackQuery, state: FSMContext):
            style = callback.data.replace("style_", "")
            self.user_style[callback.from_user.id] = style
            
            style_info = AnimationStyles.get_style_info(style)
            
            await callback.message.edit_text(
                f"✅ **سبک انتخاب شد:** {style_info['name']}\n"
                f"📝 {style_info['description']}\n\n"
                "📤 **حالا متن خود را بفرستید:**\n"
                "مثال: `A golden logo with blue neon lights`",
                parse_mode="Markdown"
            )
            
            await callback.answer()
            await state.set_state(VideoStates.waiting_for_text)
        
        @self.dp.message(VideoStates.waiting_for_text)
        async def handle_text(message: types.Message, state: FSMContext):
            text = message.text
            user_id = message.from_user.id
            
            if len(text) < 3:
                await message.answer("❌ لطفاً متن معتبری بفرستید (حداقل ۳ کاراکتر).")
                return
            
            # دریافت سبک کاربر
            style = self.user_style.get(user_id, "cinematic")
            style_info = AnimationStyles.get_style_info(style)
            
            status = await message.answer(
                f"⚡ **در حال ساخت ویدیو با سبک {style_info['name']}...**\n"
                f"⏳ حدود ۴۰-۶۰ ثانیه\n"
                f"🎬 {style_info['description']}",
                parse_mode="Markdown"
            )
            
            try:
                # انتخاب انیمیشن تصادفی
                animations = ["zoom", "rotate", "fade", "glitch", None]
                selected_animation = random.choice(animations)
                
                # ساخت ویدیو
                video_path = self.engine.generate_video(
                    prompt=text,
                    style=style,
                    duration=5,
                    custom_animation=selected_animation
                )
                
                # ارسال ویدیو
                with open(video_path, 'rb') as f:
                    await message.answer_video(
                        video=types.BufferedInputFile(f.read(), filename="video.mp4"),
                        caption=(
                            f"✅ **ویدیوی شما آماده است!**\n\n"
                            f"🎨 سبک: {style_info['name']}\n"
                            f"⏱ مدت: ۵ ثانیه\n"
                            f"🎬 افکت: {selected_animation or 'عادی'}\n"
                            f"⚡ زمان ساخت: کمتر از ۱ دقیقه\n\n"
                            "🔄 **برای ساخت ویدیوی جدید:**\n"
                            "• /start - انتخاب سبک جدید\n"
                            "• متن جدید - ساخت با همین سبک"
                        ),
                        parse_mode="Markdown"
                    )
                
                # پاک کردن فایل
                os.remove(video_path)
                os.rmdir(os.path.dirname(video_path))
                
                await status.delete()
                
            except Exception as e:
                await status.edit_text(
                    f"❌ **خطا:**\n```\n{str(e)[:150]}\n```\n\n"
                    "لطفاً متن خود را کوتاه‌تر یا ساده‌تر بنویسید.",
                    parse_mode="Markdown"
                )
            
            await state.set_state(VideoStates.waiting_for_text)
    
    async def start(self):
        print("=" * 60)
        print("🚀 UTYOB ULTRA - ربات پیشرفته سازنده ویدیو")
        print("=" * 60)
        print(f"📱 Device: {self.engine.device}")
        print(f"⚡ زمان ساخت: ~40-60 ثانیه")
        print(f"🎨 تعداد سبک‌ها: {len(AnimationStyles.get_all_styles())}")
        print("=" * 60)
        print("🤖 ربات آماده است! (با ۸ سبک انیمیشن)")
        print("=" * 60)
        
        await self.dp.start_polling(self.bot)

# ============================================================
# اجرا
# ============================================================

async def main():
    bot = UTYOBUltraBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())