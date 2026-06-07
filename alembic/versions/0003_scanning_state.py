"""Add scan_progress column to batches for SCANNING state.

Revision ID: 0003_scanning_state
Revises: 0002_llm_profiles
Create Date: 2026-05-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_scanning_state"
down_revision: Union[str, None] = "0002_llm_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "batches",
        sa.Column("scan_progress", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("batches", "scan_progress")
