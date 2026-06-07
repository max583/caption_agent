"""Add llm_profiles table for named LLM configuration snapshots.

Revision ID: 0002_llm_profiles
Revises: 0001_initial
Create Date: 2026-05-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_llm_profiles"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("config_json", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_llm_profiles_name", "llm_profiles", ["name"])
    op.create_index("ix_llm_profiles_is_active", "llm_profiles", ["is_active"])


def downgrade() -> None:
    op.drop_table("llm_profiles")
