"""merge_heads_bad99e_4b5694f

Revision ID: 8d3b2c1f2a00
Revises: bad99e59d04b, 4b5694f4f96d
Create Date: 2025-09-29 00:00:00.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "8d3b2c1f2a00"
down_revision: Union[str, tuple[str, ...], None] = ("bad99e59d04b", "4b5694f4f96d")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads - no-op upgrade."""
    pass


def downgrade() -> None:
    """No-op downgrade for merge."""
    pass
