"""add caption_policy to projects

Revision ID: 0008_caption_policy
Revises: 0007_candidate_prompts
Create Date: 2026-06-07
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_caption_policy"
down_revision: Union[str, None] = "0007_candidate_prompts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("caption_policy", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("caption_policy")
