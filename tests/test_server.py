"""End-to-end tests: start the server on a random port and connect with a socket."""

import asyncio
import socket

import pytest

from redis_clone.resp import RESPDecoder, encode_array
from redis_clone.server import dispatch, serve
from redis_clone.store import Store


# --- Pure dispatch tests (no network) ------------------------------------


def test_dispatch_ping():
    store = Store()
    out = dispatch(store, ["PING"])
    assert out == b"+PONG\r\n"


def test_dispatch_ping_with_message():
    store = Store()
    out = dispatch(store, ["PING", "hello"])
    assert out == b"$5\r\nhello\r\n"


def test_dispatch_set_then_get():
    store = Store()
    assert dispatch(store, ["SET", "k", "v"]) == b"+OK\r\n"
    assert dispatch(store, ["GET", "k"]) == b"$1\r\nv\r\n"


def test_dispatch_get_missing_returns_null():
    store = Store()
    assert dispatch(store, ["GET", "nope"]) == b"$-1\r\n"


def test_dispatch_del():
    store = Store()
    dispatch(store, ["SET", "k", "v"])
    assert dispatch(store, ["DEL", "k"]) == b":1\r\n"
    assert dispatch(store, ["DEL", "k"]) == b":0\r\n"


def test_dispatch_unknown_command():
    store = Store()
    out = dispatch(store, ["NOPE"])
    assert out.startswith(b"-ERR unknown command")


def test_dispatch_wrong_arg_count():
    store = Store()
    out = dispatch(store, ["GET"])
    assert out.startswith(b"-ERR wrong number of arguments")


def test_dispatch_flushall():
    store = Store()
    dispatch(store, ["SET", "a", "1"])
    dispatch(store, ["SET", "b", "2"])
    assert dispatch(store, ["FLUSHALL"]) == b"+OK\r\n"
    assert store.keys() == []


# --- Real socket tests ---------------------------------------------------


def _free_port() -> int:
    """Grab an unused localhost port."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def _send_recv(host: str, port: int, payload: bytes) -> bytes:
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(payload)
    await writer.drain()
    # Read just enough for a typical reply
    data = await asyncio.wait_for(reader.read(4096), timeout=3.0)
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass
    return data


@pytest.mark.asyncio
async def test_server_ping_over_socket():
    port = _free_port()
    server = await serve(host="127.0.0.1", port=port, store=Store())
    try:
        async with server:
            reply = await _send_recv("127.0.0.1", port, encode_array(["PING"]))
            assert reply == b"+PONG\r\n"
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_server_set_get_over_socket():
    port = _free_port()
    server = await serve(host="127.0.0.1", port=port, store=Store())
    try:
        async with server:
            set_reply = await _send_recv(
                "127.0.0.1", port, encode_array(["SET", "name", "Kali"])
            )
            assert set_reply == b"+OK\r\n"

            get_reply = await _send_recv(
                "127.0.0.1", port, encode_array(["GET", "name"])
            )
            assert get_reply == b"$4\r\nKali\r\n"
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_server_pipelining():
    """Two commands in one TCP packet should both be handled."""
    port = _free_port()
    server = await serve(host="127.0.0.1", port=port, store=Store())
    try:
        async with server:
            payload = encode_array(["SET", "x", "1"]) + encode_array(["GET", "x"])
            reply = await _send_recv("127.0.0.1", port, payload)
            assert reply == b"+OK\r\n$1\r\n1\r\n"
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_server_unknown_command():
    port = _free_port()
    server = await serve(host="127.0.0.1", port=port, store=Store())
    try:
        async with server:
            reply = await _send_recv(
                "127.0.0.1", port, encode_array(["BOGUS"])
            )
            assert reply.startswith(b"-ERR unknown command")
    finally:
        server.close()
        await server.wait_closed()
