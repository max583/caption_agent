"""LLMProfile ORM model — named snapshots of the full LLM configuration."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


class LLMProfile(Base, TimestampMixin):
    """A saved snapshot of {llm, llm_analyst, llm_normalizer, llm_checker} config blocks.

    Activating a profile copies its config_json values back into the `configuration`
    table. The pipeline reads the flat configuration table directly — it never
    touches this table.

    At most one row may have is_active=True. This invariant is enforced in the
    application layer (SQLite does not support partial unique indexes in stock builds).
    """

    __tablename__ = "llm_profiles"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    def __repr__(self) -> str:
        active = " [active]" if self.is_active else ""
        return f"<LLMProfile id={self.id} name={self.name!r}{active}>"
