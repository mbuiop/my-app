#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات جامع تبدیل و دانلود مدیا
ویژگی‌ها: تبدیل عکس/ویدیو به لینک، استخراج صدا، TTS، دانلود اینستاگرام، فاکتور آنلاین
"""

import asyncio
import logging
import sqlite3
import os
import shutil
import json
import time
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager
from threading import Lock
import aiohttp
import aiofiles
from pathlib import Path

# ==================== تنظیمات ====================
try:
    import resource
    resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
except:
    pass

# ==================== Telegram ====================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ==================== پردازش مدیا ====================
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import qrcode
from gtts import gTTS
import instaloader
from yt_dlp import YoutubeDL

# ==================== تنظیمات لاگ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== تنظیمات اصلی ====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # 👈 توکن خود را وارد کنید
ADMIN_IDS = [327855654, 123456789]  # 👈 آیدی ادمین‌ها

# ==================== تنظیمات فایل ====================
UPLOAD_DIR = "uploads"
TEMP_DIR = "temp"
PDF_DIR = "pdfs"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_VIDEO_DURATION = 600  # 10 دقیقه

# ایجاد دایرکتوری‌ها
for dir_name in [UPLOAD_DIR, TEMP_DIR, PDF_DIR]:
    os.makedirs(dir_name, exist_ok=True)

# ==================== دیتابیس ====================
class Database:
    def __init__(self, db_path="media_bot.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language TEXT DEFAULT 'fa',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                    total_requests INTEGER DEFAULT 0,
                    is_premium INTEGER DEFAULT 0,
                    premium_expiry TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    input_text TEXT,
                    output_file TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    processed_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT UNIQUE,
                    user_id INTEGER,
                    customer_name TEXT,
                    customer_phone TEXT,
                    customer_email TEXT,
                    items TEXT,
                    subtotal REAL,
                    tax REAL,
                    total REAL,
                    status TEXT DEFAULT 'pending',
                    pdf_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('is_paid', '0')")
            conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('price_per_month', '10')")
            conn.commit()
    
    @asynccontextmanager
    async def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            """, (user_id, username, first_name))
            conn.commit()
            return await self.get_user(user_id)
    
    async def update_user_active(self, user_id: int):
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_active = CURRENT_TIMESTAMP, 
                total_requests = total_requests + 1
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
    
    async def add_request(self, user_id: int, type: str, input_text: str, output_file: str = None) -> int:
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO requests (user_id, type, input_text, output_file)
                VALUES (?, ?, ?, ?)
            """, (user_id, type, input_text, output_file))
            conn.commit()
            return cursor.lastrowid
    
    async def update_request(self, request_id: int, status: str, output_file: str = None):
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE requests SET status = ?, processed_at = CURRENT_TIMESTAMP, output_file = ?
                WHERE id = ?
            """, (status, output_file, request_id))
            conn.commit()
    
    async def create_invoice(self, user_id: int, customer_name: str, customer_phone: str,
                            customer_email: str, items: List[Dict], subtotal: float,
                            tax: float, total: float) -> Tuple[str, int]:
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO invoices (invoice_number, user_id, customer_name, customer_phone,
                    customer_email, items, subtotal, tax, total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_number, user_id, customer_name, customer_phone,
                  customer_email, json.dumps(items), subtotal, tax, total))
            conn.commit()
            return invoice_number, cursor.lastrowid
    
    async def update_invoice_pdf(self, invoice_id: int, pdf_path: str):
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE invoices SET pdf_path = ?, status = 'ready'
                WHERE id = ?
            """, (pdf_path, invoice_id))
            conn.commit()
    
    async def get_invoice(self, invoice_number: str) -> Optional[Dict]:
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM invoices WHERE invoice_number = ?", (invoice_number,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                data['items'] = json.loads(data['items'])
                return data
            return None
    
    async def get_user_requests(self, user_id: int, limit: int = 20) -> List[Dict]:
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM requests WHERE user_id = ? 
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    async def get_stats(self) -> Dict:
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM users")
            users = cursor.fetchone()['total']
            cursor.execute("SELECT COUNT(*) as total FROM requests")
            requests = cursor.fetchone()['total']
            cursor.execute("SELECT COUNT(*) as total FROM invoices WHERE status = 'ready'")
            invoices = cursor.fetchone()['total']
            return {
                'users': users,
                'requests': requests,
                'invoices': invoices
            }
    
    async def is_premium(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False
        if user['is_premium']:
            if user['premium_expiry']:
                if datetime.fromisoformat(user['premium_expiry']) > datetime.now():
                    return True
        return False
    
    async def set_premium(self, user_id: int, months: int = 1):
        expiry = datetime.now() + timedelta(days=30 * months)
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_premium = 1, premium_expiry = ?
                WHERE user_id = ?
            """, (expiry.isoformat(), user_id))
            conn.commit()

# ==================== کلاس پردازش مدیا ====================
class MediaProcessor:
    def __init__(self):
        self.upload_dir = UPLOAD_DIR
        self.temp_dir = TEMP_DIR
        self.session = None
    
    async def ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def download_file(self, url: str, filename: str) -> str:
        """دانلود فایل از URL"""
        session = await self.ensure_session()
        filepath = os.path.join(self.temp_dir, filename)
        
        async with session.get(url) as response:
            if response.status == 200:
                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(await response.read())
                return filepath
        return None
    
    async def upload_to_cloud(self, filepath: str, file_type: str = 'image') -> str:
        """آپلود فایل و دریافت لینک (از سرور خودت استفاده کن)"""
        # اینجا می‌توانید از Cloudinary، S3 یا سرور خودتان استفاده کنید
        # برای نمونه، لینک محلی برمی‌گردانیم
        
        filename = os.path.basename(filepath)
        upload_path = os.path.join(self.upload_dir, filename)
        shutil.copy(filepath, upload_path)
        
        # در حالت واقعی، اینجا آپلود روی سرور انجام میشه
        base_url = "https://your-server.com/uploads/"
        return f"{base_url}{filename}"
    
    # ===== ۱. تبدیل عکس به لینک =====
    async def photo_to_link(self, photo_path: str) -> Tuple[bool, str]:
        try:
            # بهینه‌سازی عکس
            img = Image.open(photo_path)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # فشرده‌سازی
            optimized_path = os.path.join(self.temp_dir, f"opt_{os.path.basename(photo_path)}")
            img.save(optimized_path, 'JPEG', quality=85, optimize=True)
            
            # آپلود
            link = await self.upload_to_cloud(optimized_path, 'image')
            return True, link
        except Exception as e:
            return False, str(e)
    
    # ===== ۲. تبدیل ویدیو به لینک =====
    async def video_to_link(self, video_path: str) -> Tuple[bool, str]:
        try:
            # فشرده‌سازی ویدیو
            clip = VideoFileClip(video_path)
            optimized_path = os.path.join(self.temp_dir, f"opt_{os.path.basename(video_path)}")
            clip.write_videofile(optimized_path, codec='libx264', audio_codec='aac', 
                                bitrate='2000k', fps=24)
            clip.close()
            
            # آپلود
            link = await self.upload_to_cloud(optimized_path, 'video')
            return True, link
        except Exception as e:
            return False, str(e)
    
    # ===== ۳. استخراج صدا از ویدیو =====
    async def extract_audio(self, video_path: str) -> Tuple[bool, str]:
        try:
            clip = VideoFileClip(video_path)
            audio_path = os.path.join(self.temp_dir, f"audio_{secrets.token_hex(8)}.mp3")
            clip.audio.write_audiofile(audio_path, bitrate='192k')
            clip.close()
            
            # آپلود
            link = await self.upload_to_cloud(audio_path, 'audio')
            return True, link
        except Exception as e:
            return False, str(e)
    
    # ===== ۴. تبدیل متن به صوت (TTS) =====
    async def text_to_speech(self, text: str, lang: str = 'fa', gender: str = 'male') -> Tuple[bool, str]:
        try:
            # پشتیبانی از زبان‌های مختلف
            lang_map = {
                'fa': 'fa', 'en': 'en', 'ar': 'ar', 'ru': 'ru', 
                'tr': 'tr', 'de': 'de', 'fr': 'fr', 'es': 'es',
                'it': 'it', 'ja': 'ja', 'ko': 'ko', 'zh': 'zh'
            }
            lang_code = lang_map.get(lang, 'fa')
            
            # محدودیت طول متن
            if len(text) > 5000:
                text = text[:5000]
            
            # ایجاد فایل صوتی
            tts = gTTS(text=text, lang=lang_code, slow=False)
            audio_path = os.path.join(self.temp_dir, f"tts_{secrets.token_hex(8)}.mp3")
            tts.save(audio_path)
            
            # آپلود
            link = await self.upload_to_cloud(audio_path, 'audio')
            return True, link
        except Exception as e:
            return False, str(e)
    
    # ===== ۵. دانلود از اینستاگرام =====
    async def download_instagram(self, url: str) -> Tuple[bool, str, str]:
        try:
            # تنظیمات yt-dlp برای اینستاگرام
            ydl_opts = {
                'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'format': 'best[ext=mp4]/best',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # اگر فایل mp4 نیست، تبدیل کن
                if not filename.endswith('.mp4'):
                    base = os.path.splitext(filename)[0]
                    mp4_path = base + '.mp4'
                    if os.path.exists(mp4_path):
                        filename = mp4_path
                
                # بررسی وجود فایل
                if not os.path.exists(filename):
                    # پیدا کردن فایل دانلود شده
                    for f in os.listdir(self.temp_dir):
                        if info['id'] in f and f.endswith('.mp4'):
                            filename = os.path.join(self.temp_dir, f)
                            break
                
                if not os.path.exists(filename):
                    return False, "فایل دانلود نشد", ""
                
                # آپلود و دریافت لینک
                link = await self.upload_to_cloud(filename, 'video')
                
                # اطلاعات ویدیو
                title = info.get('title', 'Instagram Video')
                return True, link, title
                
        except Exception as e:
            logger.error(f"Instagram download error: {e}")
            return False, str(e), ""
    
    # ===== ۶. ساخت فاکتور آنلاین =====
    async def create_invoice_pdf(self, invoice_data: Dict) -> Tuple[bool, str]:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm, inch
            from reportlab.pdfgen import canvas
            
            # تولید PDF
            pdf_filename = f"invoice_{invoice_data['invoice_number']}.pdf"
            pdf_path = os.path.join(PDF_DIR, pdf_filename)
            
            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            
            # ===== هدر =====
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a237e'),
                alignment=1,  # مرکز
                spaceAfter=20
            )
            
            # لوگو یا عنوان
            elements.append(Paragraph("📄 فاکتور رسمی", title_style))
            elements.append(Spacer(1, 10))
            
            # شماره فاکتور و تاریخ
            info_style = styles['Normal']
            elements.append(Paragraph(f"<b>شماره فاکتور:</b> {invoice_data['invoice_number']}", info_style))
            elements.append(Paragraph(f"<b>تاریخ:</b> {datetime.now().strftime('%Y/%m/%d %H:%M')}", info_style))
            elements.append(Spacer(1, 20))
            
            # ===== اطلاعات مشتری =====
            elements.append(Paragraph("<b>اطلاعات مشتری</b>", styles['Heading2']))
            elements.append(Paragraph(f"نام: {invoice_data['customer_name']}", info_style))
            if invoice_data.get('customer_phone'):
                elements.append(Paragraph(f"تلفن: {invoice_data['customer_phone']}", info_style))
            if invoice_data.get('customer_email'):
                elements.append(Paragraph(f"ایمیل: {invoice_data['customer_email']}", info_style))
            elements.append(Spacer(1, 20))
            
            # ===== جدول اقلام =====
            elements.append(Paragraph("<b>اقلام فاکتور</b>", styles['Heading2']))
            
            table_data = [
                ['ردیف', 'شرح', 'تعداد', 'قیمت واحد', 'قیمت کل']
            ]
            
            items = invoice_data.get('items', [])
            for i, item in enumerate(items, 1):
                table_data.append([
                    str(i),
                    item.get('description', ''),
                    str(item.get('quantity', 1)),
                    f"{item.get('price', 0):,} تومان",
                    f"{item.get('total', 0):,} تومان"
                ])
            
            # جمع‌ها
            table_data.append(['', '', '', 'جمع کل:', f"{invoice_data['total']:,} تومان"])
            
            # ایجاد جدول
            table = Table(table_data, colWidths=[0.8*cm, 6*cm, 1.5*cm, 2.5*cm, 2.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8eaf6')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))
            
            # ===== امضا =====
            elements.append(Paragraph("<b>مهر و امضای فروشنده</b>", styles['Heading2']))
            elements.append(Spacer(1, 40))
            elements.append(Paragraph("نام شرکت: شرکت نمونه", info_style))
            elements.append(Paragraph("تلفن: ۰۲۱-۱۲۳۴۵۶۷۸", info_style))
            
            # ساخت PDF
            doc.build(elements)
            
            # آپلود PDF
            link = await self.upload_to_cloud(pdf_path, 'pdf')
            return True, link
            
        except Exception as e:
            logger.error(f"Invoice PDF error: {e}")
            return False, str(e)
    
    async def close(self):
        if self.session:
            await self.session.close()

# ==================== ربات اصلی ====================
class MediaBot:
    def __init__(self, token: str):
        self.token = token
        self.db = Database()
        self.processor = MediaProcessor()
        self.user_states = {}
        self.pending_invoices = {}
        
        logger.info("🚀 ربات جامع مدیا راه‌اندازی شد")
    
    def get_text(self, lang: str, key: str, **kwargs) -> str:
        texts = {
            'fa': {
                'welcome': "🌟 به ربات جامع مدیا خوش آمدید!\n\n"
                          "🎯 با این ربات می‌توانید:\n"
                          "🖼️ عکس را به لینک تبدیل کنید\n"
                          "🎬 ویدیو را به لینک تبدیل کنید\n"
                          "🎵 از ویدیو صدا استخراج کنید\n"
                          "🎤 متن را به صوت تبدیل کنید\n"
                          "📥 از اینستاگرام دانلود کنید\n"
                          "📄 فاکتور آنلاین بسازید",
                
                'help': "📖 **راهنمای ربات**\n\n"
                       "📸 **تبدیل عکس:**\n"
                       "یک عکس ارسال کنید تا لینک دریافت کنید\n\n"
                       "🎬 **تبدیل ویدیو:**\n"
                       "یک ویدیو ارسال کنید تا لینک دریافت کنید\n\n"
                       "🎵 **استخراج صدا:**\n"
                       "یک ویدیو ارسال کرده و گزینه استخراج صدا را انتخاب کنید\n\n"
                       "🎤 **متن به صوت:**\n"
                       "از منو گزینه «متن به صوت» را انتخاب کرده و متن خود را ارسال کنید\n\n"
                       "📥 **دانلود اینستاگرام:**\n"
                       "لینک پست/ریلس/استوری اینستاگرام را ارسال کنید\n\n"
                       "📄 **ساخت فاکتور:**\n"
                       "از منو گزینه «ساخت فاکتور» را انتخاب کنید",
                
                'photo_to_link': "🖼️ عکس خود را ارسال کنید:\n\n"
                                "📌 عکس با کیفیت بالا آپلود و لینک دریافت می‌شود",
                
                'video_to_link': "🎬 ویدیو خود را ارسال کنید:\n\n"
                                "📌 ویدیو با کیفیت بالا آپلود و لینک دریافت می‌شود",
                
                'extract_audio': "🎵 ویدیو خود را ارسال کنید تا صدا استخراج شود",
                
                'tts_prompt': "🎤 متن خود را ارسال کنید:\n\n"
                             "📌 حداکثر ۵۰۰۰ کاراکتر\n"
                             "🌐 زبان‌های پشتیبانی: فارسی، انگلیسی، عربی، ترکی، روسی، آلمانی و...",
                
                'instagram_prompt': "📥 لینک اینستاگرام را ارسال کنید:\n\n"
                                   "🔹 پست: https://www.instagram.com/p/...\n"
                                   "🔹 ریلس: https://www.instagram.com/reel/...\n"
                                   "🔹 استوری: https://www.instagram.com/stories/...",
                
                'invoice_prompt': "📄 **ساخت فاکتور آنلاین**\n\n"
                                 "لطفا اطلاعات زیر را به ترتیب وارد کنید:\n\n"
                                 "1️⃣ نام مشتری\n"
                                 "2️⃣ تلفن مشتری (اختیاری)\n"
                                 "3️⃣ ایمیل مشتری (اختیاری)\n"
                                 "4️⃣ شرح کالا/خدمت\n"
                                 "5️⃣ تعداد\n"
                                 "6️⃣ قیمت واحد\n\n"
                                 "📌 مثال:\n"
                                 "علی محمدی\n"
                                 "09123456789\n"
                                 "ali@email.com\n"
                                 "لپ تاپ\n"
                                 "2\n"
                                 "15000000",
                
                'processing': "⏳ در حال پردازش... لطفاً صبر کنید",
                'success': "✅ عملیات با موفقیت انجام شد!\n\n🔗 لینک: {link}",
                'error': "❌ خطا: {error}",
                'not_premium': "❌ این قابلیت فقط برای کاربران ویژه (Premium) فعال است.\n"
                               "💳 برای خرید اشتراک از ادمین پیام دهید.",
                
                'invoice_result': "✅ **فاکتور شما آماده شد!**\n\n"
                                 "📄 شماره فاکتور: {number}\n"
                                 "👤 مشتری: {customer}\n"
                                 "💰 مبلغ کل: {total:,} تومان\n"
                                 "🔗 لینک دانلود: {link}",
                
                'menu': "📋 **منوی اصلی**",
                
                'stats': "📊 **آمار ربات**\n\n"
                        "👥 کل کاربران: {users:,}\n"
                        "📝 درخواست‌ها: {requests:,}\n"
                        "📄 فاکتورها: {invoices:,}",
                
                'admin_panel': "🛠 **پنل مدیریت**",
                
                'broadcast_prompt': "📢 پیام خود را برای ارسال همگانی وارد کنید:",
                'broadcast_sent': "✅ پیام به {count} کاربر ارسال شد",
                
                'premium_set': "✅ اشتراک ویژه برای کاربر {user_id} به مدت {months} ماه فعال شد",
                'premium_error': "❌ کاربر یافت نشد",
            },
            'en': {
                'welcome': "🌟 Welcome to Media Bot!\n\n"
                          "🎯 Features:\n"
                          "🖼️ Photo to Link\n"
                          "🎬 Video to Link\n"
                          "🎵 Extract Audio from Video\n"
                          "🎤 Text to Speech\n"
                          "📥 Instagram Downloader\n"
                          "📄 Create Online Invoice"
            }
        }
        
        lang_texts = texts.get(lang, texts['fa'])
        return lang_texts.get(key, key).format(**kwargs)
    
    # ===== دستورات اصلی =====
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        # ثبت کاربر
        db_user = await self.db.get_user(user_id)
        if not db_user:
            await self.db.create_user(user_id, user.username, user.first_name)
        
        await self.db.update_user_active(user_id)
        
        lang = db_user.get('language', 'fa') if db_user else 'fa'
        
        # منوی اصلی
        keyboard = [
            [InlineKeyboardButton("🖼️ عکس به لینک", callback_data='photo_to_link')],
            [InlineKeyboardButton("🎬 ویدیو به لینک", callback_data='video_to_link')],
            [InlineKeyboardButton("🎵 استخراج صدا", callback_data='extract_audio')],
            [InlineKeyboardButton("🎤 متن به صوت", callback_data='tts')],
            [InlineKeyboardButton("📥 دانلود اینستاگرام", callback_data='instagram')],
            [InlineKeyboardButton("📄 ساخت فاکتور", callback_data='invoice')],
            [InlineKeyboardButton("📊 آمار من", callback_data='my_stats')],
            [InlineKeyboardButton("❓ راهنما", callback_data='help')],
        ]
        
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data='admin_panel')])
        
        await update.message.reply_text(
            self.get_text(lang, 'welcome'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ===== Callback ها =====
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        db_user = await self.db.get_user(user_id)
        lang = db_user.get('language', 'fa') if db_user else 'fa'
        
        data = query.data
        
        if data == 'photo_to_link':
            await query.edit_message_text(
                self.get_text(lang, 'photo_to_link'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ])
            )
            self.user_states[user_id] = 'waiting_for_photo'
        
        elif data == 'video_to_link':
            await query.edit_message_text(
                self.get_text(lang, 'video_to_link'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ])
            )
            self.user_states[user_id] = 'waiting_for_video'
        
        elif data == 'extract_audio':
            await query.edit_message_text(
                self.get_text(lang, 'extract_audio'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ])
            )
            self.user_states[user_id] = 'waiting_for_audio_extract'
        
        elif data == 'tts':
            # بررسی پریمیوم
            is_premium = await self.db.is_premium(user_id)
            if not is_premium:
                await query.edit_message_text(
                    self.get_text(lang, 'not_premium'),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ])
                )
                return
            
            await query.edit_message_text(
                self.get_text(lang, 'tts_prompt'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 انتخاب زبان", callback_data='tts_lang')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ])
            )
            self.user_states[user_id] = 'waiting_for_tts'
        
        elif data == 'tts_lang':
            keyboard = [
                [InlineKeyboardButton("🇮🇷 فارسی", callback_data='tts_set_lang_fa')],
                [InlineKeyboardButton("🇬🇧 English", callback_data='tts_set_lang_en')],
                [InlineKeyboardButton("🇦🇪 العربية", callback_data='tts_set_lang_ar')],
                [InlineKeyboardButton("🇷🇺 Русский", callback_data='tts_set_lang_ru')],
                [InlineKeyboardButton("🇹🇷 Türkçe", callback_data='tts_set_lang_tr')],
                [InlineKeyboardButton("🇩🇪 Deutsch", callback_data='tts_set_lang_de')],
                [InlineKeyboardButton("🇫🇷 Français", callback_data='tts_set_lang_fr')],
                [InlineKeyboardButton("🇪🇸 Español", callback_data='tts_set_lang_es')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
            ]
            await query.edit_message_text(
                "🌐 **انتخاب زبان**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data.startswith('tts_set_lang_'):
            lang_code = data.split('_')[3]
            self.user_states[f"tts_lang_{user_id}"] = lang_code
            await query.edit_message_text(
                f"✅ زبان انتخاب شد!\n\n{self.get_text(lang, 'tts_prompt')}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ])
            )
            self.user_states[user_id] = 'waiting_for_tts'
        
        elif data == 'instagram':
            await query.edit_message_text(
                self.get_text(lang, 'instagram_prompt'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ])
            )
            self.user_states[user_id] = 'waiting_for_instagram'
        
        elif data == 'invoice':
            await query.edit_message_text(
                self.get_text(lang, 'invoice_prompt'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ])
            )
            self.user_states[user_id] = 'waiting_for_invoice'
        
        elif data == 'my_stats':
            user_requests = await self.db.get_user_requests(user_id, 10)
            is_premium = await self.db.is_premium(user_id)
            
            text = f"📊 **آمار شما**\n\n"
            text += f"🆔 ID: {user_id}\n"
            text += f"⭐ وضعیت: {'💎 ویژه' if is_premium else '🆓 معمولی'}\n"
            text += f"📝 کل درخواست‌ها: {db_user.get('total_requests', 0)}\n"
            text += f"📅 آخرین فعالیت: {db_user.get('last_active', '')[:16]}\n\n"
            text += f"📋 **آخرین درخواست‌ها:**\n"
            
            for req in user_requests[:5]:
                text += f"• {req['type']} - {req['created_at'][:16]}\n"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == 'help':
            await query.edit_message_text(
                self.get_text(lang, 'help'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == 'admin_panel' and user_id in ADMIN_IDS:
            keyboard = [
                [InlineKeyboardButton("📢 ارسال همگانی", callback_data='broadcast')],
                [InlineKeyboardButton("📊 آمار کلی", callback_data='admin_stats')],
                [InlineKeyboardButton("💎 اعطای پریمیوم", callback_data='set_premium')],
                [InlineKeyboardButton("📋 لیست کاربران", callback_data='list_users')],
                [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
            ]
            await query.edit_message_text(
                self.get_text(lang, 'admin_panel'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == 'admin_stats' and user_id in ADMIN_IDS:
            stats = await self.db.get_stats()
            await query.edit_message_text(
                self.get_text(lang, 'stats', **stats),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 بروزرسانی", callback_data='admin_stats')],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == 'broadcast' and user_id in ADMIN_IDS:
            await query.edit_message_text(
                self.get_text(lang, 'broadcast_prompt'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                ])
            )
            self.user_states[user_id] = 'waiting_for_broadcast'
        
        elif data == 'set_premium' and user_id in ADMIN_IDS:
            await query.edit_message_text(
                "💎 **اعطای اشتراک ویژه**\n\n"
                "لطفا آیدی کاربر و تعداد ماه را به این فرمت وارد کنید:\n"
                "`USER_ID MONTHS`\n\n"
                "مثال: `123456789 3`",
                parse_mode=ParseMode.MARKDOWN
            )
            self.user_states[user_id] = 'waiting_for_premium'
        
        elif data == 'list_users' and user_id in ADMIN_IDS:
            await query.edit_message_text("⏳ در حال دریافت لیست...")
            
            async with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, first_name, total_requests, is_premium 
                    FROM users ORDER BY total_requests DESC LIMIT 50
                """)
                rows = cursor.fetchall()
            
            text = "📋 **۵۰ کاربر برتر**\n\n"
            for i, row in enumerate(rows, 1):
                text += f"{i}. 🆔 {row['user_id']} - {row['first_name'] or 'کاربر'}\n"
                text += f"   📝 {row['total_requests']} درخواست - {'💎' if row['is_premium'] else '🆓'}\n"
            
            await query.edit_message_text(
                text[:4000],
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif data == 'back':
            keyboard = [
                [InlineKeyboardButton("🖼️ عکس به لینک", callback_data='photo_to_link')],
                [InlineKeyboardButton("🎬 ویدیو به لینک", callback_data='video_to_link')],
                [InlineKeyboardButton("🎵 استخراج صدا", callback_data='extract_audio')],
                [InlineKeyboardButton("🎤 متن به صوت", callback_data='tts')],
                [InlineKeyboardButton("📥 دانلود اینستاگرام", callback_data='instagram')],
                [InlineKeyboardButton("📄 ساخت فاکتور", callback_data='invoice')],
                [InlineKeyboardButton("📊 آمار من", callback_data='my_stats')],
                [InlineKeyboardButton("❓ راهنما", callback_data='help')],
            ]
            if user_id in ADMIN_IDS:
                keyboard.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data='admin_panel')])
            
            await query.edit_message_text(
                self.get_text(lang, 'welcome'),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ===== پردازش پیام‌ها =====
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        db_user = await self.db.get_user(user_id)
        lang = db_user.get('language', 'fa') if db_user else 'fa'
        state = self.user_states.get(user_id)
        
        # ===== برودکست =====
        if state == 'waiting_for_broadcast' and user_id in ADMIN_IDS:
            msg_text = update.message.text or update.message.caption or ""
            photo = update.message.photo[-1].file_id if update.message.photo else None
            
            # دریافت لیست کاربران
            async with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users")
                users = [row['user_id'] for row in cursor.fetchall()]
            
            await update.message.reply_text(f"⏳ ارسال به {len(users)} کاربر...")
            
            success_count = 0
            for uid in users:
                try:
                    if photo:
                        await context.bot.send_photo(uid, photo, caption=msg_text, parse_mode=ParseMode.HTML)
                    else:
                        await context.bot.send_message(uid, msg_text, parse_mode=ParseMode.HTML)
                    success_count += 1
                    await asyncio.sleep(0.05)  # جلوگیری از محدودیت
                except:
                    pass
            
            await update.message.reply_text(
                self.get_text(lang, 'broadcast_sent', count=success_count),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                ])
            )
            self.user_states[user_id] = None
        
        # ===== اعطای پریمیوم =====
        elif state == 'waiting_for_premium' and user_id in ADMIN_IDS:
            try:
                parts = update.message.text.strip().split()
                target_id = int(parts[0])
                months = int(parts[1]) if len(parts) > 1 else 1
                
                await self.db.set_premium(target_id, months)
                await update.message.reply_text(
                    self.get_text(lang, 'premium_set', user_id=target_id, months=months),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                    ])
                )
            except:
                await update.message.reply_text(
                    self.get_text(lang, 'premium_error'),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]
                    ])
                )
            self.user_states[user_id] = None
        
        # ===== عکس به لینک =====
        elif state == 'waiting_for_photo':
            if not update.message.photo:
                await update.message.reply_text("❌ لطفاً یک عکس ارسال کنید")
                return
            
            await update.message.reply_text(self.get_text(lang, 'processing'))
            
            photo = await update.message.photo[-1].get_file()
            file_path = os.path.join(TEMP_DIR, f"photo_{secrets.token_hex(8)}.jpg")
            await photo.download_to_drive(file_path)
            
            success, result = await self.processor.photo_to_link(file_path)
            
            if success:
                await self.db.add_request(user_id, 'photo_to_link', '', result)
                await update.message.reply_text(
                    self.get_text(lang, 'success', link=result),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ])
                )
            else:
                await update.message.reply_text(
                    self.get_text(lang, 'error', error=result)
                )
            
            os.remove(file_path)
            self.user_states[user_id] = None
        
        # ===== ویدیو به لینک =====
        elif state == 'waiting_for_video':
            if not update.message.video:
                await update.message.reply_text("❌ لطفاً یک ویدیو ارسال کنید")
                return
            
            await update.message.reply_text(self.get_text(lang, 'processing'))
            
            video = await update.message.video.get_file()
            file_path = os.path.join(TEMP_DIR, f"video_{secrets.token_hex(8)}.mp4")
            await video.download_to_drive(file_path)
            
            success, result = await self.processor.video_to_link(file_path)
            
            if success:
                await self.db.add_request(user_id, 'video_to_link', '', result)
                await update.message.reply_text(
                    self.get_text(lang, 'success', link=result),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ])
                )
            else:
                await update.message.reply_text(
                    self.get_text(lang, 'error', error=result)
                )
            
            os.remove(file_path)
            self.user_states[user_id] = None
        
        # ===== استخراج صدا =====
        elif state == 'waiting_for_audio_extract':
            if not update.message.video:
                await update.message.reply_text("❌ لطفاً یک ویدیو ارسال کنید")
                return
            
            await update.message.reply_text(self.get_text(lang, 'processing'))
            
            video = await update.message.video.get_file()
            file_path = os.path.join(TEMP_DIR, f"video_{secrets.token_hex(8)}.mp4")
            await video.download_to_drive(file_path)
            
            success, result = await self.processor.extract_audio(file_path)
            
            if success:
                await self.db.add_request(user_id, 'extract_audio', '', result)
                await update.message.reply_text(
                    self.get_text(lang, 'success', link=result),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ])
                )
                # ارسال فایل صوتی هم
                audio_path = os.path.join(TEMP_DIR, f"audio_{secrets.token_hex(8)}.mp3")
                if os.path.exists(audio_path):
                    await update.message.reply_audio(open(audio_path, 'rb'))
            else:
                await update.message.reply_text(
                    self.get_text(lang, 'error', error=result)
                )
            
            os.remove(file_path)
            self.user_states[user_id] = None
        
        # ===== متن به صوت (TTS) =====
        elif state == 'waiting_for_tts':
            text = update.message.text
            if not text:
                await update.message.reply_text("❌ لطفاً متن خود را ارسال کنید")
                return
            
            if len(text) > 5000:
                await update.message.reply_text("❌ متن طولانی است. حداکثر ۵۰۰۰ کاراکتر")
                return
            
            await update.message.reply_text(self.get_text(lang, 'processing'))
            
            tts_lang = self.user_states.get(f"tts_lang_{user_id}", 'fa')
            
            success, result = await self.processor.text_to_speech(text, tts_lang)
            
            if success:
                await self.db.add_request(user_id, 'tts', text[:100], result)
                await update.message.reply_text(
                    self.get_text(lang, 'success', link=result),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ])
                )
                # ارسال فایل صوتی
                audio_path = os.path.join(TEMP_DIR, f"tts_{secrets.token_hex(8)}.mp3")
                if os.path.exists(audio_path):
                    await update.message.reply_audio(open(audio_path, 'rb'))
            else:
                await update.message.reply_text(
                    self.get_text(lang, 'error', error=result)
                )
            
            self.user_states[user_id] = None
        
        # ===== دانلود اینستاگرام =====
        elif state == 'waiting_for_instagram':
            url = update.message.text.strip()
            if not url.startswith(('http://', 'https://')):
                await update.message.reply_text("❌ لطفاً یک لینک معتبر ارسال کنید")
                return
            
            if 'instagram.com' not in url:
                await update.message.reply_text("❌ لطفاً یک لینک اینستاگرام ارسال کنید")
                return
            
            await update.message.reply_text(self.get_text(lang, 'processing'))
            
            # بررسی پریمیوم برای دانلود با کیفیت بالا
            is_premium = await self.db.is_premium(user_id)
            
            success, result, title = await self.processor.download_instagram(url)
            
            if success:
                await self.db.add_request(user_id, 'instagram', url, result)
                await update.message.reply_text(
                    self.get_text(lang, 'success', link=result),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                    ])
                )
            else:
                await update.message.reply_text(
                    self.get_text(lang, 'error', error=result)
                )
            
            self.user_states[user_id] = None
        
        # ===== ساخت فاکتور =====
        elif state == 'waiting_for_invoice':
            lines = update.message.text.strip().split('\n')
            if len(lines) < 4:
                await update.message.reply_text(
                    "❌ اطلاعات کامل نیست. لطفاً همه موارد را وارد کنید:\n\n"
                    "نام مشتری\nتلفن (اختیاری)\nایمیل (اختیاری)\nشرح کالا\nتعداد\nقیمت واحد"
                )
                return
            
            try:
                customer_name = lines[0].strip()
                customer_phone = lines[1].strip() if len(lines) > 1 else ""
                customer_email = lines[2].strip() if len(lines) > 2 else ""
                description = lines[3].strip() if len(lines) > 3 else ""
                quantity = int(lines[4].strip()) if len(lines) > 4 else 1
                unit_price = float(lines[5].strip()) if len(lines) > 5 else 0
                
                if not customer_name or not description:
                    await update.message.reply_text("❌ نام مشتری و شرح کالا الزامی است")
                    return
                
                subtotal = quantity * unit_price
                tax = subtotal * 0.09  # 9% مالیات
                total = subtotal + tax
                
                items = [{
                    'description': description,
                    'quantity': quantity,
                    'price': unit_price,
                    'total': subtotal
                }]
                
                await update.message.reply_text("⏳ در حال ساخت فاکتور...")
                
                # ذخیره در دیتابیس
                invoice_number, invoice_id = await self.db.create_invoice(
                    user_id, customer_name, customer_phone,
                    customer_email, items, subtotal, tax, total
                )
                
                invoice_data = {
                    'invoice_number': invoice_number,
                    'customer_name': customer_name,
                    'customer_phone': customer_phone,
                    'customer_email': customer_email,
                    'items': items,
                    'subtotal': subtotal,
                    'tax': tax,
                    'total': total
                }
                
                # ساخت PDF
                success, pdf_link = await self.processor.create_invoice_pdf(invoice_data)
                
                if success:
                    await self.db.update_invoice_pdf(invoice_id, pdf_link)
                    await update.message.reply_text(
                        self.get_text(lang, 'invoice_result', 
                                    number=invoice_number,
                                    customer=customer_name,
                                    total=int(total),
                                    link=pdf_link),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 بازگشت", callback_data='back')]
                        ])
                    )
                else:
                    await update.message.reply_text(
                        self.get_text(lang, 'error', error=pdf_link)
                    )
                
            except ValueError as e:
                await update.message.reply_text(f"❌ خطا در اطلاعات: {e}")
            except Exception as e:
                await update.message.reply_text(f"❌ خطا: {e}")
            
            self.user_states[user_id] = None
        
        else:
            # پیام ناشناخته
            await update.message.reply_text(
                "❓ دستور نامعتبر\n\n"
                "برای شروع /start را بزنید",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 صفحه اصلی", callback_data='back')]
                ])
            )
    
    # ===== راه‌اندازی =====
    async def run(self):
        application = Application.builder().token(self.token).build()
        
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        application.add_handler(MessageHandler(
            filters.TEXT | filters.PHOTO | filters.VIDEO, 
            self.handle_message
        ))
        
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        logger.info("✅ ربات جامع مدیا راه‌اندازی شد!")
        
        try:
            await asyncio.Event().wait()
        finally:
            await application.updater.stop()
            await application.stop()
            await self.processor.close()

# ==================== اجرا ====================
async def main():
    bot = MediaBot(BOT_TOKEN)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())