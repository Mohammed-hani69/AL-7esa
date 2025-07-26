"""Add google_id to User model and attendance features

Revision ID: google_id_attendance_2025
Revises: 8d3ad43a342b
Create Date: 2025-01-26 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'google_id_attendance_2025'
down_revision = '8d3ad43a342b'
branch_labels = None
depends_on = None


def upgrade():
    """Add google_id column to user table"""
    # Add google_id column to user table
    op.add_column('user', sa.Column('google_id', sa.String(100), nullable=True))
    
    # Add unique constraint for google_id
    op.create_unique_constraint('uq_user_google_id', 'user', ['google_id'])
    
    # Create index for better performance
    op.create_index('idx_user_google_id', 'user', ['google_id'])


def downgrade():
    """Remove google_id column from user table"""
    # Drop index
    op.drop_index('idx_user_google_id', 'user')
    
    # Drop unique constraint
    op.drop_constraint('uq_user_google_id', 'user', type_='unique')
    
    # Drop column
    op.drop_column('user', 'google_id')
