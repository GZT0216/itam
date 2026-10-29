"""asset inbound base code and per-unit asset codes

Revision ID: a4d8f2c6b1e9
Revises: b6c9e4a72d18
Create Date: 2026-10-22 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4d8f2c6b1e9"
down_revision: Union[str, Sequence[str], None] = "b6c9e4a72d18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ast_asset_inbound_items") as batch_op:
        batch_op.add_column(
            sa.Column("base_asset_no", sa.String(length=40), nullable=True)
        )

    op.create_table(
        "ast_asset_code_sequences",
        sa.Column("base_key", sa.String(length=40), nullable=False),
        sa.Column("last_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("base_key", name=op.f("pk_ast_asset_code_sequences")),
    )

    op.create_table(
        "ast_asset_inbound_codes",
        sa.Column("inbound_id", sa.BigInteger(), nullable=False),
        sa.Column("item_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_no", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["inbound_id"],
            ["ast_asset_inbounds.id"],
            name=op.f("fk_ast_asset_inbound_codes_inbound_id_ast_asset_inbounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["ast_asset_inbound_items.id"],
            name=op.f("fk_ast_asset_inbound_codes_item_id_ast_asset_inbound_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_inbound_codes")),
        sa.UniqueConstraint(
            "asset_no", name=op.f("uq_ast_asset_inbound_codes_asset_no")
        ),
    )
    op.create_index(
        "ix_ast_asset_inbound_codes_inbound_id",
        "ast_asset_inbound_codes",
        ["inbound_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_asset_inbound_codes_item_id",
        "ast_asset_inbound_codes",
        ["item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ast_asset_inbound_codes_item_id",
        table_name="ast_asset_inbound_codes",
    )
    op.drop_index(
        "ix_ast_asset_inbound_codes_inbound_id",
        table_name="ast_asset_inbound_codes",
    )
    op.drop_table("ast_asset_inbound_codes")
    op.drop_table("ast_asset_code_sequences")

    with op.batch_alter_table("ast_asset_inbound_items") as batch_op:
        batch_op.drop_column("base_asset_no")
