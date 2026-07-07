# ============================================
# PROFESSIONAL SIGNAL BOT V5 - FULLY WORKING
# WITH TELEGRAM SEND, AUTO LEARNING, 7 INDICATORS
# ============================================

import requests
import numpy as np
import time
import json
import os
from datetime import datetime
from collections import deque
import threading

# ============================================
# 🔧 CONFIGURATION (فقط اینجا رو عوض کن!)
# ============================================

BOT_TOKEN = "توکن_ربات_اینجا"  # از @BotFather بگیر
CHANNEL_ID = "@davnold"  # کانال خودت
ADMIN_ID = "ایدی_تلگرامت"  # ایدی خودت (عدد)

# تنظیمات سیگنال
INTERVAL = 180  # ۳ دقیقه
MIN_CONFIDENCE = 65
MAX_SIGNALS = 2

# ============================================
# 📡 ۱. گرفتن داده از بایننس
# ============================================

def get_candles(symbol, limit=250):
    """گرفتن کندل واقعی از بایننس"""
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
    except Exception as e:
        print(f"⚠️ Error getting candles: {e}")
    return None

def get_current_price(symbol):
    """گرفتن قیمت لحظه‌ای"""
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return float(r.json()['price'])
    except:
        pass
    return None

# ============================================
# 📊 ۲. اندیکاتورهای واقعی
# ============================================

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    p = np.array(prices[-period-1:])
    deltas = np.diff(p)
    gain = np.mean(deltas[deltas > 0]) if np.sum(deltas > 0) > 0 else 0
    loss = -np.mean(deltas[deltas < 0]) if np.sum(deltas < 0) > 0 else 0.001
    rs = gain / loss
    return round(100 - (100 / (1 + rs)), 1)

def calc_macd(prices, fast=12, slow=26, signal=9):
    if len(prices) < slow:
        return 0, 0, 0
    p = np.array(prices)
    
    # Fast EMA
    f_mult = 2 / (fast + 1)
    f_ema = float(np.mean(p[-fast:]))
    for price in p[-fast:]:
        f_ema = float(price) * f_mult + f_ema * (1 - f_mult)
    
    # Slow EMA
    s_mult = 2 / (slow + 1)
    s_ema = float(np.mean(p[-slow:]))
    for price in p[-slow:]:
        s_ema = float(price) * s_mult + s_ema * (1 - s_mult)
    
    macd_line = f_ema - s_ema
    
    # Signal line
    sig_mult = 2 / (signal + 1)
    sig_line = macd_line
    for _ in range(signal):
        sig_line = macd_line * sig_mult + sig_line * (1 - sig_mult)
    
    hist = macd_line - sig_line
    return round(macd_line, 4), round(sig_line, 4), round(hist, 4)

def calc_ma(prices, period):
    if len(prices) < period:
        return prices[-1]
    return round(float(np.mean(np.array(prices[-period:]))), 2)

def calc_ema(prices, period):
    if len(prices) < period:
        return prices[-1]
    p = np.array(prices)
    mult = 2 / (period + 1)
    ema = float(np.mean(p[-period:]))
    for price in p[-period:]:
        ema = float(price) * mult + ema * (1 - mult)
    return round(ema, 2)

def calc_bollinger(prices, period=20, std_dev=2):
    if len(prices) < period:
        return prices[-1], prices[-1], prices[-1]
    p = np.array(prices[-period:])
    ma = float(np.mean(p))
    std = float(np.std(p))
    return round(ma + std_dev * std, 2), round(ma, 2), round(ma - std_dev * std, 2)

def calc_vwap(prices, volumes):
    if len(prices) < 2:
        return prices[-1] if prices else 0
    total_value = sum(prices[i] * volumes[i] for i in range(len(prices)))
    total_volume = sum(volumes)
    if total_volume == 0:
        return prices[-1]
    return round(total_value / total_volume, 2)

def calc_atr(highs, lows, prices, period=14):
    if len(prices) < period:
        return 0.01
    tr = []
    for i in range(1, period + 1):
        if i < len(prices):
            tr.append(max(highs[-i] - lows[-i], abs(highs[-i] - prices[-i-1]), abs(lows[-i] - prices[-i-1])))
    return round(float(np.mean(np.array(tr))) if tr else 0.01, 2)

def calc_support_resistance(highs, lows, prices):
    if len(prices) < 20:
        return 0, 0
    
    peaks, troughs = [], []
    for i in range(2, len(prices)-2):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i] > highs[i-2] and highs[i] > highs[i+2]:
            peaks.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i] < lows[i-2] and lows[i] < lows[i+2]:
            troughs.append(lows[i])
    
    resistance = peaks[0] if peaks else 0
    support = troughs[0] if troughs else 0
    
    # پیدا کردن سطوح قوی‌تر
    if len(peaks) >= 2:
        for i in range(1, min(5, len(peaks))):
            if abs(peaks[i] - peaks[0]) / peaks[0] < 0.02:
                resistance = max(resistance, peaks[i])
    
    if len(troughs) >= 2:
        for i in range(1, min(5, len(troughs))):
            if abs(troughs[i] - troughs[0]) / troughs[0] < 0.02:
                support = min(support, troughs[i])
    
    return round(support, 2), round(resistance, 2)

# ============================================
# 🧠 ۳. سیستم یادگیری
# ============================================

class LearningSystem:
    def __init__(self):
        self.file = "learning_data.json"
        self.load()
        
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r') as f:
                    data = json.load(f)
                    self.positive = data.get('positive', 0)
                    self.negative = data.get('negative', 0)
                    self.total = data.get('total', 0)
                    self.weights = data.get('weights', {
                        'rsi': 1.0, 'macd': 1.0, 'ma': 1.0,
                        'bollinger': 1.0, 'volume': 1.0, 'vwap': 1.5,
                        'support': 1.0
                    })
                    return
            except:
                pass
        
        self.positive = 0
        self.negative = 0
        self.total = 0
        self.weights = {'rsi': 1.0, 'macd': 1.0, 'ma': 1.0, 'bollinger': 1.0, 'volume': 1.0, 'vwap': 1.5, 'support': 1.0}
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
                self.weights[key] = max(0.5, self.weights[key] * 0.98)
        self.total += 1
        self.save()
    
    def get_accuracy(self):
        total = self.positive + self.negative
        if total == 0:
            return 50.0
        return round((self.positive / total) * 100, 1)

# ============================================
# 🎯 ۴. تولید سیگنال
# ============================================

def generate_signal(symbol, learner):
    data = get_candles(symbol, 200)
    if not data:
        return None
    
    prices = data['close']
    highs = data['high']
    lows = data['low']
    volumes = data['volume']
    current = prices[-1]
    
    # محاسبه همه اندیکاتورها
    rsi = calc_rsi(prices, 14)
    macd, macd_sig, macd_hist = calc_macd(prices, 12, 26, 9)
    ma20 = calc_ma(prices, 20)
    ma50 = calc_ma(prices, 50)
    ma200 = calc_ma(prices, 200)
    upper, middle, lower = calc_bollinger(prices, 20, 2)
    vwap = calc_vwap(prices, volumes)
    support, resistance = calc_support_resistance(highs, lows, prices)
    atr = calc_atr(highs, lows, prices, 14)
    
    # حجم
    if len(volumes) >= 20:
        vol_ratio = round(volumes[-1] / float(np.mean(np.array(volumes[-20:]))), 2)
    else:
        vol_ratio = 1.0
    
    # ===== امتیازدهی =====
    score = 0
    reasons = []
    
    # ۱. VWAP (قوی‌ترین)
    if current > vwap:
        score += 20 * learner.weights['vwap']
        reasons.append(f"✅ VWAP: قیمت بالای میانگین وزنی (Bullish)")
    else:
        score -= 20 * learner.weights['vwap']
        reasons.append(f"❌ VWAP: قیمت پایین میانگین وزنی (Bearish)")
    
    # ۲. RSI
    if rsi < 30:
        score += 20 * learner.weights['rsi']
        reasons.append(f"✅ RSI اشباع فروش: {rsi}")
    elif rsi > 70:
        score -= 20 * learner.weights['rsi']
        reasons.append(f"❌ RSI اشباع خرید: {rsi}")
    elif rsi < 40:
        score += 10 * learner.weights['rsi']
        reasons.append(f"✅ RSI نزدیک اشباع فروش: {rsi}")
    elif rsi > 60:
        score -= 10 * learner.weights['rsi']
        reasons.append(f"❌ RSI نزدیک اشباع خرید: {rsi}")
    
    # ۳. MACD
    if macd > 0 and macd > macd_sig:
        score += 15 * learner.weights['macd']
        reasons.append(f"✅ MACD صعودی: {macd}")
    elif macd < 0 and macd < macd_sig:
        score -= 15 * learner.weights['macd']
        reasons.append(f"❌ MACD نزولی: {macd}")
    
    # ۴. میانگین متحرک
    if current > ma20 and ma20 > ma50:
        score += 15 * learner.weights['ma']
        reasons.append(f"✅ روند صعودی (MA20: {ma20:.0f} > MA50: {ma50:.0f})")
    elif current < ma20 and ma20 < ma50:
        score -= 15 * learner.weights['ma']
        reasons.append(f"❌ روند نزولی (MA20: {ma20:.0f} < MA50: {ma50:.0f})")
    
    # ۵. باند بولینگر
    if current < lower:
        score += 12 * learner.weights['bollinger']
        reasons.append(f"✅ برخورد به کف بولینگر: {lower:.0f}")
    elif current > upper:
        score -= 12 * learner.weights['bollinger']
        reasons.append(f"❌ برخورد به سقف بولینگر: {upper:.0f}")
    
    # ۶. حجم
    if vol_ratio > 2.0:
        score += 10 * learner.weights['volume']
        reasons.append(f"✅ حجم بالا: {vol_ratio}x میانگین")
    elif vol_ratio > 1.5:
        score += 5 * learner.weights['volume']
        reasons.append(f"✅ حجم خوب: {vol_ratio}x میانگین")
    elif vol_ratio < 0.5:
        score -= 10 * learner.weights['volume']
        reasons.append(f"❌ حجم کم: {vol_ratio}x میانگین")
    
    # ۷. حمایت/مقاومت
    if support > 0:
        dist_support = ((current - support) / current) * 100
        if dist_support < 1.0:
            score += 10 * learner.weights['support']
            reasons.append(f"✅ نزدیک حمایت: {support:.0f} (فاصله {dist_support:.1f}%)")
    
    if resistance > 0:
        dist_resistance = ((resistance - current) / current) * 100
        if dist_resistance < 1.0:
            score -= 10 * learner.weights['support']
            reasons.append(f"❌ نزدیک مقاومت: {resistance:.0f} (فاصله {dist_resistance:.1f}%)")
    
    # ===== تصمیم نهایی =====
    confidence = min(97, 50 + abs(score))
    
    if score > 25 and confidence >= MIN_CONFIDENCE:
        signal = "BUY"
    elif score < -25 and confidence >= MIN_CONFIDENCE:
        signal = "SELL"
    else:
        signal = "HOLD"
    
    # ===== حد سود و ضرر =====
    if signal == "BUY":
        tp = round(current * (1.02 + (confidence / 3000)), 2)
        sl = round(current * (0.98 - (confidence / 3000)), 2)
        if support > 0 and sl < support:
            sl = round(support * 0.995, 2)
    elif signal == "SELL":
        tp = round(current * (0.98 - (confidence / 3000)), 2)
        sl = round(current * (1.02 + (confidence / 3000)), 2)
        if resistance > 0 and sl > resistance:
            sl = round(resistance * 1.005, 2)
    else:
        tp = current
        sl = current
    
    return {
        'symbol': symbol,
        'price': current,
        'signal': signal,
        'confidence': round(confidence, 1),
        'score': round(score, 1),
        'tp': tp,
        'sl': sl,
        'support': support,
        'resistance': resistance,
        'rsi': rsi,
        'macd': macd,
        'ma20': ma20,
        'ma50': ma50,
        'ma200': ma200,
        'vwap': vwap,
        'upper_bb': upper,
        'lower_bb': lower,
        'volume_ratio': vol_ratio,
        'atr': atr,
        'reasons': reasons[:5],
        'time': datetime.now().strftime("%H:%M")
    }

# ============================================
# 📋 ۵. لیست ارزها
# ============================================

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

# ============================================
# 📡 ۶. ارسال به تلگرام (با تست)
# ============================================

def send_to_telegram(message):
    """ارسال پیام به کانال با نمایش خطا"""
    if not message:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': CHANNEL_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        r = requests.post(url, data=data, timeout=15)
        
        if r.status_code == 200:
            print("✅ Sent to Telegram")
            return True
        else:
            print(f"❌ Telegram Error: {r.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout: Check VPN/Internet")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def send_to_admin(message):
    """ارسال به ادمین"""
    if not ADMIN_ID or ADMIN_ID == "ایدی_تلگرامت":
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {'chat_id': ADMIN_ID, 'text': message, 'parse_mode': 'HTML'}
        r = requests.post(url, data=data, timeout=10)
        return r.status_code == 200
    except:
        return False

# ============================================
# 💬 ۷. ساخت پیام سیگنال
# ============================================

def build_message(signal, learner):
    if not signal or signal['signal'] == 'HOLD':
        return None
    
    emoji = "🟢" if signal['signal'] == 'BUY' else "🔴"
    direction = "🚀 LONG (خرید)" if signal['signal'] == 'BUY' else "💀 SHORT (فروش)"
    
    accuracy = learner.get_accuracy()
    
    msg = f"""
{emoji} <b>{signal['symbol']}</b>
⏰ {signal['time']}

📊 <b>{direction}</b>
💰 <b>ورود:</b> <code>${signal['price']:,.2f}</code>
🎯 <b>اطمینان:</b> <b>{signal['confidence']}%</b>
📈 <b>امتیاز:</b> {signal['score']}

━━━━━━━━━━━━━━━━━━━
🎯 <b>حد سود:</b> <code>${signal['tp']:,.2f}</code>
🛑 <b>حد ضرر:</b> <code>${signal['sl']:,.2f}</code>

━━━━━━━━━━━━━━━━━━━
📊 <b>حمایت:</b> <code>${signal['support']:,.2f}</code>
📊 <b>مقاومت:</b> <code>${signal['resistance']:,.2f}</code>

━━━━━━━━━━━━━━━━━━━
📊 <b>اندیکاتورها:</b>
• RSI: {signal['rsi']}
• MACD: {signal['macd']}
• VWAP: ${signal['vwap']:,.2f}
• MA20: ${signal['ma20']:,.2f}
• MA50: ${signal['ma50']:,.2f}

━━━━━━━━━━━━━━━━━━━
📝 <b>دلایل:</b>
"""
    
    for reason in signal['reasons'][:5]:
        msg += f"• {reason}\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━
🧠 <b>دقت یادگیری:</b> {accuracy}%
📊 <b>بازخورد:</b> {learner.positive}✅ / {learner.negative}❌

⚠️ <i>با مسئولیت خودت معامله کن!</i>
"""
    
    return msg

# ============================================
# 🔍 ۸. تست اتصال تلگرام
# ============================================

def test_connection():
    """تست اتصال به تلگرام"""
    print("\n" + "="*50)
    print("🔍 تست اتصال به تلگرام")
    print("="*50)
    
    # تست توکن
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('ok'):
                print(f"✅ توکن درست است! ربات: @{data['result']['username']}")
            else:
                print("❌ توکن اشتباه است!")
                return False
        else:
            print(f"❌ خطا: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False
    
    # تست ارسال به کانال
    try:
        test_msg = "✅ <b>ربات سیگنال روشن شد!</b>\n⏰ " + datetime.now().strftime("%H:%M:%S")
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {'chat_id': CHANNEL_ID, 'text': test_msg, 'parse_mode': 'HTML'}
        r = requests.post(url, data=data, timeout=10)
        
        if r.status_code == 200:
            print(f"✅ ارسال به کانال {CHANNEL_ID} موفق بود!")
            return True
        else:
            print(f"❌ ارسال به کانال失敗: {r.text}")
            print("\n💡 راه‌حل:")
            print("1. ربات را به کانال اضافه کن")
            print("2. ربات را ادمین کن")
            print("3. VPN را روشن کن")
            return False
    except Exception as e:
        print(f"❌ خطا: {e}")
        return False

# ============================================
# 🚀 ۹. حلقه اصلی
# ============================================

def main_loop():
    print("\n" + "="*60)
    print("🚀 RABAT SIGNAL BOT V5 - PROFESSIONAL")
    print("="*60)
    print(f"📢 Channel: {CHANNEL_ID}")
    print(f"📊 Symbols: {len(SYMBOLS)}")
    print(f"⏱ Interval: {INTERVAL//60} minutes")
    print("="*60)
    
    # تست اتصال
    if not test_connection():
        print("\n❌ اتصال به تلگرام برقرار نیست!")
        print("لطفاً تنظیمات را بررسی کن:")
        print(f"1. BOT_TOKEN: {BOT_TOKEN[:10]}...")
        print(f"2. CHANNEL_ID: {CHANNEL_ID}")
        print("3. ربات را به کانال اضافه کن")
        return
    
    learner = LearningSystem()
    cycle = 0
    
    print("\n✅ ربات روشن شد! منتظر سیگنال‌ها...\n")
    
    while True:
        try:
            cycle += 1
            print(f"\n🔄 Cycle {cycle} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"🧠 Accuracy: {learner.get_accuracy()}%")
            
            # پیدا کردن سیگنال‌ها
            signals = []
            for symbol in SYMBOLS:
                signal = generate_signal(symbol, learner)
                if signal and signal['signal'] != 'HOLD':
                    if signal['confidence'] >= MIN_CONFIDENCE:
                        signals.append(signal)
                        print(f"✅ {signal['symbol']}: {signal['signal']} ({signal['confidence']}%)")
                time.sleep(0.05)
            
            # مرتب‌سازی
            signals.sort(key=lambda x: x['confidence'], reverse=True)
            signals = signals[:MAX_SIGNALS]
            
            # ارسال به کانال
            if signals:
                for signal in signals:
                    msg = build_message(signal, learner)
                    if msg:
                        if send_to_telegram(msg):
                            print(f"✅ Sent: {signal['symbol']} - {signal['signal']}")
                        else:
                            print(f"❌ Failed to send: {signal['symbol']}")
                        time.sleep(1)
            else:
                print("⏳ No strong signals found")
                if cycle % 3 == 0:
                    send_to_telegram("⏳ هیچ سیگنال قوی در این دور پیدا نشد...")
            
            # منتظر ماندن
            print(f"⏱ Waiting {INTERVAL//60} min...")
            time.sleep(INTERVAL)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            send_to_admin(f"❌ Error in cycle {cycle}: {e}")
            time.sleep(60)

# ============================================
# 🏁 ۱۰. اجرا
# ============================================

if __name__ == "__main__":
    main_loop()