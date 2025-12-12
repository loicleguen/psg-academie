from fastapi import APIRouter, HTTPException
from src.models.pays import Pays
from src.db.database import get_session
from sqlmodel import select
from typing import List

router = APIRouter(prefix="/pays", tags=["Pays"])

@router.post("/", response_model=Pays)
def create_pays(pays: Pays):
    with get_session() as session:
        session.add(pays)
        session.commit()
        session.refresh(pays)
        return pays

@router.get("/", response_model=List[Pays])
def list_pays():
    with get_session() as session:
        pays_list = session.exec(select(Pays)).all()
        return pays_list

@router.put("/{pays_id}", response_model=Pays)
def update_pays(pays_id: int, pays: Pays):
    with get_session() as session:
        db_pays = session.get(Pays, pays_id)
        if not db_pays:
            raise HTTPException(status_code=404, detail="Pays non trouvé")
        db_pays.nom = pays.nom
        session.add(db_pays)
        session.commit()
        session.refresh(db_pays)
        return db_pays

@router.delete("/{pays_id}")
def delete_pays(pays_id: int):
    with get_session() as session:
        db_pays = session.get(Pays, pays_id)
        if not db_pays:
            raise HTTPException(status_code=404, detail="Pays non trouvé")
        session.delete(db_pays)
        session.commit()
        return {"message": "Pays supprimé"}
