from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from ..db.database import get_session
from ..models.academie import AcademieDuPays, AcademieDuPaysUpdate

router = APIRouter(prefix="/academies", tags=["academies"])

@router.post("/", response_model=AcademieDuPays, status_code=status.HTTP_201_CREATED)
def create_academie(academie: AcademieDuPaysUpdate, session: Session = Depends(get_session)):
    db_academie = AcademieDuPays.from_orm(academie)
    session.add(db_academie)
    session.commit()
    session.refresh(db_academie)
    return db_academie

@router.get("/", response_model=list[AcademieDuPays])
def read_academies(session: Session = Depends(get_session)):
    academies = session.exec(select(AcademieDuPays)).all()
    return academies


# Nouvelle route : GET academies par pays_id
@router.get("/pays/{pays_id}", response_model=list[AcademieDuPays])
def read_academies_by_pays(pays_id: int, session: Session = Depends(get_session)):
    academies = session.exec(select(AcademieDuPays).where(AcademieDuPays.pays_id == pays_id)).all()
    return academies

@router.put("/{academie_id}", response_model=AcademieDuPays)
def update_academie(academie_id: int, academie_update: AcademieDuPaysUpdate, session: Session = Depends(get_session)):
    academie = session.get(AcademieDuPays, academie_id)
    if not academie:
        raise HTTPException(status_code=404, detail="Academie not found")
    academie.nom = academie_update.nom
    academie.pays_id = academie_update.pays_id
    session.commit()
    session.refresh(academie)
    return academie

@router.delete("/{academie_id}", status_code=status.HTTP_200_OK)
def delete_academie(academie_id: int, session: Session = Depends(get_session)):
    academie = session.get(AcademieDuPays, academie_id)
    if not academie:
        raise HTTPException(status_code=404, detail="Academie not found")
    session.delete(academie)
    session.commit()
    return {"message": "Academie deleted successfully"}
