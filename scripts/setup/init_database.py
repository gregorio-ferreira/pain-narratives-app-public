#!/usr/bin/env python3
"""
Database initialization script for AINarratives application.

This script initializes the database schema using Alembic migrations.
For security reasons, user creation is handled separately through the user management scripts.

Usage:
    python scripts/setup/init_database.py

After running this script:
1. Use scripts/register_user.py to create your first admin user
2. Use the web UI to create experiment groups
"""

import sys

from sqlmodel import SQLModel, create_engine

from pain_narratives.config.settings import get_settings

# Import all models to register them with SQLModel metadata
from pain_narratives.db.models_sqlmodel import (  # noqa: F401
    AssessmentFeedback,
    EvaluationResult,
    ExperimentGroup,
    ExperimentGroupUser,
    ExperimentList,
    Narrative,
    Questionnaire,
    QuestionnaireFeedback,
    QuestionnairePrompt,
    RequestResponse,
    User,
    UserPrompt,
)


def init_database_schema() -> None:
    """Initialize the database schema by creating all tables."""
    print("🏥 Initializing AINarratives Database Schema")
    print("=" * 50)

    try:
        # Get database settings
        settings = get_settings()
        print(f"📊 Connecting to database: {settings.database_url.split('@')[-1]}")  # Hide credentials

        # Create engine
        engine = create_engine(settings.database_url)

        # Create all tables from SQLModel metadata
        print("📋 Creating database tables...")
        SQLModel.metadata.create_all(engine)
        print("✅ Database tables created successfully!")

        print("\n" + "=" * 50)
        print("🎉 Database initialization completed!")
        print("\n📝 Next Steps:")
        print("1. Create your first admin user:")
        print("   uv run python scripts/register_user.py")
        print("2. Start the application:")
        print("   uv run streamlit run scripts/run_app.py")
        print("3. Create experiment groups through the web UI")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("\n🔍 Troubleshooting:")
        print("- Ensure PostgreSQL is running")
        print("- Check database connection settings in config.yaml")
        print("- Verify database credentials and permissions")
        sys.exit(1)


def main():
    """Main initialization function."""
    init_database_schema()


if __name__ == "__main__":
    main()
