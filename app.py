import asyncio
import json
import os
import uuid
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import aioredis  # ✅ درست: aioredis
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import aiofiles
import uvicorn

# ===================================================
# Configuration
# ===================================================

class Config:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    UPLOAD_DIR = "uploads"
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
    
    @classmethod
    def ensure_directories(cls):
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)

Config.ensure_directories()

# ===================================================
# Database Models
# ===================================================

class User(BaseModel):
    id: str
    username: str
    avatar: str
    bio: str = ""
    followers: int = 0
    following: int = 0
    posts: int = 0
    created_at: datetime = datetime.now()

class Post(BaseModel):
    id: str
    user_id: str
    username: str
    media: str
    type: str = "image"
    caption: str = ""
    likes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    created_at: datetime = datetime.now()

class Comment(BaseModel):
    id: str
    post_id: str
    user_id: str
    username: str
    text: str
    created_at: datetime = datetime.now()

class ChatMessage(BaseModel):
    id: str
    from_user: str
    to_user: str
    message: str
    created_at: datetime = datetime.now()
    read: bool = False

class Story(BaseModel):
    id: str
    user_id: str
    username: str
    avatar: str
    media: str
    created_at: datetime = datetime.now()
    expires_at: datetime = datetime.now() + timedelta(hours=24)

# ===================================================
# Database Connection Pool
# ===================================================

class Database:
    _instance = None
    _client = None
    _redis = None
    
    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = Database()
            await cls._instance.connect()
        return cls._instance
    
    async def connect(self):
        # MongoDB
        self._client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self._client.social_media
        
        # Redis (با استفاده از aioredis)
        self._redis = await aioredis.from_url(Config.REDIS_URL, decode_responses=True)
        
        # Create indexes
        await self.db.posts.create_index("created_at")
        await self.db.posts.create_index("user_id")
        await self.db.comments.create_index("post_id")
        await self.db.chat_messages.create_index([("from_user", 1), ("to_user", 1)])
        await self.db.chat_messages.create_index("created_at")
        await self.db.stories.create_index("expires_at", expireAfterSeconds=0)
    
    @property
    def mongo(self):
        return self.db
    
    @property
    def redis(self):
        return self._redis

# ===================================================
# WebSocket Manager
# ===================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, str] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        
        async with self._lock:
            if user_id in self.user_connections:
                old_conn_id = self.user_connections[user_id]
                if old_conn_id in self.active_connections:
                    try:
                        await self.active_connections[old_conn_id].close()
                    except:
                        pass
                    del self.active_connections[old_conn_id]
            
            self.active_connections[connection_id] = websocket
            self.user_connections[user_id] = connection_id
        
        websocket.state.user_id = user_id
        websocket.state.connection_id = connection_id
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        async with self._lock:
            if connection_id in self.active_connections:
                ws = self.active_connections[connection_id]
                user_id = getattr(ws.state, 'user_id', None)
                if user_id and user_id in self.user_connections:
                    del self.user_connections[user_id]
                del self.active_connections[connection_id]
    
    async def send_to_user(self, user_id: str, data: dict):
        async with self._lock:
            if user_id in self.user_connections:
                conn_id = self.user_connections[user_id]
                if conn_id in self.active_connections:
                    try:
                        await self.active_connections[conn_id].send_json(data)
                        return True
                    except:
                        pass
        return False
    
    async def broadcast(self, data: dict, exclude_user: str = None):
        async with self._lock:
            for conn_id, ws in self.active_connections.items():
                user_id = getattr(ws.state, 'user_id', None)
                if user_id != exclude_user:
                    try:
                        await ws.send_json(data)
                    except:
                        pass

manager = ConnectionManager()

# ===================================================
# FastAPI Application
# ===================================================

app = FastAPI(title="Social Media API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================================================
# Dependency Injection
# ===================================================

async def get_db() -> Database:
    return await Database.get_instance()

async def get_current_user(request: Request) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        user_id = f"user_{uuid.uuid4().hex[:8]}"
    return user_id

# ===================================================
# Helper Functions
# ===================================================

def generate_id() -> str:
    return str(ObjectId())

def get_avatar_url(user_id: str) -> str:
    return f"https://i.pravatar.cc/150?img={hash(user_id) % 70 + 1}"

def get_media_url(filename: str) -> str:
    return f"/uploads/{filename}"

# ===================================================
# API Routes
# ===================================================

@app.get("/api/stories")
async def get_stories(
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    stories = await db.mongo.stories.find(
        {"expires_at": {"$gt": datetime.now()}}
    ).limit(20).to_list(None)
    
    return {
        "stories": [
            {
                "id": str(s["_id"]),
                "username": s["username"],
                "avatar": s["avatar"],
                "media": s["media"],
                "created_at": s["created_at"].isoformat()
            }
            for s in stories
        ]
    }

@app.get("/api/posts")
async def get_posts(
    mode: str = "explore",
    limit: int = 50,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    query = {}
    
    if mode == "following":
        follow_key = f"followers:{user_id}"
        following = await db.redis.smembers(follow_key)
        if following:
            query["user_id"] = {"$in": list(following)}
        else:
            query = {}
    
    if mode == "reels":
        query["type"] = "video"
    
    posts = await db.mongo.posts.find(query).sort(
        "created_at", -1
    ).limit(limit).to_list(None)
    
    result = []
    for post in posts:
        post_id = str(post["_id"])
        liked_key = f"likes:{post_id}"
        liked = await db.redis.sismember(liked_key, user_id)
        
        result.append({
            "id": post_id,
            "user_id": post["user_id"],
            "username": post.get("username", "کاربر"),
            "media": post["media"],
            "type": post.get("type", "image"),
            "caption": post.get("caption", ""),
            "likes": post.get("likes", 0),
            "comments": post.get("comments", 0),
            "shares": post.get("shares", 0),
            "views": post.get("views", 0),
            "liked": liked,
            "created_at": post["created_at"].isoformat()
        })
    
    return {"posts": result}

@app.get("/api/post/{post_id}")
async def get_post(
    post_id: str,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    from bson import ObjectId
    
    post = await db.mongo.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    liked_key = f"likes:{post_id}"
    liked = await db.redis.sismember(liked_key, user_id)
    
    return {
        "id": str(post["_id"]),
        "user_id": post["user_id"],
        "username": post.get("username", "کاربر"),
        "media": post["media"],
        "type": post.get("type", "image"),
        "caption": post.get("caption", ""),
        "likes": post.get("likes", 0),
        "comments": post.get("comments", 0),
        "shares": post.get("shares", 0),
        "views": post.get("views", 0),
        "liked": liked,
        "created_at": post["created_at"].isoformat()
    }

@app.get("/api/comments/{post_id}")
async def get_comments(
    post_id: str,
    limit: int = 50,
    db: Database = Depends(get_db)
):
    from bson import ObjectId
    
    comments = await db.mongo.comments.find(
        {"post_id": post_id}
    ).sort("created_at", 1).limit(limit).to_list(None)
    
    return {
        "comments": [
            f"{c['username']}: {c['text']}"
            for c in comments
        ]
    }

@app.post("/api/comment/{post_id}")
async def add_comment(
    post_id: str,
    data: dict,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    from bson import ObjectId
    
    text = data.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Comment text is required")
    
    user_key = f"user:{user_id}"
    username = await db.redis.hget(user_key, "username") or "کاربر"
    
    comment = {
        "id": generate_id(),
        "post_id": post_id,
        "user_id": user_id,
        "username": username,
        "text": text,
        "created_at": datetime.now()
    }
    
    await db.mongo.comments.insert_one(comment)
    
    result = await db.mongo.posts.update_one(
        {"_id": ObjectId(post_id)},
        {"$inc": {"comments": 1}}
    )
    
    post = await db.mongo.posts.find_one({"_id": ObjectId(post_id)})
    comments_count = post.get("comments", 0) if post else 0
    
    if post:
        await manager.broadcast({
            "type": "new_comment",
            "post_id": post_id,
            "user_id": user_id,
            "username": username,
            "text": text,
            "comments": comments_count
        })
    
    return {"success": True, "comments": comments_count}

@app.post("/api/like/{post_id}")
async def toggle_like(
    post_id: str,
    data: dict = None,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    from bson import ObjectId
    
    unlike = data.get("unlike", False) if data else False
    liked_key = f"likes:{post_id}"
    
    if unlike:
        await db.redis.srem(liked_key, user_id)
    else:
        await db.redis.sadd(liked_key, user_id)
    
    likes = await db.redis.scard(liked_key)
    
    await db.mongo.posts.update_one(
        {"_id": ObjectId(post_id)},
        {"$set": {"likes": likes}}
    )
    
    await manager.broadcast({
        "type": "like_update",
        "post_id": post_id,
        "user_id": user_id,
        "likes": likes,
        "liked": not unlike
    })
    
    return {"likes": likes, "liked": not unlike}

@app.post("/api/share/{post_id}")
async def share_post(
    post_id: str,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    from bson import ObjectId
    
    result = await db.mongo.posts.update_one(
        {"_id": ObjectId(post_id)},
        {"$inc": {"shares": 1}}
    )
    
    post = await db.mongo.posts.find_one({"_id": ObjectId(post_id)})
    shares = post.get("shares", 0) if post else 0
    
    return {"success": True, "shares": shares}

@app.post("/api/view/{post_id}")
async def increment_view(
    post_id: str,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    from bson import ObjectId
    
    view_key = f"views:{post_id}:{user_id}"
    if await db.redis.setnx(view_key, "1"):
        await db.redis.expire(view_key, 3600)
        
        await db.mongo.posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$inc": {"views": 1}}
        )
    
    return {"success": True}

@app.get("/api/profile")
async def get_profile(
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    user_key = f"user:{user_id}"
    
    username = await db.redis.hget(user_key, "username") or user_id[:8]
    bio = await db.redis.hget(user_key, "bio") or "توسعه‌دهنده وب | عاشق کدنویسی"
    posts = int(await db.redis.hget(user_key, "posts") or 0)
    
    followers = await db.redis.scard(f"followers:{user_id}")
    following = await db.redis.scard(f"following:{user_id}")
    is_following = False
    
    user_posts = await db.mongo.posts.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(20).to_list(None)
    
    profile_posts = []
    for post in user_posts:
        post_id = str(post["_id"])
        liked_key = f"likes:{post_id}"
        liked = await db.redis.sismember(liked_key, user_id)
        
        profile_posts.append({
            "id": post_id,
            "media": post["media"],
            "type": post.get("type", "image"),
            "likes": post.get("likes", 0),
            "comments": post.get("comments", 0),
            "shares": post.get("shares", 0),
            "views": post.get("views", 0),
            "liked": liked
        })
    
    return {
        "username": username,
        "bio": bio,
        "avatar": get_avatar_url(user_id),
        "posts": posts,
        "followers": followers,
        "following": following,
        "is_following": is_following,
        "profile_posts": profile_posts
    }

@app.post("/api/profile/bio")
async def update_bio(
    data: dict,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    bio = data.get("bio", "").strip()
    if not bio:
        raise HTTPException(status_code=400, detail="Bio is required")
    
    user_key = f"user:{user_id}"
    await db.redis.hset(user_key, "bio", bio)
    
    return {"success": True}

@app.post("/api/follow/toggle")
async def toggle_follow(
    data: dict = None,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    target_user = data.get("username", user_id) if data else user_id
    
    if target_user == user_id:
        return {"following": False, "followers": 0}
    
    follow_key = f"following:{user_id}"
    is_following = await db.redis.sismember(follow_key, target_user)
    
    if is_following:
        await db.redis.srem(follow_key, target_user)
        await db.redis.srem(f"followers:{target_user}", user_id)
        following = False
    else:
        await db.redis.sadd(follow_key, target_user)
        await db.redis.sadd(f"followers:{target_user}", user_id)
        following = True
    
    followers = await db.redis.scard(f"followers:{target_user}")
    
    return {"following": following, "followers": followers}

@app.get("/api/follow/{type}")
async def get_follow_list(
    type: str,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    if type == "followers":
        users = await db.redis.smembers(f"followers:{user_id}")
    else:
        users = await db.redis.smembers(f"following:{user_id}")
    
    result = []
    for uid in list(users)[:50]:
        user_key = f"user:{uid}"
        username = await db.redis.hget(user_key, "username") or uid[:8]
        is_following = await db.redis.sismember(f"following:{user_id}", uid)
        
        result.append({
            "id": uid,
            "name": username,
            "avatar": get_avatar_url(uid),
            "is_following": is_following
        })
    
    return {"users": result}

@app.get("/api/chats")
async def get_chats(
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    chat_partners = await db.mongo.chat_messages.aggregate([
        {"$match": {"$or": [{"from_user": user_id}, {"to_user": user_id}]}},
        {"$group": {"_id": {
            "$cond": [
                {"$eq": ["$from_user", user_id]},
                "$to_user",
                "$from_user"
            ]
        }}},
        {"$lookup": {
            "from": "chat_messages",
            "let": {"partner": "$_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$or": [
                            {"$and": [{"$eq": ["$from_user", user_id]}, {"$eq": ["$to_user", "$$partner"]}]},
                            {"$and": [{"$eq": ["$from_user", "$$partner"]}, {"$eq": ["$to_user", user_id]}]}
                        ]
                    }
                }},
                {"$sort": {"created_at": -1}},
                {"$limit": 1}
            ],
            "as": "last_msg"
        }},
        {"$unwind": {"path": "$last_msg", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"last_msg.created_at": -1}},
        {"$limit": 50}
    ]).to_list(None)
    
    chats = []
    for partner in chat_partners:
        partner_id = partner["_id"]
        if partner_id != user_id:
            user_key = f"user:{partner_id}"
            username = await db.redis.hget(user_key, "username") or partner_id[:8]
            last_msg = partner.get("last_msg", {})
            
            chats.append({
                "id": partner_id,
                "name": username,
                "avatar": get_avatar_url(partner_id),
                "last_message": "پیام جدید" if not last_msg else "پیام رمزنگاری شده",
                "time": "همین حالا" if not last_msg else last_msg.get("created_at", datetime.now()).strftime("%H:%M")
            })
    
    return {"chats": chats}

@app.get("/api/chat/{user_id}")
async def get_chat_messages(
    user_id: str,
    limit: int = 100,
    current_user: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    messages = await db.mongo.chat_messages.find({
        "$or": [
            {"$and": [{"from_user": current_user}, {"to_user": user_id}]},
            {"$and": [{"from_user": user_id}, {"to_user": current_user}]}
        ]
    }).sort("created_at", -1).limit(limit).to_list(None)
    
    return {
        "messages": [
            {
                "id": str(m["_id"]),
                "sender": m["from_user"],
                "text": m["message"],
                "time": m["created_at"].isoformat()
            }
            for m in reversed(messages)
        ]
    }

@app.post("/api/chat/send")
async def send_chat_message(
    data: dict,
    current_user: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    to_user = data.get("to")
    message = data.get("message")
    
    if not to_user or not message:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    chat_message = {
        "id": generate_id(),
        "from_user": current_user,
        "to_user": to_user,
        "message": message,
        "created_at": datetime.now(),
        "read": False
    }
    
    await db.mongo.chat_messages.insert_one(chat_message)
    
    await manager.send_to_user(to_user, {
        "type": "new_message",
        "from": current_user,
        "message": message,
        "time": datetime.now().isoformat()
    })
    
    return {"success": True}

@app.post("/api/upload")
async def upload_post(
    media: UploadFile = File(...),
    caption: str = Form(""),
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    content_type = media.content_type
    is_video = content_type.startswith("video/")
    is_image = content_type.startswith("image/")
    
    if not is_video and not is_image:
        raise HTTPException(status_code=400, detail="Only images and videos are allowed")
    
    ext = media.filename.split(".")[-1] if "." in media.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(Config.UPLOAD_DIR, filename)
    
    async with aiofiles.open(filepath, "wb") as f:
        content = await media.read()
        if len(content) > Config.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        await f.write(content)
    
    media_url = f"/uploads/{filename}"
    
    user_key = f"user:{user_id}"
    username = await db.redis.hget(user_key, "username") or user_id[:8]
    
    post = {
        "user_id": user_id,
        "username": username,
        "media": media_url,
        "type": "video" if is_video else "image",
        "caption": caption,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "views": 0,
        "created_at": datetime.now()
    }
    
    result = await db.mongo.posts.insert_one(post)
    post_id = str(result.inserted_id)
    
    await db.redis.hincrby(user_key, "posts", 1)
    
    await manager.broadcast({
        "type": "new_post",
        "post_id": post_id,
        "user_id": user_id,
        "username": username,
        "media": media_url,
        "caption": caption
    })
    
    return {"success": True, "post_id": post_id}

@app.get("/api/search")
async def search_posts(
    q: str,
    limit: int = 30,
    user_id: str = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    results = await db.mongo.posts.find({
        "$or": [
            {"caption": {"$regex": q, "$options": "i"}},
            {"username": {"$regex": q, "$options": "i"}}
        ]
    }).sort("created_at", -1).limit(limit).to_list(None)
    
    posts = []
    for post in results:
        post_id = str(post["_id"])
        liked_key = f"likes:{post_id}"
        liked = await db.redis.sismember(liked_key, user_id)
        
        posts.append({
            "id": post_id,
            "media": post["media"],
            "type": post.get("type", "image"),
            "likes": post.get("likes", 0),
            "comments": post.get("comments", 0),
            "shares": post.get("shares", 0),
            "views": post.get("views", 0),
            "liked": liked
        })
    
    return {"results": posts}

# ===================================================
# WebSocket Handler
# ===================================================

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    db = await Database.get_instance()
    connection_id = await manager.connect(websocket, user_id)
    
    try:
        await websocket.send_json({"type": "connected", "user_id": user_id})
        
        user_key = f"user:{user_id}"
        await db.redis.hsetnx(user_key, "username", user_id[:8])
        
        while True:
            data = await websocket.receive_json()
            
            msg_type = data.get("type")
            
            if msg_type == "chat":
                to_user = data.get("to")
                message = data.get("message")
                
                if to_user and message:
                    chat_message = {
                        "id": generate_id(),
                        "from_user": user_id,
                        "to_user": to_user,
                        "message": message,
                        "created_at": datetime.now(),
                        "read": False
                    }
                    
                    await db.mongo.chat_messages.insert_one(chat_message)
                    await manager.send_to_user(to_user, {
                        "type": "new_message",
                        "from": user_id,
                        "message": message,
                        "time": datetime.now().isoformat()
                    })
            
            elif msg_type == "typing":
                to_user = data.get("to")
                if to_user:
                    await manager.send_to_user(to_user, {
                        "type": "typing",
                        "from": user_id,
                        "is_typing": data.get("is_typing", True)
                    })
            
            elif msg_type == "read_receipt":
                to_user = data.get("to")
                if to_user:
                    await db.mongo.chat_messages.update_many(
                        {"from_user": to_user, "to_user": user_id, "read": False},
                        {"$set": {"read": True}}
                    )
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(connection_id)

# ===================================================
# Static Files
# ===================================================

@app.get("/uploads/{filename}")
async def serve_media(filename: str):
    filepath = os.path.join(Config.UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)

# ===================================================
# Health Check
# ===================================================

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ===================================================
# Main Entry Point
# ===================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        workers=4,
        log_level="info"
    )