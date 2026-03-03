"""add_injury_coordinates

Revision ID: 18d312554f1c
Revises: 14a3aca86c75
Create Date: 2026-02-13 18:25:10.748139

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '18d312554f1c'
down_revision: Union[str, Sequence[str], None] = '14a3aca86c75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Add coord_x / coord_y only if missing (fresh DB may already have them)
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'injury' AND column_name = 'coord_x'
      ) THEN
        ALTER TABLE injury ADD COLUMN coord_x FLOAT;
      END IF;

      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'injury' AND column_name = 'coord_y'
      ) THEN
        ALTER TABLE injury ADD COLUMN coord_y FLOAT;
      END IF;
    END
    $$;
    """)

    # Keep the alter_column as-is (it should be safe even if coords already exist)
    op.alter_column(
        'injury',
        'body_part',
        existing_type=postgresql.ENUM(
            'CERVICALES', 'EPAULES', 'COUDES', 'POIGNETS', 'ADDUCTEURS', 'CUISSES', 'GENOUX', 'CHEVILLES',
            name='bodypart'
        ),
        type_=sqlmodel.sql.sqltypes.AutoString(length=100),
        nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.alter_column(
        'injury',
        'body_part',
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=100),
        type_=postgresql.ENUM(
            'CERVICALES', 'EPAULES', 'COUDES', 'POIGNETS', 'ADDUCTEURS', 'CUISSES', 'GENOUX', 'CHEVILLES',
            name='bodypart'
        ),
        nullable=False
    )

    # Drop coord columns only if they exist
    op.execute("ALTER TABLE injury DROP COLUMN IF EXISTS coord_y;")
    op.execute("ALTER TABLE injury DROP COLUMN IF EXISTS coord_x;")
