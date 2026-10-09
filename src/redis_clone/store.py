"""In-memory key-value store with optional expiry.

Thread-safe via a lock. Expiry is lazy: we only check whether a key
has expired when it is read or listed. That is how real Redis behaves
by default for reads (it does have an active expiry cycle, but the
lazy path is enough for a toy clone).
"""

from __future__ import annotations

import threading
import time


class Store:
    """A tiny thread-safe dict with optional per-key expiry."""

    def __init__(self) -> None:
        self._data: dict = {}
        self._expires: dict = {}  # key -> unix timestamp when key expires
        self._lock = threading.Lock()

    def _is_expired(self, key: str) -> bool:
        when = self._expires.get(key)
        if when is None:
            return False
        if time.time() >= when:
            self._data.pop(key, None)
            self._expires.pop(key, None)
            return True
        return False

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._data[key] = value
            self._expires.pop(key, None)

    def get(self, key: str):
        with self._lock:
            if self._is_expired(key):
                return None
            return self._data.get(key)

    def delete(self, key: str) -> int:
        """Delete a key. Returns 1 if it existed, 0 otherwise."""
        with self._lock:
            self._is_expired(key)
            existed = key in self._data
            self._data.pop(key, None)
            self._expires.pop(key, None)
            return 1 if existed else 0

    def exists(self, key: str) -> int:
        with self._lock:
            if self._is_expired(key):
                return 0
            return 1 if key in self._data else 0

    def expire(self, key: str, seconds: int) -> int:
        """Set a TTL in seconds. Returns 1 if the key exists, 0 otherwise."""
        with self._lock:
            if self._is_expired(key):
                return 0
            if key not in self._data:
                return 0
            self._expires[key] = time.time() + seconds
            return 1

    def ttl(self, key: str) -> int:
        """Seconds remaining until expiry. -1 = no expiry, -2 = no such key."""
        with self._lock:
            if self._is_expired(key):
                return -2
            if key not in self._data:
                return -2
            when = self._expires.get(key)
            if when is None:
                return -1
            remaining = int(when - time.time())
            return max(remaining, 0)

    def keys(self) -> list:
        """Return all live (non-expired) keys, sorted for determinism."""
        with self._lock:
            # Trigger lazy expiry cleanup
            for k in list(self._expires.keys()):
                self._is_expired(k)
            return sorted(self._data.keys())

    def flushall(self) -> None:
        with self._lock:
            self._data.clear()
            self._expires.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._data)
