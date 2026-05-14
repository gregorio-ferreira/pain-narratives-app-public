"""Smoke test for the Bedrock client.

Sends one short prompt to a given model and prints the parsed result. Confirms
the wiring (bearer token, model id, request shape, response extraction) before
running a 4,500-call batch.

Usage:
    uv run python scripts/dev/test_bedrock_smoke.py --model deepseek-r1
    uv run python scripts/dev/test_bedrock_smoke.py --model sonnet-4-5-thinking
    uv run python scripts/dev/test_bedrock_smoke.py --model sonnet-4-5  # no thinking

Exits non-zero on auth or model error; treats successful calls as the only pass.
"""

from __future__ import annotations

import argparse
import logging
import sys

from pain_narratives.core.bedrock_client import (
    BedrockAuthError,
    BedrockClient,
    BedrockModelError,
    BedrockTransientError,
    inspect_bearer_token,
)
from pain_narratives.config.settings import get_settings

_PRESETS: dict[str, dict] = {
    "deepseek-r1": {
        "model": "us.deepseek.r1-v1:0",
        "kwargs": {"temperature": 0.6, "top_p": 0.9, "max_tokens": 800},
    },
    "sonnet-4-5": {
        "model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "kwargs": {"temperature": 0.0, "max_tokens": 800},
    },
    "sonnet-4-5-thinking": {
        "model": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "kwargs": {"thinking_enabled": True, "thinking_budget_tokens": 4000, "max_tokens": 5000},
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(_PRESETS), help="Preset to exercise")
    ap.add_argument(
        "--prompt",
        default="In one sentence, what is fibromyalgia? Reply with the sentence and nothing else.",
        help="User prompt to send",
    )
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument(
        "--region",
        help="AWS region for Bedrock calls. Defaults to bedrock.default_region from config.",
    )
    ap.add_argument(
        "--profile",
        help="AWS profile to use for boto3 credential auth (for example: mfa).",
    )
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    preset = _PRESETS[args.model]

    # Diagnostic: token info
    cfg = get_settings().bedrock_config
    if cfg.api_key:
        info = inspect_bearer_token(cfg.api_key)
    else:
        info = None
    if info is not None and info.expires_at is not None:
        remaining = info.time_remaining()
        print(f"Bearer token expires at {info.expires_at.isoformat()} (in {remaining})")
    elif cfg.api_key:
        print("Bearer token: no expiry recorded (likely a long-term key)")
    else:
        print("Bearer token: not configured; using boto3 credential chain (for example EC2 IAM role)")

    print(f"Region: {cfg.default_region}")
    if args.region:
        print(f"Region override: {args.region}")
    if args.profile:
        print(f"AWS profile override: {args.profile}")
    print(f"Model:  {preset['model']}")
    print(f"Kwargs: {preset['kwargs']}\n")

    client = BedrockClient(region=args.region, profile_name=args.profile)
    try:
        auth = client.check_credentials()
    except BedrockAuthError as e:
        print(f"PRE-FLIGHT FAILED: {e}")
        return 2
    print(f"Auth:   {auth.auth_method}")
    if auth.profile_name:
        print(f"Profile: {auth.profile_name}")
    if auth.principal_arn:
        print(f"STS:    {auth.principal_arn}")
    if auth.expires_at:
        print(f"Expires: {auth.expires_at.isoformat()} (in {auth.time_remaining()})")
    print("")

    messages = [{"role": "user", "content": args.prompt}]
    try:
        resp = client.create_completion(messages=messages, model=preset["model"], **preset["kwargs"])
    except BedrockAuthError as e:
        print(f"AUTH ERROR: {e}")
        return 2
    except BedrockTransientError as e:
        print(f"TRANSIENT ERROR (after retries): {e}")
        return 3
    except BedrockModelError as e:
        print(f"MODEL ERROR: {e}")
        return 4

    answer = resp["choices"][0]["message"]["content"]
    reasoning = resp.get("reasoning_content")
    usage = resp["usage"]

    print(f"Finish reason: {resp['choices'][0]['finish_reason']}")
    print(
        f"Usage:         prompt={usage['prompt_tokens']}  completion={usage['completion_tokens']}  "
        f"total={usage['total_tokens']}  (reasoning≈{resp['reasoning_tokens']})"
    )
    print("\n--- Answer ---")
    print(answer)
    if reasoning:
        print(f"\n--- Reasoning ({len(reasoning)} chars) ---")
        print(reasoning[:1000] + ("..." if len(reasoning) > 1000 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
