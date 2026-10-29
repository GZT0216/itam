"""ldap directory sync

Revision ID: a1b2c3d4e5f6
Revises: 3d7a9c1e5b24
Create Date: 2026-10-21 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "3d7a9c1e5b24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sys_departments") as batch_op:
        batch_op.add_column(
            sa.Column("source", sa.String(length=10), nullable=False, server_default="local")
        )
        batch_op.add_column(sa.Column("ldap_dn", sa.String(length=512), nullable=True))
        batch_op.create_unique_constraint(
            "uq_sys_departments_ldap_dn", ["ldap_dn"]
        )

    with op.batch_alter_table("sys_users") as batch_op:
        batch_op.add_column(
            sa.Column("source", sa.String(length=10), nullable=False, server_default="local")
        )
        batch_op.add_column(sa.Column("ldap_dn", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("ldap_uid", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("ldap_synced_at", sa.DateTime(), nullable=True))
        batch_op.create_unique_constraint("uq_sys_users_ldap_dn", ["ldap_dn"])
        batch_op.create_index("ix_sys_users_ldap_uid", ["ldap_uid"], unique=False)

    op.create_table(
        "sys_ldap_configs",
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("server_host", sa.String(length=255), nullable=False),
        sa.Column("server_port", sa.Integer(), nullable=False),
        sa.Column("use_ssl", sa.Boolean(), nullable=False),
        sa.Column("start_tls", sa.Boolean(), nullable=False),
        sa.Column("base_dn", sa.String(length=512), nullable=False),
        sa.Column("bind_dn", sa.String(length=512), nullable=False),
        sa.Column("bind_password_encrypted", sa.String(length=1024), nullable=True),
        sa.Column("user_filter", sa.String(length=500), nullable=False),
        sa.Column("dept_filter", sa.String(length=500), nullable=False),
        sa.Column("username_attribute", sa.String(length=80), nullable=False),
        sa.Column("real_name_attribute", sa.String(length=80), nullable=False),
        sa.Column("email_attribute", sa.String(length=80), nullable=False),
        sa.Column("phone_attribute", sa.String(length=80), nullable=False),
        sa.Column("employee_no_attribute", sa.String(length=80), nullable=False),
        sa.Column("default_role_id", sa.BigInteger(), nullable=True),
        sa.Column("root_dept_id", sa.BigInteger(), nullable=True),
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_status", sa.String(length=20), nullable=True),
        sa.Column("last_sync_message", sa.String(length=1000), nullable=True),
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_status", sa.String(length=20), nullable=True),
        sa.Column("last_test_message", sa.String(length=1000), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["default_role_id"],
            ["sys_roles.id"],
            name=op.f("fk_sys_ldap_configs_default_role_id_sys_roles"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["root_dept_id"],
            ["sys_departments.id"],
            name=op.f("fk_sys_ldap_configs_root_dept_id_sys_departments"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_ldap_configs")),
    )

    op.create_table(
        "sys_ldap_sync_logs",
        sa.Column("config_id", sa.BigInteger(), nullable=True),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("dept_total", sa.Integer(), nullable=False),
        sa.Column("dept_created", sa.Integer(), nullable=False),
        sa.Column("dept_updated", sa.Integer(), nullable=False),
        sa.Column("user_total", sa.Integer(), nullable=False),
        sa.Column("user_created", sa.Integer(), nullable=False),
        sa.Column("user_updated", sa.Integer(), nullable=False),
        sa.Column("user_disabled", sa.Integer(), nullable=False),
        sa.Column("user_skipped", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.BigInteger(), nullable=True),
        sa.Column("operator_name", sa.String(length=50), nullable=True),
        sa.Column("message", sa.String(length=1000), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_id"],
            ["sys_ldap_configs.id"],
            name=op.f("fk_sys_ldap_sync_logs_config_id_sys_ldap_configs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["operator_id"],
            ["sys_users.id"],
            name=op.f("fk_sys_ldap_sync_logs_operator_id_sys_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sys_ldap_sync_logs")),
    )
    op.create_index(
        "ix_sys_ldap_sync_logs_config_id",
        "sys_ldap_sync_logs",
        ["config_id"],
        unique=False,
    )
    op.create_index(
        "ix_sys_ldap_sync_logs_started_at",
        "sys_ldap_sync_logs",
        ["started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_sys_ldap_sync_logs_started_at", table_name="sys_ldap_sync_logs")
    op.drop_index("ix_sys_ldap_sync_logs_config_id", table_name="sys_ldap_sync_logs")
    op.drop_table("sys_ldap_sync_logs")
    op.drop_table("sys_ldap_configs")

    with op.batch_alter_table("sys_users") as batch_op:
        batch_op.drop_index("ix_sys_users_ldap_uid")
        batch_op.drop_constraint("uq_sys_users_ldap_dn", type_="unique")
        batch_op.drop_column("ldap_synced_at")
        batch_op.drop_column("ldap_uid")
        batch_op.drop_column("ldap_dn")
        batch_op.drop_column("source")

    with op.batch_alter_table("sys_departments") as batch_op:
        batch_op.drop_constraint("uq_sys_departments_ldap_dn", type_="unique")
        batch_op.drop_column("ldap_dn")
        batch_op.drop_column("source")
