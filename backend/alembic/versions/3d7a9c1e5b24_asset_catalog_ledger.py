"""asset catalog, models and ledger

Revision ID: 3d7a9c1e5b24
Revises: 9c2f4a71b8d3
Create Date: 2026-10-21 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3d7a9c1e5b24"
down_revision: Union[str, Sequence[str], None] = "9c2f4a71b8d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ast_categories",
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("category_type", sa.String(length=20), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("status", sa.SmallInteger(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["ast_categories.id"],
            name=op.f("fk_ast_categories_parent_id_ast_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_categories")),
        sa.UniqueConstraint("code", name="uq_ast_categories_code"),
    )
    op.create_index("ix_ast_categories_parent_id", "ast_categories", ["parent_id"], unique=False)
    op.create_index("ix_ast_categories_path", "ast_categories", ["path"], unique=False)

    op.create_table(
        "ast_category_fields",
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("field_key", sa.String(length=50), nullable=False),
        sa.Column("field_type", sa.String(length=20), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("status", sa.SmallInteger(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ast_categories.id"],
            name=op.f("fk_ast_category_fields_category_id_ast_categories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_category_fields")),
        sa.UniqueConstraint("category_id", "field_key", name="uq_ast_category_fields_key"),
    )
    op.create_index(
        "ix_ast_category_fields_category_id",
        "ast_category_fields",
        ["category_id"],
        unique=False,
    )

    op.create_table(
        "ast_models",
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("brand", sa.String(length=80), nullable=True),
        sa.Column("spec", sa.String(length=255), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("depreciation_months", sa.Integer(), nullable=True),
        sa.Column("residual_rate", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("status", sa.SmallInteger(), nullable=False),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ast_categories.id"],
            name=op.f("fk_ast_models_category_id_ast_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_models")),
        sa.UniqueConstraint("code", name="uq_ast_models_code"),
    )
    op.create_index("ix_ast_models_category_id", "ast_models", ["category_id"], unique=False)

    op.create_table(
        "ast_assets",
        sa.Column("asset_no", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("model_id", sa.BigInteger(), nullable=True),
        sa.Column("serial_no", sa.String(length=120), nullable=True),
        sa.Column("mac_address", sa.String(length=64), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("supplier", sa.String(length=120), nullable=True),
        sa.Column("purchase_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("warranty_end", sa.Date(), nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("dept_id", sa.BigInteger(), nullable=True),
        sa.Column("custodian_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("custom_fields", sa.JSON(), nullable=True),
        sa.Column("remark", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ast_categories.id"],
            name=op.f("fk_ast_assets_category_id_ast_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["ast_models.id"],
            name=op.f("fk_ast_assets_model_id_ast_models"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_ast_assets_dept_id_sys_departments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["custodian_id"],
            ["sys_users.id"],
            name=op.f("fk_ast_assets_custodian_id_sys_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ast_assets")),
        sa.UniqueConstraint("asset_no", name="uq_ast_assets_asset_no"),
    )
    op.create_index("ix_ast_assets_category_id", "ast_assets", ["category_id"], unique=False)
    op.create_index("ix_ast_assets_model_id", "ast_assets", ["model_id"], unique=False)
    op.create_index("ix_ast_assets_dept_id", "ast_assets", ["dept_id"], unique=False)
    op.create_index("ix_ast_assets_custodian_id", "ast_assets", ["custodian_id"], unique=False)
    op.create_index("ix_ast_assets_status", "ast_assets", ["status"], unique=False)
    op.create_index("ix_ast_assets_warranty_end", "ast_assets", ["warranty_end"], unique=False)
    op.create_index("ix_ast_assets_deleted_at", "ast_assets", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ast_assets_deleted_at", table_name="ast_assets")
    op.drop_index("ix_ast_assets_warranty_end", table_name="ast_assets")
    op.drop_index("ix_ast_assets_status", table_name="ast_assets")
    op.drop_index("ix_ast_assets_custodian_id", table_name="ast_assets")
    op.drop_index("ix_ast_assets_dept_id", table_name="ast_assets")
    op.drop_index("ix_ast_assets_model_id", table_name="ast_assets")
    op.drop_index("ix_ast_assets_category_id", table_name="ast_assets")
    op.drop_table("ast_assets")

    op.drop_index("ix_ast_models_category_id", table_name="ast_models")
    op.drop_table("ast_models")

    op.drop_index("ix_ast_category_fields_category_id", table_name="ast_category_fields")
    op.drop_table("ast_category_fields")

    op.drop_index("ix_ast_categories_path", table_name="ast_categories")
    op.drop_index("ix_ast_categories_parent_id", table_name="ast_categories")
    op.drop_table("ast_categories")
