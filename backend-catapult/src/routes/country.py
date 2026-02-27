from fastapi import APIRouter, HTTPException, Depends, status
from ..models.country import Country, CountryCreate, CountryUpdate, CountryRead
from ..models.user import User
from ..db.database import get_session
from common.security import require_coach_or_admin, get_current_user
from sqlmodel import select, func, Session
from sqlalchemy.orm import selectinload
from typing import List

router = APIRouter(prefix="/countries", tags=["countries"])

@router.post("/", response_model=CountryRead, status_code=status.HTTP_201_CREATED)
def create_country(
    country: CountryCreate,
    session: Session=Depends(get_session),
    current_user: User = Depends(
        lambda token=Depends(): require_coach_or_admin(
            get_current_user(token, session=Depends(get_session))
        )
    )
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
    session: Session=Depends(get_session),
    current_user: User = Depends(
        lambda token=Depends(): require_coach_or_admin(
            get_current_user(token, session=Depends(get_session))
        )
    )
):
    statement = select(Country).options(selectinload(Country.academies))
    country_list = session.exec(statement).all()
    return country_list


@router.put("/{country_name}", response_model=CountryRead)
def update_country_by_name(
    country_name: str,
    country: CountryUpdate,
    session: Session=Depends(get_session),
    current_user: User = Depends(
        lambda token=Depends(): require_coach_or_admin(
            get_current_user(token, session=Depends(get_session))
        )
    )
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
    session: Session=Depends(get_session),
    current_user: User = Depends(
        lambda token=Depends(): require_coach_or_admin(
            get_current_user(token, session=Depends(get_session))
        )
    )
):
    db_country = session.exec(select(Country).where(Country.name == country_name)).first()
    if not db_country:
        raise HTTPException(status_code=404, detail="Country not found")
    session.delete(db_country)
    session.commit()
    return {"message": "Country deleted successfully"}
