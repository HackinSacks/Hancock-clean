from __future__ import annotations

import argparse
import asyncio

import uvicorn

from hancock.config import get_settings
from hancock.modes import normalize_mode, system_prompt
from hancock.backends import get_backend


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hancock", description="CyberViser Hancock")
    p.add_argument("--server", action="store_true", help="Start FastAPI server")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument("--ask", type=str, default=None, help="One-shot question")
    p.add_argument("--mode", default="auto")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    if args.server:
        host = args.host or settings.hancock_host
        port = args.port or settings.hancock_port
        print(f"[CyberViser] Hancock API starting on {host}:{port}")
        uvicorn.run("hancock.api.app:app", host=host, port=port, reload=False)
        return 0
    if args.ask:
        mode = normalize_mode(args.mode)
        backend = get_backend(settings)

        async def _run() -> str:
            return await backend.chat(
                [
                    {"role": "system", "content": system_prompt(mode)},
                    {"role": "user", "content": args.ask},
                ]
            )

        print(asyncio.run(_run()))
        return 0
    build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
