from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .country import CountryRead

class AcademyBase(SQLModel):
    name: str
    country_id: int

class Academy(AcademyBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    country_id: Optional[int] = Field(default=None, foreign_key="country.id", ondelete="CASCADE")
    country: Optional["Country"] = Relationship(back_populates="academies")
    teams: List["Team"] = Relationship(back_populates="academy")

class AcademyCreate(SQLModel):
    name: str
    country_id: int

class AcademyCreateByName(SQLModel):
    name: str
    country_name: str

class AcademyUpdate(SQLModel):
    name: Optional[str] = None
    country_id: Optional[int] = None

class AcademyRead(SQLModel):
    id: int
    name: str
    country: Optional["CountryRead"] = None

    model_config = {"from_attributes": True}
