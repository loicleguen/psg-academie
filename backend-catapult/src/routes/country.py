from fastapi import APIRouter, HTTPException, Depends, status
from src.models.country import Country, CountryCreate, CountryUpdate, CountryRead
from src.models.user import User
from src.db.database import get_session
from src.middleware.security import require_coach_or_admin
from sqlmodel import select, func
from sqlalchemy.orm import selectinload
from typing import List

router = APIRouter(prefix="/countries", tags=["countries"])

@router.post("/", response_model=CountryRead, status_code=status.HTTP_201_CREATED)
def create_country(
    country: CountryCreate,
    session=Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    existing = session.exec(
        select(Country).where(func.lower(Country.name) == country.name.lower())
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Country name already exists.")
    db_country = Country(**country.model_dump())
    session.add(db_country)
    session.commit()
    session.refresh(db_country)
    return db_country

@router.get("/", response_model=List[CountryRead])
def list_countries(
    session=Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    statement = select(Country).options(selectinload(Country.academies))
    country_list = session.exec(statement).all()
    return country_list


@router.put("/{country_name}", response_model=CountryRead)
def update_country_by_name(
    country_name: str,
    country: CountryUpdate,
    session=Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    db_country = session.exec(select(Country).where(Country.name == country_name)).first()
    if not db_country:
        raise HTTPException(status_code=404, detail="Country not found.")
    db_country.name = country.name
    session.add(db_country)
    session.commit()
    session.refresh(db_country)
    return db_country

@router.delete("/{country_name}", status_code=status.HTTP_200_OK)
def delete_country_by_name(
    country_name: str,
    session=Depends(get_session),
    current_user: User = Depends(require_coach_or_admin)
):
    db_country = session.exec(select(Country).where(Country.name == country_name)).first()
    if not db_country:
        raise HTTPException(status_code=404, detail="Country not found")
    session.delete(db_country)
    session.commit()
    return {"message": "Country deleted successfully"}
