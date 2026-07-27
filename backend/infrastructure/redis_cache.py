import redis
import pickle
from typing import Any, Optional
from backend.domain.interfaces import ICacheService
from backend.infrastructure.cache import OrderedDictLRUCache
from backend.infrastructure.logging import log_event

class RedisCacheService(ICacheService):
    def __init__(self, redis_url: Optional[str] = None):
        self.fallback = OrderedDictLRUCache()
        self.enabled = False
        self.client = None
        
        if redis_url:
            try:
                self.client = redis.from_url(redis_url, socket_timeout=2.0)
                # Quick test connection
                self.client.ping()
                self.enabled = True
                log_event("redis_init_success", {"redis_url": redis_url.split("@")[-1]}) # omit passwords
            except Exception as e:
                self.enabled = False
                log_event("redis_init_failed", {"error": str(e), "info": "Gracefully falling back to memory cache"}, "warning")
        else:
            log_event("redis_bypass", {"info": "No REDIS_URL provided, using memory cache"})

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled or not self.client:
            return self.fallback.get(key)
        try:
            data = self.client.get(key)
            return pickle.loads(data) if data else None
        except Exception as e:
            log_event("redis_read_error", {"error": str(e)}, "warning")
            return self.fallback.get(key)

    def set(self, key: str, value: Any, expiration_seconds: int = 3600) -> None:
        if not self.enabled or not self.client:
            self.fallback.set(key, value, expiration_seconds)
            return
        try:
            self.client.setex(key, expiration_seconds, pickle.dumps(value))
        except Exception as e:
            log_event("redis_write_error", {"error": str(e)}, "warning")
            self.fallback.set(key, value, expiration_seconds)

    def clear(self) -> None:
        if self.enabled and self.client:
            try:
                self.client.flushdb()
            except Exception as e:
                log_event("redis_clear_error", {"error": str(e)}, "warning")
        self.fallback.clear()
