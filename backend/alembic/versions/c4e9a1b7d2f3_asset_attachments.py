"""asset image and attachment upload

Revision ID: c4e9a1b7d2f3
Revises: b3d8f2a6c1e5
Create Date: 2026-10-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e9a1b7d2f3"
down_revision: Union[str, Sequence[str], None] = "b3d8f2a6c1e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ast_asset_attachments",
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("uploaded_by_id", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_by_name", sa.String(length=80), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["ast_assets.id"],
            name="fk_ast_asset_attachments_asset_id_ast_assets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["sys_users.id"],
            name="fk_ast_asset_attachments_uploaded_by_id_sys_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ast_asset_attachments"),
        sa.UniqueConstraint(
            "stored_name", name="uq_ast_asset_attachments_stored_name"
        ),
    )
    op.create_index(
        "ix_ast_asset_attachments_asset_id",
        "ast_asset_attachments",
        ["asset_id"],
    )
    op.create_index(
        "ix_ast_asset_attachments_deleted_at",
        "ast_asset_attachments",
        ["deleted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ast_asset_attachments_deleted_at",
        table_name="ast_asset_attachments",
    )
    op.drop_index(
        "ix_ast_asset_attachments_asset_id",
        table_name="ast_asset_attachments",
    )
    op.drop_table("ast_asset_attachments")
