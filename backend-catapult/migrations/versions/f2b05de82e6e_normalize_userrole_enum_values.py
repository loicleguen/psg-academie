"""normalize userrole enum values

Revision ID: f2b05de82e6e
Revises: tmp_add_user_fields_1771506972
Create Date: 2026-03-03 13:16:22.560458

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f2b05de82e6e"
down_revision: Union[str, Sequence[str], None] = "tmp_add_user_fields_1771506972"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Normalize enum userrole to lowercase values (admin/coach/analyst/player)
    to match application-level enums.
    """
    op.execute(
        """
        DO $$
        BEGIN
          -- If the enum already uses lowercase labels, do nothing.
          IF EXISTS (
            SELECT 1
            FROM pg_type t
            JOIN pg_enum e ON e.enumtypid = t.oid
            WHERE t.typname = 'userrole' AND e.enumlabel = 'admin'
          ) THEN
            RETURN;
          END IF;

          -- 1) Create a new enum with lowercase labels
          CREATE TYPE userrole_new AS ENUM ('admin', 'coach', 'analyst', 'player');

          -- 2) Convert column "user".role -> text -> mapped lowercase -> new enum
          ALTER TABLE "user"
            ALTER COLUMN role TYPE userrole_new
            USING (
              CASE UPPER(role::text)
                WHEN 'ADMIN'   THEN 'admin'
                WHEN 'COACH'   THEN 'coach'
                WHEN 'ANALYST' THEN 'analyst'
                WHEN 'PLAYER'  THEN 'player'
                ELSE 'player'  -- fallback safe default
              END
            )::userrole_new;

          -- 3) Drop old enum + rename new enum to userrole
          DROP TYPE userrole;
          ALTER TYPE userrole_new RENAME TO userrole;
        END
        $$;
        """
    )


def downgrade() -> None:
    """
    Reverse: recreate enum in uppercase labels and convert role back.
    """
    op.execute(
        """
        DO $$
        BEGIN
          -- If enum already uses uppercase labels, do nothing.
          IF EXISTS (
            SELECT 1
            FROM pg_type t
            JOIN pg_enum e ON e.enumtypid = t.oid
            WHERE t.typname = 'userrole' AND e.enumlabel = 'ADMIN'
          ) THEN
            RETURN;
          END IF;

          CREATE TYPE userrole_old AS ENUM ('ADMIN', 'COACH', 'ANALYST', 'PLAYER');

          ALTER TABLE "user"
            ALTER COLUMN role TYPE userrole_old
            USING (
              CASE LOWER(role::text)
                WHEN 'admin'   THEN 'ADMIN'
                WHEN 'coach'   THEN 'COACH'
                WHEN 'analyst' THEN 'ANALYST'
                WHEN 'player'  THEN 'PLAYER'
                ELSE 'PLAYER'
              END
            )::userrole_old;

          DROP TYPE userrole;
          ALTER TYPE userrole_old RENAME TO userrole;
        END
        $$;
        """
    )