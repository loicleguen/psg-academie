from datetime import date
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app import schemas
from app.db.session import get_db
from app.models import Match, MatchPlayerParticipation, Player, Season, Team
from app.schemas.summary import MatchSummaryResponse
from app.services.match_summary import MatchSummaryService

router = APIRouter(prefix="/matches", tags=["matches"])


def _normalize_whitespace(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _normalize_key(value: str) -> str:
    return _normalize_whitespace(value).lower()


def _split_player_name(full_name: str) -> Tuple[str, str]:
    normalized = _normalize_whitespace(full_name)
    if not normalized:
        return ("Joueur", "Inconnu")

    tokens = normalized.split(" ")
    if len(tokens) == 1:
        token = tokens[0].title()
        return (token, token)

    first_name = tokens[0].title()
    last_name = " ".join(tokens[1:]).title()
    return (first_name, last_name)


def _season_bounds_for_date(session_date: date) -> Tuple[str, date, date]:
    if session_date.month >= 7:
        start_year = session_date.year
        end_year = session_date.year + 1
    else:
        start_year = session_date.year - 1
        end_year = session_date.year

    label = f"{start_year}-{end_year}"
    return (label, date(start_year, 7, 1), date(end_year, 6, 30))


@router.get("", response_model=List[schemas.Match])
def list_matches(
    team_id: Optional[int] = Query(None),
    season_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    """List matches with optional filters"""
    query = db.query(Match)

    if team_id:
        query = query.filter(Match.team_id == team_id)
    if season_id:
        query = query.filter(Match.season_id == season_id)
    if from_date:
        query = query.filter(Match.date >= from_date)
    if to_date:
        query = query.filter(Match.date <= to_date)

    matches = query.order_by(Match.date.desc()).all()
    return matches


@router.post("", response_model=schemas.Match, status_code=201)
def create_match(match: schemas.MatchCreate, db: Session = Depends(get_db)):
    """Create a new match"""
    # Verify team exists
    team = db.query(Team).get(match.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Verify season exists
    season = db.query(Season).get(match.season_id)
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")

    db_match = Match(**match.model_dump())
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match


@router.post(
    "/bootstrap-from-catapult",
    response_model=schemas.MatchBootstrapFromCatapultResponse,
)
def bootstrap_match_from_catapult(
    payload: schemas.MatchBootstrapFromCatapultRequest, db: Session = Depends(get_db)
):
    """
    Bootstrap Veo entities from an existing Catapult session context.

    This endpoint avoids re-creating season/team/player references manually on the
    frontend by upserting:
    - season (derived from session date),
    - team (by name),
    - players (from full names),
    - match (linked to session date/title),
    - participations (missing players only, or full replace if requested).
    """
    session_title = _normalize_whitespace(payload.session_title)
    team_name = _normalize_whitespace(payload.team_name)
    if not session_title:
        raise HTTPException(status_code=400, detail="session_title is required")
    if not team_name:
        raise HTTPException(status_code=400, detail="team_name is required")

    season_label, season_start, season_end = _season_bounds_for_date(payload.session_date)

    created_season = False
    created_team = False
    created_match = False
    created_players = 0
    participations_created = 0

    season = db.query(Season).filter(Season.label == season_label).first()
    if not season:
        season = Season(label=season_label, start_date=season_start, end_date=season_end)
        db.add(season)
        db.flush()
        created_season = True

    team = db.query(Team).filter(func.lower(Team.name) == team_name.lower()).first()
    if not team:
        team = Team(name=team_name)
        db.add(team)
        db.flush()
        created_team = True

    opponent_name = _normalize_whitespace(payload.opponent_name or session_title)
    veo_title = _normalize_whitespace(payload.veo_title or session_title)

    match = (
        db.query(Match)
        .filter(
            Match.team_id == team.id,
            Match.date == payload.session_date,
            func.lower(Match.veo_title) == veo_title.lower(),
        )
        .first()
    )
    if not match:
        match = (
            db.query(Match)
            .filter(
                Match.team_id == team.id,
                Match.date == payload.session_date,
                func.lower(Match.opponent_name) == opponent_name.lower(),
            )
            .first()
        )

    if not match:
        match = Match(
            team_id=team.id,
            season_id=season.id,
            date=payload.session_date,
            opponent_name=opponent_name,
            is_home=payload.is_home,
            match_type=payload.match_type,
            competition=payload.competition,
            score_for=payload.score_for,
            score_against=payload.score_against,
            veo_title=veo_title,
            veo_url=payload.veo_url,
            veo_duration=payload.veo_duration,
            veo_camera=payload.veo_camera,
        )
        db.add(match)
        db.flush()
        created_match = True
    else:
        match.season_id = season.id
        if payload.opponent_name:
            match.opponent_name = opponent_name
        if payload.competition is not None:
            match.competition = payload.competition
        if payload.score_for is not None:
            match.score_for = payload.score_for
        if payload.score_against is not None:
            match.score_against = payload.score_against
        if payload.veo_title:
            match.veo_title = veo_title
        if payload.veo_url is not None:
            match.veo_url = payload.veo_url
        if payload.veo_duration is not None:
            match.veo_duration = payload.veo_duration
        if payload.veo_camera is not None:
            match.veo_camera = payload.veo_camera

    existing_players = db.query(Player).filter(Player.team_id == team.id).all()
    players_by_name: Dict[str, Player] = {
        _normalize_key(f"{player.first_name} {player.last_name}"): player
        for player in existing_players
    }

    resolved_players: List[Player] = []
    seen_player_keys = set()
    for raw_name in payload.player_names:
        normalized_name = _normalize_whitespace(raw_name)
        if not normalized_name:
            continue

        key = _normalize_key(normalized_name)
        if key in seen_player_keys:
            continue
        seen_player_keys.add(key)

        player = players_by_name.get(key)
        if not player:
            first_name, last_name = _split_player_name(normalized_name)
            player = Player(
                team_id=team.id,
                first_name=first_name,
                last_name=last_name,
                main_position="INCONNU",
                secondary_positions=None,
            )
            db.add(player)
            db.flush()
            players_by_name[key] = player
            created_players += 1
        resolved_players.append(player)

    if payload.replace_participations:
        db.query(MatchPlayerParticipation).filter(
            MatchPlayerParticipation.match_id == match.id
        ).delete()
        existing_participation_ids = set()
    else:
        existing_participation_ids = {
            row.player_id
            for row in db.query(MatchPlayerParticipation.player_id).filter(
                MatchPlayerParticipation.match_id == match.id
            )
        }

    for player in resolved_players:
        if player.id in existing_participation_ids:
            continue
        participation = MatchPlayerParticipation(
            match_id=match.id,
            player_id=player.id,
            is_starter=False,
            is_captain=False,
            minutes_played=None,
            position_played=player.main_position,
        )
        db.add(participation)
        participations_created += 1

    db.commit()

    return schemas.MatchBootstrapFromCatapultResponse(
        match_id=match.id,
        team_id=team.id,
        season_id=season.id,
        created_team=created_team,
        created_season=created_season,
        created_match=created_match,
        created_players=created_players,
        total_players=len(resolved_players),
        participations_created=participations_created,
    )


@router.get("/{match_id}", response_model=schemas.Match)
def get_match(match_id: int, db: Session = Depends(get_db)):
    """Get match by ID"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.patch("/{match_id}", response_model=schemas.Match)
def update_match(
    match_id: int, match_update: schemas.MatchUpdate, db: Session = Depends(get_db)
):
    """Update match information"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    update_data = match_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(match, field, value)

    db.commit()
    db.refresh(match)
    return match


@router.delete("/{match_id}", status_code=204)
def delete_match(match_id: int, db: Session = Depends(get_db)):
    """Delete a match"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    db.delete(match)
    db.commit()
    return None


# Participations endpoints
@router.get("/{match_id}/participations", response_model=List[schemas.Participation])
def get_match_participations(match_id: int, db: Session = Depends(get_db)):
    """Get all participations for a match"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    participations = (
        db.query(MatchPlayerParticipation)
        .filter(MatchPlayerParticipation.match_id == match_id)
        .all()
    )
    return participations


@router.put("/{match_id}/participations", response_model=List[schemas.Participation])
def update_match_participations(
    match_id: int, bulk: schemas.ParticipationBulk, db: Session = Depends(get_db)
):
    """Bulk update participations for a match"""
    match = db.query(Match).get(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Verify all players exist and belong to same team
    player_ids = [p.player_id for p in bulk.participations]
    players = db.query(Player).filter(Player.id.in_(player_ids)).all()

    if len(players) != len(player_ids):
        raise HTTPException(status_code=404, detail="One or more players not found")

    if any(p.team_id != match.team_id for p in players):
        raise HTTPException(
            status_code=400, detail="All players must belong to match team"
        )

    # Delete existing participations
    db.query(MatchPlayerParticipation).filter(
        MatchPlayerParticipation.match_id == match_id
    ).delete()

    # Create new participations
    new_participations = []
    for part in bulk.participations:
        db_part = MatchPlayerParticipation(match_id=match_id, **part.model_dump())
        db.add(db_part)
        new_participations.append(db_part)

    db.commit()

    # Refresh all
    for part in new_participations:
        db.refresh(part)

    return new_participations


@router.post("/{match_id}/duplicate-participations/{source_match_id}")
def duplicate_participations(
    match_id: int, source_match_id: int, db: Session = Depends(get_db)
):
    """Duplicate participations from another match"""
    match = db.query(Match).get(match_id)
    source_match = db.query(Match).get(source_match_id)

    if not match or not source_match:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.team_id != source_match.team_id:
        raise HTTPException(status_code=400, detail="Matches must be from same team")

    # Get source participations
    source_parts = (
        db.query(MatchPlayerParticipation)
        .filter(MatchPlayerParticipation.match_id == source_match_id)
        .all()
    )

    # Delete existing and create new
    db.query(MatchPlayerParticipation).filter(
        MatchPlayerParticipation.match_id == match_id
    ).delete()

    new_parts = []
    for src in source_parts:
        new_part = MatchPlayerParticipation(
            match_id=match_id,
            player_id=src.player_id,
            is_starter=src.is_starter,
            is_captain=src.is_captain,
            minutes_played=None,  # Don't copy minutes
            position_played=src.position_played,
        )
        db.add(new_part)
        new_parts.append(new_part)

    db.commit()
    return {
        "message": f"Duplicated {len(new_parts)} participations",
        "count": len(new_parts),
    }


@router.get("/{match_id}/summary", response_model=MatchSummaryResponse)
def get_match_summary(match_id: int, db: Session = Depends(get_db)):
    """
    Get a complete, Excel-like summary for a match.

    This endpoint returns a single payload designed for coach usage and frontend
    simplicity (one request = match + participations + team metrics + player grid).

    Notes:
        - Raw values only (no derived computations).
        - Derived KPIs are computed via /analytics endpoints.
        - Designed as a stable contract for future CSV/Excel export.

    Args:
        match_id: Match identifier.
        db: SQLAlchemy session dependency.

    Returns:
        A MatchSummaryResponse payload.

    Raises:
        HTTPException: 404 if the match does not exist.
    """
    service = MatchSummaryService(db)

    try:
        return service.get_match_summary(match_id=match_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Match not found")
