"""business_config table (singleton runtime settings)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("menu_source_url", sa.String(2048), nullable=False),
        sa.Column("min_cart_for_free_delivery", sa.Numeric(10, 2), nullable=False),
        sa.Column("free_delivery_radius_km", sa.Numeric(6, 2), nullable=False),
        sa.Column("delivery_time_minutes", sa.Integer(), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("payment_phone_number", sa.String(32), nullable=False),
        sa.Column("payment_upi_id", sa.String(255), nullable=False),
        sa.Column("extra_instructions", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("business_config")
