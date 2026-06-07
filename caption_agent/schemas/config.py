"""Pydantic schemas for Config API endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ConfigOut(BaseModel):
    key: str
    value: Any
    description: str | None = None


class ConfigPatch(BaseModel):
    value: Any
