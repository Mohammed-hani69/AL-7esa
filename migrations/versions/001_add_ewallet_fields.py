"""Add ewallet number fields to User model

Revision ID: 001_add_ewallet_fields
Revises: f8b0eb7037a8
Create Date: 2025-07-17 22:52:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_add_ewallet_fields'
down_revision = 'f8b0eb7037a8'
branch_labels = None
depends_on = None

def upgrade():
    """Add ewallet number fields to the user table."""
    # Add ewallet_number_1 column
    op.add_column('user', sa.Column('ewallet_number_1', sa.String(length=50), nullable=True))
    
    # Add ewallet_number_2 column  
    op.add_column('user', sa.Column('ewallet_number_2', sa.String(length=50), nullable=True))

def downgrade():
    """Remove ewallet number fields from the user table."""
    # Remove ewallet_number_2 column
    op.drop_column('user', 'ewallet_number_2')
    
    # Remove ewallet_number_1 column
    op.drop_column('user', 'ewallet_number_1')
