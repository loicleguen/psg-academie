from fastapi import APIRouter, HTTPException, Body
from src.models.country import Country, CountryUpdate
from src.db.database import get_session
from sqlmodel import select, func
from typing import List

router = APIRouter(prefix="/countries", tags=["countries"])

@router.post("/", response_model=Country)
def create_country(country: Country = Body(..., example={"name": "France"})):
    country.id = None  # Ensure id is not set by client
    with get_session() as session:
        existing = session.exec(
            select(Country).where(func.lower(Country.name) == country.name.lower())
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Country name already exists.")
        session.add(country)
        session.commit()
        session.refresh(country)
        return country

@router.get("/", response_model=List[Country])
def list_countries():
    with get_session() as session:
        country_list = session.exec(select(Country)).all()
        return country_list

@router.put("/{country_id}", response_model=Country)
def update_country(country_id: int, country: CountryUpdate):
    with get_session() as session:
        db_country = session.get(Country, country_id)
        if not db_country:
            raise HTTPException(status_code=404, detail="Country not found.")
        db_country.name = country.name
        session.add(db_country)
        session.commit()
        session.refresh(db_country)
        return db_country

@router.delete("/{country_id}")
def delete_country(country_id: int):
    with get_session() as session:
        db_country = session.get(Country, country_id)
        if not db_country:
            raise HTTPException(status_code=404, detail="Country not found")
        session.delete(db_country)
        session.commit()
        return {"message": "Country deleted"}
