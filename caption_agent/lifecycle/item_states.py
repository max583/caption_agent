"""Image item state transitions per D-087."""

from __future__ import annotations

from ..models.enums import ItemState

ITEM_TERMINAL_STATES: frozenset[ItemState] = frozenset(
    {ItemState.DONE, ItemState.DROPPED}
)


def _build_transitions() -> set[tuple[ItemState, ItemState]]:
    transitions: set[tuple[ItemState, ItemState]] = set()

    # Forward pipeline flow.
    transitions.add((ItemState.QUEUED, ItemState.READING_CONTEXT))
    transitions.add((ItemState.READING_CONTEXT, ItemState.ANALYZING))
    transitions.add((ItemState.ANALYZING, ItemState.NORMALIZING))
    transitions.add((ItemState.NORMALIZING, ItemState.RULE_CHECK))
    transitions.add((ItemState.RULE_CHECK, ItemState.GAP_FILLING))
    transitions.add((ItemState.GAP_FILLING, ItemState.LLM_PASS_CHECK))
    # Direct exit from RULE_CHECK to AWAITING_REVIEW for MULTI_CHARACTER sentinel
    # (normalizer returns a non-caption string; remaining pipeline steps are skipped).
    transitions.add((ItemState.RULE_CHECK, ItemState.AWAITING_REVIEW))
    transitions.add((ItemState.LLM_PASS_CHECK, ItemState.AWAITING_REVIEW))

    # Self-retry loop (normalizer): RuleCheck or LLMPassCheck fails policy → back to normalizing.
    transitions.add((ItemState.RULE_CHECK, ItemState.NORMALIZING))
    transitions.add((ItemState.LLM_PASS_CHECK, ItemState.NORMALIZING))

    # User decisions after AWAITING_REVIEW.
    transitions.add((ItemState.AWAITING_REVIEW, ItemState.APPROVED))
    transitions.add((ItemState.AWAITING_REVIEW, ItemState.REGENERATING))
    transitions.add((ItemState.AWAITING_REVIEW, ItemState.DROPPED))
    transitions.add((ItemState.AWAITING_REVIEW, ItemState.SKIPPED))
    # Skip is sticky until next review session — back to AWAITING_REVIEW eventually.
    transitions.add((ItemState.SKIPPED, ItemState.AWAITING_REVIEW))

    # Regenerate re-enters normalizer.
    transitions.add((ItemState.REGENERATING, ItemState.NORMALIZING))

    # Approved items go to exporting then done.
    transitions.add((ItemState.APPROVED, ItemState.EXPORTING))
    transitions.add((ItemState.EXPORTING, ItemState.DONE))

    # Error reachable from any non-terminal active state.
    active = {
        ItemState.QUEUED,
        ItemState.READING_CONTEXT,
        ItemState.ANALYZING,
        ItemState.NORMALIZING,
        ItemState.GAP_FILLING,
        ItemState.RULE_CHECK,
        ItemState.LLM_PASS_CHECK,
        ItemState.AWAITING_REVIEW,
        ItemState.REGENERATING,
        ItemState.EXPORTING,
    }
    for state in active:
        transitions.add((state, ItemState.ERROR))

    # Recovery from Error: user retry → re-queue; user drop → DROPPED.
    transitions.add((ItemState.ERROR, ItemState.QUEUED))
    transitions.add((ItemState.ERROR, ItemState.DROPPED))

    # Crash recovery: orphaned active items → QUEUED on server start.
    for state in {
        ItemState.READING_CONTEXT,
        ItemState.ANALYZING,
        ItemState.NORMALIZING,
        ItemState.GAP_FILLING,
        ItemState.RULE_CHECK,
        ItemState.LLM_PASS_CHECK,
        ItemState.EXPORTING,
        ItemState.REGENERATING,
    }:
        transitions.add((state, ItemState.QUEUED))

    return transitions


ITEM_TRANSITIONS: frozenset[tuple[ItemState, ItemState]] = frozenset(_build_transitions())


def is_valid_item_transition(from_state: ItemState, to_state: ItemState) -> bool:
    """Check whether an item state transition is allowed."""
    return (from_state, to_state) in ITEM_TRANSITIONS


def is_item_terminal(state: ItemState) -> bool:
    """Check whether an item state is terminal."""
    return state in ITEM_TERMINAL_STATES
