# Architecture

## System

AINarratives is a Streamlit app that drives LLM evaluations of chronic-pain
patient narratives. Three runtime components:

- **Streamlit UI** ([`src/pain_narratives/ui/`](../src/pain_narratives/ui/)) — operator-facing app for browsing narratives, configuring experiment groups, running evaluations, and collecting expert feedback. Deployed on EC2 (see [`deployment.md`](deployment.md)).
- **PostgreSQL** — schema `pain_narratives_app` on AWS RDS in `eu-central-1` (account `ai-for-society`). Read-write from both the Streamlit app and batch runners.
- **LLM providers** — OpenAI for the original GPT-5 baseline; AWS Bedrock (`us-east-1`) for the revision-experiment models. The OpenAI client lives at [`src/pain_narratives/core/openai_client.py`](../src/pain_narratives/core/openai_client.py); the Bedrock client at [`src/pain_narratives/core/bedrock_client.py`](../src/pain_narratives/core/bedrock_client.py).

## Package layout

```
src/pain_narratives/
├── ui/                     Streamlit pages and components (app.py is the entry point)
├── core/                   LLM clients, database manager, analytics, translation service,
│                           questionnaire prompts
├── config/                 settings loader; default_prompts.yaml + prompts.py;
│                           simplified_v1_prompts.yaml for revision experiments
├── batch/                  processor.py — long-running batch evaluation pipeline
├── experiments/            runner.py — single-narrative evaluation orchestration
├── db/                     SQLModel definitions, alembic migrations,
│                           models_acm_202512.py (read-mostly analysis schema)
└── locales/                en.yml / es.yml for UI i18n
```

Notebooks under [`notebooks/`](../notebooks/) consume the database read-only to
produce the publication tables and figures; orchestrated by
[`scripts/run_all_notebooks.sh`](../scripts/run_all_notebooks.sh) and the
Makefile target `publication`.

## Database schema

Primary schema is `pain_narratives_app`. Key tables:

| Table | Purpose |
|---|---|
| `narratives` | One row per submitted patient narrative. Includes `narrative_hash`, `word_count`, `char_count` (added by migration `0000000dedup`). |
| `experiments_groups` | A run configuration: system role, base prompt, dimensions JSON, owner. |
| `experiments_list` | One row per (group × narrative × rep). Stores `model`, `model_provider`, `temperature`, `prompt_version`, `reasoning_tokens`, `succeeded`, `parsed_answers`. |
| `evaluation_results` | Detailed sub-call results: `result_type` is one of `dimensions`, `PCS`, `BPI-IS`, `TSK-11SV`. |
| `request_response` | Full request payload and response JSON for the dimensions call (questionnaires are not persisted here). |
| `questionnaire_prompts` | Per-group questionnaire system prompts and instructions. |
| `users`, `experiment_group_users` | Authentication and per-user group membership. See [`user_management.md`](user_management.md). |
| `assessment_feedback`, `questionnaire_feedback` | Expert evaluator scores collected through the Streamlit UI. |

A separate read-mostly schema `pain_narratives_acm_202512` ([`models_acm_202512.py`](../src/pain_narratives/db/models_acm_202512.py))
holds the snapshot used by the publication notebooks. It is not under alembic;
its tables already exist in production.

### Alembic state

```
alembic head: 2026051100rev   (add prompt_version + reasoning_tokens to experiments_list)
```

`prompt_version` and `reasoning_tokens` are both nullable and additive, so the
production app keeps working unchanged after the migration.

Do **not** `alembic downgrade` past `260d578db51b`, `47f5ef239b72`, or
`bad99e59d04b` on production: those revisions exist in the alembic chain but
their downgrade bodies were rewritten as safe-for-fresh-install no-ops during
the public-repo consolidation. Forward-only is fine; the dedup migration
`0000000dedup` has a real downgrade and can be reversed safely.

## Narratives dataset

| Set | Count | Definition |
|---|---:|---|
| Rows in `narratives` | 303 | Total rows, including duplicates from batch repetitions. |
| Empty narratives | 11 | Whitespace-only; excluded from analysis. |
| Non-empty rows | 292 | One per `narrative_id`. |
| Unique by `narrative_hash` | 177 | Deduplicated by content. |
| **Published GPT-5 ACM baseline** (groups 38, 39, 40) | **152** | Canonical input set for the revision experiments. |
| Any human (expert) feedback | 47 | From 19 evaluators, via the Streamlit expert UI. |
| **In ACM baseline AND have human feedback** | **40** | Subset on which LLM-vs-human correlation analyses are computed. |

The 40-narrative human-comparable subset uses different `narrative_id`s but the
same content (`narrative_hash`) as the synthetic-batch entries. The
[`narratives_inventory.csv`](revision/narratives_inventory.csv) exposes both
views. Regenerate it with:

```bash
uv run python scripts/dev/build_narratives_inventory.py
```

Token-count distributions (`o200k_base` tokenizer):

| Subset | n | min | median | mean | max |
|---|---:|---:|---:|---:|---:|
| All non-empty rows | 292 | 1 | 271 | 508 | 12,806 |
| ACM baseline only | 152 | 4 | 304 | 489 | 3,718 |
| Human-comparable (40) | 40 | 38 | 272 | 459 | 2,161 |

The 12,806-token outlier is a Catalan research-grant application that was
accidentally pasted into the system; it's not in any experiment group.

## Cross-references

- Runtime configuration: [`configuration.md`](configuration.md)
- Deployment topology and credentials: [`deployment.md`](deployment.md)
- Active rebuttal experiments and the prompt/model matrix: [`revision_experiments.md`](revision_experiments.md)
