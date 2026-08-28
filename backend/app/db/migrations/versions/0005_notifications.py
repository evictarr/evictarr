"""notification_config, seeded with discord and telegram

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

notification_provider_enum = sa.Enum("discord", "telegram", name="notification_provider")


def upgrade() -> None:
    # op.create_table() creates this enum type itself as part of emitting
    # the column DDL - see the note in 0002_integrations.py.
    op.create_table(
        "notification_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", notification_provider_enum, nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("notify_on_stage", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_on_execute", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_daily_summary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    notification_config_table = sa.table(
        "notification_config",
        sa.column("provider", notification_provider_enum),
        sa.column("config", sa.JSON()),
    )
    op.bulk_insert(
        notification_config_table,
        [
            {"provider": "discord", "config": {}},
            {"provider": "telegram", "config": {}},
        ],
    )


def downgrade() -> None:
    op.drop_table("notification_config")
    # op.drop_table() already drops the enum type with it.
