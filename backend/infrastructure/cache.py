import time
from collections import OrderedDict
from typing import Any, Optional
from backend.domain.interfaces import ICacheService

class OrderedDictLRUCache(ICacheService):
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        value, expires_at = self.cache[key]
        if time.time() > expires_at:
            del self.cache[key]
            return None
        # Move to end to represent recently used
        self.cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any, expiration_seconds: int = 3600) -> None:
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.capacity:
            # Pop the oldest (least recently used) item
            self.cache.popitem(last=False)
        expires_at = time.time() + expiration_seconds
        self.cache[key] = (value, expires_at)

    def clear(self) -> None:
        self.cache.clear()
