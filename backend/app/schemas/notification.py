from datetime import datetime

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: str
    category: str
    level: str
    title: str
    description: str
    occurred_at: datetime
    link: str | None = None


class NotificationSummary(BaseModel):
    items: list[NotificationItem]
    total: int
    warning_count: int
    danger_count: int
    generated_at: datetime
