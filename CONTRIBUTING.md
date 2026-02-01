# Contributing to Pain Narratives

Thank you for your interest in contributing to the Pain Narratives research platform! This document provides guidelines for contributing to this project.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [UV package manager](https://docs.astral.sh/uv/)
- Docker and Docker Compose (for local database)
- PostgreSQL (if not using Docker)
- OpenAI API key

### Development Setup

1. **Fork and clone the repository**:

   ```bash
   git clone https://github.com/YOUR_USERNAME/pain-narratives-app.git
   cd pain-narratives-app
   ```

2. **Install development dependencies**:

   ```bash
   uv sync --group dev
   ```

3. **Set up the database** (using Docker):

   ```bash
   docker compose up -d postgres
   ```

4. **Configure the application**:

   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your settings
   ```

5. **Run migrations**:

   ```bash
   cd src/pain_narratives/db && uv run alembic upgrade head && cd ../../..
   ```

6. **Create a test user**:
   ```bash
   uv run python scripts/register_user.py
   ```

## Code Standards

### Python Style Guide

We follow [PEP 8](https://peps.python.org/pep-0008/) with the following tools:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run all checks with:

```bash
make check
```

Or individually:

```bash
make format   # Format code with black and isort
make lint     # Run flake8
make typecheck  # Run mypy
```

### Type Hints

All functions should include type hints:

```python
def evaluate_narrative(narrative: str, model: str = "gpt-5-mini") -> Dict[str, Any]:
    """Evaluate a pain narrative using AI.

    Args:
        narrative: The pain narrative text to evaluate
        model: The OpenAI model to use

    Returns:
        Dictionary containing evaluation results
    """
    ...
```

### Database Operations

Use SQLModel for all database operations:

```python
from sqlmodel import select
from pain_narratives.db.models_sqlmodel import User

with db_manager.get_session() as session:
    user = session.exec(select(User).where(User.username == username)).first()
```

### Localization

All user-facing text must use the localization system:

```python
from pain_narratives.ui.utils.localization import get_translator

t = get_translator(language)
st.header(t("my_section.header"))
```

Add translations to both `src/pain_narratives/locales/en.yml` and `es.yml`.

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
uv run pytest tests/test_specific.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Use pytest fixtures from `conftest.py`
- Mock external API calls (OpenAI)
- Test both success and error cases

Example test:

```python
def test_create_user(db_manager):
    user = db_manager.create_user(
        username="test_user",
        password="test_pass",
        is_admin=False
    )
    assert user.username == "test_user"
    assert user.is_admin is False
```

## Submitting Changes

### Pull Request Process

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and ensure tests pass:

   ```bash
   make check
   make test
   ```

3. **Commit with clear messages**:

   ```bash
   git commit -m "feat: Add narrative deduplication feature"
   ```

4. **Push and create a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Build/config changes

## Reporting Issues

### Bug Reports

Please include:

- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

### Feature Requests

Please include:

- Clear description of the feature
- Use case / motivation
- Proposed implementation (optional)

## Questions?

If you have questions, please:

1. Check existing issues and documentation
2. Open a new issue with the "question" label

Thank you for contributing! 🙏
