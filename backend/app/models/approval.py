from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, VersionMixin

if TYPE_CHECKING:
    from app.models.asset import AssetRequest
    from app.models.rbac import Dept, User

approval_flow_depts = Table(
    "ast_approval_flow_depts",
    Base.metadata,
    Column(
        "flow_id",
        BigInteger,
        ForeignKey("ast_approval_flows.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "dept_id",
        BigInteger,
        ForeignKey("sys_departments.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class ApprovalFlow(Base, IdMixin, TimestampMixin, VersionMixin):
    __tablename__ = "ast_approval_flows"
    __table_args__ = (
        UniqueConstraint("name", name="uq_ast_approval_flows_name"),
        Index("ix_ast_approval_flows_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    created_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    created_by_name: Mapped[str | None] = mapped_column(String(50))
    updated_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    updated_by_name: Mapped[str | None] = mapped_column(String(50))

    nodes: Mapped[list[ApprovalFlowNode]] = relationship(
        "ApprovalFlowNode",
        back_populates="flow",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ApprovalFlowNode.step_no",
    )
    departments: Mapped[list["Dept"]] = relationship(
        "Dept",
        secondary=approval_flow_depts,
        lazy="selectin",
    )


class ApprovalFlowNode(Base, IdMixin, TimestampMixin):
    __tablename__ = "ast_approval_flow_nodes"
    __table_args__ = (
        UniqueConstraint("flow_id", "step_no", name="uq_ast_approval_flow_nodes_step"),
        UniqueConstraint("flow_id", "step_code", name="uq_ast_approval_flow_nodes_code"),
        Index("ix_ast_approval_flow_nodes_flow_id", "flow_id"),
    )

    flow_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ast_approval_flows.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    step_code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    role_code: Mapped[str | None] = mapped_column(String(50))
    manager_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approve_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="OR")
    fallback_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ASSET_ADMIN"
    )

    flow: Mapped[ApprovalFlow] = relationship("ApprovalFlow", back_populates="nodes")
    user: Mapped["User | None"] = relationship("User", lazy="selectin")


class ApprovalTask(Base, IdMixin, TimestampMixin):
    __tablename__ = "ast_approval_tasks"
    __table_args__ = (
        Index("ix_ast_approval_tasks_request_id", "request_id"),
        Index("ix_ast_approval_tasks_approver_status", "approver_id", "status"),
    )

    request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ast_asset_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    flow_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ast_approval_flows.id", ondelete="SET NULL")
    )
    flow_name: Mapped[str | None] = mapped_column(String(80))
    node_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ast_approval_flow_nodes.id", ondelete="SET NULL")
    )
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    step_code: Mapped[str] = mapped_column(String(32), nullable=False)
    step_name: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_type: Mapped[str] = mapped_column(String(20), nullable=False)
    approver_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("sys_users.id", ondelete="SET NULL")
    )
    approver_name: Mapped[str | None] = mapped_column(String(50))
    approve_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="OR")
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="WAITING")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime)
    comment: Mapped[str | None] = mapped_column(String(500))

    request: Mapped["AssetRequest"] = relationship(
        "AssetRequest", back_populates="tasks"
    )


__all__ = [
    "ApprovalFlow",
    "ApprovalFlowNode",
    "ApprovalTask",
    "approval_flow_depts",
]
