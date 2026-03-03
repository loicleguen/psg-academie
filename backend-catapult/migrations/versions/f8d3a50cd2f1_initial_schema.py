"""Initial schema

Revision ID: f8d3a50cd2f1
Revises:
Create Date: 2026-01-11 11:18:02.038022
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8d3a50cd2f1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables for catapult backend (SQLModel)."""

    # ---- Enum types
    user_role_enum = sa.Enum("admin", "coach", "player", name="userrole")

    # ---- country
    op.create_table(
        "country",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
    )

    # ---- academy
    op.create_table(
        "academy",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["country_id"],
            ["country.id"],
            name="academy_country_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # ---- team
    op.create_table(
        "team",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("academy_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["academy_id"],
            ["academy.id"],
            name="team_academy_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # ---- user
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False, server_default="player"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("player_name", sa.String(), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("date_of_birth", sa.DateTime(), nullable=True),
        sa.Column("adress", sa.String(length=255), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("strong_foot", sa.String(length=10), nullable=True),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("emergency_contact", sa.String(length=255), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("position", sa.String(length=50), nullable=True),
        sa.Column("photo_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["team.id"],
            name="user_team_id_fkey",
        ),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )
    op.create_index("ix_user_email", "user", ["email"])
    op.create_index("ix_user_player_name", "user", ["player_name"])

    # ---- injury
    op.create_table(
        "injury",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body_part", sa.String(length=100), nullable=True),
        sa.Column("injury_date", sa.Date(), nullable=False),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("coord_x", sa.Float(), nullable=True),
        sa.Column("coord_y", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="injury_user_id_fkey",
        ),
    )
    op.create_index("ix_injury_user_id", "injury", ["user_id"])

    # ---- refresh_token
    op.create_table(
        "refreshtoken",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("token", sa.String(length=500), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="refreshtoken_user_id_fkey",
        ),
        sa.UniqueConstraint("token", name="uq_refreshtoken_token"),
    )
    op.create_index("ix_refreshtoken_token", "refreshtoken", ["token"])

    # ---- catapult_session
    op.create_table(
        "catapultsession",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("session_title", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("split_name", sa.String(), nullable=False),
        sa.Column("tags", sa.String(), nullable=False),
        sa.Column("split_start_time", sa.Float(), nullable=False),
        sa.Column("split_end_time", sa.Float(), nullable=False),
        sa.Column("duration", sa.Integer(), nullable=False),

        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("sprint_distance_m", sa.Float(), nullable=False),
        sa.Column("distance_per_min", sa.Float(), nullable=False),

        sa.Column("top_speed", sa.Float(), nullable=False),
        sa.Column("power_score", sa.Float(), nullable=False),
        sa.Column("hr_max", sa.Integer(), nullable=True),
        sa.Column("player_load", sa.Float(), nullable=False),
        sa.Column("energy_kcal", sa.Float(), nullable=False),

        sa.Column("impacts", sa.Integer(), nullable=False),
        sa.Column("power_plays", sa.Integer(), nullable=False),
        sa.Column("hr_load", sa.Integer(), nullable=False),
        sa.Column("time_in_red_zone_min", sa.Float(), nullable=False),

        sa.Column("speed_zone_1_km", sa.Float(), nullable=False),
        sa.Column("speed_zone_2_km", sa.Float(), nullable=False),
        sa.Column("speed_zone_3_km", sa.Float(), nullable=False),
        sa.Column("speed_zone_4_km", sa.Float(), nullable=False),
        sa.Column("speed_zone_5_km", sa.Float(), nullable=False),

        sa.Column("speed_zone_1_secs", sa.Integer(), nullable=False),
        sa.Column("speed_zone_2_secs", sa.Integer(), nullable=False),
        sa.Column("speed_zone_3_secs", sa.Integer(), nullable=False),
        sa.Column("speed_zone_4_secs", sa.Integer(), nullable=False),
        sa.Column("speed_zone_5_secs", sa.Integer(), nullable=False),

        sa.Column("max_acceleration", sa.Float(), nullable=False),
        sa.Column("max_deceleration", sa.Float(), nullable=False),
        sa.Column("work_ratio", sa.Float(), nullable=False),

        sa.Column("session_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="catapultsession_user_id_fkey",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    """Drop all tables (reverse dependency order)."""

    op.drop_table("catapultsession")
    op.drop_index("ix_refreshtoken_token", table_name="refreshtoken")
    op.drop_table("refreshtoken")
    op.drop_index("ix_injury_user_id", table_name="injury")
    op.drop_table("injury")
    op.drop_index("ix_user_player_name", table_name="user")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")
    op.drop_table("team")
    op.drop_table("academy")
    op.drop_table("country")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS userrole;")