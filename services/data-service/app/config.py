from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://platform:changeme@localhost/platform"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300
    log_level: str = "INFO"

    # Bump this whenever the cache value shape or the underlying schema changes,
    # so stale entries from a previous deploy are never served.
    cache_version: str = "v1"


settings = Settings()
