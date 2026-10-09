# Redis Clone

[![CI](https://github.com/ongechiosiango/redis-clone/actions/workflows/ci.yml/badge.svg)](https://github.com/ongechiosiango/redis-clone/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)

A tiny in-memory Redis clone that speaks the **real RESP protocol**.

## What this is

A ~500-line Python server that listens on a TCP socket and speaks enough of
the Redis wire protocol to be driven by the real `redis-cli`. It is **not**
a production Redis replacement - it is a teaching project that demonstrates:

- RESP parsing (incremental, byte-level, handles split packets)
- An asyncio TCP server
- A thread-safe in-memory key-value store with lazy expiry
- A clean command dispatch layer

## Supported commands

| Command | Example | Notes |
|---------|---------|-------|
| `PING` | `PING` | replies `PONG` |
| `PING <msg>` | `PING hello` | echoes the message |
| `ECHO <msg>` | `ECHO hi` | returns the message |
| `SET <k> <v>` | `SET name Kali` | overwrites |
| `GET <k>` | `GET name` | `(nil)` if missing |
| `DEL <k> [k ...]` | `DEL a b` | integer count deleted |
| `EXISTS <k> [k ...]` | `EXISTS name` | integer count present |
| `EXPIRE <k> <sec>` | `EXPIRE k 60` | 1 if key exists, 0 otherwise |
| `TTL <k>` | `TTL k` | seconds left, -1 if no TTL, -2 if missing |
| `KEYS <pattern>` | `KEYS *` | prefix globs supported |
| `FLUSHALL` | `FLUSHALL` | wipes everything |

## Quick start

    python3 -m venv venv
    source venv/bin/activate
    pip install -e ".[dev]"

Start the server (use port 6380 so you do not collide with real Redis on 6379):

    redis-clone --port 6380

In another terminal, talk to it with the real Redis client:

    redis-cli -p 6380
    127.0.0.1:6380> PING
    PONG
    127.0.0.1:6380> SET name Kali
    OK
    127.0.0.1:6380> GET name
    "Kali"

See docs/usage.md for a full walkthrough.

## Design notes

- **RESP is incremental.** The decoder holds partial bytes until a full
  message arrives, so a message can be split across TCP reads.
- **Pipelining works for free.** Multiple commands in one packet are all
  decoded and answered in order.
- **Errors never crash the server.** Command failures are turned into RESP
  error replies (`-ERR ...`), including unknown commands and wrong arity.
- **Money is NOT involved, but bytes are.** All values are UTF-8 strings.
  There is no persistence, no replication, no cluster - just one process
  holding a dict.

## Development

    pip install -e ".[dev]"
    pytest -v

## Contributing

See CONTRIBUTING.md.

## License

MIT - see LICENSE.
