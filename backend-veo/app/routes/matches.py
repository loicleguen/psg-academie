from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app import schemas
from app.db.session import get_db
from app.models import Match, MatchPlayerParticipation, Player, Season, Team
from app.schemas.summary import MatchSummaryResponse
from app.services.match_summary import MatchSummaryService

router = APIRouter(prefix="/matches", tags=["matches"])


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
