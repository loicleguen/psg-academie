from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date
from app.models import MatchType, MetricScope, MetricCategory, MetricDataType, MetricSide

# Season schemas
class SeasonBase(BaseModel):
    label: str
    start_date: date
    end_date: date

class SeasonCreate(SeasonBase):
    pass

class Season(SeasonBase):
    id: int

    class Config:
        from_attributes = True

# Team schemas
class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    pass

class Team(TeamBase):
    id: int

    class Config:
        from_attributes = True

# Player schemas
class PlayerBase(BaseModel):
    first_name: str
    last_name: str
    main_position: str
    secondary_positions: Optional[str] = None

class PlayerCreate(PlayerBase):
    team_id: int

class PlayerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    main_position: Optional[str] = None
    secondary_positions: Optional[str] = None

class Player(PlayerBase):
    id: int
    team_id: int

    class Config:
        from_attributes = True

# Match schemas
class MatchBase(BaseModel):
    date: date
    opponent_name: str
    is_home: bool = True
    match_type: MatchType = MatchType.LEAGUE
    competition: Optional[str] = None
    score_for: Optional[int] = None
    score_against: Optional[int] = None
    veo_title: Optional[str] = None
    veo_url: Optional[str] = None
    veo_duration: Optional[int] = None
    veo_camera: Optional[str] = None

class MatchCreate(MatchBase):
    team_id: int
    season_id: int

class MatchUpdate(BaseModel):
    date: Optional["date"] = None
    opponent_name: Optional[str] = None
    is_home: Optional[bool] = None
    match_type: Optional[MatchType] = None
    competition: Optional[str] = None
    score_for: Optional[int] = None
    score_against: Optional[int] = None
    veo_title: Optional[str] = None
    veo_url: Optional[str] = None
    veo_duration: Optional[int] = None
    veo_camera: Optional[str] = None

class Match(MatchBase):
    id: int
    team_id: int
    season_id: int

    class Config:
        from_attributes = True

# Participation schemas
class ParticipationBase(BaseModel):
    player_id: int
    is_starter: bool = False
    is_captain: bool = False
    minutes_played: Optional[int] = None
    position_played: Optional[str] = None

class ParticipationCreate(ParticipationBase):
    pass

class ParticipationUpdate(ParticipationBase):
    pass

class Participation(ParticipationBase):
    id: int
    match_id: int

    class Config:
        from_attributes = True

class ParticipationBulk(BaseModel):
    """Bulk update of participations for a match"""
    participations: List[ParticipationBase]

# Metric Definition schemas
class MetricDefinitionBase(BaseModel):
    slug: str
    label_fr: str
    description_fr: Optional[str] = None
    scope: MetricScope
    category: MetricCategory
    datatype: MetricDataType = MetricDataType.INT
    unit: Optional[str] = None
    side: MetricSide = MetricSide.NONE
    is_derived: bool = False
    formula: Optional[str] = None

class MetricDefinition(MetricDefinitionBase):
    id: int

    class Config:
        from_attributes = True

# Metric Value schemas
class TeamMetricValueInput(BaseModel):
    metric_slug: str
    side: MetricSide
    value: float

    @validator('value')
    def validate_value(cls, v, values):
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v

class TeamMetricValueBulk(BaseModel):
    """Bulk upsert of team metrics for a match"""
    values: List[TeamMetricValueInput]

class PlayerMetricValueInput(BaseModel):
    player_id: int
    metric_slug: str
    value: float

    @validator('value')
    def validate_value(cls, v):
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v

class PlayerMetricValueBulk(BaseModel):
    """Bulk upsert of player metrics for a match"""
    values: List[PlayerMetricValueInput]

class TeamMetricValueOutput(BaseModel):
    metric_slug: str
    metric_label: str
    side: MetricSide
    value: float
    unit: Optional[str] = None

class PlayerMetricValueOutput(BaseModel):
    player_id: int
    player_name: str
    metric_slug: str
    metric_label: str
    value: float
    unit: Optional[str] = None

# Analytics schemas
class KPIValue(BaseModel):
    metric_slug: str
    metric_label: str
    value: float
    unit: Optional[str] = None
    delta: Optional[float] = None  # vs previous period

class KPIResponse(BaseModel):
    kpis: List[KPIValue]

class TimeSeriesPoint(BaseModel):
    match_id: int
    match_date: date
    opponent_name: str
    value: float

class TimeSeriesResponse(BaseModel):
    metric_slug: str
    metric_label: str
    unit: Optional[str] = None
    data: List[TimeSeriesPoint]

class RadarPoint(BaseModel):
    metric_slug: str
    metric_label: str
    value_a: float
    value_b: float
    unit: Optional[str] = None

class RadarResponse(BaseModel):
    label_a: str
    label_b: str
    metrics: List[RadarPoint]

class LeaderboardEntry(BaseModel):
    player_id: int
    player_name: str
    value: float
    matches_played: int

class LeaderboardResponse(BaseModel):
    metric_slug: str
    metric_label: str
    unit: Optional[str] = None
    entries: List[LeaderboardEntry]
