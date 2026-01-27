from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models import Team
from app import schemas

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("", response_model=List[schemas.Team])
def list_teams(db: Session = Depends(get_db)):
    """List all teams"""
    teams = db.query(Team).order_by(Team.name).all()
    return teams

@router.post("", response_model=schemas.Team, status_code=201)
def create_team(team: schemas.TeamCreate, db: Session = Depends(get_db)):
    """Create a new team"""
    # Check for duplicate name
    existing = db.query(Team).filter_by(name=team.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team with this name already exists")

    db_team = Team(**team.model_dump())
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

@router.get("/{team_id}", response_model=schemas.Team)
def get_team(team_id: int, db: Session = Depends(get_db)):
    """Get team by ID"""
    team = db.query(Team).get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team
