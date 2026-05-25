# Configuration

Runtime configuration is YAML-based and must stay out of git. Use
`config.yaml.example` as the public schema reference.

## Load Order

The settings loader resolves configuration in this order:

1. An explicit path passed to `ConfigManager`.
2. `PAIN_NARRATIVES_CONFIG`.
3. Project `.yaml`.
4. `~/.yaml`.

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
