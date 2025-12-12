from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from ..db.database import get_session
from ..models.equipe import EquipeAcademie, EquipeAcademieUpdate

router = APIRouter(prefix="/equipes", tags=["equipes"])

@router.post("/", response_model=EquipeAcademie, status_code=status.HTTP_201_CREATED)
def create_equipe(equipe: EquipeAcademieUpdate, session: Session = Depends(get_session)):
    db_equipe = EquipeAcademie.from_orm(equipe)
    session.add(db_equipe)
    session.commit()
    session.refresh(db_equipe)
    return db_equipe

@router.get("/", response_model=list[EquipeAcademie])
def read_equipes(session: Session = Depends(get_session)):
    equipes = session.exec(select(EquipeAcademie)).all()
    return equipes


# Nouvelle route : GET equipes par academie_id
@router.get("/academie/{academie_id}", response_model=list[EquipeAcademie])
def read_equipes_by_academie(academie_id: int, session: Session = Depends(get_session)):
    equipes = session.exec(select(EquipeAcademie).where(EquipeAcademie.academie_id == academie_id)).all()
    return equipes

@router.put("/{equipe_id}", response_model=EquipeAcademie)
def update_equipe(equipe_id: int, equipe_update: EquipeAcademieUpdate, session: Session = Depends(get_session)):
    equipe = session.get(EquipeAcademie, equipe_id)
    if not equipe:
        raise HTTPException(status_code=404, detail="Equipe not found")
    equipe.nom = equipe_update.nom
    equipe.academie_id = equipe_update.academie_id
    session.commit()
    session.refresh(equipe)
    return equipe

@router.delete("/{equipe_id}", status_code=status.HTTP_200_OK)
def delete_equipe(equipe_id: int, session: Session = Depends(get_session)):
    equipe = session.get(EquipeAcademie, equipe_id)
    if not equipe:
        raise HTTPException(status_code=404, detail="Equipe not found")
    session.delete(equipe)
    session.commit()
    return {"message": "Equipe deleted successfully"}
