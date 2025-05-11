"""normalize device_type and add lowercase check

Revision ID: f6adcb79bb11
Revises: 2255520df70a
Create Date: 2025-05-09 08:59:23.205505
"""
from alembic import op
from sqlalchemy.exc import ProgrammingError

# revision identifiers, used by Alembic.
revision = 'f6adcb79bb11'
down_revision = '2255520df70a'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # drop existing constraint if present
    try:
        op.drop_constraint("chk_device_type_lower", "ips", type_="check")
    except ProgrammingError:
        pass

    # add the new check constraint
    op.create_check_constraint(
        "chk_device_type_lower",
        "ips",
        "device_type IN ('pc','laptop','mobile','tablet','other')"
    )

def downgrade() -> None:
    op.drop_constraint("chk_device_type_lower", "ips", type_="check")
