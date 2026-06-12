import asyncpg
from typing import Optional, Dict, Any, List
from .config import Config

class Database:
    def __init__(self):
        self.pool = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            Config.DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        print("✅ PostgreSQL connected")
    
    async def execute(self, query: str, *args) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetchval(self, query: str, *args) -> Any:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    # ==================== User Methods ====================
    async def get_user(self, user_id: int) -> Optional[Dict]:
        return await self.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    
    async def create_user(self, user_id: int, username: str, first_name: str, last_name: str, referral_code: str):
        await self.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referral_code, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (user_id) DO UPDATE SET last_active = NOW()
        """, user_id, username, first_name, last_name, referral_code)
    
    async def update_user_language(self, user_id: int, language: str):
        await self.execute("UPDATE users SET language = $1, last_active = NOW() WHERE user_id = $2", language, user_id)
    
    async def update_wallet(self, user_id: int, amount: int):
        await self.execute("UPDATE users SET wallet_balance = wallet_balance + $1, last_active = NOW() WHERE user_id = $2", amount, user_id)
    
    async def activate_subscription(self, user_id: int, days: int = 30):
        await self.execute("""
            UPDATE users 
            SET subscription_status = 'active', 
                subscription_expiry = NOW() + INTERVAL '$1 days',
                last_active = NOW()
            WHERE user_id = $2
        """, days, user_id)
    
    # ==================== Bot Methods ====================
    async def create_bot(self, bot_id: str, user_id: int, token: str, name: str, username: str, file_path: str, language: str = 'python'):
        await self.execute("""
            INSERT INTO bots (id, user_id, token, name, username, file_path, language, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'running', NOW())
        """, bot_id, user_id, token, name, username, file_path, language)
        await self.execute("UPDATE users SET bots_count = bots_count + 1, last_active = NOW() WHERE user_id = $1", user_id)
    
    async def get_user_bots(self, user_id: int) -> List[Dict]:
        return await self.fetch("SELECT * FROM bots WHERE user_id = $1 ORDER BY created_at DESC", user_id)
    
    async def get_bot(self, bot_id: str) -> Optional[Dict]:
        return await self.fetchrow("SELECT * FROM bots WHERE id = $1", bot_id)
    
    async def update_bot_status(self, bot_id: str, status: str):
        await self.execute("UPDATE bots SET status = $1, last_active = NOW() WHERE id = $2", status, bot_id)
    
    async def delete_bot(self, bot_id: str, user_id: int):
        await self.execute("DELETE FROM bots WHERE id = $1 AND user_id = $2", bot_id, user_id)
        await self.execute("UPDATE users SET bots_count = bots_count - 1 WHERE user_id = $1", user_id)
    
    # ==================== Receipt Methods ====================
    async def create_receipt(self, user_id: int, amount: int, receipt_path: str, tx_hash: str):
        return await self.fetchval("""
            INSERT INTO receipts (user_id, amount, receipt_path, tx_hash, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            RETURNING id
        """, user_id, amount, receipt_path, tx_hash)
    
    async def get_pending_receipts(self) -> List[Dict]:
        return await self.fetch("SELECT * FROM receipts WHERE status = 'pending' ORDER BY created_at")
    
    async def approve_receipt(self, receipt_id: int, admin_id: int):
        await self.execute("UPDATE receipts SET status = 'approved', reviewed_by = $1, reviewed_at = NOW() WHERE id = $2", admin_id, receipt_id)
    
    # ==================== Withdraw Methods ====================
    async def create_withdraw(self, user_id: int, amount: int, address: str):
        await self.execute("""
            INSERT INTO withdraw_requests (user_id, amount, address, created_at)
            VALUES ($1, $2, $3, NOW())
        """, user_id, amount, address)
        await self.execute("UPDATE users SET wallet_balance = 0 WHERE user_id = $1", user_id)
    
    async def get_pending_withdraws(self) -> List[Dict]:
        return await self.fetch("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY created_at")
    
    async def approve_withdraw(self, withdraw_id: int):
        await self.execute("UPDATE withdraw_requests SET status = 'approved', processed_at = NOW() WHERE id = $1", withdraw_id)
    
    # ==================== Stats Methods ====================
    async def get_stats(self) -> Dict:
        total_users = await self.fetchval("SELECT COUNT(*) FROM users")
        active_subs = await self.fetchval("SELECT COUNT(*) FROM users WHERE subscription_status = 'active'")
        total_bots = await self.fetchval("SELECT COUNT(*) FROM bots")
        running_bots = await self.fetchval("SELECT COUNT(*) FROM bots WHERE status = 'running'")
        total_wallet = await self.fetchval("SELECT COALESCE(SUM(wallet_balance), 0) FROM users")
        
        return {
            'total_users': total_users,
            'active_subs': active_subs,
            'total_bots': total_bots,
            'running_bots': running_bots,
            'total_wallet': total_wallet
        }
    
    # ==================== Machine Methods ====================
    async def get_machines(self) -> List[Dict]:
        return await self.fetch("SELECT * FROM machines ORDER BY id")
    
    async def update_machine_capacity(self, machine_id: int, max_bots: int):
        await self.execute("UPDATE machines SET max_bots = $1 WHERE id = $2", max_bots, machine_id)
    
    async def update_machine_bots(self, machine_id: int, delta: int):
        await self.execute("UPDATE machines SET current_bots = current_bots + $1 WHERE id = $2", delta, machine_id)
