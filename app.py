"""
🤖 هوش مصنوعی MON - نسخه نهایی با پنل مدیریت و ظرفیت بی‌نهایت
"""

import os
import json
import hashlib
import re
import threading
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import logging
from concurrent.futures import ThreadPoolExecutor
import queue

# ==================== کتابخانه‌ها ====================
import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

import redis
from pymongo import MongoClient, ASCENDING, DESCENDING

# ==================== تنظیمات ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = "8691128478:AAE7eZ0vo5kkFcvrerHt3vjw-mvJ3CqxpWE"
ADMIN_ID = 327855654

# ==================== مغز با ظرفیت بی‌نهایت ====================
class UltraBrain:
    def __init__(self):
        # دیتابیس‌ها
        try:
            self.mongo = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=5000)
            self.db = self.mongo['ultra_ai']
            self.knowledge_collection = self.db['knowledge']
            self.index_collection = self.db['indexes']
            self.stats_collection = self.db['stats']
            
            # ایندکس‌ها
            self.knowledge_collection.create_index([('question', 'text')])
            self.knowledge_collection.create_index('keywords')
            self.knowledge_collection.create_index([('usage', DESCENDING)])
            logger.info("✅ MongoDB متصل شد")
        except Exception as e:
            logger.warning(f"⚠️ MongoDB در دسترس نیست: {e}")
            self.mongo = None
        
        try:
            self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
            logger.info("✅ Redis متصل شد")
        except:
            self.redis = None
        
        # کش
        self.cache = {}
        self.cache_max = 10000
        
        # آمار
        self.stats = {'total_learned': 0, 'total_queries': 0, 'successful_queries': 0}
        self._load_stats()
        
        logger.info("🧠 مغز با ظرفیت بی‌نهایت راه‌اندازی شد")
    
    def _load_stats(self):
        try:
            if self.mongo:
                stats = self.stats_collection.find_one({'_id': 'global'})
                if stats:
                    self.stats = stats.get('data', self.stats)
        except:
            pass
    
    def _save_stats(self):
        try:
            if self.mongo:
                self.stats_collection.update_one(
                    {'_id': 'global'},
                    {'$set': {'data': self.stats}},
                    upsert=True
                )
        except:
            pass
    
    def learn(self, question: str, answer: str) -> bool:
        try:
            q_id = hashlib.md5(f"{question}{datetime.now()}".encode()).hexdigest()
            keywords = self._extract_keywords(question)
            
            data = {
                '_id': q_id,
                'question': question,
                'answer': answer,
                'keywords': keywords,
                'created': datetime.now().isoformat(),
                'usage': 0
            }
            
            # ذخیره در MongoDB
            if self.mongo:
                self.knowledge_collection.update_one({'_id': q_id}, {'$set': data}, upsert=True)
                
                # ایندکس کلمات کلیدی
                for keyword in keywords:
                    self.index_collection.update_one(
                        {'keyword': keyword},
                        {'$addToSet': {'documents': q_id}},
                        upsert=True
                    )
            
            # کش
            self.cache[question] = answer
            if len(self.cache) > self.cache_max:
                oldest = next(iter(self.cache))
                del self.cache[oldest]
            
            # Redis
            if self.redis:
                self.redis.setex(f"qa:{q_id}", 3600, json.dumps(data))
                for keyword in keywords:
                    self.redis.sadd(f"idx:{keyword}", q_id)
            
            self.stats['total_learned'] += 1
            self._save_stats()
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در یادگیری: {e}")
            return False
    
    def search(self, question: str) -> Dict:
        try:
            # کش
            if question in self.cache:
                return {'found': True, 'answer': self.cache[question]}
            
            # Redis
            if self.redis:
                cached = self.redis.get(f"cache:{hashlib.md5(question.encode()).hexdigest()}")
                if cached:
                    self.cache[question] = cached
                    return {'found': True, 'answer': cached}
            
            keywords = self._extract_keywords(question)
            if not keywords:
                return {'found': False}
            
            # جستجو در MongoDB
            if self.mongo:
                doc_ids = set()
                for keyword in keywords[:3]:
                    index = self.index_collection.find_one({'keyword': keyword})
                    if index:
                        doc_ids.update(index.get('documents', []))
                
                if not doc_ids:
                    return {'found': False}
                
                results = []
                for doc_id in list(doc_ids)[:100]:
                    data = self.knowledge_collection.find_one({'_id': doc_id})
                    if data:
                        doc_keywords = set(data.get('keywords', []))
                        overlap = len(set(keywords) & doc_keywords)
                        union = len(set(keywords) | doc_keywords)
                        score = overlap / union if union > 0 else 0
                        results.append({'data': data, 'score': score, 'q_id': doc_id})
                
                if results:
                    best = max(results, key=lambda x: x['score'])
                    if best['score'] > 0.15:
                        self.knowledge_collection.update_one(
                            {'_id': best['q_id']},
                            {'$inc': {'usage': 1}}
                        )
                        self.cache[question] = best['data']['answer']
                        if self.redis:
                            self.redis.setex(
                                f"cache:{hashlib.md5(question.encode()).hexdigest()}",
                                3600,
                                best['data']['answer']
                            )
                        return {'found': True, 'answer': best['data']['answer']}
            
            return {'found': False}
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return {'found': False}
    
    def _extract_keywords(self, text: str) -> List[str]:
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        stopwords = {'و', 'به', 'از', 'برای', 'با', 'در', 'که', 'این', 'آن', 'را', 'یا', 'اما', 'اگر', 'هر', 'هم'}
        return [w for w in words if w not in stopwords and len(w) > 2][:5]
    
    def learn_from_text(self, text: str) -> int:
        count = 0
        lines = text.split('\n')
        
        patterns = [
            r'([^؟\n]+[؟])\s*[-:]\s*(.+)',
            r'([^؟\n]+[؟])\s*\((.+)\)',
            r'([^؟\n]+[؟])\s*=\s*(.+)',
            r'سوال:\s*(.+)\s*پاسخ:\s*(.+)',
            r'([^،\n]+)\s*[,،]\s*(.+)',
            r'([^\n]+)\s*[-–—]\s*(.+)',
            r'([^\n]+)\s*:\s*(.+)',
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    question = match.group(1).strip()
                    answer = match.group(2).strip()
                    if question and answer and len(question) > 2 and len(answer) > 1:
                        self.learn(question, answer)
                        count += 1
                    break
        
        return count
    
    def get_stats(self) -> Dict:
        total = self.knowledge_collection.count_documents({}) if self.mongo else len(self.cache)
        return {
            'total_knowledge': total,
            'cache_size': len(self.cache),
            'total_learned': self.stats['total_learned'],
            'total_queries': self.stats['total_queries'],
            'successful_queries': self.stats['successful_queries']
        }
    
    def get_all_knowledge(self, limit: int = 20) -> List[Dict]:
        if self.mongo:
            items = list(self.knowledge_collection.find().sort('created', -1).limit(limit))
            return items
        return list(self.cache.items())[:limit]
    
    def clear_all(self):
        if self.mongo:
            self.knowledge_collection.delete_many({})
            self.index_collection.delete_many({})
        self.cache = {}
        if self.redis:
            self.redis.flushdb()
        self.stats = {'total_learned': 0, 'total_queries': 0, 'successful_queries': 0}
        self._save_stats()


# ==================== ربات ====================
brain = UltraBrain()
bot = telebot.TeleBot(TOKEN)

# ==================== دکمه‌های پنل مدیریت ====================

def get_admin_keyboard():
    """کیبورد اصلی مدیریت"""
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("📝 یاد دادن دستی"),
        KeyboardButton("📤 یاد دادن با فایل"),
        KeyboardButton("🤖 یاد دادن از هوش مصنوعی"),
        KeyboardButton("📊 آمار"),
        KeyboardButton("📚 مشاهده دانش"),
        KeyboardButton("🗑️ پاک کردن همه"),
        KeyboardButton("📤 خروجی گرفتن"),
        KeyboardButton("📥 وارد کردن"),
        KeyboardButton("❌ بستن پنل")
    )
    return keyboard


# ==================== هندلرهای ربات ====================

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
        "👑 **پنل مدیریت هوش مصنوعی MON**\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )


# ========== مدیریت دکمه‌ها ==========
@bot.message_handler(func=lambda m: m.text in [
    "📝 یاد دادن دستی",
    "📤 یاد دادن با فایل",
    "🤖 یاد دادن از هوش مصنوعی",
    "📊 آمار",
    "📚 مشاهده دانش",
    "🗑️ پاک کردن همه",
    "📤 خروجی گرفتن",
    "📥 وارد کردن",
    "❌ بستن پنل"
])
def handle_admin_buttons(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ دسترسی غیرمجاز!")
        return
    
    # ========== یاد دادن دستی ==========
    if message.text == "📝 یاد دادن دستی":
        bot.send_message(
            message.chat.id,
            "📝 **سوال را بفرستید:**",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, get_question_for_learn)
    
    # ========== یاد دادن با فایل ==========
    elif message.text == "📤 یاد دادن با فایل":
        bot.send_message(
            message.chat.id,
            "📤 **فایل TXT را بفرستید:**\n\n"
            "📌 فرمت فایل:\n"
            "سلام, سلام خوبی\n"
            "چطوری؟ - خوبم\n"
            "سوال: چی هست؟ پاسخ: این هست",
            parse_mode='Markdown'
        )
    
    # ========== یاد دادن از هوش مصنوعی ==========
    elif message.text == "🤖 یاد دادن از هوش مصنوعی":
        bot.send_message(
            message.chat.id,
            "🤖 **API هوش مصنوعی را بفرستید:**\n\n"
            "مثال: `https://api.openai.com/v1/chat/completions`",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, get_ai_api)
    
    # ========== آمار ==========
    elif message.text == "📊 آمار":
        stats = brain.get_stats()
        text = f"""
📊 **آمار هوش مصنوعی MON**

🧠 دانش: {stats['total_knowledge']:,} مورد
📚 یادگیری کل: {stats['total_learned']:,} مورد
📝 سوالات: {stats['total_queries']:,} مورد
✅ موفق: {stats['successful_queries']:,} مورد
⚡ کش: {stats['cache_size']:,} مورد
"""
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    
    # ========== مشاهده دانش ==========
    elif message.text == "📚 مشاهده دانش":
        items = brain.get_all_knowledge(20)
        if items:
            text = "📚 **۲۰ دانش آخر:**\n\n"
            for i, data in enumerate(items, 1):
                if isinstance(data, dict):
                    question = data.get('question', '')
                    answer = data.get('answer', '')
                else:
                    question, answer = data[0], data[1]
                text += f"{i}. ❓ {question[:40]}...\n"
                text += f"   💡 {answer[:40]}...\n\n"
            
            if len(text) > 4000:
                text = text[:4000] + "\n\n... ادامه دارد"
            
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "📚 هنوز چیزی یاد نگرفته‌ام!")
    
    # ========== پاک کردن همه ==========
    elif message.text == "🗑️ پاک کردن همه":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("✅ بله، پاک کن", callback_data="clear_confirm"),
            InlineKeyboardButton("❌ انصراف", callback_data="clear_cancel")
        )
        bot.send_message(
            message.chat.id,
            "⚠️ **هشدار!**\nآیا مطمئن هستید که می‌خواهید **همه دانش** را پاک کنید؟",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    # ========== خروجی گرفتن ==========
    elif message.text == "📤 خروجی گرفتن":
        try:
            items = brain.get_all_knowledge(1000)
            data = {
                'export_date': datetime.now().isoformat(),
                'total': len(items),
                'knowledge': []
            }
            
            for item in items:
                if isinstance(item, dict):
                    data['knowledge'].append({
                        'question': item.get('question', ''),
                        'answer': item.get('answer', '')
                    })
                else:
                    data['knowledge'].append({
                        'question': item[0],
                        'answer': item[1]
                    })
            
            with open('export.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            with open('export.json', 'rb') as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"📤 **خروجی دانش**\n\nتعداد: {len(data['knowledge'])} مورد",
                    parse_mode='Markdown'
                )
            
            os.remove('export.json')
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطا: {str(e)}")
    
    # ========== وارد کردن ==========
    elif message.text == "📥 وارد کردن":
        bot.send_message(
            message.chat.id,
            "📥 **فایل JSON را بفرستید:**",
            parse_mode='Markdown'
        )
    
    # ========== بستن پنل ==========
    elif message.text == "❌ بستن پنل":
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("/start"))
        bot.send_message(
            message.chat.id,
            "👋 پنل مدیریت بسته شد.",
            reply_markup=keyboard
        )


# ========== کالبک‌ها ==========
@bot.callback_query_handler(func=lambda call: call.data in ['clear_confirm', 'clear_cancel'])
def clear_callback(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    if call.data == 'clear_confirm':
        brain.clear_all()
        bot.edit_message_text(
            "✅ **همه دانش پاک شد!**",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
    else:
        bot.edit_message_text(
            "❌ عملیات لغو شد.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
    
    bot.answer_callback_query(call.id)


# ========== دریافت فایل ==========
@bot.message_handler(content_types=['document'])
def handle_file(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ فقط ادمین!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        
        downloaded_file = bot.download_file(file_info.file_path)
        text = downloaded_file.decode('utf-8', errors='ignore')
        
        # ====== فایل TXT ======
        if file_name.endswith('.txt'):
            count = brain.learn_from_text(text)
            bot.reply_to(
                message,
                f"✅ **یادگیری از فایل انجام شد!**\n\n"
                f"📄 {file_name}\n"
                f"📝 تعداد: {count} مورد\n"
                f"🧠 کل: {brain.get_stats()['total_knowledge']:,} مورد",
                parse_mode='Markdown'
            )
        
        # ====== فایل JSON ======
        elif file_name.endswith('.json'):
            data = json.loads(text)
            if 'knowledge' in data:
                count = 0
                for item in data['knowledge']:
                    question = item.get('question', '')
                    answer = item.get('answer', '')
                    if question and answer:
                        brain.learn(question, answer)
                        count += 1
                
                bot.reply_to(
                    message,
                    f"✅ **وارد کردن دانش انجام شد!**\n\n"
                    f"📥 تعداد وارد شده: {count} مورد",
                    parse_mode='Markdown'
                )
            else:
                bot.reply_to(message, "❌ فرمت JSON نامعتبر است!")
        
        else:
            bot.reply_to(message, "❌ فقط فایل TXT یا JSON!")
            
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")


# ========== مراحل یادگیری دستی ==========
def get_question_for_learn(message):
    if message.chat.id != ADMIN_ID:
        return
    
    question = message.text.strip()
    if not question:
        bot.send_message(message.chat.id, "❌ سوال معتبری وارد نشد!")
        return
    
    bot.send_message(
        message.chat.id,
        f"📝 سوال: {question}\n\n💡 **جواب را بفرستید:**",
        parse_mode='Markdown'
    )
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
        bot.send_message(message.chat.id, "❌ خطا در یادگیری!")


# ========== API هوش مصنوعی ==========
def get_ai_api(message):
    if message.chat.id != ADMIN_ID:
        return
    
    api_url = message.text.strip()
    if not api_url:
        bot.send_message(message.chat.id, "❌ API معتبری وارد نشد!")
        return
    
    bot.send_message(
        message.chat.id,
        "🔑 **کلید API را بفرستید:**",
        parse_mode='Markdown'
    )
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
            bot.send_message(
                message.chat.id,
                "✅ **اتصال به هوش مصنوعی برقرار شد!**\n\n"
                "حالا می‌توانم از این API استفاده کنم.",
                parse_mode='Markdown'
            )
            with open('api_config.json', 'w') as f:
                json.dump({'url': api_url, 'key': api_key}, f)
        else:
            bot.send_message(
                message.chat.id,
                f"❌ خطا: {response.status_code}\n{response.text[:200]}",
                parse_mode='Markdown'
            )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)}")


# ========== پیام‌های عادی ==========
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
    except Exception as e:
        bot.reply_to(message, "لطفاً دوباره تلاش کنید")


# ==================== اجرا ====================
if __name__ == "__main__":
    try:
        logger.info("🚀 راه‌اندازی ربات...")
        
        print("\n" + "="*60)
        print("🤖 ربات هوش مصنوعی MON - نسخه نهایی")
        print("📊 ظرفیت: بی‌نهایت (MongoDB)")
        print("👑 پنل مدیریت: داخل ربات")
        print("👤 ادمین: " + str(ADMIN_ID))
        print("="*60)
        print("\n📌 دستورات:")
        print("  /start - شروع")
        print("  /admin - پنل مدیریت")
        print("="*60 + "\n")
        
        bot.polling(none_stop=True, interval=1)
        
    except KeyboardInterrupt:
        logger.info("👋 سیستم متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")
