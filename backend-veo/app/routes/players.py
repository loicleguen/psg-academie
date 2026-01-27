from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.models import Player, Team
from app import schemas

router = APIRouter(prefix="/players", tags=["players"])

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
