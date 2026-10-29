from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class TodoItemOut(BaseModel):
    key: str
    category: str
    category_label: str
    todo_type: str
    todo_type_label: str
    title: str
    subtitle: str | None = None
    doc_no: str
    status: str
    status_label: str
    related_name: str | None = None
    dept_name: str | None = None
    occurred_at: datetime | None = None
    due_date: date | None = None
    days_to_due: int | None = None
    is_overdue: bool = False
    link: str


class TodoTypeCountOut(BaseModel):
    todo_type: str
    label: str
    category: str
    count: int


class TodoCategoryOut(BaseModel):
    category: str
    label: str
    count: int
    types: list[TodoTypeCountOut]
    items: list[TodoItemOut]


class TodoSummaryOut(BaseModel):
    total: int
    categories: list[TodoCategoryOut]
    generated_at: datetime


class TodoPageOut(BaseModel):
    items: list[TodoItemOut]
    total: int
    page: int
    page_size: int
