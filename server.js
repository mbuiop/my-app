const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const multer = require('multer');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: { origin: "*" }
});

app.use(cors());
app.use(express.json());
app.use(express.static('public'));
app.use('/uploads', express.static('uploads'));

// ============================================
// 📁 ایجاد پوشه‌ها
// ============================================
if (!fs.existsSync('./uploads')) {
    fs.mkdirSync('./uploads');
}
if (!fs.existsSync('./public')) {
    fs.mkdirSync('./public');
}

// ============================================
// 📁 تنظیمات آپلود
// ============================================
const storage = multer.diskStorage({
    destination: './uploads/',
    filename: (req, file, cb) => {
        cb(null, Date.now() + path.extname(file.originalname));
    }
});
const upload = multer({ storage });

// ============================================
// 🗄️ دیتابیس در حافظه
// ============================================
let posts = [];
let users = {};
let chatMessages = {};
let currentId = 1;

// ============================================
// 📡 API
// ============================================

// دریافت پست‌ها
app.get('/api/posts', (req, res) => {
    res.json(posts.sort((a, b) => b.createdAt - a.createdAt));
});

// ایجاد پست جدید
app.post('/api/posts', upload.single('image'), (req, res) => {
    const { caption, userId, userName } = req.body;
    const imageUrl = req.file ? `/uploads/${req.file.filename}` : null;

    const newPost = {
        id: String(currentId++),
        image: imageUrl,
        caption: caption || '',
        userId: userId || 'user1',
        userName: userName || 'کاربر',
        likes: 0,
        comments: [],
        shares: 0,
        views: 0,
        createdAt: Date.now()
    };

    posts.unshift(newPost);
    res.status(201).json(newPost);
});

// لایک کردن
app.put('/api/posts/:id/like', (req, res) => {
    const post = posts.find(p => p.id === req.params.id);
    if (post) {
        post.likes += 1;
        res.json(post);
    } else {
        res.status(404).json({ error: 'Post not found' });
    }
});

// کامنت گذاشتن
app.post('/api/posts/:id/comment', (req, res) => {
    const post = posts.find(p => p.id === req.params.id);
    if (post) {
        const comment = {
            userId: req.body.userId || 'user1',
            userName: req.body.userName || 'کاربر',
            text: req.body.text,
            time: new Date().toLocaleString('fa-IR')
        };
        post.comments.push(comment);
        res.json(post);
    } else {
        res.status(404).json({ error: 'Post not found' });
    }
});

// ============================================
// 💬 WebSocket چت
// ============================================

io.on('connection', (socket) => {
    console.log('🔌 کاربر متصل شد:', socket.id);

    socket.on('register', (data) => {
        const { userId, userName } = data;
        users[userId] = {
            name: userName || 'کاربر',
            online: true,
            lastSeen: Date.now()
        };
        socket.userId = userId;
        socket.userName = userName || 'کاربر';
        io.emit('users-update', users);
    });

    socket.on('join-room', (data) => {
        const { roomId } = data;
        socket.join(roomId);
    });

    socket.on('send-message', (data) => {
        const { roomId, userId, userName, text } = data;
        
        if (!chatMessages[roomId]) chatMessages[roomId] = [];
        chatMessages[roomId].push({
            userId,
            userName: userName || 'کاربر',
            text,
            timestamp: Date.now()
        });

        io.to(roomId).emit('receive-message', {
            userId,
            userName: userName || 'کاربر',
            text,
            timestamp: Date.now()
        });
    });

    socket.on('get-messages', (data) => {
        const { roomId } = data;
        if (chatMessages[roomId]) {
            socket.emit('history-messages', chatMessages[roomId]);
        }
    });

    socket.on('disconnect', () => {
        if (socket.userId && users[socket.userId]) {
            users[socket.userId].online = false;
            users[socket.userId].lastSeen = Date.now();
            io.emit('users-update', users);
        }
    });
});

// ============================================
// 🌐 صفحه HTML
// ============================================
app.get('/', (req, res) => {
    res.send(`
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سوشال مدیا</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #fafafa; font-family: Tahoma, sans-serif; height: 100vh; display: flex; flex-direction: column; overflow: hidden; transition: background 0.3s, color 0.3s; }
        body.dark-theme { background: #121212; color: #ffffff; }
        body.dark-theme .header { background: #1e1e1e; border-bottom-color: #2c2c2c; }
        body.dark-theme .header .menu-icon, body.dark-theme .header .header-right i { color: #ffffff; }
        body.dark-theme .search-box { background: #2c2c2c; }
        body.dark-theme .search-box input { color: #ffffff; }
        body.dark-theme .search-box input::placeholder { color: #888; }
        body.dark-theme .gallery-item { background: #1e1e1e; border-color: #2c2c2c; }
        body.dark-theme .bottom-nav { background: #1e1e1e; border-top-color: #2c2c2c; }
        body.dark-theme .bottom-nav button { color: #ffffff; }
        body.dark-theme .bottom-nav button i { color: #ffffff; }
        body.dark-theme .profile-page { background: #121212; }
        body.dark-theme .profile-info { background: #1e1e1e; border-bottom-color: #2c2c2c; }
        body.dark-theme .profile-username, body.dark-theme .profile-bio { color: #ffffff; }
        body.dark-theme .profile-stats { background: #1e1e1e; border-bottom-color: #2c2c2c; }
        body.dark-theme .profile-stats .stat .number { color: #ffffff; }
        body.dark-theme .profile-stats .stat .label { color: #888; }
        body.dark-theme .profile-gallery { background: #121212; }
        body.dark-theme .profile-header { background: #1e1e1e; border-bottom-color: #2c2c2c; }
        body.dark-theme .profile-header h2 { color: #ffffff; }
        body.dark-theme .profile-header .close-profile { color: #ffffff; }
        body.dark-theme .side-menu { background: #1e1e1e; }
        body.dark-theme .side-menu .menu-header { border-bottom-color: #2c2c2c; }
        body.dark-theme .side-menu .menu-header h3 { color: #ffffff; }
        body.dark-theme .side-menu .menu-header .close-menu { color: #ffffff; }
        body.dark-theme .side-menu .menu-item { border-bottom-color: #2c2c2c; color: #ffffff; }
        body.dark-theme .side-menu .menu-item:hover { background: #2c2c2c; }
        body.dark-theme .side-menu .menu-item i { color: #ffffff; }
        body.dark-theme .chat-interface { background: #1e1e1e; }
        body.dark-theme .chat-messages { background: #121212; }
        body.dark-theme .chat-message { background: #2c2c2c; color: #ffffff; }
        body.dark-theme .chat-message.own { background: #0095f6; color: #ffffff; }
        body.dark-theme .chat-input input { background: #2c2c2c; color: #ffffff; border-color: #3c3c3c; }
        body.dark-theme .chat-user { color: #ffffff; }
        body.dark-theme .chat-user:hover { background: #2c2c2c; }
        body.dark-theme .modal-content { background: #1e1e1e; }
        body.dark-theme .modal-header { border-bottom-color: #2c2c2c; }
        body.dark-theme .modal-header h3 { color: #ffffff; }
        body.dark-theme .modal-header .close-modal { color: #ffffff; }
        body.dark-theme .comment-item { border-bottom-color: #2c2c2c; }
        body.dark-theme .comment-username { color: #ffffff; }
        body.dark-theme .comment-text { color: #ddd; }
        body.dark-theme .comment-time { color: #888; }
        body.dark-theme .modal-footer { border-top-color: #2c2c2c; }
        body.dark-theme .modal-footer input { background: #2c2c2c; color: #ffffff; border-color: #3c3c3c; }
        body.dark-theme .upload-page { background: #121212; }
        body.dark-theme .upload-header { background: #1e1e1e; border-bottom-color: #2c2c2c; }
        body.dark-theme .upload-header h2 { color: #ffffff; }
        body.dark-theme .upload-header .close-upload { color: #ffffff; }
        body.dark-theme .upload-container { background: #1e1e1e; border-color: #2c2c2c; }
        body.dark-theme .upload-container h3 { color: #ffffff; }
        body.dark-theme .upload-container p { color: #888; }
        body.dark-theme .upload-caption textarea { background: #2c2c2c; color: #ffffff; border-color: #3c3c3c; }
        body.dark-theme .follow-modal-content { background: #1e1e1e; }
        body.dark-theme .follow-modal-header { border-bottom-color: #2c2c2c; }
        body.dark-theme .follow-modal-header h3 { color: #ffffff; }
        body.dark-theme .follow-modal-header .close-follow { color: #ffffff; }
        body.dark-theme .follow-item { border-bottom-color: #2c2c2c; }
        body.dark-theme .follow-item .follow-name { color: #ffffff; }
        body.dark-theme .share-modal-content { background: #1e1e1e; }
        body.dark-theme .share-modal-header { border-bottom-color: #2c2c2c; }
        body.dark-theme .share-modal-header h3 { color: #ffffff; }
        body.dark-theme .share-modal-header .close-share { color: #ffffff; }
        body.dark-theme .share-option { border-bottom-color: #2c2c2c; }
        body.dark-theme .share-option:hover { background: #2c2c2c; }
        body.dark-theme .share-option .share-name { color: #ffffff; }
        .header { background: white; border-bottom: 1px solid #dbdbdb; padding: 12px 16px; position: sticky; top: 0; z-index: 100; display: flex; align-items: center; gap: 15px; flex-shrink: 0; }
        .menu-icon { font-size: 24px; color: #262626; cursor: pointer; }
        .search-box { flex: 1; background: #efefef; padding: 8px 15px; border-radius: 25px; display: flex; align-items: center; gap: 10px; }
        .search-box input { border: none; background: transparent; outline: none; width: 100%; font-size: 14px; }
        .search-box i { color: #8e8e8e; }
        .header-right { display: flex; gap: 18px; font-size: 22px; color: #262626; }
        .header-right i { cursor: pointer; }
        .header-right i:hover { color: #0095f6; }
        .stories-section { background: white; padding: 15px 16px; border-bottom: 1px solid #dbdbdb; overflow-x: auto; flex-shrink: 0; }
        .stories-container { display: flex; gap: 20px; }
        .story-item { display: flex; flex-direction: column; align-items: center; gap: 5px; cursor: pointer; flex-shrink: 0; }
        .story-avatar { width: 60px; height: 60px; border-radius: 50%; padding: 3px; background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); }
        .story-avatar img { width: 100%; height: 100%; border-radius: 50%; border: 2px solid white; object-fit: cover; }
        .story-username { font-size: 11px; color: #262626; max-width: 60px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; }
        .gallery-wrapper { flex: 1; overflow-y: auto; padding-bottom: 10px; }
        .gallery { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; padding: 3px; }
        .gallery-item { background: white; overflow: hidden; border: 1px solid #dbdbdb; cursor: pointer; position: relative; }
        .gallery-item .image-container { width: 100%; aspect-ratio: 1 / 1; overflow: hidden; background: #ddd; }
        .gallery-item .image-container img { width: 100%; height: 100%; object-fit: cover; }
        .gallery-item .explore-post-actions { display: flex; position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); padding: 6px; justify-content: space-around; color: white; }
        .gallery-item .explore-post-actions .action-btn { display: flex; align-items: center; gap: 4px; color: white; font-size: 12px; cursor: pointer; padding: 3px 6px; border-radius: 4px; border: none; background: transparent; }
        .gallery-item .explore-post-actions .action-btn:hover { background: rgba(255,255,255,0.2); }
        .gallery-item .explore-post-actions .action-btn.liked i { color: #ff4757; }
        .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: white; border-top: 1px solid #dbdbdb; display: flex; justify-content: space-around; align-items: center; padding: 12px 0; z-index: 100; }
        .bottom-nav button { background: transparent; border: none; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 4px; font-size: 12px; color: #262626; padding: 5px 15px; border-radius: 30px; }
        .bottom-nav button i { font-size: 26px; color: #262626; }
        .bottom-nav button:hover { background: #efefef; }
        .bottom-nav button.active i { color: #0095f6; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 300; justify-content: center; align-items: center; padding: 20px; }
        .modal-overlay.active { display: flex; }
        .modal-content { background: white; border-radius: 16px; max-width: 500px; width: 100%; max-height: 80vh; display: flex; flex-direction: column; overflow: hidden; direction: rtl; }
        .modal-header { padding: 16px 20px; border-bottom: 1px solid #dbdbdb; display: flex; justify-content: space-between; align-items: center; }
        .modal-header h3 { font-size: 16px; color: #262626; }
        .modal-header .close-modal { font-size: 24px; cursor: pointer; color: #262626; background: none; border: none; }
        .modal-body { flex: 1; overflow-y: auto; padding: 16px 20px; }
        .comment-item { display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px solid #efefef; }
        .comment-item:last-child { border-bottom: none; }
        .comment-avatar { width: 36px; height: 36px; border-radius: 50%; background: #ddd; flex-shrink: 0; overflow: hidden; }
        .comment-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .comment-content { flex: 1; }
        .comment-username { font-weight: 600; font-size: 13px; color: #262626; }
        .comment-text { font-size: 13px; color: #262626; margin-top: 2px; }
        .comment-time { font-size: 11px; color: #8e8e8e; margin-top: 4px; }
        .modal-footer { padding: 12px 20px; border-top: 1px solid #dbdbdb; display: flex; gap: 10px; }
        .modal-footer input { flex: 1; padding: 8px 12px; border: 1px solid #dbdbdb; border-radius: 20px; outline: none; font-size: 14px; direction: rtl; }
        .modal-footer button { background: #0095f6; color: white; border: none; padding: 8px 20px; border-radius: 20px; font-weight: 600; cursor: pointer; }
        .modal-footer button:hover { background: #0081d6; }
        .profile-page { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #fafafa; z-index: 150; overflow-y: auto; padding-top: 60px; }
        .profile-page.active { display: block; }
        .profile-header { position: fixed; top: 0; left: 0; right: 0; background: white; padding: 12px 16px; border-bottom: 1px solid #dbdbdb; z-index: 151; display: flex; justify-content: space-between; align-items: center; }
        .profile-header h2 { font-size: 18px; color: #262626; }
        .profile-header .close-profile { font-size: 24px; cursor: pointer; color: #262626; background: none; border: none; }
        .profile-info { background: white; padding: 20px; margin-top: 10px; display: flex; flex-direction: column; align-items: center; border-bottom: 1px solid #dbdbdb; }
        .profile-avatar-large { width: 100px; height: 100px; border-radius: 50%; overflow: hidden; border: 3px solid #dbdbdb; margin-bottom: 10px; }
        .profile-avatar-large img { width: 100%; height: 100%; object-fit: cover; }
        .profile-username { font-size: 20px; font-weight: 600; color: #262626; }
        .profile-bio { font-size: 14px; color: #262626; margin: 8px 0; text-align: center; padding: 0 20px; }
        .profile-bio-edit { display: flex; gap: 10px; margin: 10px 0; width: 100%; max-width: 300px; }
        .profile-bio-edit input { flex: 1; padding: 8px 12px; border: 1px solid #dbdbdb; border-radius: 8px; outline: none; font-size: 14px; direction: rtl; }
        .profile-bio-edit button { padding: 8px 16px; background: #0095f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .profile-stats { display: flex; justify-content: space-around; padding: 15px 0; background: white; border-bottom: 1px solid #dbdbdb; width: 100%; }
        .profile-stats .stat { display: flex; flex-direction: column; align-items: center; cursor: pointer; }
        .profile-stats .stat:hover { opacity: 0.7; }
        .profile-stats .stat .number { font-size: 18px; font-weight: 600; color: #262626; }
        .profile-stats .stat .label { font-size: 13px; color: #8e8e8e; }
        .profile-follow-btn { padding: 8px 30px; background: #0095f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; margin: 5px 0; }
        .profile-follow-btn:hover { background: #0081d6; }
        .profile-follow-btn.following { background: #efefef; color: #262626; }
        .profile-gallery { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; padding: 3px; background: #fafafa; }
        .profile-post { aspect-ratio: 1 / 1; overflow: hidden; background: #ddd; position: relative; cursor: pointer; }
        .profile-post .image-container { width: 100%; height: 100%; position: relative; }
        .profile-post .image-container img { width: 100%; height: 100%; object-fit: cover; }
        .profile-post .image-container .profile-post-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.3); display: flex; justify-content: center; align-items: center; gap: 20px; color: white; opacity: 0; transition: opacity 0.3s; }
        .profile-post .image-container:hover .profile-post-overlay { opacity: 1; }
        .profile-post .image-container .profile-post-overlay span { display: flex; align-items: center; gap: 5px; font-size: 14px; font-weight: 600; }
        .profile-post .image-container .profile-post-overlay i { font-size: 16px; }
        .upload-page { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #fafafa; z-index: 150; overflow-y: auto; padding-top: 60px; }
        .upload-page.active { display: block; }
        .upload-header { position: fixed; top: 0; left: 0; right: 0; background: white; padding: 12px 16px; border-bottom: 1px solid #dbdbdb; z-index: 151; display: flex; justify-content: space-between; align-items: center; }
        .upload-header h2 { font-size: 18px; color: #262626; }
        .upload-header .close-upload { font-size: 24px; cursor: pointer; color: #262626; background: none; border: none; }
        .upload-container { background: white; margin: 10px 16px; border-radius: 16px; padding: 30px 20px; border: 2px dashed #dbdbdb; text-align: center; min-height: 300px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .upload-container i { font-size: 60px; color: #0095f6; margin-bottom: 20px; }
        .upload-container h3 { font-size: 20px; color: #262626; margin-bottom: 10px; }
        .upload-container p { font-size: 14px; color: #8e8e8e; margin-bottom: 20px; }
        .upload-container input[type="file"] { display: none; }
        .upload-container .upload-btn { padding: 10px 30px; background: #0095f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 16px; }
        .upload-container .upload-btn:hover { background: #0081d6; }
        .upload-preview { display: none; margin-top: 20px; width: 100%; max-width: 300px; margin-left: auto; margin-right: auto; }
        .upload-preview img, .upload-preview video { width: 100%; border-radius: 8px; max-height: 300px; object-fit: cover; }
        .upload-preview.active { display: block; }
        .upload-caption { display: none; margin-top: 15px; width: 100%; max-width: 300px; margin-left: auto; margin-right: auto; }
        .upload-caption.active { display: block; }
        .upload-caption textarea { width: 100%; padding: 10px; border: 1px solid #dbdbdb; border-radius: 8px; outline: none; font-size: 14px; font-family: Tahoma, sans-serif; resize: vertical; min-height: 60px; direction: rtl; }
        .upload-submit { display: none; margin-top: 10px; padding: 10px 30px; background: #0095f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 16px; }
        .upload-submit.active { display: inline-block; }
        .upload-submit:hover { background: #0081d6; }
        .follow-modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 400; justify-content: center; align-items: center; padding: 20px; }
        .follow-modal.active { display: flex; }
        .follow-modal-content { background: white; border-radius: 16px; max-width: 400px; width: 100%; max-height: 70vh; display: flex; flex-direction: column; overflow: hidden; direction: rtl; }
        .follow-modal-header { padding: 16px 20px; border-bottom: 1px solid #dbdbdb; display: flex; justify-content: space-between; align-items: center; }
        .follow-modal-header h3 { font-size: 16px; color: #262626; }
        .follow-modal-header .close-follow { font-size: 24px; cursor: pointer; color: #262626; background: none; border: none; }
        .follow-modal-body { flex: 1; overflow-y: auto; padding: 16px 20px; }
        .follow-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #efefef; }
        .follow-item:last-child { border-bottom: none; }
        .follow-item .follow-avatar { width: 40px; height: 40px; border-radius: 50%; overflow: hidden; background: #ddd; flex-shrink: 0; }
        .follow-item .follow-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .follow-item .follow-name { flex: 1; font-size: 14px; color: #262626; font-weight: 500; }
        .follow-item .follow-btn { padding: 6px 16px; background: #0095f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
        .follow-item .follow-btn:hover { background: #0081d6; }
        .follow-item .follow-btn.following { background: #efefef; color: #262626; }
        .share-modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 500; justify-content: center; align-items: center; padding: 20px; }
        .share-modal.active { display: flex; }
        .share-modal-content { background: white; border-radius: 16px; max-width: 400px; width: 100%; max-height: 70vh; display: flex; flex-direction: column; overflow: hidden; direction: rtl; }
        .share-modal-header { padding: 16px 20px; border-bottom: 1px solid #dbdbdb; display: flex; justify-content: space-between; align-items: center; }
        .share-modal-header h3 { font-size: 16px; color: #262626; }
        .share-modal-header .close-share { font-size: 24px; cursor: pointer; color: #262626; background: none; border: none; }
        .share-modal-body { flex: 1; overflow-y: auto; padding: 16px 20px; }
        .share-option { display: flex; align-items: center; gap: 15px; padding: 12px 0; border-bottom: 1px solid #efefef; cursor: pointer; }
        .share-option:hover { background: #fafafa; }
        .share-option .share-icon { width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; color: white; flex-shrink: 0; }
        .share-option .share-icon.telegram { background: #0088cc; }
        .share-option .share-icon.whatsapp { background: #25d366; }
        .share-option .share-icon.instagram { background: #e4405f; }
        .share-option .share-icon.copy { background: #6c757d; }
        .share-option .share-icon.site { background: #0095f6; }
        .share-option .share-name { font-size: 15px; color: #262626; font-weight: 500; }
        .menu-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 600; }
        .menu-overlay.active { display: block; }
        .side-menu { position: fixed; top: 0; right: -300px; width: 280px; height: 100%; background: white; z-index: 601; transition: right 0.3s ease; padding-top: 20px; box-shadow: -2px 0 10px rgba(0,0,0,0.1); overflow-y: auto; }
        .side-menu.active { right: 0; }
        .side-menu .menu-header { padding: 16px 20px; border-bottom: 1px solid #dbdbdb; display: flex; align-items: center; justify-content: space-between; }
        .side-menu .menu-header h3 { font-size: 18px; color: #262626; }
        .side-menu .menu-header .close-menu { font-size: 24px; cursor: pointer; color: #262626; background: none; border: none; }
        .side-menu .menu-item { display: flex; align-items: center; gap: 15px; padding: 16px 20px; border-bottom: 1px solid #efefef; cursor: pointer; color: #262626; }
        .side-menu .menu-item:hover { background: #fafafa; }
        .side-menu .menu-item i { font-size: 20px; width: 25px; color: #262626; }
        .side-menu .menu-item .menu-text { font-size: 15px; font-weight: 500; }
        .loading-spinner { text-align: center; padding: 50px; color: #0095f6; font-size: 18px; }
        .loading-spinner i { font-size: 40px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .no-posts { text-align: center; padding: 50px; color: #8e8e8e; font-size: 16px; }
        .no-posts i { font-size: 50px; color: #dbdbdb; display: block; margin-bottom: 15px; }

        .chat-interface { display: none; position: fixed; bottom: 70px; left: 0; right: 0; top: 60px; background: white; z-index: 200; flex-direction: column; border-top: 1px solid #dbdbdb; }
        .chat-interface.active { display: flex; }
        .chat-header-bar { padding: 12px 16px; border-bottom: 1px solid #dbdbdb; display: flex; justify-content: space-between; align-items: center; background: white; flex-shrink: 0; }
        .chat-header-bar h3 { font-size: 16px; color: #262626; }
        .chat-header-bar .close-chat-btn { font-size: 24px; cursor: pointer; color: #262626; background: none; border: none; }
        .chat-users-list { border-bottom: 1px solid #dbdbdb; max-height: 150px; overflow-y: auto; flex-shrink: 0; background: #fafafa; }
        .chat-user { display: flex; align-items: center; gap: 12px; padding: 10px 16px; cursor: pointer; border-bottom: 1px solid #efefef; }
        .chat-user:hover { background: #efefef; }
        .chat-user .user-avatar { width: 40px; height: 40px; border-radius: 50%; overflow: hidden; background: #ddd; flex-shrink: 0; }
        .chat-user .user-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .chat-user .user-name { font-size: 14px; color: #262626; font-weight: 500; }
        .chat-user .user-status { font-size: 11px; color: #8e8e8e; }
        .chat-user .user-status.online { color: #2ecc71; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 15px; background: #fafafa; display: flex; flex-direction: column; gap: 8px; }
        .chat-message { max-width: 75%; padding: 10px 14px; border-radius: 16px; background: white; box-shadow: 0 1px 2px rgba(0,0,0,0.1); align-self: flex-start; word-wrap: break-word; }
        .chat-message.own { align-self: flex-end; background: #0095f6; color: white; }
        .chat-message .msg-user { font-size: 11px; font-weight: 600; color: #0095f6; margin-bottom: 3px; }
        .chat-message.own .msg-user { color: rgba(255,255,255,0.8); }
        .chat-message .msg-text { font-size: 14px; }
        .chat-message .msg-time { font-size: 10px; color: #8e8e8e; margin-top: 4px; text-align: left; }
        .chat-message.own .msg-time { color: rgba(255,255,255,0.7); }
        .chat-input { display: flex; gap: 10px; padding: 10px 16px; border-top: 1px solid #dbdbdb; background: white; flex-shrink: 0; }
        .chat-input input { flex: 1; padding: 10px 14px; border: 1px solid #dbdbdb; border-radius: 25px; outline: none; font-size: 14px; direction: rtl; }
        .chat-input button { padding: 10px 20px; background: #0095f6; color: white; border: none; border-radius: 25px; cursor: pointer; font-size: 16px; }
        .chat-input button:hover { background: #0081d6; }
        .chat-empty { text-align: center; padding: 40px; color: #8e8e8e; }
        .chat-empty i { font-size: 40px; display: block; margin-bottom: 15px; color: #dbdbdb; }

        @media (max-width: 400px) { .gallery { gap: 2px; padding: 2px; } .chat-message { max-width: 90%; } }
    </style>
</head>
<body>

    <header class="header">
        <i class="fas fa-bars menu-icon" id="menuIcon"></i>
        <div class="search-box">
            <i class="fas fa-search"></i>
            <input type="text" id="searchInput" placeholder="جستجو...">
        </div>
        <div class="header-right">
            <i class="fas fa-comment-dots" id="chatOpenBtn"></i>
        </div>
    </header>

    <div class="stories-section" id="storiesSection">
        <div class="stories-container" id="storiesContainer"></div>
    </div>

    <div class="gallery-wrapper">
        <div id="loadingIndicator" class="loading-spinner">
            <i class="fas fa-spinner"></i><br> در حال بارگذاری...
        </div>
        <div class="gallery" id="gallery"></div>
        <div id="noPostsMessage" class="no-posts" style="display:none;">
            <i class="fas fa-camera"></i>
            هیچ پستی وجود ندارد<br> اولین پست را شما آپلود کنید!
        </div>
    </div>

    <div class="chat-interface" id="chatInterface">
        <div class="chat-header-bar">
            <h3 id="chatTitle">💬 چت</h3>
            <button class="close-chat-btn" id="closeChatBtn">&times;</button>
        </div>
        <div class="chat-users-list" id="chatUsersList"></div>
        <div class="chat-messages" id="chatMessages">
            <div class="chat-empty">
                <i class="fas fa-comments"></i>
                برای شروع چت، یک کاربر را انتخاب کنید
            </div>
        </div>
        <div class="chat-input">
            <input type="text" id="chatInput" placeholder="پیام خود را بنویسید...">
            <button id="chatSendBtn"><i class="fas fa-paper-plane"></i></button>
        </div>
    </div>

    <div class="modal-overlay" id="commentModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>کامنت‌ها</h3>
                <button class="close-modal" id="closeModal">&times;</button>
            </div>
            <div class="modal-body" id="commentList"></div>
            <div class="modal-footer">
                <input type="text" id="modalCommentInput" placeholder="کامنت خود را بنویسید...">
                <button id="modalSendComment">ارسال</button>
            </div>
        </div>
    </div>

    <div class="share-modal" id="shareModal">
        <div class="share-modal-content">
            <div class="share-modal-header">
                <h3>اشتراک‌گذاری</h3>
                <button class="close-share" id="closeShareModal">&times;</button>
            </div>
            <div class="share-modal-body">
                <div class="share-option" data-share="telegram">
                    <div class="share-icon telegram"><i class="fab fa-telegram-plane"></i></div>
                    <span class="share-name">ارسال به تلگرام</span>
                </div>
                <div class="share-option" data-share="whatsapp">
                    <div class="share-icon whatsapp"><i class="fab fa-whatsapp"></i></div>
                    <span class="share-name">ارسال به واتساپ</span>
                </div>
                <div class="share-option" data-share="instagram">
                    <div class="share-icon instagram"><i class="fab fa-instagram"></i></div>
                    <span class="share-name">ارسال به اینستاگرام</span>
                </div>
                <div class="share-option" data-share="site">
                    <div class="share-icon site"><i class="fas fa-users"></i></div>
                    <span class="share-name">ارسال به کاربران سایت</span>
                </div>
                <div class="share-option" data-share="copy">
                    <div class="share-icon copy"><i class="fas fa-copy"></i></div>
                    <span class="share-name">کپی لینک پست</span>
                </div>
            </div>
        </div>
    </div>

    <div class="profile-page" id="profilePage">
        <div class="profile-header">
            <h2>پروفایل</h2>
            <button class="close-profile" id="closeProfile">&times;</button>
        </div>
        <div style="margin-top: 60px;">
            <div class="profile-info">
                <div class="profile-avatar-large">
                    <img id="profileAvatar" src="https://i.pravatar.cc/150?img=10" alt="profile">
                </div>
                <div class="profile-username" id="profileUsername">کاربر</div>
                <div class="profile-bio" id="bioDisplay">توسعه‌دهنده وب | عاشق کدنویسی</div>
                <button class="profile-follow-btn" id="profileFollowBtn">دنبال کردن</button>
                <div class="profile-bio-edit">
                    <input type="text" id="bioInput" placeholder="بیوگرافی خود را بنویسید...">
                    <button id="saveBio">ذخیره</button>
                </div>
            </div>
            <div class="profile-stats">
                <div class="stat" id="statPosts">
                    <span class="number" id="postCount">۰</span>
                    <span class="label">پست</span>
                </div>
                <div class="stat" id="statFollowers">
                    <span class="number" id="followerCount">۰</span>
                    <span class="label">دنبال‌کننده</span>
                </div>
                <div class="stat" id="statFollowing">
                    <span class="number" id="followingCount">۰</span>
                    <span class="label">دنبال‌شونده</span>
                </div>
            </div>
            <div style="padding: 10px 0; background: white; margin-top: 5px;">
                <h4 style="padding: 0 20px 10px; font-size: 14px; color: #262626;">پست‌های من</h4>
                <div class="profile-gallery" id="profileGallery"></div>
            </div>
        </div>
    </div>

    <div class="follow-modal" id="followModal">
        <div class="follow-modal-content">
            <div class="follow-modal-header">
                <h3 id="followModalTitle">دنبال‌کنندگان</h3>
                <button class="close-follow" id="closeFollowModal">&times;</button>
            </div>
            <div class="follow-modal-body" id="followModalBody"></div>
        </div>
    </div>

    <div class="menu-overlay" id="menuOverlay"></div>
    <div class="side-menu" id="sideMenu">
        <div class="menu-header">
            <h3>منو</h3>
            <button class="close-menu" id="closeMenu">&times;</button>
        </div>
        <div class="menu-item" id="menuTheme">
            <i class="fas fa-palette"></i>
            <span class="menu-text">تغیر تم</span>
        </div>
        <div class="menu-item" id="menuActivity">
            <i class="fas fa-clock"></i>
            <span class="menu-text">فعالیت من</span>
        </div>
        <div class="menu-item" id="menuStats">
            <i class="fas fa-chart-bar"></i>
            <span class="menu-text">اطلاعات آماری</span>
        </div>
        <div class="menu-item" id="menuLanguage">
            <i class="fas fa-globe"></i>
            <span class="menu-text">تغیر زبان</span>
        </div>
    </div>

    <div class="upload-page" id="uploadPage">
        <div class="upload-header">
            <h2>آپلود</h2>
            <button class="close-upload" id="closeUpload">&times;</button>
        </div>
        <div style="margin-top: 70px; padding: 10px;">
            <div class="upload-container" id="uploadContainer">
                <i class="fas fa-cloud-upload-alt"></i>
                <h3>انتخاب فایل</h3>
                <p>برای آپلود عکس یا ویدئو کلیک کنید</p>
                <button class="upload-btn" id="uploadSelectBtn">انتخاب فایل</button>
                <input type="file" id="fileInput" accept="image/*,video/*">
                <div class="upload-preview" id="uploadPreview">
                    <img id="previewImage" src="#" alt="preview">
                    <video id="previewVideo" controls style="display:none;"></video>
                </div>
                <div class="upload-caption" id="uploadCaption">
                    <textarea id="captionInput" placeholder="توضیحات پست را بنویسید..."></textarea>
                </div>
                <button class="upload-submit" id="uploadSubmit">ارسال پست</button>
            </div>
        </div>
    </div>

    <nav class="bottom-nav">
        <button id="profileBtn">
            <i class="fas fa-user"></i>
            <span>پروفایل</span>
        </button>
        <button id="uploadBtn">
            <i class="fas fa-upload"></i>
            <span>آپلود</span>
        </button>
        <button id="exploreBtn" class="active">
            <i class="fas fa-compass"></i>
            <span>اکسپلور</span>
        </button>
        <button id="reelsBtn">
            <i class="fas fa-film"></i>
            <span>ریلز</span>
        </button>
    </nav>

    <script src="/socket.io/socket.io.js"></script>
    <script>
        const API_URL = window.location.origin;
        const socket = io();
        const USER_ID = 'user_' + Math.random().toString(36).substr(2, 9);
        const USER_NAME = 'کاربر_' + Math.floor(Math.random() * 10000);
        let currentPostId = null;
        let currentChatRoom = null;
        let isDarkTheme = localStorage.getItem('theme') === 'dark';
        let isFollowing = false;

        if (isDarkTheme) document.body.classList.add('dark-theme');

        async function getPosts() {
            const res = await fetch(API_URL + '/api/posts');
            return await res.json();
        }

        async function createPost(imageFile, caption) {
            const formData = new FormData();
            formData.append('image', imageFile);
            formData.append('caption', caption);
            formData.append('userId', USER_ID);
            formData.append('userName', USER_NAME);
            const res = await fetch(API_URL + '/api/posts', { method: 'POST', body: formData });
            return await res.json();
        }

        async function likePost(postId) {
            const res = await fetch(API_URL + '/api/posts/' + postId + '/like', { method: 'PUT' });
            return await res.json();
        }

        async function addComment(postId, text) {
            const res = await fetch(API_URL + '/api/posts/' + postId + '/comment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: USER_ID, userName: USER_NAME, text })
            });
            return await res.json();
        }

        socket.on('connect', () => {
            socket.emit('register', { userId: USER_ID, userName: USER_NAME });
        });

        socket.on('users-update', (users) => {
            const list = document.getElementById('chatUsersList');
            list.innerHTML = '';
            let hasUsers = false;
            for (const [userId, data] of Object.entries(users)) {
                if (userId === USER_ID) continue;
                hasUsers = true;
                const div = document.createElement('div');
                div.className = 'chat-user';
                div.onclick = () => {
                    const roomId = [USER_ID, userId].sort().join('_');
                    currentChatRoom = roomId;
                    document.getElementById('chatTitle').textContent = '💬 چت با ' + data.name;
                    socket.emit('join-room', { roomId });
                    socket.emit('get-messages', { roomId });
                    document.getElementById('chatInterface').classList.add('active');
                };
                div.innerHTML = '<div class="user-avatar"><img src="https://i.pravatar.cc/150?img=' + Math.floor(Math.random() * 70) + '" alt="user"></div><div><div class="user-name">' + data.name + '</div><div class="user-status ' + (data.online ? 'online' : '') + '">' + (data.online ? 'آنلاین' : 'آفلاین') + '</div></div>';
                list.appendChild(div);
            }
            if (!hasUsers) list.innerHTML = '<div style="padding:10px 16px;color:#8e8e8e;">هیچ کاربر دیگری آنلاین نیست</div>';
        });

        socket.on('receive-message', (data) => {
            const messagesDiv = document.getElementById('chatMessages');
            const empty = messagesDiv.querySelector('.chat-empty');
            if (empty) empty.remove();
            const div = document.createElement('div');
            div.className = 'chat-message' + (data.userId === USER_ID ? ' own' : '');
            div.innerHTML = '<div class="msg-user">' + (data.userId === USER_ID ? 'شما' : data.userName) + '</div><div class="msg-text">' + data.text + '</div><div class="msg-time">' + new Date(data.timestamp).toLocaleTimeString('fa-IR') + '</div>';
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        });

        socket.on('history-messages', (messages) => {
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.innerHTML = '';
            messages.forEach(msg => {
                const div = document.createElement('div');
                div.className = 'chat-message' + (msg.userId === USER_ID ? ' own' : '');
                div.innerHTML = '<div class="msg-user">' + (msg.userId === USER_ID ? 'شما' : msg.userName) + '</div><div class="msg-text">' + msg.text + '</div><div class="msg-time">' + new Date(msg.timestamp).toLocaleTimeString('fa-IR') + '</div>';
                messagesDiv.appendChild(div);
            });
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        });

        document.getElementById('chatOpenBtn').addEventListener('click', () => {
            document.getElementById('chatInterface').classList.add('active');
        });

        document.getElementById('closeChatBtn').addEventListener('click', () => {
            document.getElementById('chatInterface').classList.remove('active');
            if (currentChatRoom) {
                socket.emit('leave-room', { roomId: currentChatRoom });
                currentChatRoom = null;
            }
        });

        document.getElementById('chatSendBtn').addEventListener('click', () => {
            const input = document.getElementById('chatInput');
            const text = input.value.trim();
            if (!text || !currentChatRoom) return;
            socket.emit('send-message', { roomId: currentChatRoom, userId: USER_ID, userName: USER_NAME, text });
            input.value = '';
        });

        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') document.getElementById('chatSendBtn').click();
        });

        function createPostElement(post) {
            const div = document.createElement('div');
            div.className = 'gallery-item';
            div.setAttribute('data-id', post.id);
            div.onclick = () => alert('📸 ' + (post.caption || 'بدون توضیحات') + '\\n❤️ ' + (post.likes || 0) + ' لایک\\n💬 ' + (post.comments || []).length + ' کامنت');
            const isLiked = localStorage.getItem('liked_' + post.id) === 'true';
            div.innerHTML = '<div class="image-container"><img src="' + (post.image || 'https://via.placeholder.com/400') + '" alt="post" loading="lazy"></div><div class="explore-post-actions"><button class="action-btn like-btn ' + (isLiked ? 'liked' : '') + '" data-id="' + post.id + '" onclick="event.stopPropagation(); handleLike(\\'' + post.id + '\\')"><i class="' + (isLiked ? 'fas' : 'far') + ' fa-heart"></i><span class="count">' + (post.likes || 0) + '</span></button><button class="action-btn comment-btn" data-id="' + post.id + '" onclick="event.stopPropagation(); openComments(\\'' + post.id + '\\')"><i class="far fa-comment"></i><span class="count">' + (post.comments || []).length + '</span></button><button class="action-btn share-btn" data-id="' + post.id + '" onclick="event.stopPropagation(); sharePost(\\'' + post.id + '\\')"><i class="fas fa-share-alt"></i><span class="count">' + (post.shares || 0) + '</span></button></div>';
            return div;
        }

        window.handleLike = async function(postId) {
            const result = await likePost(postId);
            document.querySelectorAll('.like-btn[data-id="' + postId + '"]').forEach(btn => {
                btn.querySelector('i').className = 'fas fa-heart';
                btn.classList.add('liked');
                btn.querySelector('.count').textContent = result.likes || 0;
                localStorage.setItem('liked_' + postId, 'true');
            });
        };

        window.openComments = async function(postId) {
            currentPostId = postId;
            const posts = await getPosts();
            const post = posts.find(p => p.id === postId);
            const list = document.getElementById('commentList');
            list.innerHTML = '';
            if (!post || !post.comments || post.comments.length === 0) {
                list.innerHTML = '<div style="text-align:center;color:#8e8e8e;padding:20px;">هنوز کامنتی وجود ندارد</div>';
            } else {
                post.comments.forEach(c => {
                    const div = document.createElement('div');
                    div.className = 'comment-item';
                    div.innerHTML = '<div class="comment-avatar"><img src="https://i.pravatar.cc/150?img=' + Math.floor(Math.random() * 70) + '" alt="avatar"></div><div class="comment-content"><div class="comment-username">' + (c.userName || c.userId || 'کاربر') + '</div><div class="comment-text">' + c.text + '</div><div class="comment-time">' + (c.time || 'چند لحظه پیش') + '</div></div>';
                    list.appendChild(div);
                });
            }
            document.getElementById('commentModal').classList.add('active');
            document.getElementById('modalCommentInput').focus();
        };

        window.sharePost = function(postId) {
            document.getElementById('shareModal').dataset.postId = postId;
            document.getElementById('shareModal').classList.add('active');
        };

        document.getElementById('modalSendComment').addEventListener('click', async function() {
            const input = document.getElementById('modalCommentInput');
            const text = input.value.trim();
            if (text && currentPostId) {
                await addComment(currentPostId, text);
                input.value = '';
                document.getElementById('commentList').innerHTML = '<div style="text-align:center;color:#2ecc71;padding:20px;">✅ کامنت با موفقیت ثبت شد!</div>';
                setTimeout(() => openComments(currentPostId), 500);
            }
        });

        document.getElementById('modalCommentInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') document.getElementById('modalSendComment').click();
        });

        document.getElementById('closeModal').addEventListener('click', function() {
            document.getElementById('commentModal').classList.remove('active');
            currentPostId = null;
        });

        document.getElementById('commentModal').addEventListener('click', function(e) {
            if (e.target === this) { this.classList.remove('active'); currentPostId = null; }
        });

        document.getElementById('closeShareModal').addEventListener('click', function() {
            document.getElementById('shareModal').classList.remove('active');
        });

        document.getElementById('shareModal').addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('active');
        });

        document.querySelectorAll('.share-option').forEach(option => {
            option.addEventListener('click', function() {
                const type = this.getAttribute('data-share');
                const postId = document.getElementById('shareModal').dataset.postId;
                const link = window.location.href + '?post=' + postId;
                if (type === 'telegram') {
                    window.open('https://t.me/share/url?url=' + encodeURIComponent(link) + '&text=' + encodeURIComponent('به این پست نگاه کن!'), '_blank');
                } else if (type === 'whatsapp') {
                    window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent('به این پست نگاه کن! ' + link), '_blank');
                } else if (type === 'instagram' || type === 'copy') {
                    navigator.clipboard.writeText(link).then(() => alert('✅ لینک کپی شد!'));
                } else if (type === 'site') {
                    alert('✅ پست برای کاربران سایت ارسال شد!');
                }
                document.getElementById('shareModal').classList.remove('active');
            });
        });

        document.getElementById('profileBtn').addEventListener('click', function() {
            document.getElementById('profilePage').classList.add('active');
            (async () => {
                const posts = await getPosts();
                const gallery = document.getElementById('profileGallery');
                gallery.innerHTML = '';
                const userPosts = posts.filter(p => p.userId === USER_ID);
                if (userPosts.length === 0) {
                    gallery.innerHTML = '<p style="grid-column:span 3;text-align:center;color:#8e8e8e;padding:20px;">هیچ پستی ندارید</p>';
                } else {
                    userPosts.forEach(post => {
                        const div = document.createElement('div');
                        div.className = 'profile-post';
                        div.onclick = () => alert('📸 ' + (post.caption || 'بدون توضیحات'));
                        div.innerHTML = '<div class="image-container"><img src="' + (post.image || 'https://via.placeholder.com/400') + '" alt="post" loading="lazy"><div class="profile-post-overlay"><span><i class="fas fa-heart"></i> ' + (post.likes || 0) + '</span><span><i class="fas fa-comment"></i> ' + (post.comments || []).length + '</span></div></div>';
                        gallery.appendChild(div);
                    });
                }
                document.getElementById('postCount').textContent = userPosts.length;
            })();
        });

        document.getElementById('closeProfile').addEventListener('click', function() {
            document.getElementById('profilePage').classList.remove('active');
        });

        document.getElementById('profilePage').addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('active');
        });

        document.getElementById('profileFollowBtn').addEventListener('click', function() {
            if (isFollowing) {
                this.classList.remove('following');
                this.textContent = 'دنبال کردن';
                isFollowing = false;
            } else {
                this.classList.add('following');
                this.textContent = 'دنبال شده';
                isFollowing = true;
            }
        });

        document.getElementById('saveBio').addEventListener('click', function() {
            const bio = document.getElementById('bioInput').value.trim();
            if (bio) {
                document.getElementById('bioDisplay').textContent = bio;
                document.getElementById('bioInput').value = '';
                alert('✅ بیوگرافی با موفقیت ذخیره شد!');
            } else {
                alert('❌ لطفا بیوگرافی خود را وارد کنید.');
            }
        });

        document.getElementById('uploadBtn').addEventListener('click', function() {
            document.getElementById('uploadPage').classList.add('active');
        });

        document.getElementById('closeUpload').addEventListener('click', function() {
            document.getElementById('uploadPage').classList.remove('active');
            resetUpload();
        });

        document.getElementById('uploadPage').addEventListener('click', function(e) {
            if (e.target === this) { this.classList.remove('active'); resetUpload(); }
        });

        document.getElementById('uploadSelectBtn').addEventListener('click', function() {
            document.getElementById('fileInput').click();
        });

        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const previewImg = document.getElementById('previewImage');
                    const previewVideo = document.getElementById('previewVideo');
                    if (file.type.startsWith('image/')) {
                        previewImg.src = e.target.result;
                        previewImg.style.display = 'block';
                        previewVideo.style.display = 'none';
                    } else if (file.type.startsWith('video/')) {
                        previewVideo.src = e.target.result;
                        previewVideo.style.display = 'block';
                        previewImg.style.display = 'none';
                    }
                    document.getElementById('uploadPreview').classList.add('active');
                    document.getElementById('uploadCaption').classList.add('active');
                    document.getElementById('uploadSubmit').classList.add('active');
                };
                reader.readAsDataURL(file);
            }
        });

        document.getElementById('uploadSubmit').addEventListener('click', async function() {
            const file = document.getElementById('fileInput').files[0];
            const caption = document.getElementById('captionInput').value.trim();
            if (!file) { alert('❌ لطفا یک فایل انتخاب کنید.'); return; }
            this.textContent = '⏳ در حال آپلود...';
            this.disabled = true;
            const result = await createPost(file, caption);
            if (result && result.id) {
                alert('✅ پست با موفقیت آپلود شد!');
                resetUpload();
                document.getElementById('uploadPage').classList.remove('active');
                location.reload();
            } else {
                alert('❌ خطا در آپلود پست!');
            }
            this.textContent = 'ارسال پست';
            this.disabled = false;
        });

        function resetUpload() {
            document.getElementById('fileInput').value = '';
            document.getElementById('uploadPreview').classList.remove('active');
            document.getElementById('uploadCaption').classList.remove('active');
            document.getElementById('uploadSubmit').classList.remove('active');
            document.getElementById('previewImage').style.display = 'none';
            document.getElementById('previewVideo').style.display = 'none';
            document.getElementById('captionInput').value = '';
        }

        document.getElementById('menuIcon').addEventListener('click', function() {
            document.getElementById('sideMenu').classList.add('active');
            document.getElementById('menuOverlay').classList.add('active');
        });

        document.getElementById('closeMenu').addEventListener('click', function() {
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
        });

        document.getElementById('menuOverlay').addEventListener('click', function() {
            document.getElementById('sideMenu').classList.remove('active');
            this.classList.remove('active');
        });

        document.getElementById('menuTheme').addEventListener('click', function() {
            isDarkTheme = !isDarkTheme;
            document.body.classList.toggle('dark-theme', isDarkTheme);
            localStorage.setItem('theme', isDarkTheme ? 'dark' : 'light');
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
            alert('✅ تم با موفقیت تغییر کرد!');
        });

        document.getElementById('menuActivity').addEventListener('click', function() {
            alert('📊 فعالیت من: فعالیت‌های اخیر شما نمایش داده شد!');
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
        });

        document.getElementById('menuStats').addEventListener('click', function() {
            alert('📈 اطلاعات آماری: آمار بازدید و تعاملات شما نمایش داده شد!');
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
        });

        document.getElementById('menuLanguage').addEventListener('click', function() {
            alert('🌍 تغیر زبان: زبان سایت با موفقیت تغییر کرد!');
            document.getElementById('sideMenu').classList.remove('active');
            document.getElementById('menuOverlay').classList.remove('active');
        });

        let exploreMode = true, reelsMode = false;
        document.getElementById('exploreBtn').addEventListener('click', function() {
            const gallery = document.getElementById('gallery');
            const stories = document.getElementById('storiesSection');
            if (exploreMode) {
                exploreMode = false; reelsMode = false;
                gallery.style.gridTemplateColumns = 'repeat(2, 1fr)';
                stories.style.display = 'block';
                this.classList.remove('active');
                document.getElementById('reelsBtn').classList.remove('active');
            } else {
                exploreMode = true; reelsMode = false;
                gallery.style.gridTemplateColumns = 'repeat(3, 1fr)';
                stories.style.display = 'none';
                this.classList.add('active');
                document.getElementById('reelsBtn').classList.remove('active');
            }
        });

        document.getElementById('reelsBtn').addEventListener('click', function() {
            const gallery = document.getElementById('gallery');
            const stories = document.getElementById('storiesSection');
            if (reelsMode) {
                reelsMode = false; exploreMode = false;
                gallery.style.gridTemplateColumns = 'repeat(2, 1fr)';
                stories.style.display = 'block';
                this.classList.remove('active');
                document.getElementById('exploreBtn').classList.remove('active');
            } else {
                reelsMode = true; exploreMode = false;
                gallery.style.gridTemplateColumns = '1fr';
                stories.style.display = 'none';
                this.classList.add('active');
                document.getElementById('exploreBtn').classList.remove('active');
            }
        });

        document.getElementById('searchInput').addEventListener('input', async function() {
            const query = this.value.trim().toLowerCase();
            const gallery = document.getElementById('gallery');
            const posts = await getPosts();
            gallery.innerHTML = '';
            const filtered = posts.filter(p => (p.caption || '').toLowerCase().includes(query));
            if (filtered.length === 0) {
                gallery.innerHTML = '<div style="grid-column:span 3;text-align:center;color:#8e8e8e;padding:40px;">🔍 هیچ نتیجه‌ای یافت نشد</div>';
                return;
            }
            filtered.forEach(post => gallery.appendChild(createPostElement(post)));
        });

        document.getElementById('statFollowers').addEventListener('click', function() {
            const modal = document.getElementById('followModal');
            document.getElementById('followModalTitle').textContent = 'دنبال‌کنندگان';
            document.getElementById('followModalBody').innerHTML = '<div style="text-align:center;color:#8e8e8e;padding:20px;"><i class="fas fa-users" style="font-size:40px;display:block;margin-bottom:15px;"></i>هنوز کسی شما را دنبال نکرده است</div>';
            modal.classList.add('active');
        });

        document.getElementById('statFollowing').addEventListener('click', function() {
            const modal = document.getElementById('followModal');
            document.getElementById('followModalTitle').textContent = 'دنبال‌شونده‌ها';
            document.getElementById('followModalBody').innerHTML = '<div style="text-align:center;color:#8e8e8e;padding:20px;"><i class="fas fa-user-plus" style="font-size:40px;display:block;margin-bottom:15px;"></i>هنوز کسی را دنبال نکرده‌اید</div>';
            modal.classList.add('active');
        });

        document.getElementById('closeFollowModal').addEventListener('click', function() {
            document.getElementById('followModal').classList.remove('active');
        });

        document.getElementById('followModal').addEventListener('click', function(e) {
            if (e.target === this) this.classList.remove('active');
        });

        document.addEventListener('DOMContentLoaded', async function() {
            document.getElementById('gallery').style.gridTemplateColumns = 'repeat(3, 1fr)';
            document.getElementById('storiesSection').style.display = 'none';
            document.getElementById('exploreBtn').classList.add('active');

            const posts = await getPosts();
            const gallery = document.getElementById('gallery');
            const loading = document.getElementById('loadingIndicator');
            const noPosts = document.getElementById('noPostsMessage');
            loading.style.display = 'block';
            gallery.innerHTML = '';
            noPosts.style.display = 'none';

            if (posts.length === 0) {
                noPosts.style.display = 'block';
            } else {
                posts.forEach(post => gallery.appendChild(createPostElement(post)));
            }
            loading.style.display = 'none';

            const storiesContainer = document.getElementById('storiesContainer');
            for (let i = 1; i <= 7; i++) {
                const div = document.createElement('div');
                div.className = 'story-item';
                div.innerHTML = '<div class="story-avatar"><img src="https://i.pravatar.cc/150?img=' + i + '" alt="user' + i + '"></div><span class="story-username">user' + i + '</span>';
                div.onclick = () => alert('استوری user' + i + ' باز شد!');
                storiesContainer.appendChild(div);
            }

            console.log('✅ App started! User:', USER_NAME);
        });
    </script>
</body>
</html>
    `);
});

// ============================================
// 🚀 اجرا
// ============================================
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log('✅ سرور اجرا شد: http://localhost:' + PORT);
    console.log('📡 WebSocket فعال است');
});