"""LLMConfig — per-AGENT model selection (the carrier `model_from_config` resolves).

Lives with the clients that consume it: the AGENT node and the Compose loader's
`llm_config:` field carry an `LLMConfig` (or the plain dict that normalizes to one),
and `factory.model_from_config` turns it into a ready chat model. Was in the
agent_composer `common/` grab-bag before this cleanup; moved here because it IS the
clients' input contract.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class LLMConfig(BaseModel):
    """
    Per-AGENT LLM selection — the carrier `model_from_config` resolves into a chat model.

    Every field is optional: an unset `provider`/`model` falls back to the package's
    env-based defaults, and the reasoning knobs apply only when they match the selected
    provider. `extra="forbid"` makes a mistyped `llm_config:` key loud at load time.

    Attributes:
        provider (`str`, *optional*, defaults to `None`):
            One of `anthropic`/`openai`/`google`/`deepseek`/`xai`/`ollama`/`vllm`.
            `None` inherits the global default provider.
        model (`str`, *optional*, defaults to `None`):
            Provider-specific model id. `None` inherits the global default model.
        anthropic_effort (`str`, *optional*, defaults to `None`):
            Anthropic reasoning effort (`high`/`medium`/`low`); ignored for other providers.
        openai_reasoning_effort (`str`, *optional*, defaults to `None`):
            OpenAI reasoning effort (`high`/`medium`/`low`); ignored for other providers.
        google_thinking_level (`str`, *optional*, defaults to `None`):
            Google thinking level; ignored for other providers.
        temperature (`float`, *optional*, defaults to `None`):
            Sampling temperature; `None` leaves the provider default.
    """

    provider: Optional[
        Literal["anthropic", "openai", "google", "deepseek", "xai", "ollama", "vllm"]
    ] = None
    model: Optional[str] = None
    anthropic_effort: Optional[Literal["high", "medium", "low"]] = None
    openai_reasoning_effort: Optional[Literal["high", "medium", "low"]] = None
    google_thinking_level: Optional[str] = None
    temperature: Optional[float] = None

    # `model` is a regular field here; don't warn on the model_ namespace.
    # extra="forbid" makes typo'd llm_config: keys (e.g. `temparature` instead of
    # `temperature`) loud at LOAD time, not silent.
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")
