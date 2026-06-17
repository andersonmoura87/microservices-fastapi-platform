from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    user_service_url: str = "http://user-service:8001"
    data_service_url: str = "http://data-service:8002"
    log_level: str = "INFO"
    upstream_timeout: float = 10.0

    redis_url: str = "redis://redis:6379/0"
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60


settings = Settings()
