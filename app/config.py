from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    groq_api_key: str
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    # Small/fast text model used to structure OCR'd payment screenshot
    # text into JSON — no vision model involved (see app/services/
    # ocr_service.py + app/agent/tools/payment_tool.py).
    groq_instant_model: str = "llama-3.1-8b-instant"

    order_phone_number: str = "7015943285"
    custom_cake_phone_number: str = "7015943285"
    bulk_order_phone_number: str = "7777777777"

    # Hours the business is CLOSED (as (start_hour, end_hour) 24h tuples).
    # Default: closed 5AM-9AM, open the other 20 hours of the day.
    business_closed_hours: tuple[tuple[int, int], ...] = ((5, 9),)

    menu_file_path: Path = REPO_ROOT / "data" / "menu.json"
    business_config_file_path: Path = REPO_ROOT / "data" / "business_config.json"

    # SMTP (Gmail) — used to email feedback instead of storing it.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    feedback_email_to: str = "gsiddhant947@gmail.com"

    requests_ca_bundle: str | None = None
    dev_disable_ssl_verify: bool = False

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_username and self.smtp_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()
