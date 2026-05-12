#!/usr/bin/env bash
# Probe an EC2 instance for Bedrock authentication options.
#
# Run this script on the EC2 itself. It checks, in priority order:
#   1. Whether an IAM instance profile is attached, and what role it assumes
#   2. Whether that role can list Bedrock foundation models in us-east-1
#   3. Whether the two revision-experiment models are accessible
#   4. As a fall-back, whether a Bedrock API key in config.yaml works
#
# Prints a clear "USE THIS AUTH" recommendation at the end. Exits 0 if any
# working path is found, non-zero otherwise.
#
# Usage:
#   bash scripts/dev/probe_ec2_bedrock_access.sh
#
# This is read-only — no resources are created, modified, or deleted.

set -u
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$*"; }
bold()  { printf "\033[1m%s\033[0m\n" "$*"; }

REGION="${BEDROCK_REGION:-us-east-1}"
MODELS=(
  "us.deepseek.r1-v1:0"
  "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)

bold "========== STEP 1: EC2 instance metadata =========="
# IMDSv2 — get a token, then ask metadata for the iam/info
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60" --max-time 3 2>/dev/null || true)
if [ -z "$TOKEN" ]; then
  yellow "  IMDS not reachable. Either this isn't an EC2, or IMDSv2 hop-limit is restrictive."
  IS_EC2=false
else
  IS_EC2=true
  INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || true)
  AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null || true)
  IAM_INFO=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/iam/info 2>/dev/null || true)
  green "  Instance: $INSTANCE_ID  AZ: $AZ"
  if [ -n "$IAM_INFO" ]; then
    green "  IAM info from IMDS:"
    echo "$IAM_INFO" | sed 's/^/    /'
  else
    yellow "  No IAM instance profile attached. Auth will need a fall-back (Bedrock API key)."
  fi
fi
echo ""

bold "========== STEP 2: AWS STS identity =========="
if command -v aws >/dev/null 2>&1; then
  IDENT=$(aws sts get-caller-identity 2>&1 || true)
  if echo "$IDENT" | grep -q "Account"; then
    green "  $IDENT"
    if echo "$IDENT" | grep -q "assumed-role"; then
      green "  -> This identity is an instance-profile assumed role."
    elif echo "$IDENT" | grep -q ":user/"; then
      yellow "  -> This identity is a plain IAM user (likely from ~/.aws/credentials)."
    fi
  else
    red "  STS failed: $IDENT"
  fi
else
  yellow "  aws CLI not installed; skipping STS check. Install with: dnf install -y aws-cli"
fi
echo ""

bold "========== STEP 3: Bedrock model access in $REGION =========="
HAS_BEDROCK_ROLE_ACCESS=false
if command -v aws >/dev/null 2>&1; then
  MODELS_JSON=$(aws bedrock list-foundation-models --region "$REGION" 2>&1 || true)
  if echo "$MODELS_JSON" | head -c 1 | grep -q '{'; then
    COUNT=$(echo "$MODELS_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('modelSummaries',[])))" 2>/dev/null || echo "?")
    green "  list-foundation-models OK ($COUNT models visible)"
    HAS_BEDROCK_ROLE_ACCESS=true
  else
    yellow "  list-foundation-models failed (role may not have bedrock:ListFoundationModels):"
    echo "$MODELS_JSON" | head -5 | sed 's/^/    /'
  fi
fi
echo ""

bold "========== STEP 4: Try invoking each model via the IAM role =========="
ROLE_INVOKE_WORKS=false
if command -v aws >/dev/null 2>&1; then
  for M in "${MODELS[@]}"; do
    OUT=$(aws bedrock-runtime converse \
      --model-id "$M" \
      --messages '[{"role":"user","content":[{"text":"reply only with: ok"}]}]' \
      --inference-config '{"maxTokens":50}' \
      --region "$REGION" 2>&1 || true)
    if echo "$OUT" | grep -q '"stopReason"'; then
      green "  $M -> OK (IAM role can invoke)"
      ROLE_INVOKE_WORKS=true
    else
      yellow "  $M -> denied / error:"
      echo "$OUT" | head -3 | sed 's/^/      /'
    fi
  done
fi
echo ""

bold "========== STEP 5: Bedrock API-key fall-back (if config.yaml exists) =========="
KEY_INVOKE_WORKS=false
CONFIG_DIR="${CONFIG_DIR:-$(pwd)}"
if [ -f "$CONFIG_DIR/config.yaml" ]; then
  KEY=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_DIR/config.yaml')).get('bedrock',{}).get('api_key',''))" 2>/dev/null || true)
  if [ -n "$KEY" ] && [ "${KEY:0:16}" = "bedrock-api-key-" ]; then
    yellow "  Found Bedrock API key in config.yaml"
    # Decode expiry, briefly
    python3 - <<PY 2>/dev/null || true
import base64, yaml
from urllib.parse import parse_qs
from datetime import datetime, timezone, timedelta
key = yaml.safe_load(open("$CONFIG_DIR/config.yaml"))["bedrock"]["api_key"]
qs = base64.b64decode(key.removeprefix("bedrock-api-key-") + "==").decode().split("?", 1)[1]
p = {k: v[0] for k, v in parse_qs(qs).items()}
if "X-Amz-Date" in p and "X-Amz-Expires" in p:
    issued = datetime.strptime(p["X-Amz-Date"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    exp = issued + timedelta(seconds=int(p["X-Amz-Expires"]))
    now = datetime.now(timezone.utc)
    remaining = exp - now
    print(f"    Expires: {exp.isoformat()}  ({remaining} remaining)")
    print(f"    Status:  {'EXPIRED' if remaining.total_seconds() < 0 else 'valid'}")
PY
    AWS_BEARER_TOKEN_BEDROCK="$KEY" AWS_PROFILE= aws bedrock-runtime converse \
      --model-id "${MODELS[0]}" \
      --messages '[{"role":"user","content":[{"text":"reply only with: ok"}]}]' \
      --inference-config '{"maxTokens":50}' \
      --region "$REGION" > /tmp/bedrock_key_probe.out 2>&1 || true
    if grep -q '"stopReason"' /tmp/bedrock_key_probe.out 2>/dev/null; then
      green "  Bedrock API key works for invoking ${MODELS[0]}"
      KEY_INVOKE_WORKS=true
    else
      yellow "  Bedrock API key invocation failed:"
      head -3 /tmp/bedrock_key_probe.out | sed 's/^/      /'
    fi
  else
    yellow "  No bedrock.api_key in $CONFIG_DIR/config.yaml"
  fi
else
  yellow "  $CONFIG_DIR/config.yaml not found"
fi
echo ""

bold "========== RECOMMENDATION =========="
if $ROLE_INVOKE_WORKS; then
  green "USE THIS AUTH: IAM instance-profile role."
  green "  - boto3 picks it up automatically; do NOT set AWS_BEARER_TOKEN_BEDROCK"
  green "  - Drop bedrock.api_key from config.yaml (or leave it; the env var will not be exported if absent)"
  green "  - Long-term auth, no 12h refresh dance"
  exit 0
elif $KEY_INVOKE_WORKS; then
  yellow "USE THIS AUTH: Bedrock API key in config.yaml (fall-back)."
  yellow "  - The runner exports AWS_BEARER_TOKEN_BEDROCK at startup"
  yellow "  - If key is short-term (12h), monitor expiry; runner halts cleanly and supports --resume"
  yellow "  - Strongly consider asking UOC IT to attach an IAM role with Bedrock perms — see docs/EC2_HANDOFF.md §3.1"
  exit 0
else
  red "NEITHER PATH WORKS."
  red "  - The IAM principal here (if any) does not have Bedrock permissions in $REGION"
  red "  - And no working Bedrock API key was found in $CONFIG_DIR/config.yaml"
  red "Next steps:"
  red "  1. Confirm the EC2's instance profile has an attached IAM policy granting"
  red "     bedrock:InvokeModel + bedrock:Converse against the model ARNs"
  red "     (or request model access in the Bedrock console for the relevant region)"
  red "  2. Or generate a Bedrock API key in us-east-1 and put it in config.yaml"
  red "     (see docs/revision/AWS_BEDROCK_SETUP.md)"
  exit 1
fi
