"""TTL-based in-memory cache with stale-while-error support."""

import time
from typing import Any


class TTLCache:
    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}
        self._stale: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            return None
        return value

    def get_stale(self, key: str) -> Any | None:
        return self._stale.get(key)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._store[key] = (value, time.time() + ttl_seconds)
        self._stale[key] = value

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired_keys:
            del self._store[k]
