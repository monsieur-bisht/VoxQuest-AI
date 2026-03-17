from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    whisper_model_size: str = "base"
    tts_engine: str = "gtts"
    llm_provider: str = "openai"
    llm_model: str = "gpt-3.5-turbo"
    data_dir: str = "./data"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    max_audio_size_mb: int = 25
    session_secret_key: str = "changeme-secret-key"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def max_audio_size_bytes(self) -> int:
        return self.max_audio_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
