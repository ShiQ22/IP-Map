"""devices: non-null defaults

Revision ID: 5bedad609c4b
Revises: db36a112ed8e
Create Date: 2025-05-10 08:15:59.644425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bedad609c4b'
down_revision: Union[str, None] = 'db36a112ed8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
