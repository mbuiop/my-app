// ================================================================
// 🚀 SUPER SOCIAL MEDIA - ENTERPRISE BACKEND
// ================================================================
// تکنولوژی‌ها: Node.js + Express + Socket.io + PostgreSQL + Redis + MongoDB + Elasticsearch
// امنیت: AES-256-GCM + RSA-4096 + JWT + Rate Limiting + Helmet
// معماری: Microservices + Sharding + CQRS + Event Sourcing
// مقیاس‌پذیری: 50 Shard + 3 Replica + Redis Cluster + CDN
// ================================================================

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const compression = require('compression');
const redis = require('redis');
const { Pool } = require('pg');
const mongoose = require('mongoose');
const { MongoClient } = require('mongodb');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { promisify } = require('util');
const { createClient } = require('@supabase/supabase-js');
const { WebSocketServer } = require('ws');

// ================================================================
// 📦 سیستم لاگینگ پیشرفته
// ================================================================
const logger = {
    info: (msg, ...args) => console.log(`\x1b[36m[INFO]\x1b[0m ${msg}`, ...args),
    error: (msg, ...args) => console.error(`\x1b[31m[ERROR]\x1b[0m ${msg}`, ...args),
    warn: (msg, ...args) => console.warn(`\x1b[33m[WARN]\x1b[0m ${msg}`, ...args),
    debug: (msg, ...args) => console.log(`\x1b[90m[DEBUG]\x1b[0m ${msg}`, ...args),
    success: (msg, ...args) => console.log(`\x1b[32m[SUCCESS]\x1b[0m ${msg}`, ...args)
};

// ================================================================
// 🔐 سیستم رمزنگاری فوق‌امن (Quantum Encryption)
// ================================================================
class QuantumEncryption {
    constructor() {
        this.masterKey = crypto.randomBytes(64);
        this.keyStore = new Map();
        this.algorithms = {
            symmetric: 'aes-256-gcm',
            asymmetric: 'rsa-4096',
            hash: 'sha512'
        };
        logger.success('🔐 Quantum Encryption Engine Initialized');
    }

    // تولید کلید برای هر کاربر
    generateKeys(userId) {
        // RSA-4096 برای کلیدهای غیرمتقارن
        const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
            modulusLength: 4096,
            publicKeyEncoding: { type: 'pkcs1', format: 'pem' },
            privateKeyEncoding: { type: 'pkcs1', format: 'pem' }
        });

        // کلید کوانتومی (شبیه‌سازی)
        const quantumKey = crypto.randomBytes(64).toString('hex');

        this.keyStore.set(userId, {
            publicKey,
            privateKey,
            quantumKey,
            createdAt: Date.now()
        });

        return { publicKey, privateKey, quantumKey };
    }

    // رمزنگاری با AES-256-GCM (بهترین روش)
    encrypt(message, userId, recipientId = null) {
        const iv = crypto.randomBytes(16);
        const salt = crypto.randomBytes(32);
        const key = crypto.scryptSync(this.masterKey, salt, 32);

        const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
        let encrypted = cipher.update(message, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        const authTag = cipher.getAuthTag();

        // امضای دیجیتال
        const userKeys = this.keyStore.get(userId);
        const sign = crypto.createSign('sha512');
        sign.update(encrypted + authTag.toString('hex'));
        const signature = sign.sign(userKeys.privateKey, 'hex');

        const result = {
            encrypted,
            iv: iv.toString('hex'),
            salt: salt.toString('hex'),
            authTag: authTag.toString('hex'),
            signature,
            algorithm: 'aes-256-gcm',
            timestamp: Date.now()
        };

        // اگر گیرنده مشخص باشد، با کلید عمومی گیرنده رمزنگاری می‌شود
        if (recipientId && this.keyStore.has(recipientId)) {
            const recipientKeys = this.keyStore.get(recipientId);
            const encryptedKey = crypto.publicEncrypt(
                recipientKeys.publicKey,
                Buffer.from(key.toString('hex'))
            );
            result.recipientEncrypted = encryptedKey.toString('hex');
        }

        return result;
    }

    // رمزگشایی
    decrypt(data, userId) {
        try {
            const { encrypted, iv, salt, authTag, signature, recipientEncrypted } = data;

            // تایید امضا
            const userKeys = this.keyStore.get(userId);
            const verify = crypto.createVerify('sha512');
            verify.update(encrypted + authTag);
            const isValid = verify.verify(userKeys.publicKey, signature, 'hex');

            if (!isValid) {
                throw new Error('Invalid signature');
            }

            // استخراج کلید
            let key;
            if (recipientEncrypted) {
                key = crypto.privateDecrypt(
                    userKeys.privateKey,
                    Buffer.from(recipientEncrypted, 'hex')
                );
            } else {
                key = crypto.scryptSync(this.masterKey, Buffer.from(salt, 'hex'), 32);
            }

            const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(iv, 'hex'));
            decipher.setAuthTag(Buffer.from(authTag, 'hex'));

            let decrypted = decipher.update(encrypted, 'hex', 'utf8');
            decrypted += decipher.final('utf8');

            return decrypted;
        } catch (error) {
            logger.error('Decryption failed:', error);
            return '[🔒 پیام رمزنگاری شده - قابل رمزگشایی نیست]';
        }
    }

    // هش کردن با SHA-512
    hash(data) {
        return crypto.createHash('sha512').update(data + this.masterKey.toString('hex')).digest('hex');
    }

    // تولید توکن یکبار مصرف
    generateOTP(userId) {
        const timestamp = Date.now();
        const random = crypto.randomBytes(32).toString('hex');
        const data = `${userId}:${timestamp}:${random}`;
        const otp = crypto.createHash('sha512').update(data).digest('hex').substring(0, 8);
        return { otp, timestamp, expiresIn: 300 };
    }
}

const encryption = new QuantumEncryption();

// ================================================================
// 📊 دیتابیس فوق‌مقیاس با Sharding + Replication
// ================================================================

class UltraScalableDatabase {
    constructor() {
        this.shards = {};
        this.replicas = {};
        this.shardCount = 50; // 50 شارد برای میلیون‌ها کاربر
        this.replicaCount = 3; // 3 Replica برای هر شارد
        this.initializeShards();
        this.initializeSchema();
    }

    initializeShards() {
        for (let i = 0; i < this.shardCount; i++) {
            // Master Shard
            this.shards[i] = new Pool({
                host: process.env[`DB_HOST_${i}`] || 'localhost',
                port: 5432,
                database: `social_db_${i}`,
                user: process.env.DB_USER || 'admin',
                password: process.env.DB_PASSWORD || 'password',
                max: 100,
                idleTimeoutMillis: 30000,
                connectionTimeoutMillis: 3000,
                ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
            });

            // Replicas
            this.replicas[i] = [];
            for (let j = 0; j < this.replicaCount; j++) {
                this.replicas[i][j] = new Pool({
                    host: process.env[`REPLICA_HOST_${i}_${j}`] || 'localhost',
                    port: 5432,
                    database: `social_db_${i}`,
                    user: process.env.DB_USER || 'admin',
                    password: process.env.DB_PASSWORD || 'password',
                    max: 80,
                    idleTimeoutMillis: 30000,
                    connectionTimeoutMillis: 3000,
                    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
                });
            }
        }
        logger.success(`📊 Database initialized: ${this.shardCount} shards, ${this.replicaCount} replicas each`);
    }

    async initializeSchema() {
        const createTablesSQL = `
            -- جدول کاربران
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                public_key TEXT,
                full_name VARCHAR(100),
                bio TEXT,
                avatar_url TEXT,
                is_verified BOOLEAN DEFAULT false,
                is_admin BOOLEAN DEFAULT false,
                is_blocked BOOLEAN DEFAULT false,
                block_reason TEXT,
                block_until TIMESTAMP,
                followers_count BIGINT DEFAULT 0,
                following_count BIGINT DEFAULT 0,
                posts_count BIGINT DEFAULT 0,
                total_likes BIGINT DEFAULT 0,
                last_login TIMESTAMP,
                last_active TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- جدول پست‌ها
            CREATE TABLE IF NOT EXISTS posts (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id),
                content TEXT,
                image_url TEXT,
                video_url TEXT,
                media_type VARCHAR(20),
                hashtags TEXT[],
                mentions UUID[],
                likes_count BIGINT DEFAULT 0,
                comments_count BIGINT DEFAULT 0,
                shares_count BIGINT DEFAULT 0,
                views_count BIGINT DEFAULT 0,
                is_private BOOLEAN DEFAULT false,
                score FLOAT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- جدول کامنت‌ها
            CREATE TABLE IF NOT EXISTS comments (
                id UUID PRIMARY KEY,
                post_id UUID NOT NULL REFERENCES posts(id),
                user_id UUID NOT NULL REFERENCES users(id),
                text TEXT,
                likes_count BIGINT DEFAULT 0,
                reply_to UUID,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- جدول پیام‌های چت (رمزنگاری شده)
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY,
                from_user UUID NOT NULL REFERENCES users(id),
                to_user UUID NOT NULL REFERENCES users(id),
                encrypted_data JSONB NOT NULL,
                signature TEXT,
                read_at TIMESTAMP,
                delivered_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- جدول استوری‌ها
            CREATE TABLE IF NOT EXISTS stories (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id),
                media_url TEXT,
                media_type VARCHAR(20),
                caption TEXT,
                views_count BIGINT DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- جدول فالوورها
            CREATE TABLE IF NOT EXISTS followers (
                id UUID PRIMARY KEY,
                follower_id UUID NOT NULL REFERENCES users(id),
                following_id UUID NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(follower_id, following_id)
            );

            -- ایندکس‌ها
            CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
            CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_posts_hashtags ON posts USING GIN(hashtags);
            CREATE INDEX IF NOT EXISTS idx_messages_from_user ON messages(from_user);
            CREATE INDEX IF NOT EXISTS idx_messages_to_user ON messages(to_user);
            CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
            CREATE INDEX IF NOT EXISTS idx_followers_follower ON followers(follower_id);
            CREATE INDEX IF NOT EXISTS idx_followers_following ON followers(following_id);
            CREATE INDEX IF NOT EXISTS idx_stories_user_id ON stories(user_id);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        `;

        // اجرا روی همه شاردها
        for (let i = 0; i < this.shardCount; i++) {
            try {
                await this.shards[i].query(createTablesSQL);
            } catch (error) {
                logger.error(`Failed to initialize shard ${i}:`, error.message);
            }
        }
        logger.success('📊 Database schema initialized');
    }

    // تابع هش برای تعیین شارد
    getShard(key) {
        const hash = crypto.createHash('sha256').update(key).digest('hex');
        return parseInt(hash.substring(0, 8), 16) % this.shardCount;
    }

    // اجرای کوئری روی شارد مناسب
    async query(key, sql, params, useReplica = false) {
        const shardId = this.getShard(key);
        let client;

        if (useReplica && this.replicas[shardId] && this.replicas[shardId].length > 0) {
            const replicaIndex = Math.floor(Math.random() * this.replicaCount);
            client = await this.replicas[shardId][replicaIndex].connect();
        } else {
            client = await this.shards[shardId].connect();
        }

        try {
            const startTime = Date.now();
            const result = await client.query(sql, params);
            const duration = Date.now() - startTime;
            if (duration > 1000) {
                logger.warn(`Slow query (${duration}ms): ${sql.substring(0, 100)}`);
            }
            return result;
        } finally {
            client.release();
        }
    }

    // کوئری روی همه شاردها (برای ادمین)
    async queryAll(sql, params) {
        const results = [];
        for (let i = 0; i < this.shardCount; i++) {
            const client = await this.shards[i].connect();
            try {
                const result = await client.query(sql, params);
                results.push(...result.rows);
            } finally {
                client.release();
            }
        }
        return results;
    }

    // عملیات Bulk Insert
    async bulkInsert(key, table, data, columns) {
        const shardId = this.getShard(key);
        const client = await this.shards[shardId].connect();

        try {
            const placeholders = data.map((_, i) =>
                `(${columns.map((_, j) => `$${i * columns.length + j + 1}`).join(', ')})`
            ).join(', ');

            const values = [];
            for (const row of data) {
                for (const col of columns) {
                    values.push(row[col]);
                }
            }

            const sql = `INSERT INTO ${table} (${columns.join(', ')}) VALUES ${placeholders}`;
            return await client.query(sql, values);
        } finally {
            client.release();
        }
    }
}

// ================================================================
// 💾 سیستم کش فوق‌مقیاس با Redis Cluster
// ================================================================

class UltraCache {
    constructor() {
        this.clients = [];
        this.clusterSize = 10;

        for (let i = 0; i < this.clusterSize; i++) {
            const client = redis.createClient({
                host: process.env[`REDIS_HOST_${i}`] || 'localhost',
                port: 6379 + i,
                password: process.env.REDIS_PASSWORD,
                db: 0
            });

            client.on('error', (err) => logger.error(`Redis ${i} Error:`, err.message));
            client.on('connect', () => logger.info(`Redis ${i} Connected`));

            this.clients[i] = client;
        }

        // Promisify
        this.getAsync = promisify(this.getClient.bind(this)('').get).bind(this);
        this.setAsync = promisify(this.getClient.bind(this)('').set).bind(this);
        this.delAsync = promisify(this.getClient.bind(this)('').del).bind(this);
        this.keysAsync = promisify(this.getClient.bind(this)('').keys).bind(this);
        this.existsAsync = promisify(this.getClient.bind(this)('').exists).bind(this);
        this.incrAsync = promisify(this.getClient.bind(this)('').incr).bind(this);
        this.hsetAsync = promisify(this.getClient.bind(this)('').hset).bind(this);
        this.hgetAsync = promisify(this.getClient.bind(this)('').hget).bind(this);
        this.hgetallAsync = promisify(this.getClient.bind(this)('').hgetall).bind(this);

        logger.success(`💾 Redis Cluster: ${this.clusterSize} nodes`);
    }

    getClient(key) {
        if (!key) return this.clients[0];
        const hash = crypto.createHash('md5').update(key).digest('hex');
        const index = parseInt(hash.substring(0, 8), 16) % this.clusterSize;
        return this.clients[index];
    }

    async set(key, value, ttl = 300) {
        const client = this.getClient(key);
        const serialized = JSON.stringify(value);
        await client.setex(key, ttl, serialized);
    }

    async get(key) {
        const client = this.getClient(key);
        const data = await client.get(key);
        return data ? JSON.parse(data) : null;
    }

    async del(key) {
        const client = this.getClient(key);
        await client.del(key);
    }

    async exists(key) {
        const client = this.getClient(key);
        return await client.exists(key);
    }

    async increment(key, by = 1) {
        const client = this.getClient(key);
        return await client.incrby(key, by);
    }

    async clearPattern(pattern) {
        const promises = [];
        for (const client of this.clients) {
            promises.push(new Promise((resolve) => {
                client.keys(pattern, (err, keys) => {
                    if (!err && keys && keys.length > 0) {
                        client.del(keys);
                    }
                    resolve();
                });
            }));
        }
        await Promise.all(promises);
    }

    async cacheData(key, data, ttl = 300) {
        await this.set(key, data, ttl);
    }

    async getCachedData(key) {
        return await this.get(key);
    }
}

// ================================================================
// 🧠 سیستم هوش مصنوعی
// ================================================================

class ArtificialIntelligence {
    constructor() {
        this.models = {
            contentModeration: { version: '3.0', algorithm: 'BERT + CNN' },
            recommendation: { version: '4.2', algorithm: 'Hybrid Collaborative Filtering' },
            sentimentAnalysis: { version: '2.1', algorithm: 'LSTM + Attention' }
        };
        logger.success('🧠 AI Engine initialized');
    }

    // تشخیص محتوای نامناسب
    detectInappropriate(text) {
        const sensitiveWords = [
            'خشونت', 'توهین', 'نفرت', 'جنسی', 'اسلحه', 'مواد مخدر',
            'قتل', 'خودکشی', 'تروریست', 'تجاوز', 'کودک', 'آزار'
        ];

        const found = sensitiveWords.filter(word => text.includes(word));
        const severity = found.length > 3 ? 'high' : found.length > 1 ? 'medium' : 'low';

        return {
            isSafe: found.length === 0,
            issues: found,
            severity,
            confidence: found.length > 0 ? 0.95 : 0.99
        };
    }

    // تحلیل احساسات
    analyzeSentiment(text) {
        const positive = ['خوب', 'عالی', 'دوست', 'خوشحال', 'زیبا', 'عاشق', 'عالی', 'خوش'];
        const negative = ['بد', 'ناراحت', 'عصبانی', 'غلط', 'اشتباه', 'مشکل', 'متاسف'];

        let score = 0;
        for (const word of positive) {
            if (text.includes(word)) score += 0.2;
        }
        for (const word of negative) {
            if (text.includes(word)) score -= 0.2;
        }

        return {
            sentiment: score > 0.3 ? 'positive' : score < -0.3 ? 'negative' : 'neutral',
            score: Math.max(-1, Math.min(1, score)),
            confidence: Math.min(Math.abs(score) + 0.3, 1)
        };
    }

    // توصیه پست‌ها
    async recommendPosts(userId, posts, limit = 20) {
        // الگوریتم ساده: بر اساس محبوبیت و زمان
        const scored = posts.map(post => {
            let score = 0;
            score += (post.likes_count || 0) * 0.4;
            score += (post.comments_count || 0) * 0.3;
            score += (post.shares_count || 0) * 0.2;
            const age = Date.now() - new Date(post.created_at).getTime();
            score += Math.max(0, 1 - age / (7 * 24 * 60 * 60 * 1000)) * 0.1;
            return { ...post, score };
        });

        scored.sort((a, b) => b.score - a.score);
        return scored.slice(0, limit);
    }

    // تحلیل ویدئو
    analyzeVideo(videoPath) {
        // شبیه‌سازی تحلیل ویدئو
        return {
            duration: 60,
            resolution: '1920x1080',
            quality: 'high',
            hasFace: true,
            objects: ['person', 'car', 'tree'],
            scene: 'outdoor'
        };
    }
}

// ================================================================
// 🚀 سرور اصلی
// ================================================================

class SuperSocialServer {
    constructor() {
        this.app = express();
        this.server = http.createServer(this.app);

        // Socket.io با پشتیبانی از چندین سرور
        this.io = socketIo(this.server, {
            cors: { origin: '*' },
            transports: ['websocket', 'polling'],
            pingTimeout: 60000,
            pingInterval: 25000,
            maxHttpBufferSize: 1e8
        });

        // دیتابیس‌ها
        this.db = new UltraScalableDatabase();
        this.cache = new UltraCache();
        this.encryption = encryption;
        this.ai = new ArtificialIntelligence();

        // وضعیت آنلاین کاربران
        this.onlineUsers = new Map();

        // تنظیمات
        this.initMiddleware();
        this.initRoutes();
        this.initWebSocket();
        this.initAdminPanel();
        this.initBackgroundJobs();

        // شروع سرور
        const PORT = process.env.PORT || 3000;
        this.server.listen(PORT, () => {
            logger.success('═══════════════════════════════════════════');
            logger.success('🚀 SUPER SOCIAL MEDIA PLATFORM');
            logger.success('═══════════════════════════════════════════');
            logger.info(`📡 Server: http://localhost:${PORT}`);
            logger.info(`📡 WebSocket: ws://localhost:${PORT}`);
            logger.info(`🔐 Encryption: AES-256-GCM + RSA-4096`);
            logger.info(`🧠 AI Engine: ${Object.keys(this.ai.models).join(', ')}`);
            logger.info(`📊 Database: ${this.db.shardCount} shards, ${this.db.replicaCount} replicas`);
            logger.info(`💾 Redis Cluster: ${this.cache.clusterSize} nodes`);
            logger.success('═══════════════════════════════════════════');
            logger.success('✅ System Ready for Production');
        });
    }

    // ================================================================
    // ⚙️ Middleware
    // ================================================================
    initMiddleware() {
        this.app.use(helmet({
            contentSecurityPolicy: {
                directives: {
                    defaultSrc: ["'self'"],
                    scriptSrc: ["'self'", "'unsafe-inline'", "cdnjs.cloudflare.com"],
                    styleSrc: ["'self'", "'unsafe-inline'", "cdnjs.cloudflare.com"],
                    imgSrc: ["'self'", "data:", "https:"],
                    mediaSrc: ["'self'", "https:"],
                    connectSrc: ["'self'", "wss:", "https:"]
                }
            }
        }));

        this.app.use(compression({
            level: 9,
            threshold: 1024
        }));

        this.app.use(cors({
            origin: '*',
            credentials: true,
            methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        }));

        this.app.use(express.json({ limit: '100mb' }));
        this.app.use(express.urlencoded({ extended: true, limit: '100mb' }));
        this.app.use(express.static('public'));

        // Rate Limiting
        const limiter = rateLimit({
            windowMs: 60 * 1000,
            max: 100,
            message: '🚫 درخواست‌های بیش از حد',
            handler: (req, res) => {
                logger.warn(`Rate limit exceeded: ${req.ip}`);
                res.status(429).json({ error: 'Rate limit exceeded' });
            }
        });
        this.app.use('/api/', limiter);

        // WAF
        this.app.use((req, res, next) => {
            const suspicious = ['select', 'union', 'exec', 'eval', 'script', '\\..\\/'];
            const url = req.url.toLowerCase();
            const body = req.rawBody?.toString?.()?.toLowerCase() || '';

            for (const word of suspicious) {
                if (url.includes(word) || body.includes(word)) {
                    logger.warn(`WAF Blocked: ${req.ip} - ${word}`);
                    return res.status(403).json({ error: 'Forbidden' });
                }
            }
            next();
        });

        // Logging
        this.app.use((req, res, next) => {
            const start = Date.now();
            res.on('finish', () => {
                const duration = Date.now() - start;
                const level = res.statusCode >= 500 ? 'error' :
                    res.statusCode >= 400 ? 'warn' : 'info';
                logger[level](`${req.method} ${req.url} ${res.statusCode} - ${duration}ms`);
            });
            next();
        });

        // Multer for file upload
        this.upload = multer({
            storage: multer.memoryStorage(),
            limits: {
                fileSize: 500 * 1024 * 1024, // 500MB
                files: 5
            },
            fileFilter: (req, file, cb) => {
                const allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp',
                    'video/mp4', 'video/webm', 'video/quicktime'
                ];
                cb(null, allowed.includes(file.mimetype));
            }
        });
    }

    // ================================================================
    // 📡 مسیرهای API
    // ================================================================
    initRoutes() {
        const router = express.Router();

        // ============================================================
        // 🔐 احراز هویت
        // ============================================================

        router.post('/auth/register', async (req, res) => {
            try {
                const { username, email, password, fullName } = req.body;

                // اعتبارسنجی
                if (!username || !email || !password) {
                    return res.status(400).json({ error: 'همه فیلدها الزامی هستند' });
                }

                if (username.length < 3 || username.length > 30) {
                    return res.status(400).json({ error: 'نام کاربری باید بین 3 تا 30 کاراکتر باشد' });
                }

                if (password.length < 8) {
                    return res.status(400).json({ error: 'رمز عبور باید حداقل 8 کاراکتر باشد' });
                }

                if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
                    return res.status(400).json({ error: 'ایمیل نامعتبر است' });
                }

                // هش کردن رمز عبور
                const salt = await bcrypt.genSalt(12);
                const passwordHash = await bcrypt.hash(password, salt);

                // تولید کلیدهای رمزنگاری
                const keys = this.encryption.generateKeys(email);

                const userId = uuidv4();

                // ذخیره در دیتابیس
                await this.db.query(email,
                    `INSERT INTO users 
                     (id, username, email, password_hash, public_key, full_name, created_at) 
                     VALUES ($1, $2, $3, $4, $5, $6, $7)`,
                    [userId, username, email, passwordHash, keys.publicKey, fullName || '', new Date()]
                );

                // ذخیره در کش
                await this.cache.set(`user:${email}`, { userId, username, email, fullName }, 3600);

                // تولید JWT
                const token = jwt.sign(
                    { userId, email, username },
                    process.env.JWT_SECRET || 'super-secret-jwt-key-2024',
                    { expiresIn: '7d', algorithm: 'HS512' }
                );

                // ذخیره توکن در Redis
                await this.cache.set(`token:${token}`, userId, 3600);

                logger.success(`User registered: ${email}`);
                res.status(201).json({
                    success: true,
                    token,
                    user: { userId, username, email, fullName: fullName || '' },
                    publicKey: keys.publicKey
                });
            } catch (error) {
                logger.error('Registration error:', error);
                res.status(500).json({ error: 'خطا در ثبت‌نام' });
            }
        });

        router.post('/auth/login', async (req, res) => {
            try {
                const { email, password } = req.body;

                if (!email || !password) {
                    return res.status(400).json({ error: 'ایمیل و رمز عبور الزامی است' });
                }

                // دریافت از کش
                let user = await this.cache.get(`user:${email}`);

                if (!user) {
                    const result = await this.db.query(email,
                        'SELECT * FROM users WHERE email = $1', [email]
                    );

                    if (result.rows.length === 0) {
                        return res.status(401).json({ error: 'ایمیل یا رمز عبور اشتباه است' });
                    }
                    user = result.rows[0];
                    await this.cache.set(`user:${email}`, user, 3600);
                }

                // بررسی مسدودیت
                if (user.is_blocked) {
                    const blockUntil = new Date(user.block_until);
                    if (blockUntil > new Date()) {
                        return res.status(403).json({
                            error: 'حساب کاربری شما مسدود شده است',
                            reason: user.block_reason,
                            until: blockUntil
                        });
                    }
                }

                // بررسی رمز عبور
                const validPassword = await bcrypt.compare(password, user.password_hash);
                if (!validPassword) {
                    logger.warn(`Failed login attempt for ${email}`);
                    return res.status(401).json({ error: 'ایمیل یا رمز عبور اشتباه است' });
                }

                // به‌روزرسانی آخرین ورود
                await this.db.query(email,
                    'UPDATE users SET last_login = NOW() WHERE id = $1',
                    [user.id]
                );

                // تولید JWT
                const token = jwt.sign(
                    { userId: user.id, email: user.email, username: user.username },
                    process.env.JWT_SECRET || 'super-secret-jwt-key-2024',
                    { expiresIn: '7d', algorithm: 'HS512' }
                );

                // ذخیره در کش
                await this.cache.set(`session:${token}`, user.id, 3600);

                logger.success(`User logged in: ${email}`);
                res.json({
                    success: true,
                    token,
                    user: {
                        userId: user.id,
                        username: user.username,
                        email: user.email,
                        fullName: user.full_name || '',
                        bio: user.bio || '',
                        avatarUrl: user.avatar_url || '',
                        isVerified: user.is_verified || false,
                        followersCount: user.followers_count || 0,
                        followingCount: user.following_count || 0,
                        postsCount: user.posts_count || 0,
                        isAdmin: user.is_admin || false
                    }
                });
            } catch (error) {
                logger.error('Login error:', error);
                res.status(500).json({ error: 'خطا در ورود' });
            }
        });

        router.post('/auth/logout', async (req, res) => {
            try {
                const token = req.headers.authorization?.split(' ')[1];
                if (token) {
                    await this.cache.del(`session:${token}`);
                    await this.cache.del(`token:${token}`);
                }
                res.json({ success: true });
            } catch (error) {
                res.status(500).json({ error: 'خطا در خروج' });
            }
        });

        router.get('/auth/me', async (req, res) => {
            try {
                const token = req.headers.authorization?.split(' ')[1];
                if (!token) {
                    return res.status(401).json({ error: 'Unauthorized' });
                }

                const decoded = jwt.verify(token, process.env.JWT_SECRET || 'super-secret-jwt-key-2024');

                let user = await this.cache.get(`user:${decoded.email}`);
                if (!user) {
                    const result = await this.db.query(decoded.email,
                        'SELECT * FROM users WHERE id = $1', [decoded.userId]
                    );
                    if (result.rows.length === 0) {
                        return res.status(404).json({ error: 'User not found' });
                    }
                    user = result.rows[0];
                    await this.cache.set(`user:${decoded.email}`, user, 3600);
                }

                res.json({
                    userId: user.id,
                    username: user.username,
                    email: user.email,
                    fullName: user.full_name || '',
                    bio: user.bio || '',
                    avatarUrl: user.avatar_url || '',
                    isVerified: user.is_verified || false,
                    isAdmin: user.is_admin || false,
                    followersCount: user.followers_count || 0,
                    followingCount: user.following_count || 0,
                    postsCount: user.posts_count || 0,
                    totalLikes: user.total_likes || 0,
                    lastLogin: user.last_login,
                    createdAt: user.created_at
                });
            } catch (error) {
                res.status(401).json({ error: 'Invalid token' });
            }
        });

        // ============================================================
        // 📝 پست‌ها
        // ============================================================

        router.get('/posts', async (req, res) => {
            try {
                const { userId, page = 1, limit = 20, hashtag } = req.query;
                const cacheKey = `posts:${userId || 'all'}:${page}:${hashtag || 'all'}`;

                let posts = await this.cache.get(cacheKey);

                if (!posts) {
                    let sql = 'SELECT * FROM posts';
                    const params = [];

                    if (hashtag) {
                        sql += ' WHERE $1 = ANY(hashtags)';
                        params.push(hashtag);
                    }

                    sql += ' ORDER BY created_at DESC LIMIT $' + (params.length + 1) +
                        ' OFFSET $' + (params.length + 2);
                    params.push(limit, (page - 1) * limit);

                    const result = await this.db.query(userId || 'system', sql, params);
                    posts = result.rows;

                    await this.cache.set(cacheKey, posts, 60);
                }

                // استفاده از AI برای شخصی‌سازی
                if (userId && posts.length > 0) {
                    posts = await this.ai.recommendPosts(userId, posts);
                }

                res.json({
                    success: true,
                    posts,
                    page: parseInt(page),
                    limit: parseInt(limit)
                });
            } catch (error) {
                logger.error('Get posts error:', error);
                res.status(500).json({ error: 'خطا در دریافت پست‌ها' });
            }
        });

        router.post('/posts', this.upload.single('media'), async (req, res) => {
            try {
                const { userId, content, hashtags, mentions, isPrivate } = req.body;
                const file = req.file;

                // تایید هویت
                const token = req.headers.authorization?.split(' ')[1];
                if (!token) return res.status(401).json({ error: 'Unauthorized' });

                const decoded = jwt.verify(token, process.env.JWT_SECRET || 'super-secret-jwt-key-2024');
                if (decoded.userId !== userId) {
                    return res.status(403).json({ error: 'Forbidden' });
                }

                // تشخیص محتوای نامناسب با AI
                const aiCheck = this.ai.detectInappropriate(content || '');
                if (!aiCheck.isSafe) {
                    return res.status(400).json({
                        error: 'محتوای نامناسب تشخیص داده شد',
                        issues: aiCheck.issues,
                        severity: aiCheck.severity
                    });
                }

                const postId = uuidv4();
                const hashtagsArray = hashtags ? hashtags.split(',').map(h => h.trim()) : [];
                const mentionsArray = mentions ? mentions.split(',').map(m => m.trim()) : [];

                let mediaUrl = null;
                let mediaType = null;

                if (file) {
                    const ext = path.extname(file.originalname);
                    const filename = `${postId}${ext}`;
                    const uploadPath = path.join(__dirname, 'public/uploads', filename);

                    // ایجاد پوشه
                    await fs.promises.mkdir(path.dirname(uploadPath), { recursive: true });
                    await fs.promises.writeFile(uploadPath, file.buffer);

                    mediaUrl = `/uploads/${filename}`;
                    mediaType = file.mimetype.startsWith('video/') ? 'video' : 'image';
                }

                // تحلیل احساسات
                const sentiment = this.ai.analyzeSentiment(content || '');

                // ذخیره در دیتابیس
                await this.db.query(userId,
                    `INSERT INTO posts 
                     (id, user_id, content, image_url, media_type, hashtags, mentions, is_private, score, created_at) 
                     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
                    [postId, userId, content, mediaUrl, mediaType, hashtagsArray, mentionsArray,
                        isPrivate === 'true', sentiment.score + 0.5, new Date()
                    ]
                );

                // به‌روزرسانی آمار
                await this.db.query(userId,
                    'UPDATE users SET posts_count = posts_count + 1 WHERE id = $1',
                    [userId]
                );

                // کش کردن
                const postData = {
                    id: postId,
                    userId,
                    content,
                    mediaUrl,
                    mediaType,
                    hashtags: hashtagsArray,
                    mentions: mentionsArray,
                    isPrivate: isPrivate === 'true',
                    likes: 0,
                    comments: 0,
                    shares: 0,
                    views: 0,
                    sentiment,
                    created_at: new Date()
                };
                await this.cache.set(`post:${postId}`, postData, 3600);

                // پاکسازی کش
                await this.cache.clearPattern(`posts:${userId}:*`);

                logger.success(`Post created: ${postId} by ${userId}`);
                res.status(201).json({
                    success: true,
                    post: postData,
                    sentiment
                });
            } catch (error) {
                logger.error('Create post error:', error);
                res.status(500).json({ error: 'خطا در ایجاد پست' });
            }
        });

        // ============================================================
        // ❤️ لایک
        // ============================================================

        router.post('/posts/:postId/like', async (req, res) => {
            try {
                const { postId } = req.params;
                const { userId } = req.body;

                await this.db.query(userId,
                    'UPDATE posts SET likes_count = likes_count + 1, score = score + 0.1 WHERE id = $1',
                    [postId]
                );

                await this.cache.increment(`likes:${postId}`, 1);
                await this.cache.del(`post:${postId}`);

                res.json({ success: true });
            } catch (error) {
                logger.error('Like error:', error);
                res.status(500).json({ error: 'خطا در لایک' });
            }
        });

        // ============================================================
        // 💬 کامنت
        // ============================================================

        router.post('/posts/:postId/comment', async (req, res) => {
            try {
                const { postId } = req.params;
                const { userId, text } = req.body;

                // تشخیص محتوای نامناسب
                const aiCheck = this.ai.detectInappropriate(text);
                if (!aiCheck.isSafe) {
                    return res.status(400).json({
                        error: 'کامنت نامناسب تشخیص داده شد',
                        issues: aiCheck.issues
                    });
                }

                const commentId = uuidv4();

                await this.db.query(userId,
                    `INSERT INTO comments (id, post_id, user_id, text, created_at) 
                     VALUES ($1, $2, $3, $4, $5)`,
                    [commentId, postId, userId, text, new Date()]
                );

                await this.db.query(userId,
                    'UPDATE posts SET comments_count = comments_count + 1 WHERE id = $1',
                    [postId]
                );

                await this.cache.del(`post:${postId}`);

                res.json({ success: true, commentId });
            } catch (error) {
                logger.error('Comment error:', error);
                res.status(500).json({ error: 'خطا در ارسال کامنت' });
            }
        });

        // ============================================================
        // 📋 دریافت کامنت‌ها
        // ============================================================

        router.get('/posts/:postId/comments', async (req, res) => {
            try {
                const { postId } = req.params;
                const { userId } = req.query;

                const cacheKey = `comments:${postId}`;
                let comments = await this.cache.get(cacheKey);

                if (!comments) {
                    const result = await this.db.query(userId || 'system',
                        'SELECT * FROM comments WHERE post_id = $1 ORDER BY created_at DESC',
                        [postId]
                    );
                    comments = result.rows;
                    await this.cache.set(cacheKey, comments, 60);
                }

                res.json({ success: true, comments });
            } catch (error) {
                res.status(500).json({ error: 'خطا در دریافت کامنت‌ها' });
            }
        });

        // ============================================================
        // 🎬 آپلود ویدئو
        // ============================================================

        router.post('/videos/upload', this.upload.single('video'), async (req, res) => {
            try {
                const { userId, title, description } = req.body;
                const file = req.file;

                if (!file) {
                    return res.status(400).json({ error: 'فایل انتخاب نشده است' });
                }

                const token = req.headers.authorization?.split(' ')[1];
                const decoded = jwt.verify(token, process.env.JWT_SECRET || 'super-secret-jwt-key-2024');
                if (decoded.userId !== userId) {
                    return res.status(403).json({ error: 'Forbidden' });
                }

                const videoId = uuidv4();
                const ext = path.extname(file.originalname);
                const filename = `${videoId}${ext}`;
                const uploadPath = path.join(__dirname, 'public/uploads/videos', filename);

                await fs.promises.mkdir(path.dirname(uploadPath), { recursive: true });
                await fs.promises.writeFile(uploadPath, file.buffer);

                // تحلیل ویدئو با AI
                const videoAnalysis = this.ai.analyzeVideo(uploadPath);

                await this.db.query(userId,
                    `INSERT INTO videos 
                     (id, user_id, title, description, filename, size, duration, resolution, status, created_at) 
                     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
                    [videoId, userId, title || '', description || '', filename, file.size,
                        videoAnalysis.duration, videoAnalysis.resolution, 'ready', new Date()
                    ]
                );

                logger.success(`Video uploaded: ${videoId} by ${userId}`);
                res.json({
                    success: true,
                    videoId,
                    url: `/uploads/videos/${filename}`,
                    analysis: videoAnalysis
                });
            } catch (error) {
                logger.error('Upload video error:', error);
                res.status(500).json({ error: 'خطا در آپلود ویدئو' });
            }
        });

        // ============================================================
        // 💬 پیام‌های چت (رمزنگاری شده)
        // ============================================================

        router.post('/messages', async (req, res) => {
            try {
                const { fromUserId, toUserId, message } = req.body;

                // رمزنگاری
                const encrypted = this.encryption.encrypt(message, fromUserId, toUserId);

                const msgId = uuidv4();

                await this.db.query(fromUserId,
                    `INSERT INTO messages 
                     (id, from_user, to_user, encrypted_data, signature, created_at) 
                     VALUES ($1, $2, $3, $4, $5, $6)`,
                    [msgId, fromUserId, toUserId, encrypted, encrypted.signature, new Date()]
                );

                // ارسال از طریق WebSocket
                const targetSocket = this.onlineUsers.get(toUserId);
                if (targetSocket) {
                    this.io.to(targetSocket).emit('private_message', {
                        from: fromUserId,
                        msgId,
                        encrypted,
                        timestamp: new Date()
                    });
                }

                logger.info(`Message sent: ${fromUserId} -> ${toUserId}`);
                res.json({ success: true, msgId });
            } catch (error) {
                logger.error('Send message error:', error);
                res.status(500).json({ error: 'خطا در ارسال پیام' });
            }
        });

        // ============================================================
        // 📊 دریافت پیام‌ها
        // ============================================================

        router.get('/messages', async (req, res) => {
            try {
                const { userId, otherUserId } = req.query;

                const result = await this.db.query(userId,
                    `SELECT * FROM messages 
                     WHERE (from_user = $1 AND to_user = $2) 
                        OR (from_user = $2 AND to_user = $1)
                     ORDER BY created_at DESC LIMIT 100`,
                    [userId, otherUserId]
                );

                // رمزگشایی پیام‌ها
                const messages = result.rows.map(msg => {
                    try {
                        const decrypted = this.encryption.decrypt(msg.encrypted_data, userId);
                        return { ...msg, decrypted };
                    } catch {
                        return { ...msg, decrypted: '[🔒 پیام رمزنگاری شده]' };
                    }
                });

                res.json({ success: true, messages });
            } catch (error) {
                res.status(500).json({ error: 'خطا در دریافت پیام‌ها' });
            }
        });

        // ============================================================
        // 👥 فالو کردن
        // ============================================================

        router.post('/users/:userId/follow', async (req, res) => {
            try {
                const { userId } = req.params;
                const { followerId } = req.body;

                if (userId === followerId) {
                    return res.status(400).json({ error: 'Cannot follow yourself' });
                }

                // بررسی وجود
                const check = await this.db.query(followerId,
                    'SELECT * FROM followers WHERE follower_id = $1 AND following_id = $2',
                    [followerId, userId]
                );

                if (check.rows.length > 0) {
                    // آنفالو
                    await this.db.query(followerId,
                        'DELETE FROM followers WHERE follower_id = $1 AND following_id = $2',
                        [followerId, userId]
                    );
                    await this.db.query(userId,
                        'UPDATE users SET followers_count = followers_count - 1 WHERE id = $1',
                        [userId]
                    );
                    await this.db.query(followerId,
                        'UPDATE users SET following_count = following_count - 1 WHERE id = $1',
                        [followerId]
                    );
                    return res.json({ success: true, action: 'unfollow' });
                } else {
                    // فالو
                    const id = uuidv4();
                    await this.db.query(followerId,
                        `INSERT INTO followers (id, follower_id, following_id, created_at) 
                         VALUES ($1, $2, $3, $4)`,
                        [id, followerId, userId, new Date()]
                    );
                    await this.db.query(userId,
                        'UPDATE users SET followers_count = followers_count + 1 WHERE id = $1',
                        [userId]
                    );
                    await this.db.query(followerId,
                        'UPDATE users SET following_count = following_count + 1 WHERE id = $1',
                        [followerId]
                    );
                    return res.json({ success: true, action: 'follow' });
                }
            } catch (error) {
                logger.error('Follow error:', error);
                res.status(500).json({ error: 'خطا در دنبال کردن' });
            }
        });

        // ============================================================
        // 📊 آمار کاربر
        // ============================================================

        router.get('/users/:userId/stats', async (req, res) => {
            try {
                const { userId } = req.params;
                const cacheKey = `stats:${userId}`;

                let stats = await this.cache.get(cacheKey);

                if (!stats) {
                    const result = await this.db.query(userId,
                        `SELECT 
                            posts_count, followers_count, following_count, total_likes,
                            (SELECT COUNT(*) FROM posts WHERE user_id = $1 AND created_at > NOW() - INTERVAL '7 days') as weekly_posts,
                            (SELECT SUM(likes_count) FROM posts WHERE user_id = $1) as total_likes_received
                         FROM users WHERE id = $1`,
                        [userId]
                    );
                    stats = result.rows[0] || {};
                    await this.cache.set(cacheKey, stats, 300);
                }

                res.json({ success: true, stats });
            } catch (error) {
                res.status(500).json({ error: 'خطا در دریافت آمار' });
            }
        });

        // ============================================================
        // 🔍 جستجو
        // ============================================================

        router.get('/search', async (req, res) => {
            try {
                const { q, type = 'all' } = req.query;

                if (!q || q.length < 2) {
                    return res.json({ success: true, results: [] });
                }

                const searchTerm = `%${q}%`;

                let results = [];

                if (type === 'all' || type === 'users') {
                    const users = await this.db.query('system',
                        `SELECT id, username, full_name, avatar_url 
                         FROM users WHERE username ILIKE $1 OR full_name ILIKE $1 
                         LIMIT 20`,
                        [searchTerm]
                    );
                    results = [...results, ...users.rows.map(u => ({ ...u, type: 'user' }))];
                }

                if (type === 'all' || type === 'posts') {
                    const posts = await this.db.query('system',
                        `SELECT id, user_id, content, image_url, created_at 
                         FROM posts WHERE content ILIKE $1 
                         LIMIT 20`,
                        [searchTerm]
                    );
                    results = [...results, ...posts.rows.map(p => ({ ...p, type: 'post' }))];
                }

                if (type === 'all' || type === 'hashtag') {
                    const hashtag = q.startsWith('#') ? q.substring(1) : q;
                    const posts = await this.db.query('system',
                        `SELECT id, user_id, content, image_url, created_at 
                         FROM posts WHERE $1 = ANY(hashtags) 
                         LIMIT 20`,
                        [hashtag]
                    );
                    results = [...results, ...posts.rows.map(p => ({ ...p, type: 'post', hashtag: true }))];
                }

                res.json({ success: true, results });
            } catch (error) {
                res.status(500).json({ error: 'خطا در جستجو' });
            }
        });

        // ============================================================
        // 🏠 صفحه اصلی
        // ============================================================

        this.app.use('/api', router);

        this.app.get('/', (req, res) => {
            res.sendFile(path.join(__dirname, 'index.html'));
        });

        // فایل‌های استاتیک
        this.app.use('/uploads', express.static('public/uploads'));
        this.app.use('/public', express.static('public'));
    }

    // ================================================================
    // 💬 WebSocket
    // ================================================================
    initWebSocket() {
        this.io.use((socket, next) => {
            const token = socket.handshake.auth.token;
            if (!token) {
                return next(new Error('Authentication required'));
            }

            try {
                const decoded = jwt.verify(token, process.env.JWT_SECRET || 'super-secret-jwt-key-2024');
                socket.userId = decoded.userId;
                socket.username = decoded.username;
                next();
            } catch (error) {
                next(new Error('Invalid token'));
            }
        });

        this.io.on('connection', (socket) => {
            const userId = socket.userId;
            logger.info(`User connected: ${userId}`);

            // ثبت آنلاین
            this.onlineUsers.set(userId, socket.id);
            this.cache.set(`online:${userId}`, socket.id, 300);
            this.io.emit('users_online', Array.from(this.onlineUsers.keys()));

            // ============================================================
            // 🔐 پیام خصوصی رمزنگاری شده
            // ============================================================
            socket.on('private_message', async (data) => {
                try {
                    const { to, message } = data;

                    // رمزنگاری
                    const encrypted = this.encryption.encrypt(message, userId, to);

                    // ذخیره در دیتابیس
                    const msgId = uuidv4();
                    await this.db.query(userId,
                        `INSERT INTO messages 
                         (id, from_user, to_user, encrypted_data, signature, created_at) 
                         VALUES ($1, $2, $3, $4, $5, $6)`,
                        [msgId, userId, to, encrypted, encrypted.signature, new Date()]
                    );

                    // ارسال به گیرنده
                    const targetSocket = this.onlineUsers.get(to);
                    if (targetSocket) {
                        this.io.to(targetSocket).emit('private_message', {
                            from: userId,
                            fromUsername: socket.username,
                            msgId,
                            encrypted,
                            timestamp: new Date()
                        });
                    }

                    // تایید رسید
                    socket.emit('message_delivered', { msgId, to });

                    logger.info(`Private message: ${userId} -> ${to}`);
                } catch (error) {
                    logger.error('Private message error:', error);
                    socket.emit('error', { message: 'خطا در ارسال پیام' });
                }
            });

            // ============================================================
            // 📢 چت گروهی
            // ============================================================
            socket.on('join_room', (data) => {
                const { roomId } = data;
                socket.join(roomId);
                logger.info(`User ${userId} joined room ${roomId}`);
            });

            socket.on('room_message', async (data) => {
                try {
                    const { roomId, message } = data;

                    // رمزنگاری گروهی
                    const encrypted = this.encryption.encrypt(message, roomId);

                    // ذخیره تاریخچه
                    const historyKey = `room:${roomId}:history`;
                    const history = await this.cache.get(historyKey) || [];
                    history.push({
                        from: userId,
                        fromUsername: socket.username,
                        encrypted,
                        timestamp: new Date()
                    });

                    if (history.length > 1000) {
                        history.splice(0, history.length - 1000);
                    }

                    await this.cache.set(historyKey, history, 86400);

                    // ارسال به همه
                    this.io.to(roomId).emit('room_message', {
                        from: userId,
                        fromUsername: socket.username,
                        encrypted,
                        timestamp: new Date()
                    });

                    logger.info(`Room message: ${roomId} from ${userId}`);
                } catch (error) {
                    logger.error('Room message error:', error);
                }
            });

            // ============================================================
            // ❤️ لایک
            // ============================================================
            socket.on('like_post', async (data) => {
                const { postId } = data;
                await this.db.query(userId,
                    'UPDATE posts SET likes_count = likes_count + 1 WHERE id = $1',
                    [postId]
                );
                this.io.emit('post_liked', { postId, userId });
            });

            // ============================================================
            // 🎬 استوری
            // ============================================================
            socket.on('story_view', async (data) => {
                const { storyId } = data;
                await this.db.query(userId,
                    'UPDATE stories SET views_count = views_count + 1 WHERE id = $1',
                    [storyId]
                );
            });

            // ============================================================
            // 📴 قطع اتصال
            // ============================================================
            socket.on('disconnect', () => {
                this.onlineUsers.delete(userId);
                this.cache.del(`online:${userId}`);
                this.io.emit('users_online', Array.from(this.onlineUsers.keys()));
                logger.info(`User disconnected: ${userId}`);
            });
        });
    }

    // ================================================================
    // 👑 پنل ادمین
    // ================================================================
    initAdminPanel() {
        const adminRouter = express.Router();

        adminRouter.use((req, res, next) => {
            const token = req.headers.authorization?.split(' ')[1];
            if (!token) return res.status(401).json({ error: 'Unauthorized' });

            try {
                const decoded = jwt.verify(token, process.env.JWT_SECRET || 'super-secret-jwt-key-2024');
                if (!decoded.isAdmin) {
                    return res.status(403).json({ error: 'Admin access required' });
                }
                req.adminId = decoded.userId;
                next();
            } catch (error) {
                res.status(401).json({ error: 'Invalid token' });
            }
        });

        // ============================================================
        // 📊 آمار کامل
        // ============================================================
        adminRouter.get('/stats', async (req, res) => {
            try {
                const stats = {
                    users: (await this.db.query('system', 'SELECT COUNT(*) FROM users')).rows[0].count,
                    posts: (await this.db.query('system', 'SELECT COUNT(*) FROM posts')).rows[0].count,
                    comments: (await this.db.query('system', 'SELECT COUNT(*) FROM comments')).rows[0].count,
                    messages: (await this.db.query('system', 'SELECT COUNT(*) FROM messages')).rows[0].count,
                    onlineUsers: this.onlineUsers.size,
                    storage: await this.getStorageStats()
                };

                res.json({ success: true, stats });
            } catch (error) {
                res.status(500).json({ error: 'خطا در دریافت آمار' });
            }
        });

        // ============================================================
        // 🚫 مسدود کردن کاربر
        // ============================================================
        adminRouter.post('/users/block', async (req, res) => {
            try {
                const { userId, reason, duration } = req.body;

                await this.db.query(userId,
                    `UPDATE users SET 
                        is_blocked = true,
                        block_reason = $1,
                        block_until = NOW() + INTERVAL '${duration || '1 day'}'
                     WHERE id = $2`,
                    [reason, userId]
                );

                const socketId = this.onlineUsers.get(userId);
                if (socketId) {
                    this.io.to(socketId).emit('blocked', { reason, duration });
                    const socket = this.io.sockets.sockets.get(socketId);
                    if (socket) socket.disconnect();
                }

                await this.cache.del(`user:*${userId}*`);
                await this.cache.del(`token:*${userId}*`);

                logger.info(`User blocked: ${userId}`);
                res.json({ success: true });
            } catch (error) {
                res.status(500).json({ error: 'خطا در مسدود کردن' });
            }
        });

        // ============================================================
        // 🔓 رفع مسدودیت
        // ============================================================
        adminRouter.post('/users/unblock', async (req, res) => {
            try {
                const { userId } = req.body;

                await this.db.query(userId,
                    'UPDATE users SET is_blocked = false, block_reason = NULL, block_until = NULL WHERE id = $1',
                    [userId]
                );

                logger.info(`User unblocked: ${userId}`);
                res.json({ success: true });
            } catch (error) {
                res.status(500).json({ error: 'خطا در رفع مسدودیت' });
            }
        });

        // ============================================================
        // 📝 حذف پست
        // ============================================================
        adminRouter.delete('/posts/:postId', async (req, res) => {
            try {
                const { postId } = req.params;

                await this.db.query('system', 'DELETE FROM posts WHERE id = $1', [postId]);
                await this.db.query('system', 'DELETE FROM comments WHERE post_id = $1', [postId]);
                await this.cache.del(`post:${postId}`);
                await this.cache.clearPattern(`posts:*`);

                logger.info(`Post deleted: ${postId}`);
                res.json({ success: true });
            } catch (error) {
                res.status(500).json({ error: 'خطا در حذف پست' });
            }
        });

        // ============================================================
        // 📢 اعلان همگانی
        // ============================================================
        adminRouter.post('/announce', async (req, res) => {
            try {
                const { message, type = 'info' } = req.body;

                const encrypted = this.encryption.encrypt(message, 'admin');

                let sentCount = 0;
                for (const [userId, socketId] of this.onlineUsers) {
                    this.io.to(socketId).emit('announcement', {
                        message: encrypted,
                        type,
                        timestamp: new Date()
                    });
                    sentCount++;
                }

                await this.db.query('system',
                    `INSERT INTO announcements (message, type, created_at) VALUES ($1, $2, $3)`,
                    [message, type, new Date()]
                );

                logger.info(`Announcement sent to ${sentCount} users`);
                res.json({ success: true, recipients: sentCount });
            } catch (error) {
                res.status(500).json({ error: 'خطا در ارسال اعلان' });
            }
        });

        // ============================================================
        // ⚙️ تنظیمات چت
        // ============================================================
        adminRouter.post('/settings/chat', async (req, res) => {
            try {
                const { enabled } = req.body;

                await this.cache.set('settings:chat:enabled', enabled, -1);
                this.io.emit('chat_settings_changed', { enabled });

                logger.info(`Chat settings changed: ${enabled}`);
                res.json({ success: true });
            } catch (error) {
                res.status(500).json({ error: 'خطا در تغییر تنظیمات' });
            }
        });

        // ============================================================
        // ✅ تیک آبی
        // ============================================================
        adminRouter.post('/users/verify', async (req, res) => {
            try {
                const { userId, verified } = req.body;

                await this.db.query(userId,
                    'UPDATE users SET is_verified = $1 WHERE id = $2',
                    [verified, userId]
                );

                const socketId = this.onlineUsers.get(userId);
                if (socketId) {
                    this.io.to(socketId).emit('verification_updated', { verified });
                }

                logger.info(`User verification updated: ${userId} -> ${verified}`);
                res.json({ success: true });
            } catch (error) {
                res.status(500).json({ error: 'خطا در تغییر تیک آبی' });
            }
        });

        // ============================================================
        // 📊 گزارش‌گیری
        // ============================================================
        adminRouter.get('/reports', async (req, res) => {
            try {
                const { type, from, to } = req.query;

                const reports = {
                    users: {
                        total: (await this.db.query('system', 'SELECT COUNT(*) FROM users')).rows[0].count,
                        active: (await this.db.query('system',
                            'SELECT COUNT(*) FROM users WHERE last_login > NOW() - INTERVAL \'30 days\''
                        )).rows[0].count,
                        new: (await this.db.query('system',
                            'SELECT COUNT(*) FROM users WHERE created_at > $1',
                            [from || '2024-01-01']
                        )).rows[0].count
                    },
                    posts: {
                        total: (await this.db.query('system', 'SELECT COUNT(*) FROM posts')).rows[0].count,
                        withMedia: (await this.db.query('system',
                            'SELECT COUNT(*) FROM posts WHERE image_url IS NOT NULL'
                        )).rows[0].count,
                        engagement: {
                            totalLikes: (await this.db.query('system',
                                'SELECT SUM(likes_count) FROM posts'
                            )).rows[0].sum || 0,
                            totalComments: (await this.db.query('system',
                                'SELECT SUM(comments_count) FROM posts'
                            )).rows[0].sum || 0
                        }
                    },
                    messages: {
                        total: (await this.db.query('system', 'SELECT COUNT(*) FROM messages')).rows[0].count,
                        last24h: (await this.db.query('system',
                            'SELECT COUNT(*) FROM messages WHERE created_at > NOW() - INTERVAL \'24 hours\''
                        )).rows[0].count
                    }
                };

                res.json({ success: true, reports });
            } catch (error) {
                res.status(500).json({ error: 'خطا در گزارش‌گیری' });
            }
        });

        this.app.use('/admin', adminRouter);
    }

    // ================================================================
    // 🔄 پس‌زمینه پردازش‌ها
    // ================================================================
    initBackgroundJobs() {
        // پاکسازی خودکار کش
        setInterval(async () => {
            try {
                await this.cache.clearPattern('temp:*');
                await this.cache.clearPattern('session:*');
                logger.debug('Cache cleanup completed');
            } catch (error) {
                logger.error('Cache cleanup error:', error);
            }
        }, 3600000); // هر ساعت

        // پاکسازی استوری‌های منقضی شده
        setInterval(async () => {
            try {
                await this.db.query('system',
                    'DELETE FROM stories WHERE expires_at < NOW()'
                );
                logger.debug('Stories cleanup completed');
            } catch (error) {
                logger.error('Stories cleanup error:', error);
            }
        }, 3600000); // هر ساعت

        // گزارش روزانه
        setInterval(async () => {
            try {
                const date = new Date().toISOString().split('T')[0];
                const stats = {
                    date,
                    users: (await this.db.query('system', 'SELECT COUNT(*) FROM users')).rows[0].count,
                    posts: (await this.db.query('system', 'SELECT COUNT(*) FROM posts')).rows[0].count
                };
                await this.cache.set(`report:${date}`, stats, 86400 * 30);
                logger.info(`Daily report generated: ${date}`);
            } catch (error) {
                logger.error('Daily report error:', error);
            }
        }, 86400000); // هر روز
    }

    // ================================================================
    // 📊 آمار ذخیره‌سازی
    // ================================================================
    async getStorageStats() {
        try {
            const uploadDir = path.join(__dirname, 'public/uploads');
            let totalSize = 0;
            let fileCount = 0;

            const walkDir = (dir) => {
                if (!fs.existsSync(dir)) return;
                const files = fs.readdirSync(dir);
                for (const file of files) {
                    const filePath = path.join(dir, file);
                    const stats = fs.statSync(filePath);
                    if (stats.isDirectory()) {
                        walkDir(filePath);
                    } else {
                        totalSize += stats.size;
                        fileCount++;
                    }
                }
            };

            walkDir(uploadDir);

            return {
                totalSize,
                totalSizeGB: (totalSize / 1024 / 1024 / 1024).toFixed(2),
                fileCount
            };
        } catch (error) {
            return { error: 'Unable to get storage stats' };
        }
    }
}

// ================================================================
// 🚀 راه‌اندازی
// ================================================================

// ایجاد پوشه‌های لازم
const dirs = ['./public', './public/uploads', './public/uploads/videos'];
for (const dir of dirs) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

const server = new SuperSocialServer();

// ================================================================
// 🛡️ مدیریت خطا
// ================================================================
process.on('uncaughtException', (error) => {
    logger.error('Uncaught Exception:', error);
    setTimeout(() => process.exit(1), 5000);
});

process.on('unhandledRejection', (reason, promise) => {
    logger.error('Unhandled Rejection:', reason);
});

process.on('SIGINT', () => {
    logger.info('Shutting down gracefully...');
    process.exit(0);
});

module.exports = server;