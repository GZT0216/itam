"""org and rbac management fields

Revision ID: 9c2f4a71b8d3
Revises: 05f17b7064d7
Create Date: 2026-10-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9c2f4a71b8d3"
down_revision: Union[str, Sequence[str], None] = "05f17b7064d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sys_departments",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1", comment="乐观锁版本号"),
    )
    op.add_column("sys_users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_sys_users_deleted_at", "sys_users", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sys_users_deleted_at", table_name="sys_users")
    op.drop_column("sys_users", "deleted_at")
    op.drop_column("sys_departments", "version")
