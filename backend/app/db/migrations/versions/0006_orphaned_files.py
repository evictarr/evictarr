"""orphaned_files

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

library_context_enum = sa.Enum("movies", "tv", name="library_context")
orphaned_status_enum = sa.Enum("open", "cleared", name="orphaned_status")


def upgrade() -> None:
    # op.create_table() creates these enum types itself as part of emitting
    # each column's DDL - see the note in 0002_integrations.py.
    op.create_table(
        "orphaned_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("path", sa.String(), nullable=False, unique=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("service_context", library_context_enum, nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", orphaned_status_enum, nullable=False, server_default="open"),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_orphaned_files_status", "orphaned_files", ["status"])


def downgrade() -> None:
    op.drop_index("ix_orphaned_files_status", table_name="orphaned_files")
    op.drop_table("orphaned_files")
    # op.drop_table() already drops each column's enum types with it.
