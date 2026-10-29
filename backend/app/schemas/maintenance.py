from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _blank_to_none(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class MaintenanceCreate(BaseModel):
    asset_id: int = Field(gt=0)
    fault_description: str = Field(min_length=2, max_length=1000)
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"] = "NORMAL"
    expected_date: date | None = None

    @field_validator("fault_description", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return _blank_to_none(value)


class MaintenanceApprovePayload(BaseModel):
    version: int = Field(ge=1)
    repairer_id: int = Field(gt=0)
    expected_date: date | None = None
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("comment", mode="before")
    @classmethod
    def trim_comment(cls, value: object) -> object:
        return _blank_to_none(value)


class MaintenanceComment(BaseModel):
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("comment", mode="before")
    @classmethod
    def trim_comment(cls, value: object) -> object:
        return _blank_to_none(value)


class MaintenanceRecordCreate(BaseModel):
    record_type: Literal["PROGRESS", "EXPENSE"] = "PROGRESS"
    content: str = Field(min_length=2, max_length=1000)
    cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    occurred_at: datetime | None = None

    @field_validator("content", mode="before")
    @classmethod
    def trim_content(cls, value: object) -> object:
        return _blank_to_none(value)


class MaintenanceCompletePayload(BaseModel):
    repair_result: str = Field(min_length=2, max_length=1000)
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("repair_result", "comment", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return _blank_to_none(value)


class MaintenanceAcceptPayload(BaseModel):
    version: int = Field(ge=1)
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("comment", mode="before")
    @classmethod
    def trim_comment(cls, value: object) -> object:
        return _blank_to_none(value)


class MaintenanceCancelPayload(BaseModel):
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return _blank_to_none(value)


class MaintenanceAssetOut(BaseModel):
    id: int
    asset_no: str
    name: str
    category_name: str | None = None
    model_name: str | None = None
    serial_no: str | None = None
    location: str | None = None
    dept_id: int | None = None
    dept_name: str | None = None
    custodian_id: int | None = None
    custodian_name: str | None = None
    status: str
    status_label: str
    version: int


class MaintenanceAssetPageOut(BaseModel):
    items: list[MaintenanceAssetOut]
    total: int
    page: int
    page_size: int


class MaintenanceRecordOut(BaseModel):
    id: int
    record_type: str
    record_type_label: str
    content: str
    cost: Decimal | None = None
    operator_name: str | None = None
    occurred_at: datetime
    created_at: datetime


class MaintenanceOut(BaseModel):
    id: int
    maintenance_no: str
    status: str
    status_label: str
    status_tag_type: str
    priority: str
    priority_label: str
    priority_tag_type: str

    asset_id: int
    asset_no: str
    asset_name: str
    asset_version: int
    asset_status: str
    asset_status_label: str
    from_status: str
    from_status_label: str
    from_dept_id: int | None = None
    from_dept_name: str | None = None
    from_custodian_id: int | None = None
    from_custodian_name: str | None = None
    from_location: str | None = None

    fault_description: str
    expected_date: date | None = None
    applicant_id: int
    applicant_name: str
    applicant_dept_id: int | None = None
    applicant_dept_name: str | None = None

    approver_name: str | None = None
    approved_at: datetime | None = None
    approval_comment: str | None = None
    repairer_id: int | None = None
    repairer_name: str | None = None
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    repair_result: str | None = None
    total_cost: Decimal = Decimal("0.00")

    accepted_by_name: str | None = None
    accepted_at: datetime | None = None
    acceptance_comment: str | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None

    records: list[MaintenanceRecordOut] = []
    can_approve: bool = False
    can_reject: bool = False
    can_start: bool = False
    can_add_record: bool = False
    can_complete: bool = False
    can_accept: bool = False
    can_cancel: bool = False

    version: int
    created_at: datetime
    updated_at: datetime


class MaintenancePageOut(BaseModel):
    items: list[MaintenanceOut]
    total: int
    page: int
    page_size: int
