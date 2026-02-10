"""drop_player_table

Revision ID: 2c3d4e5f6a7b
Revises: 1a2b3c4d5e6f
Create Date: 2026-01-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2c3d4e5f6a7b"
down_revision: Union[str, Sequence[str], None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop player table and dependencies safely
    op.execute("DROP TABLE IF EXISTS player CASCADE;")


def downgrade() -> None:
    # Recreate a minimal `player` table if it does not exist
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'player') THEN
        CREATE TABLE player (
          id SERIAL PRIMARY KEY,
          first_name TEXT,
          last_name TEXT,
          team_id INTEGER
        );
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'team') THEN
          BEGIN
            ALTER TABLE player DROP CONSTRAINT IF EXISTS player_team_id_fkey;
            ALTER TABLE player ADD CONSTRAINT player_team_id_fkey FOREIGN KEY (team_id) REFERENCES team (id) ON DELETE CASCADE;
          EXCEPTION WHEN undefined_table THEN
            NULL;
          END;
        END IF;
      END IF;
    END
    $$;
    """)

