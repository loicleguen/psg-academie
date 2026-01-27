"""perf: add partial indexes for OWN metrics

Revision ID: f652a511cdba
Revises: 8faf87dba1c4
Create Date: 2026-01-22 11:18:46.522023

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f652a511cdba"
down_revision = "8faf87dba1c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Team metrics: optimize common queries on OWN side
    op.execute(
        """
    CREATE INDEX IF NOT EXISTS ix_tmmv_own_metric_match
    ON team_match_metric_values(metric_id, match_id)
    WHERE side = 'OWN';
    """
    )

    # Optional: also optimize opponent side queries (if you use them often)
    op.execute(
        """
    CREATE INDEX IF NOT EXISTS ix_tmmv_opp_metric_match
    ON team_match_metric_values(metric_id, match_id)
    WHERE side = 'OPPONENT';
    """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tmmv_own_metric_match;")
    op.execute("DROP INDEX IF EXISTS ix_tmmv_opp_metric_match;")
