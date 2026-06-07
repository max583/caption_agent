"""Bootstrap configuration loaded from environment variables.

Reads values needed BEFORE the DB is available: server host/port, DB URL, paths, log file.
Everything else is runtime config in the DB.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# App root = scripts/caption_agent/ (parent of the package directory).
_APP_ROOT = Path(__file__).resolve().parents[2]


class BootstrapSettings(BaseSettings):
    """Read once at startup. Source: env vars prefixed CAPTION_AGENT_."""

    model_config = SettingsConfigDict(
        env_prefix="CAPTION_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server.
    host: str = "127.0.0.1"
    port: int = 8765
    # Dev hot-reload: when true, uvicorn watches Python files and restarts the
    # server on save. Templates always reload (Jinja2 reads from disk per request).
    # DB schema changes still require a restart + DB recreate.
    reload: bool = False

    # Database. Default: SQLite in app data folder.
    db_url: str = Field(
        default_factory=lambda: f"sqlite:///{(_APP_ROOT / 'data' / 'agent.db').as_posix()}"
    )
    db_echo: bool = False

    # Paths.
    app_root: Path = _APP_ROOT
    data_dir: Path = _APP_ROOT / "data"
    logs_dir: Path = _APP_ROOT / "logs"
    llm_io_dir: Path = _APP_ROOT / "logs" / "llm_io"

    # System logging.
    log_level: str = "INFO"
    log_file: Path = _APP_ROOT / "logs" / "server.log"
    log_rotate_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_rotate_backup_count: int = 5

    @field_validator("reload", mode="before")
    @classmethod
    def _empty_string_means_default(cls, v: object) -> object:
        """Treat empty env strings (e.g. ``CAPTION_AGENT_RELOAD=``) as the default.

        Without this, pydantic raises a ValidationError at startup on an empty
        boolean env var — easy to hit when a launcher script leaves the variable
        declared but blank.
        """
        if isinstance(v, str) and v.strip() == "":
            return False
        return v

    def ensure_directories(self) -> None:
        """Create data/logs/llm_io directories if missing."""
        for path in (self.data_dir, self.logs_dir, self.llm_io_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_bootstrap_settings() -> BootstrapSettings:
    """Cached singleton accessor."""
    return BootstrapSettings()
