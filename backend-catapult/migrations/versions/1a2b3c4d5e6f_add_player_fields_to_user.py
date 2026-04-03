"""add_player_fields_to_user

Revision ID: 1a2b3c4d5e6f
Revises: 6bfec02ad189
Create Date: 2026-01-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "6bfec02ad189"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable columns to `user` only if they don't exist
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'player_name'
      ) THEN
        ALTER TABLE "user" ADD COLUMN player_name TEXT;
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'age'
      ) THEN
        ALTER TABLE "user" ADD COLUMN age INTEGER;
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'team_id'
      ) THEN
        ALTER TABLE "user" ADD COLUMN team_id INTEGER;
      END IF;
    END
    $$;
    """)

    # Create index if not exists
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'ix_user_player_name' AND n.nspname = 'public'
      ) THEN
        CREATE INDEX ix_user_player_name ON "user" (player_name);
      END IF;
    END
    $$;
    """)

    # Create FK if not exists
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_team'
      ) THEN
        ALTER TABLE "user"
        ADD CONSTRAINT fk_user_team FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE;
      END IF;
    END
    $$;
    """)


def downgrade() -> None:
    # Drop FK if exists
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_user_team') THEN
        ALTER TABLE "user" DROP CONSTRAINT fk_user_team;
      END IF;
    END
    $$;
    """)

    # Drop index if exists
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'ix_user_player_name' AND n.nspname = 'public'
      ) THEN
        DROP INDEX ix_user_player_name;
      END IF;
    END
    $$;
    """)

    # Drop columns if they exist
    op.execute("""
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'team_id'
      ) THEN
        ALTER TABLE "user" DROP COLUMN team_id;
      END IF;
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'age'
      ) THEN
        ALTER TABLE "user" DROP COLUMN age;
      END IF;
      IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user' AND column_name = 'player_name'
      ) THEN
        ALTER TABLE "user" DROP COLUMN player_name;
      END IF;
    END
    $$;
    """)
    