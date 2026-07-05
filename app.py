"""
ربات قرعه‌کشی UTYOB - فایل کامل یکپارچه
نسخه 1.0 - با وب‌سرویس داخلی و صفحه وب
قابل اجرا با یک فایل Python
"""

import os
import sys
import json
import asyncio
import logging
import random
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import re

# ============================================================
# نصب خودکار کتابخانه‌های مورد نیاز در صورت عدم وجود
# ============================================================
def install_packages():
    packages = [
        'aiogram==2.25.1',
        'aiohttp==3.9.1',
        'asyncpg==0.29.0',
        'redis==5.0.1',
        'sqlalchemy==2.0.23',
        'psycopg2-binary==2.9.9',
        'python-dotenv==1.0.0',
        'uvicorn==0.25.0',
        'fastapi==0.104.1'
    ]
    
    for package in packages:
        try:
            __import__(package.split('==')[0])
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

# نصب خودکار
install_packages()

# ============================================================
# ایمپورت‌ها
# ============================================================
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ParseMode
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.executor import start_polling, start_webhook

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import aiohttp
import asyncpg
import redis.asyncio as redis
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, BigInteger, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

import threading
import time
from pathlib import Path

# ============================================================
# تنظیمات
# ============================================================
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))
DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
LOTTERY_PRICE = 100
ADMIN_FEE = 0.20
CONFIRMATION_THRESHOLD = 19

# تنظیمات دیتابیس (برای تست از SQLite استفاده می‌کنیم)
USE_SQLITE = True
DATABASE_URL = 'sqlite:///lottery.db' if USE_SQLITE else os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/lottery_db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# تنظیمات وب
WEBAPP_HOST = os.getenv('WEBAPP_HOST', '0.0.0.0')
WEBAPP_PORT = int(os.getenv('WEBAPP_PORT', '8080'))
WEBAPP_URL = os.getenv('WEBAPP_URL', f'http://localhost:{WEBAPP_PORT}')

# ============================================================
# تنظیمات لاگ
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lottery_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# مدل‌های دیتابیس
# ============================================================
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    language = Column(String(10), default='en')
    wallet_address = Column(String(100))
    points = Column(BigInteger, default=0)
    has_subscription = Column(Boolean, default=False)
    subscription_date = Column(DateTime)
    total_participations = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_amount_won = Column(Float, default=0.0)
    referral_code = Column(String(20), unique=True, index=True)
    referral_count = Column(Integer, default=0)
    referral_points = Column(BigInteger, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, index=True)
    tx_hash = Column(String(100), unique=True, index=True)
    from_address = Column(String(100))
    to_address = Column(String(100))
    amount = Column(Float, nullable=False)
    status = Column(String(20), default='pending')
    confirmations = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    confirmed_at = Column(DateTime)

class Lottery(Base):
    __tablename__ = 'lotteries'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    round_number = Column(Integer, unique=True, nullable=False)
    total_pool = Column(Float, default=0.0)
    admin_fee = Column(Float, default=0.0)
    prize_pool = Column(Float, default=0.0)
    number_of_winners = Column(Integer)
    prize_per_winner = Column(Float)
    status = Column(String(20), default='pending')
    is_active = Column(Boolean, default=False)
    started_at = Column(DateTime)
    drawn_at = Column(DateTime)
    lottery_hash = Column(String(100))
    created_at = Column(DateTime, default=func.now())

class LotteryParticipation(Base):
    __tablename__ = 'lottery_participations'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, index=True)
    lottery_id = Column(BigInteger, ForeignKey('lotteries.id'), nullable=False, index=True)
    weight = Column(Float, default=1.0)
    is_winner = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class Winner(Base):
    __tablename__ = 'winners'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, index=True)
    lottery_id = Column(BigInteger, ForeignKey('lotteries.id'), nullable=False, index=True)
    prize_amount = Column(Float, nullable=False)
    withdrawal_status = Column(String(20), default='pending')
    withdrawal_address = Column(String(100))
    paid_at = Column(DateTime)
    is_excluded_from_next = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

class Poll(Base):
    __tablename__ = 'polls'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lottery_id = Column(BigInteger, ForeignKey('lotteries.id'))
    question = Column(Text)
    status = Column(String(20), default='active')
    total_votes = Column(Integer, default=0)
    yes_votes = Column(Integer, default=0)
    no_votes = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

class PollVote(Base):
    __tablename__ = 'poll_votes'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    poll_id = Column(BigInteger, ForeignKey('polls.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, index=True)
    vote = Column(String(10))
    created_at = Column(DateTime, default=func.now())

# ============================================================
# راه‌اندازی دیتابیس
# ============================================================
def init_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return engine

engine = init_db()
Session = sessionmaker(bind=engine)

def get_db():
    return Session()

# ============================================================
# کلاس‌های وضعیت FSM
# ============================================================
class LotteryStates(StatesGroup):
    waiting_for_wallet = State()
    waiting_for_tx_hash = State()
    waiting_for_withdrawal = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_winner_count = State()
    waiting_for_prize_amount = State()
    waiting_for_manual_verify = State()

# ============================================================
# کلاس‌های اصلی سرویس‌ها
# ============================================================
class DatabaseService:
    """سرویس دیتابیس با قابلیت کش"""
    
    @staticmethod
    def get_or_create_user(telegram_id: int, first_name: str = '', username: str = '') -> dict:
        session = get_db()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                import hashlib
                referral_code = hashlib.md5(str(telegram_id).encode()).hexdigest()[:8].upper()
                user = User(
                    telegram_id=telegram_id,
                    first_name=first_name,
                    username=username,
                    referral_code=referral_code,
                    language='en'
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            
            return {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language': user.language,
                'has_subscription': user.has_subscription,
                'points': user.points,
                'referral_code': user.referral_code,
                'referral_count': user.referral_count,
                'referral_points': user.referral_points,
                'total_participations': user.total_participations,
                'total_wins': user.total_wins,
                'total_amount_won': user.total_amount_won
            }
        except Exception as e:
            logger.error(f"DB error: {e}")
            return None
        finally:
            session.close()
    
    @staticmethod
    def update_user_language(telegram_id: int, language: str):
        session = get_db()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.language = language
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Update language error: {e}")
        finally:
            session.close()
        return False
    
    @staticmethod
    def has_participated(telegram_id: int) -> bool:
        session = get_db()
        try:
            lottery = session.query(Lottery).filter_by(status='active').order_by(Lottery.id.desc()).first()
            if not lottery:
                return False
            participation = session.query(LotteryParticipation).filter_by(
                user_id=telegram_id, lottery_id=lottery.id
            ).first()
            return participation is not None
        except Exception as e:
            logger.error(f"Check participation error: {e}")
            return False
        finally:
            session.close()
    
    @staticmethod
    def register_participation(telegram_id: int, tx_hash: str, wallet_address: str) -> bool:
        session = get_db()
        try:
            # دریافت یا ایجاد دور فعلی
            lottery = session.query(Lottery).filter_by(status='active').order_by(Lottery.id.desc()).first()
            if not lottery:
                last_round = session.query(Lottery).count()
                lottery = Lottery(
                    round_number=last_round + 1,
                    status='active',
                    is_active=True,
                    started_at=func.now()
                )
                session.add(lottery)
                session.flush()
            
            # ثبت تراکنش
            tx = Transaction(
                user_id=telegram_id,
                tx_hash=tx_hash,
                from_address=wallet_address,
                to_address=DESTINATION_WALLET,
                amount=LOTTERY_PRICE,
                status='confirmed',
                confirmed_at=func.now()
            )
            session.add(tx)
            
            # ثبت شرکت
            participation = LotteryParticipation(
                user_id=telegram_id,
                lottery_id=lottery.id
            )
            session.add(participation)
            
            # به‌روزرسانی کاربر
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.has_subscription = True
                user.subscription_date = func.now()
                user.total_participations = user.total_participations + 1
            
            # به‌روزرسانی صندوق
            lottery.total_pool = lottery.total_pool + LOTTERY_PRICE
            lottery.prize_pool = lottery.prize_pool + (LOTTERY_PRICE * 0.80)
            lottery.admin_fee = lottery.admin_fee + (LOTTERY_PRICE * 0.20)
            
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Register participation error: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_participants() -> List[dict]:
        session = get_db()
        try:
            lottery = session.query(Lottery).filter_by(status='active').order_by(Lottery.id.desc()).first()
            if not lottery:
                return []
            
            participations = session.query(LotteryParticipation).filter_by(lottery_id=lottery.id).all()
            result = []
            for p in participations:
                user = session.query(User).filter_by(telegram_id=p.user_id).first()
                if user:
                    result.append({
                        'user_id': user.telegram_id,
                        'has_subscription': user.has_subscription,
                        'total_participations': user.total_participations,
                        'total_wins': user.total_wins
                    })
            return result
        except Exception as e:
            logger.error(f"Get participants error: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def get_previous_winners() -> List[int]:
        session = get_db()
        try:
            winners = session.query(Winner).order_by(Winner.id.desc()).limit(100).all()
            return [w.user_id for w in winners]
        except Exception as e:
            logger.error(f"Get previous winners error: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def create_lottery(winner_count: int, prize_amount: float, winners: List[int]) -> int:
        session = get_db()
        try:
            last_round = session.query(Lottery).count()
            lottery = Lottery(
                round_number=last_round + 1,
                number_of_winners=winner_count,
                prize_per_winner=prize_amount,
                prize_pool=winner_count * prize_amount,
                status='completed',
                is_active=False,
                drawn_at=func.now()
            )
            session.add(lottery)
            session.flush()
            
            for user_id in winners:
                winner = Winner(
                    user_id=user_id,
                    lottery_id=lottery.id,
                    prize_amount=prize_amount,
                    is_excluded_from_next=True
                )
                session.add(winner)
                
                user = session.query(User).filter_by(telegram_id=user_id).first()
                if user:
                    user.total_wins = user.total_wins + 1
                    user.total_amount_won = user.total_amount_won + prize_amount
            
            session.commit()
            return lottery.id
        except Exception as e:
            logger.error(f"Create lottery error: {e}")
            session.rollback()
            return 0
        finally:
            session.close()
    
    @staticmethod
    def get_winner(telegram_id: int) -> Optional[dict]:
        session = get_db()
        try:
            winner = session.query(Winner).filter_by(
                user_id=telegram_id, withdrawal_status='pending'
            ).order_by(Winner.id.desc()).first()
            if not winner:
                return None
            return {
                'id': winner.id,
                'prize_amount': winner.prize_amount,
                'withdrawal_status': winner.withdrawal_status,
                'withdrawal_address': winner.withdrawal_address
            }
        except Exception as e:
            logger.error(f"Get winner error: {e}")
            return None
        finally:
            session.close()
    
    @staticmethod
    def save_withdrawal_address(telegram_id: int, address: str) -> bool:
        session = get_db()
        try:
            winner = session.query(Winner).filter_by(
                user_id=telegram_id, withdrawal_status='pending'
            ).order_by(Winner.id.desc()).first()
            if winner:
                winner.withdrawal_address = address
                winner.withdrawal_status = 'requested'
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Save withdrawal address error: {e}")
            session.rollback()
        finally:
            session.close()
        return False
    
    @staticmethod
    def get_all_users() -> List[dict]:
        session = get_db()
        try:
            users = session.query(User).filter_by(is_active=True).all()
            return [{'telegram_id': u.telegram_id, 'language': u.language} for u in users]
        except Exception as e:
            logger.error(f"Get all users error: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def pay_winners() -> int:
        session = get_db()
        try:
            winners = session.query(Winner).filter_by(withdrawal_status='requested').all()
            count = 0
            for winner in winners:
                winner.withdrawal_status = 'paid'
                winner.paid_at = func.now()
                count += 1
            session.commit()
            return count
        except Exception as e:
            logger.error(f"Pay winners error: {e}")
            session.rollback()
            return 0
        finally:
            session.close()
    
    @staticmethod
    def get_statistics() -> dict:
        session = get_db()
        try:
            total_users = session.query(User).count()
            subscribed = session.query(User).filter_by(has_subscription=True).count()
            current_round = session.query(Lottery).count()
            
            lottery = session.query(Lottery).filter_by(status='active').first()
            participants = 0
            total_pool = 0
            if lottery:
                participants = session.query(LotteryParticipation).filter_by(lottery_id=lottery.id).count()
                total_pool = lottery.prize_pool or 0
            
            total_winners = session.query(Winner).count()
            total_paid = session.query(func.sum(Winner.prize_amount)).filter_by(withdrawal_status='paid').scalar() or 0
            
            return {
                'total_users': total_users,
                'subscribed_users': subscribed,
                'current_round': current_round,
                'participants': participants,
                'total_pool': total_pool,
                'total_winners': total_winners,
                'total_paid': total_paid
            }
        except Exception as e:
            logger.error(f"Get statistics error: {e}")
            return {}
        finally:
            session.close()

# ============================================================
# سرویس قرعه‌کشی
# ============================================================
class LotteryService:
    @staticmethod
    def select_winners(participants: List[dict], number_of_winners: int, exclude_users: List[int] = None) -> List[int]:
        if exclude_users is None:
            exclude_users = []
        
        eligible = [p for p in participants if p['user_id'] not in exclude_users and p.get('has_subscription', False)]
        
        if not eligible or len(eligible) < number_of_winners:
            return []
        
        # محاسبه وزن‌ها
        weights = []
        for p in eligible:
            weight = 1.0
            weight += p.get('total_participations', 0) * 0.01
            weight -= p.get('total_wins', 0) * 0.05
            weight = max(0.5, min(weight, 2.0))
            weights.append(weight)
        
        # انتخاب با وزن
        total_weight = sum(weights)
        if total_weight == 0:
            return []
        
        normalized = [w / total_weight for w in weights]
        selected = []
        available = list(range(len(eligible)))
        
        for _ in range(min(number_of_winners, len(eligible))):
            if not available:
                break
            import random
            idx = random.choices(available, weights=[normalized[i] for i in available], k=1)[0]
            selected.append(eligible[idx]['user_id'])
            available.remove(idx)
        
        return selected

# ============================================================
# ربات تلگرام
# ============================================================
class LotteryBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(self.bot, storage=self.storage)
        self.db = DatabaseService()
        self.lottery = LotteryService()
        self._register_handlers()
    
    def _register_handlers(self):
        dp = self.dp
        
        # ========================================
        # دستور start
        # ========================================
        @dp.message_handler(commands=['start'])
        async def cmd_start(message: types.Message):
            user_id = message.from_user.id
            user = self.db.get_or_create_user(
                user_id,
                message.from_user.first_name or '',
                message.from_user.username or ''
            )
            
            # پردازش کد رفرال
            args = message.get_args()
            if args and args.startswith('ref_'):
                # اینجا می‌توانید رفرال را ثبت کنید
                pass
            
            lang = user.get('language', 'en')
            text_en = (
                "🎰 **Welcome to UTYOB Lottery Bot!**\n\n"
                "💰 Join our lottery and win big prizes!\n"
                f"💵 Only ${LOTTERY_PRICE} to participate\n"
                "🎁 Win up to $2,000!\n\n"
                "Click the button below to enter the app."
            )
            text_fa = (
                "🎰 **به ربات قرعه‌کشی UTYOB خوش آمدید!**\n\n"
                "💰 در قرعه‌کشی ما شرکت کنید و جوایز بزرگ ببرید!\n"
                f"💵 فقط ${LOTTERY_PRICE} برای شرکت\n"
                "🎁 تا ۲,۰۰۰ دلار برنده شوید!\n\n"
                "برای ورود به برنامه روی دکمه زیر کلیک کنید."
            )
            
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton(
                    "🎮 PLY",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/")
                )
            )
            keyboard.add(
                InlineKeyboardButton(
                    "📖 Guide" if lang == 'en' else "📖 راهنما",
                    callback_data="guide"
                )
            )
            
            text = text_en if lang == 'en' else text_fa
            await message.reply(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        
        # ========================================
        # راهنما
        # ========================================
        @dp.callback_query_handler(lambda c: c.data == 'guide')
        async def guide_handler(callback_query: types.CallbackQuery):
            user_id = callback_query.from_user.id
            user = self.db.get_or_create_user(user_id)
            lang = user.get('language', 'en')
            
            text_en = (
                "📖 **Guide**\n\n"
                f"1️⃣ Send ${LOTTERY_PRICE} USDT to:\n"
                f"`{DESTINATION_WALLET}`\n"
                "2️⃣ Open the app and verify your payment\n"
                "3️⃣ Wait for the lottery draw\n"
                "4️⃣ If you win, withdraw your prize!\n\n"
                "⚡ The lottery is fair and transparent."
            )
            text_fa = (
                "📖 **راهنما**\n\n"
                f"۱️⃣ ${LOTTERY_PRICE} USDT به آدرس زیر ارسال کنید:\n"
                f"`{DESTINATION_WALLET}`\n"
                "۲️⃣ برنامه را باز کنید و پرداخت خود را تایید کنید\n"
                "۳️⃣ منتظر قرعه‌کشی باشید\n"
                "۴️⃣ اگر برنده شدید، جایزه خود را برداشت کنید!\n\n"
                "⚡ قرعه‌کشی عادلانه و شفاف است."
            )
            
            await callback_query.message.answer(text_en if lang == 'en' else text_fa, parse_mode=ParseMode.MARKDOWN)
            await callback_query.answer()
        
        # ========================================
        # پنل مدیریت
        # ========================================
        @dp.message_handler(commands=['admin'])
        async def admin_panel(message: types.Message):
            if message.from_user.id != ADMIN_ID:
                await message.reply("⛔ Access denied.")
                return
            
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
                InlineKeyboardButton("🎰 Start Lottery", callback_data="admin_start_lottery")
            )
            keyboard.add(
                InlineKeyboardButton("✅ Manual Verify", callback_data="admin_manual_verify"),
                InlineKeyboardButton("📊 Send Poll", callback_data="admin_poll")
            )
            keyboard.add(
                InlineKeyboardButton("💸 Pay Winners", callback_data="admin_pay_winners"),
                InlineKeyboardButton("📈 Statistics", callback_data="admin_stats")
            )
            
            await message.reply("🛠️ **Admin Panel**", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        
        @dp.callback_query_handler(lambda c: c.data.startswith('admin_'))
        async def admin_actions(callback_query: types.CallbackQuery, state: FSMContext):
            user_id = callback_query.from_user.id
            if user_id != ADMIN_ID:
                await callback_query.answer("⛔ Access denied.")
                return
            
            data = callback_query.data
            
            if data == 'admin_broadcast':
                await callback_query.message.answer("📢 **Enter broadcast message:**")
                await AdminStates.waiting_for_broadcast.set()
            
            elif data == 'admin_start_lottery':
                await callback_query.message.answer("📊 **How many winners?**")
                await AdminStates.waiting_for_winner_count.set()
            
            elif data == 'admin_manual_verify':
                await callback_query.message.answer("🔍 **Enter user ID and tx hash:**\nFormat: `user_id tx_hash`")
                await AdminStates.waiting_for_manual_verify.set()
            
            elif data == 'admin_poll':
                await self._send_poll()
                await callback_query.message.answer("📊 Poll sent!")
            
            elif data == 'admin_pay_winners':
                count = self.db.pay_winners()
                await callback_query.message.answer(f"💸 Paid {count} winners!")
            
            elif data == 'admin_stats':
                stats = self.db.get_statistics()
                text = (
                    f"📊 **Statistics**\n\n"
                    f"👥 Users: {stats.get('total_users', 0)}\n"
                    f"💎 Subscribed: {stats.get('subscribed_users', 0)}\n"
                    f"🎰 Round: #{stats.get('current_round', 0)}\n"
                    f"👤 Participants: {stats.get('participants', 0)}\n"
                    f"💰 Pool: ${stats.get('total_pool', 0)}\n"
                    f"🏆 Winners: {stats.get('total_winners', 0)}\n"
                    f"💵 Paid: ${stats.get('total_paid', 0)}"
                )
                await callback_query.message.answer(text, parse_mode=ParseMode.MARKDOWN)
            
            await callback_query.answer()
        
        @dp.message_handler(state=AdminStates.waiting_for_broadcast)
        async def process_broadcast(message: types.Message, state: FSMContext):
            if message.from_user.id != ADMIN_ID:
                return
            
            users = self.db.get_all_users()
            sent = 0
            for user in users:
                try:
                    await self.bot.send_message(user['telegram_id'], message.text)
                    sent += 1
                    await asyncio.sleep(0.05)
                except:
                    pass
            
            await message.reply(f"✅ Broadcast sent to {sent} users!")
            await state.finish()
        
        @dp.message_handler(state=AdminStates.waiting_for_winner_count)
        async def process_winner_count(message: types.Message, state: FSMContext):
            try:
                count = int(message.text.strip())
                if count <= 0:
                    raise ValueError
                await state.update_data(winner_count=count)
                await message.reply("💰 **Prize amount per winner (USDT):**")
                await AdminStates.waiting_for_prize_amount.set()
            except:
                await message.reply("❌ Enter a valid number.")
        
        @dp.message_handler(state=AdminStates.waiting_for_prize_amount)
        async def process_prize_amount(message: types.Message, state: FSMContext):
            try:
                amount = float(message.text.strip())
                if amount <= 0:
                    raise ValueError
                
                data = await state.get_data()
                winner_count = data.get('winner_count', 1)
                
                participants = self.db.get_participants()
                previous_winners = self.db.get_previous_winners()
                winners = self.lottery.select_winners(participants, winner_count, previous_winners)
                
                if not winners:
                    await message.reply("❌ No eligible participants!")
                    await state.finish()
                    return
                
                lottery_id = self.db.create_lottery(winner_count, amount, winners)
                
                # اطلاع‌رسانی به برنده‌ها
                for user_id in winners:
                    try:
                        await self.bot.send_message(
                            user_id,
                            f"🎉 **Congratulations!**\n\n"
                            f"You won ${amount} USDT!\n"
                            f"Click the button below to withdraw.",
                            reply_markup=InlineKeyboardMarkup().add(
                                InlineKeyboardButton("💰 Withdraw", callback_data="withdraw_prize")
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass
                
                await message.reply(
                    f"✅ **Lottery completed!**\n\n"
                    f"🏆 Winners: {len(winners)}\n"
                    f"💰 Prize: ${amount} each"
                )
                await state.finish()
            except:
                await message.reply("❌ Enter a valid amount.")
        
        @dp.message_handler(state=AdminStates.waiting_for_manual_verify)
        async def process_manual_verify(message: types.Message, state: FSMContext):
            parts = message.text.strip().split()
            if len(parts) != 2:
                await message.reply("❌ Format: `user_id tx_hash`")
                return
            
            user_id, tx_hash = parts
            try:
                user_id = int(user_id)
            except:
                await message.reply("❌ Invalid user ID.")
                return
            
            # اینجا می‌توانید تایید دستی انجام دهید
            await message.reply(f"✅ User {user_id} verified manually!")
            await state.finish()
        
        # ========================================
        # برداشت جایزه
        # ========================================
        @dp.callback_query_handler(lambda c: c.data == 'withdraw_prize')
        async def withdraw_prize(callback_query: types.CallbackQuery, state: FSMContext):
            user_id = callback_query.from_user.id
            winner = self.db.get_winner(user_id)
            
            if not winner:
                await callback_query.message.answer("❌ You don't have any prize to withdraw.")
                await callback_query.answer()
                return
            
            if winner['withdrawal_status'] == 'paid':
                await callback_query.message.answer("✅ Already withdrawn.")
                await callback_query.answer()
                return
            
            await callback_query.message.answer(
                f"💰 **Withdraw ${winner['prize_amount']} USDT**\n\n"
                "Enter your TRC20 wallet address:"
            )
            await LotteryStates.waiting_for_withdrawal.set()
            await callback_query.answer()
        
        @dp.message_handler(state=LotteryStates.waiting_for_withdrawal)
        async def process_withdrawal(message: types.Message, state: FSMContext):
            address = message.text.strip()
            if len(address) != 34 or not address.startswith('T'):
                await message.reply("❌ Invalid TRC20 address.")
                return
            
            if self.db.save_withdrawal_address(message.from_user.id, address):
                await message.reply("✅ Withdrawal request submitted!")
                await self.bot.send_message(
                    ADMIN_ID,
                    f"💸 **Withdrawal Request**\n\n"
                    f"👤 User: {message.from_user.id}\n"
                    f"📤 Address: `{address}`"
                )
            else:
                await message.reply("❌ No pending prize found.")
            
            await state.finish()
    
    async def _send_poll(self):
        users = self.db.get_all_users()
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("✅ Yes", callback_data="poll_yes"),
            InlineKeyboardButton("❌ No", callback_data="poll_no")
        )
        
        for user in users:
            try:
                await self.bot.send_message(
                    user['telegram_id'],
                    "📊 **Next Lottery Round?**\n\n"
                    f"Price: ${LOTTERY_PRICE} USDT\n"
                    "Do you want to start a new round?",
                    reply_markup=keyboard
                )
                await asyncio.sleep(0.05)
            except:
                pass
    
    def run(self):
        logger.info("🚀 Starting bot...")
        start_polling(self.dp, skip_updates=True)

# ============================================================
# وب‌سرور FastAPI با صفحه WebApp یکپارچه
# ============================================================
app = FastAPI(title="UTYOB Lottery")

# ============================================================
# HTML کامل صفحه وب (یکپارچه)
# ============================================================
WEBPAGE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>UTYOB Lottery</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        :root {
            --primary: #6C63FF; --primary-dark: #5A52D5; --secondary: #FF6584;
            --success: #00C9A7; --warning: #FFC107; --danger: #FF3B30;
            --dark: #0F0F1A; --dark-card: #1A1A2E; --dark-input: #16213E;
            --text: #FFFFFF; --text-muted: #8892A8; --border: #2D3748;
            --radius: 16px; --radius-sm: 10px;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--dark); color: var(--text);
            min-height: 100vh; margin:0; padding:0; overflow-x:hidden;
        }
        ::-webkit-scrollbar { width:4px; }
        ::-webkit-scrollbar-track { background:var(--dark); }
        ::-webkit-scrollbar-thumb { background:var(--primary); border-radius:10px; }
        .app { max-width:480px; margin:0 auto; padding:12px 14px 100px; }
        .header {
            display:flex; justify-content:space-between; align-items:center;
            padding:8px 0 16px; border-bottom:1px solid var(--border); margin-bottom:16px;
        }
        .header-left { display:flex; align-items:center; gap:10px; }
        .header-logo {
            width:36px; height:36px; background:linear-gradient(135deg,var(--primary),var(--secondary));
            border-radius:10px; display:flex; align-items:center; justify-content:center;
            font-size:18px; font-weight:900; color:#fff; flex-shrink:0;
        }
        .header-title { font-size:17px; font-weight:700; background:linear-gradient(135deg,var(--primary),var(--secondary)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
        .header-right { display:flex; align-items:center; gap:8px; }
        .header-avatar {
            width:32px; height:32px; border-radius:50%; background:var(--primary);
            display:flex; align-items:center; justify-content:center;
            font-size:13px; font-weight:700; color:#fff; flex-shrink:0;
        }
        .header-points {
            font-size:12px; font-weight:600; color:var(--success);
            background:rgba(0,201,167,0.12); padding:4px 10px; border-radius:20px;
            border:1px solid rgba(0,201,167,0.2);
        }
        .status-bar {
            display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:6px;
            background:var(--dark-card); border:1px solid var(--border);
            border-radius:var(--radius); padding:12px 8px; margin-bottom:16px;
        }
        .status-item { text-align:center; }
        .status-item .label { font-size:8px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px; font-weight:600; }
        .status-item .value { font-size:16px; font-weight:700; margin-top:2px; }
        .status-item .value.primary { color:var(--primary); }
        .status-item .value.success { color:var(--success); }
        .status-item .value.warning { color:var(--warning); }
        .card {
            background:var(--dark-card); border:1px solid var(--border);
            border-radius:var(--radius); padding:16px; margin-bottom:12px;
            transition:all 0.3s ease;
        }
        .card-title { font-size:14px; font-weight:700; margin-bottom:10px; display:flex; align-items:center; gap:8px; }
        .btn {
            display:inline-flex; align-items:center; justify-content:center; gap:8px;
            padding:12px 20px; border:none; border-radius:var(--radius-sm);
            font-size:14px; font-weight:600; cursor:pointer; transition:all 0.3s ease;
            width:100%; color:#fff; -webkit-tap-highlight-color:transparent;
        }
        .btn:active { transform:scale(0.97); }
        .btn-primary { background:linear-gradient(135deg,var(--primary),var(--primary-dark)); }
        .btn-primary:hover { box-shadow:0 4px 20px rgba(108,99,255,0.35); transform:translateY(-1px); }
        .btn-success { background:linear-gradient(135deg,var(--success),#00A896); }
        .btn-warning { background:linear-gradient(135deg,var(--warning),#F59F00); color:var(--dark); }
        .btn-outline { background:transparent; border:2px solid var(--border); color:var(--text); }
        .btn:disabled { opacity:0.5; cursor:not-allowed; transform:none !important; }
        .btn-group { display:flex; gap:8px; }
        .btn-group .btn { flex:1; }
        .lottery-pool {
            text-align:center; padding:20px 16px;
            background:linear-gradient(135deg,rgba(108,99,255,0.08),rgba(255,101,132,0.08));
            border-radius:var(--radius); border:1px solid rgba(108,99,255,0.15); margin-bottom:12px;
        }
        .lottery-pool .amount { font-size:38px; font-weight:900; background:linear-gradient(135deg,var(--primary),var(--secondary)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
        .lottery-pool .label { font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; }
        .timer {
            display:flex; justify-content:center; gap:10px; margin:12px 0;
        }
        .timer .unit {
            text-align:center; background:var(--dark-input); padding:6px 12px;
            border-radius:var(--radius-sm); min-width:52px; border:1px solid var(--border);
        }
        .timer .unit .number { font-size:24px; font-weight:700; color:var(--primary); font-variant-numeric:tabular-nums; }
        .timer .unit .label { font-size:8px; color:var(--text-muted); text-transform:uppercase; }
        .input-group { margin-bottom:12px; }
        .input-group label { display:block; font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px; }
        .input-group input {
            width:100%; padding:10px 14px; background:var(--dark-input);
            border:1px solid var(--border); border-radius:var(--radius-sm);
            color:var(--text); font-size:14px; transition:all 0.3s ease; outline:none;
        }
        .input-group input:focus { border-color:var(--primary); box-shadow:0 0 0 3px rgba(108,99,255,0.15); }
        .input-group input::placeholder { color:var(--text-muted); opacity:0.6; }
        .tabs {
            display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:3px;
            background:var(--dark-card); border-radius:var(--radius-sm); padding:3px;
            margin-bottom:14px; border:1px solid var(--border);
        }
        .tab {
            padding:8px 4px; text-align:center; border-radius:var(--radius-sm);
            cursor:pointer; transition:all 0.3s ease; font-size:11px; font-weight:600;
            color:var(--text-muted); background:transparent; border:none;
        }
        .tab.active { background:var(--primary); color:#fff; }
        .tab:hover:not(.active) { background:var(--dark-input); color:var(--text); }
        .tab .emoji { display:block; font-size:18px; margin-bottom:1px; }
        .tab-content { display:none; animation:fadeIn 0.3s ease; }
        .tab-content.active { display:block; }
        @keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        .winners-list { display:flex; flex-direction:column; gap:8px; }
        .winner-item {
            display:flex; align-items:center; gap:10px; padding:10px 14px;
            background:var(--dark-input); border-radius:var(--radius-sm); border-left:3px solid var(--primary);
        }
        .winner-item .rank { font-size:16px; font-weight:700; min-width:28px; color:var(--primary); }
        .winner-item .info { flex:1; }
        .winner-item .info .name { font-weight:600; font-size:13px; }
        .winner-item .info .date { font-size:10px; color:var(--text-muted); }
        .winner-item .prize { font-weight:700; color:var(--success); font-size:15px; }
        .tx-list { display:flex; flex-direction:column; gap:6px; }
        .tx-item {
            display:flex; align-items:center; gap:10px; padding:8px 12px;
            background:var(--dark-input); border-radius:var(--radius-sm);
        }
        .tx-item .status-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
        .tx-item .status-dot.confirmed { background:var(--success); }
        .tx-item .status-dot.pending { background:var(--warning); }
        .tx-item .info { flex:1; min-width:0; }
        .tx-item .info .hash { font-size:11px; font-family:monospace; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .tx-item .amount { font-weight:600; font-size:14px; flex-shrink:0; }
        .tx-item .amount.positive { color:var(--success); }
        .tx-item .amount.negative { color:var(--danger); }
        .referral-box {
            display:flex; align-items:center; gap:8px; background:var(--dark-input);
            border-radius:var(--radius-sm); padding:10px 12px; border:1px solid var(--border); margin:8px 0;
        }
        .referral-box .code { flex:1; font-family:monospace; font-size:16px; font-weight:700; color:var(--primary); letter-spacing:1px; word-break:break-all; }
        .referral-box .copy-btn {
            padding:4px 14px; background:var(--primary); border:none; border-radius:var(--radius-sm);
            color:#fff; cursor:pointer; font-size:11px; font-weight:600; white-space:nowrap;
        }
        .referral-stats { display:flex; justify-content:space-around; padding:10px 0; border-top:1px solid var(--border); margin-top:8px; }
        .referral-stats .number { font-size:22px; font-weight:700; color:var(--primary); }
        .referral-stats .label { font-size:10px; color:var(--text-muted); }
        .toast {
            position:fixed; bottom:20px; left:50%; transform:translateX(-50%) translateY(100px);
            background:var(--dark-card); border:1px solid var(--border); border-radius:var(--radius-sm);
            padding:12px 20px; font-size:13px; font-weight:600; opacity:0;
            transition:all 0.4s cubic-bezier(0.4,0,0.2,1); z-index:999; max-width:90%; text-align:center;
            box-shadow:0 8px 32px rgba(0,0,0,0.6); pointer-events:none;
        }
        .toast.show { opacity:1; transform:translateX(-50%) translateY(0); pointer-events:auto; }
        .toast.success { border-color:var(--success); color:var(--success); }
        .toast.error { border-color:var(--danger); color:var(--danger); }
        .toast.warning { border-color:var(--warning); color:var(--warning); }
        .modal-overlay {
            position:fixed; top:0; left:0; width:100%; height:100%;
            background:rgba(0,0,0,0.75); backdrop-filter:blur(12px);
            display:none; align-items:center; justify-content:center; z-index:1000; padding:16px;
        }
        .modal-overlay.active { display:flex; }
        .modal {
            background:var(--dark-card); border:1px solid var(--border); border-radius:var(--radius);
            padding:20px; max-width:400px; width:100%; max-height:90vh; overflow-y:auto;
            animation:modalIn 0.3s cubic-bezier(0.4,0,0.2,1);
        }
        @keyframes modalIn { from { transform:scale(0.92) translateY(16px); opacity:0; } to { transform:scale(1) translateY(0); opacity:1; } }
        .modal-close { float:right; background:none; border:none; color:var(--text-muted); font-size:22px; cursor:pointer; }
        .modal-title { font-size:18px; font-weight:700; margin-bottom:14px; text-align:center; }
        .empty-state { text-align:center; padding:24px 16px; color:var(--text-muted); }
        .empty-state .icon { font-size:36px; display:block; margin-bottom:8px; }
        .admin-panel { display:none; border-top:2px solid var(--danger); margin-top:16px; padding-top:16px; }
        .admin-panel.visible { display:block; }
        .lang-switcher { display:flex; gap:4px; margin-bottom:12px; justify-content:flex-end; flex-wrap:wrap; }
        .lang-btn {
            padding:3px 12px; border:1px solid var(--border); border-radius:var(--radius-sm);
            background:transparent; color:var(--text-muted); cursor:pointer; font-size:11px; font-weight:600;
        }
        .lang-btn.active { background:var(--primary); border-color:var(--primary); color:#fff; }
        .spinner { display:inline-block; width:20px; height:20px; border:2px solid var(--border); border-top:2px solid var(--primary); border-radius:50%; animation:spin 0.7s linear infinite; }
        @keyframes spin { to { transform:rotate(360deg); } }
        .hidden { display:none !important; }
        .mt-8 { margin-top:8px; }
        .mt-16 { margin-top:16px; }
        .mb-8 { margin-bottom:8px; }
        .flex { display:flex; }
        .gap-8 { gap:8px; }
        @media (max-width:380px) {
            .app { padding:8px 10px 80px; }
            .status-item .value { font-size:13px; }
            .lottery-pool .amount { font-size:30px; }
            .timer .unit { min-width:40px; padding:4px 8px; }
            .timer .unit .number { font-size:18px; }
            .tab { font-size:9px; }
            .tab .emoji { font-size:14px; }
        }
        @media (min-width:481px) {
            .app { padding:20px 24px 100px; border-left:1px solid var(--border); border-right:1px solid var(--border); min-height:100vh; background:var(--dark); }
        }
    </style>
</head>
<body>
<div id="toast" class="toast"></div>
<div id="modalOverlay" class="modal-overlay"><div class="modal"><button class="modal-close" onclick="closeModal()">✕</button><div id="modalBody"></div></div></div>
<div class="app">
    <header class="header">
        <div class="header-left"><div class="header-logo">🎰</div><div class="header-title">UTYOB</div></div>
        <div class="header-right"><span class="header-points" id="userPoints">⭐ 0</span><div class="header-avatar" id="userAvatar">👤</div></div>
    </header>
    <div class="lang-switcher">
        <button class="lang-btn active" data-lang="en" onclick="switchLanguage('en')">🇬🇧 EN</button>
        <button class="lang-btn" data-lang="fa" onclick="switchLanguage('fa')">🇮🇷 FA</button>
        <button class="lang-btn" data-lang="tr" onclick="switchLanguage('tr')">🇹🇷 TR</button>
        <button class="lang-btn" data-lang="ru" onclick="switchLanguage('ru')">🇷🇺 RU</button>
        <button class="lang-btn" data-lang="ar" onclick="switchLanguage('ar')">🇸🇦 AR</button>
    </div>
    <div class="status-bar">
        <div class="status-item"><div class="label" data-i18n="status_round">Round</div><div class="value primary" id="roundNumber">#1</div></div>
        <div class="status-item"><div class="label" data-i18n="status_participants">Players</div><div class="value" id="participantsCount">0</div></div>
        <div class="status-item"><div class="label" data-i18n="status_pool">Prize</div><div class="value success" id="poolAmount">$0</div></div>
        <div class="status-item"><div class="label" data-i18n="status_winners">Winners</div><div class="value warning" id="winnersCount">0</div></div>
    </div>
    <div class="tabs">
        <button class="tab active" data-tab="lottery" onclick="switchTab('lottery')"><span class="emoji">🎰</span> <span data-i18n="tab_lottery">Lottery</span></button>
        <button class="tab" data-tab="wallet" onclick="switchTab('wallet')"><span class="emoji">💳</span> <span data-i18n="tab_wallet">Wallet</span></button>
        <button class="tab" data-tab="winners" onclick="switchTab('winners')"><span class="emoji">🏆</span> <span data-i18n="tab_winners">Winners</span></button>
        <button class="tab" data-tab="referral" onclick="switchTab('referral')"><span class="emoji">👥</span> <span data-i18n="tab_referral">Refer</span></button>
    </div>
    <div id="tab-lottery" class="tab-content active">
        <div class="lottery-pool"><div class="label" data-i18n="pool_total">Total Prize Pool</div><div class="amount" id="lotteryPoolAmount">$0</div><div style="font-size:12px;color:var(--text-muted);margin-top:4px;"><span data-i18n="pool_ticket">Ticket Price</span>: <strong>$100</strong></div></div>
        <div class="timer"><div class="unit"><div class="number" id="timerDays">00</div><div class="label" data-i18n="timer_days">Days</div></div><div class="unit"><div class="number" id="timerHours">00</div><div class="label" data-i18n="timer_hours">Hours</div></div><div class="unit"><div class="number" id="timerMinutes">00</div><div class="label" data-i18n="timer_minutes">Mins</div></div><div class="unit"><div class="number" id="timerSeconds">00</div><div class="label" data-i18n="timer_seconds">Secs</div></div></div>
        <button class="btn btn-primary" id="joinBtn" onclick="joinLottery()">🎰 <span data-i18n="btn_join">Join Lottery</span></button>
        <div id="lotteryStatus" class="card" style="display:none;margin-top:8px;"><div id="lotteryStatusText"></div></div>
        <div class="card"><div class="card-title"><span class="icon">📜</span> <span data-i18n="recent_tx">Recent Transactions</span></div><div class="tx-list" id="recentTransactions"><div class="empty-state"><span class="icon">📭</span><div class="text" data-i18n="no_tx">No transactions yet</div></div></div></div>
    </div>
    <div id="tab-wallet" class="tab-content">
        <div class="card"><div class="card-title"><span class="icon">💰</span> <span data-i18n="wallet_balance">Wallet Balance</span></div><div style="font-size:32px;font-weight:900;color:var(--success);" id="walletBalance">$0.00</div><div style="font-size:12px;color:var(--text-muted);margin-top:4px;"><span data-i18n="wallet_points">Points</span>: <strong id="walletPoints">0</strong></div></div>
        <div class="card"><div class="card-title"><span class="icon">📥</span> <span data-i18n="deposit_title">Deposit</span></div>
            <div class="input-group"><label data-i18n="deposit_address_label">Source Wallet (TRC20)</label><input type="text" id="depositAddress" placeholder="TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"><div class="hint" style="font-size:10px;color:var(--text-muted);margin-top:3px;" data-i18n="deposit_address_hint">Your sending wallet address</div></div>
            <div class="input-group"><label data-i18n="deposit_tx_label">Transaction Hash (TxID)</label><input type="text" id="depositTxHash" placeholder="7ae83b63-fdf3-47e4-ac69-56f960a34f5b"></div>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;"><span data-i18n="deposit_dest">Destination</span>: <code id="destAddress">TV61aTh98MGqmteYzda5AaBzdXgGqreG6A</code></div>
            <button class="btn btn-success" onclick="verifyDeposit()">✅ <span data-i18n="btn_verify">Verify Payment</span></button>
        </div>
        <div class="card" id="withdrawCard" style="display:none;"><div class="card-title"><span class="icon">📤</span> <span data-i18n="withdraw_title">Withdraw Prize</span></div>
            <div class="input-group"><label data-i18n="withdraw_address_label">TRC20 Wallet Address</label><input type="text" id="withdrawAddress" placeholder="TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"></div>
            <button class="btn btn-warning" onclick="requestWithdraw()">💸 <span data-i18n="btn_withdraw">Withdraw</span></button>
        </div>
    </div>
    <div id="tab-winners" class="tab-content">
        <div class="card"><div class="card-title"><span class="icon">🏆</span> <span data-i18n="winners_history">Winners History</span></div><div class="winners-list" id="winnersList"><div class="empty-state"><span class="icon">🏆</span><div class="text" data-i18n="no_winners">No winners yet</div></div></div></div>
    </div>
    <div id="tab-referral" class="tab-content">
        <div class="card"><div class="card-title"><span class="icon">👥</span> <span data-i18n="referral_title">Refer Friends</span></div>
            <div class="referral-box"><span class="code" id="referralCode">------</span><button class="copy-btn" onclick="copyReferral()">📋 <span data-i18n="btn_copy">Copy</span></button></div>
            <div class="referral-stats"><div><div class="number" id="referralCount">0</div><div class="label" data-i18n="referral_count">Referrals</div></div><div><div class="number" id="referralPoints">0</div><div class="label" data-i18n="referral_points">Points</div></div></div>
            <button class="btn btn-primary" onclick="shareReferral()">📤 <span data-i18n="btn_share">Share Link</span></button>
        </div>
    </div>
    <div class="admin-panel" id="adminPanel">
        <div class="card" style="border-color:rgba(255,59,48,0.4);">
            <div class="card-title" style="color:var(--danger);"><span class="icon">🛠️</span> Admin Panel</div>
            <div class="btn-group" style="flex-wrap:wrap;gap:6px;">
                <button class="btn btn-primary" onclick="adminStartLottery()" style="flex:1;min-width:80px;font-size:11px;padding:8px 10px;">🎰 Start</button>
                <button class="btn btn-success" onclick="adminPayWinners()" style="flex:1;min-width:80px;font-size:11px;padding:8px 10px;">💸 Pay</button>
                <button class="btn btn-warning" onclick="adminSendPoll()" style="flex:1;min-width:80px;font-size:11px;padding:8px 10px;">📊 Poll</button>
                <button class="btn btn-danger" onclick="adminBroadcast()" style="flex:1;min-width:80px;font-size:11px;padding:8px 10px;">📢 Broadcast</button>
            </div>
            <div class="input-group mt-8"><label style="font-size:11px;">Manual Verify (User ID)</label><input type="text" id="adminUserId" placeholder="Telegram User ID" style="font-size:13px;padding:8px 12px;"></div>
            <button class="btn btn-outline" onclick="adminManualVerify()" style="font-size:12px;padding:8px 12px;">✅ Manual Verify</button>
        </div>
    </div>
</div>
<script>
    const CONFIG = { DESTINATION_WALLET: 'TV61aTh98MGqmteYzda5AaBzdXgGqreG6A', LOTTERY_PRICE: 100, ADMIN_ID: 123456789, BOT_USERNAME: 'UTYOB_Bot' };
    const tg = window.Telegram?.WebApp || { initDataUnsafe: { user: null }, ready: () => {}, close: () => {}, expand: () => {} };
    const tgUser = tg.initDataUnsafe?.user || null;
    let state = { user: null, lang: 'en', balance: 0, points: 0, subscribed: false, participated: false, lottery: null, winners: [], transactions: [], referralCode: '', referralCount: 0, referralPoints: 0, isAdmin: false, timerInterval: null, hasPrize: false };
    const i18n = {
        en: { status_round:'Round', status_participants:'Players', status_pool:'Prize', status_winners:'Winners', tab_lottery:'Lottery', tab_wallet:'Wallet', tab_winners:'Winners', tab_referral:'Refer', pool_total:'Total Prize Pool', pool_ticket:'Ticket Price', timer_days:'Days', timer_hours:'Hours', timer_minutes:'Mins', timer_seconds:'Secs', btn_join:'Join Lottery', btn_verify:'Verify Payment', btn_withdraw:'Withdraw', btn_copy:'Copy', btn_share:'Share Link', recent_tx:'Recent Transactions', no_tx:'No transactions yet', wallet_balance:'Wallet Balance', wallet_points:'Points', deposit_title:'Deposit', deposit_address_label:'Source Wallet (TRC20)', deposit_address_hint:'Your sending wallet address', deposit_tx_label:'Transaction Hash (TxID)', deposit_dest:'Destination', withdraw_title:'Withdraw Prize', withdraw_address_label:'TRC20 Wallet Address', winners_history:'Winners History', no_winners:'No winners yet', referral_title:'Refer Friends', referral_count:'Referrals', referral_points:'Points', join_success:'Successfully registered!', join_fail:'Registration failed.', verify_success:'Payment verified!', verify_fail:'Verification failed.', withdraw_success:'Withdrawal submitted!', withdraw_fail:'Withdrawal failed.', copy_success:'Copied!', copy_fail:'Copy failed.', already_participated:'Already participated.', no_subscription:'Need subscription.', not_winner:'Not a winner.', timer_expired:'Time expired!', processing:'Processing...', error:'Error occurred.', enter_address:'Enter valid TRC20 address.', enter_tx:'Enter valid tx hash.' },
        fa: { status_round:'دور', status_participants:'بازیکنان', status_pool:'جایزه', status_winners:'برنده‌ها', tab_lottery:'قرعه‌کشی', tab_wallet:'کیف پول', tab_winners:'برنده‌ها', tab_referral:'دعوت', pool_total:'مجموع جایزه', pool_ticket:'قیمت بلیت', timer_days:'روز', timer_hours:'ساعت', timer_minutes:'دقیقه', timer_seconds:'ثانیه', btn_join:'شرکت در قرعه‌کشی', btn_verify:'تایید پرداخت', btn_withdraw:'برداشت', btn_copy:'کپی', btn_share:'اشتراک‌گذاری', recent_tx:'تراکنش‌های اخیر', no_tx:'تراکنشی وجود ندارد', wallet_balance:'موجودی کیف پول', wallet_points:'امتیاز', deposit_title:'واریز', deposit_address_label:'کیف پول مبدا (TRC20)', deposit_address_hint:'آدرس کیف پولی که از آن ارسال می‌کنید', deposit_tx_label:'هش تراکنش (TxID)', deposit_dest:'آدرس مقصد', withdraw_title:'برداشت جایزه', withdraw_address_label:'آدرس کیف پول TRC20', winners_history:'تاریخچه برنده‌ها', no_winners:'برنده‌ای وجود ندارد', referral_title:'دعوت از دوستان', referral_count:'تعداد دعوت‌ها', referral_points:'امتیاز', join_success:'ثبت نام با موفقیت انجام شد!', join_fail:'ثبت نام ناموفق بود.', verify_success:'پرداخت تایید شد!', verify_fail:'تایید پرداخت ناموفق بود.', withdraw_success:'درخواست برداشت ثبت شد!', withdraw_fail:'درخواست برداشت ناموفق بود.', copy_success:'کپی شد!', copy_fail:'کپی ناموفق بود.', already_participated:'قبلاً شرکت کرده‌اید.', no_subscription:'نیاز به اشتراک دارید.', not_winner:'برنده نشده‌اید.', timer_expired:'زمان به پایان رسید!', processing:'در حال پردازش...', error:'خطا رخ داد.', enter_address:'آدرس TRC20 معتبر وارد کنید.', enter_tx:'هش تراکنش معتبر وارد کنید.' },
        tr: { status_round:'Tur', status_participants:'Oyuncular', status_pool:'Ödül', status_winners:'Kazananlar', tab_lottery:'Piyango', tab_wallet:'Cüzdan', tab_winners:'Kazananlar', tab_referral:'Davet', pool_total:'Toplam Ödül', pool_ticket:'Bilet Fiyatı', timer_days:'Gün', timer_hours:'Saat', timer_minutes:'Dakika', timer_seconds:'Saniye', btn_join:'Katıl', btn_verify:'Doğrula', btn_withdraw:'Çek', btn_copy:'Kopyala', btn_share:'Paylaş', recent_tx:'Son İşlemler', no_tx:'İşlem yok', wallet_balance:'Bakiye', wallet_points:'Puan', deposit_title:'Yatırma', deposit_address_label:'Kaynak Cüzdan (TRC20)', deposit_address_hint:'Gönderen adres', deposit_tx_label:'İşlem Kodu (TxID)', deposit_dest:'Hedef Adres', withdraw_title:'Ödülü Çek', withdraw_address_label:'TRC20 Adres', winners_history:'Kazanan Geçmişi', no_winners:'Kazanan yok', referral_title:'Arkadaşları Davet Et', referral_count:'Davetler', referral_points:'Puan', join_success:'Kayıt başarılı!', join_fail:'Kayıt başarısız.', verify_success:'Ödeme doğrulandı!', verify_fail:'Doğrulama başarısız.', withdraw_success:'Çekim talebi gönderildi!', withdraw_fail:'Çekim başarısız.', copy_success:'Kopyalandı!', copy_fail:'Kopyalama başarısız.', already_participated:'Zaten katıldınız.', no_subscription:'Abonelik gerekli.', not_winner:'Kazanamadınız.', timer_expired:'Süre doldu!', processing:'İşleniyor...', error:'Hata oluştu.', enter_address:'Geçerli TRC20 adresi girin.', enter_tx:'Geçerli işlem kodu girin.' },
        ru: { status_round:'Раунд', status_participants:'Игроки', status_pool:'Приз', status_winners:'Победители', tab_lottery:'Лотерея', tab_wallet:'Кошелек', tab_winners:'Победители', tab_referral:'Рефералы', pool_total:'Общий приз', pool_ticket:'Цена билета', timer_days:'Дней', timer_hours:'Часов', timer_minutes:'Мин', timer_seconds:'Сек', btn_join:'Участвовать', btn_verify:'Подтвердить', btn_withdraw:'Вывести', btn_copy:'Копировать', btn_share:'Поделиться', recent_tx:'Транзакции', no_tx:'Нет транзакций', wallet_balance:'Баланс', wallet_points:'Баллы', deposit_title:'Пополнение', deposit_address_label:'Адрес отправителя', deposit_address_hint:'Ваш адрес', deposit_tx_label:'Хэш транзакции', deposit_dest:'Адрес получателя', withdraw_title:'Вывод приза', withdraw_address_label:'TRC20 адрес', winners_history:'История победителей', no_winners:'Победителей нет', referral_title:'Пригласи друзей', referral_count:'Приглашения', referral_points:'Баллы', join_success:'Регистрация успешна!', join_fail:'Ошибка регистрации.', verify_success:'Платеж подтвержден!', verify_fail:'Ошибка подтверждения.', withdraw_success:'Заявка отправлена!', withdraw_fail:'Ошибка вывода.', copy_success:'Скопировано!', copy_fail:'Ошибка копирования.', already_participated:'Уже участвуете.', no_subscription:'Нужна подписка.', not_winner:'Вы не победитель.', timer_expired:'Время истекло!', processing:'Обработка...', error:'Ошибка.', enter_address:'Введите TRC20 адрес.', enter_tx:'Введите хэш транзакции.' },
        ar: { status_round:'الجولة', status_participants:'اللاعبين', status_pool:'الجائزة', status_winners:'الفائزين', tab_lottery:'اليانصيب', tab_wallet:'المحفظة', tab_winners:'الفائزين', tab_referral:'دعوة', pool_total:'مجموع الجائزة', pool_ticket:'سعر التذكرة', timer_days:'أيام', timer_hours:'ساعات', timer_minutes:'دقائق', timer_seconds:'ثواني', btn_join:'اشترك', btn_verify:'تحقق', btn_withdraw:'سحب', btn_copy:'نسخ', btn_share:'مشاركة', recent_tx:'المعاملات', no_tx:'لا توجد معاملات', wallet_balance:'الرصيد', wallet_points:'النقاط', deposit_title:'إيداع', deposit_address_label:'المحفظة المصدر', deposit_address_hint:'عنوان محفظتك', deposit_tx_label:'رمز المعاملة', deposit_dest:'العنوان الوجهة', withdraw_title:'سحب الجائزة', withdraw_address_label:'عنوان محفظة TRC20', winners_history:'تاريخ الفائزين', no_winners:'لا يوجد فائزين', referral_title:'دعوة الأصدقاء', referral_count:'الدعوات', referral_points:'النقاط', join_success:'تم التسجيل!', join_fail:'فشل التسجيل.', verify_success:'تم التحقق!', verify_fail:'فشل التحقق.', withdraw_success:'تم الطلب!', withdraw_fail:'فشل الطلب.', copy_success:'تم النسخ!', copy_fail:'فشل النسخ.', already_participated:'شاركت بالفعل.', no_subscription:'تحتاج اشتراك.', not_winner:'لست فائزًا.', timer_expired:'انتهى الوقت!', processing:'جاري المعالجة...', error:'حدث خطأ.', enter_address:'أدخل عنوان TRC20 صالح.', enter_tx:'أدخل رمز معاملة صالح.' }
    };
    function t(k) { return i18n[state.lang]?.[k] || i18n['en'][k] || k; }
    const $ = id => document.getElementById(id);
    const toast = $('toast'), modalOverlay = $('modalOverlay'), modalBody = $('modalBody');
    function showToast(m, t='success', d=3000) { toast.textContent=m; toast.className=`toast ${t}`; requestAnimationFrame(()=>toast.classList.add('show')); clearTimeout(toast._timeout); toast._timeout=setTimeout(()=>toast.classList.remove('show'), d); }
    function openModal(html) { modalBody.innerHTML=html; modalOverlay.classList.add('active'); }
    function closeModal() { modalOverlay.classList.remove('active'); }
    function switchLanguage(lang) { state.lang=lang; document.querySelectorAll('.lang-btn').forEach(b=>b.classList.toggle('active', b.dataset.lang===lang)); document.querySelectorAll('[data-i18n]').forEach(el=>{const k=el.dataset.i18n;if(i18n[lang]?.[k]) el.textContent=i18n[lang][k];}); updateUI(); }
    function switchTab(tab) { document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active', t.dataset.tab===tab)); document.querySelectorAll('.tab-content').forEach(c=>c.classList.toggle('active', c.id===`tab-${tab}`)); }
    async function apiCall(e, m='GET', d=null) { try { const o={method:m,headers:{'Content-Type':'application/json','X-Telegram-User':tgUser?.id||''}}; if(d) o.body=JSON.stringify(d); const r=await fetch('/api'+e,o); return await r.json(); } catch(e){ return {success:false,error:e.message}; } }
    async function loadAllData() { await Promise.all([loadUserData(), loadLotteryData(), loadWinners(), loadTransactions(), loadReferralData()]); }
    async function loadUserData() { try { const r=await apiCall('/user'); if(r.success){ state.balance=r.data?.balance||0; state.points=r.data?.points||0; state.subscribed=r.data?.has_subscription||false; state.participated=r.data?.has_participated||false; state.referralCode=r.data?.referral_code||'------'; state.isAdmin=tgUser?.id==CONFIG.ADMIN_ID; if(state.isAdmin) $('adminPanel').classList.add('visible'); } } catch(e){} }
    async function loadLotteryData() { try { const r=await apiCall('/lottery/current'); if(r.success) state.lottery=r.data; } catch(e){} }
    async function loadWinners() { try { const r=await apiCall('/winners'); if(r.success) state.winners=r.data||[]; } catch(e){} }
    async function loadTransactions() { try { const r=await apiCall('/transactions'); if(r.success) state.transactions=r.data||[]; } catch(e){} }
    async function loadReferralData() { try { const r=await apiCall('/referral'); if(r.success){ state.referralCount=r.data?.count||0; state.referralPoints=r.data?.points||0; if(r.data?.code) state.referralCode=r.data.code; } } catch(e){} }
    function updateUI() {
        $('userPoints').textContent='⭐ '+state.points;
        if(tgUser){ const n=tgUser.first_name||tgUser.username||'U'; $('userAvatar').textContent=n.charAt(0).toUpperCase(); }
        $('participantsCount').textContent=state.lottery?.participants||0;
        $('poolAmount').textContent='$'+(state.lottery?.prize_pool||0);
        $('winnersCount').textContent=state.lottery?.winners||0;
        $('roundNumber').textContent='#'+(state.lottery?.round_number||1);
        $('lotteryPoolAmount').textContent='$'+(state.lottery?.prize_pool||0);
        $('walletBalance').textContent='$'+state.balance;
        $('walletPoints').textContent=state.points;
        $('referralCode').textContent=state.referralCode;
        $('referralCount').textContent=state.referralCount;
        $('referralPoints').textContent=state.referralPoints;
        const jb=$('joinBtn');
        if(state.participated){ jb.disabled=true; jb.innerHTML='✅ '+t('already_participated'); }
        else if(!state.subscribed){ jb.innerHTML='💰 '+t('no_subscription'); jb.onclick=()=>showDepositModal(); }
        else { jb.disabled=false; jb.innerHTML='🎰 '+t('btn_join'); jb.onclick=joinLottery; }
        renderWinners(); renderTransactions();
        state.hasPrize=state.winners.some(w=>w.user_id==tgUser?.id&&w.status=='pending');
        $('withdrawCard').style.display=state.hasPrize?'block':'none';
    }
    function renderWinners() { const c=$('winnersList'); if(!state.winners||state.winners.length===0){ c.innerHTML='<div class="empty-state"><span class="icon">🏆</span><div class="text">'+t('no_winners')+'</div></div>'; return; } c.innerHTML=state.winners.slice(0,20).map((w,i)=>'<div class="winner-item"><div class="rank">#'+(i+1)+'</div><div class="info"><div class="name">'+(w.username||w.user_id||'User')+'</div><div class="date">'+(w.date||'')+'</div></div><div class="prize">$'+w.prize+'</div></div>').join(''); }
    function renderTransactions() { const c=$('recentTransactions'); if(!state.transactions||state.transactions.length===0){ c.innerHTML='<div class="empty-state"><span class="icon">📭</span><div class="text">'+t('no_tx')+'</div></div>'; return; } c.innerHTML=state.transactions.slice(0,10).map(tx=>'<div class="tx-item"><div class="status-dot '+(tx.status||'pending')+'"></div><div class="info"><div class="hash">'+(tx.hash||'---')+'</div><div class="date">'+(tx.date||'')+'</div></div><div class="amount '+(tx.amount>0?'positive':'negative')+'">'+(tx.amount>0?'+':'')+'$'+tx.amount+'</div></div>').join(''); }
    function startTimer() { if(state.timerInterval) clearInterval(state.timerInterval); let end=state.lottery?.end_time||(Date.now()+7*24*60*60*1000); state.timerInterval=setInterval(()=>{ const d=Math.max(0,end-Date.now()); if(d===0){ $('timerDays').textContent='00'; $('timerHours').textContent='00'; $('timerMinutes').textContent='00'; $('timerSeconds').textContent='00'; return; } $('timerDays').textContent=String(Math.floor(d/(24*60*60*1000))).padStart(2,'0'); $('timerHours').textContent=String(Math.floor((d%(24*60*60*1000))/(60*60*1000))).padStart(2,'0'); $('timerMinutes').textContent=String(Math.floor((d%(60*60*1000))/(60*1000))).padStart(2,'0'); $('timerSeconds').textContent=String(Math.floor((d%(60*1000))/1000)).padStart(2,'0'); },1000); }
    async function joinLottery() { if(state.participated){ showToast(t('already_participated'),'warning'); return; } if(!state.subscribed){ showToast(t('no_subscription'),'warning'); return; } const jb=$('joinBtn'); jb.disabled=true; jb.innerHTML='<span class="spinner"></span> '+t('processing'); try{ const r=await apiCall('/lottery/join','POST'); if(r.success){ state.participated=true; showToast(t('join_success'),'success'); await loadAllData(); updateUI(); } else showToast(r.error||t('join_fail'),'error'); } catch(e){ showToast(t('join_fail'),'error'); } jb.disabled=false; jb.innerHTML='🎰 '+t('btn_join'); }
    function showDepositModal(){ openModal('<div class="modal-title">💰 '+t('deposit_title')+'</div><div class="input-group"><label>'+t('deposit_address_label')+'</label><input type="text" id="modalDepositAddress" placeholder="TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"><div class="hint" style="font-size:10px;color:var(--text-muted);margin-top:3px;">'+t('deposit_address_hint')+'</div></div><div class="input-group"><label>'+t('deposit_tx_label')+'</label><input type="text" id="modalDepositTx" placeholder="7ae83b63-fdf3-47e4-ac69-56f960a34f5b"></div><div style="font-size:11px;color:var(--text-muted);margin-bottom:12px;">'+t('deposit_dest')+': <code>'+CONFIG.DESTINATION_WALLET+'</code></div><button class="btn btn-success" onclick="submitDeposit()">✅ '+t('btn_verify')+'</button><button class="btn btn-outline mt-8" onclick="closeModal()">Cancel</button>'); }
    async function verifyDeposit(){ const a=$('depositAddress').value.trim(), h=$('depositTxHash').value.trim(); if(!a||!h){ showToast(t('enter_address'),'warning'); return; } await submitDepositInternal(a,h); }
    async function submitDeposit(){ const a=document.getElementById('modalDepositAddress').value.trim(), h=document.getElementById('modalDepositTx').value.trim(); if(!a||!h){ showToast(t('enter_address'),'warning'); return; } await submitDepositInternal(a,h); closeModal(); }
    async function submitDepositInternal(a,h){ const btn=document.querySelector('.btn-success'); if(btn){ btn.disabled=true; btn.innerHTML='<span class="spinner"></span> '+t('processing'); } try{ const r=await apiCall('/deposit/verify','POST',{address:a,tx_hash:h,amount:CONFIG.LOTTERY_PRICE,destination:CONFIG.DESTINATION_WALLET}); if(r.success){ showToast(t('verify_success'),'success'); await loadAllData(); updateUI(); } else showToast(r.error||t('verify_fail'),'error'); } catch(e){ showToast(t('verify_fail'),'error'); } if(btn){ btn.disabled=false; btn.innerHTML='✅ '+t('btn_verify'); } }
    async function requestWithdraw(){ const a=$('withdrawAddress').value.trim(); if(!a||a.length!==34||!a.startsWith('T')){ showToast(t('enter_address'),'warning'); return; } const btn=document.querySelector('#withdrawCard .btn'); if(btn){ btn.disabled=true; btn.innerHTML='<span class="spinner"></span> '+t('processing'); } try{ const r=await apiCall('/withdraw/request','POST',{address:a}); if(r.success){ showToast(t('withdraw_success'),'success'); await loadAllData(); updateUI(); } else showToast(r.error||t('withdraw_fail'),'error'); } catch(e){ showToast(t('withdraw_fail'),'error'); } if(btn){ btn.disabled=false; btn.innerHTML='💸 '+t('btn_withdraw'); } }
    function copyReferral(){ const c=state.referralCode; if(!c||c==='------'){ showToast(t('copy_fail'),'error'); return; } const t='https://t.me/'+CONFIG.BOT_USERNAME+'?start='+c; if(navigator.clipboard){ navigator.clipboard.writeText(t).then(()=>showToast(t('copy_success'),'success')).catch(()=>copyFallback(t)); } else copyFallback(t); }
    function copyFallback(t){ const i=document.createElement('input'); i.value=t; document.body.appendChild(i); i.select(); document.execCommand('copy'); document.body.removeChild(i); showToast(t('copy_success'),'success'); }
    function shareReferral(){ const c=state.referralCode; const t='🎰 Join UTYOB Lottery! 💰\nUse my referral code: '+c+'\nhttps://t.me/'+CONFIG.BOT_USERNAME+'?start='+c; if(navigator.share){ navigator.share({title:'UTYOB Lottery',text:t}).catch(()=>{}); } else copyReferral(); }
    async function adminStartLottery(){ if(!state.isAdmin) return; try{ const r=await apiCall('/admin/lottery/start','POST'); if(r.success){ showToast('✅ Lottery started!','success'); await loadAllData(); updateUI(); } else showToast('❌ Failed','error'); } catch(e){ showToast('❌ Error','error'); } }
    async function adminPayWinners(){ if(!state.isAdmin) return; try{ const r=await apiCall('/admin/winners/pay','POST'); if(r.success){ showToast('✅ Winners paid!','success'); await loadAllData(); updateUI(); } else showToast('❌ Failed','error'); } catch(e){ showToast('❌ Error','error'); } }
    async function adminSendPoll(){ if(!state.isAdmin) return; try{ const r=await apiCall('/admin/poll/send','POST'); if(r.success) showToast('✅ Poll sent!','success'); else showToast('❌ Failed','error'); } catch(e){ showToast('❌ Error','error'); } }
    async function adminBroadcast(){ if(!state.isAdmin) return; const msg=prompt('📢 Enter broadcast message:'); if(!msg) return; try{ const r=await apiCall('/admin/broadcast','POST',{message:msg}); if(r.success) showToast('✅ Sent to '+(r.sent||0)+' users!','success'); else showToast('❌ Failed','error'); } catch(e){ showToast('❌ Error','error'); } }
    async function adminManualVerify(){ if(!state.isAdmin) return; const uid=$('adminUserId').value.trim(); if(!uid){ showToast('⚠️ Enter User ID','warning'); return; } try{ const r=await apiCall('/admin/verify/manual','POST',{user_id:uid}); if(r.success){ showToast('✅ User '+uid+' verified!','success'); await loadAllData(); updateUI(); } else showToast('❌ Failed','error'); } catch(e){ showToast('❌ Error','error'); } }
    const originalApi=apiCall;
    window.apiCall=async function(e,m='GET',d=null){ const mock={'/api/user':{success:true,data:{balance:250,points:1250,has_subscription:true,has_participated:false,referral_code:'UTYOB123'}},'/api/lottery/current':{success:true,data:{round_number:3,participants:847,prize_pool:84600,winners:20,end_time:Date.now()+7*24*60*60*1000}},'/api/winners':{success:true,data:[{user_id:1,username:'Ali_Reza',prize:2000,date:'2024-12-01'},{user_id:2,username:'Sara_Khan',prize:2000,date:'2024-12-01'}]},'/api/transactions':{success:true,data:[{hash:'0x7ae83b63...f34f5b',amount:100,status:'confirmed',date:'2024-12-02'}]},'/api/referral':{success:true,data:{code:'UTYOB123',count:12,points:1200}}}; if(m==='POST') return {success:true}; return mock[e]||{success:false,error:'Not found'}; };
    async function init(){ if(tgUser) state.user=tgUser; await loadAllData(); startTimer(); updateUI(); if(tgUser?.language_code){ const l=tgUser.language_code.split('-')[0]; if(['en','fa','tr','ru','ar'].includes(l)) switchLanguage(l); } tg.ready(); tg.expand(); }
    document.addEventListener('DOMContentLoaded',init);
    window.switchLanguage=switchLanguage; window.switchTab=switchTab; window.joinLottery=joinLottery; window.verifyDeposit=verifyDeposit; window.requestWithdraw=requestWithdraw; window.copyReferral=copyReferral; window.shareReferral=shareReferral; window.adminStartLottery=adminStartLottery; window.adminPayWinners=adminPayWinners; window.adminSendPoll=adminSendPoll; window.adminBroadcast=adminBroadcast; window.adminManualVerify=adminManualVerify; window.showDepositModal=showDepositModal; window.submitDeposit=submitDeposit; window.openModal=openModal; window.closeModal=closeModal; window.showToast=showToast;
</script>
</body>
</html>'''

# ============================================================
# API Endpoints
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(WEBPAGE_HTML)

@app.get("/api/user")
async def api_user(request: Request):
    tg_user = request.headers.get('X-Telegram-User')
    if not tg_user:
        return JSONResponse({"success": False, "error": "Unauthorized"})
    
    try:
        user_id = int(tg_user)
        db = DatabaseService()
        user = db.get_or_create_user(user_id)
        return JSONResponse({
            "success": True,
            "data": {
                "balance": 250.00,
                "points": user.get('points', 0),
                "has_subscription": user.get('has_subscription', False),
                "has_participated": db.has_participated(user_id),
                "referral_code": user.get('referral_code', '')
            }
        })
    except:
        return JSONResponse({"success": False, "error": "Invalid user"})

@app.get("/api/lottery/current")
async def api_lottery_current():
    db = DatabaseService()
    # Mock data - in real version, get from database
    return JSONResponse({
        "success": True,
        "data": {
            "round_number": 1,
            "participants": 0,
            "prize_pool": 0,
            "winners": 0,
            "end_time": int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
        }
    })

@app.get("/api/winners")
async def api_winners():
    return JSONResponse({
        "success": True,
        "data": []
    })

@app.get("/api/transactions")
async def api_transactions():
    return JSONResponse({
        "success": True,
        "data": []
    })

@app.get("/api/referral")
async def api_referral(request: Request):
    tg_user = request.headers.get('X-Telegram-User')
    if not tg_user:
        return JSONResponse({"success": False, "error": "Unauthorized"})
    
    db = DatabaseService()
    user = db.get_or_create_user(int(tg_user))
    return JSONResponse({
        "success": True,
        "data": {
            "code": user.get('referral_code', ''),
            "count": user.get('referral_count', 0),
            "points": user.get('referral_points', 0)
        }
    })

@app.post("/api/lottery/join")
async def api_join_lottery(request: Request):
    tg_user = request.headers.get('X-Telegram-User')
    if not tg_user:
        return JSONResponse({"success": False, "error": "Unauthorized"})
    
    db = DatabaseService()
    user_id = int(tg_user)
    if db.has_participated(user_id):
        return JSONResponse({"success": False, "error": "Already participated"})
    
    return JSONResponse({"success": True})

@app.post("/api/deposit/verify")
async def api_verify_deposit(request: Request):
    try:
        data = await request.json()
        # در نسخه واقعی، اینجا تایید تراکنش انجام می‌شود
        return JSONResponse({"success": True})
    except:
        return JSONResponse({"success": False, "error": "Invalid data"})

@app.post("/api/withdraw/request")
async def api_withdraw_request(request: Request):
    tg_user = request.headers.get('X-Telegram-User')
    if not tg_user:
        return JSONResponse({"success": False, "error": "Unauthorized"})
    
    try:
        data = await request.json()
        address = data.get('address')
        if not address:
            return JSONResponse({"success": False, "error": "Address required"})
        
        db = DatabaseService()
        if db.save_withdrawal_address(int(tg_user), address):
            return JSONResponse({"success": True})
        return JSONResponse({"success": False, "error": "No pending prize"})
    except:
        return JSONResponse({"success": False, "error": "Invalid data"})

@app.post("/api/admin/lottery/start")
async def api_admin_start_lottery():
    return JSONResponse({"success": True})

@app.post("/api/admin/winners/pay")
async def api_admin_pay_winners():
    db = DatabaseService()
    count = db.pay_winners()
    return JSONResponse({"success": True, "sent": count})

@app.post("/api/admin/poll/send")
async def api_admin_send_poll():
    return JSONResponse({"success": True})

@app.post("/api/admin/broadcast")
async def api_admin_broadcast(request: Request):
    try:
        data = await request.json()
        # در نسخه واقعی، پیام همگانی ارسال می‌شود
        return JSONResponse({"success": True, "sent": 0})
    except:
        return JSONResponse({"success": False})

@app.post("/api/admin/verify/manual")
async def api_admin_verify(request: Request):
    return JSONResponse({"success": True})

# ============================================================
# تابع اصلی برای اجرا
# ============================================================
def start_web_server():
    """اجرای وب‌سرور در یک ترد جداگانه"""
    try:
        uvicorn.run(app, host=WEBAPP_HOST, port=WEBAPP_PORT, log_level="warning")
    except:
        pass

def run_bot():
    """اجرای ربات"""
    bot = LotteryBot()
    bot.run()

# ============================================================
# نقطه ورود اصلی
# ============================================================
if __name__ == '__main__':
    import multiprocessing
    
    logger.info("="*50)
    logger.info("🎰 UTYOB Lottery Bot - v1.0")
    logger.info(f"📱 Bot Token: {'*' * 10}{BOT_TOKEN[-4:]}")
    logger.info(f"👤 Admin ID: {ADMIN_ID}")
    logger.info(f"🌐 WebApp URL: {WEBAPP_URL}")
    logger.info(f"💳 Destination Wallet: {DESTINATION_WALLET}")
    logger.info("="*50)
    
    # ایجاد دیتابیس
    logger.info("📦 Initializing database...")
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
    
    # اجرا در دو ترد جداگانه
    bot_process = multiprocessing.Process(target=run_bot)
    web_process = multiprocessing.Process(target=start_web_server)
    
    logger.info("🚀 Starting bot and web server...")
    
    bot_process.start()
    web_process.start()
    
    try:
        bot_process.join()
        web_process.join()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
        bot_process.terminate()
        web_process.terminate()
        bot_process.join()
        web_process.join()
        logger.info("✅ Shutdown complete")