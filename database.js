// ============================================
// database.js - نسخه نهایی PostgreSQL
// ============================================
const { Pool } = require('pg');
const crypto = require('crypto');

const SHARD_COUNT = Math.max(1, parseInt(process.env.DB_SHARD_COUNT || '4', 10));

class DatabaseManager {
    constructor() {
        this.shardCount = SHARD_COUNT;
        this.cache = new Map();
        this.cacheTTL = 60000;
        this.cacheMaxEntries = 3000;
        this.directory = new Map();
        this.encryptionKey = crypto.randomBytes(32);

        this.pool = new Pool({
            connectionString: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/yareman',
            max: 20,
            idleTimeoutMillis: 30000,
            connectionTimeoutMillis: 10000,
        });

        this.pool.on('error', (err) => {
            console.error('❌ خطای PostgreSQL:', err.message);
        });

        this.ready = this._init();
    }

    async _init() {
        try {
            await this._initSchemas();
            await this._ensureAdmin();
            console.log(`✅ PostgreSQL آماده شد با ${this.shardCount} شارد`);
        } catch (error) {
            console.error('❌ خطا در راه‌اندازی:', error);
            throw error;
        }
    }

    async _initSchemas() {
        for (let i = 0; i < this.shardCount; i++) {
            const client = await this.pool.connect();
            try {
                const schema = `shard_${i}`;
                await client.query(`CREATE SCHEMA IF NOT EXISTS ${schema}`);
                await client.query(`SET search_path TO ${schema}, public`);

                // ==================== جدول users ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        username TEXT UNIQUE,
                        email TEXT UNIQUE,
                        password_hash TEXT,
                        avatar TEXT,
                        bio TEXT,
                        score INTEGER DEFAULT 0,
                        role TEXT DEFAULT 'user',
                        is_verified INTEGER DEFAULT 0,
                        restricted INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول channels ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS channels (
                        id TEXT PRIMARY KEY,
                        user_id TEXT UNIQUE,
                        name TEXT NOT NULL,
                        description TEXT,
                        posts_count INTEGER DEFAULT 0,
                        followers_count INTEGER DEFAULT 0,
                        boost_level TEXT DEFAULT 'normal',
                        activity_score INTEGER DEFAULT 0,
                        last_boost_calc TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول posts ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS posts (
                        id TEXT PRIMARY KEY,
                        channel_id TEXT,
                        content TEXT NOT NULL,
                        media_url TEXT,
                        media_type TEXT,
                        views INTEGER DEFAULT 0,
                        likes INTEGER DEFAULT 0,
                        comments INTEGER DEFAULT 0,
                        scheduled_time TIMESTAMPTZ,
                        is_published INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        published_at TIMESTAMPTZ,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول messages ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        from_user TEXT NOT NULL,
                        to_user TEXT NOT NULL,
                        message TEXT NOT NULL,
                        media_url TEXT,
                        media_type TEXT,
                        is_read INTEGER DEFAULT 0,
                        encrypted INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول follows ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS follows (
                        follower_id TEXT NOT NULL,
                        following_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (follower_id, following_id)
                    )
                `);

                // ==================== جدول post_likes ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS post_likes (
                        post_id TEXT,
                        user_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (post_id, user_id)
                    )
                `);

                // ==================== جدول post_comments ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS post_comments (
                        id TEXT PRIMARY KEY,
                        post_id TEXT,
                        user_id TEXT NOT NULL,
                        user_name TEXT,
                        user_avatar TEXT,
                        text TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول assistant_training ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS assistant_training (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        type TEXT,
                        question TEXT,
                        answer TEXT,
                        keyword TEXT,
                        response TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول stories ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS stories (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        media_url TEXT,
                        media_type TEXT DEFAULT 'image',
                        caption TEXT,
                        bg_color TEXT DEFAULT '#6c5ce7',
                        text_color TEXT DEFAULT '#ffffff',
                        views_count INTEGER DEFAULT 0,
                        is_highlight INTEGER DEFAULT 0,
                        highlight_title TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMPTZ NOT NULL
                    )
                `);

                // ==================== جدول story_views ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS story_views (
                        id TEXT PRIMARY KEY,
                        story_id TEXT NOT NULL,
                        viewer_id TEXT NOT NULL,
                        viewed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول system_notifications ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS system_notifications (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        type TEXT DEFAULT 'general',
                        broadcast_id TEXT,
                        is_read INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول blocked_users ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS blocked_users (
                        blocker_id TEXT NOT NULL,
                        blocked_id TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (blocker_id, blocked_id)
                    )
                `);

                // ==================== جدول ads ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS ads (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT,
                        media_url TEXT,
                        media_type TEXT DEFAULT 'none',
                        link_url TEXT,
                        is_active INTEGER DEFAULT 1,
                        views INTEGER DEFAULT 0,
                        clicks INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول payment_receipts ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS payment_receipts (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        post_id TEXT,
                        receipt_image TEXT NOT NULL,
                        amount TEXT,
                        status TEXT DEFAULT 'pending',
                        admin_note TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        reviewed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول reports ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS reports (
                        id TEXT PRIMARY KEY,
                        reporter_id TEXT NOT NULL,
                        target_id TEXT,
                        target_type TEXT,
                        reason TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                `);

                // ==================== جدول password_resets ====================
                await client.query(`
                    CREATE TABLE IF NOT EXISTS password_resets (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        code_hash TEXT NOT NULL,
                        used INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMPTZ NOT NULL
                    )
                `);

            } finally {
                client.release();
            }
        }
        console.log(`✅ ${this.shardCount} شارد با تمام جدول‌ها ساخته شد`);
    }

    // ==================== ساخت ادمین ====================
    async _ensureAdmin() {
        const ADMIN_EMAIL = 'milad.yari1377m@gmail.com';
        const ADMIN_USERNAME = 'milad13777';
        const ADMIN_PASSWORD = 'M09145978426mbn';
        const ADMIN_ID = 'admin_milad';

        const shardIdx = 0;
        const passwordHash = this.hashPassword(ADMIN_PASSWORD);

        try {
            const existing = await this._exec(shardIdx, 
                `SELECT id FROM users WHERE id = $1 OR email = $2`, 
                [ADMIN_ID, ADMIN_EMAIL]
            );

            if (existing.rows.length === 0) {
                await this._exec(shardIdx, `
                    INSERT INTO users (id, name, username, email, password_hash, avatar, role, is_verified, score, created_at)
                    VALUES ($1, $2, $3, $4, $5, '/admin-avatar.png', 'admin', 1, 999999, CURRENT_TIMESTAMP)
                `, [ADMIN_ID, 'مدیر سیستم', ADMIN_USERNAME, ADMIN_EMAIL, passwordHash]);

                await this._exec(shardIdx, `
                    INSERT INTO channels (id, user_id, name, boost_level, created_at)
                    VALUES ('channel_admin', $1, 'کانال مدیریت', 'superstar', CURRENT_TIMESTAMP)
                `, [ADMIN_ID]);

                console.log(`✅ کاربر ادمین ساخته شد: ${ADMIN_USERNAME}`);
            } else {
                console.log(`✅ کاربر ادمین از قبل وجود دارد`);
            }
        } catch (error) {
            console.error('❌ خطا در ساخت ادمین:', error.message);
        }
    }

    // ==================== هش رمز ====================
    hashPassword(password) {
        const salt = crypto.randomBytes(16).toString('hex');
        const hash = crypto.scryptSync(String(password), salt, 64).toString('hex');
        return `${salt}:${hash}`;
    }

    verifyPassword(password, stored) {
        try {
            if (!stored || !stored.includes(':')) return false;
            const [salt, hash] = stored.split(':');
            const check = crypto.scryptSync(String(password), salt, 64).toString('hex');
            return crypto.timingSafeEqual(
                Buffer.from(hash, 'hex'),
                Buffer.from(check, 'hex')
            );
        } catch (e) {
            return false;
        }
    }

    // ==================== شاردینگ ====================
    hashKey(key) {
        const hash = crypto.createHash('md5').update(String(key)).digest();
        return hash.readUInt32BE(0) % this.shardCount;
    }

    resolveShardIndex(key) {
        if (key === null || key === undefined) return 0;
        const hit = this.directory.get(String(key));
        if (hit !== undefined) return hit;
        return this.hashKey(key);
    }

    // ==================== جستجوی کاربر (برای ثبت‌نام و ورود) ====================
    async findUserByUsernameOrEmail(usernameOrEmail) {
        const val = String(usernameOrEmail || '').trim().toLowerCase();
        if (!val) return null;

        for (let i = 0; i < this.shardCount; i++) {
            try {
                const result = await this._exec(i, 
                    `SELECT * FROM users WHERE LOWER(username) = $1 OR LOWER(email) = $1 LIMIT 1`, 
                    [val]
                );
                if (result.rows.length > 0) {
                    return result.rows[0];
                }
            } catch (e) {
                // خطاهای نبود جدول رو نادیده بگیر
                if (!e.message.includes('relation') && !e.message.includes('schema')) {
                    console.error('findUserByUsernameOrEmail error on shard', i, e.message);
                }
            }
        }
        return null;
    }

    // ==================== اجرای کوئری ====================
    async _exec(shardIndex, text, params = []) {
        const client = await this.pool.connect();
        try {
            await client.query(`SET search_path TO shard_${shardIndex}, public`);
            return await client.query(text, params);
        } finally {
            client.release();
        }
    }

    // ==================== متد query اصلی ====================
    async query(key, text, params = []) {
        const shardIndex = key === null ? 0 : this.resolveShardIndex(key);
        const result = await this._exec(shardIndex, text, params);
        return { rows: result.rows || [], rowCount: result.rowCount || 0 };
    }

    async queryShardByIndex(shardIndex, text, params = []) {
        return this._exec(shardIndex, text, params);
    }

    getAllShardIndexes() {
        return Array.from({ length: this.shardCount }, (_, i) => i);
    }

    // ==================== متدهای کمکی ====================
    async followUser(followerId, followingId) {
        return { success: true };
    }

    async unfollowUser(followerId, followingId) {
        return { success: true };
    }

    async blockUser(blockerId, blockedId) {
        return { success: true };
    }

    async unblockUser(blockerId, blockedId) {
        return { success: true };
    }

    async isBlocked(userA, userB) {
        return false;
    }

    async toggleLike(postId, userId) {
        return { success: true, liked: true, likes: 0 };
    }

    invalidateCache() {
        this.cache.clear();
    }

    clearCache() {
        this.cache.clear();
    }

    async getStats() {
        return { shardCount: this.shardCount, perShard: [] };
    }

    async close() {
        await this.pool.end();
    }
}

module.exports = DatabaseManager;