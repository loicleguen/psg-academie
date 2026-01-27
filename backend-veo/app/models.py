from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey, Enum, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum

# Enums
class MetricScope(str, enum.Enum):
    TEAM = "TEAM"
    PLAYER = "PLAYER"

class MetricCategory(str, enum.Enum):
    POSSESSION = "POSSESSION"
    PASSES = "PASSES"
    EVENTS = "EVENTS"
    COMBINATIONS = "COMBINATIONS"
    GENERAL = "GENERAL"

class MetricDataType(str, enum.Enum):
    INT = "INT"
    FLOAT = "FLOAT"
    PERCENT = "PERCENT"

class MetricSide(str, enum.Enum):
    OWN = "OWN"
    OPPONENT = "OPPONENT"
    NONE = "NONE"

class MatchType(str, enum.Enum):
    LEAGUE = "LEAGUE"
    CUP = "CUP"
    FRIENDLY = "FRIENDLY"
    TOURNAMENT = "TOURNAMENT"

# Models
class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False, unique=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    matches = relationship("Match", back_populates="season")

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)

    players = relationship("Player", back_populates="team")
    matches = relationship("Match", back_populates="team")

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    main_position = Column(String(50), nullable=False)
    secondary_positions = Column(String(200), nullable=True)  # comma-separated

    team = relationship("Team", back_populates="players")
    participations = relationship("MatchPlayerParticipation", back_populates="player")
    metric_values = relationship("PlayerMatchMetricValue", back_populates="player")

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    date = Column(Date, nullable=False)
    opponent_name = Column(String(200), nullable=False)
    is_home = Column(Boolean, default=True)
    match_type = Column(Enum(MatchType), default=MatchType.LEAGUE)
    competition = Column(String(200), nullable=True)
    score_for = Column(Integer, nullable=True)
    score_against = Column(Integer, nullable=True)

    # Veo metadata
    veo_title = Column(String(300), nullable=True)
    veo_url = Column(String(500), nullable=True)
    veo_duration = Column(Integer, nullable=True)  # seconds
    veo_camera = Column(String(100), nullable=True)

    team = relationship("Team", back_populates="matches")
    season = relationship("Season", back_populates="matches")
    participations = relationship("MatchPlayerParticipation", back_populates="match", cascade="all, delete-orphan")
    team_metrics = relationship("TeamMatchMetricValue", back_populates="match", cascade="all, delete-orphan")
    player_metrics = relationship("PlayerMatchMetricValue", back_populates="match", cascade="all, delete-orphan")

class MatchPlayerParticipation(Base):
    __tablename__ = "match_player_participations"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    is_starter = Column(Boolean, default=False)
    is_captain = Column(Boolean, default=False)
    minutes_played = Column(Integer, nullable=True)
    position_played = Column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint('match_id', 'player_id', name='uq_match_player'),
    )

    match = relationship("Match", back_populates="participations")
    player = relationship("Player", back_populates="participations")

class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    label_fr = Column(String(200), nullable=False)
    description_fr = Column(Text, nullable=True)
    scope = Column(Enum(MetricScope), nullable=False)
    category = Column(Enum(MetricCategory), nullable=False)
    datatype = Column(Enum(MetricDataType), default=MetricDataType.INT)
    unit = Column(String(50), nullable=True)
    side = Column(Enum(MetricSide), default=MetricSide.NONE)
    is_derived = Column(Boolean, default=False)
    formula = Column(Text, nullable=True)

    team_values = relationship("TeamMatchMetricValue", back_populates="metric")
    player_values = relationship("PlayerMatchMetricValue", back_populates="metric")

class TeamMatchMetricValue(Base):
    __tablename__ = "team_match_metric_values"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("metric_definitions.id"), nullable=False)
    side = Column(Enum(MetricSide), nullable=False)
    value_number = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('match_id', 'metric_id', 'side', name='uq_match_metric_side'),
    )

    match = relationship("Match", back_populates="team_metrics")
    metric = relationship("MetricDefinition", back_populates="team_values")

class PlayerMatchMetricValue(Base):
    __tablename__ = "player_match_metric_values"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("metric_definitions.id"), nullable=False)
    value_number = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint('match_id', 'player_id', 'metric_id', name='uq_match_player_metric'),
    )

    match = relationship("Match", back_populates="player_metrics")
    player = relationship("Player", back_populates="metric_values")
    metric = relationship("MetricDefinition", back_populates="player_values")
