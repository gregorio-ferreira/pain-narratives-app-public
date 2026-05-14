# AWS Bedrock Setup for Revision Experiments

The revision experiments should use AWS credentials through boto3 rather than
short-lived Bedrock bearer tokens whenever possible. The recommended workflow
on a long-lived host is an MFA-backed AWS profile (or, on EC2, an attached
instance profile).

## 1. Create or Refresh the MFA Session

Run your local MFA helper to write temporary STS credentials into an AWS profile
(for example `mfa`), then:

```bash
export AWS_PROFILE=mfa
aws sts get-caller-identity
```

Refresh the session before long runs if it has less than a few hours remaining.

## 2. Configure the App

In `config.yaml`, prefer:

```yaml
bedrock:
  api_key: ""
  aws_profile: mfa
  default_region: us-east-1
  aws_region: us-east-1
```

You can also omit `aws_profile` and run commands with `AWS_PROFILE=mfa`.

Use Bedrock bearer-token auth only as a fallback:

```yaml
bedrock:
  api_key: bedrock-api-key-...
  default_region: us-east-1
```

When `api_key` is set, the Bedrock client intentionally uses bearer-token auth
instead of the AWS profile.

## 3. Verify Access

```bash
bash scripts/dev/probe_ec2_bedrock_access.sh
uv run python scripts/dev/test_bedrock_smoke.py \
  --model deepseek-r1 \
  --profile mfa \
  --region us-east-1
uv run python scripts/dev/test_bedrock_smoke.py \
  --model sonnet-4-5-thinking \
  --profile mfa \
  --region us-east-1
```

Both smoke tests should print an STS identity, token usage, and a short answer.

## 4. Run Experiments

Pass the profile and region explicitly for reproducibility:

```bash
uv run python scripts/run_batch_evaluation.py \
  --from-groups 38,39,40 \
  --run-number 2 \
  --model us.deepseek.r1-v1:0 \
  --model-provider bedrock_deepseek \
  --prompt-version simplified_v1 \
  --temperature 0.6 \
  --bedrock-profile mfa \
  --bedrock-region us-east-1 \
  --description "Revision Run 2 - DeepSeek-R1 simplified_v1" \
  --consecutive-failure-threshold 5 \
  --yes
```

For Claude Sonnet 4.5 with thinking, include `--thinking-enabled` and
`--thinking-budget-tokens 8000`, and omit `--temperature`.
