from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ReminderItem(BaseModel):
    id: str
    category: str
    category_label: str
    level: str
    level_label: str
    title: str
    description: str
    due_date: date | None = None
    days_left: int | None = None
    source_no: str | None = None
    owner: str | None = None
    link: str


class ReminderCategorySummary(BaseModel):
    category: str
    label: str
    count: int
    danger_count: int
    warning_count: int
    info_count: int
    link: str


class ReminderSummaryOut(BaseModel):
    total: int
    danger_count: int
    warning_count: int
    info_count: int
    categories: list[ReminderCategorySummary]
    email_enabled: bool
    generated_at: datetime


class ReminderPage(BaseModel):
    items: list[ReminderItem]
    total: int
    page: int
    page_size: int


class ReminderScanOut(BaseModel):
    warranty: int
    contract: int
    borrow: int
    inventory: int
    total: int
    created: int
    already_scanned: bool
    email_status: str
    generated_at: datetime
