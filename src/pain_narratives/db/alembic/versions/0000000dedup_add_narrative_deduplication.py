"""Add narrative deduplication fields

Revision ID: 0000000dedup
Revises: 1a2b3c4d5e6f
Create Date: 2025-10-15 00:00:00.000000

This migration adds columns for narrative deduplication:
- narrative_hash: SHA256 hash of the narrative text for quick duplicate detection
- word_count: Number of words in the narrative
- char_count: Number of characters in the narrative
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0000000dedup"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add narrative deduplication columns."""
    schema = "pain_narratives_app"

    # Add deduplication columns to narratives table
    op.add_column(
        "narratives",
        sa.Column("narrative_hash", sa.String(64), nullable=True),
        schema=schema,
    )
    op.add_column(
        "narratives",
        sa.Column("word_count", sa.Integer(), nullable=True),
        schema=schema,
    )
    op.add_column(
        "narratives",
        sa.Column("char_count", sa.Integer(), nullable=True),
        schema=schema,
    )

    # Create index on narrative_hash for efficient duplicate lookup
    op.create_index(
        "ix_narratives_narrative_hash",
        "narratives",
        ["narrative_hash"],
        schema=schema,
    )


def downgrade() -> None:
    """Remove narrative deduplication columns."""
    schema = "pain_narratives_app"

    # Drop index first
    op.drop_index("ix_narratives_narrative_hash", table_name="narratives", schema=schema)

    # Drop columns
    op.drop_column("narratives", "char_count", schema=schema)
    op.drop_column("narratives", "word_count", schema=schema)
    op.drop_column("narratives", "narrative_hash", schema=schema)
