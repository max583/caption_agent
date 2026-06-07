"""Add lora_type and base_model_family columns to projects.

Revision ID: 0006_project_lora_type
Revises: 0005_processing_started_at
Create Date: 2026-06-04
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_project_lora_type"
down_revision: Union[str, None] = "0005_processing_started_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "lora_type",
                sa.String(32),
                nullable=False,
                server_default="character",
            )
        )
        batch_op.add_column(
            sa.Column(
                "base_model_family",
                sa.String(64),
                nullable=False,
                server_default="flux",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("base_model_family")
        batch_op.drop_column("lora_type")
