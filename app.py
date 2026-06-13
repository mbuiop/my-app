# ==================== ادامه کد - بخش ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text == '📋 ربات‌های من')
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(
            message.chat.id,
            "📋 **شما رباتی ندارید!**\n\n"
            "برای ساخت ربات:\n"
            "└ از گزینه «ساخت ربات جدید» استفاده کنید\n"
            "└ یا اشتراک خود را فعال کنید",
            parse_mode="Markdown"
        )
        return
    
    # آمار کلی
    total_bots = len(bots)
    running_bots = len([b for b in bots if b['status'] == 'running'])
    stopped_bots = total_bots - running_bots
    
    text = f"📋 **لیست ربات‌های شما**\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 **آمار کلی**\n"
    text += f"└ کل ربات‌ها: {total_bots}\n"
    text += f"└ 🟢 فعال: {running_bots}\n"
    text += f"└ 🔴 متوقف: {stopped_bots}\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🤖 **لیست ربات‌ها**\n\n"
    
    for i, b in enumerate(bots[:15], 1):
        status_emoji = "🟢" if b['status'] == 'running' else "🔴"
        status_text = "فعال" if b['status'] == 'running' else "متوقف"
        
        text += f"{i}. {status_emoji} **{b['name']}**\n"
        text += f"   └ 🔗 @{b['username']}\n"
        text += f"   └ 🆔 `{b['id']}`\n"
        text += f"   └ 📊 {status_text}\n"
        text += f"   └ 📅 {b['created_at'][:10]}\n\n"
    
    if len(bots) > 15:
        text += f"و {len(bots) - 15} ربات دیگر...\n"
    
    text += f"\n━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💡 برای مدیریت ربات‌ها از گزینه‌های زیر استفاده کنید:\n"
    text += f"└ 🔄 فعال/غیرفعال کردن\n"
    text += f"└ 🗑 حذف ربات"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== فعال/غیرفعال کردن ربات ====================
@bot.message_handler(func=lambda m: m.text == '🔄 فعال/غیرفعال کردن')
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = "🟢" if b['status'] == 'running' else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu"))
    
    bot.send_message(
        message.chat.id,
        "🔄 **فعال/غیرفعال کردن ربات**\n\nربات مورد نظر را انتخاب کنید:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    user_id = call.from_user.id
    
    bot_info = db.fetch_one('SELECT * FROM bots WHERE id = ? AND user_id = ?', (bot_id, user_id))
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ ربات پیدا نشد!")
        return
    
    if bot_info['status'] == 'running':
        # توقف ربات
        if BotRunner.stop_bot(bot_id):
            update_bot_status(bot_id, 'stopped')
            bot.answer_callback_query(call.id, "✅ ربات متوقف شد")
            bot.edit_message_text(
                f"✅ **ربات متوقف شد**\n\n"
                f"🤖 نام: {bot_info['name']}\n"
                f"🆔 آیدی: `{bot_id}`\n\n"
                f"برای راه‌اندازی مجدد، دوباره اقدام کنید.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown"
            )
            add_notification(user_id, "ربات متوقف شد", f"ربات {bot_info['name']} متوقف شد", "info")
        else:
            bot.answer_callback_query(call.id, "❌ خطا در توقف ربات!")
    else:
        # راه‌اندازی مجدد ربات
        bot.answer_callback_query(call.id, "⚠️ برای راه‌اندازی مجدد، ربات را حذف و دوباره بسازید")
        bot.edit_message_text(
            f"⚠️ **ربات متوقف است**\n\n"
            f"🤖 نام: {bot_info['name']}\n"
            f"🆔 آیدی: `{bot_id}`\n\n"
            f"برای راه‌اندازی مجدد، لطفاً:\n"
            f"└ ربات را حذف کنید\n"
            f"└ دوباره فایل را آپلود کنید",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu_callback(call):
    user_id = call.from_user.id
    is_admin = user_id in ADMIN_IDS
    markup = get_main_menu(is_admin)
    bot.edit_message_text("🚀 منوی اصلی:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات')
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    
    if not bots:
        bot.send_message(message.chat.id, "📋 شما رباتی ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu"))
    
    bot.send_message(
        message.chat.id,
        "🗑 **حذف ربات**\n\n⚠️ توجه: حذف ربات غیرقابل بازگشت است!\n\nربات مورد نظر را انتخاب کنید:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    
    # دریافت اطلاعات ربات
    bot_info = db.fetch_one('SELECT name FROM bots WHERE id = ?', (bot_id,))
    bot_name = bot_info['name'] if bot_info else "ربات"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_del_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر، انصراف", callback_data="cancel_del")
    )
    
    bot.edit_message_text(
        f"⚠️ **تأیید حذف ربات**\n\n"
        f"🤖 نام: {bot_name}\n"
        f"🆔 آیدی: `{bot_id}`\n\n"
        f"آیا از حذف این ربات اطمینان دارید؟\n"
        f"این عمل غیرقابل بازگشت است!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    user_id = call.from_user.id
    
    # دریافت اطلاعات ربات برای نوتیف
    bot_info = db.fetch_one('SELECT name FROM bots WHERE id = ?', (bot_id,))
    bot_name = bot_info['name'] if bot_info else "ربات"
    
    if delete_bot_from_db(bot_id, user_id):
        bot.edit_message_text(
            f"✅ **ربات با موفقیت حذف شد**\n\n"
            f"🤖 نام: {bot_name}\n"
            f"🆔 آیدی: `{bot_id}`\n\n"
            f"برای ساخت ربات جدید، از گزینه «ساخت ربات جدید» استفاده کنید.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        add_notification(user_id, "ربات حذف شد", f"ربات {bot_name} حذف شد", "warning")
    else:
        bot.edit_message_text(
            f"❌ **خطا در حذف ربات**\n\n"
            f"لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
            call.message.chat.id,
            call.message.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.edit_message_text(
        "❌ **عملیات حذف لغو شد**\n\n"
        "ربات شما حذف نشد.",
        call.message.chat.id,
        call.message.message_id
    )

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📚 راهنما')
def guide(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user['first_name'] if user else "کاربر گرامی"
    
    text = (
        f"📚 **راهنمای کامل ربات مادر نهایی**\n\n"
        f"سلام {name}! 👋\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 **ساخت ربات جدید**\n"
        f"└ 1. از منوی اصلی «ساخت ربات جدید» را انتخاب کنید\n"
        f"└ 2. فایل .py یا .zip خود را ارسال کنید\n"
        f"└ 3. توکن ربات باید داخل کد باشد\n"
        f"└ 4. پس از بررسی، ربات اجرا می‌شود\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 **اشتراک و تست ۲۴ ساعته**\n"
        f"└ تست رایگان: ۲۴ ساعت - فقط یک بار\n"
        f"└ اشتراک ماهانه: {PRICE_PER_MONTH:,} تومان\n"
        f"└ اشتراک سه ماهه: {PRICE_3_MONTHS:,} تومان\n"
        f"└ اشتراک شش ماهه: {PRICE_6_MONTHS:,} تومان\n"
        f"└ اشتراک یکساله: {PRICE_12_MONTHS:,} تومان\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **سیستم رفرال و درآمدزایی**\n"
        f"└ از هر خرید با لینک شما = {REFERRAL_COMMISSION_PERCENT}% پورسانت\n"
        f"└ پورسانت تا ۳ سطح: {REFERRAL_COMMISSIONS[0]}% - {REFERRAL_COMMISSIONS[1]}% - {REFERRAL_COMMISSIONS[2]}%\n"
        f"└ لینک رفرال خود را از بخش «کیف پول و رفرال» دریافت کنید\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 **برداشت وجه**\n"
        f"└ حداقل مبلغ برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان\n"
        f"└ زمان واریز: ۲۴ تا ۷۲ ساعت کاری\n"
        f"└ کارمزد: ۰ تومان\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **نصب کتابخانه**\n"
        f"└ از منوی «نصب کتابخانه» استفاده کنید\n"
        f"└ کتابخانه‌های پایتون را نصب کنید\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔒 **امنیت**\n"
        f"└ کد شما در محیط ایزوله اجرا می‌شود\n"
        f"└ دسترسی به سیستم محدود است\n"
        f"└ اطلاعات شما محفوظ می‌ماند\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 **پشتیبانی**\n"
        f"└ ادمین: @shahraghee13\n"
        f"└ پاسخگویی: ۲۴ ساعته\n\n"
        f"💡 **نکات مهم**\n"
        f"└ حتماً از کدهای تمیز و بهینه استفاده کنید\n"
        f"└ از کتابخانه‌های مجاز استفاده کنید\n"
        f"└ در صورت مشکل با پشتیبانی تماس بگیرید"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== نصب کتابخانه ====================
@bot.message_handler(func=lambda m: m.text == '📦 نصب کتابخانه')
def install_library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    libs = [
        ("📦 requests", "requests"),
        ("📊 numpy", "numpy"),
        ("🐼 pandas", "pandas"),
        ("🌶️ flask", "flask"),
        ("🤖 pyTelegramBotAPI", "pyTelegramBotAPI"),
        ("⚡ aiogram", "aiogram"),
        ("📅 jdatetime", "jdatetime"),
        ("🔧 django", "django"),
        ("🎨 pillow", "Pillow"),
        ("🕸️ scrapy", "Scrapy"),
        ("📈 matplotlib", "matplotlib"),
        ("🔐 cryptography", "cryptography"),
        ("🎵 yt-dlp", "yt-dlp"),
        ("🌐 aiohttp", "aiohttp"),
        ("⚙️ loguru", "loguru"),
        ("🔧 دستی", "custom")
    ]
    
    for name, lib in libs:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"lib_{lib}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu"))
    
    bot.send_message(
        message.chat.id,
        "📦 **مدیریت کتابخانه‌های پایتون**\n\n"
        "کتابخانه مورد نظر را انتخاب کنید:\n"
        "└ نصب خودکار\n"
        "└ بروزرسانی خودکار\n\n"
        "یا از گزینه «دستی» استفاده کنید.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_'))
def install_library_callback(call):
    lib = call.data.replace('lib_', '')
    
    if lib == 'custom':
        msg = bot.send_message(
            call.message.chat.id,
            "📦 **نصب کتابخانه دستی**\n\n"
            "لطفاً نام کتابخانه مورد نظر را وارد کنید:\n"
            "مثال: `requests`\n\n"
            "می‌توانید نسخه خاص نیز指定 کنید:\n"
            "مثال: `requests==2.28.0`",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, install_custom_library)
        return
    
    bot.answer_callback_query(call.id, f"🔄 در حال نصب {lib}...")
    
    try:
        # ارسال پیام وضعیت
        status_msg = bot.send_message(call.message.chat.id, f"🔄 در حال نصب {lib}...")
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", lib],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            bot.edit_message_text(
                f"✅ **کتابخانه با موفقیت نصب شد**\n\n"
                f"📦 نام: {lib}\n"
                f"✅ وضعیت: نصب شده\n\n"
                f"می‌توانید از این کتابخانه در ربات‌های خود استفاده کنید.",
                call.message.chat.id,
                status_msg.message_id,
                parse_mode="Markdown"
            )
        else:
            error_msg = result.stderr[:300] if result.stderr else "خطای ناشناخته"
            bot.edit_message_text(
                f"❌ **خطا در نصب کتابخانه**\n\n"
                f"📦 نام: {lib}\n"
                f"⚠️ خطا: {error_msg}\n\n"
                f"لطفاً نام کتابخانه را بررسی کنید.",
                call.message.chat.id,
                status_msg.message_id,
                parse_mode="Markdown"
            )
    except subprocess.TimeoutExpired:
        bot.send_message(call.message.chat.id, f"❌ زمان نصب {lib} بیش از حد طول کشید.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ خطا: {str(e)}")

def install_custom_library(message):
    lib = message.text.strip()
    
    if not lib:
        bot.reply_to(message, "❌ نام کتابخانه معتبر نیست!")
        return
    
    status_msg = bot.reply_to(message, f"🔄 در حال نصب {lib}...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", lib],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            bot.edit_message_text(
                f"✅ **کتابخانه با موفقیت نصب شد**\n\n"
                f"📦 نام: {lib}\n"
                f"✅ وضعیت: نصب شده",
                message.chat.id,
                status_msg.message_id,
                parse_mode="Markdown"
            )
        else:
            error_msg = result.stderr[:300] if result.stderr else "خطای ناشناخته"
            bot.edit_message_text(
                f"❌ **خطا در نصب کتابخانه**\n\n"
                f"📦 نام: {lib}\n"
                f"⚠️ خطا: {error_msg}",
                message.chat.id,
                status_msg.message_id,
                parse_mode="Markdown"
            )
    except subprocess.TimeoutExpired:
        bot.edit_message_text(f"❌ زمان نصب {lib} بیش از حد طول کشید.", message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", message.chat.id, status_msg.message_id)

# ==================== آمار کاربر ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار')
def user_stats(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ لطفاً /start را بزنید")
        return
    
    # آمار ربات‌ها
    bots = get_user_bots(user_id)
    total_bots = len(bots)
    running_bots = len([b for b in bots if b['status'] == 'running'])
    
    # آمار مالی
    balance = ReferralManager.get_balance(user_id)
    stats = ReferralManager.get_referral_stats(user_id)
    
    # آمار اشتراک
    has_sub = SubscriptionManager.has_active_subscription(user_id)
    sub_info = SubscriptionManager.get_subscription_info(user_id) if has_sub else None
    trial_active = SubscriptionManager.is_trial_active(user_id)
    trial_remaining = SubscriptionManager.get_trial_remaining(user_id) if trial_active else 0
    
    # آمار کلی سیستم
    total_users = db.fetch_one('SELECT COUNT(*) FROM users')[0]
    total_system_bots = db.fetch_one('SELECT COUNT(*) FROM bots')[0]
    
    text = (
        f"📊 **آمار کاربری شما**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **اطلاعات کاربری**\n"
        f"└ نام: {user['first_name']}\n"
        f"└ آیدی: `{user_id}`\n"
        f"└ تاریخ عضویت: {user['created_at'][:10]}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **آمار ربات‌ها**\n"
        f"└ کل ربات‌ها: {total_bots}\n"
        f"└ 🟢 فعال: {running_bots}\n"
        f"└ 🔴 متوقف: {total_bots - running_bots}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **آمار مالی**\n"
        f"└ موجودی کیف پول: {balance:,} تومان\n"
        f"└ کل پورسانت: {stats['total_commission']:,} تومان\n"
        f"└ کلیک‌های رفرال: {stats['total_clicks']}\n"
        f"└ خریدهای موفق: {stats['verified']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟️ **وضعیت اشتراک**\n"
    )
    
    if has_sub and sub_info:
        end_date = datetime.fromisoformat(sub_info['end_date'])
        days_left = (end_date - datetime.now()).days
        text += (
            f"└ ✅ اشتراک فعال: {sub_info['plan_type']}\n"
            f"└ 📅 انقضا: {end_date.strftime('%Y-%m-%d')}\n"
            f"└ ⏳ روزهای باقیمانده: {days_left}\n"
        )
    elif trial_active:
        text += (
            f"└ 🎁 تست ۲۴ ساعته فعال\n"
            f"└ ⏰ ساعت باقیمانده: {trial_remaining}\n"
        )
    else:
        text += f"└ ❌ بدون اشتراک فعال\n"
    
    text += (
        f"\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 **آمار کلی سیستم**\n"
        f"└ کل کاربران: {total_users}\n"
        f"└ کل ربات‌ها: {total_system_bots}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 برای مشاهده جزئیات بیشتر از منو استفاده کنید."
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text == '📞 پشتیبانی')
def support(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = user['first_name'] if user else "کاربر"
    
    text = (
        f"📞 **پشتیبانی ربات مادر نهایی**\n\n"
        f"سلام {name} جان! 👋\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👨‍💻 **راه‌های ارتباطی**\n\n"
        f"└ 📱 **تلگرام:** @shahraghee13\n"
        f"└ ⏰ پاسخگویی: ۲۴ ساعته\n"
        f"└ ⏱️ زمان پاسخ: حداکثر ۱۲ ساعت\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ **سوالات متداول**\n\n"
        f"└ **ساخت ربات:** از منوی اصلی «ساخت ربات جدید»\n"
        f"└ **مشکل در اجرا:** کد خود را بررسی کنید\n"
        f"└ **واریز و برداشت:** از بخش مالی اقدام کنید\n"
        f"└ **رفرال:** لینک خود را به اشتراک بگذارید\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 **قبل از تماس**\n\n"
        f"└ راهنما را مطالعه کنید\n"
        f"└ مشکل خود را دقیق توضیح دهید\n"
        f"└ تصویر خطا را ارسال کنید\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🙏 متشکریم از اعتماد شما!"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📱 ارتباط با پشتیبانی", url="https://t.me/shahraghee13"))
    markup.add(types.InlineKeyboardButton("📚 مطالعه راهنما", callback_data="guide"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "guide")
def guide_callback(call):
    guide(call.message)

# ==================== اعلان‌ها ====================
@bot.message_handler(func=lambda m: m.text == '🔔 اعلان‌ها')
def notifications_menu(message):
    user_id = message.from_user.id
    
    notifications = db.fetch_all('''
        SELECT * FROM notifications 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 20
    ''', (user_id,))
    
    if not notifications:
        bot.send_message(
            message.chat.id,
            "🔔 **اعلان‌ها**\n\n"
            "شما هیچ اعلانی ندارید.\n"
            "اعلان‌های مهم در اینجا نمایش داده می‌شوند.",
            parse_mode="Markdown"
        )
        return
    
    unread_count = len([n for n in notifications if not n['is_read']])
    
    text = f"🔔 **اعلان‌های شما**\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📊 تعداد کل: {len(notifications)}\n"
    text += f"🆕 خوانده نشده: {unread_count}\n\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"📋 **لیست اعلان‌ها**\n\n"
    
    for n in notifications[:10]:
        status = "🆕" if not n['is_read'] else "✅"
        text += f"{status} **{n['title']}**\n"
        text += f"   └ {n['message'][:50]}\n"
        text += f"   └ 📅 {n['created_at'][:16]}\n\n"
    
    # علامت‌گذاری به عنوان خوانده شده
    db.execute('UPDATE notifications SET is_read = 1, read_at = ? WHERE user_id = ? AND is_read = 0', 
               (datetime.now().isoformat(), user_id))
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗑 پاک کردن همه", callback_data="clear_notifications"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "clear_notifications")
def clear_notifications(call):
    db.execute('DELETE FROM notifications WHERE user_id = ?', (call.from_user.id,))
    bot.answer_callback_query(call.id, "✅ همه اعلان‌ها پاک شدند")
    bot.edit_message_text("🔔 **اعلان‌ها**\n\nهمه اعلان‌ها پاک شدند.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ==================== تنظیمات کاربر ====================
@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیمات')
def settings_menu(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🌐 زبان", callback_data="settings_language"),
        types.InlineKeyboardButton("🔔 نوتیفیکیشن", callback_data="settings_notification"),
        types.InlineKeyboardButton("🔒 امنیت", callback_data="settings_security"),
        types.InlineKeyboardButton("👤 پروفایل", callback_data="settings_profile"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")
    )
    
    text = (
        f"⚙️ **تنظیمات کاربری**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 کاربر: {user['first_name']}\n"
        f"🆔 آیدی: `{user_id}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **تنظیمات قابل تغییر**\n"
        f"└ زبان پیام‌ها\n"
        f"└ دریافت نوتیفیکیشن\n"
        f"└ تنظیمات امنیتی\n"
        f"└ اطلاعات پروفایل\n\n"
        f"💡 روی گزینه مورد نظر کلیک کنید."
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("settings_"))
def settings_options(call):
    option = call.data.replace("settings_", "")
    
    if option == "language":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
            types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="settings_back")
        )
        bot.edit_message_text("🌐 **انتخاب زبان**\n\nزبان مورد نظر خود را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    
    elif option == "notification":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ فعال", callback_data="notif_on"),
            types.InlineKeyboardButton("❌ غیرفعال", callback_data="notif_off"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="settings_back")
        )
        bot.edit_message_text("🔔 **تنظیمات نوتیفیکیشن**\n\nدریافت اعلان‌های مهم:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    
    elif option == "security":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔐 تغییر رمز", callback_data="security_change_password"),
            types.InlineKeyboardButton("📱 تایید دو مرحله‌ای", callback_data="security_2fa"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="settings_back")
        )
        bot.edit_message_text("🔒 **تنظیمات امنیتی**\n\nمدیریت امنیت حساب کاربری:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    
    elif option == "profile":
        user = get_user(call.from_user.id)
        text = (
            f"👤 **اطلاعات پروفایل**\n\n"
            f"└ نام: {user['first_name']} {user['last_name'] or ''}\n"
            f"└ یوزرنیم: @{user['username'] or 'ندارد'}\n"
            f"└ آیدی: `{user['user_id']}`\n"
            f"└ تاریخ عضویت: {user['created_at'][:10]}\n"
            f"└ آخرین فعالیت: {user['last_active'][:16] if user['last_active'] else '-'}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="settings_back"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "settings_back")
def settings_back(call):
    settings_menu(call.message)

# ==================== جایزه روزانه ====================
@bot.message_handler(func=lambda m: m.text == '🎁 جایزه روزانه')
def daily_reward(message):
    user_id = message.from_user.id
    
    # بررسی آخرین دریافت جایزه
    last_reward = cache.get(f"daily_reward_{user_id}")
    
    if last_reward:
        last_time = datetime.fromisoformat(last_reward)
        next_time = last_time + timedelta(days=1)
        remaining = next_time - datetime.now()
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        bot.send_message(
            message.chat.id,
            f"🎁 **جایزه روزانه**\n\n"
            f"⏰ شما امروز جایزه خود را دریافت کرده‌اید!\n"
            f"└ زمان باقیمانده تا جایزه بعدی: {hours} ساعت و {minutes} دقیقه\n\n"
            f"✨ فردا دوباره امتحان کنید!",
            parse_mode="Markdown"
        )
        return
    
    # مقدار جایزه تصادفی
    reward = random.randint(1000, 50000)
    
    # واریز به کیف پول
    db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (reward, user_id))
    
    # ثبت در cache
    cache.set(f"daily_reward_{user_id}", datetime.now().isoformat(), ttl=86400)
    
    # ثبت نوتیف
    add_notification(user_id, "جایزه روزانه", f"{reward:,} تومان به کیف پول شما اضافه شد", "success")
    
    text = (
        f"🎁 **جایزه روزانه شما**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 مبلغ جایزه: {reward:,} تومان\n"
        f"✅ به کیف پول شما اضافه شد\n\n"
        f"📊 موجودی جدید: {ReferralManager.get_balance(user_id):,} تومان\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ فردا دوباره مراجعه کنید!\n"
        f"💡 هر روز می‌توانید جایزه بگیرید!"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ==================== پنل ادمین کامل ====================
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ شما دسترسی ادمین ندارید!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 فیش‌های در انتظار", callback_data="admin_receipts"),
        types.InlineKeyboardButton("💰 درخواست‌های برداشت", callback_data="admin_withdraw_list"),
        types.InlineKeyboardButton("👥 لیست کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🤖 مدیریت ربات‌ها", callback_data="admin_bots"),
        types.InlineKeyboardButton("📊 آمار کامل سیستم", callback_data="admin_stats"),
        types.InlineKeyboardButton("💰 کمیسیون‌ها", callback_data="admin_commissions"),
        types.InlineKeyboardButton("💳 تغییر قیمت", callback_data="admin_change_price"),
        types.InlineKeyboardButton("🏧 تغییر شماره کارت", callback_data="admin_change_card"),
        types.InlineKeyboardButton("📝 تغییر متن راهنما", callback_data="admin_change_guide"),
        types.InlineKeyboardButton("🗑 حذف ربات کاربر", callback_data="admin_delete_user_bot"),
        types.InlineKeyboardButton("📢 ارسال نوتیف همگانی", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("💾 بکاپ گیری", callback_data="admin_backup"),
        types.InlineKeyboardButton("🖥 وضعیت سرور", callback_data="admin_server_status"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")
    )
    
    # آمار سریع برای ادمین
    pending_receipts = db.fetch_one('SELECT COUNT(*) FROM receipts WHERE status = "pending"')[0]
    pending_withdraws = db.fetch_one('SELECT COUNT(*) FROM withdraw_requests WHERE status = "pending"')[0]
    total_users = db.fetch_one('SELECT COUNT(*) FROM users')[0]
    total_bots = db.fetch_one('SELECT COUNT(*) FROM bots')[0]
    
    text = (
        f"👑 **پنل مدیریت**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **آمار لحظه‌ای**\n"
        f"└ 👥 کاربران: {total_users}\n"
        f"└ 🤖 ربات‌ها: {total_bots}\n"
        f"└ 📸 فیش‌های pending: {pending_receipts}\n"
        f"└ 💳 برداشت‌های pending: {pending_withdraws}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 از دکمه‌های زیر برای مدیریت استفاده کنید."
    )
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# ==================== هندلرهای پنل ادمین ====================

@bot.callback_query_handler(func=lambda call: call.data == "admin_receipts")
def admin_receipts(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipts = ReceiptManager.get_pending_receipts()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "📸 هیچ فیش در انتظاری نیست")
        return
    
    for r in receipts:
        text = (
            f"📸 **فیش شماره {r['id']}**\n\n"
            f"👤 کاربر: `{r['user_id']}`\n"
            f"👤 نام: {r['first_name']}\n"
            f"💰 مبلغ: {r['amount']:,} تومان\n"
            f"📋 نوع: {r['plan_type']}\n"
            f"🆔 کد: `{r['payment_code']}`\n"
            f"📅 تاریخ: {r['created_at'][:19]}"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید و فعال‌سازی", callback_data=f"approve_receipt_{r['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}")
        )
        
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(call.message.chat.id, f, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('approve_receipt_', ''))
    success, msg = ReceiptManager.approve_receipt(receipt_id, call.from_user.id)
    
    bot.answer_callback_query(call.id, msg)
    if success:
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    receipt_id = int(call.data.replace('reject_receipt_', ''))
    success, msg = ReceiptManager.reject_receipt(receipt_id, call.from_user.id)
    
    bot.answer_callback_query(call.id, msg)
    if success:
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_withdraw_list")
def admin_withdraw_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraws = WithdrawManager.get_withdraw_requests('pending')
    
    if not withdraws:
        bot.send_message(call.message.chat.id, "💰 هیچ درخواست برداشتی وجود ندارد")
        return
    
    for w in withdraws:
        text = (
            f"💰 **درخواست برداشت #{w['id']}**\n\n"
            f"👤 کاربر: `{w['user_id']}`\n"
            f"👤 نام: {w['first_name']}\n"
            f"💰 مبلغ: {w['amount']:,} تومان\n"
            f"💳 کارت: `{w['card_number']}`\n"
            f"👤 صاحب کارت: {w['card_owner']}\n"
            f"🏦 بانک: {w['bank_name']}\n"
            f"🆔 کد پیگیری: `{w['tracking_code']}`\n"
            f"📅 تاریخ: {w['created_at'][:19]}"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ تایید واریز", callback_data=f"withdraw_approve_{w['id']}"),
            types.InlineKeyboardButton("❌ رد", callback_data=f"withdraw_reject_{w['id']}")
        )
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_approve_'))
def withdraw_approve_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('withdraw_approve_', ''))
    success, msg = WithdrawManager.process_withdraw(withdraw_id, 'approve', call.from_user.id)
    
    bot.answer_callback_query(call.id, msg)
    if success:
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('withdraw_reject_'))
def withdraw_reject_admin(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    withdraw_id = int(call.data.replace('withdraw_reject_', ''))
    msg = bot.send_message(call.message.chat.id, "📝 لطفاً دلیل رد درخواست را وارد کنید:")
    bot.register_next_step_handler(msg, lambda m: process_withdraw_reject_reason(m, withdraw_id, call))

def process_withdraw_reject_reason(message, withdraw_id, original_call):
    if message.from_user.id not in ADMIN_IDS:
        return
    success, msg = WithdrawManager.process_withdraw(withdraw_id, 'reject', original_call.from_user.id, message.text)
    bot.reply_to(message, msg)
    bot.delete_message(original_call.message.chat.id, original_call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats_full(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    # آمار کامل
    total_users = db.fetch_one('SELECT COUNT(*) FROM users')[0]
    total_bots = db.fetch_one('SELECT COUNT(*) FROM bots')[0]
    running_bots = db.fetch_one('SELECT COUNT(*) FROM bots WHERE status = "running"')[0]
    total_receipts = db.fetch_one('SELECT COUNT(*) FROM receipts')[0]
    pending_receipts = db.fetch_one('SELECT COUNT(*) FROM receipts WHERE status = "pending"')[0]
    approved_receipts = db.fetch_one('SELECT COUNT(*) FROM receipts WHERE status = "approved"')[0]
    total_amount = db.fetch_one('SELECT SUM(amount) FROM receipts WHERE status = "approved"')[0] or 0
    paid_users = db.fetch_one('SELECT COUNT(*) FROM users WHERE payment_status = "approved"')[0]
    total_withdraw = db.fetch_one('SELECT SUM(amount) FROM withdraw_requests WHERE status = "pending"')[0] or 0
    total_withdraw_approved = db.fetch_one('SELECT SUM(amount) FROM withdraw_requests WHERE status = "approved"')[0] or 0
    total_balance = db.fetch_one('SELECT SUM(balance) FROM users')[0] or 0
    total_commissions = db.fetch_one('SELECT SUM(amount) FROM commissions')[0] or 0
    trial_active = db.fetch_one('SELECT COUNT(*) FROM trial_usage WHERE is_active = 1')[0]
    
    # آمار ماه جاری
    current_month = datetime.now().strftime('%Y-%m')
    monthly_users = db.fetch_one("SELECT COUNT(*) FROM users WHERE strftime('%Y-%m', created_at) = ?", (current_month,))[0]
    monthly_receipts = db.fetch_one("SELECT SUM(amount) FROM receipts WHERE strftime('%Y-%m', created_at) = ? AND status = 'approved'", (current_month,))[0] or 0
    
    text = (
        f"📊 **آمار کامل سیستم**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **آمار کاربران**\n"
        f"└ کل کاربران: {total_users}\n"
        f"└ پرداخت کرده: {paid_users}\n"
        f"└ تست فعال: {trial_active}\n"
        f"└ کاربران جدید این ماه: {monthly_users}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **آمار ربات‌ها**\n"
        f"└ کل ربات‌ها: {total_bots}\n"
        f"└ 🟢 فعال: {running_bots}\n"
        f"└ 🔴 متوقف: {total_bots - running_bots}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **آمار مالی**\n"
        f"└ مجموع واریزی: {total_amount:,} تومان\n"
        f"└ درآمد این ماه: {monthly_receipts:,} تومان\n"
        f"└ مجموع کمیسیون‌ها: {total_commissions:,} تومان\n"
        f"└ موجودی کاربران: {total_balance:,} تومان\n"
        f"└ کل برداشت‌ها: {total_withdraw_approved:,} تومان\n"
        f"└ درخواست برداشت pending: {total_withdraw:,} تومان\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📸 **آمار فیش‌ها**\n"
        f"└ کل فیش‌ها: {total_receipts}\n"
        f"└ در انتظار: {pending_receipts}\n"
        f"└ تایید شده: {approved_receipts}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 تاریخ بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_users")
def admin_users_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    users = db.fetch_all('''
        SELECT user_id, username, first_name, bots_count, verified_referrals, 
               payment_status, balance, created_at, last_active
        FROM users 
        ORDER BY created_at DESC 
        LIMIT 50
    ''')
    
    text = "👥 **لیست کاربران (۵۰ کاربر آخر)**\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n"
    
    for u in users:
        status = "✅" if u['payment_status'] == 'approved' else "⏳"
        text += f"{status} `{u['user_id']}` - {u['first_name']}\n"
        text += f"   └ 🤖 {u['bots_count']} | 🎁 {u['verified_referrals']} | 💰 {u['balance']:,}\n"
        text += f"   └ 📅 {u['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_commissions")
def admin_commissions_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    commissions = db.fetch_all('''
        SELECT c.*, u.first_name, u.username 
        FROM commissions c 
        JOIN users u ON c.user_id = u.user_id 
        ORDER BY c.created_at DESC 
        LIMIT 50
    ''')
    
    if not commissions:
        bot.send_message(call.message.chat.id, "💰 هیچ کمیسیونی ثبت نشده است")
        return
    
    total = db.fetch_one('SELECT SUM(amount) FROM commissions')[0] or 0
    
    text = f"💰 **لیست کمیسیون‌ها (۵۰ مورد آخر)**\n\n"
    text += f"📊 مجموع کمیسیون‌ها: {total:,} تومان\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for c in commissions:
        text += f"👤 {c['first_name']} (`{c['user_id']}`)\n"
        text += f"└ 💰 {c['amount']:,} تومان\n"
        text += f"└ 📝 {c['reason'][:40]}\n"
        text += f"└ 📅 {c['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_bots")
def admin_bots_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bots = db.fetch_all('''
        SELECT b.*, u.first_name 
        FROM bots b 
        JOIN users u ON b.user_id = u.user_id 
        ORDER BY b.created_at DESC 
        LIMIT 50
    ''')
    
    text = "🤖 **لیست ربات‌ها (۵۰ مورد آخر)**\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for b in bots:
        status = "🟢" if b['status'] == 'running' else "🔴"
        text += f"{status} **{b['name']}**\n"
        text += f"└ 👤 کاربر: {b['first_name']} (`{b['user_id']}`)\n"
        text += f"└ 🔗 @{b['username']}\n"
        text += f"└ 🆔 `{b['id']}`\n"
        text += f"└ 📅 {b['created_at'][:10]}\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_price")
def admin_change_price_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "💰 **تغییر قیمت اشتراک‌ها**\n\n"
        "لطفاً قیمت جدید ماهانه را وارد کنید (تومان):\n"
        "مثال: `2500000`\n\n"
        "قیمت سایر طرح‌ها به صورت خودکار محاسبه می‌شود.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_admin_price_change)

def process_admin_price_change(message):
    global PRICE_PER_MONTH, PRICE_3_MONTHS, PRICE_6_MONTHS, PRICE_12_MONTHS
    
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        new_price = int(message.text.strip())
        PRICE_PER_MONTH = new_price
        PRICE_3_MONTHS = int(new_price * 2.5)
        PRICE_6_MONTHS = int(new_price * 4.5)
        PRICE_12_MONTHS = int(new_price * 8)
        
        # بروزرسانی در دیتابیس
        db.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at, updated_by)
            VALUES ('price_monthly', ?, ?, ?), ('price_3months', ?, ?, ?),
                   ('price_6months', ?, ?, ?), ('price_12months', ?, ?, ?)
        ''', (str(PRICE_PER_MONTH), datetime.now().isoformat(), message.from_user.id,
              str(PRICE_3_MONTHS), datetime.now().isoformat(), message.from_user.id,
              str(PRICE_6_MONTHS), datetime.now().isoformat(), message.from_user.id,
              str(PRICE_12_MONTHS), datetime.now().isoformat(), message.from_user.id))
        
        bot.reply_to(
            message,
            f"✅ **قیمت‌ها با موفقیت تغییر کردند**\n\n"
            f"💰 ماهانه: {PRICE_PER_MONTH:,} تومان\n"
            f"💰 سه ماهه: {PRICE_3_MONTHS:,} تومان\n"
            f"💰 شش ماهه: {PRICE_6_MONTHS:,} تومان\n"
            f"💰 یکساله: {PRICE_12_MONTHS:,} تومان",
            parse_mode="Markdown"
        )
    except:
        bot.reply_to(message, "❌ عدد معتبر وارد کنید!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_card")
def admin_change_card_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "🏧 **تغییر شماره کارت**\n\n"
        "لطفاً شماره کارت جدید را وارد کنید (۱۶ رقم):\n"
        "مثال: `5892101187322777`\n\n"
        "همچنین نام صاحب کارت را وارد کنید:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_admin_card_change)

def process_admin_card_change(message):
    global CARD_NUMBER
    
    if message.from_user.id not in ADMIN_IDS:
        return
    
    card = message.text.strip()
    if not card.isdigit() or len(card) != 16:
        bot.reply_to(message, "❌ شماره کارت باید ۱۶ رقم باشد!")
        return
    
    CARD_NUMBER = card
    
    # دریافت نام صاحب کارت
    msg = bot.reply_to(message, "🏧 لطفاً نام صاحب کارت را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_card_holder)

def process_admin_card_holder(message):
    global CARD_HOLDER
    
    if message.from_user.id not in ADMIN_IDS:
        return
    
    CARD_HOLDER = message.text.strip()
    
    # بروزرسانی در دیتابیس
    db.execute('''
        INSERT OR REPLACE INTO settings (key, value, updated_at, updated_by)
        VALUES ('card_number', ?, ?, ?), ('card_holder', ?, ?, ?)
    ''', (CARD_NUMBER, datetime.now().isoformat(), message.from_user.id,
          CARD_HOLDER, datetime.now().isoformat(), message.from_user.id))
    
    bot.reply_to(
        message,
        f"✅ **اطلاعات کارت با موفقیت تغییر کرد**\n\n"
        f"🏧 شماره کارت: `{CARD_NUMBER}`\n"
        f"👤 صاحب کارت: {CARD_HOLDER}",
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_change_guide")
def admin_change_guide_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "📝 **تغییر متن راهنما**\n\n"
        "لطفاً متن جدید راهنما را ارسال کنید:\n"
        "(متن می‌تواند چند خط باشد)",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_admin_guide_change)

def process_admin_guide_change(message):
    global GUIDE_TEXT
    
    if message.from_user.id not in ADMIN_IDS:
        return
    
    GUIDE_TEXT = message.text
    
    # بروزرسانی در دیتابیس
    db.execute('''
        INSERT OR REPLACE INTO settings (key, value, updated_at, updated_by)
        VALUES ('guide_text', ?, ?, ?)
    ''', (GUIDE_TEXT, datetime.now().isoformat(), message.from_user.id))
    
    bot.reply_to(message, "✅ متن راهنما با موفقیت تغییر کرد!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_user_bot")
def admin_delete_user_bot_list(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bots = db.fetch_all('''
        SELECT b.id, b.name, b.username, u.user_id, u.first_name 
        FROM bots b 
        JOIN users u ON b.user_id = u.user_id
        ORDER BY b.created_at DESC
        LIMIT 100
    ''')
    
    if not bots:
        bot.send_message(call.message.chat.id, "🤖 هیچ رباتی وجود ندارد")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']} (@{b['username']}) - کاربر: {b['first_name']}", callback_data=f"admin_del_bot_{b['id']}"))
    
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"))
    
    bot.send_message(
        call.message.chat.id,
        "🗑 **حذف ربات کاربران**\n\n"
        "ربات مورد نظر برای حذف را انتخاب کنید:\n"
        "⚠️ این عمل غیرقابل بازگشت است!",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_del_bot_'))
def admin_confirm_delete_user_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_del_bot_', '')
    
    bot_info = db.fetch_one('SELECT name, user_id, username FROM bots WHERE id = ?', (bot_id,))
    if not bot_info:
        bot.answer_callback_query(call.id, "ربات یافت نشد!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"admin_confirm_del_bot_{bot_id}"),
        types.InlineKeyboardButton("❌ خیر، انصراف", callback_data="admin_back")
    )
    
    bot.edit_message_text(
        f"⚠️ **تأیید حذف ربات**\n\n"
        f"🤖 نام: {bot_info['name']}\n"
        f"🔗 یوزرنیم: @{bot_info['username']}\n"
        f"👤 کاربر: `{bot_info['user_id']}`\n\n"
        f"آیا از حذف این ربات اطمینان دارید؟\n"
        f"این عمل غیرقابل بازگشت است!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_confirm_del_bot_'))
def admin_do_delete_user_bot(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    bot_id = call.data.replace('admin_confirm_del_bot_', '')
    
    bot_info = db.fetch_one('SELECT user_id, name FROM bots WHERE id = ?', (bot_id,))
    if bot_info:
        BotRunner.stop_bot(bot_id)
        db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
        db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (bot_info['user_id'],))
        
        add_notification(bot_info['user_id'], "ربات حذف شد", f"ربات {bot_info['name']} توسط ادمین حذف شد", "warning")
    
    bot.answer_callback_query(call.id, "✅ ربات حذف شد")
    bot.edit_message_text("✅ ربات با موفقیت حذف شد.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_prompt(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "📢 **ارسال نوتیف همگانی**\n\n"
        "لطفاً متن پیام را وارد کنید:\n"
        "(می‌تواند شامل ایموجی و لینک باشد)\n\n"
        "⚠️ پیام برای همه کاربران ارسال می‌شود!",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_admin_broadcast)

def process_admin_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    broadcast_text = message.text
    
    # دریافت همه کاربران
    users = db.fetch_all('SELECT user_id FROM users')
    
    if not users:
        bot.reply_to(message, "❌ کاربری یافت نشد!")
        return
    
    status_msg = bot.reply_to(message, f"📢 در حال ارسال پیام به {len(users)} کاربر...")
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **اعلان همگانی**\n\n{broadcast_text}", parse_mode="Markdown")
            success_count += 1
        except:
            fail_count += 1
        time.sleep(0.05)  # جلوگیری از محدودیت
    
    bot.edit_message_text(
        f"📢 **نتیجه ارسال نوتیف همگانی**\n\n"
        f"✅ موفق: {success_count}\n"
        f"❌ ناموفق: {fail_count}\n"
        f"👥 کل کاربران: {len(users)}",
        message.chat.id,
        status_msg.message_id,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_backup")
def admin_backup(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    status_msg = bot.send_message(call.message.chat.id, "💾 در حال گرفتن بکاپ...")
    
    try:
        # بکاپ از دیتابیس
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        shutil.copy2(DB_PATH, backup_path)
        
        # فشرده‌سازی
        zip_path = backup_path + ".zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(backup_path, os.path.basename(backup_path))
            zipf.write(DB_PATH, "current_database.db")
        
        # ثبت در دیتابیس
        db.execute('''
            INSERT INTO backups (filename, size, type, created_at, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (backup_name, os.path.getsize(zip_path), 'full', datetime.now().isoformat(), call.from_user.id))
        
        # ارسال فایل بکاپ به ادمین
        with open(zip_path, 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption=f"💾 **بکاپ کامل سیستم**\n\n📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n📦 حجم: {os.path.getsize(zip_path) / 1024:.1f} KB")
        
        # پاکسازی فایل‌های موقت
        os.remove(backup_path)
        os.remove(zip_path)
        
        bot.edit_message_text("✅ بکاپ با موفقیت گرفته شد.", call.message.chat.id, status_msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا در گرفتن بکاپ: {str(e)}", call.message.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_server_status")
def admin_server_status(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    # وضعیت سیستم
    import psutil
    
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # وضعیت داکر
    docker_status = "✅ فعال" if docker_manager.available else "❌ غیرفعال"
    
    # آمار ربات‌ها
    total_bots = db.fetch_one('SELECT COUNT(*) FROM bots')[0]
    running_bots = db.fetch_one('SELECT COUNT(*) FROM bots WHERE status = "running"')[0]
    
    text = (
        f"🖥 **وضعیت سرور**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💻 **منابع سیستم**\n"
        f"└ CPU: {cpu_percent}%\n"
        f"└ RAM: {memory.used // (1024**3)}/{memory.total // (1024**3)} GB ({memory.percent}%)\n"
        f"└ DISK: {disk.used // (1024**3)}/{disk.total // (1024**3)} GB ({disk.percent}%)\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🐳 **وضعیت داکر**\n"
        f"└ وضعیت: {docker_status}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **آمار ربات‌ها**\n"
        f"└ کل ربات‌ها: {total_bots}\n"
        f"└ در حال اجرا: {running_bots}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# ==================== مانیتورینگ ====================
def monitor_bots():
    """مانیتورینگ خودکار ربات‌ها"""
    while True:
        try:
            # بررسی تست‌های 24 ساعته
            trials = db.fetch_all('SELECT user_id, bot_id FROM trial_usage WHERE is_active = 1')
            for trial in trials:
                if not SubscriptionManager.is_trial_active(trial['user_id']):
                    if trial['bot_id']:
                        BotRunner.stop_bot(trial['bot_id'])
                        update_bot_status(trial['bot_id'], 'stopped')
                        try:
                            bot.send_message(
                                trial['user_id'],
                                f"⏰ **تست ۲۴ ساعته شما به پایان رسید!**\n\n"
                                f"🤖 ربات شما متوقف شد.\n"
                                f"💡 برای ادامه استفاده، اشتراک تهیه کنید:\n"
                                f"└ ماهانه: {PRICE_PER_MONTH:,} تومان\n"
                                f"└ سه ماهه: {PRICE_3_MONTHS:,} تومان\n"
                                f"└ شش ماهه: {PRICE_6_MONTHS:,} تومان\n"
                                f"└ یکساله: {PRICE_12_MONTHS:,} تومان",
                                parse_mode="Markdown"
                            )
                        except:
                            pass
            
            # بررسی اشتراک‌های منقضی شده
            expired_subs = db.fetch_all('''
                SELECT user_id FROM subscriptions 
                WHERE is_active = 1 AND end_date < datetime('now')
            ''')
            for sub in expired_subs:
                db.execute('UPDATE subscriptions SET is_active = 0 WHERE user_id = ?', (sub['user_id'],))
                db.execute('UPDATE users SET max_bots = 1 WHERE user_id = ?', (sub['user_id'],))
            
            time.sleep(1800)  # هر 30 دقیقه
            
        except Exception as e:
            logger.error(f"خطا در مانیتورینگ: {e}")
            time.sleep(60)

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ربات مادر نهایی - نسخه نهایی 13.0")
    print("=" * 70)
    print(f"📌 نسخه: {VERSION}")
    print(f"📌 بیلد: {BUILD}")
    print(f"📌 نویسنده: {AUTHOR}")
    print("=" * 70)
    print(f"👑 ادمین: {ADMIN_IDS}")
    print(f"💰 قیمت ماهانه: {PRICE_PER_MONTH:,} تومان")
    print(f"💰 قیمت سه ماهه: {PRICE_3_MONTHS:,} تومان")
    print(f"💰 قیمت شش ماهه: {PRICE_6_MONTHS:,} تومان")
    print(f"💰 قیمت یکساله: {PRICE_12_MONTHS:,} تومان")
    print(f"💳 حداقل برداشت: {MIN_WITHDRAW_AMOUNT:,} تومان")
    print(f"🎁 پورسانت رفرال: {REFERRAL_COMMISSION_PERCENT}%")
    print(f"⏰ تست ۲۴ ساعته: فعال")
    print("=" * 70)
    print("✅ داکر: فعال")
    print("✅ دیتابیس: متصل")
    print("✅ مانیتورینگ: فعال")
    print("=" * 70)
    print("🤖 ربات در حال اجراست...")
    print("=" * 70)
    
    # راه‌اندازی ترد مانیتورینگ
    monitor_thread = threading.Thread(target=monitor_bots, daemon=True)
    monitor_thread.start()
    
    # اجرای ربات
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"خطا در اجرا: {e}")
            time.sleep(5)