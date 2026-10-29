"""asset maintenance orders and records

Revision ID: e3a7c5d91f24
Revises: d8f2b6c01e47
Create Date: 2026-10-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3a7c5d91f24"
down_revision: Union[str, Sequence[str], None] = "d8f2b6c01e47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "ast_asset_maintenances",
        sa.Column("maintenance_no", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="NORMAL"),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_no", sa.String(length=50), nullable=False),
        sa.Column("asset_name", sa.String(length=120), nullable=False),
        sa.Column("asset_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("from_status", sa.String(length=20), nullable=False),
        sa.Column("from_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("from_dept_name", sa.String(length=100), nullable=True),
        sa.Column("from_custodian_id", sa.BigInteger(), nullable=True),
        sa.Column("from_custodian_name", sa.String(length=50), nullable=True),
        sa.Column("from_location", sa.String(length=120), nullable=True),
        sa.Column("fault_description", sa.String(length=1000), nullable=False),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("applicant_id", sa.BigInteger(), nullable=False),
        sa.Column("applicant_name", sa.String(length=50), nullable=False),
        sa.Column("applicant_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("applicant_dept_name", sa.String(length=100), nullable=True),
        sa.Column("approver_id", sa.BigInteger(), nullable=True),
        sa.Column("approver_name", sa.String(length=50), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_comment", sa.String(length=500), nullable=True),
        sa.Column("repairer_id", sa.BigInteger(), nullable=True),
        sa.Column("repairer_name", sa.String(length=50), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("repair_result", sa.String(length=1000), nullable=True),
        sa.Column(
            "total_cost", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"
        ),
        sa.Column("accepted_by_id", sa.BigInteger(), nullable=True),
        sa.Column("accepted_by_name", sa.String(length=50), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("acceptance_comment", sa.String(length=500), nullable=True),
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
            ["asset_id"],
            ["ast_assets.id"],
            name=op.f("fk_ast_asset_maintenances_asset_id_ast_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["from_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_asset_maintenances_from_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["from_custodian_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_maintenances_from_custodian_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_maintenances_applicant_id_sys_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["applicant_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_asset_maintenances_applicant_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_maintenances_approver_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["repairer_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_maintenances_repairer_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_maintenances_accepted_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_maintenances")),
        sa.UniqueConstraint(
            "maintenance_no", name=op.f("uq_ast_asset_maintenances_maintenance_no")
        ),
    )
    for name in ("asset_id", "status", "repairer_id", "applicant_id", "from_dept_id"):
        op.create_index(
            f"ix_ast_asset_maintenances_{name}",
            "ast_asset_maintenances",
            [name],
            unique=False,
        )

    op.create_table(
        "ast_maintenance_records",
        sa.Column("maintenance_id", sa.BigInteger(), nullable=False),
        sa.Column("record_type", sa.String(length=16), nullable=False),
        sa.Column("content", sa.String(length=1000), nullable=False),
        sa.Column("cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("operator_name", sa.String(length=50), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["maintenance_id"],
            ["ast_asset_maintenances.id"],
            name=op.f("fk_ast_maintenance_records_maintenance_id_ast_asset_maintenances"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_maintenance_records_operator_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_maintenance_records")),
    )
    op.create_index(
        "ix_ast_maintenance_records_maintenance_id",
        "ast_maintenance_records",
        ["maintenance_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_maintenance_records_record_type",
        "ast_maintenance_records",
        ["record_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ast_maintenance_records_record_type", table_name="ast_maintenance_records"
    )
    op.drop_index(
        "ix_ast_maintenance_records_maintenance_id", table_name="ast_maintenance_records"
    )
    op.drop_table("ast_maintenance_records")

    for name in ("asset_id", "status", "repairer_id", "applicant_id", "from_dept_id"):
        op.drop_index(
            f"ix_ast_asset_maintenances_{name}", table_name="ast_asset_maintenances"
        )
    op.drop_table("ast_asset_maintenances")
