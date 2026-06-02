# AINarratives

AINarratives is a research platform for evaluating chronic-pain patient
narratives with large language models. It provides a Streamlit web application,
batch evaluation tools, prompt configuration, user management, and notebook-based
analysis workflows for comparing model outputs with questionnaire data.

The project is intended for research use. Do not commit patient data, private
configuration, generated analysis artifacts, checkpoints, logs, or credentials.

## Features

- Streamlit interface for single-narrative evaluation and experiment groups.
- Batch runner for repeated evaluations across narrative sets.
- OpenAI and AWS Bedrock model clients.
- YAML-managed narrative and questionnaire prompts.
- PostgreSQL persistence through SQLModel and Alembic migrations.
- English and Spanish UI localization.
- Reproducible notebook and script-based analysis workflows.

## Quick Start

Prerequisites:

- Python 3.11+
- `uv`
- PostgreSQL, either local or via Docker
- An OpenAI API key for OpenAI-backed evaluations

Clone and install:

```bash
git clone <repository-url>
cd pain-narratives-app-public
uv sync
```

Start a local database with Docker:

```bash
docker compose up -d postgres
cp config.yaml.example config.yaml
```

Edit `config.yaml` so `pg-prod` points at the local Docker database and the
`openai` section contains your API key. Then run migrations and create the first
admin user:

```bash
cd src/pain_narratives/db
uv run alembic upgrade head
cd ../../..
uv run python scripts/register_user.py
```

Run the app:

```bash
make app
```

Open `http://localhost:8501`.

## Configuration

Configuration is loaded in this order:

1. Explicit path passed in code.
2. `PAIN_NARRATIVES_CONFIG`.
3. `<repo_root>/config.yaml`.
4. `~/config.yaml`.

For normal local development, copy `config.yaml.example` to `config.yaml` and
keep it untracked. See [docs/configuration.md](docs/configuration.md) for the
full schema and provider-specific notes.

## Common Commands

Run the Streamlit app:

```bash
make app
```

Create users:

```bash
uv run python scripts/register_user.py
uv run python scripts/register_user_batch.py <username> <password> --admin
```

Run a batch evaluation:

```bash
uv run python scripts/run_batch_evaluation.py --help
```

Run tests:

```bash
uv run pytest
```

Live database/cloud tests are skipped by default. Run them only with a private
config:

```bash
RUN_LIVE_DB_TESTS=1 PAIN_NARRATIVES_CONFIG=/path/to/private.yaml uv run pytest -m live_db
```

Run publication/analysis notebooks:

```bash
make list-notebooks
make run-notebooks
make consolidate-tables
```

Generated notebook outputs are intentionally ignored by git.

## Documentation

Start with [docs/README.md](docs/README.md). Key topics:

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Deployment](docs/deployment.md)
- [Experiments and batch runs](docs/experiments.md)
- [Analysis workflows](docs/analysis.md)
- [Operations](docs/operations.md)
- [User management](docs/user_management.md)

## Repository Hygiene

The public repository should contain source code, reusable notebooks, tests, and
general documentation. Keep these out of git:

- `config.yaml`, `.yaml`, `.env`, and Streamlit secrets.
- Raw patient data and private Excel workbooks.
- Generated CSV/XLSX/PDF/Parquet outputs.
- Batch checkpoints and logs.
- Local notes under `docs/local/`.

Before publishing changes, run:

```bash
git status --short --ignored
git diff --check
uv run pytest
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
