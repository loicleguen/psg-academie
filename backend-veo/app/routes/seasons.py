from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.db.session import get_db
from app.models import Season
from app import schemas
from backend_catapult.src.middleware.security import require_coach_or_admin
from backend_catapult.src.models.user import User
from fastapi import Depends

router = APIRouter(prefix="/seasons", tags=["seasons"])

@router.get("", response_model=List[schemas.Season])
def list_seasons(db: Session = Depends(get_db), current_user: User = Depends(require_coach_or_admin)):
    """List all seasons"""
    seasons = db.query(Season).order_by(Season.start_date.desc()).all()
    return seasons

@router.post("", response_model=schemas.Season, status_code=201)
def create_season(season: schemas.SeasonCreate, db: Session = Depends(get_db), current_user: User = Depends(require_coach_or_admin)):
    """Create a new season"""
    # Check for duplicate label
    existing = db.query(Season).filter_by(label=season.label).first()
    if existing:
        raise HTTPException(status_code=400, detail="Season with this label already exists")

    # Validate dates
    if season.end_date <= season.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    db_season = Season(**season.model_dump())
    db.add(db_season)
    db.commit()
    db.refresh(db_season)
    return db_season

@router.get("/{season_id}", response_model=schemas.Season)
def get_season(season_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_coach_or_admin)):
    """Get season by ID"""
    season = db.query(Season).get(season_id)
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    return season