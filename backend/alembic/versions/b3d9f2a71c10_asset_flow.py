"""asset requisition borrow return flow

Revision ID: b3d9f2a71c10
Revises: a1b2c3d4e5f6
Create Date: 2026-10-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3d9f2a71c10"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ast_asset_requests",
        sa.Column("request_no", sa.String(length=50), nullable=False),
        sa.Column("request_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_no", sa.String(length=50), nullable=False),
        sa.Column("asset_name", sa.String(length=120), nullable=False),
        sa.Column("asset_version", sa.Integer(), nullable=False),
        sa.Column("applicant_id", sa.BigInteger(), nullable=False),
        sa.Column("applicant_name", sa.String(length=50), nullable=False),
        sa.Column("applicant_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("applicant_dept_name", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("expected_return_date", sa.Date(), nullable=True),
        sa.Column("source_request_id", sa.BigInteger(), nullable=True),
        sa.Column("approver_id", sa.BigInteger(), nullable=True),
        sa.Column("approver_name", sa.String(length=50), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_comment", sa.String(length=500), nullable=True),
        sa.Column("outbound_by_id", sa.BigInteger(), nullable=True),
        sa.Column("outbound_by_name", sa.String(length=50), nullable=True),
        sa.Column("outbound_at", sa.DateTime(), nullable=True),
        sa.Column("outbound_location", sa.String(length=120), nullable=True),
        sa.Column("return_requested_at", sa.DateTime(), nullable=True),
        sa.Column("confirm_by_id", sa.BigInteger(), nullable=True),
        sa.Column("confirm_by_name", sa.String(length=50), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("confirm_comment", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["ast_assets.id"],
            name=op.f("fk_ast_asset_requests_asset_id_ast_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_requests_applicant_id_sys_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_asset_requests_applicant_dept_id_sys_departments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_request_id"],
            ["ast_asset_requests.id"],
            name=op.f("fk_ast_asset_requests_source_request_id_ast_asset_requests"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_requests_approver_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["outbound_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_requests_outbound_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["confirm_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_requests_confirm_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_requests")),
        sa.UniqueConstraint(
            "request_no", name=op.f("uq_ast_asset_requests_request_no")
        ),
    )
    op.create_index(
        "ix_ast_asset_requests_asset_id",
        "ast_asset_requests",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_asset_requests_type",
        "ast_asset_requests",
        ["request_type"],
        unique=False,
    )
    op.create_index(
        "ix_ast_asset_requests_status",
        "ast_asset_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_ast_asset_requests_applicant_id",
        "ast_asset_requests",
        ["applicant_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_asset_requests_expected_return_date",
        "ast_asset_requests",
        ["expected_return_date"],
        unique=False,
    )

    op.create_table(
        "ast_asset_histories",
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("request_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("action_label", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=False),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("before_snapshot", sa.JSON(), nullable=False),
        sa.Column("after_snapshot", sa.JSON(), nullable=False),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("operator_name", sa.String(length=50), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["ast_assets.id"],
            name=op.f("fk_ast_asset_histories_asset_id_ast_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ast_asset_requests.id"],
            name=op.f("fk_ast_asset_histories_request_id_ast_asset_requests"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_histories_operator_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_histories")),
    )
    op.create_index(
        "ix_ast_asset_histories_asset_id",
        "ast_asset_histories",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_asset_histories_request_id",
        "ast_asset_histories",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_asset_histories_created_at",
        "ast_asset_histories",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ast_asset_histories_created_at", table_name="ast_asset_histories"
    )
    op.drop_index(
        "ix_ast_asset_histories_request_id", table_name="ast_asset_histories"
    )
    op.drop_index("ix_ast_asset_histories_asset_id", table_name="ast_asset_histories")
    op.drop_table("ast_asset_histories")

    op.drop_index(
        "ix_ast_asset_requests_expected_return_date",
        table_name="ast_asset_requests",
    )
    op.drop_index(
        "ix_ast_asset_requests_applicant_id", table_name="ast_asset_requests"
    )
    op.drop_index("ix_ast_asset_requests_status", table_name="ast_asset_requests")
    op.drop_index("ix_ast_asset_requests_type", table_name="ast_asset_requests")
    op.drop_index("ix_ast_asset_requests_asset_id", table_name="ast_asset_requests")
    op.drop_table("ast_asset_requests")
