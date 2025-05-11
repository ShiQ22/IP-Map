"""Add department, device_type, updated_by to ips

Revision ID: 1234567890ab
Revises: <previous_revision_id>
Create Date: 2025-05-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = '905818f12073'
branch_labels = None
depends_on = None


# Define the DeviceType enum here so Alembic can create it
device_type_enum = sa.Enum(
    'PC', 'Laptop', 'Mobile', 'Tablet', 'Other',
    name='devicetype'
)

def upgrade():
    # 1) Create the new enum type in the database
    device_type_enum.create(op.get_bind(), checkfirst=True)

    # 2) Add the new columns with safe defaults
    op.add_column('ips',
        sa.Column('department', sa.String(length=100), nullable=False, server_default='')
    )
    op.add_column('ips',
        sa.Column('device_type', device_type_enum, nullable=False, server_default='Other')
    )
    op.add_column('ips',
        sa.Column('updated_by', sa.Integer(), nullable=True)
    )

    # 3) Add foreign key constraint for updated_by → admins.id
    op.create_foreign_key(
        'fk_ips_updated_by_admins',
        'ips', 'admins',
        ['updated_by'], ['id'],
        ondelete='SET NULL'
    )

    # 4) Remove the server defaults now that existing rows are populated
    op.alter_column('ips', 'department', server_default=None)
    op.alter_column('ips', 'device_type', server_default=None)


def downgrade():
    # Reverse: drop FK, drop columns, drop the enum
    op.drop_constraint('fk_ips_updated_by_admins', 'ips', type_='foreignkey')
    op.drop_column('ips', 'updated_by')
    op.drop_column('ips', 'device_type')
    op.drop_column('ips', 'department')
    device_type_enum.drop(op.get_bind(), checkfirst=True)
