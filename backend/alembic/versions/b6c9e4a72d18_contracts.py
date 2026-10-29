"""asset contracts and contract asset links

Revision ID: b6c9e4a72d18
Revises: e3a7c5d91f24
Create Date: 2026-10-22 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6c9e4a72d18"
down_revision: Union[str, Sequence[str], None] = "e3a7c5d91f24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "ast_asset_contracts",
        sa.Column("contract_no", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("contract_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("supplier", sa.String(length=160), nullable=True),
        sa.Column(
            "amount", sa.Numeric(precision=14, scale=2), nullable=False, server_default="0"
        ),
        sa.Column("sign_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("dept_id", sa.BigInteger(), nullable=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("terminated_at", sa.DateTime(), nullable=True),
        sa.Column("terminate_reason", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_name", sa.String(length=80), nullable=True),
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
            name=op.f("fk_ast_asset_contracts_dept_id_sys_departments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_contracts_owner_id_sys_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_asset_contracts_created_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_asset_contracts")),
        sa.UniqueConstraint(
            "contract_no", name=op.f("uq_ast_asset_contracts_contract_no")
        ),
    )
    for name in ("contract_type", "status", "end_date", "dept_id"):
        op.create_index(
            f"ix_ast_asset_contracts_{name}",
            "ast_asset_contracts",
            [name],
            unique=False,
        )

    op.create_table(
        "ast_contract_assets",
        sa.Column("contract_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("linked_at", sa.DateTime(), nullable=False),
        sa.Column("linked_by_id", sa.BigInteger(), nullable=True),
        sa.Column("linked_by_name", sa.String(length=80), nullable=True),
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["ast_asset_contracts.id"],
            name=op.f("fk_ast_contract_assets_contract_id_ast_asset_contracts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["ast_assets.id"],
            name=op.f("fk_ast_contract_assets_asset_id_ast_assets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["linked_by_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_contract_assets_linked_by_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_contract_assets")),
        sa.UniqueConstraint(
            "contract_id",
            "asset_id",
            name=op.f("uq_ast_contract_assets_contract_asset"),
        ),
    )
    op.create_index(
        "ix_ast_contract_assets_contract_id",
        "ast_contract_assets",
        ["contract_id"],
        unique=False,
    )
    op.create_index(
        "ix_ast_contract_assets_asset_id",
        "ast_contract_assets",
        ["asset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ast_contract_assets_asset_id", table_name="ast_contract_assets")
    op.drop_index("ix_ast_contract_assets_contract_id", table_name="ast_contract_assets")
    op.drop_table("ast_contract_assets")

    for name in ("contract_type", "status", "end_date", "dept_id"):
        op.drop_index(
            f"ix_ast_asset_contracts_{name}", table_name="ast_asset_contracts"
        )
    op.drop_table("ast_asset_contracts")
