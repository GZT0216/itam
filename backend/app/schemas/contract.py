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


class ContractBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    contract_type: Literal["PURCHASE", "MAINTENANCE", "LEASE"] = "PURCHASE"
    supplier: str | None = Field(default=None, max_length=160)
    amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    sign_date: date | None = None
    start_date: date
    end_date: date
    dept_id: int | None = Field(default=None, gt=0)
    owner_id: int | None = Field(default=None, gt=0)
    remark: str | None = Field(default=None, max_length=500)

    @field_validator("name", "supplier", "remark", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return _blank_to_none(value)


class ContractCreate(ContractBase):
    asset_ids: list[int] = Field(default_factory=list, max_length=200)


class ContractUpdate(ContractBase):
    version: int = Field(ge=1)


class ContractTerminatePayload(BaseModel):
    version: int = Field(ge=1)
    reason: str = Field(min_length=2, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return _blank_to_none(value)


class ContractRenewPayload(BaseModel):
    version: int = Field(ge=1)
    end_date: date
    amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    remark: str | None = Field(default=None, max_length=500)

    @field_validator("remark", mode="before")
    @classmethod
    def trim_remark(cls, value: object) -> object:
        return _blank_to_none(value)


class ContractLinkPayload(BaseModel):
    asset_ids: list[int] = Field(min_length=1, max_length=200)


class ContractAssetOut(BaseModel):
    id: int
    asset_no: str
    name: str
    category_name: str | None = None
    model_name: str | None = None
    serial_no: str | None = None
    location: str | None = None
    dept_name: str | None = None
    custodian_name: str | None = None
    status: str
    status_label: str
    linked_at: datetime
    linked_by_name: str | None = None


class ContractAssetOption(BaseModel):
    id: int
    asset_no: str
    name: str
    category_name: str | None = None
    model_name: str | None = None
    serial_no: str | None = None
    location: str | None = None
    dept_name: str | None = None
    custodian_name: str | None = None
    status: str
    status_label: str
    linked: bool = False


class ContractAssetOptionPage(BaseModel):
    items: list[ContractAssetOption]
    total: int
    page: int
    page_size: int


class ContractOwnerOption(BaseModel):
    id: int
    name: str
    username: str
    dept_id: int | None = None
    dept_name: str | None = None


class ContractOut(BaseModel):
    id: int
    contract_no: str
    name: str
    contract_type: str
    contract_type_label: str
    contract_type_tag_type: str
    status: str
    status_label: str
    status_tag_type: str
    supplier: str | None = None
    amount: Decimal
    sign_date: date | None = None
    start_date: date
    end_date: date
    days_to_expiry: int
    dept_id: int | None = None
    dept_name: str | None = None
    owner_id: int | None = None
    owner_name: str | None = None
    remark: str | None = None
    terminated_at: datetime | None = None
    terminate_reason: str | None = None
    created_by_name: str | None = None
    assets: list[ContractAssetOut] = []
    asset_count: int = 0
    can_edit: bool = False
    can_terminate: bool = False
    can_renew: bool = False
    can_link_asset: bool = False
    version: int
    created_at: datetime
    updated_at: datetime


class ContractPageOut(BaseModel):
    items: list[ContractOut]
    total: int
    page: int
    page_size: int


class ContractSummaryOut(BaseModel):
    active_count: int
    expiring_count: int
    expired_count: int
    terminated_count: int
    total_amount: Decimal
    linked_asset_count: int
