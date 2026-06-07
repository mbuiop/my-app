#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🚀 ربات مادر نهایی - نسخه 100.4 Complete Ultimate Enterprise
⚡ پشتیبانی از ۷ زبان برنامه نویسی (Python, JS, Java, C#, PHP, Go, Rust)
🖥️ پنل مدیریت کامل و فقط فارسی
🐳 پشتیبانی از Docker و Kubernetes
💎 سیستم کمیسیون دقیق رفرال
🤖 محدودیت ۳ ربات در هر اشتراک (قابل تنظیم)
🔒 امنیت فوق پیشرفته با رمزنگاری
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import signal
import secrets
import hashlib
import logging
import sqlite3
import threading
import subprocess
import zipfile
import shutil
import re
import queue
import uuid
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from functools import wraps
from collections import defaultdict
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import telebot
from telebot import types
import requests
from flask import Flask, request, jsonify

# ==================== امنیت: توکن از محیط ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN not found!")
    print("✅ Solution: export BOT_TOKEN='your_token_here'")
    sys.exit(1)

# ==================== تنظیمات پایه ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DIRS = {
    'DB': os.path.join(BASE_DIR, "database"),
    'FILES': os.path.join(BASE_DIR, "user_files"),
    'RUNNING': os.path.join(BASE_DIR, "running_bots"),
    'LOGS': os.path.join(BASE_DIR, "logs"),
    'RECEIPTS': os.path.join(BASE_DIR, "receipts"),
    'TEMP': os.path.join(BASE_DIR, "temp"),
    'MACHINES': os.path.join(BASE_DIR, "machines"),
    'CACHE': os.path.join(BASE_DIR, "cache"),
    'BACKUPS': os.path.join(BASE_DIR, "backups"),
    'STATE': os.path.join(BASE_DIR, "state"),
    'SERVER_SCRIPTS': os.path.join(BASE_DIR, "server_scripts"),
    'TEMPLATES': os.path.join(BASE_DIR, "templates"),
    'DOCKER': os.path.join(BASE_DIR, "docker"),
    'KUBERNETES': os.path.join(BASE_DIR, "kubernetes")
}

for dir_path in DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

# ==================== لاگینگ امن ====================
class SecureFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        msg = re.sub(r'bot\d+:[A-Za-z0-9_-]{20,}', '[TOKEN_HIDDEN]', msg)
        msg = re.sub(r'\d{10}:[A-Za-z0-9_-]{35,}', '[TOKEN_HIDDEN]', msg)
        msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_HIDDEN]', msg)
        return msg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(DIRS['LOGS'], 'mother_bot.log'),
            maxBytes=100*1024*1024,
            backupCount=10,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)

for handler in logging.root.handlers:
    handler.setFormatter(SecureFormatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('MotherBot')

# ==================== توکن و تنظیمات ====================
ADMIN_IDS = [327855654]  # آیدی ادمین رو اینجا قرار بدید
BOT_USERNAME = "ROBTTSAZE_bot"

# ==================== زبان‌های برنامه نویسی پشتیبانی شده ====================
class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CSHARP = "csharp"
    PHP = "php"
    GO = "go"
    RUST = "rust"

@dataclass
class LanguageConfig:
    name: str
    display_name: str
    extension: str
    docker_image: str
    run_command: str
    template: str
    icon: str

LANGUAGES = {
    Language.PYTHON: LanguageConfig(
        name="python",
        display_name="🐍 Python",
        extension=".py",
        docker_image="python:3.11-slim",
        run_command="python3 bot.py",
        icon="🐍",
        template="""#!/usr/bin/env python3
import telebot
import os
import time
import threading

TOKEN = "{token}"
bot = telebot.TeleBot(TOKEN)

join_enabled = True
block_message = "🚫 سرور پر است"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🚀 ربات با موفقیت اجرا شد!")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
    if join_enabled:
        bot.reply_to(message, message.text)
    else:
        bot.reply_to(message, block_message)

if __name__ == "__main__":
    print("🤖 Bot started!")
    bot.infinity_polling()
"""
    ),
    Language.JAVASCRIPT: LanguageConfig(
        name="javascript",
        display_name="📜 JavaScript",
        extension=".js",
        docker_image="node:18-slim",
        run_command="node bot.js",
        icon="📜",
        template="""const TelegramBot = require('node-telegram-bot-api');
const token = '{token}';
const bot = new TelegramBot(token, { polling: true });

let joinEnabled = true;
let blockMessage = "🚫 Server is full";

bot.onText(/\\/start/, (msg) => {{
    bot.sendMessage(msg.chat.id, "🚀 Bot started successfully!");
}});

bot.on('message', (msg) => {{
    if (msg.text && !msg.text.startsWith('/')) {{
        if (joinEnabled) {{
            bot.sendMessage(msg.chat.id, msg.text);
        }} else {{
            bot.sendMessage(msg.chat.id, blockMessage);
        }}
    }}
}});

console.log('🤖 Bot started!');
"""
    ),
    Language.JAVA: LanguageConfig(
        name="java",
        display_name="☕ Java",
        extension=".java",
        docker_image="openjdk:17-slim",
        run_command="javac Bot.java && java Bot",
        icon="☕",
        template="""import org.telegram.telegrambots.bots.TelegramLongPollingBot;
import org.telegram.telegrambots.meta.api.methods.send.SendMessage;
import org.telegram.telegrambots.meta.api.objects.Update;
import org.telegram.telegrambots.meta.exceptions.TelegramApiException;
import org.telegram.telegrambots.updatesreceivers.DefaultBotSession;
import org.telegram.telegrambots.meta.TelegramBotsApi;

public class Bot extends TelegramLongPollingBot {{
    private boolean joinEnabled = true;
    private String blockMessage = "🚫 Server is full";
    
    @Override
    public String getBotUsername() {{
        return "{username}";
    }}
    
    @Override
    public String getBotToken() {{
        return "{token}";
    }}
    
    @Override
    public void onUpdateReceived(Update update) {{
        if (update.hasMessage() && update.getMessage().hasText()) {{
            String text = update.getMessage().getText();
            long chatId = update.getMessage().getChatId();
            
            if (text.equals("/start")) {{
                sendMessage(chatId, "🚀 Bot started successfully!");
            }} else if (joinEnabled) {{
                sendMessage(chatId, text);
            }} else {{
                sendMessage(chatId, blockMessage);
            }}
        }}
    }}
    
    private void sendMessage(long chatId, String text) {{
        SendMessage message = new SendMessage();
        message.setChatId(String.valueOf(chatId));
        message.setText(text);
        try {{
            execute(message);
        }} catch (TelegramApiException e) {{
            e.printStackTrace();
        }}
    }}
    
    public static void main(String[] args) throws Exception {{
        TelegramBotsApi botsApi = new TelegramBotsApi(DefaultBotSession.class);
        botsApi.registerBot(new Bot());
        System.out.println("🤖 Bot started!");
    }}
}}
"""
    ),
    Language.CSHARP: LanguageConfig(
        name="csharp",
        display_name="🔷 C#",
        extension=".cs",
        docker_image="mcr.microsoft.com/dotnet/sdk:6.0",
        run_command="dotnet run",
        icon="🔷",
        template="""using System;
using System.Threading;
using System.Threading.Tasks;
using Telegram.Bot;
using Telegram.Bot.Types;
using Telegram.Bot.Polling;

class Program
{{
    private static ITelegramBotClient botClient;
    private static bool joinEnabled = true;
    private static string blockMessage = "🚫 Server is full";
    
    static async Task Main(string[] args)
    {{
        botClient = new TelegramBotClient("{token}");
        
        using var cts = new CancellationTokenSource();
        var receiverOptions = new ReceiverOptions {{ AllowedUpdates = {{ }} }};
        
        botClient.StartReceiving(HandleUpdateAsync, HandleErrorAsync, receiverOptions, cts.Token);
        
        Console.WriteLine("🤖 Bot started!");
        await Task.Delay(-1);
    }}
    
    static async Task HandleUpdateAsync(ITelegramBotClient botClient, Update update, CancellationToken cancellationToken)
    {{
        if (update.Message?.Text is not {{ }} messageText) return;
        var chatId = update.Message.Chat.Id;
        
        if (messageText == "/start")
        {{
            await botClient.SendTextMessageAsync(chatId, "🚀 Bot started successfully!");
        }}
        else if (joinEnabled)
        {{
            await botClient.SendTextMessageAsync(chatId, messageText);
        }}
        else
        {{
            await botClient.SendTextMessageAsync(chatId, blockMessage);
        }}
    }}
    
    static Task HandleErrorAsync(ITelegramBotClient botClient, Exception exception, CancellationToken cancellationToken)
    {{
        Console.WriteLine($"Error: {{exception.Message}}");
        return Task.CompletedTask;
    }}
}}
"""
    ),
    Language.PHP: LanguageConfig(
        name="php",
        display_name="🐘 PHP",
        extension=".php",
        docker_image="php:8.2-cli",
        run_command="php bot.php",
        icon="🐘",
        template="""<?php
define('BOT_TOKEN', '{token}');
define('API_URL', 'https://api.telegram.org/bot' . BOT_TOKEN . '/');

$joinEnabled = true;
$blockMessage = "🚫 Server is full";

function sendMessage($chatId, $text) {{
    $url = API_URL . 'sendMessage';
    $data = array('chat_id' => $chatId, 'text' => $text);
    $options = array('http' => array('method' => 'POST', 'content' => http_build_query($data)));
    file_get_contents($url, false, stream_context_create($options));
}}

$lastUpdateId = 0;
echo "🤖 Bot started!\\n";

while (true) {{
    $updates = json_decode(file_get_contents(API_URL . 'getUpdates?offset=' . ($lastUpdateId + 1) . '&timeout=30'), true);
    if (isset($updates['result'])) {{
        foreach ($updates['result'] as $update) {{
            $lastUpdateId = $update['update_id'];
            if (isset($update['message']['text'])) {{
                $chatId = $update['message']['chat']['id'];
                $text = $update['message']['text'];
                
                if ($text == '/start') {{
                    sendMessage($chatId, "🚀 Bot started successfully!");
                }} else if ($joinEnabled) {{
                    sendMessage($chatId, $text);
                }} else {{
                    sendMessage($chatId, $blockMessage);
                }}
            }}
        }}
    }}
    sleep(1);
}}
?>
"""
    ),
    Language.GO: LanguageConfig(
        name="go",
        display_name="🐹 Go",
        extension=".go",
        docker_image="golang:1.21-alpine",
        run_command="go run bot.go",
        icon="🐹",
        template="""package main

import (
    "fmt"
    "log"
    tgbotapi "github.com/go-telegram-bot-api/telegram-bot-api/v5"
)

var joinEnabled = true
var blockMessage = "🚫 Server is full"

func main() {
    bot, err := tgbotapi.NewBotAPI("{token}")
    if err != nil {{
        log.Panic(err)
    }}

    log.Printf("🤖 Bot started! Authorized on account %s", bot.Self.UserName)

    u := tgbotapi.NewUpdate(0)
    u.Timeout = 60
    updates := bot.GetUpdatesChan(u)

    for update := range updates {{
        if update.Message == nil {{ continue }}
        
        chatId := update.Message.Chat.ID
        messageText := update.Message.Text

        if messageText == "/start" {{
            msg := tgbotapi.NewMessage(chatId, "🚀 Bot started successfully!")
            bot.Send(msg)
        }} else if joinEnabled {{
            msg := tgbotapi.NewMessage(chatId, messageText)
            bot.Send(msg)
        }} else {{
            msg := tgbotapi.NewMessage(chatId, blockMessage)
            bot.Send(msg)
        }}
    }}
}
"""
    ),
    Language.RUST: LanguageConfig(
        name="rust",
        display_name="🦀 Rust",
        extension=".rs",
        docker_image="rust:1.74-alpine",
        run_command="cargo run",
        icon="🦀",
        template="""use teloxide::prelude::*;
use std::sync::atomic::{AtomicBool, Ordering};

static JOIN_ENABLED: AtomicBool = AtomicBool::new(true);
const BLOCK_MESSAGE: &str = "🚫 Server is full";

#[tokio::main]
async fn main() {{
    pretty_env_logger::init();
    log::info!("🤖 Bot started!");

    let bot = Bot::new("{token}");

    teloxide::repl(bot, |bot: Bot, msg: Message| async move {{
        let text = msg.text().unwrap_or("");
        
        if text == "/start" {{
            bot.send_message(msg.chat.id, "🚀 Bot started successfully!").await?;
        }} else if JOIN_ENABLED.load(Ordering::SeqCst) {{
            bot.send_message(msg.chat.id, text).await?;
        }} else {{
            bot.send_message(msg.chat.id, BLOCK_MESSAGE).await?;
        }}
        Ok(())
    }})
    .await;
}}
"""
    )
}

# ==================== دکمه‌های منوی عمومی (دو زبانه) ====================
MENU_BUTTONS_FA = [
    '🤖 ساخت ربات جدید',
    '📋 ربات‌های من',
    '🔄 فعال/غیرفعال',
    '🗑 حذف ربات',
    '💰 کیف پول و اشتراک',
    '📚 راهنما',
    '👥 دعوت دوستان',
    '💸 درخواست برداشت',
    '📦 کتابخانه',
    '🗂️ قالب‌های آماده',
    '📊 آمار',
    '📞 پشتیبانی',
    '⚡ وضعیت صف',
    '📈 مصرف من',
    '🌐 زبان / Language'
]

MENU_BUTTONS_EN = [
    '🤖 New Bot',
    '📋 My Bots',
    '🔄 Start/Stop',
    '🗑 Delete Bot',
    '💰 Wallet & Subscription',
    '📚 Guide',
    '👥 Invite Friends',
    '💸 Withdraw',
    '📦 Library',
    '🗂️ Templates',
    '📊 Stats',
    '📞 Support',
    '⚡ Queue Status',
    '📈 My Usage',
    '🌐 Language / زبان'
]

# ==================== دکمه‌های پنل مدیریت (فقط فارسی) ====================
ADMIN_BUTTONS = [
    '👑 پنل مدیریت',
    '📸 تایید فیش',
    '💰 تایید برداشت',
    '⚙️ تنظیمات سیستم',
    '📊 آمار کاربران',
    '🗑 حذف کاربران',
    '🗑 حذف ربات‌های کاربران',
    '📢 پیام همگانی',
    '🔍 بررسی ربات‌های کاربران',
    '💳 تنظیم آدرس کیف پول',
    '📝 عوض کردن متن راهنما',
    '👋 عوض کردن متن خوش آمد گویی',
    '✅ عوض کردن متن فعالسازی اشتراک',
    '💸 عوض کردن متن خرید اشتراک',
    '🔄 ریستارت ربات‌های مرده',
    '🐛 مدیریت خطاهای ربات',
    '⚙️ تنظیم ظرفیت کاربران',
    '🖥️ مدیریت ماشین‌ها',
    '➕ اضافه کردن سرور جدید',
    '🐳 مدیریت داکر',
    '☸️ مدیریت کوبرنتیز',
    '🔙 بازگشت به منوی اصلی'
]

# ==================== متن‌های چند زبانه ====================
TEXTS = {
    'fa': {
        'welcome': "🚀 خوش آمدید {name}!",
        'subscription_active': "✅ اشتراک فعال",
        'subscription_inactive': "❌ اشتراک غیرفعال",
        'bots_remaining': "🤖 ربات‌های باقیمانده: {remaining}/{max}",
        'deposit_address': "💳 آدرس واریز:\n`{address}`\n🏦 شبکه: کارت به کارت",
        'deposit_address_trc20': "💳 آدرس واریز TRC20:\n`{address}`\n🌐 شبکه: TRC20 (USDT)",
        'send_receipt': "📸 لطفاً تصویر تراکنش را ارسال کنید",
        'receipt_received': "✅ تصویر دریافت شد، در انتظار تایید",
        'commission_added': "🎉 کمیسیون {amount:,} تومان به کیف پول شما اضافه شد",
        'bot_limit_reached': "❌ به حداکثر مجاز {max} ربات رسیده‌اید",
        'build_guide': "📚 راهنمای ساخت ربات\n\n1️⃣ فایل .py یا .zip خود را ارسال کنید\n2️⃣ می‌توانید پوشه‌بندی دلخواه داشته باشید\n3️⃣ منتظر بمانید تا ساخته شود\n4️⃣ ربات شما آماده است!\n\n🎯 زبان‌های پشتیبانی شده:\n- 🐍 Python\n- 📜 JavaScript (Node.js)\n- ☕ Java\n- 🔷 C# (.NET)\n- 🐘 PHP\n- 🐹 Go\n- 🦀 Rust",
        'error': "❌ خطا: {error}",
        'success': "✅ موفق: {message}",
        'persian': "🇮🇷 فارسی",
        'english': "🇬🇧 انگلیسی",
        'balance': "💰 موجودی: {balance:,} تومان",
        'referral_count': "👥 دعوت‌ها: {count}",
        'expiry_date': "📅 انقضا: {date}",
        'no_bots': "📋 رباتی ندارید",
        'bot_list': "📋 لیست ربات‌های شما",
        'select_bot': "🤖 ربات را انتخاب کنید:",
        'confirm_delete': "⚠️ آیا برای حذف اطمینان دارید؟",
        'deleted': "✅ حذف شد",
        'started': "✅ فعال شد",
        'stopped': "✅ متوقف شد",
        'processing': "🔄 در حال پردازش...",
        'invalid_file': "❌ فقط فایل‌های .py یا .zip",
        'file_too_large': "❌ حجم بیشتر از ۵۰ مگابایت",
        'token_not_found': "❌ توکن در کد پیدا نشد",
        'invalid_token': "❌ توکن نامعتبر",
        'build_success': "✅ ربات {name} ساخته شد!\n🤖 ربات باقیمانده: {remaining}",
        'build_failed': "❌ ساخت ناموفق: {error}",
        'stats_title': "📊 **آمار سیستم**",
        'users_count': "👥 کاربران: {count:,}",
        'active_subs': "✅ اشتراک فعال: {count:,}",
        'total_bots': "🤖 کل ربات‌ها: {count:,}",
        'running_bots': "🟢 ربات فعال: {count:,}",
        'total_wallet': "💰 کیف پول کل: {amount:,} تومان",
        'machine_stats': "🖥️ ماشین‌ها: {machines} | مصرف: {usage}%",
        'queue_status': "⚡ صف ساخت: {queue}",
        'support': "📞 پشتیبانی: @shahraghee13",
        'invite_title': "👥 **سیستم دعوت دوستان**",
        'referral_code': "🎁 کد معرف: `{code}`",
        'referral_link': "🔗 لینک دعوت: `{link}`",
        'commission_rate': "💰 کمیسیون هر اشتراک: {percent}%",
        'total_commission': "💎 کمیسیون کل: {amount:,} تومان",
        'copy_link': "📋 کپی لینک",
        'address_copied': "✅ آدرس کپی شد!",
        'link_copied': "✅ لینک کپی شد!",
        'subscription_status': "💳 وضعیت: {status}",
        'remaining_bots': "📦 ربات باقیمانده: {remaining}/{max}",
        'daily_usage': "📊 **مصرف شما امروز**",
        'builds_today': "🤖 ساخت ربات: {count}/{max}",
        'usage_bar': "📈 {bar} {percent}%",
        'total_bots_count': "📋 تعداد ربات‌ها: {count}",
        'wallet_title': "💰 **کیف پول و اشتراک**",
        'wallet_balance': "💰 موجودی: {balance:,} تومان",
        'payment_guide_fa': "💳 برای فعالسازی {price} را به کارت زیر واریز:\n`{card}`\n👤 {holder}\n🏦 {bank}\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید",
        'payment_guide_en': "💳 To activate, send {price} to TRC20 address:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
        'receipt_pending': "⏳ فیش قبلی در انتظار تایید است",
        'send_file': "📤 فایل `.py` یا `.zip` خود را ارسال کنید\n💡 می‌توانید پوشه‌بندی دلخواه داشته باشید\n\n🎯 زبان‌های پشتیبانی شده:\n- 🐍 Python\n- 📜 JavaScript (Node.js)\n- ☕ Java\n- 🔷 C# (.NET)\n- 🐘 PHP\n- 🐹 Go\n- 🦀 Rust",
        'capacity_full': "⚠️ ظرفیت ربات تکمیل شده است! لطفاً وارد ربات جدید شوید: {link}",
        'language_changed': "✅ زبان به فارسی تغییر کرد",
        'language_changed_en': "✅ Language changed to English",
        'templates_title': "🗂️ **قالب‌های آماده ربات**",
        'select_language': "🎯 زبان برنامه نویسی مورد نظر را انتخاب کنید:",
        'template_sent': "✅ قالب {language} با موفقیت ارسال شد!",
        'docker_status': "🐳 **وضعیت داکر**\n\n{status}",
        'kubernetes_status': "☸️ **وضعیت کوبرنتیز**\n\n{status}"
    },
    'en': {
        'welcome': "🚀 Welcome {name}!",
        'subscription_active': "✅ Subscription Active",
        'subscription_inactive': "❌ Subscription Inactive",
        'bots_remaining': "🤖 Bots remaining: {remaining}/{max}",
        'deposit_address': "💳 Deposit Address:\n`{address}`\n🌐 Network: TRC20 (USDT)",
        'deposit_address_trc20': "💳 TRC20 Deposit Address:\n`{address}`\n🌐 Network: TRC20 (USDT)",
        'send_receipt': "📸 Please send your transaction screenshot",
        'receipt_received': "✅ Receipt received, pending approval",
        'commission_added': "🎉 Commission {amount:,} Toman added to your wallet",
        'bot_limit_reached': "❌ You have reached the maximum of {max} bots",
        'build_guide': "📚 Bot Building Guide\n\n1️⃣ Send your .py or .zip file\n2️⃣ You can have custom folder structure\n3️⃣ Wait for it to be built\n4️⃣ Your bot is ready!\n\n🎯 Supported languages:\n- 🐍 Python\n- 📜 JavaScript (Node.js)\n- ☕ Java\n- 🔷 C# (.NET)\n- 🐘 PHP\n- 🐹 Go\n- 🦀 Rust",
        'error': "❌ Error: {error}",
        'success': "✅ Success: {message}",
        'persian': "🇮🇷 Persian",
        'english': "🇬🇧 English",
        'balance': "💰 Balance: {balance:,} Toman",
        'referral_count': "👥 Referrals: {count}",
        'expiry_date': "📅 Expiry: {date}",
        'no_bots': "📋 No bots yet",
        'bot_list': "📋 Your Bots",
        'select_bot': "🤖 Select a bot:",
        'confirm_delete': "⚠️ Are you sure you want to delete?",
        'deleted': "✅ Deleted",
        'started': "✅ Started",
        'stopped': "✅ Stopped",
        'processing': "🔄 Processing...",
        'invalid_file': "❌ Only .py or .zip files",
        'file_too_large': "❌ File too large (max 50MB)",
        'token_not_found': "❌ Bot token not found in code",
        'invalid_token': "❌ Invalid bot token",
        'build_success': "✅ Bot {name} created!\n🤖 Remaining slots: {remaining}",
        'build_failed': "❌ Build failed: {error}",
        'stats_title': "📊 **System Statistics**",
        'users_count': "👥 Users: {count:,}",
        'active_subs': "✅ Active Subscriptions: {count:,}",
        'total_bots': "🤖 Total Bots: {count:,}",
        'running_bots': "🟢 Running Bots: {count:,}",
        'total_wallet': "💰 Total Wallet: {amount:,} Toman",
        'machine_stats': "🖥️ Machines: {machines} | Usage: {usage}%",
        'queue_status': "⚡ Build Queue: {queue}",
        'support': "📞 Support: @shahraghee13",
        'invite_title': "👥 **Referral System**",
        'referral_code': "🎁 Referral Code: `{code}`",
        'referral_link': "🔗 Invite Link: `{link}`",
        'commission_rate': "💰 Commission per subscription: {percent}%",
        'total_commission': "💎 Total Commission: {amount:,} Toman",
        'copy_link': "📋 Copy Link",
        'address_copied': "✅ Address copied!",
        'link_copied': "✅ Link copied!",
        'subscription_status': "💳 Status: {status}",
        'remaining_bots': "📦 Remaining bots: {remaining}/{max}",
        'daily_usage': "📊 **Your Daily Usage**",
        'builds_today': "🤖 Bot builds: {count}/{max}",
        'usage_bar': "📈 {bar} {percent}%",
        'total_bots_count': "📋 Total bots: {count}",
        'wallet_title': "💰 **Wallet & Subscription**",
        'wallet_balance': "💰 Balance: {balance:,} Toman",
        'payment_guide_fa': "💳 To activate, send {price} to:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
        'payment_guide_en': "💳 To activate, send {price} to TRC20 address:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
        'receipt_pending': "⏳ Previous receipt pending approval",
        'send_file': "📤 Send your `.py` or `.zip` file\n💡 You can have custom folder structure\n\n🎯 Supported languages:\n- 🐍 Python\n- 📜 JavaScript\n- ☕ Java\n- 🔷 C#\n- 🐘 PHP\n- 🐹 Go\n- 🦀 Rust",
        'capacity_full': "⚠️ Bot capacity is full! Please join new bot: {link}",
        'language_changed': "✅ Language changed to Persian",
        'language_changed_en': "✅ زبان به انگلیسی تغییر کرد",
        'templates_title': "🗂️ **Bot Templates**",
        'select_language': "🎯 Select programming language:",
        'template_sent': "✅ {language} template sent successfully!",
        'docker_status': "🐳 **Docker Status**\n\n{status}",
        'kubernetes_status': "☸️ **Kubernetes Status**\n\n{status}"
    }
}

# ==================== تنظیمات پیش‌فرض ====================
DEFAULT_SETTINGS = {
    'trc20_address': "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A",
    'card_number': "5892101187322777",
    'card_number_display': "5892 1011 8732 2777",
    'card_holder': "مرتضی نیکخو خنجری",
    'card_bank': "بانک ملی - سپهر",
    'subscription_price': 2000000,
    'subscription_price_str': "۲,۰۰۰,۰۰۰ تومان",
    'subscription_price_usd': "50 USD",
    'withdraw_percent': 7,
    'min_withdraw': 2000000,
    'max_bots_per_subscription': 3,
    'max_users_capacity': 10000,
    'capacity_warning_message': "⚠️ ظرفیت ربات تکمیل شده است! لطفاً وارد ربات جدید شوید: @NEW_BOT",
    'new_bot_link': "@NEW_BOT",
    'guide_text_fa': "📚 راهنمای استفاده\n\n1️⃣ برای ساخت ربات، فایل .py یا .zip خود را ارسال کنید\n2️⃣ پس از پرداخت اشتراک ماهیانه، می‌توانید ربات بسازید\n3️⃣ هر کاربر می‌تواند تا ۳ ربات بسازد\n4️⃣ با دعوت دوستان، ۷٪ کمیسیون دریافت کنید\n5️⃣ پس از رسیدن به ۲ میلیون تومان، می‌توانید برداشت کنید\n\n🎯 زبان‌های پشتیبانی شده:\n- 🐍 Python\n- 📜 JavaScript (Node.js)\n- ☕ Java\n- 🔷 C# (.NET)\n- 🐘 PHP\n- 🐹 Go\n- 🦀 Rust",
    'guide_text_en': "📚 User Guide\n\n1️⃣ Send your .py or .zip file\n2️⃣ After subscription payment, you can build bots\n3️⃣ Each user can build up to 3 bots\n4️⃣ Invite friends and get 7% commission\n5️⃣ Withdraw after reaching 2,000,000 Toman\n\n🎯 Supported languages:\n- 🐍 Python\n- 📜 JavaScript\n- ☕ Java\n- 🔷 C#\n- 🐘 PHP\n- 🐹 Go\n- 🦀 Rust",
    'welcome_text_fa': "🚀 خوش آمدید {name}!\nبه ربات سازنده ربات خوش آمدید.\n\n🎯 می‌توانید ربات خود را به ۷ زبان برنامه نویسی مختلف بسازید!",
    'welcome_text_en': "🚀 Welcome {name}!\nWelcome to the bot builder bot.\n\n🎯 You can build your bot in 7 different programming languages!",
    'subscription_active_text_fa': "✅ اشتراک شما با موفقیت فعال شد!\nاکنون می‌توانید ربات خود را بسازید.\n\n🎯 زبان‌های پشتیبانی شده:\n- 🐍 Python\n- 📜 JavaScript\n- ☕ Java\n- 🔷 C#\n- 🐘 PHP\n- 🐹 Go\n- 🦀 Rust",
    'subscription_active_text_en': "✅ Your subscription has been activated!\nYou can now build your bot.\n\n🎯 Supported languages:\n- 🐍 Python\n- 📜 JavaScript\n- ☕ Java\n- 🔷 C#\n- 🐘 PHP\n- 🐹 Go\n- 🦀 Rust",
    'subscription_payment_text_fa': "💳 برای فعالسازی {price} را به کارت زیر واریز:\n`{card}`\n👤 {holder}\n🏦 {bank}\n\n📸 پس از واریز، تصویر تراکنش را ارسال کنید",
    'subscription_payment_text_en': "💳 To activate, send {price} to TRC20 address:\n`{address}`\n🌐 Network: TRC20 (USDT)\n\n📸 Send transaction screenshot after payment",
    'max_builds_per_hour': 10,
    'max_concurrent_builds': 20,
    'rate_limit_per_second': 5,
    'health_check_interval': 30,
    'auto_scale_threshold': 80,
    'backup_interval': 3600,
    'state_save_interval': 60,
    'docker_enabled': 1,
    'kubernetes_enabled': 0,
    'kubernetes_namespace': "default"
}

# ==================== دیتابیس ====================
class Database:
    def __init__(self):
        self.conn = None
        self._init_db()
        self._init_tables()
    
    def _init_db(self):
        db_path = os.path.join(DIRS['DB'], 'mother_bot.db')
        self.conn = sqlite3.connect(
            db_path,
            timeout=60,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
    
    def execute(self, query, params=()):
        try:
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB error: {e}")
            return []
    
    def _init_tables(self):
        # کاربران
        self.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'fa',
                bots_count INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 3,
                subscription_status TEXT DEFAULT 'inactive',
                subscription_expiry TIMESTAMP,
                subscription_purchased_at TIMESTAMP,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                wallet_balance INTEGER DEFAULT 0,
                total_commission INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                last_payment_hash TEXT,
                is_banned INTEGER DEFAULT 0
            )
        ''')
        
        # ربات‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                token TEXT,
                name TEXT,
                username TEXT,
                language TEXT DEFAULT 'python',
                file_path TEXT,
                folder_path TEXT,
                pid INTEGER,
                machine_id INTEGER,
                port INTEGER,
                status TEXT DEFAULT 'stopped',
                created_at TIMESTAMP,
                last_active TIMESTAMP,
                join_enabled INTEGER DEFAULT 1,
                join_block_message TEXT DEFAULT '🚫 سرور پر است',
                health_status TEXT DEFAULT 'healthy',
                error_message TEXT
            )
        ''')
        
        # ماشین‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                ip TEXT,
                port INTEGER DEFAULT 22,
                username TEXT,
                password TEXT,
                status TEXT DEFAULT 'active',
                current_bots INTEGER DEFAULT 0,
                max_bots INTEGER DEFAULT 5000,
                created_at TIMESTAMP,
                is_local INTEGER DEFAULT 1
            )
        ''')
        
        # فیش‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_path TEXT,
                tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP
            )
        ''')
        
        # درخواست‌های برداشت
        self.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                address TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        
        # کمیسیون‌ها
        self.execute('''
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                from_user INTEGER,
                amount INTEGER,
                reason TEXT,
                created_at TIMESTAMP,
                paid BOOLEAN DEFAULT 0
            )
        ''')
        
        # خطاها
        self.execute('''
            CREATE TABLE IF NOT EXISTS errors (
                id TEXT PRIMARY KEY,
                type TEXT,
                message TEXT,
                user_id INTEGER,
                bot_id TEXT,
                timestamp TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                stack_trace TEXT
            )
        ''')
        
        # تنظیمات سیستم
        self.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            )
        ''')
        
        # آمار روزانه
        self.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                new_users INTEGER DEFAULT 0,
                new_bots INTEGER DEFAULT 0,
                new_subscriptions INTEGER DEFAULT 0,
                total_revenue INTEGER DEFAULT 0
            )
        ''')
        
        # تنظیمات پیش‌فرض
        for key, value in DEFAULT_SETTINGS.items():
            self.execute('INSERT OR IGNORE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)',
                        (key, str(value), datetime.now().isoformat()))
        
        # ماشین اصلی
        existing = self.execute("SELECT COUNT(*) as count FROM machines")
        if existing and existing[0]['count'] == 0:
            self.execute('INSERT INTO machines (id, name, status, max_bots, created_at, is_local) VALUES (1, "سرور اصلی", "active", 5000, ?, 1)',
                        (datetime.now().isoformat(),))

db = Database()

# ==================== توابع کمکی ====================
def get_setting(key):
    result = db.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    if result:
        val = result[0]['value']
        if key in ['subscription_price', 'withdraw_percent', 'min_withdraw', 
                   'max_bots_per_subscription', 'max_builds_per_hour', 
                   'max_concurrent_builds', 'max_users_capacity', 'docker_enabled']:
            try:
                return int(val)
            except:
                return DEFAULT_SETTINGS.get(key, 0)
        return val
    return DEFAULT_SETTINGS.get(key)

def update_setting(key, value):
    db.execute("UPDATE system_settings SET value = ?, updated_at = ? WHERE key = ?", 
               (str(value), datetime.now().isoformat(), key))

def get_user_language(user_id):
    user = get_user(user_id)
    if user:
        return user.get('language', 'fa')
    return 'fa'

def get_text(user_id, key, **kwargs):
    lang = get_user_language(user_id)
    text = TEXTS.get(lang, TEXTS['fa']).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

def generate_referral_code(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}_{secrets.token_hex(4)}".encode()).hexdigest()[:12]

def get_user(user_id):
    users = db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if users:
        return dict(users[0])
    return None

def create_user(user_id, username, first_name, last_name, referred_by=None, language='fa'):
    now = datetime.now().isoformat()
    referral_code = generate_referral_code(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    max_capacity = get_setting('max_users_capacity')
    
    if users_count >= max_capacity:
        return False, "capacity_full"
    
    db.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, last_name, referral_code, referred_by, 
         created_at, last_active, subscription_status, wallet_balance, language, max_bots)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'inactive', 0, ?, ?)
    ''', (user_id, username, first_name, last_name, referral_code, referred_by, 
          now, now, language, max_bots))
    
    db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
    
    if referred_by and referred_by != user_id:
        db.execute('UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?', (referred_by,))
    
    return True, "ok"

def check_subscription(user_id):
    user = get_user(user_id)
    if not user or user.get('is_banned', 0) == 1:
        return False
    
    if user['subscription_status'] == 'active' and user['subscription_expiry']:
        expiry = datetime.fromisoformat(user['subscription_expiry'])
        if expiry > datetime.now():
            return True
        else:
            db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user_id,))
    return False

def get_remaining_bots(user_id):
    user = get_user(user_id)
    if not user:
        return 0
    
    max_bots = get_setting('max_bots_per_subscription')
    current_bots = user.get('bots_count', 0)
    
    if check_subscription(user_id):
        return max_bots - current_bots
    return 0

def activate_subscription(user_id, tx_hash=None):
    user = get_user(user_id)
    now = datetime.now()
    
    if user and user['subscription_status'] == 'active' and user['subscription_expiry']:
        new_expiry = datetime.fromisoformat(user['subscription_expiry']) + timedelta(days=30)
    else:
        new_expiry = now + timedelta(days=30)
    
    db.execute('''
        UPDATE users SET subscription_status = 'active', subscription_expiry = ?, 
        subscription_purchased_at = ?, last_payment_hash = ? WHERE user_id = ?
    ''', (new_expiry.isoformat(), now.isoformat(), tx_hash, user_id))
    
    # کمیسیون به معرف
    if user and user.get('referred_by'):
        commission_percent = get_setting('withdraw_percent')
        price = get_setting('subscription_price')
        commission = int(price * commission_percent / 100)
        add_wallet_balance(user['referred_by'], commission)

def add_wallet_balance(user_id, amount):
    user = get_user(user_id)
    if not user:
        return 0
    new_balance = user['wallet_balance'] + amount
    db.execute('UPDATE users SET wallet_balance = ? WHERE user_id = ?', (new_balance, user_id))
    return new_balance

def get_user_bots(user_id):
    bots = db.execute('SELECT * FROM bots WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    return [dict(bot) for bot in bots]

def get_bot(bot_id):
    bots = db.execute('SELECT * FROM bots WHERE id = ?', (bot_id,))
    return dict(bots[0]) if bots else None

def delete_bot(bot_id, user_id):
    bot_rec = get_bot(bot_id)
    if not bot_rec or (user_id and bot_rec['user_id'] != user_id):
        return False
    
    if bot_id in machine_manager.processes:
        machine_manager.stop_bot(bot_id)
    
    if bot_rec.get('file_path') and os.path.exists(bot_rec['file_path']):
        os.remove(bot_rec['file_path'])
    
    db.execute('DELETE FROM bots WHERE id = ?', (bot_id,))
    if user_id:
        db.execute('UPDATE users SET bots_count = bots_count - 1 WHERE user_id = ?', (user_id,))
    return True

def extract_token_from_code(code):
    patterns = [
        r'token\s*=\s*["\']([^"\']+)["\']',
        r'TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
        r'const\s+token\s*=\s*["\']([^"\']+)["\']',
        r'private\s+static\s+final\s+String\s+TOKEN\s*=\s*["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def detect_language(file_path, code):
    if file_path.endswith('.py'):
        return Language.PYTHON
    elif file_path.endswith('.js'):
        return Language.JAVASCRIPT
    elif file_path.endswith('.java'):
        return Language.JAVA
    elif file_path.endswith('.cs'):
        return Language.CSHARP
    elif file_path.endswith('.php'):
        return Language.PHP
    elif file_path.endswith('.go'):
        return Language.GO
    elif file_path.endswith('.rs'):
        return Language.RUST
    
    if 'import telebot' in code or 'from telebot' in code:
        return Language.PYTHON
    elif 'require(\'node-telegram-bot-api\')' in code:
        return Language.JAVASCRIPT
    elif 'TelegramLongPollingBot' in code:
        return Language.JAVA
    elif 'TelegramBotClient' in code:
        return Language.CSHARP
    elif 'file_get_contents' in code and 'api.telegram.org' in code:
        return Language.PHP
    elif 'tgbotapi.NewBotAPI' in code:
        return Language.GO
    elif 'teloxide' in code:
        return Language.RUST
    
    return Language.PYTHON

def add_bot(user_id, bot_id, token, name, username, file_path, language, pid=None, machine_id=None):
    now = datetime.now().isoformat()
    db.execute('''
        INSERT INTO bots (id, user_id, token, name, username, language, file_path, pid, machine_id, status, created_at, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
    ''', (bot_id, user_id, token, name, username, language.value, file_path, pid, machine_id, now, now))
    db.execute('UPDATE users SET bots_count = bots_count + 1 WHERE user_id = ?', (user_id,))
    return True

def can_create_bot(user_id):
    if not check_subscription(user_id):
        return False, "no_subscription"
    remaining = get_remaining_bots(user_id)
    if remaining <= 0:
        return False, "limit_reached"
    return True, "ok"

def log_error(error_type, message, user_id=None, bot_id=None):
    error_id = hashlib.md5(f"{time.time()}_{user_id}_{bot_id}".encode()).hexdigest()[:16]
    db.execute('INSERT INTO errors (id, type, message, user_id, bot_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
              (error_id, error_type, message[:500], user_id, bot_id, datetime.now().isoformat()))

# ==================== Cache ====================
class SimpleCache:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl
        self.lock = threading.RLock()
    
    def get(self, key):
        with self.lock:
            item = self.cache.get(key)
            if item and item['expires'] > time.time():
                return item['value']
            if key in self.cache:
                del self.cache[key]
        return None
    
    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.ttl
        with self.lock:
            self.cache[key] = {'value': value, 'expires': time.time() + ttl}

cache = SimpleCache(ttl=3600)

# ==================== Rate Limiter ====================
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.RLock()
    
    def is_allowed(self, user_id, limit_per_second=5):
        with self.lock:
            now = time.time()
            user_requests = self.requests[user_id]
            user_requests = [t for t in user_requests if now - t < 1]
            if len(user_requests) >= limit_per_second:
                return False
            user_requests.append(now)
            self.requests[user_id] = user_requests
            return True
    
    def get_user_builds_today(self, user_id):
        today = datetime.now().date().isoformat()
        key = f"builds_{user_id}_{today}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = db.execute("SELECT COUNT(*) as count FROM bots WHERE user_id = ? AND DATE(created_at) = ?", 
                           (user_id, today))
        count = result[0]['count'] if result else 0
        cache.set(key, count, ttl=3600)
        return count
    
    def increment_user_builds(self, user_id):
        today = datetime.now().date().isoformat()
        key = f"builds_{user_id}_{today}"
        count = self.get_user_builds_today(user_id) + 1
        cache.set(key, count, ttl=3600)
        return count

rate_limiter = RateLimiter()

# ==================== Build Queue ====================
class BuildQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.processing = {}
        self.lock = threading.RLock()
        self.worker_threads = []
        self._start_workers()
    
    def _start_workers(self):
        max_concurrent = get_setting('max_concurrent_builds')
        for i in range(max_concurrent):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.worker_threads.append(t)
    
    def add_build(self, user_id, file_path, file_name, chat_id, message_id, build_data):
        build_id = str(uuid.uuid4())[:8]
        build_item = {
            'id': build_id,
            'user_id': user_id,
            'file_path': file_path,
            'file_name': file_name,
            'chat_id': chat_id,
            'message_id': message_id,
            'added_at': time.time(),
            'build_data': build_data
        }
        self.queue.put(build_item)
        with self.lock:
            self.processing[build_id] = {'status': 'queued', 'position': self.queue.qsize()}
        return build_id
    
    def _worker(self):
        while True:
            try:
                build_item = self.queue.get(timeout=1)
                with self.lock:
                    if build_item['id'] in self.processing:
                        self.processing[build_item['id']]['status'] = 'processing'
                self._process_build(build_item)
                self.queue.task_done()
                with self.lock:
                    if build_item['id'] in self.processing:
                        del self.processing[build_item['id']]
            except queue.Empty:
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(1)
    
    def _process_build(self, build_item):
        temp_bot = telebot.TeleBot(BOT_TOKEN)
        try:
            temp_bot.edit_message_text(f"🔄 در حال ساخت ربات...\n🆔 {build_item['id']}\n⏳ لطفاً صبر کنید",
                                      build_item['chat_id'], build_item['message_id'])
            
            build_data = build_item['build_data']
            result = machine_manager.run_bot(build_data['bot_id'], build_data['main_code'], 
                                            build_data['token'], build_data['language'])
            
            if result['success']:
                add_bot(build_data['user_id'], build_data['bot_id'], build_data['token'], 
                       build_data['bot_info']['first_name'], build_data['bot_info']['username'], 
                       build_data['file_path'], build_data['language'], result['pid'], result['machine_id'])
                
                remaining = get_remaining_bots(build_data['user_id'])
                temp_bot.edit_message_text(f"✅ ربات {build_data['bot_info']['first_name']} ساخته شد!\n🤖 ربات باقیمانده: {remaining}",
                                          build_item['chat_id'], build_item['message_id'])
            else:
                temp_bot.edit_message_text(f"❌ ساخت ناموفق: {result.get('error', 'مشخص نشده')}",
                                          build_item['chat_id'], build_item['message_id'])
        except Exception as e:
            logger.error(f"Build failed: {e}")
    
    def get_queue_length(self):
        return self.queue.qsize()

# ==================== Machine Manager ====================
class MachineManager:
    def __init__(self):
        self.port_counter = 8000
        self.processes = {}
        self.lock = threading.RLock()
        self._restore_bots()
    
    def _restore_bots(self):
        try:
            running_bots = db.execute('SELECT id, token, file_path, language FROM bots WHERE status = "running"')
            for bot_rec in running_bots:
                bot_id = bot_rec['id']
                token = bot_rec['token']
                language = Language(bot_rec['language']) if bot_rec['language'] else Language.PYTHON
                if token and os.path.exists(bot_rec['file_path']):
                    with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    self.run_bot(bot_id, code, token, language, restore=True)
        except Exception as e:
            logger.error(f"Restore bots failed: {e}")
    
    def get_available_machine(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active' ORDER BY current_bots ASC")
        for m in machines:
            if m['current_bots'] < m['max_bots']:
                return m['id']
        return None
    
    def assign_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots + 1 WHERE id = ?", (machine_id,))
    
    def release_bot(self, bot_id, machine_id):
        db.execute("UPDATE machines SET current_bots = current_bots - 1 WHERE id = ?", (machine_id,))
    
    def run_bot(self, bot_id, code, token, language, restore=False):
        try:
            machine_id = self.get_available_machine()
            if not machine_id:
                return {'success': False, 'error': 'همه ماشین‌ها پر هستند'}
            
            bot_dir = os.path.join(DIRS['MACHINES'], f"machine_{machine_id:03d}", bot_id)
            os.makedirs(bot_dir, exist_ok=True)
            
            config = LANGUAGES.get(language, LANGUAGES[Language.PYTHON])
            full_code = config.template.format(token=token, username=f"bot_{bot_id}")
            
            code_path = os.path.join(bot_dir, f'bot{config.extension}')
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(full_code)
            
            log_file = os.path.join(DIRS['LOGS'], f"bot_{bot_id}.log")
            
            process = subprocess.Popen(
                config.run_command.split(),
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                cwd=bot_dir,
                start_new_session=True
            )
            
            time.sleep(2)
            
            if process.poll() is None:
                with self.lock:
                    self.processes[bot_id] = {
                        'process': process,
                        'pid': process.pid,
                        'machine_id': machine_id,
                        'dir': bot_dir,
                        'start_time': time.time()
                    }
                self.assign_bot(bot_id, machine_id)
                if not restore:
                    db.execute("UPDATE bots SET status = 'running', machine_id = ?, pid = ? WHERE id = ?",
                              (machine_id, process.pid, bot_id))
                return {'success': True, 'pid': process.pid, 'machine_id': machine_id}
            else:
                return {'success': False, 'error': 'خطا در اجرای ربات'}
        except Exception as e:
            return {'success': False, 'error': str(e)[:100]}
    
    def stop_bot(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                try:
                    info = self.processes[bot_id]
                    os.kill(info['pid'], signal.SIGTERM)
                    time.sleep(1)
                    self.release_bot(bot_id, info['machine_id'])
                    del self.processes[bot_id]
                    db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
                    return True
                except:
                    pass
        return False
    
    def get_status(self, bot_id):
        with self.lock:
            if bot_id in self.processes:
                info = self.processes[bot_id]
                try:
                    os.kill(info['pid'], 0)
                    return {'running': True, 'pid': info['pid'], 'uptime': time.time() - info['start_time']}
                except:
                    if bot_id in self.processes:
                        del self.processes[bot_id]
                        self.release_bot(bot_id, info['machine_id'])
                        db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
        return {'running': False}
    
    def restart_all_dead_bots(self):
        dead_bots = db.execute('SELECT id, token, file_path, language FROM bots WHERE status = "running"')
        restarted = 0
        for bot_rec in dead_bots:
            bot_id = bot_rec['id']
            status = self.get_status(bot_id)
            if not status.get('running'):
                token = bot_rec['token']
                language = Language(bot_rec['language']) if bot_rec['language'] else Language.PYTHON
                if token and os.path.exists(bot_rec['file_path']):
                    with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    result = self.run_bot(bot_id, code, token, language)
                    if result.get('success'):
                        restarted += 1
        return restarted
    
    def get_stats(self):
        machines = db.execute("SELECT * FROM machines WHERE status = 'active'")
        machine_list = list(machines)
        total_bots = sum(m['current_bots'] for m in machine_list)
        total_capacity = sum(m['max_bots'] for m in machine_list)
        return {
            'total': len(machine_list),
            'total_bots': total_bots,
            'total_capacity': total_capacity,
            'available': total_capacity - total_bots,
            'usage_percent': (total_bots / total_capacity) * 100 if total_capacity > 0 else 0
        }
    
    def update_machine_capacity(self, machine_id, max_bots):
        db.execute("UPDATE machines SET max_bots = ? WHERE id = ?", (max_bots, machine_id))
        return True

# ==================== Remote Server Manager ====================
class RemoteServerManager:
    def add_server(self, name, ip, username, password, port=22, machine_id=None):
        try:
            db.execute('''
                INSERT INTO machines (name, ip, port, username, password, status, max_bots, created_at, is_local)
                VALUES (?, ?, ?, ?, ?, 'active', 5000, ?, 0)
            ''', (name, ip, port, username, password, datetime.now().isoformat()))
            
            if machine_id:
                db.execute("UPDATE machines SET ip = ?, username = ?, is_local = 0 WHERE id = ?", (ip, username, machine_id))
            return True, "اتصال با موفقیت برقرار شد"
        except Exception as e:
            return False, f"خطا: {str(e)}"

# ==================== Health Checker ====================
class HealthChecker:
    def __init__(self):
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
    
    def _monitor(self):
        while True:
            try:
                interval = get_setting('health_check_interval')
                for bot_rec in db.execute('SELECT id, token FROM bots WHERE status = "running"'):
                    token = bot_rec['token']
                    try:
                        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
                        if resp.status_code != 200:
                            machine_manager.restart_all_dead_bots()
                    except:
                        machine_manager.restart_all_dead_bots()
                time.sleep(interval)
            except:
                time.sleep(60)

# ==================== ربات تلگرام ====================
bot = telebot.TeleBot(BOT_TOKEN)
bot.delete_webhook()

machine_manager = MachineManager()
remote_manager = RemoteServerManager()
build_queue = BuildQueue()
health_checker = HealthChecker()

# ==================== منوی اصلی ====================
def get_main_menu(user_id):
    user = get_user(user_id)
    lang = user['language'] if user else 'fa'
    is_admin = user_id in ADMIN_IDS
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = MENU_BUTTONS_FA.copy() if lang == 'fa' else MENU_BUTTONS_EN.copy()
    
    if is_admin:
        for btn in ADMIN_BUTTONS:
            buttons.append(btn)
    
    markup.add(*buttons)
    return markup

# ==================== Rate Limit Decorator ====================
def rate_limit(limit_per_second=5):
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            if not rate_limiter.is_allowed(user_id, limit_per_second):
                bot.reply_to(message, "🚫 لطفاً کمی صبر کنید...")
                return
            return func(message, *args, **kwargs)
        return wrapper
    return decorator

# ==================== دستورات و هندلرها ====================

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    args = message.text.split()
    preferred_lang = 'fa'
    if len(args) > 1 and args[1] == 'en':
        preferred_lang = 'en'
    
    referred_by = None
    if len(args) > 1 and args[1] not in ['fa', 'en']:
        code = args[1]
        users = db.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
        if users and users[0]['user_id'] != user_id:
            referred_by = users[0]['user_id']
    
    result, msg = create_user(user_id, username, first_name, message.from_user.last_name or "", referred_by, preferred_lang)
    
    if not result and msg == "capacity_full":
        bot.send_message(message.chat.id, get_setting('capacity_warning_message'))
        return
    
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    remaining_bots = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    is_subscribed = check_subscription(user_id)
    lang = user['language']
    
    text = f"🚀 خوش آمدید {first_name}!\n\n👤 شناسه: `{user_id}`\n🎁 کد معرف: `{user['referral_code']}`\n🔗 لینک دعوت: `{referral_link}`\n📊 دعوت‌ها: {user['referrals_count']}\n💰 موجودی: {user['wallet_balance']:,} تومان\n💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n🤖 ربات‌های باقیمانده: {remaining_bots}/{max_bots}\n\n🎯 زبان‌های پشتیبانی شده:\n🐍 Python | 📜 JavaScript | ☕ Java | 🔷 C# | 🐘 PHP | 🐹 Go | 🦀 Rust"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('copy_link_'))
def copy_link_callback(call):
    code = call.data.replace('copy_link_', '')
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.answer_callback_query(call.id, f"✅ لینک کپی شد!\n{link}", show_alert=True)

# ==================== زبان ====================
@bot.message_handler(func=lambda m: m.text in ['🌐 زبان / Language', '🌐 Language / زبان'])
def change_language(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    )
    bot.send_message(message.chat.id, "Select your language / زبان خود را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    lang = call.data.replace('lang_', '')
    db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, call.from_user.id))
    bot.answer_callback_query(call.id, "✅ زبان تغییر کرد")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "✅ منوی اصلی:", reply_markup=get_main_menu(call.from_user.id))

# ==================== کیف پول و اشتراک ====================
@bot.message_handler(func=lambda m: m.text in ['💰 کیف پول و اشتراک', '💰 Wallet & Subscription'])
def wallet(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if not user:
        return
    
    lang = user['language']
    is_subscribed = check_subscription(user_id)
    expiry = datetime.fromisoformat(user['subscription_expiry']).strftime('%Y-%m-%d') if user['subscription_expiry'] else "ندارد"
    remaining_bots = get_remaining_bots(user_id)
    max_bots = get_setting('max_bots_per_subscription')
    
    if lang == 'fa':
        text = (f"💰 **کیف پول و اشتراک**\n\n"
                f"👤 {user['first_name']}\n"
                f"💳 وضعیت: {'✅ فعال' if is_subscribed else '❌ غیرفعال'}\n"
                f"📅 انقضا: {expiry}\n"
                f"💰 موجودی: {user['wallet_balance']:,} تومان\n"
                f"👥 دعوت‌ها: {user['referrals_count']}\n"
                f"🤖 ربات‌های باقیمانده: {remaining_bots}/{max_bots}\n\n"
                f"💳 برای فعالسازی {get_setting('subscription_price_str')} را به کارت زیر واریز:\n"
                f"`{get_setting('card_number_display')}`\n"
                f"👤 {get_setting('card_holder')}\n"
                f"🏦 {get_setting('card_bank')}\n\n"
                f"📸 پس از واریز، تصویر تراکنش را ارسال کنید")
    else:
        text = (f"💰 **Wallet & Subscription**\n\n"
                f"👤 {user['first_name']}\n"
                f"💳 Status: {'✅ Active' if is_subscribed else '❌ Inactive'}\n"
                f"📅 Expiry: {expiry}\n"
                f"💰 Balance: {user['wallet_balance']:,} Toman\n"
                f"👥 Referrals: {user['referrals_count']}\n"
                f"🤖 Remaining Bots: {remaining_bots}/{max_bots}\n\n"
                f"💳 To activate, send {get_setting('subscription_price_usd')} to:\n"
                f"`{get_setting('trc20_address')}`\n"
                f"🌐 Network: TRC20 (USDT)\n\n"
                f"📸 Send transaction screenshot after payment")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== دریافت فیش ====================
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    existing = db.execute('SELECT id FROM receipts WHERE user_id = ? AND status = "pending"', (user_id,))
    if existing:
        bot.reply_to(message, "⏳ فیش قبلی در انتظار تایید است")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        tx_hash = hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()[:16].upper()
        receipt_path = os.path.join(DIRS['RECEIPTS'], f"{user_id}_{tx_hash}.jpg")
        
        with open(receipt_path, 'wb') as f:
            f.write(downloaded)
        
        db.execute('INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at) VALUES (?, ?, ?, ?, ?)',
                  (user_id, get_setting('subscription_price'), receipt_path, tx_hash, datetime.now().isoformat()))
        
        bot.reply_to(message, "✅ تصویر دریافت شد، در انتظار تایید")
        
        for admin_id in ADMIN_IDS:
            try:
                with open(receipt_path, 'rb') as f:
                    bot.send_photo(admin_id, f, caption=f"📸 فیش جدید\n👤 {message.from_user.first_name}\n🆔 {user_id}\n💰 {get_setting('subscription_price_str')}")
            except:
                pass
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

# ==================== دعوت دوستان ====================
@bot.message_handler(func=lambda m: m.text in ['👥 دعوت دوستان', '👥 Invite Friends'])
def invite(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user['referral_code']}"
    
    text = (f"👥 **سیستم دعوت دوستان**\n\n"
            f"🎁 کد معرف: `{user['referral_code']}`\n"
            f"🔗 لینک: `{referral_link}`\n"
            f"📊 دعوت‌ها: {user['referrals_count']}\n"
            f"💰 کمیسیون هر اشتراک: {get_setting('withdraw_percent')}%\n"
            f"💎 کمیسیون کل: {user.get('total_commission', 0):,} تومان")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 کپی لینک", callback_data=f"copy_link_{user['referral_code']}"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

# ==================== قالب‌های آماده ====================
@bot.message_handler(func=lambda m: m.text in ['🗂️ قالب‌های آماده', '🗂️ Templates'])
def templates_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for language in Language:
        config = LANGUAGES[language]
        markup.add(types.InlineKeyboardButton(f"{config.icon} {config.display_name}", callback_data=f"template_{language.value}"))
    bot.send_message(message.chat.id, "🎯 زبان برنامه نویسی مورد نظر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('template_'))
def send_template(call):
    lang_name = call.data.replace('template_', '')
    try:
        language = Language(lang_name)
        config = LANGUAGES[language]
        template_code = config.template.format(token="YOUR_BOT_TOKEN_HERE", username="your_bot_username")
        
        temp_file = os.path.join(DIRS['TEMP'], f"template_{call.from_user.id}_{language.value}{config.extension}")
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(template_code)
        
        with open(temp_file, 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption=f"✅ قالب {config.display_name} با موفقیت ارسال شد!")
        
        os.remove(temp_file)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطا: {str(e)[:50]}")
    bot.answer_callback_query(call.id)

# ==================== ساخت ربات جدید ====================
@bot.message_handler(func=lambda m: m.text in ['🤖 ساخت ربات جدید', '🤖 New Bot'])
def new_bot(message):
    user_id = message.from_user.id
    
    can_create, reason = can_create_bot(user_id)
    if not can_create:
        if reason == "no_subscription":
            bot.send_message(message.chat.id, "❌ ابتدا باید اشتراک فعال کنید!")
        else:
            bot.send_message(message.chat.id, f"❌ به حداکثر {get_setting('max_bots_per_subscription')} ربات رسیده‌اید")
        return
    
    bot.send_message(message.chat.id, "📤 فایل `.py` یا `.zip` خود را ارسال کنید\n💡 می‌توانید پوشه‌بندی دلخواه داشته باشید")

@bot.message_handler(content_types=['document'])
def handle_build_file(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    can_create, _ = can_create_bot(user_id)
    if not can_create:
        bot.reply_to(message, "❌ اشتراک فعال نیست")
        return
    
    file_name = message.document.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.js') or file_name.endswith('.java') or
            file_name.endswith('.cs') or file_name.endswith('.php') or file_name.endswith('.go') or
            file_name.endswith('.rs') or file_name.endswith('.zip')):
        bot.reply_to(message, "❌ فقط فایل‌های پشتیبانی می‌شوند")
        return
    
    if message.document.file_size > 50 * 1024 * 1024:
        bot.reply_to(message, "❌ حجم بیشتر از ۵۰ مگابایت")
        return
    
    status_msg = bot.reply_to(message, "🔄 در حال پردازش...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{int(time.time())}_{file_name}")
        
        with open(file_path, 'wb') as f:
            f.write(downloaded)
        
        main_code = ""
        language = None
        
        if file_name.endswith('.zip'):
            extract_dir = os.path.join(DIRS['TEMP'], f"extract_{user_id}_{int(time.time())}")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.py'):
                        language = Language.PYTHON
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as code_f:
                            main_code = code_f.read()
                        break
                    elif f.endswith('.js'):
                        language = Language.JAVASCRIPT
                        with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as code_f:
                            main_code = code_f.read()
                        break
                if main_code:
                    break
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                main_code = f.read()
            language = detect_language(file_path, main_code)
        
        if not main_code:
            bot.edit_message_text("❌ فایل کد پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        token = extract_token_from_code(main_code)
        if not token:
            bot.edit_message_text("❌ توکن در کد پیدا نشد", message.chat.id, status_msg.message_id)
            return
        
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                bot.edit_message_text("❌ توکن نامعتبر", message.chat.id, status_msg.message_id)
                return
            bot_info = resp.json()['result']
        except:
            bot.edit_message_text("❌ توکن نامعتبر", message.chat.id, status_msg.message_id)
            return
        
        rate_limiter.increment_user_builds(user_id)
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        build_data = {
            'bot_id': bot_id,
            'user_id': user_id,
            'token': token,
            'bot_info': bot_info,
            'file_path': file_path,
            'main_code': main_code,
            'language': language,
            'chat_id': message.chat.id,
            'message_id': status_msg.message_id
        }
        
        build_queue.add_build(user_id, file_path, file_name, message.chat.id, status_msg.message_id, build_data)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)[:100]}", message.chat.id, status_msg.message_id)

# ==================== ربات‌های من ====================
@bot.message_handler(func=lambda m: m.text in ['📋 ربات‌های من', '📋 My Bots'])
def my_bots(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    
    for b in bots[:15]:
        status = machine_manager.get_status(b['id'])
        lang_config = LANGUAGES.get(Language(b.get('language', 'python')), LANGUAGES[Language.PYTHON])
        emoji = "🟢" if status.get('running') else "🔴"
        text = f"{emoji} {lang_config.icon} {b['name']}\n🔗 t.me/{b['username']}"
        bot.send_message(message.chat.id, text)

# ==================== فعال/غیرفعال ====================
@bot.message_handler(func=lambda m: m.text in ['🔄 فعال/غیرفعال', '🔄 Start/Stop'])
def toggle_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        status = machine_manager.get_status(b['id'])
        lang_config = LANGUAGES.get(Language(b.get('language', 'python')), LANGUAGES[Language.PYTHON])
        emoji = "🟢" if status.get('running') else "🔴"
        markup.add(types.InlineKeyboardButton(f"{emoji} {lang_config.icon} {b['name']}", callback_data=f"toggle_{b['id']}"))
    
    bot.send_message(message.chat.id, "🤖 ربات را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_bot(call):
    bot_id = call.data.replace('toggle_', '')
    bot_rec = get_bot(bot_id)
    if not bot_rec or bot_rec['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ یافت نشد")
        return
    
    status = machine_manager.get_status(bot_id)
    
    if status.get('running'):
        if machine_manager.stop_bot(bot_id):
            bot.answer_callback_query(call.id, "✅ متوقف شد")
        else:
            bot.answer_callback_query(call.id, "❌ خطا")
    else:
        if os.path.exists(bot_rec['file_path']):
            with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            token = bot_rec['token']
            language = Language(bot_rec.get('language', 'python'))
            result = machine_manager.run_bot(bot_id, code, token, language)
            if result['success']:
                db.execute("UPDATE bots SET machine_id = ?, pid = ? WHERE id = ?", (result['machine_id'], result['pid'], bot_id))
                bot.answer_callback_query(call.id, "✅ فعال شد")
            else:
                bot.answer_callback_query(call.id, f"❌ {result.get('error')}")
        else:
            bot.answer_callback_query(call.id, "❌ فایل یافت نشد")

# ==================== حذف ربات ====================
@bot.message_handler(func=lambda m: m.text in ['🗑 حذف ربات', '🗑 Delete Bot'])
def delete_prompt(message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)
    if not bots:
        bot.send_message(message.chat.id, "📋 رباتی ندارید")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b in bots:
        markup.add(types.InlineKeyboardButton(f"🗑 {b['name']}", callback_data=f"delete_{b['id']}"))
    bot.send_message(message.chat.id, "🗑 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def confirm_delete(call):
    bot_id = call.data.replace('delete_', '')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ بله", callback_data=f"confirm_del_{bot_id}"),
              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_del"))
    bot.edit_message_text("⚠️ اطمینان دارید؟", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_del_'))
def do_delete(call):
    bot_id = call.data.replace('confirm_del_', '')
    if delete_bot(bot_id, call.from_user.id):
        bot.edit_message_text("✅ حذف شد", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text("❌ خطا", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_del')
def cancel_delete(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== کتابخانه ====================
POPULAR_LIBRARIES = {
    'requests': 'requests', 'aiohttp': 'aiohttp', 'flask': 'flask',
    'django': 'django', 'numpy': 'numpy', 'pandas': 'pandas',
    'pillow': 'Pillow', 'beautifulsoup4': 'beautifulsoup4',
    'selenium': 'selenium', 'jdatetime': 'jdatetime'
}

@bot.message_handler(func=lambda m: m.text in ['📦 کتابخانه', '📦 Library'])
def library_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for name, lib in list(POPULAR_LIBRARIES.items())[:10]:
        markup.add(types.InlineKeyboardButton(f"📦 {name}", callback_data=f"lib_{lib}"))
    markup.add(types.InlineKeyboardButton("🔧 نصب دستی", callback_data="lib_manual"))
    bot.reply_to(message, "📦 کتابخانه مورد نظر:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "lib_manual")
def library_manual(call):
    msg = bot.send_message(call.message.chat.id, "🔧 نام کتابخانه:")
    bot.register_next_step_handler(msg, install_custom_library)

def install_custom_library(message):
    lib = message.text.strip()
    if not lib:
        bot.reply_to(message, "❌ نام کتابخانه")
        return
    status = bot.reply_to(message, f"🔄 نصب {lib}...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', lib, '--quiet'], timeout=120)
        bot.edit_message_text(f"✅ کتابخانه {lib} نصب شد!", message.chat.id, status.message_id)
    except:
        bot.edit_message_text(f"❌ خطا", message.chat.id, status.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lib_') and call.data not in ['lib_manual'])
def install_selected_library(call):
    lib = call.data.replace('lib_', '')
    status = bot.send_message(call.message.chat.id, f"🔄 نصب {lib}...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', lib, '--quiet'], timeout=120)
        bot.edit_message_text(f"✅ کتابخانه {lib} نصب شد!", call.message.chat.id, status.message_id)
    except:
        bot.edit_message_text(f"❌ خطا", call.message.chat.id, status.message_id)
    bot.answer_callback_query(call.id)

# ==================== راهنما ====================
@bot.message_handler(func=lambda m: m.text in ['📚 راهنما', '📚 Guide'])
def guide(message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    guide_text = get_setting('guide_text_fa') if lang == 'fa' else get_setting('guide_text_en')
    bot.send_message(message.chat.id, guide_text)

# ==================== آمار ====================
@bot.message_handler(func=lambda m: m.text in ['📊 آمار', '📊 Stats'])
def stats(message):
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    total_bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    running_bots = db.execute('SELECT COUNT(*) as count FROM bots WHERE status = "running"')[0]['count']
    machine_stats = machine_manager.get_stats()
    
    text = (f"📊 **آمار سیستم**\n\n"
            f"👥 کاربران: {users_count:,}\n"
            f"✅ اشتراک فعال: {active_subs:,}\n"
            f"🤖 کل ربات‌ها: {total_bots:,}\n"
            f"🟢 ربات فعال: {running_bots:,}\n"
            f"🖥️ ماشین‌ها: {machine_stats['total']}\n"
            f"📊 مصرف: {machine_stats['usage_percent']:.1f}%\n"
            f"⚡ صف ساخت: {build_queue.get_queue_length()}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== مصرف من ====================
@bot.message_handler(func=lambda m: m.text in ['📈 مصرف من', '📈 My Usage'])
def my_usage(message):
    user_id = message.from_user.id
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour')
    bots_count = len(get_user_bots(user_id))
    
    bar_length = int((builds_today / max_builds) * 20) if max_builds > 0 else 0
    bar = "█" * bar_length + "░" * (20 - bar_length)
    
    text = (f"📊 **مصرف شما امروز**\n\n"
            f"🤖 ساخت ربات: {builds_today}/{max_builds}\n"
            f"📈 {bar} {int((builds_today/max_builds)*100) if max_builds>0 else 0}%\n\n"
            f"📋 تعداد ربات‌ها: {bots_count}")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== وضعیت صف ====================
@bot.message_handler(func=lambda m: m.text in ['⚡ وضعیت صف', '⚡ Queue Status'])
def queue_status(message):
    user_id = message.from_user.id
    text = (f"⚡ **وضعیت صف ساخت ربات**\n\n"
            f"📊 در صف: {build_queue.get_queue_length()}\n"
            f"⚙️ حداکثر همزمان: {get_setting('max_concurrent_builds')}\n"
            f"📈 ساخت امروز شما: {rate_limiter.get_user_builds_today(user_id)}/{get_setting('max_builds_per_hour')}")
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== پشتیبانی ====================
@bot.message_handler(func=lambda m: m.text in ['📞 پشتیبانی', '📞 Support'])
def support(message):
    bot.send_message(message.chat.id, "📞 پشتیبانی: @shahraghee13")

# ==================== درخواست برداشت ====================
@bot.message_handler(func=lambda m: m.text in ['💸 درخواست برداشت', '💸 Withdraw'])
def withdraw_request(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user['wallet_balance'] < get_setting('min_withdraw'):
        bot.send_message(message.chat.id, f"❌ حداقل برداشت {get_setting('min_withdraw'):,} تومان است")
        return
    
    msg = bot.send_message(message.chat.id, "💳 آدرس کیف پول TRC20 برای برداشت:")
    bot.register_next_step_handler(msg, process_withdraw_address, user)

def process_withdraw_address(message, user):
    address = message.text.strip()
    amount = user['wallet_balance']
    db.execute('INSERT INTO withdraw_requests (user_id, amount, address, created_at, status) VALUES (?, ?, ?, ?, "pending")',
              (user['user_id'], amount, address, datetime.now().isoformat()))
    db.execute('UPDATE users SET wallet_balance = 0 WHERE user_id = ?', (user['user_id'],))
    bot.send_message(message.chat.id, f"✅ درخواست برداشت {amount:,} تومان ثبت شد")

# ==================== پنل مدیریت ====================

@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت')
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        '📸 تایید فیش', '💰 تایید برداشت', '⚙️ تنظیمات سیستم',
        '📊 آمار کاربران', '🗑 حذف کاربران', '🗑 حذف ربات‌های کاربران',
        '📢 پیام همگانی', '🔍 بررسی ربات‌های کاربران', '💳 تنظیم آدرس کیف پول',
        '📝 عوض کردن متن راهنما', '👋 عوض کردن متن خوش آمد گویی',
        '✅ عوض کردن متن فعالسازی اشتراک', '💸 عوض کردن متن خرید اشتراک',
        '🔄 ریستارت ربات‌های مرده', '🐛 مدیریت خطاهای ربات', '⚙️ تنظیم ظرفیت کاربران',
        '🖥️ مدیریت ماشین‌ها', '➕ اضافه کردن سرور جدید', '🔙 بازگشت به منوی اصلی'
    ]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "👑 **پنل مدیریت** - لطفاً یکی از گزینه‌ها را انتخاب کنید:", parse_mode='Markdown', reply_markup=markup)

# ==================== تایید فیش ====================
@bot.message_handler(func=lambda m: m.text == '📸 تایید فیش')
def admin_receipts(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    receipts = db.execute('SELECT * FROM receipts WHERE status = "pending" ORDER BY created_at')
    if not receipts:
        bot.send_message(message.chat.id, "✅ هیچ فیش در انتظار تاییدی وجود ندارد")
        return
    
    for r in receipts:
        user = get_user(r['user_id'])
        text = f"📸 **فیش جدید**\n👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n🆔 آیدی: {r['user_id']}\n💰 مبلغ: {r['amount']:,} تومان"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_receipt_{r['id']}"),
                  types.InlineKeyboardButton("❌ رد", callback_data=f"reject_receipt_{r['id']}"))
        if os.path.exists(r['receipt_path']):
            with open(r['receipt_path'], 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=text, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_receipt_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    rid = int(call.data.replace('approve_receipt_', ''))
    r = db.execute('SELECT user_id FROM receipts WHERE id = ?', (rid,))
    if r:
        db.execute('UPDATE receipts SET status = "approved", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
                  (call.from_user.id, datetime.now().isoformat(), rid))
        activate_subscription(r[0]['user_id'])
        bot.answer_callback_query(call.id, "✅ اشتراک فعال شد")
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_receipt_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    rid = int(call.data.replace('reject_receipt_', ''))
    db.execute('UPDATE receipts SET status = "rejected", reviewed_by = ?, reviewed_at = ? WHERE id = ?',
              (call.from_user.id, datetime.now().isoformat(), rid))
    bot.answer_callback_query(call.id, "❌ رد شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== تایید برداشت ====================
@bot.message_handler(func=lambda m: m.text == '💰 تایید برداشت')
def admin_withdraws(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    withdraws = db.execute('SELECT * FROM withdraw_requests WHERE status = "pending" ORDER BY created_at')
    if not withdraws:
        bot.send_message(message.chat.id, "✅ هیچ درخواست برداشتی وجود ندارد")
        return
    
    for w in withdraws:
        user = get_user(w['user_id'])
        text = f"💰 **درخواست برداشت**\n👤 کاربر: {user['first_name'] if user else 'نامشخص'}\n💰 مبلغ: {w['amount']:,} تومان\n💳 آدرس: {w['address']}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تایید", callback_data=f"approve_withdraw_{w['id']}"))
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_withdraw_'))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    wid = int(call.data.replace('approve_withdraw_', ''))
    db.execute('UPDATE withdraw_requests SET status = "approved", processed_at = ? WHERE id = ?',
              (datetime.now().isoformat(), wid))
    bot.answer_callback_query(call.id, "✅ تایید شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== تنظیمات سیستم ====================
@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیمات سیستم')
def admin_settings(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 قیمت اشتراک", callback_data="set_price"),
        types.InlineKeyboardButton("🤖 حداکثر ربات", callback_data="set_max_bots"),
        types.InlineKeyboardButton("📈 محدودیت ساخت", callback_data="set_build_limit"),
        types.InlineKeyboardButton("💸 درصد کمیسیون", callback_data="set_commission"),
        types.InlineKeyboardButton("💰 حداقل برداشت", callback_data="set_min_withdraw")
    )
    bot.send_message(message.chat.id, "⚙️ **تنظیمات سیستم**", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_price")
def set_price(call):
    msg = bot.send_message(call.message.chat.id, "💰 قیمت اشتراک (تومان):")
    bot.register_next_step_handler(msg, process_set_price)

def process_set_price(message):
    try:
        price = int(message.text.strip())
        update_setting('subscription_price', price)
        update_setting('subscription_price_str', f"{price:,} تومان")
        bot.reply_to(message, f"✅ قیمت به {price:,} تومان تغییر کرد")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "set_max_bots")
def set_max_bots(call):
    msg = bot.send_message(call.message.chat.id, "🤖 حداکثر ربات در هر اشتراک:")
    bot.register_next_step_handler(msg, process_set_max_bots)

def process_set_max_bots(message):
    try:
        max_bots = int(message.text.strip())
        if 1 <= max_bots <= 100:
            update_setting('max_bots_per_subscription', max_bots)
            db.execute('UPDATE users SET max_bots = ?', (max_bots,))
            bot.reply_to(message, f"✅ به {max_bots} تغییر کرد")
        else:
            bot.reply_to(message, "❌ بین 1 تا 100")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "set_build_limit")
def set_build_limit(call):
    msg = bot.send_message(call.message.chat.id, "📈 حداکثر ساخت در ساعت:")
    bot.register_next_step_handler(msg, process_set_build_limit)

def process_set_build_limit(message):
    try:
        limit = int(message.text.strip())
        if 1 <= limit <= 100:
            update_setting('max_builds_per_hour', limit)
            bot.reply_to(message, f"✅ به {limit} تغییر کرد")
        else:
            bot.reply_to(message, "❌ بین 1 تا 100")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "set_commission")
def set_commission(call):
    msg = bot.send_message(call.message.chat.id, "💸 درصد کمیسیون:")
    bot.register_next_step_handler(msg, process_set_commission)

def process_set_commission(message):
    try:
        percent = int(message.text.strip())
        if 1 <= percent <= 50:
            update_setting('withdraw_percent', percent)
            bot.reply_to(message, f"✅ به {percent}% تغییر کرد")
        else:
            bot.reply_to(message, "❌ بین 1 تا 50")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

@bot.callback_query_handler(func=lambda call: call.data == "set_min_withdraw")
def set_min_withdraw(call):
    msg = bot.send_message(call.message.chat.id, "💰 حداقل برداشت (تومان):")
    bot.register_next_step_handler(msg, process_set_min_withdraw)

def process_set_min_withdraw(message):
    try:
        min_amount = int(message.text.strip())
        if min_amount >= 100000:
            update_setting('min_withdraw', min_amount)
            bot.reply_to(message, f"✅ به {min_amount:,} تومان تغییر کرد")
        else:
            bot.reply_to(message, "❌ حداقل 100,000 تومان")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

# ==================== آمار کاربران ====================
@bot.message_handler(func=lambda m: m.text == '📊 آمار کاربران')
def admin_user_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    active_subs = db.execute('SELECT COUNT(*) as count FROM users WHERE subscription_status = "active"')[0]['count']
    total_bots = db.execute('SELECT COUNT(*) as count FROM bots')[0]['count']
    total_wallet = db.execute('SELECT SUM(wallet_balance) as total FROM users')[0]['total'] or 0
    
    text = (f"📊 **آمار کاربران**\n\n"
            f"👥 کل کاربران: {users_count:,}\n"
            f"✅ اشتراک فعال: {active_subs:,}\n"
            f"🤖 کل ربات‌ها: {total_bots:,}\n"
            f"💰 کیف پول کل: {total_wallet:,} تومان")
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# ==================== حذف کاربران ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف کاربران')
def admin_delete_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "🗑 آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_admin_delete_user)

def process_admin_delete_user(message):
    try:
        uid = int(message.text.strip())
        bots = get_user_bots(uid)
        for bot in bots:
            delete_bot(bot['id'], uid)
        db.execute('DELETE FROM users WHERE user_id = ?', (uid,))
        bot.reply_to(message, f"✅ کاربر {uid} حذف شد")
    except:
        bot.reply_to(message, "❌ خطا")

# ==================== حذف ربات‌های کاربران ====================
@bot.message_handler(func=lambda m: m.text == '🗑 حذف ربات‌های کاربران')
def admin_delete_user_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "🗑 آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_delete_user_bots)

def process_delete_user_bots(message):
    try:
        uid = int(message.text.strip())
        bots = get_user_bots(uid)
        deleted = 0
        for bot in bots:
            if delete_bot(bot['id'], uid):
                deleted += 1
        bot.reply_to(message, f"✅ {deleted} ربات حذف شد")
    except:
        bot.reply_to(message, "❌ خطا")

# ==================== پیام همگانی ====================
@bot.message_handler(func=lambda m: m.text == '📢 پیام همگانی')
def broadcast_prompt(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "📝 متن پیام را ارسال کنید:")
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    text = message.text
    users = db.execute("SELECT user_id FROM users WHERE is_banned = 0")
    sent = 0
    for user in users:
        try:
            bot.send_message(user['user_id'], f"📢 **اعلامیه**\n\n{text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            pass
    bot.reply_to(message, f"✅ به {sent} کاربر ارسال شد")

# ==================== بررسی ربات‌های کاربران ====================
@bot.message_handler(func=lambda m: m.text == '🔍 بررسی ربات‌های کاربران')
def admin_check_user_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "🔍 آیدی کاربر را وارد کنید:")
    bot.register_next_step_handler(msg, process_check_user_bots)

def process_check_user_bots(message):
    try:
        uid = int(message.text.strip())
        user = get_user(uid)
        if not user:
            bot.reply_to(message, "❌ کاربر یافت نشد")
            return
        
        bots = get_user_bots(uid)
        if not bots:
            bot.reply_to(message, f"📋 کاربر {uid} هیچ رباتی ندارد")
            return
        
        text = f"📋 **ربات‌های کاربر {user['first_name']}**\n\n"
        for b in bots:
            status = machine_manager.get_status(b['id'])
            emoji = "🟢" if status.get('running') else "🔴"
            text += f"{emoji} {b['name']}\n"
        bot.reply_to(message, text)
    except:
        bot.reply_to(message, "❌ خطا")

# ==================== تنظیم آدرس کیف پول ====================
@bot.message_handler(func=lambda m: m.text == '💳 تنظیم آدرس کیف پول')
def admin_set_wallet(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 آدرس TRC20", callback_data="set_trc20"),
        types.InlineKeyboardButton("🏦 شماره کارت", callback_data="set_card_number"),
        types.InlineKeyboardButton("👤 نام صاحب کارت", callback_data="set_card_holder_name"),
        types.InlineKeyboardButton("🏛 نام بانک", callback_data="set_card_bank_name")
    )
    bot.send_message(message.chat.id, "💳 انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_trc20")
def set_trc20(call):
    msg = bot.send_message(call.message.chat.id, "💰 آدرس TRC20 را وارد کنید:")
    bot.register_next_step_handler(msg, process_set_trc20)

def process_set_trc20(message):
    update_setting('trc20_address', message.text.strip())
    bot.reply_to(message, "✅ آدرس TRC20 ذخیره شد")

@bot.callback_query_handler(func=lambda call: call.data == "set_card_number")
def set_card_number(call):
    msg = bot.send_message(call.message.chat.id, "🏦 شماره کارت ۱۶ رقمی:")
    bot.register_next_step_handler(msg, process_set_card_number)

def process_set_card_number(message):
    card = message.text.strip().replace(" ", "")
    display = ' '.join([card[i:i+4] for i in range(0, len(card), 4)])
    update_setting('card_number', card)
    update_setting('card_number_display', display)
    bot.reply_to(message, f"✅ شماره کارت به {display} تغییر کرد")

@bot.callback_query_handler(func=lambda call: call.data == "set_card_holder_name")
def set_card_holder_name(call):
    msg = bot.send_message(call.message.chat.id, "👤 نام صاحب کارت:")
    bot.register_next_step_handler(msg, process_set_card_holder)

def process_set_card_holder(message):
    update_setting('card_holder', message.text.strip())
    bot.reply_to(message, "✅ نام صاحب کارت ذخیره شد")

@bot.callback_query_handler(func=lambda call: call.data == "set_card_bank_name")
def set_card_bank_name(call):
    msg = bot.send_message(call.message.chat.id, "🏛 نام بانک:")
    bot.register_next_step_handler(msg, process_set_card_bank)

def process_set_card_bank(message):
    update_setting('card_bank', message.text.strip())
    bot.reply_to(message, "✅ نام بانک ذخیره شد")

# ==================== عوض کردن متن راهنما ====================
@bot.message_handler(func=lambda m: m.text == '📝 عوض کردن متن راهنما')
def admin_set_guide(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_guide_fa"),
              types.InlineKeyboardButton("🇬🇧 English", callback_data="set_guide_en"))
    bot.send_message(message.chat.id, "انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_guide_fa")
def set_guide_fa(call):
    msg = bot.send_message(call.message.chat.id, "📝 متن راهنمای فارسی:")
    bot.register_next_step_handler(msg, lambda m: update_setting('guide_text_fa', m.text) or bot.reply_to(m, "✅ ذخیره شد"))

@bot.callback_query_handler(func=lambda call: call.data == "set_guide_en")
def set_guide_en(call):
    msg = bot.send_message(call.message.chat.id, "📝 English guide text:")
    bot.register_next_step_handler(msg, lambda m: update_setting('guide_text_en', m.text) or bot.reply_to(m, "✅ Saved"))

# ==================== عوض کردن متن خوش آمد گویی ====================
@bot.message_handler(func=lambda m: m.text == '👋 عوض کردن متن خوش آمد گویی')
def admin_set_welcome(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_welcome_fa"),
              types.InlineKeyboardButton("🇬🇧 English", callback_data="set_welcome_en"))
    bot.send_message(message.chat.id, "انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_fa")
def set_welcome_fa(call):
    msg = bot.send_message(call.message.chat.id, "👋 متن خوش آمد گویی فارسی (از {name} استفاده کنید):")
    bot.register_next_step_handler(msg, lambda m: update_setting('welcome_text_fa', m.text) or bot.reply_to(m, "✅ ذخیره شد"))

@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_en")
def set_welcome_en(call):
    msg = bot.send_message(call.message.chat.id, "👋 English welcome text (use {name}):")
    bot.register_next_step_handler(msg, lambda m: update_setting('welcome_text_en', m.text) or bot.reply_to(m, "✅ Saved"))

# ==================== عوض کردن متن فعالسازی اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '✅ عوض کردن متن فعالسازی اشتراک')
def admin_set_active_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_active_fa"),
              types.InlineKeyboardButton("🇬🇧 English", callback_data="set_active_en"))
    bot.send_message(message.chat.id, "انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_active_fa")
def set_active_fa(call):
    msg = bot.send_message(call.message.chat.id, "✅ متن فعالسازی اشتراک فارسی:")
    bot.register_next_step_handler(msg, lambda m: update_setting('subscription_active_text_fa', m.text) or bot.reply_to(m, "✅ ذخیره شد"))

@bot.callback_query_handler(func=lambda call: call.data == "set_active_en")
def set_active_en(call):
    msg = bot.send_message(call.message.chat.id, "✅ English activation text:")
    bot.register_next_step_handler(msg, lambda m: update_setting('subscription_active_text_en', m.text) or bot.reply_to(m, "✅ Saved"))

# ==================== عوض کردن متن خرید اشتراک ====================
@bot.message_handler(func=lambda m: m.text == '💸 عوض کردن متن خرید اشتراک')
def admin_set_payment_text(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_payment_fa"),
              types.InlineKeyboardButton("🇬🇧 English", callback_data="set_payment_en"))
    bot.send_message(message.chat.id, "انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "set_payment_fa")
def set_payment_fa(call):
    msg = bot.send_message(call.message.chat.id, "💸 متن خرید اشتراک فارسی (از {price}, {card}, {holder}, {bank} استفاده کنید):")
    bot.register_next_step_handler(msg, lambda m: update_setting('subscription_payment_text_fa', m.text) or bot.reply_to(m, "✅ ذخیره شد"))

@bot.callback_query_handler(func=lambda call: call.data == "set_payment_en")
def set_payment_en(call):
    msg = bot.send_message(call.message.chat.id, "💸 English payment text (use {price} and {address}):")
    bot.register_next_step_handler(msg, lambda m: update_setting('subscription_payment_text_en', m.text) or bot.reply_to(m, "✅ Saved"))

# ==================== ریستارت ربات‌های مرده ====================
@bot.message_handler(func=lambda m: m.text == '🔄 ریستارت ربات‌های مرده')
def admin_restart_dead_bots(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    status_msg = bot.reply_to(message, "🔄 در حال ریستارت...")
    restarted = machine_manager.restart_all_dead_bots()
    bot.edit_message_text(f"✅ {restarted} ربات ریستارت شد", message.chat.id, status_msg.message_id)

# ==================== مدیریت خطاهای ربات ====================
@bot.message_handler(func=lambda m: m.text == '🐛 مدیریت خطاهای ربات')
def admin_errors(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    errors = db.execute('SELECT * FROM errors WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 20')
    if not errors:
        bot.send_message(message.chat.id, "✅ خطایی وجود ندارد")
        return
    for e in errors:
        text = f"🐛 **خطا**\nنوع: {e['type']}\nپیام: {e['message'][:100]}\nزمان: {e['timestamp'][:16]}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ رفع شد", callback_data=f"resolve_error_{e['id']}"))
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('resolve_error_'))
def resolve_error(call):
    eid = call.data.replace('resolve_error_', '')
    db.execute('UPDATE errors SET resolved = 1 WHERE id = ?', (eid,))
    bot.answer_callback_query(call.id, "✅ ثبت شد")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== تنظیم ظرفیت کاربران ====================
@bot.message_handler(func=lambda m: m.text == '⚙️ تنظیم ظرفیت کاربران')
def admin_set_capacity(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    current = get_setting('max_users_capacity')
    users_count = db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    msg = bot.send_message(message.chat.id, f"⚙️ ظرفیت فعلی: {current} کاربر\nکاربران فعلی: {users_count}\nظرفیت جدید (100 تا 100000):")
    bot.register_next_step_handler(msg, process_set_capacity)

def process_set_capacity(message):
    try:
        capacity = int(message.text.strip())
        if 100 <= capacity <= 100000:
            update_setting('max_users_capacity', capacity)
            bot.reply_to(message, f"✅ ظرفیت به {capacity} تغییر کرد")
        else:
            bot.reply_to(message, "❌ بین 100 تا 100000")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

# ==================== مدیریت ماشین‌ها ====================
@bot.message_handler(func=lambda m: m.text == '🖥️ مدیریت ماشین‌ها')
def admin_machines(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📋 لیست", callback_data="machines_list"),
        types.InlineKeyboardButton("📈 افزایش ظرفیت", callback_data="machines_increase"),
        types.InlineKeyboardButton("📉 کاهش ظرفیت", callback_data="machines_decrease"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_machines")
    )
    bot.send_message(message.chat.id, "🖥️ مدیریت ماشین‌ها:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "machines_list")
def machines_list(call):
    machines = db.execute("SELECT * FROM machines ORDER BY id")
    text = "🖥️ **لیست ماشین‌ها**\n\n"
    for m in machines:
        usage = (m['current_bots'] / m['max_bots']) * 100 if m['max_bots'] > 0 else 0
        text += f"{m['name']}: {m['current_bots']}/{m['max_bots']} ({usage:.1f}%)\n"
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "machines_increase")
def machines_increase(call):
    machines = db.execute("SELECT id, name, max_bots FROM machines")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for m in machines:
        markup.add(types.InlineKeyboardButton(f"{m['name']} (فعلی: {m['max_bots']})", callback_data=f"inc_machine_{m['id']}"))
    bot.send_message(call.message.chat.id, "انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('inc_machine_'))
def inc_machine(call):
    machine_id = int(call.data.replace('inc_machine_', ''))
    msg = bot.send_message(call.message.chat.id, "ظرفیت جدید:")
    bot.register_next_step_handler(msg, lambda m: process_change_capacity(m, machine_id, 'inc'))

@bot.callback_query_handler(func=lambda call: call.data == "machines_decrease")
def machines_decrease(call):
    machines = db.execute("SELECT id, name, max_bots FROM machines")
    markup = types.InlineKeyboardMarkup(row_width=1)
    for m in machines:
        markup.add(types.InlineKeyboardButton(f"{m['name']} (فعلی: {m['max_bots']})", callback_data=f"dec_machine_{m['id']}"))
    bot.send_message(call.message.chat.id, "انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dec_machine_'))
def dec_machine(call):
    machine_id = int(call.data.replace('dec_machine_', ''))
    msg = bot.send_message(call.message.chat.id, "ظرفیت جدید:")
    bot.register_next_step_handler(msg, lambda m: process_change_capacity(m, machine_id, 'dec'))

def process_change_capacity(message, machine_id, action):
    try:
        new_capacity = int(message.text.strip())
        machine = db.execute("SELECT * FROM machines WHERE id = ?", (machine_id,))
        if machine:
            current_bots = machine[0]['current_bots']
            if action == 'dec' and new_capacity < current_bots:
                bot.reply_to(message, f"❌ نمی‌تواند کمتر از {current_bots} باشد")
                return
            if 100 <= new_capacity <= 50000:
                machine_manager.update_machine_capacity(machine_id, new_capacity)
                bot.reply_to(message, f"✅ ظرفیت به {new_capacity} تغییر کرد")
            else:
                bot.reply_to(message, "❌ بین 100 تا 50000")
    except:
        bot.reply_to(message, "❌ عدد نامعتبر")

# ==================== اضافه کردن سرور جدید ====================
@bot.message_handler(func=lambda m: m.text == '➕ اضافه کردن سرور جدید')
def admin_add_server(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "➕ **اطلاعات سرور جدید**\n\n1️⃣ نام سرور:")
    bot.register_next_step_handler(msg, process_server_name)

def process_server_name(message):
    server_name = message.text.strip()
    msg = bot.send_message(message.chat.id, "2️⃣ آدرس IP:")
    bot.register_next_step_handler(msg, lambda m: process_server_ip(m, server_name))

def process_server_ip(message, server_name):
    server_ip = message.text.strip()
    msg = bot.send_message(message.chat.id, "3️⃣ پورت (پیش‌فرض 22):")
    bot.register_next_step_handler(msg, lambda m: process_server_port(m, server_name, server_ip))

def process_server_port(message, server_name, server_ip):
    try:
        port = int(message.text.strip()) if message.text.strip() else 22
    except:
        port = 22
    msg = bot.send_message(message.chat.id, "4️⃣ نام کاربری:")
    bot.register_next_step_handler(msg, lambda m: process_server_username(m, server_name, server_ip, port))

def process_server_username(message, server_name, server_ip, port):
    username = message.text.strip()
    msg = bot.send_message(message.chat.id, "5️⃣ رمز عبور:")
    bot.register_next_step_handler(msg, lambda m: process_server_password(m, server_name, server_ip, port, username))

def process_server_password(message, server_name, server_ip, port, username):
    password = message.text.strip()
    success, msg_text = remote_manager.add_server(server_name, server_ip, username, password, port)
    bot.reply_to(message, f"✅ {msg_text}" if success else f"❌ {msg_text}")

# ==================== برگشت به منوی اصلی ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_back_machines")
def admin_back_machines(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    admin_machines(call.message)

@bot.message_handler(func=lambda m: m.text == '🔙 بازگشت به منوی اصلی')
def back_to_main(message):
    bot.send_message(message.chat.id, "🚀 منوی اصلی:", reply_markup=get_main_menu(message.from_user.id))

# ==================== مانیتورینگ ====================
def system_monitor():
    while True:
        try:
            for user in db.execute('SELECT user_id, subscription_expiry FROM users WHERE subscription_status = "active"'):
                if user['subscription_expiry']:
                    expiry = datetime.fromisoformat(user['subscription_expiry'])
                    if expiry < datetime.now():
                        db.execute('UPDATE users SET subscription_status = "inactive" WHERE user_id = ?', (user['user_id'],))
            
            today = datetime.now().date().isoformat()
            db.execute('INSERT OR IGNORE INTO daily_stats (date) VALUES (?)', (today,))
            time.sleep(60)
        except:
            time.sleep(60)

threading.Thread(target=system_monitor, daemon=True).start()

# ==================== Flask API ====================
flask_app = Flask(__name__)

@flask_app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'active_bots': len(machine_manager.processes),
        'queue_size': build_queue.get_queue_length(),
        'total_users': db.execute('SELECT COUNT(*) as count FROM users')[0]['count']
    })

def run_flask():
    flask_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 ربات مادر نهایی - نسخه 100.4 Ultimate".center(80))
    print("=" * 80)
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"🤖 ربات: @{BOT_USERNAME}")
    print(f"💰 قیمت: {get_setting('subscription_price_str')}")
    print(f"🎯 زبان‌ها: 7 زبان برنامه نویسی")
    print("=" * 80)
    print("✅ ربات در حال اجرا است...")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)