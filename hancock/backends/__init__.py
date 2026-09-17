from __future__ import annotations

from hancock.backends.base import LLMBackend
from hancock.backends.nvidia import NvidiaBackend
from hancock.backends.ollama import OllamaBackend
from hancock.backends.openai_backend import OpenAIBackend
from hancock.config import Settings, get_settings


def get_backend(settings: Settings | None = None) -> LLMBackend:
    s = settings or get_settings()
    if s.hancock_llm_backend == "nvidia":
        return NvidiaBackend(s)
    if s.hancock_llm_backend == "openai":
        return OpenAIBackend(s)
    return OllamaBackend(s)


__all__ = ["LLMBackend", "get_backend", "OllamaBackend", "NvidiaBackend", "OpenAIBackend"]
