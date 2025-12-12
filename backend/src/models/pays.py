from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import BaseModel
import pycountry
import pycountry_convert
from pycountry_convert import country_name_to_country_alpha2

def is_valid_country(name: str) -> bool:
    name = name.strip().lower()
    # Vérification anglais (pycountry)
    for country in pycountry.countries:
        if country.name.lower() == name:
            return True
        if hasattr(country, 'official_name') and country.official_name.lower() == name:
            return True
    # Vérification français (pycountry-convert)
    try:
        # pycountry-convert attend le nom français avec la première lettre en majuscule
        # On tente la conversion, si ça échoue, ce n'est pas un pays reconnu
        country_name_to_country_alpha2(name.title(), cn_name_format='french')
        return True
    except Exception:
        return False

class Pays(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str

    class Config:
        orm_mode = True


class PaysUpdate(BaseModel):
    nom: str
