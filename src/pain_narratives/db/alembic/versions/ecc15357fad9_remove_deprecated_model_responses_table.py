"""Remove deprecated model_responses table

Revision ID: ecc15357fad9
Revises: da3b50e81a44
Create Date: 2025-09-27 08:10:14.956746

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ecc15357fad9"
down_revision: Union[str, None] = "da3b50e81a44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the deprecated model_responses table
    # This table was not being used in the application code
    op.drop_table("model_responses", schema="pain_narratives_app")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the model_responses table if needed to rollback
    # This recreation is based on the original schema
    op.create_table(
        "model_responses",
        sa.Column("narrative_id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("response_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["experiment_id"], ["pain_narratives_app.experiment_lists.id"]),
        sa.ForeignKeyConstraint(["narrative_id"], ["pain_narratives_app.narratives.id"]),
        sa.PrimaryKeyConstraint("narrative_id", "experiment_id"),
        schema="pain_narratives_app",
    )
