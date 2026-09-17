from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

from hancock.config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_s: float = 60.0) -> None:
        now = time.time()
        q = self._hits[key]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        q.append(now)


rate_limiter = RateLimiter()


async def require_auth(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    client = request.client.host if request.client else "unknown"
    rate_limiter.check(client, settings.hancock_rate_limit)
    expected = (settings.hancock_api_key or "").strip()
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: Bearer token required")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
