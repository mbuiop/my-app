-- users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language TEXT DEFAULT 'fa',
    bots_count INTEGER DEFAULT 0,
    max_bots INTEGER DEFAULT 3,
    subscription_status TEXT DEFAULT 'inactive',
    subscription_expiry TIMESTAMP,
    referral_code TEXT UNIQUE,
    referred_by BIGINT,
    referrals_count INTEGER DEFAULT 0,
    wallet_balance BIGINT DEFAULT 0,
    total_commission BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    is_banned BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE
);

-- bots table
CREATE TABLE IF NOT EXISTS bots (
    id TEXT PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    token TEXT,
    name TEXT,
    username TEXT,
    language TEXT DEFAULT 'python',
    file_path TEXT,
    folder_path TEXT,
    pid INTEGER,
    machine_id INTEGER,
    port INTEGER,
    status TEXT DEFAULT 'stopped',
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    join_enabled BOOLEAN DEFAULT TRUE,
    join_block_message TEXT DEFAULT '🚫 Server is full',
    health_status TEXT DEFAULT 'healthy',
    error_message TEXT,
    restart_count INTEGER DEFAULT 0
);

-- receipts table
CREATE TABLE IF NOT EXISTS receipts (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    amount BIGINT,
    receipt_path TEXT,
    tx_hash TEXT,
    status TEXT DEFAULT 'pending',
    reviewed_by BIGINT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- withdraw_requests table
CREATE TABLE IF NOT EXISTS withdraw_requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    amount BIGINT,
    address TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

-- commissions table
CREATE TABLE IF NOT EXISTS commissions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    from_user BIGINT,
    amount BIGINT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    paid BOOLEAN DEFAULT FALSE
);

-- machines table
CREATE TABLE IF NOT EXISTS machines (
    id SERIAL PRIMARY KEY,
    name TEXT,
    ip TEXT,
    port INTEGER DEFAULT 22,
    username TEXT,
    password TEXT,
    status TEXT DEFAULT 'active',
    current_bots INTEGER DEFAULT 0,
    max_bots INTEGER DEFAULT 5000,
    created_at TIMESTAMP DEFAULT NOW(),
    is_local BOOLEAN DEFAULT TRUE
);

-- errors table
CREATE TABLE IF NOT EXISTS errors (
    id TEXT PRIMARY KEY,
    type TEXT,
    message TEXT,
    user_id BIGINT,
    bot_id TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    stack_trace TEXT
);

-- system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- daily_stats table
CREATE TABLE IF NOT EXISTS daily_stats (
    date DATE PRIMARY KEY,
    new_users INTEGER DEFAULT 0,
    new_bots INTEGER DEFAULT 0,
    new_subscriptions INTEGER DEFAULT 0,
    total_revenue BIGINT DEFAULT 0
);

-- indexes
CREATE INDEX IF NOT EXISTS idx_users_referral ON users(referral_code);
CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription_status, subscription_expiry);
CREATE INDEX IF NOT EXISTS idx_bots_user ON bots(user_id);
CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status);
CREATE INDEX IF NOT EXISTS idx_receipts_pending ON receipts(status, created_at);
CREATE INDEX IF NOT EXISTS idx_withdraw_pending ON withdraw_requests(status, created_at);

-- insert default machine
INSERT INTO machines (id, name, status, max_bots, created_at, is_local)
VALUES (1, 'سرور اصلی', 'active', 5000, NOW(), TRUE)
ON CONFLICT (id) DO NOTHING;

-- insert default settings
INSERT INTO system_settings (key, value) VALUES
    ('trc20_address', 'TV61aTh98MGqmteYzda5AaBzdXgGqreG6A'),
    ('card_number', '5892101187322777'),
    ('card_holder', 'مرتضی نیکخو خنجری'),
    ('card_bank', 'بانک ملی - سپهر'),
    ('subscription_price', '2000000'),
    ('withdraw_percent', '7'),
    ('min_withdraw', '2000000'),
    ('max_bots_per_subscription', '3'),
    ('max_builds_per_hour', '10'),
    ('max_concurrent_builds', '5'),
    ('health_check_interval', '30')
ON CONFLICT (key) DO NOTHING;
