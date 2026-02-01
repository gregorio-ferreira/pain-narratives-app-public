# Default Prompts Configuration Guide

## Overview

As of October 2025, the Pain Narratives Application uses a **centralized YAML-based configuration system** for all default prompts. This makes it easy for researchers to update default prompts without modifying Python code.

**Key File**: `src/pain_narratives/config/default_prompts.yaml`

## What's in the Configuration?

The YAML file contains three main sections:

### 1. Narrative Evaluation Prompts

These are used for the main pain narrative assessments:

- **system_role**: The AI's role and expertise (e.g., "You are an expert in evaluating chronic pain...")
- **base_prompt**: General instructions about scoring and evaluation approach
- **dimensions**: The evaluation dimensions (currently in Spanish based on experiment group 12):
  - Severidad del dolor (Pain Severity): 0-10 scale
  - Discapacidad (Disability): 0-10 scale

### 2. Questionnaire Prompts

Three validated questionnaires with their specific prompts:

- **PCS** (Pain Catastrophizing Scale): 13 questions in Spanish
- **BPI-IS** (Brief Pain Inventory - Interference Scale): 7 questions in Spanish
- **TSK-11SV** (Tampa Scale for Kinesiophobia): 11 questions in Spanish

Each has:

- `system_role`: Instructions for the AI to impersonate the patient
- `instructions`: Detailed questionnaire questions and output format

### 3. Prompt Library

Pre-configured prompt templates for different use cases:

- Fibromyalgia Expert Assessment (Default)
- Fibromyalgia Comprehensive
- General Pain Assessment
- Research Analysis

## How to Update Default Prompts

### Updating from an Experiment Group

If a researcher has created an experiment group with better prompts (like experiment group 12), follow these steps:

1. **Query the database** to get the experiment group data:

```sql
-- Get narrative evaluation prompts
SELECT system_role, base_prompt, dimensions
FROM pain_narratives_app.experiments_groups
WHERE experiments_group_id = <YOUR_GROUP_ID>;

-- Get questionnaire prompts
SELECT questionnaire_type, system_role, instructions
FROM pain_narratives_app.questionnaire_prompts
WHERE experiments_group_id = <YOUR_GROUP_ID>;
```

2. **Edit the YAML file**: Open `src/pain_narratives/config/default_prompts.yaml`

3. **Update the relevant sections**:

```yaml
narrative_evaluation:
  system_role: |
    <paste new system role here>

  base_prompt: |
    <paste new base prompt here>

  dimensions:
    - name: "<dimension name>"
      definition: "<definition with proper quotes>"
      min: 0
      max: 10
      active: true
```

4. **For questionnaires**:

```yaml
questionnaires:
  PCS:
    system_role: |
      <paste new system role>

    instructions: |
      <paste new instructions>
```

5. **Save the file** - Changes take effect immediately (the config is cached, but reloads on app restart)

### Important Notes

- **Quote Handling**: If your text contains quotes, use single quotes `'...'` for the YAML string and double quotes `"..."` inside the text
- **Multiline Text**: Use the pipe `|` symbol for multiline strings
- **Language**: The current defaults use Spanish dimension names per experiment group 12
- **Validation**: Run the test to verify: `uv run python tests/test_yaml_prompts_config.py`

## Architecture

### How It Works

```
default_prompts.yaml
    ↓ (loaded by)
config/prompts.py
    ↓ (provides functions)
Components use: get_system_role(), get_default_dimensions(), etc.
    ↓
prompt_manager.py
questionnaire_prompts.py
analytics.py
```

### Key Functions

From `pain_narratives.config.prompts`:

- `get_system_role()` - Returns the system role string
- `get_base_prompt()` - Returns the base prompt string
- `get_default_dimensions()` - Returns list of dimension dicts
- `get_default_prompt()` - Returns the complete generated prompt
- `get_questionnaire_prompts()` - Returns all questionnaire prompts
- `get_questionnaire_prompt(type)` - Returns specific questionnaire prompt
- `get_prompt_library()` - Returns all prompt templates
- `reload_prompts_config()` - Force reload from YAML (clears cache)

## Migration History

**October 2025**: Migrated from hardcoded prompts to YAML configuration based on experiment group 12

**Changes made**:

- Created `src/pain_narratives/config/default_prompts.yaml`
- Created `src/pain_narratives/config/prompts.py` loader module
- Updated `prompt_manager.py` to use YAML
- Updated `questionnaire_prompts.py` to use YAML
- Updated `analytics.py` to use YAML
- Switched from English to Spanish dimension names (from group 12)
- Removed hardcoded prompt strings from Python files

**Benefits**:

- ✅ Researchers can update prompts without coding
- ✅ All prompts in one central location
- ✅ Easy to version control and track changes
- ✅ Prompts based on validated research (experiment group 12)
- ✅ No need to redeploy when updating prompts

## Testing

To verify your changes work correctly:

```bash
# Run the prompts configuration test
uv run python tests/test_yaml_prompts_config.py

# Run the full test suite
uv run pytest

# Check for import errors
uv run python -c "from pain_narratives.config.prompts import get_default_prompt; print('OK')"
```

## Example: Adding a New Dimension

To add a new evaluation dimension:

1. Edit `default_prompts.yaml`:

```yaml
narrative_evaluation:
  dimensions:
    - name: "Severidad del dolor"
      definition: "..."
      min: 0
      max: 10
      active: true

    - name: "Discapacidad"
      definition: "..."
      min: 0
      max: 10
      active: true

    # NEW DIMENSION
    - name: "Impacto emocional"
      definition: "El grado en que el dolor afecta el estado emocional y mental de la persona"
      min: 0
      max: 10
      active: true
```

2. The new dimension will automatically appear in:

   - The dimension editor UI
   - The generated prompts
   - The JSON response structure

3. Test with: `uv run python tests/test_yaml_prompts_config.py`

## Troubleshooting

### "YAML parse error"

Check for:

- Proper indentation (use spaces, not tabs)
- Matching quotes (use `'text "with" quotes'` or `"text 'with' quotes"`)
- Pipe `|` for multiline text

### "Prompts not updating"

1. Verify the YAML file is saved
2. Restart the Streamlit app
3. Clear cache: call `reload_prompts_config()` in Python
4. Check file location: `src/pain_narratives/config/default_prompts.yaml`

### "Missing dimension in output"

Check that `active: true` is set for the dimension in the YAML file.

## See Also

- Main configuration: `src/pain_narratives/config/settings.py`
- Localization files: `src/pain_narratives/locales/`
- Database schema: `src/pain_narratives/db/models_sqlmodel.py`

## Deprecated: user_prompts table

The `user_prompts` table (model `UserPrompt`) is currently considered deprecated:

- Not used by the Streamlit UI; intended for a future per-user custom prompts feature
- Present in the codebase for backward compatibility with CLI scripts/tests
- Safe to ignore for default prompts configuration (YAML-based system is authoritative)

If removal is desired in the future, plan to:

- Drop the `user_prompts` table via an Alembic migration
- Remove `UserPrompt` from `models_sqlmodel.py`
- Remove related methods from `DatabaseManager` (save/get/set/delete user prompt)
- Update or remove `tests/test_user_prompt_current.py` and CLI references in `scripts/manage_users.py`
