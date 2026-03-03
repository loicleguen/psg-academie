"""Add position field to User

Revision ID: 32f0864c8ac0
Revises: 2c3d4e5f6a7b
Create Date: 2026-02-13 14:06:32.044613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '32f0864c8ac0'
down_revision: Union[str, Sequence[str], None] = '2c3d4e5f6a7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) player table may not exist on fresh DBs
    op.execute("DROP TABLE IF EXISTS player CASCADE;")

    # 2) constraint name may differ depending on how it was created
    op.execute("ALTER TABLE catapultsession DROP CONSTRAINT IF EXISTS catapultsession_user_id_fkey;")
    op.create_foreign_key(
        "catapultsession_user_id_fkey",
        "catapultsession",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3) add position column ONLY if it doesn't exist
    op.execute("""
    DO $$
    BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'user'
        AND column_name = 'position'
    ) THEN
        ALTER TABLE "user" ADD COLUMN position VARCHAR(50);
    END IF;
    END
    $$;
    """)

    # 4) fk_user_team may not exist / name may differ
    op.execute("ALTER TABLE \"user\" DROP CONSTRAINT IF EXISTS fk_user_team;")
    op.create_foreign_key(
        "fk_user_team",
        "user",
        "team",
        ["team_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Revert user-team FK
    op.execute('ALTER TABLE "user" DROP CONSTRAINT IF EXISTS fk_user_team;')
    op.create_foreign_key(
        "fk_user_team",
        "user",
        "team",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Drop position column
    op.drop_column("user", "position")

    # Revert catapultsession FK
    op.execute("ALTER TABLE catapultsession DROP CONSTRAINT IF EXISTS catapultsession_user_id_fkey;")
    op.create_foreign_key(
        "catapultsession_user_id_fkey",
        "catapultsession",
        "user",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Recreate player table (legacy)
    op.create_table(
        "player",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("age", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], name="player_team_id_fkey", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="player_user_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="player_pkey"),
    )
