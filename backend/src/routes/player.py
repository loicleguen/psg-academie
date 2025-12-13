from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from ..db.database import get_session
from ..models.player import Player, PlayerUpdate

router = APIRouter(prefix="/player", tags=["player"])

@router.post("/", response_model=Player, status_code=status.HTTP_201_CREATED)
def create_Player(Player: PlayerUpdate, session: Session = Depends(get_session)):
    db_Player = Player.from_orm(Player)
    session.add(db_Player)
    session.commit()
    session.refresh(db_Player)
    return db_Player

@router.get("/", response_model=list[Player])
def read_player(session: Session = Depends(get_session)):
    player = session.exec(select(Player)).all()
    return player

# GET player par equipe_id
@router.get("/equipe/{equipe_id}", response_model=list[Player])
def read_player_by_equipe(equipe_id: int, session: Session = Depends(get_session)):
    player = session.exec(select(Player).where(Player.equipe_id == equipe_id)).all()
    return player

@router.put("/{Player_id}", response_model=Player)
def update_Player(Player_id: int, Player_update: PlayerUpdate, session: Session = Depends(get_session)):
    Player = session.get(Player, Player_id)
    if not Player:
        raise HTTPException(status_code=404, detail="Player not found")
    Player.nom = Player_update.nom
    Player.age = Player_update.age
    Player.equipe_id = Player_update.equipe_id
    session.commit()
    session.refresh(Player)
    return Player

@router.delete("/{Player_id}", status_code=status.HTTP_200_OK)
def delete_Player(Player_id: int, session: Session = Depends(get_session)):
    Player = session.get(Player, Player_id)
    if not Player:
        raise HTTPException(status_code=404, detail="Player not found")
    session.delete(Player)
    session.commit()
    return {"message": "Player deleted successfully"}
