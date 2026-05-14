# Configuration

## `config.yaml`

Operator-supplied runtime config. Gitignored. Use
[`config.yaml.example`](../config.yaml.example) as the schema reference. Top-level keys:

- `pg-prod:` connection to the `pain_narratives_app` Postgres schema.
- `openai:` API key and organization id.
- `models:` evaluation and translation model selection (see below).
- `bedrock:` AWS auth + region for Bedrock-served models (see [`deployment.md`](deployment.md)).
- `app:` Streamlit-side options (theme, default language).

`.streamlit/config.toml` holds operator-specific Streamlit settings (server
port, base URL, theme). The example template is at
[`.streamlit/config.toml.example`](../.streamlit/config.toml.example); the live
file is gitignored.

## Default prompts (YAML-based)

The Streamlit UI loads all default prompts from
[`src/pain_narratives/config/default_prompts.yaml`](../src/pain_narratives/config/default_prompts.yaml).
Researchers update prompts by editing the YAML and restarting the app, no code
changes needed. The YAML was seeded from experiment group 12 (October 2025).

Structure:

```yaml
narrative_evaluation:
  system_role: |
    <one paragraph describing the assistant's role>
  base_prompt: |
    <general scoring instructions>
  dimensions:
    - name: "Severidad del dolor"   # Spanish per group 12
      definition: "..."
      min: 0
      max: 10
      active: true
    - name: "Discapacidad"
      definition: "..."
      min: 0
      max: 10
      active: true

questionnaires:
  PCS: { system_role: "...", instructions: "..." }   # 13 Spanish items
  BPI-IS: { ... }                                    # 7 Spanish items
  TSK-11SV: { ... }                                  # 11 Spanish items

prompt_library:
  - { id, label, description, system_role, base_prompt }   # 4 templates
```

The loader is [`src/pain_narratives/config/prompts.py`](../src/pain_narratives/config/prompts.py).
Public API:

```python
from pain_narratives.config.prompts import (
    get_system_role, get_base_prompt, get_default_dimensions,
    get_default_prompt, get_questionnaire_prompt, get_prompt_library,
    reload_prompts_config,
)
```

Validation: `uv run python tests/test_yaml_prompts_config.py`.

### Updating from an existing experiment group

If a researcher has saved a better prompt in an experiment group, copy it into
the YAML:

```sql
-- Narrative evaluation prompts
SELECT system_role, base_prompt, dimensions
FROM pain_narratives_app.experiments_groups
WHERE experiments_group_id = <id>;

-- Questionnaire prompts
SELECT questionnaire_type, system_role, instructions
FROM pain_narratives_app.questionnaire_prompts
WHERE experiments_group_id = <id>;
```

Then paste the values into `default_prompts.yaml` and restart the app. YAML
gotchas: use spaces (not tabs) for indentation; use the `|` block-scalar marker
for multi-line strings; use single quotes around YAML strings that themselves
contain double quotes.

### Revision experiments use a separate prompt set

The DeepSeek-R1 / Sonnet-4.5 rebuttal runs use
[`src/pain_narratives/config/simplified_v1_prompts.yaml`](../src/pain_narratives/config/simplified_v1_prompts.yaml),
not `default_prompts.yaml`. The simplified prompts strip explanation/reasoning
text from each sub-call so the model returns only structured answer values. See
[`revision_experiments.md`](revision_experiments.md) for the rationale.

## Translation model

The translation service ([`src/pain_narratives/core/translation_service.py`](../src/pain_narratives/core/translation_service.py))
can use a dedicated translation model so the evaluation model can stay
frontier-tier. The shipped defaults in
[`config.yaml.example`](../config.yaml.example) use the same model for both
(`gpt-5-mini`); override `translation_model` / `translation_temperature` /
`translation_max_tokens` under the `models:` block to split them.

The service translates both the `reasoning` and `explanations` fields and
preserves the JSON shape. Independent of which evaluation model the operator
selects.

## Deprecated: `user_prompts` table

The `user_prompts` table (SQLModel: `UserPrompt`) is **deprecated**. The
Streamlit UI no longer reads or writes it. The YAML config is the authoritative
source for default prompts. The table is kept in the schema for backward
compatibility with CLI scripts/tests. If removal is desired, plan to:

1. Drop the table via an alembic migration.
2. Remove `UserPrompt` from `models_sqlmodel.py`.
3. Remove `save_user_prompt` / `get_user_prompts` / `delete_user_prompt` from `DatabaseManager`.
4. Remove `tests/test_user_prompt_current.py` and any CLI references in `scripts/manage_users.py`.
