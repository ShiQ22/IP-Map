"""merge heads + add department to users + wifi to device_type"""

# revision identifiers, used by Alembic.
revision = "c16e5f45a9a9"
down_revision = ("abcd1234", "fd84240a1c95")
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Add 'department' to users
    op.add_column(
        "users",
        sa.Column("department", sa.String(length=100), nullable=False, server_default="")
    )
    # Clear the default so future inserts must specify department
    op.alter_column("users", "department", server_default=None)

    # 2. Extend ips.device_type enum to include 'wifi'
    op.execute(
        "ALTER TABLE ips "
        "MODIFY device_type ENUM('pc','laptop','mobile','tablet','wifi','other') "
        "NOT NULL DEFAULT 'other'"
    )

def downgrade():
    # 1. Revert ips.device_type enum
    op.execute(
        "ALTER TABLE ips "
        "MODIFY device_type ENUM('pc','laptop','mobile','tablet','other') "
        "NOT NULL DEFAULT 'other'"
    )
    # 2. Drop 'department' from users
    op.drop_column("users", "department")
