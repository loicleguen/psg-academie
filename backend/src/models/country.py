from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import BaseModel
import pycountry
from pycountry_convert import country_name_to_country_alpha2
import unicodedata

def is_valid_country(name: str) -> bool:
    name = name.strip().lower()
    # Vérification anglais (pycountry)
    for country in pycountry.countries:
        if country.name.lower() == name:
            return True
        if hasattr(country, 'official_name') and country.official_name.lower() == name:
            return True

    # Vérification français (pycountry-convert), gestion des accents
    def strip_accents(text):
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

    name_no_accents = strip_accents(name)
    try:
        # pycountry-convert attend le nom français avec la première lettre en majuscule
        # On tente la conversion avec et sans accents
        country_name_to_country_alpha2(name.title(), cn_name_format='french')
        return True
    except Exception:
        pass
    try:
        country_name_to_country_alpha2(name_no_accents.title(), cn_name_format='french')
        return True
    except Exception:
        return False

class Country(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    class Config:
        orm_mode = True

class PaysUpdate(BaseModel):
    nom: str
