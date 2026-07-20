from dataclasses import dataclass


@dataclass(frozen=True)
class MenuItem:
    name: str
    description: str | None
    price: float
    category: str | None
    image_url: str | None
    is_available: bool = True


@dataclass(frozen=True)
class BusinessConfig:
    business_name: str
    menu_source_url: str
    min_cart_for_free_delivery: float
    free_delivery_radius_km: float
    delivery_time_minutes: int
    discount_percent: float
    payment_phone_number: str
    payment_upi_id: str
    extra_instructions: str | None = None
