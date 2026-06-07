"""DB-backed runtime configuration manager.

Read/write operations on the Configuration table. Used by API endpoints (Settings UI)
and by pipeline modules to fetch effective per-step LLM configs.

Per D-088: per-step LLM config resolves field-by-field — fields set on the step
override the main config; unset fields inherit.
"""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from ..models import Configuration
from .defaults import DEFAULT_RUNTIME_CONFIG
from .schema import LLMConfig, StepLLMOverride
from ..schemas.llm_profile import LLMProfileSnapshot


_STEP_KEYS = {
    "analyst": "llm_analyst",
    "normalizer": "llm_normalizer",
    "checker": "llm_checker",
    # gap_filler removed (D-102)
}


class ConfigManager:
    """Thin wrapper around the Configuration table.

    Instances are scoped to a SQLAlchemy session (one per request or one per orchestration
    task). Does not cache — always reads from DB. Caching can be added later if profiling
    shows a need.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ---- generic CRUD ----

    def get(self, key: str) -> Any:
        """Return the value for `key`, or None if absent."""
        row = self._session.get(Configuration, key)
        return row.value if row is not None else None

    def set(self, key: str, value: Any, description: str | None = None) -> None:
        """Upsert a top-level config key."""
        row = self._session.get(Configuration, key)
        if row is None:
            row = Configuration(key=key, value=value, description=description)
            self._session.add(row)
        else:
            row.value = value
            if description is not None:
                row.description = description

    def delete(self, key: str) -> None:
        """Delete a config key (use sparingly; usually reset via set with default)."""
        row = self._session.get(Configuration, key)
        if row is not None:
            self._session.delete(row)

    def all(self) -> dict[str, Any]:
        """Return all stored config as a dict."""
        rows = self._session.query(Configuration).all()
        return {row.key: row.value for row in rows}

    # ---- bootstrap ----

    def seed_defaults_if_missing(self) -> None:
        """Insert default values for any missing config key. Called at server startup."""
        for key, value in DEFAULT_RUNTIME_CONFIG.items():
            if self._session.get(Configuration, key) is None:
                self._session.add(Configuration(key=key, value=value))

    # ---- LLM-specific helpers ----

    def get_main_llm(self) -> LLMConfig:
        """Return the main LLM config with env-var overrides applied."""
        raw = self.get("llm") or {}
        cfg = LLMConfig.model_validate(raw)
        # Env-var override for API key (security: avoid storing keys in DB if env set).
        env_key = os.environ.get("CAPTION_AGENT_LLM_API_KEY")
        if env_key:
            cfg.api_key = env_key
        return cfg

    def get_effective_llm_for_step(self, step: str) -> LLMConfig:
        """Resolve effective LLM config for a pipeline step (analyst / normalizer / checker).

        Per D-088: unset fields in the step override fall back to main config.
        Env-var override for API key takes precedence: per-step env var first, then main.
        """
        if step not in _STEP_KEYS:
            raise ValueError(f"Unknown step: {step}")
        main = self.get_main_llm()
        override_raw = self.get(_STEP_KEYS[step]) or {}
        override = StepLLMOverride.model_validate(override_raw)

        # Field-by-field merge: override wins if non-None.
        merged_fields = main.model_dump()
        for field_name, value in override.model_dump().items():
            if value is not None:
                merged_fields[field_name] = value
        merged = LLMConfig.model_validate(merged_fields)

        # Step-specific env var takes precedence over main.
        step_env_var = f"CAPTION_AGENT_{step.upper()}_LLM_API_KEY"
        step_env_key = os.environ.get(step_env_var)
        if step_env_key:
            merged.api_key = step_env_key
        return merged

    # ---- profile snapshot helpers ----

    def snapshot_current_llm(self) -> LLMProfileSnapshot:
        """Capture the current flat LLM config as a profile snapshot.

        Reads config keys directly from the DB (no env-var override applied —
        profiles store what's in the DB, not the runtime-effective values).
        """
        return LLMProfileSnapshot(
            llm=LLMConfig.model_validate(self.get("llm") or {}),
            llm_analyst=StepLLMOverride.model_validate(self.get("llm_analyst") or {}),
            llm_normalizer=StepLLMOverride.model_validate(self.get("llm_normalizer") or {}),
            llm_checker=StepLLMOverride.model_validate(self.get("llm_checker") or {}),
        )

    def apply_llm_snapshot(self, snapshot: LLMProfileSnapshot) -> None:
        """Write LLM config blocks from the snapshot into the configuration table.

        After this call, the pipeline's next `get_effective_llm_for_step()` will use the
        profile's values (env-var overrides still take precedence at runtime as usual).
        """
        self.set("llm", snapshot.llm.model_dump())
        self.set("llm_analyst", snapshot.llm_analyst.model_dump())
        self.set("llm_normalizer", snapshot.llm_normalizer.model_dump())
        self.set("llm_checker", snapshot.llm_checker.model_dump())
