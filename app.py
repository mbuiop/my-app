# ============================================
# LOTTERY BOT WITH WEB APP INTERFACE
# VERSION: 4.0 ENTERPRISE
# FULL FEATURES IN SINGLE WEB PAGE
# ============================================

import asyncio
import logging
import random
import json
import hashlib
import hmac
import time
import sqlite3
import redis
import aiohttp
import base58
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from cachetools import TTLCache
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ============ CONFIGURATION ============
class Config:
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your token
    ADMIN_IDS = [123456789]  # Replace with your admin IDs
    WEBAPP_URL = "https://your-domain.com"  # Replace with your domain
    
    # TronGrid Configuration
    TRONGRID_API = "https://api.trongrid.io"
    CONTRACT_ADDRESS = "TV61aTh98MGqmteYzda5AaBzdXgGqreG6A"
    USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    API_KEY = "7ae83b63-fdf3-47e4-ac69-56f960a34f5b"
    
    # Database
    REDIS_URL = "redis://localhost:6379/0"
    SHARD_COUNT = 100
    
    # Performance
    MAX_WORKERS = 100
    CACHE_SIZE = 10000
    
    # Lottery Settings
    LOTTERY_COST = 100  # USDT
    
    # Language Settings
    DEFAULT_LANGUAGE = "en"
    SUPPORTED_LANGUAGES = ["en", "fa", "tr"]

# ============ HTML WEBAPP INTERFACE ============
WEBAPP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🎰 Lottery Bot</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0a0b1e 0%, #1a1b3e 50%, #2a1b4e 100%);
            min-height: 100vh;
            color: #ffffff;
            padding: 0;
            margin: 0;
            overflow-x: hidden;
            position: relative;
        }
        
        /* Animated Background */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 50%, rgba(120, 80, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 50%, rgba(255, 80, 150, 0.1) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }
        
        .container {
            max-width: 420px;
            margin: 0 auto;
            padding: 12px 16px 100px 16px;
            position: relative;
            z-index: 1;
        }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            margin-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .logo-icon {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #7c5cfc, #fc5c7c);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 15px rgba(124, 92, 252, 0.3);
        }
        
        .logo-text {
            font-weight: 700;
            font-size: 18px;
            background: linear-gradient(135deg, #7c5cfc, #fc5c7c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header-actions {
            display: flex;
            gap: 8px;
        }
        
        .btn-icon {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            color: white;
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s;
            backdrop-filter: blur(10px);
        }
        
        .btn-icon:active {
            transform: scale(0.95);
            background: rgba(255,255,255,0.1);
        }
        
        /* User Card */
        .user-card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 16px;
            border: 1px solid rgba(255,255,255,0.08);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .user-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .user-avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, #7c5cfc, #fc5c7c);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(124, 92, 252, 0.2);
        }
        
        .user-name {
            font-weight: 600;
            font-size: 15px;
            color: #fff;
        }
        
        .user-id {
            font-size: 12px;
            color: rgba(255,255,255,0.5);
            font-family: monospace;
        }
        
        .user-badge {
            background: rgba(124, 92, 252, 0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            color: #7c5cfc;
            border: 1px solid rgba(124, 92, 252, 0.2);
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 16px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(20px);
            border-radius: 12px;
            padding: 12px 8px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
        }
        
        .stat-value {
            font-size: 20px;
            font-weight: 700;
            background: linear-gradient(135deg, #7c5cfc, #fc5c7c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .stat-label {
            font-size: 10px;
            color: rgba(255,255,255,0.5);
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Main Actions */
        .main-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 16px;
        }
        
        .btn-main {
            padding: 14px;
            border: none;
            border-radius: 12px;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-family: inherit;
            color: white;
            text-decoration: none;
        }
        
        .btn-main:active {
            transform: scale(0.97);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #7c5cfc, #fc5c7c);
            box-shadow: 0 4px 20px rgba(124, 92, 252, 0.3);
        }
        
        .btn-primary:active {
            box-shadow: 0 2px 10px rgba(124, 92, 252, 0.2);
        }
        
        .btn-secondary {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #00d4ff, #00b894);
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            box-shadow: 0 4px 20px rgba(255, 107, 107, 0.2);
        }
        
        .btn-gold {
            background: linear-gradient(135deg, #f9d423, #f7971e);
            box-shadow: 0 4px 20px rgba(249, 212, 35, 0.2);
            color: #1a1a2e;
        }
        
        .btn-full {
            grid-column: 1 / -1;
        }
        
        /* Card Sections */
        .section {
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 16px 18px;
            margin-bottom: 12px;
            border: 1px solid rgba(255,255,255,0.05);
        }
        
        .section-title {
            font-size: 13px;
            font-weight: 600;
            color: rgba(255,255,255,0.6);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .section-title .icon {
            font-size: 16px;
        }
        
        /* Lottery Status */
        .lottery-status {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: rgba(124, 92, 252, 0.1);
            border-radius: 10px;
            border: 1px solid rgba(124, 92, 252, 0.2);
            margin-bottom: 12px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        
        .status-dot.active {
            background: #00b894;
            animation: pulse 1.5s infinite;
        }
        
        .status-dot.inactive {
            background: #ff6b6b;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
        }
        
        /* Participant List */
        .participant-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        
        .participant-item:last-child {
            border-bottom: none;
        }
        
        .participant-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: rgba(255,255,255,0.05);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
        }
        
        .participant-name {
            font-size: 13px;
            flex: 1;
        }
        
        .participant-wallet {
            font-size: 11px;
            font-family: monospace;
            color: rgba(255,255,255,0.4);
        }
        
        /* Winner Badge */
        .winner-badge {
            background: linear-gradient(135deg, #f9d423, #f7971e);
            color: #1a1a2e;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
        }
        
        /* Admin Panel */
        .admin-panel {
            display: none;
        }
        
        .admin-panel.show {
            display: block;
        }
        
        .admin-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 10px;
        }
        
        .btn-admin {
            padding: 10px 12px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: white;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-family: inherit;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        
        .btn-admin:active {
            transform: scale(0.95);
            background: rgba(255,255,255,0.1);
        }
        
        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(10px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }
        
        .modal-overlay.show {
            display: flex;
        }
        
        .modal {
            background: linear-gradient(135deg, #1a1b3e, #2a1b4e);
            border-radius: 20px;
            padding: 24px;
            max-width: 400px;
            width: 100%;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            max-height: 90vh;
            overflow-y: auto;
        }
        
        .modal-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 16px;
            text-align: center;
        }
        
        .modal-input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: white;
            font-size: 14px;
            font-family: inherit;
            margin-bottom: 12px;
            transition: all 0.3s;
        }
        
        .modal-input:focus {
            outline: none;
            border-color: #7c5cfc;
            background: rgba(255,255,255,0.08);
        }
        
        .modal-input::placeholder {
            color: rgba(255,255,255,0.3);
        }
        
        .modal-actions {
            display: flex;
            gap: 10px;
        }
        
        .modal-actions .btn-main {
            flex: 1;
        }
        
        .modal-close {
            position: absolute;
            top: 16px;
            right: 16px;
            background: none;
            border: none;
            color: rgba(255,255,255,0.5);
            font-size: 24px;
            cursor: pointer;
        }
        
        /* Toast Notification */
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(20px);
            padding: 12px 24px;
            border-radius: 12px;
            color: white;
            font-size: 14px;
            font-weight: 500;
            z-index: 2000;
            display: none;
            max-width: 90%;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .toast.show {
            display: block;
            animation: slideUp 0.3s ease;
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateX(-50%) translateY(20px); }
            to { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
        
        .toast.success {
            border-color: #00b894;
        }
        
        .toast.error {
            border-color: #ff6b6b;
        }
        
        .toast.warning {
            border-color: #f9d423;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 3px;
        }
        
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(124, 92, 252, 0.3);
            border-radius: 10px;
        }
        
        /* Loading Spinner */
        .spinner {
            width: 30px;
            height: 30px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #7c5cfc;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Responsive */
        @media (max-width: 380px) {
            .container { padding: 8px 10px 80px 10px; }
            .stats-grid { gap: 4px; }
            .stat-card { padding: 8px 4px; }
            .stat-value { font-size: 16px; }
            .btn-main { font-size: 12px; padding: 10px; }
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 4px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 4px;
            margin-bottom: 12px;
        }
        
        .tab {
            flex: 1;
            padding: 8px;
            text-align: center;
            border: none;
            background: transparent;
            color: rgba(255,255,255,0.5);
            font-weight: 600;
            font-size: 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            font-family: inherit;
        }
        
        .tab.active {
            background: rgba(124, 92, 252, 0.2);
            color: white;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <!-- Toast Notification -->
    <div id="toast" class="toast"></div>
    
    <!-- Modal -->
    <div id="modal" class="modal-overlay">
        <div class="modal" style="position: relative;">
            <button class="modal-close" onclick="closeModal()">✕</button>
            <div id="modal-content"></div>
        </div>
    </div>
    
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo">
                <div class="logo-icon">🎰</div>
                <span class="logo-text">Lottery</span>
            </div>
            <div class="header-actions">
                <button class="btn-icon" onclick="showLanguageModal()" title="Language">🌐</button>
                <button class="btn-icon" onclick="showHelp()" title="Help">❓</button>
            </div>
        </div>
        
        <!-- User Card -->
        <div class="user-card" id="userCard">
            <div class="user-info">
                <div class="user-avatar" id="userAvatar">👤</div>
                <div>
                    <div class="user-name" id="userName">Loading...</div>
                    <div class="user-id" id="userId">ID: ---</div>
                </div>
            </div>
            <div>
                <span class="user-badge" id="userBadge">🟢 Active</span>
            </div>
        </div>
        
        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="statBalance">0</div>
                <div class="stat-label">💰 Balance</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="statWins">0</div>
                <div class="stat-label">🏆 Wins</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="statReferrals">0</div>
                <div class="stat-label">👥 Referrals</div>
            </div>
        </div>
        
        <!-- Main Actions -->
        <div class="main-actions">
            <button class="btn-main btn-primary" onclick="joinLottery()">
                🎯 Join Lottery
            </button>
            <button class="btn-main btn-secondary" onclick="showReferral()">
                🔗 Referral
            </button>
            <button class="btn-main btn-gold" onclick="showWithdraw()">
                💰 Withdraw
            </button>
            <button class="btn-main btn-secondary" onclick="showHistory()">
                📜 History
            </button>
        </div>
        
        <!-- Lottery Status -->
        <div class="section">
            <div class="section-title">
                <span class="icon">🎯</span> Lottery Status
            </div>
            <div class="lottery-status">
                <div>
                    <span class="status-dot active" id="statusDot"></span>
                    <span id="statusText">Active</span>
                </div>
                <div style="font-size:13px; color: rgba(255,255,255,0.5);">
                    <span id="participantCount">0</span> participants
                </div>
            </div>
            <div style="font-size:13px; color: rgba(255,255,255,0.5);">
                🏆 Prize: <span id="prizeAmount">0</span> USDT
            </div>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('participants')">👥 Participants</button>
            <button class="tab" onclick="switchTab('winners')">🏆 Winners</button>
            <button class="tab" onclick="switchTab('admin')">🛠 Admin</button>
        </div>
        
        <!-- Participants Tab -->
        <div class="tab-content active" id="tab-participants">
            <div class="section">
                <div class="section-title">
                    <span class="icon">👥</span> Participants (<span id="participantCount2">0</span>)
                </div>
                <div id="participantList">
                    <div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">
                        No participants yet
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Winners Tab -->
        <div class="tab-content" id="tab-winners">
            <div class="section">
                <div class="section-title">
                    <span class="icon">🏆</span> Winners
                </div>
                <div id="winnerList">
                    <div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">
                        No winners yet
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Admin Tab -->
        <div class="tab-content" id="tab-admin">
            <div class="section" id="adminPanel">
                <div class="section-title">
                    <span class="icon">🛠</span> Admin Panel
                </div>
                <div id="adminContent">
                    <div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">
                        🔒 Admin access required
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // ============ STATE ============
        const state = {
            userId: null,
            userName: '',
            language: 'en',
            isAdmin: false,
            data: {}
        };
        
        // ============ API CALLS ============
        async function apiCall(endpoint, method = 'GET', data = null) {
            try {
                const options = {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-User-Id': state.userId || ''
                    }
                };
                if (data) options.body = JSON.stringify(data);
                
                const response = await fetch('/api/' + endpoint, options);
                return await response.json();
            } catch (e) {
                showToast('Connection error', 'error');
                return null;
            }
        }
        
        // ============ TOAST ============
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type + ' show';
            clearTimeout(toast._timeout);
            toast._timeout = setTimeout(() => {
                toast.className = 'toast';
            }, 3000);
        }
        
        // ============ MODAL ============
        function showModal(content) {
            document.getElementById('modal-content').innerHTML = content;
            document.getElementById('modal').classList.add('show');
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('show');
        }
        
        // ============ TABS ============
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            
            document.querySelector(`.tab[onclick*="${tab}"]`).classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }
        
        // ============ LOAD USER DATA ============
        async function loadUserData() {
            const userData = await apiCall('user');
            if (userData) {
                state.userId = userData.id;
                state.userName = userData.name || 'User';
                state.isAdmin = userData.is_admin || false;
                
                document.getElementById('userName').textContent = state.userName;
                document.getElementById('userId').textContent = 'ID: ' + state.userId;
                document.getElementById('userAvatar').textContent = state.userName.charAt(0).toUpperCase();
                
                // Update stats
                document.getElementById('statBalance').textContent = userData.balance || 0;
                document.getElementById('statWins').textContent = userData.wins || 0;
                document.getElementById('statReferrals').textContent = userData.referrals || 0;
                
                // Update admin panel
                if (state.isAdmin) {
                    loadAdminPanel();
                }
                
                // Load participants
                loadParticipants();
            }
        }
        
        // ============ LOAD PARTICIPANTS ============
        async function loadParticipants() {
            const data = await apiCall('lottery/participants');
            if (data) {
                document.getElementById('participantCount').textContent = data.count || 0;
                document.getElementById('participantCount2').textContent = data.count || 0;
                
                const list = document.getElementById('participantList');
                if (data.participants && data.participants.length > 0) {
                    list.innerHTML = data.participants.map(p => `
                        <div class="participant-item">
                            <div class="participant-avatar">${p.name ? p.name.charAt(0).toUpperCase() : '👤'}</div>
                            <div class="participant-name">${p.name || 'User ' + p.id}</div>
                            <div class="participant-wallet">${p.wallet ? p.wallet.slice(0,6)+'...'+p.wallet.slice(-4) : 'No wallet'}</div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">No participants yet</div>';
                }
            }
        }
        
        // ============ LOAD ADMIN PANEL ============
        function loadAdminPanel() {
            if (!state.isAdmin) {
                document.getElementById('adminContent').innerHTML = `
                    <div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">
                        🔒 Admin access required
                    </div>
                `;
                return;
            }
            
            document.getElementById('adminContent').innerHTML = `
                <div class="admin-actions">
                    <button class="btn-admin" onclick="adminBroadcast()">📢 Broadcast</button>
                    <button class="btn-admin" onclick="adminStartLottery()">🎯 Start Lottery</button>
                    <button class="btn-admin" onclick="adminManualVerify()">✅ Manual Verify</button>
                    <button class="btn-admin" onclick="adminAddApi()">🔑 Add API</button>
                    <button class="btn-admin" onclick="adminWithdrawals()">💰 Withdrawals</button>
                    <button class="btn-admin" onclick="adminRestart()">🔄 Restart</button>
                </div>
                <div style="margin-top:10px; font-size:12px; color: rgba(255,255,255,0.3);">
                    🟢 System: Online | ${new Date().toLocaleString()}
                </div>
            `;
        }
        
        // ============ JOIN LOTTERY ============
        async function joinLottery() {
            showModal(`
                <div class="modal-title">🎯 Join Lottery</div>
                <p style="color: rgba(255,255,255,0.6); margin-bottom: 16px; font-size:14px;">
                    Send <strong>100 USDT</strong> to the contract address:
                </p>
                <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 13px; margin-bottom: 16px; word-break: break-all; color: #7c5cfc;">
                    TV61aTh98MGqmteYzda5AaBzdXgGqreG6A
                </div>
                <input class="modal-input" id="walletInput" placeholder="Enter your TRC20 wallet address" />
                <input class="modal-input" id="txInput" placeholder="Enter transaction ID" />
                <div class="modal-actions">
                    <button class="btn-main btn-primary" onclick="submitJoin()">✅ Verify</button>
                    <button class="btn-main btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            `);
        }
        
        async function submitJoin() {
            const wallet = document.getElementById('walletInput').value.trim();
            const txId = document.getElementById('txInput').value.trim();
            
            if (!wallet || !txId) {
                showToast('Please fill all fields', 'error');
                return;
            }
            
            if (wallet.length !== 34 || !wallet.startsWith('T')) {
                showToast('Invalid wallet address', 'error');
                return;
            }
            
            closeModal();
            showToast('⏳ Verifying transaction...', 'warning');
            
            const result = await apiCall('lottery/join', 'POST', {
                wallet: wallet,
                tx_id: txId
            });
            
            if (result && result.success) {
                showToast('✅ Successfully joined lottery!', 'success');
                loadParticipants();
                loadUserData();
            } else {
                showToast(result?.message || '❌ Verification failed', 'error');
            }
        }
        
        // ============ REFERRAL ============
        function showReferral() {
            showModal(`
                <div class="modal-title">🔗 Your Referral Link</div>
                <p style="color: rgba(255,255,255,0.6); margin-bottom: 16px; font-size:14px;">
                    Share your referral link and earn rewards!
                </p>
                <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; font-size: 12px; margin-bottom: 16px; word-break: break-all; color: #7c5cfc;">
                    https://t.me/UTYOB_Bot?start=${state.userId || ''}
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="btn-main btn-primary" onclick="copyReferral()">📋 Copy</button>
                    <button class="btn-main btn-secondary" onclick="closeModal()">Close</button>
                </div>
            `);
        }
        
        function copyReferral() {
            const text = `https://t.me/UTYOB_Bot?start=${state.userId || ''}`;
            navigator.clipboard?.writeText(text);
            showToast('✅ Copied to clipboard!', 'success');
            closeModal();
        }
        
        // ============ WITHDRAW ============
        function showWithdraw() {
            showModal(`
                <div class="modal-title">💰 Withdraw</div>
                <p style="color: rgba(255,255,255,0.6); margin-bottom: 16px; font-size:14px;">
                    Enter your TRC20 wallet address to withdraw your prize.
                </p>
                <input class="modal-input" id="withdrawInput" placeholder="Enter TRC20 wallet address" />
                <div class="modal-actions">
                    <button class="btn-main btn-gold" onclick="submitWithdraw()">💰 Withdraw</button>
                    <button class="btn-main btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            `);
        }
        
        async function submitWithdraw() {
            const wallet = document.getElementById('withdrawInput').value.trim();
            if (!wallet || wallet.length !== 34 || !wallet.startsWith('T')) {
                showToast('Invalid wallet address', 'error');
                return;
            }
            
            closeModal();
            showToast('⏳ Processing withdrawal...', 'warning');
            
            const result = await apiCall('withdraw', 'POST', { wallet: wallet });
            if (result && result.success) {
                showToast('✅ Withdrawal request submitted!', 'success');
            } else {
                showToast(result?.message || '❌ Withdrawal failed', 'error');
            }
        }
        
        // ============ HISTORY ============
        function showHistory() {
            showModal(`
                <div class="modal-title">📜 Transaction History</div>
                <div id="historyList" style="max-height: 300px; overflow-y: auto;">
                    <div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">
                        Loading...
                    </div>
                </div>
                <button class="btn-main btn-secondary" onclick="closeModal()">Close</button>
            `);
            
            loadHistory();
        }
        
        async function loadHistory() {
            const data = await apiCall('history');
            const list = document.getElementById('historyList');
            
            if (data && data.history && data.history.length > 0) {
                list.innerHTML = data.history.map(h => `
                    <div style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size:13px;">
                        <div>${h.type} - ${h.amount || 0} USDT</div>
                        <div style="color: rgba(255,255,255,0.3); font-size:11px;">${h.date || ''}</div>
                        <div style="color: ${h.status === 'completed' ? '#00b894' : '#ff6b6b'}; font-size:11px;">${h.status || ''}</div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">No history</div>';
            }
        }
        
        // ============ LANGUAGE ============
        function showLanguageModal() {
            showModal(`
                <div class="modal-title">🌐 Select Language</div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <button class="btn-main btn-secondary" onclick="setLanguage('en')">🇬🇧 English</button>
                    <button class="btn-main btn-secondary" onclick="setLanguage('fa')">🇮🇷 فارسی</button>
                    <button class="btn-main btn-secondary" onclick="setLanguage('tr')">🇹🇷 Türkçe</button>
                </div>
                <button class="btn-main btn-secondary" style="margin-top:12px;" onclick="closeModal()">Close</button>
            `);
        }
        
        async function setLanguage(lang) {
            state.language = lang;
            await apiCall('language', 'POST', { language: lang });
            showToast('✅ Language changed!', 'success');
            closeModal();
        }
        
        // ============ HELP ============
        function showHelp() {
            showModal(`
                <div class="modal-title">❓ Help</div>
                <div style="font-size:14px; color: rgba(255,255,255,0.7); line-height: 1.6;">
                    <p><strong>🎯 Join Lottery:</strong> Send 100 USDT to the contract address and verify.</p>
                    <p><strong>🔗 Referral:</strong> Share your referral link and earn rewards.</p>
                    <p><strong>💰 Withdraw:</strong> Claim your prize if you win.</p>
                    <p><strong>📜 History:</strong> View your transaction history.</p>
                    <p><strong>🏆 Winners:</strong> See all past winners.</p>
                    <p style="margin-top:12px; color: rgba(255,255,255,0.3); font-size:12px;">
                        Support: @Admin
                    </p>
                </div>
                <button class="btn-main btn-secondary" style="margin-top:12px;" onclick="closeModal()">Close</button>
            `);
        }
        
        // ============ ADMIN FUNCTIONS ============
        async function adminBroadcast() {
            showModal(`
                <div class="modal-title">📢 Broadcast</div>
                <textarea class="modal-input" id="broadcastMsg" rows="3" placeholder="Enter your message..." style="resize: vertical;"></textarea>
                <div class="modal-actions">
                    <button class="btn-main btn-primary" onclick="submitBroadcast()">📢 Send</button>
                    <button class="btn-main btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            `);
        }
        
        async function submitBroadcast() {
            const msg = document.getElementById('broadcastMsg').value.trim();
            if (!msg) {
                showToast('Please enter a message', 'error');
                return;
            }
            
            closeModal();
            showToast('⏳ Sending broadcast...', 'warning');
            
            const result = await apiCall('admin/broadcast', 'POST', { message: msg });
            if (result && result.success) {
                showToast(`✅ Broadcast sent to ${result.sent || 0} users!`, 'success');
            } else {
                showToast('❌ Broadcast failed', 'error');
            }
        }
        
        async function adminStartLottery() {
            showModal(`
                <div class="modal-title">🎯 Start Lottery</div>
                <input class="modal-input" id="winnersCount" type="number" placeholder="Number of winners" />
                <input class="modal-input" id="prizeAmount" type="number" placeholder="Prize per winner (USDT)" />
                <div style="background: rgba(255, 107, 107, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 12px; color: #ff6b6b;">
                    ⚠️ This will start a new lottery and select winners!
                </div>
                <div class="modal-actions">
                    <button class="btn-main btn-danger" onclick="submitStartLottery()">🚀 Start</button>
                    <button class="btn-main btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            `);
        }
        
        async function submitStartLottery() {
            const winners = parseInt(document.getElementById('winnersCount').value);
            const prize = parseFloat(document.getElementById('prizeAmount').value);
            
            if (!winners || !prize || winners < 1 || prize < 1) {
                showToast('Please enter valid numbers', 'error');
                return;
            }
            
            closeModal();
            showToast('⏳ Starting lottery...', 'warning');
            
            const result = await apiCall('admin/start_lottery', 'POST', {
                winners_count: winners,
                prize_amount: prize
            });
            
            if (result && result.success) {
                showToast(`✅ Lottery started! ${winners} winners, ${prize} USDT each!`, 'success');
                loadParticipants();
                loadUserData();
            } else {
                showToast(result?.message || '❌ Failed to start lottery', 'error');
            }
        }
        
        async function adminManualVerify() {
            showModal(`
                <div class="modal-title">✅ Manual Verify</div>
                <input class="modal-input" id="verifyUserId" type="number" placeholder="User ID" />
                <div class="modal-actions">
                    <button class="btn-main btn-success" onclick="submitManualVerify()">✅ Verify</button>
                    <button class="btn-main btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            `);
        }
        
        async function submitManualVerify() {
            const userId = parseInt(document.getElementById('verifyUserId').value);
            if (!userId) {
                showToast('Please enter user ID', 'error');
                return;
            }
            
            closeModal();
            showToast('⏳ Verifying user...', 'warning');
            
            const result = await apiCall('admin/manual_verify', 'POST', { user_id: userId });
            if (result && result.success) {
                showToast(`✅ User ${userId} verified!`, 'success');
            } else {
                showToast('❌ Verification failed', 'error');
            }
        }
        
        async function adminAddApi() {
            showModal(`
                <div class="modal-title">🔑 Add API Key</div>
                <input class="modal-input" id="apiKeyInput" placeholder="Enter API key" />
                <input class="modal-input" id="apiMaxUsage" type="number" placeholder="Max usage (default: 1000)" />
                <div class="modal-actions">
                    <button class="btn-main btn-primary" onclick="submitAddApi()">➕ Add</button>
                    <button class="btn-main btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            `);
        }
        
        async function submitAddApi() {
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            const maxUsage = parseInt(document.getElementById('apiMaxUsage').value) || 1000;
            
            if (!apiKey) {
                showToast('Please enter API key', 'error');
                return;
            }
            
            closeModal();
            showToast('⏳ Adding API key...', 'warning');
            
            const result = await apiCall('admin/add_api', 'POST', {
                api_key: apiKey,
                max_usage: maxUsage
            });
            
            if (result && result.success) {
                showToast('✅ API key added!', 'success');
            } else {
                showToast('❌ Failed to add API key', 'error');
            }
        }
        
        async function adminWithdrawals() {
            showModal(`
                <div class="modal-title">💰 Withdrawals</div>
                <div id="withdrawalList" style="max-height: 300px; overflow-y: auto;">
                    <div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">
                        Loading...
                    </div>
                </div>
                <button class="btn-main btn-secondary" onclick="closeModal()">Close</button>
            `);
            
            loadWithdrawals();
        }
        
        async function loadWithdrawals() {
            const data = await apiCall('admin/withdrawals');
            const list = document.getElementById('withdrawalList');
            
            if (data && data.withdrawals && data.withdrawals.length > 0) {
                list.innerHTML = data.withdrawals.map(w => `
                    <div style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <div style="display: flex; justify-content: space-between; font-size:13px;">
                            <span>User: ${w.user_id}</span>
                            <span>${w.amount || 0} USDT</span>
                        </div>
                        <div style="font-size:11px; color: rgba(255,255,255,0.3);">
                            ${w.wallet || ''}
                        </div>
                        <div style="margin-top:6px; display: flex; gap: 6px;">
                            <span style="font-size:11px; color: ${w.status === 'completed' ? '#00b894' : '#f9d423'};">
                                ${w.status || 'pending'}
                            </span>
                            ${w.status !== 'completed' ? `
                                <button class="btn-admin" style="padding: 4px 12px; font-size: 10px;" onclick="adminConfirmWithdrawal(${w.id})">
                                    ✅ Confirm
                                </button>
                            ` : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                list.innerHTML = '<div style="text-align:center; padding:20px; color: rgba(255,255,255,0.3);">No withdrawals</div>';
            }
        }
        
        async function adminConfirmWithdrawal(id) {
            closeModal();
            showToast('⏳ Confirming...', 'warning');
            
            const result = await apiCall('admin/confirm_withdrawal', 'POST', { withdrawal_id: id });
            if (result && result.success) {
                showToast('✅ Withdrawal confirmed!', 'success');
            } else {
                showToast('❌ Confirmation failed', 'error');
            }
        }
        
        async function adminRestart() {
            if (confirm('Are you sure you want to restart the bot?')) {
                showToast('⏳ Restarting...', 'warning');
                const result = await apiCall('admin/restart', 'POST');
                if (result && result.success) {
                    showToast('✅ Bot restarted!', 'success');
                }
            }
        }
        
        // ============ INIT ============
        async function init() {
            // Get user ID from URL parameter
            const urlParams = new URLSearchParams(window.location.search);
            const userId = urlParams.get('user_id');
            
            if (userId) {
                state.userId = parseInt(userId);
            }
            
            await loadUserData();
            
            // Auto refresh every 30 seconds
            setInterval(() => {
                loadUserData();
                loadParticipants();
            }, 30000);
        }
        
        // Handle Telegram WebApp
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }
        
        // Start
        init();
    </script>
</body>
</html>
"""

# ============ FLASK APP ============
flask_app = Flask(__name__)
CORS(flask_app)

# ============ DATABASE SHARDING ============
class DatabaseShard:
    def __init__(self, shard_id: int):
        self.shard_id = shard_id
        self.conn = sqlite3.connect(f"shard_{shard_id}.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_tables()
        self.lock = threading.Lock()
    
    def init_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'en',
                referral_code TEXT UNIQUE,
                referrer_id INTEGER,
                subscription_expiry INTEGER,
                wallet_address TEXT,
                balance REAL DEFAULT 0,
                is_winner BOOLEAN DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                participated_count INTEGER DEFAULT 0,
                created_at INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                wallet_from TEXT,
                wallet_to TEXT,
                status TEXT,
                type TEXT,
                block_number INTEGER,
                verified_at INTEGER,
                created_at INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_participants (
                user_id INTEGER,
                lottery_id INTEGER,
                wallet_address TEXT,
                joined_at INTEGER,
                is_winner BOOLEAN DEFAULT 0,
                PRIMARY KEY (user_id, lottery_id)
            )
        ''')
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                max_usage INTEGER DEFAULT 1000,
                created_at INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                wallet_address TEXT,
                status TEXT DEFAULT 'pending',
                tx_hash TEXT,
                requested_at INTEGER,
                completed_at INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winners_count INTEGER DEFAULT 1,
                prize_amount REAL DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at INTEGER
            )
        ''')
        self.conn.commit()
    
    def execute(self, query: str, params: tuple = ()):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor

class ShardManager:
    def __init__(self, shard_count: int = Config.SHARD_COUNT):
        self.shards = [DatabaseShard(i) for i in range(shard_count)]
        self.shard_count = shard_count
    
    def get_shard(self, user_id: int) -> DatabaseShard:
        shard_id = user_id % self.shard_count
        return self.shards[shard_id]

shard_manager = ShardManager()

# ============ REDIS CACHE ============
class CacheManager:
    def __init__(self):
        try:
            self.redis = redis.Redis.from_url(Config.REDIS_URL, decode_responses=True)
        except:
            self.redis = None
        self.local_cache = TTLCache(maxsize=Config.CACHE_SIZE, ttl=300)
    
    def get(self, key: str):
        if self.local_cache:
            value = self.local_cache.get(key)
            if value:
                return value
        if self.redis:
            return self.redis.get(key)
        return None
    
    def set(self, key: str, value: str, ttl: int = 300):
        if self.local_cache:
            self.local_cache[key] = value
        if self.redis:
            self.redis.setex(key, ttl, value)
    
    def delete(self, key: str):
        if self.local_cache and key in self.local_cache:
            del self.local_cache[key]
        if self.redis:
            self.redis.delete(key)

cache = CacheManager()

# ============ TRANSACTION VERIFIER ============
class TransactionVerifier:
    def __init__(self):
        self.session = None
        self.api_keys = [Config.API_KEY]
        self.current_key_index = 0
        self.key_lock = threading.Lock()
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def verify_transaction(self, tx_id: str, from_wallet: str, to_wallet: str, amount: float) -> Tuple[bool, Dict]:
        try:
            session = await self.get_session()
            
            with self.key_lock:
                api_key = self.api_keys[self.current_key_index % len(self.api_keys)]
                self.current_key_index += 1
            
            url = f"{Config.TRONGRID_API}/v1/transactions/{tx_id}"
            headers = {"TRON-PRO-API-KEY": api_key}
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    tx_data = data.get('data', [{}])[0]
                    
                    contract_data = tx_data.get('raw_data', {}).get('contract', [{}])[0]
                    parameter = contract_data.get('parameter', {}).get('value', {})
                    
                    to_address = parameter.get('to_address')
                    if to_address:
                        to_address = base58.b58encode(bytes.fromhex(to_address)).decode()
                    
                    owner_address = parameter.get('owner_address')
                    if owner_address:
                        owner_address = base58.b58encode(bytes.fromhex(owner_address)).decode()
                    
                    amount_transferred = parameter.get('amount', 0) / 1_000_000
                    
                    if (to_address.lower() == to_wallet.lower() and
                        owner_address.lower() == from_wallet.lower() and
                        amount_transferred >= amount):
                        return True, {'amount': amount_transferred, 'from': owner_address, 'to': to_address}
            
            return False, {}
        except:
            return False, {}

# ============ USER SERVICE ============
class UserService:
    def get_user(self, user_id: int) -> Optional[Dict]:
        cache_key = f"user:{user_id}"
        cached = cache.get(cache_key)
        if cached:
            return json.loads(cached)
        
        shard = shard_manager.get_shard(user_id)
        cursor = shard.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            user_data = dict(row)
            cache.set(cache_key, json.dumps(user_data), 300)
            return user_data
        return None
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None, 
                   last_name: str = None, language: str = Config.DEFAULT_LANGUAGE) -> Dict:
        shard = shard_manager.get_shard(user_id)
        referral_code = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8]
        now = int(time.time())
        
        shard.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, language, referral_code, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, language, referral_code, now))
        
        user_data = {'user_id': user_id, 'username': username, 'first_name': first_name, 
                    'last_name': last_name, 'language': language, 'referral_code': referral_code}
        cache.set(f"user:{user_id}", json.dumps(user_data), 300)
        return user_data
    
    def update_wallet(self, user_id: int, wallet: str):
        shard = shard_manager.get_shard(user_id)
        shard.execute("UPDATE users SET wallet_address = ? WHERE user_id = ?", (wallet, user_id))
        cache.delete(f"user:{user_id}")
    
    def add_balance(self, user_id: int, amount: float):
        shard = shard_manager.get_shard(user_id)
        shard.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        cache.delete(f"user:{user_id}")
    
    def mark_winner(self, user_id: int):
        shard = shard_manager.get_shard(user_id)
        shard.execute("UPDATE users SET is_winner = 1, total_wins = total_wins + 1 WHERE user_id = ?", (user_id,))
        cache.delete(f"user:{user_id}")

user_service = UserService()

# ============ LOTTERY SERVICE ============
class LotteryService:
    def __init__(self):
        self.verifier = TransactionVerifier()
    
    async def add_participant(self, user_id: int, wallet: str, tx_id: str) -> Tuple[bool, str]:
        # Check if already participating
        shard = shard_manager.get_shard(user_id)
        cursor = shard.execute(
            "SELECT * FROM lottery_participants WHERE user_id = ? AND lottery_id = (SELECT MAX(lottery_id) FROM lottery_participants)",
            (user_id,)
        )
        if cursor.fetchone():
            return False, "already_participating"
        
        # Verify transaction
        verified, details = await self.verifier.verify_transaction(
            tx_id, wallet, Config.CONTRACT_ADDRESS, Config.LOTTERY_COST
        )
        
        if not verified:
            return False, "transaction_failed"
        
        # Add participant
        now = int(time.time())
        shard.execute('''
            INSERT INTO lottery_participants (user_id, lottery_id, wallet_address, joined_at)
            VALUES (?, (SELECT COALESCE(MAX(lottery_id), 0) + 1 FROM lottery_participants), ?, ?)
        ''', (user_id, wallet, now))
        
        shard.execute("UPDATE users SET participated_count = participated_count + 1 WHERE user_id = ?", (user_id,))
        cache.delete(f"user:{user_id}")
        
        return True, "success"
    
    def get_participants(self) -> List[Dict]:
        participants = []
        for shard in shard_manager.shards:
            cursor = shard.execute('''
                SELECT lp.user_id, lp.wallet_address, u.first_name, u.username
                FROM lottery_participants lp
                JOIN users u ON lp.user_id = u.user_id
                WHERE lp.lottery_id = (SELECT MAX(lottery_id) FROM lottery_participants)
            ''')
            for row in cursor.fetchall():
                participants.append(dict(row))
        return participants
    
    def select_winners(self, winners_count: int, prize_amount: float) -> List[int]:
        participants = self.get_participants()
        if len(participants) < winners_count:
            return []
        
        # Get previous winners
        previous_winners = []
        for shard in shard_manager.shards:
            cursor = shard.execute("SELECT user_id FROM users WHERE is_winner = 1")
            for row in cursor.fetchall():
                previous_winners.append(row['user_id'])
        
        eligible = [p['user_id'] for p in participants if p['user_id'] not in previous_winners]
        
        if len(eligible) < winners_count:
            eligible = [p['user_id'] for p in participants]
        
        # Fair random selection
        random.seed(time.time() + random.randint(1, 1000000))
        winners = random.sample(eligible, min(winners_count, len(eligible)))
        
        # Mark winners
        for user_id in winners:
            user_service.mark_winner(user_id)
        
        return winners

lottery_service = LotteryService()

# ============ FLASK API ENDPOINTS ============

@flask_app.route('/')
def index():
    return render_template_string(WEBAPP_HTML)

@flask_app.route('/api/user')
def api_get_user():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 401
    
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    user = user_service.get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get participation count
    shard = shard_manager.get_shard(user_id)
    cursor = shard.execute(
        "SELECT COUNT(*) as count FROM lottery_participants WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    
    return jsonify({
        'id': user_id,
        'name': user.get('first_name') or user.get('username') or f"User{user_id}",
        'balance': user.get('balance', 0),
        'wins': user.get('total_wins', 0),
        'referrals': 0,  # Would need separate table
        'is_admin': user_id in Config.ADMIN_IDS,
        'is_winner': user.get('is_winner', False),
        'wallet': user.get('wallet_address', '')
    })

@flask_app.route('/api/lottery/participants')
def api_get_participants():
    participants = lottery_service.get_participants()
    return jsonify({
        'count': len(participants),
        'participants': participants
    })

@flask_app.route('/api/lottery/join', methods=['POST'])
async def api_join_lottery():
    data = request.json
    user_id = request.headers.get('X-User-Id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 401
    
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    wallet = data.get('wallet')
    tx_id = data.get('tx_id')
    
    if not wallet or not tx_id:
        return jsonify({'error': 'Wallet and TX ID required'}), 400
    
    # Update wallet
    user_service.update_wallet(user_id, wallet)
    
    # Join lottery
    success, message = await lottery_service.add_participant(user_id, wallet, tx_id)
    
    return jsonify({
        'success': success,
        'message': message
    })

@flask_app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    data = request.json
    user_id = request.headers.get('X-User-Id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 401
    
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    wallet = data.get('wallet')
    if not wallet:
        return jsonify({'error': 'Wallet required'}), 400
    
    user = user_service.get_user(user_id)
    if not user or not user.get('is_winner'):
        return jsonify({'error': 'Not eligible for withdrawal'}), 400
    
    # Get prize amount from last lottery
    shard = shard_manager.get_shard(user_id)
    cursor = shard.execute(
        "SELECT prize_amount FROM lottery_results WHERE status = 'completed' ORDER BY created_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    amount = row['prize_amount'] if row else 0
    
    if amount <= 0:
        return jsonify({'error': 'No prize available'}), 400
    
    # Create withdrawal request
    now = int(time.time())
    shard.execute('''
        INSERT INTO withdrawals (user_id, amount, wallet_address, requested_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, amount, wallet, now))
    
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
    
    shard = shard_manager.get_shard(user_id)
    cursor = shard.execute('''
        SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 50
    ''', (user_id,))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'type': row.get('type', 'transaction'),
            'amount': row.get('amount', 0),
            'status': row.get('status', 'pending'),
            'date': datetime.fromtimestamp(row.get('created_at', 0)).strftime('%Y-%m-%d %H:%M')
        })
    
    return jsonify({'history': history})

@flask_app.route('/api/language', methods=['POST'])
def api_set_language():
    data = request.json
    user_id = request.headers.get('X-User-Id')
    
    if not user_id or not data.get('language'):
        return jsonify({'error': 'Invalid request'}), 400
    
    try:
        user_id = int(user_id)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    shard = shard_manager.get_shard(user_id)
    shard.execute("UPDATE users SET language = ? WHERE user_id = ?", (data['language'], user_id))
    cache.delete(f"user:{user_id}")
    
    return jsonify({'success': True})

# ============ ADMIN API ============

@flask_app.route('/api/admin/broadcast', methods=['POST'])
def api_admin_broadcast():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    message = data.get('message')
    if not message:
        return jsonify({'error': 'Message required'}), 400
    
    # Send to all users (async in background)
    def send_broadcast():
        sent = 0
        for shard in shard_manager.shards:
            cursor = shard.execute("SELECT user_id FROM users")
            for row in cursor.fetchall():
                try:
                    # Would use telegram bot here
                    sent += 1
                except:
                    pass
        return sent
    
    # Run in thread
    thread = threading.Thread(target=send_broadcast)
    thread.start()
    
    return jsonify({'success': True, 'sent': 0, 'queued': True})

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
    
    # Select winners
    winners = lottery_service.select_winners(winners_count, prize_amount)
    
    if not winners:
        return jsonify({'error': 'Not enough participants'}), 400
    
    # Record results
    participants = lottery_service.get_participants()
    now = int(time.time())
    
    for shard in shard_manager.shards:
        shard.execute('''
            INSERT INTO lottery_results (total_participants, winners_count, prize_amount, created_at, status)
            VALUES (?, ?, ?, ?, 'completed')
        ''', (len(participants), len(winners), prize_amount, now))
    
    return jsonify({
        'success': True,
        'winners': winners,
        'count': len(winners)
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
    
    try:
        target_user = int(target_user)
    except:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    # Mark as winner
    user_service.mark_winner(target_user)
    
    return jsonify({'success': True})

@flask_app.route('/api/admin/add_api', methods=['POST'])
def api_admin_add_api():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    api_key = data.get('api_key')
    max_usage = data.get('max_usage', 1000)
    
    if not api_key:
        return jsonify({'error': 'API key required'}), 400
    
    # Add to all shards
    for shard in shard_manager.shards:
        try:
            shard.execute('''
                INSERT INTO api_keys (api_key, max_usage, created_at)
                VALUES (?, ?, ?)
            ''', (api_key, max_usage, int(time.time())))
        except:
            pass
    
    return jsonify({'success': True})

@flask_app.route('/api/admin/withdrawals')
def api_admin_withdrawals():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    withdrawals = []
    for shard in shard_manager.shards:
        cursor = shard.execute("SELECT * FROM withdrawals WHERE status = 'pending' ORDER BY requested_at DESC")
        for row in cursor.fetchall():
            withdrawals.append(dict(row))
    
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
    
    for shard in shard_manager.shards:
        shard.execute('''
            UPDATE withdrawals SET status = 'completed', completed_at = ?
            WHERE id = ? AND status = 'pending'
        ''', (int(time.time()), withdrawal_id))
    
    return jsonify({'success': True})

@flask_app.route('/api/admin/restart', methods=['POST'])
def api_admin_restart():
    user_id = request.headers.get('X-User-Id')
    if not user_id or int(user_id) not in Config.ADMIN_IDS:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Restart logic would go here
    return jsonify({'success': True})

# ============ TELEGRAM BOT ============

class LotteryBot:
    def __init__(self, token: str):
        self.token = token
        self.application = None
        self.webapp_url = Config.WEBAPP_URL
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        # Create or get user
        existing = user_service.get_user(user.id)
        if not existing:
            user_service.create_user(
                user.id,
                user.username,
                user.first_name,
                user.last_name
            )
        
        # Handle referral
        if context.args and len(context.args) > 0:
            referrer_code = context.args[0]
            for shard in shard_manager.shards:
                cursor = shard.execute("SELECT user_id FROM users WHERE referral_code = ?", (referrer_code,))
                row = cursor.fetchone()
                if row:
                    shard.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (row['user_id'], user.id))
                    break
        
        # Show Play button
        keyboard = [[
            InlineKeyboardButton(
                "🎮 Play", 
                web_app=WebAppInfo(url=f"{self.webapp_url}?user_id={user.id}")
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎰 *Welcome to the Lottery Bot!*\n\n"
            "Click the button below to open the full app experience:\n\n"
            "✨ *Features:*\n"
            "• 🎯 Join Lottery\n"
            "• 🔗 Referral System\n"
            "• 💰 Withdraw Prizes\n"
            "• 📜 Transaction History\n"
            "• 🏆 View Winners\n\n"
            "Tap the button to get started! 🚀",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Unauthorized access!")
            return
        
        keyboard = [[
            InlineKeyboardButton(
                "🛠 Open Admin Panel", 
                web_app=WebAppInfo(url=f"{self.webapp_url}?user_id={user_id}")
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🛠 *Admin Panel*\n\n"
            "Open the admin panel to manage the lottery system.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

def setup_application():
    app = Application.builder().token(Config.BOT_TOKEN).build()
    bot = LotteryBot(Config.BOT_TOKEN)
    
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("admin", bot.admin))
    
    return app

# ============ MAIN ============

async def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    # Start Flask server
    def run_flask():
        flask_app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start bot
    app = setup_application()
    print("🤖 Lottery Bot starting...")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    print("✅ Bot is running! WebApp: " + Config.WEBAPP_URL)
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")