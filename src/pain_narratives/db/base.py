"""
Base declarative class for SQLAlchemy models.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

SCHEMA_NAME = "pain_narratives_app"

Base = declarative_base(metadata=MetaData(schema=SCHEMA_NAME))
