"""Async TCP server that speaks RESP and dispatches commands."""

from __future__ import annotations

import asyncio

from .resp import (
    RESPDecoder,
    ProtocolError,
    SimpleString,
    encode_error,
    encode_value,
)
from .store import Store


class CommandError(Exception):
    """Raised by a command handler to signal an error response."""


# --- Command handlers -----------------------------------------------------
# Each handler has signature (store, *args) -> Python value.
# The value is then encoded with encode_value().


def cmd_ping(store, *args):
    if len(args) == 0:
        return SimpleString("PONG")
    if len(args) == 1:
        return args[0]
    raise CommandError("ERR wrong number of arguments for 'ping' command")


def cmd_echo(store, *args):
    if len(args) != 1:
        raise CommandError("ERR wrong number of arguments for 'echo' command")
    return args[0]


def cmd_set(store, *args):
    if len(args) < 2:
        raise CommandError("ERR wrong number of arguments for 'set' command")
    store.set(args[0], args[1])
    return SimpleString("OK")


def cmd_get(store, *args):
    if len(args) != 1:
        raise CommandError("ERR wrong number of arguments for 'get' command")
    return store.get(args[0])


def cmd_del(store, *args):
    if len(args) < 1:
        raise CommandError("ERR wrong number of arguments for 'del' command")
    return sum(store.delete(k) for k in args)


def cmd_exists(store, *args):
    if len(args) < 1:
        raise CommandError("ERR wrong number of arguments for 'exists' command")
    return sum(store.exists(k) for k in args)


def cmd_expire(store, *args):
    if len(args) != 2:
        raise CommandError("ERR wrong number of arguments for 'expire' command")
    try:
        seconds = int(args[1])
    except ValueError:
        raise CommandError("ERR value is not an integer or out of range")
    return store.expire(args[0], seconds)


def cmd_ttl(store, *args):
    if len(args) != 1:
        raise CommandError("ERR wrong number of arguments for 'ttl' command")
    return store.ttl(args[0])


def cmd_keys(store, *args):
    pattern = args[0] if args else "*"
    if pattern == "*":
        return store.keys()
    # Simple glob: only support prefix matching with trailing *
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        return [k for k in store.keys() if k.startswith(prefix)]
    return [k for k in store.keys() if k == pattern]


def cmd_flushall(store, *args):
    store.flushall()
    return SimpleString("OK")


COMMANDS = {
    "PING": cmd_ping,
    "ECHO": cmd_echo,
    "SET": cmd_set,
    "GET": cmd_get,
    "DEL": cmd_del,
    "EXISTS": cmd_exists,
    "EXPIRE": cmd_expire,
    "TTL": cmd_ttl,
    "KEYS": cmd_keys,
    "FLUSHALL": cmd_flushall,
}


def dispatch(store: Store, message) -> bytes:
    """Given a decoded RESP message, return RESP-encoded response bytes."""
    if not isinstance(message, list) or not message:
        return encode_error("ERR empty or invalid command")

    parts = [str(x) for x in message]
    name = parts[0].upper()
    args = parts[1:]

    handler = COMMANDS.get(name)
    if handler is None:
        return encode_error(f"ERR unknown command '{parts[0]}'")

    try:
        result = handler(store, *args)
    except CommandError as exc:
        return encode_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        return encode_error(f"ERR internal error: {exc}")

    return encode_value(result)


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, store: Store):
    decoder = RESPDecoder()
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            decoder.feed(data)

            while True:
                try:
                    message = decoder.next_message()
                except ProtocolError as exc:
                    writer.write(encode_error(f"ERR protocol error: {exc}"))
                    await writer.drain()
                    return
                if message is None:
                    break

                if isinstance(message, ProtocolError):
                    writer.write(encode_error(f"ERR {message}"))
                    await writer.drain()
                    continue

                response = dispatch(store, message)
                writer.write(response)
                await writer.drain()

    except (ConnectionResetError, asyncio.IncompleteReadError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


async def serve(host: str = "127.0.0.1", port: int = 6380, store: Store = None):
    """Start the server. Returns the asyncio.Server object."""
    if store is None:
        store = Store()

    server = await asyncio.start_server(
        lambda r, w: _handle_client(r, w, store),
        host=host,
        port=port,
    )
    return server
