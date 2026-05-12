"""Add prompt_version and reasoning_tokens to experiments_list.

Revision ID: 2026051100rev
Revises: 0000000dedup
Create Date: 2026-05-11

Two additive nullable columns on `experiments_list` to support the revision
experiments (DeepSeek-R1, Claude Sonnet 4.5 with extended thinking):

- prompt_version: which prompts the experiment used ("original" for the
  published GPT-5 baseline, "simplified_v1" for the revision runs).
- reasoning_tokens: count of tokens produced as chain-of-thought / extended
  thinking, separate from the visible-answer output token count. Lets us
  reconstruct per-cell cost from the database without re-querying the API.

Purely additive, both columns nullable, fully reversible.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026051100rev"
down_revision: Union[str, None] = "0000000dedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCHEMA = "pain_narratives_app"


def upgrade() -> None:
    """Add prompt_version and reasoning_tokens columns."""
    op.add_column(
        "experiments_list",
        sa.Column("prompt_version", sa.String(64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "experiments_list",
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Remove the columns."""
    op.drop_column("experiments_list", "reasoning_tokens", schema=SCHEMA)
    op.drop_column("experiments_list", "prompt_version", schema=SCHEMA)
