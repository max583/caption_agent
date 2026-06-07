"""Tests for ConfigManager: defaults seeding, get/set, per-step LLM resolution."""

from __future__ import annotations

import os

import pytest
from sqlalchemy.orm import Session

from caption_agent.config import ConfigManager
from caption_agent.config.defaults import DEFAULT_RUNTIME_CONFIG


def test_seed_defaults_creates_all_keys(session: Session) -> None:
    manager = ConfigManager(session)
    manager.seed_defaults_if_missing()
    session.flush()

    stored = manager.all()
    for key in DEFAULT_RUNTIME_CONFIG:
        assert key in stored


def test_seed_defaults_idempotent(session: Session) -> None:
    manager = ConfigManager(session)
    manager.seed_defaults_if_missing()
    session.flush()
    manager.set("llm", {"model_id": "custom-model"})
    session.flush()
    manager.seed_defaults_if_missing()
    session.flush()
    # Existing value preserved.
    assert manager.get("llm")["model_id"] == "custom-model"


def test_set_and_get(session: Session) -> None:
    manager = ConfigManager(session)
    manager.set("foo", {"bar": 42})
    session.flush()
    assert manager.get("foo") == {"bar": 42}


def test_per_step_llm_inherits_when_override_unset(session: Session) -> None:
    manager = ConfigManager(session)
    manager.seed_defaults_if_missing()
    session.flush()

    main = manager.get_main_llm()
    analyst = manager.get_effective_llm_for_step("analyst")
    # All defaults match main.
    assert analyst.base_url == main.base_url
    assert analyst.model_id == main.model_id
    assert analyst.temperature == main.temperature


def test_per_step_llm_override_takes_precedence(session: Session) -> None:
    manager = ConfigManager(session)
    manager.seed_defaults_if_missing()
    session.flush()

    manager.set("llm_analyst", {"model_id": "gemma-4-26b-a4b", "temperature": 0.1})
    session.flush()

    analyst = manager.get_effective_llm_for_step("analyst")
    assert analyst.model_id == "gemma-4-26b-a4b"
    assert analyst.temperature == 0.1
    # Unset fields still inherit.
    main = manager.get_main_llm()
    assert analyst.base_url == main.base_url


def test_env_override_for_main_api_key(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = ConfigManager(session)
    manager.seed_defaults_if_missing()
    session.flush()

    monkeypatch.setenv("CAPTION_AGENT_LLM_API_KEY", "env-secret")
    main = manager.get_main_llm()
    assert main.api_key == "env-secret"


def test_env_override_per_step_api_key(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = ConfigManager(session)
    manager.seed_defaults_if_missing()
    session.flush()

    monkeypatch.setenv("CAPTION_AGENT_LLM_API_KEY", "main-env-key")
    monkeypatch.setenv("CAPTION_AGENT_ANALYST_LLM_API_KEY", "analyst-env-key")

    analyst = manager.get_effective_llm_for_step("analyst")
    normalizer = manager.get_effective_llm_for_step("normalizer")

    assert analyst.api_key == "analyst-env-key"
    assert normalizer.api_key == "main-env-key"


def test_unknown_step_raises(session: Session) -> None:
    manager = ConfigManager(session)
    with pytest.raises(ValueError):
        manager.get_effective_llm_for_step("nonexistent")


# ---------------------------------------------------------------------------
# Bootstrap reload flag
# ---------------------------------------------------------------------------

def test_bootstrap_reload_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CAPTION_AGENT_RELOAD", raising=False)
    from caption_agent.config.bootstrap import BootstrapSettings
    assert BootstrapSettings().reload is False


def test_bootstrap_reload_truthy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from caption_agent.config.bootstrap import BootstrapSettings
    for v in ("1", "true", "True", "yes"):
        monkeypatch.setenv("CAPTION_AGENT_RELOAD", v)
        assert BootstrapSettings().reload is True, f"value {v!r} should be truthy"


def test_bootstrap_reload_empty_string_treated_as_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: empty env value used to raise ValidationError at startup."""
    monkeypatch.setenv("CAPTION_AGENT_RELOAD", "")
    from caption_agent.config.bootstrap import BootstrapSettings
    assert BootstrapSettings().reload is False
