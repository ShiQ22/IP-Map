"""add updated_by to devices

Revision ID: ee9ef544852a
Revises: 5bedad609c4b
Create Date: 2025-05-10 08:34:32.535115
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ee9ef544852a"
down_revision: Union[str, None] = "5bedad609c4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add devices.updated_by (FK → admins.id)."""
    with op.batch_alter_table("devices") as batch:
        batch.add_column(sa.Column("updated_by", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_devices_updated_by_admins",
            "admins",
            ["updated_by"],
            ["id"],
        )


def downgrade() -> None:
    """Remove devices.updated_by."""
    with op.batch_alter_table("devices") as batch:
        batch.drop_constraint("fk_devices_updated_by_admins", type_="foreignkey")
        batch.drop_column("updated_by")
