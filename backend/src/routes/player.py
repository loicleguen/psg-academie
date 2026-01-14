from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from ..db.database import get_session
from ..models.player import Player, PlayerCreate, PlayerUpdate
from ..models.user import User
from ..middleware.security import require_coach_or_admin

router = APIRouter(prefix="/players", tags=["players"])

@router.post("/", response_model=Player, status_code=status.HTTP_201_CREATED)
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

@router.get("/", response_model=list[Player])
def read_player(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    player = session.exec(select(Player)).all()
    return player

# GET player par team_id
@router.get("/team/{team_id}", response_model=list[Player])
def read_player_by_team(
    team_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    player = session.exec(select(Player).where(Player.team_id == team_id)).all()
    return player

@router.put("/{player_id}", response_model=Player)
def update_player(
    player_id: int,
    player_update: PlayerUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    player.name = player_update.name
    player.age = player_update.age
    # player.team_id n'est pas modifié
    session.commit()
    session.refresh(player)
    return player

@router.delete("/{player_id}", status_code=status.HTTP_200_OK)
def delete_player(
    player_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    session.delete(player)
    session.commit()
    return {"message": "Player deleted successfully"}
