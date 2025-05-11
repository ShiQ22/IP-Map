"""lowercase device_type and owner_type enums

Revision ID: 47361bc74832
Revises: f6adcb79bb11
Create Date: 2025-05-09 09:11:51.901729

"""
"""lowercase device_type and owner_type enums

Revision ID: abcd1234
Revises: 2255520df70a
Create Date: 2025-05-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# these values come from your generated filename and your previous head
revision = "abcd1234"
down_revision = "2255520df70a"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1) Drop the old ENUMs by converting to VARCHAR
    op.alter_column(
        "ips", "device_type",
        existing_type=sa.Enum(name="devicetype"),
        type_=sa.VARCHAR(10),
        nullable=False,
    )
    op.alter_column(
        "ips", "owner_type",
        existing_type=sa.Enum(name="ownertype"),
        type_=sa.VARCHAR(10),
        nullable=False,
    )

    # 2) Normalize all current rows to lowercase
    op.execute("UPDATE ips SET device_type = LOWER(device_type)")
    op.execute("UPDATE ips SET owner_type  = LOWER(owner_type)")

    # 3) Re-apply the ENUM definitions with lowercase members
    op.alter_column(
        "ips", "device_type",
        existing_type=sa.VARCHAR(10),
        type_=sa.Enum("pc","laptop","mobile","tablet","other", name="devicetype"),
        nullable=False,
    )
    op.alter_column(
        "ips", "owner_type",
        existing_type=sa.VARCHAR(10),
        type_=sa.Enum("user","device","server", name="ownertype"),
        nullable=False,
    )


def downgrade() -> None:
    # Reverse: drop back to simple VARCHAR
    op.alter_column(
        "ips", "device_type",
        existing_type=sa.Enum("pc","laptop","mobile","tablet","other", name="devicetype"),
        type_=sa.VARCHAR(10),
        nullable=False,
    )
    op.alter_column(
        "ips", "owner_type",
        existing_type=sa.Enum("user","device","server", name="ownertype"),
        type_=sa.VARCHAR(10),
        nullable=False,
    )
    # (we leave the lowercase text values in place on downgrade)
