from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

REQUESTS = Counter("hancock_requests_total", "Total API requests", ["endpoint", "mode"])
ERRORS = Counter("hancock_errors_total", "Total API errors", ["endpoint"])


def metrics_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
