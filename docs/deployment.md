# Deployment

The production AINarratives app runs on an EC2 instance in `eu-central-1`
serving a Streamlit UI, with Postgres on RDS in the same region and AWS Bedrock
inference in `us-east-1`. This page covers the deploy layout, AWS Bedrock
authentication, and the recommended `systemd` configuration.

## EC2 host layout

Recommended path: `/opt/pain-narratives-app-public` (or wherever the operator
prefers). The repo manages dependencies with `uv`:

```bash
cd /opt
git clone https://github.com/gregorio-ferreira/pain-narratives-app-public.git
cd pain-narratives-app-public
git checkout main && git pull

# uv (skip if already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync
uv run python -c "import boto3, sqlmodel, streamlit; print('deps OK')"
```

Operator-specific configs are gitignored — copy them from a safe location after
cloning:

- `config.yaml` (DB credentials, Bedrock auth, model selection)
- `.streamlit/config.toml` (port, base URL, theme)

Validate the DB connection and alembic head before launching:

```bash
cd /opt/pain-narratives-app-public/src/pain_narratives/db
uv run alembic current   # expected: 2026051100rev
```

If the head is older, run `uv run alembic upgrade head` (the revision-experiment
columns are additive and nullable, so the running app is not affected).

## AWS Bedrock authentication

The revision experiments call Bedrock in `us-east-1`. Authentication options,
in order of preference:

### 1. EC2 IAM instance profile (preferred)

If the EC2 has an instance profile with `bedrock:InvokeModel` and
`bedrock:Converse` permissions on the revision model ARNs, boto3 picks the
credentials up automatically — no token to refresh. Strongly recommended given
each model takes ~3 hours of wall time.

Diagnostic script:

```bash
bash scripts/dev/probe_ec2_bedrock_access.sh
```

It checks the IMDS instance profile, STS identity, `bedrock list-foundation-models`,
attempts a real call against each revision model, and finally falls back to
the `config.yaml` bearer token. Ends with a `USE THIS AUTH: ...` recommendation.

Manual checks:

```bash
curl -s http://169.254.169.254/latest/meta-data/iam/info && echo
aws sts get-caller-identity
aws bedrock list-foundation-models --region us-east-1 | head -50
uv run python scripts/dev/test_bedrock_smoke.py --model deepseek-r1
```

### 2. MFA-backed AWS profile

If the EC2 has no Bedrock-capable instance profile, use a local MFA helper to
write temporary STS credentials into a profile named `mfa`:

```bash
/home/ubuntu/aws_mfa_session.sh
export AWS_PROFILE=mfa
aws sts get-caller-identity
```

`config.yaml`:

```yaml
bedrock:
  api_key: ""
  aws_profile: mfa
  default_region: us-east-1
  aws_region: us-east-1
```

You can also leave `aws_profile` unset and pass it on the command line:

```bash
uv run python scripts/run_batch_evaluation.py \
  --bedrock-profile mfa --bedrock-region us-east-1 ...
```

Refresh the session before long runs if fewer than a few hours remain.

### 3. Bedrock bearer token (fallback)

If neither instance profile nor MFA is available:

1. AWS Console → Bedrock → API keys → Generate API key, in `us-east-1`.
2. Add to `config.yaml`:
   ```yaml
   bedrock:
     api_key: bedrock-api-key-<the-long-base64>
     default_region: us-east-1
   ```
3. Smoke-test: `uv run python scripts/dev/test_bedrock_smoke.py --model deepseek-r1`

When the 12-hour token expires the batch runner halts cleanly with a clear
`Bedrock auth failure mid-batch` log line and writes a checkpoint. Refresh the
key and rerun with `--resume`.

### Model access in `us-east-1`

Confirm the revision model IDs are accessible to your IAM principal:

```bash
uv run python scripts/dev/test_bedrock_smoke.py --model deepseek-r1
uv run python scripts/dev/test_bedrock_smoke.py --model sonnet-4-5-thinking
```

If you see `AccessDeniedException: You don't have access to the model with the
specified model ID`, request access in the Bedrock console (Model access page)
for that model in `us-east-1`. Non-Anthropic approvals are typically minutes;
Anthropic can take longer.

The current Bedrock account is **730335551675** (UOC academic account, user
`jferreirade`). RDS lives in a different account in `eu-central-1`.

## `systemd` service

The runtime unit lives at `/etc/systemd/system/pain-narratives.service`. The
in-repo template is [`deploy/pain-narratives.service`](../deploy/pain-narratives.service):
a minimal `Restart=always` configuration with placeholders for `<APP_USER>`,
`<APP_ROOT>`, and `<UV_BIN_DIR>`. To deploy:

```bash
sudo cp deploy/pain-narratives.service /etc/systemd/system/
sudo $EDITOR /etc/systemd/system/pain-narratives.service   # fill placeholders
sudo systemctl daemon-reload
sudo systemctl enable --now pain-narratives
```

For production hosts, the template should be hardened with memory limits, a
crash-loop ceiling, and filesystem protections. The full hardened unit and the
rationale for each directive are in
[`improvements.md`](improvements.md#2-systemd-hardening) (Track 2 of the
backlog).

## Post-deploy smoke test

```bash
# UI
make app    # then open http://<host>:8501

# Click through:
#   - language toggle (en/es)
#   - log in and list experiment groups 38/39/40
#   - load a narrative for evaluation
#   - questionnaire feedback page

# Batch dry-run (no tokens spent)
uv run python scripts/run_batch_evaluation.py --input data/narratives.xlsx --dry-run
```

The notebook smoke test (cheapest one):

```bash
uv run jupyter nbconvert --to notebook --execute \
  notebooks/02_patient_demographics_for_publication.ipynb \
  --output notebooks/_smoke_test_02.ipynb
rm notebooks/_smoke_test_02.ipynb
```
