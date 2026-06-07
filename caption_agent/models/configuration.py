"""Configuration key-value store (D-087).

Runtime configuration lives in this table; UI edits it. Bootstrap config (DB connection,
server host/port, app folder) lives in environment variables and pydantic-settings.

Values stored as JSON to support typed nested structures (per-step LLM config blocks etc.).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Configuration(Base, TimestampMixin):
    """One row per top-level config key (e.g. 'llm', 'llm_analyst', 'retry', 'polling')."""

    __tablename__ = "configuration"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any] | list[Any] | str | int | float | bool | None] = mapped_column(
        JSON, nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
