"""stage 1 schema: menu_items, feedback, chat_history

Revision ID: 0001
Revises:
Create Date: 2026-07-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "menu_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_id", sa.String(255), nullable=True, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_menu_items_name", "menu_items", ["name"])
    op.create_index("ix_menu_items_source_id", "menu_items", ["source_id"])

    feedback_platform = postgresql.ENUM(
        "swiggy", "zomato", "other", name="feedback_platform"
    )
    feedback_platform.create(op.get_bind(), checkfirst=True)
    feedback_platform_column = postgresql.ENUM(
        "swiggy", "zomato", "other", name="feedback_platform", create_type=False
    )

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=True),
        sa.Column("platform", feedback_platform_column, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_feedback_order_id", "feedback", ["order_id"])
    op.create_index("ix_feedback_conversation_id", "feedback", ["conversation_id"])

    message_role = postgresql.ENUM("user", "assistant", name="message_role")
    message_role.create(op.get_bind(), checkfirst=True)
    message_role_column = postgresql.ENUM(
        "user", "assistant", name="message_role", create_type=False
    )

    op.create_table(
        "chat_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("role", message_role_column, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("detected_language", sa.String(16), nullable=True),
        sa.Column("intent", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chat_history_conversation_id", "chat_history", ["conversation_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_chat_history_conversation_id", table_name="chat_history")
    op.drop_table("chat_history")
    postgresql.ENUM(name="message_role").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_feedback_conversation_id", table_name="feedback")
    op.drop_index("ix_feedback_order_id", table_name="feedback")
    op.drop_table("feedback")
    postgresql.ENUM(name="feedback_platform").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_menu_items_source_id", table_name="menu_items")
    op.drop_index("ix_menu_items_name", table_name="menu_items")
    op.drop_table("menu_items")
