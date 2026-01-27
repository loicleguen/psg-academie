"""
Schemas package.

This package centralizes all Pydantic schemas used by the API.

For backward compatibility, this module re-exports commonly used schemas
so existing imports like `from app import schemas` keep working.
"""

# Core (CRUD + common)
from .core import (
    KPIResponse,
    KPIValue,
    LeaderboardEntry,  # noqa: F401
    LeaderboardResponse,
    Match,
    MatchBase,
    MatchCreate,
    MatchUpdate,
    MetricDefinition,
    MetricDefinitionBase,
    Participation,
    ParticipationBase,
    ParticipationBulk,
    ParticipationCreate,
    ParticipationUpdate,
    Player,
    PlayerBase,
    PlayerCreate,
    PlayerMetricValueBulk,
    PlayerMetricValueInput,
    PlayerMetricValueOutput,
    PlayerUpdate,
    RadarPoint,
    RadarResponse,
    Season,
    SeasonBase,
    SeasonCreate,
    Team,
    TeamBase,
    TeamCreate,
    TeamMetricValueBulk,
    TeamMetricValueInput,
    TeamMetricValueOutput,
    TimeSeriesPoint,
    TimeSeriesResponse,
)

# Summary (new feature)
from .summary import (
    MatchSummaryMatch,
    MatchSummaryResponse,  # noqa: F401
    ParticipationWithPlayer,
    PlayerGridColumn,
    PlayerGridPlayer,
    PlayerMetricsGrid,
    TeamMetricCell,
    TeamMetricsBlock,
)
