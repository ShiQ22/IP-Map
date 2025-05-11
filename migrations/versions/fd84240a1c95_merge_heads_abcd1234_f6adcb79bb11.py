"""merge heads abcd1234 & f6adcb79bb11

Revision ID: fd84240a1c95
Revises: f6adcb79bb11
Create Date: 2025-05-09 09:15:03.483385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd84240a1c95'
down_revision: Union[str, None] = 'f6adcb79bb11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
