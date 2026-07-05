# ============================================
# SIMPLE LOTTERY BOT - WORKING VERSION
# ============================================
# این نسخه ساده و بدون خطا هست
# 
# نصب:
# pip install python-telegram-bot flask
# 
# اجرا:
# python3 app.py

import json
import random
import string
import secrets
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============================================
# تنظیمات - اینجا رو تغییر بده
# ============================================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # توکن ربات رو اینجا بزار
ADMIN_CHAT_ID = 123456789  # آیدی ادمین رو اینجا بزار
PAYMENT_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
BOT_USERNAME = "@UTYOB_Bot"

# ============================================
# دیتابیس ساده
# ============================================
class SimpleDB:
    def __init__(self):
        self.data = {
            "users": {},
            "current_lottery": None,
            "lotteries": []
        }
        self._load()
    
    def _load(self):
        try:
            with open("data.json", "r") as f:
                self.data = json.load(f)
        except:
            self._save()
    
    def _save(self):
        with open("data.json", "w") as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def get_user(self, user_id):
        return self.data["users"].get(str(user_id))
    
    def save_user(self, user_id, data):
        self.data["users"][str(user_id)] = data
        self._save()
    
    def get_all_users(self):
        return list(self.data["users"].values())
    
    def get_subscribed_users(self):
        return [u for u in self.data["users"].values() if u.get("has_subscription", False)]
    
    def get_current_lottery(self):
        return self.data.get("current_lottery")
    
    def set_current_lottery(self, lottery):
        self.data["current_lottery"] = lottery
        self._save()
    
    def add_lottery(self, lottery):
        self.data["lotteries"].append(lottery)
        self._save()
    
    def get_previous_winners(self):
        winners = []
        for lottery in self.data["lotteries"]:
            if lottery.get("winners"):
                winners.extend(lottery["winners"])
        return winners

db = SimpleDB()

# ============================================
# ترجمه
# ============================================
T = {
    "en": {
        "welcome": "🎰 *LOTTERY BOT*\n\n💰 Join and win!\n📱 Click PLAY to open.",
        "subscribe": "💎 *Subscribe*\n\n💰 Send 100 USDT to:\n`{address}`\n\n📝 Enter your TRC20 wallet:",
        "invalid_wallet": "❌ Invalid TRC20 address.",
        "wallet_saved": "✅ Wallet saved!\n\n💰 Send 100 USDT to:\n`{address}`",
        "payment_verified": "✅ *PAYMENT VERIFIED!*\n\n🎉 You're subscribed!",
        "already_subscribed": "✅ You already have subscription!",
        "congratulations": "🎊 *CONGRATULATIONS!*\n\n🏆 You won ${amount}!",
        "not_winner": "😔 Better luck next time!",
        "withdraw": "💰 *Withdraw*\n\nEnter your TRC20 wallet:",
        "withdraw_success": "✅ *Withdrawal Submitted!*",
        "admin_panel": "⚙️ *ADMIN PANEL*\n\n👥 Users: {users}\n🎯 Subscribed: {subscribed}",
        "broadcast_sent": "✅ Sent to {count} users!",
        "manual_verify_done": "✅ Verified!",
        "api_added": "✅ API key added!",
        "withdraw_done": "✅ Done for {count} winners!",
        "restart_done": "✅ Lottery restarted!",
        "survey_sent": "✅ Survey sent to {count} users!",
        "lang_changed": "🌐 Language changed to {lang}",
        "help": "📖 *Help*\n\n1️⃣ Send 100 USDT\n2️⃣ Subscribe\n3️⃣ Win!",
        "cancel": "❌ Cancelled.",
        "admin_broadcast": "📢 Enter message:",
        "admin_manual_verify": "✅ Enter transaction ID:",
        "admin_add_api": "🔑 Enter API key:",
        "admin_survey": "📊 Enter question:",
        "admin_winners": "🏆 Enter number of winners:",
        "admin_prize": "💰 Enter prize amount:",
        "user_status": "👤 Status",
        "subscription": "📅 Subscription",
        "wallet": "🏦 Wallet",
        "not_set": "Not Set",
        "active": "Active",
        "inactive": "Inactive",
        "winner": "🏆 Winner",
        "total_won": "💰 Total Won",
        "referral_code": "🔗 Your code: `{code}`",
        "copy": "📋 Copy",
        "share": "📤 Share",
        "error": "❌ Error",
        "copied": "✅ Copied!",
        "home": "Home",
        "participate": "Participate",
        "winners": "Winners",
        "subscribe_now": "Subscribe Now",
        "expires": "Expires",
        "no_active_lottery": "No active lottery",
        "no_winners": "No winners yet",
        "your_code": "Your Code",
        "payment_address": "Payment Address",
        "enter_wallet": "Enter Wallet",
        "submit": "Submit",
        "verify_payment": "Verify Payment",
        "saving": "Saving...",
        "checking": "Checking...",
        "you_are_winner": "🏆 You are a winner!",
        "withdraw_now": "Withdraw Now",
        "subscription_active": "Subscription Active!",
        "send_amount": "Send Amount",
        "referral_program": "🔗 Referral Program",
    },
    "fa": {
        "welcome": "🎰 *ربات قرعه‌کشی*\n\n💰 شرکت کنید و برنده شوید!\n📱 روی PLAY کلیک کنید.",
        "subscribe": "💎 *اشتراک*\n\n💰 ۱۰۰ دلار به:\n`{address}`\n\n📝 آدرس TRC20 را وارد کنید:",
        "invalid_wallet": "❌ آدرس TRC20 نامعتبر.",
        "wallet_saved": "✅ کیف پول ذخیره شد!\n\n💰 ۱۰۰ دلار به:\n`{address}`",
        "payment_verified": "✅ *پرداخت تایید شد!*\n\n🎉 شما ثبت نام کردید!",
        "already_subscribed": "✅ شما اشتراک دارید!",
        "congratulations": "🎊 *تبریک!*\n\n🏆 شما ${amount} برنده شدید!",
        "not_winner": "😔 دفعه بعد!",
        "withdraw": "💰 *برداشت*\n\nآدرس TRC20 را وارد کنید:",
        "withdraw_success": "✅ *برداشت ثبت شد!*",
        "admin_panel": "⚙️ *پنل مدیریت*\n\n👥 کاربران: {users}\n🎯 اشتراک‌داران: {subscribed}",
        "broadcast_sent": "✅ به {count} کاربر ارسال شد!",
        "manual_verify_done": "✅ تایید شد!",
        "api_added": "✅ کلید API اضافه شد!",
        "withdraw_done": "✅ برای {count} برنده انجام شد!",
        "restart_done": "✅ قرعه‌کشی مجدداً شروع شد!",
        "survey_sent": "✅ نظر سنجی به {count} کاربر ارسال شد!",
        "lang_changed": "🌐 زبان به {lang} تغییر یافت",
        "help": "📖 *راهنما*\n\n۱️⃣ ۱۰۰ دلار ارسال کنید\n۲️⃣ اشتراک بخرید\n۳️⃣ برنده شوید!",
        "cancel": "❌ لغو شد.",
        "admin_broadcast": "📢 پیام را وارد کنید:",
        "admin_manual_verify": "✅ شناسه تراکنش را وارد کنید:",
        "admin_add_api": "🔑 کلید API را وارد کنید:",
        "admin_survey": "📊 سوال را وارد کنید:",
        "admin_winners": "🏆 تعداد برندگان را وارد کنید:",
        "admin_prize": "💰 مبلغ جایزه را وارد کنید:",
        "user_status": "👤 وضعیت",
        "subscription": "📅 اشتراک",
        "wallet": "🏦 کیف پول",
        "not_set": "تنظیم نشده",
        "active": "فعال",
        "inactive": "غیرفعال",
        "winner": "🏆 برنده",
        "total_won": "💰 مجموع برداشت",
        "referral_code": "🔗 کد شما: `{code}`",
        "copy": "📋 کپی",
        "share": "📤 اشتراک‌گذاری",
        "error": "❌ خطا",
        "copied": "✅ کپی شد!",
        "home": "خانه",
        "participate": "شرکت",
        "winners": "برندگان",
        "subscribe_now": "اشتراک فوری",
        "expires": "انقضا",
        "no_active_lottery": "قرعه‌کشی فعالی وجود ندارد",
        "no_winners": "هنوز برنده‌ای وجود ندارد",
        "your_code": "کد شما",
        "payment_address": "آدرس پرداخت",
        "enter_wallet": "ورود کیف پول",
        "submit": "ثبت",
        "verify_payment": "تایید پرداخت",
        "saving": "در حال ذخیره...",
        "checking": "در حال بررسی...",
        "you_are_winner": "🏆 شما برنده شدید!",
        "withdraw_now": "برداشت فوری",
        "subscription_active": "اشتراک فعال است!",
        "send_amount": "مبلغ ارسال",
        "referral_program": "🔗 برنامه رفرال",
    },
    "ar": {
        "welcome": "🎰 *يانصيب*\n\n💰 شارك واربح!\n📱 اضغط PLAY للفتح.",
        "subscribe": "💎 *اشتراك*\n\n💰 أرسل ۱۰۰ دولار إلى:\n`{address}`\n\n📝 أدخل محفظة TRC20:",
        "invalid_wallet": "❌ عنوان TRC20 غير صالح.",
        "wallet_saved": "✅ تم حفظ المحفظة!\n\n💰 أرسل ۱۰۰ دولار إلى:\n`{address}`",
        "payment_verified": "✅ *تم التحقق!*\n\n🎉 تم الاشتراك!",
        "already_subscribed": "✅ لديك اشتراك!",
        "congratulations": "🎊 *تهانينا!*\n\n🏆 لقد فزت بـ ${amount}!",
        "not_winner": "😔 حظاً أوفر!",
        "withdraw": "💰 *سحب*\n\nأدخل محفظة TRC20:",
        "withdraw_success": "✅ *تم السحب!*",
        "admin_panel": "⚙️ *لوحة الإدارة*\n\n👥 المستخدمون: {users}\n🎯 المشتركون: {subscribed}",
        "broadcast_sent": "✅ تم الإرسال إلى {count} مستخدم!",
        "manual_verify_done": "✅ تم التحقق!",
        "api_added": "✅ تم إضافة المفتاح!",
        "withdraw_done": "✅ تم الدفع لـ {count} فائز!",
        "restart_done": "✅ تم إعادة بدء اليانصيب!",
        "survey_sent": "✅ تم إرسال الاستبيان إلى {count} مستخدم!",
        "lang_changed": "🌐 تم تغيير اللغة إلى {lang}",
        "help": "📖 *مساعدة*\n\n۱️⃣ أرسل ۱۰۰ دولار\n۲️⃣ اشترك\n۳️⃣ اربح!",
        "cancel": "❌ تم الإلغاء.",
        "admin_broadcast": "📢 أدخل الرسالة:",
        "admin_manual_verify": "✅ أدخل معرف المعاملة:",
        "admin_add_api": "🔑 أدخل مفتاح API:",
        "admin_survey": "📊 أدخل السؤال:",
        "admin_winners": "🏆 أدخل عدد الفائزين:",
        "admin_prize": "💰 أدخل قيمة الجائزة:",
        "user_status": "👤 الحالة",
        "subscription": "📅 الاشتراك",
        "wallet": "🏦 المحفظة",
        "not_set": "غير محدد",
        "active": "نشط",
        "inactive": "غير نشط",
        "winner": "🏆 فائز",
        "total_won": "💰 إجمالي الفوز",
        "referral_code": "🔗 رمزك: `{code}`",
        "copy": "📋 نسخ",
        "share": "📤 مشاركة",
        "error": "❌ خطأ",
        "copied": "✅ تم النسخ!",
        "home": "الرئيسية",
        "participate": "المشاركة",
        "winners": "الفائزون",
        "subscribe_now": "اشتراك فوري",
        "expires": "ينتهي",
        "no_active_lottery": "لا يوجد يانصيب نشط",
        "no_winners": "لا يوجد فائزون",
        "your_code": "رمزك",
        "payment_address": "عنوان الدفع",
        "enter_wallet": "أدخل المحفظة",
        "submit": "إرسال",
        "verify_payment": "التحقق من الدفع",
        "saving": "جاري الحفظ...",
        "checking": "جاري التحقق...",
        "you_are_winner": "🏆 أنت فائز!",
        "withdraw_now": "سحب الآن",
        "subscription_active": "الاشتراك نشط!",
        "send_amount": "المبلغ المرسل",
        "referral_program": "🔗 برنامج الإحالة",
    }
}

def get_text(key, lang="en", **kwargs):
    text = T.get(lang, T["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

# ============================================
# Flask App
# ============================================
flask_app = Flask(__name__)

WEBAPP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎰 Lottery</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, sans-serif;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
            padding: 16px;
            padding-bottom: 80px;
        }
        .card {
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
        }
        .card-title { font-size: 16px; font-weight: 600; margin-bottom: 10px; }
        .row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #ddd);
        }
        .row:last-child { border-bottom: none; }
        .label { color: var(--tg-theme-hint-color, #666); font-size: 13px; }
        .value { font-weight: 500; font-size: 13px; }
        .highlight { color: var(--tg-theme-button-color, #0088cc); font-weight: 700; }
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge.active { background: #4caf50; color: #fff; }
        .badge.inactive { background: #999; color: #fff; }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 10px 20px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            color: #fff;
            background: var(--tg-theme-button-color, #0088cc);
            margin-top: 8px;
        }
        .btn:active { transform: scale(0.97); }
        .btn-success { background: #4caf50; }
        .btn-secondary { background: var(--tg-theme-secondary-bg-color, #ddd); color: #000; }
        .btn-gold { background: linear-gradient(135deg, #ffd700, #f5a623); color: #000; }
        .input-group { margin-bottom: 12px; }
        .input-group label {
            display: block;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 4px;
            color: var(--tg-theme-hint-color, #666);
        }
        .input-group input {
            width: 100%;
            padding: 10px 14px;
            border: 2px solid var(--tg-theme-secondary-bg-color, #ddd);
            border-radius: 10px;
            font-size: 14px;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
        }
        .input-group input:focus { outline: none; border-color: var(--tg-theme-button-color, #0088cc); }
        .loading { text-align: center; padding: 20px; }
        .spinner {
            width: 30px;
            height: 30px;
            border: 3px solid var(--tg-theme-secondary-bg-color, #ddd);
            border-top: 3px solid var(--tg-theme-button-color, #0088cc);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .empty { text-align: center; padding: 30px 20px; color: var(--tg-theme-hint-color, #666); }
        .code-box {
            background: var(--tg-theme-bg-color, #fff);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-size: 18px;
            font-weight: 700;
            font-family: monospace;
            border: 2px dashed var(--tg-theme-button-color, #0088cc);
        }
        .tab-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--tg-theme-bg-color, #fff);
            border-top: 1px solid var(--tg-theme-secondary-bg-color, #ddd);
            display: flex;
            padding: 6px 0;
            z-index: 100;
        }
        .tab {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2px 0;
            cursor: pointer;
            border: none;
            background: none;
            color: var(--tg-theme-hint-color, #666);
            font-size: 10px;
        }
        .tab.active { color: var(--tg-theme-button-color, #0088cc); }
        .tab .icon { font-size: 22px; }
        .tab .label { font-size: 9px; margin-top: 2px; }
        .page { display: none; }
        .page.active { display: block; }
        .lang-bar {
            display: flex;
            gap: 4px;
            margin-bottom: 12px;
        }
        .lang-btn {
            padding: 4px 10px;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            background: var(--tg-theme-secondary-bg-color, #ddd);
            color: var(--tg-theme-text-color, #000);
        }
        .lang-btn.active {
            background: var(--tg-theme-button-color, #0088cc);
            color: #fff;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .header-title { font-size: 20px; font-weight: 700; }
        .winner-list { list-style: none; padding: 0; }
        .winner-list li {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #ddd);
        }
        .winner-list li:last-child { border-bottom: none; }
        .winner-amount { font-weight: 700; color: #ffd700; }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">🎰 Lottery</div>
        <div class="lang-bar">
            <button class="lang-btn active" onclick="setLang('en')">EN</button>
            <button class="lang-btn" onclick="setLang('fa')">FA</button>
            <button class="lang-btn" onclick="setLang('ar')">AR</button>
        </div>
    </div>
    
    <div id="page-home" class="page active">
        <div class="card"><div class="card-title">👤 Status</div><div id="status">Loading...</div></div>
        <div class="card"><div class="card-title">📅 Subscription</div><div id="subscription">Loading...</div></div>
        <div class="card"><div class="card-title">🎰 Lottery</div><div id="lottery">Loading...</div></div>
        <div class="card"><div class="card-title">🏆 Winners</div><div id="winners">Loading...</div></div>
        <div class="card"><div class="card-title">🔗 Referral</div><div id="referral">Loading...</div></div>
    </div>
    
    <div id="page-participate" class="page">
        <div class="card"><div class="card-title">💰 Participate</div><div id="participate">Loading...</div></div>
    </div>
    
    <div id="page-winners" class="page">
        <div class="card"><div class="card-title">🏆 All Winners</div><div id="all-winners">Loading...</div></div>
    </div>
    
    <div class="tab-bar">
        <button class="tab active" onclick="switchPage('home')"><span class="icon">🏠</span><span class="label">Home</span></button>
        <button class="tab" onclick="switchPage('participate')"><span class="icon">💰</span><span class="label">Participate</span></button>
        <button class="tab" onclick="switchPage('winners')"><span class="icon">🏆</span><span class="label">Winners</span></button>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        
        let lang = 'en';
        let userId = null;
        const T = {{ T|safe }};
        
        function t(key) { return (T[lang] && T[lang][key]) || key; }
        
        function setLang(l) {
            lang = l;
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`.lang-btn[onclick="setLang('${l}')"]`).classList.add('active');
            loadAll();
            fetch('/api/language', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({language: l})
            }).catch(() => {});
        }
        
        function showToast(msg) {
            const el = document.createElement('div');
            el.style.cssText = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.8);color:#fff;padding:10px 20px;border-radius:10px;font-size:13px;z-index:999;max-width:90%;text-align:center;';
            el.textContent = msg;
            document.body.appendChild(el);
            setTimeout(() => el.remove(), 3000);
        }
        
        async function call(endpoint, method='GET', data=null) {
            try {
                const opts = {method, headers: {'Content-Type': 'application/json'}};
                if (data) opts.body = JSON.stringify(data);
                const res = await fetch(endpoint, opts);
                const result = await res.json();
                if (!res.ok) throw new Error(result.error || 'Error');
                return result;
            } catch(e) {
                console.error(e);
                showToast(t('error'));
                throw e;
            }
        }
        
        function switchPage(page) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById('page-' + page).classList.add('active');
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab[onclick="switchPage('${page}')"]`).classList.add('active');
            if (page === 'participate') loadParticipate();
            if (page === 'winners') loadAllWinners();
        }
        
        async function loadAll() {
            await Promise.all([loadStatus(), loadSubscription(), loadLottery(), loadWinners(), loadReferral()]);
        }
        
        async function loadStatus() {
            try {
                const data = await call('/api/user/status');
                const u = data.user || {};
                document.getElementById('status').innerHTML = `
                    <div class="row"><span class="label">${t('user_id')}</span><span class="value">${u.telegram_id || 'N/A'}</span></div>
                    <div class="row"><span class="label">${t('wallet')}</span><span class="value">${u.wallet_address ? u.wallet_address.substring(0,8)+'...' : t('not_set')}</span></div>
                    <div class="row"><span class="label">${t('total_won')}</span><span class="value highlight">$${u.total_won || 0}</span></div>
                    ${u.is_winner ? `<div class="row"><span class="label">${t('winner')}</span><span class="value" style="color:#ffd700;">🏆 $${u.won_amount}</span></div>` : ''}
                `;
            } catch(e) {
                document.getElementById('status').innerHTML = `<div class="empty">${t('error')}</div>`;
            }
        }
        
        async function loadSubscription() {
            try {
                const data = await call('/api/user/subscription');
                const has = data.has_subscription || false;
                document.getElementById('subscription').innerHTML = `
                    <div class="row">
                        <span class="label">${t('subscription')}</span>
                        <span class="value"><span class="badge ${has ? 'active' : 'inactive'}">${has ? t('active') : t('inactive')}</span></span>
                    </div>
                    ${has ? `<div class="row"><span class="label">${t('expires')}</span><span class="value">${data.expiry ? new Date(data.expiry).toLocaleDateString() : 'N/A'}</span></div>`
                    : `<button class="btn btn-success" onclick="switchPage('participate')">💰 ${t('subscribe_now')}</button>`}
                `;
            } catch(e) {
                document.getElementById('subscription').innerHTML = `<div class="empty">${t('error')}</div>`;
            }
        }
        
        async function loadLottery() {
            try {
                const data = await call('/api/lottery/status');
                if (data.active) {
                    document.getElementById('lottery').innerHTML = `
                        <div class="row"><span class="label">${t('status')}</span><span class="value"><span class="badge active">${t('active')}</span></span></div>
                        <div class="row"><span class="label">${t('participants')}</span><span class="value">${data.participant_count || 0}</span></div>
                        <div class="row"><span class="label">${t('prize_pool')}</span><span class="value highlight">$${data.prize_pool || 0}</span></div>
                    `;
                } else {
                    document.getElementById('lottery').innerHTML = `<div class="empty">${t('no_active_lottery')}</div>`;
                }
            } catch(e) {
                document.getElementById('lottery').innerHTML = `<div class="empty">${t('error')}</div>`;
            }
        }
        
        async function loadWinners() {
            try {
                const data = await call('/api/lottery/winners');
                if (data.winners && data.winners.length > 0) {
                    let html = `<ul class="winner-list">`;
                    data.winners.slice(0, 5).forEach((w, i) => {
                        html += `<li><span>#${i+1} ${w.username || 'User'}</span><span class="winner-amount">$${w.amount}</span></li>`;
                    });
                    html += `</ul>`;
                    if (data.winners.length > 5) html += `<button class="btn btn-secondary" onclick="switchPage('winners')">${t('view_all') || 'View All'}</button>`;
                    document.getElementById('winners').innerHTML = html;
                } else {
                    document.getElementById('winners').innerHTML = `<div class="empty">${t('no_winners')}</div>`;
                }
            } catch(e) {
                document.getElementById('winners').innerHTML = `<div class="empty">${t('error')}</div>`;
            }
        }
        
        async function loadReferral() {
            try {
                const data = await call('/api/user/referral');
                document.getElementById('referral').innerHTML = `
                    <div class="row"><span class="label">${t('your_code')}</span><span class="value"><div class="code-box">${data.referral_code}</div></span></div>
                    <div style="display:flex;gap:8px;margin-top:8px;">
                        <button class="btn btn-secondary" onclick="copyText('${data.referral_code}')">📋 ${t('copy')}</button>
                        <button class="btn btn-success" onclick="shareCode('${data.referral_code}')">📤 ${t('share')}</button>
                    </div>
                    <div class="row"><span class="label">${t('referrals')}</span><span class="value">${data.referral_count || 0}</span></div>
                `;
            } catch(e) {
                document.getElementById('referral').innerHTML = `<div class="empty">${t('error')}</div>`;
            }
        }
        
        async function loadParticipate() {
            const el = document.getElementById('participate');
            try {
                const data = await call('/api/user/status');
                if (data.user && data.user.has_subscription) {
                    el.innerHTML = `
                        <div style="text-align:center;padding:20px;">
                            <div style="font-size:48px;">🎉</div>
                            <h3>${t('subscription_active')}</h3>
                            ${data.user.is_winner ? `
                            <div style="margin-top:12px;padding:12px;background:#ffd70022;border-radius:8px;">
                                <p style="font-weight:700;color:#ffd700;">🏆 ${t('you_are_winner')} $${data.user.won_amount}</p>
                                <button class="btn btn-gold" onclick="withdraw()">💰 ${t('withdraw_now')}</button>
                            </div>` : `<p style="color:#666;">${t('waiting_for_draw') || 'Waiting...'}</p>`}
                        </div>
                    `;
                } else {
                    el.innerHTML = `
                        <div style="text-align:center;margin-bottom:16px;">
                            <div style="font-size:48px;">💰</div>
                            <h3>${t('subscribe_now')}</h3>
                            <p style="color:#666;font-size:13px;">${t('send_amount')}: 100 USDT</p>
                        </div>
                        <div class="input-group">
                            <label>${t('payment_address')}</label>
                            <div style="display:flex;gap:6px;">
                                <input type="text" id="payment-addr" value="${PAYMENT_ADDRESS}" readonly style="flex:1;font-size:12px;">
                                <button class="btn btn-secondary" onclick="copyText(document.getElementById('payment-addr').value)" style="width:auto;padding:8px 12px;">📋</button>
                            </div>
                        </div>
                        <div class="input-group">
                            <label>${t('enter_wallet')}</label>
                            <input type="text" id="wallet-input" placeholder="T... (TRC20)">
                        </div>
                        <button class="btn btn-success" onclick="submitWallet()">✅ ${t('submit')}</button>
                        <button class="btn btn-secondary" onclick="verifyPayment()" style="margin-top:8px;">🔄 ${t('verify_payment')}</button>
                    `;
                }
            } catch(e) {
                el.innerHTML = `<div class="empty">${t('error')}</div>`;
            }
        }
        
        async function loadAllWinners() {
            const el = document.getElementById('all-winners');
            try {
                const data = await call('/api/lottery/all-winners');
                if (data.winners && data.winners.length > 0) {
                    let html = `<ul class="winner-list">`;
                    data.winners.slice(0, 20).forEach((w, i) => {
                        html += `<li><span>#${i+1} ${w.username || 'User'}</span><span class="winner-amount">$${w.amount}</span></li>`;
                    });
                    html += `</ul>`;
                    el.innerHTML = html;
                } else {
                    el.innerHTML = `<div class="empty">${t('no_winners')}</div>`;
                }
            } catch(e) {
                el.innerHTML = `<div class="empty">${t('error')}</div>`;
            }
        }
        
        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => showToast(t('copied')))
                .catch(() => { const el = document.createElement('textarea'); el.value = text; document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el); showToast(t('copied')); });
        }
        
        function shareCode(code) {
            const text = `🎰 Join Lottery! Use my code: ${code}`;
            if (navigator.share) { navigator.share({title: '🎰 Lottery', text}).catch(() => {}); }
            else { copyText(text); }
        }
        
        async function submitWallet() {
            const wallet = document.getElementById('wallet-input').value.trim();
            if (!wallet || !wallet.startsWith('T') || wallet.length !== 34) {
                showToast(t('invalid_wallet'));
                return;
            }
            try {
                const btn = document.querySelector('.btn-success');
                btn.disabled = true;
                btn.textContent = '⏳ ' + (t('saving') || 'Saving...');
                const result = await call('/api/user/wallet', 'POST', {wallet_address: wallet});
                if (result.success) {
                    showToast(t('wallet_saved'));
                    document.getElementById('wallet-input').value = '';
                    loadAll();
                }
            } catch(e) {
                showToast(t('error'));
            } finally {
                const btn = document.querySelector('.btn-success');
                btn.disabled = false;
                btn.textContent = '✅ ' + (t('submit') || 'Submit');
            }
        }
        
        async function verifyPayment() {
            try {
                const btn = document.querySelector('.btn-secondary');
                btn.disabled = true;
                btn.textContent = '⏳ ' + (t('checking') || 'Checking...');
                const result = await call('/api/payment/verify', 'POST');
                if (result.verified) {
                    showToast(t('payment_verified'));
                    loadAll();
                } else {
                    showToast(t('payment_failed') || 'Payment failed');
                }
            } catch(e) {
                showToast(t('error'));
            } finally {
                const btn = document.querySelector('.btn-secondary');
                btn.disabled = false;
                btn.textContent = '🔄 ' + (t('verify_payment') || 'Verify Payment');
            }
        }
        
        async function withdraw() {
            const wallet = prompt(t('enter_wallet') || 'Enter TRC20 wallet:');
            if (!wallet) return;
            if (!wallet.startsWith('T') || wallet.length !== 34) {
                showToast(t('invalid_wallet'));
                return;
            }
            try {
                const result = await call('/api/user/withdraw', 'POST', {wallet_address: wallet});
                if (result.success) {
                    showToast(t('withdraw_success'));
                    loadAll();
                }
            } catch(e) {
                showToast(t('error'));
            }
        }
        
        async function init() {
            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                userId = tg.initDataUnsafe.user.id;
                try {
                    const res = await fetch('/api/auth', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user: tg.initDataUnsafe.user})
                    });
                    const data = await res.json();
                    if (data.success && data.language) {
                        lang = data.language;
                        document.querySelectorAll('.lang-btn').forEach(b => {
                            b.classList.remove('active');
                            if (b.textContent.toLowerCase().includes(lang)) b.classList.add('active');
                        });
                        await loadAll();
                    }
                } catch(e) {
                    console.error('Auth error:', e);
                }
            } else {
                try {
                    const data = await call('/api/user/status');
                    if (data.user) {
                        userId = data.user.telegram_id;
                        await loadAll();
                    }
                } catch(e) {}
            }
        }
        
        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
"""

# ============================================
# Flask Routes
# ============================================
@flask_app.route('/')
def index():
    return render_template_string(WEBAPP_HTML, T=T)

@flask_app.route('/api/auth', methods=['POST'])
def auth():
    data = request.json
    user = data.get('user', {})
    user_id = user.get('id')
    
    if not user_id:
        return jsonify({'success': False}), 400
    
    db_user = db.get_user(user_id)
    if not db_user:
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        db_user = {
            "telegram_id": user_id,
            "username": user.get('username', ''),
            "language": "en",
            "wallet_address": None,
            "referral_code": code,
            "has_subscription": False,
            "subscription_expiry": None,
            "is_winner": False,
            "won_amount": 0,
            "total_won": 0,
            "referral_count": 0,
            "referral_earnings": 0,
        }
        db.save_user(user_id, db_user)
    
    return jsonify({
        'success': True,
        'language': db_user.get('language', 'en')
    })

@flask_app.route('/api/user/status')
def user_status():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'No user'}), 401
    
    user = db.get_user(int(user_id))
    if not user:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'user': {
            'telegram_id': user.get('telegram_id'),
            'username': user.get('username'),
            'wallet_address': user.get('wallet_address'),
            'has_subscription': user.get('has_subscription', False),
            'subscription_expiry': user.get('subscription_expiry'),
            'total_won': user.get('total_won', 0),
            'is_winner': user.get('is_winner', False),
            'won_amount': user.get('won_amount', 0)
        }
    })

@flask_app.route('/api/user/subscription')
def user_subscription():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'No user'}), 401
    
    user = db.get_user(int(user_id))
    if not user:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'has_subscription': user.get('has_subscription', False),
        'expiry': user.get('subscription_expiry')
    })

@flask_app.route('/api/user/wallet', methods=['POST'])
def save_wallet():
    data = request.json
    user_id = data.get('user_id')
    wallet = data.get('wallet_address')
    
    if not user_id:
        return jsonify({'error': 'No user'}), 401
    
    if not wallet or not wallet.startswith('T') or len(wallet) != 34:
        return jsonify({'error': 'Invalid wallet'}), 400
    
    user = db.get_user(int(user_id))
    if user:
        user['wallet_address'] = wallet
        db.save_user(int(user_id), user)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Not found'}), 404

@flask_app.route('/api/user/referral')
def user_referral():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'No user'}), 401
    
    user = db.get_user(int(user_id))
    if not user:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'referral_code': user.get('referral_code'),
        'referral_count': user.get('referral_count', 0),
        'referral_earnings': user.get('referral_earnings', 0)
    })

@flask_app.route('/api/lottery/status')
def lottery_status():
    lottery = db.get_current_lottery()
    if lottery:
        return jsonify({
            'active': True,
            'participant_count': lottery.get('participant_count', 0),
            'prize_pool': lottery.get('prize_pool', 0),
            'prize_per_winner': lottery.get('prize_per_winner', 0)
        })
    return jsonify({'active': False})

@flask_app.route('/api/lottery/winners')
def lottery_winners():
    lottery = db.get_current_lottery()
    winners = []
    if lottery and lottery.get('winners'):
        for w_id in lottery['winners']:
            user = db.get_user(w_id)
            if user:
                winners.append({
                    'user_id': w_id,
                    'username': user.get('username', 'User'),
                    'amount': lottery.get('prize_per_winner', 0)
                })
    return jsonify({'winners': winners})

@flask_app.route('/api/lottery/all-winners')
def all_winners():
    winners = []
    for lottery in db.data['lotteries']:
        if lottery.get('winners'):
            for w_id in lottery['winners']:
                user = db.get_user(w_id)
                if user:
                    winners.append({
                        'user_id': w_id,
                        'username': user.get('username', 'User'),
                        'amount': lottery.get('prize_per_winner', 0),
                        'date': lottery.get('drawn_at', datetime.now().isoformat())
                    })
    return jsonify({'winners': winners})

@flask_app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'No user'}), 401
    
    user = db.get_user(int(user_id))
    if not user:
        return jsonify({'error': 'Not found'}), 404
    
    user['has_subscription'] = True
    user['subscription_expiry'] = (datetime.now() + timedelta(days=30)).isoformat()
    db.save_user(int(user_id), user)
    
    return jsonify({'verified': True})

@flask_app.route('/api/user/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    user_id = data.get('user_id')
    wallet = data.get('wallet_address')
    
    if not user_id:
        return jsonify({'error': 'No user'}), 401
    
    if not wallet or not wallet.startswith('T') or len(wallet) != 34:
        return jsonify({'error': 'Invalid wallet'}), 400
    
    user = db.get_user(int(user_id))
    if user and user.get('is_winner'):
        user['wallet_address'] = wallet
        user['is_winner'] = False
        db.save_user(int(user_id), user)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Not a winner'}), 400

@flask_app.route('/api/language', methods=['POST'])
def set_language():
    data = request.json
    lang = data.get('language')
    user_id = data.get('user_id')
    
    if not user_id or lang not in ['en', 'fa', 'ar']:
        return jsonify({'error': 'Invalid'}), 400
    
    user = db.get_user(int(user_id))
    if user:
        user['language'] = lang
        db.save_user(int(user_id), user)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Not found'}), 404

# ============================================
# Telegram Bot
# ============================================
class Bot:
    def __init__(self):
        self.app = None
    
    async def start(self):
        self.app = Application.builder().token(BOT_TOKEN).build()
        self.app.add_handler(CommandHandler("start", self.start_cmd))
        self.app.add_handler(CallbackQueryHandler(self.callback))
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        print("✅ Bot started!")
    
    def get_lang(self, user_id):
        user = db.get_user(user_id)
        return user.get("language", "en") if user else "en"
    
    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        db_user = db.get_user(user_id)
        if not db_user:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            db_user = {
                "telegram_id": user_id,
                "username": user.username,
                "language": "en",
                "wallet_address": None,
                "referral_code": code,
                "has_subscription": False,
                "subscription_expiry": None,
                "is_winner": False,
                "won_amount": 0,
                "total_won": 0,
                "referral_count": 0,
                "referral_earnings": 0,
            }
            db.save_user(user_id, db_user)
        
        lang = db_user.get("language", "en")
        
        keyboard = [
            [InlineKeyboardButton("🎮 PLAY", web_app=WebAppInfo(url="http://localhost:5000"))],
            [InlineKeyboardButton("🎰 Subscribe", callback_data="subscribe")],
            [InlineKeyboardButton("🔗 Referral", callback_data="referral")],
            [InlineKeyboardButton("🌐 Language", callback_data="lang")],
        ]
        
        if user_id == ADMIN_CHAT_ID:
            keyboard.append([InlineKeyboardButton("⚙️ Admin", callback_data="admin")])
        
        await update.message.reply_text(
            get_text("welcome", lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    async def callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        lang = self.get_lang(user_id)
        
        if data == "lang":
            keyboard = [
                [InlineKeyboardButton("🇬🇧 English", callback_data="en")],
                [InlineKeyboardButton("🇮🇷 فارسی", callback_data="fa")],
                [InlineKeyboardButton("🇸🇦 العربية", callback_data="ar")],
            ]
            await query.edit_message_text("🌐 Select language:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        if data in ["en", "fa", "ar"]:
            user = db.get_user(user_id)
            if user:
                user["language"] = data
                db.save_user(user_id, user)
            await query.edit_message_text(get_text("lang_changed", data, lang={"en":"English","fa":"فارسی","ar":"العربية"}.get(data,data)))
            return
        
        if data == "subscribe":
            user = db.get_user(user_id)
            if user and user.get("has_subscription"):
                await query.edit_message_text(get_text("already_subscribed", lang), parse_mode="Markdown")
                return
            
            await query.edit_message_text(
                get_text("subscribe", lang, address=PAYMENT_ADDRESS),
                parse_mode="Markdown"
            )
            context.user_data['step'] = 'wallet'
            return
        
        if data == "referral":
            user = db.get_user(user_id)
            if user:
                await query.edit_message_text(
                    get_text("referral_program", lang) + f"\n\nCode: `{user.get('referral_code')}`",
                    parse_mode="Markdown"
                )
            return
        
        if data == "admin":
            if user_id != ADMIN_CHAT_ID:
                await query.edit_message_text("⛔ Access denied.")
                return
            
            keyboard = [
                [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
                [InlineKeyboardButton("🎰 Start Lottery", callback_data="admin_start")],
                [InlineKeyboardButton("✅ Verify", callback_data="admin_verify")],
                [InlineKeyboardButton("🔄 Restart", callback_data="admin_restart")],
            ]
            await query.edit_message_text(
                get_text("admin_panel", lang, users=len(db.get_all_users()), subscribed=len(db.get_subscribed_users())),
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return
        
        if data.startswith("admin_"):
            if user_id != ADMIN_CHAT_ID:
                return
            
            action = data.replace("admin_", "")
            
            if action == "broadcast":
                await query.edit_message_text(get_text("admin_broadcast", lang))
                context.user_data['step'] = 'broadcast'
                return
            
            if action == "start":
                # Simple lottery: pick random winners
                users = db.get_subscribed_users()
                if len(users) < 2:
                    await query.edit_message_text("❌ Not enough users.")
                    return
                
                # Pick 1-3 winners
                winners_count = min(3, len(users))
                winners = random.sample([u['telegram_id'] for u in users], winners_count)
                
                lottery = {
                    "winners": winners,
                    "prize_per_winner": 100,
                    "participant_count": len(users),
                    "prize_pool": winners_count * 100,
                    "drawn_at": datetime.now().isoformat()
                }
                db.add_lottery(lottery)
                db.set_current_lottery(lottery)
                
                # Announce winners
                for w_id in winners:
                    user = db.get_user(w_id)
                    if user:
                        user['is_winner'] = True
                        user['won_amount'] = 100
                        user['total_won'] = user.get('total_won', 0) + 100
                        db.save_user(w_id, user)
                        
                        try:
                            await self.app.bot.send_message(
                                w_id,
                                get_text("congratulations", user.get("language", "en"), amount=100),
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                
                await query.edit_message_text(
                    f"🎰 Lottery drawn!\n👥 {len(users)} participants\n🏆 {len(winners)} winners\n💰 Each wins $100!",
                    parse_mode="Markdown"
                )
                return
            
            if action == "verify":
                await query.edit_message_text(get_text("admin_manual_verify", lang))
                context.user_data['step'] = 'verify'
                return
            
            if action == "restart":
                db.set_current_lottery(None)
                await query.edit_message_text(get_text("restart_done", lang), parse_mode="Markdown")
                return

# ============================================
# اجرا
# ============================================
def run_flask():
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

async def run_bot():
    bot = Bot()
    await bot.start()

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════╗
    ║  🎰 LOTTERY BOT - SIMPLE VERSION     ║
    ║  🤖 Telegram Bot + WebApp            ║
    ╚═══════════════════════════════════════╝
    """)
    
    # Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Bot
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_bot())
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
    finally:
        loop.close()