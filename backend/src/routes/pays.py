from fastapi import APIRouter, HTTPException, Body
from src.models.pays import Pays
from src.db.database import get_session
from sqlmodel import select, func
from typing import List
import pycountry

router = APIRouter(prefix="/pays", tags=["Pays"])

def is_valid_country(name: str) -> bool:
    name = name.strip().lower()
    for country in pycountry.countries:
        if country.name.lower() == name:
            return True
        if hasattr(country, 'official_name') and country.official_name.lower() == name:
            return True
    return False

@router.post("/", response_model=Pays)
def create_pays(pays: Pays = Body(..., example={"nom": "France"})):
    pays.id = None  # Ensure id is not set by client
    # Vérification que le pays existe dans la liste officielle (pycountry)
    if not is_valid_country(pays.nom):
        raise HTTPException(status_code=400, detail="Country name is not a valid official country (ISO 3166, English)")
    with get_session() as session:
        # Vérification unicité insensible à la casse
        existing = session.exec(
            select(Pays).where(func.lower(Pays.nom) == pays.nom.lower())
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Country name already exists (case-insensitive)")
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
            raise HTTPException(status_code=404, detail="Country not found")
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
            raise HTTPException(status_code=404, detail="Country not found")
        session.delete(db_pays)
        session.commit()
        return {"message": "Country deleted"}
