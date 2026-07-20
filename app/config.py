from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    groq_api_key: str
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"

    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    order_phone_number: str = "7015943285"
    custom_cake_phone_number: str = "7015943285"
    bulk_order_phone_number: str = "7777777777"

    business_hours: tuple[tuple[int, int], ...] = ((0, 5), (9, 12))

    requests_ca_bundle: str | None = None
    dev_disable_ssl_verify: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
