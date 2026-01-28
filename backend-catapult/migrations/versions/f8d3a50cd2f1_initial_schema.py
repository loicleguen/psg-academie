"""Initial schema

Revision ID: f8d3a50cd2f1
Revises: 
Create Date: 2026-01-11 11:18:02.038022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8d3a50cd2f1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely: create FK constraints only if absent."""
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'academy_country_id_fkey'
      ) THEN
        ALTER TABLE academy ADD CONSTRAINT academy_country_id_fkey FOREIGN KEY (country_id) REFERENCES country (id) ON DELETE CASCADE;
      END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'player_team_id_fkey'
      ) THEN
        ALTER TABLE player ADD CONSTRAINT player_team_id_fkey FOREIGN KEY (team_id) REFERENCES team (id) ON DELETE CASCADE;
      END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'team_academy_id_fkey'
      ) THEN
        ALTER TABLE team ADD CONSTRAINT team_academy_id_fkey FOREIGN KEY (academy_id) REFERENCES academy (id) ON DELETE CASCADE;
      END IF;
    END
    $$;
    """)


def downgrade() -> None:
    """Downgrade schema safely: drop if exists then recreate original-named FKs."""
    op.execute("ALTER TABLE team DROP CONSTRAINT IF EXISTS team_academy_id_fkey;")
    op.create_foreign_key(op.f("team_academy_id_fkey"), "team", "academy", ["academy_id"], ["id"])

    op.execute("ALTER TABLE player DROP CONSTRAINT IF EXISTS player_team_id_fkey;")
    op.create_foreign_key(op.f("player_equipe_id_fkey"), "player", "team", ["team_id"], ["id"])

    op.execute("ALTER TABLE academy DROP CONSTRAINT IF EXISTS academy_country_id_fkey;")
    op.create_foreign_key(op.f("academy_country_id_fkey"), "academy", "country", ["country_id"], ["id"])
    