from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.asset import Asset
from app.models.base import Base, IdMixin, TimestampMixin, VersionMixin, now_cst


class AssetMaintenance(Base, IdMixin, TimestampMixin, VersionMixin):
    __tablename__ = "ast_asset_maintenances"
    __table_args__ = (
        UniqueConstraint("maintenance_no", name="uq_ast_asset_maintenances_maintenance_no"),
        Index("ix_ast_asset_maintenances_asset_id", "asset_id"),
        Index("ix_ast_asset_maintenances_status", "status"),
        Index("ix_ast_asset_maintenances_repairer_id", "repairer_id"),
        Index("ix_ast_asset_maintenances_applicant_id", "applicant_id"),
        Index("ix_ast_asset_maintenances_from_dept_id", "from_dept_id"),
    )

    maintenance_no: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")

    asset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ast_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asset_no: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_name: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    from_status: Mapped[str] = mapped_column(String(20), nullable=False)

    from_dept_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_departments.id", ondelete="SET NULL")
    )
    from_dept_name: Mapped[str | None] = mapped_column(String(100))
    from_custodian_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    from_custodian_name: Mapped[str | None] = mapped_column(String(50))
    from_location: Mapped[str | None] = mapped_column(String(120))

    fault_description: Mapped[str] = mapped_column(String(1000), nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date)

    applicant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sys_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    applicant_name: Mapped[str] = mapped_column(String(50), nullable=False)
    applicant_dept_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_departments.id", ondelete="SET NULL")
    )
    applicant_dept_name: Mapped[str | None] = mapped_column(String(100))

    approver_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    approver_name: Mapped[str | None] = mapped_column(String(50))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    approval_comment: Mapped[str | None] = mapped_column(String(500))

    repairer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    repairer_name: Mapped[str | None] = mapped_column(String(50))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    repair_result: Mapped[str | None] = mapped_column(String(1000))
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    accepted_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    accepted_by_name: Mapped[str | None] = mapped_column(String(50))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    acceptance_comment: Mapped[str | None] = mapped_column(String(500))

    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancel_reason: Mapped[str | None] = mapped_column(String(500))

    asset: Mapped[Asset] = relationship("Asset", lazy="selectin")
    records: Mapped[list["AssetMaintenanceRecord"]] = relationship(
        "AssetMaintenanceRecord",
        back_populates="maintenance",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssetMaintenanceRecord.id",
    )


class AssetMaintenanceRecord(Base, IdMixin):
    __tablename__ = "ast_maintenance_records"
    __table_args__ = (
        Index("ix_ast_maintenance_records_maintenance_id", "maintenance_id"),
        Index("ix_ast_maintenance_records_record_type", "record_type"),
    )

    maintenance_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ast_asset_maintenances.id", ondelete="CASCADE"),
        nullable=False,
    )
    record_type: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    operator_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    operator_name: Mapped[str | None] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_cst)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_cst)

    maintenance: Mapped[AssetMaintenance] = relationship(
        "AssetMaintenance",
        back_populates="records",
    )


__all__ = ["AssetMaintenance", "AssetMaintenanceRecord"]
