from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from ..db.database import get_session
from ..models.academy import Academy
from ..models.team import Team
from ..models.user import User, UserRead
from ..middleware.security import require_coach_or_admin
from sqlalchemy import func

router = APIRouter(prefix="/players", tags=["players"])

@router.post("/", response_model=PlayerRead, status_code=status.HTTP_201_CREATED)
def create_player(
    player: PlayerCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    raise HTTPException(status_code=410, detail="This endpoint is deprecated. Use /auth/users or /players (user-backed) instead.")

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

# NOTE: this GET now reads from User (role='player') via User.player_name
@router.get("/{player_name}", response_model=list[UserRead])
def read_player_by_name(
    player_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    statement = select(User).where(User.role == "player", User.player_name == player_name)
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
    raise HTTPException(status_code=410, detail="This endpoint is deprecated. Update player data via /auth/users instead.")

@router.delete("/{player_id}", status_code=status.HTTP_200_OK)
def delete_player_by_id(
    player_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    raise HTTPException(status_code=410, detail="This endpoint is deprecated and will be removed soon.")
