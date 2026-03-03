"""Add user profile fields

Revision ID: tmp_add_user_fields_1771506972
Revises: 1771231664_add_user_photo_url
Create Date: 2026-02-19 13:16:13.257939

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'tmp_add_user_fields_1771506972'
down_revision: Union[str, Sequence[str], None] = '1771231664_add_user_photo_url'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Add profile fields only if missing
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'date_of_birth'
      ) THEN
        ALTER TABLE "user" ADD COLUMN date_of_birth TIMESTAMP;
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'adress'
      ) THEN
        ALTER TABLE "user" ADD COLUMN adress VARCHAR(255);
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'height'
      ) THEN
        ALTER TABLE "user" ADD COLUMN height FLOAT;
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'weight'
      ) THEN
        ALTER TABLE "user" ADD COLUMN weight FLOAT;
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'strong_foot'
      ) THEN
        ALTER TABLE "user" ADD COLUMN strong_foot VARCHAR(10);
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'phone_number'
      ) THEN
        ALTER TABLE "user" ADD COLUMN phone_number VARCHAR(20);
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'emergency_contact'
      ) THEN
        ALTER TABLE "user" ADD COLUMN emergency_contact VARCHAR(255);
      END IF;
    END
    $$;
    """)

    # photo_url type change (keep it, but guard it so it doesn't fail if column missing)
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'photo_url'
      ) THEN
        ALTER TABLE "user" ALTER COLUMN photo_url TYPE VARCHAR(1024);
      END IF;
    END
    $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""

    # Revert photo_url type only if column exists
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'photo_url'
      ) THEN
        ALTER TABLE "user" ALTER COLUMN photo_url TYPE TEXT;
      END IF;
    END
    $$;
    """)

    # Drop columns only if they exist
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS emergency_contact;')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS phone_number;')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS strong_foot;')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS weight;')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS height;')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS adress;')
    op.execute('ALTER TABLE "user" DROP COLUMN IF EXISTS date_of_birth;')
