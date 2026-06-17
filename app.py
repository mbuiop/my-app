"""
🤖 هوش مصنوعی MON - پنل مدیریت داخل ربات
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

# ==================== کتابخانه‌ها ====================
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import redis
from pymongo import MongoClient

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

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

# ==================== توکن و آیدی ادمین ====================
TOKEN = "YOUR_BOT_TOKEN_HERE"  # توکن خود را وارد کنید
ADMIN_ID = 327855654  # آیدی شما

# ==================== کلاس مغز ====================
class SimpleBrain:
    """مغز ساده و کارآمد"""
    
    def __init__(self):
        self.knowledge = {}
        self.keywords = defaultdict(set)
        self.cache = {}
        
        # اتصال به دیتابیس‌ها
        self.redis = None
        self.mongo = None
        self.collection = None
        
        try:
            self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
            logger.info("✅ Redis متصل شد")
        except:
            logger.warning("⚠️ Redis در دسترس نیست")
            
        try:
            self.mongo = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=3000)
            self.db = self.mongo['mon_ai']
            self.collection = self.db['knowledge']
            logger.info("✅ MongoDB متصل شد")
        except:
            logger.warning("⚠️ MongoDB در دسترس نیست")
        
        # بارگذاری داده‌ها
        self._load_data()
        
        logger.info("🧠 مغز راه‌اندازی شد")
    
    def _load_data(self):
        """بارگذاری داده‌ها از فایل"""
        try:
            if os.path.exists('data.json'):
                with open('data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.knowledge = data.get('knowledge', {})
                    self.keywords = defaultdict(set, data.get('keywords', {}))
                    logger.info(f"✅ بارگذاری {len(self.knowledge)} دانش")
        except Exception as e:
            logger.error(f"❌ خطا در بارگذاری: {e}")
    
    def _save_data(self):
        """ذخیره داده‌ها در فایل"""
        try:
            data = {
                'knowledge': self.knowledge,
                'keywords': {k: list(v) for k, v in self.keywords.items()}
            }
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("💾 داده‌ها ذخیره شدند")
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره: {e}")
    
    def learn(self, question: str, answer: str) -> bool:
        """یادگیری سوال و جواب"""
        try:
            q_id = hashlib.md5(f"{question}{datetime.now()}".encode()).hexdigest()
            keywords = self._extract_keywords(question)
            
            data = {
                'question': question,
                'answer': answer,
                'keywords': keywords,
                'created': datetime.now().isoformat(),
                'usage': 0
            }
            
            self.knowledge[q_id] = data
            
            for kw in keywords:
                self.keywords[kw].add(q_id)
            
            self.cache[question] = answer
            
            if self.collection:
                try:
                    self.collection.update_one({'_id': q_id}, {'$set': data}, upsert=True)
                except:
                    pass
            
            if self.redis:
                try:
                    self.redis.hset(f"qa:{q_id}", mapping=data)
                    for kw in keywords:
                        self.redis.sadd(f"index:{kw}", q_id)
                except:
                    pass
            
            self._save_data()
            logger.info(f"✅ یادگیری: {question[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در یادگیری: {e}")
            return False
    
    def search(self, question: str) -> Dict:
        """جستجوی پاسخ"""
        try:
            if question in self.cache:
                return {'found': True, 'answer': self.cache[question], 'source': 'cache'}
            
            q_keywords = self._extract_keywords(question)
            if not q_keywords:
                return {'found': False}
            
            results = []
            for kw in q_keywords:
                for q_id in self.keywords.get(kw, []):
                    data = self.knowledge.get(q_id)
                    if data:
                        doc_keywords = set(data.get('keywords', []))
                        overlap = len(set(q_keywords) & doc_keywords)
                        union = len(set(q_keywords) | doc_keywords)
                        score = overlap / union if union > 0 else 0
                        results.append({'data': data, 'score': score, 'q_id': q_id})
            
            if results:
                best = max(results, key=lambda x: x['score'])
                if best['score'] > 0.2:
                    if best['q_id'] in self.knowledge:
                        self.knowledge[best['q_id']]['usage'] += 1
                    self.cache[question] = best['data']['answer']
                    return {'found': True, 'answer': best['data']['answer'], 'confidence': best['score']}
            
            return {'found': False, 'suggestion': self._suggest_answer(question)}
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return {'found': False}
    
    def _extract_keywords(self, text: str) -> List[str]:
        """استخراج کلمات کلیدی"""
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        stopwords = {'و', 'به', 'از', 'برای', 'با', 'در', 'که', 'این', 'آن', 'را', 'یا', 'اما', 'اگر', 'هر', 'هم'}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return keywords[:5]
    
    def _suggest_answer(self, question: str) -> str:
        """پاسخ پیشنهادی"""
        return f"""🤔 هنوز جواب این سوال را یاد نگرفته‌ام!

سوال: {question}

📝 با دستور زیر به من یاد دهید:
`/learn {question} | پاسخ`

من هر روز چیزهای جدیدی یاد می‌گیرم! 📚"""
    
    def learn_from_text(self, text: str) -> int:
        """یادگیری از متن (استخراج سوال و جواب)"""
        count = 0
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            patterns = [
                r'([^؟\n]+[؟])\s*[-:]\s*(.+)',
                r'([^؟\n]+[؟])\s*\((.+)\)',
                r'([^؟\n]+[؟])\s*=\s*(.+)',
                r'سوال:\s*(.+)\s*پاسخ:\s*(.+)',
                r'Q:\s*(.+)\s*A:\s*(.+)',
                r'([^؟\n]+[؟])\s*→\s*(.+)',
                r'([^؟\n]+[؟])\s*⇒\s*(.+)',
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    question = match.group(1).strip()
                    answer = match.group(2).strip()
                    if question and answer and len(question) > 3 and len(answer) > 2:
                        self.learn(question, answer)
                        count += 1
                    break
        
        return count
    
    def get_stats(self) -> Dict:
        """گرفتن آمار"""
        return {
            'total_knowledge': len(self.knowledge),
            'cache_size': len(self.cache),
            'keywords_count': len(self.keywords)
        }
    
    def get_all_knowledge(self, limit: int = 20) -> List[Dict]:
        """گرفتن لیست دانش"""
        items = list(self.knowledge.values())
        items.reverse()
        return items[:limit]
    
    def clear_all(self):
        """پاک کردن همه دانش"""
        self.knowledge = {}
        self.keywords = defaultdict(set)
        self.cache = {}
        if self.collection:
            self.collection.delete_many({})
        if self.redis:
            self.redis.flushdb()
        self._save_data()


# ==================== ربات ====================
brain = SimpleBrain()
bot = telebot.TeleBot(TOKEN)

# ==================== کیبوردهای مدیریت ====================

def get_admin_keyboard():
    """کیبورد اصلی مدیریت"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📝 یاد دادن", callback_data="admin_learn"),
        InlineKeyboardButton("📤 یادگیری از فایل", callback_data="admin_file"),
        InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        InlineKeyboardButton("📚 مشاهده دانش", callback_data="admin_knowledge"),
        InlineKeyboardButton("🔍 جستجو در دانش", callback_data="admin_search"),
        InlineKeyboardButton("🗑️ پاک کردن همه", callback_data="admin_clear"),
        InlineKeyboardButton("📤 خروجی گرفتن", callback_data="admin_export"),
        InlineKeyboardButton("📥 وارد کردن", callback_data="admin_import"),
        InlineKeyboardButton("❌ بستن پنل", callback_data="admin_close")
    )
    return keyboard


# ==================== هندلرهای ربات ====================

@bot.message_handler(commands=['start'])
def start(message):
    """پیام خوش‌آمدگویی"""
    welcome = """
🧠 **به هوش مصنوعی MON خوش آمدید!**

من یک هوش مصنوعی هستم که **هر روز یاد می‌گیرم**!

✨ **چطور استفاده کنم؟**
• هر سوالی دارید، بپرسید
• من پاسخ می‌دهم یا یاد می‌گیرم
• هرچه بیشتر بپرسید، هوشمندتر می‌شوم

📌 **نکته:** اگر پاسخ را نمی‌دانم، با `/learn` به من یاد دهید!
"""
    bot.send_message(message.chat.id, welcome, parse_mode='Markdown')


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    """پنل مدیریت (فقط ادمین)"""
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ دسترسی غیرمجاز!")
        return
    
    bot.send_message(
        message.chat.id,
        "👑 **پنل مدیریت هوش مصنوعی MON**\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['learn'])
def learn_command(message):
    """یادگیری دستی از کاربر"""
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ فقط ادمین می‌تواند به من یاد دهد!")
        return
    
    try:
        text = message.text.replace('/learn', '').strip()
        if '|' not in text:
            bot.reply_to(
                message,
                "❌ **فرمت صحیح:**\n`/learn سوال | پاسخ`\n\n📌 **مثال:**\n`/learn سلام | سلام علیک`",
                parse_mode='Markdown'
            )
            return
        
        question, answer = text.split('|', 1)
        question = question.strip()
        answer = answer.strip()
        
        if not question or not answer:
            bot.reply_to(message, "❌ سوال و پاسخ را کامل وارد کنید!")
            return
        
        if brain.learn(question, answer):
            bot.reply_to(
                message,
                f"✅ **یاد گرفتم!**\n\n📝 سوال: {question}\n💡 پاسخ: {answer}",
                parse_mode='Markdown'
            )
        else:
            bot.reply_to(message, "❌ خطا در یادگیری!")
            
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback(call):
    """مدیریت دکمه‌های پنل ادمین"""
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    # ========== یاد دادن ==========
    if call.data == "admin_learn":
        bot.send_message(
            call.message.chat.id,
            "📝 **یاد دادن به من**\n\n"
            "از دستور زیر استفاده کنید:\n"
            "`/learn سوال | پاسخ`\n\n"
            "📌 **مثال:**\n"
            "`/learn پایتون چیست؟ | پایتون یک زبان برنامه‌نویسی است`\n\n"
            "💡 می‌توانید چندین سوال را یکجا یاد دهید.",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    # ========== یادگیری از فایل ==========
    elif call.data == "admin_file":
        bot.send_message(
            call.message.chat.id,
            "📤 **یادگیری از فایل TXT**\n\n"
            "یک فایل TXT حاوی سوال و جواب آپلود کنید.\n\n"
            "📌 **فرمت فایل:**\n"
            "هر خط یک سوال و جواب:\n"
            "`سوال؟ - پاسخ`\n"
            "`سوال؟ = پاسخ`\n"
            "`سوال: ... پاسخ: ...`\n\n"
            "📎 فایل را ارسال کنید.",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    # ========== آمار ==========
    elif call.data == "admin_stats":
        stats = brain.get_stats()
        text = f"""
📊 **آمار هوش مصنوعی MON**

🧠 دانش: {stats['total_knowledge']} مورد
🔑 کلمات کلیدی: {stats['keywords_count']} کلمه
⚡ کش: {stats['cache_size']} مورد

💪 هر روز قوی‌تر می‌شوم!
"""
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    # ========== مشاهده دانش ==========
    elif call.data == "admin_knowledge":
        items = brain.get_all_knowledge(20)
        if items:
            text = "📚 **دانش ذخیره شده (۲۰ مورد آخر):**\n\n"
            for i, data in enumerate(items, 1):
                text += f"{i}. ❓ {data['question'][:40]}...\n"
                text += f"   💡 {data['answer'][:40]}...\n"
                text += f"   📊 استفاده: {data.get('usage', 0)} بار\n\n"
            
            if len(text) > 4000:
                text = text[:4000] + "\n\n... ادامه دارد"
            
            bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
        else:
            bot.send_message(call.message.chat.id, "📚 هنوز چیزی یاد نگرفته‌ام!")
        bot.answer_callback_query(call.id)
    
    # ========== جستجو در دانش ==========
    elif call.data == "admin_search":
        bot.send_message(
            call.message.chat.id,
            "🔍 **جستجو در دانش**\n\n"
            "کلمه کلیدی مورد نظر را وارد کنید:",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        # حالت جستجو فعال می‌شود
    
    # ========== پاک کردن ==========
    elif call.data == "admin_clear":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("✅ بله، پاک کن", callback_data="admin_clear_confirm"),
            InlineKeyboardButton("❌ انصراف", callback_data="admin_cancel")
        )
        bot.edit_message_text(
            "⚠️ **هشدار!**\nآیا مطمئن هستید که می‌خواهید **همه دانش** را پاک کنید؟\n\nاین عمل غیرقابل بازگشت است!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_clear_confirm":
        brain.clear_all()
        bot.edit_message_text(
            "✅ **همه دانش پاک شد!**\n\nمن دوباره از صفر شروع می‌کنم.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_cancel":
        bot.edit_message_text(
            "❌ عملیات لغو شد.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_admin_keyboard(),
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    # ========== خروجی گرفتن ==========
    elif call.data == "admin_export":
        try:
            data = {
                'knowledge': brain.knowledge,
                'keywords': {k: list(v) for k, v in brain.keywords.items()},
                'export_date': datetime.now().isoformat(),
                'total': len(brain.knowledge)
            }
            
            # ذخیره موقت
            with open('export.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # ارسال فایل
            with open('export.json', 'rb') as f:
                bot.send_document(
                    call.message.chat.id,
                    f,
                    caption=f"📤 **خروجی دانش**\n\nتعداد: {len(brain.knowledge)} مورد\nتاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode='Markdown'
                )
            
            os.remove('export.json')
            
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")
        
        bot.answer_callback_query(call.id)
    
    # ========== وارد کردن ==========
    elif call.data == "admin_import":
        bot.send_message(
            call.message.chat.id,
            "📥 **وارد کردن دانش**\n\n"
            "فایل JSON خروجی را ارسال کنید.",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    # ========== بستن پنل ==========
    elif call.data == "admin_close":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            "👋 پنل مدیریت بسته شد.",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)


# ========== دریافت فایل ==========
@bot.message_handler(content_types=['document'])
def handle_file(message):
    """پردازش فایل آپلودی"""
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ فقط ادمین می‌تواند فایل آپلود کند!")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        
        # ====== فایل TXT ======
        if file_name.endswith('.txt'):
            downloaded_file = bot.download_file(file_info.file_path)
            text = downloaded_file.decode('utf-8', errors='ignore')
            
            count = brain.learn_from_text(text)
            
            bot.reply_to(
                message,
                f"✅ **یادگیری از فایل انجام شد!**\n\n"
                f"📄 فایل: {file_name}\n"
                f"📝 تعداد یادگیری: {count} مورد\n"
                f"🧠 کل دانش: {len(brain.knowledge)} مورد",
                parse_mode='Markdown'
            )
        
        # ====== فایل JSON (وارد کردن) ======
        elif file_name.endswith('.json'):
            downloaded_file = bot.download_file(file_info.file_path)
            data = json.loads(downloaded_file.decode('utf-8'))
            
            if 'knowledge' in data:
                count = 0
                for q_id, item in data['knowledge'].items():
                    if 'question' in item and 'answer' in item:
                        brain.knowledge[q_id] = item
                        for kw in item.get('keywords', []):
                            brain.keywords[kw].add(q_id)
                        count += 1
                
                brain._save_data()
                
                bot.reply_to(
                    message,
                    f"✅ **وارد کردن دانش انجام شد!**\n\n"
                    f"📥 تعداد وارد شده: {count} مورد\n"
                    f"🧠 کل دانش: {len(brain.knowledge)} مورد",
                    parse_mode='Markdown'
                )
            else:
                bot.reply_to(message, "❌ فرمت فایل JSON نامعتبر است!")
        
        else:
            bot.reply_to(message, "❌ لطفاً فقط فایل TXT یا JSON آپلود کنید!")
            
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")


# ========== جستجوی دستی ==========
@bot.message_handler(commands=['search'])
def search_command(message):
    """جستجو در دانش"""
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ فقط ادمین!")
        return
    
    query = message.text.replace('/search', '').strip()
    if not query:
        bot.reply_to(message, "🔍 کلمه مورد نظر را وارد کنید:\n`/search کلمه`", parse_mode='Markdown')
        return
    
    # جستجو
    results = []
    for q_id, data in brain.knowledge.items():
        if query in data['question'] or query in data['answer']:
            results.append(data)
    
    if results:
        text = f"🔍 **نتایج جستجو برای:** `{query}`\n\n"
        for i, data in enumerate(results[:10], 1):
            text += f"{i}. ❓ {data['question'][:50]}...\n"
            text += f"   💡 {data['answer'][:50]}...\n\n"
        
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, f"🔍 چیزی برای `{query}` پیدا نشد!", parse_mode='Markdown')


# ========== پیام‌های عادی ==========
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    """پردازش پیام‌های عادی کاربران"""
    try:
        user_text = message.text
        
        # اگر دستور نبود
        if not user_text.startswith('/'):
            result = brain.search(user_text)
            
            if result.get('found'):
                bot.reply_to(message, result['answer'], parse_mode='Markdown')
            else:
                bot.reply_to(
                    message,
                    result.get('suggestion', "🤔 هنوز جواب را نمی‌دانم!"),
                    parse_mode='Markdown'
                )
                
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")


# ==================== اجرا ====================
if __name__ == "__main__":
    try:
        logger.info("🚀 راه‌اندازی ربات...")
        logger.info(f"👤 آیدی ادمین: {ADMIN_ID}")
        
        print("\n" + "="*50)
        print("🤖 ربات هوش مصنوعی MON راه‌اندازی شد!")
        print(f"👤 ادمین: {ADMIN_ID}")
        print("📌 دستورات:")
        print("  /start - شروع")
        print("  /admin - پنل مدیریت")
        print("  /learn سوال | پاسخ - یاد دادن")
        print("  /search کلمه - جستجو")
        print("="*50 + "\n")
        
        bot.polling(none_stop=True, interval=1)
        
    except KeyboardInterrupt:
        logger.info("👋 سیستم متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")