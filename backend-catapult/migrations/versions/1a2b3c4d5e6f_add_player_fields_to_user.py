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
    # Add nullable columns to `user`
    op.add_column("user", sa.Column("player_name", sa.Text(), nullable=True))
    op.add_column("user", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("user", sa.Column("team_id", sa.Integer(), nullable=True))

    # Index for player_name (matches model index=True)
    op.create_index(op.f("ix_user_player_name"), "user", ["player_name"], unique=False)

    # Foreign key from user.team_id -> team.id
    op.create_foreign_key(
        "fk_user_team",
        "user",
        "team",
        ["team_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop FK, index and columns in reverse order
    op.drop_constraint("fk_user_team", "user", type_="foreignkey")
    op.drop_index(op.f("ix_user_player_name"), table_name="user")
    op.drop_column("user", "team_id")
    op.drop_column("user", "age")
    op.drop_column("user", "player_name")
    