from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .academy import AcademyRead

class CountryBase(SQLModel):
    name: str

class Country(CountryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    academies: List["Academy"] = Relationship(back_populates="country")

class CountryCreate(SQLModel):
    name: str

class CountryUpdate(SQLModel):
    name: Optional[str] = None

class CountryRead(SQLModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
