"""add_user_photo_url

Revision ID: add_user_photo_url
Revises: 
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1771231664_add_user_photo_url'
down_revision = '18d312554f1c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('photo_url', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('user', 'photo_url')
