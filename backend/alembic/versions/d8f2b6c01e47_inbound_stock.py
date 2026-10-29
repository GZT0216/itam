"""asset inbound and stock safety threshold

Revision ID: d8f2b6c01e47
Revises: c7e1a4d92b30
Create Date: 2026-10-22 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8f2b6c01e47"
down_revision: Union[str, Sequence[str], None] = "c7e1a4d92b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "ast_asset_inbounds",
        sa.Column("inbound_no", sa.String(length=50), nullable=False),
        sa.Column("inbound_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("supplier", sa.String(length=120), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("dept_id", sa.BigInteger(), nullable=True),
        sa.Column("dept_name", sa.String(length=100), nullable=True),
        sa.Column("total_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"
        ),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_name", sa.String(length=50), nullable=True),
        sa.Column("confirmed_by_id", sa.BigInteger(), nullable=True),
        sa.Column("confirmed_by_name", sa.String(length=50), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("completion_comment", sa.String(length=500), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_asset_inbounds_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_inbounds_created_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["confirmed_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_inbounds_confirmed_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_inbounds")),
        sa.UniqueConstraint(
            "inbound_no", name=op.f("uq_ast_asset_inbounds_inbound_no")
        ),
    )
    for name in ("status", "inbound_type", "dept_id", "created_by_id"):
        op.create_index(
            f"ix_ast_asset_inbounds_{name}",
            "ast_asset_inbounds",
            [name],
            unique=False,
        )

    op.create_table(
        "ast_asset_inbound_items",
        sa.Column("inbound_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("category_name", sa.String(length=100), nullable=False),
        sa.Column("model_id", sa.BigInteger(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "unit_price", sa.Numeric(precision=12, scale=2), nullable=True
        ),
        sa.Column("warranty_end", sa.Date(), nullable=True),
        sa.Column("remark", sa.String(length=255), nullable=True),
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
            name=op.f("fk_ast_asset_inbound_items_inbound_id_ast_asset_inbounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ast_categories.id"],
            name=op.f("fk_ast_asset_inbound_items_category_id_ast_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["ast_models.id"],
            name=op.f("fk_ast_asset_inbound_items_model_id_ast_models"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_inbound_items")),
    )
    op.create_index(
        "ix_ast_asset_inbound_items_inbound_id",
        "ast_asset_inbound_items",
        ["inbound_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_asset_inbound_items_category_id",
        "ast_asset_inbound_items",
        ["category_id"],
        unique=False,
    )

    with op.batch_alter_table("ast_categories") as batch_op:
        batch_op.add_column(
            sa.Column(
                "safety_stock", sa.Integer(), nullable=False, server_default="0"
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("ast_categories") as batch_op:
        batch_op.drop_column("safety_stock")

    op.drop_index(
        "ix_ast_asset_inbound_items_category_id",
        table_name="ast_asset_inbound_items",
    )
    op.drop_index(
        "ix_ast_asset_inbound_items_inbound_id",
        table_name="ast_asset_inbound_items",
    )
    op.drop_table("ast_asset_inbound_items")

    op.drop_index(
        "ix_ast_asset_inbounds_created_by_id", table_name="ast_asset_inbounds"
    )
    op.drop_index("ix_ast_asset_inbounds_dept_id", table_name="ast_asset_inbounds")
    op.drop_index(
        "ix_ast_asset_inbounds_inbound_type", table_name="ast_asset_inbounds"
    )
    op.drop_index("ix_ast_asset_inbounds_status", table_name="ast_asset_inbounds")
    op.drop_table("ast_asset_inbounds")
