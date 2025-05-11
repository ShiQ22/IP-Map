"""department not null + default '' on ips

Revision ID: 89077151746e
Revises: c16e5f45a9a9
Create Date: 2025-05-10 06:23:54.469679
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "89077151746e"
down_revision: Union[str, None] = "c16e5f45a9a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --------------------------------------------------------------------------- #
# UPGRADE – make department NOT NULL and give it a default ''                 #
# --------------------------------------------------------------------------- #
def upgrade() -> None:
    # 1) replace any existing NULLs with an empty string
    op.execute("UPDATE ips SET department = '' WHERE department IS NULL")

    # 2) alter the column to NOT NULL with server-side default ''
    op.alter_column(
        "ips",
        "department",
        existing_type=sa.String(length=100),
        nullable=False,
        server_default=sa.text("''"),
    )


# --------------------------------------------------------------------------- #
# DOWNGRADE – revert to nullable and drop the default                         #
# --------------------------------------------------------------------------- #
def downgrade() -> None:
    op.alter_column(
        "ips",
        "department",
        existing_type=sa.String(length=100),
        nullable=True,
        server_default=None,
    )
