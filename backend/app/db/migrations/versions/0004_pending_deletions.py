"""pending_deletions, action_log

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pending_media_type_enum = sa.Enum("movie", "series", "season", name="pending_media_type")
pending_status_enum = sa.Enum("pending", "cancelled", "executing", "completed", "failed", name="pending_status")
system_status_enum = sa.Enum("success", "failed", "skipped", name="system_status")
overall_status_enum = sa.Enum("success", "partial_failure", "failed", name="overall_status")


def upgrade() -> None:
    # op.create_table() creates these enum types itself as part of emitting
    # each column's DDL - see the note in 0002_integrations.py. system_status
    # is reused across three columns in action_log below; SQLAlchemy
    # deduplicates repeated use of the same Enum object within one table so
    # this only emits one CREATE TYPE for it.
    op.create_table(
        "pending_deletions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("rules.id"), nullable=True),
        sa.Column("media_type", pending_media_type_enum, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("external_ids", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("dedupe_key", sa.String(), nullable=False),
        sa.Column("staged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("grace_period_hours", sa.Integer(), nullable=False),
        sa.Column("execute_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", pending_status_enum, nullable=False, server_default="pending"),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_reason", sa.String(), nullable=True),
    )
    op.create_index("ix_pending_deletions_dedupe_key", "pending_deletions", ["dedupe_key"])
    op.create_index("ix_pending_deletions_execute_after", "pending_deletions", ["execute_after"])

    op.create_table(
        "action_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pending_deletion_id", sa.Integer(), sa.ForeignKey("pending_deletions.id"), nullable=False),
        sa.Column("seerr_status", system_status_enum, nullable=True),
        sa.Column("radarr_sonarr_status", system_status_enum, nullable=True),
        sa.Column("disk_status", system_status_enum, nullable=True),
        sa.Column("overall_status", overall_status_enum, nullable=False),
        sa.Column("error_detail", sa.JSON(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_action_log_pending_deletion_id", "action_log", ["pending_deletion_id"])


def downgrade() -> None:
    op.drop_index("ix_action_log_pending_deletion_id", table_name="action_log")
    op.drop_table("action_log")
    op.drop_index("ix_pending_deletions_execute_after", table_name="pending_deletions")
    op.drop_index("ix_pending_deletions_dedupe_key", table_name="pending_deletions")
    op.drop_table("pending_deletions")
    # op.drop_table() already drops each table's own enum types with it.
