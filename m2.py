#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
🛡️ m2.py - ایزوله‌سازی سخت‌افزاری - هر ربات در کانتینر جدا
═══════════════════════════════════════════════════════════════════
"""

import docker
import asyncio
import os
import subprocess
import shutil
from typing import Dict, Optional
from loguru import logger
import yaml

# ==================== تنظیمات ====================
MAX_MEMORY_PER_BOT = 128  # 128 MB
MAX_CPU_PER_BOT = 0.5     # 0.5 هسته
MAX_PIDS_PER_BOT = 100     # حداکثر 100 پروسه

class ContainerIsolator:
    """ایزوله‌سازی ربات‌ها با Docker"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("✅ Docker connected successfully")
        except Exception as e:
            logger.error(f"❌ Docker not available: {e}")
            self.docker_client = None
    
    async def create_bot_container(
        self, 
        bot_id: str, 
        code: str, 
        token: str,
        user_id: int
    ) -> Optional[str]:
        """
        ایجاد کانتینر برای ربات
        Returns: container_id
        """
        if not self.docker_client:
            logger.error("Docker not available")
            return None
        
        try:
            # ایجاد پوشه موقت
            bot_dir = f"/tmp/bot_{bot_id}"
            os.makedirs(bot_dir, exist_ok=True)
            
            # ذخیره کد
            code_path = os.path.join(bot_dir, "bot.py")
            with open(code_path, 'w', encoding='utf-8') as f:
                # اضافه کردن سیستم مدیریت عضوگیری
                join_code = self._get_join_management_code(bot_id)
                f.write(join_code + "\n" + code)
            
            # Dockerfile
            dockerfile = f'''
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pyTelegramBotAPI requests

COPY bot.py .

CMD ["python", "bot.py"]
'''
            dockerfile_path = os.path.join(bot_dir, "Dockerfile")
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile)
            
            # ساخت ایمیج
            image_name = f"bot_{bot_id}"
            self.docker_client.images.build(
                path=bot_dir,
                tag=image_name,
                rm=True
            )
            
            # اجرای کانتینر
            container = self.docker_client.containers.run(
                image_name,
                detach=True,
                name=f"bot_{bot_id}",
                mem_limit=f"{MAX_MEMORY_PER_BOT}m",
                memswap_limit=f"{MAX_MEMORY_PER_BOT}m",
                nano_cpus=int(MAX_CPU_PER_BOT * 1e9),
                pids_limit=MAX_PIDS_PER_BOT,
                restart_policy={"Name": "always"},
                remove=False,
                network_mode="bridge"
            )
            
            logger.info(f"✅ Container created for bot {bot_id}: {container.id}")
            
            # تمیزکاری
            shutil.rmtree(bot_dir, ignore_errors=True)
            
            return container.id
            
        except Exception as e:
            logger.error(f"Failed to create container for bot {bot_id}: {e}")
            return None
    
    async def stop_bot_container(self, bot_id: str, container_id: str) -> bool:
        """توقف کانتینر ربات"""
        if not self.docker_client:
            return False
        
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove()
            logger.info(f"✅ Container stopped for bot {bot_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {bot_id}: {e}")
            return False
    
    async def get_container_status(self, container_id: str) -> Dict:
        """دریافت وضعیت کانتینر"""
        if not self.docker_client:
            return {'running': False}
        
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            return {
                'running': container.status == 'running',
                'cpu_usage': stats['cpu_stats']['cpu_usage']['total_usage'] / 1e9,
                'memory_usage': stats['memory_stats']['usage'] / (1024 * 1024),
                'memory_limit': stats['memory_stats']['limit'] / (1024 * 1024)
            }
        except:
            return {'running': False}
    
    def _get_join_management_code(self, bot_id: str) -> str:
        """کد مدیریت عضوگیری که به ربات اضافه می‌شود"""
        return f'''
# ========== سیستم مدیریت عضوگیری ==========
import sqlite3, os, time, threading, asyncpg
from functools import wraps

# اتصال به دیتابیس مرکزی
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@host.docker.internal:5432/mother_bot")
bot_id = "{bot_id}"
join_enabled_cache = True
block_message_cache = "🚫 سرور در حال حاضر پر است. لطفاً بعداً تلاش کنید."

async def update_cache():
    global join_enabled_cache, block_message_cache
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        result = await conn.fetchrow("SELECT join_enabled, join_block_message FROM bots WHERE id = $1", bot_id)
        await conn.close()
        if result:
            join_enabled_cache = result[0]
            block_message_cache = result[1] if result[1] else "🚫 سرور پر است"
    except:
        pass

def cache_updater():
    import asyncio
    while True:
        asyncio.run(update_cache())
        time.sleep(30)

threading.Thread(target=cache_updater, daemon=True).start()

def check_join_enabled(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        if not join_enabled_cache:
            bot.reply_to(message, block_message_cache)
            return
        return func(message, *args, **kwargs)
    return wrapper
# ===========================================
'''

class KubernetesManager:
    """مدیریت Kubernetes برای مقیاس بالا"""
    
    def __init__(self):
        self.namespace = "mother-bot"
    
    async def deploy_bot_as_pod(self, bot_id: str, code: str, token: str) -> Optional[str]:
        """استقرار ربات به عنوان Pod در Kubernetes"""
        
        # ایجاد ConfigMap با کد
        configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": f"bot-code-{bot_id}", "namespace": self.namespace},
            "data": {"bot.py": code}
        }
        
        # ایجاد Pod
        pod = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": f"bot-{bot_id}", "namespace": self.namespace, "labels": {"bot-id": bot_id}},
            "spec": {
                "containers": [{
                    "name": "bot",
                    "image": "python:3.11-slim",
                    "command": ["python", "/app/bot.py"],
                    "resources": {
                        "requests": {"memory": "128Mi", "cpu": "0.25"},
                        "limits": {"memory": "256Mi", "cpu": "0.5"}
                    },
                    "volumeMounts": [{"name": "code", "mountPath": "/app"}]
                }],
                "volumes": [{"name": "code", "configMap": {"name": f"bot-code-{bot_id}"}}],
                "restartPolicy": "Always"
            }
        }
        
        # اعمال به Kubernetes
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(configmap, f)
            subprocess.run(['kubectl', 'apply', '-f', f.name])
            
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(pod, f)
            subprocess.run(['kubectl', 'apply', '-f', f.name])
        
        return f"bot-{bot_id}"  # pod name

# نمونه گلوبال
isolator = ContainerIsolator()
k8s_manager = KubernetesManager()
