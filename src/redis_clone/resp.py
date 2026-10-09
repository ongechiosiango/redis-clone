"""RESP (Redis Serialization Protocol) encoder and decoder.

See https://redis.io/docs/reference/protocol-spec/ for the full spec.

Every message starts with a type byte:
    +    simple string   -> b"+OK\r\n"
    -    error           -> b"-ERR message\r\n"
    :    integer         -> b":42\r\n"
    $    bulk string     -> b"$5\r\nhello\r\n"
    *    array           -> b"*2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"

All values on the wire are UTF-8 encoded.
"""

from __future__ import annotations

from typing import Union

CRLF = b"\r\n"


class ProtocolError(Exception):
    """Raised when RESP input cannot be parsed."""


# --- Encoding -------------------------------------------------------------


def encode_simple_string(value: str) -> bytes:
    return b"+" + value.encode("utf-8") + CRLF


def encode_error(message: str) -> bytes:
    return b"-" + message.encode("utf-8") + CRLF


def encode_integer(value: int) -> bytes:
    return b":" + str(int(value)).encode("utf-8") + CRLF


def encode_bulk_string(value: Union[str, bytes, None]) -> bytes:
    if value is None:
        return b"$-1" + CRLF
    if isinstance(value, str):
        value = value.encode("utf-8")
    return b"$" + str(len(value)).encode("utf-8") + CRLF + value + CRLF


def encode_array(items) -> bytes:
    if items is None:
        return b"*-1" + CRLF
    out = [b"*" + str(len(items)).encode("utf-8") + CRLF]
    for item in items:
        out.append(encode_value(item))
    return b"".join(out)


def encode_value(value) -> bytes:
    """Encode a Python value as the most natural RESP type."""
    if isinstance(value, SimpleString):
        return encode_simple_string(str(value))
    if isinstance(value, bool):
        return encode_integer(1 if value else 0)
    if isinstance(value, int):
        return encode_integer(value)
    if isinstance(value, str):
        return encode_bulk_string(value)
    if isinstance(value, bytes):
        return encode_bulk_string(value)
    if value is None:
        return encode_bulk_string(None)
    if isinstance(value, (list, tuple)):
        return encode_array(list(value))
    raise TypeError(f"Cannot encode {type(value).__name__} to RESP")


# --- Decoding -------------------------------------------------------------


class RESPDecoder:
    """Incremental RESP decoder.

    Feed raw bytes with `feed()`. Then call `next_message()` repeatedly
    to pull out one decoded message at a time. Returns None when the
    buffer does not yet contain a complete message.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> None:
        self._buffer.extend(data)

    def _read_line(self, start: int):
        """Return (line_bytes, next_index) or (None, start) if incomplete."""
        idx = self._buffer.find(CRLF, start)
        if idx == -1:
            return None, start
        return bytes(self._buffer[start:idx]), idx + 2

    def next_message(self):
        """Return the next fully-parsed message, or None if more data needed."""
        if not self._buffer:
            return None
        try:
            value, consumed = self._parse_at(0)
        except _Incomplete:
            return None
        del self._buffer[:consumed]
        return value

    def _parse_at(self, pos: int):
        if pos >= len(self._buffer):
            raise _Incomplete()

        type_byte = self._buffer[pos:pos + 1]
        line_start = pos + 1

        line, next_pos = self._read_line(line_start)
        if line is None:
            raise _Incomplete()

        if type_byte == b"+":
            return line.decode("utf-8"), next_pos
        if type_byte == b"-":
            return ProtocolError(line.decode("utf-8")), next_pos
        if type_byte == b":":
            return int(line), next_pos
        if type_byte == b"$":
            return self._parse_bulk(line, next_pos)
        if type_byte == b"*":
            return self._parse_array(line, next_pos)

        raise ProtocolError(f"Unknown RESP type byte: {type_byte!r}")

    def _parse_bulk(self, length_line: bytes, pos: int):
        length = int(length_line)
        if length == -1:
            return None, pos
        end = pos + length
        if end + 2 > len(self._buffer):
            raise _Incomplete()
        payload = bytes(self._buffer[pos:end])
        # Skip trailing CRLF
        if bytes(self._buffer[end:end + 2]) != CRLF:
            raise ProtocolError("Bulk string missing trailing CRLF")
        return payload.decode("utf-8"), end + 2

    def _parse_array(self, count_line: bytes, pos: int):
        count = int(count_line)
        if count == -1:
            return None, pos
        items = []
        for _ in range(count):
            item, pos = self._parse_at(pos)
            items.append(item)
        return items, pos


class _Incomplete(Exception):
    """Internal: signals that more bytes are needed to finish parsing."""


class SimpleString(str):
    """Marker subclass of str that encodes as a RESP simple string (+...).

    Used for status replies like OK, PONG, and QUEUED where the spec
    requires a simple string rather than a bulk string.
    """
