from fastapi import APIRouter
from src.models.pays import Pays
from typing import List

router = APIRouter(prefix="/pays", tags=["Pays"])

# Stockage temporaire en mémoire
fake_db: List[Pays] = []

@router.post("/", response_model=Pays)
def create_pays(pays: Pays):
    pays.id = len(fake_db) + 1
    fake_db.append(pays)
    return pays

@router.get("/", response_model=List[Pays])
def list_pays():
    return fake_db

@router.put("/{pays_id}", response_model=Pays)
def update_pays(pays_id: int, pays: Pays):
    for idx, p in enumerate(fake_db):
        if p.id == pays_id:
            pays.id = pays_id
            fake_db[idx] = pays
            return pays
    return None

@router.delete("/{pays_id}")
def delete_pays(pays_id: int):
    for idx, p in enumerate(fake_db):
        if p.id == pays_id:
            del fake_db[idx]
            return {"message": "Pays supprimé"}
    return {"message": "Pays non trouvé"}
