"""add residual value to asset scrap

Revision ID: b3d8f2a6c1e5
Revises: a7c3e9f1b2d4
Create Date: 2026-10-27 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3d8f2a6c1e5"
down_revision: Union[str, Sequence[str], None] = "a7c3e9f1b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ast_asset_scraps",
        sa.Column("residual_value", sa.Numeric(precision=12, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ast_asset_scraps", "residual_value")
