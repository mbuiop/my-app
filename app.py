#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================
🤖 AUTONOMOUS SIGNAL BOT V17 - FULLY AUTOMATIC
====================================================================
✅ اسکن خودکار بازار هر ۳ دقیقه
✅ شناسایی خودکار ارزهای مستعد پامپ
✅ شناسایی خودکار ارزهای مستعد دامپ (شورت)
✅ ارسال خودکار سیگنال به کانال @davnold
✅ یادگیری از بازخورد (بدون دکمه - از طریق پیام)
✅ بدون نیاز به هیچ دکمه یا ورودی کاربر
====================================================================
"""

import logging
import os
import sys
import time
import json
import sqlite3
import threading
import warnings
import pickle
import math
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings('ignore')

# ==================== PID ====================
PID_FILE = "bot_v17.pid"

def check_and_create_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            try:
                os.kill(old_pid, 9)
                time.sleep(1)
                os.remove(PID_FILE)
            except:
                pass
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        return True
    except:
        return True

def remove_pid():
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except:
        pass

# ==================== Libraries ====================
import requests
import numpy as np
from scipy.stats import skew, kurtosis, entropy, linregress
from scipy.fft import fft

# ==================== Machine Learning ====================
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except:
    XGB_AVAILABLE = False

# ==================== Settings ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('bot_v17.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8710979491:AAF3YwifUyipir7TkOnYOcsWpbB0QFojkw0"
CHANNEL_ID = "@davnold"  # کانال شما
ADMIN_ID = 327855654
SCAN_INTERVAL = 180  # ۳ دقیقه
MIN_VOLUME_USDT = 300000
MAX_SYMBOLS_TO_SCAN = 40
MIN_PREDICTION_CONFIDENCE = 55
MIN_FEEDBACK_FOR_RETRAIN = 3

# ==================== Database ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_v17.db', check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.cursor = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                direction TEXT,
                entry REAL,
                tp REAL,
                sl REAL,
                support REAL,
                resistance REAL,
                leverage INTEGER,
                confidence INTEGER,
                created_at TIMESTAMP,
                model_votes TEXT DEFAULT '',
                signal_accuracy REAL DEFAULT 0,
                feedback TEXT DEFAULT '',
                features_snapshot TEXT DEFAULT '',
                signal_type TEXT DEFAULT 'NORMAL',
                sent_to_channel BOOLEAN DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        ''')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("last_scan", "")')
        self.cursor.execute('INSERT OR IGNORE INTO settings VALUES ("signal_count", "0")')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                feedback TEXT,
                created_at TIMESTAMP,
                symbol TEXT,
                direction TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                features TEXT,
                label INTEGER,
                source TEXT DEFAULT 'historical',
                timestamp TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                accuracy REAL,
                samples INTEGER,
                created_at TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dynamic_symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE,
                pump_score INTEGER DEFAULT 0,
                dump_score INTEGER DEFAULT 0,
                volume REAL DEFAULT 0,
                change_24h REAL DEFAULT 0,
                last_seen TIMESTAMP,
                signal_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()
    
    def get_setting(self, key):
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        r = self.cursor.fetchone()
        return r[0] if r else None
    
    def update_setting(self, key, value):
        self.cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
        self.conn.commit()
    
    def save_signal(self, data, features=None):
        features_json = json.dumps(features) if features else ''
        self.cursor.execute('''
            INSERT INTO signals (
                symbol, direction, entry, tp, sl, support, resistance,
                leverage, confidence, created_at, model_votes,
                signal_accuracy, features_snapshot, signal_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['symbol'], data['direction'], data['entry'], data['tp'], data['sl'],
            data.get('support', 0), data.get('resistance', 0),
            data['leverage'], data['confidence'], datetime.now().isoformat(),
            data.get('model_votes', ''), data.get('signal_accuracy', 0),
            features_json, data.get('signal_type', 'NORMAL')
        ))
        signal_id = self.cursor.lastrowid
        self.conn.commit()
        return signal_id
    
    def mark_signal_sent(self, signal_id):
        self.cursor.execute('UPDATE signals SET sent_to_channel = 1 WHERE id = ?', (signal_id,))
        self.conn.commit()
    
    def is_signal_sent(self, signal_id):
        self.cursor.execute('SELECT sent_to_channel FROM signals WHERE id = ?', (signal_id,))
        r = self.cursor.fetchone()
        return r and r[0] == 1
    
    def get_unsent_signals(self):
        self.cursor.execute('''
            SELECT id, symbol, direction, entry, tp, sl, confidence, signal_type
            FROM signals WHERE sent_to_channel = 0
            ORDER BY created_at DESC LIMIT 10
        ''')
        return self.cursor.fetchall()
    
    def update_signal_feedback(self, signal_id, feedback):
        self.cursor.execute('''
            UPDATE signals SET feedback = ? WHERE id = ?
        ''', (feedback, signal_id))
        self.conn.commit()
        
        self.cursor.execute('SELECT symbol, direction FROM signals WHERE id = ?', (signal_id,))
        result = self.cursor.fetchone()
        if result:
            symbol, direction = result
            self.cursor.execute('''
                INSERT INTO feedback_log (signal_id, feedback, created_at, symbol, direction)
                VALUES (?, ?, ?, ?, ?)
            ''', (signal_id, feedback, datetime.now().isoformat(), symbol, direction))
            self.conn.commit()
            
            if feedback == 'positive':
                self.cursor.execute('''
                    UPDATE dynamic_symbols SET success_count = success_count + 1
                    WHERE symbol = ?
                ''', (symbol,))
            self.conn.commit()
    
    def get_recent_signals(self, hours=24):
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        self.cursor.execute('''
            SELECT symbol, direction, confidence, signal_type, created_at
            FROM signals WHERE created_at > ?
            ORDER BY created_at DESC
        ''', (cutoff,))
        return self.cursor.fetchall()
    
    def get_feedback_training_data(self, limit=500):
        self.cursor.execute('''
            SELECT features_snapshot, feedback
            FROM signals 
            WHERE features_snapshot IS NOT NULL AND features_snapshot != '' AND feedback != ''
            ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def save_training_data(self, symbol, features, label, source='historical'):
        self.cursor.execute('''
            INSERT INTO training_data (symbol, features, label, source, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, json.dumps(features), label, source, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_training_data(self, limit=10000):
        self.cursor.execute('''
            SELECT features, label FROM training_data ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        return self.cursor.fetchall()
    
    def save_model_performance(self, accuracy, samples):
        self.cursor.execute('''
            INSERT INTO model_performance (date, accuracy, samples, created_at)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().date().isoformat(), accuracy, samples, datetime.now().isoformat()))
        self.conn.commit()
    
    def update_dynamic_symbol(self, symbol, pump_score=0, dump_score=0, volume=0, change_24h=0):
        self.cursor.execute('''
            INSERT OR REPLACE INTO dynamic_symbols 
            (symbol, pump_score, dump_score, volume, change_24h, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, pump_score, dump_score, volume, change_24h, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_hot_symbols(self, limit=30):
        self.cursor.execute('''
            SELECT symbol FROM dynamic_symbols 
            ORDER BY (pump_score * 2 + success_count) DESC
            LIMIT ?
        ''', (limit,))
        return [r[0] for r in self.cursor.fetchall()]
    
    def get_performance_stats(self):
        total = self.cursor.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        positive = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE feedback = "positive"').fetchone()[0]
        negative = self.cursor.execute('SELECT COUNT(*) FROM signals WHERE feedback = "negative"').fetchone()[0]
        return total, positive, negative

db = Database()

# ==================== Price Service ====================
class PriceService:
    def __init__(self):
        self.binance = "https://api.binance.com/api/v3"
        self.cache = {}
    
    def get_candles(self, symbol, interval='5m', limit=200):
        cache_key = f"{symbol}_{interval}_{limit}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            r = requests.get(
                f"{self.binance}/klines",
                params={'symbol': symbol, 'interval': interval, 'limit': limit},
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                candles = []
                for c in data:
                    candles.append({
                        'open': float(c[1]), 'high': float(c[2]),
                        'low': float(c[3]), 'close': float(c[4]),
                        'volume': float(c[5]), 'timestamp': datetime.fromtimestamp(c[0]/1000)
                    })
                self.cache[cache_key] = candles
                return candles
        except Exception as e:
            logger.error(f"Error getting candles for {symbol}: {e}")
        return None
    
    def get_historical_candles(self, symbol, start_date, end_date, interval='1h'):
        try:
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
            all_candles = []
            
            while start_ts < end_ts:
                r = requests.get(
                    f"{self.binance}/klines",
                    params={
                        'symbol': symbol,
                        'interval': interval,
                        'startTime': start_ts,
                        'limit': 1000
                    },
                    timeout=10
                )
                if r.status_code == 200:
                    data = r.json()
                    if not data:
                        break
                    for c in data:
                        ts = c[0]
                        if ts > end_ts:
                            break
                        all_candles.append({
                            'open': float(c[1]), 'high': float(c[2]),
                            'low': float(c[3]), 'close': float(c[4]),
                            'volume': float(c[5]), 'timestamp': datetime.fromtimestamp(ts/1000)
                        })
                    start_ts = data[-1][0] + 1
                    time.sleep(0.1)
                else:
                    break
            return all_candles
        except:
            return []

price_service = PriceService()

# ==================== Dynamic Symbol Scanner ====================
class DynamicSymbolScanner:
    def __init__(self):
        self.binance = "https://api.binance.com/api/v3"
        self.pump_candidates = []
        self.dump_candidates = []
        self.hot_symbols = []
        
    def get_all_tickers(self):
        try:
            r = requests.get(f"{self.binance}/ticker/24hr", timeout=10)
            if r.status_code == 200:
                data = r.json()
                tickers = []
                for item in data:
                    symbol = item['symbol']
                    if symbol.endswith('USDT') and not any(x in symbol for x in ['UP', 'DOWN', 'BUSD', 'FDUSD']):
                        try:
                            vol = float(item['quoteVolume'])
                            price = float(item['lastPrice'])
                            change = float(item['priceChangePercent'])
                            if vol > MIN_VOLUME_USDT and price > 0.00001:
                                tickers.append({
                                    'symbol': symbol,
                                    'price': price,
                                    'volume': vol,
                                    'change_24h': change,
                                    'high': float(item['highPrice']),
                                    'low': float(item['lowPrice']),
                                    'bid': float(item['bidPrice']),
                                    'ask': float(item['askPrice']),
                                    'trades': int(item['count'])
                                })
                        except:
                            continue
                return tickers
        except Exception as e:
            logger.error(f"Error getting tickers: {e}")
        return []
    
    def scan(self):
        tickers = self.get_all_tickers()
        if not tickers:
            return [], [], []
        
        pump = []
        dump = []
        
        for t in tickers:
            # امتیاز پامپ
            pump_score = 0
            if 1.5 < t['change_24h'] < 15:
                pump_score += 5
            if t['volume'] > 5_000_000:
                pump_score += 3
            if t['trades'] > 10000:
                pump_score += 2
            if 0.01 < t['price'] < 50:
                pump_score += 2
            range_pct = ((t['high'] - t['low']) / (t['low'] + 0.0001)) * 100
            if range_pct > 8:
                pump_score += 2
            dist_from_low = ((t['price'] - t['low']) / (t['low'] + 0.0001)) * 100
            if dist_from_low < 10:
                pump_score += 2
            
            # امتیاز دامپ
            dump_score = 0
            if t['change_24h'] > 20:
                dump_score += 6
            elif t['change_24h'] > 10:
                dump_score += 3
            if t['volume'] > 8_000_000 and t['change_24h'] > 10:
                dump_score += 4
            dist_from_high = ((t['high'] - t['price']) / (t['high'] + 0.0001)) * 100
            if dist_from_high < 3 and t['change_24h'] > 5:
                dump_score += 4
            spread = ((t['ask'] - t['bid']) / (t['bid'] + 0.0001)) * 100
            if spread > 0.2:
                dump_score += 2
            
            if pump_score >= 8:
                pump.append({**t, 'pump_score': pump_score})
            if dump_score >= 6:
                dump.append({**t, 'dump_score': dump_score})
            
            # ذخیره در دیتابیس
            if pump_score >= 5 or dump_score >= 5:
                db.update_dynamic_symbol(t['symbol'], pump_score, dump_score, t['volume'], t['change_24h'])
        
        pump.sort(key=lambda x: x['pump_score'], reverse=True)
        dump.sort(key=lambda x: x['dump_score'], reverse=True)
        
        self.pump_candidates = [p['symbol'] for p in pump[:15]]
        self.dump_candidates = [d['symbol'] for d in dump[:12]]
        
        # ترکیب
        hot = []
        for p in pump[:12]:
            if p['symbol'] not in hot:
                hot.append(p['symbol'])
        for d in dump[:8]:
            if d['symbol'] not in hot:
                hot.append(d['symbol'])
        
        main = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
        for s in main:
            if s not in hot:
                hot.insert(0, s)
        
        self.hot_symbols = hot[:MAX_SYMBOLS_TO_SCAN]
        
        logger.info(f"🔍 Scan: {len(pump)} pumps, {len(dump)} dumps, {len(self.hot_symbols)} hot")
        
        return pump[:5], dump[:5], self.hot_symbols

# ==================== Feature Engineer ====================
class FeatureEngineer:
    @staticmethod
    def extract_all_features(candles):
        if not candles or len(candles) < 50:
            return None
        
        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        opens = np.array([c['open'] for c in candles])
        volumes = np.array([c['volume'] for c in candles])
        
        features = {}
        current_price = closes[-1]
        
        # بازده‌ها
        for p in [5, 10, 20, 30, 50]:
            if len(closes) > p:
                features[f'return_{p}'] = ((closes[-1] - closes[-p]) / closes[-p]) * 100
        
        # میانگین‌ها
        for p in [7, 14, 21, 50]:
            if len(closes) >= p:
                ma = np.mean(closes[-p:])
                features[f'ma_{p}'] = ma
                features[f'price_to_ma_{p}'] = (current_price / (ma + 0.0001) - 1) * 100
        
        # RSI
        for p in [7, 14, 21]:
            if len(closes) >= p + 1:
                delta = np.diff(closes[-p-1:])
                gain = np.mean(delta[delta > 0]) if np.sum(delta > 0) > 0 else 0
                loss = -np.mean(delta[delta < 0]) if np.sum(delta < 0) > 0 else 0.001
                rs = gain / loss
                features[f'rsi_{p}'] = 100 - (100 / (1 + rs))
        
        # MACD
        if len(closes) >= 26:
            ema12 = FeatureEngineer._ema(closes, 12)
            ema26 = FeatureEngineer._ema(closes, 26)
            features['macd'] = ema12 - ema26
        
        # بولینگر
        if len(closes) >= 20:
            sma = np.mean(closes[-20:])
            std = np.std(closes[-20:])
            bb_upper = sma + 2 * std
            bb_lower = sma - 2 * std
            features['bb_position'] = (current_price - bb_lower) / (bb_upper - bb_lower + 0.0001)
        
        # حجم
        avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else 1
        features['volume_ratio'] = volumes[-1] / (avg_vol + 0.0001)
        
        # حمایت و مقاومت
        features['support'] = np.min(closes[-20:])
        features['resistance'] = np.max(closes[-20:])
        features['dist_to_support'] = ((current_price - features['support']) / (current_price + 0.0001)) * 100
        features['dist_to_resistance'] = ((features['resistance'] - current_price) / (current_price + 0.0001)) * 100
        
        # آمار
        returns = np.diff(closes) / (closes[:-1] + 0.0001)
        if len(returns) >= 20:
            features['skewness'] = skew(returns[-20:])
            features['kurtosis'] = kurtosis(returns[-20:])
        
        # روند
        if len(closes) >= 20:
            x = np.arange(20)
            slope, _, _, _, _ = linregress(x, closes[-20:])
            features['trend_slope'] = slope
        
        # کندل
        last = candles[-1]
        body = abs(last['close'] - last['open'])
        range_hl = last['high'] - last['low']
        features['body_ratio'] = body / (range_hl + 0.0001)
        
        return features
    
    @staticmethod
    def _ema(data, period):
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        alpha = 2 / (period + 1)
        ema = data[-period:].mean()
        for v in data[-period:]:
            ema = v * alpha + ema * (1 - alpha)
        return ema

# ==================== AI Model ====================
class ProfessionalAIModel:
    def __init__(self):
        self.models = {}
        self.scaler = RobustScaler()
        self.pca = PCA(n_components=0.95)
        self.is_trained = False
        self.feature_names = []
        self.version = 1
        
        self.models['random_forest'] = RandomForestClassifier(
            n_estimators=300, max_depth=15, random_state=42, n_jobs=-1
        )
        self.models['gradient_boosting'] = GradientBoostingClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=5, random_state=42
        )
        if XGB_AVAILABLE:
            self.models['xgboost'] = xgb.XGBClassifier(
                n_estimators=300, learning_rate=0.03, max_depth=6, random_state=42
            )
        
        self.voting_model = None
        self._load_model()
        logger.info("✅ AI Model initialized")
    
    def train(self, features_list, labels):
        if len(features_list) < 30:
            return False
        
        X = []
        feature_names = []
        
        for features in features_list:
            row = []
            for key in sorted(features.keys()):
                if isinstance(features[key], (int, float)) and not np.isnan(features[key]):
                    row.append(features[key])
                    if key not in feature_names:
                        feature_names.append(key)
            X.append(row)
        
        X = np.array(X)
        y = np.array(labels)
        self.feature_names = feature_names
        
        X_scaled = self.scaler.fit_transform(X)
        X_pca = self.pca.fit_transform(X_scaled)
        
        for name, model in self.models.items():
            try:
                model.fit(X_pca, y)
            except:
                pass
        
        try:
            estimators = [(name, model) for name, model in self.models.items()]
            self.voting_model = VotingClassifier(estimators=estimators, voting='soft')
            self.voting_model.fit(X_pca, y)
        except:
            pass
        
        self.is_trained = True
        self.version += 1
        
        accuracy = self.voting_model.score(X_pca, y) if self.voting_model else 0
        db.save_model_performance(accuracy, len(X))
        self._save_model()
        
        logger.info(f"✅ Model trained! Accuracy: {accuracy:.2%}")
        return True
    
    def predict(self, features):
        if not self.is_trained:
            return None, 0, {}
        
        try:
            row = []
            for key in self.feature_names:
                row.append(features.get(key, 0))
            
            X = np.array([row])
            X_scaled = self.scaler.transform(X)
            X_pca = self.pca.transform(X_scaled)
            
            if self.voting_model:
                pred = self.voting_model.predict(X_pca)[0]
                prob = self.voting_model.predict_proba(X_pca)[0]
                confidence = max(prob) * 100
                return pred, confidence, {}
            
            return None, 0, {}
        except:
            return None, 0, {}
    
    def _save_model(self):
        try:
            with open('ai_model_v17.pkl', 'wb') as f:
                pickle.dump({
                    'models': self.models,
                    'voting_model': self.voting_model,
                    'scaler': self.scaler,
                    'pca': self.pca,
                    'feature_names': self.feature_names,
                    'is_trained': self.is_trained,
                    'version': self.version
                }, f)
        except:
            pass
    
    def _load_model(self):
        try:
            if os.path.exists('ai_model_v17.pkl'):
                with open('ai_model_v17.pkl', 'rb') as f:
                    data = pickle.load(f)
                self.models = data['models']
                self.voting_model = data['voting_model']
                self.scaler = data['scaler']
                self.pca = data['pca']
                self.feature_names = data['feature_names']
                self.is_trained = data['is_trained']
                self.version = data.get('version', 1)
                logger.info(f"✅ Model loaded (v{self.version})")
        except:
            pass

# ==================== Signal Engine ====================
class SignalEngine:
    def __init__(self):
        self.ai_model = ProfessionalAIModel()
        self.scanner = DynamicSymbolScanner()
        self.feature_engineer = FeatureEngineer()
        self.last_signals = {}
        
    def train_initial(self):
        logger.info("🔄 Initial training...")
        
        # از داده‌های تاریخی
        end = datetime.now()
        start = end - timedelta(days=30)
        candles = price_service.get_historical_candles('BTCUSDT', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), '1h')
        
        if candles and len(candles) > 100:
            features_list = []
            labels = []
            for i in range(50, len(candles) - 10):
                window = candles[i-50:i+1]
                features = self.feature_engineer.extract_all_features(window)
                if features:
                    future_price = candles[i+10]['close']
                    current_price = candles[i]['close']
                    label = 1 if future_price > current_price else 0
                    features_list.append(features)
                    labels.append(label)
                    db.save_training_data('BTCUSDT', features, label, 'historical')
            
            if len(features_list) >= 30:
                self.ai_model.train(features_list, labels)
                logger.info("✅ Initial training complete")
                return True
        
        logger.warning("⚠️ Initial training failed")
        return False
    
    def train_from_feedback(self):
        feedback_data = db.get_feedback_training_data(200)
        if len(feedback_data) < MIN_FEEDBACK_FOR_RETRAIN:
            return False
        
        features_list = []
        labels = []
        for fb in feedback_data:
            features_snapshot = fb[0]
            feedback = fb[1]
            if features_snapshot:
                try:
                    features = json.loads(features_snapshot)
                    if features and len(features) > 5:
                        features_list.append(features)
                        labels.append(1 if feedback == 'positive' else 0)
                except:
                    continue
        
        if len(features_list) >= MIN_FEEDBACK_FOR_RETRAIN:
            return self.ai_model.train(features_list, labels)
        return False
    
    def analyze(self, symbol):
        try:
            candles = price_service.get_candles(symbol, '5m', 200)
            if not candles or len(candles) < 50:
                return None
            
            features = self.feature_engineer.extract_all_features(candles)
            if not features:
                return None
            
            current_price = candles[-1]['close']
            prediction, confidence, _ = self.ai_model.predict(features)
            
            closes = np.array([c['close'] for c in candles])
            atr = np.std(closes[-20:]) if len(closes) >= 20 else current_price * 0.01
            support = np.min(closes[-20:])
            resistance = np.max(closes[-20:])
            
            # تشخیص نوع
            signal_type = 'NORMAL'
            if symbol in self.scanner.pump_candidates:
                signal_type = 'PUMP'
            elif symbol in self.scanner.dump_candidates:
                signal_type = 'DUMP'
            
            if prediction is None or confidence < MIN_PREDICTION_CONFIDENCE:
                return None
            
            direction = 'LONG' if prediction == 1 else 'SHORT'
            
            if direction == 'LONG':
                sl = max(current_price - (atr * 2.5), support * 0.98)
                tp = current_price + (atr * 4)
            else:
                sl = min(current_price + (atr * 2.5), resistance * 1.02)
                tp = current_price - (atr * 4)
            
            if confidence >= 75:
                leverage = 15
            elif confidence >= 65:
                leverage = 10
            else:
                leverage = 5
            
            return {
                'symbol': symbol,
                'direction': direction,
                'confidence': int(confidence),
                'entry': round(current_price, 2),
                'sl': round(sl, 2),
                'tp': round(tp, 2),
                'leverage': leverage,
                'support': round(support, 2),
                'resistance': round(resistance, 2),
                'model_votes': f'Confidence: {int(confidence)}%',
                'signal_accuracy': confidence,
                'features': features,
                'signal_type': signal_type
            }
        except Exception as e:
            logger.error(f"Analyze error {symbol}: {e}")
            return None
    
    def scan_and_signal(self):
        """اسکن و تولید سیگنال - هر ۳ دقیقه یک بار"""
        pump, dump, hot = self.scanner.scan()
        
        if not hot:
            hot = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
        
        signals = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(self.analyze, symbol): symbol for symbol in hot[:MAX_SYMBOLS_TO_SCAN]}
            for future in futures:
                try:
                    result = future.result(timeout=15)
                    if result:
                        signals.append(result)
                except:
                    continue
        
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # فقط بهترین سیگنال رو نگه دار
        if signals:
            # فیلتر سیگنال‌های تکراری
            unique = []
            seen = set()
            for s in signals:
                if s['symbol'] not in seen:
                    seen.add(s['symbol'])
                    unique.append(s)
            
            # اولویت با سیگنال‌های پامپ و دامپ
            priority = []
            normal = []
            for s in unique:
                if s['signal_type'] in ['PUMP', 'DUMP']:
                    priority.append(s)
                else:
                    normal.append(s)
            
            best = priority[:2] + normal[:1]
            
            # ذخیره و ارسال
            sent_count = 0
            for signal in best[:1]:  # فقط یک سیگنال بفرست
                signal_id = db.save_signal(signal, signal.get('features'))
                if self.send_to_channel(signal):
                    db.mark_signal_sent(signal_id)
                    sent_count += 1
                    logger.info(f"📤 Signal sent: {signal['symbol']} {signal['direction']} (conf: {signal['confidence']}%)")
                    time.sleep(2)  # جلوگیری از اسپم
            
            return sent_count
        return 0
    
    def send_to_channel(self, signal):
        """ارسال سیگنال به کانال"""
        try:
            emoji = '🟢' if signal['direction'] == 'LONG' else '🔴'
            direction_text = 'خرید (LONG)' if signal['direction'] == 'LONG' else 'فروش (SHORT)'
            
            tag = ""
            if signal.get('signal_type') == 'PUMP':
                tag = "🔥 **سیگنال پامپ** - "
            elif signal.get('signal_type') == 'DUMP':
                tag = "📉 **سیگنال ریزش** - "
            
            msg = f"""
🚨 **سیگنال معاملاتی V17**

{emoji} **{signal['symbol']} - {direction_text}**
{tag}
💰 ورود: ${signal['entry']:,.2f}
🎯 حد سود: ${signal['tp']:,.2f}
🛑 حد ضرر: ${signal['sl']:,.2f}
📉 حمایت: ${signal['support']:,.2f}
📈 مقاومت: ${signal['resistance']:,.2f}
⚡ اهرم: {signal['leverage']}x
🎯 اطمینان: {signal['confidence']}%

🧠 مدل: V17 AUTONOMOUS
📊 نسخه: {self.ai_model.version}

📌 برای بازخورد: 
✅ سود کردم -> پیام دهید "سود کردم {id}"
❌ سود نکردم -> پیام دهید "سود نکردم {id}"

#سیگنال #{'LONG' if signal['direction'] == 'LONG' else 'SHORT'} #{signal['symbol']}
"""
            # ارسال به کانال
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': CHANNEL_ID,
                'text': msg,
                'parse_mode': 'Markdown'
            }
            r = requests.post(url, data=data, timeout=10)
            
            if r.status_code == 200:
                # استخراج signal_id برای بازخورد
                result = r.json()
                if result.get('ok'):
                    return True
            
            logger.error(f"Channel send failed: {r.text}")
            return False
            
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    def process_feedback(self, message_text):
        """پردازش بازخورد از پیام‌های کانال"""
        import re
        
        # الگوی بازخورد: "سود کردم 123" یا "سود نکردم 123"
        pattern = r'(سود کردم|سود نکردم)\s*(\d+)'
        match = re.search(pattern, message_text)
        
        if match:
            feedback_type = match.group(1)
            signal_id = int(match.group(2))
            
            feedback = 'positive' if feedback_type == 'سود کردم' else 'negative'
            db.update_signal_feedback(signal_id, feedback)
            
            logger.info(f"📝 Feedback: {feedback_type} for signal {signal_id}")
            
            # اگر بازخورد منفی بود، مدل رو آموزش بده
            if feedback == 'negative':
                threading.Thread(target=self.train_from_feedback, daemon=True).start()
            
            return True
        return False

# ==================== Main Bot ====================
class AutonomousBot:
    def __init__(self):
        self.engine = SignalEngine()
        self.running = True
        self.last_signal_time = None
        
    def start(self):
        logger.info("="*60)
        logger.info("🤖 AUTONOMOUS SIGNAL BOT V17 STARTED")
        logger.info(f"📡 Channel: {CHANNEL_ID}")
        logger.info(f"⏱️ Scan interval: {SCAN_INTERVAL} seconds")
        logger.info("="*60)
        
        # آموزش اولیه
        if not self.engine.ai_model.is_trained:
            self.engine.train_initial()
        
        # حلقه اصلی
        while self.running:
            try:
                # اسکن و ارسال سیگنال
                sent = self.engine.scan_and_signal()
                
                if sent > 0:
                    logger.info(f"✅ {sent} signal(s) sent to channel")
                    self.last_signal_time = datetime.now()
                
                # هر ۵ دقیقه یک بار یادگیری از بازخورد
                if self.last_signal_time and (datetime.now() - self.last_signal_time).seconds > 300:
                    self.engine.train_from_feedback()
                
                # منتظر اسکن بعدی
                time.sleep(SCAN_INTERVAL)
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)
    
    def stop(self):
        self.running = False

# ==================== Telegram Feedback Handler ====================
class FeedbackHandler:
    """پردازش بازخورد از پیام‌های کانال"""
    
    def __init__(self, engine):
        self.engine = engine
        self.last_check = None
    
    def check_feedback(self):
        """چک کردن پیام‌های جدید کانال برای بازخورد"""
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {
                'chat_id': CHANNEL_ID,
                'limit': 10,
                'timeout': 5
            }
            
            # استفاده از offset برای جلوگیری از تکراری
            offset = db.get_setting('feedback_offset')
            if offset:
                params['offset'] = int(offset)
            
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get('ok') and data.get('result'):
                    for update in data['result']:
                        if 'message' in update and 'text' in update['message']:
                            text = update['message']['text']
                            if self.engine.process_feedback(text):
                                # ذخیره offset
                                db.update_setting('feedback_offset', str(update['update_id'] + 1))
        except Exception as e:
            logger.error(f"Feedback check error: {e}")

# ==================== Run ====================
def main():
    check_and_create_pid()
    
    # راه‌اندازی ربات خودکار
    bot = AutonomousBot()
    
    # ترد جداگانه برای چک کردن بازخورد
    feedback_handler = FeedbackHandler(bot.engine)
    
    def feedback_loop():
        while True:
            try:
                feedback_handler.check_feedback()
                time.sleep(30)  # هر ۳۰ ثانیه چک کن
            except:
                time.sleep(60)
    
    feedback_thread = threading.Thread(target=feedback_loop, daemon=True)
    feedback_thread.start()
    
    # شروع ربات
    try:
        bot.start()
    except KeyboardInterrupt:
        logger.info("🛑 Stopping...")
    finally:
        remove_pid()

if __name__ == "__main__":
    main()