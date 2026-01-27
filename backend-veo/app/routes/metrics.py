from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from app.db.session import get_db
from app.models import (
    MetricDefinition, TeamMatchMetricValue, PlayerMatchMetricValue,
    Match, Player, MetricScope, MetricCategory, MetricSide
)
from app import schemas

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("", response_model=List[schemas.MetricDefinition])
def list_metrics(
    scope: Optional[MetricScope] = Query(None),
    category: Optional[MetricCategory] = Query(None),
    is_derived: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """List metric definitions with optional filters"""
    query = db.query(MetricDefinition)

    if scope:
        query = query.filter(MetricDefinition.scope == scope)
    if category:
        query = query.filter(MetricDefinition.category == category)
    if is_derived is not None:
        query = query.filter(MetricDefinition.is_derived == is_derived)

    metrics = query.order_by(MetricDefinition.category, MetricDefinition.slug).all()
    return metrics

@router.get("/{metric_id}", response_model=schemas.MetricDefinition)
def get_metric(metric_id: int, db: Session = Depends(get_db)):
    """Get metric definition by ID"""
    metric = db.query(MetricDefinition).get(metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric

# Team metrics endpoints
@router.get("/matches/{match_id}/team-metrics", response_model=List[schemas.TeamMetricValueOutput])
def get_team_metrics(match_id: int, db: Session = Depends(get_db)):
    """Get all team metrics for a match"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    values = db.query(TeamMatchMetricValue, MetricDefinition).join(
        MetricDefinition, TeamMatchMetricValue.metric_id == MetricDefinition.id
    ).filter(
        TeamMatchMetricValue.match_id == match_id
    ).all()

    return [
        schemas.TeamMetricValueOutput(
            metric_slug=metric.slug,
            metric_label=metric.label_fr,
            side=value.side,
            value=value.value_number,
            unit=metric.unit
        )
        for value, metric in values
    ]

@router.put("/matches/{match_id}/team-metrics")
def update_team_metrics(
    match_id: int,
    bulk: schemas.TeamMetricValueBulk,
    db: Session = Depends(get_db)
):
    """Bulk upsert team metrics for a match"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    results = {"created": 0, "updated": 0, "errors": []}

    for value_input in bulk.values:
        # Get metric definition
        metric = db.query(MetricDefinition).filter_by(slug=value_input.metric_slug).first()
        if not metric:
            results["errors"].append(f"Metric {value_input.metric_slug} not found")
            continue

        # Validate not storing derived metrics
        if metric.is_derived:
            results["errors"].append(f"Cannot store derived metric {value_input.metric_slug}")
            continue

        # Validate scope
        if metric.scope != MetricScope.TEAM:
            results["errors"].append(f"Metric {value_input.metric_slug} is not a team metric")
            continue

        # Validate percentage range
        if metric.datatype.value == "PERCENT" and not (0 <= value_input.value <= 100):
            results["errors"].append(f"Percentage value must be between 0 and 100")
            continue

        # Upsert value
        existing = db.query(TeamMatchMetricValue).filter(
            and_(
                TeamMatchMetricValue.match_id == match_id,
                TeamMatchMetricValue.metric_id == metric.id,
                TeamMatchMetricValue.side == value_input.side
            )
        ).first()

        if existing:
            existing.value_number = value_input.value
            results["updated"] += 1
        else:
            new_value = TeamMatchMetricValue(
                match_id=match_id,
                metric_id=metric.id,
                side=value_input.side,
                value_number=value_input.value
            )
            db.add(new_value)
            results["created"] += 1

    db.commit()
    return results

# Player metrics endpoints
@router.get("/matches/{match_id}/player-metrics", response_model=List[schemas.PlayerMetricValueOutput])
def get_player_metrics(match_id: int, db: Session = Depends(get_db)):
    """Get all player metrics for a match"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    values = db.query(PlayerMatchMetricValue, MetricDefinition, Player).join(
        MetricDefinition, PlayerMatchMetricValue.metric_id == MetricDefinition.id
    ).join(
        Player, PlayerMatchMetricValue.player_id == Player.id
    ).filter(
        PlayerMatchMetricValue.match_id == match_id
    ).all()

    return [
        schemas.PlayerMetricValueOutput(
            player_id=value.player_id,
            player_name=f"{player.first_name} {player.last_name}",
            metric_slug=metric.slug,
            metric_label=metric.label_fr,
            value=value.value_number,
            unit=metric.unit
        )
        for value, metric, player in values
    ]

@router.put("/matches/{match_id}/player-metrics")
def update_player_metrics(
    match_id: int,
    bulk: schemas.PlayerMetricValueBulk,
    db: Session = Depends(get_db)
):
    """Bulk upsert player metrics for a match"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    results = {"created": 0, "updated": 0, "errors": []}

    for value_input in bulk.values:
        # Get metric definition
        metric = db.query(MetricDefinition).filter_by(slug=value_input.metric_slug).first()
        if not metric:
            results["errors"].append(f"Metric {value_input.metric_slug} not found")
            continue

        # Validate not storing derived metrics
        if metric.is_derived:
            results["errors"].append(f"Cannot store derived metric {value_input.metric_slug}")
            continue

        # Validate scope
        if metric.scope != MetricScope.PLAYER:
            results["errors"].append(f"Metric {value_input.metric_slug} is not a player metric")
            continue

        # Verify player exists
        player = db.query(Player).get(value_input.player_id)
        if not player:
            results["errors"].append(f"Player {value_input.player_id} not found")
            continue

        # Validate percentage range
        if metric.datatype.value == "PERCENT" and not (0 <= value_input.value <= 100):
            results["errors"].append(f"Percentage value must be between 0 and 100")
            continue

        # Upsert value
        existing = db.query(PlayerMatchMetricValue).filter(
            and_(
                PlayerMatchMetricValue.match_id == match_id,
                PlayerMatchMetricValue.player_id == value_input.player_id,
                PlayerMatchMetricValue.metric_id == metric.id
            )
        ).first()

        if existing:
            existing.value_number = value_input.value
            results["updated"] += 1
        else:
            new_value = PlayerMatchMetricValue(
                match_id=match_id,
                player_id=value_input.player_id,
                metric_id=metric.id,
                value_number=value_input.value
            )
            db.add(new_value)
            results["created"] += 1

    db.commit()
    return results
