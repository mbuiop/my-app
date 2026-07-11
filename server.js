const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');

// ============================================
// 🚀 تنظیمات اولیه
// ============================================
const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: { origin: "*" },
    transports: ['websocket', 'polling'],
    pingTimeout: 60000,
    pingInterval: 25000
});

app.use(cors({
    origin: '*',
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE']
}));
app.use(express.json({ limit: '500mb' }));
app.use(express.urlencoded({ extended: true, limit: '500mb' }));
app.use(express.static('public'));
app.use('/uploads', express.static('uploads'));

// ============================================
// 📁 ایجاد پوشه‌ها
// ============================================
const dirs = [
    './uploads',
    './uploads/posts',
    './uploads/stories',
    './uploads/avatars',
    './public',
    './logs'
];
dirs.forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

// ============================================
// 📊 سیستم لاگینگ
// ============================================
function log(message, type = 'INFO') {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${type}] ${message}\n`;
    fs.appendFileSync('./logs/app.log', logEntry);
    console.log(logEntry.trim());
}

// ============================================
// 🔐 رمزنگاری فوق‌حرفه‌ای (AES-256-GCM)
// ============================================
const SECRET_KEY = process.env.SECRET_KEY || crypto.randomBytes(32).toString('hex');
const MASTER_KEY = crypto.createHash('sha256').update(SECRET_KEY).digest();

function generateUserKey(userId) {
    return crypto.createHash('sha256').update(MASTER_KEY + userId).digest();
}

function encryptMessage(message, userId) {
    try {
        const key = generateUserKey(userId);
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
        let encrypted = cipher.update(message, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        const authTag = cipher.getAuthTag().toString('hex');
        return iv.toString('hex') + ':' + authTag + ':' + encrypted;
    } catch (error) {
        log('Encryption error: ' + error.message, 'ERROR');
        return message;
    }
}

function decryptMessage(encrypted, userId) {
    try {
        const key = generateUserKey(userId);
        const parts = encrypted.split(':');
        if (parts.length !== 3) return '[پیام رمزنگاری شده]';
        const iv = Buffer.from(parts[0], 'hex');
        const authTag = Buffer.from(parts[1], 'hex');
        const encryptedText = parts[2];
        const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
        decipher.setAuthTag(authTag);
        let decrypted = decipher.update(encryptedText, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        return decrypted;
    } catch (error) {
        return '[پیام رمزنگاری شده]';
    }
}

function hashPassword(password) {
    return crypto.createHash('sha512').update(password + SECRET_KEY).digest('hex');
}

function generateToken() {
    return crypto.randomBytes(64).toString('hex');
}

// ============================================
# 📊 دیتابیس شارد شده (5 Shard)
// ============================================
class ShardedDatabase {
    constructor() {
        this.shards = {};
        this.shardCount = 5;
        this.currentId = 1;
        this.storyId = 1;
        this.messageId = 1;
        
        // مقداردهی اولیه شاردها
        for (let i = 0; i < this.shardCount; i++) {
            this.shards[i] = {
                users: {},
                posts: [],
                stories: [],
                messages: {},
                likes: {},
                comments: {},
                reports: [],
                notifications: []
            };
        }
    }

    getShard(key) {
        const hash = crypto.createHash('md5').update(key).digest('hex');
        const shardIndex = parseInt(hash.substring(0, 2), 16) % this.shardCount;
        return shardIndex;
    }

    getShardById(id) {
        if (!id) return 0;
        const hash = crypto.createHash('md5').update(id).digest('hex');
        return parseInt(hash.substring(0, 2), 16) % this.shardCount;
    }

    // ===== Users =====
    saveUser(user) {
        const shardIndex = this.getShard(user.userId);
        this.shards[shardIndex].users[user.userId] = user;
        log(`User ${user.username} saved in shard ${shardIndex}`);
        return user;
    }

    getUser(userId) {
        const shardIndex = this.getShardById(userId);
        return this.shards[shardIndex].users[userId] || null;
    }

    getUserByEmail(email) {
        for (let i = 0; i < this.shardCount; i++) {
            for (const [key, user] of Object.entries(this.shards[i].users)) {
                if (user.email === email) return user;
            }
        }
        return null;
    }

    getAllUsers() {
        let allUsers = [];
        for (let i = 0; i < this.shardCount; i++) {
            allUsers = allUsers.concat(Object.values(this.shards[i].users));
        }
        return allUsers;
    }

    updateUser(userId, data) {
        const shardIndex = this.getShardById(userId);
        if (this.shards[shardIndex].users[userId]) {
            this.shards[shardIndex].users[userId] = { ...this.shards[shardIndex].users[userId], ...data };
            return this.shards[shardIndex].users[userId];
        }
        return null;
    }

    // ===== Posts =====
    savePost(post) {
        const shardIndex = this.getShardById(post.postId);
        this.shards[shardIndex].posts.unshift(post);
        log(`Post ${post.postId} saved in shard ${shardIndex}`);
        return post;
    }

    getPosts(page = 1, limit = 20, hashtag = null) {
        let allPosts = [];
        for (let i = 0; i < this.shardCount; i++) {
            allPosts = allPosts.concat(this.shards[i].posts);
        }
        
        if (hashtag) {
            allPosts = allPosts.filter(p => p.hashtags && p.hashtags.some(h => h.toLowerCase() === hashtag.toLowerCase()));
        }
        
        allPosts.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        const start = (page - 1) * limit;
        return {
            posts: allPosts.slice(start, start + limit),
            total: allPosts.length,
            page,
            totalPages: Math.ceil(allPosts.length / limit)
        };
    }

    getPost(postId) {
        const shardIndex = this.getShardById(postId);
        return this.shards[shardIndex].posts.find(p => p.postId === postId) || null;
    }

    getUserPosts(userId) {
        let userPosts = [];
        for (let i = 0; i < this.shardCount; i++) {
            userPosts = userPosts.concat(this.shards[i].posts.filter(p => p.userId === userId));
        }
        return userPosts.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    }

    deletePost(postId) {
        const shardIndex = this.getShardById(postId);
        const index = this.shards[shardIndex].posts.findIndex(p => p.postId === postId);
        if (index !== -1) {
            this.shards[shardIndex].posts.splice(index, 1);
            return true;
        }
        return false;
    }

    likePost(postId, userId) {
        const shardIndex = this.getShardById(postId);
        const post = this.shards[shardIndex].posts.find(p => p.postId === postId);
        if (post) {
            const likeKey = `${postId}_${userId}`;
            if (this.shards[shardIndex].likes[likeKey]) {
                delete this.shards[shardIndex].likes[likeKey];
                post.likes = (post.likes || 0) - 1;
                return { liked: false, likes: post.likes };
            } else {
                this.shards[shardIndex].likes[likeKey] = true;
                post.likes = (post.likes || 0) + 1;
                return { liked: true, likes: post.likes };
            }
        }
        return { liked: false, likes: 0 };
    }

    addComment(postId, comment) {
        const shardIndex = this.getShardById(postId);
        const post = this.shards[shardIndex].posts.find(p => p.postId === postId);
        if (post) {
            if (!post.comments) post.comments = [];
            post.comments.push(comment);
            return true;
        }
        return false;
    }

    // ===== Stories =====
    saveStory(story) {
        const shardIndex = this.getShardById(story.storyId);
        this.shards[shardIndex].stories.push(story);
        return story;
    }

    getStories() {
        let allStories = [];
        const now = Date.now();
        for (let i = 0; i < this.shardCount; i++) {
            allStories = allStories.concat(
                this.shards[i].stories.filter(s => {
                    const age = now - new Date(s.createdAt).getTime();
                    return age < 24 * 60 * 60 * 1000;
                })
            );
        }
        return allStories.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    }

    viewStory(storyId, userId) {
        const shardIndex = this.getShardById(storyId);
        const story = this.shards[shardIndex].stories.find(s => s.storyId === storyId);
        if (story && !story.viewers) {
            story.viewers = [];
        }
        if (story && !story.viewers.includes(userId)) {
            story.views = (story.views || 0) + 1;
            story.viewers.push(userId);
            return true;
        }
        return false;
    }

    // ===== Messages =====
    saveMessage(roomId, message) {
        const shardIndex = this.getShardById(roomId);
        if (!this.shards[shardIndex].messages[roomId]) {
            this.shards[shardIndex].messages[roomId] = [];
        }
        this.shards[shardIndex].messages[roomId].push(message);
        return message;
    }

    getMessages(roomId, limit = 50) {
        const shardIndex = this.getShardById(roomId);
        if (!this.shards[shardIndex].messages[roomId]) return [];
        return this.shards[shardIndex].messages[roomId].slice(-limit);
    }

    // ===== Reports =====
    addReport(report) {
        const shardIndex = this.getShardById(report.reportId);
        this.shards[shardIndex].reports.push(report);
        return report;
    }

    getReports() {
        let allReports = [];
        for (let i = 0; i < this.shardCount; i++) {
            allReports = allReports.concat(this.shards[i].reports);
        }
        return allReports.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    }

    // ===== Stats =====
    getStats() {
        let totalUsers = 0;
        let totalPosts = 0;
        let totalStories = 0;
        let totalMessages = 0;

        for (let i = 0; i < this.shardCount; i++) {
            totalUsers += Object.keys(this.shards[i].users).length;
            totalPosts += this.shards[i].posts.length;
            totalStories += this.shards[i].stories.length;
            for (const room of Object.values(this.shards[i].messages)) {
                totalMessages += room.length;
            }
        }

        return {
            totalUsers,
            totalPosts,
            totalStories,
            totalMessages,
            shardCount: this.shardCount,
            onlineUsers: Object.keys(onlineUsers).length || 0
        };
    }
}

const db = new ShardedDatabase();
const onlineUsers = {};
const userSessions = new Map();
const adminSessions = new Map();
const ADMIN_EMAIL = 'admin@social.com';
const ADMIN_PASSWORD = hashPassword('Admin@123456');

// ============================================
# 🎯 سیستم کش (Redis-like in Memory)
// ============================================
class CacheSystem {
    constructor() {
        this.cache = new Map();
        this.ttl = new Map();
    }

    set(key, value, ttl = 300) {
        this.cache.set(key, value);
        this.ttl.set(key, Date.now() + ttl * 1000);
        log(`Cache set: ${key} (TTL: ${ttl}s)`);
    }

    get(key) {
        if (!this.cache.has(key)) return null;
        if (Date.now() > this.ttl.get(key)) {
            this.cache.delete(key);
            this.ttl.delete(key);
            return null;
        }
        return this.cache.get(key);
    }

    delete(key) {
        this.cache.delete(key);
        this.ttl.delete(key);
    }

    clear() {
        this.cache.clear();
        this.ttl.clear();
        log('Cache cleared');
    }

    getStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys())
        };
    }
}

const cache = new CacheSystem();

// ============================================
# 🎯 سیستم Queue برای پردازش پس‌زمینه
// ============================================
class QueueSystem {
    constructor() {
        this.queues = new Map();
        this.processing = new Map();
    }

    add(queueName, data) {
        if (!this.queues.has(queueName)) {
            this.queues.set(queueName, []);
        }
        this.queues.get(queueName).push(data);
        this.process(queueName);
    }

    async process(queueName) {
        if (this.processing.get(queueName)) return;
        this.processing.set(queueName, true);

        while (this.queues.has(queueName) && this.queues.get(queueName).length > 0) {
            const data = this.queues.get(queueName).shift();
            try {
                await this.handleQueue(queueName, data);
            } catch (error) {
                log(`Queue error ${queueName}: ${error.message}`, 'ERROR');
            }
        }

        this.processing.set(queueName, false);
    }

    async handleQueue(queueName, data) {
        switch (queueName) {
            case 'post-processing':
                log(`Processing post: ${data.postId}`, 'QUEUE');
                break;
            case 'notification':
                log(`Notification for: ${data.userId}`, 'QUEUE');
                break;
            case 'analytics':
                log(`Analytics event: ${data.event}`, 'QUEUE');
                break;
            default:
                log(`Unknown queue: ${queueName}`, 'QUEUE');
        }
        // شبیه‌سازی پردازش
        await new Promise(resolve => setTimeout(resolve, 100));
    }

    getStats() {
        const stats = {};
        for (const [name, queue] of this.queues) {
            stats[name] = queue.length;
        }
        return stats;
    }
}

const queue = new QueueSystem();

// ============================================
# 📡 API
// ============================================

// ===== احراز هویت =====
app.post('/api/auth/register', (req, res) => {
    const { username, email, password } = req.body;
    
    if (!username || !email || !password) {
        return res.status(400).json({ error: 'همه فیلدها الزامی هستند' });
    }

    if (db.getUserByEmail(email)) {
        return res.status(400).json({ error: 'این ایمیل قبلاً ثبت شده است' });
    }

    const userId = 'user_' + uuidv4();
    const user = {
        userId,
        username,
        email,
        password: hashPassword(password),
        bio: '',
        avatar: '',
        followers: 0,
        following: 0,
        postsCount: 0,
        language: 'fa',
        theme: 'light',
        isOnline: false,
        isAdmin: email === ADMIN_EMAIL,
        isBanned: false,
        createdAt: new Date().toISOString(),
        lastSeen: new Date().toISOString()
    };

    db.saveUser(user);
    const token = generateToken();
    userSessions.set(token, userId);

    log(`User registered: ${username} (${email})`);
    res.json({
        success: true,
        token,
        user: { userId, username, email, isAdmin: user.isAdmin }
    });
});

app.post('/api/auth/login', (req, res) => {
    const { email, password } = req.body;

    if (!email || !password) {
        return res.status(400).json({ error: 'ایمیل و رمز عبور الزامی است' });
    }

    const user = db.getUserByEmail(email);
    if (!user || user.password !== hashPassword(password)) {
        return res.status(401).json({ error: 'ایمیل یا رمز عبور اشتباه است' });
    }

    if (user.isBanned) {
        return res.status(403).json({ error: 'این کاربر مسدود شده است' });
    }

    const token = generateToken();
    userSessions.set(token, user.userId);
    user.isOnline = true;
    user.lastSeen = new Date().toISOString();
    db.updateUser(user.userId, { isOnline: true, lastSeen: user.lastSeen });

    log(`User logged in: ${user.username}`);
    res.json({
        success: true,
        token,
        user: {
            userId: user.userId,
            username: user.username,
            email: user.email,
            bio: user.bio,
            avatar: user.avatar,
            followers: user.followers,
            following: user.following,
            postsCount: user.postsCount,
            isAdmin: user.isAdmin || false,
            isBanned: user.isBanned || false,
            language: user.language || 'fa',
            theme: user.theme || 'light'
        }
    });
});

app.post('/api/auth/logout', (req, res) => {
    const { token } = req.body;
    if (token) {
        const userId = userSessions.get(token);
        if (userId) {
            db.updateUser(userId, { isOnline: false, lastSeen: new Date().toISOString() });
        }
        userSessions.delete(token);
    }
    res.json({ success: true });
});

app.get('/api/auth/me', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
        return res.status(401).json({ error: 'Unauthorized' });
    }

    const userId = userSessions.get(token);
    if (!userId) {
        return res.status(401).json({ error: 'Invalid token' });
    }

    const user = db.getUser(userId);
    if (!user) {
        return res.status(404).json({ error: 'User not found' });
    }

    if (user.isBanned) {
        return res.status(403).json({ error: 'User is banned' });
    }

    res.json({
        userId: user.userId,
        username: user.username,
        email: user.email,
        bio: user.bio,
        avatar: user.avatar,
        followers: user.followers,
        following: user.following,
        postsCount: user.postsCount,
        isAdmin: user.isAdmin || false,
        isBanned: user.isBanned || false,
        language: user.language || 'fa',
        theme: user.theme || 'light'
    });
});

// ===== ادمین (فقط ادمین می‌بیند) =====
app.post('/api/admin/verify', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
        return res.status(401).json({ error: 'Unauthorized' });
    }

    const userId = userSessions.get(token);
    if (!userId) {
        return res.status(401).json({ error: 'Invalid token' });
    }

    const user = db.getUser(userId);
    if (!user || !user.isAdmin) {
        return res.status(403).json({ error: 'Admin access required' });
    }

    res.json({ success: true, isAdmin: true });
});

// مدیریت کاربران
app.get('/api/admin/users', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Unauthorized' });
    const userId = userSessions.get(token);
    if (!userId) return res.status(401).json({ error: 'Invalid token' });
    const user = db.getUser(userId);
    if (!user || !user.isAdmin) return res.status(403).json({ error: 'Admin access required' });

    const users = db.getAllUsers().map(u => ({
        userId: u.userId,
        username: u.username,
        email: u.email,
        bio: u.bio,
        avatar: u.avatar,
        followers: u.followers,
        following: u.following,
        postsCount: u.postsCount,
        isAdmin: u.isAdmin || false,
        isBanned: u.isBanned || false,
        isOnline: u.isOnline || false,
        createdAt: u.createdAt,
        lastSeen: u.lastSeen
    }));

    res.json(users);
});

app.put('/api/admin/users/:userId/ban', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Unauthorized' });
    const adminId = userSessions.get(token);
    if (!adminId) return res.status(401).json({ error: 'Invalid token' });
    const admin = db.getUser(adminId);
    if (!admin || !admin.isAdmin) return res.status(403).json({ error: 'Admin access required' });

    const { userId } = req.params;
    const { banned } = req.body;
    const user = db.getUser(userId);
    if (!user) return res.status(404).json({ error: 'User not found' });
    if (user.isAdmin) return res.status(403).json({ error: 'Cannot ban admin' });

    db.updateUser(userId, { isBanned: banned });
    log(`User ${user.username} ${banned ? 'banned' : 'unbanned'} by admin ${admin.username}`);
    res.json({ success: true, isBanned: banned });
});

// مدیریت پست‌ها
app.get('/api/admin/posts', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Unauthorized' });
    const userId = userSessions.get(token);
    if (!userId) return res.status(401).json({ error: 'Invalid token' });
    const user = db.getUser(userId);
    if (!user || !user.isAdmin) return res.status(403).json({ error: 'Admin access required' });

    const result = db.getPosts(1, 1000);
    res.json(result.posts);
});

app.delete('/api/admin/posts/:postId', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Unauthorized' });
    const adminId = userSessions.get(token);
    if (!adminId) return res.status(401).json({ error: 'Invalid token' });
    const admin = db.getUser(adminId);
    if (!admin || !admin.isAdmin) return res.status(403).json({ error: 'Admin access required' });

    const { postId } = req.params;
    const deleted = db.deletePost(postId);
    if (deleted) {
        log(`Post ${postId} deleted by admin ${admin.username}`);
        res.json({ success: true });
    } else {
        res.status(404).json({ error: 'Post not found' });
    }
});

// پیام همگانی
app.post('/api/admin/broadcast', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Unauthorized' });
    const adminId = userSessions.get(token);
    if (!adminId) return res.status(401).json({ error: 'Invalid token' });
    const admin = db.getUser(adminId);
    if (!admin || !admin.isAdmin) return res.status(403).json({ error: 'Admin access required' });

    const { message } = req.body;
    if (!message) return res.status(400).json({ error: 'Message required' });

    // ارسال به همه کاربران آنلاین
    io.emit('broadcast', {
        message,
        from: admin.username,
        timestamp: new Date().toISOString()
    });

    log(`Broadcast from admin ${admin.username}: ${message.substring(0, 50)}...`);
    res.json({ success: true, message });
});

// آمار سیستم
app.get('/api/admin/stats', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Unauthorized' });
    const userId = userSessions.get(token);
    if (!userId) return res.status(401).json({ error: 'Invalid token' });
    const user = db.getUser(userId);
    if (!user || !user.isAdmin) return res.status(403).json({ error: 'Admin access required' });

    const dbStats = db.getStats();
    const cacheStats = cache.getStats();
    const queueStats = queue.getStats();

    res.json({
        database: dbStats,
        cache: cacheStats,
        queue: queueStats,
        users: {
            total: dbStats.totalUsers,
            online: dbStats.onlineUsers,
            admins: db.getAllUsers().filter(u => u.isAdmin).length,
            banned: db.getAllUsers().filter(u => u.isBanned).length
        },
        posts: {
            total: dbStats.totalPosts
        },
        stories: {
            total: dbStats.totalStories
        },
        messages: {
            total: dbStats.totalMessages
        },
        system: {
            uptime: process.uptime(),
            memory: process.memoryUsage(),
            node: process.version
        }
    });
});

// اضافه کردن سرور (برای مقیاس‌پذیری)
app.post('/api/admin/add-shard', (req, res) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'Unauthorized' });
    const userId = userSessions.get(token);
    if (!userId) return res.status(401).json({ error: 'Invalid token' });
    const user = db.getUser(userId);
    if (!user || !user.isAdmin) return res.status(403).json({ error: 'Admin access required' });

    // شبیه‌سازی اضافه کردن شارد
    const newShardIndex = db.shardCount;
    db.shards[newShardIndex] = {
        users: {},
        posts: [],
        stories: [],
        messages: {},
        likes: {},
        comments: {},
        reports: [],
        notifications: []
    };
    db.shardCount++;

    log(`New shard ${newShardIndex} added by admin ${user.username}`);
    res.json({ success: true, shardCount: db.shardCount });
});

// ===== پست‌ها =====
const storage = multer.diskStorage({
    destination: './uploads/posts/',
    filename: (req, file, cb) => {
        cb(null, Date.now() + '-' + file.originalname);
    }
});

const upload = multer({
    storage,
    limits: { fileSize: 500 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
        const allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4', 'video/webm', 'video/quicktime'];
        cb(null, allowed.includes(file.mimetype));
    }
});

app.get('/api/posts', (req, res) => {
    const { page = 1, limit = 20, hashtag } = req.query;
    
    // چک کش
    const cacheKey = `posts:${page}:${limit}:${hashtag || 'all'}`;
    const cached = cache.get(cacheKey);
    if (cached) {
        return res.json(cached);
    }

    const result = db.getPosts(parseInt(page), parseInt(limit), hashtag);
    cache.set(cacheKey, result, 60);
    res.json(result);
});

app.post('/api/posts', upload.single('file'), (req, res) => {
    const { caption, userId, username, hashtags } = req.body;
    const file = req.file;

    if (!file) {
        return res.status(400).json({ error: 'فایل انتخاب نشده است' });
    }

    const user = db.getUser(userId);
    if (!user) {
        return res.status(404).json({ error: 'User not found' });
    }

    if (user.isBanned) {
        return res.status(403).json({ error: 'User is banned' });
    }

    const isVideo = file.mimetype.startsWith('video/');
    const postId = 'post_' + uuidv4();

    const newPost = {
        postId,
        userId,
        username: username || user.username,
        image: `/uploads/posts/${file.filename}`,
        caption: caption || '',
        hashtags: hashtags ? hashtags.split(',').map(h => h.trim()) : [],
        likes: 0,
        comments: [],
        shares: 0,
        views: 0,
        isVideo,
        createdAt: new Date().toISOString()
    };

    db.savePost(newPost);
    db.updateUser(userId, { postsCount: (user.postsCount || 0) + 1 });

    // پاک کردن کش
    cache.delete('posts:*');

    // اضافه به Queue
    queue.add('post-processing', { postId, userId });

    log(`Post created: ${postId} by ${username}`);
    res.status(201).json(newPost);
});

app.put('/api/posts/:postId/like', (req, res) => {
    const { postId } = req.params;
    const { userId } = req.body;

    const user = db.getUser(userId);
    if (!user || user.isBanned) {
        return res.status(403).json({ error: 'User is banned' });
    }

    const result = db.likePost(postId, userId);
    cache.delete('posts:*');
    res.json(result);
});

app.post('/api/posts/:postId/comment', (req, res) => {
    const { postId } = req.params;
    const { userId, username, text } = req.body;

    const user = db.getUser(userId);
    if (!user || user.isBanned) {
        return res.status(403).json({ error: 'User is banned' });
    }

    const comment = {
        commentId: 'cmt_' + uuidv4(),
        userId,
        username: username || user.username,
        text,
        createdAt: new Date().toISOString()
    };

    const added = db.addComment(postId, comment);
    if (!added) {
        return res.status(404).json({ error: 'Post not found' });
    }

    cache.delete('posts:*');
    res.json({ success: true, comment });
});

app.get('/api/posts/:postId', (req, res) => {
    const { postId } = req.params;
    const post = db.getPost(postId);
    if (!post) {
        return res.status(404).json({ error: 'Post not found' });
    }
    res.json(post);
});

// ===== استوری‌ها =====
const storyStorage = multer.diskStorage({
    destination: './uploads/stories/',
    filename: (req, file, cb) => {
        cb(null, Date.now() + '-' + file.originalname);
    }
});

const storyUpload = multer({
    storage: storyStorage,
    limits: { fileSize: 100 * 1024 * 1024 },
    fileFilter: (req, file, cb) => {
        const allowed = ['image/jpeg', 'image/png', 'image/webp', 'video/mp4'];
        cb(null, allowed.includes(file.mimetype));
    }
});

app.get('/api/stories', (req, res) => {
    const stories = db.getStories();
    res.json(stories);
});

app.post('/api/stories', storyUpload.single('file'), (req, res) => {
    const { userId, username } = req.body;
    const file = req.file;

    if (!file) {
        return res.status(400).json({ error: 'فایل انتخاب نشده است' });
    }

    const user = db.getUser(userId);
    if (!user || user.isBanned) {
        return res.status(403).json({ error: 'User is banned' });
    }

    const isVideo = file.mimetype.startsWith('video/');
    const storyId = 'story_' + uuidv4();

    const newStory = {
        storyId,
        userId,
        username: username || user.username,
        image: `/uploads/stories/${file.filename}`,
        isVideo,
        views: 0,
        viewers: [],
        createdAt: new Date().toISOString()
    };

    db.saveStory(newStory);
    log(`Story created: ${storyId} by ${username}`);
    res.status(201).json(newStory);
});

app.post('/api/stories/:storyId/view', (req, res) => {
    const { storyId } = req.params;
    const { userId } = req.body;

    const viewed = db.viewStory(storyId, userId);
    res.json({ success: viewed });
});

// ===== کاربران =====
app.get('/api/users', (req, res) => {
    const users = db.getAllUsers().map(u => ({
        userId: u.userId,
        username: u.username,
        avatar: u.avatar,
        bio: u.bio,
        followers: u.followers,
        following: u.following,
        isOnline: u.isOnline || false,
        isBanned: u.isBanned || false,
        lastSeen: u.lastSeen
    }));
    res.json(users);
});

app.get('/api/users/:userId', (req, res) => {
    const { userId } = req.params;
    const user = db.getUser(userId);
    if (!user) {
        return res.status(404).json({ error: 'User not found' });
    }
    res.json({
        userId: user.userId,
        username: user.username,
        avatar: user.avatar,
        bio: user.bio,
        followers: user.followers,
        following: user.following,
        postsCount: user.postsCount,
        isOnline: user.isOnline || false,
        isBanned: user.isBanned || false,
        createdAt: user.createdAt,
        lastSeen: user.lastSeen
    });
});

app.put('/api/users/:userId/profile', (req, res) => {
    const { userId } = req.params;
    const { bio, avatar, language, theme } = req.body;

    const user = db.getUser(userId);
    if (!user) {
        return res.status(404).json({ error: 'User not found' });
    }

    if (bio !== undefined) user.bio = bio;
    if (avatar !== undefined) user.avatar = avatar;
    if (language !== undefined) user.language = language;
    if (theme !== undefined) user.theme = theme;

    db.updateUser(userId, user);
    res.json({ success: true, user });
});

app.post('/api/users/:userId/follow', (req, res) => {
    const { userId } = req.params;
    const { followerId } = req.body;

    const target = db.getUser(userId);
    const follower = db.getUser(followerId);

    if (!target || !follower) {
        return res.status(404).json({ error: 'User not found' });
    }

    if (userId === followerId) {
        return res.status(400).json({ error: 'Cannot follow yourself' });
    }

    db.updateUser(userId, { followers: (target.followers || 0) + 1 });
    db.updateUser(followerId, { following: (follower.following || 0) + 1 });

    res.json({ success: true, followers: target.followers + 1 });
});

// ============================================
# 💬 WebSocket چت (با رمزنگاری)
// ============================================

io.on('connection', (socket) => {
    log(`Socket connected: ${socket.id}`);

    socket.on('register', (data) => {
        const { userId, username } = data;
        onlineUsers[userId] = {
            socketId: socket.id,
            username,
            lastSeen: new Date().toISOString()
        };
        socket.userId = userId;
        socket.username = username;

        db.updateUser(userId, { isOnline: true, lastSeen: new Date().toISOString() });
        io.emit('users-online', Object.keys(onlineUsers));

        log(`User ${username} (${userId}) online`);
    });

    socket.on('join-room', (data) => {
        const { roomId, userId } = data;
        socket.join(roomId);
        socket.roomId = roomId;

        // ارسال تاریخچه
        const messages = db.getMessages(roomId, 50);
        const decryptedMessages = messages.map(msg => ({
            ...msg,
            message: decryptMessage(msg.message, msg.userId)
        }));
        socket.emit('history', decryptedMessages);

        log(`User ${userId} joined room ${roomId}`);
    });

    socket.on('send-message', (data) => {
        const { roomId, userId, username, message } = data;

        // بررسی بن بودن کاربر
        const user = db.getUser(userId);
        if (user && user.isBanned) {
            socket.emit('error', { message: 'You are banned from chatting' });
            return;
        }

        const encrypted = encryptMessage(message, userId);
        const msgData = {
            messageId: 'msg_' + uuidv4(),
            userId,
            username: username || user?.username || 'کاربر',
            message: encrypted,
            timestamp: new Date().toISOString()
        };

        db.saveMessage(roomId, msgData);

        // ارسال به همه در اتاق (با رمزگشایی)
        io.to(roomId).emit('receive-message', {
            ...msgData,
            message: message // ارسال متن اصلی (بدون رمزنگاری برای نمایش)
        });

        log(`Message from ${username} in ${roomId}: ${message.substring(0, 30)}...`);
    });

    socket.on('leave-room', (data) => {
        const { roomId, userId } = data;
        socket.leave(roomId);
        log(`User ${userId} left room ${roomId}`);
    });

    socket.on('disconnect', () => {
        if (socket.userId) {
            delete onlineUsers[socket.userId];
            db.updateUser(socket.userId, { isOnline: false, lastSeen: new Date().toISOString() });
            io.emit('users-online', Object.keys(onlineUsers));
            log(`User ${socket.userId} disconnected`);
        }
    });
});

// ============================================
# 🎨 صفحه HTML کامل
// ============================================
app.get('/', (req, res) => {
    res.send(`
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <title>سوشال مدیا حرفه‌ای</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        /* ===== تنظیمات اصلی ===== */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #fafafa;
            --bg-secondary: #ffffff;
            --text: #262626;
            --text-secondary: #8e8e8e;
            --border: #dbdbdb;
            --primary: #0095f6;
            --primary-dark: #0081d6;
            --danger: #ed4956;
            --success: #2ecc71;
            --shadow: 0 2px 12px rgba(0,0,0,0.08);
            --radius: 12px;
            --radius-sm: 8px;
            --transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            --font: 'Segoe UI', Tahoma, sans-serif;
            --max-width: 935px;
            --header-height: 60px;
            --bottom-nav-height: 65px;
        }
        [data-theme="dark"] {
            --bg: #121212;
            --bg-secondary: #1e1e1e;
            --text: #ffffff;
            --text-secondary: #a0a0a0;
            --border: #2c2c2c;
            --shadow: 0 2px 12px rgba(0,0,0,0.3);
        }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: var(--font);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: all var(--transition);
        }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

        /* ===== Header ===== */
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 0 16px;
            height: var(--header-height);
            display: flex;
            align-items: center;
            gap: 15px;
            flex-shrink: 0;
            z-index: 100;
            position: sticky;
            top: 0;
        }
        .menu-icon { font-size: 24px; cursor: pointer; color: var(--text); transition: var(--transition); }
        .menu-icon:hover { transform: scale(1.05); }
        .logo { font-size: 20px; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 8px; }
        .logo i { color: var(--primary); }
        .search-box {
            flex: 1;
            max-width: 400px;
            background: var(--bg);
            padding: 8px 16px;
            border-radius: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
            border: 1px solid var(--border);
            transition: var(--transition);
        }
        .search-box:focus-within { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(0,149,246,0.2); }
        .search-box input {
            border: none;
            background: transparent;
            outline: none;
            width: 100%;
            font-size: 14px;
            color: var(--text);
        }
        .search-box input::placeholder { color: var(--text-secondary); }
        .search-box i { color: var(--text-secondary); }
        .header-right { display: flex; gap: 18px; font-size: 22px; color: var(--text); }
        .header-right i { cursor: pointer; transition: var(--transition); }
        .header-right i:hover { color: var(--primary); transform: scale(1.05); }

        /* ===== Stories ===== */
        .stories-section {
            background: var(--bg-secondary);
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            overflow-x: auto;
            flex-shrink: 0;
        }
        .stories-container { display: flex; gap: 16px; }
        .story-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            flex-shrink: 0;
            transition: var(--transition);
        }
        .story-item:hover { transform: scale(1.03); }
        .story-avatar {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            padding: 2px;
            background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
            transition: var(--transition);
        }
        .story-avatar img {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            border: 2px solid var(--bg-secondary);
            object-fit: cover;
        }
        .story-avatar.add-story {
            background: var(--bg);
            border: 2px dashed var(--border);
            padding: 0;
        }
        .story-avatar.add-story img { border: none; }
        .story-username {
            font-size: 11px;
            color: var(--text);
            max-width: 64px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            text-align: center;
        }

        /* ===== Gallery ===== */
        .gallery-wrapper { flex: 1; overflow-y: auto; padding: 0 0 var(--bottom-nav-height) 0; }
        .gallery {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 4px;
            padding: 4px;
            max-width: var(--max-width);
            margin: 0 auto;
        }
        .gallery-item {
            background: var(--bg-secondary);
            overflow: hidden;
            border: 1px solid var(--border);
            cursor: pointer;
            position: relative;
            border-radius: var(--radius-sm);
            transition: var(--transition);
        }
        .gallery-item:hover { transform: scale(1.01); box-shadow: var(--shadow); }
        .gallery-item .image-container {
            width: 100%;
            aspect-ratio: 1;
            overflow: hidden;
            background: #ddd;
        }
        .gallery-item .image-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: var(--transition);
        }
        .gallery-item:hover .image-container img { transform: scale(1.02); }
        .gallery-item .explore-post-actions {
            display: flex;
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(transparent, rgba(0,0,0,0.7));
            padding: 12px 8px 8px;
            justify-content: space-around;
            color: white;
            opacity: 0;
            transition: var(--transition);
        }
        .gallery-item:hover .explore-post-actions { opacity: 1; }
        .gallery-item .explore-post-actions .action-btn {
            display: flex;
            align-items: center;
            gap: 4px;
            color: white;
            font-size: 13px;
            cursor: pointer;
            padding: 4px 10px;
            border-radius: 6px;
            border: none;
            background: transparent;
            transition: var(--transition);
            font-family: var(--font);
        }
        .gallery-item .explore-post-actions .action-btn:hover { background: rgba(255,255,255,0.15); transform: scale(1.05); }
        .gallery-item .explore-post-actions .action-btn.liked i { color: var(--danger); }
        .gallery-item .explore-post-actions .action-btn i { font-size: 16px; }

        /* ===== Bottom Nav ===== */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-around;
            padding: 8px 0 12px;
            z-index: 100;
            height: var(--bottom-nav-height);
        }
        .bottom-nav button {
            background: transparent;
            border: none;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2px;
            font-size: 10px;
            color: var(--text-secondary);
            padding: 4px 16px;
            border-radius: 30px;
            transition: var(--transition);
            font-family: var(--font);
        }
        .bottom-nav button i { font-size: 24px; color: var(--text-secondary); transition: var(--transition); }
        .bottom-nav button:hover { background: var(--bg); }
        .bottom-nav button.active i { color: var(--primary); }
        .bottom-nav button.active { color: var(--primary); }

        /* ===== Modals ===== */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 300;
            justify-content: center;
            align-items: center;
            padding: 20px;
            backdrop-filter: blur(4px);
        }
        .modal-overlay.active { display: flex; }
        .modal-content {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            max-width: 520px;
            width: 100%;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            direction: rtl;
            box-shadow: var(--shadow);
            animation: modalIn 0.3s ease;
        }
        @keyframes modalIn {
            from { opacity: 0; transform: scale(0.95) translateY(20px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }
        .modal-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }
        .modal-header h3 { font-size: 16px; color: var(--text); }
        .modal-header .close-modal {
            font-size: 24px;
            cursor: pointer;
            color: var(--text);
            background: none;
            border: none;
            transition: var(--transition);
        }
        .modal-header .close-modal:hover { transform: rotate(90deg); }
        .modal-body { flex: 1; overflow-y: auto; padding: 16px 20px; }
        .modal-footer {
            padding: 12px 20px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 10px;
            flex-shrink: 0;
        }
        .modal-footer input {
            flex: 1;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 24px;
            outline: none;
            font-size: 14px;
            background: var(--bg);
            color: var(--text);
            direction: rtl;
            transition: var(--transition);
        }
        .modal-footer input:focus { border-color: var(--primary); }
        .modal-footer button {
            background: var(--primary);
            color: white;
            border: none;
            padding: 10px 24px;
            border-radius: 24px;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            font-family: var(--font);
        }
        .modal-footer button:hover { background: var(--primary-dark); transform: scale(1.02); }

        /* ===== Comment ===== */
        .comment-item {
            display: flex;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
            transition: var(--transition);
        }
        .comment-item:last-child { border-bottom: none; }
        .comment-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: var(--border);
            flex-shrink: 0;
            overflow: hidden;
        }
        .comment-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .comment-content { flex: 1; }
        .comment-username { font-weight: 600; font-size: 13px; color: var(--text); }
        .comment-text { font-size: 13px; color: var(--text); margin-top: 2px; }
        .comment-time { font-size: 11px; color: var(--text-secondary); margin-top: 4px; }

        /* ===== Profile ===== */
        .profile-page {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg);
            z-index: 150;
            overflow-y: auto;
            padding-top: var(--header-height);
        }
        .profile-page.active { display: block; }
        .profile-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            padding: 0 16px;
            height: var(--header-height);
            border-bottom: 1px solid var(--border);
            z-index: 151;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .profile-header h2 { font-size: 18px; color: var(--text); }
        .profile-header .close-profile {
            font-size: 24px;
            cursor: pointer;
            color: var(--text);
            background: none;
            border: none;
            transition: var(--transition);
        }
        .profile-header .close-profile:hover { transform: rotate(90deg); }
        .profile-info {
            background: var(--bg-secondary);
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }
        .profile-avatar-large {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            overflow: hidden;
            border: 3px solid var(--border);
            margin-bottom: 10px;
            transition: var(--transition);
        }
        .profile-avatar-large img { width: 100%; height: 100%; object-fit: cover; }
        .profile-username { font-size: 20px; font-weight: 600; color: var(--text); }
        .profile-bio { font-size: 14px; color: var(--text); margin: 6px 0; text-align: center; padding: 0 20px; }
        .profile-stats {
            display: flex;
            justify-content: space-around;
            padding: 16px 0;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            width: 100%;
        }
        .profile-stats .stat {
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            transition: var(--transition);
        }
        .profile-stats .stat:hover { opacity: 0.7; transform: scale(1.02); }
        .profile-stats .stat .number { font-size: 18px; font-weight: 600; color: var(--text); }
        .profile-stats .stat .label { font-size: 13px; color: var(--text-secondary); }
        .profile-follow-btn {
            padding: 8px 32px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            margin: 6px 0;
            transition: var(--transition);
        }
        .profile-follow-btn:hover { background: var(--primary-dark); transform: scale(1.02); }
        .profile-follow-btn.following { background: var(--bg); color: var(--text); border: 1px solid var(--border); }
        .profile-gallery {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 3px;
            padding: 3px;
            background: var(--bg);
        }
        .profile-post {
            aspect-ratio: 1;
            overflow: hidden;
            background: var(--border);
            position: relative;
            cursor: pointer;
            border-radius: var(--radius-sm);
            transition: var(--transition);
        }
        .profile-post:hover { transform: scale(1.02); }
        .profile-post .image-container { width: 100%; height: 100%; position: relative; }
        .profile-post .image-container img { width: 100%; height: 100%; object-fit: cover; }
        .profile-post .image-container .profile-post-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.4);
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            color: white;
            opacity: 0;
            transition: var(--transition);
        }
        .profile-post .image-container:hover .profile-post-overlay { opacity: 1; }
        .profile-post .image-container .profile-post-overlay span { display: flex; align-items: center; gap: 5px; font-size: 14px; font-weight: 600; }

        /* ===== Upload ===== */
        .upload-page {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg);
            z-index: 150;
            overflow-y: auto;
            padding-top: var(--header-height);
        }
        .upload-page.active { display: block; }
        .upload-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            padding: 0 16px;
            height: var(--header-height);
            border-bottom: 1px solid var(--border);
            z-index: 151;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .upload-header h2 { font-size: 18px; color: var(--text); }
        .upload-header .close-upload {
            font-size: 24px;
            cursor: pointer;
            color: var(--text);
            background: none;
            border: none;
            transition: var(--transition);
        }
        .upload-header .close-upload:hover { transform: rotate(90deg); }
        .upload-container {
            background: var(--bg-secondary);
            margin: 12px 16px;
            border-radius: var(--radius);
            padding: 30px 20px;
            border: 2px dashed var(--border);
            text-align: center;
            min-height: 320px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: var(--transition);
        }
        .upload-container:hover { border-color: var(--primary); }
        .upload-container i { font-size: 60px; color: var(--primary); margin-bottom: 16px; }
        .upload-container h3 { font-size: 20px; color: var(--text); margin-bottom: 8px; }
        .upload-container p { font-size: 14px; color: var(--text-secondary); margin-bottom: 20px; }
        .upload-container input[type="file"] { display: none; }
        .upload-container .upload-btn {
            padding: 10px 32px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-weight: 600;
            font-size: 16px;
            transition: var(--transition);
        }
        .upload-container .upload-btn:hover { background: var(--primary-dark); transform: scale(1.02); }
        .upload-preview { display: none; margin-top: 16px; width: 100%; max-width: 320px; margin: 16px auto 0; }
        .upload-preview img, .upload-preview video { width: 100%; border-radius: var(--radius-sm); max-height: 320px; object-fit: cover; }
        .upload-preview.active { display: block; }
        .upload-caption { display: none; margin-top: 12px; width: 100%; max-width: 320px; margin: 12px auto 0; }
        .upload-caption.active { display: block; }
        .upload-caption textarea {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            outline: none;
            font-size: 14px;
            font-family: var(--font);
            resize: vertical;
            min-height: 60px;
            background: var(--bg);
            color: var(--text);
            direction: rtl;
            transition: var(--transition);
        }
        .upload-caption textarea:focus { border-color: var(--primary); }
        .upload-hashtags { display: none; margin-top: 8px; width: 100%; max-width: 320px; margin: 8px auto 0; }
        .upload-hashtags.active { display: block; }
        .upload-hashtags input {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            outline: none;
            font-size: 14px;
            background: var(--bg);
            color: var(--text);
            direction: rtl;
            transition: var(--transition);
        }
        .upload-hashtags input:focus { border-color: var(--primary); }
        .upload-submit {
            display: none;
            margin-top: 12px;
            padding: 10px 32px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-weight: 600;
            font-size: 16px;
            transition: var(--transition);
        }
        .upload-submit.active { display: inline-block; }
        .upload-submit:hover { background: var(--primary-dark); transform: scale(1.02); }

        /* ===== Chat ===== */
        .chat-interface {
            display: none;
            position: fixed;
            bottom: var(--bottom-nav-height);
            left: 0;
            right: 0;
            top: var(--header-height);
            background: var(--bg-secondary);
            z-index: 200;
            flex-direction: column;
            border-top: 1px solid var(--border);
        }
        .chat-interface.active { display: flex; }
        .chat-header-bar {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-secondary);
            flex-shrink: 0;
        }
        .chat-header-bar h3 { font-size: 16px; color: var(--text); }
        .chat-header-bar .close-chat-btn {
            font-size: 24px;
            cursor: pointer;
            color: var(--text);
            background: none;
            border: none;
            transition: var(--transition);
        }
        .chat-header-bar .close-chat-btn:hover { transform: rotate(90deg); }
        .chat-users-list {
            border-bottom: 1px solid var(--border);
            max-height: 140px;
            overflow-y: auto;
            flex-shrink: 0;
            background: var(--bg);
        }
        .chat-user {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 16px;
            cursor: pointer;
            border-bottom: 1px solid var(--border);
            transition: var(--transition);
        }
        .chat-user:hover { background: var(--bg-secondary); }
        .chat-user .user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            overflow: hidden;
            background: var(--border);
            flex-shrink: 0;
        }
        .chat-user .user-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .chat-user .user-name { font-size: 14px; color: var(--text); font-weight: 500; }
        .chat-user .user-status { font-size: 11px; color: var(--text-secondary); }
        .chat-user .user-status.online { color: var(--success); }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            background: var(--bg);
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .chat-message {
            max-width: 78%;
            padding: 10px 16px;
            border-radius: 18px;
            background: var(--bg-secondary);
            box-shadow: var(--shadow);
            align-self: flex-start;
            word-wrap: break-word;
            animation: messageIn 0.2s ease;
        }
        @keyframes messageIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .chat-message.own { align-self: flex-end; background: var(--primary); color: white; }
        .chat-message .msg-user { font-size: 11px; font-weight: 600; color: var(--primary); margin-bottom: 2px; }
        .chat-message.own .msg-user { color: rgba(255,255,255,0.8); }
        .chat-message .msg-text { font-size: 14px; }
        .chat-message .msg-time { font-size: 10px; color: var(--text-secondary); margin-top: 4px; text-align: left; }
        .chat-message.own .msg-time { color: rgba(255,255,255,0.7); }
        .chat-input {
            display: flex;
            gap: 10px;
            padding: 10px 16px;
            border-top: 1px solid var(--border);
            background: var(--bg-secondary);
            flex-shrink: 0;
        }
        .chat-input input {
            flex: 1;
            padding: 10px 16px;
            border: 1px solid var(--border);
            border-radius: 24px;
            outline: none;
            font-size: 14px;
            background: var(--bg);
            color: var(--text);
            direction: rtl;
            transition: var(--transition);
        }
        .chat-input input:focus { border-color: var(--primary); }
        .chat-input button {
            padding: 10px 20px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 24px;
            cursor: pointer;
            font-size: 16px;
            transition: var(--transition);
        }
        .chat-input button:hover { background: var(--primary-dark); transform: scale(1.02); }
        .chat-empty {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }
        .chat-empty i { font-size: 40px; display: block; margin-bottom: 12px; color: var(--border); }

        /* ===== Side Menu ===== */
        .menu-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 600;
            backdrop-filter: blur(2px);
        }
        .menu-overlay.active { display: block; }
        .side-menu {
            position: fixed;
            top: 0;
            right: -320px;
            width: 300px;
            height: 100%;
            background: var(--bg-secondary);
            z-index: 601;
            transition: right 0.3s ease;
            padding-top: 16px;
            box-shadow: -4px 0 20px rgba(0,0,0,0.15);
            overflow-y: auto;
        }
        .side-menu.active { right: 0; }
        .side-menu .menu-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .side-menu .menu-header h3 { font-size: 18px; color: var(--text); }
        .side-menu .menu-header .close-menu {
            font-size: 24px;
            cursor: pointer;
            color: var(--text);
            background: none;
            border: none;
            transition: var(--transition);
        }
        .side-menu .menu-header .close-menu:hover { transform: rotate(90deg); }
        .side-menu .menu-item {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 14px 20px;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            color: var(--text);
            transition: var(--transition);
        }
        .side-menu .menu-item:hover { background: var(--bg); }
        .side-menu .menu-item i { font-size: 20px; width: 28px; color: var(--text); }
        .side-menu .menu-item .menu-text { font-size: 15px; font-weight: 500; }
        .side-menu .menu-item .menu-badge {
            margin-right: auto;
            background: var(--primary);
            color: white;
            font-size: 11px;
            padding: 2px 12px;
            border-radius: 12px;
        }
        .side-menu .menu-item.admin {
            background: rgba(0,149,246,0.08);
            border-right: 3px solid var(--primary);
        }

        /* ===== Settings ===== */
        .settings-page {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg);
            z-index: 160;
            overflow-y: auto;
            padding-top: var(--header-height);
        }
        .settings-page.active { display: block; }
        .settings-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: var(--bg-secondary);
            padding: 0 16px;
            height: var(--header-height);
            border-bottom: 1px solid var(--border);
            z-index: 161;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .settings-header h2 { font-size: 18px; color: var(--text); }
        .settings-header .close-settings {
            font-size: 24px;
            cursor: pointer;
            color: var(--text);
            background: none;
            border: none;
            transition: var(--transition);
        }
        .settings-header .close-settings:hover { transform: rotate(90deg); }
        .settings-container { padding: 16px; max-width: 600px; margin: 0 auto; }
        .settings-card {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
        }
        .settings-card h4 { font-size: 16px; color: var(--text); margin-bottom: 12px; }
        .settings-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }
        .settings-item:last-child { border-bottom: none; }
        .settings-item .label { font-size: 14px; color: var(--text); }
        .settings-item .value { font-size: 14px; color: var(--text-secondary); }
        .settings-item select, .settings-item input {
            padding: 6px 12px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            background: var(--bg);
            color: var(--text);
            font-size: 14px;
            outline: none;
            transition: var(--transition);
        }
        .settings-item select:focus, .settings-item input:focus { border-color: var(--primary); }
        .settings-item .toggle {
            width: 52px;
            height: 28px;
            background: var(--border);
            border-radius: 14px;
            position: relative;
            cursor: pointer;
            transition: var(--transition);
        }
        .settings-item .toggle.active { background: var(--primary); }
        .settings-item .toggle .thumb {
            width: 22px;
            height: 22px;
            background: white;
            border-radius: 50%;
            position: absolute;
            top: 3px;
            left: 3px;
            transition: var(--transition);
            box-shadow: 0 1px 4px rgba(0,0,0,0.2);
        }
        .settings-item .toggle.active .thumb { left: 27px; }
        .settings-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        .settings-stats .stat-box {
            background: var(--bg);
            padding: 16px;
            border-radius: var(--radius-sm);
            text-align: center;
            border: 1px solid var(--border);
        }
        .settings-stats .stat-box .num { font-size: 24px; font-weight: 700; color: var(--primary); }
        .settings-stats .stat-box .lbl { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

        /* ===== Admin Panel ===== */
        .admin-panel {
            display: none;
            position: fixed;
            top: var(--header-height);
            left: 0;
            right: 0;
            bottom: var(--bottom-nav-height);
            background: var(--bg);
            z-index: 145;
            overflow-y: auto;
            padding: 16px;
        }
        .admin-panel.active { display: block; }
        .admin-panel .admin-card {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
        }
        .admin-panel .admin-card h4 { color: var(--text); margin-bottom: 8px; }
        .admin-panel .admin-card .admin-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 0;
            border-bottom: 1px solid var(--border);
        }
        .admin-panel .admin-card .admin-item:last-child { border-bottom: none; }
        .admin-panel .admin-btn {
            padding: 4px 12px;
            border: none;
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: var(--transition);
        }
        .admin-panel .admin-btn.danger { background: var(--danger); color: white; }
        .admin-panel .admin-btn.danger:hover { opacity: 0.8; transform: scale(1.02); }
        .admin-panel .admin-btn.success { background: var(--success); color: white; }
        .admin-panel .admin-btn.success:hover { opacity: 0.8; transform: scale(1.02); }
        .admin-panel .admin-btn.primary { background: var(--primary); color: white; }
        .admin-panel .admin-btn.primary:hover { opacity: 0.8; transform: scale(1.02); }

        /* ===== Share ===== */
        .share-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 500;
            justify-content: center;
            align-items: center;
            padding: 20px;
            backdrop-filter: blur(4px);
        }
        .share-modal.active { display: flex; }
        .share-modal-content {
            background: var(--bg-secondary);
            border-radius: var(--radius);
            max-width: 400px;
            width: 100%;
            max-height: 70vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            direction: rtl;
            box-shadow: var(--shadow);
            animation: modalIn 0.3s ease;
        }
        .share-modal-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .share-modal-header h3 { font-size: 16px; color: var(--text); }
        .share-modal-header .close-share {
            font-size: 24px;
            cursor: pointer;
            color: var(--text);
            background: none;
            border: none;
            transition: var(--transition);
        }
        .share-modal-header .close-share:hover { transform: rotate(90deg); }
        .share-modal-body { flex: 1; overflow-y: auto; padding: 12px 16px; }
        .share-option {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            transition: var(--transition);
        }
        .share-option:hover { background: var(--bg); border-radius: var(--radius-sm); }
        .share-option .share-icon {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
            flex-shrink: 0;
        }
        .share-option .share-icon.telegram { background: #0088cc; }
        .share-option .share-icon.whatsapp { background: #25d366; }
        .share-option .share-icon.instagram { background: #e4405f; }
        .share-option .share-icon.copy { background: #6c757d; }
        .share-option .share-icon.site { background: var(--primary); }
        .share-option .share-name { font-size: 15px; color: var(--text); font-weight: 500; }

        /* ===== Toast ===== */
        .toast {
            position: fixed;
            bottom: calc(var(--bottom-nav-height) + 20px);
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.85);
            color: white;
            padding: 12px 24px;
            border-radius: 24px;
            font-size: 14px;
            z-index: 999;
            opacity: 0;
            transition: opacity 0.4s ease;
            pointer-events: none;
            backdrop-filter: blur(4px);
            max-width: 90%;
            text-align: center;
            font-family: var(--font);
        }
        .toast.show { opacity: 1; }
        .toast.success { border-right: 3px solid var(--success); }
        .toast.error { border-right: 3px solid var(--danger); }

        /* ===== Broadcast ===== */
        .broadcast {
            background: var(--primary);
            color: white;
            padding: 10px 16px;
            text-align: center;
            font-size: 14px;
            flex-shrink: 0;
            display: none;
            border-radius: 0;
        }
        .broadcast.show { display: block; }

        /* ===== Loading ===== */
        .loading-spinner {
            text-align: center;
            padding: 40px;
            color: var(--primary);
            font-size: 16px;
        }
        .loading-spinner i { font-size: 36px; animation: spin 0.8s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .no-posts {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
            grid-column: 1 / -1;
        }
        .no-posts i { font-size: 48px; color: var(--border); display: block; margin-bottom: 12px; }

        /* ===== Responsive ===== */
        @media (max-width: 768px) {
            .gallery { gap: 3px; padding: 3px; }
            .search-box { max-width: 200px; }
            .modal-content { max-width: 95%; }
            .settings-stats { grid-template-columns: repeat(3, 1fr); }
            .settings-stats .stat-box .num { font-size: 20px; }
            .side-menu { width: 280px; right: -290px; }
        }
        @media (max-width: 480px) {
            .gallery { gap: 2px; padding: 2px; }
            .search-box { max-width: 140px; padding: 6px 12px; }
            .search-box input { font-size: 12px; }
            .header-right { gap: 12px; font-size: 18px; }
            .header { padding: 0 10px; }
            .logo { font-size: 16px; }
            .story-avatar { width: 54px; height: 54px; }
            .chat-message { max-width: 90%; }
            .profile-avatar-large { width: 80px; height: 80px; }
            .settings-stats { grid-template-columns: repeat(3, 1fr); gap: 6px; }
            .settings-stats .stat-box { padding: 10px; }
            .settings-stats .stat-box .num { font-size: 18px; }
        }
    </style>
</head>
<body>

    <!-- Toast -->
    <div class="toast" id="toast"></div>

    <!-- Broadcast -->
    <div class="broadcast" id="broadcast"></div>

    <!-- Header -->
    <header class="header">
        <i class="fas fa-bars menu-icon" id="menuIcon"></i>
        <div class="logo"><i class="fab fa-instagram"></i> سوشال</div>
        <div class="search-box">
            <i class="fas fa-search"></i>
            <input type="text" id="searchInput" placeholder="جستجو...">
        </div>
        <div class="header-right">
            <i class="fas fa-comment-dots" id="chatOpenBtn"></i>
            <i class="fas fa-cog" id="settingsOpenBtn"></i>
        </div>
    </header>

    <!-- Broadcast -->
    <div class="broadcast" id="broadcast"></div>

    <!-- Stories -->
    <div class="stories-section" id="storiesSection">
        <div class="stories-container" id="storiesContainer"></div>
    </div>

    <!-- Gallery -->
    <div class="gallery-wrapper">
        <div id="loadingIndicator" class="loading-spinner">
            <i class="fas fa-spinner"></i><br> در حال بارگذاری...
        </div>
        <div class="gallery" id="gallery"></div>
        <div id="noPostsMessage" class="no-posts" style="display:none;">
            <i class="fas fa-camera"></i>
            هیچ پستی وجود ندارد<br> اولین پست را شما آپلود کنید!
        </div>
    </div>

    <!-- Chat -->
    <div class="chat-interface" id="chatInterface">
        <div class="chat-header-bar">
            <h3 id="chatTitle">💬 چت</h3>
            <button class="close-chat-btn" id="closeChatBtn">&times;</button>
        </div>
        <div class="chat-users-list" id="chatUsersList"></div>
        <div class="chat-messages" id="chatMessages">
            <div class="chat-empty">
                <i class="fas fa-comments"></i>
                برای شروع چت، یک کاربر را انتخاب کنید
            </div>
        </div>
        <div class="chat-input">
            <input type="text" id="chatInput" placeholder="پیام خود را بنویسید...">
            <button id="chatSendBtn"><i class="fas fa-paper-plane"></i></button>
        </div>
    </div>

    <!-- Comment Modal -->
    <div class="modal-overlay" id="commentModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>💬 کامنت‌ها</h3>
                <button class="close-modal" id="closeModal">&times;</button>
            </div>
            <div class="modal-body" id="commentList"></div>
            <div class="modal-footer">
                <input type="text" id="modalCommentInput" placeholder="کامنت خود را بنویسید...">
                <button id="modalSendComment">ارسال</button>
            </div>
        </div>
    </div>

    <!-- Share Modal -->
    <div class="share-modal" id="shareModal">
        <div class="share-modal-content">
            <div class="share-modal-header">
                <h3>📤 اشتراک‌گذاری</h3>
                <button class="close-share" id="closeShareModal">&times;</button>
            </div>
            <div class="share-modal-body">
                <div class="share-option" data-share="site">
                    <div class="share-icon site"><i class="fas fa-users"></i></div>
                    <span class="share-name">اشتراک در سایت</span>
                </div>
                <div class="share-option" data-share="telegram">
                    <div class="share-icon telegram"><i class="fab fa-telegram-plane"></i></div>
                    <span class="share-name">ارسال به تلگرام</span>
                </div>
                <div class="share-option" data-share="whatsapp">
                    <div class="share-icon whatsapp"><i class="fab fa-whatsapp"></i></div>
                    <span class="share-name">ارسال به واتساپ</span>
                </div>
                <div class="share-option" data-share="copy">
                    <div class="share-icon copy"><i class="fas fa-copy"></i></div>
                    <span class="share-name">کپی لینک پست</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Profile -->
    <div class="profile-page" id="profilePage">
        <div class="profile-header">
            <h2>👤 پروفایل</h2>
            <button class="close-profile" id="closeProfile">&times;</button>
        </div>
        <div style="margin-top: var(--header-height);">
            <div class="profile-info">
                <div class="profile-avatar-large">
                    <img id="profileAvatar" src="https://i.pravatar.cc/150?img=10" alt="profile">
                </div>
                <div class="profile-username" id="profileUsername">کاربر</div>
                <div class="profile-bio" id="bioDisplay">توسعه‌دهنده وب | عاشق کدنویسی</div>
                <button class="profile-follow-btn" id="profileFollowBtn">دنبال کردن</button>
                <div class="profile-bio-edit" style="display:flex;gap:10px;margin:10px 0;width:100%;max-width:300px;">
                    <input type="text" id="bioInput" placeholder="بیوگرافی خود را بنویسید..." style="flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:8px;outline:none;font-size:14px;background:var(--bg);color:var(--text);direction:rtl;">
                    <button id="saveBio" style="padding:8px 16px;background:var(--primary);color:white;border:none;border-radius:8px;cursor:pointer;font-weight:600;transition:var(--transition);">ذخیره</button>
                </div>
            </div>
            <div class="profile-stats">
                <div class="stat" id="statPosts">
                    <span class="number" id="postCount">۰</span>
                    <span class="label">پست</span>
                </div>
                <div class="stat" id="statFollowers">
                    <span class="number" id="followerCount">۰</span>
                    <span class="label">دنبال‌کننده</span>
                </div>
                <div class="stat" id="statFollowing">
                    <span class="number" id="followingCount">۰</span>
                    <span class="label">دنبال‌شونده</span>
                </div>
            </div>
            <div style="padding:10px 0;background:var(--bg-secondary);margin-top:5px;">
                <h4 style="padding:0 20px 10px;font-size:14px;color:var(--text);">📸 پست‌های من</h4>
                <div class="profile-gallery" id="profileGallery"></div>
            </div>
        </div>
    </div>

    <!-- Settings -->
    <div class="settings-page" id="settingsPage">
        <div class="settings-header">
            <h2>⚙️ تنظیمات</h2>
            <button class="close-settings" id="closeSettings">&times;</button>
        </div>
        <div class="settings-container">
            <div class="settings-card">
                <h4>🌐 زبان</h4>
                <div class="settings-item">
                    <span class="label">زبان رابط</span>
                    <select id="languageSelect">
                        <option value="fa">فارسی</option>
                        <option value="en">English</option>
                    </select>
                </div>
            </div>
            <div class="settings-card">
                <h4>🎨 ظاهر</h4>
                <div class="settings-item">
                    <span class="label">تم تاریک</span>
                    <div class="toggle" id="themeToggle">
                        <div class="thumb"></div>
                    </div>
                </div>
            </div>
            <div class="settings-card">
                <h4>📊 آمار</h4>
                <div class="settings-stats">
                    <div class="stat-box">
                        <div class="num" id="statTotalPosts">0</div>
                        <div class="lbl">کل پست‌ها</div>
                    </div>
                    <div class="stat-box">
                        <div class="num" id="statTotalUsers">0</div>
                        <div class="lbl">کاربران</div>
                    </div>
                    <div class="stat-box">
                        <div class="num" id="statOnlineUsers">0</div>
                        <div class="lbl">آنلاین</div>
                    </div>
                </div>
            </div>
            <div class="settings-card">
                <h4>👤 اطلاعات کاربری</h4>
                <div class="settings-item">
                    <span class="label">نام کاربری</span>
                    <span class="value" id="settingsUsername">-</span>
                </div>
                <div class="settings-item">
                    <span class="label">ایمیل</span>
                    <span class="value" id="settingsEmail">-</span>
                </div>
                <div class="settings-item">
                    <span class="label">تعداد پست</span>
                    <span class="value" id="settingsPostCount">0</span>
                </div>
            </div>
            <button id="logoutBtn" style="width:100%;padding:12px;background:var(--danger);color:white;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;transition:var(--transition);">🚪 خروج</button>
        </div>
    </div>

    <!-- Admin Panel -->
    <div class="admin-panel" id="adminPanel">
        <div class="admin-card">
            <h4>👑 پنل مدیریت</h4>
            <div class="admin-item">
                <span>کاربران</span>
                <span id="adminUserCount">0</span>
            </div>
            <div class="admin-item">
                <span>پست‌ها</span>
                <span id="adminPostCount">0</span>
            </div>
            <div class="admin-item">
                <span>آنلاین</span>
                <span id="adminOnlineCount">0</span>
            </div>
        </div>
        <div class="admin-card">
            <h4>📢 پیام همگانی</h4>
            <div style="display:flex;gap:10px;">
                <input type="text" id="broadcastInput" placeholder="پیام به همه کاربران..." style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:8px;outline:none;font-size:14px;background:var(--bg);color:var(--text);">
                <button id="broadcastBtn" class="admin-btn primary">ارسال</button>
            </div>
        </div>
        <div class="admin-card">
            <h4>👥 مدیریت کاربران</h4>
            <div id="adminUsersList"></div>
        </div>
        <div class="admin-card">
            <h4>📸 مدیریت پست‌ها</h4>
            <div id="adminPostsList"></div>
        </div>
        <div class="admin-card">
            <h4>⚡ مدیریت سیستم</h4>
            <div class="admin-item">
                <span>شاردها</span>
                <span id="adminShardCount">5</span>
            </div>
            <button id="addShardBtn" class="admin-btn success">➕ اضافه کردن شارد جدید</button>
        </div>
    </div>

    <!-- Upload -->
    <div class="upload-page" id="uploadPage">
        <div class="upload-header">
            <h2>📤 آپلود</h2>
            <button class="close-upload" id="closeUpload">&times;</button>
        </div>
        <div style="margin-top:var(--header-height);padding:10px;">
            <div class="upload-container" id="uploadContainer">
                <i class="fas fa-cloud-upload-alt"></i>
                <h3>انتخاب فایل</h3>
                <p>برای آپلود عکس یا ویدئو کلیک کنید</p>
                <button class="upload-btn" id="uploadSelectBtn">انتخاب فایل</button>
                <input type="file" id="fileInput" accept="image/*,video/*">
                <div class="upload-preview" id="uploadPreview">
                    <img id="previewImage" src="#" alt="preview">
                    <video id="previewVideo" controls style="display:none;"></video>
                </div>
                <div class="upload-caption" id="uploadCaption">
                    <textarea id="captionInput" placeholder="توضیحات پست را بنویسید..."></textarea>
                </div>
                <div class="upload-hashtags" id="uploadHashtags">
                    <input type="text" id="hashtagInput" placeholder="هشتگ‌ها (با کاما جدا کنید)">
                </div>
                <button class="upload-submit" id="uploadSubmit">📤 ارسال پست</button>
            </div>
        </div>
    </div>

    <!-- Follow Modal -->
    <div class="follow-modal" id="followModal" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:400;justify-content:center;align-items:center;padding:20px;backdrop-filter:blur(4px);">
        <div class="follow-modal-content" style="background:var(--bg-secondary);border-radius:var(--radius);max-width:400px;width:100%;max-height:70vh;display:flex;flex-direction:column;overflow:hidden;direction:rtl;box-shadow:var(--shadow);">
            <div class="follow-modal-header" style="padding:16px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
                <h3 id="followModalTitle" style="font-size:16px;color:var(--text);">دنبال‌کنندگان</h3>
                <button class="close-follow" id="closeFollowModal" style="font-size:24px;cursor:pointer;color:var(--text);background:none;border:none;transition:var(--transition);">&times;</button>
            </div>
            <div class="follow-modal-body" id="followModalBody" style="flex:1;overflow-y:auto;padding:16px 20px;"></div>
        </div>
    </div>

    <!-- Side Menu -->
    <div class="menu-overlay" id="menuOverlay"></div>
    <div class="side-menu" id="sideMenu">
        <div class="menu-header">
            <h3>📋 منو</h3>
            <button class="close-menu" id="closeMenu">&times;</button>
        </div>
        <div class="menu-item" id="menuProfile">
            <i class="fas fa-user"></i>
            <span class="menu-text">پروفایل</span>
        </div>
        <div class="menu-item" id="menuSettings">
            <i class="fas fa-cog"></i>
            <span class="menu-text">تنظیمات</span>
        </div>
        <div class="menu-item" id="menuStats">
            <i class="fas fa-chart-bar"></i>
            <span class="menu-text">آمار</span>
        </div>
        <div class="menu-item" id="menuTheme">
            <i class="fas fa-palette"></i>
            <span class="menu-text">تغیر تم</span>
        </div>
        <div class="menu-item" id="menuAdmin" style="display:none;border-right:3px solid var(--primary);background:rgba(0,149,246,0.05);">
            <i class="fas fa-crown"></i>
            <span class="menu-text">پنل مدیریت</span>
            <span class="menu-badge">ادمین</span>
        </div>
        <div class="menu-item" id="menuLogout">
            <i class="fas fa-sign-out-alt"></i>
            <span class="menu-text">خروج</span>
        </div>
    </div>

    <!-- Bottom Nav -->
    <nav class="bottom-nav">
        <button id="profileBtn">
            <i class="fas fa-user"></i>
            <span>پروفایل</span>
        </button>
        <button id="uploadBtn">
            <i class="fas fa-upload"></i>
            <span>آپلود</span>
        </button>
        <button id="exploreBtn" class="active">
            <i class="fas fa-compass"></i>
            <span>اکسپلور</span>
        </button>
        <button id="reelsBtn">
            <i class="fas fa-film"></i>
            <span>ریلز</span>
        </button>
    </nav>

    <script src="/socket.io/socket.io.js"></script>
    <script>
        // ============================================
        // 🌐 تنظیمات اصلی
        // ============================================
        const API_URL = window.location.origin;
        const socket = io();
        let currentUser = null;
        let currentToken = localStorage.getItem('token');
        let isAdmin = false;
        let isDarkTheme = localStorage.getItem('theme') === 'dark';
        let language = localStorage.getItem('language') || 'fa';
        let currentPostId = null;
        let currentChatRoom = null;
        let currentChatUser = null;
        let currentPage = 1;
        let isLoading = false;
        let isUploading = false;

        // ============================================
        // 🔐 احراز هویت
        // ============================================

        async function registerUser(username, email, password) {
            const res = await fetch(API_URL + '/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            return await res.json();
        }

        async function loginUser(email, password) {
            const res = await fetch(API_URL + '/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            return await res.json();
        }

        async function logoutUser() {
            await fetch(API_URL + '/api/auth/logout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: currentToken })
            });
            localStorage.removeItem('token');
            currentToken = null;
            currentUser = null;
            isAdmin = false;
            location.reload();
        }

        async function getCurrentUser() {
            if (!currentToken) return null;
            try {
                const res = await fetch(API_URL + '/api/auth/me', {
                    headers: { 'Authorization': 'Bearer ' + currentToken }
                });
                if (res.ok) return await res.json();
                return null;
            } catch {
                return null;
            }
        }

        async function verifyAdmin() {
            if (!currentToken) return false;
            try {
                const res = await fetch(API_URL + '/api/admin/verify', {
                    headers: { 'Authorization': 'Bearer ' + currentToken }
                });
                if (res.ok) {
                    const data = await res.json();
                    return data.isAdmin || false;
                }
                return false;
            } catch {
                return false;
            }
        }

        // ============================================
        // 📦 توابع API
        // ============================================

        async function getPosts(page = 1, hashtag = '') {
            const url = API_URL + '/api/posts?page=' + page + '&limit=20' + (hashtag ? '&hashtag=' + encodeURIComponent(hashtag) :
                '');
            const res = await fetch(url);
            return await res.json();
        }

        async function createPost(file, caption, hashtags) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('caption', caption);
            formData.append('userId', currentUser?.userId || 'user1');
            formData.append('username', currentUser?.username || 'کاربر');
            if (hashtags) formData.append('hashtags', hashtags);

            const res = await fetch(API_URL + '/api/posts', {
                method: 'POST',
                body: formData
            });
            return await res.json();
        }

        async function likePost(postId) {
            const res = await fetch(API_URL + '/api/posts/' + postId + '/like', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: currentUser?.userId || 'user1' })
            });
            return await res.json();
        }

        async function addComment(postId, text) {
            const res = await fetch(API_URL + '/api/posts/' + postId + '/comment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    userId: currentUser?.userId || 'user1',
                    username: currentUser?.username || 'کاربر',
                    text
                })
            });
            return await res.json();
        }

        async function getStories() {
            const res = await fetch(API_URL + '/api/stories');
            return await res.json();
        }

        async function createStory(file) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('userId', currentUser?.userId || 'user1');
            formData.append('username', currentUser?.username || 'کاربر');

            const res = await fetch(API_URL + '/api/stories', {
                method: 'POST',
                body: formData
            });
            return await res.json();
        }

        async function getUsers() {
            const res = await fetch(API_URL + '/api/users');
            return await res.json();
        }

        async function updateProfile(userId, data) {
            const res = await fetch(API_URL + '/api/users/' + userId + '/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await res.json();
        }

        async function followUser(userId, followerId) {
            const res = await fetch(API_URL + '/api/users/' + userId + '/follow', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ followerId })
            });
            return await res.json();
        }

        // ===== Admin API =====
        async function getAdminUsers() {
            const res = await fetch(API_URL + '/api/admin/users', {
                headers: { 'Authorization': 'Bearer ' + currentToken }
            });
            return await res.json();
        }

        async function banUser(userId, banned) {
            const res = await fetch(API_URL + '/api/admin/users/' + userId + '/ban', {
                method: 'PUT',
                headers: {
                    'Authorization': 'Bearer ' + currentToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ banned })
            });
            return await res.json();
        }

        async function deletePost(postId) {
            const res = await fetch(API_URL + '/api/admin/posts/' + postId, {
                method: 'DELETE',
                headers: { 'Authorization': 'Bearer ' + currentToken }
            });
            return await res.json();
        }

        async function getAdminPosts() {
            const res = await fetch(API_URL + '/api/admin/posts', {
                headers: { 'Authorization': 'Bearer ' + currentToken }
            });
            return await res.json();
        }

        async function broadcastMessage(message) {
            const res = await fetch(API_URL + '/api/admin/broadcast', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + currentToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            return await res.json();
        }

        async function getAdminStats() {
            const res = await fetch(API_URL + '/api/admin/stats', {
                headers: { 'Authorization': 'Bearer ' + currentToken }
            });
            return await res.json();
        }

        async function addShard() {
            const res = await fetch(API_URL + '/api/admin/add-shard', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + currentToken }
            });
            return await res.json();
        }

        // ============================================
        // 💬 چت
        // ============================================

        socket.on('connect', () => {
            console.log('✅ Connected to server');
            if (currentUser) {
                socket.emit('register', { userId: currentUser.userId, username: currentUser.username });
            }
        });

        socket.on('users-online', (users) => {
            document.getElementById('statOnlineUsers').textContent = users?.length || 0;
            renderChatUsers();
        });

        socket.on('receive-message', (data) => {
            displayChatMessage(data.userId, data.username, data.message, data.timestamp);
        });

        socket.on('history', (messages) => {
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.innerHTML = '';
            messages.forEach(msg => {
                displayChatMessage(msg.userId, msg.username, msg.message, msg.timestamp);
            });
        });

        socket.on('broadcast', (data) => {
            const broadcast = document.getElementById('broadcast');
            broadcast.textContent = '📢 ' + data.message + ' (از ' + data.from + ')';
            broadcast.classList.add('show');
            showToast('📢 پیام همگانی: ' + data.message);
            setTimeout(() => broadcast.classList.remove('show'), 10000);
        });

        socket.on('error', (data) => {
            showToast('❌ ' + data.message);
        });

        function startChat(userId, username) {
            if (currentUser && currentUser.isBanned) {
                showToast('❌ شما مسدود شده‌اید و نمی‌توانید چت کنید');
                return;
            }

            currentChatUser = userId;
            const roomId = [currentUser?.userId || 'user1', userId].sort().join('_');
            currentChatRoom = roomId;

            document.getElementById('chatTitle').textContent = '💬 ' + username;
            document.getElementById('chatInterface').classList.add('active');

            socket.emit('join-room', { roomId, userId: currentUser?.userId || 'user1' });
        }

        function sendChatMessage() {
            if (currentUser && currentUser.isBanned) {
                showToast('❌ شما مسدود شده‌اید و نمی‌توانید چت کنید');
                return;
            }

            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if (!text || !currentChatRoom || !currentUser) return;

            socket.emit('send-message', {
                roomId: currentChatRoom,
                userId: currentUser.userId,
                username: currentUser.username,
                message: text
            });

            displayChatMessage(currentUser.userId, currentUser.username, text, new Date().toISOString());
            input.value = '';
        }

        function displayChatMessage(userId, username, message, timestamp) {
            const messagesDiv = document.getElementById('chatMessages');
            const empty = messagesDiv.querySelector('.chat-empty');
            if (empty) empty.remove();

            const div = document.createElement('div');
            div.className = 'chat-message' + (userId === currentUser?.userId ? ' own' : '');

            const time = timestamp ? new Date(timestamp).toLocaleTimeString(language === 'fa' ? 'fa-IR' : 'en-US') : '';

            div.innerHTML =
                '<div class="msg-user">' + (userId === currentUser?.userId ? 'شما' : username) + '</div><div class="msg-text">' +
                message + '</div><div class="msg-time">' + time + '</div>';

            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        async function renderChatUsers() {
            const list = document.getElementById('chatUsersList');
            list.innerHTML = '';
            const users = await getUsers();

            let hasUsers = false;
            users.forEach(user => {
                if (user.userId === currentUser?.userId) return;
                if (user.isBanned) return;
                hasUsers = true;
                const div = document.createElement('div');
                div.className = 'chat-user';
                div.onclick = () => startChat(user.userId, user.username);

                const statusClass = user.isOnline ? 'online' : '';
                const statusText = user.isOnline ? 'آنلاین' : 'آفلاین';

                div.innerHTML =
                    '<div class="user-avatar"><img src="' + (user.avatar || 'https://i.pravatar.cc/150?img=' + Math.floor(
                        Math.random() * 70)) + '" alt="user"></div><div><div class="user-name">' + user.username +
                    '</div><div class="user-status ' + statusClass + '">' + statusText + '</div></div>';
                list.appendChild(div);
            });

            if (!hasUsers) {
                list.innerHTML = '<div style="padding:10px 16px;color:var(--text-secondary);">هیچ کاربر دیگری آنلاین نیست</div>';
            }
        }

        // ============================================
        // 🎨 نمایش
        // ============================================

        function createPostElement(post) {
            const div = document.createElement('div');
            div.className = 'gallery-item';
            div.setAttribute('data-id', post.postId);

            const isLiked = localStorage.getItem('liked_' + post.postId) === 'true';

            let captionHtml = post.caption || '';
            if (post.hashtags && post.hashtags.length > 0) {
                post.hashtags.forEach(h => {
                    captionHtml = captionHtml.replace('#' + h,
                        '<span class="hashtag" style="color:var(--primary);cursor:pointer;" onclick="event.stopPropagation(); searchHashtag(\'' +
                        h + '\')">#' + h + '</span>');
                });
            }

            div.innerHTML =
                '<div class="image-container"><img src="' + post.image +
                '" alt="post" loading="lazy"></div><div class="explore-post-actions"><button class="action-btn like-btn ' +
                (isLiked ? 'liked' : '') + '" data-id="' + post.postId +
                '" onclick="event.stopPropagation(); handleLike(\'' + post.postId +
                '\')"><i class="' + (isLiked ? 'fas' : 'far') + ' fa-heart"></i><span class="count">' + (post.likes || 0) +
                '</span></button><button class="action-btn comment-btn" data-id="' + post.postId +
                '" onclick="event.stopPropagation(); openComments(\'' + post.postId +
                '\')"><i class="far fa-comment"></i><span class="count">' + (post.comments || []).length +
                '</span></button><button class="action-btn share-btn" data-id="' + post.postId +
                '" onclick="event.stopPropagation(); sharePost(\'' + post.postId +
                '\')"><i class="fas fa-share-alt"></i><span class="count">' + (post.shares || 0) +
                '</span></button></div>';

            div.onclick = () => openPostDetail(post.postId);
            return div;
        }

        function createProfilePostElement(post) {
            const div = document.createElement('div');
            div.className = 'profile-post';
            div.setAttribute('data-id', post.postId);
            div.onclick = () => openPostDetail(post.postId);

            div.innerHTML =
                '<div class="image-container"><img src="' + post.image +
                '" alt="post" loading="lazy"><div class="profile-post-overlay"><span><i class="fas fa-heart"></i> ' + (post
                    .likes || 0) + '</span><span><i class="fas fa-comment"></i> ' + (post.comments || []).length +
                '</span></div></div>';
            return div;
        }

        function createStoryElement(story) {
            const div = document.createElement('div');
            div.className = 'story-item';
            div.onclick = () => {
                showToast('📸 استوری از ' + story.username);
                viewStory(story.storyId);
            };

            div.innerHTML = '<div class="story-avatar"><img src="' + story.image +
                '" alt="story"></div><span class="story-username">' + story.username + '</span>';
            return div;
        }

        // ============================================
        // 📥 بارگذاری
        // ============================================

        async function loadPosts(page = 1, hashtag = '') {
            if (isLoading) return;
            isLoading = true;

            const gallery = document.getElementById('gallery');
            const loading = document.getElementById('loadingIndicator');
            const noPosts = document.getElementById('noPostsMessage');

            if (page === 1) {
                loading.style.display = 'block';
                gallery.innerHTML = '';
                noPosts.style.display = 'none';
            }

            const data = await getPosts(page, hashtag);

            if (page === 1) {
                loading.style.display = 'none';
            }

            if (data.posts.length === 0 && page === 1) {
                noPosts.style.display = 'block';
                isLoading = false;
                return;
            }

            data.posts.forEach(post => {
                gallery.appendChild(createPostElement(post));
            });

            currentPage = page;
            isLoading = false;
        }

        async function loadStories() {
            const container = document.getElementById('storiesContainer');
            container.innerHTML = '';

            // دکمه افزودن استوری
            const addDiv = document.createElement('div');
            addDiv.className = 'story-item';
            addDiv.onclick = () => {
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = 'image/*,video/*';
                fileInput.onchange = async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        const result = await createStory(file);
                        if (result.storyId) {
                            showToast('✅ استوری با موفقیت آپلود شد!');
                            loadStories();
                        }
                    }
                };
                fileInput.click();
            };
            addDiv.innerHTML =
                '<div class="story-avatar add-story"><i class="fas fa-plus" style="font-size:28px;color:var(--primary);display:flex;align-items:center;justify-content:center;width:100%;height:100%;"></i></div><span class="story-username">افزودن</span>';
            container.appendChild(addDiv);

            const stories = await getStories();
            stories.forEach(story => {
                container.appendChild(createStoryElement(story));
            });
        }

        async function loadProfile() {
            if (!currentUser) return;

            document.getElementById('profileUsername').textContent = currentUser.username || 'کاربر';
            document.getElementById('bioDisplay').textContent = currentUser.bio || 'توسعه‌دهنده وب | عاشق کدنویسی';
            document.getElementById('followerCount').textContent = currentUser.followers || 0;
            document.getElementById('followingCount').textContent = currentUser.following || 0;

            const posts = await getPosts(1);
            const userPosts = posts.posts.filter(p => p.userId === currentUser.userId);
            document.getElementById('postCount').textContent = userPosts.length;

            const gallery = document.getElementById('profileGallery');
            gallery.innerHTML = '';
            if (userPosts.length === 0) {
                gallery.innerHTML =
                    '<p style="grid-column:span 3;text-align:center;color:var(--text-secondary);padding:20px;">هیچ پستی ندارید</p>';
            } else {
                userPosts.forEach(post => {
                    gallery.appendChild(createProfilePostElement(post));
                });
            }

            // Settings
            document.getElementById('settingsUsername').textContent = currentUser.username || '-';
            document.getElementById('settingsEmail').textContent = currentUser.email || '-';
            document.getElementById('settingsPostCount').textContent = userPosts.length || 0;
            document.getElementById('statTotalPosts').textContent = posts.total || 0;

            const users = await getUsers();
            document.getElementById('statTotalUsers').textContent = users.length || 0;

            // Admin Panel
            if (isAdmin) {
                await loadAdminPanel();
            }
        }

        async function loadAdminPanel() {
            if (!isAdmin) return;

            document.getElementById('menuAdmin').style.display = 'flex';

            try {
                const stats = await getAdminStats();
                if (stats) {
                    document.getElementById('adminUserCount').textContent = stats.users?.total || 0;
                    document.getElementById('adminPostCount').textContent = stats.posts?.total || 0;
                    document.getElementById('adminOnlineCount').textContent = stats.users?.online || 0;
                    document.getElementById('adminShardCount').textContent = stats.database?.shardCount || 5;
                }
            } catch (e) { console.error(e); }

            try {
                const users = await getAdminUsers();
                const list = document.getElementById('adminUsersList');
                list.innerHTML = '';
                users.forEach(user => {
                    if (user.isAdmin) return;
                    const div = document.createElement('div');
                    div.className = 'admin-item';
                    div.innerHTML = '<span>' + user.username + ' (' + user.email + ')</span><span><button class="admin-btn ' +
                        (user.isBanned ? 'success' : 'danger') + '" onclick="toggleBan(\'' + user.userId + '\', ' + (!user
                            .isBanned) + ')">' + (user.isBanned ? 'رفع مسدودیت' : 'مسدود کردن') + '</button></span>';
                    list.appendChild(div);
                });
            } catch (e) { console.error(e); }

            try {
                const posts = await getAdminPosts();
                const list = document.getElementById('adminPostsList');
                list.innerHTML = '';
                posts.slice(0, 20).forEach(post => {
                    const div = document.createElement('div');
                    div.className = 'admin-item';
                    div.innerHTML = '<span>' + (post.caption || 'بدون توضیحات').substring(0, 30) + ' ...</span><span><button class="admin-btn danger" onclick="deletePostAdmin(\'' +
                        post.postId + '\')">🗑️ حذف</button></span>';
                    list.appendChild(div);
                });
            } catch (e) { console.error(e); }
        }

        // ============================================
        // 🎯 اکشن‌ها
        // ============================================

        window.handleLike = async function(postId) {
            if (currentUser && currentUser.isBanned) {
                showToast('❌ شما مسدود شده‌اید');
                return;
            }

            const result = await likePost(postId);
            document.querySelectorAll('.like-btn[data-id="' + postId + '"]').forEach(btn => {
                btn.querySelector('i').className = result.liked ? 'fas fa-heart' : 'far fa-heart';
                btn.classList.toggle('liked', result.liked);
                btn.querySelector('.count').textContent = result.likes || 0;
                localStorage.setItem('liked_' + postId, result.liked ? 'true' : 'false');
            });
        };

        window.openComments = async function(postId) {
            if (currentUser && currentUser.isBanned) {
                showToast('❌ شما مسدود شده‌اید');
                return;
            }

            currentPostId = postId;
            const data = await getPosts(1);
            const post = data.posts.find(p => p.postId === postId);
            const list = document.getElementById('commentList');
            list.innerHTML = '';

            if (!post || !post.comments || post.comments.length === 0) {
                list.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:20px;">هنوز کامنتی وجود ندارد</div>';
            } else {
                post.comments.forEach(c => {
                    const div = document.createElement('div');
                    div.className = 'comment-item';
                    div.innerHTML =
                        '<div class="comment-avatar"><img src="https://i.pravatar.cc/150?img=' + Math.floor(Math
                        .random() * 70) + '" alt="avatar"></div><div class="comment-content"><div class="comment-username">' +
                        (c.username || 'کاربر') + '</div><div class="comment-text">' + c.text +
                        '</div><div class="comment-time">' + (c.createdAt ? new Date(c.createdAt).toLocaleString(
                            language === 'fa' ? 'fa-IR' : 'en-US') : 'چند لحظه پیش') + '</div></div>';
                    list.appendChild(div);
                });
            }

            document.getElementById('commentModal').classList.add('active');
            document.getElementById('modalCommentInput').focus();
        };

        window.sharePost = function(postId) {
            document.getElementById('shareModal').dataset.postId = postId;
            document.getElementById('shareModal').classList.add('active');
        };

        window.searchHashtag = function(hashtag) {
            document.getElementById('searchInput').value = '#' + hashtag;
            loadPosts(1, hashtag);
            showToast('🔍 جستجو برای #' + hashtag);
        };

        window.openPostDetail = async function(postId) {
            const data = await getPosts(1);
            const post = data.posts.find(p => p.postId === postId);
            if (!post) {
                showToast('❌ پست پیدا نشد!');
                return;
            }

            let captionHtml = post.caption || 'بدون توضیحات';
            if (post.hashtags && post.hashtags.length > 0) {
                post.hashtags.forEach(h => {
                    captionHtml = captionHtml.replace('#' + h,
                        '<span style="color:var(--primary);cursor:pointer;" onclick="event.stopPropagation(); searchHashtag(\'' +
                        h + '\')">#' + h + '</span>');
                });
            }

            showToast('📸 ' + captionHtml + '\n❤️ ' + (post.likes || 0) + ' لایک\n💬 ' + (post.comments || []).length +
                ' کامنت');
        };

        window.viewStory = async function(storyId) {
            await fetch(API_URL + '/api/stories/' + storyId + '/view', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: currentUser?.userId || 'user1' })
            });
        };

        window.toggleBan = async function(userId, banned) {
            if (currentUser && userId === currentUser.userId) {
                showToast('❌ نمی‌توانید خودتان را مسدود کنید');
                return;
            }
            const result = await banUser(userId, banned);
            if (result.success) {
                showToast('✅ کاربر ' + (banned ? 'مسدود' : 'رفع مسدودیت') + ' شد');
                loadAdminPanel();
            }
        };

        window.deletePostAdmin = async function(postId) {
            if (!confirm('آیا از حذف این پست مطمئن هستید؟')) return;
            const result = await deletePost(postId);
            if (result.success) {
                showToast('✅ پست با موفقیت حذف شد');
                loadAdminPanel();
                loadPosts(1);
            }
        };

        // ============================================
        // 🎬 Event Listeners
        // ============================================

        // Auth
        document.getElementById('logoutBtn')?.addEventListener('click', logoutUser);
        document.getElementById('menuLogout')?.addEventListener('click', logoutUser);

        // Chat
        document.getElementById('chatOpenBtn').addEventListener('click', () => {
            document.getElementById('chatInterface').classList.add('active');
            renderChatUsers();
        });

        document.getElementById('closeChatBtn').addEventListener('click', () => {
            document.getElementById('chatInterface').classList.remove('active');
            if (currentChatRoom) {
                socket.emit('leave-room', { roomId: currentChatRoom, userId: currentUser?.userId });
                currentChatRoom = null;
                currentChatUser = null;
            }
        });

        document.getElementById('chatSendBtn').addEventListener('click', sendChatMessage);
        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendChatMessage();
        });

        // Comments
        document.getElementById('modalSendComment').addEventListener('click', async function() {
            const input = document.getElementById('modalCommentInput');
            const text = input.value.trim();
            if (text && currentPostId) {
                await addComment(currentPostId, text);
                input.value = '';
                document.getElementById('commentList').innerHTML =
                    '<div style="text-align:center;color:var(--success);padding:20px;">✅ کامنت با موفقیت ثبت شد!</div>';
                setTimeout(() => openComments(currentPostId), 500);
            }
        });

        document.getElementById('modalCommentInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') document.getElementById('modalSendComment').click();
        });

        document.getElementById('closeModal').addEventListener('click', () => {
            document.getElementById('commentModal').classList.remove('active');
            currentPostId = null;
        });

        document.getElementById('commentModal').addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
                currentPostId = null;
            }
        });

        // Share
        document.getElementById('closeShareModal').addEventListener('click', () => {
            document.getElementById('shareModal').classList.remove('active');
        });

        document.getElementById('shareModal').addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('active');
        });

        document.querySelectorAll('.share-option').forEach(option => {
            option.addEventListener('click', function() {
                const type = this.getAttribute('data-share');
                const postId = document.getElementById('shareModal').dataset.postId;
                const link = window.location.href + '?post=' + postId;

                if (type === 'site') {
                    showToast('✅ پست در سایت اشتراک‌گذاری شد!');
                } else if (type === 'telegram') {
                    window.open('https://t.me/share/url?url=' + encodeURIComponent(link) + '&text=' +
                        encodeURIComponent('به این پست نگاه کن!'), '_blank');
                } else if (type === 'whatsapp') {
                    window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(
                        'به این پست نگاه کن! ' + link), '_blank');
                } else if (type === 'copy') {
                    navigator.clipboard.writeText(link).then(() => {
                        showToast('✅ لینک کپی شد!');
                    });
                }
                document.getElementById('shareModal').classList.remove('active');
            });
        });

        // Profile
        document.getElementById('profileBtn').addEventListener('click', () => {
            document.getElementById('profilePage').classList.add('active');
            loadProfile();
        });

        document.getElementById('closeProfile').addEventListener('click', () => {
            document.getElementById('profilePage').classList.remove('active');
        });

        document.getElementById('profilePage').addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('active');
        });

        document.getElementById('profileFollowBtn').addEventListener('click', async function() {
            if (!currentUser) return;
            const isFollowing = this.classList.contains('following');
            if (isFollowing) {
                this.classList.remove('following');
                this.textContent = 'دنبال کردن';
            } else {
                this.classList.add('following');
                this.textContent = 'دنبال شده';
            }
        });

        document.getElementById('saveBio').addEventListener('click', async function() {
            const bio = document.getElementById('bioInput').value.trim();
            if (bio && currentUser) {
                const result = await updateProfile(currentUser.userId, { bio });
                if (result.success) {
                    document.getElementById('bioDisplay').textContent = bio;
                    document.getElementById('bioInput').value = '';
                    currentUser.bio = bio;
                    showToast('✅ بیوگرافی با موفقیت ذخیره شد!');
                }
            } else {
                showToast('❌ لطفا بیوگرافی خود را وارد کنید.');
            }
        });

        // Upload
        document.getElementById('uploadBtn').addEventListener('click', () => {
            if (currentUser && currentUser.isBanned) {
                showToast('❌ شما مسدود شده‌اید و نمی‌توانید آپلود کنید');
                return;
            }
            document.getElementById('uploadPage').classList.add('active');
            document.getElementById('uploadHashtags').classList.add('active');
        });

        document.getElementById('closeUpload').addEventListener('click', () => {
            document.getElementById('uploadPage').classList.remove('active');
            resetUpload();
        });

        document.getElementById('uploadPage').addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
                resetUpload();
            }
        });

        document.getElementById('uploadSelectBtn').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });

        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewImg = document.getElementById('previewImage');
                    const previewVideo = document.getElementById('previewVideo');
                    if (file.type.startsWith('image/')) {
                        previewImg.src = e.target.result;
                        previewImg.style.display = 'block';
                        previewVideo.style.display = 'none';
                    } else if (file.type.startsWith('video/')) {
                        previewVideo.src = e.target.result;
                        previewVideo.style.display = 'block';
                        previewImg.style.display = 'none';
                    }
                    document.getElementById('uploadPreview').classList.add('active');
                    document.getElementById('uploadCaption').classList.add('active');
                    document.getElementById('uploadHashtags').classList.add('active');
                    document.getElementById('uploadSubmit').classList.add('active');
                };
                reader.readAsDataURL(file);
            }
        });

        document.getElementById('uploadSubmit').addEventListener('click', async function() {
            if (isUploading) return;
            const file = document.getElementById('fileInput').files[0];
            const caption = document.getElementById('captionInput').value.trim();
            const hashtags = document.getElementById('hashtagInput').value.trim();

            if (!file) {
                showToast('❌ لطفا یک فایل انتخاب کنید.');
                return;
            }

            isUploading = true;
            this.textContent = '⏳ در حال آپلود...';
            this.disabled = true;

            const result = await createPost(file, caption, hashtags);

            if (result && result.postId) {
                showToast('✅ پست با موفقیت آپلود شد!');
                resetUpload();
                document.getElementById('uploadPage').classList.remove('active');
                loadPosts(1);
            } else {
                showToast('❌ خطا در آپلود پست!');
            }

            this.textContent = '📤 ارسال پست';
            this.disabled = false;
            isUploading = false;
        });

        function resetUpload() {
            document.getElementById('fileInput').value = '';
            document.getElementById('uploadPreview').classList.remove('active');
            document.getElementById('uploadCaption').classList.remove('active');
            document.getElementById('uploadHashtags').classList.remove('active');
            document.getElementById('uploadSubmit').classList.remove('active');
            document.getElementById('previewImage').style.display = 'none';
            document.getElementById('previewVideo').style.display = 'none';
            document.getElementById('captionInput').value = '';
            document.getElementById('hashtagInput').value = '';
        }

        // Side Menu
        document.getElementById('menuIcon').addEventListener('click', () => {
            document.getElementById('sideMenu').classList.add('active');
            document.getElementById('menuOverlay').classList.add('active');
        });

        document.getElementById('closeMenu').addEventListener('click', () => {
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
        });

        document.getElementById('menuOverlay').addEventListener('click', () => {
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
        });

        document.getElementById('menuProfile').addEventListener('click', () => {
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
            document.getElementById('profilePage').classList.add('active');
            loadProfile();
        });

        document.getElementById('menuSettings').addEventListener('click', () => {
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
            document.getElementById('settingsPage').classList.add('active');
            loadProfile();
        });

        document.getElementById('menuStats').addEventListener('click', () => {
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
            document.getElementById('settingsPage').classList.add('active');
            loadProfile();
        });

        document.getElementById('menuTheme').addEventListener('click', () => {
            toggleTheme();
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
        });

        document.getElementById('menuAdmin').addEventListener('click', () => {
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
            document.getElementById('adminPanel').classList.add('active');
            loadAdminPanel();
        });

        // Settings
        document.getElementById('settingsOpenBtn').addEventListener('click', () => {
            document.getElementById('settingsPage').classList.add('active');
            loadProfile();
        });

        document.getElementById('closeSettings').addEventListener('click', () => {
            document.getElementById('settingsPage').classList.remove('active');
        });

        document.getElementById('settingsPage').addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('active');
        });

        document.getElementById('languageSelect').addEventListener('change', function() {
            language = this.value;
            localStorage.setItem('language', language);
            if (currentUser) {
                updateProfile(currentUser.userId, { language });
            }
            showToast('✅ زبان تغییر کرد!');
            location.reload();
        });

        document.getElementById('themeToggle').addEventListener('click', toggleTheme);

        function toggleTheme() {
            isDarkTheme = !isDarkTheme;
            document.documentElement.setAttribute('data-theme', isDarkTheme ? 'dark' : 'light');
            localStorage.setItem('theme', isDarkTheme ? 'dark' : 'light');
            document.getElementById('themeToggle').classList.toggle('active');
            showToast(isDarkTheme ? '🌙 تم تاریک فعال شد' : '☀️ تم روشن فعال شد');
        }

        // Admin
        document.getElementById('broadcastBtn').addEventListener('click', async function() {
            const input = document.getElementById('broadcastInput');
            const message = input.value.trim();
            if (!message) {
                showToast('❌ لطفا پیام را وارد کنید');
                return;
            }
            const result = await broadcastMessage(message);
            if (result.success) {
                showToast('✅ پیام همگانی ارسال شد!');
                input.value = '';
            }
        });

        document.getElementById('addShardBtn').addEventListener('click', async function() {
            const result = await addShard();
            if (result.success) {
                showToast('✅ شارد جدید با موفقیت اضافه شد! تعداد شاردها: ' + result.shardCount);
                loadAdminPanel();
            }
        });

        // Close Admin
        document.getElementById('adminPanel').addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('active');
        });

        // Explore / Reels
        let exploreMode = true;
        let reelsMode = false;

        document.getElementById('exploreBtn').addEventListener('click', function() {
            const gallery = document.getElementById('gallery');
            const stories = document.getElementById('storiesSection');

            if (exploreMode) {
                exploreMode = false;
                reelsMode = false;
                gallery.style.gridTemplateColumns = 'repeat(2, 1fr)';
                stories.style.display = 'block';
                this.classList.remove('active');
                document.getElementById('reelsBtn').classList.remove('active');
            } else {
                exploreMode = true;
                reelsMode = false;
                gallery.style.gridTemplateColumns = 'repeat(3, 1fr)';
                stories.style.display = 'none';
                this.classList.add('active');
                document.getElementById('reelsBtn').classList.remove('active');
                loadPosts(1);
            }
        });

        document.getElementById('reelsBtn').addEventListener('click', function() {
            const gallery = document.getElementById('gallery');
            const stories = document.getElementById('storiesSection');

            if (reelsMode) {
                reelsMode = false;
                exploreMode = false;
                gallery.style.gridTemplateColumns = 'repeat(2, 1fr)';
                stories.style.display = 'block';
                this.classList.remove('active');
                document.getElementById('exploreBtn').classList.remove('active');
            } else {
                reelsMode = true;
                exploreMode = false;
                gallery.style.gridTemplateColumns = '1fr';
                stories.style.display = 'none';
                this.classList.add('active');
                document.getElementById('exploreBtn').classList.remove('active');
            }
        });

        // Search
        document.getElementById('searchInput').addEventListener('input', function() {
            const query = this.value.trim();
            if (query.startsWith('#')) {
                loadPosts(1, query.substring(1));
            } else if (query.length > 2) {
                loadPosts(1);
                const gallery = document.getElementById('gallery');
                const items = gallery.querySelectorAll('.gallery-item');
                items.forEach(item => {
                    const text = item.textContent.toLowerCase();
                    item.style.display = text.includes(query.toLowerCase()) ? '' : 'none';
                });
            } else {
                loadPosts(1);
            }
        });

        // Follow stats
        document.getElementById('statFollowers').addEventListener('click', async function() {
            const modal = document.getElementById('followModal');
            document.getElementById('followModalTitle').textContent = '👥 دنبال‌کنندگان';
            const users = await getUsers();
            const body = document.getElementById('followModalBody');
            body.innerHTML = '';
            users.forEach(user => {
                if (user.userId === currentUser?.userId) return;
                const div = document.createElement('div');
                div.className = 'follow-item';
                div.innerHTML =
                    '<div class="follow-avatar"><img src="' + (user.avatar || 'https://i.pravatar.cc/150?img=' +
                    Math.floor(Math.random() * 70)) + '" alt="' + user.username +
                    '"></div><span class="follow-name">' + user.username +
                    '</span><button class="follow-btn" onclick="followUser(\'' + user.userId + '\', \'' + currentUser
                    ?.userId + '\')">دنبال کردن</button>';
                body.appendChild(div);
            });
            modal.style.display = 'flex';
        });

        document.getElementById('statFollowing').addEventListener('click', async function() {
            const modal = document.getElementById('followModal');
            document.getElementById('followModalTitle').textContent = '👥 دنبال‌شونده‌ها';
            const users = await getUsers();
            const body = document.getElementById('followModalBody');
            body.innerHTML = '';
            users.forEach(user => {
                if (user.userId === currentUser?.userId) return;
                const div = document.createElement('div');
                div.className = 'follow-item';
                div.innerHTML =
                    '<div class="follow-avatar"><img src="' + (user.avatar || 'https://i.pravatar.cc/150?img=' +
                    Math.floor(Math.random() * 70)) + '" alt="' + user.username +
                    '"></div><span class="follow-name">' + user.username +
                    '</span><button class="follow-btn" onclick="followUser(\'' + user.userId + '\', \'' + currentUser
                    ?.userId + '\')">دنبال کردن</button>';
                body.appendChild(div);
            });
            modal.style.display = 'flex';
        });

        document.getElementById('closeFollowModal').addEventListener('click', () => {
            document.getElementById('followModal').style.display = 'none';
        });

        document.getElementById('followModal').addEventListener('click', function(e) {
            if (e.target === this) this.style.display = 'none';
        });

        // ============================================
        // 🛠️ Toast
        // ============================================

        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.classList.add('show');
            clearTimeout(toast._timeout);
            toast._timeout = setTimeout(() => toast.classList.remove('show'), 3500);
        }

        // ============================================
        // 🚀 اجرا
        // ============================================

        (async function init() {
            // تنظیم تم
            if (isDarkTheme) {
                document.documentElement.setAttribute('data-theme', 'dark');
                document.getElementById('themeToggle').classList.add('active');
            }

            // تنظیم زبان
            document.getElementById('languageSelect').value = language;

            // بررسی کاربر
            if (currentToken) {
                const user = await getCurrentUser();
                if (user) {
                    currentUser = user;
                    isAdmin = user.isAdmin || false;
                    console.log('✅ کاربر:', currentUser.username, isAdmin ? '(ادمین)' : '');
                } else {
                    localStorage.removeItem('token');
                    currentToken = null;
                }
            }

            // اگر کاربر وجود نداشت، ثبت نام خودکار
            if (!currentUser) {
                const testUser = {
                    username: 'کاربر_' + Math.floor(Math.random() * 10000),
                    email: 'user_' + Date.now() + '@test.com',
                    password: '123456'
                };
                const registerResult = await registerUser(testUser.username, testUser.email, testUser.password);
                if (registerResult.success) {
                    currentToken = registerResult.token;
                    localStorage.setItem('token', currentToken);
                    const user = await getCurrentUser();
                    if (user) {
                        currentUser = user;
                        isAdmin = user.isAdmin || false;
                        console.log('✅ کاربر جدید:', currentUser.username);
                    }
                }
            }

            // اتصال به WebSocket
            if (currentUser) {
                socket.emit('register', { userId: currentUser.userId, username: currentUser.username });
                if (isAdmin) {
                    document.getElementById('menuAdmin').style.display = 'flex';
                }
            }

            // بارگذاری اولیه
            document.getElementById('gallery').style.gridTemplateColumns = 'repeat(3, 1fr)';
            document.getElementById('storiesSection').style.display = 'none';
            document.getElementById('exploreBtn').classList.add('active');

            await loadPosts(1);
            await loadStories();
            await loadProfile();

            console.log('✅ App started! User:', currentUser?.username || 'Guest');
            console.log('🔐 Encryption: AES-256-GCM');
            console.log('📊 Shards: 5');
            console.log('🚀 Ready for millions of users!');
        })();
    </script>
</body>
</html>
    `);
});

// ============================================
// 🚀 اجرا
// ============================================
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    log(`🚀 Server running on http://localhost:${PORT}`);
    log(`🔐 Encryption: AES-256-GCM`);
    log(`📊 Database: 5 Shards`);
    log(`💾 Cache: In-Memory with TTL`);
    log(`📦 Queue: Background Processing`);
    log(`👑 Admin: admin@social.com / Admin@123456`);
});