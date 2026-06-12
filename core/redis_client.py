import redis.asyncio as redis
import json
from typing import Optional, Any
from datetime import datetime
from .config import Config

class RedisClient:
    def __init__(self):
        self.client = None
    
    async def connect(self):
        self.client = await redis.from_url(
            Config.REDIS_URL,
            decode_responses=True,
            max_connections=20
        )
        print("✅ Redis connected")
    
    # ==================== Rate Limiting ====================
    async def check_rate_limit(self, user_id: int, limit: int = 5, window: int = 1) -> bool:
        key = f"rate:{user_id}"
        current = await self.client.incr(key)
        if current == 1:
            await self.client.expire(key, window)
        return current <= limit
    
    async def get_builds_today(self, user_id: int) -> int:
        key = f"builds:{user_id}:{datetime.now().date()}"
        val = await self.client.get(key)
        return int(val) if val else 0
    
    async def increment_builds(self, user_id: int):
        key = f"builds:{user_id}:{datetime.now().date()}"
        await self.client.incr(key)
        await self.client.expire(key, 86400)
    
    # ==================== Cache ====================
    async def get(self, key: str) -> Optional[Any]:
        data = await self.client.get(key)
        if data:
            try:
                return json.loads(data)
            except:
                return data
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.setex(key, ttl, value)
    
    async def delete(self, key: str):
        await self.client.delete(key)
    
    # ==================== Queue ====================
    async def push_queue(self, queue_name: str, data: Any):
        await self.client.lpush(queue_name, json.dumps(data))
    
    async def pop_queue(self, queue_name: str) -> Optional[Any]:
        data = await self.client.rpop(queue_name)
        return json.loads(data) if data else None
    
    async def get_queue_length(self, queue_name: str) -> int:
        return await self.client.llen(queue_name)
    
    # ==================== Session ====================
    async def set_user_session(self, user_id: int, data: dict, ttl: int = 300):
        await self.set(f"session:{user_id}", data, ttl)
    
    async def get_user_session(self, user_id: int) -> Optional[dict]:
        return await self.get(f"session:{user_id}")
    
    async def clear_user_session(self, user_id: int):
        await self.delete(f"session:{user_id}")
