"""Configuration management.

Bootstrap config (server host/port, DB URL, paths) is loaded from environment via
`bootstrap.BootstrapSettings`. Runtime config (LLM settings, retries, polling, retention)
lives in the DB and is accessed via `manager.ConfigManager`.
"""

from .bootstrap import BootstrapSettings, get_bootstrap_settings
from .defaults import DEFAULT_RUNTIME_CONFIG
from .manager import ConfigManager
from .schema import LLMConfig, PollingConfig, RetryConfig

__all__ = [
    "BootstrapSettings",
    "ConfigManager",
    "DEFAULT_RUNTIME_CONFIG",
    "LLMConfig",
    "PollingConfig",
    "RetryConfig",
    "get_bootstrap_settings",
]
