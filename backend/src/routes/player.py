from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from ..db.database import get_session
from ..models.player import Player, PlayerCreate, PlayerUpdate, PlayerRead
from ..models.academy import Academy
from ..models.team import Team
from ..models.user import User
from ..middleware.security import require_coach_or_admin
from sqlalchemy import func

router = APIRouter(prefix="/players", tags=["players"])

@router.post("/", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(
    player: PlayerCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    db_player = Player(**player.model_dump())
    session.add(db_player)
    session.commit()
    session.refresh(db_player)
    return db_player

@router.get("/", response_model=list[PlayerRead])
def read_players(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    statement = select(Player).options(
        selectinload(Player.team).selectinload(Team.academy).selectinload(Academy.country)
    )
    players = session.exec(statement).all()
    return players

@router.get("/team/{team_name}", response_model=list[PlayerRead])
def read_players_by_team_name(
    team_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    teams = session.exec(
        select(Team).where(func.lower(Team.name) == team_name.lower())
    ).all()
    if not teams:
        raise HTTPException(status_code=404, detail="Team not found")
    team_ids = [t.id for t in teams]

    statement = select(Player).where(Player.team_id.in_(team_ids)).options(
        selectinload(Player.team).selectinload(Team.academy).selectinload(Academy.country)
    )
    players = session.exec(statement).all()
    return players

@router.get("/{player_name}", response_model=list[PlayerRead])
def read_player_by_name(
    player_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    statement = select(Player).where(Player.name == player_name).options(
        selectinload(Player.team).selectinload(Team.academy).selectinload(Academy.country)
    )
    players = session.exec(statement).all()
    if not players:
        raise HTTPException(status_code=404, detail="Player not found")
    return players

@router.put("/{player_id}", response_model=PlayerRead)
def update_player_by_id(
    player_id: int,
    player_update: PlayerUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    player = session.exec(select(Player).where(Player.id == player_id)).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    player.name = player_update.name
    player.age = player_update.age
    session.commit()
    session.refresh(player)
    return player

@router.delete("/{player_id}", status_code=status.HTTP_200_OK)
def delete_player_by_id(
    player_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    player = session.exec(select(Player).where(Player.id == player_id)).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    session.delete(player)
    session.commit()
    return {"message": "Player deleted successfully"}
