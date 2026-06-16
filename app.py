"""
🤖 هوش مصنوعی MON تلگرام - نسخه فوق‌پیشرفته با معماری میکروسرویس
طراحی شده با بالاترین تکنولوژی برای یادگیری و پاسخگویی هوشمند
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
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import logging
import pickle
from pathlib import Path

# ==================== کتابخانه‌های اصلی ====================
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== دیتابیس و کش ====================
import redis
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import sqlite3
from elasticsearch import Elasticsearch, helpers

# ==================== پردازش زبان طبیعی ====================
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import jieba  # برای تجزیه کلمات فارسی
import hazm  # برای پردازش زبان فارسی
from transformers import AutoTokenizer, AutoModel  # برای embedding

# ==================== وب سرویس ====================
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import jwt
from functools import wraps
import secrets

# ==================== ابزارهای کمکی ====================
import requests
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# ==================== تنظیمات لاگ ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== تنظیمات اصلی ====================
class Config:
    """تنظیمات مرکزی سیستم"""
    # تلگرام
    TELEGRAM_TOKEN = "8691128478:AAE7eZ0vo5kkFcvrerHt3vjw-mvJ3CqxpWE"
    ADMIN_IDS = [327855654, ]  # آیدی ادمین‌ها
    
    # دیتابیس‌ها
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    
    MONGODB_URI = "mongodb://localhost:27017"
    MONGODB_DB = "ai_brain"
    
    ELASTICSEARCH_HOST = "http://localhost:9200"
    
    # امنیت
    JWT_SECRET = secrets.token_urlsafe(32)
    JWT_EXPIRATION = 3600  # 1 ساعت
    
    # مسیرها
    KNOWLEDGE_PATH = "./knowledge"
    FILES_PATH = "./files"
    MODELS_PATH = "./models"
    BACKUP_PATH = "./backups"
    
    # تنظیمات هوش مصنوعی
    MEMORY_THRESHOLD = 0.6
    KEYWORD_BOOST = 2.0
    MAX_RESULTS = 10
    LEARNING_RATE = 0.1
    
    # ایجاد پوشه‌ها
    for path in [KNOWLEDGE_PATH, FILES_PATH, MODELS_PATH, BACKUP_PATH]:
        Path(path).mkdir(parents=True, exist_ok=True)

# ==================== کلاس‌های اصلی دیتا ====================
@dataclass
class KnowledgeItem:
    """ساختار دانش"""
    id: str
    question: str
    answer: str
    category: str
    keywords: List[str]
    embedding: List[float]
    usage_count: int
    created_at: datetime
    updated_at: datetime
    weight: float = 1.0
    
    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'category': self.category,
            'keywords': self.keywords,
            'embedding': self.embedding,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'weight': self.weight
        }

@dataclass
class KeywordItem:
    """ساختار کلمات کلیدی"""
    keyword: str
    response: str
    category: str
    weight: float
    related: List[str]
    created_at: datetime
    
    def to_dict(self):
        return {
            'keyword': self.keyword,
            'response': self.response,
            'category': self.category,
            'weight': self.weight,
            'related': self.related,
            'created_at': self.created_at.isoformat()
        }

# ==================== مغز اول: حافظه فوق‌پیشرفته ====================
class UltraMemory:
    """مغز حافظه با قابلیت‌های فوق‌پیشرفته"""
    
    def __init__(self):
        self.redis = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            decode_responses=True,
            socket_keepalive=True,
            socket_timeout=10
        )
        
        # مدل‌های NLP
        self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
        self.model = AutoModel.from_pretrained("distilbert-base-uncased")
        
        # Cache برای سرعت بیشتر
        self.cache = {}
        self.cache_size = 1000
        
        logger.info("🧠 مغز حافظه فوق‌پیشرفته راه‌اندازی شد")
    
    def save_qa(self, question: str, answer: str, category: str = "general") -> str:
        """ذخیره سوال و جواب با تحلیل عمیق"""
        try:
            # تولید ID یکتا
            q_id = hashlib.sha256(f"{question}{datetime.now().isoformat()}".encode()).hexdigest()
            
            # استخراج کلمات کلیدی پیشرفته
            keywords = self._extract_keywords_advanced(question)
            
            # تولید embedding
            embedding = self._generate_embedding(question)
            
            # ایجاد آیتم دانش
            item = KnowledgeItem(
                id=q_id,
                question=question,
                answer=answer,
                category=category,
                keywords=keywords,
                embedding=embedding.tolist(),
                usage_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                weight=1.0
            )
            
            # ذخیره در Redis با ساختار پیشرفته
            key = f"qa:{q_id}"
            self.redis.hset(key, mapping=item.to_dict())
            
            # ایندکس‌گذاری کلمات کلیدی
            for keyword in keywords:
                self.redis.sadd(f"index:{keyword}", q_id)
                # ذخیره وزنی
                self.redis.zadd(f"weight:{keyword}", {q_id: 1.0})
            
            # ذخیره در کش
            self.cache[question] = item
            
            # اطمینان از permanence
            self.redis.persist(key)
            
            logger.info(f"✅ دانش جدید ذخیره شد: {question[:50]}...")
            return q_id
            
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره‌سازی: {e}")
            return None
    
    def search(self, query: str, threshold: float = 0.6) -> List[Dict]:
        """جستجوی هوشمند با ترکیب چندین روش"""
        try:
            # روش ۱: جستجوی کلمات کلیدی
            keyword_results = self._keyword_search(query)
            
            # روش ۲: جستجوی معنایی (embedding)
            semantic_results = self._semantic_search(query)
            
            # روش ۳: جستجوی ترکیبی
            combined_results = self._combined_search(query)
            
            # ادغام و امتیازدهی
            all_results = self._merge_results(
                keyword_results,
                semantic_results,
                combined_results
            )
            
            # فیلتر بر اساس آستانه
            filtered = [r for r in all_results if r.get('score', 0) >= threshold]
            
            # مرتب‌سازی نهایی
            sorted_results = sorted(
                filtered,
                key=lambda x: (x['score'], x.get('usage_count', 0)),
                reverse=True
            )
            
            # آپدیت تعداد استفاده
            if sorted_results:
                best = sorted_results[0]
                self._increment_usage(best['id'])
            
            return sorted_results[:Config.MAX_RESULTS]
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجو: {e}")
            return []
    
    def _keyword_search(self, query: str) -> List[Dict]:
        """جستجوی مبتنی بر کلمات کلیدی"""
        keywords = self._extract_keywords_advanced(query)
        results = []
        
        for keyword in keywords:
            q_ids = self.redis.smembers(f"index:{keyword}")
            for q_id in q_ids:
                data = self.redis.hgetall(f"qa:{q_id}")
                if data:
                    score = self._calculate_keyword_score(query, data['question'], keywords)
                    results.append({
                        'id': q_id,
                        'question': data['question'],
                        'answer': data['answer'],
                        'score': score,
                        'usage_count': int(data.get('usage_count', 0))
                    })
        
        # حذف تکراری‌ها
        seen = set()
        unique_results = []
        for r in results:
            if r['id'] not in seen:
                seen.add(r['id'])
                unique_results.append(r)
        
        return unique_results
    
    def _semantic_search(self, query: str) -> List[Dict]:
        """جستجوی معنایی با استفاده از embedding"""
        query_embedding = self._generate_embedding(query)
        
        # گرفتن همه آیتم‌ها (برای دقت بالا)
        all_items = []
        keys = self.redis.keys("qa:*")
        
        for key in keys:
            data = self.redis.hgetall(key)
            if data:
                # تبدیل embedding از string به list
                embedding = json.loads(data.get('embedding', '[]'))
                if embedding:
                    similarity = cosine_similarity(
                        [query_embedding],
                        [embedding]
                    )[0][0]
                    
                    all_items.append({
                        'id': data['id'],
                        'question': data['question'],
                        'answer': data['answer'],
                        'score': similarity,
                        'usage_count': int(data.get('usage_count', 0))
                    })
        
        return sorted(all_items, key=lambda x: x['score'], reverse=True)[:Config.MAX_RESULTS]
    
    def _combined_search(self, query: str) -> List[Dict]:
        """جستجوی ترکیبی با روش‌های مختلف"""
        # ترکیب نتایج keyword و semantic
        keyword_results = self._keyword_search(query)
        semantic_results = self._semantic_search(query)
        
        return self._merge_results(keyword_results, semantic_results, [])
    
    def _merge_results(self, *result_lists) -> List[Dict]:
        """ادغام هوشمند نتایج مختلف"""
        merged = {}
        
        for results in result_lists:
            for r in results:
                q_id = r['id']
                if q_id not in merged:
                    merged[q_id] = r
                    merged[q_id]['score'] = 0
                
                # ترکیب امتیازات با وزن‌های مختلف
                if 'score' in r:
                    merged[q_id]['score'] += r['score'] * 0.5
        
        return list(merged.values())
    
    def _extract_keywords_advanced(self, text: str) -> List[str]:
        """استخراج کلمات کلیدی با روش‌های پیشرفته"""
        # پاکسازی متن
        text = re.sub(r'[^\w\s]', '', text)
        
        # تجزیه با hazm
        normalizer = hazm.Normalizer()
        text = normalizer.normalize(text)
        
        # استفاده از jieba برای کلمات کلیدی
        words = jieba.cut(text)
        
        # حذف کلمات بی‌معنی
        stopwords = set(hazm.stopwords_list())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # TF-IDF برای کلمات مهم‌تر
        if len(keywords) > 5:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([' '.join(keywords)])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # انتخاب کلمات با بالاترین TF-IDF
            important = sorted(
                zip(feature_names, tfidf_scores),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            keywords = [k for k, _ in important]
        
        return keywords[:10]
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """تولید embedding با استفاده از transformer"""
        try:
            # Tokenize
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            # تولید embedding
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).detach().numpy()
            
            return embedding[0]
            
        except Exception as e:
            logger.error(f"❌ خطا در تولید embedding: {e}")
            # Fallback به روش ساده
            return np.random.randn(768)
    
    def _calculate_keyword_score(self, query: str, stored_q: str, query_keywords: List[str]) -> float:
        """محاسبه امتیاز بر اساس کلمات کلیدی"""
        stored_keywords = self._extract_keywords_advanced(stored_q)
        
        # Jaccard similarity
        intersection = set(query_keywords) & set(stored_keywords)
        union = set(query_keywords) | set(stored_keywords)
        
        if not union:
            return 0.0
        
        jaccard = len(intersection) / len(union)
        
        # ضریب تشابه متنی
        text_sim = self._text_similarity(query, stored_q)
        
        # ترکیب امتیازات
        final_score = (jaccard * 0.7) + (text_sim * 0.3)
        
        return final_score
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """محاسبه شباهت متنی"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _increment_usage(self, q_id: str):
        """افزایش شمارنده استفاده"""
        try:
            key = f"qa:{q_id}"
            self.redis.hincrby(key, 'usage_count', 1)
            
            # به‌روزرسانی زمان
            self.redis.hset(key, 'updated_at', datetime.now().isoformat())
            
        except Exception as e:
            logger.error(f"❌ خطا در بروزرسانی استفاده: {e}")
    
    def get_statistics(self) -> Dict:
        """دریافت آمار حافظه"""
        try:
            total_items = len(self.redis.keys("qa:*"))
            total_keywords = len(self.redis.keys("index:*"))
            
            # بیشترین سوالات استفاده شده
            usage_stats = []
            keys = self.redis.keys("qa:*")
            for key in keys:
                data = self.redis.hgetall(key)
                if data:
                    usage_stats.append({
                        'question': data.get('question', ''),
                        'usage_count': int(data.get('usage_count', 0))
                    })
            
            usage_stats.sort(key=lambda x: x['usage_count'], reverse=True)
            
            return {
                'total_items': total_items,
                'total_keywords': total_keywords,
                'most_used': usage_stats[:10],
                'cache_size': len(self.cache)
            }
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت آمار: {e}")
            return {}

# ==================== مغز دوم: کلمات کلیدی فوق‌پیشرفته ====================
class UltraKeywordBrain:
    """مغز کلمات کلیدی با Elasticsearch و الگوریتم‌های پیشرفته"""
    
    def __init__(self):
        self.es = Elasticsearch([Config.ELASTICSEARCH_HOST])
        self._create_index()
        self.keyword_cache = {}
        
        # مدل پیشرفته برای کلمات کلیدی
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.keyword_vectors = None
        
        logger.info("🔑 مغز کلمات کلیدی فوق‌پیشرفته راه‌اندازی شد")
    
    def _create_index(self):
        """ایجاد ایندکس با تنظیمات پیشرفته"""
        settings = {
            'settings': {
                'number_of_shards': 2,
                'number_of_replicas': 1,
                'analysis': {
                    'analyzer': {
                        'persian_analyzer': {
                            'type': 'custom',
                            'tokenizer': 'standard',
                            'filter': ['lowercase', 'stop', 'persian_stemmer']
                        }
                    },
                    'filter': {
                        'persian_stemmer': {
                            'type': 'stemmer',
                            'language': 'persian'
                        }
                    }
                }
            },
            'mappings': {
                'properties': {
                    'keyword': {
                        'type': 'text',
                        'analyzer': 'persian_analyzer',
                        'fields': {
                            'keyword': {'type': 'keyword'},
                            'completion': {'type': 'completion'}
                        }
                    },
                    'response': {'type': 'text', 'analyzer': 'persian_analyzer'},
                    'category': {'type': 'keyword'},
                    'weight': {'type': 'float'},
                    'related_keywords': {'type': 'keyword'},
                    'created_at': {'type': 'date'},
                    'usage_count': {'type': 'integer'},
                    'embedding': {'type': 'dense_vector', 'dims': 768}
                }
            }
        }
        
        if not self.es.indices.exists(index='ultra_keywords'):
            self.es.indices.create(index='ultra_keywords', body=settings)
    
    def add_keyword(self, keyword: str, response: str, category: str = "general", weight: float = 1.0):
        """افزودن کلمه کلیدی با تحلیل عمیق"""
        try:
            # تولید embedding برای کلمه
            embedding = self._generate_keyword_embedding(keyword)
            
            # پیدا کردن کلمات مرتبط
            related = self._find_related_keywords(keyword)
            
            doc = {
                'keyword': keyword,
                'response': response,
                'category': category,
                'weight': weight,
                'related_keywords': related,
                'created_at': datetime.now().isoformat(),
                'usage_count': 0,
                'embedding': embedding
            }
            
            # ذخیره در Elasticsearch
            doc_id = hashlib.md5(keyword.encode()).hexdigest()
            self.es.index(index='ultra_keywords', id=doc_id, body=doc)
            
            # ذخیره در کش
            self.keyword_cache[keyword] = response
            
            logger.info(f"✅ کلمه کلیدی ذخیره شد: {keyword}")
            
        except Exception as e:
            logger.error(f"❌ خطا در افزودن کلمه کلیدی: {e}")
    
    def search_keywords(self, query: str, min_score: float = 0.3) -> List[Dict]:
        """جستجوی پیشرفته کلمات کلیدی با ترکیب روش‌ها"""
        try:
            # روش ۱: جستجوی فازی
            fuzzy_results = self._fuzzy_search(query)
            
            # روش ۲: جستجوی معنایی
            semantic_results = self._semantic_search(query)
            
            # روش ۳: جستجوی مرتبط
            related_results = self._related_search(query)
            
            # ادغام نتایج
            merged = self._merge_keyword_results(
                fuzzy_results,
                semantic_results,
                related_results
            )
            
            # فیلتر بر اساس امتیاز
            filtered = [r for r in merged if r.get('score', 0) >= min_score]
            
            # مرتب‌سازی نهایی
            sorted_results = sorted(
                filtered,
                key=lambda x: (x['score'], x.get('weight', 0)),
                reverse=True
            )
            
            return sorted_results[:Config.MAX_RESULTS]
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی کلمات کلیدی: {e}")
            return []
    
    def _fuzzy_search(self, query: str) -> List[Dict]:
        """جستجوی فازی با Elasticsearch"""
        body = {
            'query': {
                'bool': {
                    'should': [
                        {
                            'match': {
                                'keyword': {
                                    'query': query,
                                    'fuzziness': 'AUTO',
                                    'boost': 2.0
                                }
                            }
                        },
                        {
                            'match_phrase': {
                                'keyword': {
                                    'query': query,
                                    'slop': 2,
                                    'boost': 3.0
                                }
                            }
                        }
                    ]
                }
            },
            'sort': [
                {'_score': {'order': 'desc'}},
                {'weight': {'order': 'desc'}}
            ],
            'size': 20
        }
        
        response = self.es.search(index='ultra_keywords', body=body)
        return [{
            'keyword': hit['_source']['keyword'],
            'response': hit['_source']['response'],
            'score': hit['_score'] / 10,
            'weight': hit['_source'].get('weight', 1.0)
        } for hit in response['hits']['hits']]
    
    def _semantic_search(self, query: str) -> List[Dict]:
        """جستجوی معنایی با embedding"""
        query_embedding = self._generate_keyword_embedding(query)
        
        body = {
            'query': {
                'script_score': {
                    'query': {'match_all': {}},
                    'script': {
                        'source': "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        'params': {'query_vector': query_embedding}
                    }
                }
            },
            'size': 20
        }
        
        response = self.es.search(index='ultra_keywords', body=body)
        return [{
            'keyword': hit['_source']['keyword'],
            'response': hit['_source']['response'],
            'score': hit['_score'] / 2,
            'weight': hit['_source'].get('weight', 1.0)
        } for hit in response['hits']['hits']]
    
    def _related_search(self, query: str) -> List[Dict]:
        """جستجوی کلمات مرتبط"""
        # پیدا کردن کلمات کلیدی مرتبط با query
        body = {
            'query': {
                'match': {
                    'related_keywords': query
                }
            },
            'size': 10
        }
        
        response = self.es.search(index='ultra_keywords', body=body)
        return [{
            'keyword': hit['_source']['keyword'],
            'response': hit['_source']['response'],
            'score': hit['_score'] / 10 * 0.8,
            'weight': hit['_source'].get('weight', 1.0)
        } for hit in response['hits']['hits']]
    
    def _merge_keyword_results(self, *result_lists) -> List[Dict]:
        """ادغام نتایج کلمات کلیدی"""
        merged = {}
        
        for results in result_lists:
            for r in results:
                keyword = r['keyword']
                if keyword not in merged:
                    merged[keyword] = r
                    merged[keyword]['score'] = 0
                
                merged[keyword]['score'] += r['score'] * 0.3
        
        return list(merged.values())
    
    def _generate_keyword_embedding(self, text: str) -> List[float]:
        """تولید embedding برای کلمات کلیدی"""
        # استفاده از مدل ساده‌تر برای سرعت
        from sklearn.feature_extraction.text import CountVectorizer
        vectorizer = CountVectorizer(max_features=768)
        embedding = vectorizer.fit_transform([text]).toarray()[0]
        return embedding.tolist() if len(embedding) == 768 else [0.0] * 768
    
    def _find_related_keywords(self, keyword: str) -> List[str]:
        """پیدا کردن کلمات مرتبط با استفاده از شباهت"""
        # جستجو در کش
        all_keywords = list(self.keyword_cache.keys())
        if not all_keywords:
            return [keyword]
        
        # محاسبه شباهت
        similar = []
        for k in all_keywords:
            similarity = self._text_similarity(keyword, k)
            if similarity > 0.5 and k != keyword:
                similar.append(k)
        
        return similar[:5]
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """محاسبه شباهت متنی"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_keyword_stats(self) -> Dict:
        """دریافت آمار کلمات کلیدی"""
        try:
            # تعداد کل کلمات
            response = self.es.count(index='ultra_keywords')
            total = response['count']
            
            # پرکاربردترین کلمات
            body = {
                'aggs': {
                    'top_keywords': {
                        'terms': {
                            'field': 'keyword.keyword',
                            'size': 10
                        }
                    }
                },
                'size': 0
            }
            
            response = self.es.search(index='ultra_keywords', body=body)
            top_keywords = [
                {'keyword': bucket['key'], 'count': bucket['doc_count']}
                for bucket in response['aggregations']['top_keywords']['buckets']
            ]
            
            return {
                'total_keywords': total,
                'top_keywords': top_keywords,
                'cache_size': len(self.keyword_cache)
            }
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت آمار کلمات کلیدی: {e}")
            return {}

# ==================== مغز سوم: یادگیری از فایل ====================
class UltraFileLearner:
    """مغز یادگیری از فایل با پردازش فوق‌پیشرفته"""
    
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URI)
        self.db = self.client[Config.MONGODB_DB]
        self.collection = self.db['file_knowledge']
        
        # ایجاد ایندکس‌های پیشرفته
        self.collection.create_index([('content', 'text')])
        self.collection.create_index('keywords')
        self.collection.create_index('category')
        self.collection.create_index('embedding')
        
        # مدل‌های پردازش
        self.tfidf_vectorizer = TfidfVectorizer(max_features=500)
        self.word_vectors = {}
        
        logger.info("📚 مغز یادگیری از فایل فوق‌پیشرفته راه‌اندازی شد")
    
    def learn_from_txt(self, file_path: str, category: str = "document") -> Dict:
        """یادگیری از فایل TXT با تحلیل عمیق"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # پیش‌پردازش
            processed = self._preprocess_text(content)
            
            # تقسیم به بخش‌های معنایی
            sections = self._split_semantic_sections(processed)
            
            results = []
            for section in sections:
                if len(section.strip()) < 20:
                    continue
                
                # استخراج کلمات کلیدی
                keywords = self._extract_keywords_advanced(section)
                
                # تولید embedding
                embedding = self._generate_embedding(section)
                
                doc = {
                    'content': section,
                    'category': category,
                    'keywords': keywords,
                    'embedding': embedding,
                    'source_file': file_path,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'usage_count': 0,
                    'weight': 1.0
                }
                
                # ذخیره در MongoDB
                doc_id = hashlib.md5(section.encode()).hexdigest()
                self.collection.update_one(
                    {'_id': doc_id},
                    {'$set': doc},
                    upsert=True
                )
                results.append(doc_id)
            
            logger.info(f"✅ یادگیری از فایل {file_path}: {len(results)} بخش")
            return {
                'file': file_path,
                'sections': len(results),
                'ids': results
            }
            
        except Exception as e:
            logger.error(f"❌ خطا در یادگیری از فایل: {e}")
            return {'error': str(e)}
    
    def learn_from_csv(self, file_path: str, question_col: str = 'question', answer_col: str = 'answer'):
        """یادگیری از فایل CSV"""
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            
            results = []
            for _, row in df.iterrows():
                question = row.get(question_col, '')
                answer = row.get(answer_col, '')
                
                if question and answer:
                    # ذخیره در حافظه اصلی
                    self._save_qa_pair(question, answer)
                    results.append({'question': question, 'answer': answer})
            
            logger.info(f"✅ یادگیری از CSV: {len(results)} جفت سوال-جواب")
            return {'total': len(results), 'results': results}
            
        except Exception as e:
            logger.error(f"❌ خطا در یادگیری از CSV: {e}")
            return {'error': str(e)}
    
    def learn_from_json(self, file_path: str):
        """یادگیری از فایل JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = []
            if isinstance(data, list):
                for item in data:
                    if 'question' in item and 'answer' in item:
                        self._save_qa_pair(item['question'], item['answer'])
                        results.append(item)
            
            logger.info(f"✅ یادگیری از JSON: {len(results)} جفت سوال-جواب")
            return {'total': len(results), 'results': results}
            
        except Exception as e:
            logger.error(f"❌ خطا در یادگیری از JSON: {e}")
            return {'error': str(e)}
    
    def learn_from_folder(self, folder_path: str, recursive: bool = True):
        """یادگیری از تمام فایل‌های یک پوشه"""
        try:
            results = []
            path = Path(folder_path)
            
            # فایل‌های پشتیبانی شده
            extensions = ['.txt', '.csv', '.json', '.md', '.docx']
            
            files = list(path.rglob('*')) if recursive else list(path.glob('*'))
            
            for file in files:
                if file.suffix in extensions:
                    if file.suffix == '.txt':
                        result = self.learn_from_txt(str(file))
                    elif file.suffix == '.csv':
                        result = self.learn_from_csv(str(file))
                    elif file.suffix == '.json':
                        result = self.learn_from_json(str(file))
                    else:
                        continue
                    
                    results.append({
                        'file': str(file),
                        'result': result
                    })
            
            logger.info(f"✅ یادگیری از پوشه {folder_path}: {len(results)} فایل")
            return {'total_files': len(results), 'results': results}
            
        except Exception as e:
            logger.error(f"❌ خطا در یادگیری از پوشه: {e}")
            return {'error': str(e)}
    
    def search_in_files(self, query: str, limit: int = 10) -> List[Dict]:
        """جستجوی پیشرفته در داده‌های یادگرفته شده"""
        try:
            # جستجوی متنی با MongoDB
            text_results = list(self.collection.find(
                {'$text': {'$search': query}},
                {'score': {'$meta': 'textScore'}}
            ).sort([('score', {'$meta': 'textScore'})]).limit(limit))
            
            # جستجوی کلمات کلیدی
            keywords = self._extract_keywords_advanced(query)
            keyword_results = list(self.collection.find({
                'keywords': {'$in': keywords}
            }).limit(limit))
            
            # جستجوی معنایی (embedding)
            query_embedding = self._generate_embedding(query)
            
            # ترکیب نتایج
            combined = {}
            for doc in text_results + keyword_results:
                doc_id = doc['_id']
                if doc_id not in combined:
                    combined[doc_id] = {
                        'content': doc.get('content', '')[:200] + '...',
                        'category': doc.get('category', 'unknown'),
                        'score': doc.get('score', 0)
                    }
                else:
                    combined[doc_id]['score'] += 0.5
            
            # تبدیل به لیست و مرتب‌سازی
            results = list(combined.values())
            results.sort(key=lambda x: x['score'], reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی فایل‌ها: {e}")
            return []
    
    def _preprocess_text(self, text: str) -> str:
        """پیش‌پردازش متن"""
        # حذف کاراکترهای اضافی
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'[^\w\s\.\?\!]', '', text)
        return text
    
    def _split_semantic_sections(self, text: str) -> List[str]:
        """تقسیم متن به بخش‌های معنایی"""
        # تقسیم بر اساس پاراگراف‌ها
        paragraphs = text.split('\n\n')
        
        # ترکیب پاراگراف‌های کوچک
        sections = []
        current = []
        
        for para in paragraphs:
            if len(para.strip()) > 50:
                if current:
                    sections.append('\n'.join(current))
                    current = []
                sections.append(para)
            else:
                current.append(para)
        
        if current:
            sections.append('\n'.join(current))
        
        return sections
    
    def _extract_keywords_advanced(self, text: str) -> List[str]:
        """استخراج پیشرفته کلمات کلیدی"""
        # ساده‌سازی
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        
        # حذف کلمات بی‌معنی
        stopwords = set(['و', 'با', 'به', 'از', 'برای', 'که', 'این', 'آن', 'در'])
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # TF-IDF برای انتخاب کلمات مهم
        if len(keywords) > 5:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([' '.join(keywords)])
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf.toarray()[0]
            
            # انتخاب کلمات با بالاترین امتیاز
            important = sorted(
                zip(feature_names, scores),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            keywords = [k for k, _ in important]
        
        return keywords
    
    def _generate_embedding(self, text: str) -> List[float]:
        """تولید embedding با روش ساده"""
        # برای سرعت بالا از روش ساده استفاده می‌کنیم
        words = text.split()[:50]  # محدودیت برای سرعت
        vector = [0.0] * 100
        
        for word in words:
            # هش کردن کلمه به عدد
            h = hash(word) % 100
            vector[h] += 1
        
        # نرمال‌سازی
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def _save_qa_pair(self, question: str, answer: str):
        """ذخیره جفت سوال-جواب در حافظه اصلی"""
        # اینجا می‌توانید به مغز حافظه متصل شوید
        logger.info(f"📝 ذخیره جفت سوال-جواب: {question[:50]}...")
    
    def get_file_stats(self) -> Dict:
        """دریافت آمار فایل‌ها"""
        try:
            total_docs = self.collection.count_documents({})
            
            # آمار بر اساس دسته‌بندی
            categories = self.collection.aggregate([
                {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
            ])
            
            return {
                'total_documents': total_docs,
                'categories': [{'category': c['_id'], 'count': c['count']} for c in categories],
                'collection_size': self.collection.count_documents({})
            }
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت آمار فایل‌ها: {e}")
            return {}

# ==================== ربات تلگرام اصلی ====================
class UltraTelegramBot:
    """ربات تلگرام با معماری فوق‌پیشرفته"""
    
    def __init__(self, token: str):
        self.token = token
        self.bot = telebot.TeleBot(token, threaded=False)
        
        # راه‌اندازی مغزها
        self.memory = UltraMemory()
        self.keyword_brain = UltraKeywordBrain()
        self.file_learner = UltraFileLearner()
        
        # صف پیام‌ها برای پردازش همزمان
        self.message_queue = queue.Queue()
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        
        # آمار
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'average_response_time': 0
        }
        
        # تنظیم هندلرها
        self._setup_handlers()
        
        logger.info("🤖 ربات تلگرام فوق‌پیشرفته راه‌اندازی شد")
    
    def _setup_handlers(self):
        """تنظیم هندلرهای پیام"""
        
        @self.bot.message_handler(commands=['start'])
        def start_handler(message):
            welcome = """
🤖 **به هوش مصنوعی MON تلگرام خوش آمدید!**

من یک هوش مصنوعی فوق‌پیشرفته هستم با قابلیت‌های:
• 🧠 **یادگیری عمیق** - از هر سوالی یاد می‌گیرم
• 🔑 **کلمات کلیدی** - دقیق‌ترین تشخیص
• 📚 **یادگیری از فایل** - از هر فایلی یاد می‌گیرم
• ⚡ **پاسخ سریع** - در کسری از ثانیه

**چطور می‌توانم کمک کنم؟**
فقط سوال خود را بپرسید...

💡 *هر چه بیشتر بپرسید، هوشمندتر می‌شوم!*
"""
            self.bot.send_message(
                message.chat.id,
                welcome,
                parse_mode='Markdown',
                reply_markup=self._get_main_keyboard()
            )
        
        @self.bot.message_handler(func=lambda m: True)
        def message_handler(message):
            # اضافه کردن به صف برای پردازش
            self.message_queue.put(message)
            
            # پاسخ اولیه (در حال پردازش)
            self.bot.send_chat_action(message.chat.id, 'typing')
    
    def _get_main_keyboard(self):
        """کیبورد اصلی"""
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [
            types.KeyboardButton("📝 سوال بپرس"),
            types.KeyboardButton("ℹ️ راهنما"),
            types.KeyboardButton("📊 آمار"),
            types.KeyboardButton("🔄 جدیدترین")
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
            start_time = datetime.now()
            user_id = message.chat.id
            user_text = message.text
            
            # تشخیص نوع پیام
            if user_text == "📝 سوال بپرس":
                self.bot.send_message(user_id, "سوال خود را بپرسید...")
                return
            
            if user_text == "ℹ️ راهنما":
                self._send_help(user_id)
                return
            
            if user_text == "📊 آمار":
                self._send_stats(user_id)
                return
            
            if user_text == "🔄 جدیدترین":
                self._send_latest(user_id)
                return
            
            # جستجوی هوشمند
            response = self._intelligent_search(user_text)
            
            # ارسال پاسخ
            self.bot.send_message(
                user_id,
                response,
                parse_mode='Markdown',
                reply_markup=self._get_main_keyboard()
            )
            
            # به‌روزرسانی آمار
            self._update_stats(start_time, response)
            
        except Exception as e:
            logger.error(f"❌ خطا در پردازش پیام: {e}")
            self.bot.send_message(
                message.chat.id,
                "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
                reply_markup=self._get_main_keyboard()
            )
    
    def _intelligent_search(self, query: str) -> str:
        """جستجوی هوشمند با ترکیب همه مغزها"""
        try:
            # ۱. جستجو در کلمات کلیدی (دقیق‌ترین)
            keyword_results = self.keyword_brain.search_keywords(query, min_score=0.3)
            
            # ۲. جستجو در حافظه اصلی
            memory_results = self.memory.search(query, threshold=0.6)
            
            # ۳. جستجو در فایل‌ها
            file_results = self.file_learner.search_in_files(query, limit=3)
            
            # ترکیب هوشمند پاسخ‌ها
            combined_response = self._combine_responses(
                keyword_results,
                memory_results,
                file_results,
                query
            )
            
            return combined_response
            
        except Exception as e:
            logger.error(f"❌ خطا در جستجوی هوشمند: {e}")
            return "⚠️ خطا در پردازش سوال. لطفاً دوباره تلاش کنید."
    
    def _combine_responses(self, keyword_results, memory_results, file_results, query) -> str:
        """ترکیب هوشمند نتایج از مغزهای مختلف"""
        parts = []
        
        # ۱. اولویت با کلمات کلیدی (دقیق‌ترین پاسخ)
        if keyword_results:
            best_keyword = keyword_results[0]
            parts.append(f"🎯 **پاسخ دقیق:**\n{best_keyword['response']}")
            
            # اضافه کردن کلمات مرتبط
            if len(keyword_results) > 1:
                related = "، ".join([r['keyword'] for r in keyword_results[1:3]])
                if related:
                    parts.append(f"📌 **کلمات مرتبط:** {related}")
        
        # ۲. پاسخ از حافظه (با امتیاز بالا)
        if memory_results:
            best_memory = memory_results[0]
            if best_memory.get('score', 0) > 0.7:
                parts.append(f"🧠 **از حافظه:**\n{best_memory['answer']}")
        
        # ۳. اطلاعات از فایل‌ها
        if file_results:
            best_file = file_results[0]
            if best_file.get('score', 0) > 0.5:
                parts.append(f"📚 **از دانشنامه:**\n{best_file['content'][:300]}...")
        
        # اگر هیچ نتیجه‌ای نداشتیم
        if not parts:
            return self._generate_fallback_response(query)
        
        # اضافه کردن پیشنهاد یادگیری
        parts.append("\n---\n💡 *اگر پاسخ دقیق‌تری می‌خواهید، با /learn به من یاد دهید.*")
        
        return "\n\n".join(parts)
    
    def _generate_fallback_response(self, query: str) -> str:
        """تولید پاسخ پیش‌فرض هوشمند"""
        return f"""
🤔 **هنوز جواب این سوال را یاد نگرفته‌ام.**

سوال شما: _{query}_

اما می‌توانید:
1️⃣ با دستور `/learn` به من یاد دهید
2️⃣ سوال را ساده‌تر بپرسید
3️⃣ از کلمات کلیدی دقیق‌تر استفاده کنید

💡 **هرچه بیشتر یادم دهید، هوشمندتر می‌شوم!**
"""
    
    def _send_help(self, user_id):
        """ارسال راهنما"""
        help_text = """
📖 **راهنمای ربات MON**

**چگونه از من استفاده کنید؟**

🔹 **پرسش سوال:**
فقط سوال خود را بپرسید. من هوشمندانه پاسخ می‌دهم.

🔹 **یاد دادن به من:**
از دستور `/learn سوال | پاسخ` استفاده کنید.

🔹 **یادگیری از فایل:**
فایل TXT خود را ارسال کنید تا از آن یاد بگیرم.

🔹 **کلمات کلیدی:**
می‌توانید کلمات کلیدی را به من یاد دهید تا دقیق‌تر پاسخ دهم.

🔹 **آمار:**
با دستور `/stats` آمار عملکرد من را ببینید.

---
**💡 نکته:** هرچه بیشتر از من استفاده کنید، هوشمندتر می‌شوم!
"""
        self.bot.send_message(user_id, help_text, parse_mode='Markdown')
    
    def _send_stats(self, user_id):
        """ارسال آمار"""
        # دریافت آمار از مغزها
        memory_stats = self.memory.get_statistics()
        keyword_stats = self.keyword_brain.get_keyword_stats()
        file_stats = self.file_learner.get_file_stats()
        
        stats_text = f"""
📊 **آمار عملکرد ربات**

🧠 **حافظه اصلی:**
• تعداد سوالات: {memory_stats.get('total_items', 0)}
• تعداد کلمات کلیدی: {memory_stats.get('total_keywords', 0)}
• اندازه کش: {memory_stats.get('cache_size', 0)}

🔑 **کلمات کلیدی:**
• تعداد کل: {keyword_stats.get('total_keywords', 0)}
• پرکاربردترین: {', '.join([k['keyword'] for k in keyword_stats.get('top_keywords', [])[:3]])}

📚 **فایل‌ها:**
• تعداد اسناد: {file_stats.get('total_documents', 0)}
• دسته‌بندی‌ها: {len(file_stats.get('categories', []))}

---
**آمار کلی سیستم:**
• کل سوالات: {self.stats['total_queries']}
• پاسخ‌های موفق: {self.stats['successful_queries']}
• میانگین زمان پاسخ: {self.stats['average_response_time']:.2f} ثانیه
"""
        self.bot.send_message(user_id, stats_text, parse_mode='Markdown')
    
    def _send_latest(self, user_id):
        """ارسال جدیدترین یادگیری‌ها"""
        latest = """
🔄 **جدیدترین یادگیری‌ها:**

اخیراً چیزهای جدیدی یاد گرفتم! 

📝 برای دیدن همه چیزهایی که یاد گرفتم:
• از من بپرسید
• یا با دستور `/stats` آمار را ببینید

💡 **نکته:** هر روز چیزهای جدیدی یاد می‌گیرم!
"""
        self.bot.send_message(user_id, latest, parse_mode='Markdown')
    
    def _update_stats(self, start_time: datetime, response: str):
        """به‌روزرسانی آمار"""
        elapsed = (datetime.now() - start_time).total_seconds()
        
        self.stats['total_queries'] += 1
        if "یاد نگرفته‌ام" not in response:
            self.stats['successful_queries'] += 1
        else:
            self.stats['failed_queries'] += 1
        
        # به‌روزرسانی میانگین زمان پاسخ
        total = self.stats['average_response_time'] * (self.stats['total_queries'] - 1)
        self.stats['average_response_time'] = (total + elapsed) / self.stats['total_queries']
    
    def run(self):
        """اجرای ربات"""
        logger.info("🚀 ربات در حال اجرا...")
        try:
            self.bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logger.error(f"❌ خطا در اجرای ربات: {e}")
            self.bot.polling()

# ==================== پنل مدیریت ====================
class AdminPanel:
    """پنل مدیریت فوق‌پیشرفته با Flask"""
    
    def __init__(self, bot_instance):
        self.app = Flask(__name__)
        self.app.secret_key = Config.JWT_SECRET
        self.bot = bot_instance
        
        # تنظیمات امنیتی
        CORS(self.app)
        
        # تنظیم مسیرها
        self._setup_routes()
        
        logger.info("👑 پنل مدیریت راه‌اندازی شد")
    
    def _setup_routes(self):
        """تنظیم مسیرهای پنل مدیریت"""
        
        @self.app.route('/')
        @self._admin_required
        def index():
            return self._render_admin_panel()
        
        @self.app.route('/api/learn', methods=['POST'])
        @self._admin_required
        def api_learn():
            data = request.json
            question = data.get('question')
            answer = data.get('answer')
            category = data.get('category', 'general')
            
            if not question or not answer:
                return jsonify({'error': 'سوال و جواب الزامی است'}), 400
            
            # ذخیره در مغزها
            self.bot.memory.save_qa(question, answer, category)
            self.bot.keyword_brain.add_keyword(question, answer, category)
            
            return jsonify({'success': True, 'message': '✅ یاد گرفتم!'})
        
        @self.app.route('/api/keyword', methods=['POST'])
        @self._admin_required
        def api_keyword():
            data = request.json
            keyword = data.get('keyword')
            response = data.get('response')
            category = data.get('category', 'general')
            
            if not keyword or not response:
                return jsonify({'error': 'کلمه کلیدی و پاسخ الزامی است'}), 400
            
            self.bot.keyword_brain.add_keyword(keyword, response, category)
            
            return jsonify({'success': True, 'message': '✅ کلمه کلیدی ذخیره شد!'})
        
        @self.app.route('/api/file', methods=['POST'])
        @self._admin_required
        def api_file():
            if 'file' not in request.files:
                return jsonify({'error': 'فایل ارسال نشده است'}), 400
            
            file = request.files['file']
            category = request.form.get('category', 'document')
            
            if file.filename == '':
                return jsonify({'error': 'فایل انتخاب نشده است'}), 400
            
            # ذخیره فایل
            file_path = os.path.join(Config.FILES_PATH, file.filename)
            file.save(file_path)
            
            # یادگیری از فایل
            result = self.bot.file_learner.learn_from_txt(file_path, category)
            
            return jsonify({'success': True, 'message': '✅ یادگیری از فایل انجام شد!', 'result': result})
        
        @self.app.route('/api/stats', methods=['GET'])
        @self._admin_required
        def api_stats():
            memory_stats = self.bot.memory.get_statistics()
            keyword_stats = self.bot.keyword_brain.get_keyword_stats()
            file_stats = self.bot.file_learner.get_file_stats()
            
            return jsonify({
                'memory': memory_stats,
                'keywords': keyword_stats,
                'files': file_stats,
                'bot': self.bot.stats
            })
        
        @self.app.route('/api/admin/add', methods=['POST'])
        @self._admin_required
        def api_add_admin():
            data = request.json
            admin_id = data.get('admin_id')
            
            if not admin_id:
                return jsonify({'error': 'آیدی ادمین الزامی است'}), 400
            
            # ذخیره در دیتابیس
            if admin_id not in Config.ADMIN_IDS:
                Config.ADMIN_IDS.append(int(admin_id))
            
            return jsonify({'success': True, 'message': f'✅ ادمین {admin_id} اضافه شد!'})
    
    def _admin_required(self, f):
        """دکوراتور برای بررسی دسترسی ادمین"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # چک کردن توکن JWT
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'error': 'توکن معتبر نیست'}), 401
            
            try:
                # بررسی توکن
                payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
                user_id = payload.get('user_id')
                
                if user_id not in Config.ADMIN_IDS:
                    return jsonify({'error': 'دسترسی غیرمجاز'}), 403
                
            except jwt.ExpiredSignatureError:
                return jsonify({'error': 'توکن منقضی شده است'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'error': 'توکن نامعتبر است'}), 401
            
            return f(*args, **kwargs)
        return decorated_function
    
    def _render_admin_panel(self):
        """رندر پنل مدیریت"""
        return """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>👑 پنل مدیریت هوش مصنوعی MON</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Vazir', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #2d3748;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        .card h3 {
            color: #4a5568;
            margin-bottom: 15px;
        }
        input, textarea, select {
            width: 100%;
            padding: 10px;
            margin: 8px 0;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.3s;
            margin-top: 10px;
        }
        button:hover {
            transform: scale(1.02);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .stat-item {
            background: #f7fafc;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-number {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #718096;
            margin-top: 5px;
        }
        .alert {
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
        }
        .alert-success {
            background: #c6f6d5;
            color: #22543d;
        }
        .alert-error {
            background: #fed7d7;
            color: #9b2c2c;
        }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>👑 پنل مدیریت هوش مصنوعی MON</h1>
        
        <div class="grid">
            <!-- کارت یادگیری سوال-جواب -->
            <div class="card">
                <h3>📝 یاد دادن سوال و جواب</h3>
                <input type="text" id="question" placeholder="سوال را وارد کنید...">
                <textarea id="answer" rows="3" placeholder="پاسخ را وارد کنید..."></textarea>
                <select id="category">
                    <option value="general">عمومی</option>
                    <option value="medical">پزشکی</option>
                    <option value="technical">فنی</option>
                    <option value="educational">آموزشی</option>
                </select>
                <button onclick="learnQA()">📚 یاد بده</button>
                <div id="qaResult" class="alert" style="display:none;"></div>
            </div>
            
            <!-- کارت یادگیری کلمات کلیدی -->
            <div class="card">
                <h3>🔑 یاد دادن کلمات کلیدی</h3>
                <input type="text" id="keyword" placeholder="کلمه کلیدی را وارد کنید...">
                <textarea id="keywordResponse" rows="3" placeholder="پاسخ مرتبط..."></textarea>
                <select id="keywordCategory">
                    <option value="general">عمومی</option>
                    <option value="medical">پزشکی</option>
                    <option value="technical">فنی</option>
                    <option value="educational">آموزشی</option>
                </select>
                <button onclick="learnKeyword()">🔑 ذخیره کن</button>
                <div id="keywordResult" class="alert" style="display:none;"></div>
            </div>
            
            <!-- کارت یادگیری از فایل -->
            <div class="card">
                <h3>📄 یادگیری از فایل TXT</h3>
                <input type="file" id="fileInput" accept=".txt,.csv,.json">
                <select id="fileCategory">
                    <option value="document">سند</option>
                    <option value="medical">پزشکی</option>
                    <option value="technical">فنی</option>
                    <option value="educational">آموزشی</option>
                </select>
                <button onclick="learnFromFile()">📚 یاد بگیر</button>
                <div id="fileResult" class="alert" style="display:none;"></div>
            </div>
            
            <!-- کارت آمار -->
            <div class="card">
                <h3>📊 آمار و عملکرد</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-number" id="totalQueries">0</div>
                        <div class="stat-label">کل سوالات</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="successRate">0%</div>
                        <div class="stat-label">موفقیت</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="avgTime">0s</div>
                        <div class="stat-label">زمان پاسخ</div>
                    </div>
                </div>
                <button onclick="loadStats()">🔄 بروزرسانی آمار</button>
                <div id="statsResult" style="margin-top:15px;"></div>
            </div>
            
            <!-- کارت مدیریت ادمین -->
            <div class="card">
                <h3>👤 مدیریت ادمین</h3>
                <input type="number" id="adminId" placeholder="آیدی تلگرام ادمین...">
                <button onclick="addAdmin()">➕ افزودن ادمین</button>
                <div id="adminResult" class="alert" style="display:none;"></div>
            </div>
        </div>
        
        <div id="statusMessage" class="alert" style="display:none;"></div>
    </div>
    
    <script>
        // ==================== توابع اصلی ====================
        const API_BASE = window.location.origin;
        const TOKEN = localStorage.getItem('admin_token') || '';
        
        function showMessage(elementId, message, type = 'success') {
            const el = document.getElementById(elementId);
            el.style.display = 'block';
            el.className = `alert alert-${type}`;
            el.textContent = message;
            setTimeout(() => { el.style.display = 'none'; }, 5000);
        }
        
        async function apiCall(endpoint, method = 'POST', data = null) {
            try {
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': TOKEN
                    }
                };
                
                if (data) {
                    options.body = JSON.stringify(data);
                }
                
                const response = await fetch(`${API_BASE}${endpoint}`, options);
                const result = await response.json();
                return result;
            } catch (error) {
                console.error('خطا در درخواست:', error);
                return { error: 'خطا در ارتباط با سرور' };
            }
        }
        
        // ==================== یادگیری سوال-جواب ====================
        async function learnQA() {
            const question = document.getElementById('question').value;
            const answer = document.getElementById('answer').value;
            const category = document.getElementById('category').value;
            
            if (!question || !answer) {
                showMessage('qaResult', '❌ سوال و پاسخ الزامی است!', 'error');
                return;
            }
            
            const result = await apiCall('/api/learn', 'POST', {
                question, answer, category
            });
            
            if (result.success) {
                showMessage('qaResult', '✅ با موفقیت یاد گرفتم!', 'success');
                document.getElementById('question').value = '';
                document.getElementById('answer').value = '';
            } else {
                showMessage('qaResult', `❌ خطا: ${result.error}`, 'error');
            }
        }
        
        // ==================== یادگیری کلمات کلیدی ====================
        async function learnKeyword() {
            const keyword = document.getElementById('keyword').value;
            const response = document.getElementById('keywordResponse').value;
            const category = document.getElementById('keywordCategory').value;
            
            if (!keyword || !response) {
                showMessage('keywordResult', '❌ کلمه کلیدی و پاسخ الزامی است!', 'error');
                return;
            }
            
            const result = await apiCall('/api/keyword', 'POST', {
                keyword, response, category
            });
            
            if (result.success) {
                showMessage('keywordResult', '✅ کلمه کلیدی ذخیره شد!', 'success');
                document.getElementById('keyword').value = '';
                document.getElementById('keywordResponse').value = '';
            } else {
                showMessage('keywordResult', `❌ خطا: ${result.error}`, 'error');
            }
        }
        
        // ==================== یادگیری از فایل ====================
        async function learnFromFile() {
            const fileInput = document.getElementById('fileInput');
            const category = document.getElementById('fileCategory').value;
            
            if (!fileInput.files.length) {
                showMessage('fileResult', '❌ لطفاً یک فایل انتخاب کنید!', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('category', category);
            
            try {
                const response = await fetch(`${API_BASE}/api/file`, {
                    method: 'POST',
                    headers: { 'Authorization': TOKEN },
                    body: formData
                });
                
                const result = await response.json();
                if (result.success) {
                    showMessage('fileResult', `✅ ${result.message}`, 'success');
                } else {
                    showMessage('fileResult', `❌ خطا: ${result.error}`, 'error');
                }
            } catch (error) {
                showMessage('fileResult', `❌ خطا در آپلود فایل`, 'error');
            }
        }
        
        // ==================== آمار ====================
        async function loadStats() {
            const result = await apiCall('/api/stats', 'GET');
            
            if (result) {
                document.getElementById('totalQueries').textContent = result.bot?.total_queries || 0;
                
                const total = result.bot?.total_queries || 0;
                const success = result.bot?.successful_queries || 0;
                const rate = total > 0 ? Math.round((success / total) * 100) : 0;
                document.getElementById('successRate').textContent = `${rate}%`;
                
                const avgTime = result.bot?.average_response_time || 0;
                document.getElementById('avgTime').textContent = `${avgTime.toFixed(2)}s`;
                
                // نمایش جزئیات بیشتر
                const details = document.getElementById('statsResult');
                details.innerHTML = `
                    <div style="background:#f7fafc;padding:15px;border-radius:10px;">
                        <p><strong>🧠 حافظه:</strong> ${result.memory?.total_items || 0} مورد</p>
                        <p><strong>🔑 کلمات کلیدی:</strong> ${result.keywords?.total_keywords || 0} کلمه</p>
                        <p><strong>📚 فایل‌ها:</strong> ${result.files?.total_documents || 0} سند</p>
                    </div>
                `;
            }
        }
        
        // ==================== افزودن ادمین ====================
        async function addAdmin() {
            const adminId = document.getElementById('adminId').value;
            
            if (!adminId) {
                showMessage('adminResult', '❌ آیدی ادمین را وارد کنید!', 'error');
                return;
            }
            
            const result = await apiCall('/api/admin/add', 'POST', {
                admin_id: parseInt(adminId)
            });
            
            if (result.success) {
                showMessage('adminResult', `✅ ${result.message}`, 'success');
                document.getElementById('adminId').value = '';
            } else {
                showMessage('adminResult', `❌ خطا: ${result.error}`, 'error');
            }
        }
        
        // ==================== بارگذاری اولیه ====================
        loadStats();
        
        // بروزرسانی خودکار آمار هر 30 ثانیه
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
        """
    
    def run(self, host='0.0.0.0', port=5000):
        """اجرای پنل مدیریت"""
        self.app.run(host=host, port=port, debug=False, threaded=True)

# ==================== اجرای اصلی ====================
if __name__ == "__main__":
    try:
        logger.info("🚀 راه‌اندازی سیستم هوش مصنوعی MON...")
        
        # ایجاد نمونه ربات
        bot = UltraTelegramBot(Config.TELEGRAM_TOKEN)
        
        # ایجاد پنل مدیریت
        admin_panel = AdminPanel(bot)
        
        # اجرای ربات در یک ترد جداگانه
        import threading
        bot_thread = threading.Thread(target=bot.run, daemon=True)
        bot_thread.start()
        
        # اجرای پنل مدیریت
        logger.info("👑 پنل مدیریت در http://localhost:5000 در حال اجراست")
        admin_panel.run()
        
    except KeyboardInterrupt:
        logger.info("👋 سیستم متوقف شد")
    except Exception as e:
        logger.error(f"❌ خطای اصلی: {e}")
        sys.exit(1)
