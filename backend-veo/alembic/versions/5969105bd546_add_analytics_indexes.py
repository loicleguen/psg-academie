"""add analytics indexes

Revision ID: 5969105bd546
Revises: 001_initial
Create Date: 2026-01-21 16:56:43.638413

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '5969105bd546'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # matches: used heavily in list_matches + analytics filters
    op.create_index(
        "ix_matches_team_season_date",
        "matches",
        ["team_id", "season_id", "date"],
        unique=False,
    )

    # optional but useful (team timelines without season filter)
    op.create_index(
        "ix_matches_team_date",
        "matches",
        ["team_id", "date"],
        unique=False,
    )

    # players: list_players(team_id=...)
    op.create_index(
        "ix_players_team_id",
        "players",
        ["team_id"],
        unique=False,
    )

    # participations: match page + player history pages
    op.create_index(
        "ix_mpp_match_id",
        "match_player_participations",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        "ix_mpp_player_id",
        "match_player_participations",
        ["player_id"],
        unique=False,
    )

    # team metrics: analytics reads values by match_id and/or metric
    # (unique already exists on match_id, metric_id, side)
    op.create_index(
        "ix_tmmv_match_id",
        "team_match_metric_values",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        "ix_tmmv_metric_match_side",
        "team_match_metric_values",
        ["metric_id", "match_id", "side"],
        unique=False,
    )

    # player metrics: leaderboard + player profile history
    # (unique already exists on match_id, player_id, metric_id)
    op.create_index(
        "ix_pmmv_match_id",
        "player_match_metric_values",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        "ix_pmmv_metric_match",
        "player_match_metric_values",
        ["metric_id", "match_id"],
        unique=False,
    )
    op.create_index(
        "ix_pmmv_player_match",
        "player_match_metric_values",
        ["player_id", "match_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pmmv_player_match", table_name="player_match_metric_values")
    op.drop_index("ix_pmmv_metric_match", table_name="player_match_metric_values")
    op.drop_index("ix_pmmv_match_id", table_name="player_match_metric_values")

    op.drop_index("ix_tmmv_metric_match_side", table_name="team_match_metric_values")
    op.drop_index("ix_tmmv_match_id", table_name="team_match_metric_values")

    op.drop_index("ix_mpp_player_id", table_name="match_player_participations")
    op.drop_index("ix_mpp_match_id", table_name="match_player_participations")

    op.drop_index("ix_players_team_id", table_name="players")

    op.drop_index("ix_matches_team_date", table_name="matches")
    op.drop_index("ix_matches_team_season_date", table_name="matches")
