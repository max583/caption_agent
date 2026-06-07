"""Default runtime configuration values (seeded into DB on first start)."""

from __future__ import annotations

from .schema import (
    LLMConfig,
    LoggingConfig,
    PathsConfig,
    PollingConfig,
    RetryConfig,
    StepLLMOverride,
    UIConfig,
)

DEFAULT_RUNTIME_CONFIG: dict[str, dict] = {
    "llm": LLMConfig().model_dump(),
    "llm_analyst": StepLLMOverride().model_dump(),
    "llm_normalizer": StepLLMOverride().model_dump(),
    "llm_checker": StepLLMOverride().model_dump(),
    # llm_gap_filler removed (D-102) — old DBs may still have this key; tolerate on read.
    "retry": RetryConfig().model_dump(),
    "polling": PollingConfig().model_dump(),
    "logging": LoggingConfig().model_dump(),
    "paths": PathsConfig().model_dump(),
    "ui": UIConfig().model_dump(),
}
