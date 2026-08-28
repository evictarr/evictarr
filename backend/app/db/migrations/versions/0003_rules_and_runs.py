"""rules, runs, run_events

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

rule_type_enum = sa.Enum(
    "movie_watched_cleanup", "series_watched_cleanup", "stale_request_cleanup", "orphaned_scan", name="rule_type"
)
threshold_unit_enum = sa.Enum("hours", "days", "weeks", "months", "years", name="threshold_unit")
series_granularity_enum = sa.Enum("series", "season", name="series_granularity")
run_type_enum = sa.Enum("scheduled", "manual", name="run_type")
run_status_enum = sa.Enum("running", "completed", "failed", name="run_status")
event_level_enum = sa.Enum("match", "skip", "error", name="event_level")


def upgrade() -> None:
    # op.create_table() creates these enum types itself as part of emitting
    # each column's DDL - see the note in 0002_integrations.py.
    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("rule_type", rule_type_enum, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("threshold_value", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("threshold_unit", threshold_unit_enum, nullable=False, server_default="days"),
        sa.Column("granularity", series_granularity_enum, nullable=True),
        sa.Column("exempt_favorite", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_type", run_type_enum, nullable=False),
        sa.Column("triggered_by", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", run_status_enum, nullable=False, server_default="running"),
        sa.Column("items_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_matched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_skipped", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("rules.id"), nullable=True),
        sa.Column("level", event_level_enum, nullable=False),
        sa.Column("media_title", sa.String(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_events_run_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_table("runs")
    op.drop_table("rules")
    # op.drop_table() already drops each table's own enum types with it.
