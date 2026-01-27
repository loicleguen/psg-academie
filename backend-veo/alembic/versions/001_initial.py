"""Initial schema with all models

Revision ID: 001_initial
Revises:
Create Date: 2024-12-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create seasons table
    op.create_table('seasons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('label')
    )
    op.create_index(op.f('ix_seasons_id'), 'seasons', ['id'], unique=False)

    # Create teams table
    op.create_table('teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_teams_id'), 'teams', ['id'], unique=False)

    # Create metric_definitions table
    op.create_table('metric_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('label_fr', sa.String(length=200), nullable=False),
        sa.Column('description_fr', sa.Text(), nullable=True),
        sa.Column('scope', sa.Enum('TEAM', 'PLAYER', name='metricscope'), nullable=False),
        sa.Column('category', sa.Enum('POSSESSION', 'PASSES', 'EVENTS', 'COMBINATIONS', 'GENERAL', name='metriccategory'), nullable=False),
        sa.Column('datatype', sa.Enum('INT', 'FLOAT', 'PERCENT', name='metricdatatype'), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('side', sa.Enum('OWN', 'OPPONENT', 'NONE', name='metricside'), nullable=True),
        sa.Column('is_derived', sa.Boolean(), nullable=True),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_metric_definitions_id'), 'metric_definitions', ['id'], unique=False)
    op.create_index(op.f('ix_metric_definitions_slug'), 'metric_definitions', ['slug'], unique=False)

    # Create players table
    op.create_table('players',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('main_position', sa.String(length=50), nullable=False),
        sa.Column('secondary_positions', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_players_id'), 'players', ['id'], unique=False)

    # Create matches table
    op.create_table('matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('opponent_name', sa.String(length=200), nullable=False),
        sa.Column('is_home', sa.Boolean(), nullable=True),
        sa.Column('match_type', sa.Enum('LEAGUE', 'CUP', 'FRIENDLY', 'TOURNAMENT', name='matchtype'), nullable=True),
        sa.Column('competition', sa.String(length=200), nullable=True),
        sa.Column('score_for', sa.Integer(), nullable=True),
        sa.Column('score_against', sa.Integer(), nullable=True),
        sa.Column('veo_title', sa.String(length=300), nullable=True),
        sa.Column('veo_url', sa.String(length=500), nullable=True),
        sa.Column('veo_duration', sa.Integer(), nullable=True),
        sa.Column('veo_camera', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matches_id'), 'matches', ['id'], unique=False)

    # Create match_player_participations table
    op.create_table('match_player_participations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('is_starter', sa.Boolean(), nullable=True),
        sa.Column('is_captain', sa.Boolean(), nullable=True),
        sa.Column('minutes_played', sa.Integer(), nullable=True),
        sa.Column('position_played', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id', 'player_id', name='uq_match_player')
    )
    op.create_index(op.f('ix_match_player_participations_id'), 'match_player_participations', ['id'], unique=False)

    # Create team_match_metric_values table
    op.create_table('team_match_metric_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('metric_id', sa.Integer(), nullable=False),
        sa.Column('side', sa.Enum('OWN', 'OPPONENT', 'NONE', name='metricside'), nullable=False),
        sa.Column('value_number', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.ForeignKeyConstraint(['metric_id'], ['metric_definitions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id', 'metric_id', 'side', name='uq_match_metric_side')
    )
    op.create_index(op.f('ix_team_match_metric_values_id'), 'team_match_metric_values', ['id'], unique=False)

    # Create player_match_metric_values table
    op.create_table('player_match_metric_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('metric_id', sa.Integer(), nullable=False),
        sa.Column('value_number', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.ForeignKeyConstraint(['metric_id'], ['metric_definitions.id'], ),
        sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id', 'player_id', 'metric_id', name='uq_match_player_metric')
    )
    op.create_index(op.f('ix_player_match_metric_values_id'), 'player_match_metric_values', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_player_match_metric_values_id'), table_name='player_match_metric_values')
    op.drop_table('player_match_metric_values')

    op.drop_index(op.f('ix_team_match_metric_values_id'), table_name='team_match_metric_values')
    op.drop_table('team_match_metric_values')

    op.drop_index(op.f('ix_match_player_participations_id'), table_name='match_player_participations')
    op.drop_table('match_player_participations')

    op.drop_index(op.f('ix_matches_id'), table_name='matches')
    op.drop_table('matches')

    op.drop_index(op.f('ix_players_id'), table_name='players')
    op.drop_table('players')

    op.drop_index(op.f('ix_metric_definitions_slug'), table_name='metric_definitions')
    op.drop_index(op.f('ix_metric_definitions_id'), table_name='metric_definitions')
    op.drop_table('metric_definitions')

    op.drop_index(op.f('ix_teams_id'), table_name='teams')
    op.drop_table('teams')

    op.drop_index(op.f('ix_seasons_id'), table_name='seasons')
    op.drop_table('seasons')
