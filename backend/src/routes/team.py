from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from ..db.database import get_session
from ..models.team import Team, TeamUpdate

router = APIRouter(prefix="/teams", tags=["teams"])

@router.post("/", response_model=Team, status_code=status.HTTP_201_CREATED)
def create_team(team: TeamUpdate, session: Session = Depends(get_session)):
    db_team = Team.from_orm(team)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    return db_team

@router.get("/", response_model=list[Team])
def read_teams(session: Session = Depends(get_session)):
    teams = session.exec(select(Team)).all()
    return teams


# Nouvelle route : GET teams par academy_id
@router.get("/academy/{academy_id}", response_model=list[Team])
def read_teams_by_academy(academy_id: int, session: Session = Depends(get_session)):
    teams = session.exec(select(Team).where(Team.academy_id == academy_id)).all()
    return teams

@router.put("/{team_id}", response_model=Team)
def update_team(team_id: int, team_update: TeamUpdate, session: Session = Depends(get_session)):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    team.name = team_update.name
    team.academy_id = team_update.academy_id
    session.commit()
    session.refresh(team)
    return team

@router.delete("/{team_id}", status_code=status.HTTP_200_OK)
def delete_team(team_id: int, session: Session = Depends(get_session)):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team)
    session.commit()
    return {"message": "Team deleted successfully"}
