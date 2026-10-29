from __future__ import annotations

from pydantic import BaseModel, Field


class ImportErrorItem(BaseModel):
    row: int
    message: str


class ImportResultOut(BaseModel):
    total: int
    success: int
    failed: int
    errors: list[ImportErrorItem] = Field(default_factory=list)
