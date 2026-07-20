from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class BusinessConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_source_url: str
    min_cart_for_free_delivery: float
    free_delivery_radius_km: float
    delivery_time_minutes: int
    discount_percent: float
    payment_phone_number: str
    payment_upi_id: str
    extra_instructions: str | None


class BusinessConfigUpdate(BaseModel):
    menu_source_url: HttpUrl | None = None
    min_cart_for_free_delivery: float | None = Field(default=None, ge=0)
    free_delivery_radius_km: float | None = Field(default=None, ge=0)
    delivery_time_minutes: int | None = Field(default=None, gt=0)
    discount_percent: float | None = Field(default=None, ge=0, le=100)
    payment_phone_number: str | None = Field(default=None, min_length=10, max_length=15)
    payment_upi_id: str | None = Field(default=None, min_length=3, max_length=255)
    extra_instructions: str | None = Field(default=None, max_length=4000)
