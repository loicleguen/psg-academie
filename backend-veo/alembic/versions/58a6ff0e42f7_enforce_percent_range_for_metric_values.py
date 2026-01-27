"""enforce percent range for metric values

Revision ID: 58a6ff0e42f7
Revises: f652a511cdba
Create Date: 2026-01-22 11:24:58.334073

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '58a6ff0e42f7'
down_revision = 'f652a511cdba'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION enforce_percent_range()
    RETURNS trigger AS $$
    DECLARE
        dtype text;
    BEGIN
        SELECT datatype::text INTO dtype
        FROM metric_definitions
        WHERE id = NEW.metric_id;

        -- Only enforce for PERCENT metrics
        IF dtype = 'PERCENT' THEN
            IF NEW.value_number < 0 OR NEW.value_number > 100 THEN
                RAISE EXCEPTION 'Percent metric out of range (0-100): metric_id=% value=%',
                    NEW.metric_id, NEW.value_number;
            END IF;
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_enforce_percent_team_values ON team_match_metric_values;
    CREATE TRIGGER trg_enforce_percent_team_values
    BEFORE INSERT OR UPDATE ON team_match_metric_values
    FOR EACH ROW
    EXECUTE FUNCTION enforce_percent_range();
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_enforce_percent_player_values ON player_match_metric_values;
    CREATE TRIGGER trg_enforce_percent_player_values
    BEFORE INSERT OR UPDATE ON player_match_metric_values
    FOR EACH ROW
    EXECUTE FUNCTION enforce_percent_range();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_enforce_percent_team_values ON team_match_metric_values;")
    op.execute("DROP TRIGGER IF EXISTS trg_enforce_percent_player_values ON player_match_metric_values;")
    op.execute("DROP FUNCTION IF EXISTS enforce_percent_range();")