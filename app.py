"""
ساده‌گرام - نسخه حرفه‌ای با پشتیبانی از SQLite
"""

# ============================================
# کتابخانه‌ها
# ============================================
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, BigInteger, Text, ForeignKey, Index, and_, or_, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import bcrypt
import jwt
import uuid
import os
import json
import asyncio
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr
import logging

# ============================================
# تنظیمات
# ============================================
SECRET_KEY = "your-super-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

# استفاده از SQLite (نیازی به PostgreSQL نیست)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sadegram.db")

# Redis (اختیاری - اگر نصب نیست، بدون کش کار می‌کند)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# سرور
SERVER_ID = int(os.getenv("SERVER_ID", 1))
MAX_USERS_PER_SERVER = int(os.getenv("MAX_USERS_PER_SERVER", 10000))

# ============================================
# اتصال به دیتابیس (SQLite)
# ============================================
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============================================
# Redis (اختیاری)
# ============================================
REDIS_AVAILABLE = False
try:
    import redis
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=2
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("✅ Redis متصل شد")
except:
    REDIS_AVAILABLE = False
    print("⚠️ Redis در دسترس نیست (بدون کش اجرا می‌شود)")

# ============================================
# مدل‌های دیتابیس
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
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    server_id = Column(Integer, default=1)
    
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    videos_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_seen = Column(DateTime, default=func.now())
    
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")

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
    
    views = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="videos")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="video", cascade="all, delete-orphan")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    video_id = Column(BigInteger, ForeignKey("videos.id"), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("comments.id"), nullable=True)
    content = Column(Text, nullable=False)
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    is_deleted = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="comments")
    video = relationship("Video", back_populates="comments")
    replies = relationship("Comment", backref="parent", remote_side=[id])

class Like(Base):
    __tablename__ = "likes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    video_id = Column(BigInteger, ForeignKey("videos.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="likes")
    video = relationship("Video", back_populates="likes")

class Follow(Base):
    __tablename__ = "follows"
    
    id = Column(BigInteger, primary_key=True, index=True)
    follower_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    following_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='unique_follow'),
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
    
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

class ServerMapping(Base):
    __tablename__ = "server_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    server_name = Column(String(50), nullable=False)
    server_ip = Column(String(50))
    server_port = Column(Integer, default=8000)
    max_users = Column(Integer, default=10000)
    current_users = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    link = Column(String(500))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

# ============================================
# Pydantic Models
# ============================================

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_premium: bool
    is_verified: bool
    followers_count: int
    following_count: int
    videos_count: int
    server_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class AddServerRequest(BaseModel):
    server_name: str
    server_ip: str
    server_port: int = 8000
    max_users: int = 10000

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
    user_id = payload.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user:
        user.last_seen = datetime.utcnow()
        db.commit()
    return user

def get_cache(key: str):
    if REDIS_AVAILABLE:
        try:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except:
            pass
    return None

def set_cache(key: str, value, expire: int = 300):
    if REDIS_AVAILABLE:
        try:
            redis_client.setex(key, expire, json.dumps(value))
        except:
            pass

def invalidate_cache(pattern: str):
    if REDIS_AVAILABLE:
        try:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
        except:
            pass

# ============================================
# سرویس شاردینگ
# ============================================

class ShardingService:
    
    @staticmethod
    def get_server_for_user(user_id: int, db: Session) -> int:
        cache_key = f"user_server:{user_id}"
        cached = get_cache(cache_key)
        if cached:
            return int(cached)
        
        user = db.query(User).filter(User.id == user_id).first()
        server_id = user.server_id if user else 1
        set_cache(cache_key, server_id, 3600)
        return server_id
    
    @staticmethod
    def assign_user_to_server(db: Session) -> int:
        servers = db.query(ServerMapping).filter(
            ServerMapping.is_active == True
        ).order_by(ServerMapping.current_users).all()
        
        if not servers:
            default = ServerMapping(
                server_name="server-1",
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
        return new_server.id

# ============================================
# WebSocket Manager
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
    
    def get_online_users(self) -> List[int]:
        if REDIS_AVAILABLE:
            try:
                keys = redis_client.keys("online:*")
                return [int(k.split(":")[1]) for k in keys]
            except:
                pass
        return list(self.active_connections.keys())

manager = ConnectionManager()

# ============================================
# اپلیکیشن FastAPI
# ============================================

app = FastAPI(
    title="ساده‌گرام",
    description="پلتفرم اشتراک ویدیو",
    version="2.0.0"
)

# ایجاد پوشه‌ها
os.makedirs("./storage", exist_ok=True)
os.makedirs("./static", exist_ok=True)

# ============================================
# WebSocket
# ============================================

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, token: str):
    db = SessionLocal()
    user = get_current_user(token, db)
    if not user:
        await websocket.close(code=1008)
        db.close()
        return
    
    user_id = user.id
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                receiver_id = data.get("receiver_id")
                content = data.get("content")
                
                if not receiver_id or not content:
                    continue
                
                new_message = Message(
                    sender_id=user_id,
                    receiver_id=receiver_id,
                    content=content
                )
                db.add(new_message)
                db.commit()
                db.refresh(new_message)
                
                # ارسال به گیرنده
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
                
                await manager.send_message(receiver_id, message_data)
                await websocket.send_json({"type": "sent", "data": {"id": new_message.id}})
            
            elif data.get("type") == "typing":
                receiver_id = data.get("receiver_id")
                if receiver_id:
                    await manager.send_message(receiver_id, {"type": "typing", "data": {"user_id": user_id}})
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        db.close()

# ============================================
# APIها
# ============================================

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    print("✅ دیتابیس راه‌اندازی شد")
    
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
        "user": UserResponse.model_validate(new_user)
    }

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(lambda: SessionLocal())):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="نام کاربری یا رمز عبور اشتباه است")
    
    token = create_access_token({"user_id": user.id})
    user.last_seen = datetime.utcnow()
    db.commit()
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(token: str, db: Session = Depends(lambda: SessionLocal())):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    return UserResponse.model_validate(user)

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
    
    # ذخیره محلی
    os.makedirs(f"./storage/videos/{user.id}", exist_ok=True)
    filename = f"{uuid.uuid4()}.mp4"
    file_path = f"./storage/videos/{user.id}/{filename}"
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    video_url = f"/static/videos/{user.id}/{filename}"
    
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
    
    user.videos_count += 1
    db.commit()
    
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
    
    # دریافت آیدی‌های فالو شده
    following = db.query(Follow.following_id).filter(Follow.follower_id == user.id).all()
    following_ids = [f[0] for f in following] + [user.id]
    
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
        return {"success": True, "liked": False}
    
    new_like = Like(
        user_id=user.id,
        video_id=video_id
    )
    db.add(new_like)
    video.likes_count += 1
    db.commit()
    
    return {"success": True, "liked": True}

@app.post("/api/videos/{video_id}/comments")
async def add_comment(
    video_id: int,
    content: str = Form(...),
    token: str = Form(...),
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    video = db.query(Video).filter(Video.id == video_id, Video.is_active == True).first()
    if not video:
        raise HTTPException(status_code=404, detail="ویدیو یافت نشد")
    
    new_comment = Comment(
        user_id=user.id,
        video_id=video_id,
        content=content
    )
    db.add(new_comment)
    video.comments_count += 1
    db.commit()
    db.refresh(new_comment)
    
    return {
        "id": new_comment.id,
        "user_id": new_comment.user_id,
        "video_id": new_comment.video_id,
        "content": new_comment.content,
        "created_at": new_comment.created_at.isoformat(),
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
        return {"success": True, "following": False}
    
    new_follow = Follow(
        follower_id=user.id,
        following_id=user_id
    )
    db.add(new_follow)
    user.following_count += 1
    target.followers_count += 1
    db.commit()
    
    return {"success": True, "following": True}

# ========== پیام‌ها ==========

@app.get("/api/messages/conversations")
async def get_conversations(
    token: str,
    db: Session = Depends(lambda: SessionLocal())
):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    
    sent_to = db.query(Message.receiver_id).filter(Message.sender_id == user.id).distinct().all()
    received_from = db.query(Message.sender_id).filter(Message.receiver_id == user.id).distinct().all()
    user_ids = set([u[0] for u in sent_to] + [u[0] for u in received_from])
    
    result = []
    for uid in user_ids:
        if uid == user.id:
            continue
        other = db.query(User).filter(User.id == uid, User.is_active == True).first()
        if not other:
            continue
        
        last_msg = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user.id, Message.receiver_id == uid),
                and_(Message.sender_id == uid, Message.receiver_id == user.id)
            )
        ).order_by(Message.created_at.desc()).first()
        
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
            "is_online": uid in manager.get_online_users()
        })
    
    result.sort(key=lambda x: x.get("last_message_time", ""), reverse=True)
    return result

@app.get("/api/messages/{other_user_id}")
async def get_messages(
    other_user_id: int,
    token: str,
    limit: int = 50,
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
    
    messages = db.query(Message).filter(
        or_(
            and_(Message.sender_id == user.id, Message.receiver_id == other_user_id),
            and_(Message.sender_id == other_user_id, Message.receiver_id == user.id)
        )
    ).order_by(Message.created_at.desc()).limit(limit).all()
    
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

@app.get("/admin/stats")
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
        "storage_used_gb": 0
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
# صفحه اصلی
# ============================================

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ساده‌گرام</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; background: #fafafa; padding-bottom: 70px; }
        .header { background: white; border-bottom: 1px solid #dbdbdb; padding: 12px 16px; position: sticky; top: 0; z-index: 100; display: flex; justify-content: space-between; align-items: center; }
        .header .logo { font-size: 22px; font-weight: bold; background: linear-gradient(45deg, #405de6, #c13584, #fd1d1d); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .bottom-tabs { position: fixed; bottom: 0; left: 0; right: 0; background: white; border-top: 1px solid #dbdbdb; display: flex; justify-content: space-around; padding: 8px 0; z-index: 100; }
        .bottom-tabs .tab { font-size: 24px; cursor: pointer; padding: 4px 16px; color: #8e8e8e; text-align: center; }
        .bottom-tabs .tab.active { color: #262626; }
        .bottom-tabs .tab .label { font-size: 10px; display: block; }
        .feed-container { max-width: 600px; margin: 0 auto; padding: 8px; }
        .post { background: white; margin-bottom: 16px; border-radius: 8px; border: 1px solid #dbdbdb; overflow: hidden; }
        .post-header { display: flex; align-items: center; padding: 12px 16px; gap: 12px; }
        .post-header .avatar { width: 36px; height: 36px; border-radius: 50%; background: #ddd; overflow: hidden; flex-shrink: 0; }
        .post-header .username { font-weight: 600; }
        .post-header .time { color: #8e8e8e; font-size: 12px; margin-right: auto; }
        .post-video { background: #000; }
        .post-video video { width: 100%; max-height: 500px; display: block; }
        .post-actions { display: flex; padding: 8px 16px; gap: 16px; align-items: center; }
        .post-actions .btn { background: none; border: none; font-size: 24px; cursor: pointer; }
        .post-actions .btn.liked { color: #ed4956; }
        .post-actions .stats { display: flex; gap: 16px; color: #8e8e8e; font-size: 14px; margin-right: auto; }
        .post-caption { padding: 0 16px 8px; font-size: 14px; }
        .post-caption .uname { font-weight: 600; }
        .post-comments { padding: 0 16px 12px; border-top: 1px solid #efefef; margin-top: 8px; }
        .post-comments .comment-form { display: flex; gap: 8px; padding-top: 8px; }
        .post-comments .comment-form input { flex: 1; border: none; outline: none; font-size: 14px; padding: 8px 0; }
        .post-comments .comment-form button { background: none; border: none; color: #0095f6; font-weight: 600; cursor: pointer; }
        .upload-container { max-width: 500px; margin: 20px auto; padding: 0 16px; }
        .upload-box { background: white; border: 2px dashed #dbdbdb; border-radius: 16px; padding: 40px 20px; text-align: center; }
        .upload-box input[type="file"] { display: none; }
        .btn-primary { background: #0095f6; color: white; border: none; padding: 10px 30px; border-radius: 8px; font-size: 16px; cursor: pointer; }
        .btn-primary:hover { background: #1877f2; }
        .profile-container { max-width: 600px; margin: 0 auto; padding: 16px; }
        .profile-header { display: flex; gap: 24px; align-items: center; padding: 16px 0; }
        .profile-header .avatar { width: 80px; height: 80px; border-radius: 50%; background: #ddd; overflow: hidden; flex-shrink: 0; }
        .profile-header .info { flex: 1; }
        .profile-header .info .name { font-size: 20px; font-weight: 600; }
        .profile-header .info .username { color: #8e8e8e; font-size: 14px; }
        .profile-stats { display: flex; gap: 24px; padding: 12px 0; border-top: 1px solid #dbdbdb; border-bottom: 1px solid #dbdbdb; }
        .profile-stats .stat { text-align: center; }
        .profile-stats .stat .num { font-weight: 600; font-size: 18px; }
        .profile-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; padding-top: 2px; }
        .profile-grid .item { aspect-ratio: 1; background: #ddd; overflow: hidden; }
        .profile-grid .item video { width: 100%; height: 100%; object-fit: cover; }
        .chat-container { max-width: 600px; margin: 0 auto; padding: 16px; }
        .chat-list { background: white; border-radius: 8px; border: 1px solid #dbdbdb; }
        .chat-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid #efefef; cursor: pointer; }
        .chat-item .avatar { width: 44px; height: 44px; border-radius: 50%; background: #ddd; flex-shrink: 0; }
        .chat-item .info { flex: 1; }
        .chat-item .info .name { font-weight: 600; }
        .chat-item .info .last-msg { color: #8e8e8e; font-size: 14px; }
        .chat-messages { background: white; border-radius: 8px; border: 1px solid #dbdbdb; height: 400px; overflow-y: auto; padding: 16px; }
        .chat-messages .msg { max-width: 70%; padding: 8px 12px; border-radius: 16px; margin-bottom: 8px; word-break: break-word; }
        .chat-messages .msg.mine { background: #0095f6; color: white; margin-left: auto; }
        .chat-messages .msg.other { background: #efefef; margin-right: auto; }
        .chat-input { display: flex; gap: 8px; padding: 12px 0; }
        .chat-input input { flex: 1; padding: 10px 16px; border: 1px solid #dbdbdb; border-radius: 24px; outline: none; }
        .chat-input button { background: #0095f6; color: white; border: none; border-radius: 24px; padding: 10px 20px; cursor: pointer; }
        .admin-container { max-width: 800px; margin: 20px auto; padding: 0 16px; }
        .admin-card { background: white; border-radius: 8px; border: 1px solid #dbdbdb; padding: 20px; margin-bottom: 16px; }
        .admin-card h2 { font-size: 18px; margin-bottom: 12px; }
        .admin-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
        .admin-stats .stat { background: #f8f9fa; padding: 12px; border-radius: 8px; text-align: center; }
        .admin-stats .stat .num { font-size: 24px; font-weight: 700; }
        .admin-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .admin-table th, .admin-table td { padding: 8px 12px; border-bottom: 1px solid #efefef; text-align: right; }
        .admin-table th { background: #f8f9fa; }
        .hidden { display: none !important; }
        .toast { position: fixed; top: 80px; left: 50%; transform: translateX(-50%); background: #262626; color: white; padding: 12px 24px; border-radius: 8px; z-index: 999; max-width: 90%; text-align: center; }
        .auth-form { max-width: 400px; margin: 40px auto; padding: 0 16px; }
        .auth-form .card { background: white; border-radius: 16px; border: 1px solid #dbdbdb; padding: 32px 24px; }
        .auth-form input { width: 100%; padding: 12px; border: 1px solid #dbdbdb; border-radius: 8px; margin-bottom: 10px; }
        .auth-form button { width: 100%; padding: 12px; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }
        .auth-tabs { display: flex; gap: 8px; margin-bottom: 20px; }
        .auth-tabs button { flex: 1; padding: 10px; border: none; border-radius: 8px; cursor: pointer; }
    </style>
</head>
<body>

<header class="header">
    <div class="logo">📸 ساده‌گرام</div>
    <div style="display:flex;gap:16px;font-size:20px;">
        <span onclick="showTab('upload')">➕</span>
        <span onclick="showTab('chat')">💬</span>
        <span onclick="showTab('profile')">👤</span>
    </div>
</header>

<div id="content"></div>

<nav class="bottom-tabs">
    <div class="tab active" onclick="showTab('feed')" data-tab="feed">🏠<span class="label">فید</span></div>
    <div class="tab" onclick="showTab('explore')" data-tab="explore">🔍<span class="label">جستجو</span></div>
    <div class="tab" onclick="showTab('upload')" data-tab="upload">➕<span class="label">آپلود</span></div>
    <div class="tab" onclick="showTab('chat')" data-tab="chat">💬<span class="label">چت</span></div>
    <div class="tab" onclick="showTab('profile')" data-tab="profile">👤<span class="label">پروفایل</span></div>
</nav>

<div id="toast" class="toast hidden"></div>

<script>
let token = localStorage.getItem('token') || '';
let currentUser = null;
let ws = null;
let chatWith = null;

function showToast(msg, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.style.background = isError ? '#ed4956' : '#262626';
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

function showTab(tab) {
    document.querySelectorAll('.bottom-tabs .tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    const container = document.getElementById('content');
    if (tab === 'feed') loadFeed(container);
    else if (tab === 'explore') loadExplore(container);
    else if (tab === 'upload') loadUpload(container);
    else if (tab === 'chat') loadChat(container);
    else if (tab === 'profile') loadProfile(container);
}

// ===== AUTH =====
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
        showToast('❌ ' + (data.detail || 'خطا'), true);
        return false;
    } catch (e) {
        showToast('❌ خطا', true);
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
        showToast('❌ ' + (data.detail || 'خطا'), true);
        return false;
    } catch (e) {
        showToast('❌ خطا', true);
        return false;
    }
}

function logout() {
    token = '';
    localStorage.removeItem('token');
    currentUser = null;
    if (ws) ws.close();
    showToast('👋 خروج');
    showTab('feed');
}

function buildAuthForm() {
    return `
        <div class="auth-form">
            <div class="card">
                <h2 style="text-align:center;margin-bottom:20px;">📸 ساده‌گرام</h2>
                <div class="auth-tabs">
                    <button onclick="switchAuth('login')" id="auth-login-btn" style="background:#0095f6;color:white;">ورود</button>
                    <button onclick="switchAuth('register')" id="auth-register-btn" style="background:#efefef;">ثبت‌نام</button>
                </div>
                <div id="auth-login">
                    <input id="login-username" placeholder="نام کاربری">
                    <input id="login-password" type="password" placeholder="رمز عبور">
                    <button onclick="login(document.getElementById('login-username').value, document.getElementById('login-password').value)" style="background:#0095f6;color:white;">ورود</button>
                </div>
                <div id="auth-register" style="display:none;">
                    <input id="reg-username" placeholder="نام کاربری">
                    <input id="reg-email" type="email" placeholder="ایمیل">
                    <input id="reg-fullname" placeholder="نام کامل">
                    <input id="reg-password" type="password" placeholder="رمز عبور">
                    <button onclick="register(document.getElementById('reg-username').value, document.getElementById('reg-email').value, document.getElementById('reg-password').value, document.getElementById('reg-fullname').value)" style="background:#0095f6;color:white;">ثبت‌نام</button>
                </div>
            </div>
        </div>
    `;
}

function switchAuth(type) {
    document.getElementById('auth-login').style.display = type === 'login' ? 'block' : 'none';
    document.getElementById('auth-register').style.display = type === 'register' ? 'block' : 'none';
    document.getElementById('auth-login-btn').style.background = type === 'login' ? '#0095f6' : '#efefef';
    document.getElementById('auth-login-btn').style.color = type === 'login' ? 'white' : '#262626';
    document.getElementById('auth-register-btn').style.background = type === 'register' ? '#0095f6' : '#efefef';
    document.getElementById('auth-register-btn').style.color = type === 'register' ? 'white' : '#262626';
}

// ===== FEED =====
async function loadFeed(container) {
    if (!token) { container.innerHTML = buildAuthForm(); return; }
    container.innerHTML = '<div class="feed-container"><p style="text-align:center;padding:40px;">⏳ بارگذاری...</p></div>';
    try {
        const res = await fetch('/api/videos/feed?limit=20', { headers: { 'token': token } });
        const data = await res.json();
        if (!Array.isArray(data)) {
            container.innerHTML = `<div class="feed-container"><p style="text-align:center;padding:40px;">${data.detail || 'خطا'}</p></div>`;
            return;
        }
        if (data.length === 0) {
            container.innerHTML = `<div class="feed-container"><div style="text-align:center;padding:60px 20px;"><div style="font-size:48px;">📹</div><h3>هنوز ویدیویی در فید شما نیست</h3><button onclick="showTab('explore')" style="background:#0095f6;color:white;border:none;padding:10px 30px;border-radius:8px;margin-top:16px;cursor:pointer;">🔍 جستجو</button></div></div>`;
            return;
        }
        let html = '<div class="feed-container">';
        for (const v of data) {
            const isLiked = v.is_liked ? 'liked' : '';
            const likeIcon = v.is_liked ? '❤️' : '🤍';
            html += `
                <div class="post">
                    <div class="post-header">
                        <div class="avatar">${v.user_avatar ? `<img src="${v.user_avatar}" style="width:100%;height:100%;object-fit:cover;">` : '👤'}</div>
                        <span class="username">${v.username || 'کاربر'}</span>
                        <span class="time">${new Date(v.created_at).toLocaleDateString('fa-IR')}</span>
                    </div>
                    <div class="post-video">
                        <video src="${v.video_url}" controls></video>
                    </div>
                    <div class="post-actions">
                        <button class="btn ${isLiked}" onclick="likeVideo(${v.id})">${likeIcon}</button>
                        <button class="btn" onclick="document.getElementById('comment-input-${v.id}').focus()">💬</button>
                        <div class="stats">
                            <span>❤️ ${v.likes_count || 0}</span>
                            <span>💬 ${v.comments_count || 0}</span>
                            <span>👁️ ${v.views || 0}</span>
                        </div>
                    </div>
                    <div class="post-caption">
                        <span class="uname">${v.username || ''}</span>
                        <span>${v.description || ''}</span>
                    </div>
                    <div class="post-comments">
                        <div class="comment-form">
                            <input id="comment-input-${v.id}" placeholder="کامنت...">
                            <button onclick="addComment(${v.id})">ارسال</button>
                        </div>
                    </div>
                </div>
            `;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<div class="feed-container"><p style="text-align:center;padding:40px;">❌ خطا</p></div>`;
    }
}

// ===== EXPLORE =====
async function loadExplore(container) {
    container.innerHTML = `<div style="max-width:600px;margin:16px auto;padding:0 16px;"><p style="text-align:center;color:#8e8e8e;">🔍 در حال توسعه...</p></div>`;
}

// ===== UPLOAD =====
function loadUpload(container) {
    if (!token) { container.innerHTML = buildAuthForm(); return; }
    container.innerHTML = `
        <div class="upload-container">
            <div class="upload-box">
                <div style="font-size:48px;">📤</div>
                <h3>آپلود ویدیو</h3>
                <p>حداکثر ۱۰ مگابایت</p>
                <input type="file" id="video-file" accept="video/*">
                <button class="btn-primary" onclick="document.getElementById('video-file').click()">انتخاب فایل</button>
                <div id="file-info" style="margin-top:12px;color:#8e8e8e;"></div>
                <div id="upload-form" style="display:none;margin-top:16px;">
                    <input id="upload-title" placeholder="عنوان" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;margin-bottom:8px;">
                    <textarea id="upload-desc" placeholder="توضیحات" style="width:100%;padding:10px;border:1px solid #dbdbdb;border-radius:8px;resize:vertical;min-height:60px;"></textarea>
                    <button class="btn-primary" onclick="uploadVideo()" style="width:100%;">📤 آپلود</button>
                    <div id="upload-status" style="margin-top:8px;text-align:center;"></div>
                </div>
            </div>
        </div>
    `;
    document.getElementById('video-file').addEventListener('change', function() {
        if (this.files[0]) {
            document.getElementById('file-info').textContent = `📁 ${this.files[0].name} (${(this.files[0].size/1024/1024).toFixed(2)} MB)`;
            document.getElementById('upload-form').style.display = 'block';
        }
    });
}

async function uploadVideo() {
    const file = document.getElementById('video-file').files[0];
    if (!file) { showToast('❌ فایلی انتخاب نشده', true); return; }
    if (file.size > 10 * 1024 * 1024) { showToast('❌ حجم بیش از ۱۰ مگابایت', true); return; }
    
    const formData = new FormData();
    formData.append('video', file);
    formData.append('title', document.getElementById('upload-title').value);
    formData.append('description', document.getElementById('upload-desc').value);
    
    document.getElementById('upload-status').textContent = '⏳ در حال آپلود...';
    try {
        const res = await fetch('/api/videos/upload', {
            method: 'POST',
            headers: { 'token': token },
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            showToast('✅ آپلود موفق!');
            document.getElementById('upload-status').textContent = '✅ کامل!';
            setTimeout(() => showTab('feed'), 1000);
        } else {
            showToast('❌ ' + (data.detail || 'خطا'), true);
            document.getElementById('upload-status').textContent = '';
        }
    } catch (e) {
        showToast('❌ خطا', true);
        document.getElementById('upload-status').textContent = '';
    }
}

// ===== CHAT =====
function loadChat(container) {
    if (!token) { container.innerHTML = buildAuthForm(); return; }
    container.innerHTML = `
        <div class="chat-container">
            <div id="chat-list-view">
                <h3>💬 پیام‌ها</h3>
                <div class="chat-list" id="chat-list"></div>
            </div>
            <div id="chat-messages-view" style="display:none;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                    <button onclick="backToChatList()" style="background:none;border:none;font-size:20px;cursor:pointer;">←</button>
                    <span id="chat-partner-name" style="font-weight:600;"></span>
                </div>
                <div class="chat-messages" id="chat-messages"></div>
                <div class="chat-input">
                    <input id="chat-input" placeholder="پیام..." onkeydown="if(event.key==='Enter') sendMessage()">
                    <button onclick="sendMessage()">ارسال</button>
                </div>
            </div>
        </div>
    `;
    loadConversations();
}

async function loadConversations() {
    try {
        const res = await fetch('/api/messages/conversations', { headers: { 'token': token } });
        const data = await res.json();
        const list = document.getElementById('chat-list');
        if (!Array.isArray(data) || data.length === 0) {
            list.innerHTML = '<div style="padding:20px;text-align:center;color:#8e8e8e;">هنوز پیامی ندارید</div>';
            return;
        }
        let html = '';
        for (const c of data) {
            html += `
                <div class="chat-item" onclick="openChat(${c.user_id}, '${c.username}')">
                    <div class="avatar">${c.avatar_url ? `<img src="${c.avatar_url}" style="width:100%;height:100%;object-fit:cover;">` : '👤'}</div>
                    <div class="info">
                        <div class="name">${c.username}</div>
                        <div class="last-msg">${c.last_message || ''}</div>
                    </div>
                    ${c.unread_count > 0 ? `<span style="background:#0095f6;color:white;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:12px;">${c.unread_count}</span>` : ''}
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

async function openChat(userId, username) {
    chatWith = userId;
    document.getElementById('chat-list-view').style.display = 'none';
    document.getElementById('chat-messages-view').style.display = 'block';
    document.getElementById('chat-partner-name').textContent = username;
    await loadMessages(userId);
}

async function loadMessages(userId) {
    try {
        const res = await fetch(`/api/messages/${userId}?limit=50`, { headers: { 'token': token } });
        const data = await res.json();
        const container = document.getElementById('chat-messages');
        let html = '';
        for (const m of data) {
            const cls = m.is_mine ? 'mine' : 'other';
            html += `<div class="msg ${cls}">${m.content}</div>`;
        }
        container.innerHTML = html;
        container.scrollTop = container.scrollHeight;
    } catch (e) {}
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const content = input.value.trim();
    if (!content || !chatWith || !ws) return;
    ws.send(JSON.stringify({ type: 'message', receiver_id: chatWith, content: content }));
    input.value = '';
}

function connectWebSocket() {
    if (!token || ws) return;
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat?token=${token}`);
        ws.onmessage = function(e) {
            const data = JSON.parse(e.data);
            if (data.type === 'message' && chatWith === data.data.sender_id) {
                const container = document.getElementById('chat-messages');
                container.innerHTML += `<div class="msg other">${data.data.content}</div>`;
                container.scrollTop = container.scrollHeight;
            }
        };
        ws.onclose = () => { ws = null; setTimeout(connectWebSocket, 3000); };
    } catch (e) {}
}

// ===== PROFILE =====
async function loadProfile(container) {
    if (!token) { container.innerHTML = buildAuthForm(); return; }
    try {
        const res = await fetch('/api/auth/me', { headers: { 'token': token } });
        const user = await res.json();
        if (!user.id) { container.innerHTML = buildAuthForm(); return; }
        currentUser = user;
        container.innerHTML = `
            <div class="profile-container">
                <div class="profile-header">
                    <div class="avatar">${user.avatar_url ? `<img src="${user.avatar_url}" style="width:100%;height:100%;object-fit:cover;">` : '📷'}</div>
                    <div class="info">
                        <div class="name">${user.full_name || user.username}</div>
                        <div class="username">@${user.username}</div>
                        <div style="font-size:14px;margin-top:4px;">${user.bio || ''}</div>
                        <div style="margin-top:4px;">
                            ${user.is_premium ? '⭐ ویژه ' : ''}
                            ${user.is_verified ? '✓ تایید شده' : ''}
                        </div>
                    </div>
                    <div>
                        <button onclick="logout()" style="background:#ed4956;color:white;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;">خروج</button>
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
        // بارگذاری ویدیوهای کاربر
        try {
            const feedRes = await fetch('/api/videos/feed?limit=30', { headers: { 'token': token } });
            const videos = await feedRes.json();
            if (Array.isArray(videos)) {
                const userVideos = videos.filter(v => v.user_id === user.id);
                let gridHtml = '';
                for (const v of userVideos.slice(0, 9)) {
                    gridHtml += `<div class="item"><video src="${v.video_url}" muted></video></div>`;
                }
                document.getElementById('profile-grid').innerHTML = gridHtml || '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#8e8e8e;">هنوز ویدیویی ندارید</div>';
            }
        } catch (e) {}
    } catch (e) {
        container.innerHTML = buildAuthForm();
    }
}

// ===== ACTIONS =====
async function likeVideo(videoId) {
    if (!token) return;
    try {
        await fetch(`/api/videos/${videoId}/like`, {
            method: 'POST',
            headers: { 'token': token }
        });
        showTab('feed');
    } catch (e) {}
}

async function addComment(videoId) {
    const input = document.getElementById(`comment-input-${videoId}`);
    const content = input.value.trim();
    if (!content || !token) return;
    try {
        const formData = new FormData();
        formData.append('content', content);
        formData.append('token', token);
        await fetch(`/api/videos/${videoId}/comments`, {
            method: 'POST',
            body: formData
        });
        input.value = '';
        showTab('feed');
    } catch (e) {}
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', function() {
    if (token) {
        fetch('/api/auth/me', { headers: { 'token': token } })
            .then(res => res.json())
            .then(data => {
                if (data.id) {
                    currentUser = data;
                    connectWebSocket();
                    showTab('feed');
                } else {
                    token = '';
                    localStorage.removeItem('token');
                    showTab('feed');
                }
            }).catch(() => { token = ''; localStorage.removeItem('token'); showTab('feed'); });
    } else {
        showTab('feed');
    }
});
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
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )