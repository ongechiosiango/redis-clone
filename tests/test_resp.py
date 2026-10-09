"""Tests for RESP encoding and decoding."""

import pytest

from redis_clone.resp import (
    ProtocolError,
    RESPDecoder,
    encode_array,
    encode_bulk_string,
    encode_error,
    encode_integer,
    encode_simple_string,
    encode_value,
)


def test_encode_simple_string():
    assert encode_simple_string("OK") == b"+OK\r\n"


def test_encode_error():
    assert encode_error("ERR bad") == b"-ERR bad\r\n"


def test_encode_integer():
    assert encode_integer(42) == b":42\r\n"
    assert encode_integer(-1) == b":-1\r\n"


def test_encode_bulk_string():
    assert encode_bulk_string("hello") == b"$5\r\nhello\r\n"


def test_encode_bulk_string_empty():
    assert encode_bulk_string("") == b"$0\r\n\r\n"


def test_encode_bulk_string_null():
    assert encode_bulk_string(None) == b"$-1\r\n"


def test_encode_array_of_bulk_strings():
    encoded = encode_array(["SET", "k", "v"])
    assert encoded == b"*3\r\n$3\r\nSET\r\n$1\r\nk\r\n$1\r\nv\r\n"


def test_encode_value_dispatches_by_type():
    assert encode_value(5) == b":5\r\n"
    assert encode_value("hi") == b"$2\r\nhi\r\n"
    assert encode_value(None) == b"$-1\r\n"
    assert encode_value(["a"]) == b"*1\r\n$1\r\na\r\n"


def test_decode_simple_string():
    d = RESPDecoder()
    d.feed(b"+OK\r\n")
    assert d.next_message() == "OK"


def test_decode_integer():
    d = RESPDecoder()
    d.feed(b":100\r\n")
    assert d.next_message() == 100


def test_decode_bulk_string():
    d = RESPDecoder()
    d.feed(b"$5\r\nhello\r\n")
    assert d.next_message() == "hello"


def test_decode_array():
    d = RESPDecoder()
    d.feed(b"*3\r\n$3\r\nSET\r\n$1\r\nk\r\n$1\r\nv\r\n")
    assert d.next_message() == ["SET", "k", "v"]


def test_decode_incremental():
    """Simulate a TCP read that splits a message across packets."""
    d = RESPDecoder()
    d.feed(b"*2\r\n$3\r\nGE")
    assert d.next_message() is None
    d.feed(b"T\r\n$3\r\nfoo\r\n")
    assert d.next_message() == ["GET", "foo"]


def test_decode_multiple_messages_from_one_feed():
    d = RESPDecoder()
    d.feed(b"+OK\r\n:1\r\n$3\r\nabc\r\n")
    assert d.next_message() == "OK"
    assert d.next_message() == 1
    assert d.next_message() == "abc"
    assert d.next_message() is None


def test_decode_null_bulk_string():
    d = RESPDecoder()
    d.feed(b"$-1\r\n")
    assert d.next_message() is None


def test_encode_value_simple_string():
    from redis_clone.resp import SimpleString
    assert encode_value(SimpleString("OK")) == b"+OK\r\n"
    assert encode_value(SimpleString("PONG")) == b"+PONG\r\n"


def test_simple_string_is_a_str():
    from redis_clone.resp import SimpleString
    s = SimpleString("hello")
    assert isinstance(s, str)
    assert s == "hello"
    assert s.upper() == "HELLO"
