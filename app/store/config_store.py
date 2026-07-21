import dataclasses
import json
from pathlib import Path

from app.config import Settings
from app.store.models import BusinessConfig

_DEFAULTS = BusinessConfig(
    business_name="The Dessert Zone",
    menu_source_url=(
        "https://www.swiggy.com/city/gurgaon/"
        "the-dessert-zone-omaxe-mall-new-sohna-road-rest624899"
    ),
    min_cart_for_free_delivery=300.0,
    free_delivery_radius_km=7.0,
    delivery_time_minutes=120,
    discount_percent=25.0,
    payment_phone_number="7479219293",
    payment_upi_id="7479219293@paytm",
    delivery_fee=75.0,
    accepted_receiver_names="Kouzina Kafe, Seema Gautam, Siddhant Gautam, Siddharth Gautam",
    cart_reminder_minutes=3.0,
    extra_instructions=None,
)


class ConfigStore:
    """File-backed replacement for the old `business_config` DB table.
    Everything an admin might change at runtime (menu source, delivery/
    discount rules, payment details, extra instructions) lives in this
    JSON file — never hardcode these elsewhere.
    """

    def __init__(self, settings: Settings) -> None:
        self._path: Path = settings.business_config_file_path

    def load(self) -> BusinessConfig:
        if not self._path.exists():
            self.save(_DEFAULTS)
            return _DEFAULTS

        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return BusinessConfig(**{**dataclasses.asdict(_DEFAULTS), **raw})

    def save(self, config: BusinessConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(dataclasses.asdict(config), indent=2), encoding="utf-8"
        )

    def update(self, **fields) -> BusinessConfig:
        current = self.load()
        updated = dataclasses.replace(
            current, **{k: v for k, v in fields.items() if v is not None}
        )
        self.save(updated)
        return updated
