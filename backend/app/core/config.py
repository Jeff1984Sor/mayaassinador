"""Configuracao central da aplicacao, carregada do .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Aplicacao ----
    APP_NAME: str = "MayaAssinador"
    APP_ENV: str = "production"
    DEBUG: bool = False

    # ---- Banco ----
    DATABASE_URL: str

    # ---- Seguranca ----
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Chave Fernet usada para criptografar a senha SMTP no banco (F2)
    FERNET_KEY: str

    # ---- Storage ----
    STORAGE_ROOT: Path = Path("/var/mayaassinador/storage")
    MAX_UPLOAD_MB: int = 20

    # ---- Pipeline de documentos (F3) ----
    SOFFICE_BIN: str = "/usr/bin/soffice"
    SOFFICE_TIMEOUT: int = 120
    WORKER_CONCURRENCY: int = 1
    WORKER_POLL_SECONDS: int = 3

    # ---- URLs / CORS ----
    PUBLIC_BASE_URL: str = "http://localhost:3030"
    CORS_ORIGINS: str = "http://localhost:3030"

    # ---- Servidor ----
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8030

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS vem como string separada por virgula no .env."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
