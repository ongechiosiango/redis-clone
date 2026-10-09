# Usage Guide

## Start the server

    redis-clone --port 6380

Options:

| Flag | Default | Description |
|------|---------|-------------|
| --host | 127.0.0.1 | Bind address |
| --port, -p | 6380 | Listen port |
| --version | | Print version and exit |

Use port 6380 (not 6379) so you do not collide with a real Redis server
that might be running on your machine.

## Talk to it with redis-cli

    redis-cli -p 6380

    PING
    SET name Kali
    GET name
    EXISTS name
    DEL name
    GET name
    SET greeting hello
    EXPIRE greeting 30
    TTL greeting
    KEYS *
    FLUSHALL

`redis-cli` speaks the wire protocol your server understands. Everything
you send is wrapped in a RESP array of bulk strings; everything you get
back is a RESP simple string, bulk string, integer, error, or array.

## Where things are stored

Nowhere on disk. The store is a Python dict in the running process. Kill
the process and the data is gone. That is intentional - this is a demo,
not a database.

## Expiry semantics

- `EXPIRE k N` sets a TTL of N seconds from now.
- `TTL k` returns:
  - `-2` if the key does not exist
  - `-1` if the key exists but has no TTL
  - a non-negative integer otherwise
- Expiry is **lazy**: a key is only removed from memory when it is
  accessed after its expiry time. This matches real Redis' read path.

## Tests

    pytest -v

The suite covers:
- RESP encoding and decoding (including incremental decode)
- The in-memory store, including expiry
- The dispatch layer (pure Python, no sockets)
- A full end-to-end test that starts a server and connects with a socket

## Caveats

- No persistence (no RDB, no AOF).
- No persistence means no replication.
- No transactions, no pub/sub, no scripting, no streams.
- No ACLs, no auth. Do not expose this to the internet.
