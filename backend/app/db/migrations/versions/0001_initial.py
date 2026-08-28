"""initial schema: users, sessions, app_settings

Revision ID: 0001
Revises:
Create Date: 2026-08-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("totp_secret_encrypted", sa.String(), nullable=True),
        sa.Column("mfa_enrolled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="users_singleton"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheduler_time", sa.Time(), nullable=False, server_default="03:30:00"),
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
        sa.Column("default_grace_period_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("executor_interval_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("log_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="app_settings_singleton"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("users")
