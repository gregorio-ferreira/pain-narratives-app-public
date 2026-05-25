# Architecture

AINarratives has three runtime parts:

- **Streamlit UI** in `src/pain_narratives/ui/` for narrative evaluation,
  experiment group management, expert feedback, and administration.
- **PostgreSQL** using the `pain_narratives_app` schema for users, narratives,
  experiment groups, model requests, parsed results, and feedback.
- **LLM providers** through `OpenAIClient` and `BedrockClient`, selected by
  experiment configuration.

## Package Layout

```text
src/pain_narratives/
├── ui/             Streamlit entry point, pages, components, localization helpers
├── core/           database manager, model clients, analytics, questionnaire logic
├── config/         settings loader and YAML prompt definitions
├── batch/          long-running batch evaluation pipeline
├── experiments/    single-narrative orchestration helpers
├── analysis/       reusable analysis data-layer helpers
├── db/             SQLModel models and Alembic migrations
└── locales/        English and Spanish UI strings
```

Reusable scripts live under `scripts/`; exploratory and publication notebooks
live under `notebooks/`.

## Main Database Tables

| Table | Purpose |
|---|---|
| `users` | Login and admin accounts. |
| `experiment_group_users` | Per-user access to experiment groups. |
| `narratives` | Submitted narrative text and deduplication metadata. |
| `experiments_groups` | Evaluation group configuration and ownership. |
| `experiments_list` | One row per evaluated narrative/run, with model/provider metadata. |
| `evaluation_results` | Parsed dimension and questionnaire results per experiment. |
| `request_response` | Full dimensions-call request/response payload. |
| `questionnaire_prompts` | Per-group questionnaire prompts. |
| `assessment_feedback` | Expert assessment feedback collected in the UI. |
| `questionnaire_feedback` | Expert questionnaire feedback collected in the UI. |

The separate `models_acm_202512.py` module describes a publication-analysis
schema used by historical notebooks. It is not part of the main Alembic-managed
application schema.

## Migrations

Alembic configuration is in `src/pain_narratives/db/`. For a fresh database:

```bash
cd src/pain_narratives/db
uv run alembic upgrade head
```

Application migrations target `pain_narratives_app`. Treat production
downgrades as a separate operational procedure and verify backups first.

## Data Privacy

The repository should not include raw patient narratives, private workbooks,
generated analysis outputs, credentials, logs, or checkpoints. Public analysis
metadata should be limited to non-identifying summaries such as counts, hashes,
and reproducibility instructions.
