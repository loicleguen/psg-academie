"""Add accel_count, decel_count, temps_ad_secs for VOL/INT calculation

Revision ID: a1b2c3d4e5f6
Revises: 32f0864c8ac0
Create Date: 2026-03-05 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f2b05de82e6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('catapultsession', sa.Column('accel_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('catapultsession', sa.Column('decel_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('catapultsession', sa.Column('temps_ad_secs', sa.Float(), nullable=False, server_default='0.0'))


def downgrade() -> None:
    op.drop_column('catapultsession', 'temps_ad_secs')
    op.drop_column('catapultsession', 'decel_count')
    op.drop_column('catapultsession', 'accel_count')
