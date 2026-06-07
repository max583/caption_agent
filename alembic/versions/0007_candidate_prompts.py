"""Add candidate_prompts column to image_items (D-102).

Revision ID: 0007_candidate_prompts
Revises: 0006_project_lora_type
Create Date: 2026-06-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_candidate_prompts"
down_revision: Union[str, None] = "0006_project_lora_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("image_items") as batch_op:
        batch_op.add_column(
            sa.Column("candidate_prompts", sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("image_items") as batch_op:
        batch_op.drop_column("candidate_prompts")
