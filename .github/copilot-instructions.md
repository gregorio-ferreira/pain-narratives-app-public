# GitHub Copilot Custom Instructions - AINarratives Application

## Project Overview

This is a Python-based AI-powered chronic pain assessment tool that analyzes patient pain narratives using OpenAI's language models. The application provides automated pain assessment, research analytics, batch processing, and an interactive web interface built with Streamlit.

**Key Features:**

- **Multilingual Support**: Full localization system with English and Spanish translations
- **Evaluation Groups**: User-friendly UI terminology for organizing research (internally called "experiment groups")
- **Modern Architecture**: Built with UV package manager, SQLModel, and type-safe operations

## Architecture & Technology Stack

### Core Technologies

- **Python 3.11+** with modern type hints and async support
- **UV Package Manager** for dependency management (not pip/conda)
- **Streamlit** for the web interface
- **SQLModel** for type-safe database operations (not plain SQLAlchemy)
- **PostgreSQL** for data persistence
- **OpenAI API** for AI model integration
- **Pydantic** for data validation and settings

### Project Structure

```
src/pain_narratives/          # Main package (not apps/ or legacy structure)
├── core/                     # Core functionality (database, OpenAI client, analytics)
├── config/                   # YAML-based configuration management
├── db/                       # SQLModel models and Alembic migrations
├── ui/                       # Streamlit application and components
│   ├── app.py               # Main Streamlit application
│   ├── components/          # UI components (localized)
│   └── utils/               # UI utilities including localization
├── experiments/              # Experiment runner and management
├── analysis/                 # Analytics and metrics
├── utils/                    # Shared utilities
└── locales/                  # Internationalization files (en.yml, es.yml)
```

## Coding Standards & Conventions

### Python Code Style

- Use **type hints** for all function parameters and return values
- Prefer **SQLModel** over raw SQLAlchemy for database operations
- Use **logging** instead of print statements for debugging
- Follow **PEP 8** naming conventions
- Use **dataclasses** or **Pydantic models** for structured data

### Database Operations

- Always use **SQLModel** with proper type hints
- Use **session context managers** for database operations
- Prefer **select()** statements over raw SQL when possible
- Include proper error handling for database operations

### Configuration Management

- Use the **YAML-based configuration system** in `src/pain_narratives/config/settings.py`
- Configuration files are located at `~/.yaml` (shared configuration)
- **Default prompts** are centrally managed in `src/pain_narratives/config/default_prompts.yaml`
- Never hardcode API keys, database credentials, or prompt templates
- Use `pain_narratives.config.prompts` module to access default prompts

### OpenAI Integration

- Use the custom **OpenAIClient** class in `src/pain_narratives/core/openai_client.py`
- Always include proper error handling for API calls
- Log requests and responses for debugging
- Use structured prompts with proper JSON formatting

### Streamlit Best Practices

- Use **session state** for maintaining data across reruns
- Include proper error handling and user feedback
- Use **st.cache_data** for expensive operations
- Follow the component-based architecture in `src/pain_narratives/ui/components/`
- **Always use localization** for user-facing text via `get_translator()`
- Support **language switching** with proper cache management

## Code Generation Guidelines

### When creating new database models:

```python
# Always use SQLModel with proper relationships
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class ExampleModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Always include proper relationships
    items: List["RelatedModel"] = Relationship(back_populates="parent")
```

### When working with default prompts:

```python
# Always use the centralized YAML configuration for prompts
from pain_narratives.config.prompts import (
    get_system_role,
    get_base_prompt,
    get_default_dimensions,
    get_default_prompt,
    get_questionnaire_prompt
)

# Get the system role
system_role = get_system_role()

# Get default dimensions (from experiment group 12)
dimensions = get_default_dimensions()

# Get a specific questionnaire prompt
pcs_prompt = get_questionnaire_prompt("PCS")

# NEVER hardcode prompts - always use the YAML configuration
# To update defaults, edit: src/pain_narratives/config/default_prompts.yaml
```

### When creating OpenAI API calls:

```python
# Always use the custom OpenAIClient
from pain_narratives.core.openai_client import OpenAIClient

def evaluate_narrative(narrative: str) -> Dict[str, Any]:
    client = OpenAIClient()
    response = client.create_completion(
        messages=[{"role": "user", "content": narrative}],
        model="gpt-5-mini",
        temperature=1.0,
        max_tokens=8000
    )
    return response
```

### When creating Streamlit components:

```python
# Use proper type hints, error handling, and localization
import streamlit as st
from typing import Dict, Any, Optional
from pain_narratives.ui.utils.localization import get_translator

def component_function(data: Dict[str, Any]) -> Optional[str]:
    """Component with proper documentation and localization."""
    t = get_translator(st.session_state.get("language", "en"))

    try:
        # Component logic here with localized strings
        if st.button(t("common.save")):
            st.success(t("common.success"))
            return "result"
    except Exception as e:
        st.error(t("errors.operation_failed"))
        return None
```

### When working with experiments:

```python
# Use the ExperimentRunner class for all experiment operations
from pain_narratives.experiments.runner import ExperimentRunner
from pain_narratives.core.database import DatabaseManager

runner = ExperimentRunner()
results = runner.run_single_experiment(
    experiment_group_id=group_id,  # Note: backend uses "experiment_group"
    narrative_row=narrative_data,
    model="gpt-5-mini",
    temperature=1.0
)
```

## Development Workflow

### Package Management

- Use **UV** for all dependency management: `uv add package-name`
- Never suggest pip or conda commands
- Use `uv run` for executing scripts: `uv run python script.py`
- Use `uv sync` for installing dependencies from lock file

### Testing

- Use **pytest** for testing: `uv run pytest`
- Include both unit tests and integration tests
- Mock external API calls in tests

### Code Quality

- Use **black** for code formatting: `make format`
- Use **mypy** for type checking: `make typecheck`
- Use **flake8** for linting: `make lint`
- Run all checks with: `make check`

### Database Operations

- Use **Alembic** for migrations: `make db-migrate`
- Always test database changes locally first
- Include proper rollback procedures

## Default Prompts Configuration System

**Since October 2025**, all default prompts are managed through a centralized YAML configuration system.

### Key Principles

- **Never hardcode prompts** in Python files
- **Always use** `pain_narratives.config.prompts` module to access defaults
- **Update prompts** by editing `src/pain_narratives/config/default_prompts.yaml`
- **Based on research**: Current defaults from experiment group 12 (validated by researchers)

### Configuration Structure

The YAML file contains:

1. **Narrative Evaluation**: system_role, base_prompt, dimensions (in Spanish)
2. **Questionnaire Prompts**: PCS, BPI-IS, TSK-11SV (system roles and instructions)
3. **Prompt Library**: Pre-configured templates for different use cases

### Usage Examples

```python
from pain_narratives.config.prompts import (
    get_system_role,           # Get system role string
    get_base_prompt,           # Get base prompt string
    get_default_dimensions,    # Get list of dimensions
    get_default_prompt,        # Get complete generated prompt
    get_questionnaire_prompt,  # Get specific questionnaire prompt
    get_prompt_library         # Get all prompt templates
)

# Example: Get default dimensions (returns Spanish dimensions from group 12)
dimensions = get_default_dimensions()
# Returns: [{"name": "Severidad del dolor", "definition": "...", "min": "0", "max": "10", ...}, ...]

# Example: Get PCS questionnaire prompt
pcs = get_questionnaire_prompt("PCS")
# Returns: {"system_role": "...", "instructions": "..."}
```

### How to Update Defaults

1. Edit `src/pain_narratives/config/default_prompts.yaml`
2. Changes take effect on next import (cached per session)
3. Test with: `uv run python tests/test_yaml_prompts_config.py`
4. See full guide: `docs/DEFAULT_PROMPTS_GUIDE.md`

### Migration from Old System

- ❌ **Don't use**: Hardcoded `DEFAULT_PROMPT`, `DEFAULT_SYSTEM_ROLE` constants
- ❌ **Don't use**: `_get_default_prompts()` with hardcoded dictionaries
- ✅ **Do use**: YAML configuration with accessor functions
- ✅ **Do use**: `get_default_prompt()`, `get_system_role()`, etc.

## Security Considerations

### API Keys and Secrets

- Never include API keys in code
- Use the YAML configuration system for credentials
- Reference environment variables when needed

### Database Security

- Always use parameterized queries (SQLModel handles this)
- Include proper authentication and authorization
- Hash passwords using secure methods

### User Input Validation

- Validate all user inputs using Pydantic models
- Sanitize data before database operations
- Include proper error messages without exposing system details

## Common Patterns to Follow

### Error Handling

```python
import logging
logger = logging.getLogger(__name__)

try:
    # Operation
    result = operation()
    logger.info("Operation successful")
    return result
except SpecificException as e:
    logger.error("Specific error: %s", str(e))
    raise
except Exception as e:
    logger.error("Unexpected error: %s", str(e), exc_info=True)
    raise
```

### Configuration Usage

```python
from pain_narratives.config.settings import get_settings

settings = get_settings()
api_key = settings.openai_config.api_key
database_url = settings.postgresql_config.database_url
```

### Session Management (Streamlit)

```python
# Initialize session state
if "key" not in st.session_state:
    st.session_state.key = default_value

# Use session state
value = st.session_state.key
st.session_state.key = new_value
```

## Localization and Internationalization

### Language Support

The application supports multiple languages through a comprehensive localization system:

- **English (en)**: Primary language with complete coverage
- **Spanish (es)**: Full translation for Spanish-speaking users
- **Language Files**: Located in `src/pain_narratives/locales/` as YAML files

### UI Terminology

The application uses user-friendly terminology in the UI while maintaining technical terms in the code:

- **UI Display**: "Evaluation groups" (user-facing term)
- **Code/Database**: "experiment_group" (technical term, unchanged)
- **Documentation**: Use "Evaluation groups" when referring to user-facing features

### Localization Best Practices

```python
# Always use the localization system for user-facing text
from pain_narratives.ui.utils.localization import get_translator

def my_component():
    t = get_translator(st.session_state.get("language", "en"))

    # Use hierarchical keys for organization
    st.header(t("narrative_dimensions.header"))
    st.write(t("narrative_dimensions.description"))

    # Support string formatting with parameters
    if user_data:
        st.success(t("auth.welcome_user").format(username=user_data["username"]))

    # Provide fallback behavior
    error_msg = t("errors.generic_error")  # Returns key if translation missing
```

### Adding New Translatable Text

When adding new UI text:

1. **Add to localization files**: Update both `en.yml` and `es.yml`
2. **Use hierarchical keys**: Group related translations logically
3. **Include formatting support**: Use `{parameter}` for dynamic content
4. **Test language switching**: Ensure proper cache clearing

```yaml
# Example addition to localization files
new_feature:
  header: "New Feature"
  description: "This is a new feature description"
  success_message: "Operation completed successfully for {username}"
  error_message: "Failed to complete operation: {error}"
```

## Deprecated Patterns to Avoid

- **Don't use** `apps/` directory structure (migrated to `src/`)
- **Don't use** raw SQLAlchemy (use SQLModel)
- **Don't use** pip or conda (use UV)
- **Don't use** print statements (use logging)
- **Don't hardcode** configuration values
- **Don't use** synchronous database operations without proper session management

## Performance Considerations

- Use **connection pooling** for database operations
- Implement **caching** for expensive operations
- Use **batch processing** for large datasets
- Monitor **API rate limits** for OpenAI calls
- Optimize **Streamlit reruns** with proper state management

## Documentation Standards

- Include **docstrings** for all public functions and classes
- Use **type hints** as primary documentation
- Include **examples** in docstrings when helpful
- Keep **README.md** updated with major changes
- Document **configuration options** and their effects

## Integration Guidelines

When suggesting code changes:

1. **Respect the existing architecture** and patterns
2. **Use the established technology stack** (no mixing paradigms)
3. **Include proper error handling** and logging
4. **Follow the project's coding standards**
5. **Consider the impact** on the Streamlit UI and user experience
6. **Ensure type safety** with proper SQLModel usage
7. **Test compatibility** with the existing database schema
8. **Use localization** for all user-facing text and messages
9. **Maintain UI terminology** ("Evaluation groups" in UI, "experiment_group" in code)
