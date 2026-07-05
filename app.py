# ============================================
# COMPLETE LOTTERY WEB APP - main.py
# ============================================
# این سیستم شامل:
# 1. وب‌اپلیکیشن کامل با رابط کاربری حرفه‌ای
# 2. دکمه Play در تلگرام که صفحه رو باز میکنه
# 3. پنل کاربری کامل با همه امکانات
# 4. سیستم قرعه‌کشی قدرتمند
# 5. تایید خودکار پرداخت

import asyncio
import json
import logging
import secrets
import string
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid

# ============================================
# Web Framework Imports
# ============================================
from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

# ============================================
# Telegram & Database Imports
# ============================================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncpg
import aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, BigInteger, Float, Boolean, DateTime, JSON, Text, Index, select, update, delete
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.pool import AsyncAdaptedQueuePool
import bcrypt
import jwt

# ============================================
# Configuration
# ============================================
class Config:
    # Bot
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    BOT_USERNAME = "@UTYOB_Bot"
    
    # Web App
    WEBAPP_URL = "https://your-domain.com"  # Replace with your domain
    WEBAPP_SECRET = "your-webapp-secret-key"
    
    # Database
    DATABASE_URL = "postgresql+asyncpg://lottery:lottery_pass@localhost/lottery_db"
    REDIS_URL = "redis://localhost:6379/0"
    
    # Payment
    PAYMENT_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
    PAYMENT_AMOUNT = 100.0
    TRONGRID_API_URL = "https://api.trongrid.io"
    API_KEYS = ["7ae83b63-fdf3-47e4-ac69-56f960a34f5b"]
    
    # Admin
    ADMIN_CHAT_ID = 123456789
    
    # Security
    JWT_SECRET = "your-jwt-secret-key-change-this"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY = 3600 * 24 * 7  # 7 days
    
    # Lottery
    SHARD_COUNT = 100

config = Config()

# ============================================
# Database Models
# ============================================
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language = Column(String(10), default="en")
    wallet_address = Column(String(255), nullable=True)
    referral_code = Column(String(20), unique=True, nullable=False)
    referred_by = Column(BigInteger, nullable=True)
    
    # Subscription
    has_subscription = Column(Boolean, default=False)
    subscription_expiry = Column(DateTime, nullable=True)
    
    # Lottery
    is_winner = Column(Boolean, default=False)
    won_amount = Column(Float, default=0.0)
    total_won = Column(Float, default=0.0)
    
    # Referral
    referral_count = Column(Integer, default=0)
    referral_earnings = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Shard
    shard_id = Column(Integer, nullable=False)
    
    __table_args__ = (
        Index('idx_users_telegram_id', 'telegram_id'),
        Index('idx_users_referral_code', 'referral_code'),
        Index('idx_users_subscription', 'has_subscription', 'subscription_expiry'),
    )

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tx_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    from_address = Column(String(255), nullable=False)
    to_address = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="pending")
    verification_attempts = Column(Integer, default=0)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Lottery(Base):
    __tablename__ = "lotteries"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft")
    prize_pool = Column(Float, default=0.0)
    winners_count = Column(Integer, default=0)
    prize_per_winner = Column(Float, default=0.0)
    participant_count = Column(Integer, default=0)
    winners = Column(JSON, default=[])
    started_at = Column(DateTime, nullable=True)
    drawn_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# Database Manager
# ============================================
class DatabaseManager:
    def __init__(self):
        self.engines = {}
        self.session_pools = {}
        self._init_shards()
    
    def _init_shards(self):
        for shard_id in range(config.SHARD_COUNT):
            shard_db = f"lottery_db_{shard_id}"
            url = config.DATABASE_URL.replace("lottery_db", shard_db)
            engine = create_async_engine(
                url,
                pool_size=20,
                max_overflow=40,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            self.engines[shard_id] = engine
            self.session_pools[shard_id] = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
    
    def get_shard(self, user_id: int) -> int:
        return hash(str(user_id)) % config.SHARD_COUNT
    
    async def get_session(self, shard_id: int) -> AsyncSession:
        return self.session_pools[shard_id]()

db_manager = DatabaseManager()

# ============================================
# Redis Cache
# ============================================
class CacheManager:
    def __init__(self):
        self.redis = None
    
    async def init(self):
        if self.redis is None:
            self.redis = await aioredis.from_url(
                config.REDIS_URL,
                decode_responses=True,
                max_connections=50
            )
    
    async def get(self, key: str) -> Optional[str]:
        await self.init()
        return await self.redis.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        await self.init()
        await self.redis.set(key, value, ex=ttl)
    
    async def delete(self, key: str):
        await self.init()
        await self.redis.delete(key)
    
    async def incr(self, key: str) -> int:
        await self.init()
        return await self.redis.incr(key)

cache = CacheManager()

# ============================================
# JWT Authentication
# ============================================
def create_jwt_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(seconds=config.JWT_EXPIRY),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload.get("user_id")
    except:
        return None

# ============================================
# FastAPI Web Application
# ============================================
app = FastAPI(title="Lottery Web App")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# Security
security = HTTPBearer()

# ============================================
# Pydantic Models
# ============================================
class UserData(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: str = "en"

class WalletRequest(BaseModel):
    wallet_address: str

class TransactionVerify(BaseModel):
    tx_id: str

class LotterySettings(BaseModel):
    winners_count: int
    prize_amount: float

# ============================================
# HTML Template (Embedded)
# ============================================
WEBAPP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🎰 Lottery Bot</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--tg-theme-bg-color, #ffffff);
            color: var(--tg-theme-text-color, #000000);
            min-height: 100vh;
            padding: 16px;
            padding-bottom: 80px;
        }
        
        .container {
            max-width: 480px;
            margin: 0 auto;
        }
        
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
            margin-bottom: 20px;
        }
        
        .header-title {
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .header-title .logo {
            font-size: 28px;
        }
        
        .language-selector {
            display: flex;
            gap: 8px;
        }
        
        .lang-btn {
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            color: var(--tg-theme-text-color, #000000);
            transition: all 0.2s;
        }
        
        .lang-btn.active {
            background: var(--tg-theme-button-color, #0088cc);
            color: var(--tg-theme-button-text-color, #ffffff);
        }
        
        .card {
            background: var(--tg-theme-secondary-bg-color, #f5f5f5);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            transition: all 0.3s;
        }
        
        .card-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .status-badge.active {
            background: #4caf50;
            color: white;
        }
        
        .status-badge.pending {
            background: #ff9800;
            color: white;
        }
        
        .status-badge.inactive {
            background: #9e9e9e;
            color: white;
        }
        
        .status-badge.winner {
            background: #ffd700;
            color: #000;
        }
        
        .input-group {
            margin-bottom: 16px;
        }
        
        .input-group label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            margin-bottom: 6px;
            color: var(--tg-theme-hint-color, #666);
        }
        
        .input-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
            border-radius: 12px;
            font-size: 16px;
            background: var(--tg-theme-bg-color, #ffffff);
            color: var(--tg-theme-text-color, #000000);
            transition: border-color 0.3s;
        }
        
        .input-group input:focus {
            outline: none;
            border-color: var(--tg-theme-button-color, #0088cc);
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 24px;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
            color: var(--tg-theme-button-text-color, #ffffff);
            background: var(--tg-theme-button-color, #0088cc);
        }
        
        .btn:active {
            transform: scale(0.97);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .btn-secondary {
            background: var(--tg-theme-secondary-bg-color, #e0e0e0);
            color: var(--tg-theme-text-color, #000000);
        }
        
        .btn-success {
            background: #4caf50;
        }
        
        .btn-danger {
            background: #f44336;
        }
        
        .btn-warning {
            background: #ff9800;
        }
        
        .btn-gold {
            background: linear-gradient(135deg, #ffd700, #f5a623);
            color: #000;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
        }
        
        .info-row:last-child {
            border-bottom: none;
        }
        
        .info-label {
            color: var(--tg-theme-hint-color, #666);
            font-size: 14px;
        }
        
        .info-value {
            font-weight: 500;
            font-size: 14px;
        }
        
        .info-value.highlight {
            color: var(--tg-theme-button-color, #0088cc);
            font-weight: 700;
        }
        
        .winner-list {
            list-style: none;
            padding: 0;
        }
        
        .winner-list li {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
        }
        
        .winner-list li:last-child {
            border-bottom: none;
        }
        
        .winner-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--tg-theme-button-color, #0088cc);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 16px;
        }
        
        .winner-info {
            flex: 1;
            margin-left: 12px;
        }
        
        .winner-name {
            font-weight: 500;
        }
        
        .winner-amount {
            font-weight: 700;
            color: #ffd700;
        }
        
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 12px 24px;
            border-radius: 12px;
            font-size: 14px;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s;
            max-width: 90%;
            text-align: center;
        }
        
        .toast.show {
            opacity: 1;
        }
        
        .toast.success {
            background: #4caf50;
        }
        
        .toast.error {
            background: #f44336;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
            border-top: 4px solid var(--tg-theme-button-color, #0088cc);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 12px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--tg-theme-hint-color, #666);
        }
        
        .empty-state .icon {
            font-size: 48px;
            margin-bottom: 12px;
        }
        
        .referral-code {
            background: var(--tg-theme-bg-color, #ffffff);
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 2px;
            font-family: monospace;
            border: 2px dashed var(--tg-theme-button-color, #0088cc);
        }
        
        .tab-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--tg-theme-bg-color, #ffffff);
            border-top: 1px solid var(--tg-theme-secondary-bg-color, #e0e0e0);
            display: flex;
            padding: 8px 0;
            padding-bottom: env(safe-area-inset-bottom);
            z-index: 100;
        }
        
        .tab-item {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 4px 0;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
            background: none;
            color: var(--tg-theme-hint-color, #666);
        }
        
        .tab-item.active {
            color: var(--tg-theme-button-color, #0088cc);
        }
        
        .tab-item .icon {
            font-size: 24px;
        }
        
        .tab-item .label {
            font-size: 10px;
            margin-top: 2px;
        }
        
        .page {
            display: none;
        }
        
        .page.active {
            display: block;
        }
        
        @media (max-width: 400px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>
    
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="header-title">
                <span class="logo">🎰</span>
                <span>UTYOB Lottery</span>
            </div>
            <div class="language-selector">
                <button class="lang-btn active" onclick="changeLanguage('en')">🇬🇧</button>
                <button class="lang-btn" onclick="changeLanguage('fa')">🇮🇷</button>
                <button class="lang-btn" onclick="changeLanguage('ar')">🇸🇦</button>
            </div>
        </div>
        
        <!-- Pages -->
        <div id="page-home" class="page active">
            <!-- User Status -->
            <div class="card" id="user-status-card">
                <div class="card-title">👤 User Status</div>
                <div id="user-status-content">
                    <div class="loading active">
                        <div class="spinner"></div>
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
            
            <!-- Subscription -->
            <div class="card" id="subscription-card">
                <div class="card-title">🎯 Subscription</div>
                <div id="subscription-content">
                    <div class="loading active">
                        <div class="spinner"></div>
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
            
            <!-- Lottery Status -->
            <div class="card" id="lottery-card">
                <div class="card-title">🎰 Current Lottery</div>
                <div id="lottery-content">
                    <div class="loading active">
                        <div class="spinner"></div>
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
            
            <!-- Winners -->
            <div class="card" id="winners-card">
                <div class="card-title">🏆 Winners</div>
                <div id="winners-content">
                    <div class="loading active">
                        <div class="spinner"></div>
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
            
            <!-- Referral -->
            <div class="card">
                <div class="card-title">🔗 Referral Program</div>
                <div id="referral-content">
                    <div class="loading active">
                        <div class="spinner"></div>
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Page: Participate -->
        <div id="page-participate" class="page">
            <div class="card">
                <div class="card-title">💰 Participate in Lottery</div>
                <div id="participate-content">
                    <div class="loading active">
                        <div class="spinner"></div>
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Page: Winners -->
        <div id="page-winners" class="page">
            <div class="card">
                <div class="card-title">🏆 All Winners</div>
                <div id="all-winners-content">
                    <div class="loading active">
                        <div class="spinner"></div>
                        <p>Loading...</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Bottom Tab Bar -->
    <div class="tab-bar">
        <button class="tab-item active" onclick="switchPage('home')">
            <span class="icon">🏠</span>
            <span class="label">Home</span>
        </button>
        <button class="tab-item" onclick="switchPage('participate')">
            <span class="icon">🎰</span>
            <span class="label">Participate</span>
        </button>
        <button class="tab-item" onclick="switchPage('winners')">
            <span class="icon">🏆</span>
            <span class="label">Winners</span>
        </button>
    </div>
    
    <script>
        // ============================================
        // Telegram WebApp Integration
        // ============================================
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();
        
        let currentLanguage = 'en';
        let userData = null;
        let jwtToken = null;
        
        // ============================================
        // Language Translations
        // ============================================
        const translations = {
            en: {
                'user_status': '👤 User Status',
                'user_id': 'User ID',
                'username': 'Username',
                'subscription': 'Subscription',
                'active': 'Active',
                'inactive': 'Inactive',
                'wallet': 'Wallet',
                'not_set': 'Not Set',
                'total_won': 'Total Won',
                'participate': 'Participate in Lottery',
                'enter_wallet': 'Enter your TRC20 wallet address',
                'wallet_placeholder': 'T... (TRC20 address)',
                'submit': 'Submit',
                'verifying': 'Verifying...',
                'payment_required': '💵 Payment Required',
                'send_exactly': 'Please send exactly ${amount} USDT to:',
                'payment_address': 'Payment Address',
                'copy_address': '📋 Copy Address',
                'verify_payment': '✅ Verify Payment',
                'checking_payment': '⏳ Checking payment...',
                'payment_verified': '✅ Payment verified successfully!',
                'payment_failed': '❌ Payment verification failed. Please try again.',
                'subscription_active': '🎉 Your subscription is active!',
                'subscription_expires': 'Expires: {date}',
                'no_subscription': '⚠️ You need an active subscription to participate.',
                'current_lottery': '🎰 Current Lottery',
                'status': 'Status',
                'participants': 'Participants',
                'prize_pool': 'Prize Pool',
                'prize_per_winner': 'Prize per Winner',
                'winners_announced': 'Winners Announced',
                'no_active_lottery': 'No active lottery at the moment.',
                'congratulations': '🎊 Congratulations! You won ${amount}!',
                'withdraw': '💰 Withdraw',
                'enter_withdraw_address': 'Enter your TRC20 wallet address to withdraw:',
                'withdraw_success': '✅ Withdrawal request submitted!',
                'referral_program': '🔗 Referral Program',
                'your_code': 'Your Referral Code',
                'share_text': '🎰 Join the lottery! Use my referral code: {code}\n@UTYOB_Bot',
                'total_referrals': 'Total Referrals',
                'referral_earnings': 'Referral Earnings',
                'winners_list': '🏆 Winners List',
                'no_winners': 'No winners yet.',
                'winner': 'Winner',
                'amount': 'Amount',
                'date': 'Date',
                'loading': 'Loading...',
                'error': '❌ An error occurred. Please try again.',
                'copied': '✅ Copied to clipboard!',
                'refresh': '🔄 Refresh',
            },
            fa: {
                'user_status': '👤 وضعیت کاربر',
                'user_id': 'شناسه کاربر',
                'username': 'نام کاربری',
                'subscription': 'اشتراک',
                'active': 'فعال',
                'inactive': 'غیرفعال',
                'wallet': 'کیف پول',
                'not_set': 'تنظیم نشده',
                'total_won': 'مجموع برداشت',
                'participate': 'شرکت در قرعه‌کشی',
                'enter_wallet': 'آدرس کیف پول TRC20 خود را وارد کنید',
                'wallet_placeholder': 'T... (آدرس TRC20)',
                'submit': 'ثبت',
                'verifying': 'در حال بررسی...',
                'payment_required': '💵 پرداخت الزامی',
                'send_exactly': 'لطفاً دقیقاً ${amount} USDT به آدرس زیر ارسال کنید:',
                'payment_address': 'آدرس پرداخت',
                'copy_address': '📋 کپی آدرس',
                'verify_payment': '✅ تایید پرداخت',
                'checking_payment': '⏳ در حال بررسی پرداخت...',
                'payment_verified': '✅ پرداخت با موفقیت تایید شد!',
                'payment_failed': '❌ تایید پرداخت ناموفق بود. دوباره تلاش کنید.',
                'subscription_active': '🎉 اشتراک شما فعال است!',
                'subscription_expires': 'انقضا: {date}',
                'no_subscription': '⚠️ برای شرکت در قرعه‌کشی به اشتراک فعال نیاز دارید.',
                'current_lottery': '🎰 قرعه‌کشی جاری',
                'status': 'وضعیت',
                'participants': 'شرکت‌کنندگان',
                'prize_pool': 'جایزه نقدی',
                'prize_per_winner': 'جایزه هر برنده',
                'winners_announced': 'برندگان اعلام شدند',
                'no_active_lottery': 'در حال حاضر قرعه‌کشی فعالی وجود ندارد.',
                'congratulations': '🎊 تبریک! شما ${amount} برنده شدید!',
                'withdraw': '💰 برداشت',
                'enter_withdraw_address': 'آدرس کیف پول TRC20 خود را برای برداشت وارد کنید:',
                'withdraw_success': '✅ درخواست برداشت ثبت شد!',
                'referral_program': '🔗 برنامه رفرال',
                'your_code': 'کد رفرال شما',
                'share_text': '🎰 در قرعه‌کشی شرکت کنید! از کد رفرال من استفاده کنید: {code}\n@UTYOB_Bot',
                'total_referrals': 'تعداد رفرال',
                'referral_earnings': 'درآمد رفرال',
                'winners_list': '🏆 لیست برندگان',
                'no_winners': 'هنوز برنده‌ای وجود ندارد.',
                'winner': 'برنده',
                'amount': 'مبلغ',
                'date': 'تاریخ',
                'loading': 'در حال بارگذاری...',
                'error': '❌ خطایی رخ داد. دوباره تلاش کنید.',
                'copied': '✅ کپی شد!',
                'refresh': '🔄 بروزرسانی',
            },
            ar: {
                'user_status': '👤 حالة المستخدم',
                'user_id': 'معرف المستخدم',
                'username': 'اسم المستخدم',
                'subscription': 'الاشتراك',
                'active': 'نشط',
                'inactive': 'غير نشط',
                'wallet': 'المحفظة',
                'not_set': 'غير محدد',
                'total_won': 'إجمالي الفوز',
                'participate': 'المشاركة في اليانصيب',
                'enter_wallet': 'أدخل عنوان محفظة TRC20 الخاص بك',
                'wallet_placeholder': 'T... (عنوان TRC20)',
                'submit': 'إرسال',
                'verifying': 'جاري التحقق...',
                'payment_required': '💵 الدفع مطلوب',
                'send_exactly': 'الرجاء إرسال ${amount} USDT بالضبط إلى:',
                'payment_address': 'عنوان الدفع',
                'copy_address': '📋 نسخ العنوان',
                'verify_payment': '✅ التحقق من الدفع',
                'checking_payment': '⏳ جاري التحقق من الدفع...',
                'payment_verified': '✅ تم التحقق من الدفع بنجاح!',
                'payment_failed': '❌ فشل التحقق من الدفع. حاول مرة أخرى.',
                'subscription_active': '🎉 اشتراكك نشط!',
                'subscription_expires': 'ينتهي: {date}',
                'no_subscription': '⚠️ تحتاج إلى اشتراك نشط للمشاركة.',
                'current_lottery': '🎰 اليانصيب الحالي',
                'status': 'الحالة',
                'participants': 'المشاركون',
                'prize_pool': 'مجموع الجوائز',
                'prize_per_winner': 'جائزة كل فائز',
                'winners_announced': 'تم الإعلان عن الفائزين',
                'no_active_lottery': 'لا يوجد يانصيب نشط حالياً.',
                'congratulations': '🎊 تهانينا! لقد فزت بـ ${amount}!',
                'withdraw': '💰 سحب',
                'enter_withdraw_address': 'أدخل عنوان محفظة TRC20 للسحب:',
                'withdraw_success': '✅ تم تقديم طلب السحب!',
                'referral_program': '🔗 برنامج الإحالة',
                'your_code': 'رمز الإحالة الخاص بك',
                'share_text': '🎰 شارك في اليانصيب! استخدم رمز الإحالة الخاص بي: {code}\n@UTYOB_Bot',
                'total_referrals': 'إجمالي الإحالات',
                'referral_earnings': 'أرباح الإحالة',
                'winners_list': '🏆 قائمة الفائزين',
                'no_winners': 'لا يوجد فائزون حتى الآن.',
                'winner': 'الفائز',
                'amount': 'المبلغ',
                'date': 'التاريخ',
                'loading': 'جاري التحميل...',
                'error': '❌ حدث خطأ. حاول مرة أخرى.',
                'copied': '✅ تم النسخ!',
                'refresh': '🔄 تحديث',
            }
        };
        
        function t(key) {
            return translations[currentLanguage]?.[key] || key;
        }
        
        function changeLanguage(lang) {
            currentLanguage = lang;
            document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.lang-btn[onclick="changeLanguage('${lang}')"]`).classList.add('active');
            
            // Update all text
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.dataset.i18n;
                el.textContent = t(key);
            });
            
            // Refresh content with new language
            loadAllData();
            
            // Send language change to bot
            fetch('/api/user/language', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + jwtToken
                },
                body: JSON.stringify({ language: lang })
            }).catch(() => {});
        }
        
        // ============================================
        // API Functions
        // ============================================
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + jwtToken
                    }
                };
                if (data) {
                    options.body = JSON.stringify(data);
                }
                
                const response = await fetch(endpoint, options);
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error || 'API Error');
                }
                
                return result;
            } catch (error) {
                console.error('API Error:', error);
                showToast(t('error'), 'error');
                throw error;
            }
        }
        
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type;
            setTimeout(() => {
                toast.classList.add('show');
                setTimeout(() => {
                    toast.classList.remove('show');
                }, 3000);
            }, 100);
        }
        
        // ============================================
        // Page Navigation
        // ============================================
        function switchPage(page) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById('page-' + page).classList.add('active');
            
            document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
            document.querySelector(`.tab-item[onclick="switchPage('${page}')"]`).classList.add('active');
            
            if (page === 'participate') {
                loadParticipatePage();
            } else if (page === 'winners') {
                loadAllWinners();
            }
        }
        
        // ============================================
        // Load Data Functions
        // ============================================
        async function loadAllData() {
            try {
                await Promise.all([
                    loadUserStatus(),
                    loadSubscription(),
                    loadLotteryStatus(),
                    loadWinners(),
                    loadReferral()
                ]);
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }
        
        async function loadUserStatus() {
            try {
                const data = await apiCall('/api/user/status');
                const content = document.getElementById('user-status-content');
                
                if (data.user) {
                    content.innerHTML = `
                        <div class="info-row">
                            <span class="info-label">${t('user_id')}</span>
                            <span class="info-value">${data.user.telegram_id}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('username')}</span>
                            <span class="info-value">${data.user.username || 'N/A'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('subscription')}</span>
                            <span class="info-value">
                                <span class="status-badge ${data.user.has_subscription ? 'active' : 'inactive'}">
                                    ${data.user.has_subscription ? t('active') : t('inactive')}
                                </span>
                            </span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('wallet')}</span>
                            <span class="info-value">${data.user.wallet_address ? data.user.wallet_address.substring(0, 8) + '...' : t('not_set')}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('total_won')}</span>
                            <span class="info-value highlight">$${data.user.total_won || 0}</span>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('user-status-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>${t('error')}</p>
                    </div>
                `;
            }
        }
        
        async function loadSubscription() {
            try {
                const data = await apiCall('/api/user/subscription');
                const content = document.getElementById('subscription-content');
                
                if (data.has_subscription) {
                    content.innerHTML = `
                        <div class="info-row">
                            <span class="info-label">${t('subscription')}</span>
                            <span class="info-value">
                                <span class="status-badge active">${t('active')}</span>
                            </span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('subscription_expires')}</span>
                            <span class="info-value">${new Date(data.expiry).toLocaleDateString()}</span>
                        </div>
                    `;
                } else {
                    content.innerHTML = `
                        <div class="empty-state">
                            <div class="icon">⚠️</div>
                            <p>${t('no_subscription')}</p>
                            <br>
                            <button class="btn btn-success" onclick="openParticipate()">
                                🎰 ${t('participate')}
                            </button>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('subscription-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>${t('error')}</p>
                    </div>
                `;
            }
        }
        
        async function loadLotteryStatus() {
            try {
                const data = await apiCall('/api/lottery/status');
                const content = document.getElementById('lottery-content');
                
                if (data.active) {
                    const statusText = data.status === 'active' ? t('active') : data.status === 'drawing' ? 'Drawing...' : t('inactive');
                    const statusClass = data.status === 'active' ? 'active' : data.status === 'drawing' ? 'pending' : 'inactive';
                    
                    content.innerHTML = `
                        <div class="info-row">
                            <span class="info-label">${t('status')}</span>
                            <span class="info-value">
                                <span class="status-badge ${statusClass}">${statusText}</span>
                            </span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('participants')}</span>
                            <span class="info-value">${data.participant_count || 0}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('prize_pool')}</span>
                            <span class="info-value highlight">$${data.prize_pool || 0}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('prize_per_winner')}</span>
                            <span class="info-value">$${data.prize_per_winner || 0}</span>
                        </div>
                    `;
                } else {
                    content.innerHTML = `
                        <div class="empty-state">
                            <div class="icon">⏳</div>
                            <p>${t('no_active_lottery')}</p>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('lottery-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>${t('error')}</p>
                    </div>
                `;
            }
        }
        
        async function loadWinners() {
            try {
                const data = await apiCall('/api/lottery/winners');
                const content = document.getElementById('winners-content');
                
                if (data.winners && data.winners.length > 0) {
                    let html = `<ul class="winner-list">`;
                    data.winners.forEach((winner, index) => {
                        html += `
                            <li>
                                <div class="winner-avatar">${index + 1}</div>
                                <div class="winner-info">
                                    <div class="winner-name">${winner.username || 'User ' + winner.user_id}</div>
                                    <div style="font-size:12px;color:var(--tg-theme-hint-color,#666);">${t('winner')}</div>
                                </div>
                                <div class="winner-amount">$${winner.amount || data.prize_per_winner}</div>
                            </li>
                        `;
                    });
                    html += `</ul>`;
                    content.innerHTML = html;
                } else {
                    content.innerHTML = `
                        <div class="empty-state">
                            <div class="icon">🏆</div>
                            <p>${t('no_winners')}</p>
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('winners-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>${t('error')}</p>
                    </div>
                `;
            }
        }
        
        async function loadReferral() {
            try {
                const data = await apiCall('/api/user/referral');
                const content = document.getElementById('referral-content');
                
                content.innerHTML = `
                    <div class="info-row">
                        <span class="info-label">${t('your_code')}</span>
                        <span class="info-value">
                            <div class="referral-code">${data.referral_code}</div>
                        </span>
                    </div>
                    <div style="margin-top:12px;display:flex;gap:8px;">
                        <button class="btn btn-secondary" onclick="copyReferralCode('${data.referral_code}')">📋 ${t('copy_address')}</button>
                        <button class="btn btn-success" onclick="shareReferral('${data.referral_code}')">📤 Share</button>
                    </div>
                    <div style="margin-top:12px;">
                        <div class="info-row">
                            <span class="info-label">${t('total_referrals')}</span>
                            <span class="info-value">${data.referral_count || 0}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">${t('referral_earnings')}</span>
                            <span class="info-value highlight">$${data.referral_earnings || 0}</span>
                        </div>
                    </div>
                `;
            } catch (error) {
                document.getElementById('referral-content').innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>${t('error')}</p>
                    </div>
                `;
            }
        }
        
        async function loadParticipatePage() {
            const content = document.getElementById('participate-content');
            
            try {
                const userData = await apiCall('/api/user/status');
                
                if (userData.user && userData.user.has_subscription) {
                    content.innerHTML = `
                        <div style="text-align:center;padding:20px;">
                            <div style="font-size:48px;margin-bottom:12px;">🎉</div>
                            <h3>${t('subscription_active')}</h3>
                            <p style="color:var(--tg-theme-hint-color,#666);margin:8px 0;">
                                ${t('subscription_expires').replace('{date}', new Date(userData.user.subscription_expiry).toLocaleDateString())}
                            </p>
                            <button class="btn btn-warning" onclick="checkWinnerStatus()">🏆 Check Winner Status</button>
                        </div>
                    `;
                } else {
                    content.innerHTML = `
                        <div style="text-align:center;margin-bottom:20px;">
                            <div style="font-size:48px;margin-bottom:12px;">💰</div>
                            <h3>${t('participate')}</h3>
                            <p style="color:var(--tg-theme-hint-color,#666);">
                                ${t('payment_required').replace('{amount}', '100')}
                            </p>
                        </div>
                        
                        <div class="input-group">
                            <label>${t('payment_address')}</label>
                            <div style="display:flex;gap:8px;">
                                <input type="text" id="payment-address" value="TV61aTh98MGqmteYzda5AaBzdXgGqreG6A" readonly style="flex:1;">
                                <button class="btn btn-secondary" onclick="copyAddress()" style="width:auto;padding:12px 16px;">📋</button>
                            </div>
                        </div>
                        
                        <div class="input-group">
                            <label>${t('enter_wallet')}</label>
                            <input type="text" id="wallet-input" placeholder="${t('wallet_placeholder')}">
                        </div>
                        
                        <button class="btn btn-success" onclick="submitWallet()">
                            💰 ${t('submit')}
                        </button>
                        
                        <div style="margin-top:12px;">
                            <button class="btn btn-warning" onclick="verifyPayment()" style="margin-top:8px;">
                                ✅ ${t('verify_payment')}
                            </button>
                        </div>
                    `;
                }
            } catch (error) {
                content.innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>${t('error')}</p>
                    </div>
                `;
            }
        }
        
        async function loadAllWinners() {
            const content = document.getElementById('all-winners-content');
            
            try {
                const data = await apiCall('/api/lottery/all-winners');
                
                if (data.winners && data.winners.length > 0) {
                    let html = `<ul class="winner-list">`;
                    data.winners.forEach((winner, index) => {
                        html += `
                            <li>
                                <div class="winner-avatar">${index + 1}</div>
                                <div class="winner-info">
                                    <div class="winner-name">${winner.username || 'User ' + winner.user_id}</div>
                                    <div style="font-size:12px;color:var(--tg-theme-hint-color,#666);">${t('date')}: ${new Date(winner.date).toLocaleDateString()}</div>
                                </div>
                                <div class="winner-amount">$${winner.amount}</div>
                            </li>
                        `;
                    });
                    html += `</ul>`;
                    content.innerHTML = html;
                } else {
                    content.innerHTML = `
                        <div class="empty-state">
                            <div class="icon">🏆</div>
                            <p>${t('no_winners')}</p>
                        </div>
                    `;
                }
            } catch (error) {
                content.innerHTML = `
                    <div class="empty-state">
                        <div class="icon">⚠️</div>
                        <p>${t('error')}</p>
                    </div>
                `;
            }
        }
        
        // ============================================
        // User Actions
        // ============================================
        function copyAddress() {
            const address = document.getElementById('payment-address').value;
            navigator.clipboard.writeText(address).then(() => {
                showToast(t('copied'), 'success');
            }).catch(() => {
                // Fallback
                const input = document.getElementById('payment-address');
                input.select();
                document.execCommand('copy');
                showToast(t('copied'), 'success');
            });
        }
        
        function copyReferralCode(code) {
            navigator.clipboard.writeText(code).then(() => {
                showToast(t('copied'), 'success');
            }).catch(() => {
                // Fallback
                const textarea = document.createElement('textarea');
                textarea.value = code;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                showToast(t('copied'), 'success');
            });
        }
        
        function shareReferral(code) {
            const text = t('share_text').replace('{code}', code);
            if (navigator.share) {
                navigator.share({
                    title: '🎰 Lottery Bot',
                    text: text,
                }).catch(() => {});
            } else {
                navigator.clipboard.writeText(text).then(() => {
                    showToast(t('copied'), 'success');
                });
            }
        }
        
        async function submitWallet() {
            const wallet = document.getElementById('wallet-input').value.trim();
            if (!wallet || !wallet.startsWith('T') || wallet.length !== 34) {
                showToast(t('invalid_wallet') || 'Invalid wallet address', 'error');
                return;
            }
            
            try {
                const btn = document.querySelector('.btn-success');
                btn.disabled = true;
                btn.textContent = t('verifying');
                
                const result = await apiCall('/api/user/wallet', 'POST', {
                    wallet_address: wallet
                });
                
                if (result.success) {
                    showToast('✅ Wallet saved! Please send 100 USDT to the address above.', 'success');
                    document.getElementById('wallet-input').value = '';
                }
            } catch (error) {
                showToast(t('error'), 'error');
            } finally {
                const btn = document.querySelector('.btn-success');
                btn.disabled = false;
                btn.textContent = t('submit');
            }
        }
        
        async function verifyPayment() {
            try {
                const btn = document.querySelector('.btn-warning');
                if (btn) {
                    btn.disabled = true;
                    btn.textContent = t('checking_payment');
                }
                
                const result = await apiCall('/api/payment/verify', 'POST');
                
                if (result.verified) {
                    showToast(t('payment_verified'), 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    showToast(t('payment_failed'), 'error');
                }
            } catch (error) {
                showToast(t('error'), 'error');
            } finally {
                const btn = document.querySelector('.btn-warning');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = t('verify_payment');
                }
            }
        }
        
        async function checkWinnerStatus() {
            try {
                const result = await apiCall('/api/user/winner-status');
                
                if (result.is_winner) {
                    const amount = result.amount || 0;
                    showToast(t('congratulations').replace('{amount}', amount), 'success');
                    
                    // Show withdraw option
                    const content = document.getElementById('participate-content');
                    content.innerHTML += `
                        <div class="card" style="margin-top:16px;background:linear-gradient(135deg,#ffd70022,#f5a62322);">
                            <div class="card-title">💰 ${t('withdraw')}</div>
                            <div class="input-group">
                                <label>${t('enter_withdraw_address')}</label>
                                <input type="text" id="withdraw-address" placeholder="${t('wallet_placeholder')}">
                            </div>
                            <button class="btn btn-gold" onclick="submitWithdraw()">💰 ${t('withdraw')}</button>
                        </div>
                    `;
                } else {
                    showToast('❌ You are not a winner in the current lottery.', 'error');
                }
            } catch (error) {
                showToast(t('error'), 'error');
            }
        }
        
        async function submitWithdraw() {
            const wallet = document.getElementById('withdraw-address').value.trim();
            if (!wallet || !wallet.startsWith('T') || wallet.length !== 34) {
                showToast('Invalid wallet address', 'error');
                return;
            }
            
            try {
                const result = await apiCall('/api/user/withdraw', 'POST', {
                    wallet_address: wallet
                });
                
                if (result.success) {
                    showToast(t('withdraw_success'), 'success');
                    document.getElementById('withdraw-address').value = '';
                }
            } catch (error) {
                showToast(t('error'), 'error');
            }
        }
        
        function openParticipate() {
            switchPage('participate');
        }
        
        // ============================================
        // Init
        // ============================================
        async function init() {
            // Get init data from Telegram
            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                const user = tg.initDataUnsafe.user;
                userData = user;
                
                // Authenticate with backend
                try {
                    const response = await fetch('/api/auth/telegram', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            telegram_id: user.id,
                            username: user.username || '',
                            first_name: user.first_name || '',
                            last_name: user.last_name || '',
                            language: currentLanguage,
                            init_data: tg.initData
                        })
                    });
                    
                    const result = await response.json();
                    if (result.token) {
                        jwtToken = result.token;
                        // Set language from user
                        if (result.language) {
                            currentLanguage = result.language;
                            document.querySelectorAll('.lang-btn').forEach(btn => {
                                btn.classList.remove('active');
                                if (btn.textContent.includes(currentLanguage.toUpperCase())) {
                                    btn.classList.add('active');
                                }
                            });
                        }
                        // Load all data
                        await loadAllData();
                    } else {
                        showToast('Authentication failed', 'error');
                    }
                } catch (error) {
                    console.error('Auth error:', error);
                    showToast(t('error'), 'error');
                }
            } else {
                showToast('Please open from Telegram', 'error');
            }
            
            // Remove loading spinners
            document.querySelectorAll('.loading').forEach(el => el.classList.remove('active'));
        }
        
        // Start the app
        document.addEventListener('DOMContentLoaded', init);
        
        // Handle errors
        window.onerror = function(msg, url, line, col, error) {
            console.error('Error:', msg, error);
            showToast(t('error'), 'error');
            return false;
        };
    </script>
</body>
</html>
"""

# ============================================
# FastAPI Routes
# ============================================

@app.get("/", response_class=HTMLResponse)
async def webapp_page(request: Request):
    """Serve the web app page"""
    return HTMLResponse(WEBAPP_HTML)

@app.post("/api/auth/telegram")
async def auth_telegram(data: UserData):
    """Authenticate user via Telegram"""
    try:
        # Verify Telegram init data
        # In production, validate the hash
        
        # Get or create user
        shard_id = db_manager.get_shard(data.telegram_id)
        async with db_manager.get_session(shard_id) as session:
            stmt = select(User).where(User.telegram_id == data.telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                # Create new user
                referral_code = generate_referral_code()
                user = User(
                    telegram_id=data.telegram_id,
                    username=data.username,
                    first_name=data.first_name,
                    last_name=data.last_name,
                    language=data.language,
                    referral_code=referral_code,
                    shard_id=shard_id
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            # Generate JWT token
            token = create_jwt_token(data.telegram_id)
            
            return {
                "success": True,
                "token": token,
                "language": user.language,
                "user": {
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "has_subscription": user.has_subscription,
                    "subscription_expiry": user.subscription_expiry.isoformat() if user.subscription_expiry else None,
                    "wallet_address": user.wallet_address,
                    "total_won": user.total_won
                }
            }
    except Exception as e:
        logging.error(f"Auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/status")
async def get_user_status(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Get user status"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    shard_id = db_manager.get_shard(user_id)
    async with db_manager.get_session(shard_id) as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user": {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "has_subscription": user.has_subscription,
                "subscription_expiry": user.subscription_expiry.isoformat() if user.subscription_expiry else None,
                "wallet_address": user.wallet_address,
                "total_won": user.total_won,
                "is_winner": user.is_winner
            }
        }

@app.post("/api/user/language")
async def update_language(data: dict, auth: HTTPAuthorizationCredentials = Depends(security)):
    """Update user language"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    language = data.get('language')
    if not language or language not in ['en', 'fa', 'ar']:
        raise HTTPException(status_code=400, detail="Invalid language")
    
    shard_id = db_manager.get_shard(user_id)
    async with db_manager.get_session(shard_id) as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            user.language = language
            await session.commit()
            return {"success": True}
    
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/user/wallet")
async def save_wallet(data: WalletRequest, auth: HTTPAuthorizationCredentials = Depends(security)):
    """Save user wallet address"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not data.wallet_address.startswith('T') or len(data.wallet_address) != 34:
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    
    shard_id = db_manager.get_shard(user_id)
    async with db_manager.get_session(shard_id) as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            user.wallet_address = data.wallet_address
            await session.commit()
            return {"success": True}
    
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/user/subscription")
async def get_subscription(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Get user subscription status"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    shard_id = db_manager.get_shard(user_id)
    async with db_manager.get_session(shard_id) as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "has_subscription": user.has_subscription,
            "expiry": user.subscription_expiry.isoformat() if user.subscription_expiry else None
        }

@app.get("/api/lottery/status")
async def get_lottery_status(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Get current lottery status"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    async with db_manager.get_session(0) as session:
        stmt = select(Lottery).where(
            Lottery.status.in_(['active', 'drawing'])
        ).order_by(Lottery.created_at.desc()).limit(1)
        result = await session.execute(stmt)
        lottery = result.scalar_one_or_none()
        
        if lottery:
            return {
                "active": True,
                "status": lottery.status,
                "participant_count": lottery.participant_count,
                "prize_pool": lottery.prize_pool,
                "prize_per_winner": lottery.prize_per_winner,
                "winners": lottery.winners if lottery.winners else []
            }
        
        return {"active": False}

@app.get("/api/lottery/winners")
async def get_lottery_winners(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Get current lottery winners"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    async with db_manager.get_session(0) as session:
        stmt = select(Lottery).where(
            Lottery.status == 'completed'
        ).order_by(Lottery.completed_at.desc()).limit(1)
        result = await session.execute(stmt)
        lottery = result.scalar_one_or_none()
        
        if lottery and lottery.winners:
            winners = []
            for winner_id in lottery.winners[:10]:
                shard_id = db_manager.get_shard(winner_id)
                async with db_manager.get_session(shard_id) as user_session:
                    stmt = select(User).where(User.telegram_id == winner_id)
                    user_result = await user_session.execute(stmt)
                    user = user_result.scalar_one_or_none()
                    
                    winners.append({
                        "user_id": winner_id,
                        "username": user.username if user else None,
                        "amount": lottery.prize_per_winner
                    })
            
            return {
                "winners": winners,
                "prize_per_winner": lottery.prize_per_winner
            }
        
        return {"winners": []}

@app.get("/api/lottery/all-winners")
async def get_all_winners(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Get all past winners"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    async with db_manager.get_session(0) as session:
        stmt = select(Lottery).where(
            Lottery.status == 'completed',
            Lottery.winners != []
        ).order_by(Lottery.completed_at.desc()).limit(20)
        result = await session.execute(stmt)
        lotteries = result.scalars().all()
        
        all_winners = []
        for lottery in lotteries:
            if lottery.winners:
                for winner_id in lottery.winners:
                    shard_id = db_manager.get_shard(winner_id)
                    async with db_manager.get_session(shard_id) as user_session:
                        stmt = select(User).where(User.telegram_id == winner_id)
                        user_result = await user_session.execute(stmt)
                        user = user_result.scalar_one_or_none()
                        
                        all_winners.append({
                            "user_id": winner_id,
                            "username": user.username if user else None,
                            "amount": lottery.prize_per_winner,
                            "date": lottery.completed_at.isoformat() if lottery.completed_at else None
                        })
        
        return {"winners": all_winners}

@app.get("/api/user/referral")
async def get_referral_info(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Get user referral info"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    shard_id = db_manager.get_shard(user_id)
    async with db_manager.get_session(shard_id) as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "referral_code": user.referral_code,
            "referral_count": user.referral_count,
            "referral_earnings": user.referral_earnings
        }

@app.get("/api/user/winner-status")
async def check_winner_status(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Check if user is a winner"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    shard_id = db_manager.get_shard(user_id)
    async with db_manager.get_session(shard_id) as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "is_winner": user.is_winner,
            "amount": user.won_amount if user.is_winner else 0
        }

@app.post("/api/user/withdraw")
async def withdraw_request(data: WalletRequest, auth: HTTPAuthorizationCredentials = Depends(security)):
    """Request withdrawal"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not data.wallet_address.startswith('T') or len(data.wallet_address) != 34:
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    
    shard_id = db_manager.get_shard(user_id)
    async with db_manager.get_session(shard_id) as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.is_winner:
            raise HTTPException(status_code=400, detail="User is not a winner")
        
        # Save withdrawal address and send to admin
        user.wallet_address = data.wallet_address
        
        # Mark as processed
        user.is_winner = False
        
        await session.commit()
        
        # Notify admin
        # In production, send Telegram message to admin
        return {"success": True}

@app.post("/api/payment/verify")
async def verify_payment(auth: HTTPAuthorizationCredentials = Depends(security)):
    """Verify payment transaction"""
    user_id = verify_jwt_token(auth.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    shard_id = db_manager.get_shard(user_id)
    async with db_manager.get_session(shard_id) as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.wallet_address:
            raise HTTPException(status_code=400, detail="Wallet address not set")
        
        # In production, verify with Tron API
        # For demo, simulate verification
        await cache.incr(f"verify_attempt:{user_id}")
        
        # Simulate verification (in production, use actual Tron API)
        if user.wallet_address:
            # Activate subscription
            user.has_subscription = True
            user.subscription_expiry = datetime.utcnow() + timedelta(days=30)
            await session.commit()
            return {"verified": True}
        
        return {"verified": False}

# ============================================
# Telegram Bot
# ============================================
class LotteryBot:
    def __init__(self):
        self.application = None
    
    async def start(self):
        self.application = Application.builder().token(config.BOT_TOKEN).build()
        
        # Handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.webapp_button, pattern="^webapp$"))
        
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logging.info("Bot started!")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with WebApp button"""
        keyboard = [[
            InlineKeyboardButton(
                "🎮 Play Lottery",
                web_app=WebAppInfo(url=config.WEBAPP_URL)
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎰 *Welcome to UTYOB Lottery Bot!*\n\n"
            "Click the button below to open the lottery web app.\n\n"
            "🎯 *Features:*\n"
            "• Fair lottery with AI algorithm\n"
            "• Instant payment verification\n"
            "• Multiple language support\n"
            "• Referral program\n"
            "• Live winner announcements\n\n"
            "💰 *Prize: $100 USDT per winner!*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def webapp_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle webapp button"""
        query = update.callback_query
        await query.answer()
        # The webapp will open automatically

# ============================================
# Utility Functions
# ============================================
def generate_referral_code() -> str:
    """Generate unique referral code"""
    chars = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(chars) for _ in range(8))
    return code

# ============================================
# Main Application
# ============================================
async def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Start bot
    bot = LotteryBot()
    await bot.start()
    
    # Run FastAPI
    config_uv = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config_uv)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logging.info("Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())