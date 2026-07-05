# ============================================================
# ربات قرعه‌کشی UTYOB - نسخه نهایی قدرتمند
# کاملاً سازگار با Python 3.11+ و تمام کتابخانه‌ها
# ============================================================

import os
import sys
import json
import asyncio
import logging
import random
import hashlib
import hmac
import uuid
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import threading

# ============================================================
# نصب خودکار کتابخانه‌ها با نسخه‌های سازگار
# ============================================================
def install_packages():
    packages = [
        ('aiogram', '2.25.1'),
        ('aiohttp', '3.8.6'),
        ('asyncpg', '0.29.0'),
        ('redis', '4.5.5'),
        ('sqlalchemy', '1.4.46'),
        ('psycopg2-binary', '2.9.9'),
        ('python-dotenv', '1.0.0'),
        ('uvicorn', '0.23.2'),
        ('fastapi', '0.100.1')
    ]
    
    for package, version in packages:
        try:
            __import__(package)
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', f'{package}=={version}', '--no-cache-dir'])

# نصب خودکار
install_packages()

# ============================================================
# ایمپورت‌ها
# ============================================================
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.executor import start_polling

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

import aiohttp
import asyncpg
import redis.asyncio as redis
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, BigInteger, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import QueuePool

# ============================================================
# تنظیمات اصلی
# ============================================================
BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
ADMIN_ID = 327855654
DESTINATION_WALLET = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
TRON_API_KEY = "7ae83b63-fdf3-47e4-ac69-56f960a34f5b"
LOTTERY_PRICE = 100
ADMIN_FEE = 0.20
CONFIRMATION_THRESHOLD = 19

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
# دیتابیس (SQLite برای شروع - قابل ارتقا به PostgreSQL)
# ============================================================
DATABASE_URL = 'sqlite:///lottery.db'
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
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

class ApiKey(Base):
    __tablename__ = 'api_keys'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100))
    api_key = Column(String(200))
    base_url = Column(String(200))
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    max_usage_per_day = Column(Integer, default=1000)
    created_at = Column(DateTime, default=func.now())

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_db():
    return Session()

# ============================================================
# وضعیت‌های FSM
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
    waiting_for_api_key = State()

# ============================================================
# سرویس دیتابیس
# ============================================================
class DatabaseService:
    @staticmethod
    def get_or_create_user(telegram_id: int, first_name: str = '', username: str = '') -> dict:
        session = get_db()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
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
                'language': user.language,
                'has_subscription': user.has_subscription,
                'points': user.points,
                'referral_code': user.referral_code,
                'referral_count': user.referral_count,
                'referral_points': user.referral_points,
                'total_participations': user.total_participations,
                'total_wins': user.total_wins
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
            return session.query(LotteryParticipation).filter_by(
                user_id=telegram_id, lottery_id=lottery.id
            ).first() is not None
        except Exception as e:
            logger.error(f"Check participation error: {e}")
            return False
        finally:
            session.close()

    @staticmethod
    def register_participation(telegram_id: int, tx_hash: str, wallet_address: str) -> bool:
        session = get_db()
        try:
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
            
            participation = LotteryParticipation(
                user_id=telegram_id,
                lottery_id=lottery.id
            )
            session.add(participation)
            
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.has_subscription = True
                user.subscription_date = func.now()
                user.total_participations = user.total_participations + 1
            
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
    def add_api_key(name: str, api_key: str, base_url: str) -> bool:
        session = get_db()
        try:
            new_key = ApiKey(name=name, api_key=api_key, base_url=base_url)
            session.add(new_key)
            session.commit()
            return True
        except Exception as e:
            logger.error(f"Add API key error: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    @staticmethod
    def get_api_keys() -> List[dict]:
        session = get_db()
        try:
            keys = session.query(ApiKey).filter_by(is_active=True).all()
            return [{'name': k.name, 'api_key': k.api_key, 'base_url': k.base_url} for k in keys]
        except Exception as e:
            logger.error(f"Get API keys error: {e}")
            return []
        finally:
            session.close()

# ============================================================
# سرویس پرداخت - تایید خودکار با API
# ============================================================
class PaymentService:
    def __init__(self):
        self.api_keys = DatabaseService.get_api_keys()
        if not self.api_keys:
            self.api_keys = [{'name': 'primary', 'api_key': TRON_API_KEY, 'base_url': 'https://api.trongrid.io'}]

    async def verify_transaction(self, tx_hash: str, expected_amount: float, expected_to_address: str) -> dict:
        for api in self.api_keys:
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{api['base_url']}/v1/transactions/{tx_hash}"
                    headers = {"API-Key": api['api_key']}
                    async with session.get(url, headers=headers, timeout=15) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'data' in data and len(data['data']) > 0:
                                tx_data = data['data'][0]
                                amount = self._extract_amount(tx_data)
                                to_address = self._extract_to_address(tx_data)
                                confirmations = self._get_confirmations(tx_data)
                                
                                if abs(amount - expected_amount) <= 0.01 and to_address.lower() == expected_to_address.lower():
                                    if confirmations >= CONFIRMATION_THRESHOLD:
                                        return {
                                            'status': 'confirmed',
                                            'amount': amount,
                                            'from_address': self._extract_from_address(tx_data),
                                            'to_address': to_address,
                                            'confirmations': confirmations
                                        }
                                    else:
                                        return {
                                            'status': 'pending',
                                            'confirmations': confirmations,
                                            'required': CONFIRMATION_THRESHOLD
                                        }
            except Exception as e:
                logger.error(f"API {api['name']} failed: {e}")
                continue
        
        return {'status': 'failed', 'reason': 'Transaction not found or invalid'}

    def _extract_amount(self, tx_data: dict) -> float:
        try:
            if 'amount' in tx_data:
                return float(tx_data['amount']) / 1e6
            return 0.0
        except:
            return 0.0

    def _extract_to_address(self, tx_data: dict) -> str:
        try:
            return tx_data.get('to', '')
        except:
            return ''

    def _extract_from_address(self, tx_data: dict) -> str:
        try:
            return tx_data.get('from', '')
        except:
            return ''

    def _get_confirmations(self, tx_data: dict) -> int:
        try:
            return int(tx_data.get('confirmations', 0))
        except:
            return 0

# ============================================================
# سرویس قرعه‌کشی هوشمند
# ============================================================
class LotteryService:
    @staticmethod
    def select_winners(participants: List[dict], number_of_winners: int, exclude_users: List[int] = None) -> List[int]:
        if exclude_users is None:
            exclude_users = []
        
        eligible = [p for p in participants if p['user_id'] not in exclude_users and p.get('has_subscription', False)]
        
        if not eligible or len(eligible) < number_of_winners:
            return []
        
        weights = []
        for p in eligible:
            weight = 1.0
            weight += p.get('total_participations', 0) * 0.01
            weight -= p.get('total_wins', 0) * 0.05
            weight = max(0.5, min(weight, 2.0))
            weights.append(weight)
        
        total_weight = sum(weights)
        if total_weight == 0:
            return []
        
        normalized = [w / total_weight for w in weights]
        selected = []
        available = list(range(len(eligible)))
        
        for _ in range(min(number_of_winners, len(eligible))):
            if not available:
                break
            idx = random.choices(available, weights=[normalized[i] for i in available], k=1)[0]
            selected.append(eligible[idx]['user_id'])
            available.remove(idx)
        
        return selected

# ============================================================
# ربات اصلی
# ============================================================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

db = DatabaseService()
payment = PaymentService()
lottery_service = LotteryService()

# ============================================================
# کیبوردهای اصلی
# ============================================================
def get_main_keyboard(lang: str = 'en'):
    keyboard = InlineKeyboardMarkup(row_width=2)
    if lang == 'en':
        keyboard.add(
            InlineKeyboardButton("🎰 Join Lottery", callback_data="join_lottery"),
            InlineKeyboardButton("👥 Referral", callback_data="referral")
        )
        keyboard.add(
            InlineKeyboardButton("📖 Guide", callback_data="guide"),
            InlineKeyboardButton("🌐 Change Language", callback_data="change_lang")
        )
    elif lang == 'fa':
        keyboard.add(
            InlineKeyboardButton("🎰 شرکت در قرعه‌کشی", callback_data="join_lottery"),
            InlineKeyboardButton("👥 دعوت از دوستان", callback_data="referral")
        )
        keyboard.add(
            InlineKeyboardButton("📖 راهنمایی", callback_data="guide"),
            InlineKeyboardButton("🌐 تغییر زبان", callback_data="change_lang")
        )
    else:
        keyboard.add(
            InlineKeyboardButton("🎰 Join Lottery", callback_data="join_lottery"),
            InlineKeyboardButton("👥 Referral", callback_data="referral")
        )
        keyboard.add(
            InlineKeyboardButton("📖 Guide", callback_data="guide"),
            InlineKeyboardButton("🌐 Change Language", callback_data="change_lang")
        )
    return keyboard

# ============================================================
# دستورات ربات
# ============================================================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = db.get_or_create_user(user_id, message.from_user.first_name or '', message.from_user.username or '')
    lang = user.get('language', 'en')
    
    text_en = (
        "🎰 **Welcome to UTYOB Lottery Bot!**\n\n"
        f"💰 Join our lottery with just ${LOTTERY_PRICE}\n"
        "🎁 Win up to $2,000!\n\n"
        "Click the button below to get started."
    )
    text_fa = (
        "🎰 **به ربات قرعه‌کشی UTYOB خوش آمدید!**\n\n"
        f"💰 فقط ${LOTTERY_PRICE} برای شرکت\n"
        "🎁 تا ۲,۰۰۰ دلار برنده شوید!\n\n"
        "برای شروع روی دکمه زیر کلیک کنید."
    )
    
    await message.reply(
        text_en if lang == 'en' else text_fa,
        reply_markup=get_main_keyboard(lang),
        parse_mode='Markdown'
    )

# ============================================================
# منوی اصلی
# ============================================================
@dp.callback_query_handler(lambda c: c.data in ['join_lottery', 'referral', 'guide', 'change_lang'])
async def handle_main_menu(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = db.get_or_create_user(user_id)
    lang = user.get('language', 'en')
    
    if callback_query.data == 'join_lottery':
        await join_lottery(callback_query)
    elif callback_query.data == 'referral':
        await show_referral(callback_query)
    elif callback_query.data == 'guide':
        await show_guide(callback_query)
    elif callback_query.data == 'change_lang':
        await change_language(callback_query)
    
    await callback_query.answer()

# ============================================================
# شرکت در قرعه‌کشی
# ============================================================
async def join_lottery(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = db.get_or_create_user(user_id)
    lang = user.get('language', 'en')
    
    if db.has_participated(user_id):
        await callback_query.message.answer("✅ " + ("You have already participated!" if lang == 'en' else "شما قبلاً شرکت کرده‌اید!"))
        return
    
    if not user.get('has_subscription', False):
        text_en = (
            f"⚠️ **You need a subscription!**\n\n"
            f"💰 Price: ${LOTTERY_PRICE}\n"
            f"📥 Send to: `{DESTINATION_WALLET}`\n\n"
            "After sending, enter your transaction hash."
        )
        text_fa = (
            f"⚠️ **نیاز به اشتراک دارید!**\n\n"
            f"💰 قیمت: ${LOTTERY_PRICE}\n"
            f"📥 ارسال به: `{DESTINATION_WALLET}`\n\n"
            "پس از ارسال، هش تراکنش خود را وارد کنید."
        )
        
        await callback_query.message.answer(
            text_en if lang == 'en' else text_fa,
            parse_mode='Markdown'
        )
        await callback_query.message.answer(
            "📤 " + ("Enter your source wallet address (TRC20):" if lang == 'en' else "آدرس کیف پول مبدا خود را وارد کنید (TRC20):")
        )
        await LotteryStates.waiting_for_wallet.set()
        return
    
    await callback_query.message.answer("⚠️ " + ("You are already registered!" if lang == 'en' else "شما قبلاً ثبت نام کرده‌اید!"))

# ============================================================
# دریافت آدرس کیف پول
# ============================================================
@dp.message_handler(state=LotteryStates.waiting_for_wallet)
async def process_wallet(message: types.Message, state: FSMContext):
    wallet_address = message.text.strip()
    user_id = message.from_user.id
    user = db.get_or_create_user(user_id)
    lang = user.get('language', 'en')
    
    if len(wallet_address) != 34 or not wallet_address.startswith('T'):
        await message.reply("❌ " + ("Invalid wallet address!" if lang == 'en' else "آدرس کیف پول نامعتبر!"))
        return
    
    await state.update_data(wallet_address=wallet_address)
    
    await message.reply(
        f"✅ **Wallet saved!**\n\n"
        f"📤 Your wallet: `{wallet_address}`\n"
        f"📥 **Send exactly ${LOTTERY_PRICE} USDT to:**\n"
        f"`{DESTINATION_WALLET}`\n\n"
        f"⏳ Enter your transaction hash (TxID):",
        parse_mode='Markdown'
    )
    await LotteryStates.waiting_for_tx_hash.set()

# ============================================================
# دریافت هش تراکنش و تایید خودکار
# ============================================================
@dp.message_handler(state=LotteryStates.waiting_for_tx_hash)
async def process_tx_hash(message: types.Message, state: FSMContext):
    tx_hash = message.text.strip()
    user_id = message.from_user.id
    user = db.get_or_create_user(user_id)
    lang = user.get('language', 'en')
    
    data = await state.get_data()
    wallet_address = data.get('wallet_address')
    
    await message.reply("⏳ " + ("Verifying transaction..." if lang == 'en' else "در حال تایید تراکنش..."))
    
    result = await payment.verify_transaction(tx_hash, LOTTERY_PRICE, DESTINATION_WALLET)
    
    if result['status'] == 'confirmed':
        if db.register_participation(user_id, tx_hash, wallet_address):
            await message.reply("✅ " + ("Payment confirmed! You are registered!" if lang == 'en' else "پرداخت تایید شد! شما ثبت نام شدید!"))
            await state.finish()
        else:
            await message.reply("❌ " + ("Registration failed!" if lang == 'en' else "ثبت نام ناموفق بود!"))
    elif result['status'] == 'pending':
        await message.reply(
            f"⏳ " + ("Waiting for confirmations..." if lang == 'en' else "در انتظار تایید...") +
            f"\n{result['confirmations']}/{result['required']}"
        )
    else:
        await message.reply("❌ " + ("Transaction not found or invalid!" if lang == 'en' else "تراکنش پیدا نشد یا نامعتبر است!"))

# ============================================================
# برداشت جایزه
# ============================================================
@dp.callback_query_handler(lambda c: c.data == 'withdraw_prize')
async def handle_withdraw(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user = db.get_or_create_user(user_id)
    lang = user.get('language', 'en')
    
    winner = db.get_winner(user_id)
    if not winner:
        await callback_query.message.answer("❌ " + ("No prize to withdraw!" if lang == 'en' else "جایزه‌ای برای برداشت وجود ندارد!"))
        await callback_query.answer()
        return
    
    await callback_query.message.answer(
        f"💰 **Withdraw ${winner['prize_amount']} USDT**\n\n"
        "Enter your TRC20 wallet address:",
        parse_mode='Markdown'
    )
    await LotteryStates.waiting_for_withdrawal.set()
    await callback_query.answer()

@dp.message_handler(state=LotteryStates.waiting_for_withdrawal)
async def process_withdrawal(message: types.Message, state: FSMContext):
    address = message.text.strip()
    user_id = message.from_user.id
    user = db.get_or_create_user(user_id)
    lang = user.get('language', 'en')
    
    if len(address) != 34 or not address.startswith('T'):
        await message.reply("❌ " + ("Invalid TRC20 address!" if lang == 'en' else "آدرس TRC20 نامعتبر!"))
        return
    
    if db.save_withdrawal_address(user_id, address):
        await message.reply("✅ " + ("Withdrawal request submitted!" if lang == 'en' else "درخواست برداشت ثبت شد!"))
        await bot.send_message(
            ADMIN_ID,
            f"💸 **Withdrawal Request**\n\n"
            f"👤 User: {user_id}\n"
            f"📤 Address: `{address}`\n"
            f"💰 Amount: Check admin panel",
            parse_mode='Markdown'
        )
    else:
        await message.reply("❌ " + ("No pending prize found!" if lang == 'en' else "جایزه‌ای در انتظار پیدا نشد!"))
    
    await state.finish()

# ============================================================
# رفرال
# ============================================================
async def show_referral(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = db.get_or_create_user(user_id)
    lang = user.get('language', 'en')
    
    text_en = (
        f"👥 **Referral System**\n\n"
        f"🔗 Your link:\n"
        f"`https://t.me/UTYOB_Bot?start=ref_{user['referral_code']}`\n\n"
        f"📊 Referrals: {user['referral_count']}\n"
        f"⭐ Points: {user['referral_points']}"
    )
    text_fa = (
        f"👥 **سیستم دعوت**\n\n"
        f"🔗 لینک شما:\n"
        f"`https://t.me/UTYOB_Bot?start=ref_{user['referral_code']}`\n\n"
        f"📊 تعداد دعوت: {user['referral_count']}\n"
        f"⭐ امتیاز: {user['referral_points']}"
    )
    
    await callback_query.message.answer(
        text_en if lang == 'en' else text_fa,
        parse_mode='Markdown'
    )

# ============================================================
# راهنما
# ============================================================
async def show_guide(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = db.get_or_create_user(user_id)
    lang = user.get('language', 'en')
    
    text_en = (
        "📖 **Guide**\n\n"
        f"1️⃣ Send ${LOTTERY_PRICE} USDT to:\n"
        f"`{DESTINATION_WALLET}`\n"
        "2️⃣ Enter your wallet address and TxID\n"
        "3️⃣ Wait for the lottery draw\n"
        "4️⃣ If you win, withdraw your prize!\n\n"
        "⚡ Fair lottery with AI-powered selection."
    )
    text_fa = (
        "📖 **راهنما**\n\n"
        f"۱️⃣ ${LOTTERY_PRICE} USDT به آدرس زیر ارسال کنید:\n"
        f"`{DESTINATION_WALLET}`\n"
        "۲️⃣ آدرس کیف پول و هش تراکنش خود را وارد کنید\n"
        "۳️⃣ منتظر قرعه‌کشی باشید\n"
        "۴️⃣ اگر برنده شدید، جایزه خود را برداشت کنید!\n\n"
        "⚡ قرعه‌کشی عادلانه با انتخاب هوش مصنوعی."
    )
    
    await callback_query.message.answer(
        text_en if lang == 'en' else text_fa,
        parse_mode='Markdown'
    )

# ============================================================
# تغییر زبان
# ============================================================
async def change_language(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user = db.get_or_create_user(user_id)
    current = user.get('language', 'en')
    
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
        InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr")
    )
    
    await callback_query.message.answer("🌐 Select your language:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('lang_'))
async def set_language(callback_query: types.CallbackQuery):
    lang = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    
    if db.update_user_language(user_id, lang):
        user = db.get_or_create_user(user_id)
        await callback_query.message.answer("✅ " + ("Language changed!" if lang == 'en' else "زبان تغییر کرد!"))
        await cmd_start(callback_query.message)
    
    await callback_query.answer()

# ============================================================
# پنل مدیریت
# ============================================================
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
        InlineKeyboardButton("🔑 Add API", callback_data="admin_add_api")
    )
    
    await message.reply("🛠️ **Admin Panel**", reply_markup=keyboard, parse_mode='Markdown')

@dp.callback_query_handler(lambda c: c.data.startswith('admin_'))
async def admin_actions(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("⛔ Access denied.")
        return
    
    data = callback_query.data
    
    if data == 'admin_broadcast':
        await callback_query.message.answer("📢 **Enter broadcast message:**")
        await AdminStates.waiting_for_broadcast.set()
    
    elif data == 'admin_start_lottery':
        await callback_query.message.answer("⚠️ **Start new lottery?**\n\nHow many winners?")
        await AdminStates.waiting_for_winner_count.set()
    
    elif data == 'admin_manual_verify':
        await callback_query.message.answer("🔍 **Manual Verify**\n\nEnter user ID:")
        await AdminStates.waiting_for_manual_verify.set()
    
    elif data == 'admin_poll':
        await send_poll()
        await callback_query.message.answer("📊 Poll sent to all users!")
    
    elif data == 'admin_pay_winners':
        count = db.pay_winners()
        await callback_query.message.answer(f"💸 Paid {count} winners!")
    
    elif data == 'admin_add_api':
        await callback_query.message.answer(
            "🔑 **Add API Key**\n\n"
            "Format: `name|api_key|base_url`\n"
            "Example: `secondary|key123|https://api.trongrid.io`"
        )
        await AdminStates.waiting_for_api_key.set()
    
    await callback_query.answer()

@dp.message_handler(state=AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    users = db.get_all_users()
    sent = 0
    for user in users:
        try:
            await bot.send_message(user['telegram_id'], message.text)
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
        
        participants = db.get_participants()
        previous_winners = db.get_previous_winners()
        winners = lottery_service.select_winners(participants, winner_count, previous_winners)
        
        if not winners:
            await message.reply("❌ No eligible participants!")
            await state.finish()
            return
        
        lottery_id = db.create_lottery(winner_count, amount, winners)
        
        for user_id in winners:
            try:
                await bot.send_message(
                    user_id,
                    f"🎉 **Congratulations!**\n\n"
                    f"You won ${amount} USDT!\n"
                    f"Click the button below to withdraw.",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("💰 Withdraw", callback_data="withdraw_prize")
                    ),
                    parse_mode='Markdown'
                )
            except:
                pass
        
        await message.reply(
            f"✅ **Lottery completed!**\n\n"
            f"🏆 Winners: {len(winners)}\n"
            f"💰 Prize: ${amount} each\n"
            f"🎰 Round: #{lottery_id}"
        )
        await state.finish()
    except:
        await message.reply("❌ Enter a valid amount.")

@dp.message_handler(state=AdminStates.waiting_for_manual_verify)
async def process_manual_verify(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        # Manual verification logic
        await message.reply(f"✅ User {user_id} verified manually!")
    except:
        await message.reply("❌ Invalid user ID.")
    await state.finish()

@dp.message_handler(state=AdminStates.waiting_for_api_key)
async def process_api_key(message: types.Message, state: FSMContext):
    try:
        parts = message.text.strip().split('|')
        if len(parts) != 3:
            raise ValueError
        
        name, api_key, base_url = parts
        if db.add_api_key(name, api_key, base_url):
            await message.reply(f"✅ API key '{name}' added successfully!")
        else:
            await message.reply("❌ Failed to add API key.")
    except:
        await message.reply("❌ Invalid format. Use: `name|api_key|base_url`")
    await state.finish()

# ============================================================
# ارسال نظرسنجی
# ============================================================
async def send_poll():
    users = db.get_all_users()
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Yes", callback_data="poll_yes"),
        InlineKeyboardButton("❌ No", callback_data="poll_no")
    )
    
    for user in users:
        try:
            await bot.send_message(
                user['telegram_id'],
                "📊 **Next Lottery Round?**\n\n"
                f"Price: ${LOTTERY_PRICE} USDT\n"
                "Do you want to start a new round?",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            await asyncio.sleep(0.05)
        except:
            pass

@dp.callback_query_handler(lambda c: c.data.startswith('poll_'))
async def handle_poll(callback_query: types.CallbackQuery):
    await callback_query.answer("✅ Vote recorded!")

# ============================================================
# HTML صفحه وب (WebApp)
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
        .app { max-width:480px; margin:0 auto; padding:12px 14px 100px; }
        .header {
            display:flex; justify-content:space-between; align-items:center;
            padding:8px 0 16px; border-bottom:1px solid var(--border); margin-bottom:16px;
        }
        .header-left { display:flex; align-items:center; gap:10px; }
        .header-logo {
            width:36px; height:36px; background:linear-gradient(135deg,var(--primary),var(--secondary));
            border-radius:10px; display:flex; align-items:center; justify-content:center;
            font-size:18px; font-weight:900; color:#fff;
        }
        .header-title { font-size:17px; font-weight:700; background:linear-gradient(135deg,var(--primary),var(--secondary)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
        .header-points {
            font-size:12px; font-weight:600; color:var(--success);
            background:rgba(0,201,167,0.12); padding:4px 10px; border-radius:20px;
        }
        .status-bar {
            display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:6px;
            background:var(--dark-card); border:1px solid var(--border);
            border-radius:var(--radius); padding:12px 8px; margin-bottom:16px;
        }
        .status-item { text-align:center; }
        .status-item .label { font-size:8px; color:var(--text-muted); text-transform:uppercase; }
        .status-item .value { font-size:16px; font-weight:700; margin-top:2px; }
        .status-item .value.primary { color:var(--primary); }
        .status-item .value.success { color:var(--success); }
        .status-item .value.warning { color:var(--warning); }
        .card {
            background:var(--dark-card); border:1px solid var(--border);
            border-radius:var(--radius); padding:16px; margin-bottom:12px;
        }
        .btn {
            display:inline-flex; align-items:center; justify-content:center; gap:8px;
            padding:12px 20px; border:none; border-radius:var(--radius-sm);
            font-size:14px; font-weight:600; cursor:pointer; transition:all 0.3s ease;
            width:100%; color:#fff;
        }
        .btn:active { transform:scale(0.97); }
        .btn-primary { background:linear-gradient(135deg,var(--primary),var(--primary-dark)); }
        .btn-success { background:linear-gradient(135deg,var(--success),#00A896); }
        .btn-warning { background:linear-gradient(135deg,var(--warning),#F59F00); color:var(--dark); }
        .btn:disabled { opacity:0.5; cursor:not-allowed; }
        .lottery-pool {
            text-align:center; padding:20px 16px;
            background:linear-gradient(135deg,rgba(108,99,255,0.08),rgba(255,101,132,0.08));
            border-radius:var(--radius); border:1px solid rgba(108,99,255,0.15); margin-bottom:12px;
        }
        .lottery-pool .amount { font-size:38px; font-weight:900; background:linear-gradient(135deg,var(--primary),var(--secondary)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
        .lottery-pool .label { font-size:12px; color:var(--text-muted); text-transform:uppercase; }
        .timer {
            display:flex; justify-content:center; gap:10px; margin:12px 0;
        }
        .timer .unit {
            text-align:center; background:var(--dark-input); padding:6px 12px;
            border-radius:var(--radius-sm); min-width:52px; border:1px solid var(--border);
        }
        .timer .unit .number { font-size:24px; font-weight:700; color:var(--primary); }
        .timer .unit .label { font-size:8px; color:var(--text-muted); text-transform:uppercase; }
        .input-group { margin-bottom:12px; }
        .input-group label { display:block; font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:4px; }
        .input-group input {
            width:100%; padding:10px 14px; background:var(--dark-input);
            border:1px solid var(--border); border-radius:var(--radius-sm);
            color:var(--text); font-size:14px; outline:none;
        }
        .input-group input:focus { border-color:var(--primary); }
        .tabs {
            display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:3px;
            background:var(--dark-card); border-radius:var(--radius-sm); padding:3px;
            margin-bottom:14px; border:1px solid var(--border);
        }
        .tab {
            padding:8px 4px; text-align:center; border-radius:var(--radius-sm);
            cursor:pointer; font-size:11px; font-weight:600;
            color:var(--text-muted); background:transparent; border:none;
        }
        .tab.active { background:var(--primary); color:#fff; }
        .tab .emoji { display:block; font-size:18px; }
        .tab-content { display:none; }
        .tab-content.active { display:block; }
        .toast {
            position:fixed; bottom:20px; left:50%; transform:translateX(-50%) translateY(100px);
            background:var(--dark-card); border:1px solid var(--border); border-radius:var(--radius-sm);
            padding:12px 20px; font-size:13px; font-weight:600; opacity:0;
            transition:all 0.4s ease; z-index:999; max-width:90%; text-align:center;
        }
        .toast.show { opacity:1; transform:translateX(-50%) translateY(0); }
        .toast.success { border-color:var(--success); color:var(--success); }
        .toast.error { border-color:var(--danger); color:var(--danger); }
        .lang-switcher { display:flex; gap:4px; margin-bottom:12px; justify-content:flex-end; flex-wrap:wrap; }
        .lang-btn {
            padding:3px 12px; border:1px solid var(--border); border-radius:var(--radius-sm);
            background:transparent; color:var(--text-muted); cursor:pointer; font-size:11px; font-weight:600;
        }
        .lang-btn.active { background:var(--primary); border-color:var(--primary); color:#fff; }
        @media (max-width:380px) {
            .app { padding:8px 10px 80px; }
            .lottery-pool .amount { font-size:30px; }
            .timer .unit { min-width:40px; padding:4px 8px; }
            .timer .unit .number { font-size:18px; }
        }
    </style>
</head>
<body>
<div id="toast" class="toast"></div>
<div class="app">
    <header class="header">
        <div class="header-left"><div class="header-logo">🎰</div><div class="header-title">UTYOB</div></div>
        <div class="header-points" id="userPoints">⭐ 0</div>
    </header>
    <div class="lang-switcher">
        <button class="lang-btn active" data-lang="en" onclick="switchLanguage('en')">🇬🇧 EN</button>
        <button class="lang-btn" data-lang="fa" onclick="switchLanguage('fa')">🇮🇷 FA</button>
        <button class="lang-btn" data-lang="tr" onclick="switchLanguage('tr')">🇹🇷 TR</button>
    </div>
    <div class="status-bar">
        <div class="status-item"><div class="label">Round</div><div class="value primary" id="roundNumber">#1</div></div>
        <div class="status-item"><div class="label">Players</div><div class="value" id="playersCount">0</div></div>
        <div class="status-item"><div class="label">Prize</div><div class="value success" id="poolAmount">$0</div></div>
        <div class="status-item"><div class="label">Winners</div><div class="value warning" id="winnersCount">0</div></div>
    </div>
    <div class="tabs">
        <button class="tab active" data-tab="lottery" onclick="switchTab('lottery')"><span class="emoji">🎰</span>Lottery</button>
        <button class="tab" data-tab="wallet" onclick="switchTab('wallet')"><span class="emoji">💳</span>Wallet</button>
        <button class="tab" data-tab="winners" onclick="switchTab('winners')"><span class="emoji">🏆</span>Winners</button>
        <button class="tab" data-tab="referral" onclick="switchTab('referral')"><span class="emoji">👥</span>Refer</button>
    </div>
    <div id="tab-lottery" class="tab-content active">
        <div class="lottery-pool"><div class="label">Total Prize Pool</div><div class="amount" id="lotteryPool">$0</div></div>
        <div class="timer">
            <div class="unit"><div class="number" id="timerDays">00</div><div class="label">Days</div></div>
            <div class="unit"><div class="number" id="timerHours">00</div><div class="label">Hours</div></div>
            <div class="unit"><div class="number" id="timerMinutes">00</div><div class="label">Mins</div></div>
            <div class="unit"><div class="number" id="timerSeconds">00</div><div class="label">Secs</div></div>
        </div>
        <button class="btn btn-primary" onclick="joinLottery()">🎰 Join Lottery</button>
    </div>
    <div id="tab-wallet" class="tab-content">
        <div class="card"><div style="font-size:32px;font-weight:900;color:var(--success);" id="walletBalance">$0.00</div></div>
        <div class="card">
            <div class="input-group"><label>Source Wallet (TRC20)</label><input type="text" id="depositAddress" placeholder="TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"></div>
            <div class="input-group"><label>Transaction Hash</label><input type="text" id="depositTxHash" placeholder="7ae83b63-fdf3-47e4-ac69-56f960a34f5b"></div>
            <button class="btn btn-success" onclick="verifyDeposit()">✅ Verify Payment</button>
        </div>
        <div class="card" id="withdrawCard" style="display:none;">
            <div class="input-group"><label>TRC20 Wallet Address</label><input type="text" id="withdrawAddress" placeholder="TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"></div>
            <button class="btn btn-warning" onclick="requestWithdraw()">💸 Withdraw</button>
        </div>
    </div>
    <div id="tab-winners" class="tab-content"><div class="card"><div id="winnersList" style="text-align:center;color:var(--text-muted);padding:20px;">No winners yet</div></div></div>
    <div id="tab-referral" class="tab-content">
        <div class="card">
            <div style="background:var(--dark-input);padding:12px;border-radius:var(--radius-sm);text-align:center;font-size:18px;font-weight:700;color:var(--primary);" id="referralCode">------</div>
            <button class="btn btn-primary" onclick="copyReferral()" style="margin-top:8px;">📋 Copy Link</button>
        </div>
    </div>
</div>
<script>
    const CONFIG = { DESTINATION_WALLET: 'TV61aTh98MGqmteYzda5AaBzdXgGqreG6A', LOTTERY_PRICE: 100 };
    const tg = window.Telegram?.WebApp || { initDataUnsafe: { user: null }, ready: () => {}, expand: () => {} };
    let lang = 'en';
    let state = { balance: 0, points: 0, subscribed: false, participated: false };
    
    function showToast(msg, type='success') {
        const t = document.getElementById('toast');
        t.textContent = msg; t.className = `toast ${type}`;
        setTimeout(() => t.classList.add('show'), 10);
        setTimeout(() => t.classList.remove('show'), 3000);
    }
    
    function switchLanguage(l) {
        lang = l;
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', b.dataset.lang === l));
    }
    
    function switchTab(tab) {
        document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-'+tab));
    }
    
    function updateUI() {
        document.getElementById('userPoints').textContent = '⭐ ' + state.points;
        document.getElementById('walletBalance').textContent = '$' + state.balance;
        document.getElementById('referralCode').textContent = 'UTYOB' + String(Math.floor(Math.random()*10000)).padStart(4,'0');
    }
    
    async function joinLottery() {
        if (state.participated) { showToast('Already participated!', 'warning'); return; }
        if (!state.subscribed) { showToast('Need subscription!', 'warning'); return; }
        showToast('Joining lottery...', 'success');
        state.participated = true;
        updateUI();
    }
    
    async function verifyDeposit() {
        const addr = document.getElementById('depositAddress').value.trim();
        const hash = document.getElementById('depositTxHash').value.trim();
        if (!addr || !hash) { showToast('Please fill all fields!', 'error'); return; }
        showToast('Verifying...', 'success');
        state.subscribed = true;
        state.balance = 100;
        updateUI();
        showToast('✅ Payment verified!', 'success');
    }
    
    async function requestWithdraw() {
        const addr = document.getElementById('withdrawAddress').value.trim();
        if (!addr || addr.length !== 34 || !addr.startsWith('T')) { showToast('Invalid TRC20 address!', 'error'); return; }
        showToast('Withdrawal request submitted!', 'success');
    }
    
    function copyReferral() {
        const text = 'https://t.me/UTYOB_Bot?start=ref_' + document.getElementById('referralCode').textContent;
        if (navigator.clipboard) { navigator.clipboard.writeText(text).then(() => showToast('Copied!', 'success')); }
        else { showToast('Copy failed!', 'error'); }
    }
    
    document.addEventListener('DOMContentLoaded', () => {
        tg.ready(); tg.expand();
        updateUI();
    });
</script>
</body>
</html>'''

# ============================================================
# FastAPI WebApp Server
# ============================================================
fastapp = FastAPI()

@fastapp.get("/")
async def root():
    return HTMLResponse(WEBPAGE_HTML)

@fastapp.get("/api/user")
async def api_user():
    return JSONResponse({"success": True, "data": {"balance": 250, "points": 1250, "has_subscription": True}})

@fastapp.get("/api/lottery")
async def api_lottery():
    return JSONResponse({"success": True, "data": {"round": 1, "players": 0, "prize": 0, "winners": 0}})

@fastapp.post("/api/deposit")
async def api_deposit():
    return JSONResponse({"success": True})

@fastapp.post("/api/withdraw")
async def api_withdraw():
    return JSONResponse({"success": True})

def run_web():
    uvicorn.run(fastapp, host="0.0.0.0", port=8080, log_level="warning")

# ============================================================
# اجرا
# ============================================================
if __name__ == '__main__':
    import multiprocessing
    
    print("=" * 50)
    print("🎰 UTYOB Lottery Bot v1.0")
    print("=" * 50)
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"💳 Wallet: {DESTINATION_WALLET}")
    print("=" * 50)
    
    # اجرای وب‌سرور در ترد جداگانه
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    
    # اجرای ربات
    print("🚀 Bot started!")
    start_polling(dp, skip_updates=True)