"""
🤖 هوش مصنوعی MON - نسخه فوق‌پیشرفته با قابلیت یادگیری خودکار و تحلیل رفتار
طراحی شده با معماری Neuro-Symbolic AI
"""

import os
import sys
import json
import hashlib
import re
import asyncio
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict, Counter
import logging
import pickle
from pathlib import Path
import random
import time
from enum import Enum

# ==================== کتابخانه‌های اصلی ====================
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ==================== دیتابیس و کش ====================
import redis
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import sqlite3

# ==================== پردازش زبان طبیعی ====================
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import jieba
import hazm
from hazm import *

# ==================== یادگیری عمیق ====================
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

# ==================== وب سرویس ====================
from flask import Flask, request, jsonify, render_template, session, send_from_directory
from flask_cors import CORS
import jwt
from functools import wraps
import secrets

# ==================== ابزارهای کمکی ====================
import requests
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import gc

# ==================== تنظیمات ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultra_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== کلاس‌های دیتا ====================
class UserBehavior(Enum):
    """رفتارهای کاربر"""
    NEW = "جدید"
    LEARNING = "در حال یادگیری"
    EXPERT = "حرفه‌ای"
    CURIOUS = "کنجکاو"
    NEEDY = "نیازمند راهنما"
    NEGATIVE = "منفی"
    POSITIVE = "مثبت"

@dataclass
class UserProfile:
    """پروفایل کاربر"""
    user_id: int
    first_seen: datetime
    last_seen: datetime
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    topics: Dict[str, int] = field(default_factory=dict)
    keywords: Dict[str, int] = field(default_factory=dict)
    behavior: UserBehavior = UserBehavior.NEW
    avg_response_time: float = 0.0
    satisfaction_score: float = 0.0
    learning_pattern: List[str] = field(default_factory=list)
    preferred_categories: List[str] = field(default_factory=list)
    complexity_level: float = 0.5
    emotional_state: str = "neutral"
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'total_queries': self.total_queries,
            'successful_queries': self.successful_queries,
            'failed_queries': self.failed_queries,
            'topics': self.topics,
            'keywords': self.keywords,
            'behavior': self.behavior.value,
            'avg_response_time': self.avg_response_time,
            'satisfaction_score': self.satisfaction_score,
            'learning_pattern': self.learning_pattern,
            'preferred_categories': self.preferred_categories,
            'complexity_level': self.complexity_level,
            'emotional_state': self.emotional_state
        }

@dataclass
class LearningHistory:
    """تاریخچه یادگیری"""
    query: str
    response: str
    timestamp: datetime
    confidence: float
    category: str
    keywords: List[str]
    user_feedback: Optional[str] = None
    was_learned: bool = False
    
    def to_dict(self):
        return {
            'query': self.query,
            'response': self.response,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'category': self.category,
            'keywords': self.keywords,
            'user_feedback': self.user_feedback,
            'was_learned': self.was_learned
        }

# ==================== مغز اصلی: Neuro-Symbolic AI ====================
class NeuroSymbolicBrain:
    """مغز فوق‌پیشرفته با ترکیب شبکه‌های عصبی و سیستم نمادین"""
    
    def __init__(self):
        # ======== بخش نمادین (Symbolic) ========
        self.symbolic_memory = {}
        self.keyword_graph = defaultdict(set)
        self.category_tree = defaultdict(set)
        self.semantic_network = {}
        
        # ======== بخش عصبی (Neural) ========
        self._init_neural_networks()
        
        # ======== بخش تحلیلی ========
        self.tfidf_vectorizer = TfidfVectorizer(max_features=2000, ngram_range=(1, 3))
        self.lda_model = LatentDirichletAllocation(n_components=10, random_state=42)
        self.cluster_model = None
        
        # ======== حافظه‌های پیشرفته ========
        self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.mongo = MongoClient('mongodb://localhost:27017')['ultra_ai']
        self.knowledge_collection = self.mongo['knowledge']
        self.profile_collection = self.mongo['profiles']
        self.history_collection = self.mongo['history']
        
        # ======== کش ========
        self.cache = {}
        self.cache_size = 2000
        
        # ======== سیستم یادگیری ========
        self.auto_learning_queue = queue.Queue()
        self.learning_thread = threading.Thread(target=self._auto_learn, daemon=True)
        self.learning_thread.start()
        
        # ======== تحلیلگر رفتار ========
        self.behavior_analyzer = BehaviorAnalyzer()
        
        # ======== آمار ========
        self.stats = {
            'total_learned': 0,
            'auto_learned': 0,
            'user_taught': 0,
            'success_rate': 0.0,
            'avg_confidence': 0.0
        }
        
        logger.info("🧠 مغز Neuro-Symbolic راه‌اندازی شد")
    
    def _init_neural_networks(self):
        """راه‌اندازی شبکه‌های عصبی"""
        try:
            # مدل ۱: تشخیص موضوع
            self.topic_classifier = self._build_topic_classifier()
            
            # مدل ۲: تولید پاسخ
            self.response_generator = self._build_response_generator()
            
            # مدل ۳: تشخیص احساسات
            self.emotion_classifier = self._build_emotion_classifier()
            
            # مدل ۴: امتیازدهی
            self.scoring_model = self._build_scoring_model()
            
            logger.info("✅ شبکه‌های عصبی راه‌اندازی شدند")
            
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی شبکه‌های عصبی: {e}")
            self._init_fallback_models()
    
    def _build_topic_classifier(self):
        """ساخت مدل تشخیص موضوع"""
        model = models.Sequential([
            layers.Dense(256, activation='relu', input_shape=(2000,)),
            layers.Dropout(0.3),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(64, activation='relu'),
            layers.Dense(10, activation='softmax')
        ])
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        return model
    
    def _build_response_generator(self):
        """ساخت مدل تولید پاسخ"""
        model = models.Sequential([
            layers.LSTM(256, return_sequences=True, input_shape=(100, 300)),
            layers.LSTM(256, return_sequences=True),
            layers.LSTM(256),
            layers.Dense(512, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(256, activation='relu'),
            layers.Dense(100, activation='softmax')
        ])
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        return model
    
    def _build_emotion_classifier(self):
        """ساخت مدل تشخیص احساسات"""
        model = models.Sequential([
            layers.Dense(128, activation='relu', input_shape=(2000,)),
            layers.Dropout(0.3),
            layers.Dense(64, activation='relu'),
            layers.Dense(7, activation='softmax')  # 7 احساس مختلف
        ])
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        return model
    
    def _build_scoring_model(self):
        """ساخت مدل امتیازدهی"""
        model = models.Sequential([
            layers.Dense(64, activation='relu', input_shape=(10,)),
            layers.Dense(32, activation='relu'),
            layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model
    
    def _init_fallback_models(self):
        """مدل‌های جایگزین ساده"""
        self.topic_classifier = None
        self.response_generator = None
        self.emotion_classifier = None
        self.scoring_model = None
        logger.warning("⚠️ استفاده از مدل‌های جایگزین ساده")
    
    # ==================== یادگیری خودکار ====================
    def auto_learn(self, query: str, response: str):
        """افزودن به صف یادگیری خودکار"""
        self.auto_learning_queue.put({
            'query': query,
            'response': response,
            'timestamp': datetime.now()
        })
    
    def _auto_learn(self):
        """پردازش خودکار یادگیری"""
        while True:
            try:
                item = self.auto_learning_queue.get(timeout=5)
                
                # تحلیل عمیق سوال
                analysis = self._deep_analyze(item['query'])
                
                # استخراج دانش
                knowledge = self._extract_knowledge(
                    item['query'],
                    item['response'],
                    analysis
                )
                
                # ذخیره در حافظه
                self._store_knowledge(knowledge)
                
                # به‌روزرسانی آمار
                self.stats['auto_learned'] += 1
                self.stats['total_learned'] += 1
                
                logger.info(f"✅ یادگیری خودکار: {item['query'][:50]}...")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ خطا در یادگیری خودکار: {e}")
    
    def _deep_analyze(self, text: str) -> Dict:
        """تحلیل عمیق متن"""
        try:
            # ۱. استخراج کلمات کلیدی
            keywords = self._extract_keywords_advanced(text)
            
            # ۲. تشخیص موضوع
            topics = self._detect_topics(text)
            
            # ۳. تشخیص احساسات
            emotion = self._detect_emotion(text)
            
            # ۴. تحلیل پیچیدگی
            complexity = self._analyze_complexity(text)
            
            # ۵. استخراج موجودیت‌ها (NER)
            entities = self._extract_entities(text)
            
            # ۶. تشخیص الگوهای زبانی
            patterns = self._detect_patterns(text)
            
            return {
                'keywords': keywords,
                'topics': topics,
                'emotion': emotion,
                'complexity': complexity,
                'entities': entities,
                'patterns': patterns
            }
            
        except Exception as e:
            logger.error(f"❌ خطا در تحلیل عمیق: {e}")
            return {
                'keywords': [],
                'topics': [],
                'emotion': 'neutral',
                'complexity': 0.5,
                'entities': [],
                'patterns': []
            }
    
    def _extract_keywords_advanced(self, text: str) -> List[str]:
        """استخراج پیشرفته کلمات کلیدی با چند روش"""
        # روش ۱: Hazel (پردازش زبان فارسی)
        normalizer = Normalizer()
        text = normalizer.normalize(text)
        
        # روش ۲: Tokenization
        tokenizer = WordTokenizer()
        tokens = tokenizer.tokenize(text)
        
        # روش ۳: حذف کلمات بی‌معنی
        stopwords = set(stopwords_list())
        cleaned = [t for t in tokens if t not in stopwords and len(t) > 2]
        
        # روش ۴: TF-IDF برای اهمیت
        if len(cleaned) > 3:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([' '.join(cleaned)])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf.toarray()[0]
            
            # انتخاب کلمات با بالاترین امتیاز
            important = sorted(
                zip(feature_names, scores),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            keywords = [k for k, _ in important if k not in stopwords]
        else:
            keywords = cleaned[:5]
        
        return keywords
    
    def _detect_topics(self, text: str) -> List[str]:
        """تشخیص موضوعات متن"""
        topics = []
        
        # لیست موضوعات
        topic_keywords = {
            'پزشکی': ['دارو', 'بیماری', 'درمان', 'سلامت', 'پزشک', 'درد', 'علائم'],
            'برنامه‌نویسی': ['کد', 'پایتون', 'برنامه', 'الگوریتم', 'وب', 'سایت', 'طراحی'],
            'آموزشی': ['یادگیری', 'آموزش', 'درس', 'مدرسه', 'دانشجو', 'تمرین'],
            'فنی': ['سیستم', 'سخت‌افزار', 'نرم‌افزار', 'اینترنت', 'شبکه'],
            'عمومی': ['سلام', 'خوبی', 'احوال', 'روز', 'زندگی'],
            'روانشناسی': ['احساس', 'افسردگی', 'اضطراب', 'خوشحالی', 'استرس'],
            'اقتصاد': ['پول', 'درآمد', 'بازار', 'کار', 'شغل', 'حقوق'],
            'سیاسی': ['انتخابات', 'وزیر', 'رییس‌جمهور', 'مجلس'],
            'علمی': ['تحقیق', 'دانشمندان', 'پژوهش', 'اکتشاف'],
            'هنری': ['نقاشی', 'موسیقی', 'فیلم', 'کتاب', 'شعر']
        }
        
        detected = []
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    detected.append(topic)
                    break
        
        return detected[:3]
    
    def _detect_emotion(self, text: str) -> str:
        """تشخیص احساسات متن"""
        # لیست کلمات احساسی
        emotions = {
            'happy': ['خوشحال', 'عالی', 'خوب', 'شاد', 'خنده', 'لذت'],
            'sad': ['ناراحت', 'غمگین', 'درد', 'افسرده', 'گریه'],
            'angry': ['عصبانی', 'خشم', 'کتک', 'ناراضی', 'بد'],
            'fear': ['ترس', 'وحشت', 'اضطراب', 'استرس', 'نگران'],
            'surprise': ['تعجب', 'شگفت', 'عجیب', 'باورنکردنی'],
            'love': ['عشق', 'دوست', 'مهربان', 'زیبا', 'دوستت دارم'],
            'neutral': ['سلام', 'چطوری', 'هست', 'بود', 'شد']
        }
        
        scores = defaultdict(int)
        for emotion, words in emotions.items():
            for word in words:
                if word in text:
                    scores[emotion] += 1
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return 'neutral'
    
    def _analyze_complexity(self, text: str) -> float:
        """تحلیل پیچیدگی متن"""
        words = text.split()
        
        # ۱. طول متن
        length_score = min(len(words) / 20, 1.0)
        
        # ۲. کلمات تخصصی
        specialized = len([w for w in words if len(w) > 7])
        specialized_score = specialized / max(len(words), 1)
        
        # ۳. تنوع کلمات
        unique_ratio = len(set(words)) / max(len(words), 1)
        
        # ۴. پیچیدگی دستوری
        # (ساده‌سازی)
        punctuation = text.count('،') + text.count('.') + text.count('؟')
        grammar_score = min(punctuation / 5, 1.0)
        
        # ترکیب امتیازات
        complexity = (length_score * 0.3 + specialized_score * 0.3 + 
                     unique_ratio * 0.2 + grammar_score * 0.2)
        
        return min(complexity, 1.0)
    
    def _extract_entities(self, text: str) -> List[Dict]:
        """استخراج موجودیت‌ها (ساده)"""
        entities = []
        
        # تشخیص اعداد
        numbers = re.findall(r'\d+', text)
        for num in numbers:
            entities.append({'type': 'NUMBER', 'value': num})
        
        # تشخیص کلمات خاص
        special = re.findall(r'[آ-ی]{5,}', text)
        for item in special[:3]:
            entities.append({'type': 'WORD', 'value': item})
        
        return entities
    
    def _detect_patterns(self, text: str) -> List[str]:
        """تشخیص الگوهای زبانی"""
        patterns = []
        
        # الگوی سوال
        if '؟' in text or 'چرا' in text or 'چطور' in text or 'چه' in text:
            patterns.append('question')
        
        # الگوی درخواست
        if 'می‌خواهم' in text or 'لطفاً' in text or 'ممنون' in text:
            patterns.append('request')
        
        # الگوی توضیح
        if len(text.split()) > 20:
            patterns.append('explanation')
        
        return patterns
    
    def _extract_knowledge(self, query: str, response: str, analysis: Dict) -> Dict:
        """استخراج دانش از تحلیل"""
        return {
            'query': query,
            'response': response,
            'keywords': analysis['keywords'],
            'topics': analysis['topics'],
            'emotion': analysis['emotion'],
            'complexity': analysis['complexity'],
            'entities': analysis['entities'],
            'patterns': analysis['patterns'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _store_knowledge(self, knowledge: Dict):
        """ذخیره دانش در دیتابیس"""
        try:
            # ۱. ذخیره در MongoDB
            doc_id = hashlib.md5(knowledge['query'].encode()).hexdigest()
            self.knowledge_collection.update_one(
                {'_id': doc_id},
                {'$set': knowledge},
                upsert=True
            )
            
            # ۲. ذخیره در Redis (برای دسترسی سریع)
            key = f"knowledge:{doc_id}"
            self.redis.hset(key, mapping={
                'query': knowledge['query'],
                'response': knowledge['response'],
                'keywords': json.dumps(knowledge['keywords']),
                'topics': json.dumps(knowledge['topics']),
                'emotion': knowledge['emotion'],
                'complexity': knowledge['complexity']
            })
            
            # ۳. به‌روزرسانی ایندکس کلمات کلیدی
            for keyword in knowledge['keywords']:
                self.redis.sadd(f"index:{keyword}", doc_id)
                # افزایش وزن
                self.redis.zincrby(f"weight:{keyword}", 1, doc_id)
            
            # ۴. به‌روزرسانی گراف دانش
            for topic in knowledge['topics']:
                self.category_tree[topic].add(doc_id)
            
            # ۵. به‌روزرسانی کش
            self.cache[knowledge['query']] = knowledge['response']
            if len(self.cache) > self.cache_size:
                # حذف قدیمی‌ترین
                oldest = next(iter(self.cache))
                del self.cache[oldest]
            
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره دانش: {e}")
    
    # ==================== جستجوی هوشمند ====================
    def search(self, query: str) -> Dict:
        """جستجوی فوق‌پیشرفته با ترکیب چندین روش"""
        try:
            start_time = time.time()
            
            # ====== ۱. تحلیل سوال ======
            analysis = self._deep_analyze(query)
            
            # ====== ۲. جستجو در کش ======
            if query in self.cache:
                logger.info(f"⚡ پاسخ از کش: {query[:50]}...")
                return {
                    'found': True,
                    'response': self.cache[query],
                    'confidence': 1.0,
                    'source': 'cache',
                    'analysis': analysis
                }
            
            # ====== ۳. جستجوی کلمات کلیدی ======
            keyword_results = self._keyword_search(query, analysis['keywords'])
            
            # ====== ۴. جستجوی معنایی ======
            semantic_results = self._semantic_search(query)
            
            # ====== ۵. جستجوی موضوعی ======
            topic_results = self._topic_search(query, analysis['topics'])
            
            # ====== ۶. جستجوی ترکیبی ======
            combined = self._combine_search_results(
                keyword_results,
                semantic_results,
                topic_results,
                analysis
            )
            
            # ====== ۷. امتیازدهی نهایی ======
            if combined:
                best = max(combined, key=lambda x: x['score'])
                
                if best['score'] > 0.7:
                    # پاسخ با اطمینان بالا
                    self.cache[query] = best['response']
                    return {
                        'found': True,
                        'response': best['response'],
                        'confidence': best['score'],
                        'source': best.get('source', 'combined'),
                        'analysis': analysis
                    }
            
            # ====== ۸. تولید پاسخ هوشمند ======
            generated = self._generate_response(query, analysis)
            
            if generated:
                # یادگیری خودکار
                self.auto_learn(query, generated)
                
                return {
                    'found': True,
                    'response': generated,
                    'confidence': 0.6,
                    'source': 'generated',
                    'analysis': analysis
                }
            
            # ====== ۹. پاسخ پیش‌فرض ======
            return {
                'found': False,
                'response': self._generate_fallback(query, analysis),
                'confidence': 0.0,
                'source': 'fallback',
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return {
                'found': False,
                'response': "⚠️ خطا در پردازش سوال. لطفاً دوباره تلاش کنید.",
                'confidence': 0.0,
                'source': 'error'
            }
    
    def _keyword_search(self, query: str, keywords: List[str]) -> List[Dict]:
        """جستجوی مبتنی بر کلمات کلیدی"""
        results = []
        
        for keyword in keywords:
            # پیدا کردن داکیومنت‌های مرتبط
            doc_ids = self.redis.smembers(f"index:{keyword}")
            
            for doc_id in doc_ids:
                data = self.redis.hgetall(f"knowledge:{doc_id}")
                if data:
                    # محاسبه امتیاز
                    stored_keywords = json.loads(data.get('keywords', '[]'))
                    score = len(set(keywords) & set(stored_keywords)) / len(set(keywords) | set(stored_keywords))
                    
                    results.append({
                        'id': doc_id,
                        'query': data['query'],
                        'response': data['response'],
                        'score': score,
                        'source': 'keyword',
                        'keywords': stored_keywords
                    })
        
        # مرتب‌سازی
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:10]
    
    def _semantic_search(self, query: str) -> List[Dict]:
        """جستجوی معنایی با استفاده از TF-IDF"""
        try:
            # گرفتن نمونه‌های از دیتابیس
            samples = list(self.knowledge_collection.find().limit(100))
            
            if not samples:
                return []
            
            # آماده‌سازی متن‌ها
            texts = [s.get('query', '') for s in samples]
            texts.append(query)
            
            # محاسبه TF-IDF
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # شباهت کسینوسی
            similarities = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]
            
            results = []
            for i, sim in enumerate(similarities):
                if sim > 0.1:
                    results.append({
                        'id': samples[i].get('_id'),
                        'query': samples[i].get('query'),
                        'response': samples[i].get('response'),
                        'score': sim,
                        'source': 'semantic'
                    })
            
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:10]
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی معنایی: {e}")
            return []
    
    def _topic_search(self, query: str, topics: List[str]) -> List[Dict]:
        """جستجوی مبتنی بر موضوع"""
        results = []
        
        for topic in topics:
            if topic in self.category_tree:
                doc_ids = self.category_tree[topic]
                
                for doc_id in doc_ids:
                    data = self.redis.hgetall(f"knowledge:{doc_id}")
                    if data:
                        stored_topics = json.loads(data.get('topics', '[]'))
                        score = len(set(topics) & set(stored_topics)) / len(set(topics) | set(stored_topics))
                        
                        results.append({
                            'id': doc_id,
                            'query': data['query'],
                            'response': data['response'],
                            'score': score * 0.8,
                            'source': 'topic'
                        })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:10]
    
    def _combine_search_results(self, *result_lists, analysis: Dict) -> List[Dict]:
        """ادغام هوشمند نتایج جستجو"""
        combined = {}
        
        for results in result_lists:
            for r in results:
                r_id = r['id']
                if r_id not in combined:
                    combined[r_id] = r
                    combined[r_id]['score'] = 0
                
                # اضافه کردن امتیاز با وزن‌های مختلف
                if r['source'] == 'keyword':
                    combined[r_id]['score'] += r['score'] * 0.5
                elif r['source'] == 'semantic':
                    combined[r_id]['score'] += r['score'] * 0.3
                elif r['source'] == 'topic':
                    combined[r_id]['score'] += r['score'] * 0.2
        
        # مرتب‌سازی
        results = list(combined.values())
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:10]
    
    def _generate_response(self, query: str, analysis: Dict) -> Optional[str]:
        """تولید پاسخ هوشمند"""
        try:
            # ====== ۱. پیدا کردن پاسخ مشابه ======
            similar = []
            
            # جستجوی در MongoDB
            cursor = self.knowledge_collection.find({
                'keywords': {'$in': analysis['keywords'][:3]}
            }).limit(5)
            
            for doc in cursor:
                similar.append(doc)
            
            if not similar:
                return None
            
            # ====== ۲. ترکیب بهترین پاسخ‌ها ======
            responses = [doc.get('response', '') for doc in similar[:3]]
            
            # ====== ۳. تولید پاسخ ترکیبی ======
            if len(responses) == 1:
                return responses[0]
            elif len(responses) == 2:
                return f"{responses[0]}\n\nهمچنین:\n{responses[1]}"
            else:
                return f"{responses[0]}\n\nهمچنین:\n{responses[1]}\n\nو:\n{responses[2]}"
            
        except Exception as e:
            logger.error(f"❌ خطا در تولید پاسخ: {e}")
            return None
    
    def _generate_fallback(self, query: str, analysis: Dict) -> str:
        """تولید پاسخ پیش‌فرض"""
        # تشخیص نوع سوال
        if 'چرا' in query:
            return f"""
🤔 سوال جالبی پرسیدید: "{query}"

من هنوز پاسخ دقیقی برای این سوال یاد نگرفته‌ام، اما:
1️⃣ می‌توانید با دستور `/learn` به من پاسخ را یاد دهید
2️⃣ یا سوال را کمی ساده‌تر بپرسید

📚 من هر روز چیزهای جدیدی یاد می‌گیرم!
"""
        elif 'چطور' in query or 'چگونه' in query:
            return f"""
💡 سوال شما: "{query}"

برای پاسخ به این سوال باید بیشتر یاد بگیرم! 
اما می‌توانید:
- با `/learn` پاسخ را به من یاد دهید
- یا از من به صورت مرحله‌ای بپرسید

🧠 من در حال یادگیری هستم...
"""
        else:
            return f"""
🌟 سوال خوبی پرسیدید!

من هنوز جواب "{query}" را نمی‌دانم، اما:
✅ با `/learn` به من یاد دهید
✅ یا سوال را دقیق‌تر بپرسید

💪 هر روز هوشمندتر می‌شوم!
"""
    
    # ==================== تحلیل رفتار کاربر ====================
    def analyze_user_behavior(self, user_id: int, query: str, response: str, success: bool) -> UserProfile:
        """تحلیل رفتار کاربر و به‌روزرسانی پروفایل"""
        try:
            # دریافت پروفایل
            profile = self._get_user_profile(user_id)
            
            # به‌روزرسانی آمار
            profile.total_queries += 1
            profile.last_seen = datetime.now()
            
            if success:
                profile.successful_queries += 1
            else:
                profile.failed_queries += 1
            
            # تحلیل موضوعات
            analysis = self._deep_analyze(query)
            for topic in analysis['topics']:
                profile.topics[topic] = profile.topics.get(topic, 0) + 1
            
            # تحلیل کلمات کلیدی
            for keyword in analysis['keywords']:
                profile.keywords[keyword] = profile.keywords.get(keyword, 0) + 1
            
            # تشخیص رفتار
            profile.behavior = self._classify_behavior(profile)
            
            # تشخیص علایق
            if profile.topics:
                sorted_topics = sorted(profile.topics.items(), key=lambda x: x[1], reverse=True)
                profile.preferred_categories = [t[0] for t in sorted_topics[:3]]
            
            # بروزرسانی سطح پیچیدگی
            avg_complexity = analysis['complexity']
            profile.complexity_level = (profile.complexity_level * 0.8 + avg_complexity * 0.2)
            
            # تشخیص حالت عاطفی
            profile.emotional_state = analysis['emotion']
            
            # محاسبه امتیاز رضایت
            if success:
                profile.satisfaction_score = min(profile.satisfaction_score + 0.05, 1.0)
            else:
                profile.satisfaction_score = max(profile.satisfaction_score - 0.02, 0.0)
            
            # ذخیره پروفایل
            self._save_user_profile(profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ خطا در تحلیل رفتار: {e}")
            return UserProfile(user_id=user_id, first_seen=datetime.now(), last_seen=datetime.now())
    
    def _get_user_profile(self, user_id: int) -> UserProfile:
        """دریافت پروفایل کاربر"""
        try:
            data = self.profile_collection.find_one({'_id': user_id})
            if data:
                return UserProfile(
                    user_id=data['user_id'],
                    first_seen=datetime.fromisoformat(data['first_seen']),
                    last_seen=datetime.fromisoformat(data['last_seen']),
                    total_queries=data['total_queries'],
                    successful_queries=data['successful_queries'],
                    failed_queries=data['failed_queries'],
                    topics=data['topics'],
                    keywords=data['keywords'],
                    behavior=UserBehavior(data['behavior']),
                    avg_response_time=data['avg_response_time'],
                    satisfaction_score=data['satisfaction_score'],
                    learning_pattern=data['learning_pattern'],
                    preferred_categories=data['preferred_categories'],
                    complexity_level=data['complexity_level'],
                    emotional_state=data['emotional_state']
                )
        except Exception as e:
            logger.error(f"❌ خطا در دریافت پروفایل: {e}")
        
        return UserProfile(user_id=user_id, first_seen=datetime.now(), last_seen=datetime.now())
    
    def _save_user_profile(self, profile: UserProfile):
        """ذخیره پروفایل کاربر"""
        try:
            self.profile_collection.update_one(
                {'_id': profile.user_id},
                {'$set': profile.to_dict()},
                upsert=True
            )
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره پروفایل: {e}")
    
    def _classify_behavior(self, profile: UserProfile) -> UserBehavior:
        """طبقه‌بندی رفتار کاربر"""
        # محاسبه نسبت موفقیت
        success_rate = profile.successful_queries / max(profile.total_queries, 1)
        
        # کاربر جدید
        if profile.total_queries < 5:
            return UserBehavior.NEW
        
        # کاربر حرفه‌ای
        if success_rate > 0.8 and profile.total_queries > 20:
            return UserBehavior.EXPERT
        
        # کاربر کنجکاو
        if len(profile.topics) > 5:
            return UserBehavior.CURIOUS
        
        # کاربر نیازمند راهنما
        if success_rate < 0.5:
            return UserBehavior.NEEDY
        
        # کاربر در حال یادگیری
        if success_rate < 0.7:
            return UserBehavior.LEARNING
        
        return UserBehavior.POSITIVE
    
    # ==================== آمار ====================
    def get_stats(self) -> Dict:
        """دریافت آمار کلی"""
        try:
            total_knowledge = self.knowledge_collection.count_documents({})
            total_profiles = self.profile_collection.count_documents({})
            
            # محاسبه نرخ موفقیت
            success_rate = self.stats['success_rate']
            
            return {
                'total_knowledge': total_knowledge,
                'total_profiles': total_profiles,
                'auto_learned': self.stats['auto_learned'],
                'user_taught': self.stats['user_taught'],
                'success_rate': success_rate,
                'avg_confidence': self.stats['avg_confidence'],
                'cache_size': len(self.cache)
            }
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت آمار: {e}")
            return {}

# ==================== تحلیلگر رفتار ====================
class BehaviorAnalyzer:
    """تحلیلگر پیشرفته رفتار کاربر"""
    
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        self.trends = defaultdict(list)
    
    def analyze_query_pattern(self, user_id: int, query: str):
        """تحلیل الگوی سوالات کاربر"""
        key = f"pattern:{user_id}"
        
        # ذخیره آخرین سوالات
        self.redis.lpush(key, query)
        self.redis.ltrim(key, 0, 99)  # فقط 100 سوال آخر
        
        # تحلیل روندها
        history = self.redis.lrange(key, 0, -1)
        
        # تشخیص تغییرات موضوع
        topics = []
        normalizer = Normalizer()
        for q in history[:10]:
            clean = normalizer.normalize(q)
            topics.append(clean[:20])
        
        return topics
    
    def get_user_insights(self, user_id: int) -> Dict:
        """دریافت بینش از رفتار کاربر"""
        key = f"pattern:{user_id}"
        history = self.redis.lrange(key, 0, -1)
        
        if not history:
            return {'status': 'new_user'}
        
        # تحلیل کلمات پرتکرار
        all_words = []
        for q in history[:50]:
            words = q.split()
            all_words.extend(words)
        
        word_freq = Counter(all_words)
        
        # تشخیص علایق
        interests = []
        for word, count in word_freq.most_common(10):
            if count > 2 and len(word) > 3:
                interests.append({'word': word, 'count': count})
        
        return {
            'total_queries': len(history),
            'interests': interests,
            'avg_length': sum(len(q) for q in history) / max(len(history), 1),
            'trend': 'active'
        }

# ==================== ربات تلگرام ====================
class UltraTelegramBot:
    """ربات تلگرام با قابلیت‌های فوق‌پیشرفته"""
    
    def __init__(self, token: str):
        self.token = token
        self.bot = telebot.TeleBot(token, threaded=False)
        
        # مغز اصلی
        self.brain = NeuroSymbolicBrain()
        
        # تحلیلگر رفتار
        self.behavior_analyzer = BehaviorAnalyzer()
        
        # صف پیام‌ها
        self.message_queue = queue.Queue()
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        
        # آمار
        self.stats = {
            'total_messages': 0,
            'processed_messages': 0,
            'learned_automatically': 0
        }
        
        # تنظیم هندلرها
        self._setup_handlers()
        
        logger.info("🤖 ربات فوق‌پیشرفته راه‌اندازی شد")
    
    def _setup_handlers(self):
        """تنظیم هندلرهای پیام"""
        
        @self.bot.message_handler(commands=['start'])
        def start_handler(message):
            welcome = """
🧠 **به هوش مصنوعی فوق‌پیشرفته MON خوش آمدید!**

من یک هوش مصنوعی هستم که **هر روز یاد می‌گیرم** و **هوشمندتر می‌شوم**!

✨ **قابلیت‌های من:**
• 📝 **یادگیری خودکار** - از هر سوالی که می‌پرسید یاد می‌گیرم
• 🔍 **تحلیل عمیق** - دقیقاً متوجه می‌شوم چه می‌پرسید
• 🧠 **حافظه فوق‌پیشرفته** - هیچوقت چیزی را فراموش نمی‌کنم
• 📊 **تحلیل رفتار** - به شما کمک می‌کنم بهتر یاد بگیرید

💡 **هر چه بیشتر سوال بپرسید، من هوشمندتر می‌شوم!**

**چطور استفاده کنم؟**
فقط سوال خود را بپرسید، من یاد می‌گیرم و پاسخ می‌دهم.

---
📌 *یادتان باشد: هر سوالی می‌پرسید، به دانش من اضافه می‌شود!*
"""
            self.bot.send_message(
                message.chat.id,
                welcome,
                parse_mode='Markdown',
                reply_markup=self._get_main_keyboard()
            )
            
            # ثبت کاربر جدید
            self._register_user(message.chat.id)
        
        @self.bot.message_handler(commands=['learn'])
        def learn_handler(message):
            """یادگیری دستی از کاربر"""
            try:
                # استخراج سوال و جواب
                text = message.text.replace('/learn', '').strip()
                if '|' not in text:
                    self.bot.reply_to(
                        message,
                        "❌ فرمت: `/learn سوال | پاسخ`\nمثال: `/learn سلام | سلام علیک`",
                        parse_mode='Markdown'
                    )
                    return
                
                question, answer = text.split('|', 1)
                question = question.strip()
                answer = answer.strip()
                
                if not question or not answer:
                    self.bot.reply_to(
                        message,
                        "❌ سوال و پاسخ را کامل وارد کنید!",
                        parse_mode='Markdown'
                    )
                    return
                
                # ذخیره در مغز
                self.brain._deep_analyze(question)
                self.brain.auto_learn(question, answer)
                
                self.bot.reply_to(
                    message,
                    f"✅ **یاد گرفتم!**\n\nسوال: {question}\nپاسخ: {answer}\n\n📚 دانش من بیشتر شد!",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                self.bot.reply_to(
                    message,
                    f"❌ خطا: {str(e)}",
                    parse_mode='Markdown'
                )
        
        @self.bot.message_handler(commands=['stats'])
        def stats_handler(message):
            """نمایش آمار"""
            stats = self.brain.get_stats()
            
            stat_text = f"""
📊 **آمار هوش مصنوعی MON**

🧠 **دانش من:**
• تعداد دانش: {stats.get('total_knowledge', 0)} مورد
• یادگیری خودکار: {stats.get('auto_learned', 0)} مورد
• یادگیری دستی: {stats.get('user_taught', 0)} مورد

📈 **عملکرد:**
• نرخ موفقیت: {stats.get('success_rate', 0)*100:.1f}%
• میانگین اطمینان: {stats.get('avg_confidence', 0)*100:.1f}%
• اندازه کش: {stats.get('cache_size', 0)} مورد

👥 **کاربران:**
• تعداد کاربران: {stats.get('total_profiles', 0)} نفر

---
💪 *هر روز قوی‌تر می‌شوم!*
"""
            self.bot.send_message(
                message.chat.id,
                stat_text,
                parse_mode='Markdown'
            )
        
        @self.bot.message_handler(commands=['insight'])
        def insight_handler(message):
            """نمایش بینش از رفتار کاربر"""
            insight = self.behavior_analyzer.get_user_insights(message.chat.id)
            
            if insight.get('status') == 'new_user':
                self.bot.reply_to(
                    message,
                    "📊 **تحلیل رفتار شما**\n\nشما کاربر جدیدی هستید!\nهرچه بیشتر سوال بپرسید، تحلیل دقیق‌تری خواهم داشت.",
                    parse_mode='Markdown'
                )
                return
            
            insight_text = f"""
📊 **تحلیل رفتار شما**

📝 **آمار سوالات:**
• تعداد کل: {insight.get('total_queries', 0)}
• میانگین طول سوال: {insight.get('avg_length', 0):.1f} کلمه

🎯 **علایق شما:**
"""
            for interest in insight.get('interests', [])[:5]:
                insight_text += f"• {interest['word']} ({interest['count']} بار)\n"
            
            insight_text += """
---
💡 *هر چه بیشتر بپرسید، بهتر می‌توانم به شما کمک کنم!*
"""
            self.bot.send_message(
                message.chat.id,
                insight_text,
                parse_mode='Markdown'
            )
        
        @self.bot.message_handler(commands=['help'])
        def help_handler(message):
            """راهنما"""
            help_text = """
📖 **راهنمای ربات MON**

**دستورات:**
• `/start` - شروع مجدد
• `/learn سوال | پاسخ` - به من یاد بده
• `/stats` - آمار عملکرد
• `/insight` - تحلیل رفتار شما
• `/help` - این راهنما

**چگونه استفاده کنم؟**
1️⃣ سوال خود را بپرسید
2️⃣ من تحلیل می‌کنم و پاسخ می‌دهم
3️⃣ اگر پاسخ را نمی‌دانم، با `/learn` به من یاد دهید

**نکات مهم:**
• هرچه بیشتر بپرسید، هوشمندتر می‌شوم
• من از هر سوالی یاد می‌گیرم
• هیچوقت چیزی را فراموش نمی‌کنم

---
💪 *با هم هوشمندتر می‌شویم!*
"""
            self.bot.send_message(
                message.chat.id,
                help_text,
                parse_mode='Markdown'
            )
        
        @self.bot.message_handler(func=lambda m: True)
        def message_handler(message):
            """پردازش پیام‌های عادی"""
            self.message_queue.put(message)
    
    def _get_main_keyboard(self):
        """کیبورد اصلی"""
        keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [
            KeyboardButton("💬 سوال بپرس"),
            KeyboardButton("📊 آمار من"),
            KeyboardButton("🎯 علایق من"),
            KeyboardButton("📖 راهنما")
        ]
        keyboard.add(*buttons)
        return keyboard
    
    def _process_queue(self):
        """پردازش صف پیام‌ها"""
        while True:
            try:
                message = self.message_queue.get(timeout=1)
                self._handle_message(message)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ خطا در پردازش صف: {e}")
    
    def _handle_message(self, message):
        """پردازش هوشمند پیام"""
        try:
            user_id = message.chat.id
            user_text = message.text
            
            # پردازش کیبورد
            if user_text == "💬 سوال بپرس":
                self.bot.send_message(user_id, "📝 سوال خود را بپرسید:")
                return
            
            if user_text == "📊 آمار من":
                self.bot.send_message(user_id, "📊 در حال دریافت آمار...")
                stats_handler = self._get_handler('stats')
                if stats_handler:
                    stats_handler(message)
                return
            
            if user_text == "🎯 علایق من":
                insight_handler = self._get_handler('insight')
                if insight_handler:
                    insight_handler(message)
                return
            
            if user_text == "📖 راهنما":
                help_handler = self._get_handler('help')
                if help_handler:
                    help_handler(message)
                return
            
            # پردازش سوال اصلی
            self.bot.send_chat_action(user_id, 'typing')
            
            # جستجوی هوشمند
            result = self.brain.search(user_text)
            
            # تحلیل رفتار
            profile = self.brain.analyze_user_behavior(
                user_id,
                user_text,
                result['response'],
                result['found']
            )
            
            # ساخت پاسخ هوشمند
            response = self._build_intelligent_response(result, profile, user_text)
            
            # ارسال پاسخ
            self.bot.send_message(
                user_id,
                response,
                parse_mode='Markdown',
                reply_markup=self._get_main_keyboard()
            )
            
            # به‌روزرسانی آمار
            self.stats['total_messages'] += 1
            if result['found']:
                self.stats['processed_messages'] += 1
            
            # یادگیری خودکار در صورت عدم وجود پاسخ
            if not result['found']:
                self.stats['learned_automatically'] += 1
                logger.info(f"🤖 یادگیری خودکار: {user_text[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ خطا در پردازش پیام: {e}")
            self.bot.send_message(
                message.chat.id,
                "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
                reply_markup=self._get_main_keyboard()
            )
    
    def _build_intelligent_response(self, result: Dict, profile: UserProfile, query: str) -> str:
        """ساخت پاسخ هوشمند بر اساس زمینه"""
        # پاسخ اصلی
        if result['found']:
            main_response = result['response']
        else:
            main_response = result['response']
        
        # اضافه کردن پیام‌های هوشمند بر اساس رفتار کاربر
        messages = [main_response]
        
        # اگر کاربر جدید است
        if profile.behavior == UserBehavior.NEW:
            messages.append("\n💡 **نکته:** من تازه با شما آشنا شدم! هرچه بیشتر بپرسید، بهتر می‌توانم کمک کنم.")
        
        # اگر کاربر نیازمند راهنما است
        elif profile.behavior == UserBehavior.NEEDY:
            messages.append("\n🔍 **راهنمایی:** می‌توانید با دستور `/learn` به من یاد دهید تا بهتر پاسخ دهم.")
        
        # اگر کاربر حرفه‌ای است
        elif profile.behavior == UserBehavior.EXPERT:
            messages.append("\n🌟 **عالی!** شما کاربر حرفه‌ای هستید. سوالات خوبی می‌پرسید!")
        
        # اگر پاسخ پیدا نشد
        if not result['found']:
            messages.append("\n📚 **یادگیری:** من این سوال را یاد گرفتم تا دفعه بعد بهتر پاسخ دهم.")
        
        # اضافه کردن آمار شخصی
        if profile.total_queries % 10 == 0:
            messages.append(f"\n📊 **آمار شما:** {profile.total_queries} سوال پرسیده‌اید! {profile.successful_queries} پاسخ مفید دریافت کردید.")
        
        return "".join(messages)
    
    def _get_handler(self, command: str):
        """دریافت هندلر دستور"""
        handlers = {
            'stats': None,
            'insight': None,
            'help': None
        }
        return handlers.get(command)
    
    def _register_user(self, user_id: int):
        """ثبت کاربر جدید"""
        try:
            profile = self.brain._get_user_profile(user_id)
            if profile.total_queries == 0:
                logger.info(f"👤 کاربر جدید: {user_id}")
        except Exception as e:
            logger.error(f"❌ خطا در ثبت کاربر: {e}")
    
    def run(self):
        """اجرای ربات"""
        logger.info("🚀 ربات در حال اجرا...")
        try:
            self.bot.polling(none_stop=True, interval=0, timeout=30)
        except Exception as e:
            logger.error(f"❌ خطا در اجرای ربات: {e}")
            self.bot.polling()

# ==================== پنل مدیریت ====================
class AdminPanel:
    """پنل مدیریت پیشرفته"""
    
    def __init__(self, bot_instance):
        self.app = Flask(__name__)
        self.app.secret_key = secrets.token_urlsafe(32)
        self.bot = bot_instance
        self.brain = bot_instance.brain
        
        CORS(self.app)
        self._setup_routes()
        
        logger.info("👑 پنل مدیریت راه‌اندازی شد")
    
    def _setup_routes(self):
        """تنظیم مسیرها"""
        
        @self.app.route('/')
        def index():
            return self._render_dashboard()
        
        @self.app.route('/api/stats')
        def api_stats():
            stats = self.brain.get_stats()
            return jsonify(stats)
        
        @self.app.route('/api/learn', methods=['POST'])
        def api_learn():
            data = request.json
            question = data.get('question')
            answer = data.get('answer')
            
            if not question or not answer:
                return jsonify({'error': 'سوال و پاسخ الزامی است'}), 400
            
            self.brain.auto_learn(question, answer)
            return jsonify({'success': True})
        
        @self.app.route('/api/knowledge')
        def api_knowledge():
            # دریافت لیست دانش
            knowledge = list(self.brain.knowledge_collection.find().limit(20))
            return jsonify([{
                'query': k.get('query'),
                'response': k.get('response')[:100],
                'keywords': k.get('keywords', [])
            } for k in knowledge])
        
        @self.app.route('/api/profile/<int:user_id>')
        def api_profile(user_id):
            profile = self.brain._get_user_profile(user_id)
            return jsonify(profile.to_dict() if profile else {})
    
    def _render_dashboard(self):
        """رندر داشبورد"""
        return """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 داشبورد MON</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Vazir', Tahoma, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: rgba(255,255,255,0.95);
            padding: 25px;
            border-radius: 20px;
            margin-bottom: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        .header h1 {
            color: #2d3748;
            font-size: 28px;
        }
        .header .subtitle {
            color: #718096;
            margin-top: 5px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .card {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
        }
        .card h3 {
            color: #2d3748;
            margin-bottom: 15px;
            font-size: 18px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        input, textarea, select {
            width: 100%;
            padding: 12px 15px;
            margin: 8px 0;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            font-size: 14px;
            transition: border-color 0.3s;
            font-family: inherit;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
            margin-top: 10px;
        }
        button:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 15px;
        }
        .stat-item {
            background: #f7fafc;
            padding: 15px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-number {
            font-size: 30px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label {
            color: #718096;
            font-size: 13px;
            margin-top: 5px;
        }
        .alert {
            padding: 12px 18px;
            border-radius: 12px;
            margin: 10px 0;
            display: none;
        }
        .alert-success {
            background: #c6f6d5;
            color: #22543d;
            border: 1px solid #9ae6b4;
        }
        .alert-error {
            background: #fed7d7;
            color: #9b2c2c;
            border: 1px solid #feb2b2;
        }
        .knowledge-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .knowledge-item {
            padding: 10px;
            border-bottom: 1px solid #e2e8f0;
        }
        .knowledge-item .q {
            color: #2d3748;
            font-weight: bold;
        }
        .knowledge-item .a {
            color: #718096;
            font-size: 13px;
            margin-top: 3px;
        }
        .knowledge-item .tags {
            margin-top: 5px;
        }
        .tag {
            display: inline-block;
            background: #e2e8f0;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 11px;
            color: #4a5568;
            margin: 2px;
        }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🧠 داشبورد هوش مصنوعی MON</h1>
            <div class="subtitle">سیستم یادگیری خودکار فوق‌پیشرفته</div>
        </div>
        
        <!-- Stats -->
        <div class="grid">
            <div class="card">
                <h3>📊 آمار کلی</h3>
                <div class="stats-grid" id="statsGrid">
                    <div class="stat-item">
                        <div class="stat-number" id="totalKnowledge">0</div>
                        <div class="stat-label">دانش</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="autoLearned">0</div>
                        <div class="stat-label">یادگیری خودکار</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="successRate">0%</div>
                        <div class="stat-label">نرخ موفقیت</div>
                    </div>
                </div>
                <button onclick="loadStats()">🔄 بروزرسانی</button>
            </div>
            
            <!-- Learn -->
            <div class="card">
                <h3>📝 یاد دادن به هوش مصنوعی</h3>
                <input type="text" id="questionInput" placeholder="سوال را وارد کنید...">
                <textarea id="answerInput" rows="3" placeholder="پاسخ دقیق..."></textarea>
                <button onclick="learnQA()">📚 یاد بده</button>
                <div id="learnResult" class="alert"></div>
            </div>
        </div>
        
        <!-- Knowledge List -->
        <div class="card">
            <h3>📚 دانش ذخیره شده</h3>
            <div class="knowledge-list" id="knowledgeList">
                <div style="text-align:center;color:#a0aec0;padding:20px;">
                    در حال بارگذاری...
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // ==================== توابع اصلی ====================
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    }
                };
                if (data) {
                    options.body = JSON.stringify(data);
                }
                const response = await fetch(endpoint, options);
                return await response.json();
            } catch (error) {
                console.error('❌ خطا:', error);
                return null;
            }
        }
        
        // ==================== بارگذاری آمار ====================
        async function loadStats() {
            const stats = await apiCall('/api/stats');
            if (stats) {
                document.getElementById('totalKnowledge').textContent = stats.total_knowledge || 0;
                document.getElementById('autoLearned').textContent = stats.auto_learned || 0;
                document.getElementById('successRate').textContent = 
                    stats.success_rate ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%';
            }
        }
        
        // ==================== یادگیری ====================
        async function learnQA() {
            const question = document.getElementById('questionInput').value;
            const answer = document.getElementById('answerInput').value;
            
            if (!question || !answer) {
                showResult('learnResult', '❌ سوال و پاسخ را کامل کنید!', 'error');
                return;
            }
            
            const result = await apiCall('/api/learn', 'POST', {
                question: question,
                answer: answer
            });
            
            if (result && result.success) {
                showResult('learnResult', '✅ با موفقیت یاد گرفتم!', 'success');
                document.getElementById('questionInput').value = '';
                document.getElementById('answerInput').value = '';
                loadKnowledge();
                loadStats();
            } else {
                showResult('learnResult', '❌ خطا در یادگیری!', 'error');
            }
        }
        
        // ==================== بارگذاری دانش ====================
        async function loadKnowledge() {
            const data = await apiCall('/api/knowledge');
            const list = document.getElementById('knowledgeList');
            
            if (data && data.length > 0) {
                list.innerHTML = data.map(item => `
                    <div class="knowledge-item">
                        <div class="q">❓ ${item.query}</div>
                        <div class="a">💡 ${item.response}</div>
                        <div class="tags">
                            ${item.keywords.map(k => `<span class="tag">#${k}</span>`).join('')}
                        </div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div style="text-align:center;color:#a0aec0;padding:20px;">هنوز دانشی ذخیره نشده است</div>';
            }
        }
        
        // ==================== نمایش پیام ====================
        function showResult(elementId, message, type = 'success') {
            const el = document.getElementById(elementId);
            el.textContent = message;
            el.className = `alert alert-${type}`;
            el.style.display = 'block';
            setTimeout(() => {
                el.style.display = 'none';
            }, 4000);
        }
        
        // ==================== بارگذاری اولیه ====================
        loadStats();
        loadKnowledge();
        
        // بروزرسانی خودکار هر 10 ثانیه
        setInterval(() => {
            loadStats();
        }, 10000);
    </script>
</body>
</html>
        """
    
    def run(self, host='0.0.0.0', port=5000):
        """اجرای پنل"""
        self.app.run(host=host, port=port, debug=False, threaded=True)

# ==================== اجرای اصلی ====================
if __name__ == "__main__":
    try:
        logger.info("🚀 راه‌اندازی سیستم فوق‌پیشرفته MON...")
        
        # راه‌اندازی ربات
        bot = UltraTelegramBot("8691128478:AAE7eZ0vo5kkFcvrerHt3vjw-mvJ3CqxpWE")
        
        # راه‌اندازی پنل مدیریت
        admin = AdminPanel(bot)
        
        # اجرا در تردهای جداگانه
        import threading
        bot_thread = threading.Thread(target=bot.run, daemon=True)
        bot_thread.start()
        
        logger.info("👑 پنل مدیریت در http://localhost:5000")
        admin.run()
        
    except KeyboardInterrupt:
        logger.info("👋 سیستم متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطا: {e}")
