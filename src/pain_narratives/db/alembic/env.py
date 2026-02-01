from logging.config import fileConfig

from alembic import context
from sqlalchemy import text
from sqlmodel import SQLModel

from pain_narratives.config.settings import get_settings
from pain_narratives.db.base import SCHEMA_NAME
from pain_narratives.db.models_sqlmodel import (  # noqa: F401
    AssessmentFeedback,
    EvaluationResult,
    ExperimentGroup,
    ExperimentGroupUser,
    ExperimentList,
    Narrative,
    Questionnaire,
    QuestionnairePrompt,
    RequestResponse,
    User,
    UserPrompt,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config  # type: ignore[attr-defined]


# function to include only the target schema
def include_name(name, type_, _):
    """
    Include only the target schema in migrations.
    This function is used to filter the names of objects
    that should be included in the migration scripts.
    """
    if type_ == "schema":
        return name == SCHEMA_NAME
    return True


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name:
    fileConfig(config.config_file_name)
else:
    print("Some informative message")

# Override sqlalchemy.url from application settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set metadata for 'autogenerate' support
# Use SQLModel metadata for Alembic migrations
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(  # type: ignore[attr-defined]
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():  # type: ignore[attr-defined]
        context.run_migrations()  # type: ignore[attr-defined]


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy import engine_from_config, pool

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(  # type: ignore[attr-defined]
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            version_table_schema=SCHEMA_NAME,
            include_schemas=True,
        )

        with context.begin_transaction():  # type: ignore[attr-defined]
            # ensure schema exists before running migrations
            connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};"))
            context.run_migrations()  # type: ignore[attr-defined]


if context.is_offline_mode():  # type: ignore[attr-defined]
    run_migrations_offline()
else:
    run_migrations_online()
