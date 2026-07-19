// ============================================
// database.js - مدیریت دیتابیس با شاردینگ، کش هوشمند و رمزنگاری
// نسخه‌ی PostgreSQL (قبلاً روی better-sqlite3 بود)
// ============================================
//
// معماری شاردینگ (بدون تغییر نسبت به قبل، فقط موتور ذخیره‌سازی عوض شده):
//   - ۱۵۰ "شارد منطقی" داریم (با DB_SHARD_COUNT قابل تغییره)، ولی به‌جای ۱۵۰ فایل SQLite جدا،
//     همه‌شون روی یه دیتابیس PostgreSQL واحدند: هر شارد یه SCHEMA جدا (shard_0 .. shard_149) با
//     یه Pool اتصال مشترک. این یعنی هزاران کاربر همزمان بدون باز نگه‌داشتن ۱۵۰ اتصال واقعی جواب
//     می‌گیرن (Pool اتصال‌ها رو بین درخواست‌ها بازیافت می‌کنه) - دقیقاً همون چیزی که برای «میلیون‌ها
//     کاربر» لازمه؛ نگه‌داشتن ۱۵۰ کانکشن دائمی به هر شارد (مثل نسخه‌ی SQLite قبلی) در مقیاس واقعی
//     غیرممکن و کندکننده بود.
//   - هر ردیف بر اساس "صاحبِ" اون ردیف مسیریابی می‌شه: کاربر با هش(id) روی یه شارد (schema) ثابت
//     قرار می‌گیره و پست‌ها/کانال/کامنت‌ها/لایک‌های همون کاربر هم روی همون شارد ذخیره می‌شن.
//   - برای موجودیت‌هایی که بعداً با شناسه‌ی خودشون (نه شناسه‌ی صاحبشون) جستجو می‌شن (مثلاً پست با
//     postId) یه "دایرکتوری" (entity_id -> shard_index) روی جدول public._shard_directory
//     نگه می‌داریم که موقع INSERT خودکار پر می‌شه (و در حافظه هم کش می‌شه، برای سرعت).
//   - برای رابطه‌هایی که ذاتاً بین دو کاربر مختلفن (پیام‌های چت) از هش زوجی استفاده می‌شه تا کل
//     مکالمه‌ی بین دو نفر همیشه روی یه شارد بمونه.
//   - فالو/آنفالو/بلاک چون بین دو کاربر مختلفن و از هر دو طرف خونده می‌شن، با "نوشتن دوگانه"
//     (dual-write) روی شارد هر دو کاربر ذخیره می‌شن.
//
// سازگاری با کد قبلی: ستون‌های تاریخ (created_at و...) به‌جای TEXT الان TIMESTAMPTZ واقعی هستن
// (که خیلی درست‌تر و سریع‌تر برای مرتب‌سازی/فیلتره)، ولی خروجی‌شون از Postgres با یه
// type-parser سفارشی به همون فرمت متنیِ قبلیِ SQLite ("YYYY-MM-DD HH:MM:SS", بدون تایم‌زون،
// UTC) برگردونده می‌شه - یعنی کدهای فرانت/بک‌اند که قبلاً با new Date(dateStr + 'Z') کار
// می‌کردن بدون هیچ تغییری درست کار می‌کنن.
// ============================================
const { Pool, types } = require('pg');
const crypto = require('crypto');

const SHARD_COUNT = Math.max(1, parseInt(process.env.DB_SHARD_COUNT || '150', 10));

// ---- سازگاری فرمت تاریخ با نسخه‌ی قبلی (SQLite) ----
const PG_TIMESTAMP_OID = 1114;   // timestamp بدون تایم‌زون
const PG_TIMESTAMPTZ_OID = 1184; // timestamp with time zone
function formatTimestampLikeBefore(raw) {
    if (raw === null || raw === undefined) return raw;
    const d = new Date(raw);
    if (isNaN(d.getTime())) return raw;
    return d.toISOString().slice(0, 19).replace('T', ' '); // "YYYY-MM-DD HH:MM:SS" (UTC)
}
types.setTypeParser(PG_TIMESTAMP_OID, formatTimestampLikeBefore);
types.setTypeParser(PG_TIMESTAMPTZ_OID, formatTimestampLikeBefore);

// ---- DDL کامل هر شارد (هر schema این جدول‌ها رو کامل داره) ----
const SHARD_SCHEMA_SQL = `
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        username TEXT,
        email TEXT,
        password_hash TEXT,
        avatar TEXT,
        bio TEXT,
        score INTEGER DEFAULT 0,
        role TEXT DEFAULT 'user',
        is_verified INTEGER DEFAULT 0,
        restricted INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        signup_rank BIGINT DEFAULT nextval('public.global_user_signup_seq')
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;
    CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_users_score ON users(score DESC);
    CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at ASC);
    CREATE INDEX IF NOT EXISTS idx_users_signup_rank ON users(signup_rank ASC);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_rank BIGINT DEFAULT nextval('public.global_user_signup_seq');

    CREATE TABLE IF NOT EXISTS channels (
        id TEXT PRIMARY KEY,
        user_id TEXT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        description TEXT,
        posts_count INTEGER DEFAULT 0,
        followers_count INTEGER DEFAULT 0,
        boost_level TEXT DEFAULT 'normal',
        activity_score INTEGER DEFAULT 0,
        last_boost_calc TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_channels_score ON channels(activity_score DESC);

    CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        channel_id TEXT REFERENCES channels(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        media_url TEXT,
        media_type TEXT CHECK (media_type IN ('image', 'video', 'audio', 'none')),
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        scheduled_time TIMESTAMPTZ,
        is_published INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        published_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_posts_channel ON posts(channel_id);
    CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(is_published, scheduled_time);
    CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);

    CREATE TABLE IF NOT EXISTS post_hashtags (
        post_id TEXT REFERENCES posts(id) ON DELETE CASCADE,
        tag TEXT NOT NULL,
        PRIMARY KEY (post_id, tag)
    );
    CREATE INDEX IF NOT EXISTS idx_hashtags_tag ON post_hashtags(tag);

    CREATE TABLE IF NOT EXISTS post_saves (
        post_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (post_id, user_id)
    );
    CREATE INDEX IF NOT EXISTS idx_saves_user ON post_saves(user_id);

    CREATE TABLE IF NOT EXISTS assistant_training (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        type TEXT CHECK (type IN ('qa', 'keyword')),
        question TEXT,
        answer TEXT,
        keyword TEXT,
        response TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_assistant_user ON assistant_training(user_id);

    -- توجه: from_user/to_user عمداً بدون REFERENCES هستن، چون ممکنه صاحب هر طرف روی شارد
    -- (schema) دیگه‌ای باشه و FK بین schema های مختلف در این معماری چک نمی‌شه.
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
    );
    CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(from_user, to_user);
    CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(to_user, is_read);

    CREATE TABLE IF NOT EXISTS follows (
        follower_id TEXT NOT NULL,
        following_id TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (follower_id, following_id)
    );
    CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_id);
    CREATE INDEX IF NOT EXISTS idx_follows_following ON follows(following_id);

    -- استوری: عکس/ویدیو/متن، ۲۴ ساعته منقضی می‌شه، قابلیت هایلایت دائمی داره
    CREATE TABLE IF NOT EXISTS stories (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        media_url TEXT,
        media_type TEXT DEFAULT 'image' CHECK (media_type IN ('image', 'video', 'text')),
        caption TEXT,
        bg_color TEXT DEFAULT '#6c5ce7',
        text_color TEXT DEFAULT '#ffffff',
        views_count INTEGER DEFAULT 0,
        is_highlight INTEGER DEFAULT 0,
        highlight_title TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_stories_user_expiry ON stories(user_id, expires_at);
    CREATE INDEX IF NOT EXISTS idx_stories_highlight ON stories(user_id, is_highlight);

    CREATE TABLE IF NOT EXISTS story_views (
        id TEXT PRIMARY KEY,
        story_id TEXT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
        viewer_id TEXT NOT NULL,
        viewed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_story_view_unique ON story_views(story_id, viewer_id);
    CREATE INDEX IF NOT EXISTS idx_story_views_story ON story_views(story_id);

    CREATE TABLE IF NOT EXISTS post_likes (
        post_id TEXT REFERENCES posts(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (post_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS post_comments (
        id TEXT PRIMARY KEY,
        post_id TEXT REFERENCES posts(id) ON DELETE CASCADE,
        user_id TEXT NOT NULL,
        user_name TEXT,
        user_avatar TEXT,
        text TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_comments_post ON post_comments(post_id);
    CREATE INDEX IF NOT EXISTS idx_comments_created ON post_comments(created_at DESC);

    CREATE TABLE IF NOT EXISTS system_notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'general',
        broadcast_id TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_notifications_user ON system_notifications(user_id, is_read);
    CREATE INDEX IF NOT EXISTS idx_notifications_created ON system_notifications(created_at DESC);

    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        reporter_id TEXT NOT NULL,
        target_id TEXT,
        target_type TEXT CHECK (target_type IN ('user', 'post', 'comment')),
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMPTZ
    );
    CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

    -- مثل follows، بین دو کاربر ممکنه روی شاردهای متفاوت باشن، بدون REFERENCES بین‌شاردی
    CREATE TABLE IF NOT EXISTS blocked_users (
        blocker_id TEXT NOT NULL,
        blocked_id TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (blocker_id, blocked_id)
    );
    CREATE INDEX IF NOT EXISTS idx_blocked_blocker ON blocked_users(blocker_id);
    CREATE INDEX IF NOT EXISTS idx_blocked_blocked ON blocked_users(blocked_id);

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
    );
    CREATE INDEX IF NOT EXISTS idx_ads_active ON ads(is_active);

    CREATE TABLE IF NOT EXISTS payment_receipts (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        post_id TEXT,
        receipt_image TEXT NOT NULL,
        amount TEXT,
        status TEXT DEFAULT 'pending',
        admin_note TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMPTZ
    );
    CREATE INDEX IF NOT EXISTS idx_receipts_status ON payment_receipts(status);
    CREATE INDEX IF NOT EXISTS idx_receipts_user ON payment_receipts(user_id);

    -- نشست‌های ورود (برای "خروج نشد، اطلاعات پاک نشد" - آی‌دی دستگاه/توکن پایدار می‌مونه)
    CREATE TABLE IF NOT EXISTS user_sessions (
        token_hash TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        device_label TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);

    -- بازیابی رمز عبور با کد یک‌بارمصرف
    CREATE TABLE IF NOT EXISTS password_resets (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        code_hash TEXT NOT NULL,
        used INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_pwreset_user ON password_resets(user_id);
`;

class DatabaseManager {
    constructor() {
        this.shardCount = SHARD_COUNT;

        // ==========================================
        // کش حافظه با سقف اندازه (LRU تقریبی) و ابطال آگاه از جدول
        // ==========================================
        this.cache = new Map(); // cacheKey -> { data, timestamp, tables: [] }
        this.cacheTTL = 60000; // ۶۰ ثانیه
        this.cacheMaxEntries = 3000;

        // دایرکتوری entity_id -> shard_index (در حافظه، پشتیبان‌گیری‌شده روی public._shard_directory)
        this.directory = new Map();

        // کلید رمزنگاری - هر بار اجرای encrypt() یک IV تصادفی جدید تولید می‌کنه
        this.encryptionKey = crypto.randomBytes(32);

        // ==========================================
        // یک Pool اتصال مشترک برای کل ۱۵۰ شارد (schema) - نه ۱۵۰ اتصال جدا
        // ==========================================
        this.pool = new Pool({
            connectionString: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/yareman',
            max: parseInt(process.env.PG_POOL_MAX || '50', 10), // برای مقیاس بالاتر افزایش داده شد (قبلاً ۲۰)
            idleTimeoutMillis: 30000,
            connectionTimeoutMillis: 10000,
        });
        this.pool.on('error', (err) => {
            console.error('⚠️  خطای غیرمنتظره در Pool اتصال PostgreSQL:', err.message);
        });

        // سرور (server.js) باید قبل از server.listen(...) این Promise رو await کنه
        this.ready = this._init();
    }

    async _init() {
        try {
            await this._initSchemas();
            await this._loadDirectory();
            await this._ensureAdmin();
            console.log(`✅ PostgreSQL آماده شد با ${this.shardCount} شارد منطقی (schema)`);
        } catch (error) {
            console.error('❌ خطا در راه‌اندازی PostgreSQL:', error);
            throw error;
        }
    }

    // ============================================
    // ساخت schema ها و جدول‌ها
    // ============================================
    async _initSchemas() {
        const bootClient = await this.pool.connect();
        try {
            await bootClient.query(`
                CREATE TABLE IF NOT EXISTS public._shard_directory (
                    entity_id TEXT PRIMARY KEY,
                    shard_index INTEGER NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE SEQUENCE IF NOT EXISTS public.global_user_signup_seq;
            `);
        } finally {
            bootClient.release();
        }

        const createOne = async (i) => {
            const client = await this.pool.connect();
            try {
                const schema = `shard_${i}`;
                await client.query(`CREATE SCHEMA IF NOT EXISTS ${schema}`);
                await client.query(`SET search_path TO ${schema}, public`);
                await client.query(SHARD_SCHEMA_SQL);
            } finally {
                client.release();
            }
        };

        // موازی ولی دسته‌ای (batch) تا موقع راه‌اندازی اول، Pool با ۱۵۰ درخواست همزمان خفه نشه
        const BATCH = 10;
        for (let start = 0; start < this.shardCount; start += BATCH) {
            const batch = [];
            for (let i = start; i < Math.min(start + BATCH, this.shardCount); i++) batch.push(createOne(i));
            await Promise.all(batch);
        }
        console.log(`✅ ${this.shardCount} schema PostgreSQL ساخته/تایید شد`);
    }

    async _ensureAdmin() {
        const shardIdx = this.hashKey('admin_milad');
        const ADMIN_USERNAME = 'milad13777';
        const ADMIN_EMAIL = 'milad.yari1377m@gmail.com';
        const ADMIN_PASSWORD = 'M09145978426mbn';

        const existing = await this._exec(shardIdx, `SELECT id, password_hash FROM users WHERE id = $1`, ['admin_milad']);
        const adminRow = existing.rows[0];

        if (!adminRow) {
            const pwHash = this.hashPassword(ADMIN_PASSWORD);
            await this._exec(shardIdx, `
                INSERT INTO users (id, name, username, email, password_hash, avatar, role, is_verified, score, created_at)
                VALUES ('admin_milad', 'مدیر سیستم', $1, $2, $3, '/admin-avatar.png', 'admin', 1, 999999, CURRENT_TIMESTAMP)
            `, [ADMIN_USERNAME, ADMIN_EMAIL, pwHash]);
            await this._exec(shardIdx, `
                INSERT INTO channels (id, user_id, name, boost_level, created_at)
                VALUES ('channel_admin', 'admin_milad', 'کانال مدیریت', 'superstar', CURRENT_TIMESTAMP)
            `);
            await this.registerDirectory('admin_milad', shardIdx);
            await this.registerDirectory('channel_admin', shardIdx);
            console.log(`✅ کاربر ادمین روی شارد ${shardIdx} ساخته شد`);
        } else if (!adminRow.password_hash) {
            const pwHash = this.hashPassword(ADMIN_PASSWORD);
            await this._exec(shardIdx, `UPDATE users SET username = $1, email = $2, password_hash = $3 WHERE id = 'admin_milad'`,
                [ADMIN_USERNAME, ADMIN_EMAIL, pwHash]);
            console.log(`✅ اطلاعات ورود ادمین تکمیل شد (شارد ${shardIdx})`);
        }
    }

    // ============================================
    // رمزنگاری و رمزگشایی (AES-256-GCM با IV تصادفی به‌ازای هر پیام)
    // ============================================
    encrypt(text) {
        try {
            const iv = crypto.randomBytes(16);
            const cipher = crypto.createCipheriv('aes-256-gcm', this.encryptionKey, iv);
            let encrypted = cipher.update(text, 'utf8', 'hex');
            encrypted += cipher.final('hex');
            const authTag = cipher.getAuthTag().toString('hex');
            return `${iv.toString('hex')}:${encrypted}:${authTag}`;
        } catch (error) {
            console.error('Encryption error:', error);
            return text;
        }
    }

    decrypt(encryptedText) {
        try {
            const parts = encryptedText.split(':');
            if (parts.length !== 3) return encryptedText;
            const [ivHex, encrypted, authTag] = parts;
            const decipher = crypto.createDecipheriv('aes-256-gcm', this.encryptionKey, Buffer.from(ivHex, 'hex'));
            decipher.setAuthTag(Buffer.from(authTag, 'hex'));
            let decrypted = decipher.update(encrypted, 'hex', 'utf8');
            decrypted += decipher.final('utf8');
            return decrypted;
        } catch (error) {
            console.error('Decryption error:', error);
            return encryptedText;
        }
    }

    // ============================================
    // هش رمز عبور (scrypt) - بدون I/O، پس همچنان synchronous
    // ============================================
    hashPassword(password) {
        const salt = crypto.randomBytes(16).toString('hex');
        const hash = crypto.scryptSync(String(password), salt, 64).toString('hex');
        return `${salt}:${hash}`;
    }

    verifyPassword(password, stored) {
        try {
            if (!stored || typeof stored !== 'string' || !stored.includes(':')) return false;
            const [salt, hash] = stored.split(':');
            const check = crypto.scryptSync(String(password), salt, 64).toString('hex');
            const a = Buffer.from(hash, 'hex');
            const b = Buffer.from(check, 'hex');
            if (a.length !== b.length) return false;
            return crypto.timingSafeEqual(a, b);
        } catch (e) {
            return false;
        }
    }

    // جستجوی کاربر با یوزرنیم یا ایمیل - همه‌ی شاردها موازی چک می‌شن (نه یکی‌یکی، برای سرعت)
    async findUserByUsernameOrEmail(usernameOrEmail) {
        const val = String(usernameOrEmail || '').trim().toLowerCase();
        if (!val) return null;
        const results = await Promise.all(
            Array.from({ length: this.shardCount }, (_, i) =>
                this._exec(i, `SELECT * FROM users WHERE lower(username) = $1 OR lower(email) = $1`, [val]).catch(() => ({ rows: [] }))
            )
        );
        for (const r of results) if (r.rows.length) return r.rows[0];
        return null;
    }

    // ============================================
    // شاردینگ - هش سازگار (consistent hashing ساده با mod) - بدون I/O
    // ============================================
    hashKey(key) {
        const hash = crypto.createHash('md5').update(String(key)).digest();
        return hash.readUInt32BE(0) % this.shardCount;
    }

    pairShardIndex(userA, userB) {
        const pairKey = [String(userA), String(userB)].sort().join('::');
        return this.hashKey(pairKey);
    }

    resolveShardIndex(key) {
        if (key === null || key === undefined) return null;
        const hit = this.directory.get(String(key));
        if (hit !== undefined) return hit;
        return this.hashKey(key);
    }

    async registerDirectory(entityId, shardIndex) {
        if (entityId === undefined || entityId === null) return;
        const id = String(entityId);
        if (this.directory.get(id) === shardIndex) return;
        this.directory.set(id, shardIndex); // فوری در حافظه، برای resolveShardIndex همین لحظه
        try {
            const client = await this.pool.connect();
            try {
                await client.query(`
                    INSERT INTO public._shard_directory (entity_id, shard_index, updated_at)
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (entity_id) DO UPDATE SET shard_index = EXCLUDED.shard_index, updated_at = CURRENT_TIMESTAMP
                `, [id, shardIndex]);
            } finally {
                client.release();
            }
        } catch (e) {
            console.error('Directory persist error:', e.message);
        }
    }

    async _loadDirectory() {
        try {
            const client = await this.pool.connect();
            try {
                const r = await client.query(`SELECT entity_id, shard_index FROM public._shard_directory`);
                for (const row of r.rows) this.directory.set(row.entity_id, row.shard_index);
                console.log(`✅ دایرکتوری بارگذاری شد: ${r.rows.length} نگاشت`);
            } finally {
                client.release();
            }
        } catch (e) {
            console.error('Directory load error:', e.message);
        }
    }

    // اگه INSERT روی ستون اول id باشه، خودکار در دایرکتوری ثبت می‌شه (fire-and-forget عمدی:
    // برای سرعت پاسخ، منتظر تمام‌شدنش نمی‌مونیم - نقشه در حافظه فوری آپدیت می‌شه، نوشتن روی
    // دیسک در پس‌زمینه انجام می‌شه)
    _maybeRegisterFromInsert(sql, params, shardIndex) {
        const m = sql.match(/INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)/i);
        if (!m) return;
        const cols = m[2].split(',').map(c => c.trim());
        if (cols[0] === 'id' && params && params[0] !== undefined) {
            this.registerDirectory(params[0], shardIndex).catch(() => {});
        }
    }

    // اجرای مستقیم یه کوئری روی یه schema مشخص (بدون کش) - برای متدهای کمکی و کارهای ادمین
    async _exec(shardIndex, text, params = []) {
        const client = await this.pool.connect();
        try {
            await client.query(`SET search_path TO shard_${shardIndex}, public`);
            const result = await client.query(text, params);
            this._maybeRegisterFromInsert(text, params, shardIndex);
            return result;
        } finally {
            client.release();
        }
    }

    // اجرای تراکنشی (BEGIN/COMMIT/ROLLBACK) روی یه schema مشخص
    async _withTransaction(shardIndex, fn) {
        const client = await this.pool.connect();
        try {
            await client.query(`SET search_path TO shard_${shardIndex}, public`);
            await client.query('BEGIN');
            const result = await fn(client);
            await client.query('COMMIT');
            return result;
        } catch (e) {
            await client.query('ROLLBACK').catch(() => {});
            throw e;
        } finally {
            client.release();
        }
    }

    // دسترسی مستقیم به یه schema با شماره (نه با کلید) - برای کارهای ادمین که باید همه‌ی
    // شاردها رو یکی‌یکی بگردن (مثل ارسال همگانی)
    async queryShardByIndex(shardIndex, text, params = []) {
        return this._exec(shardIndex, text, params);
    }

    getAllShardIndexes() {
        return Array.from({ length: this.shardCount }, (_, i) => i);
    }

    // ============================================
    // اجرای کوئری با مسیریابی شارد + کش (امضای بیرونی دقیقاً مثل قبل: db.query(key, sql, params))
    // ============================================
    async query(key, text, params = []) {
        const cmd = text.trim().slice(0, 6).toUpperCase();
        const messagesRoute = this._routeMessagesQuery(text, params);

        if (messagesRoute) {
            if (messagesRoute.mode === 'single') {
                return this._runOnShard(messagesRoute.shard, text, params, cmd, `msg:${messagesRoute.shard}`);
            }
            return this._runScatterGather(text, params, cmd);
        }

        if (key === null) {
            return this._runScatterGather(text, params, cmd);
        }

        const shardIndex = this.resolveShardIndex(key);
        return this._runOnShard(shardIndex, text, params, cmd, `s:${shardIndex}`);
    }

    _routeMessagesQuery(sql, params) {
        if (!/\bmessages\b/i.test(sql)) return null;

        if (/INSERT\s+INTO\s+messages/i.test(sql)) {
            const from = params[1], to = params[2];
            if (from !== undefined && to !== undefined) {
                return { mode: 'single', shard: this.pairShardIndex(from, to) };
            }
            return null;
        }

        if (/from_user\s*=\s*\$1[\s\S]*to_user\s*=\s*\$2[\s\S]*from_user\s*=\s*\$2/i.test(sql)) {
            const a = params[0], b = params[1];
            if (a !== undefined && b !== undefined) {
                return { mode: 'single', shard: this.pairShardIndex(a, b) };
            }
        }

        if (/from_user\s*=\s*\$1\s*OR\s*to_user\s*=\s*\$1/i.test(sql) || /WHERE\s+from_user\s*=\s*\$1\s+OR\s+to_user\s*=\s*\$1/i.test(sql)) {
            return { mode: 'scatter' };
        }
        if (/UPDATE\s+messages/i.test(sql) && params.length >= 2) {
            return { mode: 'single', shard: this.pairShardIndex(params[0], params[1]) };
        }
        return { mode: 'scatter' };
    }

    async _runOnShard(shardIndex, text, params, cmd, cacheTag) {
        const cacheKey = `${cacheTag}_${text}_${JSON.stringify(params)}`;
        if (cmd === 'SELECT') {
            const cached = this.cache.get(cacheKey);
            if (cached && (Date.now() - cached.timestamp) < this.cacheTTL) {
                return cached.data;
            }
        }

        const result = await this._exec(shardIndex, text, params);

        if (cmd === 'SELECT') {
            const out = { rows: result.rows };
            this._cacheSet(cacheKey, out, this._tablesInSql(text));
            return out;
        }

        this._invalidateByTables(this._tablesInSql(text));
        return { rows: result.rows || [], rowCount: result.rowCount };
    }

    // پخش موازی کوئری بین همه‌ی شاردها و ادغام نتایج (برای کلید null یا وقتی صاحب مشخصی نداریم)
    // موازی (Promise.all) نه یکی‌یکی - چون ۱۵۰ رفت‌وبرگشت پشت‌سرهم خیلی کند می‌شد.
    async _runScatterGather(text, params, cmd) {
        const cacheKey = `scatter_${text}_${JSON.stringify(params)}`;
        if (cmd === 'SELECT') {
            const cached = this.cache.get(cacheKey);
            if (cached && (Date.now() - cached.timestamp) < this.cacheTTL) {
                return cached;
            }
        }

        let results;
        try {
            results = await Promise.all(
                Array.from({ length: this.shardCount }, (_, i) => this._exec(i, text, params))
            );
        } catch (error) {
            console.error('Database scatter error:', error.message, '\nSQL:', text);
            throw error;
        }

        if (cmd !== 'SELECT') {
            const combinedChanges = results.reduce((sum, r) => sum + (r.rowCount || 0), 0);
            this._invalidateByTables(this._tablesInSql(text));
            return { rows: [], rowCount: combinedChanges };
        }

        const combinedRows = results.flatMap(r => r.rows);
        const merged = this._mergeRows(text, combinedRows);
        const result = { rows: merged };
        this._cacheSet(cacheKey, result, this._tablesInSql(text));
        return result;
    }

    // ادغام هوشمند نتایج چند شارد: جمع COUNT(*)، یا اعمال دوباره‌ی ORDER BY/LIMIT روی نتایج ترکیب‌شده
    _mergeRows(sql, rows) {
        const countMatch = sql.match(/^\s*SELECT\s+COUNT\(\*\)\s+as\s+(\w+)\s+FROM/i);
        if (countMatch && rows.length) {
            const alias = countMatch[1];
            const total = rows.reduce((sum, r) => sum + (Number(r[alias]) || 0), 0);
            return [{ [alias]: total }];
        }

        // برای پیدا کردن ORDER BY واقعیِ سطح بیرونیِ کوئری (نه ORDER BY داخل یه ساب‌کوئری تو دل SELECT/FROM)،
        // آخرین رخداد «ORDER BY» تو کل متن رو در نظر می‌گیریم - چون ساب‌کوئری‌ها همیشه قبل از تمومِ
        // کوئری میان، پس ORDER BY سطح بیرونی همیشه از همه‌شون بعدتر ظاهر می‌شه. قبلاً اولین رخداد
        // در نظر گرفته می‌شد که با وجود ساب‌کوئری‌های دارای ORDER BY خودشون (مثل اکسپلور)، کل بقیه‌ی
        // متن SQL به اشتباه به‌عنوان ستون‌های مرتب‌سازی پارس می‌شد و ادغام نتایج شاردها رو خراب می‌کرد.
        const orderMatches = [...sql.matchAll(/ORDER BY/gi)];
        if (!orderMatches.length) return rows;
        const lastOrderBy = orderMatches[orderMatches.length - 1];
        const tail = sql.slice(lastOrderBy.index + lastOrderBy[0].length);
        const limitInTail = tail.match(/\bLIMIT\s+(\d+)/i);
        const orderClause = limitInTail ? tail.slice(0, limitInTail.index) : tail;
        const limit = limitInTail ? parseInt(limitInTail[1], 10) : null;

        const sortKeys = orderClause.split(',').map(part => {
            const [, col, dir] = part.trim().match(/([\w.]+)\s*(ASC|DESC)?/i) || [];
            const cleanCol = col ? col.split('.').pop() : null;
            return { col: cleanCol, desc: (dir || '').toUpperCase() === 'DESC' };
        }).filter(k => k.col);

        if (sortKeys.length) {
            rows.sort((a, b) => {
                for (const { col, desc } of sortKeys) {
                    const av = a[col], bv = b[col];
                    if (av === bv) continue;
                    const cmp = av > bv ? 1 : -1;
                    return desc ? -cmp : cmp;
                }
                return 0;
            });
        }

        return limit !== null ? rows.slice(0, limit) : rows;
    }

    _tablesInSql(sql) {
        const tables = new Set();
        const patterns = [/FROM\s+(\w+)/gi, /JOIN\s+(\w+)/gi, /INTO\s+(\w+)/gi, /UPDATE\s+(\w+)/gi];
        for (const re of patterns) {
            let m;
            while ((m = re.exec(sql)) !== null) tables.add(m[1].toLowerCase());
        }
        return [...tables];
    }

    _cacheSet(key, data, tables) {
        this.cache.set(key, { data, timestamp: Date.now(), tables });
        if (this.cache.size > this.cacheMaxEntries) {
            const oldestKey = this.cache.keys().next().value;
            this.cache.delete(oldestKey);
        }
    }

    _invalidateByTables(tables) {
        if (!tables.length) return;
        for (const [key, entry] of this.cache) {
            if (entry.tables && entry.tables.some(t => tables.includes(t))) {
                this.cache.delete(key);
            }
        }
    }

    invalidateCache() { this.cache.clear(); }
    clearCache() { this.cache.clear(); }

    // ============================================
    // فالو/آنفالو - نوشتن دوگانه روی شارد هر دو کاربر
    // ============================================
    async followUser(followerId, followingId) {
        if (followerId === followingId) return { success: false, error: 'نمی‌توانید خودتان را فالو کنید' };

        const shardsInvolved = new Set([this.hashKey(followerId), this.hashKey(followingId)]);
        let alreadyFollowing = false;
        for (const idx of shardsInvolved) {
            const r = await this._exec(idx, `SELECT 1 FROM follows WHERE follower_id = $1 AND following_id = $2`, [followerId, followingId]);
            if (r.rows.length) alreadyFollowing = true;
        }
        if (alreadyFollowing) return { success: true, alreadyFollowing: true };

        for (const idx of shardsInvolved) {
            await this._exec(idx, `
                INSERT INTO follows (follower_id, following_id, created_at) VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (follower_id, following_id) DO NOTHING
            `, [followerId, followingId]);
        }

        const targetShardIdx = this.hashKey(followingId);
        await this._exec(targetShardIdx, `UPDATE channels SET followers_count = followers_count + 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = $1`, [followingId]);

        this._invalidateByTables(['follows', 'channels']);
        return { success: true };
    }

    async unfollowUser(followerId, followingId) {
        const shardsInvolved = new Set([this.hashKey(followerId), this.hashKey(followingId)]);
        let removed = false;
        for (const idx of shardsInvolved) {
            const r = await this._exec(idx, `DELETE FROM follows WHERE follower_id = $1 AND following_id = $2`, [followerId, followingId]);
            if (r.rowCount > 0) removed = true;
        }
        if (removed) {
            const targetShardIdx = this.hashKey(followingId);
            await this._exec(targetShardIdx, `UPDATE channels SET followers_count = GREATEST(followers_count - 1, 0), updated_at = CURRENT_TIMESTAMP WHERE user_id = $1`, [followingId]);
        }
        this._invalidateByTables(['follows', 'channels']);
        return { success: true };
    }

    // مسدود کردن کاربر در چت خصوصی - نوشتن دوگانه مثل فالو
    async blockUser(blockerId, blockedId) {
        const shardsInvolved = new Set([this.hashKey(blockerId), this.hashKey(blockedId)]);
        for (const idx of shardsInvolved) {
            await this._exec(idx, `
                INSERT INTO blocked_users (blocker_id, blocked_id, created_at) VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (blocker_id, blocked_id) DO NOTHING
            `, [blockerId, blockedId]);
        }
        this._invalidateByTables(['blocked_users']);
        return { success: true };
    }

    async unblockUser(blockerId, blockedId) {
        const shardsInvolved = new Set([this.hashKey(blockerId), this.hashKey(blockedId)]);
        for (const idx of shardsInvolved) {
            await this._exec(idx, `DELETE FROM blocked_users WHERE blocker_id = $1 AND blocked_id = $2`, [blockerId, blockedId]);
        }
        this._invalidateByTables(['blocked_users']);
        return { success: true };
    }

    async isBlocked(userA, userB) {
        const idx = this.hashKey(userA);
        const r = await this._exec(idx, `
            SELECT 1 FROM blocked_users
            WHERE (blocker_id = $1 AND blocked_id = $2) OR (blocker_id = $3 AND blocked_id = $4)
            LIMIT 1
        `, [userA, userB, userB, userA]);
        return r.rows.length > 0;
    }

    // لایک/آنلایک یک پست - شارد از روی دایرکتوری postId پیدا می‌شه، همه در یه تراکنش واقعی
    async toggleLike(postId, userId) {
        const shardIndex = this.resolveShardIndex(postId);
        let liked, likes;

        await this._withTransaction(shardIndex, async (client) => {
            const existing = await client.query(`SELECT 1 FROM post_likes WHERE post_id = $1 AND user_id = $2`, [postId, userId]);
            if (existing.rows.length) {
                await client.query(`DELETE FROM post_likes WHERE post_id = $1 AND user_id = $2`, [postId, userId]);
                await client.query(`UPDATE posts SET likes = GREATEST(likes - 1, 0), updated_at = CURRENT_TIMESTAMP WHERE id = $1`, [postId]);
                liked = false;
            } else {
                await client.query(`INSERT INTO post_likes (post_id, user_id, created_at) VALUES ($1, $2, CURRENT_TIMESTAMP)`, [postId, userId]);
                await client.query(`UPDATE posts SET likes = likes + 1, updated_at = CURRENT_TIMESTAMP WHERE id = $1`, [postId]);
                liked = true;
            }
            const p = await client.query(`SELECT likes FROM posts WHERE id = $1`, [postId]);
            likes = p.rows[0]?.likes || 0;
        });

        this._invalidateByTables(['posts', 'post_likes']);
        return { success: true, liked, likes };
    }

    // ============================================
    // نگهداری/آمار
    // ============================================
    async getStats() {
        const stats = { shardCount: this.shardCount, perShard: [] };
        for (let i = 0; i < this.shardCount; i++) {
            const shardStats = {};
            try {
                const tables = await this._exec(i, `
                    SELECT table_name FROM information_schema.tables WHERE table_schema = $1
                `, [`shard_${i}`]);
                for (const t of tables.rows) {
                    const count = await this._exec(i, `SELECT COUNT(*) as count FROM ${t.table_name}`);
                    shardStats[t.table_name] = Number(count.rows[0]?.count || 0);
                }
            } catch (error) {
                console.error(`Stats error (shard ${i}):`, error.message);
            }
            stats.perShard.push(shardStats);
        }
        return stats;
    }

    async close() {
        await this.pool.end();
    }
}

module.exports = DatabaseManager;
