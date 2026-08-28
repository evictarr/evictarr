"""auth_method column on app_settings

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite can't ALTER TABLE ADD CONSTRAINT directly - batch mode rebuilds
    # the table under the hood, which handles both the new column and the
    # CHECK constraint in one pass.
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.add_column(
            sa.Column("auth_method", sa.String(), nullable=False, server_default="none")
        )
        batch_op.create_check_constraint(
            "app_settings_auth_method_valid", "auth_method IN ('none', 'basic')"
        )


def downgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_constraint("app_settings_auth_method_valid", type_="check")
        batch_op.drop_column("auth_method")
