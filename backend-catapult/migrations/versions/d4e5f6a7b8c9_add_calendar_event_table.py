"""add calendar event table

Revision ID: d4e5f6a7b8c9
Revises: cc1ce2b2f1bf
Create Date: 2026-04-24 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "cc1ce2b2f1bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


event_type_enum = postgresql.ENUM(
    "training",
    "match",
    "meeting",
    "medical",
    "travel",
    "rest",
    "other",
    name="calendareventtype",
    create_type=False,
)
visibility_enum = postgresql.ENUM(
    "all",
    "team",
    "staff",
    "players",
    "private",
    name="calendareventvisibility",
    create_type=False,
)
status_enum = postgresql.ENUM(
    "scheduled",
    "cancelled",
    "completed",
    name="calendareventstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    event_type_enum.create(bind, checkfirst=True)
    visibility_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    inspector = sa.inspect(bind)
    table_exists = inspector.has_table("calendarevent")

    if not table_exists:
        op.create_table(
            "calendarevent",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=2000), nullable=True),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column(
                "event_type",
                event_type_enum,
                nullable=False,
                server_default="training",
            ),
            sa.Column(
                "visibility",
                visibility_enum,
                nullable=False,
                server_default="all",
            ),
            sa.Column(
                "status",
                status_enum,
                nullable=False,
                server_default="scheduled",
            ),
            sa.Column("start_at", sa.DateTime(), nullable=False),
            sa.Column("end_at", sa.DateTime(), nullable=False),
            sa.Column("all_day", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column(
                "timezone",
                sa.String(length=64),
                nullable=False,
                server_default="Europe/Paris",
            ),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("source_type", sa.String(length=50), nullable=True),
            sa.Column("source_ref", sa.String(length=255), nullable=True),
            sa.Column("color", sa.String(length=20), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["user.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = (
        {idx["name"] for idx in inspector.get_indexes("calendarevent")}
        if table_exists
        else set()
    )

    index_specs = [
        ("ix_calendarevent_title", ["title"]),
        ("ix_calendarevent_start_at", ["start_at"]),
        ("ix_calendarevent_end_at", ["end_at"]),
        ("ix_calendarevent_team_id", ["team_id"]),
        ("ix_calendarevent_created_by_id", ["created_by_id"]),
        ("ix_calendarevent_type", ["event_type"]),
        ("ix_calendarevent_status", ["status"]),
    ]
    for index_name, columns in index_specs:
        if index_name not in existing_indexes:
            op.create_index(index_name, "calendarevent", columns)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("calendarevent"):
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("calendarevent")}
        for index_name in [
            "ix_calendarevent_status",
            "ix_calendarevent_type",
            "ix_calendarevent_created_by_id",
            "ix_calendarevent_team_id",
            "ix_calendarevent_end_at",
            "ix_calendarevent_start_at",
            "ix_calendarevent_title",
        ]:
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name="calendarevent")
        op.drop_table("calendarevent")

    status_enum.drop(bind, checkfirst=True)
    visibility_enum.drop(bind, checkfirst=True)
    event_type_enum.drop(bind, checkfirst=True)
