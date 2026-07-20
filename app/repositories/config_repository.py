from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_config import BusinessConfig

_DEFAULTS = dict(
    menu_source_url=(
        "https://www.swiggy.com/city/gurgaon/"
        "warmoven-cake-and-desserts-sector-49-sohna-road-rest1296665"
    ),
    min_cart_for_free_delivery=300.0,
    free_delivery_radius_km=7.0,
    delivery_time_minutes=120,
    discount_percent=25.0,
    payment_phone_number="7479219293",
    payment_upi_id="7479219293@paytm",
    extra_instructions=None,
)


class ConfigRepository:
    """Access to the single BusinessConfig row. Everything the bot and
    scraper need to know that an admin might change at runtime (menu
    source, delivery/discount rules, payment details, extra instructions)
    lives here — never hardcode these elsewhere.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> BusinessConfig:
        result = await self._session.execute(select(BusinessConfig).limit(1))
        config = result.scalar_one_or_none()
        if config is None:
            config = BusinessConfig(**_DEFAULTS)
            self._session.add(config)
            await self._session.flush()
        return config

    async def update(self, **fields) -> BusinessConfig:
        config = await self.get()
        for key, value in fields.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)
        await self._session.flush()
        return config
