from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class CalendarEventType(str, Enum):
    TRAINING = "training"
    MATCH = "match"
    MEETING = "meeting"
    MEDICAL = "medical"
    TRAVEL = "travel"
    REST = "rest"
    OTHER = "other"


class CalendarEventVisibility(str, Enum):
    ALL = "all"
    TEAM = "team"
    STAFF = "staff"
    PLAYERS = "players"
    PRIVATE = "private"


class CalendarEventStatus(str, Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class CalendarEvent(SQLModel, table=True):
    """Shared academy calendar event."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255, index=True)
    description: Optional[str] = Field(default=None, max_length=2000)
    location: Optional[str] = Field(default=None, max_length=255)
    event_type: CalendarEventType = Field(
        default=CalendarEventType.TRAINING,
        sa_column=Column(
            SAEnum(
                CalendarEventType,
                name="calendareventtype",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        ),
    )
    visibility: CalendarEventVisibility = Field(
        default=CalendarEventVisibility.ALL,
        sa_column=Column(
            SAEnum(
                CalendarEventVisibility,
                name="calendareventvisibility",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        ),
    )
    status: CalendarEventStatus = Field(
        default=CalendarEventStatus.SCHEDULED,
        sa_column=Column(
            SAEnum(
                CalendarEventStatus,
                name="calendareventstatus",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        ),
    )
    start_at: datetime = Field(index=True)
    end_at: datetime = Field(index=True)
    all_day: bool = Field(default=False)
    timezone: str = Field(default="Europe/Paris", max_length=64)
    team_id: Optional[int] = Field(default=None, foreign_key="team.id", index=True)
    created_by_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    source_type: Optional[str] = Field(default=None, max_length=50)
    source_ref: Optional[str] = Field(default=None, max_length=255)
    custom_type_label: Optional[str] = Field(default=None, max_length=100)
    color: Optional[str] = Field(default=None, max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class CalendarEventCreate(SQLModel):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    event_type: CalendarEventType = CalendarEventType.TRAINING
    visibility: CalendarEventVisibility = CalendarEventVisibility.ALL
    status: CalendarEventStatus = CalendarEventStatus.SCHEDULED
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    timezone: str = "Europe/Paris"
    team_id: Optional[int] = None
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    custom_type_label: Optional[str] = None
    color: Optional[str] = None


class CalendarEventUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    event_type: Optional[CalendarEventType] = None
    visibility: Optional[CalendarEventVisibility] = None
    status: Optional[CalendarEventStatus] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    all_day: Optional[bool] = None
    timezone: Optional[str] = None
    team_id: Optional[int] = None
    source_type: Optional[str] = None
    source_ref: Optional[str] = None
    custom_type_label: Optional[str] = None
    color: Optional[str] = None


class CalendarEventRead(SQLModel):
    id: int
    title: str
    description: Optional[str]
    location: Optional[str]
    event_type: CalendarEventType
    visibility: CalendarEventVisibility
    status: CalendarEventStatus
    start_at: datetime
    end_at: datetime
    all_day: bool
    timezone: str
    team_id: Optional[int]
    created_by_id: Optional[int]
    source_type: Optional[str]
    source_ref: Optional[str]
    custom_type_label: Optional[str]
    color: Optional[str]
    created_at: datetime
    updated_at: datetime
