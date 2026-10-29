"""configurable approval flows and approval tasks

Revision ID: f5b8c2d4e6a9
Revises: c9e4d1a7b2f3
Create Date: 2026-10-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5b8c2d4e6a9"
down_revision: Union[str, Sequence[str], None] = "c9e4d1a7b2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column(
        "sys_departments", sa.Column("manager_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        "fk_sys_departments_manager_id_sys_users",
        "sys_departments",
        "sys_users",
        ["manager_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_sys_departments_manager_id", "sys_departments", ["manager_id"]
    )

    op.create_table(
        "ast_approval_flows",
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("created_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_name", sa.String(length=50), nullable=True),
        sa.Column("updated_by_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_by_name", sa.String(length=50), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["sys_users.id"], name="fk_ast_approval_flows_created_by_id_sys_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"], ["sys_users.id"], name="fk_ast_approval_flows_updated_by_id_sys_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ast_approval_flows"),
        sa.UniqueConstraint("name", name="uq_ast_approval_flows_name"),
    )
    op.create_index(
        "ix_ast_approval_flows_status", "ast_approval_flows", ["status"]
    )

    op.create_table(
        "ast_approval_flow_nodes",
        sa.Column("flow_id", sa.BigInteger(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("step_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("approver_type", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("role_code", sa.String(length=50), nullable=True),
        sa.Column("manager_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approve_mode", sa.String(length=10), nullable=False, server_default="OR"),
        sa.Column("fallback_type", sa.String(length=20), nullable=False, server_default="ASSET_ADMIN"),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["flow_id"], ["ast_approval_flows.id"], name="fk_ast_approval_flow_nodes_flow_id_ast_approval_flows", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["sys_users.id"], name="fk_ast_approval_flow_nodes_user_id_sys_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ast_approval_flow_nodes"),
        sa.UniqueConstraint("flow_id", "step_no", name="uq_ast_approval_flow_nodes_step"),
        sa.UniqueConstraint("flow_id", "step_code", name="uq_ast_approval_flow_nodes_code"),
    )
    op.create_index(
        "ix_ast_approval_flow_nodes_flow_id",
        "ast_approval_flow_nodes",
        ["flow_id"],
    )

    op.create_table(
        "ast_approval_flow_depts",
        sa.Column("flow_id", sa.BigInteger(), nullable=False),
        sa.Column("dept_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["flow_id"], ["ast_approval_flows.id"], name="fk_ast_approval_flow_depts_flow_id_ast_approval_flows", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["dept_id"], ["sys_departments.id"], name="fk_ast_approval_flow_depts_dept_id_sys_departments", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("flow_id", "dept_id", name="pk_ast_approval_flow_depts"),
    )

    op.create_table(
        "ast_approval_tasks",
        sa.Column("request_id", sa.BigInteger(), nullable=False),
        sa.Column("flow_id", sa.BigInteger(), nullable=True),
        sa.Column("flow_name", sa.String(length=80), nullable=True),
        sa.Column("node_id", sa.BigInteger(), nullable=True),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("step_code", sa.String(length=32), nullable=False),
        sa.Column("step_name", sa.String(length=50), nullable=False),
        sa.Column("approver_type", sa.String(length=20), nullable=False),
        sa.Column("approver_id", sa.BigInteger(), nullable=True),
        sa.Column("approver_name", sa.String(length=50), nullable=True),
        sa.Column("approve_mode", sa.String(length=10), nullable=False, server_default="OR"),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="WAITING"),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("acted_at", sa.DateTime(), nullable=True),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["request_id"], ["ast_asset_requests.id"], name="fk_ast_approval_tasks_request_id_ast_asset_requests", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["flow_id"], ["ast_approval_flows.id"], name="fk_ast_approval_tasks_flow_id_ast_approval_flows", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["node_id"], ["ast_approval_flow_nodes.id"], name="fk_ast_approval_tasks_node_id_ast_approval_flow_nodes", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"], ["sys_users.id"], name="fk_ast_approval_tasks_approver_id_sys_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ast_approval_tasks"),
    )
    op.create_index(
        "ix_ast_approval_tasks_request_id", "ast_approval_tasks", ["request_id"]
    )
    op.create_index(
        "ix_ast_approval_tasks_approver_status",
        "ast_approval_tasks",
        ["approver_id", "status"],
    )

    op.add_column(
        "ast_asset_requests", sa.Column("flow_id", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "ast_asset_requests", sa.Column("flow_name", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "ast_asset_requests", sa.Column("current_step_no", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_ast_asset_requests_flow_id_ast_approval_flows",
        "ast_asset_requests",
        "ast_approval_flows",
        ["flow_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "ast_request_approvals", sa.Column("task_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        "fk_ast_request_approvals_task_id_ast_approval_tasks",
        "ast_request_approvals",
        "ast_approval_tasks",
        ["task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "uq_ast_request_approvals_step",
        "ast_request_approvals",
        type_="unique",
    )
    op.create_index(
        "ix_ast_request_approvals_request_step",
        "ast_request_approvals",
        ["request_id", "step_no"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ast_request_approvals_request_step",
        table_name="ast_request_approvals",
    )
    op.create_unique_constraint(
        "uq_ast_request_approvals_step",
        "ast_request_approvals",
        ["request_id", "step_no"],
    )
    op.drop_constraint(
        "fk_ast_request_approvals_task_id_ast_approval_tasks",
        "ast_request_approvals",
        type_="foreignkey",
    )
    op.drop_column("ast_request_approvals", "task_id")

    op.drop_constraint(
        "fk_ast_asset_requests_flow_id_ast_approval_flows",
        "ast_asset_requests",
        type_="foreignkey",
    )
    op.drop_column("ast_asset_requests", "current_step_no")
    op.drop_column("ast_asset_requests", "flow_name")
    op.drop_column("ast_asset_requests", "flow_id")

    op.drop_index("ix_ast_approval_tasks_approver_status", table_name="ast_approval_tasks")
    op.drop_index("ix_ast_approval_tasks_request_id", table_name="ast_approval_tasks")
    op.drop_table("ast_approval_tasks")

    op.drop_table("ast_approval_flow_depts")

    op.drop_index(
        "ix_ast_approval_flow_nodes_flow_id", table_name="ast_approval_flow_nodes"
    )
    op.drop_table("ast_approval_flow_nodes")

    op.drop_index("ix_ast_approval_flows_status", table_name="ast_approval_flows")
    op.drop_table("ast_approval_flows")

    op.drop_index("ix_sys_departments_manager_id", table_name="sys_departments")
    op.drop_constraint(
        "fk_sys_departments_manager_id_sys_users",
        "sys_departments",
        type_="foreignkey",
    )
    op.drop_column("sys_departments", "manager_id")
