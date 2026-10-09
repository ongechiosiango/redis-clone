"""Command-line entry point for redis-clone."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys

from . import __version__
from .server import serve
from .store import Store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redis-clone",
        description="A tiny in-memory Redis clone that speaks RESP.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=6380, help="Port (default: 6380)")
    parser.add_argument("--version", action="version", version=f"redis-clone {__version__}")
    return parser


async def _run(host: str, port: int) -> None:
    store = Store()
    server = await serve(host=host, port=port, store=store)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(f"redis-clone {__version__} listening on {addrs}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        pass


def main() -> int:
    args = build_parser().parse_args()
    try:
        asyncio.run(_run(args.host, args.port))
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
