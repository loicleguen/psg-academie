"""Add decel_high_count (Deceleration Zone Count > 4 m/s/s) to catapultsession

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('catapultsession',
        sa.Column('decel_high_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('catapultsession', 'decel_high_count')
