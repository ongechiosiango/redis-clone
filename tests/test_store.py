"""Tests for the in-memory store."""

import time

from redis_clone.store import Store


def test_set_and_get():
    s = Store()
    s.set("k", "v")
    assert s.get("k") == "v"


def test_get_missing():
    s = Store()
    assert s.get("nope") is None


def test_set_overwrites():
    s = Store()
    s.set("k", "a")
    s.set("k", "b")
    assert s.get("k") == "b"


def test_delete_existing():
    s = Store()
    s.set("k", "v")
    assert s.delete("k") == 1
    assert s.get("k") is None


def test_delete_missing():
    s = Store()
    assert s.delete("nope") == 0


def test_exists():
    s = Store()
    s.set("k", "v")
    assert s.exists("k") == 1
    assert s.exists("nope") == 0


def test_keys_sorted():
    s = Store()
    s.set("c", "1")
    s.set("a", "2")
    s.set("b", "3")
    assert s.keys() == ["a", "b", "c"]


def test_flushall():
    s = Store()
    s.set("a", "1")
    s.set("b", "2")
    s.flushall()
    assert s.keys() == []


def test_expire_and_ttl():
    s = Store()
    s.set("k", "v")
    assert s.ttl("k") == -1  # no expiry

    s.expire("k", 5)
    ttl = s.ttl("k")
    assert 0 < ttl <= 5


def test_expire_missing_key():
    s = Store()
    assert s.expire("nope", 5) == 0


def test_expiry_removes_key_on_read():
    s = Store()
    s.set("k", "v")
    s.expire("k", 1)
    # Force the expiry by manually jumping time
    time.sleep(1.1)
    assert s.get("k") is None
    assert s.exists("k") == 0
    assert s.ttl("k") == -2


def test_keys_skips_expired():
    s = Store()
    s.set("alive", "1")
    s.set("dead", "2")
    s.expire("dead", 1)
    time.sleep(1.1)
    assert s.keys() == ["alive"]
