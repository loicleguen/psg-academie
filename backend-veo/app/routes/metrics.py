from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, List, Optional
from app.db.session import get_db
from app.models import (
    MetricDefinition, TeamMatchMetricValue, PlayerMatchMetricValue,
    Match, Player, MetricScope, MetricCategory, MetricSide
)
from app import schemas
from app.security import require_coach_or_admin, get_current_user
from common.user import User

router = APIRouter(prefix="/metrics", tags=["metrics"])

CATEGORY_LABELS_FR: Dict[MetricCategory, str] = {
    MetricCategory.GENERAL: "General",
    MetricCategory.EVENTS: "Evenements",
    MetricCategory.POSSESSION: "Possession",
    MetricCategory.PASSES: "Passes",
    MetricCategory.COMBINATIONS: "Combinaisons",
}

CATEGORY_SORT_INDEX: Dict[MetricCategory, int] = {
    MetricCategory.GENERAL: 1,
    MetricCategory.EVENTS: 2,
    MetricCategory.POSSESSION: 3,
    MetricCategory.PASSES: 4,
    MetricCategory.COMBINATIONS: 5,
}


def _build_metric_catalog_groups(
    metrics: List[MetricDefinition], scope: MetricScope
) -> List[schemas.MetricCatalogGroup]:
    grouped: Dict[MetricCategory, List[schemas.MetricCatalogItem]] = {}

    for metric in metrics:
        if metric.scope != scope:
            continue

        grouped.setdefault(metric.category, []).append(
            schemas.MetricCatalogItem(
                slug=metric.slug,
                label_fr=metric.label_fr,
                description_fr=metric.description_fr,
                datatype=metric.datatype,
                unit=metric.unit,
                side=metric.side,
                is_derived=metric.is_derived,
                formula=metric.formula,
            )
        )

    groups: List[schemas.MetricCatalogGroup] = []
    for category, items in grouped.items():
        groups.append(
            schemas.MetricCatalogGroup(
                category=category,
                category_label_fr=CATEGORY_LABELS_FR.get(category, category.value),
                metrics=sorted(items, key=lambda item: item.slug),
            )
        )

    return sorted(groups, key=lambda group: CATEGORY_SORT_INDEX.get(group.category, 99))

@router.get("", response_model=List[schemas.MetricDefinition])
def list_metrics(
    scope: Optional[MetricScope] = Query(None),
    category: Optional[MetricCategory] = Query(None),
    is_derived: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
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


@router.get("/entry-schema", response_model=schemas.MetricsEntrySchemaResponse)
def get_entry_schema(
    include_derived: bool = Query(
        False,
        description="Include derived metrics in catalog (default: raw metrics only)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
    """
    Return a UI-oriented schema for manual data entry.

    This endpoint centralizes:
    - match-level fields (metadata + VEO context),
    - participation fields,
    - team and player metrics grouped by category.

    It is designed as the contract for frontend forms and future smart paste.
    """
    query = db.query(MetricDefinition)
    if not include_derived:
        query = query.filter(MetricDefinition.is_derived.is_(False))

    metrics = query.order_by(
        MetricDefinition.scope, MetricDefinition.category, MetricDefinition.slug
    ).all()

    match_fields = [
        schemas.EntryFieldDescriptor(
            key="date",
            label_fr="Date du match",
            input_type="date",
            required=True,
        ),
        schemas.EntryFieldDescriptor(
            key="opponent_name",
            label_fr="Adversaire",
            input_type="text",
            required=True,
        ),
        schemas.EntryFieldDescriptor(
            key="is_home",
            label_fr="Match a domicile",
            input_type="boolean",
            required=True,
        ),
        schemas.EntryFieldDescriptor(
            key="match_type",
            label_fr="Type de match",
            input_type="select",
            required=True,
            help_text="LEAGUE, CUP, FRIENDLY, TOURNAMENT",
        ),
        schemas.EntryFieldDescriptor(
            key="competition",
            label_fr="Competition",
            input_type="text",
        ),
        schemas.EntryFieldDescriptor(
            key="score_for",
            label_fr="Buts marques",
            input_type="int",
        ),
        schemas.EntryFieldDescriptor(
            key="score_against",
            label_fr="Buts encaisses",
            input_type="int",
        ),
        schemas.EntryFieldDescriptor(
            key="veo_title",
            label_fr="Titre Veo",
            input_type="text",
        ),
        schemas.EntryFieldDescriptor(
            key="veo_url",
            label_fr="URL Veo",
            input_type="url",
        ),
        schemas.EntryFieldDescriptor(
            key="veo_duration",
            label_fr="Duree video",
            input_type="int",
            unit="seconds",
        ),
        schemas.EntryFieldDescriptor(
            key="veo_camera",
            label_fr="Camera Veo",
            input_type="text",
        ),
    ]

    participation_fields = [
        schemas.EntryFieldDescriptor(
            key="player_id",
            label_fr="Joueur",
            input_type="select",
            required=True,
        ),
        schemas.EntryFieldDescriptor(
            key="is_starter",
            label_fr="Titulaire",
            input_type="boolean",
        ),
        schemas.EntryFieldDescriptor(
            key="is_captain",
            label_fr="Capitaine",
            input_type="boolean",
        ),
        schemas.EntryFieldDescriptor(
            key="minutes_played",
            label_fr="Minutes jouees",
            input_type="int",
        ),
        schemas.EntryFieldDescriptor(
            key="position_played",
            label_fr="Poste joue",
            input_type="text",
        ),
    ]

    return schemas.MetricsEntrySchemaResponse(
        match_fields=match_fields,
        participation_fields=participation_fields,
        team_metrics_by_category=_build_metric_catalog_groups(metrics, MetricScope.TEAM),
        player_metrics_by_category=_build_metric_catalog_groups(
            metrics, MetricScope.PLAYER
        ),
    )

@router.get("/{metric_id}", response_model=schemas.MetricDefinition)
def get_metric(
    metric_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
    """Get metric definition by ID"""
    metric = db.query(MetricDefinition).get(metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric

# Team metrics endpoints
@router.get("/matches/{match_id}/team-metrics", response_model=List[schemas.TeamMetricValueOutput])
def get_team_metrics(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
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
def get_player_metrics(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
):
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_coach_or_admin),
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
