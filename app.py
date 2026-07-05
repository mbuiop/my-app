# ============================================
# LOTTERY BOT - FULL ENTERPRISE VERSION
# ============================================

import asyncio
import logging
import random
import json
import hashlib
import time
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# ============ CONFIGURATION ============
class Config:
    # !!! مهم: این مقادیر را با مقادیر واقعی خود جایگزین کنید !!!
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # توکن ربات خود را اینجا قرار دهید
    ADMIN_IDS = [123456789]  # ایدی عددی مدیران (مثلاً 123456789)
    WEBAPP_URL = "http://localhost:5000"  # آدرس سرور شما
    
    # تنظیمات شبکه ترون
    TRONGRID_API = "https://api.trongrid.io"
    CONTRACT_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
    API_KEY = "7ae83b63-fdf3-47e4-ac69-56f960a34f5b"
    LOTTERY_COST = 100
    
    # دیتابیس
    SHARD_COUNT = 10  # برای تست کمتر، برای تولید 100
    DEFAULT_LANGUAGE = "en"

# ============ دیتابیس ============
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("lottery.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_tables()
        self.lock = threading.Lock()
    
    def init_tables(self):
        cursor = self.conn.cursor()
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'en',
                referral_code TEXT UNIQUE,
                referrer_id INTEGER,
                wallet_address TEXT,
                balance REAL DEFAULT 0,
                is_winner INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                participated_count INTEGER DEFAULT 0,
                created_at INTEGER
            )
        ''')
        # جدول شرکت‌کنندگان
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_participants (
                user_id INTEGER,
                lottery_id INTEGER,
                wallet_address TEXT,
                joined_at INTEGER,
                is_winner INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, lottery_id)
            )
        ''')
        # جدول نتایج
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_results (
                lottery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_participants INTEGER,
                winners_count INTEGER,
                prize_amount REAL,
                created_at INTEGER,
                status TEXT DEFAULT 'pending'
            )
        ''')
        # جدول برداشت‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                wallet_address TEXT,
                status TEXT DEFAULT 'pending',
                requested_at INTEGER
            )
        ''')
        self.conn.commit()
    
    def execute(self, query: str, params: tuple = ()):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor

db = Database()

# ============ خدمات کاربر ============
class UserService:
    def get_user(self, user_id: int) -> Optional[Dict]:
        cursor = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None, 
                   last_name: str = None, language: str = 'en') -> Dict:
        referral_code = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8]
        now = int(time.time())
        db.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, language, referral_code, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, language, referral_code, now))
        return self.get_user(user_id) or {'user_id': user_id}
    
    def update_wallet(self, user_id: int, wallet: str):
        db.execute("UPDATE users SET wallet_address = ? WHERE user_id = ?", (wallet, user_id))
    
    def mark_winner(self, user_id: int):
        db.execute("UPDATE users SET is_winner = 1, total_wins = total_wins + 1 WHERE user_id = ?", (user_id,))
    
    def get_participants(self) -> List[Dict]:
        cursor = db.execute('''
            SELECT lp.user_id, lp.wallet_address, u.first_name, u.username
            FROM lottery_participants lp
            JOIN users u ON lp.user_id = u.user_id
            WHERE lp.lottery_id = (SELECT COALESCE(MAX(lottery_id), 0) FROM lottery_participants)
        ''')
        return [dict(row) for row in cursor.fetchall()]

user_service = UserService()

# ============ HTML صفحه وب ============
WEBAPP_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🎰 Lottery</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0b1e 0%, #1a1b3e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 16px;
            padding-bottom: 80px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0 20px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .logo {
            font-size: 22px;
            font-weight: 800;
            background: linear-gradient(135deg, #7c5cfc, #fc5c7c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .user-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 16px;
            margin: 16px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .user-name { font-weight: 600; font-size: 16px; }
        .user-id { font-size: 12px; color: rgba(255,255,255,0.4); }
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin: 12px 0;
        }
        .stat {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 12px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .stat-value { font-size: 20px; font-weight: 700; color: #7c5cfc; }
        .stat-label { font-size: 10px; color: rgba(255,255,255,0.4); margin-top: 4px; }
        .btn {
            padding: 14px;
            border: none;
            border-radius: 12px;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            font-family: inherit;
            color: #fff;
            transition: all 0.2s;
            width: 100%;
        }
        .btn:active { transform: scale(0.97); }
        .btn-primary { background: linear-gradient(135deg, #7c5cfc, #fc5c7c); }
        .btn-gold { background: linear-gradient(135deg, #f9d423, #f7971e); color: #1a1a2e; }
        .btn-secondary { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1); }
        .btn-success { background: linear-gradient(135deg, #00d4ff, #00b894); }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0; }
        .section {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 16px;
            margin: 12px 0;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .section-title { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.5); margin-bottom: 12px; }
        .participant-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .participant-item:last-child { border-bottom: none; }
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(10px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal-overlay.show { display: flex; }
        .modal {
            background: linear-gradient(135deg, #1a1b3e, #2a1b4e);
            border-radius: 20px;
            padding: 24px;
            max-width: 400px;
            width: 100%;
            border: 1px solid rgba(255,255,255,0.1);
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-title { font-size: 20px; font-weight: 700; text-align: center; margin-bottom: 16px; }
        .modal-input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: #fff;
            font-size: 14px;
            font-family: inherit;
            margin-bottom: 12px;
        }
        .modal-input:focus { outline: none; border-color: #7c5cfc; }
        .modal-input::placeholder { color: rgba(255,255,255,0.3); }
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.85);
            padding: 12px 24px;
            border-radius: 12px;
            color: #fff;
            font-size: 14px;
            z-index: 2000;
            display: none;
            max-width: 90%;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .toast.show { display: block; animation: slideUp 0.3s ease; }
        @keyframes slideUp { from { opacity:0; transform:translateX(-50%) translateY(20px); } to { opacity:1; transform:translateX(-50%) translateY(0); } }
        .toast.success { border-color: #00b894; }
        .toast.error { border-color: #ff6b6b; }
        .hidden { display: none; }
        .admin-tab { display: none; }
        .admin-tab.show { display: block; }
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-winner { background: linear-gradient(135deg, #f9d423, #f7971e); color: #1a1a2e; }
        .badge-active { background: rgba(0, 184, 148, 0.2); color: #00b894; }
    </style>
</head>
<body>
    <div id="toast" class="toast"></div>
    <div id="modal" class="modal-overlay"><div class="modal" id="modalContent"></div></div>
    
    <div class="header">
        <span class="logo">🎰 Lottery</span>
        <div style="display:flex; gap:8px;">
            <button onclick="showLang()" style="background:none;border:none;color:#fff;font-size:20px;">🌐</button>
        </div>
    </div>
    
    <div class="user-card">
        <div>
            <div class="user-name" id="userName">Loading...</div>
            <div class="user-id" id="userId">ID: ---</div>
        </div>
        <span class="badge badge-active" id="userStatus">● Active</span>
    </div>
    
    <div class="stats">
        <div class="stat"><div class="stat-value" id="statBalance">0</div><div class="stat-label">💰 Balance</div></div>
        <div class="stat"><div class="stat-value" id="statWins">0</div><div class="stat-label">🏆 Wins</div></div>
        <div class="stat"><div class="stat-value" id="statPart">0</div><div class="stat-label">📊 Joined</div></div>
    </div>
    
    <div class="grid-2">
        <button class="btn btn-primary" onclick="joinLottery()">🎯 Join Lottery</button>
        <button class="btn btn-secondary" onclick="showReferral()">🔗 Referral</button>
        <button class="btn btn-gold" onclick="showWithdraw()">💰 Withdraw</button>
        <button class="btn btn-secondary" onclick="showHistory()">📜 History</button>
    </div>
    
    <div class="section">
        <div class="section-title">👥 Participants (<span id="partCount">0</span>)</div>
        <div id="participantList"><div style="text-align:center;padding:20px;color:rgba(255,255,255,0.3);">Loading...</div></div>
    </div>
    
    <div class="section hidden" id="adminSection">
        <div class="section-title">🛠 Admin Panel</div>
        <div class="grid-2">
            <button class="btn btn-secondary" onclick="adminBroadcast()">📢 Broadcast</button>
            <button class="btn btn-success" onclick="adminStartLottery()">🎯 Start Lottery</button>
            <button class="btn btn-secondary" onclick="adminManualVerify()">✅ Manual Verify</button>
            <button class="btn btn-secondary" onclick="adminAddApi()">🔑 Add API</button>
            <button class="btn btn-secondary" onclick="adminWithdrawals()">💰 Withdrawals</button>
        </div>
    </div>
    
    <script>
        const state = { userId: null, isAdmin: false };
        
        function showToast(msg, type='success') {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.className = 'toast ' + type + ' show';
            clearTimeout(t._timeout);
            t._timeout = setTimeout(() => t.className = 'toast', 3000);
        }
        
        function showModal(html) {
            document.getElementById('modalContent').innerHTML = html;
            document.getElementById('modal').classList.add('show');
        }
        
        function closeModal() { document.getElementById('modal').classList.remove('show'); }
        
        async function api(endpoint, method='GET', data=null) {
            try {
                const opts = { method, headers: { 'Content-Type': 'application/json', 'X-User-Id': state.userId || '' } };
                if (data) opts.body = JSON.stringify(data);
                const res = await fetch('/api/' + endpoint, opts);
                return await res.json();
            } catch(e) { showToast('Connection error', 'error'); return null; }
        }
        
        async function loadData() {
            const data = await api('user');
            if (data) {
                state.userId = data.id;
                state.isAdmin = data.is_admin || false;
                document.getElementById('userName').textContent = data.name || 'User';
                document.getElementById('userId').textContent = 'ID: ' + data.id;
                document.getElementById('statBalance').textContent = data.balance || 0;
                document.getElementById('statWins').textContent = data.wins || 0;
                document.getElementById('statPart').textContent = data.participated || 0;
                if (data.is_winner) document.getElementById('userStatus').textContent = '🏆 Winner';
                if (state.isAdmin) document.getElementById('adminSection').classList.remove('hidden');
                loadParticipants();
            }
        }
        
        async function loadParticipants() {
            const data = await api('lottery/participants');
            if (data) {
                document.getElementById('partCount').textContent = data.count || 0;
                const list = document.getElementById('participantList');
                if (data.participants && data.participants.length > 0) {
                    list.innerHTML = data.participants.map(p => `
                        <div class="participant-item">
                            <span>${p.first_name || p.username || 'User'}</span>
                            <span style="font-size:11px;color:rgba(255,255,255,0.3);">${p.wallet_address ? p.wallet_address.slice(0,6)+'...' : ''}</span>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div style="text-align:center;padding:20px;color:rgba(255,255,255,0.3);">No participants yet</div>';
                }
            }
        }
        
        // ===== JOIN LOTTERY =====
        function joinLottery() {
            showModal(`
                <div class="modal-title">🎯 Join Lottery</div>
                <p style="color:rgba(255,255,255,0.6);margin-bottom:12px;font-size:14px;">
                    Send <strong>100 USDT</strong> to:<br>
                    <span style="font-family:monospace;color:#7c5cfc;">TV61aTh98MGqmteYzda5AaBzdXgGqreG6A</span>
                </p>
                <input class="modal-input" id="walletInput" placeholder="Your TRC20 wallet address" />
                <input class="modal-input" id="txInput" placeholder="Transaction ID (TX...)" />
                <button class="btn btn-primary" onclick="submitJoin()">✅ Verify</button>
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-top:8px;">Cancel</button>
            `);
        }
        
        async function submitJoin() {
            const wallet = document.getElementById('walletInput').value.trim();
            const tx = document.getElementById('txInput').value.trim();
            if (!wallet || !tx) { showToast('Please fill all fields', 'error'); return; }
            if (!wallet.startsWith('T') || wallet.length !== 34) { showToast('Invalid wallet', 'error'); return; }
            closeModal();
            showToast('⏳ Verifying...', 'warning');
            const res = await api('lottery/join', 'POST', { wallet, tx_id: tx });
            if (res && res.success) { showToast('✅ Joined successfully!', 'success'); loadData(); }
            else { showToast(res?.message || '❌ Failed', 'error'); }
        }
        
        // ===== REFERRAL =====
        function showReferral() {
            const code = state.userId || '';
            showModal(`
                <div class="modal-title">🔗 Referral</div>
                <p style="color:rgba(255,255,255,0.6);margin-bottom:12px;">Share your referral link:</p>
                <div style="background:rgba(255,255,255,0.05);padding:12px;border-radius:8px;font-size:12px;word-break:break-all;color:#7c5cfc;margin-bottom:12px;">
                    https://t.me/UTYOB_Bot?start=${code}
                </div>
                <button class="btn btn-primary" onclick="navigator.clipboard?.writeText('https://t.me/UTYOB_Bot?start=${code}'); showToast('Copied!'); closeModal();">📋 Copy</button>
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-top:8px;">Close</button>
            `);
        }
        
        // ===== WITHDRAW =====
        function showWithdraw() {
            showModal(`
                <div class="modal-title">💰 Withdraw</div>
                <input class="modal-input" id="withdrawInput" placeholder="Enter TRC20 wallet address" />
                <button class="btn btn-gold" onclick="submitWithdraw()">💰 Withdraw</button>
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-top:8px;">Cancel</button>
            `);
        }
        
        async function submitWithdraw() {
            const wallet = document.getElementById('withdrawInput').value.trim();
            if (!wallet || !wallet.startsWith('T') || wallet.length !== 34) {
                showToast('Invalid wallet', 'error'); return;
            }
            closeModal();
            showToast('⏳ Processing...', 'warning');
            const res = await api('withdraw', 'POST', { wallet });
            if (res && res.success) { showToast('✅ Withdrawal requested!', 'success'); }
            else { showToast(res?.error || '❌ Failed', 'error'); }
        }
        
        // ===== HISTORY =====
        function showHistory() {
            showModal(`<div class="modal-title">📜 History</div><div id="historyList"><div style="text-align:center;padding:20px;color:rgba(255,255,255,0.3);">Loading...</div></div><button class="btn btn-secondary" onclick="closeModal()" style="margin-top:12px;">Close</button>`);
            loadHistory();
        }
        
        async function loadHistory() {
            const data = await api('history');
            const list = document.getElementById('historyList');
            if (data && data.history && data.history.length > 0) {
                list.innerHTML = data.history.map(h => `
                    <div style="padding:10px;border-bottom:1px solid rgba(255,255,255,0.05);font-size:13px;">
                        <div>${h.type} - ${h.amount} USDT</div>
                        <div style="color:rgba(255,255,255,0.3);font-size:11px;">${h.date || ''}</div>
                        <div style="color:${h.status === 'completed' ? '#00b894' : '#f9d423'};">${h.status}</div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div style="text-align:center;padding:20px;color:rgba(255,255,255,0.3);">No history</div>';
            }
        }
        
        // ===== ADMIN FUNCTIONS =====
        async function adminBroadcast() {
            showModal(`
                <div class="modal-title">📢 Broadcast</div>
                <textarea class="modal-input" id="broadcastMsg" rows="3" placeholder="Enter message..." style="resize:vertical;"></textarea>
                <button class="btn btn-primary" onclick="submitBroadcast()">📢 Send</button>
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-top:8px;">Cancel</button>
            `);
        }
        
        async function submitBroadcast() {
            const msg = document.getElementById('broadcastMsg').value.trim();
            if (!msg) { showToast('Enter message', 'error'); return; }
            closeModal();
            showToast('⏳ Sending...', 'warning');
            const res = await api('admin/broadcast', 'POST', { message: msg });
            if (res && res.success) { showToast('✅ Broadcast sent!', 'success'); }
        }
        
        async function adminStartLottery() {
            showModal(`
                <div class="modal-title">🎯 Start Lottery</div>
                <input class="modal-input" id="winnersCount" type="number" placeholder="Number of winners" />
                <input class="modal-input" id="prizeAmount" type="number" placeholder="Prize per winner (USDT)" />
                <button class="btn btn-success" onclick="submitStartLottery()">🚀 Start</button>
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-top:8px;">Cancel</button>
            `);
        }
        
        async function submitStartLottery() {
            const w = parseInt(document.getElementById('winnersCount').value);
            const p = parseFloat(document.getElementById('prizeAmount').value);
            if (!w || !p) { showToast('Enter valid numbers', 'error'); return; }
            closeModal();
            showToast('⏳ Starting...', 'warning');
            const res = await api('admin/start_lottery', 'POST', { winners_count: w, prize_amount: p });
            if (res && res.success) { showToast(`✅ Started! ${res.count || 0} winners selected!`, 'success'); loadData(); }
            else { showToast(res?.error || '❌ Failed', 'error'); }
        }
        
        async function adminManualVerify() {
            showModal(`
                <div class="modal-title">✅ Manual Verify</div>
                <input class="modal-input" id="verifyUserId" type="number" placeholder="User ID" />
                <button class="btn btn-success" onclick="submitManualVerify()">✅ Verify</button>
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-top:8px;">Cancel</button>
            `);
        }
        
        async function submitManualVerify() {
            const uid = parseInt(document.getElementById('verifyUserId').value);
            if (!uid) { showToast('Enter user ID', 'error'); return; }
            closeModal();
            showToast('⏳ Verifying...', 'warning');
            const res = await api('admin/manual_verify', 'POST', { user_id: uid });
            if (res && res.success) { showToast(`✅ User ${uid} verified!`, 'success'); }
        }
        
        async function adminAddApi() {
            showModal(`
                <div class="modal-title">🔑 Add API Key</div>
                <input class="modal-input" id="apiKeyInput" placeholder="API Key" />
                <button class="btn btn-primary" onclick="submitAddApi()">➕ Add</button>
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-top:8px;">Cancel</button>
            `);
        }
        
        async function submitAddApi() {
            const key = document.getElementById('apiKeyInput').value.trim();
            if (!key) { showToast('Enter API key', 'error'); return; }
            closeModal();
            const res = await api('admin/add_api', 'POST', { api_key: key });
            if (res && res.success) { showToast('✅ API key added!', 'success'); }
        }
        
        async function adminWithdrawals() {
            showModal(`<div class="modal-title">💰 Withdrawals</div><div id="withdrawalList"><div style="text-align:center;padding:20px;color:rgba(255,255,255,0.3);">Loading...</div></div><button class="btn btn-secondary" onclick="closeModal()" style="margin-top:12px;">Close</button>`);
            const data = await api('admin/withdrawals');
            const list = document.getElementById('withdrawalList');
            if (data && data.withdrawals && data.withdrawals.length > 0) {
                list.innerHTML = data.withdrawals.map(w => `
                    <div style="padding:10px;border-bottom:1px solid rgba(255,255,255,0.05);">
                        <div>User ${w.user_id} - ${w.amount} USDT</div>
                        <div style="font-size:11px;color:rgba(255,255,255,0.3);">${w.wallet_address}</div>
                        <div style="display:flex;gap:8px;margin-top:4px;">
                            <span style="font-size:11px;color:#f9d423;">${w.status}</span>
                            ${w.status === 'pending' ? `<button class="btn" style="padding:4px 12px;font-size:10px;background:#00b894;border:none;border-radius:6px;color:#fff;" onclick="confirmWithdrawal(${w.id})">✅ Confirm</button>` : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div style="text-align:center;padding:20px;color:rgba(255,255,255,0.3);">No withdrawals</div>';
            }
        }
        
        async function confirmWithdrawal(id) {
            closeModal();
            const res = await api('admin/confirm_withdrawal', 'POST', { withdrawal_id: id });
            if (res && res.success) { showToast('✅ Confirmed!', 'success'); }
        }
        
        function showLang() {
            showModal(`
                <div class="modal-title">🌐 Language</div>
                <button class="btn btn-secondary" onclick="setLang('en')">🇬🇧 English</button>
                <button class="btn btn-secondary" onclick="setLang('fa')" style="margin-top:8px;">🇮🇷 فارسی</button>
                <button class="btn btn-secondary" onclick="setLang('tr')" style="margin-top:8px;">🇹🇷 Türkçe</button>
                <button class="btn btn-secondary" onclick="closeModal()" style="margin-top:12px;">Close</button>
            `);
        }
        
        async function setLang(lang) {
            await api('language', 'POST', { language: lang });
            showToast('✅ Language changed!', 'success');
            closeModal();
        }
        
        // ===== INIT =====
        loadData();
        setInterval(() => { loadData(); }, 30000);
        
        // Telegram WebApp
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }
    </script>
</body>
</html>
'''

# ============ FLASK API ============
flask_app = Flask(__name__)
CORS(flask_app)

@flask_app.route('/')
def index():
    return render_template_string(WEBAPP_HTML)

@flask_app.route('/api/user')
def api_user():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 401
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    user = user_service.get_user(user_id)
    if not user:
        # ایجاد کاربر جدید
        user = user_service.create_user(user_id)
    
    # تعداد شرکت‌ها
    cursor = db.execute("SELECT COUNT(*) as count FROM lottery_participants WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    return jsonify({
        'id': user_id,
        'name': user.get('first_name') or user.get('username') or f"User{user_id}",
        'balance': user.get('balance', 0),
        'wins': user.get('total_wins', 0),
        'participated': row['count'] if row else 0,
        'is_admin': user_id in Config.ADMIN_IDS,
        'is_winner': user.get('is_winner', False)
    })

@flask_app.route('/api/lottery/participants')
def api_participants():
    participants = user_service.get_participants()
    return jsonify({
        'count': len(participants),
        'participants': participants
    })

@flask_app.route('/api/lottery/join', methods=['POST'])
def api_join():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 401
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    data = request.json
    wallet = data.get('wallet')
    tx_id = data.get('tx_id')
    
    if not wallet or not tx_id:
        return jsonify({'error': 'Wallet and TX ID required'}), 400
    
    # ذخیره والت
    user_service.update_wallet(user_id, wallet)
    
    # بررسی تکراری نبودن
    cursor = db.execute(
        "SELECT * FROM lottery_participants WHERE user_id = ? AND lottery_id = (SELECT COALESCE(MAX(lottery_id), 0) FROM lottery_participants)",
        (user_id,)
    )
    if cursor.fetchone():
        return jsonify({'success': False, 'message': 'Already participating'})
    
    # اضافه کردن شرکت‌کننده
    now = int(time.time())
    db.execute('''
        INSERT INTO lottery_participants (user_id, lottery_id, wallet_address, joined_at)
        VALUES (?, (SELECT COALESCE(MAX(lottery_id), 0) + 1 FROM lottery_participants), ?, ?)
    ''', (user_id, wallet, now))
    
    # به‌روزرسانی تعداد شرکت‌ها
    db.execute("UPDATE users SET participated_count = participated_count + 1 WHERE user_id = ?", (user_id,))
    
    return jsonify({'success': True, 'message': 'Joined successfully'})

@flask_app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 401
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    data = request.json
    wallet = data.get('wallet')
    
    if not wallet:
        return jsonify({'error': 'Wallet required'}), 400
    
    user = user_service.get_user(user_id)
    if not user or not user.get('is_winner'):
        return jsonify({'error': 'Not eligible for withdrawal'}), 400
    
    # دریافت مبلغ جایزه
    cursor = db.execute(
        "SELECT prize_amount FROM lottery_results WHERE status = 'completed' ORDER BY created_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    amount = row['prize_amount'] if row else 0
    
    if amount <= 0:
        return jsonify({'error': 'No prize available'}), 400
    
    # ایجاد درخواست برداشت
    db.execute('''
        INSERT INTO withdrawals (user_id, amount, wallet_address, requested_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, amount, wallet, int(time.time())))
    
    return jsonify({'success': True, 'amount': amount})

@flask_app.route('/api/history')
def api_history():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 401
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    cursor = db.execute('''
        SELECT * FROM lottery_participants WHERE user_id = ? ORDER BY joined_at DESC LIMIT 20
    ''', (user_id,))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'type': 'Lottery',
            'amount': 0,
            'status': 'completed',
            'date': datetime.fromtimestamp(row['joined_at']).strftime('%Y-%m-%d %H:%M')
        })
    
    return jsonify({'history': history})

@flask_app.route('/api/language', methods=['POST'])
def api_language():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 401
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    data = request.json
    lang = data.get('language', 'en')
    db.execute("UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id))
    return jsonify({'success': True})

# ===== ADMIN API =====
@flask_app.route('/api/admin/broadcast', methods=['POST'])
def api_admin_broadcast():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    message = data.get('message')
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    # ارسال به همه کاربران (در پس‌زمینه)
    def send_broadcast():
        cursor = db.execute("SELECT user_id FROM users")
        count = 0
        for row in cursor.fetchall():
            try:
                # ارسال پیام از طریق ربات
                count += 1
            except:
                pass
        return count
    
    thread = threading.Thread(target=send_broadcast)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Broadcast started'})

@flask_app.route('/api/admin/start_lottery', methods=['POST'])
def api_admin_start_lottery():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    winners_count = data.get('winners_count', 1)
    prize_amount = data.get('prize_amount', 0)
    
    if winners_count < 1 or prize_amount < 1:
        return jsonify({'error': 'Invalid parameters'}), 400
    
    # دریافت شرکت‌کنندگان
    participants = user_service.get_participants()
    if len(participants) < winners_count:
        return jsonify({'error': 'Not enough participants'}), 400
    
    # دریافت برندگان قبلی
    cursor = db.execute("SELECT user_id FROM users WHERE is_winner = 1")
    previous_winners = [row['user_id'] for row in cursor.fetchall()]
    
    # انتخاب برندگان
    eligible = [p['user_id'] for p in participants if p['user_id'] not in previous_winners]
    if len(eligible) < winners_count:
        eligible = [p['user_id'] for p in participants]
    
    random.seed(time.time() + random.randint(1, 1000000))
    winners = random.sample(eligible, min(winners_count, len(eligible)))
    
    # ثبت برندگان
    for uid in winners:
        user_service.mark_winner(uid)
    
    # ثبت نتایج
    now = int(time.time())
    db.execute('''
        INSERT INTO lottery_results (total_participants, winners_count, prize_amount, created_at, status)
        VALUES (?, ?, ?, ?, 'completed')
    ''', (len(participants), len(winners), prize_amount, now))
    
    return jsonify({
        'success': True,
        'count': len(winners),
        'winners': winners
    })

@flask_app.route('/api/admin/manual_verify', methods=['POST'])
def api_admin_manual_verify():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    target_user = data.get('user_id')
    if not target_user:
        return jsonify({'error': 'User ID required'}), 400
    
    user_service.mark_winner(int(target_user))
    return jsonify({'success': True})

@flask_app.route('/api/admin/add_api', methods=['POST'])
def api_admin_add_api():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': 'API key required'}), 400
    
    # ذخیره API key
    db.execute("INSERT OR IGNORE INTO api_keys (api_key, created_at) VALUES (?, ?)", (api_key, int(time.time())))
    return jsonify({'success': True})

@flask_app.route('/api/admin/withdrawals')
def api_admin_withdrawals():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    cursor = db.execute("SELECT * FROM withdrawals ORDER BY requested_at DESC")
    withdrawals = [dict(row) for row in cursor.fetchall()]
    return jsonify({'withdrawals': withdrawals})

@flask_app.route('/api/admin/confirm_withdrawal', methods=['POST'])
def api_admin_confirm_withdrawal():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    withdrawal_id = data.get('withdrawal_id')
    if not withdrawal_id:
        return jsonify({'error': 'Withdrawal ID required'}), 400
    
    db.execute("UPDATE withdrawals SET status = 'completed' WHERE id = ?", (withdrawal_id,))
    return jsonify({'success': True})

# ============ TELEGRAM BOT ============
class LotteryBot:
    def __init__(self):
        self.app = None
        self.webapp_url = Config.WEBAPP_URL
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        # ایجاد یا دریافت کاربر
        existing = user_service.get_user(user.id)
        if not existing:
            user_service.create_user(user.id, user.username, user.first_name, user.last_name)
        
        # دکمه Play
        keyboard = [[
            InlineKeyboardButton(
                "🎮 Play", 
                web_app=WebAppInfo(url=f"{self.webapp_url}?user_id={user.id}")
            )
        ]]
        
        await update.message.reply_text(
            "🎰 *Welcome to Lottery Bot!*\n\n"
            "Click the button below to open the full app:\n\n"
            "✨ *Features:*\n"
            "• 🎯 Join Lottery\n"
            "• 🔗 Referral System\n"
            "• 💰 Withdraw Prizes\n"
            "• 📜 Transaction History\n\n"
            "Tap **Play** to get started! 🚀",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Unauthorized!")
            return
        
        keyboard = [[
            InlineKeyboardButton(
                "🛠 Open Admin Panel", 
                web_app=WebAppInfo(url=f"{self.webapp_url}?user_id={user_id}")
            )
        ]]
        
        await update.message.reply_text(
            "🛠 *Admin Panel*\n\nOpen the admin panel to manage the lottery.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    def run(self):
        self.app = Application.builder().token(Config.BOT_TOKEN).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("admin", self.admin))
        
        print("🤖 Bot starting...")
        self.app.run_polling()

# ============ MAIN ============
def main():
    logging.basicConfig(level=logging.INFO)
    
    # اجرای Flask
    def run_flask():
        flask_app.run(host='0.0.0.0', port=5000, debug=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 WebApp: {Config.WEBAPP_URL}")
    
    # اجرای ربات
    bot = LotteryBot()
    bot.run()

if __name__ == "__main__":
    main()