"""Remove device_sn from ocr_records table

Revision ID: c1f2d3e4f5g6
Revises: b9cc15fb145d
Create Date: 2025-08-01 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1f2d3e4f5g6'
down_revision = 'b9cc15fb145d'
branch_labels = None
depends_on = None


def upgrade():
    # Remove device_sn column from ocr_records table
    op.drop_index('ix_ocr_records_device_sn', table_name='ocr_records')
    op.drop_column('ocr_records', 'device_sn')


def downgrade():
    # Add device_sn column back
    op.add_column('ocr_records', sa.Column('device_sn', sa.VARCHAR(length=255), nullable=False))
    op.create_index('ix_ocr_records_device_sn', 'ocr_records', ['device_sn'], unique=False)