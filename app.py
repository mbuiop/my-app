"""
ساده‌گرام - نسخه حرفه‌ای
پلتفرم اشتراک ویدیو با مدیریت کامل
"""

# ============================================
# کتابخانه‌ها
# ============================================
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, BigInteger, Text, ForeignKey, Index, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import bcrypt
import jwt
import redis
import boto3
from botocore.config import Config
import uuid
import os
import shutil
import subprocess
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
import json
import asyncio
from contextlib import asynccontextmanager
import logging
from threading import Thread
import time

# ============================================
# تنظیمات
# ============================================
SECRET_KEY = "your-super-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # ۳۰ روز

# دیتابیس
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/sadegram")
# برای تست با SQLite: "sqlite:///./sadegram.db"

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# فضای ابری
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = os.getenv("S3_BUCKET", "sadegram-videos")

# سرور
SERVER_ID = int(os.getenv("SERVER_ID", 1))
MAX_USERS_PER_SERVER = int(os.getenv("MAX_USERS_PER_SERVER", 10000))

# ============================================
# اتصالات
# ============================================

# دیتابیس
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✅ Redis متصل شد")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️ Redis در دسترس نیست: {e}")

# S3
if S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
    s3_client = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version='s3v4', max_pool_connections=50)
    )
    S3_AVAILABLE = True
    print("✅ فضای ابری متصل شد")
else:
    S3_AVAILABLE = False
    print("⚠️ فضای ابری تنظیم نشده")

# ============================================
# مدل‌های دیتابیس (کامل)
# ============================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    bio = Column(Text)
    avatar_url = Column(String(500))
    website = Column(String(200))
    location = Column(String(100))
    
    is_premium = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)  # نشان آبی
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    server_id = Column(Integer, default=1)
    
    # آمار
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    videos_count = Column(Integer, default=0)
    total_likes_received = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_seen = Column(DateTime, default=func.now())
    
    # روابط
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", cascade="all, delete-orphan")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", cascade="all, delete-orphan")
    
    # ایندکس‌ها
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
        Index('idx_users_server_id', 'server_id'),
    )

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    title = Column(String(200))
    description = Column(Text)
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    duration = Column(Integer, default=0)
    size_mb = Column(Integer, default=0)
    
    # آمار
    views = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    is_private = Column(Boolean, default=False)  # فقط فالوکنندگان ببینند
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # روابط
    user = relationship("User", back_populates="videos")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="video", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_videos_user_id', 'user_id'),
        Index('idx_videos_created_at', 'created_at'),
        Index('idx_videos_views', 'views'),
        Index('idx_videos_likes', 'likes_count'),
    )

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    video_id = Column(BigInteger, ForeignKey("videos.id"), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("comments.id"), nullable=True)  # پاسخ به کامنت
    content = Column(Text, nullable=False)
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # روابط
    user = relationship("User", back_populates="comments")
    video = relationship("Video", back_populates="comments")
    replies = relationship("Comment", backref="parent", remote_side=[id])
    
    __table_args__ = (
        Index('idx_comments_video_id', 'video_id'),
        Index('idx_comments_user_id', 'user_id'),
        Index('idx_comments_created_at', 'created_at'),
    )

class Like(Base):
    __tablename__ = "likes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    video_id = Column(BigInteger, ForeignKey("videos.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="likes")
    video = relationship("Video", back_populates="likes")
    
    __table_args__ = (
        Index('idx_likes_user_video', 'user_id', 'video_id', unique=True),
    )

class Follow(Base):
    __tablename__ = "follows"
    
    id = Column(BigInteger, primary_key=True, index=True)
    follower_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    following_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_follows_follower', 'follower_id'),
        Index('idx_follows_following', 'following_id'),
        Index('idx_follows_unique', 'follower_id', 'following_id', unique=True),
    )

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True, index=True)
    sender_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # روابط
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    
    __table_args__ = (
        Index('idx_messages_sender', 'sender_id'),
        Index('idx_messages_receiver', 'receiver_id'),
        Index('idx_messages_created', 'created_at'),
        Index('idx_messages_conversation', 'sender_id', 'receiver_id'),
    )

class ServerMapping(Base):
    __tablename__ = "server_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    server_name = Column(String(50), nullable=False)
    server_ip = Column(String(50))
    server_port = Column(Integer, default=8000)
    max_users = Column(Integer, default=10000)
    current_users = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    load_avg = Column(Integer, default=0)  # بار سرور
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(BigInteger, primary_key=True, index=True)
    reporter_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    video_id = Column(BigInteger, ForeignKey("videos.id"), nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    comment_id = Column(BigInteger, ForeignKey("comments.id"), nullable=True)
    reason = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="pending")  # pending, reviewed, rejected, resolved
    created_at = Column(DateTime, default=func.now())
    resolved_at = Column(DateTime, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)  # like, comment, follow, message, system
    content = Column(Text, nullable=False)
    link = Column(String(500))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_notifications_user', 'user_id'),
        Index('idx_notifications_read', 'is_read'),
    )

# ============================================
# Pydantic Models
# ============================================

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    is_premium: bool
    is_verified: bool
    followers_count: int
    following_count: int
    videos_count: int
    server_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class VideoCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_private: bool = False

class VideoResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    video_url: str
    thumbnail_url: Optional[str] = None
    duration: int
    views: int
    likes_count: int
    comments_count: int
    shares_count: int
    is_private: bool
    created_at: datetime
    username: Optional[str] = None
    user_avatar: Optional[str] = None
    is_liked: bool = False
    is_following: bool = False
    
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None

class CommentResponse(BaseModel):
    id: int
    user_id: int
    video_id: int
    parent_id: Optional[int] = None
    content: str
    likes_count: int
    created_at: datetime
    username: str
    user_avatar: Optional[str] = None
    
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    receiver_id: int
    content: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    is_read: bool
    created_at: datetime
    sender_username: str
    sender_avatar: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class AddServerRequest(BaseModel):
    server_name: str
    server_ip: str
    server_port: int = 8000
    max_users: int = 10000

class AdminStatsResponse(BaseModel):
    total_users: int
    total_videos: int
    total_views: int
    total_comments: int
    active_users_today: int
    new_users_today: int
    new_videos_today: int
    premium_users: int
    server_count: int
    storage_used_gb: float

# ============================================
# توابع ابزاری
# ============================================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None

def get_current_user(token: str, db: Session) -> Optional[User]:
    payload = decode_access_token(token)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload.get("user_id"), User.is_active == True).first()

def get_cache_or_query(key: str, query_func, expire: int = 300):
    """کش کردن نتیجه کوئری"""
    if REDIS_AVAILABLE:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    
    result = query_func()
    
    if REDIS_AVAILABLE:
        redis_client.setex(key, expire, json.dumps(result))
    
    return result

def invalidate_cache(pattern: str):
    """پاک کردن کش با الگو"""
    if REDIS_AVAILABLE:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)

# ============================================
# سرویس شاردینگ
# ============================================

class ShardingService:
    
    @staticmethod
    def get_server_for_user(user_id: int, db: Session) -> int:
        cache_key = f"user_server:{user_id}"
        if REDIS_AVAILABLE:
            cached = redis_client.get(cache_key)
            if cached:
                return int(cached)
        
        user = db.query(User).filter(User.id == user_id).first()
        server_id = user.server_id if user else 1
        
        if REDIS_AVAILABLE:
            redis_client.setex(cache_key, 3600, server_id)
        
        return server_id
    
    @staticmethod
    def assign_user_to_server(db: Session) -> int:
        servers = db.query(ServerMapping).filter(
            ServerMapping.is_active == True
        ).order_by(ServerMapping.current_users).all()
        
        if not servers:
            default = ServerMapping(
                server_name=f"server-1",
                server_ip="127.0.0.1",
                server_port=8000,
                max_users=MAX_USERS_PER_SERVER,
                current_users=0
            )
            db.add(default)
            db.commit()
            db.refresh(default)
            servers = [default]
        
        selected = servers[0]
        selected.current_users += 1
        db.commit()
        
        if REDIS_AVAILABLE:
            redis_client.publish("server_update", json.dumps({
                "server_id": selected.id,
                "current_users": selected.current_users
            }))
        
        return selected.id
    
    @staticmethod
    def add_new_server(db: Session, name: str, ip: str, port: int, max_users: int) -> int:
        new_server = ServerMapping(
            server_name=name,
            server_ip=ip,
            server_port=port,
            max_users=max_users,
            current_users=0,
            is_active=True
        )
        db.add(new_server)
        db.commit()
        db.refresh(new_server)
        
        if REDIS_AVAILABLE:
            redis_client.publish("server_added", json.dumps({
                "server_id": new_server.id,
                "server_ip": ip,
                "server_port": port
            }))
        
        return new_server.id

# ============================================
# سرویس کش (Cache Manager)
# ============================================

class CacheManager:
    
    @staticmethod
    def get_feed_cache(user_id: int, limit: int = 20) -> Optional[List[Dict]]:
        if not REDIS_AVAILABLE:
            return None
        
        key = f"feed:{user_id}:{limit}"
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    @staticmethod
    def set_feed_cache(user_id: int, data: List[Dict], limit: int = 20):
        if not REDIS_AVAILABLE:
            return
        
        key = f"feed:{user_id}:{limit}"
        redis_client.setex(key, 60, json.dumps(data))  # ۱ دقیقه کش
    
    @staticmethod
    def invalidate_feed_cache(user_id: int):
        if not REDIS_AVAILABLE:
            return
        
        pattern = f"feed:{user_id}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    
    @staticmethod
    def get_user_cache(user_id: int) -> Optional[Dict]:
        if not REDIS_AVAILABLE:
            return None
        
        key = f"user:{user_id}"
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    @staticmethod
    def set_user_cache(user_id: int, data: Dict):
        if not REDIS_AVAILABLE:
            return
        
        key = f"user:{user_id}"
        redis_client.setex(key, 600, json.dumps(data))  # ۱۰ دقیقه
    
    @staticmethod
    def invalidate_user_cache(user_id: int):
        if not REDIS_AVAILABLE:
            return
        
        redis_client.delete(f"user:{user_id}")
    
    @staticmethod
    def get_video_cache(video_id: int) -> Optional[Dict]:
        if not REDIS_AVAILABLE:
            return None
        
        key = f"video:{video_id}"
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    @staticmethod
    def set_video_cache(video_id: int, data: Dict):
        if not REDIS_AVAILABLE:
            return
        
        key = f"video:{video_id}"
        redis_client.setex(key, 300, json.dumps(data))  # ۵ دقیقه
    
    @staticmethod
    def invalidate_video_cache(video_id: int):
        if not REDIS_AVAILABLE:
            return
        
        redis_client.delete(f"video:{video_id}")
    
    @staticmethod
    def get_online_users() -> List[int]:
        if not REDIS_AVAILABLE:
            return []
        
        keys = redis_client.keys("online:*")
        return [int(k.split(":")[1]) for k in keys]

# ============================================
# سرویس ذخیره‌سازی
# ============================================

class StorageService:
    
    @staticmethod
    async def upload_video(video_data: bytes, user_id: int, filename: str) -> str:
        ext = filename.split('.')[-1] if '.' in filename else 'mp4'
        unique_name = f"{uuid.uuid4()}.{ext}"
        file_path = f"videos/{user_id}/{unique_name}"
        
        if S3_AVAILABLE:
            try:
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=file_path,
                    Body=video_data,
                    ACL='public-read',
                    ContentType='video/mp4',
                    Metadata={'user_id': str(user_id), 'filename': filename}
                )
                return f"{S3_ENDPOINT}/{S3_BUCKET}/{file_path}"
            except Exception as e:
                logging.error(f"S3 upload error: {e}")
                # Fallback to local
        
        # ذخیره محلی
        os.makedirs(f"./storage/{user_id}", exist_ok=True)
        local_path = f"./storage/{file_path}"
        with open(local_path, "wb") as f:
            f.write(video_data)
        
        return f"/static/{file_path}"
    
    @staticmethod
    async def upload_avatar(avatar_data: bytes, user_id: int) -> str:
        unique_name = f"{uuid.uuid4()}.jpg"
        file_path = f"avatars/{user_id}/{unique_name}"
        
        if S3_AVAILABLE:
            try:
                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=file_path,
                    Body=avatar_data,
                    ACL='public-read',
                    ContentType='image/jpeg'
                )
                return f"{S3_ENDPOINT}/{S3_BUCKET}/{file_path}"
            except:
                pass
        
        os.makedirs(f"./storage/avatars/{user_id}", exist_ok=True)
        local_path = f"./storage/{file_path}"
        with open(local_path, "wb") as f:
            f.write(avatar_data)
        
        return f"/static/{file_path}"

# ============================================
# سرویس اعلان‌ها (Notification Service)
# ============================================

class NotificationService:
    
    @staticmethod
    async def create_notification(db: Session, user_id: int, type: str, content: str, link: str = None):
        notification = Notification(
            user_id=user_id,
            type=type,
            content=content,
            link=link
        )
        db.add(notification)
        db.commit()
        
        # ارسال نوتیفیکیشن از طریق WebSocket
        if REDIS_AVAILABLE:
            redis_client.publish(f"notifications:{user_id}", json.dumps({
                "type": type,
                "content": content,
                "link": link,
                "created_at": datetime.utcnow().isoformat()
            }))
    
    @staticmethod
    def get_unread_count(user_id: int, db: Session) -> int:
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()

# ============================================
# اپلیکیشن FastAPI
# ============================================

app = FastAPI(
    title="ساده‌گرام - نسخه حرفه‌ای",
    description="پلتفرم اشتراک ویدیو با مدیریت کامل",
    version="2.0.0"
)

# ایجاد پوشه‌ها
os.makedirs("./storage", exist_ok=True)
os.makedirs("./static", exist_ok=True)

# ============================================
# WebSocket برای چت
# ============================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        if REDIS_AVAILABLE:
            redis_client.setex(f"online:{user_id}", 300, "1")
    
    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if REDIS_AVAILABLE:
            redis_client.delete(f"online:{user_id}")
    
    async def send_message(self, receiver_id: int, message: dict):
        if receiver_id in self.active_connections:
            try:
                await self.active_connections[receiver_id].send_json(message)
                return True
            except:
                self.disconnect(receiver_id)
        return False

manager = ConnectionManager()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # احراز هویت از طریق توکن
    db = SessionLocal()
    user = get_current_user(token, db)
    if not user:
        await websocket.close(code=1008)
        db.close()
        return
    
    user_id = user.id
    await manager.connect(websocket, user_id)
    
    # ذخیره وضعیت آنلاین
    if REDIS_AVAILABLE:
        redis_client.setex(f"online:{user_id}", 300, "1")
    
    # ارسال پیام‌های خوانده نشده
    unread = db.query(Message).filter(
        Message.receiver_id == user_id,
        Message.is_read == False
    ).order_by(Message.created_at).all()
    
    for msg in unread:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        await websocket.send_json({
            "type": "message",
            "data": {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "sender_username": sender.username if sender else "نامشخص"
            }
        })
        msg.is_read = True
        msg.read_at = datetime.utcnow()
    db.commit()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                receiver_id = data.get("receiver_id")
                content = data.get("content")
                
                if not receiver_id or not content:
                    continue
                
                # ذخیره در دیتابیس
                new_message = Message(
                    sender_id=user_id,
                    receiver_id=receiver_id,
                    content=content
                )
                db.add(new_message)
                db.commit()
                db.refresh(new_message)
                
                # ارسال به گیرنده
                receiver_user = db.query(User).filter(User.id == receiver_id).first()
                message_data = {
                    "type": "message",
                    "data": {
                        "id": new_message.id,
                        "sender_id": user_id,
                        "content": content,
                        "created_at": new_message.created_at.isoformat(),
                        "sender_username": user.username,
                        "sender_avatar": user.avatar_url
                    }
                }
                
                # تلاش برای ارسال فوری
                sent = await manager.send_message(receiver_id, message_data)
                
                # اگر گیرنده آفلاین بود، به عنوان پیام خوانده نشده ذخیره می‌شود
                if not sent and REDIS_AVAILABLE:
                    redis_client.lpush(f"offline_messages:{receiver_id}", json.dumps(message_data))
                    redis_client.ltrim(f"offline_messages:{receiver_id}", 0, 99)
                
                # ارسال تایید به فرستنده
                await websocket.send_json({
                    "type": "sent",
                    "data": {"id": new_message.id}
                })
                
                # نوتیفیکیشن
                if sent:
                    await NotificationService.create_notification(
                        db=db,
                        user_id=receiver_id,
                        type="message",
                        content=f"{user.username}: {content[:50]}",
                        link=f"/chat/{user_id}"
                    )
            
            elif data.get("type") == "typing":
                receiver_id = data.get("receiver_id")
                if receiver_id:
                    await manager.send_message(receiver_id, {
                        "type": "typing",
                        "data": {"user_id": user_id}
                    })
            
            elif data.get("type") == "read":
                message_id = data.get("message_id")
                if message_id:
                    msg = db.query(Message).filter(Message.id == message_id).first()
                    if msg and msg.receiver_id == user_id:
                        msg.is_read = True
                        msg.read_at = datetime.utcnow()
                        db.commit()
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        db.close()
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)
        db.close()

# ============================================
# APIها
# ============================================

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    print("✅ دیتابیس راه‌اندازی شد")
    
    # سرور پیش‌فرض
    db = SessionLocal()
    existing = db.query(ServerMapping).filter(ServerMapping.server_name == "server-1").first()
    if not existing:
        default = ServerMapping(
            server_name="server-1",
            server_ip="127.0.0.1",
            server_port=8000,
            max_users=MAX_USERS_PER_SERVER,
            current_users=0
        )
        db.add(default)
        db.commit()
    db.close()

# ========== احراز هویت ==========

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(lambda: SessionLocal())):
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="نام کاربری یا ایمیل تکراری است")
    
    server_id = ShardingService.assign_user_to_server(db)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name or user_data.username,
        server_id=server_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"user_id": new_user.id})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(new_user)
    }

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(lambda: SessionLocal())):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="نام کاربری یا رمز عبور اشتباه است")
    
    token = create_access_token({"user_id": user.id})
    
    # به‌روزرسانی آخرین بازدید
    user.last_seen = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(token: str, db: Session = Depends(lambda: SessionLocal())):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    return user

# ========== ویدیوها ==========

@app.post("/api/videos/upload")
async def upload_video(
    token: str,
    video: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_private: bool = Form(False),
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    content = await video.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم ویدیو نباید بیشتر از ۱۰ مگابایت باشد")
    
    video_url = await StorageService.upload_video(content, user.id, video.filename)
    
    new_video = Video(
        user_id=user.id,
        title=title or video.filename,
        description=description or "",
        video_url=video_url,
        size_mb=len(content) // (1024 * 1024),
        is_private=is_private
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    
    # به‌روزرسانی تعداد ویدیوهای کاربر
    user.videos_count += 1
    db.commit()
    
    # پاک کردن کش فید
    CacheManager.invalidate_feed_cache(user.id)
    
    return {
        "success": True,
        "video_id": new_video.id,
        "video_url": video_url
    }

@app.get("/api/videos/feed")
async def get_feed(
    token: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    # بررسی کش
    cached = CacheManager.get_feed_cache(user.id, limit)
    if cached:
        return cached
    
    # دریافت آیدی‌های فالو شده
    following = db.query(Follow.following_id).filter(Follow.follower_id == user.id).all()
    following_ids = [f[0] for f in following] + [user.id]
    
    # دریافت ویدیوها
    videos = db.query(Video).filter(
        Video.user_id.in_(following_ids),
        Video.is_active == True,
        Video.is_private == False
    ).order_by(Video.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for v in videos:
        v_user = db.query(User).filter(User.id == v.user_id).first()
        is_liked = db.query(Like).filter(
            Like.user_id == user.id,
            Like.video_id == v.id
        ).first() is not None
        
        result.append({
            "id": v.id,
            "user_id": v.user_id,
            "title": v.title,
            "description": v.description,
            "video_url": v.video_url,
            "thumbnail_url": v.thumbnail_url,
            "duration": v.duration,
            "views": v.views,
            "likes_count": v.likes_count,
            "comments_count": v.comments_count,
            "shares_count": v.shares_count,
            "is_private": v.is_private,
            "created_at": v.created_at.isoformat(),
            "username": v_user.username if v_user else None,
            "user_avatar": v_user.avatar_url if v_user else None,
            "is_liked": is_liked
        })
    
    # ذخیره در کش
    CacheManager.set_feed_cache(user.id, result, limit)
    
    return result

@app.get("/api/videos/{video_id}")
async def get_video(
    video_id: int,
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    # بررسی کش
    cached = CacheManager.get_video_cache(video_id)
    if cached:
        return cached
    
    video = db.query(Video).filter(Video.id == video_id, Video.is_active == True).first()
    if not video:
        raise HTTPException(status_code=404, detail="ویدیو یافت نشد")
    
    # افزایش بازدید
    video.views += 1
    db.commit()
    
    v_user = db.query(User).filter(User.id == video.user_id).first()
    is_liked = db.query(Like).filter(
        Like.user_id == user.id,
        Like.video_id == video.id
    ).first() is not None
    
    result = {
        "id": video.id,
        "user_id": video.user_id,
        "title": video.title,
        "description": video.description,
        "video_url": video.video_url,
        "thumbnail_url": video.thumbnail_url,
        "duration": video.duration,
        "views": video.views,
        "likes_count": video.likes_count,
        "comments_count": video.comments_count,
        "shares_count": video.shares_count,
        "is_private": video.is_private,
        "created_at": video.created_at.isoformat(),
        "username": v_user.username if v_user else None,
        "user_avatar": v_user.avatar_url if v_user else None,
        "is_liked": is_liked
    }
    
    # ذخیره در کش
    CacheManager.set_video_cache(video_id, result)
    
    return result

@app.post("/api/videos/{video_id}/like")
async def like_video(
    video_id: int,
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    video = db.query(Video).filter(Video.id == video_id, Video.is_active == True).first()
    if not video:
        raise HTTPException(status_code=404, detail="ویدیو یافت نشد")
    
    existing = db.query(Like).filter(
        Like.user_id == user.id,
        Like.video_id == video_id
    ).first()
    
    if existing:
        db.delete(existing)
        video.likes_count -= 1
        db.commit()
        CacheManager.invalidate_video_cache(video_id)
        return {"success": True, "liked": False}
    
    new_like = Like(
        user_id=user.id,
        video_id=video_id
    )
    db.add(new_like)
    video.likes_count += 1
    db.commit()
    CacheManager.invalidate_video_cache(video_id)
    
    return {"success": True, "liked": True}

# ========== کامنت‌ها ==========

@app.post("/api/videos/{video_id}/comments", response_model=CommentResponse)
async def add_comment(
    video_id: int,
    comment_data: CommentCreate,
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    video = db.query(Video).filter(Video.id == video_id, Video.is_active == True).first()
    if not video:
        raise HTTPException(status_code=404, detail="ویدیو یافت نشد")
    
    # بررسی parent_id
    if comment_data.parent_id:
        parent = db.query(Comment).filter(Comment.id == comment_data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="کامنت والد یافت نشد")
    
    new_comment = Comment(
        user_id=user.id,
        video_id=video_id,
        parent_id=comment_data.parent_id,
        content=comment_data.content
    )
    db.add(new_comment)
    video.comments_count += 1
    db.commit()
    db.refresh(new_comment)
    
    CacheManager.invalidate_video_cache(video_id)
    
    return {
        "id": new_comment.id,
        "user_id": new_comment.user_id,
        "video_id": new_comment.video_id,
        "parent_id": new_comment.parent_id,
        "content": new_comment.content,
        "likes_count": new_comment.likes_count,
        "created_at": new_comment.created_at,
        "username": user.username,
        "user_avatar": user.avatar_url
    }

# ========== فالو ==========

@app.post("/api/users/{user_id}/follow")
async def follow_user(
    user_id: int,
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    if user.id == user_id:
        raise HTTPException(status_code=400, detail="نمی‌توانید خودتان را دنبال کنید")
    
    target = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not target:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    existing = db.query(Follow).filter(
        Follow.follower_id == user.id,
        Follow.following_id == user_id
    ).first()
    
    if existing:
        db.delete(existing)
        user.following_count -= 1
        target.followers_count -= 1
        db.commit()
        CacheManager.invalidate_user_cache(user_id)
        return {"success": True, "following": False}
    
    new_follow = Follow(
        follower_id=user.id,
        following_id=user_id
    )
    db.add(new_follow)
    user.following_count += 1
    target.followers_count += 1
    db.commit()
    CacheManager.invalidate_user_cache(user_id)
    
    return {"success": True, "following": True}

# ========== پیام‌ها (چت) ==========

@app.get("/api/messages/conversations")
async def get_conversations(
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    # دریافت آخرین پیام با هر کاربر
    # کوئری پیچیده برای گرفتن آخرین پیام هر مکالمه
    result = []
    
    # روش ساده: دریافت همه کاربرانی که با آنها پیام داشتیم
    sent_to = db.query(Message.receiver_id).filter(Message.sender_id == user.id).distinct().all()
    received_from = db.query(Message.sender_id).filter(Message.receiver_id == user.id).distinct().all()
    
    user_ids = set([u[0] for u in sent_to] + [u[0] for u in received_from])
    
    for uid in user_ids:
        if uid == user.id:
            continue
        other = db.query(User).filter(User.id == uid, User.is_active == True).first()
        if not other:
            continue
        
        # آخرین پیام
        last_msg = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user.id, Message.receiver_id == uid),
                and_(Message.sender_id == uid, Message.receiver_id == user.id)
            )
        ).order_by(Message.created_at.desc()).first()
        
        # تعداد پیام‌های خوانده نشده
        unread = db.query(Message).filter(
            Message.sender_id == uid,
            Message.receiver_id == user.id,
            Message.is_read == False
        ).count()
        
        result.append({
            "user_id": other.id,
            "username": other.username,
            "avatar_url": other.avatar_url,
            "last_message": last_msg.content if last_msg else "",
            "last_message_time": last_msg.created_at.isoformat() if last_msg else None,
            "unread_count": unread,
            "is_online": user_id in CacheManager.get_online_users()
        })
    
    # مرتب‌سازی بر اساس آخرین پیام
    result.sort(key=lambda x: x.get("last_message_time", ""), reverse=True)
    
    return result

@app.get("/api/messages/{other_user_id}")
async def get_messages(
    other_user_id: int,
    token: str,
    limit: int = 50,
    before: Optional[str] = None,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    other = db.query(User).filter(User.id == other_user_id, User.is_active == True).first()
    if not other:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    # خوانده شدن پیام‌ها
    db.query(Message).filter(
        Message.sender_id == other_user_id,
        Message.receiver_id == user.id,
        Message.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()
    
    # دریافت پیام‌ها
    query = db.query(Message).filter(
        or_(
            and_(Message.sender_id == user.id, Message.receiver_id == other_user_id),
            and_(Message.sender_id == other_user_id, Message.receiver_id == user.id)
        )
    )
    
    if before:
        query = query.filter(Message.created_at < before)
    
    messages = query.order_by(Message.created_at.desc()).limit(limit).all()
    
    return [{
        "id": m.id,
        "sender_id": m.sender_id,
        "receiver_id": m.receiver_id,
        "content": m.content,
        "is_read": m.is_read,
        "created_at": m.created_at.isoformat(),
        "is_mine": m.sender_id == user.id
    } for m in messages[::-1]]

# ========== پنل مدیریت ==========

@app.get("/admin/stats", response_model=AdminStatsResponse)
async def admin_stats(
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="دسترسی محدود به ادمین")
    
    today = datetime.utcnow().date()
    today_start = datetime(today.year, today.month, today.day)
    
    return {
        "total_users": db.query(User).filter(User.is_active == True).count(),
        "total_videos": db.query(Video).filter(Video.is_active == True).count(),
        "total_views": db.query(Video).filter(Video.is_active == True).with_entities(func.sum(Video.views)).scalar() or 0,
        "total_comments": db.query(Comment).count(),
        "active_users_today": db.query(User).filter(User.last_seen >= today_start).count(),
        "new_users_today": db.query(User).filter(User.created_at >= today_start).count(),
        "new_videos_today": db.query(Video).filter(Video.created_at >= today_start).count(),
        "premium_users": db.query(User).filter(User.is_premium == True).count(),
        "server_count": db.query(ServerMapping).filter(ServerMapping.is_active == True).count(),
        "storage_used_gb": 0  # محاسبه بعداً
    }

@app.get("/admin/users")
async def admin_users(
    token: str,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="دسترسی محدود به ادمین")
    
    query = db.query(User).filter(User.is_active == True)
    
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": [{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "is_premium": u.is_premium,
            "is_verified": u.is_verified,
            "videos_count": u.videos_count,
            "followers_count": u.followers_count,
            "server_id": u.server_id,
            "created_at": u.created_at.isoformat()
        } for u in users]
    }

@app.post("/admin/users/{user_id}/toggle-premium")
async def toggle_premium(
    user_id: int,
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="دسترسی محدود به ادمین")
    
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    
    target.is_premium = not target.is_premium
    db.commit()
    
    return {"success": True, "is_premium": target.is_premium}

@app.post("/admin/servers/add")
async def add_server(
    server_data: AddServerRequest,
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="دسترسی محدود به ادمین")
    
    existing = db.query(ServerMapping).filter(
        ServerMapping.server_name == server_data.server_name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="این نام سرور قبلاً ثبت شده است")
    
    server_id = ShardingService.add_new_server(
        db=db,
        name=server_data.server_name,
        ip=server_data.server_ip,
        port=server_data.server_port,
        max_users=server_data.max_users
    )
    
    return {
        "success": True,
        "server_id": server_id,
        "message": f"سرور {server_data.server_name} با موفقیت اضافه شد"
    }

@app.get("/admin/servers/status")
async def get_servers_status(
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="دسترسی محدود به ادمین")
    
    servers = db.query(ServerMapping).all()
    
    return {
        "total_servers": len(servers),
        "servers": [
            {
                "id": s.id,
                "name": s.server_name,
                "ip": s.server_ip,
                "port": s.server_port,
                "max_users": s.max_users,
                "current_users": s.current_users,
                "load_percent": round((s.current_users / s.max_users) * 100, 2) if s.max_users > 0 else 0,
                "is_active": s.is_active
            }
            for s in servers
        ]
    }

# ============================================
# صفحه اصلی (HTML کامل با چیدمان اینستاگرامی)
# ============================================

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ساده‌گرام</title>
    <style>
        /* ===== RESET & BASE ===== */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: #fafafa;
            color: #262626;
            padding-bottom: 70px;
        }
        a { text-decoration: none; color: inherit; }
        
        /* ===== HEADER ===== */
        .header {
            background: white;
            border-bottom: 1px solid #dbdbdb;
            padding: 12px 16px;
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header .logo {
            font-size: 22px;
            font-weight: bold;
            background: linear-gradient(45deg, #405de6, #5851db, #833ab4, #c13584, #e1306c, #fd1d1d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header .icons {
            display: flex;
            gap: 20px;
            font-size: 24px;
        }
        .header .icons span { cursor: pointer; }
        .header .icons .badge {
            position: relative;
        }
        .header .icons .badge::after {
            content: '';
            position: absolute;
            top: -2px;
            right: -2px;
            width: 10px;
            height: 10px;
            background: #ed4956;
            border-radius: 50%;
            border: 2px solid white;
        }
        
        /* ===== TABS ===== */
        .bottom-tabs {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            border-top: 1px solid #dbdbdb;
            display: flex;
            justify-content: space-around;
            padding: 8px 0;
            z-index: 100;
        }
        .bottom-tabs .tab {
            font-size: 26px;
            cursor: pointer;
            padding: 4px 16px;
            border-radius: 8px;
            transition: 0.3s;
            color: #8e8e8e;
        }
        .bottom-tabs .tab.active {
            color: #262626;
        }
        .bottom-tabs .tab .label {
            font-size: 10px;
            display: block;
            text-align: center;
            margin-top: 2px;
        }
        
        /* ===== FEED ===== */
        .feed-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 8px 0;
        }
        
        /* ===== VIDEO POST ===== */
        .post {
            background: white;
            margin-bottom: 16px;
            border-radius: 8px;
            border: 1px solid #dbdbdb;
            overflow: hidden;
        }
        .post-header {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            gap: 12px;
        }
        .post-header .avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #ddd;
            overflow: hidden;
            flex-shrink: 0;
        }
        .post-header .avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .post-header .username {
            font-weight: 600;
            font-size: 14px;
        }
        .post-header .time {
            color: #8e8e8e;
            font-size: 12px;
            margin-right: auto;
        }
        .post-header .verified {
            color: #0095f6;
            font-size: 14px;
        }
        
        .post-video {
            position: relative;
            background: #000;
        }
        .post-video video {
            width: 100%;
            max-height: 500px;
            display: block;
        }
        .post-video .duration {
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        
        .post-actions {
            display: flex;
            padding: 8px 16px;
            gap: 16px;
            align-items: center;
        }
        .post-actions .btn {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            transition: 0.2s;
            padding: 4px;
        }
        .post-actions .btn:hover { transform: scale(1.1); }
        .post-actions .btn.liked { color: #ed4956; }
        .post-actions .stats {
            display: flex;
            gap: 16px;
            color: #8e8e8e;
            font-size: 14px;
            margin-right: auto;
        }
        .post-actions .stats span { display: flex; align-items: center; gap: 4px; }
        
        .post-caption {
            padding: 0 16px 8px;
            font-size: 14px;
        }
        .post-caption .uname { font-weight: 600; }
        .post-caption .text { margin-right: 6px; }
        
        .post-comments {
            padding: 0 16px 12px;
            border-top: 1px solid #efefef;
            margin-top: 8px;
        }
        .post-comments .comment {
            display: flex;
            gap: 8px;
            padding: 4px 0;
            font-size: 14px;
            align-items: flex-start;
        }
        .post-comments .comment .c-uname {
            font-weight: 600;
            flex-shrink: 0;
        }
        .post-comments .comment .c-text {
            word-break: break-word;
        }
        .post-comments .comment-form {
            display: flex;
            gap: 8px;
            padding-top: 8px;
            border-top: 1px solid #efefef;
            margin-top: 8px;
        }
        .post-comments .comment-form input {
            flex: 1;
            border: none;
            outline: none;
            font-size: 14px;
            padding: 8px 0;
        }
        .post-comments .comment-form button {
            background: none;
            border: none;
            color: #0095f6;
            font-weight: 600;
            cursor: pointer;
            font-size: 14px;
        }
        .post-comments .comment-form button:disabled { opacity: 0.3; cursor: default; }
        
        /* ===== UPLOAD ===== */
        .upload-container {
            max-width: 500px;
            margin: 20px auto;
            padding: 0 16px;
        }
        .upload-box {
            background: white;
            border: 2px dashed #dbdbdb;
            border-radius: 16px;
            padding: 40px 20px;
            text-align: center;
        }
        .upload-box .icon { font-size: 48px; }
        .upload-box h3 { margin: 16px 0 8px; }
        .upload-box p { color: #8e8e8e; font-size: 14px; }
        .upload-box input[type="file"] { display: none; }
        .upload-box .btn-upload {
            background: #0095f6;
            color: white;
            border: none;
            padding: 10px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 16px;
        }
        .upload-box .btn-upload:hover { background: #1877f2; }
        .upload-form { margin-top: 20px; }
        .upload-form input, .upload-form textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #dbdbdb;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 12px;
        }
        .upload-form textarea { resize: vertical; min-height: 60px; }
        .upload-form .checkbox { display: flex; align-items: center; gap: 8px; }
        .upload-form .checkbox input { width: auto; margin: 0; }
        
        /* ===== PROFILE ===== */
        .profile-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
        }
        .profile-header {
            display: flex;
            gap: 24px;
            align-items: center;
            padding: 16px 0;
        }
        .profile-header .avatar {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: #ddd;
            overflow: hidden;
            flex-shrink: 0;
        }
        .profile-header .avatar img { width: 100%; height: 100%; object-fit: cover; }
        .profile-header .info { flex: 1; }
        .profile-header .info .name { font-size: 20px; font-weight: 600; }
        .profile-header .info .username { color: #8e8e8e; font-size: 14px; }
        .profile-header .info .bio { margin-top: 4px; font-size: 14px; }
        .profile-stats {
            display: flex;
            gap: 24px;
            padding: 12px 0;
            border-top: 1px solid #dbdbdb;
            border-bottom: 1px solid #dbdbdb;
        }
        .profile-stats .stat { text-align: center; }
        .profile-stats .stat .num { font-weight: 600; font-size: 18px; }
        .profile-stats .stat .label { color: #8e8e8e; font-size: 12px; }
        
        .profile-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 2px;
            padding-top: 2px;
        }
        .profile-grid .item {
            aspect-ratio: 1;
            background: #ddd;
            overflow: hidden;
            position: relative;
        }
        .profile-grid .item img, .profile-grid .item video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .profile-grid .item .overlay {
            position: absolute;
            inset: 0;
            background: rgba(0,0,0,0.4);
            display: none;
            align-items: center;
            justify-content: center;
            color: white;
            gap: 16px;
        }
        .profile-grid .item:hover .overlay { display: flex; }
        
        /* ===== CHAT ===== */
        .chat-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
        }
        .chat-list {
            background: white;
            border-radius: 8px;
            border: 1px solid #dbdbdb;
        }
        .chat-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            border-bottom: 1px solid #efefef;
            cursor: pointer;
        }
        .chat-item:last-child { border-bottom: none; }
        .chat-item .avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: #ddd;
            overflow: hidden;
            flex-shrink: 0;
        }
        .chat-item .avatar img { width: 100%; height: 100%; object-fit: cover; }
        .chat-item .info { flex: 1; }
        .chat-item .info .name { font-weight: 600; }
        .chat-item .info .last-msg {
            color: #8e8e8e;
            font-size: 14px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }
        .chat-item .badge {
            background: #0095f6;
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
        }
        .chat-item .online {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #31a24c;
            flex-shrink: 0;
        }
        
        .chat-messages {
            background: white;
            border-radius: 8px;
            border: 1px solid #dbdbdb;
            height: 400px;
            overflow-y: auto;
            padding: 16px;
        }
        .chat-messages .msg {
            max-width: 70%;
            padding: 8px 12px;
            border-radius: 16px;
            margin-bottom: 8px;
            word-break: break-word;
        }
        .chat-messages .msg.mine {
            background: #0095f6;
            color: white;
            margin-left: auto;
            border-bottom-left-radius: 4px;
        }
        .chat-messages .msg.other {
            background: #efefef;
            color: #262626;
            margin-right: auto;
            border-bottom-right-radius: 4px;
        }
        .chat-messages .msg .time {
            font-size: 10px;
            opacity: 0.6;
            display: block;
            margin-top: 4px;
        }
        .chat-input {
            display: flex;
            gap: 8px;
            padding: 12px 0;
        }
        .chat-input input {
            flex: 1;
            padding: 10px 16px;
            border: 1px solid #dbdbdb;
            border-radius: 24px;
            outline: none;
            font-size: 14px;
        }
        .chat-input input:focus { border-color: #0095f6; }
        .chat-input button {
            background: #0095f6;
            color: white;
            border: none;
            border-radius: 24px;
            padding: 10px 20px;
            font-weight: 600;
            cursor: pointer;
        }
        .chat-input button:disabled { opacity: 0.5; }
        
        /* ===== ADMIN ===== */
        .admin-container {
            max-width: 800px;
            margin: 20px auto;
            padding: 0 16px;
        }
        .admin-card {
            background: white;
            border-radius: 8px;
            border: 1px solid #dbdbdb;
            padding: 20px;
            margin-bottom: 16px;
        }
        .admin-card h2 { font-size: 18px; margin-bottom: 12px; }
        .admin-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
        }
        .admin-stats .stat {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }
        .admin-stats .stat .num { font-size: 24px; font-weight: 700; }
        .admin-stats .stat .label { color: #8e8e8e; font-size: 12px; }
        .admin-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .admin-table th, .admin-table td {
            padding: 8px 12px;
            border-bottom: 1px solid #efefef;
            text-align: right;
        }
        .admin-table th { background: #f8f9fa; font-weight: 600; }
        .admin-table .badge-success { color: #31a24c; }
        .admin-table .badge-danger { color: #ed4956; }
        
        /* ===== MODAL ===== */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.5);
            z-index: 200;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal-overlay.show { display: flex; }
        .modal {
            background: white;
            border-radius: 16px;
            max-width: 500px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
            padding: 24px;
        }
        .modal .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .modal .modal-header h2 { font-size: 20px; }
        .modal .modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
        }
        
        /* ===== UTILITY ===== */
        .hidden { display: none !important; }
        .text-center { text-align: center; }
        .mt-16 { margin-top: 16px; }
        .mb-16 { margin-bottom: 16px; }
        
        /* ===== RESPONSIVE ===== */
        @media (max-width: 600px) {
            .header .logo { font-size: 18px; }
            .bottom-tabs .tab { font-size: 22px; padding: 4px 12px; }
            .post-header .username { font-size: 13px; }
        }
    </style>
</head>
<body>

<!-- ===== HEADER ===== -->
<header class="header">
    <div class="logo">📸 ساده‌گرام</div>
    <div class="icons">
        <span onclick="showTab('chat')">💬</span>
        <span onclick="showTab('upload')">➕</span>
        <span class="badge" onclick="showTab('profile')">👤</span>
    </div>
</header>

<!-- ===== CONTENT ===== -->
<div id="content"></div>

<!-- ===== BOTTOM TABS ===== -->
<nav class="bottom-tabs">
    <div class="tab active" onclick="showTab('feed')" data-tab="feed">
        🏠
        <span class="label">فید</span>
    </div>
    <div class="tab" onclick="showTab('explore')" data-tab="explore">
        🔍
        <span class="label">جستجو</span>
    </div>
    <div class="tab" onclick="showTab('upload')" data-tab="upload">
        ➕
        <span class="label">آپلود</span>
    </div>
    <div class="tab" onclick="showTab('chat')" data-tab="chat">
        💬
        <span class="label">چت</span>
    </div>
    <div class="tab" onclick="showTab('profile')" data-tab="profile">
        👤
        <span class="label">پروفایل</span>
    </div>
</nav>

<!-- ===== MODAL ===== -->
<div class="modal-overlay" id="modal">
    <div class="modal">
        <div class="modal-header">
            <h2 id="modal-title">عنوان</h2>
            <button class="modal-close" onclick="closeModal()">✕</button>
        </div>
        <div id="modal-body"></div>
    </div>
</div>

<script>
// ============================================
// STATE
// ============================================
let token = localStorage.getItem('token') || '';
let currentUser = null;
let currentTab = 'feed';
let ws = null;
let wsReconnectTimer = null;

// ============================================
// TOAST
// ============================================
function showToast(msg, type = 'info') {
    const existing = document.querySelector('.toast-global');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = 'toast-global';
    toast.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'error' ? '#ed4956' : '#262626'};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        z-index: 999;
        font-size: 14px;
        max-width: 90%;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        transition: opacity 0.3s;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
}

// ============================================
// AUTH
// ============================================
async function login(username, password) {
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });
        const data = await res.json();
        if (data.access_token) {
            token = data.access_token;
            localStorage.setItem('token', token);
            currentUser = data.user;
            showToast('✅ خوش آمدید!');
            showTab('feed');
            connectWebSocket();
            return true;
        }
        showToast('❌ ' + (data.detail || 'خطا'), 'error');
        return false;
    } catch (e) {
        showToast('❌ خطا در ارتباط با سرور', 'error');
        return false;
    }
}

async function register(username, email, password, fullName) {
    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, full_name: fullName })
        });
        const data = await res.json();
        if (data.access_token) {
            token = data.access_token;
            localStorage.setItem('token', token);
            currentUser = data.user;
            showToast('✅ ثبت‌نام موفق!');
            showTab('feed');
            connectWebSocket();
            return true;
        }
        showToast('❌ ' + (data.detail || 'خطا'), 'error');
        return false;
    } catch (e) {
        showToast('❌ خطا در ارتباط با سرور', 'error');
        return false;
    }
}

function logout() {
    token = '';
    localStorage.removeItem('token');
    currentUser = null;
    if (ws) { ws.close(); ws = null; }
    showToast('👋 خروج موفق');
    showTab('feed');
}

// ============================================
// TAB MANAGEMENT
// ============================================
function showTab(tab) {
    currentTab = tab;
    
    // Highlight tab
    document.querySelectorAll('.bottom-tabs .tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    
    // Load content
    const container = document.getElementById('content');
    switch(tab) {
        case 'feed': loadFeed(container); break;
        case 'explore': loadExplore(container); break;
        case 'upload': loadUpload(container); break;
        case 'chat': loadChat(container); break;
        case 'profile': loadProfile(container); break;
        case 'admin': loadAdmin(container); break;
        default: container.innerHTML = '<p>صفحه در حال ساخت...</p>';
    }
}

// ============================================
// FEED
// ============================================
async function loadFeed(container) {
    if (!token) {
        container.innerHTML = buildAuthForm();
        return;
    }
    
    container.innerHTML = `<div class="feed-container"><p style="text-align:center;padding:40px;">⏳ بارگذاری...</p></div>`;
    
    try {
        const res = await fetch('/api/videos/feed?limit=20', {
            headers: { 'token': token }
        });
        const data = await res.json();
        
        if (!Array.isArray(data)) {
            container.innerHTML = `<div class="feed-container"><p style="text-align:center;padding:40px;">${data.detail || 'خطا'}</p></div>`;
            return;
        }
        
        if (data.length === 0) {
            container.innerHTML = `
                <div class="feed-container">
                    <div style="text-align:center;padding:60px 20px;">
                        <div style="font-size:48px;">📹</div>
                        <h3 style="margin:16px 0;">هنوز ویدیویی در فید شما نیست</h3>
                        <p style="color:#8e8e8e;">افراد را دنبال کنید یا اولین ویدیو را آپلود کنید</p>
                        <button class="btn-upload" onclick="showTab('explore')" style="margin-top:16px;background:#0095f6;color:white;border:none;padding:10px 30px;border-radius:8px;font-size:16px;cursor:pointer;">🔍 جستجو</button>
                    </div>
                </div>
            `;
            return;
        }
        
        let html = '<div class="feed-container">';
        for (const v of data) {
            html += buildPost(v);
        }
        html += '</div>';
        container.innerHTML = html;
        
        // اتصال event listener برای کامنت‌ها
        document.querySelectorAll('.comment-form button').forEach(btn => {
            btn.onclick = function() {
                const videoId = this.dataset.videoId;
                const input = document.getElementById(`comment-input-${videoId}`);
                if (input && input.value.trim()) {
                    addComment(videoId, input.value.trim());
                }
            };
        });
        document.querySelectorAll('.comment-form input').forEach(inp => {
            inp.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    const videoId = this.dataset.videoId;
                    if (this.value.trim()) {
                        addComment(videoId, this.value.trim());
                    }
                }
            });
        });
        
    } catch (e) {
        container.innerHTML = `<div class="feed-container"><p style="text-align:center;padding:40px;">❌ خطا: ${e.message}</p></div>`;
    }
}

function buildPost(v) {
    const isLiked = v.is_liked ? 'liked' : '';
    const likeIcon = v.is_liked ? '❤️' : '🤍';
    const videoSrc = v.video_url || '';
    const thumb = v.thumbnail_url || '';
    const avatar = v.user_avatar || '';
    const username = v.username || 'کاربر';
    const time = new Date(v.created_at).toLocaleDateString('fa-IR');
    
    return `
        <div class="post" id="post-${v.id}">
            <div class="post-header">
                <div class="avatar">${avatar ? `<img src="${avatar}" alt="">` : '📷'}</div>
                <span class="username">${username}</span>
                ${v.is_verified ? '<span class="verified">✓</span>' : ''}
                <span class="time">${time}</span>
            </div>
            <div class="post-video">
                <video src="${videoSrc}" controls poster="${thumb}" preload="metadata"></video>
                ${v.duration ? `<span class="duration">${Math.floor(v.duration/60)}:${String(v.duration%60).padStart(2,'0')}</span>` : ''}
            </div>
            <div class="post-actions">
                <button class="btn ${isLiked}" onclick="likeVideo(${v.id})">${likeIcon}</button>
                <button class="btn" onclick="document.getElementById('comment-input-${v.id}').focus()">💬</button>
                <button class="btn" onclick="shareVideo('${v.video_url}')">🔗</button>
                <div class="stats">
                    <span>❤️ ${v.likes_count || 0}</span>
                    <span>💬 ${v.comments_count || 0}</span>
                    <span>👁️ ${v.views || 0}</span>
                </div>
            </div>
            <div class="post-caption">
                <span class="uname">${username}</span>
                <span class="text">${v.description || ''}</span>
            </div>
            <div class="post-comments" id="comments-${v.id}">
                <div id="comments-list-${v.id}"></div>
                <div class="comment-form">
                    <input id="comment-input-${v.id}" data-video-id="${v.id}" placeholder="کامنت بنویسید...">
                    <button data-video-id="${v.id}">ارسال</button>
                </div>
            </div>
        </div>
    `;
}

// ============================================
// EXPLORE
// ============================================
async function loadExplore(container) {
    container.innerHTML = `
        <div style="max-width:600px;margin:16px auto;padding:0 16px;">
            <div style="background:white;border-radius:8px;border:1px solid #dbdbdb;padding:16px;">
                <input id="search-input" placeholder="🔍 جستجوی کاربران..." style="width:100%;padding:12px;border:1px solid #dbdbdb;border-radius:8px;font-size:16px;">
                <div id="search-results" style="margin-top:12px;"></div>
            </div>
            <h3 style="margin:16px 0 12px;">🔥 ویدیوهای محبوب</h3>
            <div id="explore-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:2px;"></div>
        </div>
    `;
    
    // جستجو
    document.getElementById('search-input').addEventListener('input', async function() {
        const q = this.value.trim();
        if (q.length < 2) {
            document.getElementById('search-results').innerHTML = '';
            return;
        }
        try {
            const res = await fetch(`/api/admin/users?search=${encodeURIComponent(q)}&limit=10`, {
                headers: { 'token': token }
            });
            const data = await res.json();
            if (data.users) {
                let html = '';
                for (const u of data.users) {
                    html += `
                        <div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #efefef;">
                            <div style="width:36px;height:36px;border-radius:50%;background:#ddd;"></div>
                            <div>
                                <div style="font-weight:600;">${u.full_name || u.username}</div>
                                <div style="color:#8e8e8e;font-size:12px;">@${u.username}</div>
                            </div>
                            <button onclick="followUser(${u.id})" style="margin-right:auto;background:#0095f6;color:white;border:none;padding:4px 16px;border-radius:4px;cursor:pointer;">دنبال کردن</button>
                        </div>
                    `;
                }
                document.getElementById('search-results').innerHTML = html;
            }
        } catch (e) {}
    });
    
    // ویدیوهای محبوب
    try {
        const res = await fetch('/api/videos/feed?limit=20', {
            headers: { 'token': token }
        });
        const data = await res.json();
        if (Array.isArray(data)) {
            const sorted = [...data].sort((a,b) => (b.likes_count || 0) - (a.likes_count || 0)).slice(0, 12);
            let html = '';
            for (const v of sorted) {
                html += `
                    <div style="aspect-ratio:1;background:#ddd;overflow:hidden;position:relative;">
                        <video src="${v.video_url}" style="width:100%;height:100%;object-fit:cover;" muted></video>
                        <div style="position:absolute;bottom:4px;right:4px;background:rgba(0,0,0,0.7);color:white;padding:2px 8px;border-radius:4px;font-size:12px;">❤️ ${v.likes_count || 0}</div>
                    </div>
                `;
            }
            document.getElementById('explore-grid').innerHTML = html;
        }
    } catch (e) {}
}

// ============================================
// UPLOAD
// ============================================
function loadUpload(container) {
    if (!token) {
        container.innerHTML = buildAuthForm();
        return;
    }
    
    container.innerHTML = `
        <div class="upload-container">
            <div class="upload-box">
                <div class="icon">📤</div>
                <h3>آپلود ویدیو جدید</h3>
                <p>حداکثر ۱۰ مگابایت، تا ۳ دقیقه</p>
                <input type="file" id="video-file-input" accept="video/*">
                <button class="btn-upload" onclick="document.getElementById('video-file-input').click()">انتخاب فایل</button>
                <div id="file-info" style="margin-top:12px;color:#8e8e8e;font-size:14px;"></div>
            </div>
            <div class="upload-form" id="upload-form" style="display:none;">
                <input id="upload-title" placeholder="عنوان (اختیاری)">
                <textarea id="upload-desc" placeholder="توضیحات..."></textarea>
                <div class="checkbox">
                    <input type="checkbox" id="upload-private">
                    <label for="upload-private">خصوصی (فقط فالوکنندگان)</label>
                </div>
                <button class="btn-upload" onclick="uploadVideo()" style="width:100%;background:#0095f6;color:white;border:none;padding:12px;border-radius:8px;font-size:16px;cursor:pointer;">📤 آپلود</button>
                <div id="upload-progress" style="margin-top:12px;text-align:center;"></div>
            </div>
        </div>
    `;
    
    document.getElementById('video-file-input').addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            document.getElementById('file-info').textContent = `📁 ${file.name} (${(file.size/1024/1024).toFixed(2)} مگابایت)`;
            document.getElementById('upload-form').style.display = 'block';
        }
    });
}

async function uploadVideo() {
    const fileInput = document.getElementById('video-file-input');
    const file = fileInput.files[0];
    if (!file) {
        showToast('❌ فایلی انتخاب نشده', 'error');
        return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
        showToast('❌ حجم فایل بیشتر از ۱۰ مگابایت است', 'error');
        return;
    }
    
    const title = document.getElementById('upload-title').value;
    const desc = document.getElementById('upload-desc').value;
    const isPrivate = document.getElementById('upload-private').checked;
    
    const formData = new FormData();
    formData.append('video', file);
    if (title) formData.append('title', title);
    if (desc) formData.append('description', desc);
    if (isPrivate) formData.append('is_private', 'true');
    
    document.getElementById('upload-progress').textContent = '⏳ در حال آپلود...';
    
    try {
        const res = await fetch('/api/videos/upload', {
            method: 'POST',
            headers: { 'token': token },
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ ویدیو با موفقیت آپلود شد!');
            document.getElementById('upload-progress').textContent = '✅ آپلود کامل!';
            document.getElementById('video-file-input').value = '';
            document.getElementById('upload-title').value = '';
            document.getElementById('upload-desc').value = '';
            document.getElementById('upload-form').style.display = 'none';
            document.getElementById('file-info').textContent = '';
            setTimeout(() => showTab('feed'), 1000);
        } else {
            showToast('❌ ' + (data.detail || 'خطا'), 'error');
            document.getElementById('upload-progress').textContent = '';
        }
    } catch (e) {
        showToast('❌ خطا: ' + e.message, 'error');
        document.getElementById('upload-progress').textContent = '';
    }
}

// ============================================
// CHAT
// ============================================
let chatWith = null;
let chatMessages = [];

function loadChat(container) {
    if (!token) {
        container.innerHTML = buildAuthForm();
        return;
    }
    
    container.innerHTML = `
        <div class="chat-container">
            <div id="chat-list-view">
                <h3 style="margin-bottom:12px;">💬 پیام‌ها</h3>
                <div class="chat-list" id="chat-list"></div>
            </div>
            <div id="chat-messages-view" style="display:none;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                    <button onclick="backToChatList()" style="background:none;border:none;font-size:20px;cursor:pointer;">←</button>
                    <span id="chat-partner-name" style="font-weight:600;"></span>
                    <span id="chat-partner-status" style="color:#8e8e8e;font-size:12px;"></span>
                </div>
                <div class="chat-messages" id="chat-messages"></div>
                <div class="chat-input">
                    <input id="chat-input" placeholder="پیام بنویسید..." onkeydown="if(event.key==='Enter') sendMessage()">
                    <button onclick="sendMessage()" id="chat-send-btn">ارسال</button>
                </div>
            </div>
        </div>
    `;
    
    loadConversations();
}

async function loadConversations() {
    try {
        const res = await fetch('/api/messages/conversations', {
            headers: { 'token': token }
        });
        const data = await res.json();
        const list = document.getElementById('chat-list');
        if (!Array.isArray(data) || data.length === 0) {
            list.innerHTML = '<div style="padding:20px;text-align:center;color:#8e8e8e;">هنوز پیامی ندارید</div>';
            return;
        }
        let html = '';
        for (const c of data) {
            const unreadBadge = c.unread_count > 0 ? `<span class="badge">${c.unread_count}</span>` : '';
            const onlineDot = c.is_online ? '<span class="online"></span>' : '';
            html += `
                <div class="chat-item" onclick="openChat(${c.user_id}, '${c.username}')">
                    <div class="avatar">${c.avatar_url ? `<img src="${c.avatar_url}">` : '👤'}</div>
                    <div class="info">
                        <div class="name">${c.username} ${onlineDot}</div>
                        <div class="last-msg">${c.last_message || ''}</div>
                    </div>
                    ${unreadBadge}
                </div>
            `;
        }
        list.innerHTML = html;
    } catch (e) {}
}

function backToChatList() {
    chatWith = null;
    document.getElementById('chat-list-view').style.display = 'block';
    document.getElementById('chat-messages-view').style.display = 'none';
    loadConversations();
}

function openChat(userId, username) {
    chatWith = userId;
    document.getElementById('chat-list-view').style.display = 'none';
    document.getElementById('chat-messages-view').style.display = 'block';
    document.getElementById('chat-partner-name').textContent = username;
    document.getElementById('chat-partner-status').textContent = 'آفلاین';
    
    // بررسی آنلاین بودن
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'online_check', user_id: userId }));
    }
    
    loadMessages(userId);
}

async function loadMessages(userId) {
    try {
        const res = await fetch(`/api/messages/${userId}?limit=50`, {
            headers: { 'token': token }
        });
        const data = await res.json();
        chatMessages = data;
        renderMessages();
    } catch (e) {}
}

function renderMessages() {
    const container = document.getElementById('chat-messages');
    let html = '';
    for (const m of chatMessages) {
        const cls = m.is_mine ? 'mine' : 'other';
        const time = new Date(m.created_at).toLocaleTimeString('fa-IR');
        html += `
            <div class="msg ${cls}">
                ${m.content}
                <span class="time">${time}</span>
            </div>
        `;
    }
    container.innerHTML = html;
    container.scrollTop = container.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const content = input.value.trim();
    if (!content || !chatWith) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast('❌ اتصال به سرور چت برقرار نیست', 'error');
        connectWebSocket();
        return;
    }
    
    ws.send(JSON.stringify({
        type: 'message',
        receiver_id: chatWith,
        content: content
    }));
    
    input.value = '';
    
    // نمایش موقت
    chatMessages.push({
        id: Date.now(),
        sender_id: currentUser?.id || 0,
        receiver_id: chatWith,
        content: content,
        is_read: false,
        created_at: new Date().toISOString(),
        is_mine: true
    });
    renderMessages();
}

// ============================================
// PROFILE
// ============================================
async function loadProfile(container) {
    if (!token) {
        container.innerHTML = buildAuthForm();
        return;
    }
    
    container.innerHTML = `<div class="profile-container"><p style="text-align:center;padding:40px;">⏳ بارگذاری...</p></div>`;
    
    try {
        const res = await fetch('/api/auth/me', {
            headers: { 'token': token }
        });
        const user = await res.json();
        if (!user.id) {
            container.innerHTML = buildAuthForm();
            return;
        }
        
        currentUser = user;
        
        let html = `
            <div class="profile-container">
                <div class="profile-header">
                    <div class="avatar">${user.avatar_url ? `<img src="${user.avatar_url}">` : '📷'}</div>
                    <div class="info">
                        <div class="name">${user.full_name || user.username}</div>
                        <div class="username">@${user.username}</div>
                        <div class="bio">${user.bio || ''}</div>
                        <div style="margin-top:4px;">
                            ${user.is_premium ? '<span style="color:#f9c74f;font-weight:600;">⭐ ویژه</span>' : ''}
                            ${user.is_verified ? '<span style="color:#0095f6;font-weight:600;">✓ تایید شده</span>' : ''}
                        </div>
                    </div>
                    <div>
                        <button onclick="showEditProfile()" style="background:#0095f6;color:white;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;">ویرایش</button>
                        <button onclick="logout()" style="background:#ed4956;color:white;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;margin-top:4px;">خروج</button>
                    </div>
                </div>
                <div class="profile-stats">
                    <div class="stat"><div class="num">${user.videos_count || 0}</div><div class="label">ویدیو</div></div>
                    <div class="stat"><div class="num">${user.followers_count || 0}</div><div class="label">دنبال‌کننده</div></div>
                    <div class="stat"><div class="num">${user.following_count || 0}</div><div class="label">دنبال‌شونده</div></div>
                </div>
                <div class="profile-grid" id="profile-grid"></div>
            </div>
        `;
        container.innerHTML = html;
        
        // بارگذاری ویدیوهای کاربر
        try {
            const feedRes = await fetch('/api/videos/feed?limit=30', {
                headers: { 'token': token }
            });
            const videos = await feedRes.json();
            if (Array.isArray(videos)) {
                const userVideos = videos.filter(v => v.user_id === user.id);
                let gridHtml = '';
                for (const v of userVideos) {
                    gridHtml += `
                        <div class="item">
                            <video src="${v.video_url}" style="width:100%;height:100%;object-fit:cover;" muted></video>
                            <div class="overlay">
                                <span>❤️ ${v.likes_count || 0}</span>
                                <span>💬 ${v.comments_count || 0}</span>
                            </div>
                        </div>
                    `;
                }
                document.getElementById('profile-grid').innerHTML = gridHtml || '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#8e8e8e;">هنوز ویدیویی آپلود نکردید</div>';
            }
        } catch (e) {}
        
    } catch (e) {
        container.innerHTML = `<div class="profile-container"><p>❌ خطا: ${e.message}</p></div>`;
    }
}

function showEditProfile() {
    if (!currentUser) return;
    showModal('ویرایش پروفایل', `
        <div class="form-group">
            <label style="display:block;margin-bottom:4px;">نام کامل</label>
            <input id="edit-fullname" value="${currentUser.full_name || ''}" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;">
        </div>
        <div class="form-group">
            <label style="display:block;margin-bottom:4px;">بیوگرافی</label>
            <textarea id="edit-bio" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;resize:vertical;min-height:60px;">${currentUser.bio || ''}</textarea>
        </div>
        <div class="form-group">
            <label style="display:block;margin-bottom:4px;">وب‌سایت</label>
            <input id="edit-website" value="${currentUser.website || ''}" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;">
        </div>
        <div class="form-group">
            <label style="display:block;margin-bottom:4px;">موقعیت</label>
            <input id="edit-location" value="${currentUser.location || ''}" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;">
        </div>
        <button onclick="updateProfile()" style="width:100%;background:#0095f6;color:white;border:none;padding:12px;border-radius:8px;font-size:16px;cursor:pointer;">💾 ذخیره تغییرات</button>
    `);
}

async function updateProfile() {
    const full_name = document.getElementById('edit-fullname').value;
    const bio = document.getElementById('edit-bio').value;
    const website = document.getElementById('edit-website').value;
    const location = document.getElementById('edit-location').value;
    
    try {
        const formData = new FormData();
        formData.append('full_name', full_name);
        formData.append('bio', bio);
        formData.append('website', website);
        formData.append('location', location);
        
        const res = await fetch('/api/users/me', {
            method: 'PUT',
            headers: { 'token': token },
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ پروفایل به‌روزرسانی شد');
            closeModal();
            showTab('profile');
        } else {
            showToast('❌ ' + (data.detail || 'خطا'), 'error');
        }
    } catch (e) {
        showToast('❌ خطا: ' + e.message, 'error');
    }
}

// ============================================
// ADMIN
// ============================================
async function loadAdmin(container) {
    if (!token) {
        container.innerHTML = buildAuthForm();
        return;
    }
    
    container.innerHTML = `
        <div class="admin-container">
            <div class="admin-card">
                <h2>📊 آمار کلی</h2>
                <div class="admin-stats" id="admin-stats">
                    <div class="stat"><div class="num">...</div><div class="label">کاربران</div></div>
                    <div class="stat"><div class="num">...</div><div class="label">ویدیوها</div></div>
                    <div class="stat"><div class="num">...</div><div class="label">بازدیدها</div></div>
                    <div class="stat"><div class="num">...</div><div class="label">کاربران امروز</div></div>
                </div>
            </div>
            
            <div class="admin-card">
                <h2>🖥️ وضعیت سرورها</h2>
                <div id="servers-status"></div>
                <button onclick="showAddServer()" style="margin-top:12px;background:#0095f6;color:white;border:none;padding:8px 20px;border-radius:4px;cursor:pointer;">➕ اضافه کردن سرور</button>
            </div>
            
            <div class="admin-card">
                <h2>👥 کاربران</h2>
                <input id="admin-user-search" placeholder="🔍 جستجوی کاربر..." style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;margin-bottom:12px;">
                <div id="admin-users-list"></div>
            </div>
        </div>
    `;
    
    // بارگذاری آمار
    try {
        const statsRes = await fetch('/admin/stats', {
            headers: { 'token': token }
        });
        const stats = await statsRes.json();
        if (stats.total_users !== undefined) {
            document.getElementById('admin-stats').innerHTML = `
                <div class="stat"><div class="num">${stats.total_users}</div><div class="label">کاربران</div></div>
                <div class="stat"><div class="num">${stats.total_videos}</div><div class="label">ویدیوها</div></div>
                <div class="stat"><div class="num">${stats.total_views}</div><div class="label">بازدیدها</div></div>
                <div class="stat"><div class="num">${stats.active_users_today}</div><div class="label">کاربران امروز</div></div>
                <div class="stat"><div class="num">${stats.premium_users}</div><div class="label">کاربران ویژه</div></div>
                <div class="stat"><div class="num">${stats.server_count}</div><div class="label">سرورها</div></div>
            `;
        }
    } catch (e) {}
    
    // بارگذاری سرورها
    loadServersStatus();
    
    // بارگذاری کاربران
    loadAdminUsers();
    
    // جستجو
    document.getElementById('admin-user-search').addEventListener('input', function() {
        loadAdminUsers(this.value.trim());
    });
}

async function loadServersStatus() {
    try {
        const res = await fetch('/admin/servers/status', {
            headers: { 'token': token }
        });
        const data = await res.json();
        if (data.servers) {
            let html = `<table class="admin-table"><tr><th>نام</th><th>کاربران</th><th>ظرفیت</th><th>بار</th><th>وضعیت</th></tr>`;
            for (const s of data.servers) {
                const color = s.load_percent > 80 ? 'badge-danger' : s.load_percent > 50 ? 'badge-warning' : 'badge-success';
                html += `
                    <tr>
                        <td>${s.name}</td>
                        <td>${s.current_users}</td>
                        <td>${s.max_users}</td>
                        <td class="${color}">${s.load_percent}%</td>
                        <td>${s.is_active ? '✅ فعال' : '❌ غیرفعال'}</td>
                    </tr>
                `;
            }
            html += '</table>';
            document.getElementById('servers-status').innerHTML = html;
        }
    } catch (e) {
        document.getElementById('servers-status').innerHTML = '<p>خطا در بارگذاری</p>';
    }
}

async function loadAdminUsers(search = '') {
    try {
        const url = `/api/admin/users?limit=20${search ? `&search=${encodeURIComponent(search)}` : ''}`;
        const res = await fetch(url, {
            headers: { 'token': token }
        });
        const data = await res.json();
        if (data.users) {
            let html = `<table class="admin-table"><tr><th>کاربر</th><th>ایمیل</th><th>ویدیو</th><th>دنبال‌کننده</th><th>ویژه</th></tr>`;
            for (const u of data.users) {
                html += `
                    <tr>
                        <td>${u.full_name || u.username}</td>
                        <td>${u.email}</td>
                        <td>${u.videos_count}</td>
                        <td>${u.followers_count}</td>
                        <td>
                            <button onclick="togglePremium(${u.id})" style="background:${u.is_premium ? '#ed4956' : '#0095f6'};color:white;border:none;padding:2px 12px;border-radius:4px;cursor:pointer;">
                                ${u.is_premium ? 'لغو' : 'ویژه'}
                            </button>
                        </td>
                    </tr>
                `;
            }
            html += '</table>';
            document.getElementById('admin-users-list').innerHTML = html;
        }
    } catch (e) {}
}

async function togglePremium(userId) {
    try {
        const res = await fetch(`/admin/users/${userId}/toggle-premium`, {
            method: 'POST',
            headers: { 'token': token }
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ وضعیت ویژه: ${data.is_premium ? 'فعال' : 'غیرفعال'}`);
            loadAdminUsers(document.getElementById('admin-user-search').value);
        }
    } catch (e) {}
}

function showAddServer() {
    showModal('➕ اضافه کردن سرور جدید', `
        <div class="form-group">
            <label style="display:block;margin-bottom:4px;">نام سرور</label>
            <input id="new-server-name" placeholder="مثلاً server-2" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;">
        </div>
        <div class="form-group">
            <label style="display:block;margin-bottom:4px;">آی‌پی سرور</label>
            <input id="new-server-ip" placeholder="مثلاً 192.168.1.2" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;">
        </div>
        <div class="form-group">
            <label style="display:block;margin-bottom:4px;">پورت</label>
            <input id="new-server-port" value="8000" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;">
        </div>
        <div class="form-group">
            <label style="display:block;margin-bottom:4px;">حداکثر کاربران</label>
            <input id="new-server-max" value="10000" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;">
        </div>
        <button onclick="addServer()" style="width:100%;background:#0095f6;color:white;border:none;padding:12px;border-radius:8px;font-size:16px;cursor:pointer;">➕ افزودن</button>
    `);
}

async function addServer() {
    const name = document.getElementById('new-server-name').value;
    const ip = document.getElementById('new-server-ip').value;
    const port = parseInt(document.getElementById('new-server-port').value);
    const max_users = parseInt(document.getElementById('new-server-max').value);
    
    if (!name || !ip) {
        showToast('❌ نام و آی‌پی را وارد کنید', 'error');
        return;
    }
    
    try {
        const res = await fetch('/admin/servers/add', {
            method: 'POST',
            headers: {
                'token': token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ server_name: name, server_ip: ip, server_port: port, max_users })
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ سرور اضافه شد');
            closeModal();
            loadServersStatus();
        } else {
            showToast('❌ ' + (data.detail || 'خطا'), 'error');
        }
    } catch (e) {
        showToast('❌ خطا: ' + e.message, 'error');
    }
}

// ============================================
// ACTIONS
// ============================================
async function likeVideo(videoId) {
    if (!token) {
        showToast('❌ لطفاً وارد شوید', 'error');
        return;
    }
    try {
        const res = await fetch(`/api/videos/${videoId}/like`, {
            method: 'POST',
            headers: { 'token': token }
        });
        const data = await res.json();
        if (data.success) {
            showTab('feed');
        }
    } catch (e) {}
}

async function addComment(videoId, content) {
    if (!token) {
        showToast('❌ لطفاً وارد شوید', 'error');
        return;
    }
    try {
        const res = await fetch(`/api/videos/${videoId}/comments`, {
            method: 'POST',
            headers: {
                'token': token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content })
        });
        const data = await res.json();
        if (data.id) {
            showTab('feed');
        }
    } catch (e) {}
}

async function followUser(userId) {
    if (!token) {
        showToast('❌ لطفاً وارد شوید', 'error');
        return;
    }
    try {
        const res = await fetch(`/api/users/${userId}/follow`, {
            method: 'POST',
            headers: { 'token': token }
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.following ? '✅ دنبال شد' : '❌ آنفالو شد');
            showTab('explore');
        }
    } catch (e) {}
}

function shareVideo(url) {
    if (navigator.share) {
        navigator.share({
            title: 'ساده‌گرام',
            text: 'این ویدیو را ببینید!',
            url: url
        });
    } else {
        navigator.clipboard.writeText(url).then(() => {
            showToast('✅ لینک کپی شد');
        });
    }
}

// ============================================
// MODAL
// ============================================
function showModal(title, body) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = body;
    document.getElementById('modal').classList.add('show');
}

function closeModal() {
    document.getElementById('modal').classList.remove('show');
}

// ============================================
// WEBSOCKET
// ============================================
function connectWebSocket() {
    if (!token) return;
    if (ws && ws.readyState === WebSocket.OPEN) return;
    
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat?token=${token}`;
        ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
            console.log('✅ WebSocket متصل شد');
        };
        
        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'message') {
                    // پیام جدید
                    if (chatWith === data.data.sender_id) {
                        chatMessages.push({
                            id: data.data.id,
                            sender_id: data.data.sender_id,
                            receiver_id: currentUser?.id || 0,
                            content: data.data.content,
                            is_read: false,
                            created_at: data.data.created_at,
                            is_mine: false
                        });
                        renderMessages();
                    }
                    // به‌روزرسانی لیست مکالمات
                    if (document.getElementById('chat-list')) {
                        loadConversations();
                    }
                } else if (data.type === 'typing') {
                    document.getElementById('chat-partner-status').textContent = 'در حال تایپ...';
                    setTimeout(() => {
                        document.getElementById('chat-partner-status').textContent = 'آنلاین';
                    }, 2000);
                } else if (data.type === 'sent') {
                    // تایید ارسال
                }
            } catch (e) {}
        };
        
        ws.onclose = function() {
            console.log('❌ WebSocket قطع شد');
            setTimeout(connectWebSocket, 3000);
        };
        
        ws.onerror = function(e) {
            console.error('WebSocket error:', e);
        };
        
    } catch (e) {
        console.error('WebSocket connection error:', e);
    }
}

// ============================================
// AUTH FORM
// ============================================
function buildAuthForm() {
    return `
        <div style="max-width:400px;margin:40px auto;padding:0 16px;">
            <div style="background:white;border-radius:16px;border:1px solid #dbdbdb;padding:32px 24px;">
                <h2 style="text-align:center;font-size:24px;margin-bottom:24px;">📸 ساده‌گرام</h2>
                <div id="auth-tabs" style="display:flex;gap:8px;margin-bottom:20px;">
                    <button onclick="switchAuth('login')" class="auth-tab active" style="flex:1;padding:10px;background:#0095f6;color:white;border:none;border-radius:8px;cursor:pointer;">ورود</button>
                    <button onclick="switchAuth('register')" class="auth-tab" style="flex:1;padding:10px;background:#efefef;color:#262626;border:none;border-radius:8px;cursor:pointer;">ثبت‌نام</button>
                </div>
                <div id="auth-login">
                    <input id="login-username" placeholder="نام کاربری" style="width:100%;padding:12px;border:1px solid #dbdbdb;border-radius:8px;margin-bottom:10px;">
                    <input id="login-password" type="password" placeholder="رمز عبور" style="width:100%;padding:12px;border:1px solid #dbdbdb;border-radius:8px;margin-bottom:16px;">
                    <button onclick="login(document.getElementById('login-username').value, document.getElementById('login-password').value)" style="width:100%;background:#0095f6;color:white;border:none;padding:12px;border-radius:8px;font-size:16px;cursor:pointer;">ورود</button>
                </div>
                <div id="auth-register" style="display:none;">
                    <input id="reg-username" placeholder="نام کاربری" style="width:100%;padding:12px;border:1px solid #dbdbdb;border-radius:8px;margin-bottom:10px;">
                    <input id="reg-email" type="email" placeholder="ایمیل" style="width:100%;padding:12px;border:1px solid #dbdbdb;border-radius:8px;margin-bottom:10px;">
                    <input id="reg-fullname" placeholder="نام کامل" style="width:100%;padding:12px;border:1px solid #dbdbdb;border-radius:8px;margin-bottom:10px;">
                    <input id="reg-password" type="password" placeholder="رمز عبور" style="width:100%;padding:12px;border:1px solid #dbdbdb;border-radius:8px;margin-bottom:16px;">
                    <button onclick="register(document.getElementById('reg-username').value, document.getElementById('reg-email').value, document.getElementById('reg-password').value, document.getElementById('reg-fullname').value)" style="width:100%;background:#0095f6;color:white;border:none;padding:12px;border-radius:8px;font-size:16px;cursor:pointer;">ثبت‌نام</button>
                </div>
            </div>
        </div>
    `;
}

function switchAuth(type) {
    document.querySelectorAll('.auth-tab').forEach(t => {
        t.style.background = '#efefef';
        t.style.color = '#262626';
    });
    document.getElementById('auth-login').style.display = type === 'login' ? 'block' : 'none';
    document.getElementById('auth-register').style.display = type === 'register' ? 'block' : 'none';
    document.querySelector(`.auth-tab:${type === 'login' ? 'first' : 'last'}-child`).style.background = '#0095f6';
    document.querySelector(`.auth-tab:${type === 'login' ? 'first' : 'last'}-child`).style.color = 'white';
}

// ============================================
// INIT
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    // اگر توکن داریم، به سرور متصل می‌شیم
    if (token) {
        connectWebSocket();
        // دریافت اطلاعات کاربر
        fetch('/api/auth/me', {
            headers: { 'token': token }
        }).then(res => res.json()).then(data => {
            if (data.id) {
                currentUser = data;
                showTab('feed');
            } else {
                token = '';
                localStorage.removeItem('token');
                showTab('feed');
            }
        }).catch(() => {
            token = '';
            localStorage.removeItem('token');
            showTab('feed');
        });
    } else {
        showTab('feed');
    }
});

// بستن مودال با کلیک خارج
document.getElementById('modal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});

console.log('📸 ساده‌گرام نسخه حرفه‌ای');
</script>
</body>
</html>
    """
# ============================================
# اجرا
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )