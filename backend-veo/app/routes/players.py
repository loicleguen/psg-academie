import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

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
from app.security import require_coach_or_admin, get_current_user
from common.user import User

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
    raw = unicodedata.normalize("NFD", (value or "").strip().lower())
    without_accents = "".join(char for char in raw if unicodedata.category(char) != "Mn")
    compact = re.sub(r"[^a-z0-9]+", " ", without_accents)
    return " ".join(compact.split())


def _normalize_player_name_for_storage(value: str) -> str:
    return " ".join((value or "").split()).strip().upper()


def _name_tokens(value: str) -> Set[str]:
    normalized = _normalize_player_name(value)
    if not normalized:
        return set()
    return set(normalized.split(" "))


def _candidate_player_names(player: Player) -> Set[str]:
    first = _normalize_player_name(player.first_name)
    last = _normalize_player_name(player.last_name)
    full = _normalize_player_name(f"{player.first_name} {player.last_name}")

    names = {full}
    if first and last:
        names.add(_normalize_player_name(f"{last} {first}"))
    if first:
        names.add(first)
    if last:
        names.add(last)
    return names


def _name_match_score(input_name: str, player: Player) -> int:
    input_normalized = _normalize_player_name(input_name)
    if not input_normalized:
        return 0

    input_tokens = _name_tokens(input_normalized)
    candidate_names = _candidate_player_names(player)

    if input_normalized in candidate_names:
        return 100

    best_score = 0
    for candidate in candidate_names:
        candidate_tokens = _name_tokens(candidate)
        if not candidate_tokens:
            continue

        if input_tokens == candidate_tokens:
            best_score = max(best_score, 90)
            continue

        if input_tokens and (input_tokens.issubset(candidate_tokens) or candidate_tokens.issubset(input_tokens)):
            best_score = max(best_score, 80)
            continue

        overlap = len(input_tokens & candidate_tokens)
        union = len(input_tokens | candidate_tokens)
        if union > 0 and (overlap / union) >= 0.67:
            best_score = max(best_score, 70)

    return best_score


def _count_matches_for_player(db: Session, player_id: int) -> int:
    return (
        db.query(MatchPlayerParticipation.id)
        .filter(MatchPlayerParticipation.player_id == player_id)
        .count()
    )


def _count_metric_matches_for_player(db: Session, player_id: int) -> int:
    return (
        db.query(PlayerMatchMetricValue.match_id)
        .filter(PlayerMatchMetricValue.player_id == player_id)
        .distinct()
        .count()
    )


@router.get("", response_model=List[schemas.Player])
def list_players(
    team_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
    """List players, optionally filtered by team"""
    query = db.query(Player)
    if team_id:
        query = query.filter(Player.team_id == team_id)

    players = query.order_by(Player.last_name, Player.first_name).all()
    return players

@router.post("", response_model=schemas.Player, status_code=201)
def create_player(
    player: schemas.PlayerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
    """Create a new player"""
    # Verify team exists
    team = db.query(Team).get(player.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    payload = player.model_dump()
    payload["first_name"] = _normalize_player_name_for_storage(payload.get("first_name"))
    payload["last_name"] = _normalize_player_name_for_storage(payload.get("last_name"))
    db_player = Player(**payload)
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

    candidates: List[Tuple[Player, int]] = []
    for player in db.query(Player).all():
        score = _name_match_score(normalized_name, player)
        if score > 0:
            candidates.append((player, score))

    if not candidates:
        raise HTTPException(status_code=404, detail="Player not found in Veo database")

    selected_player, _ = max(
        candidates,
        key=lambda item: (
            item[1],
            _count_metric_matches_for_player(db, item[0].id),
            _count_matches_for_player(db, item[0].id),
            item[0].id,
        ),
    )

    participation_match_rows = (
        db.query(Match.id)
        .join(MatchPlayerParticipation, MatchPlayerParticipation.match_id == Match.id)
        .filter(MatchPlayerParticipation.player_id == selected_player.id)
        .distinct()
        .all()
    )

    metric_match_rows = (
        db.query(PlayerMatchMetricValue.match_id)
        .filter(PlayerMatchMetricValue.player_id == selected_player.id)
        .distinct()
        .all()
    )

    match_ids = sorted(
        {
            match_id
            for (match_id,) in participation_match_rows + metric_match_rows
            if match_id is not None
        }
    )
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
def get_player(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
    """Get player by ID"""
    player = db.query(Player).get(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@router.patch("/{player_id}", response_model=schemas.Player)
def update_player(
    player_id: int,
    player_update: schemas.PlayerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
    """Update player information"""
    player = db.query(Player).get(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Update only provided fields
    update_data = player_update.model_dump(exclude_unset=True)
    if "first_name" in update_data and update_data["first_name"] is not None:
        update_data["first_name"] = _normalize_player_name_for_storage(update_data["first_name"])
    if "last_name" in update_data and update_data["last_name"] is not None:
        update_data["last_name"] = _normalize_player_name_for_storage(update_data["last_name"])
    for field, value in update_data.items():
        setattr(player, field, value)

    db.commit()
    db.refresh(player)
    return player

@router.delete("/{player_id}", status_code=204)
def delete_player(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
    """Delete a player"""
    player = db.query(Player).get(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    db.delete(player)
    db.commit()
    return None