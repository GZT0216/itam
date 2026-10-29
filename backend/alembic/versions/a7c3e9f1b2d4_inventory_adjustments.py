"""inventory surplus and adjustment approval

Revision ID: a7c3e9f1b2d4
Revises: f5b8c2d4e6a9
Create Date: 2026-10-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c3e9f1b2d4"
down_revision: Union[str, Sequence[str], None] = "f5b8c2d4e6a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "ast_inventory_adjustments",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("task_no", sa.String(length=50), nullable=False),
        sa.Column("task_name", sa.String(length=120), nullable=False),
        sa.Column("adjustment_no", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("loss_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("surplus_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("requested_by_id", sa.BigInteger(), nullable=True),
        sa.Column("requested_by_name", sa.String(length=50), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by_id", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_by_name", sa.String(length=50), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_comment", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["ast_inventory_tasks.id"],
            name="fk_ast_inventory_adjustments_task_id_ast_inventory_tasks",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_id"],
            ["sys_users.id"],
            name="fk_ast_inventory_adjustments_requested_by_id_sys_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_id"],
            ["sys_users.id"],
            name="fk_ast_inventory_adjustments_reviewed_by_id_sys_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ast_inventory_adjustments"),
        sa.UniqueConstraint(
            "adjustment_no", name="uq_ast_inventory_adjustments_adjustment_no"
        ),
    )
    op.create_index(
        "ix_ast_inventory_adjustments_task_id",
        "ast_inventory_adjustments",
        ["task_id"],
    )
    op.create_index(
        "ix_ast_inventory_adjustments_status",
        "ast_inventory_adjustments",
        ["status"],
    )

    op.create_table(
        "ast_inventory_surplus",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_no", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("category_name", sa.String(length=100), nullable=True),
        sa.Column("model_id", sa.BigInteger(), nullable=True),
        sa.Column("dept_id", sa.BigInteger(), nullable=True),
        sa.Column("dept_name", sa.String(length=100), nullable=True),
        sa.Column("serial_no", sa.String(length=120), nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_name", sa.String(length=50), nullable=True),
        sa.Column("created_asset_id", sa.BigInteger(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["ast_inventory_tasks.id"],
            name="fk_ast_inventory_surplus_task_id_ast_inventory_tasks",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ast_categories.id"],
            name="fk_ast_inventory_surplus_category_id_ast_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["ast_models.id"],
            name="fk_ast_inventory_surplus_model_id_ast_models",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["dept_id"],
            ["sys_departments.id"],
            name="fk_ast_inventory_surplus_dept_id_sys_departments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["sys_users.id"],
            name="fk_ast_inventory_surplus_created_by_id_sys_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_asset_id"],
            ["ast_assets.id"],
            name="fk_ast_inventory_surplus_created_asset_id_ast_assets",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ast_inventory_surplus"),
    )
    op.create_index(
        "ix_ast_inventory_surplus_task_id", "ast_inventory_surplus", ["task_id"]
    )
    op.create_index(
        "ix_ast_inventory_surplus_asset_no", "ast_inventory_surplus", ["asset_no"]
    )
    op.create_index(
        "ix_ast_inventory_surplus_applied_at", "ast_inventory_surplus", ["applied_at"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ast_inventory_surplus_applied_at", table_name="ast_inventory_surplus"
    )
    op.drop_index(
        "ix_ast_inventory_surplus_asset_no", table_name="ast_inventory_surplus"
    )
    op.drop_index(
        "ix_ast_inventory_surplus_task_id", table_name="ast_inventory_surplus"
    )
    op.drop_table("ast_inventory_surplus")
    op.drop_index(
        "ix_ast_inventory_adjustments_status", table_name="ast_inventory_adjustments"
    )
    op.drop_index(
        "ix_ast_inventory_adjustments_task_id",
        table_name="ast_inventory_adjustments",
    )
    op.drop_table("ast_inventory_adjustments")
