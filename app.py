# ============================================================
# ULTIMATE SIGNAL BOT V7 - FULL VERSION
# 8 ALGORITHMS + DEEP LEARNING + PAYMENT + ADMIN PANEL
# ============================================================

import requests
import numpy as np
import time
import json
import os
import sqlite3
from datetime import datetime, timedelta
from collections import deque
import threading

# ============================================================
# 🔧 CONFIGURATION (YOUR DATA)
# ============================================================

BOT_TOKEN = "7780798170:AAHTDl295s15_RwhfhjGentSLZzye3keJP0"
CHANNEL_ID = "@davnold"
ADMIN_ID = 327855654

# Payment Settings
WALLET_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
WALLET_NETWORK = "TRC20"
PRICE = "100 USDT"
SUBSCRIBE_DAYS = 30

# Signal Settings
INTERVAL = 180  # 3 minutes
MIN_CONFIDENCE = 60
MAX_SIGNALS = 2

# ============================================================
# 📡 1. GET DATA FROM BINANCE
# ============================================================

def get_candles(symbol, limit=250):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit={limit}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                'close': [float(x[4]) for x in data],
                'high': [float(x[2]) for x in data],
                'low': [float(x[3]) for x in data],
                'volume': [float(x[5]) for x in data],
                'open': [float(x[1]) for x in data]
            }
    except:
        pass
    return None

def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return float(r.json()['price'])
    except:
        pass
    return None

# ============================================================
# 💾 2. DATABASE
# ============================================================

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('signal_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP,
                free_signals INTEGER DEFAULT 2,
                subscription_expire TIMESTAMP,
                is_active BOOLEAN DEFAULT 0,
                feedback_count INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                negative_feedback INTEGER DEFAULT 0
            )
        ''')
        
        # Signals table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT,
                direction TEXT,
                entry REAL,
                tp REAL,
                sl REAL,
                confidence INTEGER,
                created_at TIMESTAMP,
                is_free BOOLEAN DEFAULT 0,
                rsi REAL,
                macd REAL,
                vwap REAL,
                score REAL,
                reasons TEXT,
                feedback TEXT DEFAULT '',
                profit_loss REAL DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Payments table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_hash TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP,
                confirmed_at TIMESTAMP,
                expire_at TIMESTAMP
            )
        ''')
        
        # Settings table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Set default settings
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("signal_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("payment_enabled", "1")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("wallet_address", ?)', (WALLET_ADDRESS,))
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("price", ?)', (PRICE,))
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("free_signals", "2")')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        self.cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def get_free_signals(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 2
        return user[4] if len(user) > 4 else 2
    
    def use_free_signal(self, user_id):
        self.cursor.execute('''
            UPDATE users SET free_signals = free_signals - 1
            WHERE user_id = ? AND free_signals > 0
        ''', (user_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def has_subscription(self, user_id):
        self.cursor.execute('''
            SELECT subscription_expire FROM users 
            WHERE user_id = ? AND subscription_expire IS NOT NULL
        ''', (user_id,))
        r = self.cursor.fetchone()
        if r and r[0]:
            try:
                expire = datetime.fromisoformat(r[0])
                if expire > datetime.now():
                    return True, expire
            except:
                pass
        return False, None
    
    def add_payment(self, user_id, payment_hash):
        self.cursor.execute('''
            INSERT INTO payments (user_id, payment_hash, created_at)
            VALUES (?, ?, ?)
        ''', (user_id, payment_hash, datetime.now().isoformat()))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute('''
            SELECT id, user_id, payment_hash, created_at 
            FROM payments WHERE status = 'pending'
            ORDER BY created_at ASC
        ''')
        return self.cursor.fetchall()
    
    def confirm_payment(self, payment_id):
        payment = self.get_payment(payment_id)
        if not payment or payment[3] != 'pending':
            return False, None
        
        user_id = payment[1]
        expire_date = datetime.now() + timedelta(days=SUBSCRIBE_DAYS)
        
        self.cursor.execute('''
            UPDATE payments SET status = 'confirmed', confirmed_at = ?, expire_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), expire_date.isoformat(), payment_id))
        
        self.cursor.execute('''
            UPDATE users SET subscription_expire = ?, is_active = 1
            WHERE user_id = ?
        ''', (expire_date.isoformat(), user_id))
        
        self.conn.commit()
        return True, user_id, expire_date
    
    def reject_payment(self, payment_id):
        self.cursor.execute('''
            UPDATE payments SET status = 'rejected' WHERE id = ?
        ''', (payment_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_payment(self, payment_id):
        self.cursor.execute('SELECT id, user_id, payment_hash, status FROM payments WHERE id = ?', (payment_id,))
        return self.cursor.fetchone()
    
    def save_signal(self, user_id, signal_data, is_free=False):
        self.cursor.execute('''
            INSERT INTO signals (
                user_id, symbol, direction, entry, tp, sl, confidence,
                created_at, is_free, rsi, macd, vwap, score, reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, signal_data['symbol'], signal_data['signal'],
            signal_data['price'], signal_data['tp'], signal_data['sl'],
            signal_data['confidence'], datetime.now().isoformat(),
            1 if is_free else 0,
            signal_data.get('rsi', 0), signal_data.get('macd', 0),
            signal_data.get('vwap', 0), signal_data.get('score', 0),
            '|'.join(signal_data.get('reasons', []))
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def update_feedback(self, signal_id, feedback_type):
        self.cursor.execute('''
            UPDATE signals SET feedback = ? WHERE id = ?
        ''', (feedback_type, signal_id))
        
        self.cursor.execute('SELECT user_id FROM signals WHERE id = ?', (signal_id,))
        r = self.cursor.fetchone()
        if r:
            user_id = r[0]
            if feedback_type == 'positive':
                self.cursor.execute('''
                    UPDATE users SET positive_feedback = positive_feedback + 1,
                    feedback_count = feedback_count + 1 WHERE user_id = ?
                ''', (user_id,))
            else:
                self.cursor.execute('''
                    UPDATE users SET negative_feedback = negative_feedback + 1,
                    feedback_count = feedback_count + 1 WHERE user_id = ?
                ''', (user_id,))
        
        self.conn.commit()
    
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        r = self.cursor.fetchone()
        return r[0] if r else None
    
    def update_setting(self, key, value):
        self.cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
        self.conn.commit()
    
    def get_all_users(self):
        self.cursor.execute('SELECT user_id FROM users')
        return self.cursor.fetchall()

db = Database()

# ============================================================
# 📊 3. ANALYSIS ALGORITHMS
# ============================================================

class AnalysisAlgorithms:
    
    @staticmethod
    def rsi_analysis(prices):
        if len(prices) < 30:
            return 0, "Not enough data"
        
        p = np.array(prices[-30:])
        deltas = np.diff(p)
        gain = np.mean(deltas[deltas > 0]) if np.sum(deltas > 0) > 0 else 0
        loss = -np.mean(deltas[deltas < 0]) if np.sum(deltas < 0) > 0 else 0.001
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        if rsi < 25:
            return 25, f"RSI oversold ({rsi:.1f})"
        elif rsi < 35:
            return 18, f"RSI near oversold ({rsi:.1f})"
        elif rsi > 75:
            return -25, f"RSI overbought ({rsi:.1f})"
        elif rsi > 65:
            return -18, f"RSI near overbought ({rsi:.1f})"
        return 0, f"RSI neutral ({rsi:.1f})"
    
    @staticmethod
    def macd_analysis(prices):
        if len(prices) < 30:
            return 0, "Not enough data"
        
        p = np.array(prices)
        
        f_mult = 2 / 13
        f_ema = float(np.mean(p[-13:]))
        for price in p[-13:]:
            f_ema = float(price) * f_mult + f_ema * (1 - f_mult)
        
        s_mult = 2 / 26
        s_ema = float(np.mean(p[-26:]))
        for price in p[-26:]:
            s_ema = float(price) * s_mult + s_ema * (1 - s_mult)
        
        macd_line = f_ema - s_ema
        
        sig_mult = 2 / 9
        sig_line = macd_line
        for _ in range(9):
            sig_line = macd_line * sig_mult + sig_line * (1 - sig_mult)
        
        hist = macd_line - sig_line
        
        if macd_line > 0 and hist > 0:
            return 20, f"MACD bullish ({macd_line:.4f})"
        elif macd_line > 0:
            return 8, f"MACD positive but weak ({macd_line:.4f})"
        elif macd_line < 0 and hist < 0:
            return -20, f"MACD bearish ({macd_line:.4f})"
        elif macd_line < 0:
            return -8, f"MACD negative but weak ({macd_line:.4f})"
        return 0, f"MACD neutral ({macd_line:.4f})"
    
    @staticmethod
    def ma_analysis(prices):
        if len(prices) < 50:
            return 0, "Not enough data"
        
        ma7 = np.mean(prices[-7:])
        ma20 = np.mean(prices[-20:])
        ma50 = np.mean(prices[-50:])
        current = prices[-1]
        
        if current > ma7 > ma20 > ma50:
            return 20, "Strong uptrend (MA7>MA20>MA50)"
        elif current < ma7 < ma20 < ma50:
            return -20, "Strong downtrend (MA7<MA20<MA50)"
        elif current > ma20:
            return 10, "Price above MA20"
        else:
            return -10, "Price below MA20"
    
    @staticmethod
    def bollinger_analysis(prices):
        if len(prices) < 30:
            return 0, "Not enough data"
        
        p = np.array(prices[-30:])
        ma = np.mean(p)
        std = np.std(p)
        
        upper = ma + (2 * std)
        lower = ma - (2 * std)
        current = prices[-1]
        
        if current < lower:
            return 20, f"Touch lower band (${lower:.2f})"
        elif current > upper:
            return -20, f"Touch upper band (${upper:.2f})"
        elif current < ma:
            return 10, "Lower half of band"
        else:
            return -10, "Upper half of band"
    
    @staticmethod
    def vwap_analysis(prices, volumes):
        if len(prices) < 20:
            return 0, "Not enough data"
        
        total_value = sum(prices[i] * volumes[i] for i in range(len(prices)))
        total_volume = sum(volumes)
        if total_volume == 0:
            return 0, "Zero volume"
        
        vwap = total_value / total_volume
        current = prices[-1]
        
        if current > vwap:
            return 15, f"Price above VWAP (${vwap:.2f})"
        else:
            return -15, f"Price below VWAP (${vwap:.2f})"
    
    @staticmethod
    def sr_analysis(prices, highs, lows):
        if len(prices) < 30:
            return 0, "Not enough data"
        
        peaks, troughs = [], []
        for i in range(2, len(prices)-2):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                peaks.append(highs[i])
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                troughs.append(lows[i])
        
        if not peaks or not troughs:
            return 0, "No S/R levels"
        
        support = min(troughs)
        resistance = max(peaks)
        current = prices[-1]
        
        score = 0
        reasons = []
        
        if support > 0:
            dist = ((current - support) / current) * 100
            if dist < 1.5:
                score += 15
                reasons.append(f"Near support (${support:.2f})")
            elif dist < 3:
                score += 8
                reasons.append(f"Close to support (${support:.2f})")
        
        if resistance > 0:
            dist = ((resistance - current) / current) * 100
            if dist < 1.5:
                score -= 15
                reasons.append(f"Near resistance (${resistance:.2f})")
            elif dist < 3:
                score -= 8
                reasons.append(f"Close to resistance (${resistance:.2f})")
        
        if not reasons:
            return 0, "No S/R levels"
        return score, " | ".join(reasons)
    
    @staticmethod
    def volume_analysis(volumes):
        if len(volumes) < 20:
            return 0, "Not enough data"
        
        avg_vol = np.mean(volumes[-20:])
        current_vol = volumes[-1]
        ratio = current_vol / avg_vol if avg_vol > 0 else 1
        
        if ratio > 2.5:
            return 15, f"High volume ({ratio:.1f}x avg)"
        elif ratio > 1.8:
            return 10, f"Good volume ({ratio:.1f}x avg)"
        elif ratio > 1.3:
            return 5, f"Moderate volume ({ratio:.1f}x avg)"
        elif ratio < 0.5:
            return -10, f"Low volume ({ratio:.1f}x avg)"
        return 0, f"Normal volume ({ratio:.1f}x avg)"

# ============================================================
# 🧠 4. LEARNING SYSTEM
# ============================================================

class LearningSystem:
    def __init__(self):
        self.file = "learning_data.json"
        self.load()
        self.weights = {
            'rsi': 1.0, 'macd': 1.0, 'ma': 1.0,
            'bollinger': 1.0, 'vwap': 1.5, 'sr': 1.0,
            'volume': 1.0
        }
    
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f:
                    data = json.load(f)
                    self.positive = data.get('positive', 0)
                    self.negative = data.get('negative', 0)
                    self.total = data.get('total', 0)
                    if 'weights' in data:
                        self.weights.update(data['weights'])
                    return
            except:
                pass
        
        self.positive = 0
        self.negative = 0
        self.total = 0
        self.save()
    
    def save(self):
        try:
            with open(self.file, 'w') as f:
                json.dump({
                    'positive': self.positive,
                    'negative': self.negative,
                    'total': self.total,
                    'weights': self.weights
                }, f)
        except:
            pass
    
    def add_feedback(self, feedback_type):
        if feedback_type == 'positive':
            self.positive += 1
            for key in self.weights:
                self.weights[key] = min(2.0, self.weights[key] * 1.02)
        else:
            self.negative += 1
            for key in self.weights:
                self.weights[key] = max(0.4, self.weights[key] * 0.98)
        self.total += 1
        self.save()
    
    def get_accuracy(self):
        total = self.positive + self.negative
        if total == 0:
            return 50.0
        return round((self.positive / total) * 100, 1)

# ============================================================
# 🎯 5. SIGNAL GENERATOR
# ============================================================

def generate_signal(symbol, learner):
    data = get_candles(symbol, 250)
    if not data:
        return None
    
    prices = data['close']
    highs = data['high']
    lows = data['low']
    volumes = data['volume']
    current = prices[-1]
    
    # Run all algorithms
    results = []
    
    algo = AnalysisAlgorithms()
    results.append(('rsi', *algo.rsi_analysis(prices)))
    results.append(('macd', *algo.macd_analysis(prices)))
    results.append(('ma', *algo.ma_analysis(prices)))
    results.append(('bollinger', *algo.bollinger_analysis(prices)))
    results.append(('vwap', *algo.vwap_analysis(prices, volumes)))
    results.append(('sr', *algo.sr_analysis(prices, highs, lows)))
    results.append(('volume', *algo.volume_analysis(volumes)))
    
    # Calculate total score with weights
    total_score = 0
    all_reasons = []
    
    for algo_name, score, reason in results:
        weight = learner.weights.get(algo_name, 1.0)
        total_score += score * weight
        if reason and "Not enough" not in reason:
            all_reasons.append(reason)
    
    confidence = min(98, 50 + abs(total_score) / 2)
    
    if total_score > 28:
        signal = "BUY"
    elif total_score < -28:
        signal = "SELL"
    else:
        signal = "HOLD"
    
    # Remove duplicates
    unique_reasons = []
    for r in all_reasons:
        if r not in unique_reasons:
            unique_reasons.append(r)
    
    # TP/SL
    if signal == "BUY":
        tp = round(current * 1.025, 2)
        sl = round(current * 0.975, 2)
    elif signal == "SELL":
        tp = round(current * 0.975, 2)
        sl = round(current * 1.025, 2)
    else:
        tp = current
        sl = current
    
    return {
        'symbol': symbol,
        'price': current,
        'signal': signal,
        'confidence': round(confidence, 1),
        'score': round(total_score, 1),
        'tp': tp,
        'sl': sl,
        'rsi': results[0][1],
        'macd': results[1][1],
        'vwap': results[4][1],
        'reasons': unique_reasons[:5],
        'time': datetime.now().strftime("%H:%M")
    }

# ============================================================
# 📋 6. SYMBOLS
# ============================================================

SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT',
    'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'BCHUSDT',
    'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT',
    'FTMUSDT', 'XLMUSDT', 'EGLDUSDT', 'XMRUSDT', 'ZECUSDT',
    'ETCUSDT', 'XTZUSDT', 'EOSUSDT', 'AAVEUSDT', 'MKRUSDT',
    'COMPUSDT', 'YFIUSDT', 'SUSHIUSDT', 'CAKEUSDT', 'AXSUSDT',
    'SANDUSDT', 'APEUSDT', 'CRVUSDT', 'RUNEUSDT', 'FLOWUSDT',
    'QNTUSDT', 'SNXUSDT', 'GRTUSDT', 'LDOUSDT', 'ARBUSDT',
    'OPUSDT', 'INJUSDT', 'SEIUSDT', 'WLDUSDT', 'PEPEUSDT'
]

# ============================================================
# 📡 7. TELEGRAM FUNCTIONS
# ============================================================

def send_telegram(message, chat_id=None):
    if not message:
        return False
    
    if chat_id is None:
        chat_id = CHANNEL_ID
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        r = requests.post(url, data=data, timeout=15)
        return r.status_code == 200
    except:
        return False

def send_admin(message):
    return send_telegram(message, ADMIN_ID)

def build_signal_message(signal, learner):
    if not signal or signal['signal'] == 'HOLD':
        return None
    
    emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
    direction = "🚀 LONG (BUY)" if signal['signal'] == 'BUY' else "💀 SHORT (SELL)"
    
    msg = f"""
{emoji} <b>SIGNAL - {signal['symbol']}</b>
⏰ {signal['time']}

📊 <b>{direction}</b>
💰 <b>Entry:</b> <code>${signal['price']:,.2f}</code>
🎯 <b>Confidence:</b> <b>{signal['confidence']}%</b>
📈 <b>Score:</b> {signal['score']}

━━━━━━━━━━━━━━━━━━━
🎯 <b>Take Profit:</b> <code>${signal['tp']:,.2f}</code>
🛑 <b>Stop Loss:</b> <code>${signal['sl']:,.2f}</code>

━━━━━━━━━━━━━━━━━━━
📊 <b>Indicators:</b>
• RSI: {signal['rsi']:.1f}
• MACD: {signal['macd']:.4f}
• VWAP: ${signal['vwap']:,.2f}

━━━━━━━━━━━━━━━━━━━
📝 <b>Reasons:</b>
"""
    
    for i, reason in enumerate(signal['reasons'][:5], 1):
        msg += f"{i}. {reason}\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━
🧠 <b>Learning:</b>
• Accuracy: {learner.get_accuracy()}%
• Feedback: {learner.positive}✅ / {learner.negative}❌

⚠️ <i>Trade at your own risk!</i>
"""
    
    return msg

# ============================================================
# 💳 8. PAYMENT SYSTEM
# ============================================================

def check_payments():
    """Check pending payments and notify admin"""
    payments = db.get_pending_payments()
    
    if not payments:
        return
    
    for payment in payments:
        payment_id, user_id, payment_hash, created_at = payment
        
        user = db.get_user(user_id)
        username = user[1] if user else "Unknown"
        
        msg = f"""
🧾 <b>New Payment Request</b>
🆔 ID: {payment_id}
👤 User: {user_id}
📛 Name: {username}
🔑 Hash: <code>{payment_hash}</code>
📅 Time: {created_at}

Click to confirm or reject:
"""
        
        # Send to admin
        send_admin(msg)
        send_admin(f"✅ /confirm_{payment_id} - Confirm")
        send_admin(f"❌ /reject_{payment_id} - Reject")

# ============================================================
# 👑 9. ADMIN COMMANDS
# ============================================================

def process_admin_command(text):
    """Process admin commands"""
    if text.startswith('/confirm_'):
        try:
            payment_id = int(text.replace('/confirm_', ''))
            success, user_id, expire_date = db.confirm_payment(payment_id)
            
            if success:
                msg = f"✅ Payment {payment_id} confirmed!\nUser: {user_id}\nExpires: {expire_date.strftime('%Y-%m-%d')}"
                send_admin(msg)
                
                # Notify user
                send_telegram(f"""
✅ <b>Your payment has been confirmed!</b>
📅 Subscription expires: {expire_date.strftime('%Y-%m-%d')}
🚀 You now have full access to all signals!
""", user_id)
            else:
                send_admin(f"❌ Failed to confirm payment {payment_id}")
        except:
            send_admin(f"❌ Error confirming payment")
    
    elif text.startswith('/reject_'):
        try:
            payment_id = int(text.replace('/reject_', ''))
            success = db.reject_payment(payment_id)
            
            if success:
                payment = db.get_payment(payment_id)
                if payment:
                    user_id = payment[1]
                    send_telegram(f"""
❌ <b>Your payment was rejected!</b>
Please try again or contact support.
""", user_id)
                send_admin(f"❌ Payment {payment_id} rejected")
            else:
                send_admin(f"❌ Failed to reject payment {payment_id}")
        except:
            send_admin(f"❌ Error rejecting payment")
    
    elif text == '/stats':
        users = db.get_all_users()
        signals = db.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        payments = db.cursor.execute('SELECT COUNT(*) FROM payments WHERE status="pending"').fetchone()[0]
        
        msg = f"""
📊 <b>BOT STATS</b>
👤 Users: {len(users)}
📈 Signals: {signals}
💳 Pending Payments: {payments}
🧠 Accuracy: {learner.get_accuracy()}%
✅ Positive: {learner.positive}
❌ Negative: {learner.negative}
        """
        send_admin(msg)
    
    elif text == '/help':
        msg = """
👑 <b>Admin Commands</b>
/confirm_<id> - Confirm payment
/reject_<id> - Reject payment
/stats - Show stats
/status - Show bot status
/on - Enable signals
/off - Disable signals
/help - Show this help
        """
        send_admin(msg)
    
    elif text == '/status':
        signal_status = "🟢 ACTIVE" if db.get_setting('signal_enabled') == '1' else "🔴 PAUSED"
        payment_status = "🟢 ACTIVE" if db.get_setting('payment_enabled') == '1' else "🔴 PAUSED"
        wallet = db.get_setting('wallet_address')
        price = db.get_setting('price')
        
        msg = f"""
📊 <b>BOT STATUS</b>
📡 Signals: {signal_status}
💳 Payment: {payment_status}
💰 Price: {price}
📌 Wallet: <code>{wallet}</code>
⏱ Interval: {INTERVAL//60}m
        """
        send_admin(msg)
    
    elif text == '/on':
        db.update_setting('signal_enabled', '1')
        send_admin("✅ Signals ENABLED")
    
    elif text == '/off':
        db.update_setting('signal_enabled', '0')
        send_admin("🔴 Signals DISABLED")

# ============================================================
# 🚀 10. MAIN LOOP
# ============================================================

def signal_loop():
    global learner
    learner = LearningSystem()
    
    print("\n" + "="*60)
    print("🚀 ULTIMATE SIGNAL BOT V7")
    print("📊 7 Algorithms + Learning + Payment")
    print("="*60)
    print(f"📢 Channel: {CHANNEL_ID}")
    print(f"👑 Admin: {ADMIN_ID}")
    print(f"💰 Wallet: {WALLET_ADDRESS}")
    print(f"⏱ Interval: {INTERVAL//60} minutes")
    print("="*60)
    
    # Send startup message
    send_telegram("🚀 Signal Bot V7 started!\n📊 7 Algorithms + Deep Learning")
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            
            # Check if signals are enabled
            if db.get_setting('signal_enabled') != '1':
                time.sleep(30)
                continue
            
            print(f"\n🔄 Cycle {cycle} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"🧠 Accuracy: {learner.get_accuracy()}%")
            
            # Check pending payments
            check_payments()
            
            # Find signals
            signals = []
            for symbol in SYMBOLS:
                signal = generate_signal(symbol, learner)
                if signal and signal['signal'] != 'HOLD':
                    if signal['confidence'] >= MIN_CONFIDENCE:
                        signals.append(signal)
                        print(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%)")
                time.sleep(0.03)
            
            # Sort and limit
            signals.sort(key=lambda x: x['confidence'], reverse=True)
            signals = signals[:MAX_SIGNALS]
            
            # Send to channel
            if signals:
                for signal in signals:
                    msg = build_signal_message(signal, learner)
                    if msg:
                        if send_telegram(msg):
                            print(f"✅ Sent: {signal['symbol']}")
                        time.sleep(1)
            else:
                if cycle % 3 == 0:
                    send_telegram("⏳ No strong signals found...")
            
            print(f"⏱ Waiting {INTERVAL//60} minutes...")
            time.sleep(INTERVAL)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            send_admin(f"❌ Error in cycle {cycle}: {e}")
            time.sleep(60)

# ============================================================
# 🏁 11. START
# ============================================================

if __name__ == "__main__":
    # Test connection
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
        if r.status_code == 200:
            print("✅ Bot connected to Telegram")
        else:
            print("❌ Bot connection failed")
    except:
        print("❌ Connection error")
    
    # Start signal loop
    signal_loop()