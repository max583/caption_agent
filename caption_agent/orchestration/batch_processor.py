"""Batch processor: drives the per-image pipeline for one batch (D-087, D-097, D-102).

Processing flow per image:
  QUEUED → ReadingContext → Analyzing →
  [Normalizing ⇌ RuleCheck ⇌ LLMPassCheck] → AwaitingReview (item-level)

The Normalizing → RuleCheck → LLMPassCheck loop shares a single attempt
counter (D-097): both rule-checker and LLM-checker violations feed back to the
normalizer; the limit applies across both checker types combined.

After all items reach a terminal-or-review state the batch transitions to
``AWAITING_REVIEW``.  The user review phase (Accept / Regenerate / Drop / Skip)
and the subsequent ``Exporting`` phase are driven by the REST API (Phase 3).

Error handling:
- ``LLMValidationError`` → retry up to ``max_validation_retries`` with temperature +0.1.
- ``LLMTransientError``  → already retried inside the client; item re-queued (not ERROR)
  so that fixing the LLM endpoint and resuming the batch is sufficient to recover.
  A separate in-memory ``consecutive_network_failures`` counter tracks consecutive
  transient errors; when it reaches ``consecutive_failure_threshold`` the batch is
  paused (not ERROR) so the user can fix the endpoint and resume.
- ``LLMPermanentError``  → item ERROR, permanent category.
- Normalizer policy violations after ``max_normalizer_retries`` → item ERROR, policy.
- ``consecutive_failure_counter`` on the batch halts the batch to ERROR on systemic
  permanent failure.
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from ..config.manager import ConfigManager
from ..config.schema import LLMConfig, LoggingConfig, RetryConfig
from ..schemas.policy import CaptionPolicyConfig, get_project_policy
from ..lifecycle.batch_states import is_valid_batch_transition
from ..lifecycle.item_states import is_valid_item_transition
from ..llm.client import LLMClient, LLMPermanentError, LLMTransientError, LLMValidationError, is_thinking_model
from ..llm.per_step_dispatch import make_client_for_step
from ..logging_setup.business_logger import BusinessLogger
from ..logging_setup.llm_io_dumper import LLMIODumper
from ..logging_setup.system_logger import get_system_logger
from ..models import Batch, BatchStateHistory, ImageItem, ImageItemErrorStats, ItemStateHistory
from ..models.enums import BatchState, ErrorCategory, ItemState
from ..pipeline import analyst, context_reader, llm_pass_checker, normalizer, rule_checker
from ..storage.session import session_scope

_MAX_VALIDATION_RETRIES = 3  # per-step temperature-bump retries for malformed JSON


class _StepResult(Enum):
    """Outcome of a single pipeline step or the whole item run."""
    OK = auto()
    TRANSIENT = auto()   # LLM unreachable — item re-queued; batch should pause on threshold
    PERMANENT = auto()   # Unrecoverable error — item set to ERROR


# ---------------------------------------------------------------------------
# Public entry point (runs synchronously in a thread via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _clear_max_tokens_for_thinking(cfg: LLMConfig) -> LLMConfig:
    """Return a copy of cfg with max_tokens cleared if the model is a thinking model."""
    if is_thinking_model(cfg.model_id) and cfg.max_tokens and cfg.max_tokens > 0:
        return cfg.model_copy(update={"max_tokens": 0})
    return cfg


def run_batch(batch_id: int) -> None:
    """Process one batch synchronously.  Designed to run in a thread pool."""
    log = get_system_logger()
    log.info("BatchProcessor: starting batch %d", batch_id)

    # Load config once per batch run.
    with session_scope() as session:
        mgr = ConfigManager(session)
        retry_cfg = RetryConfig.model_validate(mgr.get("retry") or {})
        logging_cfg = LoggingConfig.model_validate(mgr.get("logging") or {})
        analyst_cfg = mgr.get_effective_llm_for_step("analyst")
        normalizer_cfg = mgr.get_effective_llm_for_step("normalizer")
        checker_cfg = mgr.get_effective_llm_for_step("checker")

    # For thinking/reasoning models (Qwen3, DeepSeek-R1, …) the token budget is
    # shared between the hidden chain-of-thought and the visible response.  A low
    # max_tokens cap causes content=null when the thinking phase exhausts the budget
    # before any output is produced.  Clear the cap so the model can finish.
    for _name, _cfg in (
        ("analyst", analyst_cfg),
        ("normalizer", normalizer_cfg),
        ("checker", checker_cfg),
    ):
        if is_thinking_model(_cfg.model_id) and _cfg.max_tokens and _cfg.max_tokens > 0:
            log.info(
                "BatchProcessor: %s uses thinking model %r — disabling max_tokens cap (%d)",
                _name, _cfg.model_id, _cfg.max_tokens,
            )
    analyst_cfg = _clear_max_tokens_for_thinking(analyst_cfg)
    normalizer_cfg = _clear_max_tokens_for_thinking(normalizer_cfg)
    checker_cfg = _clear_max_tokens_for_thinking(checker_cfg)

    # Determine dump directory relative to DB location.
    from ..config.bootstrap import get_bootstrap_settings  # noqa: PLC0415

    settings = get_bootstrap_settings()
    dump_dir = settings.llm_io_dir
    dumper = LLMIODumper(dump_dir=dump_dir, enabled=logging_cfg.debug_dump_llm_io)

    # ── SCANNING PHASE ─────────────────────────────────────────────────────────
    # Run context_reader for every item before starting any LLM work.
    # Only run when coming from QUEUED state (fresh start).
    # Re-runs from AWAITING_REVIEW (after user re-queues items) skip this phase —
    # generation_prompt is already populated from the first run.
    with session_scope() as session:
        batch_row_init = session.get(Batch, batch_id)
        if batch_row_init is None:
            return
        project_id: int = batch_row_init.project_id
        _do_scan = batch_row_init.state == BatchState.QUEUED
        from ..models import Project  # noqa: PLC0415
        _project = session.get(Project, project_id)
        trigger_token: str = _project.trigger_token if _project else "p3rs0n4"
        lora_type: str = _project.lora_type.value if _project else "character"
        policy: CaptionPolicyConfig = get_project_policy(_project) if _project else CaptionPolicyConfig()

    if _do_scan:
        if not _transition_batch(batch_id, BatchState.SCANNING, reason="scan_started"):
            log.warning("BatchProcessor: batch %d could not transition to SCANNING — skipping", batch_id)
            return

        with session_scope() as session:
            all_item_ids: list[int] = [
                i.id for i in session.query(ImageItem.id)
                .filter(ImageItem.batch_id == batch_id)
                .order_by(ImageItem.id)
                .all()
            ]

        total_items = len(all_item_ids)
        log.info("BatchProcessor: batch %d — scanning %d items", batch_id, total_items)

        for scan_idx, item_id in enumerate(all_item_ids):
            with session_scope() as session:
                batch_check = session.get(Batch, batch_id)
                if batch_check is None:
                    log.warning("BatchProcessor: batch %d disappeared during scan", batch_id)
                    return

            _scan_item_context(item_id)

            scanned = scan_idx + 1
            with session_scope() as session:
                batch_check = session.get(Batch, batch_id)
                if batch_check:
                    batch_check.scan_progress = scanned
            log.debug("[scan] batch %d — %d/%d items scanned", batch_id, scanned, total_items)

        log.info("BatchProcessor: batch %d — scan complete, starting captioning", batch_id)

    # ── PROCESSING PHASE ───────────────────────────────────────────────────────
    if not _transition_batch(batch_id, BatchState.PROCESSING, reason="processing_started"):
        log.warning("BatchProcessor: batch %d could not transition to PROCESSING after scan", batch_id)
        return

    # Collect item IDs that need LLM processing (QUEUED or crash-recovered in-flight states).
    with session_scope() as session:
        items = (
            session.query(ImageItem)
            .filter(
                ImageItem.batch_id == batch_id,
                ImageItem.state.in_([
                    ItemState.QUEUED,
                    ItemState.READING_CONTEXT,
                    ItemState.ANALYZING,
                    ItemState.NORMALIZING,
                    ItemState.RULE_CHECK,
                    ItemState.LLM_PASS_CHECK,
                    ItemState.REGENERATING,
                    # GAP_FILLING kept for crash-recovery of items left in-flight from
                    # pre-D-102 batches; the state enum member is deprecated but still valid.
                    ItemState.GAP_FILLING,
                ]),
            )
            .order_by(ImageItem.id)
            .all()
        )
        item_ids = [i.id for i in items]

    log.info("BatchProcessor: batch %d — %d items to process", batch_id, len(item_ids))


    # Read the effective consecutive-failure threshold once (respects per-batch override).
    with session_scope() as session:
        batch_row = session.get(Batch, batch_id)
        effective_threshold = (
            batch_row.consecutive_failure_threshold_override
            if batch_row and batch_row.consecutive_failure_threshold_override
            else retry_cfg.consecutive_failure_threshold
        )

    # In-memory counter for consecutive network (transient) failures.
    # Resets on any successful item or on resume, so recovering the endpoint is enough.
    consecutive_network_failures = 0

    with LLMClient(analyst_cfg) as analyst_client, \
         LLMClient(normalizer_cfg) as norm_client, \
         LLMClient(checker_cfg) as checker_client:

        for item_id in item_ids:
            # Soft-pause check: stop processing if batch was paused via API.
            with session_scope() as session:
                batch = session.get(Batch, batch_id)
                if batch is None:
                    log.warning("BatchProcessor: batch %d disappeared, stopping", batch_id)
                    return
                if batch.state == BatchState.PAUSED:
                    log.info("BatchProcessor: batch %d is PAUSED — stopping before item %d", batch_id, item_id)
                    return

            result = _process_item(
                project_id=project_id,
                batch_id=batch_id,
                item_id=item_id,
                analyst_client=analyst_client,
                normalizer_client=norm_client,
                checker_client=checker_client,
                retry_cfg=retry_cfg,
                dumper=dumper,
                trigger_token=trigger_token,
                lora_type=lora_type,
                policy=policy,
            )

            if result == _StepResult.TRANSIENT:
                consecutive_network_failures += 1
                log.warning(
                    "BatchProcessor: batch %d transient network error on item %d "
                    "(%d consecutive network failure(s))",
                    batch_id, item_id, consecutive_network_failures,
                )
                if consecutive_network_failures >= effective_threshold:
                    log.error(
                        "BatchProcessor: batch %d paused — %d consecutive network failures",
                        batch_id, consecutive_network_failures,
                    )
                    _transition_batch(
                        batch_id,
                        BatchState.PAUSED,
                        reason=f"network_failure_threshold_{consecutive_network_failures}_exceeded",
                    )
                    return
            elif result == _StepResult.PERMANENT:
                consecutive_network_failures = 0
                # Check global consecutive-failure counter (permanent / policy errors).
                if _consecutive_failures_exceeded(batch_id, retry_cfg.consecutive_failure_threshold):
                    log.error(
                        "BatchProcessor: batch %d halted — consecutive failure threshold exceeded",
                        batch_id,
                    )
                    _transition_batch(
                        batch_id,
                        BatchState.ERROR,
                        reason=f"consecutive_failure_threshold_{retry_cfg.consecutive_failure_threshold}_exceeded",
                    )
                    return
            else:
                # Successful item — reset both counters.
                consecutive_network_failures = 0
                _reset_batch_failure_counter(batch_id)

    # All items processed — move batch to AWAITING_REVIEW.
    _transition_batch(batch_id, BatchState.AWAITING_REVIEW, reason="all_items_processed")
    log.info("BatchProcessor: batch %d → AWAITING_REVIEW", batch_id)


# ---------------------------------------------------------------------------
# Per-image processing
# ---------------------------------------------------------------------------


def _process_item(
    *,
    project_id: int,
    batch_id: int,
    item_id: int,
    analyst_client: LLMClient,
    normalizer_client: LLMClient,
    checker_client: LLMClient,
    retry_cfg: RetryConfig,
    dumper: LLMIODumper,
    trigger_token: str = "p3rs0n4",
    lora_type: str = "character",
    policy: CaptionPolicyConfig | None = None,
) -> _StepResult:
    """Drive one image through all pipeline steps; return the outcome."""
    log = get_system_logger()

    with session_scope() as _s:
        _item = _s.get(ImageItem, item_id)
        _name = _item.file_name if _item else str(item_id)
    log.debug("BatchProcessor: ── item %d [%s] start ──", item_id, _name)

    # Step 1: Context Reader (non-LLM).
    if not _run_non_llm_step(
        item_id=item_id,
        target_state=ItemState.READING_CONTEXT,
        step_fn=context_reader.run,
        error_category=ErrorCategory.PERMANENT,
        dumper=dumper,
        step_name="context_reader",
    ):
        return _StepResult.PERMANENT

    # Step 2: Analyst (VLM).
    result = _run_llm_step(
        item_id=item_id,
        target_state=ItemState.ANALYZING,
        step_fn=analyst.run,
        client=analyst_client,
        step_name="analyst",
        project_id=project_id,
        batch_id=batch_id,
        dumper=dumper,
    )
    if result != _StepResult.OK:
        if result == _StepResult.PERMANENT:
            _record_batch_failure(batch_id)
        return result

    # Steps 3-5: Normalizer → RuleCheck → LLMPassCheck shared-limit loop (D-097, D-102).
    # MULTI_CHARACTER short-circuit and llm_pass_checker are handled inside
    # _run_normalizer_loop; they share the same attempt counter.
    result = _run_normalizer_loop(
        item_id=item_id,
        normalizer_client=normalizer_client,
        checker_client=checker_client,
        max_retries=retry_cfg.normalizer_max_self_retries,
        project_id=project_id,
        batch_id=batch_id,
        dumper=dumper,
        trigger_token=trigger_token,
        lora_type=lora_type,
        policy=policy,
    )
    if result != _StepResult.OK:
        if result == _StepResult.PERMANENT:
            _record_batch_failure(batch_id)
        return result

    # Transition to item-level AWAITING_REVIEW and clear any stale error fields
    # (e.g. left over from a prior failed run that later recovered).
    _transition_item(item_id, ItemState.AWAITING_REVIEW, reason="pipeline_complete")
    _clear_item_error(item_id)
    log.debug("BatchProcessor: ── item %d [%s] → AWAITING_REVIEW ──", item_id, _name)
    return _StepResult.OK


# ---------------------------------------------------------------------------
# Scan helper (SCANNING phase — no state transitions on items)
# ---------------------------------------------------------------------------


def _scan_item_context(item_id: int) -> None:
    """Run context_reader for one item without changing its lifecycle state.

    Sets generation_prompt / provenance on the item in-place so the analyst
    has the correct generation intent when the LLM phase runs.
    Any extraction error is logged as a warning and silently skipped so
    one bad PNG does not block the rest of the batch.
    """
    log = get_system_logger()
    try:
        with session_scope() as session:
            item = session.get(ImageItem, item_id)
            if item is None:
                return
            context_reader.run(item, session)
            log.debug("[scan] item %d (%s) — candidates: %d",
                      item_id, item.file_name,
                      len(item.candidate_prompts or []))
    except (StaleDataError, IntegrityError):
        log.warning("[scan] item %d no longer exists in DB — skipped", item_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("[scan] context_reader failed for item %d: %s", item_id, exc)


# ---------------------------------------------------------------------------
# Step runners
# ---------------------------------------------------------------------------


def _run_non_llm_step(
    *,
    item_id: int,
    target_state: ItemState,
    step_fn: Any,
    error_category: ErrorCategory,
    dumper: LLMIODumper,
    step_name: str,
) -> bool:
    """Run a non-LLM step; return True on success, False on error (item set to ERROR)."""
    _transition_item(item_id, target_state)
    try:
        with session_scope() as session:
            item = session.get(ImageItem, item_id)
            if item is None:
                return False
            step_fn(item, session)
    except Exception as exc:  # noqa: BLE001
        _set_item_error(item_id, error_category, str(exc))
        get_system_logger().error("Step %s failed for item %d: %s", step_name, item_id, exc)
        return False
    return True


def _run_llm_step(
    *,
    item_id: int,
    target_state: ItemState,
    step_fn: Any,
    client: LLMClient,
    step_name: str,
    project_id: int,
    batch_id: int,
    dumper: LLMIODumper,
    extra_kwargs: dict[str, Any] | None = None,
) -> _StepResult:
    """Run an LLM step with validation-error retries.  Return a _StepResult."""
    _transition_item(item_id, target_state)
    client.set_dump_context(dumper=dumper if dumper.is_enabled() else None,
                            project_id=project_id, batch_id=batch_id,
                            item_id=item_id, step=step_name)
    base_temp = client._config.temperature
    last_exc: Exception | None = None

    for attempt in range(_MAX_VALIDATION_RETRIES):
        temp = (base_temp + 0.1 * attempt) if attempt > 0 else None
        try:
            with session_scope() as session:
                item = session.get(ImageItem, item_id)
                if item is None:
                    return _StepResult.PERMANENT
                kwargs: dict[str, Any] = {"temperature": temp}
                if extra_kwargs:
                    kwargs.update(extra_kwargs)
                step_fn(item, session, client, **kwargs)
            return _StepResult.OK
        except StaleDataError:
            get_system_logger().warning(
                "Step %s: item %d vanished from DB (batch deleted mid-run) — skipping",
                step_name, item_id,
            )
            return _StepResult.PERMANENT
        except LLMValidationError as exc:
            last_exc = exc
            _increment_error_stat(item_id, ErrorCategory.VALIDATION)
            get_system_logger().warning(
                "Step %s validation error for item %d (attempt %d): %s",
                step_name, item_id, attempt + 1, exc,
            )
        except LLMPermanentError as exc:
            _set_item_error(item_id, ErrorCategory.PERMANENT, str(exc))
            get_system_logger().error("Step %s permanent error for item %d: %s", step_name, item_id, exc)
            return _StepResult.PERMANENT
        except LLMTransientError as exc:
            _requeue_item(item_id, f"transient error in {step_name}: {exc}")
            get_system_logger().warning(
                "Step %s transient error for item %d — re-queued: %s", step_name, item_id, exc
            )
            return _StepResult.TRANSIENT
        except Exception as exc:  # noqa: BLE001
            _set_item_error(item_id, ErrorCategory.PERMANENT, str(exc))
            get_system_logger().error("Step %s unexpected error for item %d: %s", step_name, item_id, exc)
            return _StepResult.PERMANENT

    _set_item_error(
        item_id,
        ErrorCategory.VALIDATION,
        f"Step {step_name} failed after {_MAX_VALIDATION_RETRIES} attempts: {last_exc}",
    )
    return _StepResult.PERMANENT


def _run_normalizer_loop(
    *,
    item_id: int,
    normalizer_client: LLMClient,
    checker_client: LLMClient,
    max_retries: int,
    project_id: int,
    batch_id: int,
    dumper: LLMIODumper,
    trigger_token: str = "p3rs0n4",
    lora_type: str = "character",
    policy: CaptionPolicyConfig | None = None,
) -> _StepResult:
    """Normalizer → RuleCheck → LLMPassCheck shared-limit loop (D-087, D-097, D-102).

    A single attempt counter covers rule-checker AND LLM-checker violations.  On each
    iteration the normalizer is re-run with feedback from whichever checker fired last.
    After ``max_retries`` full attempts any remaining LLM-checker warnings are surfaced
    to the reviewer as soft flags (AWAITING_REVIEW) rather than ERROR.
    """
    normalizer_client.set_dump_context(
        dumper=dumper if dumper.is_enabled() else None,
        project_id=project_id,
        batch_id=batch_id,
        item_id=item_id,
        step="normalizer",
    )
    feedback: list[dict[str, str]] | None = None

    for attempt in range(max_retries + 1):
        # Transition to NORMALIZING.
        _transition_item(item_id, ItemState.NORMALIZING)
        _set_normalizer_attempt(item_id, attempt)

        base_temp = normalizer_client._config.temperature
        norm_ok = False
        last_norm_exc: Exception | None = None

        # Normalizer call with validation-error retries.
        for val_attempt in range(_MAX_VALIDATION_RETRIES):
            temp = (base_temp + 0.1 * val_attempt) if val_attempt > 0 else None
            try:
                with session_scope() as session:
                    item = session.get(ImageItem, item_id)
                    if item is None:
                        return _StepResult.PERMANENT
                    normalizer.run(item, session, normalizer_client, temperature=temp, feedback=feedback, trigger_token=trigger_token, lora_type=lora_type, policy=policy)
                norm_ok = True
                break
            except StaleDataError:
                # Item was deleted (batch deleted while processing) — nothing to do.
                get_system_logger().warning(
                    "Normalizer: item %d vanished from DB (batch deleted mid-run) — skipping",
                    item_id,
                )
                return _StepResult.PERMANENT
            except LLMValidationError as exc:
                last_norm_exc = exc
                _increment_error_stat(item_id, ErrorCategory.VALIDATION)
            except LLMPermanentError as exc:
                _set_item_error(item_id, ErrorCategory.PERMANENT, str(exc))
                return _StepResult.PERMANENT
            except LLMTransientError as exc:
                _requeue_item(item_id, f"transient error in normalizer: {exc}")
                get_system_logger().warning(
                    "Normalizer transient error for item %d — re-queued: %s", item_id, exc
                )
                return _StepResult.TRANSIENT
            except Exception as exc:  # noqa: BLE001
                _set_item_error(item_id, ErrorCategory.PERMANENT, str(exc))
                return _StepResult.PERMANENT

        if not norm_ok:
            _set_item_error(
                item_id,
                ErrorCategory.VALIDATION,
                f"Normalizer failed after {_MAX_VALIDATION_RETRIES} validation attempts: {last_norm_exc}",
            )
            return _StepResult.PERMANENT

        # Rule check.
        _transition_item(item_id, ItemState.RULE_CHECK)
        with session_scope() as session:
            item = session.get(ImageItem, item_id)
            if item is None:
                return _StepResult.PERMANENT
            batch = item.batch
            src_type = batch.source_type if batch else None
            branch = batch.branch if batch else None
            caption = item.normalized_caption or ""
            analyst_out = item.raw_analyst_output

        from ..models.enums import BranchType, SourceType  # noqa: PLC0415

        warnings = rule_checker.check(
            caption,
            source_type=src_type or SourceType.SYNTHETIC,
            branch=branch or BranchType.IDENTITY,
            analyst_output=analyst_out,
            trigger_token=trigger_token,
            lora_type=lora_type,
            policy=policy,
        )

        # Save warnings.
        with session_scope() as session:
            item = session.get(ImageItem, item_id)
            if item is None:
                return _StepResult.PERMANENT
            tagged = [{**w, "source": "rule_checker"} for w in warnings]
            item.warnings = tagged or None

        if not warnings:
            get_system_logger().debug(
                "[rule_checker] item %d attempt %d — OK, no violations",
                item_id, attempt + 1,
            )
            # Rule check clean — run llm_pass_checker within the same shared attempt counter (D-097).
            chk_result = _run_llm_step(
                item_id=item_id,
                target_state=ItemState.LLM_PASS_CHECK,
                step_fn=llm_pass_checker.run,
                client=checker_client,
                step_name="llm_pass_checker",
                project_id=project_id,
                batch_id=batch_id,
                dumper=dumper,
                extra_kwargs={"trigger_token": trigger_token, "lora_type": lora_type, "policy": policy},
            )
            if chk_result != _StepResult.OK:
                if chk_result == _StepResult.PERMANENT:
                    _record_batch_failure(batch_id)
                return chk_result

            # Read warnings written by llm_pass_checker.
            with session_scope() as _s:
                _chk_item = _s.get(ImageItem, item_id)
                llm_warnings: list[dict[str, str]] = [
                    w for w in (_chk_item.warnings or [])
                    if w.get("source") == "llm_pass_checker"
                ] if _chk_item else []

            if not llm_warnings:
                # Fully clean — proceed to AWAITING_REVIEW.
                return _StepResult.OK

            if attempt >= max_retries:
                # Last attempt — surface LLM warnings to reviewer as soft flags.
                get_system_logger().warning(
                    "BatchProcessor: item %d → AWAITING_REVIEW "
                    "(llm_pass_checker warnings after %d attempt(s))",
                    item_id, max_retries + 1,
                )
                return _StepResult.OK

            # Retries remain — feed LLM warnings back to normalizer.
            feedback = llm_warnings  # type: ignore[assignment]
            _increment_error_stat(item_id, ErrorCategory.POLICY)
            get_system_logger().debug(
                "[llm_pass_checker] item %d attempt %d/%d — %d violation(s), retrying: %s",
                item_id, attempt + 1, max_retries + 1,
                len(llm_warnings), [w.get("code") for w in llm_warnings],
            )
            continue

        # MULTI_CHARACTER sentinel: normalizer correctly identified a multi-person image.
        # This is not a fixable policy violation — retrying will not help.
        # Surface to reviewer immediately with only the MULTI_CHARACTER warning.
        if len(warnings) == 1 and warnings[0]["code"] == "MULTI_CHARACTER":
            get_system_logger().debug(
                "[rule_checker] item %d — MULTI_CHARACTER sentinel, skipping retry",
                item_id,
            )
            return _StepResult.OK

        # Violations found — provide feedback for next normalizer attempt.
        feedback = warnings  # type: ignore[assignment]
        _increment_error_stat(item_id, ErrorCategory.POLICY)
        get_system_logger().debug(
            "[rule_checker] item %d attempt %d/%d — %d violation(s): %s",
            item_id, attempt + 1, max_retries + 1,
            len(warnings), [w["code"] for w in warnings],
        )

    # Exhausted retries.
    # Soft fallback (D-099): if only SLOT_MISSING remains, surface to reviewer rather
    # than ERROR — a partially-complete caption is recoverable by a human in the textarea.
    remaining_codes = {w["code"] for w in (feedback or [])}
    if remaining_codes <= {"SLOT_MISSING"}:
        with session_scope() as session:
            item = session.get(ImageItem, item_id)
            if item is not None:
                item.warnings = [
                    {**w, "source": "rule_checker"} for w in (feedback or [])
                ]
        _transition_item(item_id, ItemState.AWAITING_REVIEW, reason="slot_missing_soft_fallback")
        _clear_item_error(item_id)
        get_system_logger().warning(
            "BatchProcessor: item %d → AWAITING_REVIEW (soft fallback, SLOT_MISSING after %d attempts)",
            item_id, max_retries + 1,
        )
        return _StepResult.OK

    # Hard policy error — unrecoverable violations remain.
    _set_item_error(
        item_id,
        ErrorCategory.POLICY,
        f"Caption policy violations after {max_retries + 1} normalizer attempts: "
        + ", ".join(w["code"] for w in (feedback or [])),
    )
    return _StepResult.PERMANENT


# ---------------------------------------------------------------------------
# State transition helpers
# ---------------------------------------------------------------------------


def _transition_batch(
    batch_id: int,
    to_state: BatchState,
    *,
    reason: str | None = None,
) -> bool:
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        batch = session.get(Batch, batch_id)
        if batch is None:
            return False
        if not is_valid_batch_transition(batch.state, to_state):
            get_system_logger().warning(
                "Invalid batch transition %s → %s for batch %d",
                batch.state, to_state, batch_id,
            )
            return False
        old_state = batch.state
        batch.state = to_state
        batch.last_state_change_at = now
        # Record when processing first starts — never reset on pause/resume (D-103).
        if to_state == BatchState.PROCESSING and batch.processing_started_at is None:
            batch.processing_started_at = now
        session.add(BatchStateHistory(
            batch_id=batch_id,
            from_state=old_state.value,
            to_state=to_state.value,
            reason=reason,
        ))
        _log_business_event(
            session,
            event_type="batch_state_change",
            message=f"Batch {batch_id}: {old_state.value} → {to_state.value}",
            batch_id=batch_id,
        )
    get_system_logger().info(
        "BatchProcessor: batch %d  %s → %s%s",
        batch_id, old_state.value, to_state.value,
        f"  ({reason})" if reason else "",
    )
    return True


def _transition_item(
    item_id: int,
    to_state: ItemState,
    *,
    reason: str | None = None,
) -> bool:
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        item = session.get(ImageItem, item_id)
        if item is None:
            return False
        if not is_valid_item_transition(item.state, to_state):
            get_system_logger().warning(
                "Invalid item transition %s → %s for item %d",
                item.state, to_state, item_id,
            )
            return False
        old_state = item.state
        item.state = to_state
        session.add(ItemStateHistory(
            image_item_id=item_id,
            from_state=old_state.value,
            to_state=to_state.value,
            reason=reason,
        ))
    return True


def _requeue_item(item_id: int, reason: str) -> None:
    """Transition an item back to QUEUED after a transient network error.

    Unlike _set_item_error, this does NOT set the item state to ERROR, so the user
    only needs to fix the LLM endpoint and resume the batch — no manual retry needed.
    The TRANSIENT error stat is still incremented for observability.
    """
    _increment_error_stat(item_id, ErrorCategory.TRANSIENT)
    with session_scope() as session:
        item = session.get(ImageItem, item_id)
        if item is None:
            return
        if is_valid_item_transition(item.state, ItemState.QUEUED):
            old_state = item.state
            item.state = ItemState.QUEUED
            # Clear any stale error from a previous run so review doesn't show a
            # phantom error after the item is re-queued for recovery.
            item.last_error_category = None
            item.last_error_message = None
            item.last_error_at = None
            session.add(ItemStateHistory(
                image_item_id=item_id,
                from_state=old_state.value,
                to_state=ItemState.QUEUED.value,
                reason=f"transient: {reason[:200]}",
            ))
            _log_business_event(
                session,
                event_type="item_requeued",
                message=f"Item {item_id} re-queued after transient error: {reason[:200]}",
                batch_id=item.batch_id,
                image_item_id=item_id,
                level="warning",
            )


def _clear_item_error(item_id: int) -> None:
    """Clear stale error fields after an item completes the pipeline successfully."""
    with session_scope() as session:
        item = session.get(ImageItem, item_id)
        if item is None:
            return
        if item.last_error_category or item.last_error_message or item.last_error_at:
            item.last_error_category = None
            item.last_error_message = None
            item.last_error_at = None


def _set_item_error(
    item_id: int,
    category: ErrorCategory,
    message: str,
) -> None:
    _increment_error_stat(item_id, category)
    try:
        with session_scope() as session:
            item = session.get(ImageItem, item_id)
            if item is None:
                return
            if is_valid_item_transition(item.state, ItemState.ERROR):
                old_state = item.state
                item.state = ItemState.ERROR
                item.last_error_category = category.value
                item.last_error_message = message[:2000]
                item.last_error_at = datetime.now(timezone.utc)
                session.add(ItemStateHistory(
                    image_item_id=item_id,
                    from_state=old_state.value,
                    to_state=ItemState.ERROR.value,
                    reason=f"{category.value}: {message[:200]}",
                ))
                _log_business_event(
                    session,
                    event_type="item_error",
                    message=f"Item {item_id} error [{category.value}]: {message[:200]}",
                    batch_id=item.batch_id,
                    image_item_id=item_id,
                    level="error",
                )
    except (StaleDataError, IntegrityError):
        # Item was deleted (e.g. batch deleted while processing) — nothing to update.
        get_system_logger().warning(
            "_set_item_error: item %d no longer exists in DB — skipping error record", item_id
        )


def _set_normalizer_attempt(item_id: int, attempt: int) -> None:
    with session_scope() as session:
        item = session.get(ImageItem, item_id)
        if item:
            item.normalizer_attempt = attempt


def _increment_error_stat(item_id: int, category: ErrorCategory) -> None:
    try:
        with session_scope() as session:
            stats = (
                session.query(ImageItemErrorStats)
                .filter(ImageItemErrorStats.image_item_id == item_id)
                .first()
            )
            if stats is None:
                # Guard: check item still exists before inserting FK-constrained row.
                if session.get(ImageItem, item_id) is None:
                    return
                stats = ImageItemErrorStats(image_item_id=item_id)
                session.add(stats)
                session.flush()
            if category == ErrorCategory.TRANSIENT:
                stats.transient_count += 1
            elif category == ErrorCategory.PERMANENT:
                stats.permanent_count += 1
            elif category == ErrorCategory.POLICY:
                stats.policy_count += 1
            elif category == ErrorCategory.VALIDATION:
                stats.validation_count += 1
    except (StaleDataError, IntegrityError):
        get_system_logger().warning(
            "_increment_error_stat: item %d no longer exists — skipping", item_id
        )


def _record_batch_failure(batch_id: int) -> None:
    with session_scope() as session:
        batch = session.get(Batch, batch_id)
        if batch:
            batch.consecutive_failure_counter += 1


def _reset_batch_failure_counter(batch_id: int) -> None:
    with session_scope() as session:
        batch = session.get(Batch, batch_id)
        if batch:
            batch.consecutive_failure_counter = 0


def _consecutive_failures_exceeded(batch_id: int, threshold: int) -> bool:
    with session_scope() as session:
        batch = session.get(Batch, batch_id)
        if batch is None:
            return False
        effective = batch.consecutive_failure_threshold_override or threshold
        return batch.consecutive_failure_counter >= effective


def _log_business_event(
    session: Session,
    *,
    event_type: str,
    message: str,
    batch_id: int | None = None,
    image_item_id: int | None = None,
    level: str = "info",
) -> None:
    from ..logging_setup.business_logger import BusinessLogger  # noqa: PLC0415
    from ..models.enums import LogLevel  # noqa: PLC0415

    lvl = LogLevel(level) if level in LogLevel._value2member_map_ else LogLevel.INFO
    BusinessLogger(session).log(
        event_type=event_type,
        message=message,
        level=lvl,
        batch_id=batch_id,
        image_item_id=image_item_id,
    )
