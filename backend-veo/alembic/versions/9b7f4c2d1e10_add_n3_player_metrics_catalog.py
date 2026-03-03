"""add n3 player metrics catalog

Revision ID: 9b7f4c2d1e10
Revises: 58a6ff0e42f7
Create Date: 2026-02-26 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9b7f4c2d1e10"
down_revision = "58a6ff0e42f7"
branch_labels = None
depends_on = None


N3_PLAYER_METRICS = [
    ("player_shots_on_target", "Tirs cadrés"),
    ("player_duels_won", "Duels gagnés"),
    ("player_fouls_committed", "Fautes"),
    ("player_cards", "Cartons"),
    ("player_offsides", "Hors-jeu"),
    ("player_dribbles_won", "Dribbles réussis"),
    ("player_tackles_won", "Tacles réussis"),
    ("player_recoveries", "Récupérations"),
    ("player_ball_losses", "Pertes de balle"),
]


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            UPDATE metric_definitions
            SET label_fr = 'Passes décisives'
            WHERE slug = 'player_goal_assists'
            """
        )
    )

    for slug, label_fr in N3_PLAYER_METRICS:
        bind.execute(
            sa.text(
                """
                INSERT INTO metric_definitions (
                    slug,
                    label_fr,
                    scope,
                    category,
                    datatype,
                    unit,
                    side,
                    is_derived,
                    formula,
                    description_fr
                )
                VALUES (
                    :slug,
                    :label_fr,
                    'PLAYER',
                    'EVENTS',
                    'INT',
                    'count',
                    'NONE',
                    false,
                    NULL,
                    NULL
                )
                ON CONFLICT (slug) DO UPDATE
                SET
                    label_fr = EXCLUDED.label_fr,
                    scope = EXCLUDED.scope,
                    category = EXCLUDED.category,
                    datatype = EXCLUDED.datatype,
                    unit = EXCLUDED.unit,
                    side = EXCLUDED.side,
                    is_derived = EXCLUDED.is_derived,
                    formula = NULL
                """
            ),
            {"slug": slug, "label_fr": label_fr},
        )


def downgrade() -> None:
    bind = op.get_bind()

    for slug, _ in N3_PLAYER_METRICS:
        bind.execute(
            sa.text(
                """
                DELETE FROM player_match_metric_values
                WHERE metric_id IN (
                    SELECT id FROM metric_definitions WHERE slug = :slug
                )
                """
            ),
            {"slug": slug},
        )

        bind.execute(
            sa.text("DELETE FROM metric_definitions WHERE slug = :slug"),
            {"slug": slug},
        )

    bind.execute(
        sa.text(
            """
            UPDATE metric_definitions
            SET label_fr = 'Goal assists'
            WHERE slug = 'player_goal_assists'
            """
        )
    )
