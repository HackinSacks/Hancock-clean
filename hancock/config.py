from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BackendName = Literal["ollama", "nvidia", "openai"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    hancock_llm_backend: BackendName = "ollama"
    hancock_host: str = "0.0.0.0"
    hancock_port: int = 5000
    hancock_api_key: str = ""
    hancock_rate_limit: int = 60

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_coder_model: str = "qwen2.5-coder:7b"

    nvidia_api_key: str = ""
    hancock_model: str = "mistralai/mistral-7b-instruct-v0.3"
    hancock_coder_model: str = "qwen/qwen2.5-coder-32b-instruct"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_coder_model: str = "gpt-4o"

    hancock_webhook_secret: str = ""
    hancock_slack_webhook: str = ""
    hancock_teams_webhook: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
