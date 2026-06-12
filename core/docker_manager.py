import docker
import hashlib
import time
from typing import Dict, Any
from .config import Config

class DockerManager:
    def __init__(self):
        self.client = None
        self._connect()
    
    def _connect(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
            print("✅ Docker connected")
        except Exception as e:
            print(f"❌ Docker error: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def run_bot_safe(self, bot_id: str, code: str) -> Dict[str, Any]:
        if not self.client:
            return {"success": False, "error": "Docker not available"}
        
        safe_name = hashlib.md5(f"{bot_id}_{time.time()}".encode()).hexdigest()[:16]
        
        try:
            container = self.client.containers.run(
                image=Config.DOCKER_SANDBOX_IMAGE,
                command=["python", "-c", code],
                name=f"bot_{safe_name}",
                detach=True,
                mem_limit=f"{Config.MAX_MEMORY_PER_BOT}m",
                memswap_limit=f"{Config.MAX_MEMORY_PER_BOT}m",
                nano_cpus=int(Config.MAX_CPU_PER_BOT * 1_000_000_000),
                pids_limit=10,
                read_only=True,
                network_disabled=True,
                auto_remove=True,
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"]
            )
            
            result = container.wait(timeout=Config.MAX_BOT_TIMEOUT)
            logs = container.logs().decode('utf-8', errors='ignore')
            
            if result["StatusCode"] == 0:
                return {"success": True, "logs": logs}
            else:
                return {"success": False, "error": "Execution failed", "logs": logs}
                
        except docker.errors.APIError as e:
            error_msg = str(e)
            if "memory" in error_msg.lower():
                return {"success": False, "error": f"Memory limit exceeded ({Config.MAX_MEMORY_PER_BOT}MB)"}
            return {"success": False, "error": error_msg[:100]}
        except Exception as e:
            return {"success": False, "error": str(e)[:100]}
