"""integrations table, seeded with the 4 known services

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

service_name_enum = sa.Enum("jellyfin", "seerr", "radarr", "sonarr", name="service_name")
test_status_enum = sa.Enum("unknown", "ok", "failed", name="test_status")


def upgrade() -> None:
    # op.create_table() below creates these enum types itself (as part of
    # emitting the column DDL) - calling .create() here too would try to
    # create them twice and crash on real Postgres (SQLite silently ignores
    # the duplicate since it has no native enum type, which is why this only
    # showed up when testing against Postgres).
    op.create_table(
        "integrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service", service_name_enum, nullable=False, unique=True),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("api_key_encrypted", sa.String(), nullable=True),
        sa.Column("extra_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_test_status", test_status_enum, nullable=False, server_default="unknown"),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_detail", sa.String(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    integrations_table = sa.table(
        "integrations",
        sa.column("service", service_name_enum),
        sa.column("extra_config", sa.JSON()),
    )
    op.bulk_insert(
        integrations_table,
        [
            {"service": "jellyfin", "extra_config": {}},
            {"service": "seerr", "extra_config": {}},
            {"service": "radarr", "extra_config": {}},
            {"service": "sonarr", "extra_config": {}},
        ],
    )


def downgrade() -> None:
    op.drop_table("integrations")
    # op.drop_table() already drops the enum types along with it - see the
    # note in upgrade().
