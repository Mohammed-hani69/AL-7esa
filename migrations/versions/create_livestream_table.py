"""Create LiveStream table

Revision ID: livestream_001
Revises: 
Create Date: 2025-07-09

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'livestream_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create live_stream table
    op.create_table('live_stream',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('classroom_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('stream_url', sa.String(length=500), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('auto_end_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['classroom_id'], ['classroom.id'], ),
        sa.ForeignKeyConstraint(['teacher_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('live_stream')
