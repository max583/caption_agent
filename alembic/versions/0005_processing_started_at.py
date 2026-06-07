"""Add processing_started_at column to batches.

Revision ID: 0005_processing_started_at
Revises: 0004_project_trigger_token
Create Date: 2026-06-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_processing_started_at"
down_revision: Union[str, None] = "0004_project_trigger_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "batches",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("batches", "processing_started_at")
