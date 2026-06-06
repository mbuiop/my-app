import telebot
from openai import OpenAI
import sqlite3
import os
import json
from datetime import datetime
import whisper  # برای تبدیل صدا به متن

# ========== تنظیمات (این قسمت را خودت پر کن) ==========
TELEGRAM_BOT_TOKEN = "توکن_ربات_تلگرام_خود_را_اینجا_بگذارید"
DEEPSEEK_API_KEY = "کلید_جدید_و_امن_DeepSeek_خود_را_اینجا_بگذارید"
ADMIN_ID = 123456789  # آیدی عددی تلگرام خودت را اینجا بگذار (با @userinfobot بگیر)
# =====================================================

# اتصال به DeepSeek
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# اتصال به ربات تلگرام
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# بارگذاری مدل Whisper برای تبدیل صدا به متن (یک بار در شروع)
try:
    whisper_model = whisper.load_model("base")  # مدل "base" سبک و دقیق است
    whisper_available = True
except:
    whisper_available = False
    print("⚠️ Whisper نصب نیست. تبدیل صدا فعال نمی‌شود. برای نصب: pip install openai-whisper")

# ========== راه‌اندازی پایگاه داده SQLite ==========
def init_database():
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    
    # جدول برای دانش دستی (یادگیری‌های شما)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learned_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_text TEXT NOT NULL,     -- کلمه یا جمله‌ای که کاربر می‌گوید
            response_text TEXT NOT NULL,    -- پاسخی که باید بدهد
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول برای حافظه مکالمه هر کاربر
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_memory (
            user_id INTEGER PRIMARY KEY,
            history TEXT DEFAULT '[]',      -- تاریخچه مکالمه به صورت JSON
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول برای کاربران مسدود شده
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول برای آمار
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            stat_name TEXT PRIMARY KEY,
            stat_value INTEGER DEFAULT 0
        )
    ''')
    
    # مقداردهی اولیه آمار
    cursor.execute('INSERT OR IGNORE INTO stats (stat_name, stat_value) VALUES ("total_messages", 0)')
    cursor.execute('INSERT OR IGNORE INTO stats (stat_name, stat_value) VALUES ("total_users", 0)')
    
    conn.commit()
    conn.close()

init_database()

# ========== توابع کمکی ==========

def is_admin(user_id):
    """بررسی آیا کاربر ادمین است"""
    return user_id == ADMIN_ID

def is_banned(user_id):
    """بررسی آیا کاربر مسدود شده"""
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM banned_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def update_stats(stat_name):
    """به روز رسانی آمار"""
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE stats SET stat_value = stat_value + 1 WHERE stat_name = ?', (stat_name,))
    conn.commit()
    conn.close()

def get_answer_from_learned(question):
    """جستجو در دانش یادگرفته شده برای پاسخ مناسب"""
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    # جستجوی کلمه یا جمله در trigger_text
    cursor.execute('SELECT response_text FROM learned_knowledge WHERE trigger_text LIKE ?', (f'%{question}%',))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def learn_new_question(trigger, response):
    """به ربات یک سوال و جواب جدید یاد بده"""
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO learned_knowledge (trigger_text, response_text) VALUES (?, ?)', 
                   (trigger.lower(), response))
    conn.commit()
    conn.close()

def get_conversation_history(user_id):
    """گرفتن تاریخچه مکالمه کاربر"""
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    cursor.execute('SELECT history FROM conversation_memory WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        return json.loads(result[0])
    else:
        return []

def save_conversation_history(user_id, history):
    """ذخیره تاریخچه مکالمه کاربر"""
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO conversation_memory (user_id, history, last_active)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, json.dumps(history)))
    conn.commit()
    conn.close()

def ask_deepseek_with_context(question, history):
    """پرسش از DeepSeek با در نظر گرفتن تاریخچه مکالمه"""
    # ساخت لیست پیام‌ها برای ارسال به API
    messages = []
    
    # اضافه کردن تاریخچه (حداکثر 10 پیام آخر)
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # اضافه کردن سوال جدید کاربر
    messages.append({"role": "user", "content": question})
    
    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ خطا در ارتباط با DeepSeek: {str(e)}"

# ========== تبدیل صدا به متن با Whisper ==========
def transcribe_voice(voice_file_path):
    if not whisper_available:
        return None
    try:
        result = whisper_model.transcribe(voice_file_path, language="fa")  # تشخیص فارسی
        return result["text"]
    except Exception as e:
        print(f"خطا در تبدیل صدا: {e}")
        return None

# ========== دستورات مدیریتی (فقط برای ادمین) ==========
@bot.message_handler(commands=['stats'])
def show_stats(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین می‌تواند از این دستور استفاده کند.")
        return
    
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT stat_value FROM stats WHERE stat_name = "total_messages"')
    total_msgs = cursor.fetchone()[0]
    
    cursor.execute('SELECT stat_value FROM stats WHERE stat_name = "total_users"')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM learned_knowledge')
    total_learned = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
📊 **آمار ربات**
━━━━━━━━━━━━━
👥 **کل کاربران:** {total_users}
💬 **کل پیام‌ها:** {total_msgs}
📚 **دانش یادگرفته شده:** {total_learned} مورد
━━━━━━━━━━━━━
    """
    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['learn'])
def learn_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین می‌تواند یاد بگیرد.")
        return
    
    # فرمت: /learn سوال | جواب
    try:
        text = message.text.replace('/learn', '').strip()
        parts = text.split('|')
        if len(parts) != 2:
            bot.reply_to(message, "❌ فرمت صحیح:\n`/learn سلام | سلام! خوش آمدی دوست من`", parse_mode='Markdown')
            return
        
        trigger = parts[0].strip()
        response = parts[1].strip()
        
        learn_new_question(trigger, response)
        bot.reply_to(message, f"✅ یاد گرفتم!\n\n**سوال:** {trigger}\n**پاسخ:** {response}", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ خطا در پردازش. فرمت صحیح:\n`/learn سوال | جواب`")

@bot.message_handler(commands=['list'])
def list_learned(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین.")
        return
    
    conn = sqlite3.connect('robot_brain.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, trigger_text, response_text FROM learned_knowledge LIMIT 20')
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        bot.reply_to(message, "📭 هنوز چیزی یاد نگرفته‌ام.")
        return
    
    text = "📚 **دانش یادگرفته شده:**\n━━━━━━━━━━━━━\n"
    for item in results:
        text += f"🆔 {item[0]} | {item[1]}\n    ➜ {item[2][:50]}...\n\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['delete'])
def delete_learned(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین.")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ `/delete 5` - عدد آیدی را وارد کن")
            return
        
        knowledge_id = int(parts[1])
        conn = sqlite3.connect('robot_brain.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM learned_knowledge WHERE id = ?', (knowledge_id,))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ آیتم {knowledge_id} حذف شد.")
    except:
        bot.reply_to(message, "❌ خطا. آیدی عددی معتبر وارد کن.")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ `/ban 123456789 دلیل`")
        return
    
    try:
        user_id = int(parts[1])
        reason = ' '.join(parts[2:]) if len(parts) > 2 else 'ندارد'
        
        conn = sqlite3.connect('robot_brain.db')
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO banned_users (user_id, reason) VALUES (?, ?)', (user_id, reason))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ کاربر {user_id} مسدود شد.\nدلیل: {reason}")
    except:
        bot.reply_to(message, "❌ خطا")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ `/unban 123456789`")
        return
    
    try:
        user_id = int(parts[1])
        conn = sqlite3.connect('robot_brain.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ کاربر {user_id} از مسدودیت خارج شد.")
    except:
        bot.reply_to(message, "❌ خطا")

# ========== پیام خوشامدگویی به کاربر جدید ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "⛔ شما مسدود شده‌اید.")
        return
    
    update_stats('total_users')
    bot.reply_to(message, """
🌟 **به ربات هوشمند خوش آمدی!** 🌟

من یک ربات با حافظه هستم. می‌توانم:
✅ مکالمه را به خاطر بسپارم
✅ به سوالاتت پاسخ دهم
✅ صدای تو را بشنوم و بفهمم

فقط سوال یا پیامت را بفرست.
""", parse_mode='Markdown')

# ========== پردازش اصلی پیام‌ها ==========
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    
    # بررسی مسدودیت
    if is_banned(user_id):
        bot.reply_to(message, "⛔ شما از این ربات مسدود شده‌اید.")
        return
    
    update_stats('total_messages')
    user_question = message.text.strip()
    
    if not user_question:
        return
    
    # 1. اول در دانش یادگرفته شده جستجو کن
    learned_answer = get_answer_from_learned(user_question.lower())
    
    if learned_answer:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.reply_to(message, learned_answer)
        return
    
    # 2. اگر پیدا نشد، از DeepSeek با حافظه بپرس
    history = get_conversation_history(user_id)
    
    bot.send_chat_action(message.chat.id, 'typing')
    answer = ask_deepseek_with_context(user_question, history)
    
    # ذخیره در تاریخچه
    history.append({"role": "user", "content": user_question})
    history.append({"role": "assistant", "content": answer})
    save_conversation_history(user_id, history)
    
    bot.reply_to(message, answer)

# ========== پردازش پیام‌های صوتی ==========
@bot.message_handler(content_types=['voice'])
def handle_voice_message(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(message, "⛔ شما مسدود شده‌اید.")
        return
    
    if not whisper_available:
        bot.reply_to(message, "🎤 قابلیت تبدیل صدا فعلاً فعال نیست. لطفاً متن بفرستید.")
        return
    
    bot.reply_to(message, "🎧 در حال پردازش صدای شما... لطفاً چند لحظه صبر کنید.")
    
    try:
        # دانلود فایل صوتی
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # ذخیره فایل
        temp_file = f"voice_{user_id}.ogg"
        with open(temp_file, "wb") as f:
            f.write(downloaded_file)
        
        # تبدیل به متن
        transcribed_text = transcribe_voice(temp_file)
        
        # پاک کردن فایل موقت
        os.remove(temp_file)
        
        if not transcribed_text:
            bot.reply_to(message, "❌ نتواستم صدایت را تشخیص دهم. دوباره تلاش کن.")
            return
        
        # نشان دادن متن تشخیص داده شده
        bot.reply_to(message, f"📝 **متن تشخیص داده شده:**\n_{transcribed_text}_\n\n🤔 در حال فکر کردن...", 
                     parse_mode='Markdown')
        
        # جستجو در دانش یا پرسش از DeepSeek
        learned_answer = get_answer_from_learned(transcribed_text.lower())
        
        if learned_answer:
            bot.reply_to(message, learned_answer)
        else:
            history = get_conversation_history(user_id)
            answer = ask_deepseek_with_context(transcribed_text, history)
            
            history.append({"role": "user", "content": transcribed_text})
            history.append({"role": "assistant", "content": answer})
            save_conversation_history(user_id, history)
            
            bot.reply_to(message, answer)
            
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در پردازش صدا: {str(e)}")

# ========== شروع ربات ==========
if __name__ == "__main__":
    print("🚀 ربات قدرتمند روشن شد...")
    print(f"👑 ادمین: {ADMIN_ID}")
    print(f"🎤 تبدیل صدا: {'فعال' if whisper_available else 'غیرفعال'}")
    print("━━━━━━━━━━━━━━━━━━━━━━━")
    bot.infinity_polling()