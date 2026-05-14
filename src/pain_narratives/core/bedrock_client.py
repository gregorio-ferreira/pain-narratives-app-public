"""AWS Bedrock Converse-API client for the revision experiments.

The client wraps `bedrock-runtime.converse(...)` for two models:

- `us.deepseek.r1-v1:0`                          (DeepSeek-R1, always-reasoning)
- `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (Claude Sonnet 4.5, optional
  extended thinking via `additionalModelRequestFields.thinking`)

Both models return content as multiple blocks (`text` + `reasoningContent`). The
order varies by provider (DeepSeek: text then reasoning; Sonnet-with-thinking:
reasoning then text), so the extractor scans by block type, never by position.

`create_completion` returns a dict shaped like the OpenAI Chat Completions
response (`choices[0].message.content`, `usage.prompt_tokens`, etc.) so it is a
drop-in replacement for `OpenAIClient.create_completion`. Reasoning text is
additionally exposed at top level as `reasoning_content` and the unmodified
Bedrock response is preserved under `raw_response`.

Authentication prefers AWS credentials resolved by boto3 (for example an MFA
session profile or EC2 instance profile). If `bedrock.api_key` is configured,
the client exports it as `AWS_BEARER_TOKEN_BEDROCK` and uses Bedrock bearer-token
auth instead.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import parse_qs

from pain_narratives.config.settings import get_settings

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Typed exceptions — the runner distinguishes auth (abort) from transient (retry)
# from model errors (skip and log).
# -----------------------------------------------------------------------------


class BedrockError(Exception):
    """Base for all Bedrock-specific errors."""


class BedrockAuthError(BedrockError):
    """Authentication failure: bearer token expired, invalid, or wrong region.
    The runner halts the batch on this — retrying will not help."""


class BedrockTransientError(BedrockError):
    """Server-side / throttling failure. Safe to retry with backoff."""


class BedrockModelError(BedrockError):
    """The model rejected the request (validation, malformed input).
    Programming bug, not transient — log and skip the narrative."""


# -----------------------------------------------------------------------------
# Bearer-token introspection
# -----------------------------------------------------------------------------


@dataclass
class BearerTokenInfo:
    """Decoded metadata for a Bedrock API key.

    Short-term keys are presigned URLs; long-term keys have an indefinite expiry
    and may not decode cleanly. `expires_at = None` indicates "no expiry recorded".
    """

    issued_at: Optional[datetime]
    expires_at: Optional[datetime]
    credential_scope: Optional[str]  # e.g. ASIA.../20260511/us-east-1/bedrock/aws4_request

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    def time_remaining(self) -> Optional[timedelta]:
        if self.expires_at is None:
            return None
        return self.expires_at - datetime.now(timezone.utc)


@dataclass
class BedrockAuthStatus:
    """Resolved Bedrock authentication status.

    `expires_at = None` means the active credential source does not expose a
    local expiry, not that it is necessarily permanent.
    """

    auth_method: str
    region: str
    profile_name: Optional[str] = None
    principal_arn: Optional[str] = None
    account_id: Optional[str] = None
    expires_at: Optional[datetime] = None

    def time_remaining(self) -> Optional[timedelta]:
        if self.expires_at is None:
            return None
        return self.expires_at - datetime.now(timezone.utc)


def inspect_bearer_token(key: str) -> BearerTokenInfo:
    """Decode a Bedrock API key. Tolerant of malformed or long-term-shaped keys."""
    try:
        b64 = key.removeprefix("bedrock-api-key-")
        decoded = base64.b64decode(b64 + "==").decode()
        if "?" not in decoded:
            return BearerTokenInfo(None, None, None)
        params = {k: v[0] for k, v in parse_qs(decoded.split("?", 1)[1]).items()}
        issued = (
            datetime.strptime(params["X-Amz-Date"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            if "X-Amz-Date" in params
            else None
        )
        expires = (
            issued + timedelta(seconds=int(params["X-Amz-Expires"]))
            if issued is not None and "X-Amz-Expires" in params
            else None
        )
        return BearerTokenInfo(issued, expires, params.get("X-Amz-Credential"))
    except Exception:
        return BearerTokenInfo(None, None, None)


# -----------------------------------------------------------------------------
# Per-model request shaping
# -----------------------------------------------------------------------------


def is_anthropic_thinking_model(model_id: str) -> bool:
    """True when the model id is an Anthropic Claude variant that supports
    `additionalModelRequestFields.thinking` (i.e. extended thinking)."""
    return "anthropic.claude" in model_id and (
        "claude-sonnet-4-5" in model_id or "claude-opus-4" in model_id or "claude-haiku-4-5" in model_id
    )


def is_deepseek_reasoning_model(model_id: str) -> bool:
    return "deepseek.r1" in model_id


# -----------------------------------------------------------------------------
# Response parsing
# -----------------------------------------------------------------------------


def extract_text_and_reasoning(content_blocks: list[dict[str, Any]]) -> tuple[str, str]:
    """Scan Bedrock Converse content blocks for `text` and `reasoningContent`.

    Position-agnostic: DeepSeek returns `[text, reasoningContent]` while Sonnet
    with thinking returns `[reasoningContent, text]`. Multiple text blocks are
    concatenated; multiple reasoning blocks likewise.
    """
    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    for block in content_blocks:
        if "text" in block:
            text_parts.append(block["text"])
        elif "reasoningContent" in block:
            inner = block["reasoningContent"].get("reasoningText", {})
            if "text" in inner:
                reasoning_parts.append(inner["text"])
    return "".join(text_parts).strip(), "".join(reasoning_parts).strip()


# -----------------------------------------------------------------------------
# Client
# -----------------------------------------------------------------------------


class BedrockClient:
    """Bedrock Converse API client.

    Lazy-initialises boto3 clients; instances are cached per region. When a
    Bedrock API key is configured, exports it into `AWS_BEARER_TOKEN_BEDROCK`.
    Otherwise boto3 uses either `bedrock.aws_profile` / `bedrock.aws_credentials`
    or the standard provider chain, including EC2 instance-profile credentials.
    """

    def __init__(self, region: Optional[str] = None, profile_name: Optional[str] = None) -> None:
        self.settings = get_settings()
        bedrock_cfg = self.settings.bedrock_config
        self._region = region or bedrock_cfg.default_region or bedrock_cfg.aws_region or "us-east-1"
        self._clients: dict[str, Any] = {}  # region -> boto3 bedrock-runtime client
        self._session: Optional[Any] = None
        self._api_key = bedrock_cfg.api_key
        self._profile_name = profile_name or bedrock_cfg.aws_profile or None
        if self._api_key:
            # Export the bearer token so any boto3 client in this process picks it up.
            # Always overwrite — config is the source of truth and may differ
            # from a stale shell-exported value.
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = self._api_key
            # Bearer-token auth and sigv4-credentials auth coexist poorly in boto3.
            # Clear AWS_PROFILE and any inline sigv4 env vars so the bearer token is
            # used unambiguously. This affects only the current process.
            for k in ("AWS_PROFILE", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
                os.environ.pop(k, None)
        else:
            # Prefer IAM instance-profile auth when no bearer token is configured.
            os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)

    @property
    def region(self) -> str:
        return self._region

    def _client_for(self, region: str) -> Any:
        if region not in self._clients:
            self._clients[region] = self._boto3_session().client("bedrock-runtime", region_name=region)
        return self._clients[region]

    def _boto3_session(self) -> Any:
        if self._session is None:
            import boto3

            if self._profile_name:
                self._session = boto3.Session(profile_name=self._profile_name)
            else:
                self._session = boto3.Session()
        return self._session

    def _credential_expiry(self) -> Optional[datetime]:
        credentials = self._boto3_session().get_credentials()
        if credentials is None:
            return None
        expiry = getattr(credentials, "_expiry_time", None)
        if expiry is None:
            return None
        if expiry.tzinfo is None:
            return expiry.replace(tzinfo=timezone.utc)
        return expiry.astimezone(timezone.utc)

    def _check_boto3_credentials(self, min_remaining: timedelta) -> BedrockAuthStatus:
        try:
            session = self._boto3_session()
            credentials = session.get_credentials()
            if credentials is None:
                raise BedrockAuthError(
                    "No AWS credentials found. Configure AWS_PROFILE, an EC2 "
                    "instance profile, or bedrock.aws_profile in config.yaml. "
                    "See docs/deployment.md (AWS Bedrock authentication)."
                )
            credentials.get_frozen_credentials()

            expires_at = self._credential_expiry()
            if expires_at is not None:
                remaining = expires_at - datetime.now(timezone.utc)
                if remaining <= timedelta(0):
                    raise BedrockAuthError(
                        f"AWS credentials expired at {expires_at.isoformat()}. " "Refresh the MFA session and retry."
                    )
                if remaining < min_remaining:
                    raise BedrockAuthError(
                        f"AWS credentials have only {remaining} remaining (less than "
                        f"{min_remaining} required by pre-flight). Refresh the MFA session."
                    )

            identity = session.client("sts", region_name=self._region).get_caller_identity()
            return BedrockAuthStatus(
                auth_method="aws_profile" if self._profile_name else "aws_default_chain",
                region=self._region,
                profile_name=self._profile_name or os.environ.get("AWS_PROFILE"),
                principal_arn=identity.get("Arn"),
                account_id=identity.get("Account"),
                expires_at=expires_at,
            )
        except BedrockAuthError:
            raise
        except Exception as exc:  # noqa: BLE001
            translated = _translate_boto_error(exc)
            if isinstance(translated, BedrockAuthError):
                raise translated from exc
            raise BedrockAuthError(str(translated)) from exc

    def check_credentials(self, min_remaining: timedelta = timedelta(hours=2)) -> BedrockAuthStatus:
        """Validate Bedrock authentication before an expensive batch starts.

        Bearer-token auth is checked locally for expiry. AWS-credential auth is
        resolved through boto3, frozen once to catch missing/partial credentials,
        and verified with STS so MFA/profile failures appear before the batch.
        """
        if not self._api_key:
            return self._check_boto3_credentials(min_remaining=min_remaining)
        info = inspect_bearer_token(self._api_key)
        if info.is_expired:
            raise BedrockAuthError(
                f"Bedrock API key already expired at {info.expires_at}. " "Generate a new key and re-run."
            )
        remaining = info.time_remaining()
        if remaining is not None and remaining < min_remaining:
            raise BedrockAuthError(
                f"Bedrock API key has only {remaining} remaining (less than "
                f"{min_remaining} required by pre-flight). Generate a fresh key."
            )
        return BedrockAuthStatus(
            auth_method="bedrock_api_key",
            region=self._region,
            expires_at=info.expires_at,
        )

    def create_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int = 8000,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        thinking_enabled: bool = False,
        thinking_budget_tokens: int = 8000,
        region: Optional[str] = None,
        response_format: Optional[str] = None,  # accepted for OpenAIClient parity; ignored
    ) -> dict[str, Any]:
        """Send a Converse request to Bedrock. Returns an OpenAI-shaped dict.

        For Claude Sonnet 4.5 with `thinking_enabled=True`, the request omits
        `temperature`, `top_p`, `top_k` (Bedrock validates this strictly).
        For DeepSeek-R1, pass `temperature=0.6` per DeepSeek's documented
        operating point; reasoning content is always returned.
        """
        _ = response_format  # unused, accepted for signature parity with OpenAIClient
        rt = self._client_for(region or self._region)

        # Split system messages from user/assistant
        system_msgs = [m["content"] for m in messages if m.get("role") == "system"]
        ua_msgs = [
            {"role": m["role"], "content": [{"text": m["content"]}]} for m in messages if m.get("role") != "system"
        ]

        # Inference config — strictly omit temp/top_p/top_k when thinking is on.
        infcfg: dict[str, Any] = {
            "maxTokens": max(max_tokens, thinking_budget_tokens + 200) if thinking_enabled else max_tokens
        }
        additional_fields: dict[str, Any] = {}

        if thinking_enabled:
            if not is_anthropic_thinking_model(model):
                raise BedrockModelError(
                    f"thinking_enabled=True is only valid for Anthropic Claude 4.x; " f"got model={model!r}"
                )
            additional_fields["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget_tokens,
            }
            # When thinking is on, Bedrock rejects any temperature != 1.0 (and
            # any top_p/top_k != default). Cleanest to omit them entirely.
        else:
            if temperature is not None:
                infcfg["temperature"] = temperature
            if top_p is not None:
                infcfg["topP"] = top_p
            if top_k is not None:
                additional_fields.setdefault("inferenceConfig", {})["top_k"] = top_k

        kwargs: dict[str, Any] = dict(
            modelId=model,
            messages=ua_msgs,
            inferenceConfig=infcfg,
        )
        if system_msgs:
            kwargs["system"] = [{"text": s} for s in system_msgs]
        if additional_fields:
            kwargs["additionalModelRequestFields"] = additional_fields

        logger.info(
            "Bedrock Converse: model=%s region=%s thinking=%s max_tokens=%s",
            model,
            region or self._region,
            thinking_enabled,
            infcfg["maxTokens"],
        )

        try:
            response = rt.converse(**kwargs)
        except Exception as e:  # noqa: BLE001
            raise _translate_boto_error(e) from e

        content_blocks = response["output"]["message"]["content"]
        text, reasoning = extract_text_and_reasoning(content_blocks)
        usage = response.get("usage", {}) or {}
        stop_reason = response.get("stopReason", "")

        # OpenAI-shaped dict so downstream code keeps working.
        return {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": stop_reason,
                }
            ],
            "usage": {
                "prompt_tokens": usage.get("inputTokens", 0),
                "completion_tokens": usage.get("outputTokens", 0),
                "total_tokens": usage.get("totalTokens", 0),
            },
            "model": model,
            # Bedrock-specific extras
            "reasoning_content": reasoning if reasoning else None,
            "reasoning_tokens": _count_tokens_approx(reasoning) if reasoning else 0,
            "request_payload": kwargs,
            "raw_response": _strip_unserialisable(response),
        }


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _translate_boto_error(exc: Exception) -> BedrockError:
    """Map a botocore ClientError to one of our typed exceptions."""
    code = ""
    msg = str(exc)
    exc_name = type(exc).__name__
    if hasattr(exc, "response"):
        err = getattr(exc, "response", {}).get("Error", {})  # type: ignore[union-attr]
        code = err.get("Code", "")
        msg = err.get("Message", msg)

    lower = msg.lower()
    if exc_name in ("NoCredentialsError", "PartialCredentialsError", "CredentialRetrievalError"):
        return BedrockAuthError(f"{exc_name}: {msg}")
    if code in ("AccessDeniedException", "UnrecognizedClientException", "ExpiredTokenException"):
        if "expired" in lower or "valid" in lower or "token" in lower:
            return BedrockAuthError(f"{code}: {msg}")
        return BedrockAuthError(f"{code}: {msg}")
    if code in (
        "ThrottlingException",
        "ServiceUnavailableException",
        "ModelTimeoutException",
        "InternalServerException",
    ):
        return BedrockTransientError(f"{code}: {msg}")
    if code in ("ValidationException", "ResourceNotFoundException", "ModelNotReadyException"):
        return BedrockModelError(f"{code}: {msg}")
    # Unknown — treat as transient so retry kicks in; the runner caps attempts.
    return BedrockTransientError(f"{code or exc_name}: {msg}")


def _count_tokens_approx(text: str) -> int:
    """Approximate token count for the reasoning trace. Uses tiktoken o200k_base
    as a proxy across all reasoning models; the exact provider tokenizer is
    different but the proxy is good enough for cost reconstruction."""
    if not text:
        return 0
    try:
        import tiktoken

        return len(tiktoken.get_encoding("o200k_base").encode(text))
    except Exception:
        # Fallback: ~4 chars per token rough heuristic
        return max(1, len(text) // 4)


def _strip_unserialisable(obj: Any) -> Any:
    """Drop fields like ResponseMetadata datetime that don't JSON-serialise cleanly."""
    if isinstance(obj, dict):
        return {k: _strip_unserialisable(v) for k, v in obj.items() if k not in ("ResponseMetadata",)}
    if isinstance(obj, list):
        return [_strip_unserialisable(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


# -----------------------------------------------------------------------------
# Adapter — lets the BedrockClient stand in wherever the codebase expects
# an OpenAIClient instance (same `create_completion(messages, model, ...)`
# signature). Binds Bedrock-only extras (thinking config) once at construction
# so caller sites don't have to know about them.
# -----------------------------------------------------------------------------


class BedrockOpenAIAdapter:
    """Adapter so a BedrockClient is callable wherever the codebase passes an
    OpenAIClient. `create_completion` accepts the same keyword set as the
    OpenAI version; `response_format` is silently ignored (Bedrock has no
    json-mode equivalent on Converse), `thinking_enabled` is supplied from
    the adapter's stored value."""

    def __init__(
        self,
        bedrock_client: BedrockClient,
        *,
        thinking_enabled: bool = False,
        thinking_budget_tokens: int = 8000,
        force_temperature: Optional[float] = None,
        force_top_p: Optional[float] = None,
    ) -> None:
        self._client = bedrock_client
        self._thinking_enabled = thinking_enabled
        self._thinking_budget_tokens = thinking_budget_tokens
        # When set, override whatever temperature/top_p the caller passes —
        # useful for vendor-pinned values (e.g. DeepSeek-R1 should always use 0.6).
        self._force_temperature = force_temperature
        self._force_top_p = force_top_p

    def create_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: int = 8000,
        response_format: Optional[str] = None,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        if self._force_temperature is not None:
            temperature = self._force_temperature
        if self._force_top_p is not None:
            top_p = self._force_top_p
        return self._client.create_completion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=None if self._thinking_enabled else temperature,
            top_p=None if self._thinking_enabled else top_p,
            thinking_enabled=self._thinking_enabled,
            thinking_budget_tokens=self._thinking_budget_tokens,
            response_format=response_format,
        )


# -----------------------------------------------------------------------------
# Retry helper for the runner
# -----------------------------------------------------------------------------


def call_with_retry(
    fn,
    max_attempts: int = 3,
    initial_delay: float = 5.0,
    backoff: float = 2.0,
):
    """Run `fn()` with exponential backoff on BedrockTransientError.
    BedrockAuthError and BedrockModelError raise immediately."""
    delay = initial_delay
    last_exc: Optional[BedrockError] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except BedrockAuthError:
            raise  # never retry auth failures
        except BedrockModelError:
            raise  # never retry model validation failures
        except BedrockTransientError as e:
            last_exc = e
            logger.warning(
                "Transient Bedrock error on attempt %d/%d: %s. Sleeping %ss.",
                attempt,
                max_attempts,
                e,
                delay,
            )
            if attempt < max_attempts:
                time.sleep(delay)
                delay *= backoff
    assert last_exc is not None
    raise last_exc
