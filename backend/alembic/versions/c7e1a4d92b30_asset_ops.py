"""asset transfer scrap and inventory

Revision ID: c7e1a4d92b30
Revises: b3d9f2a71c10
Create Date: 2026-10-22 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e1a4d92b30"
down_revision: Union[str, Sequence[str], None] = "b3d9f2a71c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "ast_asset_transfers",
        sa.Column("transfer_no", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_no", sa.String(length=50), nullable=False),
        sa.Column("asset_name", sa.String(length=120), nullable=False),
        sa.Column("asset_version", sa.Integer(), nullable=False),
        sa.Column("from_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("from_dept_name", sa.String(length=100), nullable=True),
        sa.Column("from_custodian_id", sa.BigInteger(), nullable=True),
        sa.Column("from_custodian_name", sa.String(length=50), nullable=True),
        sa.Column("from_location", sa.String(length=120), nullable=True),
        sa.Column("to_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("to_dept_name", sa.String(length=100), nullable=True),
        sa.Column("to_custodian_id", sa.BigInteger(), nullable=True),
        sa.Column("to_custodian_name", sa.String(length=50), nullable=True),
        sa.Column("to_location", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("applicant_id", sa.BigInteger(), nullable=False),
        sa.Column("applicant_name", sa.String(length=50), nullable=False),
        sa.Column("applicant_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("applicant_dept_name", sa.String(length=100), nullable=True),
        sa.Column("approver_id", sa.BigInteger(), nullable=True),
        sa.Column("approver_name", sa.String(length=50), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_comment", sa.String(length=500), nullable=True),
        sa.Column("completed_by_id", sa.BigInteger(), nullable=True),
        sa.Column("completed_by_name", sa.String(length=50), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("completion_comment", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["ast_assets.id"],
            name=op.f("fk_ast_asset_transfers_asset_id_ast_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["from_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_asset_transfers_from_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["to_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_asset_transfers_to_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["from_custodian_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_transfers_from_custodian_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["to_custodian_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_transfers_to_custodian_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_transfers_applicant_id_sys_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_dept_id"],
            ["sys_departments.id"],
            name=op.f(
                "fk_ast_asset_transfers_applicant_dept_id_sys_departments"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_transfers_approver_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_transfers_completed_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_transfers")),
        sa.UniqueConstraint(
            "transfer_no", name=op.f("uq_ast_asset_transfers_transfer_no")
        ),
    )
    for name, column in (
        ("asset_id", "asset_id"),
        ("status", "status"),
        ("from_dept_id", "from_dept_id"),
        ("applicant_id", "applicant_id"),
    ):
        op.create_index(
            f"ix_ast_asset_transfers_{name}",
            "ast_asset_transfers",
            [column],
            unique=False,
        )

    op.create_table(
        "ast_asset_scraps",
        sa.Column("scrap_no", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_no", sa.String(length=50), nullable=False),
        sa.Column("asset_name", sa.String(length=120), nullable=False),
        sa.Column("asset_version", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=False),
        sa.Column("from_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("from_dept_name", sa.String(length=100), nullable=True),
        sa.Column("from_custodian_id", sa.BigInteger(), nullable=True),
        sa.Column("from_custodian_name", sa.String(length=50), nullable=True),
        sa.Column("from_location", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("disposal_method", sa.String(length=120), nullable=True),
        sa.Column("applicant_id", sa.BigInteger(), nullable=False),
        sa.Column("applicant_name", sa.String(length=50), nullable=False),
        sa.Column("applicant_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("applicant_dept_name", sa.String(length=100), nullable=True),
        sa.Column("approver_id", sa.BigInteger(), nullable=True),
        sa.Column("approver_name", sa.String(length=50), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_comment", sa.String(length=500), nullable=True),
        sa.Column("completed_by_id", sa.BigInteger(), nullable=True),
        sa.Column("completed_by_name", sa.String(length=50), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("completion_comment", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["ast_assets.id"],
            name=op.f("fk_ast_asset_scraps_asset_id_ast_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["from_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_asset_scraps_from_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["from_custodian_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_scraps_from_custodian_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_scraps_applicant_id_sys_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_asset_scraps_applicant_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_scraps_approver_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_scraps_completed_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_scraps")),
        sa.UniqueConstraint(
            "scrap_no", name=op.f("uq_ast_asset_scraps_scrap_no")
        ),
    )
    for name in ("asset_id", "status", "applicant_id"):
        op.create_index(
            f"ix_ast_asset_scraps_{name}",
            "ast_asset_scraps",
            [name],
            unique=False,
        )

    op.create_table(
        "ast_inventory_tasks",
        sa.Column("task_no", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("scope_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("scope_dept_name", sa.String(length=100), nullable=True),
        sa.Column("include_child", sa.Boolean(), nullable=False),
        sa.Column("scope_category_id", sa.BigInteger(), nullable=True),
        sa.Column("scope_category_name", sa.String(length=100), nullable=True),
        sa.Column("include_child_category", sa.Boolean(), nullable=False),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_name", sa.String(length=50), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["scope_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_inventory_tasks_scope_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scope_category_id"],
            ["ast_categories.id"],
            name=op.f("fk_ast_inventory_tasks_scope_category_id_ast_categories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_inventory_tasks_created_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_inventory_tasks")),
        sa.UniqueConstraint("task_no", name=op.f("uq_ast_inventory_tasks_task_no")),
    )
    op.create_index(
        "ix_ast_inventory_tasks_status",
        "ast_inventory_tasks",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_ast_inventory_tasks_created_by_id",
        "ast_inventory_tasks",
        ["created_by_id"],
        unique=False,
    )

    op.create_table(
        "ast_inventory_items",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_no", sa.String(length=50), nullable=False),
        sa.Column("asset_name", sa.String(length=120), nullable=False),
        sa.Column("category_name", sa.String(length=100), nullable=True),
        sa.Column("dept_name", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("custodian_name", sa.String(length=50), nullable=True),
        sa.Column("expected_status", sa.String(length=20), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("actual_location", sa.String(length=120), nullable=True),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("checked_by_id", sa.BigInteger(), nullable=True),
        sa.Column("checked_by_name", sa.String(length=50), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["ast_inventory_tasks.id"],
            name=op.f("fk_ast_inventory_items_task_id_ast_inventory_tasks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["ast_assets.id"],
            name=op.f("fk_ast_inventory_items_asset_id_ast_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["checked_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_inventory_items_checked_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_inventory_items")),
        sa.UniqueConstraint(
            "task_id", "asset_id", name="uq_ast_inventory_items_task_asset"
        ),
    )
    op.create_index(
        "ix_ast_inventory_items_task_id",
        "ast_inventory_items",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_inventory_items_asset_id",
        "ast_inventory_items",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_inventory_items_result",
        "ast_inventory_items",
        ["result"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ast_inventory_items_result", table_name="ast_inventory_items")
    op.drop_index("ix_ast_inventory_items_asset_id", table_name="ast_inventory_items")
    op.drop_index("ix_ast_inventory_items_task_id", table_name="ast_inventory_items")
    op.drop_table("ast_inventory_items")

    op.drop_index("ix_ast_inventory_tasks_created_by_id", table_name="ast_inventory_tasks")
    op.drop_index("ix_ast_inventory_tasks_status", table_name="ast_inventory_tasks")
    op.drop_table("ast_inventory_tasks")

    op.drop_index("ix_ast_asset_scraps_applicant_id", table_name="ast_asset_scraps")
    op.drop_index("ix_ast_asset_scraps_status", table_name="ast_asset_scraps")
    op.drop_index("ix_ast_asset_scraps_asset_id", table_name="ast_asset_scraps")
    op.drop_table("ast_asset_scraps")

    op.drop_index(
        "ix_ast_asset_transfers_applicant_id", table_name="ast_asset_transfers"
    )
    op.drop_index("ix_ast_asset_transfers_from_dept_id", table_name="ast_asset_transfers")
    op.drop_index("ix_ast_asset_transfers_status", table_name="ast_asset_transfers")
    op.drop_index("ix_ast_asset_transfers_asset_id", table_name="ast_asset_transfers")
    op.drop_table("ast_asset_transfers")
