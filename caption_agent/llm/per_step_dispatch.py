"""Create an LLMClient resolved for a named pipeline step (D-088).

Per-step config inherits unset fields from the main llm config. Env-var API keys
take precedence over DB-stored keys.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..config.manager import ConfigManager
from .client import LLMClient


def make_client_for_step(step: str, session: Session) -> LLMClient:
    """Return an LLMClient configured for the given pipeline step.

    Args:
        step: one of ``"analyst"``, ``"normalizer"``, ``"checker"``.
        session: active SQLAlchemy session used to read config from DB.
    """
    cfg = ConfigManager(session).get_effective_llm_for_step(step)
    return LLMClient(cfg)
