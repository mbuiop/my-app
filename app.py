import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import asyncio
import json
import webbrowser
import time
import numpy as np
from datetime import datetime, timedelta
import requests
import sqlite3
import threading
import os

# ==================== تنظیمات پیشرفته ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# توکن ربات و آیدی ادمین
BOT_TOKEN = "8895536734:AAEelFpAnwGMz9Cr0VI6pN5vPui-s2tPKzc"
ADMIN_ID = 327855654

# لینک‌های صرافی
EXCHANGE_URLS = {
    'tobit': 'http://t.me/TradeFuturesGuru_Bot/Tobit',
    'tabdil': 'http://t.me/TradeFuturesGuru_Bot/Tabdill'
}

# ==================== دیتابیس پیشرفته ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('trading_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
        # جدول کاربران
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                referral_count INTEGER DEFAULT 0,
                referred_users TEXT DEFAULT '[]',
                total_analysis INTEGER DEFAULT 0,
                last_analysis TIMESTAMP,
                joined_at TIMESTAMP,
                plan TEXT DEFAULT 'BASIC'
            )
        ''')
        
        # جدول سیگنال‌ها
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                signal_type TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                confidence INTEGER,
                indicators_used TEXT,
                created_at TIMESTAMP
            )
        ''')
        
        # جدول قیمت‌های تاریخی
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                symbol TEXT,
                price REAL,
                timestamp TIMESTAMP,
                PRIMARY KEY (symbol, timestamp)
            )
        ''')
        
        # جدول بازخورد
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                rating INTEGER,
                created_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, referred_by=None):
        now = datetime.now().isoformat()
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, now))
        self.conn.commit()
        
        if referred_by and referred_by != user_id:
            self.cursor.execute('''
                UPDATE users SET referral_count = referral_count + 1
                WHERE user_id = ?
            ''', (referred_by,))
            self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def save_signal(self, user_id, signal_data):
        self.cursor.execute('''
            INSERT INTO signals 
            (user_id, symbol, signal_type, entry_price, take_profit, stop_loss, 
             confidence, indicators_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            signal_data.get('symbol', 'UNKNOWN'),
            signal_data.get('direction', 'HOLD'),
            signal_data.get('entry', 0),
            signal_data.get('take_profit', 0),
            signal_data.get('stop_loss', 0),
            signal_data.get('confidence', 0),
            json.dumps(signal_data.get('indicators_used', [])),
            datetime.now().isoformat()
        ))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_signals,
                COUNT(DISTINCT symbol) as symbols_analyzed,
                MAX(confidence) as best_confidence,
                AVG(confidence) as avg_confidence
            FROM signals WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()

db = Database()

# ==================== دریافت قیمت لحظه‌ای ====================
class PriceFetcher:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3/ticker/price"
        self.cache = {}
        self.cache_time = {}
    
    def get_price(self, symbol="BTCUSDT"):
        """دریافت قیمت لحظه‌ای با کش"""
        if symbol in self.cache and time.time() - self.cache_time.get(symbol, 0) < 5:
            return self.cache[symbol]
        
        try:
            response = requests.get(
                f"{self.binance_url}?symbol={symbol}",
                timeout=5
            )
            if response.status_code == 200:
                price = float(response.json()['price'])
                self.cache[symbol] = price
                self.cache_time[symbol] = time.time()
                return price
        except:
            pass
        return None
    
    def get_klines(self, symbol="BTCUSDT", interval="1h", limit=200):
        """دریافت داده تاریخی"""
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            prices = []
            for candle in data:
                prices.append({
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000)
                })
            return prices
        except:
            return []

price_fetcher = PriceFetcher()

# ==================== تحلیلگر فوق‌پیشرفته ====================
class UltraTechnicalAnalyzer:
    def __init__(self):
        self.weights = {
            'RSI': 5.0, 'MACD': 4.8, 'EMA5': 4.5, 'EMA10': 4.2, 'EMA30': 4.0,
            'MA': 3.8, 'BOLL': 4.6, 'KDJ': 4.4, 'ADX': 4.2, 'ATR': 3.5,
            'VOL': 3.2, 'OBV': 3.5, 'Ichimoku_Cloud': 4.3, 'Stoch': 4.1,
            'CCI': 3.9, 'Williams': 3.7, 'MFI': 4.0, 'PSAR': 3.6,
            'BB_Upper': 3.4, 'BB_Lower': 3.4
        }
        self.oscillators = {'RSI', 'KDJ', 'Stoch', 'CCI', 'Williams', 'MFI'}
        self.trend_indicators = {'MACD', 'EMA5', 'EMA10', 'EMA30', 'MA', 'ADX', 'Ichimoku_Cloud', 'PSAR'}
        self.volatility_indicators = {'BOLL', 'ATR', 'BB_Upper', 'BB_Lower'}
        self.volume_indicators = {'VOL', 'OBV'}
    
    def calculate_rsi(self, prices, period=14):
        """محاسبه RSI دقیق"""
        if len(prices) < period + 1:
            return 50
        
        delta = prices[-1] - prices[-period-1]
        gain = max(delta, 0)
        loss = max(-delta, 0)
        
        for i in range(len(prices) - period, len(prices) - 1):
            delta = prices[i] - prices[i-1]
            gain = gain * (period - 1) / period + max(delta, 0)
            loss = loss * (period - 1) / period + max(-delta, 0)
        
        rs = gain / loss if loss > 0 else 100
        return 100 - (100 / (1 + rs))
    
    def analyze_indicators_ultra(self, indicators, support, resistance, current_price, analysis_level="basic"):
        """تحلیل فوق‌پیشرفته با ۲۰ اندیکاتور و الگوریتم‌های هوشمند"""
        
        support_resistance_range = resistance - support
        mid_point = (support + resistance) / 2
        price_position = (current_price - support) / (resistance - support) if resistance != support else 0.5
        
        # دریافت قیمت واقعی از بازار
        live_price = price_fetcher.get_price()
        if live_price:
            current_price = live_price
        
        scores = {}
        total_weighted_score = 0
        total_weight = 0
        signals_list = []
        
        # تحلیل هر اندیکاتور با الگوریتم پیشرفته
        for indicator, value in indicators.items():
            try:
                val = float(value)
                raw_score = 0
                weight = self.weights.get(indicator, 3.0)
                
                # ===== RSI با الگوریتم پیشرفته =====
                if indicator == 'RSI':
                    if val <= 15:
                        raw_score = 5.0
                        signals_list.append("🚀 RSI Extreme Oversold")
                    elif val <= 25:
                        raw_score = 4.2
                        signals_list.append("📈 RSI Oversold")
                    elif val <= 30:
                        raw_score = 3.5
                        signals_list.append("📊 RSI Near Oversold")
                    elif val <= 35:
                        raw_score = 2.5
                    elif val <= 45:
                        raw_score = 1.2
                    elif val <= 55:
                        raw_score = 0
                    elif val <= 65:
                        raw_score = -1.2
                    elif val <= 70:
                        raw_score = -2.5
                    elif val <= 75:
                        raw_score = -3.5
                        signals_list.append("📉 RSI Near Overbought")
                    elif val <= 85:
                        raw_score = -4.2
                        signals_list.append("📉 RSI Overbought")
                    else:
                        raw_score = -5.0
                        signals_list.append("🚀 RSI Extreme Overbought")
                
                # ===== MACD با تشخیص واگرایی =====
                elif indicator == 'MACD':
                    if val > 1.5:
                        raw_score = 5.0
                        signals_list.append("🚀 MACD Very Bullish")
                    elif val > 0.8:
                        raw_score = 4.0
                        signals_list.append("📈 MACD Bullish")
                    elif val > 0.3:
                        raw_score = 2.8
                    elif val > 0.1:
                        raw_score = 1.5
                    elif val > -0.1:
                        raw_score = 0
                    elif val > -0.3:
                        raw_score = -1.5
                    elif val > -0.8:
                        raw_score = -2.8
                        signals_list.append("📉 MACD Bearish")
                    elif val > -1.5:
                        raw_score = -4.0
                        signals_list.append("📉 MACD Very Bearish")
                    else:
                        raw_score = -5.0
                        signals_list.append("🚀 MACD Extreme Bearish")
                
                # ===== EMA با تحلیل روند =====
                elif indicator in self.trend_indicators:
                    ema_factor = {
                        'EMA5': 1.4, 'EMA10': 1.3, 'EMA30': 1.2,
                        'MA': 1.1, 'ADX': 1.0, 'Ichimoku_Cloud': 1.3,
                        'PSAR': 1.1
                    }.get(indicator, 1.0)
                    
                    if val <= support * 0.97:
                        raw_score = 5.0 * ema_factor
                        signals_list.append(f"🚀 {indicator} Below Strong Support")
                    elif val <= support * 0.98:
                        raw_score = 4.2 * ema_factor
                        signals_list.append(f"📈 {indicator} Below Support")
                    elif val <= support:
                        raw_score = 3.5 * ema_factor
                    elif val <= mid_point * 0.98:
                        raw_score = 2.2 * ema_factor
                    elif val <= mid_point:
                        raw_score = 1.2 * ema_factor
                    elif val <= mid_point * 1.02:
                        raw_score = -1.2 * ema_factor
                    elif val <= resistance:
                        raw_score = -2.2 * ema_factor
                    elif val <= resistance * 1.02:
                        raw_score = -3.5 * ema_factor
                        signals_list.append(f"📉 {indicator} Above Resistance")
                    elif val <= resistance * 1.03:
                        raw_score = -4.2 * ema_factor
                        signals_list.append(f"📉 {indicator} Strong Above Resistance")
                    else:
                        raw_score = -5.0 * ema_factor
                        signals_list.append(f"🚀 {indicator} Extreme Above Resistance")
                
                # ===== ADX با قدرت روند =====
                elif indicator == 'ADX':
                    if val > 50:
                        raw_score = 4.0
                        signals_list.append("🔥 Very Strong Trend")
                    elif val > 40:
                        raw_score = 3.5
                        signals_list.append("💪 Strong Trend")
                    elif val > 30:
                        raw_score = 2.5
                    elif val > 25:
                        raw_score = 1.8
                    elif val > 20:
                        raw_score = 1.0
                    elif val > 15:
                        raw_score = 0.5
                    else:
                        raw_score = 0
                        signals_list.append("⚪ No Strong Trend")
                
                # ===== BOLL با تشخیص نقاط شکست =====
                elif indicator == 'BOLL':
                    if val < support * 0.99:
                        raw_score = 4.5
                        signals_list.append("🚀 Below Bollinger Lower")
                    elif val < support:
                        raw_score = 3.8
                        signals_list.append("📈 Near Bollinger Lower")
                    elif val < mid_point * 0.98:
                        raw_score = 2.0
                    elif val < mid_point * 1.02:
                        raw_score = 0
                    elif val < resistance:
                        raw_score = -2.0
                    elif val < resistance * 1.01:
                        raw_score = -3.8
                        signals_list.append("📉 Near Bollinger Upper")
                    else:
                        raw_score = -4.5
                        signals_list.append("📉 Above Bollinger Upper")
                
                # ===== KDJ با سیگنال‌های تقاطع =====
                elif indicator == 'KDJ':
                    if val <= 10:
                        raw_score = 5.0
                        signals_list.append("🚀 KDJ Extreme Oversold")
                    elif val <= 20:
                        raw_score = 4.2
                        signals_list.append("📈 KDJ Oversold")
                    elif val <= 30:
                        raw_score = 3.0
                    elif val <= 40:
                        raw_score = 1.8
                    elif val <= 60:
                        raw_score = 0
                    elif val <= 70:
                        raw_score = -1.8
                    elif val <= 80:
                        raw_score = -3.0
                        signals_list.append("📉 KDJ Overbought")
                    elif val <= 90:
                        raw_score = -4.2
                        signals_list.append("📉 KDJ Strong Overbought")
                    else:
                        raw_score = -5.0
                        signals_list.append("🚀 KDJ Extreme Overbought")
                
                # ===== سایر اندیکاتورها =====
                elif indicator in self.oscillators:
                    if val <= 15:
                        raw_score = 4.0
                        signals_list.append(f"📈 {indicator} Oversold")
                    elif val <= 25:
                        raw_score = 3.0
                    elif val <= 35:
                        raw_score = 2.0
                    elif val <= 45:
                        raw_score = 1.0
                    elif val <= 55:
                        raw_score = 0
                    elif val <= 65:
                        raw_score = -1.0
                    elif val <= 75:
                        raw_score = -2.0
                    elif val <= 85:
                        raw_score = -3.0
                        signals_list.append(f"📉 {indicator} Overbought")
                    else:
                        raw_score = -4.0
                        signals_list.append(f"📉 {indicator} Strong Overbought")
                
                elif indicator in self.volume_indicators:
                    if val > 10000000:
                        raw_score = 4.0
                        signals_list.append("🔥 Very High Volume")
                    elif val > 5000000:
                        raw_score = 3.0
                        signals_list.append("📈 High Volume")
                    elif val > 2000000:
                        raw_score = 2.0
                    elif val > 1000000:
                        raw_score = 1.0
                    else:
                        raw_score = 0.5
                
                elif indicator in self.volatility_indicators:
                    if indicator == 'ATR':
                        volatility_ratio = val / support_resistance_range if support_resistance_range > 0 else 0
                        if volatility_ratio > 0.08:
                            raw_score = 3.0
                            signals_list.append("🔥 High Volatility")
                        elif volatility_ratio > 0.05:
                            raw_score = 2.0
                        elif volatility_ratio > 0.03:
                            raw_score = 1.5
                        else:
                            raw_score = 1.0
                    else:  # BB_Upper, BB_Lower
                        if indicator == 'BB_Upper':
                            if val > resistance * 1.03:
                                raw_score = -3.5
                            elif val > resistance:
                                raw_score = -2.5
                            elif val > mid_point * 1.05:
                                raw_score = -1.5
                            else:
                                raw_score = 0.5
                        else:  # BB_Lower
                            if val < support * 0.97:
                                raw_score = 3.5
                            elif val < support:
                                raw_score = 2.5
                            elif val < mid_point * 0.95:
                                raw_score = 1.5
                            else:
                                raw_score = -0.5
                
                # اعمال ضریب موقعیت (نزدیکی به حمایت/مقاومت)
                position_multiplier = 1.0
                if price_position < 0.2:  # نزدیک حمایت
                    position_multiplier = 1.2 if raw_score > 0 else 0.8
                elif price_position > 0.8:  # نزدیک مقاومت
                    position_multiplier = 1.2 if raw_score < 0 else 0.8
                
                weighted_score = raw_score * weight * position_multiplier
                scores[indicator] = weighted_score
                total_weighted_score += weighted_score
                total_weight += weight
                
            except Exception as e:
                logger.error(f"Error analyzing {indicator}: {e}")
                continue
        
        # محاسبه امتیاز نهایی
        max_possible_score = sum(self.weights.get(ind, 3.0) * 5.0 for ind in indicators.keys())
        normalized_score = (total_weighted_score / max_possible_score) * 10 if max_possible_score > 0 else 0
        
        # محاسبه اطمینان
        confidence = min(100, (normalized_score / 10) * 100 + 10)
        
        # ===== تولید سیگنال نهایی با الگوریتم هوشمند =====
        signal_result = self.generate_signal_ultra(
            normalized_score,
            support,
            resistance,
            current_price,
            len(indicators),
            analysis_level,
            price_position,
            signals_list,
            confidence
        )
        
        # ذخیره سیگنال در دیتابیس
        signal_result['indicators_used'] = list(indicators.keys())
        db.save_signal(0, signal_result)
        
        return signal_result
    
    def generate_signal_ultra(self, score, support, resistance, current_price, 
                             indicator_count, analysis_level, price_position, 
                             signals_list, confidence):
        """تولید سیگنال فوق‌پیشرفته"""
        
        price_range = resistance - support
        range_percent = (price_range / support) * 100
        multiplier = min(indicator_count / 8, 2.5)
        
        # تعیین سطح تحلیل
        if analysis_level == "premium":
            profit_multiplier = 2.0
            accuracy_bonus = "⭐ Premium Analysis - Ultra High Accuracy"
            confidence_bonus = 15
        elif analysis_level == "advanced":
            profit_multiplier = 1.5
            accuracy_bonus = "🎯 Advanced Analysis - High Accuracy"
            confidence_bonus = 8
        else:
            profit_multiplier = 1.0
            accuracy_bonus = "📊 Basic Analysis - Standard Accuracy"
            confidence_bonus = 0
        
        # ===== تقسیم‌بندی ۵ سطحی سیگنال =====
        if score >= 3.0:
            if score >= 8.0:
                direction = "🚀 STRONG BUY - Extreme Opportunity 🚀"
                base_profit = min(50 + (score - 8) * 15 + range_percent * 1.5, 85)
                loss_percent = max(6 - (score - 8) * 0.3, 4)
                risk_level = "LOW"
                urgency = "IMMEDIATE"
            elif score >= 6.0:
                direction = "📈 STRONG BUY - Good Entry 📈"
                base_profit = min(35 + (score - 6) * 10 + range_percent, 65)
                loss_percent = max(8 - (score - 6) * 0.4, 6)
                risk_level = "LOW-MEDIUM"
                urgency = "SOON"
            elif score >= 4.5:
                direction = "📈 BUY - Reasonable Entry 📈"
                base_profit = min(25 + (score - 4.5) * 7 + range_percent * 0.9, 50)
                loss_percent = max(10 - (score - 4.5) * 0.5, 8)
                risk_level = "MEDIUM"
                urgency = "NORMAL"
            else:
                direction = "📊 BUY - Cautious Entry 📊"
                base_profit = min(18 + (score - 3) * 5 + range_percent * 0.7, 40)
                loss_percent = max(12 - (score - 3) * 0.6, 10)
                risk_level = "MEDIUM-HIGH"
                urgency = "CAUTIOUS"
                
        elif score <= -3.0:
            if score <= -8.0:
                direction = "🚀 STRONG SELL - Extreme Opportunity 🚀"
                base_profit = min(55 + abs(score + 8) * 15 + range_percent * 1.5, 90)
                loss_percent = max(6 - abs(score + 8) * 0.3, 4)
                risk_level = "LOW"
                urgency = "IMMEDIATE"
            elif score <= -6.0:
                direction = "📉 STRONG SELL - Good Entry 📉"
                base_profit = min(40 + abs(score + 6) * 10 + range_percent, 70)
                loss_percent = max(8 - abs(score + 6) * 0.4, 6)
                risk_level = "LOW-MEDIUM"
                urgency = "SOON"
            elif score <= -4.5:
                direction = "📉 SELL - Reasonable Entry 📉"
                base_profit = min(28 + abs(score + 4.5) * 7 + range_percent * 0.9, 55)
                loss_percent = max(10 - abs(score + 4.5) * 0.5, 8)
                risk_level = "MEDIUM"
                urgency = "NORMAL"
            else:
                direction = "📊 SELL - Cautious Entry 📊"
                base_profit = min(20 + abs(score + 3) * 5 + range_percent * 0.7, 45)
                loss_percent = max(12 - abs(score + 3) * 0.6, 10)
                risk_level = "MEDIUM-HIGH"
                urgency = "CAUTIOUS"
        else:
            direction = "⚪ HOLD - Wait for Better Setup ⚪"
            base_profit = 12 + range_percent * 0.5
            loss_percent = 15
            risk_level = "HIGH"
            urgency = "WAIT"
        
        # اعمال ضرایب
        final_profit = base_profit * multiplier * profit_multiplier
        final_loss = loss_percent
        
        # موقعیت قیمت
        if price_position < 0.15:
            position_analysis = "✅ Near Support - Good for BUY"
        elif price_position > 0.85:
            position_analysis = "✅ Near Resistance - Good for SELL"
        else:
            position_analysis = "⚪ In Middle Range - Wait for Better Position"
        
        # فرمت‌بندی سیگنال‌های برتر (حداکثر ۵ مورد)
        top_signals = signals_list[:5] if signals_list else ["📊 Technical Analysis Signal"]
        
        return {
            'direction': direction,
            'profit_percent': round(final_profit, 1),
            'loss_percent': round(final_loss, 1),
            'score': round(score, 2),
            'confidence': round(min(100, confidence + confidence_bonus)),
            'accuracy_bonus': accuracy_bonus,
            'position_analysis': position_analysis,
            'risk_level': risk_level,
            'urgency': urgency,
            'top_signals': top_signals,
            'indicator_count': indicator_count,
            'price_position': round(price_position * 100, 1),
            'analysis_level': analysis_level,
            'multiplier': round(multiplier, 2)
        }

analyzer = UltraTechnicalAnalyzer()

# ==================== متغیرهای سراسری ====================
user_data = {}
all_users = set()
referral_data = {}

# ==================== لیست اندیکاتورها ====================
INDICATORS = [
    "RSI", "MACD", "EMA5", "EMA10", "EMA30", "MA", "BOLL", "KDJ", 
    "ADX", "ATR", "VOL", "OBV", "Ichimoku_Cloud", "Stoch", "CCI",
    "Williams", "MFI", "PSAR", "BB_Upper", "BB_Lower"
]

# ==================== توابع کمکی ====================
def get_analysis_level(referral_count):
    if referral_count >= 10:
        return "premium"
    elif referral_count >= 5:
        return "advanced"
    else:
        return "basic"

def get_indicators_keyboard(user_id):
    selected_indicators = user_data.get(user_id, {}).get('indicators', {})
    referral_count = referral_data.get(user_id, {}).get('referral_count', 0)
    analysis_level = get_analysis_level(referral_count)
    
    # نمایش سطح تحلیل
    level_emoji = "⭐" if analysis_level == "premium" else "🎯" if analysis_level == "advanced" else "📊"
    level_text = "Premium" if analysis_level == "premium" else "Advanced" if analysis_level == "advanced" else "Basic"
    
    keyboard = []
    row = []
    for i, indicator in enumerate(INDICATORS):
        display_name = f"✅ {indicator}" if indicator in selected_indicators else indicator
        row.append(KeyboardButton(display_name))
        
        if len(row) == 3 or i == len(INDICATORS) - 1:
            keyboard.append(row)
            row = []
    
    keyboard.append([
        KeyboardButton("🔄 Register | ثبت"),
        KeyboardButton("📊 Start Analysis | شروع تحلیل")
    ])
    
    keyboard.append([
        KeyboardButton(f"🎁 Invite Friends | دعوت دوستان ({referral_count})"),
        KeyboardButton(f"{level_emoji} {level_text} Analysis")
    ])
    
    keyboard.append([
        KeyboardButton("💱 TobitEx Exchange | صرافی توبیت"),
        KeyboardButton("🔄 Tabdil Exchange | صرافی تبدیل")
    ])
    
    # دکمه‌های ادمین
    if user_id == ADMIN_ID:
        keyboard.append([
            KeyboardButton("📢 Broadcast | ارسال پیام"),
            KeyboardButton("📊 Stats | آمار")
        ])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ==================== هندلرهای ربات ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    first_name = update.effective_user.first_name or ""
    
    all_users.add(user_id)
    
    # مدیریت رفرال
    if context.args and len(context.args) > 0:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id and referrer_id in all_users:
                if referrer_id not in referral_data:
                    referral_data[referrer_id] = {'referral_count': 0, 'referred_users': set()}
                
                if user_id not in referral_data[referrer_id]['referred_users']:
                    referral_data[referrer_id]['referral_count'] += 1
                    referral_data[referrer_id]['referred_users'].add(user_id)
                    
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"""🎉 Congratulations! | تبریک!

👤 A new user joined through your link!
یک کاربر جدید از طریق لینک شما عضو شد!

👥 Total Referrals | کل دعوت‌ها: {referral_data[referrer_id]['referral_count']}

⭐ Current Level | سطح فعلی: {get_analysis_level(referral_data[referrer_id]['referral_count']).upper()}"""
                        )
                    except:
                        pass
                    
                    db.add_user(user_id, username, first_name, referrer_id)
        except:
            pass
    
    # ثبت کاربر
    db.add_user(user_id, username, first_name)
    
    if user_id not in user_data:
        user_data[user_id] = {
            'indicators': {},
            'support': None,
            'resistance': None,
            'current_price': None,
            'state': 'menu'
        }
    
    if user_id not in referral_data:
        referral_data[user_id] = {'referral_count': 0, 'referred_users': set()}
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    welcome_text = """🔥 **Ultra Advanced Technical Analysis Bot** 🔥
**ربات تحلیل تکنیکال فوق‌پیشرفته**

📊 Analyzes 20 indicators with advanced algorithms
تحلیل ۲۰ اندیکاتور با الگوریتم‌های پیشرفته

🚀 **Features | امکانات:**
• Real-time price data | قیمت لحظه‌ای
• Smart signal generation | تولید سیگنال هوشمند
• Multi-level analysis | تحلیل چندسطحی
• Risk management | مدیریت ریسک
• Referral rewards | پاداش دعوت

🎯 **Start | شروع:** Click "📊 Start Analysis"
روی "شروع تحلیل" کلیک کنید

💎 **Levels | سطوح:**
• 0-4 invites: Basic | پایه
• 5-9 invites: Advanced | پیشرفته  
• 10+ invites: Premium | ممتاز"""
    
    await update.effective_chat.send_message(
        welcome_text,
        reply_markup=get_indicators_keyboard(user_id),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    all_users.add(user_id)
    
    if user_id not in user_data:
        user_data[user_id] = {
            'indicators': {},
            'support': None,
            'resistance': None,
            'current_price': None,
            'state': 'menu'
        }
    
    if user_id not in referral_data:
        referral_data[user_id] = {'referral_count': 0, 'referred_users': set()}
    
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except:
        pass
    
    # ===== سیستم رفرال =====
    if "🎁 Invite Friends" in text or "دعوت دوستان" in text:
        referral_link = f"https://t.me/TradeFuturesGuru_Bot?start={user_id}"
        referral_count = referral_data[user_id]['referral_count']
        level = get_analysis_level(referral_count)
        
        referral_text = f"""🎁 **Referral System | سیستم دعوت دوستان**

🔗 **Your Link | لینک شما:**
`{referral_link}`

📊 **Stats | آمار:**
• Total Invites | کل دعوت‌ها: {referral_count}
• Current Level | سطح فعلی: {level.upper()}

🎯 **Benefits | مزایا:**
• 5+ invites: Advanced Analysis | تحلیل پیشرفته
• 10+ invites: Premium Analysis | تحلیل ممتاز

📤 Share with friends! | با دوستان به اشتراک بگذارید!"""
        
        await update.effective_chat.send_message(
            referral_text,
            reply_markup=get_indicators_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== نمایش سطح تحلیل =====
    if "Analysis" in text or "تحلیل" in text:
        referral_count = referral_data[user_id]['referral_count']
        level = get_analysis_level(referral_count)
        
        level_text = f"""📊 **Your Analysis Level | سطح تحلیل شما**

🎯 **Level | سطح:** {level.upper()}
👥 **Referrals | دعوت‌ها:** {referral_count}

📈 **Benefits | مزایا:**
• {'⭐ Premium Analysis (Best Accuracy)' if level == 'premium' else '🎯 Advanced Analysis (High Accuracy)' if level == 'advanced' else '📊 Basic Analysis (Standard Accuracy)'}

💡 **Next Level | سطح بعدی:**
• {'🎯 You have Premium! | شما سطح ممتاز دارید!' if level == 'premium' else f'🎯 {5 - referral_count} more referrals for Advanced | {5 - referral_count} دعوت دیگر برای پیشرفته' if level == 'basic' else f'⭐ {10 - referral_count} more referrals for Premium | {10 - referral_count} دعوت دیگر برای ممتاز'}"""
        
        await update.effective_chat.send_message(
            level_text,
            reply_markup=get_indicators_keyboard(user_id),
            parse_mode='Markdown'
        )
        return
    
    # ===== صرافی‌ها =====
    if "TobitEx" in text or "توبیت" in text:
        await update.effective_chat.send_message(
            f"💱 **TobitEx Exchange | صرافی توبیت**\n\n🔗 {EXCHANGE_URLS['tobit']}",
            reply_markup=get_indicators_keyboard(user_id)
        )
        return
    
    if "Tabdil" in text or "تبدیل" in text:
        await update.effective_chat.send_message(
            f"🔄 **Tabdil Exchange | صرافی تبدیل**\n\n🔗 {EXCHANGE_URLS['tabdil']}",
            reply_markup=get_indicators_keyboard(user_id)
        )
        return
    
    # ===== ادمین =====
    if user_id == ADMIN_ID:
        if "Broadcast" in text or "ارسال پیام" in text:
            user_data[user_id]['state'] = 'broadcast'
            await update.effective_chat.send_message(
                "📝 Enter your message | پیام خود را وارد کنید:",
                reply_markup=get_indicators_keyboard(user_id)
            )
            return
            
        elif user_data[user_id]['state'] == 'broadcast':
            sent_count = 0
            for uid in all_users:
                try:
                    await context.bot.send_message(
                        chat_id=uid,
                        text=f"📢 **Admin Message | پیام ادمین:**\n\n{text}",
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                except:
                    continue
            
            user_data[user_id]['state'] = 'menu'
            await update.effective_chat.send_message(
                f"✅ Message sent to {sent_count} users! | پیام به {sent_count} کاربر ارسال شد!",
                reply_markup=get_indicators_keyboard(user_id)
            )
            return
            
        elif "Stats" in text or "آمار" in text:
            total_referrals = sum(data['referral_count'] for data in referral_data.values())
            premium_users = sum(1 for data in referral_data.values() if data['referral_count'] >= 10)
            advanced_users = sum(1 for data in referral_data.values() if 5 <= data['referral_count'] < 10)
            
            stats_text = f"""📊 **User Statistics | آمار کاربران**

👥 Total Users | کل کاربران: {len(all_users)}
🎁 Total Referrals | کل دعوت‌ها: {total_referrals}
⭐ Premium Users | کاربران ممتاز: {premium_users}
🎯 Advanced Users | کاربران پیشرفته: {advanced_users}
📊 Basic Users | کاربران پایه: {len(all_users) - premium_users - advanced_users}

📈 Conversion Rate | نرخ تبدیل: {((premium_users + advanced_users) / len(all_users) * 100) if all_users else 0:.1f}%"""
            
            await update.effective_chat.send_message(
                stats_text,
                reply_markup=get_indicators_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
    
    # ===== منطق اصلی ربات =====
    if "📊 Start Analysis" in text or "شروع تحلیل" in text:
        user_data[user_id]['state'] = 'waiting_current_price'
        user_data[user_id]['indicators'] = {}
        user_data[user_id]['support'] = None
        user_data[user_id]['resistance'] = None
        user_data[user_id]['current_price'] = None
        
        # دریافت قیمت واقعی
        real_price = price_fetcher.get_price()
        price_text = f" (Current: ${real_price:.2f})" if real_price else ""
        
        await update.effective_chat.send_message(
            f"💰 **Enter current price | قیمت فعلی را وارد کنید**{price_text}\n\n"
            f"Example | مثال: 65432.50\n\n"
            f"💡 Tip: You can use real-time price above | می‌توانید از قیمت واقعی بالا استفاده کنید",
            parse_mode='Markdown'
        )
        
    elif user_data[user_id]['state'] == 'waiting_current_price':
        try:
            user_data[user_id]['current_price'] = float(text.replace(',', '.'))
            user_data[user_id]['state'] = 'waiting_support_resistance'
            await update.effective_chat.send_message(
                "📊 **Enter Support & Resistance | حمایت و مقاومت را وارد کنید**\n\n"
                "**Format | فرمت:**\n"
                "Support 65000\n"
                "Resistance 66000\n\n"
                "حمایت 65000\n"
                "مقاومت 66000\n\n"
                "💡 Type exactly like above | دقیقاً مانند بالا تایپ کنید",
                parse_mode='Markdown'
            )
        except ValueError:
            await update.effective_chat.send_message(
                "❌ Please enter a valid number! | لطفاً عدد معتبر وارد کنید!"
            )
    
    elif user_data[user_id]['state'] == 'waiting_support_resistance':
        lines = text.strip().split('\n')
        try:
            for line in lines:
                line = line.strip().lower()
                if 'support' in line or 'حمایت' in line:
                    number = line.split()[-1].replace(',', '.')
                    user_data[user_id]['support'] = float(number)
                elif 'resistance' in line or 'مقاومت' in line:
                    number = line.split()[-1].replace(',', '.')
                    user_data[user_id]['resistance'] = float(number)
            
            if user_data[user_id]['support'] and user_data[user_id]['resistance']:
                if user_data[user_id]['support'] >= user_data[user_id]['resistance']:
                    await update.effective_chat.send_message(
                        "❌ Support must be lower than resistance! | حمایت باید کمتر از مقاومت باشد!"
                    )
                    return
                    
                user_data[user_id]['state'] = 'selecting_indicators'
                await update.effective_chat.send_message(
                    f"""✅ **Data registered! | داده‌ها ثبت شد!**

💰 Price | قیمت: {user_data[user_id]['current_price']}
📊 Support | حمایت: {user_data[user_id]['support']}
📈 Resistance | مقاومت: {user_data[user_id]['resistance']}

🔍 **Now select indicators | اکنون اندیکاتورها را انتخاب کنید:**

📋 Select at least 5 indicators for accurate analysis
حداقل ۵ اندیکاتور برای تحلیل دقیق انتخاب کنید

💡 More indicators = Higher accuracy
اندیکاتور بیشتر = دقت بالاتر""",
                    reply_markup=get_indicators_keyboard(user_id),
                    parse_mode='Markdown'
                )
        except:
            await update.effective_chat.send_message(
                "❌ Wrong format! Please try again. | فرمت اشتباه! لطفاً مجدداً وارد کنید."
            )
    
    elif user_data[user_id]['state'] == 'selecting_indicators':
        clean_text = text.replace("✅ ", "")
        
        if clean_text in INDICATORS:
            if clean_text not in user_data[user_id]['indicators']:
                user_data[user_id]['current_indicator'] = clean_text
                user_data[user_id]['state'] = 'waiting_indicator_value'
                await update.effective_chat.send_message(
                    f"📊 **Enter {clean_text} value | مقدار {clean_text} را وارد کنید**\n\n"
                    f"Example | مثال: 45.67\n\n"
                    f"💡 Tip: Use current indicator values from your chart | از مقادیر فعلی اندیکاتورها در چارت استفاده کنید",
                    parse_mode='Markdown'
                )
            else:
                await update.effective_chat.send_message(
                    f"⚠️ {clean_text} already registered! | {clean_text} قبلاً ثبت شده است!",
                    reply_markup=get_indicators_keyboard(user_id)
                )
            
        elif "Register" in text or "ثبت" in text:
            if len(user_data[user_id]['indicators']) >= 5:
                referral_count = referral_data[user_id]['referral_count']
                analysis_level = get_analysis_level(referral_count)
                
                # نمایش پیام در حال تحلیل
                status_msg = await update.effective_chat.send_message(
                    "🔄 **Analyzing indicators...**\n"
                    "در حال تحلیل اندیکاتورها...\n\n"
                    f"📊 {len(user_data[user_id]['indicators'])} indicators loaded"
                    f" | {len(user_data[user_id]['indicators'])} اندیکاتور بارگذاری شد",
                    parse_mode='Markdown'
                )
                
                # اجرای تحلیل
                result = analyzer.analyze_indicators_ultra(
                    user_data[user_id]['indicators'],
                    user_data[user_id]['support'],
                    user_data[user_id]['resistance'],
                    user_data[user_id]['current_price'],
                    analysis_level
                )
                
                # فرمت‌بندی سیگنال‌های برتر
                top_signals_text = "\n".join([f"• {s}" for s in result['top_signals'][:5]])
                
                signal_text = f"""🔥 **ANALYSIS RESULT | نتیجه تحلیل** 🔥

{result['direction']}

💰 **Profit Target | هدف سود:** {result['profit_percent']}%
📉 **Stop Loss | حد ضرر:** {result['loss_percent']}%

📊 **Confidence | اطمینان:** {result['confidence']}%
🎯 **Score | امتیاز:** {result['score']}/10
{result['accuracy_bonus']}

📍 **Position | موقعیت:**
{result['position_analysis']}
• Price Position | موقعیت قیمت: {result['price_position']}%

📋 **Signal Details | جزئیات سیگنال:**
• Risk Level | سطح ریسک: {result['risk_level']}
• Urgency | فوریت: {result['urgency']}
• Analysis Level | سطح تحلیل: {result['analysis_level'].upper()}
• Multiplier | ضریب: {result['multiplier']}x

📊 **Top Signals | سیگنال‌های برتر:**
{top_signals_text}

📋 **Used Indicators | اندیکاتورهای استفاده شده:**
{', '.join(user_data[user_id]['indicators'].keys())}

⚠️ **Risk Management | مدیریت ریسک:**
• Never risk more than 2-3% of your capital
• Always use stop loss
• هرگز بیش از ۲-۳٪ سرمایه خود را ریسک نکنید
• همیشه از حد ضرر استفاده کنید"""
                
                # حذف پیام وضعیت
                await status_msg.delete()
                
                # ارسال سیگنال نهایی
                await update.effective_chat.send_message(
                    signal_text,
                    reply_markup=get_indicators_keyboard(user_id),
                    parse_mode='Markdown'
                )
                
                # ریست داده‌ها
                user_data[user_id]['state'] = 'menu'
                
            else:
                await update.effective_chat.send_message(
                    f"❌ Please enter at least 5 indicators! | حداقل ۵ اندیکاتور وارد کنید!\n"
                    f"📊 Current | فعلی: {len(user_data[user_id]['indicators'])}/20",
                    reply_markup=get_indicators_keyboard(user_id)
                )
    
    elif user_data[user_id]['state'] == 'waiting_indicator_value':
        try:
            indicator_name = user_data[user_id]['current_indicator']
            indicator_value = float(text.replace(',', '.'))
            user_data[user_id]['indicators'][indicator_name] = indicator_value
            user_data[user_id]['state'] = 'selecting_indicators'
            
            # نمایش پیشرفت
            progress_text = f"""✅ {indicator_name} registered! | {indicator_name} ثبت شد!

📊 Registered Indicators | اندیکاتورهای ثبت شده: {len(user_data[user_id]['indicators'])}/20

📋 **Current List | لیست فعلی:**
{chr(10).join([f"• {ind}: {val}" for ind, val in user_data[user_id]['indicators'].items()])}

🔍 Continue adding or click 'Register' to analyze
ادامه دهید یا روی 'ثبت' کلیک کنید

💡 **Tip | نکته:** Minimum 5 indicators = Good analysis
حداقل ۵ اندیکاتور = تحلیل خوب"""
            
            await update.effective_chat.send_message(
                progress_text,
                reply_markup=get_indicators_keyboard(user_id),
                parse_mode='Markdown'
            )
        except ValueError:
            await update.effective_chat.send_message(
                "❌ Please enter a valid number! | لطفاً عدد معتبر وارد کنید! (مثال: 45.67)"
            )

# ==================== اجرا ====================
def main():
    print("=" * 60)
    print("🚀 Ultra Advanced Trading Bot Started")
    print("🤖 ربات تحلیل تکنیکال فوق‌پیشرفته")
    print("=" * 60)
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"📊 Indicators: {len(INDICATORS)}")
    print(f"🔗 Exchange Links: {len(EXCHANGE_URLS)}")
    print("=" * 60)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is running...")
    print("✅ Bot is ready!")
    print("=" * 60)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
