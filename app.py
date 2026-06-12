#!/usr/bin/env python3
import asyncio
import threading
import time
from flask import Flask, jsonify

from core.config import Config
from core.database import Database
from core.redis_client import RedisClient
from core.logging_config import setup_logging
from handlers.user_handlers import register_user_handlers
from handlers.bot_handlers import register_bot_handlers
from handlers.payment_handlers import register_payment_handlers
from handlers.admin_handlers import register_admin_handlers

import telebot

logger = setup_logging()

# Validate config
Config.validate()

# Initialize bot
bot = telebot.TeleBot(Config.BOT_TOKEN)

# Initialize services
db = Database()
redis = RedisClient()

# Flask app for health checks
flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "timestamp": time.time(),
        "bot": "running"
    })

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000)

# Register all handlers
register_user_handlers(bot)
register_bot_handlers(bot)
register_payment_handlers(bot)
register_admin_handlers(bot)

# Main entry point
async def main():
    await db.connect()
    await redis.connect()
    logger.info("✅ All services connected")
    
    # Start Flask in background
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start bot polling
    logger.info("🚀 Mother Bot started!")
    
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 MOTHER BOT - ULTIMATE ENTERPRISE 3.0")
    print("=" * 70)
    print(f"👑 Admins: {Config.ADMIN_IDS}")
    print(f"🤖 Bot: @{Config.BOT_USERNAME}")
    print(f"🐳 Docker: Enabled")
    print(f"🗄️ PostgreSQL: Configured")
    print(f"⚡ Redis: Configured")
    print("=" * 70)
    
    asyncio.run(main())
