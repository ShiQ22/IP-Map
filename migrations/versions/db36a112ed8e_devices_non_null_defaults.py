"""devices: non-null defaults

Revision ID: db36a112ed8e
Revises: 2693693a1c10
Create Date: 2025-05-10 08:13:19.953348
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'db36a112ed8e'
down_revision: Union[str, None] = '2693693a1c10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make account_name / location / hostname non-null and unique hostname."""
    with op.batch_alter_table("devices") as t:
        t.alter_column(
            "account_name",
            existing_type=sa.String(length=100),
            nullable=False,
            server_default=""
        )
        t.alter_column(
            "location",
            existing_type=sa.String(length=100),
            nullable=False,
            server_default=""
        )
        t.alter_column(
            "hostname",
            existing_type=sa.String(length=100),
            nullable=False,
            server_default=""
        )
        t.create_unique_constraint("uq_devices_hostname", ["hostname"])


def downgrade() -> None:
    """Revert the non-nulls / default and drop the unique constraint."""
    with op.batch_alter_table("devices") as t:
        t.drop_constraint("uq_devices_hostname", type_="unique")
        t.alter_column(
            "hostname",
            existing_type=sa.String(length=100),
            nullable=True,
            server_default=None
        )
        t.alter_column(
            "location",
            existing_type=sa.String(length=100),
            nullable=True,
            server_default=None
        )
        t.alter_column(
            "account_name",
            existing_type=sa.String(length=100),
            nullable=True,
            server_default=None
        )
