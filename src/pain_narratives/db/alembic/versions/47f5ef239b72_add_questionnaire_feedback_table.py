"""add_questionnaire_feedback_table

Revision ID: 47f5ef239b72
Revises: 260d578db51b
Create Date: 2025-09-30 09:35:39.488934

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '47f5ef239b72'
down_revision: Union[str, None] = '260d578db51b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # This migration was for renaming columns in an existing table.
    # For fresh installs, the previous migration already created the table 
    # with the correct column names, so this is a no-op.
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # No-op for fresh installs
    pass
