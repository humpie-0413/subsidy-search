import time
from cache import TTLCache


def test_set_and_get():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=60)
    assert cache.get("key1") == "value1"


def test_get_returns_none_for_missing_key():
    cache = TTLCache()
    assert cache.get("nonexistent") is None


def test_ttl_expiry():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=1)
    assert cache.get("key1") == "value1"
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_stale_survives_expiry():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get("key1") is None
    assert cache.get_stale("key1") == "value1"


def test_stale_updated_on_set():
    cache = TTLCache()
    cache.set("key1", "v1", ttl_seconds=60)
    cache.set("key1", "v2", ttl_seconds=60)
    assert cache.get_stale("key1") == "v2"


def test_clear_expired_removes_from_store_not_stale():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=1)
    time.sleep(1.1)
    cache.clear_expired()
    assert cache.get("key1") is None
    assert cache.get_stale("key1") == "value1"


def test_invalidate():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=60)
    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_invalidate_nonexistent_key_no_error():
    cache = TTLCache()
    cache.invalidate("nope")
