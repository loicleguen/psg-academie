from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from ..db.database import get_session
from ..models.academy import Academy, AcademyUpdate

router = APIRouter(prefix="/academies", tags=["academies"])

@router.post("/", response_model=Academy, status_code=status.HTTP_201_CREATED)
def create_academy(academy: AcademyUpdate, session: Session = Depends(get_session)):
    db_academy = Academy.from_orm(academy)
    session.add(db_academy)
    session.commit()
    session.refresh(db_academy)
    return db_academy

@router.get("/", response_model=list[Academy])
def read_academies(session: Session = Depends(get_session)):
    academies = session.exec(select(Academy)).all()
    return academies


# Nouvelle route : GET academies par country_id
@router.get("/country/{country_id}", response_model=list[Academy])
def read_academies_by_country(country_id: int, session: Session = Depends(get_session)):
    academies = session.exec(select(Academy).where(Academy.country_id == country_id)).all()
    return academies

@router.put("/{academy_id}", response_model=Academy)
def update_academy(academy_id: int, academy_update: AcademyUpdate, session: Session = Depends(get_session)):
    academy = session.get(Academy, academy_id)
    if not academy:
        raise HTTPException(status_code=404, detail="Academy not found")
    academy.name = academy_update.name
    # academy.country_id n'est pas modifié
    session.commit()
    session.refresh(academy)
    return academy

@router.delete("/{academy_id}", status_code=status.HTTP_200_OK)
def delete_academy(academy_id: int, session: Session = Depends(get_session)):
    academy = session.get(Academy, academy_id)
    if not academy:
        raise HTTPException(status_code=404, detail="Academy not found")
    session.delete(academy)
    session.commit()
    return {"message": "Academy deleted successfully"}
