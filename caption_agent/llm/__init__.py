"""LLM client package (D-088): OpenAI-compatible HTTP client and per-step dispatch."""

from .client import LLMClient, LLMError, LLMPermanentError, LLMTransientError, LLMValidationError
from .per_step_dispatch import make_client_for_step

__all__ = [
    "LLMClient",
    "LLMError",
    "LLMPermanentError",
    "LLMTransientError",
    "LLMValidationError",
    "make_client_for_step",
]
