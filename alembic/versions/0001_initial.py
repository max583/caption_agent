"""initial schema: projects, batches, image_items, state_history, error_stats, configuration, business_logs

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-26
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("default_source_type", sa.String(32), nullable=False),
        sa.Column("default_branch", sa.String(32), nullable=False),
        sa.Column("default_output_policy", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_projects_name", "projects", ["name"])

    op.create_table(
        "batches",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "project_id",
            sa.Integer,
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_folder_path", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("branch", sa.String(32), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("last_state_change_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schedule_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failure_counter", sa.Integer, nullable=False, server_default="0"),
        sa.Column("normalizer_max_retries_override", sa.Integer, nullable=True),
        sa.Column("consecutive_failure_threshold_override", sa.Integer, nullable=True),
        sa.Column("last_error_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_batches_project_id", "batches", ["project_id"])
    op.create_index("ix_batches_state", "batches", ["state"])
    op.create_index("ix_batches_schedule_at", "batches", ["schedule_at"])

    op.create_table(
        "image_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "batch_id",
            sa.Integer,
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("raw_analyst_output", sa.JSON, nullable=True),
        sa.Column("normalized_caption", sa.Text, nullable=True),
        sa.Column("final_caption", sa.Text, nullable=True),
        sa.Column("generation_prompt", sa.Text, nullable=True),
        sa.Column("provenance", sa.JSON, nullable=True),
        sa.Column("warnings", sa.JSON, nullable=True),
        sa.Column("llm_pass_result", sa.JSON, nullable=True),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("decision_notes", sa.Text, nullable=True),
        sa.Column("last_error_category", sa.String(32), nullable=True),
        sa.Column("last_error_message", sa.Text, nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalizer_attempt", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_id", "file_path", name="uq_image_items_batch_file"),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_image_items_batch_id", "image_items", ["batch_id"])
    op.create_index("ix_image_items_state", "image_items", ["state"])

    op.create_table(
        "batch_state_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "batch_id",
            sa.Integer,
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_batch_state_history_batch_id", "batch_state_history", ["batch_id"])
    op.create_index("ix_batch_state_history_changed_at", "batch_state_history", ["changed_at"])

    op.create_table(
        "item_state_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "image_item_id",
            sa.Integer,
            sa.ForeignKey("image_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_item_state_history_item_id", "item_state_history", ["image_item_id"])
    op.create_index("ix_item_state_history_changed_at", "item_state_history", ["changed_at"])

    op.create_table(
        "image_item_error_stats",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "image_item_id",
            sa.Integer,
            sa.ForeignKey("image_items.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("transient_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("permanent_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("policy_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("validation_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_image_item_error_stats_item_id", "image_item_error_stats", ["image_item_id"]
    )

    op.create_table(
        "configuration",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.JSON, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "business_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column(
            "project_id",
            sa.Integer,
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "batch_id",
            sa.Integer,
            sa.ForeignKey("batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "image_item_id",
            sa.Integer,
            sa.ForeignKey("image_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("details", sa.JSON, nullable=True),
    )
    op.create_index("ix_business_logs_timestamp", "business_logs", ["timestamp"])
    op.create_index("ix_business_logs_level", "business_logs", ["level"])
    op.create_index("ix_business_logs_event_type", "business_logs", ["event_type"])
    op.create_index("ix_business_logs_project_id", "business_logs", ["project_id"])
    op.create_index("ix_business_logs_batch_id", "business_logs", ["batch_id"])
    op.create_index("ix_business_logs_image_item_id", "business_logs", ["image_item_id"])


def downgrade() -> None:
    op.drop_table("business_logs")
    op.drop_table("configuration")
    op.drop_table("image_item_error_stats")
    op.drop_table("item_state_history")
    op.drop_table("batch_state_history")
    op.drop_table("image_items")
    op.drop_table("batches")
    op.drop_table("projects")
