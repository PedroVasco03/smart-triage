"""Configuração da aplicação via variáveis de ambiente (ficheiro .env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Smart Triage - Agente Baseado em Utilidade"
    # Sem credenciais por defeito: define DATABASE_URL no .env (MySQL).
    database_url: str = "sqlite:///./smart_triage_dev.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Origens locais e de rede privada (qualquer porta): útil quando a página é aberta por 127.0.0.1 ou pelo IP da rede.
    cors_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|[\w-]+\.local)(:\d+)?$"
    sql_echo: bool = False
    auto_create_tables: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
