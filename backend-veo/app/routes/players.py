from typing import Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    Match,
    MatchPlayerParticipation,
    MetricDefinition,
    MetricScope,
    Player,
    PlayerMatchMetricValue,
    Team,
)
from app import schemas

router = APIRouter(prefix="/players", tags=["players"])


PLAYER_PROFILE_METRIC_SLUGS = [
    "player_goal_assists",
    "player_shots",
    "player_shots_on_target",
    "player_goals",
    "player_duels_won",
    "player_fouls_committed",
    "player_cards",
    "player_offsides",
    "player_dribbles_won",
    "player_tackles_won",
    "player_recoveries",
    "player_ball_losses",
]


def _normalize_player_name(value: str) -> str:
    return " ".join((value or "").split()).strip().lower()


def _candidate_player_names(player: Player) -> Set[str]:
    first = _normalize_player_name(player.first_name)
    last = _normalize_player_name(player.last_name)
    full = _normalize_player_name(f"{player.first_name} {player.last_name}")

    names = {full}
    if first and last:
        names.add(_normalize_player_name(f"{last} {first}"))
    return names


def _count_matches_for_player(db: Session, player_id: int) -> int:
    return (
        db.query(MatchPlayerParticipation.id)
        .filter(MatchPlayerParticipation.player_id == player_id)
        .count()
    )


@router.get("", response_model=List[schemas.Player])
def list_players(
    team_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """List players, optionally filtered by team"""
    query = db.query(Player)
    if team_id:
        query = query.filter(Player.team_id == team_id)

    players = query.order_by(Player.last_name, Player.first_name).all()
    return players

@router.post("", response_model=schemas.Player, status_code=201)
def create_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    """Create a new player"""
    # Verify team exists
    team = db.query(Team).get(player.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    db_player = Player(**player.model_dump())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player


@router.get(
    "/by-name/{player_name}/metrics-summary",
    response_model=schemas.PlayerMetricsSummaryResponse,
)
def get_player_metrics_summary_by_name(
    player_name: str,
    db: Session = Depends(get_db),
):
    """
    Aggregate tracked Veo player metrics over all available Veo sessions.

    Name matching is case-insensitive and accepts either "First Last" or "Last First".
    """
    normalized_name = _normalize_player_name(player_name)
    if not normalized_name:
        raise HTTPException(status_code=400, detail="player_name is required")

    candidates = [
        player
        for player in db.query(Player).all()
        if normalized_name in _candidate_player_names(player)
    ]
    if not candidates:
        raise HTTPException(status_code=404, detail="Player not found in Veo database")

    selected_player = max(
        candidates,
        key=lambda player: (
            _count_matches_for_player(db, player.id),
            player.id,
        ),
    )

    match_rows = (
        db.query(Match.id)
        .join(MatchPlayerParticipation, MatchPlayerParticipation.match_id == Match.id)
        .filter(MatchPlayerParticipation.player_id == selected_player.id)
        .distinct()
        .all()
    )
    match_ids = [match_id for (match_id,) in match_rows]
    sessions_count = len(match_ids)

    metric_defs = (
        db.query(MetricDefinition)
        .filter(
            and_(
                MetricDefinition.scope == MetricScope.PLAYER,
                MetricDefinition.is_derived.is_(False),
                MetricDefinition.slug.in_(PLAYER_PROFILE_METRIC_SLUGS),
            )
        )
        .all()
    )
    metric_by_slug: Dict[str, MetricDefinition] = {metric.slug: metric for metric in metric_defs}

    totals_by_metric_id: Dict[int, float] = {}
    metric_ids = [metric.id for metric in metric_defs]
    if match_ids and metric_ids:
        metric_totals = (
            db.query(
                PlayerMatchMetricValue.metric_id,
                func.sum(PlayerMatchMetricValue.value_number),
            )
            .filter(
                and_(
                    PlayerMatchMetricValue.player_id == selected_player.id,
                    PlayerMatchMetricValue.match_id.in_(match_ids),
                    PlayerMatchMetricValue.metric_id.in_(metric_ids),
                )
            )
            .group_by(PlayerMatchMetricValue.metric_id)
            .all()
        )
        totals_by_metric_id = {
            metric_id: float(total or 0.0) for metric_id, total in metric_totals
        }

    metrics = []
    for slug in PLAYER_PROFILE_METRIC_SLUGS:
        metric = metric_by_slug.get(slug)
        if not metric:
            continue

        metrics.append(
            schemas.PlayerMetricAggregate(
                slug=slug,
                label_fr=metric.label_fr,
                value=round(
                    (totals_by_metric_id.get(metric.id, 0.0) / sessions_count)
                    if sessions_count > 0
                    else 0.0,
                    2,
                ),
                unit=metric.unit,
            )
        )

    return schemas.PlayerMetricsSummaryResponse(
        player_id=selected_player.id,
        player_name=f"{selected_player.first_name} {selected_player.last_name}",
        team_id=selected_player.team_id,
        sessions_count=sessions_count,
        metrics=metrics,
    )


@router.get("/{player_id}", response_model=schemas.Player)
def get_player(player_id: int, db: Session = Depends(get_db)):
    """Get player by ID"""
    player = db.query(Player).get(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@router.patch("/{player_id}", response_model=schemas.Player)
def update_player(
    player_id: int,
    player_update: schemas.PlayerUpdate,
    db: Session = Depends(get_db)
):
    """Update player information"""
    player = db.query(Player).get(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Update only provided fields
    update_data = player_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(player, field, value)

    db.commit()
    db.refresh(player)
    return player

@router.delete("/{player_id}", status_code=204)
def delete_player(player_id: int, db: Session = Depends(get_db)):
    """Delete a player"""
    player = db.query(Player).get(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    db.delete(player)
    db.commit()
    return None
