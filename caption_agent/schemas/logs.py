"""Pydantic schemas for BusinessLog API endpoints (Journal)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models.enums import LogLevel


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    level: LogLevel
    event_type: str
    message: str
    project_id: int | None
    batch_id: int | None
    image_item_id: int | None
    details: dict[str, Any] | None


class LogFilter(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    level: LogLevel | None = None
    project_id: int | None = None
    batch_id: int | None = None
    event_type: str | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 50


class LogsPage(BaseModel):
    items: list[LogOut]
    total: int
    page: int
    page_size: int
    pages: int
