"""Model profiles and token-aware governance for the conversation loop.

This module defines per-model configurations (context windows, tokenizers,
governance thresholds) and provides token-counting utilities used by the
Loop to keep messages within budget.

---
What we bring in (3rd-party):
  tiktoken — OpenAI's BPE tokenizer for GPT-4 / GPT-3.5 family.
  transformers — Hugging Face tokenizer hub (used as fallback for non-OpenAI
  models when tiktoken doesn't have a matching encoding).

What we write ourselves:
  ModelProfile dataclass — declarative per-model config.
  TokenCounter protocol + implementations — abstracts tokenizer differences.
  ModelRegistry — loads profiles from config, resolves model → profile.
  estimate_tokens() — convenience function used by the Loop.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Protocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 3rd-party imports (with graceful degradation)
# ---------------------------------------------------------------------------

try:
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None  # type: ignore[assignment]

try:
    from transformers import AutoTokenizer  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    AutoTokenizer = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Self-written: ModelProfile
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelProfile:
    """Static configuration for a single model.

    Attributes:
        name: Human-readable model identifier (e.g. "gpt-4o", "claude-sonnet-4-20250514").
        context_window: Maximum context length in *tokens* (not characters).
        encoding_name: tiktoken encoding name, or "hf:<repo_id>" for Hugging Face.
            "auto" means "try tiktoken first, fall back to character estimate".
        reserved_output_tokens: Tokens reserved for the model's response.
        governance: Mutable dict of thresholds (kept mutable so users can tune
            without editing code).
    """
    name: str
    context_window: int
    encoding_name: str = "auto"
    reserved_output_tokens: int = 4096
    governance: dict[str, int | float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Fill defaults if user didn't supply them
        defaults = {
            "max_messages_before_compact": 30,
            "compact_threshold_ratio": 0.75,          # compact when > 75 % full
            "hard_trim_ratio": 0.90,                  # hard truncate when > 90 % full
            "microcompact_age_turns": 10,             # turns old before microcompact
        }
        for k, v in defaults.items():
            if k not in self.governance:
                object.__setattr__(self, "governance", {**self.governance, k: v})

    @property
    def usable_context(self) -> int:
        """Tokens available for the conversation history after reserving output."""
        return self.context_window - self.reserved_output_tokens


# ---------------------------------------------------------------------------
# Self-written: TokenCounter protocol + implementations
# ---------------------------------------------------------------------------

class TokenCounter(Protocol):
    """Callable that returns token count for a text string."""

    def __call__(self, text: str) -> int: ...


def _char_estimate(text: str) -> int:
    """Fallback: ~4 characters per token (rough English average)."""
    return max(1, len(text) // 4)


def _build_tiktoken_counter(encoding_name: str) -> TokenCounter:
    """Build a tiktoken-based counter.

    Raises:
        ValueError: If tiktoken is not installed or encoding unknown.
    """
    if tiktoken is None:
        raise ValueError("tiktoken not installed; install with: pip install tiktoken")
    enc = tiktoken.get_encoding(encoding_name)
    return lambda text: len(enc.encode(text))


def _build_hf_counter(repo_id: str) -> TokenCounter:
    """Build a Hugging-Face-transformers counter.

    Raises:
        ValueError: If transformers is not installed.
    """
    if AutoTokenizer is None:
        raise ValueError(
            "transformers not installed; install with: pip install transformers"
        )
    tok = AutoTokenizer.from_pretrained(repo_id)
    return lambda text: len(tok.encode(text))


def build_counter(encoding_name: str) -> TokenCounter:
    """Resolve an encoding name to a concrete TokenCounter.

    Supported prefixes:
      - "auto"      → try cl100k_base (tiktoken), fall back to char estimate
      - "tiktoken:<name>" → explicit tiktoken encoding
      - "hf:<repo_id>"    → Hugging Face tokenizer
      - plain string matching a tiktoken encoding name
    """
    if encoding_name == "auto":
        if tiktoken is not None:
            try:
                return _build_tiktoken_counter("cl100k_base")
            except Exception:  # pragma: no cover
                pass
        logger.warning("tiktoken unavailable; falling back to character estimate")
        return _char_estimate

    if encoding_name.startswith("tiktoken:"):
        return _build_tiktoken_counter(encoding_name.split(":", 1)[1])

    if encoding_name.startswith("hf:"):
        return _build_hf_counter(encoding_name.split(":", 1)[1])

    # Assume it's a raw tiktoken encoding name
    return _build_tiktoken_counter(encoding_name)


# ---------------------------------------------------------------------------
# Self-written: convenience API used by the Loop
# ---------------------------------------------------------------------------

def estimate_tokens(text: str, counter: TokenCounter | None = None) -> int:
    """Count tokens in *text* using the provided counter or char fallback."""
    if counter is None:
        counter = _char_estimate
    return counter(text)


# ---------------------------------------------------------------------------
# Self-written: ModelRegistry
# ---------------------------------------------------------------------------

class ModelRegistry:
    """Resolves model names → ModelProfile, with a default fallback.

    Profiles can be loaded from config.yaml or registered programmatically.
    """

    # Built-in profiles for popular models
    _DEFAULTS: dict[str, ModelProfile] = {
        "gpt-4o": ModelProfile(
            name="gpt-4o",
            context_window=128_000,
            encoding_name="o200k_base",
            reserved_output_tokens=16_384,
        ),
        "gpt-4o-mini": ModelProfile(
            name="gpt-4o-mini",
            context_window=128_000,
            encoding_name="o200k_base",
            reserved_output_tokens=16_384,
        ),
        "gpt-4-turbo": ModelProfile(
            name="gpt-4-turbo",
            context_window=128_000,
            encoding_name="cl100k_base",
            reserved_output_tokens=4096,
        ),
        "gpt-3.5-turbo": ModelProfile(
            name="gpt-3.5-turbo",
            context_window=16_384,
            encoding_name="cl100k_base",
            reserved_output_tokens=4096,
        ),
        "claude-sonnet-4-20250514": ModelProfile(
            name="claude-sonnet-4-20250514",
            context_window=200_000,
            encoding_name="auto",   # Anthropic uses their own tokenizer; we approximate
            reserved_output_tokens=8192,
            governance={"compact_threshold_ratio": 0.80, "hard_trim_ratio": 0.92},
        ),
        "kimi-k2.6": ModelProfile(
            name="kimi-k2.6",
            context_window=256_000,
            encoding_name="auto",
            reserved_output_tokens=8192,
        ),
    }

    def __init__(self, overrides: dict[str, ModelProfile] | None = None) -> None:
        self._profiles: dict[str, ModelProfile] = {
            **self._DEFAULTS,
            **(overrides or {}),
        }

    def get(self, model_name: str) -> ModelProfile:
        """Look up a profile by exact name, falling back to a generic default."""
        if model_name in self._profiles:
            return self._profiles[model_name]
        logger.warning("Unknown model %r; using generic fallback profile", model_name)
        return ModelProfile(
            name=model_name,
            context_window=128_000,
            encoding_name="auto",
            reserved_output_tokens=4096,
        )

    def register(self, profile: ModelProfile) -> None:
        """Programmatically add or overwrite a profile."""
        self._profiles[profile.name] = profile
