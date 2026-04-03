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
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'user'
          AND column_name = 'photo_url'
      ) THEN
        ALTER TABLE "user" ADD COLUMN photo_url TEXT;
      END IF;
    END
    $$;
    """)


def downgrade():
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS photo_url;')