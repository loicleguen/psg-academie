from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List

class AcademieDuPays(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str
    pays_id: int = Field(foreign_key="pays.id")

    # Relationship to Pays (optional, for ORM navigation)
    # pays: Optional["Pays"] = Relationship(back_populates="academies")

    class Config:
        orm_mode = True

# Optionally, add a Pydantic schema for update/create if needed
from pydantic import BaseModel

class AcademieDuPaysUpdate(BaseModel):
    nom: str
    pays_id: int
