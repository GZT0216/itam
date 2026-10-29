from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.contract import ContractStatus, ContractType
from app.models.base import Base, IdMixin, TimestampMixin, VersionMixin, now_cst
from app.models.rbac import Dept, User


class AssetContract(Base, IdMixin, TimestampMixin, VersionMixin):
    __tablename__ = "ast_asset_contracts"
    __table_args__ = (
        UniqueConstraint("contract_no", name="uq_ast_asset_contracts_contract_no"),
        Index("ix_ast_asset_contracts_type", "contract_type"),
        Index("ix_ast_asset_contracts_status", "status"),
        Index("ix_ast_asset_contracts_end_date", "end_date"),
        Index("ix_ast_asset_contracts_dept_id", "dept_id"),
    )

    contract_no: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    contract_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ContractType.PURCHASE
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ContractStatus.ACTIVE
    )
    supplier: Mapped[str | None] = mapped_column(String(160))
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    sign_date: Mapped[date | None] = mapped_column(Date)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    dept_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sys_departments.id", ondelete="RESTRICT"),
    )
    owner_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sys_users.id", ondelete="RESTRICT"),
    )
    remark: Mapped[str | None] = mapped_column(String(500))
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime)
    terminate_reason: Mapped[str | None] = mapped_column(String(500))
    created_by_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sys_users.id", ondelete="SET NULL"),
    )
    created_by_name: Mapped[str | None] = mapped_column(String(80))

    dept: Mapped[Dept | None] = relationship("Dept", lazy="selectin")
    owner: Mapped[User | None] = relationship(
        "User", lazy="selectin", foreign_keys=[owner_id]
    )
    links: Mapped[list["AssetContractAsset"]] = relationship(
        "AssetContractAsset",
        back_populates="contract",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AssetContractAsset.id",
    )


class AssetContractAsset(Base, IdMixin):
    __tablename__ = "ast_contract_assets"
    __table_args__ = (
        UniqueConstraint(
            "contract_id", "asset_id", name="uq_ast_contract_assets_contract_asset"
        ),
        Index("ix_ast_contract_assets_asset_id", "asset_id"),
        Index("ix_ast_contract_assets_contract_id", "contract_id"),
    )

    contract_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ast_asset_contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ast_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now_cst
    )
    linked_by_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("sys_users.id", ondelete="SET NULL"),
    )
    linked_by_name: Mapped[str | None] = mapped_column(String(80))

    contract: Mapped[AssetContract] = relationship(
        "AssetContract", back_populates="links"
    )
    asset: Mapped["Asset"] = relationship("Asset", lazy="selectin")


__all__ = ["AssetContract", "AssetContractAsset"]
