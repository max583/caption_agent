"""Pydantic schema for the server-wide summary endpoint."""

from __future__ import annotations

from pydantic import BaseModel


class ServerSummary(BaseModel):
    total_projects: int
    active_batches: int
    awaiting_review_items: int
    scheduled_batches: int
    error_batches: int
    queue_depth: int
