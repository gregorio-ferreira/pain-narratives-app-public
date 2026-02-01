"""Drop legacy seve/disca columns from narratives

Revision ID: 1a2b3c4d5e6f
Revises: f000f471d152
Create Date: 2025-10-09 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "f000f471d152"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop unused legacy columns from narratives."""
    schema = "pain_narratives_app"
    table = "narratives"

    # Columns are never populated (0 non-null across 66 records); replaced by evaluation_results
    for col in ("seve_rube", "seve_pat", "disca_rube", "disca_pat"):
        with op.batch_alter_table(table, schema=schema) as batch_op:
            batch_op.drop_column(col)


def downgrade() -> None:
    """Downgrade schema: restore previously dropped columns."""
    schema = "pain_narratives_app"
    table = "narratives"

    # Recreate columns as nullable integers as per original schema
    for col in ("seve_rube", "seve_pat", "disca_rube", "disca_pat"):
        with op.batch_alter_table(table, schema=schema) as batch_op:
            batch_op.add_column(sa.Column(col, sa.Integer(), nullable=True))
