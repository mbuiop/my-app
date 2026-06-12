import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # توکن‌ها
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ENCRYPTION_PASSWORD = os.getenv('ENCRYPTION_PASSWORD')
    BOT_USERNAME = os.getenv('BOT_USERNAME', 'ROBTTSAZE_bot')
    
    # ادمین‌ها
    ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    
    # دیتابیس
    DATABASE_URL = os.getenv('DATABASE_URL')
    REDIS_URL = os.getenv('REDIS_URL')
    
    # محدودیت‌ها
    MAX_BOTS_PER_USER = int(os.getenv('MAX_BOTS_PER_USER', 3))
    MAX_MEMORY_PER_BOT = int(os.getenv('MAX_MEMORY_PER_BOT', 50))
    MAX_CPU_PER_BOT = float(os.getenv('MAX_CPU_PER_BOT', 0.5))
    MAX_BOT_TIMEOUT = int(os.getenv('MAX_BOT_TIMEOUT', 30))
    MAX_BUILDS_PER_HOUR = int(os.getenv('MAX_BUILDS_PER_HOUR', 10))
    MAX_CONCURRENT_BUILDS = int(os.getenv('MAX_CONCURRENT_BUILDS', 5))
    RATE_LIMIT_PER_SECOND = int(os.getenv('RATE_LIMIT_PER_SECOND', 3))
    MAX_USERS_CAPACITY = int(os.getenv('MAX_USERS_CAPACITY', 10000))
    
    # پرداخت
    TRC20_ADDRESS = os.getenv('TRC20_ADDRESS')
    CARD_NUMBER = os.getenv('CARD_NUMBER')
    CARD_HOLDER = os.getenv('CARD_HOLDER')
    CARD_BANK = os.getenv('CARD_BANK')
    SUBSCRIPTION_PRICE = int(os.getenv('SUBSCRIPTION_PRICE', 2000000))
    WITHDRAW_PERCENT = int(os.getenv('WITHDRAW_PERCENT', 7))
    MIN_WITHDRAW = int(os.getenv('MIN_WITHDRAW', 2000000))
    
    # مسیرها
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    USER_FILES_PATH = os.getenv('USER_FILES_PATH', os.path.join(BASE_DIR, 'user_files'))
    LOGS_PATH = os.getenv('LOGS_PATH', os.path.join(BASE_DIR, 'logs'))
    MACHINES_PATH = os.path.join(BASE_DIR, 'machines')
    
    # داکر
    DOCKER_SANDBOX_IMAGE = "bot-sandbox:latest"
    
    @classmethod
    def validate(cls):
        errors = []
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is required")
        if not cls.ENCRYPTION_PASSWORD:
            errors.append("ENCRYPTION_PASSWORD is required")
        if not cls.ADMIN_IDS:
            errors.append("ADMIN_IDS is required")
        if errors:
            raise ValueError("\n".join(errors))
