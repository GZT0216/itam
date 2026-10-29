"""request category and multi-level approval flow

Revision ID: c9e4d1a7b2f3
Revises: a4d8f2c6b1e9
Create Date: 2026-10-23 09:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9e4d1a7b2f3"
down_revision: Union[str, Sequence[str], None] = "a4d8f2c6b1e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("ast_asset_requests") as batch_op:
        batch_op.add_column(sa.Column("category_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(
            sa.Column("category_name", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "include_child",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            )
        )
        batch_op.add_column(
            sa.Column("approval_stage", sa.String(length=16), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "dept_approval_required",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    op.execute(
        sa.text(
            """
            UPDATE ast_asset_requests
            SET category_id = (
                    SELECT a.category_id
                    FROM ast_assets a
                    WHERE a.id = ast_asset_requests.asset_id
                ),
                category_name = (
                    SELECT c.name
                    FROM ast_assets a
                    JOIN ast_categories c ON c.id = a.category_id
                    WHERE a.id = ast_asset_requests.asset_id
                )
            WHERE category_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE ast_asset_requests
            SET approval_stage = 'ASSET'
            WHERE status = 'PENDING_APPROVAL' AND approval_stage IS NULL
            """
        )
    )

    with op.batch_alter_table("ast_asset_requests") as batch_op:
        batch_op.alter_column(
            "category_id", existing_type=sa.BigInteger(), nullable=False
        )
        batch_op.alter_column(
            "category_name",
            existing_type=sa.String(length=100),
            nullable=False,
        )
        batch_op.alter_column(
            "asset_id", existing_type=sa.BigInteger(), nullable=True
        )
        batch_op.alter_column(
            "asset_no", existing_type=sa.String(length=50), nullable=True
        )
        batch_op.alter_column(
            "asset_name", existing_type=sa.String(length=120), nullable=True
        )
        batch_op.create_foreign_key(
            "fk_ast_asset_requests_category_id_ast_categories",
            "ast_categories",
            ["category_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_table(
        "ast_request_approvals",
        sa.Column("request_id", sa.BigInteger(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("step_code", sa.String(length=16), nullable=False),
        sa.Column("step_name", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("approver_id", sa.BigInteger(), nullable=True),
        sa.Column("approver_name", sa.String(length=50), nullable=True),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("operated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ast_asset_requests.id"],
            name=op.f("fk_ast_request_approvals_request_id_ast_asset_requests"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_request_approvals_approver_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_request_approvals")),
        sa.UniqueConstraint(
            "request_id",
            "step_no",
            name="uq_ast_request_approvals_step",
        ),
    )
    op.create_index(
        "ix_ast_request_approvals_request_id",
        "ast_request_approvals",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_request_approvals_approver_id",
        "ast_request_approvals",
        ["approver_id"],
        unique=False,
    )

    op.create_table(
        "ast_request_settings",
        sa.Column(
            "dept_approval_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("updated_by_id", sa.BigInteger(), nullable=True),
        sa.Column("updated_by_name", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_request_settings_updated_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_request_settings")),
    )
    now = datetime.now()
    op.execute(
        sa.text(
            """
            INSERT INTO ast_request_settings
                (dept_approval_required, created_at, updated_at, version)
            VALUES
                (1, :now, :now, 1)
            """
        ).bindparams(now=now)
    )


def downgrade() -> None:
    op.drop_table("ast_request_settings")

    op.drop_index(
        "ix_ast_request_approvals_approver_id",
        table_name="ast_request_approvals",
    )
    op.drop_index(
        "ix_ast_request_approvals_request_id",
        table_name="ast_request_approvals",
    )
    op.drop_table("ast_request_approvals")

    with op.batch_alter_table("ast_asset_requests") as batch_op:
        batch_op.drop_constraint(
            "fk_ast_asset_requests_category_id_ast_categories",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "asset_id", existing_type=sa.BigInteger(), nullable=False
        )
        batch_op.alter_column(
            "asset_no", existing_type=sa.String(length=50), nullable=False
        )
        batch_op.alter_column(
            "asset_name", existing_type=sa.String(length=120), nullable=False
        )
        batch_op.drop_column("dept_approval_required")
        batch_op.drop_column("approval_stage")
        batch_op.drop_column("include_child")
        batch_op.drop_column("category_name")
        batch_op.drop_column("category_id")
