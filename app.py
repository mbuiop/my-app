from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import jwt
import os
import json
import redis
import threading
import time
import uuid
import shutil
from PIL import Image
import ffmpeg

# ==================== تنظیمات پیشرفته ====================
app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = 'your-super-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instagram.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_SIZE'] = 50
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['THUMBNAIL_FOLDER'] = 'thumbnails'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'webm'}

# اطمینان از وجود پوشه‌ها
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['THUMBNAIL_FOLDER'], exist_ok=True)

CORS(app, origins='*')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ==================== Redis برای کش ====================
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_available = True
except:
    redis_available = False
    print("⚠️ Redis not available, running without cache")

# ==================== دیتابیس ====================
db = SQLAlchemy(app)

# ==================== مدل‌های حرفه‌ای ====================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    bio = db.Column(db.String(300), default='')
    avatar = db.Column(db.String(200), default='https://i.pravatar.cc/150?img=10')
    is_verified = db.Column(db.Boolean, default=False)
    is_private = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    stories = db.relationship('Story', backref='author', lazy='dynamic')
    followers = db.relationship('Follow', foreign_keys='Follow.following_id', backref='following_user', lazy='dynamic')
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower_user', lazy='dynamic')
    likes = db.relationship('Like', backref='user', lazy='dynamic')
    comments = db.relationship('Comment', backref='user', lazy='dynamic')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    media_type = db.Column(db.String(20), default='image')  # image, video
    media_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500))
    caption = db.Column(db.String(2200), default='')
    location = db.Column(db.String(100))
    views = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    shares_count = db.Column(db.Integer, default=0)
    is_archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    likes = db.relationship('Like', backref='post', lazy='dynamic')
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    hashtags = db.relationship('PostHashtag', backref='post', lazy='dynamic')

class Story(db.Model):
    __tablename__ = 'stories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    media_type = db.Column(db.String(20), default='image')
    media_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500))
    caption = db.Column(db.String(200))
    views = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    viewers = db.relationship('StoryView', backref='story', lazy='dynamic')

class StoryView(db.Model):
    __tablename__ = 'story_views'
    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('stories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Follow(db.Model):
    __tablename__ = 'follows'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    following_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='accepted')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'following_id', name='unique_follow'),)

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_like'),)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    text = db.Column(db.String(300), nullable=False)
    likes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    message_type = db.Column(db.String(20), default='text')  # text, image, video, audio
    content = db.Column(db.String(2000))
    media_url = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # like, comment, follow, mention
    target_id = db.Column(db.Integer)  # post_id or user_id
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Hashtag(db.Model):
    __tablename__ = 'hashtags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    posts_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PostHashtag(db.Model):
    __tablename__ = 'post_hashtags'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    hashtag_id = db.Column(db.Integer, db.ForeignKey('hashtags.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('post_id', 'hashtag_id', name='unique_post_hashtag'),)

class SavedPost(db.Model):
    __tablename__ = 'saved_posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    collection_name = db.Column(db.String(100), default='default')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_save'),)

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)  # post, comment, user
    target_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== سیستم کش ====================
class CacheService:
    @staticmethod
    def get(key):
        if redis_available:
            return redis_client.get(key)
        return None
    
    @staticmethod
    def set(key, value, expire=3600):
        if redis_available:
            redis_client.setex(key, expire, value)
    
    @staticmethod
    def delete(key):
        if redis_available:
            redis_client.delete(key)
    
    @staticmethod
    def clear_pattern(pattern):
        if redis_available:
            for key in redis_client.scan_iter(pattern):
                redis_client.delete(key)

# ==================== دکوراتورهای امنیتی ====================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'توکن احراز هویت یافت نشد'}), 401
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'کاربر یافت نشد'}), 401
        except:
            return jsonify({'error': 'توکن نامعتبر است'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def rate_limit(limit=60, window=60):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = request.remote_addr
            key = f"rate_limit:{ip}:{f.__name__}"
            if redis_available:
                count = redis_client.get(key)
                if count and int(count) >= limit:
                    return jsonify({'error': 'درخواست بیش از حد. لطفاً بعداً تلاش کنید'}), 429
                redis_client.incr(key)
                redis_client.expire(key, window)
            return f(*args, **kwargs)
        return decorated
    return decorator

# ==================== توابع کمکی ====================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_thumbnail(filepath, output_path, size=(300, 300)):
    try:
        img = Image.open(filepath)
        img.thumbnail(size)
        img.save(output_path)
        return True
    except:
        return False

def generate_video_thumbnail(filepath, output_path):
    try:
        ffmpeg.input(filepath, ss=1).output(output_path, vframes=1, format='image2').run(quiet=True)
        return True
    except:
        return False

def get_user_from_token():
    token = request.headers.get('Authorization')
    if not token:
        return None
    try:
        token = token.split(' ')[1]
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return User.query.get(data['user_id'])
    except:
        return None

def send_notification(user_id, actor_id, type, target_id):
    notification = Notification(
        user_id=user_id,
        actor_id=actor_id,
        type=type,
        target_id=target_id
    )
    db.session.add(notification)
    db.session.commit()
    
    # ارسال نوتیفیکیشن از طریق WebSocket
    socketio.emit('new_notification', {
        'user_id': user_id,
        'type': type,
        'actor_id': actor_id,
        'target_id': target_id
    }, room=f'user_{user_id}')

# ==================== API‌ها ====================

# ---------- احراز هویت ----------
@app.route('/api/auth/register', methods=['POST'])
@rate_limit(10, 60)
def register():
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    full_name = data.get('full_name', '').strip()
    
    if not username or not email or not password:
        return jsonify({'error': 'همه فیلدها الزامی هستند'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'این نام کاربری قبلاً ثبت شده است'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'این ایمیل قبلاً ثبت شده است'}), 400
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        full_name=full_name
    )
    db.session.add(user)
    db.session.commit()
    
    token = jwt.encode({'user_id': user.id, 'exp': datetime.utcnow() + timedelta(days=30)}, 
                       app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'message': 'ثبت نام با موفقیت انجام شد',
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'avatar': user.avatar
        }
    })

@app.route('/api/auth/login', methods=['POST'])
@rate_limit(20, 60)
def login():
    data = request.json
    identifier = data.get('identifier', '').strip()
    password = data.get('password', '').strip()
    
    if not identifier or not password:
        return jsonify({'error': 'نام کاربری/ایمیل و رمز عبور الزامی هستند'}), 400
    
    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    if not user:
        return jsonify({'error': 'کاربر یافت نشد'}), 404
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user.password_hash != password_hash:
        return jsonify({'error': 'رمز عبور اشتباه است'}), 401
    
    token = jwt.encode({'user_id': user.id, 'exp': datetime.utcnow() + timedelta(days=30)}, 
                       app.config['SECRET_KEY'], algorithm='HS256')
    
    user.last_seen = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'ورود با موفقیت انجام شد',
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'avatar': user.avatar,
            'bio': user.bio,
            'is_verified': user.is_verified
        }
    })

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'full_name': current_user.full_name,
        'bio': current_user.bio,
        'avatar': current_user.avatar,
        'is_verified': current_user.is_verified,
        'is_private': current_user.is_private,
        'last_seen': current_user.last_seen.isoformat() if current_user.last_seen else None
    })

# ---------- کاربران ----------
@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    # کش کردن
    cache_key = f"user:{user_id}"
    cached = CacheService.get(cache_key)
    if cached:
        return jsonify(json.loads(cached))
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'کاربر یافت نشد'}), 404
    
    posts = Post.query.filter_by(user_id=user_id, is_archived=False).count()
    followers_count = Follow.query.filter_by(following_id=user_id, status='accepted').count()
    following_count = Follow.query.filter_by(follower_id=user_id, status='accepted').count()
    
    result = {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'bio': user.bio,
        'avatar': user.avatar,
        'is_verified': user.is_verified,
        'is_private': user.is_private,
        'posts_count': posts,
        'followers': followers_count,
        'following': following_count,
        'last_seen': user.last_seen.isoformat() if user.last_seen else None,
        'created_at': user.created_at.isoformat()
    }
    
    CacheService.set(cache_key, json.dumps(result), expire=300)
    return jsonify(result)

@app.route('/api/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    posts = Post.query.filter_by(user_id=user_id, is_archived=False)\
        .order_by(Post.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for p in posts.items:
        result.append({
            'id': p.id,
            'media_type': p.media_type,
            'media_url': p.media_url,
            'thumbnail_url': p.thumbnail_url,
            'caption': p.caption,
            'likes_count': p.likes_count,
            'comments_count': p.comments_count,
            'views': p.views,
            'created_at': p.created_at.isoformat()
        })
    
    return jsonify({
        'items': result,
        'total': posts.total,
        'page': posts.page,
        'pages': posts.pages
    })

@app.route('/api/users/<int:user_id>/follow', methods=['POST'])
@token_required
@rate_limit(50, 60)
def follow_user(current_user, user_id):
    if current_user.id == user_id:
        return jsonify({'error': 'نمی‌توانید خودتان را دنبال کنید'}), 400
    
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({'error': 'کاربر یافت نشد'}), 404
    
    existing = Follow.query.filter_by(follower_id=current_user.id, following_id=user_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        CacheService.delete(f"user:{user_id}")
        CacheService.delete(f"user:{current_user.id}")
        return jsonify({'following': False, 'message': 'آنفالو شد'})
    
    follow = Follow(follower_id=current_user.id, following_id=user_id)
    db.session.add(follow)
    db.session.commit()
    
    send_notification(user_id, current_user.id, 'follow', current_user.id)
    CacheService.delete(f"user:{user_id}")
    CacheService.delete(f"user:{current_user.id}")
    
    return jsonify({'following': True, 'message': 'فالو شد'})

@app.route('/api/users/<int:user_id>/followers', methods=['GET'])
def get_followers(user_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    followers = Follow.query.filter_by(following_id=user_id, status='accepted')\
        .join(User, User.id == Follow.follower_id)\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for f in followers.items:
        user = User.query.get(f.follower_id)
        result.append({
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'avatar': user.avatar,
            'is_verified': user.is_verified
        })
    
    return jsonify({
        'items': result,
        'total': followers.total,
        'page': followers.page,
        'pages': followers.pages
    })

@app.route('/api/users/<int:user_id>/following', methods=['GET'])
def get_following(user_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    following = Follow.query.filter_by(follower_id=user_id, status='accepted')\
        .join(User, User.id == Follow.following_id)\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for f in following.items:
        user = User.query.get(f.following_id)
        result.append({
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'avatar': user.avatar,
            'is_verified': user.is_verified
        })
    
    return jsonify({
        'items': result,
        'total': following.total,
        'page': following.page,
        'pages': following.pages
    })

@app.route('/api/users/update', methods=['PUT'])
@token_required
def update_profile(current_user):
    data = request.json
    if 'bio' in data:
        current_user.bio = data['bio'][:300]
    if 'full_name' in data:
        current_user.full_name = data['full_name'][:100]
    if 'is_private' in data:
        current_user.is_private = data['is_private']
    
    db.session.commit()
    CacheService.delete(f"user:{current_user.id}")
    
    return jsonify({'message': 'پروفایل با موفقیت به‌روزرسانی شد'})

# ---------- پست‌ها ----------
@app.route('/api/posts', methods=['GET'])
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    user_id = request.args.get('user_id', type=int)
    
    query = Post.query.filter_by(is_archived=False)
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    posts = query.order_by(Post.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for p in posts.items:
        user = User.query.get(p.user_id)
        result.append({
            'id': p.id,
            'user_id': p.user_id,
            'username': user.username if user else 'unknown',
            'user_avatar': user.avatar if user else '',
            'is_verified': user.is_verified if user else False,
            'media_type': p.media_type,
            'media_url': p.media_url,
            'thumbnail_url': p.thumbnail_url,
            'caption': p.caption,
            'location': p.location,
            'views': p.views,
            'likes': p.likes_count,
            'comments': p.comments_count,
            'shares': p.shares_count,
            'created_at': p.created_at.isoformat()
        })
    
    return jsonify({
        'items': result,
        'total': posts.total,
        'page': posts.page,
        'pages': posts.pages
    })

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    p = Post.query.get(post_id)
    if not p:
        return jsonify({'error': 'پست یافت نشد'}), 404
    
    # افزایش بازدید
    p.views += 1
    db.session.commit()
    
    user = User.query.get(p.user_id)
    comments = Comment.query.filter_by(post_id=p.id, parent_id=None)\
        .order_by(Comment.created_at.desc()).limit(10).all()
    
    return jsonify({
        'id': p.id,
        'user_id': p.user_id,
        'username': user.username if user else 'unknown',
        'user_avatar': user.avatar if user else '',
        'is_verified': user.is_verified if user else False,
        'media_type': p.media_type,
        'media_url': p.media_url,
        'thumbnail_url': p.thumbnail_url,
        'caption': p.caption,
        'location': p.location,
        'views': p.views,
        'likes': p.likes_count,
        'comments': [{
            'id': c.id,
            'user_id': c.user_id,
            'username': User.query.get(c.user_id).username,
            'user_avatar': User.query.get(c.user_id).avatar,
            'text': c.text,
            'likes_count': c.likes_count,
            'created_at': c.created_at.isoformat()
        } for c in comments],
        'created_at': p.created_at.isoformat()
    })

@app.route('/api/posts', methods=['POST'])
@token_required
@rate_limit(20, 60)
def create_post(current_user):
    caption = request.form.get('caption', '')
    location = request.form.get('location', '')
    media_type = request.form.get('media_type', 'image')
    
    if 'file' not in request.files:
        return jsonify({'error': 'فایلی ارسال نشده است'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'فایلی انتخاب نشده است'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'فرمت فایل پشتیبانی نمی‌شود'}), 400
    
    # ذخیره فایل
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{datetime.utcnow().timestamp()}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # تولید تامب‌نیل
    thumbnail_path = None
    if media_type == 'image':
        thumb_filename = f"thumb_{filename}"
        thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumb_filename)
        if generate_thumbnail(filepath, thumb_path):
            thumbnail_path = f"/thumbnails/{thumb_filename}"
    elif media_type == 'video':
        thumb_filename = f"thumb_{filename}.jpg"
        thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumb_filename)
        if generate_video_thumbnail(filepath, thumb_path):
            thumbnail_path = f"/thumbnails/{thumb_filename}"
    
    # ذخیره در دیتابیس
    post = Post(
        user_id=current_user.id,
        media_type=media_type,
        media_url=f"/uploads/{filename}",
        thumbnail_url=thumbnail_path,
        caption=caption,
        location=location
    )
    db.session.add(post)
    db.session.commit()
    
    # استخراج هشتگ‌ها
    import re
    hashtags = re.findall(r'#([\w]+)', caption)
    for tag_name in hashtags:
        hashtag = Hashtag.query.filter_by(name=tag_name).first()
        if not hashtag:
            hashtag = Hashtag(name=tag_name)
            db.session.add(hashtag)
            db.session.flush()
        ph = PostHashtag(post_id=post.id, hashtag_id=hashtag.id)
        db.session.add(ph)
        hashtag.posts_count += 1
    
    db.session.commit()
    CacheService.clear_pattern("posts:*")
    
    return jsonify({
        'message': 'پست با موفقیت ایجاد شد',
        'id': post.id,
        'media_url': post.media_url
    })

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@token_required
def like_post(current_user, post_id):
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'error': 'پست یافت نشد'}), 404
    
    existing = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        db.session.delete(existing)
        post.likes_count -= 1
        db.session.commit()
        return jsonify({'liked': False, 'likes_count': post.likes_count})
    
    like = Like(user_id=current_user.id, post_id=post_id)
    db.session.add(like)
    post.likes_count += 1
    db.session.commit()
    
    if post.user_id != current_user.id:
        send_notification(post.user_id, current_user.id, 'like', post_id)
    
    return jsonify({'liked': True, 'likes_count': post.likes_count})

@app.route('/api/posts/<int:post_id>/comment', methods=['POST'])
@token_required
def add_comment(current_user, post_id):
    data = request.json
    text = data.get('text', '').strip()
    parent_id = data.get('parent_id')
    
    if not text:
        return jsonify({'error': 'متن کامنت نمی‌تواند خالی باشد'}), 400
    
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'error': 'پست یافت نشد'}), 404
    
    comment = Comment(
        user_id=current_user.id,
        post_id=post_id,
        parent_id=parent_id,
        text=text
    )
    db.session.add(comment)
    post.comments_count += 1
    db.session.commit()
    
    if post.user_id != current_user.id:
        send_notification(post.user_id, current_user.id, 'comment', post_id)
    
    return jsonify({
        'message': 'کامنت با موفقیت ارسال شد',
        'id': comment.id,
        'username': current_user.username,
        'user_avatar': current_user.avatar,
        'text': comment.text,
        'created_at': comment.created_at.isoformat()
    })

@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    comments = Comment.query.filter_by(post_id=post_id, parent_id=None)\
        .order_by(Comment.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for c in comments.items:
        user = User.query.get(c.user_id)
        replies = Comment.query.filter_by(parent_id=c.id).count()
        result.append({
            'id': c.id,
            'user_id': c.user_id,
            'username': user.username if user else 'unknown',
            'user_avatar': user.avatar if user else '',
            'text': c.text,
            'likes_count': c.likes_count,
            'replies_count': replies,
            'created_at': c.created_at.isoformat()
        })
    
    return jsonify({
        'items': result,
        'total': comments.total,
        'page': comments.page,
        'pages': comments.pages
    })

@app.route('/api/posts/<int:post_id>/share', methods=['POST'])
@token_required
def share_post(current_user, post_id):
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'error': 'پست یافت نشد'}), 404
    
    post.shares_count += 1
    db.session.commit()
    
    return jsonify({'message': 'پست با موفقیت به اشتراک گذاشته شد', 'shares_count': post.shares_count})

@app.route('/api/posts/<int:post_id>/save', methods=['POST'])
@token_required
def save_post(current_user, post_id):
    data = request.json
    collection = data.get('collection', 'default')
    
    post = Post.query.get(post_id)
    if not post:
        return jsonify({'error': 'پست یافت نشد'}), 404
    
    existing = SavedPost.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'saved': False})
    
    saved = SavedPost(
        user_id=current_user.id,
        post_id=post_id,
        collection_name=collection
    )
    db.session.add(saved)
    db.session.commit()
    
    return jsonify({'saved': True})

# ---------- استوری‌ها ----------
@app.route('/api/stories', methods=['GET'])
def get_stories():
    now = datetime.utcnow()
    stories = Story.query.filter(Story.expires_at > now)\
        .order_by(Story.created_at.desc()).all()
    
    result = []
    for s in stories:
        user = User.query.get(s.user_id)
        result.append({
            'id': s.id,
            'user_id': s.user_id,
            'username': user.username if user else 'unknown',
            'user_avatar': user.avatar if user else '',
            'media_type': s.media_type,
            'media_url': s.media_url,
            'thumbnail_url': s.thumbnail_url,
            'caption': s.caption,
            'views': s.views,
            'expires_at': s.expires_at.isoformat(),
            'created_at': s.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/stories', methods=['POST'])
@token_required
@rate_limit(10, 60)
def create_story(current_user):
    caption = request.form.get('caption', '')
    
    if 'file' not in request.files:
        return jsonify({'error': 'فایلی ارسال نشده است'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'فایلی انتخاب نشده است'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'فرمت فایل پشتیبانی نمی‌شود'}), 400
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"story_{datetime.utcnow().timestamp()}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    media_type = 'image' if ext in ['png', 'jpg', 'jpeg', 'gif'] else 'video'
    thumbnail_path = None
    if media_type == 'image':
        thumb_filename = f"thumb_{filename}"
        thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumb_filename)
        if generate_thumbnail(filepath, thumb_path):
            thumbnail_path = f"/thumbnails/{thumb_filename}"
    else:
        thumb_filename = f"thumb_{filename}.jpg"
        thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumb_filename)
        if generate_video_thumbnail(filepath, thumb_path):
            thumbnail_path = f"/thumbnails/{thumb_filename}"
    
    story = Story(
        user_id=current_user.id,
        media_type=media_type,
        media_url=f"/uploads/{filename}",
        thumbnail_url=thumbnail_path,
        caption=caption,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.session.add(story)
    db.session.commit()
    
    return jsonify({
        'message': 'استوری با موفقیت ایجاد شد',
        'id': story.id,
        'media_url': story.media_url
    })

@app.route('/api/stories/<int:story_id>/view', methods=['POST'])
@token_required
def view_story(current_user, story_id):
    story = Story.query.get(story_id)
    if not story:
        return jsonify({'error': 'استوری یافت نشد'}), 404
    
    existing = StoryView.query.filter_by(story_id=story_id, user_id=current_user.id).first()
    if not existing:
        view = StoryView(story_id=story_id, user_id=current_user.id)
        db.session.add(view)
        story.views += 1
        db.session.commit()
    
    return jsonify({'message': 'استوری مشاهده شد'})

# ---------- پیام‌ها (چت) ----------
@app.route('/api/messages', methods=['GET'])
@token_required
def get_messages(current_user):
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'شناسه کاربر مورد نیاز است'}), 400
    
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at).all()
    
    # علامت‌گذاری به عنوان خوانده شده
    for m in messages:
        if m.receiver_id == current_user.id and not m.is_read:
            m.is_read = True
            m.read_at = datetime.utcnow()
    db.session.commit()
    
    result = []
    for m in messages:
        result.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'receiver_id': m.receiver_id,
            'message_type': m.message_type,
            'content': m.content,
            'media_url': m.media_url,
            'is_read': m.is_read,
            'created_at': m.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/messages', methods=['POST'])
@token_required
def send_message(current_user):
    data = request.json
    receiver_id = data.get('receiver_id')
    message_type = data.get('message_type', 'text')
    content = data.get('content', '')
    media_url = data.get('media_url')
    
    if not receiver_id:
        return jsonify({'error': 'شناسه گیرنده مورد نیاز است'}), 400
    
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({'error': 'کاربر گیرنده یافت نشد'}), 404
    
    if message_type == 'text' and not content:
        return jsonify({'error': 'متن پیام نمی‌تواند خالی باشد'}), 400
    
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        message_type=message_type,
        content=content,
        media_url=media_url
    )
    db.session.add(message)
    db.session.commit()
    
    # ارسال از طریق WebSocket
    socketio.emit('new_message', {
        'id': message.id,
        'sender_id': message.sender_id,
        'receiver_id': message.receiver_id,
        'message_type': message.message_type,
        'content': message.content,
        'media_url': message.media_url,
        'created_at': message.created_at.isoformat()
    }, room=f'user_{receiver_id}')
    
    return jsonify({
        'message': 'پیام با موفقیت ارسال شد',
        'id': message.id,
        'created_at': message.created_at.isoformat()
    })

@app.route('/api/messages/conversations', methods=['GET'])
@token_required
def get_conversations(current_user):
    # لیست گفتگوها
    sent = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id).distinct().all()
    received = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id).distinct().all()
    
    user_ids = set([r[0] for r in sent] + [r[0] for r in received])
    result = []
    for uid in user_ids:
        user = User.query.get(uid)
        if user:
            last_msg = Message.query.filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == uid)) |
                ((Message.sender_id == uid) & (Message.receiver_id == current_user.id))
            ).order_by(Message.created_at.desc()).first()
            
            unread = Message.query.filter_by(sender_id=uid, receiver_id=current_user.id, is_read=False).count()
            
            result.append({
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'avatar': user.avatar,
                'last_message': last_msg.content if last_msg else None,
                'last_message_time': last_msg.created_at.isoformat() if last_msg else None,
                'unread_count': unread
            })
    
    return jsonify(result)

# ---------- اعلان‌ها ----------
@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifications(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for n in notifications.items:
        actor = User.query.get(n.actor_id)
        result.append({
            'id': n.id,
            'type': n.type,
            'actor_id': n.actor_id,
            'actor_username': actor.username if actor else 'unknown',
            'actor_avatar': actor.avatar if actor else '',
            'target_id': n.target_id,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        })
    
    # علامت‌گذاری همه به عنوان خوانده شده
    for n in notifications.items:
        n.is_read = True
    db.session.commit()
    
    return jsonify({
        'items': result,
        'total': notifications.total,
        'page': notifications.page,
        'pages': notifications.pages
    })

# ---------- جستجو ----------
@app.route('/api/search', methods=['GET'])
def search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'users': [], 'posts': [], 'hashtags': []})
    
    # جستجوی کاربران
    users = User.query.filter(
        (User.username.contains(q)) | (User.full_name.contains(q))
    ).limit(10).all()
    
    # جستجوی پست‌ها
    posts = Post.query.filter(
        Post.caption.contains(q),
        Post.is_archived == False
    ).order_by(Post.created_at.desc()).limit(10).all()
    
    # جستجوی هشتگ‌ها
    hashtags = Hashtag.query.filter(Hashtag.name.contains(q)).limit(10).all()
    
    return jsonify({
        'users': [{
            'id': u.id,
            'username': u.username,
            'full_name': u.full_name,
            'avatar': u.avatar,
            'is_verified': u.is_verified
        } for u in users],
        'posts': [{
            'id': p.id,
            'media_url': p.media_url,
            'thumbnail_url': p.thumbnail_url,
            'caption': p.caption,
            'likes_count': p.likes_count
        } for p in posts],
        'hashtags': [{
            'name': h.name,
            'posts_count': h.posts_count
        } for h in hashtags]
    })

# ---------- هشتگ‌ها ----------
@app.route('/api/hashtags/<name>', methods=['GET'])
def get_hashtag(name):
    hashtag = Hashtag.query.filter_by(name=name).first()
    if not hashtag:
        return jsonify({'error': 'هشتگ یافت نشد'}), 404
    
    posts = Post.query.join(PostHashtag).filter(
        PostHashtag.hashtag_id == hashtag.id,
        Post.is_archived == False
    ).order_by(Post.created_at.desc()).limit(20).all()
    
    return jsonify({
        'hashtag': {
            'name': hashtag.name,
            'posts_count': hashtag.posts_count
        },
        'posts': [{
            'id': p.id,
            'media_url': p.media_url,
            'thumbnail_url': p.thumbnail_url,
            'caption': p.caption,
            'likes_count': p.likes_count,
            'created_at': p.created_at.isoformat()
        } for p in posts]
    })

# ---------- فایل‌های استاتیک ----------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/thumbnails/<filename>')
def thumbnail_file(filename):
    return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename)

@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

# ==================== WebSocket رویدادها ====================
@socketio.on('connect')
def handle_connect():
    user = get_user_from_token()
    if user:
        join_room(f'user_{user.id}')
        emit('connected', {'user_id': user.id})
    else:
        emit('error', {'message': 'احراز هویت نشده'})

@socketio.on('disconnect')
def handle_disconnect():
    user = get_user_from_token()
    if user:
        leave_room(f'user_{user.id}')

@socketio.on('typing')
def handle_typing(data):
    receiver_id = data.get('receiver_id')
    if receiver_id:
        emit('typing', {'sender_id': data.get('sender_id'), 'is_typing': data.get('is_typing', True)}, 
             room=f'user_{receiver_id}')

@socketio.on('message_read')
def handle_message_read(data):
    message_id = data.get('message_id')
    if message_id:
        message = Message.query.get(message_id)
        if message:
            message.is_read = True
            message.read_at = datetime.utcnow()
            db.session.commit()

# ==================== پاکسازی خودکار استوری‌ها ====================
def cleanup_stories():
    with app.app_context():
        while True:
            time.sleep(3600)  # هر ساعت
            expired = Story.query.filter(Story.expires_at < datetime.utcnow()).all()
            for story in expired:
                db.session.delete(story)
            db.session.commit()
            print(f"🧹 Cleaned up {len(expired)} expired stories")

# ==================== دیتای اولیه ====================
def init_db():
    db.create_all()
    
    if not User.query.first():
        # ایجاد کاربر ادمین
        admin = User(
            username='admin',
            email='admin@instagram.com',
            password_hash=hashlib.sha256('admin123'.encode()).hexdigest(),
            full_name='مدیر سیستم',
            is_verified=True
        )
        db.session.add(admin)
        db.session.flush()
        
        # ایجاد کاربران نمونه
        users = []
        for i in range(1, 11):
            user = User(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password_hash=hashlib.sha256('password123'.encode()).hexdigest(),
                full_name=f'کاربر {i}',
                avatar=f'https://i.pravatar.cc/150?img={i+10}'
            )
            db.session.add(user)
            users.append(user)
        
        db.session.commit()
        
        # ایجاد پست‌های نمونه
        import random
        sample_images = [
            'https://picsum.photos/600/600?random=1',
            'https://picsum.photos/600/600?random=2',
            'https://picsum.photos/600/600?random=3',
            'https://picsum.photos/600/600?random=4',
            'https://picsum.photos/600/600?random=5',
            'https://picsum.photos/600/600?random=6',
            'https://picsum.photos/600/600?random=7',
            'https://picsum.photos/600/600?random=8',
            'https://picsum.photos/600/600?random=9',
            'https://picsum.photos/600/600?random=10',
        ]
        
        captions = [
            'یک روز زیبا در طبیعت 🌿 #طبیعت #سفر',
            'غروب قشنگ امروز 🌅 #غروب #عشق',
            'عکس جدید از سفر 🏔️ #سفر #کوه',
            'لحظات خوش با دوستان 😊 #دوستی',
            'هنر در طبیعت 🎨 #هنر #طبیعت',
            'شهر در شب 🌃 #شهر #شب',
            'رویای آبی 💙 #رویا #آبی',
            'صبحانه امروز ☕ #صبحانه #قهوه',
            'گل‌های زیبا 🌸 #گل #طبیعت',
            'سفر به جنوب 🌴 #سفر #جنوب'
        ]
        
        for i, user in enumerate(users[:5]):
            for j in range(2):
                idx = (i * 2 + j) % len(sample_images)
                post = Post(
                    user_id=user.id,
                    media_type='image',
                    media_url=sample_images[idx],
                    caption=captions[idx],
                    views=random.randint(100, 3000),
                    likes_count=random.randint(20, 500),
                    comments_count=random.randint(5, 100)
                )
                db.session.add(post)
        
        db.session.commit()
        print("✅ دیتابیس با موفقیت مقداردهی اولیه شد")

# ==================== اجرا ====================
if __name__ == '__main__':
    with app.app_context():
        init_db()
    
    # شروع پاکسازی خودکار استوری‌ها
    threading.Thread(target=cleanup_stories, daemon=True).start()
    
    print("🚀 سرور با موفقیت راه‌اندازی شد!")
    print("📍 آدرس: http://localhost:5000")
    print("🔐 API: http://localhost:5000/api")
    print("💬 WebSocket: ws://localhost:5000/socket.io")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)