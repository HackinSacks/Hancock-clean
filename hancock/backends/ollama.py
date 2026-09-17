from __future__ import annotations

from typing import Any

import httpx

from hancock.backends.base import LLMBackend
from hancock.config import Settings


class OllamaBackend(LLMBackend):
    name = "ollama"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base = settings.ollama_base_url.rstrip("/")
        self.default_model = settings.ollama_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        return (data.get("message") or {}).get("content") or data.get("response") or ""

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base}/api/tags")
                ok = r.status_code == 200
                models = [m.get("name") for m in (r.json().get("models") or [])] if ok else []
            return {"backend": self.name, "ok": ok, "models": models}
        except Exception as exc:
            return {"backend": self.name, "ok": False, "error": str(exc)}
