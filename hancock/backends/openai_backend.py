from __future__ import annotations

from typing import Any

import httpx

from hancock.backends.base import LLMBackend
from hancock.config import Settings


class OpenAIBackend(LLMBackend):
    name = "openai"
    base = "https://api.openai.com/v1"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.default_model = settings.openai_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base}/chat/completions", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    async def health(self) -> dict[str, Any]:
        return {
            "backend": self.name,
            "ok": bool(self.settings.openai_api_key),
            "model": self.default_model,
        }
