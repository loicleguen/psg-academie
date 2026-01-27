"""enforce raw-only metric values

Revision ID: 8faf87dba1c4
Revises: 5969105bd546
Create Date: 2026-01-22 10:56:53.578004

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '8faf87dba1c4'
down_revision = '5969105bd546'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_derived_metric_values()
    RETURNS trigger AS $$
    DECLARE
        derived boolean;
    BEGIN
        SELECT is_derived INTO derived
        FROM metric_definitions
        WHERE id = NEW.metric_id;

        IF derived IS TRUE THEN
            RAISE EXCEPTION 'Cannot store derived metric_id=%', NEW.metric_id;
        END IF;

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_prevent_derived_team_values ON team_match_metric_values;
    CREATE TRIGGER trg_prevent_derived_team_values
    BEFORE INSERT OR UPDATE ON team_match_metric_values
    FOR EACH ROW
    EXECUTE FUNCTION prevent_derived_metric_values();
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_prevent_derived_player_values ON player_match_metric_values;
    CREATE TRIGGER trg_prevent_derived_player_values
    BEFORE INSERT OR UPDATE ON player_match_metric_values
    FOR EACH ROW
    EXECUTE FUNCTION prevent_derived_metric_values();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_derived_team_values ON team_match_metric_values;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_derived_player_values ON player_match_metric_values;")
    op.execute("DROP FUNCTION IF EXISTS prevent_derived_metric_values();")
