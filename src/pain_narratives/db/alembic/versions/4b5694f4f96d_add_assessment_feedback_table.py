"""Add assessment feedback table

Revision ID: 4b5694f4f96d
Revises: ecc15357fad9
Create Date: 2025-10-12 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b5694f4f96d"
down_revision: Union[str, None] = "ecc15357fad9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "assessment_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("experiments_group_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("narrative_id", sa.Integer(), nullable=True),
        sa.Column("intensity_score_alignment", sa.String(length=64), nullable=False),
        sa.Column("intensity_explanation_alignment", sa.String(length=64), nullable=False),
        sa.Column("intensity_usage_intent", sa.String(length=64), nullable=False),
        sa.Column("disability_score_alignment", sa.String(length=64), nullable=False),
        sa.Column("disability_explanation_alignment", sa.String(length=64), nullable=False),
        sa.Column("disability_usage_intent", sa.String(length=64), nullable=False),
        sa.Column("dimension_feedback", sa.JSON(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint([
            "experiment_id",
        ], ["pain_narratives_app.experiments_list.experiment_id"]),
        sa.ForeignKeyConstraint([
            "experiments_group_id",
        ], ["pain_narratives_app.experiments_groups.experiments_group_id"]),
        sa.ForeignKeyConstraint([
            "user_id",
        ], ["pain_narratives_app.users.id"]),
        sa.ForeignKeyConstraint([
            "narrative_id",
        ], ["pain_narratives_app.narratives.narrative_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", name="uq_assessment_feedback_experiment"),
        schema="pain_narratives_app",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("assessment_feedback", schema="pain_narratives_app")
