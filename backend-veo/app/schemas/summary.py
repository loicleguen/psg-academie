"""
Match summary schemas.

This module defines the Pydantic schemas used by the
`GET /matches/{match_id}/summary` endpoint.

The goal of this payload is to provide a **single, stable, Excel-like view**
of a match, intended to:
- replace manual Excel spreadsheets used by coaches,
- minimize frontend API calls (one request = full match context),
- serve as a foundation for future CSV / Excel exports.

The summary payload intentionally contains **raw values only**:
- no derived metrics,
- no analytics computations.

Derived KPIs remain exposed exclusively through the `/analytics` endpoints.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models import MetricSide


# =============================================================================
# Core blocks
# =============================================================================

class MatchSummaryMatch(BaseModel):
    """
    Minimal match representation for the match summary payload.

    This object aggregates all match-level information required by the frontend
    and by coaches, including optional VEO metadata.

    It is intentionally kept flat and explicit to ensure frontend stability
    and easy serialization for exports.
    """

    id: int
    team_id: int
    season_id: int

    date: date
    opponent_name: str
    is_home: bool
    match_type: str
    competition: Optional[str] = None

    score_for: Optional[int] = None
    score_against: Optional[int] = None

    # VEO metadata
    veo_title: Optional[str] = None
    veo_url: Optional[str] = None
    veo_duration: Optional[int] = Field(
        default=None,
        description="Video duration in seconds."
    )
    veo_camera: Optional[str] = None


class ParticipationWithPlayer(BaseModel):
    """
    Participation row enriched with player identity.

    This schema merges:
    - participation data (minutes played, captain, starter, etc.),
    - essential player identity fields.

    It is optimized for coach readability and avoids requiring
    additional player lookups on the frontend.
    """

    player_id: int
    player_name: str

    # Optional player info (useful for UI display)
    main_position: Optional[str] = None

    # Participation fields
    is_starter: bool = False
    is_captain: bool = False
    minutes_played: Optional[int] = None
    position_played: Optional[str] = None


class TeamMetricCell(BaseModel):
    """
    A single raw team metric value.

    This represents one metric value for a given match and side
    (OWN or OPPONENT), without any derived computation.
    """

    metric_slug: str
    metric_label: str
    side: MetricSide
    value: float
    unit: Optional[str] = None


class TeamMetricsBlock(BaseModel):
    """
    Container for team metrics split by side.

    Metrics are explicitly separated into OWN and OPPONENT
    to improve readability and frontend rendering.

    Example:
        {
            "OWN": [...],
            "OPPONENT": [...]
        }
    """

    OWN: List[TeamMetricCell] = Field(default_factory=list)
    OPPONENT: List[TeamMetricCell] = Field(default_factory=list)


# =============================================================================
# Player metrics grid (Excel-like)
# =============================================================================

class PlayerGridPlayer(BaseModel):
    """
    A player row definition for the player metrics grid.

    This object defines the identity of a row in the Excel-like grid.
    """

    id: int
    name: str
    main_position: Optional[str] = None


class PlayerGridColumn(BaseModel):
    """
    A metric column definition for the player metrics grid.

    Columns describe the structure of the grid and allow the frontend
    to render headers, units, and optional groupings.
    """

    slug: str
    label: str
    unit: Optional[str] = None
    category: Optional[str] = None


class PlayerMetricsGrid(BaseModel):
    """
    Excel-like grid structure for player metrics.

    This structure is designed for direct table rendering and export.

    Structure:
        - players: list of rows (players),
        - columns: list of metric columns,
        - values: mapping of player_id -> metric_slug -> raw value.

    Notes:
        - player IDs are represented as strings in `values` to ensure
          JSON key stability across clients.
        - Missing metrics are represented as null values.
    """

    players: List[PlayerGridPlayer]
    columns: List[PlayerGridColumn]
    values: Dict[str, Dict[str, Optional[float]]]


# =============================================================================
# Full response
# =============================================================================

class MatchSummaryResponse(BaseModel):
    """
    Full match summary response.

    This is the top-level schema returned by the match summary endpoint.
    It contains everything required to render a complete match view
    without additional API calls.
    """

    match: MatchSummaryMatch
    participations: List[ParticipationWithPlayer]
    team_metrics: TeamMetricsBlock
    player_metrics: PlayerMetricsGrid
