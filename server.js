const express = require('express');
const http = require('http');
const socketIO = require('socket.io');
const cors = require('cors');
const bodyParser = require('body-parser');
const crypto = require('crypto');
const compression = require('compression');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const DatabaseManager = require('./database');
const IntelligentAssistant = require('./assistant_logic');

const app = express();
app.set('trust proxy', 1);
const server = http.createServer(app);
const io = socketIO(server, {
    cors: { origin: "*", methods: ["GET", "POST"] },
    pingTimeout: 60000,
    pingInterval: 25000,
    maxHttpBufferSize: 1e8
});
const db = new DatabaseManager();

// ============================================
// سکرت نشست
// ============================================
const sessionSecretPath = path.join(__dirname, '.session_secret');
let SESSION_SECRET;
try {
    if (fs.existsSync(sessionSecretPath)) {
        SESSION_SECRET = fs.readFileSync(sessionSecretPath, 'utf8').trim();
    }
    if (!SESSION_SECRET) {
        SESSION_SECRET = crypto.randomBytes(48).toString('hex');
        fs.writeFileSync(sessionSecretPath, SESSION_SECRET, { mode: 0o600 });
    }
} catch (e) {
    console.error('⚠️ خطا در بارگذاری سکرت نشست:', e.message);
    SESSION_SECRET = crypto.randomBytes(48).toString('hex');
}

const TOKEN_TTL_MS = 30 * 24 * 60 * 60 * 1000;

function signToken(userId) {
    const expires = Date.now() + TOKEN_TTL_MS;
    const payload = `${userId}.${expires}`;
    const sig = crypto.createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');
    return Buffer.from(`${payload}.${sig}`).toString('base64url');
}

function verifyToken(token) {
    try {
        const decoded = Buffer.from(String(token), 'base64url').toString('utf8');
        const parts = decoded.split('.');
        if (parts.length !== 3) return null;
        const [userId, expires, sig] = parts;
        const payload = `${userId}.${expires}`;
        const expectedSig = crypto.createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');
        const a = Buffer.from(sig, 'hex');
        const b = Buffer.from(expectedSig, 'hex');
        if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
        if (Date.now() > Number(expires)) return null;
        return userId;
    } catch (e) {
        return null;
    }
}

// ============================================
// امنیت و بهینه‌سازی
// ============================================
app.use(helmet({ contentSecurityPolicy: false, crossOriginEmbedderPolicy: false }));
app.use(compression());
app.use(cors());

const limiter = rateLimit({
    windowMs: 60 * 1000,
    max: 200,
    message: { error: 'تعداد درخواست‌ها بیش از حد مجاز است' }
});
app.use('/api/', limiter);

app.use(bodyParser.json({ limit: '3mb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '3mb' }));
app.use(express.static(__dirname, { maxAge: '1d', etag: true }));

// ============================================
// آپلود فایل
// ============================================
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir, { recursive: true });

const upload = multer({
    storage: multer.diskStorage({
        destination: (req, file, cb) => cb(null, uploadsDir),
        filename: (req, file, cb) => {
            const ext = path.extname(file.originalname || '').toLowerCase().replace(/[^a-z0-9.]/g, '');
            cb(null, `${Date.now()}_${crypto.randomBytes(8).toString('hex')}${ext}`);
        }
    }),
    limits: { fileSize: parseInt(process.env.MAX_UPLOAD_MB || '300', 10) * 1024 * 1024, files: 1 },
    fileFilter: (req, file, cb) => {
        const allowed = /^(image\/(jpeg|png|gif|webp)|video\/(mp4|webm|quicktime|ogg))$/;
        if (allowed.test(file.mimetype)) return cb(null, true);
        cb(new Error('نوع فایل مجاز نیست (فقط عکس یا ویدیو)'));
    }
});

const uploadLimiter = rateLimit({
    windowMs: 10 * 60 * 1000,
    max: 30,
    message: { success: false, error: 'تعداد آپلودها بیش از حد مجاز است، کمی صبر کن' }
});

app.use('/uploads', express.static(uploadsDir, { maxAge: '7d', etag: true }));

app.post('/api/upload', uploadLimiter, (req, res) => {
    upload.single('file')(req, res, (err) => {
        if (err instanceof multer.MulterError) {
            if (err.code === 'LIMIT_FILE_SIZE') {
                return res.status(413).json({ success: false, error: `حجم فایل بیشتر از حد مجاز (${process.env.MAX_UPLOAD_MB || 300} مگابایت) است` });
            }
            return res.status(400).json({ success: false, error: 'خطا در آپلود فایل: ' + err.message });
        } else if (err) {
            return res.status(400).json({ success: false, error: err.message || 'خطا در آپلود فایل' });
        }
        if (!req.file) {
            return res.status(400).json({ success: false, error: 'فایلی ارسال نشده' });
        }
        const mediaType = req.file.mimetype.startsWith('video/') ? 'video' : 'image';
        res.json({ success: true, url: `/uploads/${req.file.filename}`, mediaType, size: req.file.size });
    });
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok', pid: process.pid, uptime: process.uptime(), memory: process.memoryUsage().rss, shards: db.shardCount });
});

// ============================================
// بررسی ادمین
// ============================================
function isAdmin(req, res, next) {
    const authHeader = req.headers.authorization || '';
    const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : (req.headers['x-auth-token'] || '');
    const userId = verifyToken(token);
    if (!userId) {
        return res.status(401).json({ error: 'ورود الزامی است' });
    }
    db.query(userId, `SELECT role FROM users WHERE id = $1`, [userId]).then(r => {
        if (r.rows[0] && r.rows[0].role === 'admin') {
            req.currentUserId = userId;
            return next();
        }
        res.status(403).json({ error: 'دسترسی غیرمجاز' });
    }).catch(() => res.status(500).json({ error: 'خطای داخلی' }));
}

// ============================================
// ثبت‌نام ساده
// ============================================
app.post('/api/user/register', async (req, res) => {
    try {
        const { name, avatar } = req.body;
        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'نام الزامی است' });
        }
        let id;
        const nameLower = name.trim().toLowerCase();
        if (nameLower === 'milad' || nameLower === 'مدیر سیستم' || nameLower === 'admin') {
            id = 'admin_milad';
        } else {
            id = 'user_' + crypto.randomBytes(8).toString('hex');
        }
        const channelId = 'channel_' + id;
        const check = await db.query(id, `SELECT id FROM users WHERE id = $1`, [id]);
        if (check.rows.length === 0) {
            await db.query(id, `
                INSERT INTO users (id, name, avatar, role, is_verified, score, created_at) 
                VALUES ($1, $2, $3, $4, 1, $5, CURRENT_TIMESTAMP)
            `, [id, name.trim(), avatar || null, id === 'admin_milad' ? 'admin' : 'user', id === 'admin_milad' ? 999999 : 0]);
            await db.query(id, `
                INSERT INTO channels (id, user_id, name, boost_level, created_at) 
                VALUES ($1, $2, $3, 'normal', CURRENT_TIMESTAMP)
            `, [channelId, id, name.trim() + ' - کانال']);
        }
        const u = await db.query(id, `SELECT id, name, avatar, score, role FROM users WHERE id = $1`, [id]);
        res.json({ success: true, user: u.rows[0] });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// کپچای پازل
// ============================================
const usedCaptchaPassTokens = new Set();
const CAPTCHA_TOLERANCE_PX = 6;
const CAPTCHA_MIN_SOLVE_MS = 350;

function signCaptchaChallenge(target, pieceY) {
    const issuedAt = Date.now();
    const expires = issuedAt + 2 * 60 * 1000;
    const payload = `${target}.${pieceY}.${issuedAt}.${expires}`;
    const sig = crypto.createHmac('sha256', SESSION_SECRET).update('captcha:' + payload).digest('hex');
    return Buffer.from(`${payload}.${sig}`).toString('base64url');
}

function verifyCaptchaChallenge(token, submittedPosition) {
    try {
        const decoded = Buffer.from(String(token), 'base64url').toString('utf8');
        const parts = decoded.split('.');
        if (parts.length !== 5) return false;
        const [target, pieceY, issuedAt, expires, sig] = parts;
        const payload = `${target}.${pieceY}.${issuedAt}.${expires}`;
        const expectedSig = crypto.createHmac('sha256', SESSION_SECRET).update('captcha:' + payload).digest('hex');
        const a = Buffer.from(sig, 'hex'), b = Buffer.from(expectedSig, 'hex');
        if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return false;
        if (Date.now() > Number(expires)) return false;
        if (Date.now() - Number(issuedAt) < CAPTCHA_MIN_SOLVE_MS) return false;
        if (Math.abs(Number(target) - Number(submittedPosition)) > CAPTCHA_TOLERANCE_PX) return false;
        return true;
    } catch (e) { return false; }
}

function issueCaptchaPassToken() {
    const expires = Date.now() + 5 * 60 * 1000;
    const nonce = crypto.randomBytes(8).toString('hex');
    const payload = `captcha_pass.${expires}.${nonce}`;
    const sig = crypto.createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');
    return Buffer.from(`${payload}.${sig}`).toString('base64url');
}

function verifyCaptchaPassToken(passToken) {
    if (!passToken || usedCaptchaPassTokens.has(passToken)) return false;
    try {
        const decoded = Buffer.from(String(passToken), 'base64url').toString('utf8');
        const parts = decoded.split('.');
        if (parts.length !== 4 || parts[0] !== 'captcha_pass') return false;
        const [marker, expires, nonce, sig] = parts;
        const payload = `${marker}.${expires}.${nonce}`;
        const expectedSig = crypto.createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');
        const a = Buffer.from(sig, 'hex'), b = Buffer.from(expectedSig, 'hex');
        if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return false;
        if (Date.now() > Number(expires)) return false;
        usedCaptchaPassTokens.add(passToken);
        setTimeout(() => usedCaptchaPassTokens.delete(passToken), 6 * 60 * 1000);
        return true;
    } catch (e) { return false; }
}

app.get('/api/captcha/challenge', (req, res) => {
    const canvasWidth = 300, canvasHeight = 150;
    const target = 60 + Math.floor(Math.random() * (canvasWidth - 100));
    const pieceY = 30 + Math.floor(Math.random() * (canvasHeight - 60));
    const token = signCaptchaChallenge(target, pieceY);
    res.json({ token, target, pieceY, canvasWidth, canvasHeight });
});

app.post('/api/captcha/verify', (req, res) => {
    const { token, position } = req.body || {};
    if (typeof position !== 'number' || !verifyCaptchaChallenge(token, position)) {
        return res.status(400).json({ success: false, error: 'پازل درست حل نشد، دوباره تلاش کن' });
    }
    res.json({ success: true, passToken: issueCaptchaPassToken() });
});

// ============================================
// ارسال ایمیل
// ============================================
let mailTransporter = null;
if (process.env.SMTP_HOST && process.env.SMTP_USER && process.env.SMTP_PASS) {
    try {
        const nodemailer = require('nodemailer');
        mailTransporter = nodemailer.createTransport({
            host: process.env.SMTP_HOST,
            port: parseInt(process.env.SMTP_PORT || '587', 10),
            secure: process.env.SMTP_PORT === '465',
            auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS }
        });
        console.log('✅ SMTP برای ارسال ایمیل واقعی تنظیم شد');
    } catch (e) {
        console.error('⚠️ nodemailer خطا:', e.message);
    }
} else {
    console.log('ℹ️ SMTP تنظیم نشده - ایمیل‌ها فقط لاگ می‌شن');
}

async function sendEmail(to, subject, text) {
    if (mailTransporter) {
        try {
            await mailTransporter.sendMail({ from: process.env.SMTP_FROM || process.env.SMTP_USER, to, subject, text });
            return true;
        } catch (e) {
            console.error('خطای ارسال ایمیل:', e.message);
            return false;
        }
    }
    console.log(`📧 [ایمیل شبیه‌سازی‌شده] به: ${to} | موضوع: ${subject}\n${text}`);
    return true;
}

const authLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 20,
    message: { success: false, error: 'تعداد تلاش‌ها بیش از حد مجاز است، کمی صبر کن' }
});

// ============================================
// ثبت‌نام با کپچا
// ============================================
app.post('/api/auth/register', authLimiter, async (req, res) => {
    try {
        const { username, email, password, name, captchaPassToken } = req.body || {};
        if (!verifyCaptchaPassToken(captchaPassToken)) {
            return res.status(400).json({ success: false, error: 'لطفاً پازل امنیتی را دوباره حل کن' });
        }
        const uname = String(username || '').trim();
        const mail = String(email || '').trim().toLowerCase();
        const pass = String(password || '');
        const displayName = String(name || uname).trim();

        if (!uname || uname.length < 3) {
            return res.status(400).json({ success: false, error: 'نام کاربری باید حداقل ۳ کاراکتر باشد' });
        }
        if (!/^[a-zA-Z0-9_.]+$/.test(uname)) {
            return res.status(400).json({ success: false, error: 'نام کاربری فقط می‌تواند شامل حروف انگلیسی، عدد، نقطه و آندرلاین باشد' });
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) {
            return res.status(400).json({ success: false, error: 'ایمیل معتبر نیست' });
        }
        if (pass.length < 8) {
            return res.status(400).json({ success: false, error: 'رمز عبور باید حداقل ۸ کاراکتر باشد' });
        }

        const existing = await db.findUserByUsernameOrEmail(uname) || await db.findUserByUsernameOrEmail(mail);
        if (existing) {
            return res.status(409).json({ success: false, error: 'این نام کاربری یا ایمیل قبلاً ثبت شده است' });
        }

        const id = 'user_' + crypto.randomBytes(8).toString('hex');
        const channelId = 'channel_' + id;
        const passwordHash = db.hashPassword(pass);

        await db.query(id, `
            INSERT INTO users (id, name, username, email, password_hash, role, is_verified, score, created_at)
            VALUES ($1, $2, $3, $4, $5, 'user', 0, 0, CURRENT_TIMESTAMP)
        `, [id, displayName, uname, mail, passwordHash]);

        await db.query(id, `
            INSERT INTO channels (id, user_id, name, boost_level, created_at)
            VALUES ($1, $2, $3, 'normal', CURRENT_TIMESTAMP)
        `, [channelId, id, displayName + ' - کانال']);

        const token = signToken(id);
        const u = await db.query(id, `SELECT id, name, username, email, avatar, score, role FROM users WHERE id = $1`, [id]);
        res.json({ success: true, token, user: u.rows[0] });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// ورود با کپچا
// ============================================
app.post('/api/auth/login', authLimiter, async (req, res) => {
    try {
        const { identifier, password, captchaPassToken } = req.body || {};
        if (!verifyCaptchaPassToken(captchaPassToken)) {
            return res.status(400).json({ success: false, error: 'لطفاً پازل امنیتی را دوباره حل کن' });
        }
        if (!identifier || !password) {
            return res.status(400).json({ success: false, error: 'نام کاربری/ایمیل و رمز عبور الزامی است' });
        }

        const row = await db.findUserByUsernameOrEmail(identifier);
        if (!row || !row.password_hash || !db.verifyPassword(password, row.password_hash)) {
            return res.status(401).json({ success: false, error: 'نام کاربری/ایمیل یا رمز عبور اشتباه است' });
        }
        if (row.restricted) {
            return res.status(403).json({ success: false, error: 'حساب کاربری شما محدود شده است' });
        }

        const token = signToken(row.id);
        res.json({ success: true, token, user: { id: row.id, name: row.name, username: row.username, email: row.email, avatar: row.avatar, score: row.score, role: row.role } });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// بازیابی رمز عبور
// ============================================
app.post('/api/auth/forgot-password', authLimiter, async (req, res) => {
    try {
        const { identifier } = req.body || {};
        if (!identifier) {
            return res.status(400).json({ success: false, error: 'ایمیل یا نام کاربری را وارد کن' });
        }
        const user = await db.findUserByUsernameOrEmail(identifier);
        if (!user || !user.email) {
            return res.json({ success: true, message: 'اگر این حساب وجود داشته باشد، کد بازیابی ارسال شد' });
        }
        const code = String(Math.floor(100000 + Math.random() * 900000));
        const codeHash = crypto.createHash('sha256').update(code).digest('hex');
        const id = crypto.randomUUID();
        await db.query(user.id, `
            INSERT INTO password_resets (id, user_id, code_hash, used, created_at, expires_at)
            VALUES ($1, $2, $3, 0, CURRENT_TIMESTAMP, NOW() + INTERVAL '15 minutes')
        `, [id, user.id, codeHash]);
        await sendEmail(user.email, 'بازیابی رمز عبور یارِ من', `کد بازیابی رمز عبورت: ${code}\nاین کد تا ۱۵ دقیقه دیگه معتبره.`);
        res.json({ success: true, message: 'اگر این حساب وجود داشته باشد، کد بازیابی ارسال شد' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/auth/reset-password', authLimiter, async (req, res) => {
    try {
        const { identifier, code, newPassword } = req.body || {};
        const pass = String(newPassword || '');
        if (!identifier || !code || pass.length < 8) {
            return res.status(400).json({ success: false, error: 'کد و رمز جدید (حداقل ۸ کاراکتر) الزامی است' });
        }
        const user = await db.findUserByUsernameOrEmail(identifier);
        if (!user) {
            return res.status(400).json({ success: false, error: 'کد نامعتبر یا منقضی‌شده است' });
        }
        const codeHash = crypto.createHash('sha256').update(String(code)).digest('hex');
        const resetRow = await db.query(user.id, `
            SELECT id FROM password_resets
            WHERE user_id = $1 AND code_hash = $2 AND used = 0 AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at DESC LIMIT 1
        `, [user.id, codeHash]);
        if (!resetRow.rows[0]) {
            return res.status(400).json({ success: false, error: 'کد نامعتبر یا منقضی‌شده است' });
        }
        const newHash = db.hashPassword(pass);
        await db.query(user.id, `UPDATE users SET password_hash = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2`, [newHash, user.id]);
        await db.query(user.id, `UPDATE password_resets SET used = 1 WHERE id = $1`, [resetRow.rows[0].id]);
        res.json({ success: true, message: 'رمز عبور با موفقیت تغییر کرد، حالا وارد شو' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// نشست پایدار - ذخیره و بازیابی
// ============================================
app.post('/api/auth/session', async (req, res) => {
    try {
        const { userId, deviceLabel } = req.body;
        if (!userId) {
            return res.status(400).json({ success: false, error: 'شناسه کاربر الزامی است' });
        }
        const token = crypto.randomBytes(32).toString('hex');
        const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
        await db.query(userId, `
            INSERT INTO user_sessions (token_hash, user_id, device_label, created_at, expires_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days')
            ON CONFLICT (token_hash) DO UPDATE SET last_seen_at = CURRENT_TIMESTAMP
        `, [tokenHash, userId, deviceLabel || req.headers['user-agent'] || 'unknown']);
        res.json({ success: true, token });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/auth/restore-session', async (req, res) => {
    try {
        const { token } = req.body;
        if (!token) {
            return res.status(400).json({ success: false, error: 'توکن الزامی است' });
        }
        const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
        const result = await db.query(null, `
            SELECT user_id FROM user_sessions 
            WHERE token_hash = $1 AND expires_at > CURRENT_TIMESTAMP
        `, [tokenHash]);
        if (!result.rows[0]) {
            return res.status(401).json({ success: false, error: 'نشست نامعتبر یا منقضی شده' });
        }
        const userId = result.rows[0].user_id;
        await db.query(userId, `
            UPDATE user_sessions SET last_seen_at = CURRENT_TIMESTAMP
            WHERE token_hash = $1
        `, [tokenHash]);
        const user = await db.query(userId, `
            SELECT id, name, username, email, avatar, score, role
            FROM users WHERE id = $1
        `, [userId]);
        res.json({ success: true, user: user.rows[0], token });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// کاربر
// ============================================
app.get('/api/user/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const u = await db.query(id, `SELECT id, name, avatar, score, bio, role, is_verified, created_at FROM users WHERE id = $1`, [id]);
        if (u.rows.length === 0) return res.status(404).json({ error: 'کاربر یافت نشد' });
        const ch = await db.query(id, `SELECT followers_count FROM channels WHERE user_id = $1`, [id]);
        res.json({ ...u.rows[0], followers: ch.rows[0]?.followers_count || 0 });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/user/avatar', async (req, res) => {
    try {
        const { userId, avatar } = req.body;
        await db.query(userId, `UPDATE users SET avatar = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2`, [avatar, userId]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/user/bio', async (req, res) => {
    try {
        const { userId, bio } = req.body;
        await db.query(userId, `UPDATE users SET bio = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2`, [bio, userId]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// پروفایل
// ============================================
const profileCache = new Map();
const PROFILE_CACHE_TTL = 30000;

app.get('/api/profile/:userId', async (req, res) => {
    try {
        const { userId } = req.params;
        const { viewerId } = req.query;
        const cacheKey = `${userId}_${viewerId}`;
        const cached = profileCache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp) < PROFILE_CACHE_TTL) {
            return res.json(cached.data);
        }
        const u = await db.query(userId, `SELECT id, name, avatar, bio, score, is_verified, created_at FROM users WHERE id = $1`, [userId]);
        if (u.rows.length === 0) return res.status(404).json({ error: 'کاربر یافت نشد' });
        const ch = await db.query(userId, `SELECT * FROM channels WHERE user_id = $1`, [userId]);
        const channel = ch.rows[0];
        const posts = await db.query(userId, `
            SELECT p.*, c.name as channel_name
            FROM posts p JOIN channels c ON p.channel_id = c.id
            WHERE c.user_id = $1 AND p.is_published = 1
            ORDER BY p.created_at DESC LIMIT 30
        `, [userId]);
        let isFollowing = false;
        if (viewerId && viewerId !== userId) {
            const f = await db.query(userId, `SELECT 1 FROM follows WHERE follower_id = $1 AND following_id = $2`, [viewerId, userId]);
            isFollowing = f.rows.length > 0;
        }
        const data = { user: u.rows[0], channel, posts: posts.rows, isFollowing };
        profileCache.set(cacheKey, { data, timestamp: Date.now() });
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// فالو
// ============================================
app.post('/api/follow', async (req, res) => {
    try {
        const { followerId, followingId } = req.body;
        if (!followerId || !followingId) {
            return res.status(400).json({ success: false, error: 'اطلاعات ناقص است' });
        }
        const result = await db.followUser(followerId, followingId);
        if (result.success && !result.alreadyFollowing) {
            const assistant = new IntelligentAssistant(followerId, db);
            await assistant.updateUserActivity('follow');
            profileCache.clear();
        }
        res.json(result);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/unfollow', async (req, res) => {
    try {
        const { followerId, followingId } = req.body;
        await db.unfollowUser(followerId, followingId);
        profileCache.clear();
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// استوری
// ============================================
app.post('/api/stories/create', async (req, res) => {
    try {
        const { userId, mediaUrl, mediaType, caption, bgColor, textColor } = req.body;
        if (!userId) {
            return res.status(400).json({ success: false, error: 'شناسه کاربر الزامی است' });
        }
        if (!mediaUrl && !(caption && caption.trim())) {
            return res.status(400).json({ success: false, error: 'استوری باید عکس/ویدیو یا متن داشته باشد' });
        }
        const userRow = await db.query(userId, `SELECT role, restricted FROM users WHERE id = $1`, [userId]);
        const u = userRow.rows[0];
        if (!u) return res.status(404).json({ success: false, error: 'کاربر پیدا نشد' });
        if (u.role === 'banned') return res.status(403).json({ success: false, error: 'حساب شما مسدود شده است' });
        if (u.restricted) return res.status(403).json({ success: false, error: 'حساب شما محدود شده است' });
        const storyId = crypto.randomUUID();
        const type = mediaUrl ? (mediaType === 'video' ? 'video' : 'image') : 'text';
        await db.query(userId, `
            INSERT INTO stories (id, user_id, media_url, media_type, caption, bg_color, text_color, views_count, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 0, CURRENT_TIMESTAMP, NOW() + INTERVAL '24 hours')
        `, [storyId, userId, mediaUrl || null, type, (caption || '').trim().substring(0, 300) || null, bgColor || '#6c5ce7', textColor || '#ffffff']);
        res.json({ success: true, storyId });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/stories/feed/:userId', async (req, res) => {
    try {
        const { userId } = req.params;
        const followingRes = await db.query(userId, `SELECT following_id FROM follows WHERE follower_id = $1`, [userId]);
        const authorIds = [userId, ...followingRes.rows.map(r => r.following_id)];
        const groups = [];
        for (const authorId of authorIds) {
            try {
                const r = await db.query(authorId, `
                    SELECT s.*, u.name, u.avatar
                    FROM stories s JOIN users u ON u.id = s.user_id
                    WHERE s.user_id = $1 AND s.expires_at > CURRENT_TIMESTAMP
                    ORDER BY s.created_at ASC
                `, [authorId]);
                if (r.rows.length) {
                    groups.push({ user_id: authorId, name: r.rows[0].name, avatar: r.rows[0].avatar, stories: r.rows.map(({ name, avatar, ...s }) => s) });
                }
            } catch (e) {}
        }
        groups.sort((a, b) => (a.user_id === userId ? -1 : b.user_id === userId ? 1 : 0));
        res.json(groups);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/stories/:storyId/view', async (req, res) => {
    try {
        const { storyId } = req.params;
        const { viewerId, ownerId } = req.body;
        if (!viewerId || !ownerId) {
            return res.status(400).json({ success: false, error: 'اطلاعات ناقص است' });
        }
        if (viewerId === ownerId) return res.json({ success: true });
        const inserted = await db.query(ownerId, `
            INSERT INTO story_views (id, story_id, viewer_id, viewed_at)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            ON CONFLICT (story_id, viewer_id) DO NOTHING
        `, [crypto.randomUUID(), storyId, viewerId]);
        if (inserted.rowCount > 0) {
            await db.query(ownerId, `UPDATE stories SET views_count = views_count + 1 WHERE id = $1`, [storyId]);
        }
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/stories/:storyId/viewers', async (req, res) => {
    try {
        const { storyId } = req.params;
        const { ownerId } = req.query;
        if (!ownerId) return res.status(400).json({ error: 'شناسه صاحب استوری الزامی است' });
        const story = await db.query(ownerId, `SELECT user_id FROM stories WHERE id = $1`, [storyId]);
        if (!story.rows[0] || story.rows[0].user_id !== ownerId) {
            return res.status(403).json({ error: 'دسترسی غیرمجاز' });
        }
        const views = await db.query(ownerId, `
            SELECT viewer_id, viewed_at FROM story_views WHERE story_id = $1 ORDER BY viewed_at DESC
        `, [storyId]);
        const viewers = [];
        for (const v of views.rows) {
            try {
                const u = await db.query(v.viewer_id, `SELECT name, avatar FROM users WHERE id = $1`, [v.viewer_id]);
                viewers.push({ user_id: v.viewer_id, name: u.rows[0]?.name || 'کاربر', avatar: u.rows[0]?.avatar, viewed_at: v.viewed_at });
            } catch (e) {}
        }
        res.json(viewers);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.delete('/api/stories/:storyId', async (req, res) => {
    try {
        const { storyId } = req.params;
        const { userId } = req.body;
        if (!userId) return res.status(400).json({ success: false, error: 'شناسه کاربر الزامی است' });
        const result = await db.query(userId, `DELETE FROM stories WHERE id = $1 AND user_id = $2`, [storyId, userId]);
        if (result.rowCount === 0) {
            return res.status(404).json({ success: false, error: 'استوری پیدا نشد یا مالک آن نیستید' });
        }
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// پست
// ============================================
app.post('/api/post/create', async (req, res) => {
    try {
        const { userId, content, mediaUrl, mediaType } = req.body;
        if (!content || !content.trim()) {
            return res.status(400).json({ success: false, error: 'متن پست الزامی است' });
        }
        const userRow = await db.query(userId, `SELECT role, restricted FROM users WHERE id = $1`, [userId]);
        const u = userRow.rows[0];
        if (u?.role === 'banned') {
            return res.status(403).json({ success: false, error: 'حساب شما مسدود شده است' });
        }
        if (u?.restricted) {
            return res.status(403).json({ success: false, error: 'حساب شما محدود شده و امکان انتشار پست ندارید' });
        }
        const channel = await db.query(userId, `SELECT id FROM channels WHERE user_id = $1`, [userId]);
        if (channel.rows.length === 0) {
            return res.status(404).json({ success: false, error: 'کانالی یافت نشد' });
        }
        const postId = crypto.randomUUID();
        const type = mediaType || 'none';
        
        // استخراج هشتگ‌ها
        const hashtags = (content.match(/#[\w\u0600-\u06FF]+/g) || []).map(t => t.slice(1).toLowerCase());
        
        await db.query(userId, `
            INSERT INTO posts (id, channel_id, content, media_url, media_type, is_published, published_at, created_at)
            VALUES ($1, $2, $3, $4, $5, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        `, [postId, channel.rows[0].id, content.trim(), mediaUrl || null, type]);

        // ذخیره هشتگ‌ها
        if (hashtags.length) {
            for (const tag of hashtags) {
                await db.query(userId, `
                    INSERT INTO post_hashtags (post_id, tag) VALUES ($1, $2)
                    ON CONFLICT (post_id, tag) DO NOTHING
                `, [postId, tag]);
            }
        }

        await db.query(userId, `UPDATE channels SET posts_count = posts_count + 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = $1`, [userId]);

        const assistant = new IntelligentAssistant(userId, db);
        await assistant.updateUserActivity('post');
        const boost = await assistant.boostVisibility();

        profileCache.clear();
        exploreCache.clear();

        res.json({ success: true, postId, boost, hashtags });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// جستجوی هشتگ
// ============================================
app.get('/api/hashtag/:tag', async (req, res) => {
    try {
        const { tag } = req.params;
        const { limit = 50 } = req.query;
        const result = await db.query(null, `
            SELECT p.*, u.name as user_name, u.avatar as user_avatar
            FROM post_hashtags h
            JOIN posts p ON h.post_id = p.id
            JOIN channels c ON p.channel_id = c.id
            JOIN users u ON c.user_id = u.id
            WHERE h.tag = $1 AND p.is_published = 1
            ORDER BY p.created_at DESC
            LIMIT $2
        `, [tag.toLowerCase(), parseInt(limit)]);
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// هشتگ‌های داغ (ترند)
// ============================================
app.get('/api/trending-hashtags', async (req, res) => {
    try {
        const result = await db.query(null, `
            SELECT tag, COUNT(*) as count
            FROM post_hashtags
            GROUP BY tag
            ORDER BY count DESC
            LIMIT 20
        `);
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// ذخیره پست (Save Post)
// ============================================
app.post('/api/post/:postId/save', async (req, res) => {
    try {
        const { postId } = req.params;
        const { userId } = req.body;
        if (!userId) {
            return res.status(400).json({ success: false, error: 'شناسه کاربر الزامی است' });
        }
        const existing = await db.query(userId, `
            SELECT 1 FROM post_saves WHERE post_id = $1 AND user_id = $2
        `, [postId, userId]);
        if (existing.rows.length) {
            await db.query(userId, `
                DELETE FROM post_saves WHERE post_id = $1 AND user_id = $2
            `, [postId, userId]);
            return res.json({ success: true, saved: false });
        }
        await db.query(userId, `
            INSERT INTO post_saves (post_id, user_id) VALUES ($1, $2)
        `, [postId, userId]);
        res.json({ success: true, saved: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// دریافت پست‌های ذخیره‌شده
// ============================================
app.get('/api/user/:userId/saved-posts', async (req, res) => {
    try {
        const { userId } = req.params;
        const { limit = 50, offset = 0 } = req.query;
        const result = await db.query(userId, `
            SELECT p.*, u.name as user_name, u.avatar as user_avatar
            FROM post_saves s
            JOIN posts p ON s.post_id = p.id
            JOIN channels c ON p.channel_id = c.id
            JOIN users u ON c.user_id = u.id
            WHERE s.user_id = $1 AND p.is_published = 1
            ORDER BY s.created_at DESC
            LIMIT $2 OFFSET $3
        `, [userId, parseInt(limit), parseInt(offset)]);
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// حذف پست
// ============================================
app.post('/api/post/:postId/delete', async (req, res) => {
    try {
        const { postId } = req.params;
        const { userId } = req.body;
        if (!userId) return res.status(400).json({ success: false, error: 'شناسه کاربر الزامی است' });
        const channel = await db.query(userId, `SELECT id FROM channels WHERE user_id = $1`, [userId]);
        if (!channel.rows[0]) return res.status(404).json({ success: false, error: 'کانالی یافت نشد' });
        const result = await db.query(userId, `DELETE FROM posts WHERE id = $1 AND channel_id = $2`, [postId, channel.rows[0].id]);
        if (result.rowCount === 0) {
            return res.status(403).json({ success: false, error: 'این پست مال شما نیست یا قبلاً حذف شده' });
        }
        await db.query(userId, `UPDATE channels SET posts_count = MAX(posts_count - 1, 0), updated_at = CURRENT_TIMESTAMP WHERE user_id = $1`, [userId]);
        profileCache.clear();
        exploreCache.clear();
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/post/:postId/view', async (req, res) => {
    try {
        const { postId } = req.params;
        await db.query(postId, `UPDATE posts SET views = views + 1 WHERE id = $1`, [postId]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// لایک
// ============================================
app.post('/api/post/:postId/like', async (req, res) => {
    try {
        const { postId } = req.params;
        const { userId } = req.body;
        if (!userId) return res.status(400).json({ success: false, error: 'کاربر نامعتبر' });
        const result = await db.toggleLike(postId, userId);
        if (result.liked) {
            const assistant = new IntelligentAssistant(userId, db);
            await assistant.updateUserActivity('like');
        }
        profileCache.clear();
        exploreCache.clear();
        res.json(result);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// کامنت
// ============================================
app.post('/api/post/:postId/comment', async (req, res) => {
    try {
        const { postId } = req.params;
        const { userId, text } = req.body;
        if (!text || !text.trim()) {
            return res.status(400).json({ success: false, error: 'متن کامنت الزامی است' });
        }
        const u = await db.query(userId, `SELECT name, avatar FROM users WHERE id = $1`, [userId]);
        const userName = u.rows[0]?.name || 'کاربر';
        const userAvatar = u.rows[0]?.avatar || null;
        const id = crypto.randomUUID();
        await db.query(postId, `
            INSERT INTO post_comments (id, post_id, user_id, user_name, user_avatar, text, created_at) 
            VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
        `, [id, postId, userId, userName, userAvatar, text.trim()]);
        await db.query(postId, `UPDATE posts SET comments = comments + 1, updated_at = CURRENT_TIMESTAMP WHERE id = $1`, [postId]);
        const assistant = new IntelligentAssistant(userId, db);
        await assistant.updateUserActivity('comment');
        profileCache.clear();
        exploreCache.clear();
        res.json({ success: true, comment: { id, userId, text: text.trim(), name: userName, avatar: userAvatar } });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/post/:postId/comments', async (req, res) => {
    try {
        const { postId } = req.params;
        const result = await db.query(postId, `
            SELECT id, user_id, user_name AS name, user_avatar AS avatar, text, created_at
            FROM post_comments
            WHERE post_id = $1 ORDER BY created_at ASC
        `, [postId]);
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// دستیار
// ============================================
app.post('/api/assistant/train', async (req, res) => {
    try {
        const { userId, question, answer } = req.body;
        const id = crypto.randomUUID();
        await db.query(userId, `
            INSERT INTO assistant_training (id, user_id, type, question, answer, created_at)
            VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
        `, [id, userId, 'qa', question, answer]);
        const assistant = new IntelligentAssistant(userId, db);
        await assistant.updateUserActivity('train');
        const boost = await assistant.boostVisibility();
        res.json({ success: true, message: 'آموزش با موفقیت ثبت شد', boost });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/assistant/keyword', async (req, res) => {
    try {
        const { userId, keyword, response } = req.body;
        const id = crypto.randomUUID();
        await db.query(userId, `
            INSERT INTO assistant_training (id, user_id, type, keyword, response, created_at)
            VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
        `, [id, userId, 'keyword', keyword, response]);
        const assistant = new IntelligentAssistant(userId, db);
        await assistant.updateUserActivity('train');
        const boost = await assistant.boostVisibility();
        res.json({ success: true, message: 'کلمه کلیدی با موفقیت ثبت شد', boost });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/assistant/schedule', async (req, res) => {
    try {
        const { userId, posts } = req.body;
        const channel = await db.query(userId, `SELECT id FROM channels WHERE user_id = $1`, [userId]);
        if (channel.rows.length === 0) {
            return res.status(404).json({ success: false, error: 'کانالی یافت نشد' });
        }
        const assistant = new IntelligentAssistant(userId, db);
        const scheduled = await assistant.schedulePosts(posts);
        res.json({ success: true, message: `${posts.length} پست با موفقیت زمان‌بندی شد`, posts: scheduled });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/assistant/:userId', async (req, res) => {
    try {
        const { userId } = req.params;
        const qa = await db.query(userId, `SELECT question, answer FROM assistant_training WHERE user_id = $1 AND type = 'qa' ORDER BY created_at DESC`, [userId]);
        const keywords = await db.query(userId, `SELECT keyword, response FROM assistant_training WHERE user_id = $1 AND type = 'keyword' ORDER BY created_at DESC`, [userId]);
        const posts = await db.query(userId, `SELECT p.*, c.name as channel_name FROM posts p JOIN channels c ON p.channel_id = c.id WHERE c.user_id = $1 AND p.is_published = 0 ORDER BY p.scheduled_time ASC`, [userId]);
        const assistant = new IntelligentAssistant(userId, db);
        const stats = await assistant.getStats();
        res.json({ qa: qa.rows, keywords: keywords.rows, posts: posts.rows, stats });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/assistant/chat/:targetUserId', async (req, res) => {
    try {
        const { targetUserId } = req.params;
        const { message } = req.body;
        const assistant = new IntelligentAssistant(targetUserId, db);
        const reply = await assistant.autoReply(message);
        res.json({ reply: reply || 'دستیار هنوز برای این موضوع آموزش ندیده 🤖' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// اکسپلور
// ============================================
const exploreCache = new Map();
const EXPLORE_CACHE_TTL = 15000;

app.get('/api/explore', async (req, res) => {
    try {
        const cached = exploreCache.get('explore');
        if (cached && (Date.now() - cached.timestamp) < EXPLORE_CACHE_TTL) {
            return res.json(cached.data);
        }
        const result = await db.query(null, `
            SELECT 
                u.id as user_id,
                u.name,
                u.avatar,
                u.score,
                c.id as channel_id,
                c.followers_count,
                c.posts_count,
                c.boost_level,
                c.activity_score,
                (
                    SELECT json_group_array(
                        json_object(
                            'id', p.id,
                            'content', p.content,
                            'media_url', p.media_url,
                            'media_type', p.media_type,
                            'likes', p.likes,
                            'comments', p.comments,
                            'views', p.views,
                            'created_at', p.created_at
                        )
                    )
                    FROM posts p
                    WHERE p.channel_id = c.id AND p.is_published = 1
                    ORDER BY p.created_at DESC
                    LIMIT 5
                ) as recent_posts
            FROM channels c
            JOIN users u ON u.id = c.user_id
            WHERE c.posts_count > 0
            ORDER BY c.activity_score DESC, c.followers_count DESC
            LIMIT 50
        `);
        const items = result.rows.map(row => ({ ...row, recent_posts: row.recent_posts ? JSON.parse(row.recent_posts) : [] }));
        exploreCache.set('explore', { data: items, timestamp: Date.now() });
        res.json(items);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/channel/:userId/posts', async (req, res) => {
    try {
        const { userId } = req.params;
        const result = await db.query(userId, `
            SELECT p.*, c.name as channel_name
            FROM posts p JOIN channels c ON p.channel_id = c.id
            WHERE c.user_id = $1 AND p.is_published = 1
            ORDER BY p.created_at DESC LIMIT 50
        `, [userId]);
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/search', async (req, res) => {
    try {
        const { q } = req.query;
        if (!q || q.length < 2) return res.json([]);
        const result = await db.query(null, `
            SELECT id, name, avatar, 'user' as type FROM users 
            WHERE name ILIKE $1 AND id != 'admin_milad'
            UNION
            SELECT id, name, NULL as avatar, 'channel' as type FROM channels 
            WHERE name ILIKE $1
            LIMIT 20
        `, [`%${q}%`]);
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// چت
// ============================================
app.post('/api/chat/save', async (req, res) => {
    try {
        const { from, to, message } = req.body;
        const id = crypto.randomUUID();
        await db.query(from, `INSERT INTO messages (id, from_user, to_user, message, created_at) VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)`, [id, from, to, message]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/chat/history/:userId/:targetId', async (req, res) => {
    try {
        const { userId, targetId } = req.params;
        const result = await db.query(userId, `
            SELECT * FROM messages 
            WHERE (from_user = $1 AND to_user = $2) OR (from_user = $2 AND to_user = $1)
            ORDER BY created_at ASC LIMIT 200
        `, [userId, targetId]);
        res.json(result.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/chat/list/:userId', async (req, res) => {
    try {
        const { userId } = req.params;
        const msgResult = await db.query(userId, `
            SELECT from_user, to_user, message, created_at, is_read
            FROM messages
            WHERE from_user = $1 OR to_user = $1
        `, [userId]);
        const lastMsgMap = new Map();
        const unreadMap = new Map();
        for (const m of msgResult.rows) {
            const partnerId = m.from_user === userId ? m.to_user : m.from_user;
            const cur = lastMsgMap.get(partnerId);
            if (!cur || new Date(m.created_at) > new Date(cur.created_at)) {
                lastMsgMap.set(partnerId, { message: m.message, created_at: m.created_at });
            }
            if (m.to_user === userId && !m.is_read) {
                unreadMap.set(partnerId, (unreadMap.get(partnerId) || 0) + 1);
            }
        }
        const chats = [];
        for (const partnerId of lastMsgMap.keys()) {
            try {
                const u = await db.query(partnerId, `SELECT id, name, avatar FROM users WHERE id = $1`, [partnerId]);
                if (u.rows[0]) {
                    const info = lastMsgMap.get(partnerId);
                    chats.push({ id: partnerId, name: u.rows[0].name, avatar: u.rows[0].avatar, lastMessage: info.message, lastTime: info.created_at, unreadCount: unreadMap.get(partnerId) || 0 });
                }
            } catch (e) {}
        }
        chats.sort((a, b) => new Date(b.lastTime) - new Date(a.lastTime));
        res.json(chats);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/chat/read', async (req, res) => {
    try {
        const { userId, fromUser } = req.body;
        await db.query(userId, `UPDATE messages SET is_read = 1 WHERE from_user = $1 AND to_user = $2 AND is_read = 0`, [fromUser, userId]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// ادمین
// ============================================
app.get('/api/admin/users', isAdmin, async (req, res) => {
    try {
        const users = await db.query(null, `SELECT u.*, c.followers_count, c.posts_count FROM users u LEFT JOIN channels c ON u.id = c.user_id ORDER BY u.created_at DESC`);
        res.json(users.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/admin/user/:action', isAdmin, async (req, res) => {
    try {
        const { action } = req.params;
        const { userId } = req.body;
        const actions = {
            verify: `UPDATE users SET is_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
            unverify: `UPDATE users SET is_verified = 0, updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
            ban: `UPDATE users SET role = 'banned', updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
            unban: `UPDATE users SET role = 'user', updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
            restrict: `UPDATE users SET restricted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = $1`,
            unrestrict: `UPDATE users SET restricted = 0, updated_at = CURRENT_TIMESTAMP WHERE id = $1`
        };
        if (!actions[action]) return res.status(400).json({ error: 'عملیات نامعتبر' });
        await db.query(null, actions[action], [userId]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/admin/posts', isAdmin, async (req, res) => {
    try {
        const posts = await db.query(null, `
            SELECT p.*, u.name as user_name, c.name as channel_name
            FROM posts p JOIN channels c ON p.channel_id = c.id JOIN users u ON c.user_id = u.id
            ORDER BY p.created_at DESC LIMIT 100
        `);
        res.json(posts.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/admin/post/delete', isAdmin, async (req, res) => {
    try {
        const { postId } = req.body;
        await db.query(null, `DELETE FROM posts WHERE id = $1`, [postId]);
        profileCache.clear();
        exploreCache.clear();
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/admin/channels', isAdmin, async (req, res) => {
    try {
        const channels = await db.query(null, `SELECT c.*, u.name as user_name, u.avatar FROM channels c JOIN users u ON c.user_id = u.id ORDER BY c.followers_count DESC`);
        res.json(channels.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/notifications/latest-broadcast/:userId', async (req, res) => {
    try {
        const { userId } = req.params;
        const result = await db.query(userId, `
            SELECT broadcast_id, title, message, created_at FROM system_notifications
            WHERE user_id = $1 AND type = 'broadcast'
            ORDER BY created_at DESC LIMIT 1
        `, [userId]);
        res.json(result.rows[0] || null);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/admin/broadcast', isAdmin, async (req, res) => {
    try {
        const { message, title } = req.body;
        if (!message || !message.trim()) {
            return res.status(400).json({ error: 'متن پیام الزامی است' });
        }
        const broadcastId = crypto.randomUUID();
        let totalSent = 0;
        await Promise.all(db.getAllShardIndexes().map(async (shardIndex) => {
            const users = await db.queryShardByIndex(shardIndex, `SELECT id FROM users`);
            if (!users.rows.length) return;
            for (const user of users.rows) {
                await db.queryShardByIndex(shardIndex, `
                    INSERT INTO system_notifications (id, user_id, title, message, type, broadcast_id, created_at)
                    VALUES ($1, $2, $3, $4, 'broadcast', $5, CURRENT_TIMESTAMP)
                `, [crypto.randomUUID(), user.id, title || 'اعلان سیستمی', message, broadcastId]);
                io.to(`user_${user.id}`).emit('broadcast', { broadcastId, title: title || 'اعلان سیستمی', message });
            }
            totalSent += users.rows.length;
        }));
        res.json({ success: true, message: `پیام به ${totalSent} کاربر ارسال شد` });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/admin/stats', isAdmin, async (req, res) => {
    try {
        const users = await db.query(null, `SELECT COUNT(*) as total FROM users`);
        const posts = await db.query(null, `SELECT COUNT(*) as total FROM posts WHERE is_published = 1`);
        const channels = await db.query(null, `SELECT COUNT(*) as total FROM channels`);
        const messages = await db.query(null, `SELECT COUNT(*) as total FROM messages`);
        const follows = await db.query(null, `SELECT COUNT(*) as total FROM follows`);
        const comments = await db.query(null, `SELECT COUNT(*) as total FROM post_comments`);
        const trainings = await db.query(null, `SELECT COUNT(*) as total FROM assistant_training`);
        const reports = await db.query(null, `SELECT COUNT(*) as total FROM reports WHERE status = 'pending'`);
        res.json({ users: users.rows[0]?.total || 0, posts: posts.rows[0]?.total || 0, channels: channels.rows[0]?.total || 0, messages: messages.rows[0]?.total || 0, follows: follows.rows[0]?.total || 0, comments: comments.rows[0]?.total || 0, trainings: trainings.rows[0]?.total || 0, pendingReports: reports.rows[0]?.total || 0 });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// گزارش
// ============================================
app.post('/api/report', async (req, res) => {
    try {
        const { reporterId, targetId, targetType, reason } = req.body;
        if (!reporterId || !targetId || !targetType || !reason || !reason.trim()) {
            return res.status(400).json({ success: false, error: 'اطلاعات گزارش ناقص است' });
        }
        if (!['user', 'post', 'comment'].includes(targetType)) {
            return res.status(400).json({ success: false, error: 'نوع گزارش نامعتبر است' });
        }
        const id = crypto.randomUUID();
        await db.query('global_reports', `
            INSERT INTO reports (id, reporter_id, target_id, target_type, reason, status, created_at)
            VALUES ($1, $2, $3, $4, $5, 'pending', CURRENT_TIMESTAMP)
        `, [id, reporterId, targetId, targetType, reason.trim().substring(0, 500)]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/admin/reports', isAdmin, async (req, res) => {
    try {
        const status = req.query.status || 'pending';
        const reports = await db.query(null, `SELECT * FROM reports WHERE status = $1 ORDER BY created_at DESC LIMIT 200`, [status]);
        res.json(reports.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/admin/report/:action', isAdmin, async (req, res) => {
    try {
        const { action } = req.params;
        const { reportId } = req.body;
        if (!['resolve', 'dismiss'].includes(action)) {
            return res.status(400).json({ error: 'عملیات نامعتبر' });
        }
        const status = action === 'resolve' ? 'resolved' : 'dismissed';
        await db.query(null, `UPDATE reports SET status = $1, resolved_at = CURRENT_TIMESTAMP WHERE id = $2`, [status, reportId]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// پرداخت
// ============================================
app.post('/api/payment/submit', async (req, res) => {
    try {
        const { userId, postId, amount, receiptUrl } = req.body;
        if (!userId || !receiptUrl) {
            return res.status(400).json({ success: false, error: 'اطلاعات فیش ناقص است' });
        }
        if (typeof receiptUrl !== 'string' || !receiptUrl.startsWith('/uploads/')) {
            return res.status(400).json({ success: false, error: 'فایل رسید نامعتبر است' });
        }
        const id = crypto.randomUUID();
        await db.query('global_payment_receipts', `
            INSERT INTO payment_receipts (id, user_id, post_id, receipt_image, amount, status, created_at)
            VALUES ($1, $2, $3, $4, $5, 'pending', CURRENT_TIMESTAMP)
        `, [id, userId, postId || null, receiptUrl, amount ? String(amount).substring(0, 40) : null]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/admin/payments', isAdmin, async (req, res) => {
    try {
        const status = req.query.status || 'pending';
        const result = await db.query(null, `SELECT * FROM payment_receipts WHERE status = $1 ORDER BY created_at DESC LIMIT 200`, [status]);
        const receipts = result.rows;
        const userIds = [...new Set(receipts.map(r => r.user_id))];
        const nameMap = {};
        for (const uid of userIds) {
            try {
                const u = await db.query(uid, `SELECT name FROM users WHERE id = $1`, [uid]);
                if (u.rows[0]) nameMap[uid] = u.rows[0].name;
            } catch (e) {}
        }
        res.json(receipts.map(r => ({ ...r, user_name: nameMap[r.user_id] || r.user_id })));
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/admin/payments/:id/:action', isAdmin, async (req, res) => {
    try {
        const { id, action } = req.params;
        if (!['approve', 'reject'].includes(action)) {
            return res.status(400).json({ error: 'عملیات نامعتبر' });
        }
        const status = action === 'approve' ? 'approved' : 'rejected';
        const existing = await db.query(null, `SELECT * FROM payment_receipts WHERE id = $1 LIMIT 1`, [id]);
        const receipt = existing.rows[0];
        if (!receipt) return res.status(404).json({ error: 'رسید پیدا نشد' });
        await db.query(null, `UPDATE payment_receipts SET status = $1, reviewed_at = CURRENT_TIMESTAMP WHERE id = $2`, [status, id]);
        const title = action === 'approve' ? '✅ فیش واریزی تایید شد' : '❌ فیش واریزی رد شد';
        const message = action === 'approve' ? 'رسید پرداخت شما بررسی و تایید شد. ممنون از حمایتت 🙏' : 'رسید پرداختی که فرستاده بودی رد شد. اگه فکر می‌کنی اشتباهی رخ داده، دوباره یه فیش واضح‌تر ارسال کن.';
        try {
            await db.query(receipt.user_id, `
                INSERT INTO system_notifications (id, user_id, title, message, type, created_at)
                VALUES ($1, $2, $3, $4, 'payment', CURRENT_TIMESTAMP)
            `, [crypto.randomUUID(), receipt.user_id, title, message]);
        } catch (e) {}
        io.to(`user_${receipt.user_id}`).emit('broadcast', { title, message });
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// بلاک
// ============================================
app.post('/api/user/block', async (req, res) => {
    try {
        const { blockerId, blockedId } = req.body;
        if (!blockerId || !blockedId) return res.status(400).json({ success: false, error: 'اطلاعات ناقص است' });
        res.json(await db.blockUser(blockerId, blockedId));
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/user/unblock', async (req, res) => {
    try {
        const { blockerId, blockedId } = req.body;
        res.json(await db.unblockUser(blockerId, blockedId));
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/user/:userId/is-blocked/:targetId', async (req, res) => {
    try {
        const { userId, targetId } = req.params;
        res.json({ blocked: await db.isBlocked(userId, targetId) });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// تبلیغات
// ============================================
app.get('/api/ads/active', async (req, res) => {
    try {
        const ads = await db.query(null, `SELECT * FROM ads WHERE is_active = 1 ORDER BY created_at DESC LIMIT 20`);
        res.json(ads.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/admin/ads', isAdmin, async (req, res) => {
    try {
        const ads = await db.query(null, `SELECT * FROM ads ORDER BY created_at DESC`);
        res.json(ads.rows);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/admin/ads/create', isAdmin, async (req, res) => {
    try {
        const { title, content, mediaUrl, mediaType, linkUrl } = req.body;
        if (!title || !title.trim()) return res.status(400).json({ success: false, error: 'عنوان تبلیغ الزامی است' });
        const id = crypto.randomUUID();
        await db.query('global_ads', `
            INSERT INTO ads (id, title, content, media_url, media_type, link_url, is_active, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, 1, CURRENT_TIMESTAMP)
        `, [id, title.trim(), content || '', mediaUrl || null, mediaType || 'none', linkUrl || null]);
        res.json({ success: true, adId: id });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/admin/ads/toggle', isAdmin, async (req, res) => {
    try {
        const { adId, active } = req.body;
        await db.query(null, `UPDATE ads SET is_active = $1 WHERE id = $2`, [active ? 1 : 0, adId]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/api/admin/ads/delete', isAdmin, async (req, res) => {
    try {
        const { adId } = req.body;
        await db.query(null, `DELETE FROM ads WHERE id = $1`, [adId]);
        res.json({ success: true });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ============================================
// ۴۰۴ و خطای سراسری
// ============================================
app.use('/api/', (req, res) => {
    res.status(404).json({ success: false, error: 'مسیر یافت نشد' });
});

app.use((err, req, res, next) => {
    console.error('Unhandled route error:', err);
    if (res.headersSent) return next(err);
    res.status(err.status || 500).json({ success: false, error: 'خطای داخلی سرور' });
});

// ============================================
// WebSocket
// ============================================
io.on('connection', (socket) => {
    console.log('🔌 New client connected:', socket.id);
    let msgTimestamps = [];

    socket.on('join', (userId) => {
        if (!userId) return;
        socket.data.userId = userId;
        socket.join(`user_${userId}`);
        console.log(`User ${userId} joined room`);
    });

    socket.on('private_message', async (data) => {
        const { from, to, message, mediaUrl, mediaType, timestamp } = data || {};
        const hasMedia = typeof mediaUrl === 'string' && mediaUrl.startsWith('/uploads/');
        const text = typeof message === 'string' ? message.trim() : '';
        if (!from || !to || (!text && !hasMedia)) {
            return io.to(`user_${from}`).emit('message_sent', { success: false, error: 'پیام نامعتبر است', timestamp });
        }
        if (text.length > 4000) {
            return io.to(`user_${from}`).emit('message_sent', { success: false, error: 'پیام خیلی طولانیه', timestamp });
        }
        if (await db.isBlocked(from, to)) {
            return io.to(`user_${from}`).emit('message_sent', { success: false, error: 'امکان ارسال پیام به این کاربر وجود ندارد', timestamp });
        }
        const now = Date.now();
        msgTimestamps = msgTimestamps.filter(t => now - t < 10000);
        if (msgTimestamps.length >= 20) {
            return io.to(`user_${from}`).emit('message_sent', { success: false, error: 'خیلی سریع پیام می‌فرستی، کمی صبر کن', timestamp });
        }
        msgTimestamps.push(now);
        const trimmed = text;
        const safeMediaType = hasMedia ? (mediaType === 'video' ? 'video' : 'image') : null;
        try {
            const id = crypto.randomUUID();
            await db.query(from, `
                INSERT INTO messages (id, from_user, to_user, message, media_url, media_type, created_at) 
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
            `, [id, from, to, trimmed, hasMedia ? mediaUrl : null, safeMediaType]);
            io.to(`user_${to}`).emit('new_message', { from, message: trimmed, mediaUrl: hasMedia ? mediaUrl : null, mediaType: safeMediaType, timestamp });
            io.to(`user_${from}`).emit('message_sent', { success: true, timestamp });
        } catch (e) {
            console.error('save message error', e);
            io.to(`user_${from}`).emit('message_sent', { success: false, error: 'ذخیره پیام ناموفق بود', timestamp });
        }
    });

    socket.on('typing', (data) => {
        const { from, to } = data || {};
        if (!from || !to) return;
        io.to(`user_${to}`).emit('user_typing', { from });
    });

    socket.on('disconnect', () => {
        console.log('🔌 Client disconnected:', socket.id);
    });
});

// ============================================
// راه‌اندازی سرور
// ============================================
const PORT = process.env.PORT || 3000;

async function startServer() {
    try {
        await db.ready;
        console.log('✅ Database ready');
        console.log('✅ Schemas created/verified');
        server.listen(PORT, () => {
            console.log(`🚀 Server running on port ${PORT} (pid ${process.pid})`);
            console.log(`📍 http://localhost:${PORT}`);
            console.log(`📊 Mode: ${process.env.NODE_ENV || 'development'} | Shards: ${db.shardCount}`);
        });
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
}

async function publishDueScheduledPosts() {
    try {
        const now = new Date().toISOString();
        const due = await db.query(null, `
            SELECT p.id, p.channel_id, c.user_id 
            FROM posts p JOIN channels c ON p.channel_id = c.id
            WHERE p.is_published = 0 AND p.scheduled_time IS NOT NULL AND p.scheduled_time <= $1
            LIMIT 200
        `, [now]);
        for (const row of due.rows) {
            try {
                const claim = await db.query(row.id, `
                    UPDATE posts SET is_published = 1, published_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = $1 AND is_published = 0
                `, [row.id]);
                if (!claim.rowCount) continue;
                await db.query(row.user_id, `UPDATE channels SET posts_count = posts_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = $1`, [row.channel_id]);
                const assistant = new IntelligentAssistant(row.user_id, db);
                await assistant.updateUserActivity('post');
                await assistant.boostVisibility();
                profileCache.clear();
                exploreCache.clear();
            } catch (e) {
                console.error('خطا در انتشار پست زمان‌بندی‌شده', row.id, e.message);
            }
        }
        if (due.rows.length) console.log(`📅 ${due.rows.length} پست زمان‌بندی‌شده منتشر شد`);
    } catch (e) {
        console.error('خطا در بررسی پست‌های زمان‌بندی‌شده:', e.message);
    }
}
setInterval(publishDueScheduledPosts, 60 * 1000);
publishDueScheduledPosts();

startServer();
publishDueScheduledPosts();

process.on('uncaughtException', (err) => {
    console.error('💥 Uncaught Exception:', err);
    gracefulExit(1);
});
process.on('unhandledRejection', (reason) => {
    console.error('💥 Unhandled Rejection:', reason);
});

function gracefulExit(code) {
    server.close(() => process.exit(code));
    setTimeout(() => process.exit(code), 10000).unref();
}

process.on('SIGTERM', () => {
    console.log('🛑 SIGTERM دریافت شد، خاموشی مرتب...');
    gracefulExit(0);
});

module.exports = { app, server, io };