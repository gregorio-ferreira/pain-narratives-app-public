"""LLM client factory + registry of UI-selectable models.

Single source of truth for how the Streamlit UI and the batch CLI construct the
right LLM client given a model selection. Adding a new UI-selectable model is one
entry in ``UI_MODEL_REGISTRY`` and an upstream provider already supported by
``build_llm_client``.

Two entry points:

- ``make_llm_client(model_key)`` -- for the UI. Looks the model up in
  ``UI_MODEL_REGISTRY`` and returns a ready-to-use client configured with the
  research-validated defaults (e.g. Claude Sonnet 4.5 with extended thinking,
  budget 8000, no custom temperature).

- ``build_llm_client(provider, **overrides)`` -- generic factory used by the
  batch CLI, which carries its own per-run overrides (region, profile, forced
  temperature). The UI never calls this directly.

Both paths converge on the same ``OpenAIClient`` / ``BedrockOpenAIAdapter``
construction logic so there is exactly one place that builds an LLM client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from pain_narratives.core.bedrock_client import (
    BedrockClient,
    BedrockOpenAIAdapter,
)
from pain_narratives.core.openai_client import OpenAIClient
from pain_narratives.core.questionnaire_runner import LLMClient


# ---------------------------------------------------------------------------
# UI registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UIModel:
    """One entry in the UI model dropdown.

    Attributes:
        key:       canonical key; this is what gets stored in ``config["model"]``
                   and in the DB ``experiment_list.model`` column.
        display:   what the user sees in the dropdown.
        provider:  ``"openai"`` or ``"bedrock_anthropic"`` (matches batch ``BatchConfig.model_provider``).
        model_id:  exact model id passed to the underlying API
                   (e.g. ``"us.anthropic.claude-sonnet-4-5-20250929-v1:0"``).
        extra:     keyword arguments forwarded to the client constructor.
                   For Claude with thinking: ``{"thinking_enabled": True, "thinking_budget_tokens": 8000}``.
    """

    key: str
    display: str
    provider: str
    model_id: str
    extra: dict[str, Any] = field(default_factory=dict)


UI_MODEL_REGISTRY: dict[str, UIModel] = {
    "gpt-5": UIModel(
        key="gpt-5", display="gpt-5",
        provider="openai", model_id="gpt-5",
    ),
    "gpt-5-mini": UIModel(
        key="gpt-5-mini", display="gpt-5-mini",
        provider="openai", model_id="gpt-5-mini",
    ),
    "gpt-5-nano": UIModel(
        key="gpt-5-nano", display="gpt-5-nano",
        provider="openai", model_id="gpt-5-nano",
    ),
    "claude-sonnet-4-5-thinking": UIModel(
        key="claude-sonnet-4-5-thinking",
        display="Claude Sonnet 4.5 (thinking)",
        provider="bedrock_anthropic",
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        extra={"thinking_enabled": True, "thinking_budget_tokens": 8000},
    ),
}

DEFAULT_UI_MODEL_KEY = "gpt-5"


def resolve_model(model_key: str) -> UIModel:
    """Look up a UI model by key. Raises ``ValueError`` for unknown keys."""
    try:
        return UI_MODEL_REGISTRY[model_key]
    except KeyError as exc:
        raise ValueError(
            f"Unknown UI model key {model_key!r}. "
            f"Known keys: {sorted(UI_MODEL_REGISTRY)}"
        ) from exc


# ---------------------------------------------------------------------------
# Generic factory
# ---------------------------------------------------------------------------


def build_llm_client(
    provider: str,
    *,
    openai_client: Optional[OpenAIClient] = None,
    openai_api_key: Optional[str] = None,
    thinking_enabled: bool = False,
    thinking_budget_tokens: int = 8000,
    force_temperature: Optional[float] = None,
    bedrock_region: Optional[str] = None,
    bedrock_profile: Optional[str] = None,
) -> LLMClient:
    """Generic LLM client factory used by the batch CLI and the UI.

    For provider ``"openai"`` returns an ``OpenAIClient`` (using the supplied
    instance, or constructing one with the given ``openai_api_key`` if any).

    For any provider starting with ``"bedrock"`` returns a ``BedrockOpenAIAdapter``
    over a freshly-constructed ``BedrockClient``. The adapter strips temperature
    and top_p when ``thinking_enabled`` is on, matching Bedrock's validation rules
    for extended-thinking models.
    """
    if provider.startswith("bedrock"):
        bedrock = BedrockClient(region=bedrock_region, profile_name=bedrock_profile)
        return BedrockOpenAIAdapter(  # type: ignore[return-value]
            bedrock,
            thinking_enabled=thinking_enabled,
            thinking_budget_tokens=thinking_budget_tokens,
            force_temperature=force_temperature,
        )
    if provider == "openai":
        if openai_client is not None:
            return openai_client
        return OpenAIClient(api_key=openai_api_key) if openai_api_key else OpenAIClient()
    raise ValueError(f"Unknown LLM provider: {provider!r}")


# ---------------------------------------------------------------------------
# UI factory
# ---------------------------------------------------------------------------


def make_llm_client(
    model_key: str,
    *,
    openai_api_key: Optional[str] = None,
) -> LLMClient:
    """Build the LLM client for the UI-selected model.

    Uses the configuration from ``UI_MODEL_REGISTRY`` (i.e. the research-validated
    defaults). The caller is responsible for passing ``entry.model_id`` to the
    client's ``create_completion(model=...)`` call when invoking it; this factory
    only handles client construction.

    ``openai_api_key`` is only used when the resolved model's provider is
    ``"openai"``; otherwise it is ignored (Bedrock uses the local AWS credentials
    chain via boto3).
    """
    entry = resolve_model(model_key)
    return build_llm_client(
        provider=entry.provider,
        openai_api_key=openai_api_key,
        thinking_enabled=bool(entry.extra.get("thinking_enabled", False)),
        thinking_budget_tokens=int(entry.extra.get("thinking_budget_tokens", 8000)),
    )
