"""add_injury_table

Revision ID: 14a3aca86c75
Revises: 32f0864c8ac0
Create Date: 2026-02-13 17:39:31.533208

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14a3aca86c75'
down_revision: Union[str, Sequence[str], None] = '32f0864c8ac0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'injury' AND column_name = 'injury_end_date'
        ) THEN
            ALTER TABLE injury ADD COLUMN injury_end_date DATE;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'injury' AND column_name = 'restriction_date'
        ) THEN
            ALTER TABLE injury ADD COLUMN restriction_date DATE;
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'injury' AND column_name = 'restriction_type'
        ) THEN
            ALTER TABLE injury ADD COLUMN restriction_type VARCHAR(50);
        END IF;
    END
    $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'injury' AND column_name = 'restriction_type'
        ) THEN
            ALTER TABLE injury DROP COLUMN restriction_type;
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'injury' AND column_name = 'restriction_date'
        ) THEN
            ALTER TABLE injury DROP COLUMN restriction_date;
        END IF;

        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'injury' AND column_name = 'injury_end_date'
        ) THEN
            ALTER TABLE injury DROP COLUMN injury_end_date;
        END IF;
    END
    $$;
    """)
    