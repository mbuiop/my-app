import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .config import Config

class SecureLogFilter(logging.Filter):
    PATTERNS = [
        (r'bot\d+:[A-Za-z0-9_-]{20,}', '[BOT_TOKEN_HIDDEN]'),
        (r'\d{10}:[A-Za-z0-9_-]{35,}', '[TOKEN_HIDDEN]'),
        (r'(?i)(password|passwd|token|secret|key)\s*[=:]\s*["\'][^"\']+["\']', r'\1=[HIDDEN]'),
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_HIDDEN]'),
        (r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '[CTRL]'),
    ]
    
    def filter(self, record):
        msg = record.getMessage()
        for pattern, repl in self.PATTERNS:
            msg = re.sub(pattern, repl, msg, flags=re.IGNORECASE)
        if len(msg) > 2000:
            msg = msg[:1997] + "..."
        record.msg = msg
        return True

def setup_logging():
    Path(Config.LOGS_PATH).mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger('MotherBot')
    logger.setLevel(logging.INFO)
    logger.addFilter(SecureLogFilter())
    
    file_handler = RotatingFileHandler(
        f"{Config.LOGS_PATH}/mother_bot.log",
        maxBytes=100*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    return logger
