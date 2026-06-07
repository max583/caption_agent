"""Tests for state machine transition rules."""

from __future__ import annotations

from caption_agent.lifecycle import (
    is_batch_terminal,
    is_item_terminal,
    is_valid_batch_transition,
    is_valid_item_transition,
)
from caption_agent.models.enums import BatchState, ItemState


# ---- Batch transitions ----


def test_batch_normal_flow() -> None:
    assert is_valid_batch_transition(BatchState.SCHEDULED, BatchState.QUEUED)
    assert is_valid_batch_transition(BatchState.QUEUED, BatchState.PROCESSING)
    assert is_valid_batch_transition(BatchState.PROCESSING, BatchState.AWAITING_REVIEW)
    assert is_valid_batch_transition(BatchState.AWAITING_REVIEW, BatchState.EXPORTING)
    assert is_valid_batch_transition(BatchState.EXPORTING, BatchState.DONE)


def test_batch_pause_resume() -> None:
    assert is_valid_batch_transition(BatchState.PROCESSING, BatchState.PAUSED)
    assert is_valid_batch_transition(BatchState.PAUSED, BatchState.PROCESSING)
    assert is_valid_batch_transition(BatchState.AWAITING_REVIEW, BatchState.PAUSED)


def test_batch_error_from_any_active() -> None:
    assert is_valid_batch_transition(BatchState.QUEUED, BatchState.ERROR)
    assert is_valid_batch_transition(BatchState.PROCESSING, BatchState.ERROR)
    assert is_valid_batch_transition(BatchState.AWAITING_REVIEW, BatchState.ERROR)


def test_batch_error_recovery_to_queued() -> None:
    assert is_valid_batch_transition(BatchState.ERROR, BatchState.QUEUED)


def test_batch_crash_recovery() -> None:
    assert is_valid_batch_transition(BatchState.PROCESSING, BatchState.QUEUED)


def test_batch_done_is_terminal() -> None:
    assert is_batch_terminal(BatchState.DONE)
    assert not is_batch_terminal(BatchState.PROCESSING)


def test_batch_invalid_transitions() -> None:
    assert not is_valid_batch_transition(BatchState.DONE, BatchState.QUEUED)
    assert not is_valid_batch_transition(BatchState.QUEUED, BatchState.DONE)


# ---- Item transitions ----


def test_item_pipeline_flow() -> None:
    assert is_valid_item_transition(ItemState.QUEUED, ItemState.READING_CONTEXT)
    assert is_valid_item_transition(ItemState.READING_CONTEXT, ItemState.ANALYZING)
    assert is_valid_item_transition(ItemState.ANALYZING, ItemState.NORMALIZING)
    assert is_valid_item_transition(ItemState.NORMALIZING, ItemState.RULE_CHECK)
    assert is_valid_item_transition(ItemState.RULE_CHECK, ItemState.GAP_FILLING)
    assert is_valid_item_transition(ItemState.GAP_FILLING, ItemState.LLM_PASS_CHECK)
    assert is_valid_item_transition(ItemState.LLM_PASS_CHECK, ItemState.AWAITING_REVIEW)


def test_item_self_retry_loop() -> None:
    assert is_valid_item_transition(ItemState.RULE_CHECK, ItemState.NORMALIZING)
    assert is_valid_item_transition(ItemState.LLM_PASS_CHECK, ItemState.NORMALIZING)


def test_item_user_decisions() -> None:
    assert is_valid_item_transition(ItemState.AWAITING_REVIEW, ItemState.APPROVED)
    assert is_valid_item_transition(ItemState.AWAITING_REVIEW, ItemState.REGENERATING)
    assert is_valid_item_transition(ItemState.AWAITING_REVIEW, ItemState.DROPPED)
    assert is_valid_item_transition(ItemState.AWAITING_REVIEW, ItemState.SKIPPED)


def test_item_regenerate_re_enters_normalizer() -> None:
    assert is_valid_item_transition(ItemState.REGENERATING, ItemState.NORMALIZING)


def test_item_approved_exports() -> None:
    assert is_valid_item_transition(ItemState.APPROVED, ItemState.EXPORTING)
    assert is_valid_item_transition(ItemState.EXPORTING, ItemState.DONE)


def test_item_error_recovery() -> None:
    assert is_valid_item_transition(ItemState.ERROR, ItemState.QUEUED)
    assert is_valid_item_transition(ItemState.ERROR, ItemState.DROPPED)


def test_item_terminal_states() -> None:
    assert is_item_terminal(ItemState.DONE)
    assert is_item_terminal(ItemState.DROPPED)
    assert not is_item_terminal(ItemState.AWAITING_REVIEW)
