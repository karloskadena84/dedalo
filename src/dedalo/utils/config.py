"""Configuración global de Dédalo."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEDALO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Directorio de datos del usuario
    data_dir: Path = Path.home() / ".dedalo"

    # Modelo LLM preferido
    llm_provider: str = "openai"  # openai | anthropic | ollama
    llm_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    # Seguridad
    encrypt_tokens: bool = True

    def ensure_data_dir(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "connectors").mkdir(exist_ok=True)
        (self.data_dir / "pipelines").mkdir(exist_ok=True)
        (self.data_dir / "cache").mkdir(exist_ok=True)
        (self.data_dir / "conversations").mkdir(exist_ok=True)
        return self.data_dir


settings = Settings()
