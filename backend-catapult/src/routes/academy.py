from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from ..db.database import get_session
from ..models.academy import Academy, AcademyCreate, AcademyUpdate, AcademyRead
from ..models.country import Country
from ..models.user import User
from ....common.security import require_coach_or_admin

router = APIRouter(prefix="/academies", tags=["academies"])

@router.post("/", response_model=AcademyRead, status_code=status.HTTP_201_CREATED)
def create_academy(
    academy: AcademyCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    db_academy = Academy(**academy.model_dump())
    session.add(db_academy)
    session.commit()
    session.refresh(db_academy)
    return db_academy

@router.get("/", response_model=list[AcademyRead])
def read_academies(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    statement = select(Academy).options(
        selectinload(Academy.country),
        selectinload(Academy.teams)
    )
    academies = session.exec(statement).all()
    return academies

@router.get("/country/{country_name}", response_model=list[AcademyRead])
def read_academies_by_country_name(
    country_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    country = session.exec(select(Country).where(Country.name == country_name)).first()
    if not country:
        raise HTTPException(status_code=404, detail="Country not found")
    statement = select(Academy).where(Academy.country_id == country.id).options(
        selectinload(Academy.country),
        selectinload(Academy.teams)
    )
    academies = session.exec(statement).all()
    return academies

@router.get("/{academy_name}", response_model=AcademyRead)
def read_academy_by_name(
    academy_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    statement = select(Academy).where(Academy.name == academy_name).options(
        selectinload(Academy.country),
        selectinload(Academy.teams)
    )
    academy = session.exec(statement).first()
    if not academy:
        raise HTTPException(status_code=404, detail="Academy not found")
    return academy

@router.put("/{academy_name}", response_model=AcademyRead)
def update_academy_by_name(
    academy_name: str,
    academy_update: AcademyUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    academy = session.exec(select(Academy).where(Academy.name == academy_name)).first()
    if not academy:
        raise HTTPException(status_code=404, detail="Academy not found")
    academy.name = academy_update.name
    # academy.country_id n'est pas modifié
    session.commit()
    session.refresh(academy)
    return academy

@router.delete("/{academy_name}", status_code=status.HTTP_200_OK)
def delete_academy_by_name(
    academy_name: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    academy = session.exec(select(Academy).where(Academy.name == academy_name)).first()
    if not academy:
        raise HTTPException(status_code=404, detail="Academy not found")
    session.delete(academy)
    session.commit()
    return {"message": "Academy deleted successfully"}
