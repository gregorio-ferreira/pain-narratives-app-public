# Deployment

This guide describes a generic EC2-style deployment. Adapt paths, users, and
domains to your environment.

## Host Setup

```bash
cd /opt
git clone <repository-url> pain-narratives-app-public
cd pain-narratives-app-public

curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

Copy private runtime files from your secret store:

- `config.yaml` or another YAML file referenced by `PAIN_NARRATIVES_CONFIG`
- Optional `.streamlit/config.toml`

Run migrations:

```bash
cd src/pain_narratives/db
uv run alembic upgrade head
cd ../../..
```

Create an admin user if this is a new database:

```bash
uv run python scripts/register_user.py
```

## Running the App

Development-style launch:

```bash
make app
```

Production deployments should use a process manager such as `systemd`.

## systemd Template

The repository includes `deploy/pain-narratives.service`. Copy it to the host
unit directory and fill in placeholders:

```bash
sudo cp deploy/pain-narratives.service /etc/systemd/system/pain-narratives.service
sudo $EDITOR /etc/systemd/system/pain-narratives.service
sudo systemctl daemon-reload
sudo systemctl enable --now pain-narratives
```

Use an environment file for host-specific settings:

```ini
EnvironmentFile=-/etc/pain-narratives.env
```

Example `/etc/pain-narratives.env`:

```text
PAIN_NARRATIVES_CONFIG=/etc/pain-narratives/config.yaml
```

## Bedrock Access

Bedrock-backed models use standard AWS credential resolution unless a profile or
bearer token is configured. Preferred order:

1. IAM role or instance profile.
2. Named AWS profile via `bedrock.aws_profile` or `--bedrock-profile`.
3. Bedrock bearer token in private config.

Validate before running a batch:

```bash
aws sts get-caller-identity
uv run python scripts/dev/test_bedrock_smoke.py --model deepseek-r1
uv run python scripts/dev/test_bedrock_smoke.py --model sonnet-4-5-thinking
```

## Smoke Test

After deployment:

```bash
systemctl status pain-narratives
journalctl -u pain-narratives -n 100 --no-pager
```

Then verify in the UI:

- Login works.
- Evaluation groups load.
- A narrative can be selected.
- Admin user management is available to admin users.

Run the local test suite on the host without live integrations:

```bash
uv run pytest
```

Run live integration checks only with explicit private config:

```bash
RUN_LIVE_DB_TESTS=1 PAIN_NARRATIVES_CONFIG=/secure/path/config.yaml uv run pytest -m live_db
```
