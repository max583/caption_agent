"""Pydantic schemas for runtime configuration (stored in DB as JSON).

Per D-087/D-088: OpenAI-compatible LLM config + per-step overrides + retry + polling.
Per D-107: UIConfig for language selection.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """OpenAI-compatible chat-completions endpoint config (D-088)."""

    base_url: str = "http://localhost:1234/v1"
    api_key: str = ""  # may be empty if endpoint doesn't require auth
    model_id: str = "qwen3.6-35b-a3b"
    context_length: int = 0
    max_tokens: int = 0
    temperature: float = 0.2
    request_timeout: int = 600
    max_retries: int = 4
    max_tool_iterations: int = 8  # reserved per D-089


class StepLLMOverride(BaseModel):
    """Per-step LLM config: any field that is None inherits from main `llm`."""

    base_url: str | None = None
    api_key: str | None = None
    model_id: str | None = None
    context_length: int | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    request_timeout: int | None = None
    max_retries: int | None = None
    max_tool_iterations: int | None = None


class RetryConfig(BaseModel):
    """Retry-related limits."""

    normalizer_max_self_retries: int = 3
    consecutive_failure_threshold: int = 10  # batch-level halt


class PollingConfig(BaseModel):
    """Polling intervals in seconds, per UI screen (D-090)."""

    projects_list: int = 30
    project_workspace: int = 15
    batch_processing: int = 7  # batch in PROCESSING
    batch_idle: int = 30  # batch in other states


class LoggingConfig(BaseModel):
    """Logging behavior."""

    business_log_retention_days: int = 30
    debug_dump_llm_io: bool = False  # enable raw LLM I/O dumps to files
    log_level: str = "INFO"  # DEBUG / INFO / WARNING / ERROR — applied to system logger on save


class PathsConfig(BaseModel):
    """Default paths used by the pipeline (not the bootstrap dirs)."""

    default_output_policy: str = "source_folder"


class UIConfig(BaseModel):
    """UI preferences (D-107)."""

    language: Literal["ru", "en"] = "ru"
