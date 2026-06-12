import hashlib
import os
import time
import re
import magic
from pathlib import Path
from typing import Tuple
from .config import Config

class SecurityManager:
    ALLOWED_EXTENSIONS = {'.py', '.zip', '.js', '.java', '.cs', '.php', '.go', '.rs'}
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    DANGEROUS_PATTERNS = [
        '__import__', '__builtins__', '__globals__', '__dict__',
        'os.system', 'subprocess', 'eval(', 'exec(',
        'open(', 'file(', 'compile(', '__getattr__', '__setattr__',
        'globals()', 'locals()', 'vars(', 'dir(', 'breakpoint(',
        '__reduce__', '__reduce_ex__', '__class__', '__base__', '__mro__'
    ]
    
    @staticmethod
    def sanitize_filename(original_name: str, user_id: int) -> str:
        ext = Path(original_name).suffix.lower()
        if ext not in SecurityManager.ALLOWED_EXTENSIONS:
            ext = '.py'
        safe_name = hashlib.md5(f"{user_id}_{original_name}_{time.time()}".encode()).hexdigest()[:16]
        return f"{safe_name}{ext}"
    
    @staticmethod
    def validate_file(content: bytes) -> Tuple[bool, str]:
        if len(content) > SecurityManager.MAX_FILE_SIZE:
            return False, f"File too large (max {SecurityManager.MAX_FILE_SIZE // 1024 // 1024}MB)"
        
        try:
            mime = magic.from_buffer(content, mime=True)
            if mime not in ['text/x-python', 'text/x-script.python', 'application/zip', 
                           'text/plain', 'application/javascript', 'text/x-java', 
                           'text/x-csharp', 'text/x-php', 'text/x-go', 'text/x-rust']:
                return False, "Invalid file type"
        except:
            pass
        
        try:
            text = content.decode('utf-8', errors='ignore')
            for pattern in SecurityManager.DANGEROUS_PATTERNS:
                if pattern in text:
                    return False, f"Dangerous code detected: {pattern}"
        except:
            return False, "Invalid encoding"
        
        return True, "OK"
    
    @staticmethod
    def save_secure(content: bytes, safe_name: str, user_id: int) -> str:
        user_dir = Path(Config.USER_FILES_PATH) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(user_dir, 0o700)
        
        file_path = user_dir / safe_name
        with open(file_path, 'wb') as f:
            f.write(content)
        os.chmod(file_path, 0o600)
        
        return str(file_path)
    
    @staticmethod
    def extract_token(code: str) -> str:
        patterns = [
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'BOT_TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'const\s+token\s*=\s*["\']([^"\']+)["\']',
            r'private\s+static\s+final\s+String\s+TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'define\s*\(\s*[\'"]BOT_TOKEN[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
        ]
        for pattern in patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
