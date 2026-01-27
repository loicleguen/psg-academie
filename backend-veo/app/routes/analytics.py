from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.db.session import get_db
from app.services.analytics import AnalyticsService
from app import schemas

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/team/kpis", response_model=schemas.KPIResponse)
def get_team_kpis(
    team_id: int = Query(..., description="Team ID"),
    metrics: str = Query(..., description="Comma-separated metric slugs"),
    season_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    compute_delta: bool = Query(False, description="Compute delta vs previous period"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated KPIs for a team.

    Example: /analytics/team/kpis?team_id=1&metrics=team_possession_pct,team_goals_scored,team_conversion_rate
    """
    metric_slugs = [s.strip() for s in metrics.split(",")]

    analytics = AnalyticsService(db)
    kpis = analytics.get_team_kpis(
        team_id=team_id,
        metric_slugs=metric_slugs,
        season_id=season_id,
        date_from=from_date,
        date_to=to_date,
        compute_delta=compute_delta
    )

    return schemas.KPIResponse(kpis=kpis)

@router.get("/team/timeseries", response_model=schemas.TimeSeriesResponse)
def get_team_timeseries(
    team_id: int = Query(..., description="Team ID"),
    metric: str = Query(..., description="Metric slug"),
    last_n: int = Query(10, description="Number of recent matches"),
    db: Session = Depends(get_db)
):
    """
    Get time series data for a team metric over last N matches.

    Example: /analytics/team/timeseries?team_id=1&metric=team_possession_pct&last_n=10
    """
    analytics = AnalyticsService(db)
    result = analytics.get_team_timeseries(
        team_id=team_id,
        metric_slug=metric,
        last_n=last_n
    )

    return result

@router.get("/team/radar", response_model=schemas.RadarResponse)
def get_team_radar(
    team_id: int = Query(..., description="Team ID"),
    metrics: str = Query(..., description="Comma-separated metric slugs (max 6 recommended)"),
    fromA: date = Query(..., description="Period A start date"),
    toA: date = Query(..., description="Period A end date"),
    fromB: date = Query(..., description="Period B start date"),
    toB: date = Query(..., description="Period B end date"),
    db: Session = Depends(get_db)
):
    """
    Compare two time periods on multiple metrics (for radar chart).

    Example: /analytics/team/radar?team_id=1&metrics=team_possession_pct,team_shots,team_goals_scored
             &fromA=2024-01-01&toA=2024-03-31&fromB=2024-04-01&toB=2024-06-30
    """
    metric_slugs = [s.strip() for s in metrics.split(",")]

    if len(metric_slugs) > 8:
        raise HTTPException(status_code=400, detail="Maximum 8 metrics allowed for radar chart")

    analytics = AnalyticsService(db)
    result = analytics.get_team_radar(
        team_id=team_id,
        metric_slugs=metric_slugs,
        date_from_a=fromA,
        date_to_a=toA,
        date_from_b=fromB,
        date_to_b=toB
    )

    return result

@router.get("/players/leaderboard", response_model=schemas.LeaderboardResponse)
def get_player_leaderboard(
    team_id: int = Query(..., description="Team ID"),
    metric: str = Query(..., description="Player metric slug"),
    season_id: Optional[int] = Query(None),
    top_n: int = Query(10, description="Number of top players"),
    db: Session = Depends(get_db)
):
    """
    Get top players leaderboard for a metric.

    Example: /analytics/players/leaderboard?team_id=1&metric=player_goals&top_n=10
    """
    analytics = AnalyticsService(db)
    result = analytics.get_player_leaderboard(
        team_id=team_id,
        metric_slug=metric,
        season_id=season_id,
        top_n=top_n
    )

    return result
