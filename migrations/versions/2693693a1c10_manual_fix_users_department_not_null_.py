"""manual fix: users.department not null + default ''

Revision ID: 2693693a1c10
Revises: 89077151746e
Create Date: 2025-05-10 06:35:48.967403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2693693a1c10'
down_revision: Union[str, None] = '89077151746e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
