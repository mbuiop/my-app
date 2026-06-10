#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
═══════════════════════════════════════════════════════════════════════════════
🌐 وب‌اپ ساخت ربات تلگرام - یکپارچه با ربات مادر
📱 کاربران می‌توانند از طریق سایت ربات بسازند
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import sqlite3
import hashlib
import time
import threading
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS

# اضافه کردن مسیر اصلی
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# import از فایل اصلی
from app import (
    db, get_user, create_user, check_subscription, get_remaining_bots,
    get_setting, update_setting, get_user_bots, delete_bot, machine_manager,
    build_queue, add_bot, extract_token_from_code, rate_limiter,
    get_text, BOT_USERNAME, ADMIN_IDS, DIRS
)

# ==================== تنظیمات Flask ====================
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "mother_bot_secret_key_2024")
CORS(app)

# ==================== دکوراتورهای احراز هویت ====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_id') not in ADMIN_IDS:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== صفحات HTML ====================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>ساخت ربات تلگرام | ربات ساز</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { font-family: 'Vazirmatn', 'Tahoma', sans-serif; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        /* کارت‌ها */
        .card {
            border: none;
            border-radius: 20px;
            box-shadow: 0 20px 35px -10px rgba(0,0,0,0.2);
            backdrop-filter: blur(10px);
            background: rgba(255,255,255,0.95);
            transition: transform 0.3s;
        }
        .card:hover { transform: translateY(-5px); }
        
        /* هدر */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 25px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        /* دکمه‌ها */
        .btn-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 12px;
            padding: 12px 25px;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-primary:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 20px rgba(102,126,234,0.4);
        }
        
        /* فرم‌ها */
        .form-control, .form-select {
            border-radius: 12px;
            border: 2px solid #e0e0e0;
            padding: 12px 15px;
            font-size: 1rem;
        }
        .form-control:focus, .form-select:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102,126,234,0.25);
        }
        
        /* جدول */
        .table-custom {
            background: white;
            border-radius: 20px;
            overflow: hidden;
        }
        .table-custom th {
            background: #667eea;
            color: white;
            padding: 15px;
            font-weight: 600;
        }
        .table-custom td {
            padding: 12px 15px;
            vertical-align: middle;
        }
        
        /* وضعیت */
        .status-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .status-running { background: #28a74520; color: #28a745; border: 1px solid #28a745; }
        .status-stopped { background: #dc354520; color: #dc3545; border: 1px solid #dc3545; }
        
        /* نوار پیشرفت */
        .progress-custom {
            height: 8px;
            border-radius: 10px;
            background: #e0e0e0;
        }
        .progress-custom .progress-bar {
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 10px;
        }
        
        /* انیمیشن */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade {
            animation: fadeIn 0.5s ease-out;
        }
        
        /* کد */
        .code-area {
            font-family: monospace;
            background: #1e1e2e;
            color: #fff;
            padding: 15px;
            border-radius: 12px;
            font-size: 0.85rem;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        /* نوتیفیکیشن */
        .toast-notify {
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background: #333;
            color: white;
            padding: 15px 20px;
            border-radius: 12px;
            text-align: center;
            z-index: 1000;
            animation: fadeInUp 0.3s ease;
            display: none;
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(50px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* ربات کارت */
        .bot-card {
            background: white;
            border-radius: 16px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: all 0.3s;
            border: 1px solid #eee;
        }
        .bot-card:hover {
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transform: translateX(-5px);
        }
        
        /* سایدبار موبایل */
        .mobile-menu {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            display: flex;
            justify-content: space-around;
            padding: 12px 20px;
            box-shadow: 0 -2px 20px rgba(0,0,0,0.1);
            border-radius: 25px 25px 0 0;
            z-index: 100;
        }
        .mobile-menu a {
            text-align: center;
            color: #666;
            text-decoration: none;
            font-size: 0.75rem;
        }
        .mobile-menu a i { font-size: 1.5rem; display: block; margin-bottom: 5px; }
        .mobile-menu a.active { color: #667eea; }
        
        @media (min-width: 768px) {
            .mobile-menu { display: none; }
            body { padding-bottom: 20px; }
        }
        @media (max-width: 767px) {
            body { padding-bottom: 80px; }
        }
        
        /* لودر */
        .loader {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>

<div class="container">
    <!-- هدر -->
    <div class="header animate-fade">
        <i class="fas fa-robot" style="font-size: 48px; margin-bottom: 15px;"></i>
        <h1>🤖 ساخت ربات تلگرام</h1>
        <p class="mb-0">به سادگی ربات تلگرام خود را بسازید و اجرا کنید</p>
    </div>

    <!-- محتوای اصلی -->
    <div id="app">
        <!-- صفحه لاگین -->
        <div id="loginPage" style="display: none;">
            <div class="card animate-fade">
                <div class="card-body p-4">
                    <h3 class="text-center mb-4">
                        <i class="fab fa-telegram me-2"></i>
                        ورود با تلگرام
                    </h3>
                    <p class="text-center text-muted mb-4">
                        برای استفاده از سرویس، باید با حساب تلگرام خود وارد شوید
                    </p>
                    <div class="text-center">
                        <a href="/auth/telegram" class="btn btn-primary btn-lg">
                            <i class="fab fa-telegram me-2"></i>
                            ورود با تلگرام
                        </a>
                    </div>
                </div>
            </div>
        </div>

        <!-- صفحه اصلی -->
        <div id="mainPage" style="display: none;">
            <!-- نوار ابزار -->
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h3 class="mb-0">
                        <i class="fas fa-user-circle me-2"></i>
                        خوش آمدید، <span id="userName">کاربر</span>
                    </h3>
                    <small class="text-muted" id="userStatus"></small>
                </div>
                <button class="btn btn-outline-danger" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i>
                    خروج
                </button>
            </div>

            <!-- کارت وضعیت -->
            <div class="row g-4 mb-4">
                <div class="col-md-3 col-6">
                    <div class="card text-center p-3">
                        <i class="fas fa-wallet" style="font-size: 28px; color: #667eea;"></i>
                        <h4 class="mt-2 mb-0" id="walletBalance">0</h4>
                        <small class="text-muted">تومان</small>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="card text-center p-3">
                        <i class="fas fa-calendar-check" style="font-size: 28px; color: #28a745;"></i>
                        <h4 class="mt-2 mb-0" id="subStatus">غیرفعال</h4>
                        <small class="text-muted">وضعیت اشتراک</small>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="card text-center p-3">
                        <i class="fas fa-robot" style="font-size: 28px; color: #764ba2;"></i>
                        <h4 class="mt-2 mb-0" id="botsCount">0</h4>
                        <small class="text-muted">ربات‌ها</small>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="card text-center p-3">
                        <i class="fas fa-chart-line" style="font-size: 28px; color: #ffc107;"></i>
                        <h4 class="mt-2 mb-0" id="remainingBots">0</h4>
                        <small class="text-muted">ظرفیت باقی‌مانده</small>
                    </div>
                </div>
            </div>

            <!-- تب‌ها -->
            <ul class="nav nav-tabs mb-4" id="myTab" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="build-tab" data-bs-toggle="tab" data-bs-target="#build" type="button" role="tab">
                        <i class="fas fa-plus-circle me-1"></i> ساخت ربات
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="bots-tab" data-bs-toggle="tab" data-bs-target="#bots" type="button" role="tab">
                        <i class="fas fa-list me-1"></i> ربات‌های من
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="wallet-tab" data-bs-toggle="tab" data-bs-target="#wallet" type="button" role="tab">
                        <i class="fas fa-coins me-1"></i> کیف پول
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="guide-tab" data-bs-toggle="tab" data-bs-target="#guide" type="button" role="tab">
                        <i class="fas fa-book me-1"></i> راهنما
                    </button>
                </li>
            </ul>

            <div class="tab-content">
                <!-- تب ساخت ربات -->
                <div class="tab-pane fade show active" id="build" role="tabpanel">
                    <div class="card">
                        <div class="card-body p-4">
                            <h5 class="mb-3">
                                <i class="fas fa-code me-2"></i>
                                ساخت ربات جدید
                            </h5>
                            
                            <!-- هشدار ظرفیت -->
                            <div id="capacityWarning" class="alert alert-warning" style="display: none;">
                                <i class="fas fa-exclamation-triangle me-2"></i>
                                <span></span>
                            </div>
                            
                            <!-- روش اول: آپلود فایل -->
                            <div class="mb-4">
                                <label class="form-label fw-bold">
                                    <i class="fas fa-upload me-2"></i>
                                    روش اول: آپلود فایل
                                </label>
                                <div class="border rounded-3 p-4 text-center" style="border-style: dashed !important;">
                                    <i class="fas fa-cloud-upload-alt" style="font-size: 48px; color: #667eea;"></i>
                                    <p class="mt-2 mb-2">فایل .py یا .zip خود را انتخاب کنید</p>
                                    <small class="text-muted">حداکثر حجم: 50 مگابایت</small>
                                    <input type="file" id="botFile" class="form-control mt-3" accept=".py,.zip" style="display: none;">
                                    <button class="btn btn-primary mt-3" onclick="document.getElementById('botFile').click()">
                                        <i class="fas fa-folder-open me-2"></i>
                                        انتخاب فایل
                                    </button>
                                </div>
                                <div id="fileUploadProgress" class="mt-2" style="display: none;">
                                    <div class="progress-custom progress">
                                        <div class="progress-bar" style="width: 0%"></div>
                                    </div>
                                    <small class="text-muted">در حال آپلود...</small>
                                </div>
                            </div>
                            
                            <hr>
                            
                            <!-- روش دوم: کد مستقیم -->
                            <div>
                                <label class="form-label fw-bold">
                                    <i class="fas fa-edit me-2"></i>
                                    روش دوم: وارد کردن کد مستقیم
                                </label>
                                <textarea id="botCode" class="form-control code-area" rows="8" placeholder="# کد ربات خود را اینجا وارد کنید
import telebot
bot = telebot.TeleBot('YOUR_BOT_TOKEN')

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 'سلام! ربات من ساخته شد!')

bot.infinity_polling()"></textarea>
                                <div class="mt-2">
                                    <small class="text-muted">
                                        <i class="fas fa-info-circle"></i>
                                        توکن ربات را در کد قرار دهید (مانند 'YOUR_BOT_TOKEN')
                                    </small>
                                </div>
                            </div>
                            
                            <div class="mt-4">
                                <button class="btn btn-primary w-100" onclick="buildBot()" id="buildBtn">
                                    <i class="fas fa-microchip me-2"></i>
                                    ساخت ربات
                                </button>
                            </div>
                            
                            <div id="buildStatus" class="mt-3" style="display: none;">
                                <div class="alert" id="buildAlert"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- تب ربات‌های من -->
                <div class="tab-pane fade" id="bots" role="tabpanel">
                    <div class="card">
                        <div class="card-body p-4">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h5 class="mb-0">
                                    <i class="fas fa-robot me-2"></i>
                                    لیست ربات‌های شما
                                </h5>
                                <button class="btn btn-sm btn-outline-primary" onclick="loadBots()">
                                    <i class="fas fa-sync-alt"></i>
                                </button>
                            </div>
                            <div id="botsList">
                                <div class="text-center py-4">
                                    <div class="loader"></div>
                                    <p class="mt-2 text-muted">در حال بارگذاری...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- تب کیف پول -->
                <div class="tab-pane fade" id="wallet" role="tabpanel">
                    <div class="card">
                        <div class="card-body p-4">
                            <h5 class="mb-3">
                                <i class="fas fa-wallet me-2"></i>
                                کیف پول و اشتراک
                            </h5>
                            
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="bg-light p-3 rounded-3 mb-3">
                                        <small class="text-muted">موجودی کیف پول</small>
                                        <h3 id="walletDetail" class="mb-0">0 تومان</h3>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="bg-light p-3 rounded-3 mb-3">
                                        <small class="text-muted">وضعیت اشتراک</small>
                                        <h3 id="subDetail" class="mb-0">❌ غیرفعال</h3>
                                        <small id="expiryDetail" class="text-muted"></small>
                                    </div>
                                </div>
                            </div>
                            
                            <hr>
                            
                            <h6 class="mb-3">خرید اشتراک ماهیانه</h6>
                            <div class="alert alert-info">
                                <i class="fas fa-info-circle me-2"></i>
                                هزینه اشتراک: <strong id="priceDisplay"></strong>
                            </div>
                            
                            <div id="paymentInfo" class="border rounded-3 p-3 mb-3">
                                <p class="mb-1"><i class="fas fa-credit-card me-2"></i> شماره کارت:</p>
                                <code class="d-block p-2 bg-light rounded" id="cardNumber"></code>
                                <p class="mb-1 mt-2"><i class="fas fa-user me-2"></i> نام دارنده حساب:</p>
                                <code class="d-block p-2 bg-light rounded" id="cardHolder"></code>
                                <p class="mb-1 mt-2"><i class="fas fa-university me-2"></i> بانک:</p>
                                <code class="d-block p-2 bg-light rounded" id="cardBank"></code>
                            </div>
                            
                            <p class="text-muted small">
                                <i class="fas fa-camera me-1"></i>
                                پس از واریز، تصویر تراکنش را از بخش ساخت ربات ارسال کنید
                            </p>
                        </div>
                    </div>
                </div>
                
                <!-- تب راهنما -->
                <div class="tab-pane fade" id="guide" role="tabpanel">
                    <div class="card">
                        <div class="card-body p-4">
                            <h5 class="mb-3">
                                <i class="fas fa-graduation-cap me-2"></i>
                                راهنمای ساخت ربات
                            </h5>
                            <div id="guideContent">
                                <div class="alert alert-info">
                                    <i class="fas fa-spinner fa-spin me-2"></i>
                                    در حال بارگذاری...
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- منوی موبایل -->
<div class="mobile-menu">
    <a href="#" onclick="switchTab('build')">
        <i class="fas fa-plus-circle"></i>
        <span>ساخت</span>
    </a>
    <a href="#" onclick="switchTab('bots')">
        <i class="fas fa-robot"></i>
        <span>ربات‌ها</span>
    </a>
    <a href="#" onclick="switchTab('wallet')">
        <i class="fas fa-wallet"></i>
        <span>کیف پول</span>
    </a>
    <a href="#" onclick="switchTab('guide')">
        <i class="fas fa-book"></i>
        <span>راهنما</span>
    </a>
</div>

<!-- نوتیفیکیشن -->
<div id="toast" class="toast-notify"></div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    let currentUser = null;
    let activeTab = 'build';
    
    // تابع نمایش نوتیفیکیشن
    function showToast(message, isError = false) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.style.backgroundColor = isError ? '#dc3545' : '#28a745';
        toast.style.display = 'block';
        setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    }
    
    // چک کردن وضعیت لاگین
    async function checkAuth() {
        try {
            const res = await fetch('/api/me');
            if (res.ok) {
                const data = await res.json();
                currentUser = data;
                document.getElementById('userName').textContent = data.first_name || 'کاربر';
                document.getElementById('userStatus').innerHTML = data.subscription_active ? 
                    '<span class="text-success">✅ اشتراک فعال</span>' : 
                    '<span class="text-danger">❌ اشتراک غیرفعال</span>';
                document.getElementById('walletBalance').textContent = data.wallet_balance.toLocaleString();
                document.getElementById('botsCount').textContent = data.bots_count;
                document.getElementById('remainingBots').textContent = data.remaining_bots;
                document.getElementById('subStatus').innerHTML = data.subscription_active ? 
                    '<span class="text-success">فعال</span>' : '<span class="text-danger">غیرفعال</span>';
                
                document.getElementById('loginPage').style.display = 'none';
                document.getElementById('mainPage').style.display = 'block';
                
                // بارگذاری داده‌ها
                loadBots();
                loadWalletDetails();
                loadGuide();
                
                // بررسی ظرفیت
                if (data.remaining_bots <= 0 && !data.subscription_active) {
                    document.getElementById('capacityWarning').style.display = 'block';
                    document.getElementById('capacityWarning').querySelector('span').textContent = 
                        '⚠️ ظرفیت ساخت ربات شما تکمیل شده است. لطفاً اشتراک خود را فعال کنید.';
                } else if (data.remaining_bots <= 0) {
                    document.getElementById('capacityWarning').style.display = 'block';
                    document.getElementById('capacityWarning').querySelector('span').textContent = 
                        '⚠️ به حداکثر تعداد ربات مجاز رسیده‌اید. برای ساخت ربات جدید، یکی از ربات‌های خود را حذف کنید.';
                } else {
                    document.getElementById('capacityWarning').style.display = 'none';
                }
            } else {
                document.getElementById('loginPage').style.display = 'block';
                document.getElementById('mainPage').style.display = 'none';
            }
        } catch (err) {
            console.error(err);
            document.getElementById('loginPage').style.display = 'block';
            document.getElementById('mainPage').style.display = 'none';
        }
    }
    
    // بارگذاری ربات‌ها
    async function loadBots() {
        try {
            const res = await fetch('/api/bots');
            if (res.ok) {
                const bots = await res.json();
                const container = document.getElementById('botsList');
                
                if (bots.length === 0) {
                    container.innerHTML = `
                        <div class="text-center py-5">
                            <i class="fas fa-robot" style="font-size: 48px; color: #ccc;"></i>
                            <p class="mt-3 text-muted">هنوز رباتی نساخته‌اید</p>
                            <button class="btn btn-primary btn-sm" onclick="switchTab('build')">
                                <i class="fas fa-plus-circle me-1"></i> ساخت ربات جدید
                            </button>
                        </div>
                    `;
                    return;
                }
                
                let html = '';
                for (const bot of bots) {
                    const isRunning = bot.status === 'running';
                    html += `
                        <div class="bot-card">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6 class="mb-1">
                                        <i class="fab fa-telegram me-1"></i>
                                        ${bot.name || bot.username || 'ربات'}
                                    </h6>
                                    <small class="text-muted d-block">@${bot.username || 'نامشخص'}</small>
                                    <span class="status-badge ${isRunning ? 'status-running' : 'status-stopped'} mt-2">
                                        ${isRunning ? '🟢 فعال' : '🔴 متوقف'}
                                    </span>
                                </div>
                                <div>
                                    <button class="btn btn-sm btn-outline-${isRunning ? 'warning' : 'success'} me-1" 
                                            onclick="toggleBot('${bot.id}')">
                                        <i class="fas fa-${isRunning ? 'pause' : 'play'}"></i>
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" 
                                            onclick="deleteBot('${bot.id}', '${bot.name}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                            ${bot.error_message ? `<small class="text-danger d-block mt-2"><i class="fas fa-exclamation-triangle"></i> خطا: ${bot.error_message.substring(0, 50)}</small>` : ''}
                        </div>
                    `;
                }
                container.innerHTML = html;
            }
        } catch (err) {
            console.error(err);
            document.getElementById('botsList').innerHTML = '<div class="alert alert-danger">خطا در بارگذاری ربات‌ها</div>';
        }
    }
    
    // تغییر وضعیت ربات
    async function toggleBot(botId) {
        try {
            const res = await fetch('/api/bots/' + botId + '/toggle', { method: 'POST' });
            const data = await res.json();
            if (res.ok) {
                showToast(data.message);
                loadBots();
            } else {
                showToast(data.error || 'خطا', true);
            }
        } catch (err) {
            showToast('خطا در ارتباط با سرور', true);
        }
    }
    
    // حذف ربات
    async function deleteBot(botId, botName) {
        if (!confirm(`آیا از حذف ربات "${botName}" اطمینان دارید؟`)) return;
        
        try {
            const res = await fetch('/api/bots/' + botId, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok) {
                showToast('ربات با موفقیت حذف شد');
                loadBots();
                checkAuth(); // به‌روزرسانی آمار
            } else {
                showToast(data.error || 'خطا', true);
            }
        } catch (err) {
            showToast('خطا در ارتباط با سرور', true);
        }
    }
    
    // ساخت ربات
    async function buildBot() {
        const buildBtn = document.getElementById('buildBtn');
        const buildStatus = document.getElementById('buildStatus');
        const buildAlert = document.getElementById('buildAlert');
        
        // بررسی اشتراک
        if (currentUser && currentUser.remaining_bots <= 0 && !currentUser.subscription_active) {
            showToast('ابتدا باید اشتراک خود را فعال کنید!', true);
            switchTab('wallet');
            return;
        }
        
        let code = document.getElementById('botCode').value;
        const fileInput = document.getElementById('botFile');
        
        if (!code.trim() && (!fileInput.files || fileInput.files.length === 0)) {
            showToast('لطفاً کد ربات را وارد کنید یا فایل را آپلود کنید', true);
            return;
        }
        
        buildBtn.disabled = true;
        buildBtn.innerHTML = '<span class="loader me-2"></span> در حال ساخت...';
        buildStatus.style.display = 'block';
        buildAlert.className = 'alert alert-info';
        buildAlert.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> در حال پردازش... لطفاً صبر کنید';
        
        try {
            let response;
            
            if (fileInput.files && fileInput.files.length > 0) {
                // آپلود فایل
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                response = await fetch('/api/build/upload', { method: 'POST', body: formData });
            } else {
                // ارسال کد
                response = await fetch('/api/build/code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: code })
                });
            }
            
            const data = await response.json();
            
            if (response.ok) {
                buildAlert.className = 'alert alert-success';
                buildAlert.innerHTML = `
                    <i class="fas fa-check-circle me-2"></i>
                    ✅ ربات با موفقیت ساخته شد!<br>
                    🤖 نام: ${data.bot_name || 'ربات'}<br>
                    🔗 لینک: <a href="https://t.me/${data.username}" target="_blank">t.me/${data.username}</a>
                `;
                showToast('ربات با موفقیت ساخته شد!');
                document.getElementById('botCode').value = '';
                fileInput.value = '';
                checkAuth();
                loadBots();
                switchTab('bots');
            } else {
                buildAlert.className = 'alert alert-danger';
                buildAlert.innerHTML = `<i class="fas fa-times-circle me-2"></i> خطا: ${data.error || 'مشخص نشده'}`;
                showToast(data.error || 'خطا در ساخت ربات', true);
            }
        } catch (err) {
            buildAlert.className = 'alert alert-danger';
            buildAlert.innerHTML = `<i class="fas fa-times-circle me-2"></i> خطا: ${err.message}`;
            showToast('خطا در ارتباط با سرور', true);
        } finally {
            buildBtn.disabled = false;
            buildBtn.innerHTML = '<i class="fas fa-microchip me-2"></i> ساخت ربات';
        }
    }
    
    // بارگذاری جزئیات کیف پول
    async function loadWalletDetails() {
        try {
            const res = await fetch('/api/wallet');
            if (res.ok) {
                const data = await res.json();
                document.getElementById('walletDetail').innerHTML = data.balance.toLocaleString() + ' تومان';
                document.getElementById('subDetail').innerHTML = data.subscription_active ? '✅ فعال' : '❌ غیرفعال';
                document.getElementById('expiryDetail').innerHTML = data.expiry_date ? `اعتبار تا: ${data.expiry_date}` : '';
                document.getElementById('priceDisplay').innerHTML = data.price_str;
                document.getElementById('cardNumber').innerHTML = data.card_number;
                document.getElementById('cardHolder').innerHTML = data.card_holder;
                document.getElementById('cardBank').innerHTML = data.card_bank;
            }
        } catch (err) {
            console.error(err);
        }
    }
    
    // بارگذاری راهنما
    async function loadGuide() {
        try {
            const res = await fetch('/api/guide');
            if (res.ok) {
                const data = await res.json();
                document.getElementById('guideContent').innerHTML = `
                    <div class="bg-light p-3 rounded-3">
                        ${data.guide_text.replace(/\\n/g, '<br>')}
                    </div>
                `;
            }
        } catch (err) {
            document.getElementById('guideContent').innerHTML = '<div class="alert alert-danger">خطا در بارگذاری راهنما</div>';
        }
    }
    
    // تغییر تب
    function switchTab(tab) {
        activeTab = tab;
        const tabEl = document.querySelector(`#${tab}-tab`);
        if (tabEl) {
            const tabTrigger = new bootstrap.Tab(tabEl);
            tabTrigger.show();
        }
    }
    
    // خروج
    async function logout() {
        await fetch('/api/logout', { method: 'POST' });
        sessionStorage.clear();
        window.location.reload();
    }
    
    // آپلود فایل
    document.getElementById('botFile').addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            if (file.size > 50 * 1024 * 1024) {
                showToast('حجم فایل نباید بیشتر از 50 مگابایت باشد', true);
                e.target.value = '';
                return;
            }
            showToast(`فایل ${file.name} انتخاب شد`);
            document.getElementById('botCode').value = '';
        }
    });
    
    // شروع
    checkAuth();
    
    // رفرش خودکار هر 30 ثانیه
    setInterval(() => {
        if (currentUser) {
            checkAuth();
            if (activeTab === 'bots') loadBots();
        }
    }, 30000);
</script>
</body>
</html>
'''

# ==================== مسیرهای API ====================

@app.route('/')
def index():
    """صفحه اصلی"""
    return HTML_TEMPLATE

@app.route('/auth/telegram')
def auth_telegram():
    """ورود با تلگرام - ریدایرکت به ربات"""
    return redirect(f"https://t.me/{BOT_USERNAME}?start=web")

@app.route('/api/me')
def api_me():
    """دریافت اطلاعات کاربر فعلی"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = get_user(user_id)
    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 401
    
    return jsonify({
        'user_id': user['user_id'],
        'first_name': user.get('first_name', ''),
        'username': user.get('username', ''),
        'wallet_balance': user.get('wallet_balance', 0),
        'bots_count': user.get('bots_count', 0),
        'subscription_active': check_subscription(user_id),
        'remaining_bots': get_remaining_bots(user_id),
        'max_bots': get_setting('max_bots_per_subscription')
    })

@app.route('/api/bots')
@login_required
def api_bots():
    """دریافت لیست ربات‌های کاربر"""
    user_id = session['user_id']
    bots = get_user_bots(user_id)
    
    result = []
    for bot in bots:
        status = machine_manager.get_status(bot['id'])
        result.append({
            'id': bot['id'],
            'name': bot.get('name', ''),
            'username': bot.get('username', ''),
            'status': 'running' if status.get('running') else 'stopped',
            'created_at': bot.get('created_at', ''),
            'error_message': bot.get('error_message', '')
        })
    
    return jsonify(result)

@app.route('/api/bots/<bot_id>/toggle', methods=['POST'])
@login_required
def api_toggle_bot(bot_id):
    """تغییر وضعیت ربات"""
    user_id = session['user_id']
    bot_rec = get_bot(bot_id)
    
    if not bot_rec or bot_rec['user_id'] != user_id:
        return jsonify({'error': 'ربات یافت نشد'}), 404
    
    status = machine_manager.get_status(bot_id)
    
    if status.get('running'):
        if machine_manager.stop_bot(bot_id):
            return jsonify({'message': 'ربات متوقف شد'})
        else:
            return jsonify({'error': 'خطا در توقف ربات'}), 500
    else:
        if os.path.exists(bot_rec['file_path']):
            with open(bot_rec['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
            token = bot_rec['token']
            if token:
                result = machine_manager.run_bot(bot_id, code, token)
                if result['success']:
                    db.execute("UPDATE bots SET machine_id = ?, pid = ?, status = 'running', error_message = NULL WHERE id = ?",
                              (result['machine_id'], result['pid'], bot_id))
                    return jsonify({'message': 'ربات راه‌اندازی شد'})
                else:
                    return jsonify({'error': result.get('error', 'خطا')}), 500
        return jsonify({'error': 'فایل ربات یافت نشد'}), 404

@app.route('/api/bots/<bot_id>', methods=['DELETE'])
@login_required
def api_delete_bot(bot_id):
    """حذف ربات"""
    user_id = session['user_id']
    if delete_bot(bot_id, user_id):
        return jsonify({'message': 'ربات حذف شد'})
    return jsonify({'error': 'خطا در حذف'}), 500

@app.route('/api/build/code', methods=['POST'])
@login_required
def api_build_code():
    """ساخت ربات با کد مستقیم"""
    user_id = session['user_id']
    data = request.get_json()
    code = data.get('code', '')
    
    return _process_build(user_id, code, None)

@app.route('/api/build/upload', methods=['POST'])
@login_required
def api_build_upload():
    """ساخت ربات با آپلود فایل"""
    user_id = session['user_id']
    
    if 'file' not in request.files:
        return jsonify({'error': 'فایلی ارسال نشده'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'فایلی انتخاب نشده'}), 400
    
    file_content = file.read()
    
    return _process_build(user_id, None, file_content, file.filename)

def _process_build(user_id, code_text, file_content, filename=None):
    """پردازش ساخت ربات"""
    # بررسی اشتراک
    can_create, reason = can_create_bot(user_id)
    if not can_create:
        if reason == "no_subscription":
            return jsonify({'error': 'ابتدا باید اشتراک خود را فعال کنید'}), 403
        return jsonify({'error': f'به حداکثر تعداد ربات مجاز ({get_setting("max_bots_per_subscription")}) رسیده‌اید'}), 403
    
    # بررسی محدودیت روزانه
    builds_today = rate_limiter.get_user_builds_today(user_id)
    max_builds = get_setting('max_builds_per_hour')
    if builds_today >= max_builds:
        return jsonify({'error': f'محدودیت ساخت امروز {max_builds} ربات است'}), 429
    
    try:
        # استخراج توکن از کد
        if code_text:
            token = extract_token_from_code(code_text)
            main_code = code_text
        else:
            # ذخیره فایل موقت
            temp_path = os.path.join(DIRS['TEMP'], f"web_{user_id}_{int(time.time())}_{filename}")
            with open(temp_path, 'wb') as f:
                f.write(file_content)
            
            if filename.endswith('.zip'):
                extract_dir = os.path.join(DIRS['TEMP'], f"web_extract_{user_id}_{int(time.time())}")
                os.makedirs(extract_dir, exist_ok=True)
                
                import zipfile
                with zipfile.ZipFile(temp_path, 'r') as zf:
                    zf.extractall(extract_dir)
                
                # پیدا کردن فایل اصلی
                main_code = ""
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        if f.endswith('.py'):
                            with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as code_f:
                                main_code = code_f.read()
                                break
                    if main_code:
                        break
                
                shutil.rmtree(extract_dir, ignore_errors=True)
            else:
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    main_code = f.read()
            
            os.remove(temp_path)
            token = extract_token_from_code(main_code)
        
        if not token:
            return jsonify({'error': 'توکن ربات در کد پیدا نشد'}), 400
        
        # اعتبارسنجی توکن
        try:
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            if resp.status_code != 200:
                return jsonify({'error': 'توکن ربات نامعتبر است'}), 400
            bot_info = resp.json()['result']
        except:
            return jsonify({'error': 'خطا در ارتباط با تلگرام'}), 500
        
        rate_limiter.increment_user_builds(user_id)
        bot_id = hashlib.md5(f"{user_id}{token}{time.time()}".encode()).hexdigest()[:16]
        
        # ذخیره فایل
        user_dir = os.path.join(DIRS['FILES'], str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{bot_id}.py")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(main_code)
        
        build_data = {
            'bot_id': bot_id,
            'user_id': user_id,
            'token': token,
            'bot_info': bot_info,
            'file_path': file_path,
            'main_code': main_code,
            'folder_path': None
        }
        
        # اضافه به صف ساخت (همگام برای وب)
        result = machine_manager.run_bot(bot_id, main_code, token)
        
        if result['success']:
            add_bot(
                user_id, bot_id, token, 
                bot_info.get('first_name', 'ربات'), 
                bot_info.get('username', ''), 
                file_path, 
                result['pid'], 
                result['machine_id']
            )
            
            return jsonify({
                'success': True,
                'bot_name': bot_info.get('first_name', 'ربات'),
                'username': bot_info.get('username', '')
            })
        else:
            return jsonify({'error': result.get('error', 'خطا در اجرای ربات')}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500

@app.route('/api/wallet')
@login_required
def api_wallet():
    """دریافت اطلاعات کیف پول"""
    user_id = session['user_id']
    user = get_user(user_id)
    
    return jsonify({
        'balance': user.get('wallet_balance', 0),
        'subscription_active': check_subscription(user_id),
        'expiry_date': user.get('subscription_expiry', ''),
        'price_str': get_setting('subscription_price_str'),
        'card_number': get_setting('card_number_display'),
        'card_holder': get_setting('card_holder'),
        'card_bank': get_setting('card_bank')
    })

@app.route('/api/guide')
@login_required
def api_guide():
    """دریافت راهنما"""
    lang = 'fa'
    guide_text = get_setting('guide_text_fa')
    return jsonify({'guide_text': guide_text})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """خروج از حساب"""
    session.clear()
    return jsonify({'message': 'Logged out'})

# ==================== تنظیم Session با دیتابیس ====================
def setup_webhook():
    """تنظیم webhook برای اتصال وب به ربات"""
    # این تابع برای لاگین از طریق ربات استفاده می‌شود
    pass

# ==================== اجرا ====================
def run_web_app(host='0.0.0.0', port=8080, debug=False):
    """اجرای وب‌اپ"""
    print("=" * 60)
    print("🌐 وب‌اپ ساخت ربات تلگرام")
    print(f"📍 آدرس: http://{host}:{port}")
    print(f"🔗 لاگین از طریق ربات: https://t.me/{BOT_USERNAME}")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == "__main__":
    run_web_app()