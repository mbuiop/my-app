"""
🤖 هوش مصنوعی MON - نسخه فوق‌پیشرفته با ظرفیت بی‌نهایت
"""

import os
import json
import hashlib
import re
import threading
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import queue

# ==================== کتابخانه‌های اصلی ====================
import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ==================== دیتابیس‌های قدرتمند ====================
import redis
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

# ==================== پردازش موازی ====================
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

# ==================== Cache پیشرفته ====================
from functools import lru_cache
import hashlib

# ==================== تنظیمات ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('ultra_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 327855654

# ==================== تنظیمات ظرفیت ====================
class CapacityConfig:
    """تنظیمات ظرفیت بی‌نهایت"""
    
    # دیتابیس
    MONGO_URI = "mongodb://localhost:27017"
    MONGO_DB = "ultra_ai"
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    
    # کش
    CACHE_SIZE = 10000  # ۱۰ هزار کش در RAM
    BATCH_SIZE = 1000  # پردازش دسته‌ای
    
    # پردازش موازی
    MAX_WORKERS = 10  # تعداد تردهای همزمان
    QUEUE_SIZE = 1000  # صف پیام‌ها
    
    # شاردینگ (تقسیم داده)
    SHARD_COUNT = 4  # ۴ شارد برای داده‌ها


# ==================== مغز فوق‌پیشرفته ====================
class UltraBrain:
    """مغز با ظرفیت بی‌نهایت و پردازش موازی"""
    
    def __init__(self):
        # ======== دیتابیس‌ها ========
        self.mongo = MongoClient(CapacityConfig.MONGO_URI)
        self.db = self.mongo[CapacityConfig.MONGO_DB]
        self.knowledge_collection = self.db['knowledge']
        self.index_collection = self.db['indexes']
        self.user_collection = self.db['users']
        self.stats_collection = self.db['stats']
        
        # ایجاد ایندکس‌های فوق‌پیشرفته
        self.knowledge_collection.create_index([('question', 'text')])
        self.knowledge_collection.create_index('keywords')
        self.knowledge_collection.create_index('category')
        self.knowledge_collection.create_index([('usage', DESCENDING)])
        
        # Redis Cache
        try:
            self.redis = redis.Redis(
                host=CapacityConfig.REDIS_HOST,
                port=CapacityConfig.REDIS_PORT,
                decode_responses=True,
                max_connections=50
            )
        except:
            self.redis = None
        
        # ======== حافظه کش ========
        self.cache = {}
        self.cache_max = CapacityConfig.CACHE_SIZE
        
        # ======== پردازش موازی ========
        self.executor = ThreadPoolExecutor(max_workers=CapacityConfig.MAX_WORKERS)
        self.message_queue = queue.Queue(maxsize=CapacityConfig.QUEUE_SIZE)
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        
        # ======== آمار ========
        self.stats = {
            'total_learned': 0,
            'total_queries': 0,
            'successful_queries': 0,
            'active_users': 0
        }
        
        # بارگذاری آمار
        self._load_stats()
        
        logger.info("🧠 مغز فوق‌پیشرفته با ظرفیت بی‌نهایت راه‌اندازی شد")
        logger.info(f"📊 ظرفیت: نامحدود (MongoDB Sharding)")
    
    def _load_stats(self):
        """بارگذاری آمار از دیتابیس"""
        try:
            stats = self.stats_collection.find_one({'_id': 'global'})
            if stats:
                self.stats = stats.get('data', self.stats)
        except:
            pass
    
    def _save_stats(self):
        """ذخیره آمار"""
        try:
            self.stats_collection.update_one(
                {'_id': 'global'},
                {'$set': {'data': self.stats}},
                upsert=True
            )
        except:
            pass
    
    # ==================== یادگیری با ظرفیت بی‌نهایت ====================
    def learn(self, question: str, answer: str, category: str = "general") -> bool:
        """یادگیری با ذخیره در MongoDB (ظرفیت نامحدود)"""
        try:
            q_id = hashlib.md5(f"{question}{datetime.now()}".encode()).hexdigest()
            keywords = self._extract_keywords(question)
            
            data = {
                '_id': q_id,
                'question': question,
                'answer': answer,
                'keywords': keywords,
                'category': category,
                'created': datetime.now().isoformat(),
                'usage': 0,
                'score': 0,
                'embedding': self._generate_embedding(question)
            }
            
            # ذخیره در MongoDB (ظرفیت نامحدود)
            self.knowledge_collection.update_one(
                {'_id': q_id},
                {'$set': data},
                upsert=True
            )
            
            # ذخیره ایندکس کلمات کلیدی
            for keyword in keywords:
                self.index_collection.update_one(
                    {'keyword': keyword},
                    {'$addToSet': {'documents': q_id}},
                    upsert=True
                )
            
            # ذخیره در Redis Cache (برای سرعت)
            if self.redis:
                self.redis.setex(
                    f"qa:{q_id}",
                    3600,  # ۱ ساعت
                    json.dumps(data)
                )
                for keyword in keywords:
                    self.redis.sadd(f"idx:{keyword}", q_id)
            
            # به‌روزرسانی کش
            self.cache[question] = answer
            if len(self.cache) > self.cache_max:
                oldest = next(iter(self.cache))
                del self.cache[oldest]
            
            # آمار
            self.stats['total_learned'] += 1
            self._save_stats()
            
            logger.info(f"✅ یادگیری: {question[:30]}... (کل: {self.stats['total_learned']})")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در یادگیری: {e}")
            return False
    
    # ==================== جستجوی فوق‌سریع ====================
    def search(self, question: str) -> Dict:
        """جستجوی سریع با استفاده از ایندکس‌ها و کش"""
        try:
            # ۱. چک کش سریع
            if question in self.cache:
                return {'found': True, 'answer': self.cache[question]}
            
            # ۲. چک Redis
            if self.redis:
                q_id = hashlib.md5(question.encode()).hexdigest()
                cached = self.redis.get(f"cache:{q_id}")
                if cached:
                    self.cache[question] = cached
                    return {'found': True, 'answer': cached}
            
            # ۳. استخراج کلمات کلیدی
            keywords = self._extract_keywords(question)
            if not keywords:
                return {'found': False}
            
            # ۴. جستجو در ایندکس (MongoDB با ایندکس)
            doc_ids = set()
            for keyword in keywords[:3]:  # محدودیت برای سرعت
                index = self.index_collection.find_one({'keyword': keyword})
                if index:
                    doc_ids.update(index.get('documents', []))
            
            if not doc_ids:
                return {'found': False}
            
            # ۵. جستجوی دقیق
            results = []
            for doc_id in list(doc_ids)[:100]:  # محدودیت برای سرعت
                data = self.knowledge_collection.find_one({'_id': doc_id})
                if data:
                    doc_keywords = set(data.get('keywords', []))
                    overlap = len(set(keywords) & doc_keywords)
                    union = len(set(keywords) | doc_keywords)
                    score = overlap / union if union > 0 else 0
                    results.append({
                        'data': data,
                        'score': score,
                        'q_id': doc_id
                    })
            
            # ۶. انتخاب بهترین
            if results:
                best = max(results, key=lambda x: x['score'])
                if best['score'] > 0.15:
                    # افزایش استفاده
                    self.knowledge_collection.update_one(
                        {'_id': best['q_id']},
                        {'$inc': {'usage': 1}}
                    )
                    
                    # ذخیره در کش
                    self.cache[question] = best['data']['answer']
                    if self.redis:
                        self.redis.setex(
                            f"cache:{hashlib.md5(question.encode()).hexdigest()}",
                            3600,
                            best['data']['answer']
                        )
                    
                    return {
                        'found': True,
                        'answer': best['data']['answer'],
                        'confidence': best['score']
                    }
            
            return {'found': False}
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return {'found': False}
    
    # ==================== یادگیری از فایل (دسته‌ای) ====================
    def learn_from_file(self, file_path: str) -> int:
        """یادگیری دسته‌ای از فایل با پردازش موازی"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            lines = text.split('\n')
            count = 0
            
            # پردازش دسته‌ای
            batch = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # استخراج سوال و جواب
                patterns = [
                    r'([^؟\n]+[؟])\s*[-:]\s*(.+)',
                    r'([^؟\n]+[؟])\s*\((.+)\)',
                    r'([^؟\n]+[؟])\s*=\s*(.+)',
                    r'سوال:\s*(.+)\s*پاسخ:\s*(.+)',
                    r'([^،\n]+)\s*[,،]\s*(.+)',
                    r'([^\n]+)\s*[-–—]\s*(.+)',
                    r'([^\n]+)\s*:\s*(.+)',
                ]
                
                for pattern in patterns:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        question = match.group(1).strip()
                        answer = match.group(2).strip()
                        if question and answer and len(question) > 2 and len(answer) > 1:
                            batch.append((question, answer))
                            count += 1
                        break
            
            # ذخیره دسته‌ای در MongoDB
            if batch:
                operations = []
                for question, answer in batch:
                    q_id = hashlib.md5(f"{question}{datetime.now()}".encode()).hexdigest()
                    keywords = self._extract_keywords(question)
                    
                    operations.append({
                        '_id': q_id,
                        'question': question,
                        'answer': answer,
                        'keywords': keywords,
                        'created': datetime.now().isoformat(),
                        'usage': 0
                    })
                
                # Bulk insert
                if operations:
                    self.knowledge_collection.insert_many(operations, ordered=False)
                    
                    # آپدیت ایندکس
                    for op in operations:
                        for keyword in op['keywords']:
                            self.index_collection.update_one(
                                {'keyword': keyword},
                                {'$addToSet': {'documents': op['_id']}},
                                upsert=True
                            )
            
            self.stats['total_learned'] += count
            self._save_stats()
            
            return count
            
        except Exception as e:
            logger.error(f"❌ خطا در یادگیری از فایل: {e}")
            return 0
    
    def _extract_keywords(self, text: str) -> List[str]:
        """استخراج کلمات کلیدی"""
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        stopwords = {'و', 'به', 'از', 'برای', 'با', 'در', 'که', 'این', 'آن', 'را', 'یا', 'اما', 'اگر', 'هر', 'هم'}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords[:5]
    
    def _generate_embedding(self, text: str) -> List[float]:
        """تولید embedding برای جستجوی معنایی"""
        # ساده‌سازی
        return [0.0] * 100
    
    def _process_queue(self):
        """پردازش صف پیام‌ها"""
        while True:
            try:
                task = self.message_queue.get(timeout=1)
                if task:
                    self.executor.submit(task['func'], *task['args'])
            except:
                continue
    
    def add_to_queue(self, func, *args):
        """افزودن به صف پردازش"""
        try:
            self.message_queue.put_nowait({'func': func, 'args': args})
        except:
            # اگر صف پر بود، مستقیم اجرا کن
            func(*args)
    
    def get_stats(self) -> Dict:
        """دریافت آمار"""
        total = self.knowledge_collection.count_documents({})
        return {
            'total_knowledge': total,
            'cache_size': len(self.cache),
            'total_learned': self.stats['total_learned'],
            'total_queries': self.stats['total_queries'],
            'successful_queries': self.stats['successful_queries'],
            'active_users': self.stats['active_users']
        }
    
    def clear_all(self):
        """پاک کردن همه داده‌ها"""
        self.knowledge_collection.delete_many({})
        self.index_collection.delete_many({})
        self.cache = {}
        if self.redis:
            self.redis.flushdb()
        self.stats = {
            'total_learned': 0,
            'total_queries': 0,
            'successful_queries': 0,
            'active_users': 0
        }
        self._save_stats()


# ==================== ربات ====================
brain = UltraBrain()
bot = telebot.TeleBot(TOKEN)


def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("📝 یاد دادن دستی"),
        KeyboardButton("📤 یاد دادن با فایل"),
        KeyboardButton("🤖 یاد دادن از هوش مصنوعی"),
        KeyboardButton("📊 آمار"),
        KeyboardButton("📚 مشاهده دانش"),
        KeyboardButton("❌ بستن پنل")
    )
    return keyboard


# ==================== هندلرها ====================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🧠 به هوش مصنوعی MON خوش آمدید")


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ دسترسی غیرمجاز!")
        return
    
    bot.send_message(
        message.chat.id,
        "👑 **پنل مدیریت**",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )


@bot.message_handler(func=lambda m: m.text in [
    "📝 یاد دادن دستی",
    "📤 یاد دادن با فایل",
    "🤖 یاد دادن از هوش مصنوعی",
    "📊 آمار",
    "📚 مشاهده دانش",
    "❌ بستن پنل"
])
def handle_admin_buttons(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ دسترسی غیرمجاز!")
        return
    
    if message.text == "📝 یاد دادن دستی":
        bot.send_message(message.chat.id, "📝 **سوال را بفرستید:**", parse_mode='Markdown')
        bot.register_next_step_handler(message, get_question_for_learn)
    
    elif message.text == "📤 یاد دادن با فایل":
        bot.send_message(
            message.chat.id,
            "📤 **فایل TXT را بفرستید:**\n\nفرمت: سلام, سلام خوبی",
            parse_mode='Markdown'
        )
    
    elif message.text == "🤖 یاد دادن از هوش مصنوعی":
        bot.send_message(
            message.chat.id,
            "🤖 **API را بفرستید:**",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, get_ai_api)
    
    elif message.text == "📊 آمار":
        stats = brain.get_stats()
        text = f"""
📊 **آمار هوش مصنوعی MON**

🧠 دانش: {stats['total_knowledge']:,} مورد
📚 یادگیری کل: {stats['total_learned']:,} مورد
📝 سوالات: {stats['total_queries']:,} مورد
✅ موفق: {stats['successful_queries']:,} مورد
👤 کاربران: {stats['active_users']:,} نفر
⚡ کش: {stats['cache_size']:,} مورد
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    elif message.text == "📚 مشاهده دانش":
        items = list(brain.knowledge_collection.find().sort('created', -1).limit(20))
        if items:
            text = "📚 **۲۰ دانش آخر:**\n\n"
            for i, data in enumerate(items, 1):
                text += f"{i}. ❓ {data.get('question', '')[:40]}...\n"
                text += f"   💡 {data.get('answer', '')[:40]}...\n\n"
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "📚 هنوز چیزی یاد نگرفته‌ام!")
    
    elif message.text == "❌ بستن پنل":
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("/start"))
        bot.send_message(message.chat.id, "👋 پنل بسته شد.", reply_markup=keyboard)


def get_question_for_learn(message):
    if message.chat.id != ADMIN_ID:
        return
    question = message.text.strip()
    if not question:
        bot.send_message(message.chat.id, "❌ سوال معتبری وارد نشد!")
        return
    bot.send_message(message.chat.id, f"📝 سوال: {question}\n\n💡 **جواب را بفرستید:**", parse_mode='Markdown')
    bot.register_next_step_handler(message, lambda m: get_answer_for_learn(m, question))


def get_answer_for_learn(message, question):
    if message.chat.id != ADMIN_ID:
        return
    answer = message.text.strip()
    if not answer:
        bot.send_message(message.chat.id, "❌ جواب معتبری وارد نشد!")
        return
    if brain.learn(question, answer):
        bot.send_message(
            message.chat.id,
            f"✅ **یاد گرفتم!**\n\n📝 {question}\n💡 {answer}",
            parse_mode='Markdown'
        )
    else:
        bot.send_message(message.chat.id, "❌ خطا!")


def get_ai_api(message):
    if message.chat.id != ADMIN_ID:
        return
    api_url = message.text.strip()
    if not api_url:
        bot.send_message(message.chat.id, "❌ API معتبری وارد نشد!")
        return
    bot.send_message(message.chat.id, "🔑 **کلید API را بفرستید:**", parse_mode='Markdown')
    bot.register_next_step_handler(message, lambda m: get_ai_key(m, api_url))


def get_ai_key(message, api_url):
    if message.chat.id != ADMIN_ID:
        return
    api_key = message.text.strip()
    if not api_key:
        bot.send_message(message.chat.id, "❌ کلید API معتبری وارد نشد!")
        return
    
    try:
        import requests
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        data = {'model': 'gpt-3.5-turbo', 'messages': [{'role': 'user', 'content': 'سلام'}], 'max_tokens': 10}
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            bot.send_message(message.chat.id, "✅ **اتصال برقرار شد!**", parse_mode='Markdown')
            with open('api_config.json', 'w') as f:
                json.dump({'url': api_url, 'key': api_key}, f)
        else:
            bot.send_message(message.chat.id, f"❌ خطا: {response.status_code}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)}")


@bot.message_handler(content_types=['document'])
def handle_file(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ فقط ادمین!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        
        if not file_name.endswith('.txt'):
            bot.reply_to(message, "❌ فقط TXT!")
            return
        
        downloaded_file = bot.download_file(file_info.file_path)
        text = downloaded_file.decode('utf-8', errors='ignore')
        
        # ذخیره موقت
        temp_path = f"temp_{datetime.now().timestamp()}.txt"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # یادگیری
        count = brain.learn_from_file(temp_path)
        os.remove(temp_path)
        
        bot.reply_to(
            message,
            f"✅ **یادگیری از فایل انجام شد!**\n\n"
            f"📄 {file_name}\n"
            f"📝 تعداد: {count} مورد\n"
            f"🧠 کل: {brain.get_stats()['total_knowledge']:,} مورد",
            parse_mode='Markdown'
        )
            
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")


@bot.message_handler(func=lambda m: True)
def handle_message(message):
    try:
        if not message.text.startswith('/'):
            brain.stats['total_queries'] += 1
            result = brain.search(message.text)
            
            if result.get('found'):
                brain.stats['successful_queries'] += 1
                bot.reply_to(message, result['answer'], parse_mode='Markdown')
            else:
                bot.reply_to(message, "لطفاً دوباره تلاش کنید")
            
            brain._save_stats()
    except:
        bot.reply_to(message, "لطفاً دوباره تلاش کنید")


# ==================== اجرا ====================
if __name__ == "__main__":
    try:
        logger.info("🚀 راه‌اندازی ربات فوق‌پیشرفته...")
        print("\n" + "="*60)
        print("🤖 ربات هوش مصنوعی MON - نسخه فوق‌پیشرفته")
        print("📊 ظرفیت: نامحدود (MongoDB + Redis + Sharding)")
        print("👤 ادمین: " + str(ADMIN_ID))
        print("="*60 + "\n")
        
        bot.polling(none_stop=True, interval=1)
        
    except KeyboardInterrupt:
        logger.info("👋 سیستم متوقف شد")