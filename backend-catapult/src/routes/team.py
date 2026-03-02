from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from ..db.database import get_session
from ..models.team import Team, TeamCreate, TeamUpdate, TeamRead
from ..models.academy import Academy
from ..models.user import User, UserRead
from ..middleware.security import require_coach_or_admin, get_current_user


def get_team_full_path(session: Session, team_id: int) -> str:
    """
    Retourne le chemin complet d'une équipe au format: Country / Academy / Team
    """
    from ..models.country import Country
    
    team = session.get(Team, team_id)
    if not team:
        return None
    
    # Charger l'academy avec le country
    academy = session.exec(
        select(Academy)
        .where(Academy.id == team.academy_id)
        .options(selectinload(Academy.country))
    ).first()
    
    if not academy:
        return team.name
    
    if academy.country:
        return f"{academy.country.name} / {academy.name} / {team.name}"
    else:
        return f"{academy.name} / {team.name}"


router = APIRouter(prefix="/teams", tags=["teams"])

@router.post("/", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(
    team: TeamCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    db_team = Team(**team.model_dump())
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    return db_team

@router.get("/", response_model=list[TeamRead])
def read_teams(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    statement = select(Team).options(
        selectinload(Team.academy).selectinload(Academy.country),
        selectinload(Team.players)
    )
    teams = session.exec(statement).all()
    return teams

@router.get("/academy/{academy_name}", response_model=list[TeamRead])
def read_teams_by_academy_name(
    academy_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    academy = session.exec(select(Academy).where(Academy.name == academy_name)).first()
    if not academy:
        raise HTTPException(status_code=404, detail="Academy not found")
    statement = select(Team).where(Team.academy_id == academy.id).options(
        selectinload(Team.academy).selectinload(Academy.country),
        selectinload(Team.players)
    )
    teams = session.exec(statement).all()
    return teams

@router.get("/{team_name}", response_model=list[TeamRead])
def read_team_by_name(
    team_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    statement = select(Team).where(func.lower(Team.name) == team_name.lower()).options(
        selectinload(Team.academy).selectinload(Academy.country),
        selectinload(Team.players)
    )
    teams = session.exec(statement).all()
    if not teams:
        raise HTTPException(status_code=404, detail="Team not found")
    return teams

@router.get("/{team_name}/players", response_model=list[UserRead])
def get_players_by_team(
    team_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    teams = session.exec(select(Team).where(func.lower(Team.name) == team_name.lower())).all()
    if not teams:
        raise HTTPException(status_code=404, detail="Team not found")
    team_ids = [t.id for t in teams]

    stmt = select(User).where(User.team_id.in_(team_ids), User.role == "player")
    players = session.exec(stmt).all()
    return players

@router.get("/id/{team_id}", response_model=TeamRead)
def read_team_by_id(
    team_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    team = session.exec(
        select(Team)
        .where(Team.id == team_id)
        .options(
            selectinload(Team.academy).selectinload(Academy.country),
            selectinload(Team.players)
        )
    ).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@router.get("/id/{team_id}/players", response_model=list[UserRead])
def get_players_by_team_id(
    team_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    players = session.exec(
        select(User).where(User.team_id == team_id, User.role == "player")
    ).all()
    return players

@router.put("/{team_id}", response_model=TeamRead)
def update_team_by_id(
    team_id: int,
    team_update: TeamUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    team.name = team_update.name
    session.commit()
    session.refresh(team)
    return team

@router.delete("/{team_id}", status_code=status.HTTP_200_OK)
def delete_team_by_id(
    team_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team)
    session.commit()
    return {"message": "Team deleted successfully"}
