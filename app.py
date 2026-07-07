# ============================================
# PROFESSIONAL SIGNAL BOT V4 - WITH VWAP
# 7 Indicators: VWAP, RSI, MACD, MA, Bollinger, Volume, Support/Resistance
# ============================================

import requests
import numpy as np
import time
import json
import os
from datetime import datetime, timedelta
from collections import deque
import threading

# ============================================
# CONFIGURATION (Edit these)
# ============================================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Get from @BotFather
CHANNEL_ID = "@davnold"  # Your channel
ADMIN_ID = "YOUR_TELEGRAM_ID"  # Your Telegram ID

# Payment Settings
WALLET_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
WALLET_NETWORK = "TRC20"
SUBSCRIPTION_PRICE = "100 USDT"

# Signal Settings
SIGNAL_INTERVAL = 180  # 3 minutes
MIN_CONFIDENCE = 65
MAX_SIGNALS_PER_CYCLE = 2

# ============================================
# 1. GET REAL DATA FROM BINANCE
# ============================================

def get_price(symbol):
    """Get real price from Binance"""
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5)
        if r.status_code == 200:
            return float(r.json()['price'])
    except:
        pass
    return None

def get_candles(symbol, limit=300):
    """Get real candlestick data from Binance"""
    try:
        r = requests.get(
            f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit={limit}",
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            closes = [float(x[4]) for x in data]
            highs = [float(x[2]) for x in data]
            lows = [float(x[3]) for x in data]
            volumes = [float(x[5]) for x in data]
            opens = [float(x[1]) for x in data]
            return {
                'close': closes,
                'high': highs,
                'low': lows,
                'volume': volumes,
                'open': opens
            }
    except Exception as e:
        print(f"Error getting candles: {e}")
    return None

def get_24hr_stats(symbol):
    """Get 24h stats"""
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return {
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'volume': float(data['volume']),
                'change': float(data['priceChangePercent']),
                'open': float(data['openPrice'])
            }
    except:
        pass
    return None

# ============================================
# 2. VWAP - POWERFUL INDICATOR
# ============================================

def calculate_vwap(prices, volumes):
    """Volume Weighted Average Price - The Strongest Indicator"""
    if len(prices) < 2 or len(volumes) < 2:
        return prices[-1] if prices else 0
    
    total_value = 0
    total_volume = 0
    
    # Use all available data
    for i in range(len(prices)):
        total_value += prices[i] * volumes[i]
        total_volume += volumes[i]
    
    if total_volume == 0:
        return prices[-1]
    
    return round(total_value / total_volume, 2)

def calculate_vwap_multi_timeframe(prices, volumes):
    """VWAP on multiple timeframes"""
    vwaps = {}
    
    # 5-minute VWAP (current)
    if len(prices) >= 10:
        vwaps['current'] = calculate_vwap(prices[-10:], volumes[-10:])
    
    # 15-minute VWAP
    if len(prices) >= 30:
        vwaps['short'] = calculate_vwap(prices[-30:], volumes[-30:])
    
    # 1-hour VWAP
    if len(prices) >= 60:
        vwaps['medium'] = calculate_vwap(prices[-60:], volumes[-60:])
    
    # 4-hour VWAP
    if len(prices) >= 240:
        vwaps['long'] = calculate_vwap(prices[-240:], volumes[-240:])
    
    # Daily VWAP
    if len(prices) >= 288:
        vwaps['daily'] = calculate_vwap(prices[-288:], volumes[-288:])
    
    return vwaps

def analyze_vwap(prices, volumes, current_price):
    """Analyze VWAP for trading signals"""
    vwaps = calculate_vwap_multi_timeframe(prices, volumes)
    
    if not vwaps:
        return 0, "No VWAP data"
    
    current_vwap = vwaps.get('current', current_price)
    
    # Calculate distance from VWAP
    if current_vwap > 0:
        distance_pct = ((current_price - current_vwap) / current_vwap) * 100
    else:
        distance_pct = 0
    
    # Score based on VWAP
    score = 0
    reasons = []
    
    # Current VWAP (most important)
    if current_price > current_vwap:
        score += 15
        reasons.append(f"Price {distance_pct:.2f}% above VWAP (Bullish)")
    else:
        score -= 15
        reasons.append(f"Price {abs(distance_pct):.2f}% below VWAP (Bearish)")
    
    # Multiple timeframe VWAP confirmation
    bullish_vwaps = 0
    bearish_vwaps = 0
    
    for tf, vwap in vwaps.items():
        if tf == 'current':
            continue
        if current_price > vwap:
            bullish_vwaps += 1
        else:
            bearish_vwaps += 1
    
    # Extra score for multiple confirmations
    if bullish_vwaps >= 2:
        score += 10
        reasons.append(f"Bullish on {bullish_vwaps} timeframes")
    elif bearish_vwaps >= 2:
        score -= 10
        reasons.append(f"Bearish on {bearish_vwaps} timeframes")
    
    # Strong VWAP signals
    if distance_pct > 3:
        score += 10
        reasons.append(f"🔥 Strong breakout above VWAP (+{distance_pct:.2f}%)")
    elif distance_pct < -3:
        score -= 10
        reasons.append(f"🔥 Strong breakdown below VWAP ({distance_pct:.2f}%)")
    
    return score, reasons

# ============================================
# 3. SUPPORT & RESISTANCE
# ============================================

def find_support_resistance(prices, highs, lows):
    """Find real support and resistance levels"""
    if len(prices) < 20:
        return 0, 0
    
    peaks = []
    troughs = []
    
    # Find peaks and troughs
    for i in range(2, len(prices)-2):
        # Peak detection
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            if highs[i] > highs[i-2] and highs[i] > highs[i+2]:
                peaks.append(highs[i])
        
        # Trough detection
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            if lows[i] < lows[i-2] and lows[i] < lows[i+2]:
                troughs.append(lows[i])
    
    # Get major levels
    resistance = 0
    support = 0
    
    if peaks:
        peaks = sorted(peaks, reverse=True)
        resistance = peaks[0] if peaks else 0
        
        # Find strong resistance (clustered peaks)
        if len(peaks) >= 2:
            for i in range(1, min(5, len(peaks))):
                if abs(peaks[i] - peaks[0]) / peaks[0] < 0.02:
                    resistance = max(resistance, peaks[i])
    
    if troughs:
        troughs = sorted(troughs)
        support = troughs[0] if troughs else 0
        
        if len(troughs) >= 2:
            for i in range(1, min(5, len(troughs))):
                if abs(troughs[i] - troughs[0]) / troughs[0] < 0.02:
                    support = min(support, troughs[i])
    
    # Use 24h high/low as backup
    stats = get_24hr_stats("BTCUSDT")
    if stats:
        if resistance == 0 or resistance < stats['high']:
            resistance = stats['high']
        if support == 0 or support > stats['low']:
            support = stats['low']
    
    return round(support, 2), round(resistance, 2)

# ============================================
# 4. INDICATORS
# ============================================

def calculate_rsi(prices, period=14):
    """Real RSI"""
    if len(prices) < period + 1:
        return 50
    
    deltas = np.diff(prices[-period-1:])
    gain = np.mean(deltas[deltas > 0]) if np.sum(deltas > 0) > 0 else 0
    loss = -np.mean(deltas[deltas < 0]) if np.sum(deltas < 0) > 0 else 0.001
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 1)

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Real MACD with signal line"""
    if len(prices) < slow:
        return 0, 0, 0
    
    # Fast EMA
    fast_multiplier = 2 / (fast + 1)
    fast_ema = prices[-fast:].mean()
    for price in prices[-fast:]:
        fast_ema = price * fast_multiplier + fast_ema * (1 - fast_multiplier)
    
    # Slow EMA
    slow_multiplier = 2 / (slow + 1)
    slow_ema = prices[-slow:].mean()
    for price in prices[-slow:]:
        slow_ema = price * slow_multiplier + slow_ema * (1 - slow_multiplier)
    
    macd_line = fast_ema - slow_ema
    
    # Signal line (9-period EMA of MACD)
    signal_multiplier = 2 / (signal + 1)
    signal_line = macd_line
    for _ in range(signal):
        signal_line = macd_line * signal_multiplier + signal_line * (1 - signal_multiplier)
    
    histogram = macd_line - signal_line
    
    return round(macd_line, 4), round(signal_line, 4), round(histogram, 4)

def calculate_ma(prices, period):
    """Simple Moving Average"""
    if len(prices) < period:
        return prices[-1]
    return round(np.mean(prices[-period:]), 2)

def calculate_ema(prices, period):
    """Exponential Moving Average"""
    if len(prices) < period:
        return prices[-1]
    
    multiplier = 2 / (period + 1)
    ema = prices[-period:].mean()
    for price in prices[-period:]:
        ema = price * multiplier + ema * (1 - multiplier)
    return round(ema, 2)

def calculate_bollinger(prices, period=20, std_dev=2):
    """Bollinger Bands"""
    if len(prices) < period:
        return prices[-1], prices[-1], prices[-1]
    
    ma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    
    upper = ma + (std_dev * std)
    lower = ma - (std_dev * std)
    
    return round(upper, 2), round(ma, 2), round(lower, 2)

def calculate_atr(highs, lows, prices, period=14):
    """Average True Range"""
    if len(prices) < period:
        return 0.01
    
    tr = []
    for i in range(1, period + 1):
        if i < len(prices):
            tr.append(max(
                highs[-i] - lows[-i],
                abs(highs[-i] - prices[-i-1]),
                abs(lows[-i] - prices[-i-1])
            ))
    
    return round(np.mean(tr) if tr else 0.01, 2)

def calculate_volume_profile(volumes):
    """Volume analysis"""
    if len(volumes) < 20:
        return 1.0
    
    avg_vol = np.mean(volumes[-20:])
    current_vol = volumes[-1]
    
    return round(current_vol / avg_vol, 2)

def calculate_adx(prices, highs, lows, period=14):
    """Average Directional Index - Trend Strength"""
    if len(prices) < period + 1:
        return 25
    
    tr = []
    up = []
    down = []
    
    for i in range(1, period + 1):
        if i < len(prices):
            tr.append(max(
                highs[-i] - lows[-i],
                abs(highs[-i] - prices[-i-1]),
                abs(lows[-i] - prices[-i-1])
            ))
            up_move = highs[-i] - highs[-i-1]
            down_move = lows[-i-1] - lows[-i]
            up.append(max(0, up_move) if up_move > down_move else 0)
            down.append(max(0, down_move) if down_move > up_move else 0)
    
    atr = np.mean(tr) if tr else 0.01
    di_plus = 100 * np.mean(up) / atr if atr > 0 else 0
    di_minus = 100 * np.mean(down) / atr if atr > 0 else 0
    
    dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus) if (di_plus + di_minus) > 0 else 0
    
    return round(dx, 1)

# ============================================
# 5. AUTO LEARNING SYSTEM
# ============================================

class AutoLearner:
    """Learn from user feedback and market patterns"""
    
    def __init__(self):
        self.load_data()
        self.weights = {
            'vwap': 1.5,      # VWAP gets highest weight
            'rsi': 1.2,
            'macd': 1.2,
            'ma': 1.0,
            'bollinger': 1.0,
            'volume': 1.0,
            'support': 1.0,
            'adx': 0.8
        }
        self.patterns = deque(maxlen=1000)
        self.feedback_history = deque(maxlen=500)
        
    def load_data(self):
        """Load saved learning data"""
        if os.path.exists('learning_data_v4.json'):
            try:
                with open('learning_data_v4.json', 'r') as f:
                    data = json.load(f)
                    self.positive_feedback = data.get('positive', 0)
                    self.negative_feedback = data.get('negative', 0)
                    self.total_signals = data.get('total', 0)
                    if 'weights' in data:
                        self.weights.update(data['weights'])
                    return
            except:
                pass
        
        self.positive_feedback = 0
        self.negative_feedback = 0
        self.total_signals = 0
        self.save_data()
    
    def save_data(self):
        """Save learning data"""
        try:
            with open('learning_data_v4.json', 'w') as f:
                json.dump({
                    'positive': self.positive_feedback,
                    'negative': self.negative_feedback,
                    'total': self.total_signals,
                    'weights': self.weights
                }, f)
        except:
            pass
    
    def add_feedback(self, signal_id, feedback_type):
        """Record user feedback"""
        if feedback_type == 'positive':
            self.positive_feedback += 1
            # Increase weights on positive feedback
            for key in self.weights:
                self.weights[key] = min(2.0, self.weights[key] * 1.02)
        else:
            self.negative_feedback += 1
            # Decrease weights on negative feedback
            for key in self.weights:
                self.weights[key] = max(0.3, self.weights[key] * 0.98)
        
        self.total_signals += 1
        self.save_data()
    
    def get_accuracy(self):
        """Calculate accuracy from feedback"""
        total = self.positive_feedback + self.negative_feedback
        if total == 0:
            return 50.0
        return round((self.positive_feedback / total) * 100, 1)
    
    def adjust_signal(self, score, signal):
        """Adjust signal confidence based on learning"""
        accuracy = self.get_accuracy()
        
        if accuracy > 75:
            score = min(97, score * 1.12)
        elif accuracy > 65:
            score = min(95, score * 1.08)
        elif accuracy < 35:
            score = max(25, score * 0.85)
        elif accuracy < 45:
            score = max(30, score * 0.92)
        
        return round(score, 1)

# ============================================
# 6. SIGNAL GENERATOR - COMPLETE
# ============================================

def generate_signal(symbol, learner):
    """Generate complete signal with all 7 indicators"""
    data = get_candles(symbol, 300)
    if not data:
        return None
    
    prices = data['close']
    highs = data['high']
    lows = data['low']
    volumes = data['volume']
    opens = data['open']
    current_price = prices[-1]
    
    # Get support and resistance
    support, resistance = find_support_resistance(prices, highs, lows)
    
    # ========== CALCULATE ALL INDICATORS ==========
    
    # 1. VWAP (Strongest)
    vwap_score, vwap_reasons = analyze_vwap(prices, volumes, current_price)
    
    # 2. RSI
    rsi = calculate_rsi(prices, 14)
    rsi_score = 0
    rsi_reasons = []
    
    if rsi < 25:
        rsi_score = 25
        rsi_reasons.append(f"🔥 RSI oversold: {rsi}")
    elif rsi < 35:
        rsi_score = 15
        rsi_reasons.append(f"📈 RSI near oversold: {rsi}")
    elif rsi > 75:
        rsi_score = -25
        rsi_reasons.append(f"🔥 RSI overbought: {rsi}")
    elif rsi > 65:
        rsi_score = -15
        rsi_reasons.append(f"📉 RSI near overbought: {rsi}")
    
    # 3. MACD
    macd_line, signal_line, histogram = calculate_macd(prices, 12, 26, 9)
    macd_score = 0
    macd_reasons = []
    
    if macd_line > signal_line:
        if histogram > 0:
            macd_score = 20
            macd_reasons.append(f"🟢 MACD bullish (Hist: {histogram:.4f})")
        else:
            macd_score = 10
            macd_reasons.append(f"🟢 MACD positive but weakening")
    else:
        if histogram < 0:
            macd_score = -20
            macd_reasons.append(f"🔴 MACD bearish (Hist: {histogram:.4f})")
        else:
            macd_score = -10
            macd_reasons.append(f"🔴 MACD negative but improving")
    
    # 4. Moving Averages
    ma20 = calculate_ma(prices, 20)
    ma50 = calculate_ma(prices, 50)
    ma200 = calculate_ma(prices, 200)
    ema20 = calculate_ema(prices, 20)
    ma_score = 0
    ma_reasons = []
    
    if current_price > ma20 and ma20 > ma50 and ma50 > ma200:
        ma_score = 20
        ma_reasons.append("🚀 Strong uptrend (MA20>MA50>MA200)")
    elif current_price < ma20 and ma20 < ma50 and ma50 < ma200:
        ma_score = -20
        ma_reasons.append("💀 Strong downtrend (MA20<MA50<MA200)")
    elif current_price > ma20 and ma20 > ma50:
        ma_score = 12
        ma_reasons.append("📈 Uptrend (MA20>MA50)")
    elif current_price < ma20 and ma20 < ma50:
        ma_score = -12
        ma_reasons.append("📉 Downtrend (MA20<MA50)")
    elif current_price > ma20:
        ma_score = 5
        ma_reasons.append("⬆️ Price above MA20")
    elif current_price < ma20:
        ma_score = -5
        ma_reasons.append("⬇️ Price below MA20")
    
    # 5. Bollinger Bands
    upper, middle, lower = calculate_bollinger(prices, 20, 2)
    bollinger_score = 0
    bollinger_reasons = []
    
    if current_price < lower:
        bollinger_score = 15
        bollinger_reasons.append(f"🎯 Touch lower band: ${lower:,.2f}")
    elif current_price > upper:
        bollinger_score = -15
        bollinger_reasons.append(f"🎯 Touch upper band: ${upper:,.2f}")
    elif current_price < middle:
        bollinger_score = 8
        bollinger_reasons.append("📊 Lower half of bands")
    elif current_price > middle:
        bollinger_score = -8
        bollinger_reasons.append("📊 Upper half of bands")
    
    # 6. Volume
    volume_ratio = calculate_volume_profile(volumes)
    volume_score = 0
    volume_reasons = []
    
    if volume_ratio > 2.0:
        volume_score = 10
        volume_reasons.append(f"📊 High volume: {volume_ratio}x avg")
    elif volume_ratio > 1.5:
        volume_score = 5
        volume_reasons.append(f"📊 Good volume: {volume_ratio}x avg")
    elif volume_ratio < 0.5:
        volume_score = -10
        volume_reasons.append(f"📊 Low volume: {volume_ratio}x avg")
    
    # 7. Support/Resistance
    support_score = 0
    support_reasons = []
    
    if support > 0:
        distance_to_support = ((current_price - support) / current_price) * 100
        if distance_to_support < 0.5:
            support_score = 12
            support_reasons.append(f"🛡️ Very near support: ${support:,.2f}")
        elif distance_to_support < 1.0:
            support_score = 8
            support_reasons.append(f"🛡️ Near support: ${support:,.2f}")
        elif distance_to_support < 2.0:
            support_score = 4
            support_reasons.append(f"🛡️ Close to support: ${support:,.2f}")
    
    if resistance > 0:
        distance_to_resistance = ((resistance - current_price) / current_price) * 100
        if distance_to_resistance < 0.5:
            support_score = -12
            support_reasons.append(f"🚫 Very near resistance: ${resistance:,.2f}")
        elif distance_to_resistance < 1.0:
            support_score = -8
            support_reasons.append(f"🚫 Near resistance: ${resistance:,.2f}")
        elif distance_to_resistance < 2.0:
            support_score = -4
            support_reasons.append(f"🚫 Close to resistance: ${resistance:,.2f}")
    
    # 8. ADX (Trend Strength)
    adx = calculate_adx(prices, highs, lows, 14)
    adx_score = 0
    adx_reasons = []
    
    if adx > 50:
        adx_score = 10 if vwap_score > 0 else -10
        adx_reasons.append(f"🔥 Strong trend (ADX: {adx})")
    elif adx > 35:
        adx_score = 5 if vwap_score > 0 else -5
        adx_reasons.append(f"📊 Moderate trend (ADX: {adx})")
    elif adx < 20:
        adx_reasons.append(f"⏳ Weak trend (ADX: {adx}) - Wait")
    
    # ========== CALCULATE TOTAL SCORE ==========
    
    # Apply weights from learning
    total_score = (
        vwap_score * learner.weights['vwap'] +
        rsi_score * learner.weights['rsi'] +
        macd_score * learner.weights['macd'] +
        ma_score * learner.weights['ma'] +
        bollinger_score * learner.weights['bollinger'] +
        volume_score * learner.weights['volume'] +
        support_score * learner.weights['support'] +
        adx_score * learner.weights.get('adx', 0.8)
    )
    
    # ========== DETERMINE SIGNAL ==========
    
    # Adjust score
    if len(prices) > 50:
        recent_change = ((prices[-1] - prices[-50]) / prices[-50]) * 100
        if recent_change > 5 and total_score > 0:
            total_score += 8
        elif recent_change < -5 and total_score < 0:
            total_score -= 8
    
    # Confidence
    confidence = 50 + abs(total_score) / 1.5
    confidence = min(97, max(30, confidence))
    
    # Signal
    if total_score > 30 and confidence >= MIN_CONFIDENCE:
        signal = "BUY"
    elif total_score < -30 and confidence >= MIN_CONFIDENCE:
        signal = "SELL"
    else:
        signal = "HOLD"
    
    # Apply learning
    confidence = learner.adjust_signal(confidence, signal)
    
    # ========== CALCULATE TP AND SL ==========
    
    fee_rate = 0.001  # 0.1% fee
    
    if signal == "BUY":
        # TP: 2.5% to 5% above entry
        tp_multiplier = 1.025 + (abs(total_score) / 2000)  # 2.5% to 5%
        tp_price = current_price * tp_multiplier
        
        # SL: 1.5% to 3% below entry
        sl_multiplier = 1 - (0.015 + (abs(total_score) / 3000))
        sl_price = current_price * sl_multiplier
        
        # Adjust based on support/resistance
        if support > 0 and sl_price < support:
            sl_price = support * 0.995
        
        if resistance > 0 and tp_price > resistance:
            tp_price = resistance * 0.995
        
        # Make sure profit > fees
        if (tp_price - current_price) < (current_price * fee_rate * 3):
            tp_price = current_price * 1.015
        
    elif signal == "SELL":
        # TP: 2.5% to 5% below entry
        tp_multiplier = 1 - (0.025 + (abs(total_score) / 2000))
        tp_price = current_price * tp_multiplier
        
        # SL: 1.5% to 3% above entry
        sl_multiplier = 1 + (0.015 + (abs(total_score) / 3000))
        sl_price = current_price * sl_multiplier
        
        # Adjust based on support/resistance
        if resistance > 0 and sl_price > resistance:
            sl_price = resistance * 1.005
        
        if support > 0 and tp_price < support:
            tp_price = support * 1.005
        
        # Make sure profit > fees
        if (current_price - tp_price) < (current_price * fee_rate * 3):
            tp_price = current_price * 0.985
    
    else:
        tp_price = current_price
        sl_price = current_price
    
    # Calculate profit percentages
    if signal == "BUY":
        profit_pct = round(((tp_price - current_price) / current_price) * 100, 2)
        loss_pct = round(((sl_price - current_price) / current_price) * 100, 2)
    elif signal == "SELL":
        profit_pct = round(((current_price - tp_price) / current_price) * 100, 2)
        loss_pct = round(((current_price - sl_price) / current_price) * 100, 2)
    else:
        profit_pct = 0
        loss_pct = 0
    
    # ========== COLLECT ALL REASONS ==========
    
    all_reasons = []
    all_reasons.extend(vwap_reasons[:2])
    all_reasons.extend(rsi_reasons[:1])
    all_reasons.extend(macd_reasons[:1])
    all_reasons.extend(ma_reasons[:1])
    all_reasons.extend(bollinger_reasons[:1])
    all_reasons.extend(volume_reasons[:1])
    all_reasons.extend(support_reasons[:1])
    all_reasons.extend(adx_reasons[:1])
    
    # Remove duplicates
    unique_reasons = []
    for reason in all_reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)
    
    # ========== RETURN SIGNAL ==========
    
    return {
        'symbol': symbol,
        'price': current_price,
        'signal': signal,
        'confidence': round(confidence, 1),
        'score': round(total_score, 1),
        'support': support,
        'resistance': resistance,
        'tp': round(tp_price, 2),
        'sl': round(sl_price, 2),
        'profit_pct': profit_pct,
        'loss_pct': loss_pct,
        'rsi': rsi,
        'macd': macd_line,
        'macd_signal': signal_line,
        'macd_hist': histogram,
        'ma20': ma20,
        'ma50': ma50,
        'ma200': ma200,
        'ema20': ema20,
        'upper_bb': upper,
        'middle_bb': middle,
        'lower_bb': lower,
        'volume_ratio': volume_ratio,
        'atr': calculate_atr(highs, lows, prices, 14),
        'vwap': calculate_vwap(prices, volumes),
        'adx': adx,
        'reasons': unique_reasons[:6],
        'vwap_reasons': vwap_reasons,
        'time': datetime.now().strftime("%H:%M"),
        'timestamp': datetime.now().isoformat()
    }

# ============================================
# 7. BOT STATE MANAGEMENT
# ============================================

class BotState:
    """Admin panel state management"""
    
    def __init__(self):
        self.load_state()
    
    def load_state(self):
        """Load bot state"""
        if os.path.exists('bot_state_v4.json'):
            try:
                with open('bot_state_v4.json', 'r') as f:
                    data = json.load(f)
                    self.signal_enabled = data.get('signal_enabled', True)
                    self.payment_enabled = data.get('payment_enabled', True)
                    self.wallet_address = data.get('wallet_address', WALLET_ADDRESS)
                    self.price = data.get('price', SUBSCRIPTION_PRICE)
                    self.total_signals_sent = data.get('total_signals_sent', 0)
                    return
            except:
                pass
        
        self.signal_enabled = True
        self.payment_enabled = True
        self.wallet_address = WALLET_ADDRESS
        self.price = SUBSCRIPTION_PRICE
        self.total_signals_sent = 0
        self.save_state()
    
    def save_state(self):
        """Save bot state"""
        try:
            with open('bot_state_v4.json', 'w') as f:
                json.dump({
                    'signal_enabled': self.signal_enabled,
                    'payment_enabled': self.payment_enabled,
                    'wallet_address': self.wallet_address,
                    'price': self.price,
                    'total_signals_sent': self.total_signals_sent
                }, f)
        except:
            pass
    
    def toggle_signals(self):
        """Enable/disable signal sending"""
        self.signal_enabled = not self.signal_enabled
        self.save_state()
        return self.signal_enabled
    
    def update_wallet(self, address):
        """Update wallet address"""
        self.wallet_address = address
        self.save_state()
        return self.wallet_address
    
    def update_price(self, price):
        """Update subscription price"""
        self.price = price
        self.save_state()
        return self.price

# ============================================
# 8. SYMBOLS LIST
# ============================================

SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT', 'DOTUSDT',
    'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'BCHUSDT',
    'NEARUSDT', 'ALGOUSDT', 'VETUSDT', 'ICPUSDT', 'FILUSDT',
    'FTMUSDT', 'XLMUSDT', 'EGLDUSDT', 'HNTUSDT', 'XMRUSDT',
    'ZECUSDT', 'DASHUSDT', 'ETCUSDT', 'XTZUSDT', 'EOSUSDT',
    'AAVEUSDT', 'MKRUSDT', 'COMPUSDT', 'YFIUSDT', 'SUSHIUSDT',
    'CAKEUSDT', 'AXSUSDT', 'SANDUSDT', 'APEUSDT', 'CRVUSDT',
    'RUNEUSDT', 'FLOWUSDT', 'QNTUSDT', 'SNXUSDT', 'GRTUSDT',
    'LDOUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SEIUSDT'
]

def find_best_signals(learner, state, count=2):
    """Find best signals from all symbols"""
    results = []
    
    print(f"Scanning {len(SYMBOLS)} symbols...")
    
    for symbol in SYMBOLS:
        result = generate_signal(symbol, learner)
        if result and result['signal'] != 'HOLD':
            if result['confidence'] >= MIN_CONFIDENCE:
                results.append(result)
                print(f"✅ Found signal: {symbol} - {result['signal']} ({result['confidence']}%)")
        time.sleep(0.03)
    
    # Sort by confidence
    results.sort(key=lambda x: x['confidence'], reverse=True)
    
    if len(results) > count:
        results = results[:count]
    
    state.total_signals_sent += len(results)
    state.save_state()
    
    return results

# ============================================
# 9. TELEGRAM MESSAGE BUILDER
# ============================================

def build_signal_message(result, learner, state):
    """Build professional signal message with all details"""
    if not result:
        return ""
    
    # Signal emoji
    if result['signal'] == 'BUY':
        emoji = "🟢"
        signal_text = "🚀 LONG"
    elif result['signal'] == 'SELL':
        emoji = "🔴"
        signal_text = "💀 SHORT"
    else:
        emoji = "⚪"
        signal_text = "⏳ HOLD"
    
    # Get accuracy
    accuracy = learner.get_accuracy()
    
    # Build message
    msg = f"""
{emoji} <b>SIGNAL - {result['symbol']}</b>
⏰ Time: {result['time']}

📊 <b>Direction:</b> {signal_text}
💰 <b>Entry Price:</b> <code>${result['price']:,.2f}</code>
🎯 <b>Confidence:</b> <b>{result['confidence']}%</b>
📈 <b>Score:</b> {result['score']}/100

━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 <b>TARGETS:</b>
✅ <b>Take Profit:</b> <code>${result['tp']:,.2f}</code>
🛑 <b>Stop Loss:</b> <code>${result['sl']:,.2f}</code>

📊 <b>Profit/Loss:</b>
• Profit: <b>+{result['profit_pct']}%</b>
• Loss: <b>{result['loss_pct']}%</b>

━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>KEY LEVELS:</b>
🛡️ Support: <code>${result['support']:,.2f}</code>
🚫 Resistance: <code>${result['resistance']:,.2f}</code>

━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>INDICATORS (7):</b>
• VWAP: <code>${result['vwap']:,.2f}</code> ⭐ (Strongest)
• RSI: {result['rsi']}
• MACD: {result['macd']} (Signal: {result['macd_signal']})
• MA20: ${result['ma20']:,.2f}
• MA50: ${result['ma50']:,.2f}
• MA200: ${result['ma200']:,.2f}
• ADX: {result['adx']} (Trend Strength)

━━━━━━━━━━━━━━━━━━━━━━━━━
📝 <b>REASONS:</b>
"""
    
    for reason in result['reasons'][:6]:
        msg += f"• {reason}\n"
    
    if result.get('vwap_reasons'):
        for reason in result['vwap_reasons'][:2]:
            msg += f"• {reason}\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 <b>LEARNING SYSTEM:</b>
• Accuracy: {accuracy}%
• Feedback: {learner.positive_feedback}✅ / {learner.negative_feedback}❌
• Signals Today: {state.total_signals_sent}

📊 <b>BOT INFO:</b>
• Version: V4 (With VWAP)
• Indicators: 7
• Symbols: {len(SYMBOLS)}
• Interval: {SIGNAL_INTERVAL//60}m

⚠️ <i>Trade at your own risk! Always use stop loss!</i>
    """
    
    return msg

def send_to_telegram(message):
    """Send message to Telegram channel"""
    if not message:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': CHANNEL_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        r = requests.post(url, data=data, timeout=5)
        return r.status_code == 200
    except:
        return False

def send_to_admin(message):
    """Send message to admin"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': ADMIN_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        r = requests.post(url, data=data, timeout=5)
        return r.status_code == 200
    except:
        return False

# ============================================
# 10. MAIN SIGNAL LOOP
# ============================================

def signal_loop():
    """Main signal loop - runs every 3 minutes"""
    learner = AutoLearner()
    state = BotState()
    
    print("="*80)
    print("🚀 PROFESSIONAL SIGNAL BOT V4 - WITH VWAP")
    print("="*80)
    print(f"📢 Channel: {CHANNEL_ID}")
    print(f"👤 Admin: {ADMIN_ID}")
    print(f"⏱ Interval: {SIGNAL_INTERVAL//60} minutes")
    print(f"📊 Total Symbols: {len(SYMBOLS)}")
    print(f"📊 Indicators: 7 (VWAP, RSI, MACD, MA, Bollinger, Volume, S/R)")
    print(f"🧠 Learning Accuracy: {learner.get_accuracy()}%")
    print(f"💳 Wallet: {state.wallet_address}")
    print(f"💰 Price: {state.price}")
    print(f"📡 Signal Sending: {'ACTIVE' if state.signal_enabled else 'PAUSED'}")
    print("="*80)
    
    cycle = 0
    
    while True:
        try:
            cycle += 1
            
            if not state.signal_enabled:
                print(f"⏸️ Cycle {cycle}: Signal sending paused")
                send_to_admin(f"⏸️ Cycle {cycle}: Signal sending paused")
                time.sleep(SIGNAL_INTERVAL)
                continue
            
            print(f"\n🔄 Cycle {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print("⏳ Scanning all symbols with VWAP...")
            
            best_signals = find_best_signals(learner, state, MAX_SIGNALS_PER_CYCLE)
            
            if best_signals:
                for i, signal in enumerate(best_signals):
                    msg = build_signal_message(signal, learner, state)
                    if send_to_telegram(msg):
                        print(f"✅ Signal {i+1}: {signal['symbol']} - {signal['signal']} ({signal['confidence']}%)")
                    else:
                        print(f"❌ Failed to send signal {i+1}")
                    time.sleep(1)
                
                # Summary to admin
                summary = f"""
📊 <b>Cycle {cycle} Summary</b>

✅ <b>Signals Sent:</b> {len(best_signals)}
📈 <b>Best Signal:</b> {best_signals[0]['symbol']} ({best_signals[0]['confidence']}%)
📊 <b>VWAP:</b> ${best_signals[0].get('vwap', 0):,.2f}
🧠 <b>Accuracy:</b> {learner.get_accuracy()}%
📊 <b>Total Today:</b> {state.total_signals_sent}
    """
                send_to_admin(summary)
            else:
                print("⏳ No strong signals found this cycle")
                # Send fewer messages to avoid spam
                if cycle % 3 == 0:
                    send_to_telegram(f"⏳ No strong signals found in cycle {cycle}. Waiting...")
            
            print(f"⏱ Waiting {SIGNAL_INTERVAL//60} minutes for next cycle...")
            time.sleep(SIGNAL_INTERVAL)
            
        except Exception as e:
            error_msg = f"❌ Error in cycle {cycle}: {str(e)}"
            print(error_msg)
            send_to_admin(error_msg)
            time.sleep(60)

# ============================================
# 11. START
# ============================================

def main():
    """Start the bot"""
    print("\n" + "="*80)
    print("🚀 PROFESSIONAL SIGNAL BOT V4 - WITH VWAP")
    print("="*80)
    print("Checking configuration...")
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set BOT_TOKEN in the code!")
        print("Get token from @BotFather on Telegram")
        return
    
    if CHANNEL_ID == "@davnold":
        print("⚠️ WARNING: Using default channel ID")
        print("Change CHANNEL_ID to your channel")
    
    if ADMIN_ID == "YOUR_TELEGRAM_ID":
        print("⚠️ WARNING: Using default admin ID")
        print("Change ADMIN_ID to your Telegram ID")
    
    print("\n✅ Configuration loaded")
    print("🚀 Starting bot...")
    print("📊 Using 7 indicators with VWAP")
    print("="*80 + "\n")
    
    signal_loop()

if __name__ == "__main__":
    main()