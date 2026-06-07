"""Batch state transitions per D-087.

Allowed transitions are defined as a set of (from, to) pairs. Pause/Resume and Error
are reachable from most active states.
"""

from __future__ import annotations

from ..models.enums import BatchState

# Active (non-terminal) states from which Pause and Error are reachable.
_ACTIVE_STATES = {
    BatchState.SCHEDULED,
    BatchState.QUEUED,
    BatchState.SCANNING,
    BatchState.PROCESSING,
    BatchState.AWAITING_REVIEW,
    BatchState.EXPORTING,
}

# Terminal states (no transitions out except deletion).
BATCH_TERMINAL_STATES: frozenset[BatchState] = frozenset({BatchState.DONE})


def _build_transitions() -> set[tuple[BatchState, BatchState]]:
    """Build the canonical allowed transitions set."""
    transitions: set[tuple[BatchState, BatchState]] = set()

    # Normal forward flow.
    transitions.add((BatchState.SCHEDULED, BatchState.QUEUED))
    transitions.add((BatchState.QUEUED, BatchState.SCANNING))
    transitions.add((BatchState.SCANNING, BatchState.PROCESSING))
    transitions.add((BatchState.QUEUED, BatchState.PROCESSING))  # kept for direct start if no scan needed
    transitions.add((BatchState.PROCESSING, BatchState.AWAITING_REVIEW))
    transitions.add((BatchState.AWAITING_REVIEW, BatchState.EXPORTING))
    transitions.add((BatchState.EXPORTING, BatchState.DONE))

    # Recovery: from Awaiting Review back to Processing if items need re-run.
    transitions.add((BatchState.AWAITING_REVIEW, BatchState.PROCESSING))

    # Pause and resume from active states.
    for state in _ACTIVE_STATES:
        transitions.add((state, BatchState.PAUSED))
        transitions.add((BatchState.PAUSED, state))

    # Error from any active state.
    for state in _ACTIVE_STATES:
        transitions.add((state, BatchState.ERROR))
    transitions.add((BatchState.PAUSED, BatchState.ERROR))

    # Recovery from Error: user can restart.
    transitions.add((BatchState.ERROR, BatchState.QUEUED))

    # Recovery from Awaiting Review: user regenerated items → back to queue.
    transitions.add((BatchState.AWAITING_REVIEW, BatchState.QUEUED))

    # Recovery from crash (auto-recovery): orphaned Processing → Queued.
    transitions.add((BatchState.PROCESSING, BatchState.QUEUED))

    return transitions


BATCH_TRANSITIONS: frozenset[tuple[BatchState, BatchState]] = frozenset(_build_transitions())


def is_valid_batch_transition(from_state: BatchState, to_state: BatchState) -> bool:
    """Check whether a batch transition is allowed."""
    return (from_state, to_state) in BATCH_TRANSITIONS


def is_batch_terminal(state: BatchState) -> bool:
    """Check whether a batch state is terminal."""
    return state in BATCH_TERMINAL_STATES
