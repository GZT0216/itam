from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class SearchItemOut(BaseModel):
    type: Literal["asset", "user", "dept"]
    id: int
    title: str
    subtitle: str | None = None
    keyword: str


class SearchResultOut(BaseModel):
    keyword: str
    items: list[SearchItemOut]
