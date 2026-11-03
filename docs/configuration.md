# Configuration

Runtime configuration is YAML-based and must stay out of git. Use
`config.yaml.example` as the public schema reference.

## Load Order

The settings loader resolves configuration in this order:

1. An explicit path passed to `ConfigManager`.
2. `PAIN_NARRATIVES_CONFIG`.
3. `<repo_root>/config.yaml`.
4. `~/config.yaml`.

Example:

```bash
PAIN_NARRATIVES_CONFIG=/secure/path/pain-narratives.yaml make app
```

## Main Sections

```yaml
openai:
  api_key: ""
  api_key_pain_narratives: ""
  org_id: ""

pg-prod:
  host: localhost
  database: pain_narratives
  user: pain_narratives
  password: pain_narratives_dev
  port: 5432

models:
  default_model: gpt-5-mini
  default_temperature: 1.0
  default_top_p: 1.0
  default_max_tokens: 8000
  translation_model: gpt-5-mini
  translation_temperature: 1.0
  translation_max_tokens: 8000

bedrock:
  api_key: ""
  aws_profile: ""
  default_region: us-east-1
  aws_region: us-east-1

app:
  data_root_path: ./data
  environment: development
  streamlit_server_port: 8501
  streamlit_server_address: localhost
```

`config.yaml`, `.yaml`, `.env`, and Streamlit secrets are ignored. Never force
add them.

## Prompt Configuration

Default UI prompts are stored in
`src/pain_narratives/config/default_prompts.yaml`. Revision/batch experiments
can use a separate prompt file, such as
`src/pain_narratives/config/simplified_v1_prompts.yaml`, selected by
`--prompt-version`.

Validate prompt YAML with:

```bash
uv run pytest tests/test_yaml_prompts_config.py
```

## OpenAI

Set `openai.api_key` for direct OpenAI evaluation calls. The UI also accepts a
user-provided key in supported workflows.

## AWS Bedrock

Bedrock can use standard AWS credential resolution, an AWS profile, or a
Bedrock bearer token:

- Prefer IAM role or normal AWS profile credentials.
- Set `bedrock.aws_profile` when a named profile should be used.
- Set `bedrock.api_key` only when intentionally using Bedrock bearer-token
  authentication.

Smoke-test Bedrock access with:

```bash
uv run python scripts/dev/test_bedrock_smoke.py --model deepseek-r1
```

## Local Database

For local development:

```bash
docker compose up -d postgres
cp config.yaml.example config.yaml
cd src/pain_narratives/db
uv run alembic upgrade head
```

Then create an admin user:

```bash
uv run python scripts/register_user.py
```

## Production database and credentials

Use `openai.api_key`; `api_key_pain_narratives` is accepted as a legacy fallback.
Local compose mounts `/config/config.yaml` and sets `PAIN_NARRATIVES_CONFIG`.
External PostgreSQL hosts require `sslmode: verify-full`; supply the trusted RDS
CA via `sslrootcert` or `PAIN_NARRATIVES_DB_CA`. `sslmode: disable` is accepted only
for localhost/loopback and the local compose `postgres` hostname. Credential URLs
are built with SQLAlchemy so reserved password characters are escaped correctly.
Malformed or unreadable config raises an error rather than silently using defaults.

The production image receives `PAIN_NARRATIVES_REVISION` from the reviewed build
SHA. Persisted requests retain effective model parameters and full prompt text in
the private DB; routine logs omit that content. Remote model aliases may change,
so choose versioned model IDs where supported. Stored provider responses preserve
returned model IDs/fingerprints, which are needed to interpret repeated runs.

The checkout pins the default interpreter to Python 3.13.16 in `.python-version`,
matching the digest-pinned Docker base. CI tests Python 3.11, 3.12 and 3.13;
the package minimum and formatter/type-checker defaults stay at 3.11 to preserve
compatibility. Use `uv` 0.13.3 or newer to install the pinned interpreter.

The existing lockfile supports 3.13, including the optional notebook dependencies.
Its Python-specific markers can select different NumPy/SciPy versions on 3.11
and 3.13. New persisted runs record the Python version and scientific dependency
versions; keep those with results and review environment differences before
comparing research runs. Live PostgreSQL/provider behavior still needs an
operator-run integration check before deployment.
