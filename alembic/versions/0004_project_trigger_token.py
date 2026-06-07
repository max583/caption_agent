"""Add trigger_token column to projects.

Revision ID: 0004_project_trigger_token
Revises: 0003_scanning_state
Create Date: 2026-05-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_project_trigger_token"
down_revision: Union[str, None] = "0003_scanning_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "trigger_token",
            sa.String(128),
            nullable=False,
            server_default="p3rs0n4",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "trigger_token")
