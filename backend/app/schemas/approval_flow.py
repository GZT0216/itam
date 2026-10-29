from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _blank_to_none(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class ApprovalFlowNodeIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    approver_type: Literal["DEPT_MANAGER", "USER", "ROLE"]
    user_id: int | None = Field(default=None, gt=0)
    role_code: str | None = Field(default=None, max_length=50)
    manager_level: int = Field(default=1, ge=1, le=5)
    approve_mode: Literal["OR", "ALL"] = "OR"
    fallback_type: Literal[
        "ASSET_ADMIN", "DEPT_ADMIN", "SUPER_ADMIN", "SKIP"
    ] = "ASSET_ADMIN"

    @field_validator("name", "role_code", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("role_code")
    @classmethod
    def upper_role(cls, value: str | None) -> str | None:
        return value.upper() if value else None


class ApprovalFlowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    is_default: bool = False
    status: int = Field(default=1, ge=0, le=1)
    dept_ids: list[int] = Field(default_factory=list, max_length=200)
    nodes: list[ApprovalFlowNodeIn] = Field(min_length=1, max_length=10)

    @field_validator("name", "description", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("dept_ids")
    @classmethod
    def dedupe_depts(cls, value: list[int]) -> list[int]:
        result = list(dict.fromkeys(value))
        if any(item <= 0 for item in result):
            raise ValueError("部门 ID 不合法")
        return result


class ApprovalFlowUpdate(ApprovalFlowCreate):
    version: int = Field(ge=1)


class ApprovalFlowStatusUpdate(BaseModel):
    status: int = Field(ge=0, le=1)
    version: int = Field(ge=1)


class ApprovalFlowNodeOut(BaseModel):
    id: int
    step_no: int
    step_code: str
    name: str
    approver_type: str
    approver_type_label: str
    user_id: int | None = None
    user_name: str | None = None
    role_code: str | None = None
    role_name: str | None = None
    manager_level: int = 1
    approve_mode: str
    approve_mode_label: str
    fallback_type: str
    fallback_type_label: str


class ApprovalFlowOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_default: bool
    status: int
    status_label: str
    dept_ids: list[int] = Field(default_factory=list)
    dept_names: list[str] = Field(default_factory=list)
    nodes: list[ApprovalFlowNodeOut] = Field(default_factory=list)
    version: int
    created_by_name: str | None = None
    updated_by_name: str | None = None
    created_at: datetime
    updated_at: datetime


class DeptOptionOut(BaseModel):
    id: int
    name: str
    path: str
    level: int
    manager_id: int | None = None
    manager_name: str | None = None


class UserOptionOut(BaseModel):
    id: int
    username: str
    real_name: str
    dept_id: int | None = None
    dept_name: str | None = None
    status: int


class RoleOptionOut(BaseModel):
    code: str
    name: str
    data_scope: str


class ApprovalFlowOptionsOut(BaseModel):
    departments: list[DeptOptionOut] = Field(default_factory=list)
    users: list[UserOptionOut] = Field(default_factory=list)
    roles: list[RoleOptionOut] = Field(default_factory=list)


class ApprovalStepOut(BaseModel):
    step_no: int
    step_code: str
    step_name: str
    approve_mode: str
    status: str
    status_label: str
    approvers: list[str] = Field(default_factory=list)
    pending_approvers: list[str] = Field(default_factory=list)
    acted_at: datetime | None = None
    comment: str | None = None
