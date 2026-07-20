import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BusinessConfig(Base):
    """Singleton table (one row) holding admin-configurable business
    settings. Edited through the Configure page / PUT /config API —
    never hardcode these values elsewhere in the app.
    """

    __tablename__ = "business_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    menu_source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    min_cart_for_free_delivery: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    free_delivery_radius_km: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    delivery_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    payment_phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_upi_id: Mapped[str] = mapped_column(String(255), nullable=False)
    extra_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
