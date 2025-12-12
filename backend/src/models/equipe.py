from sqlmodel import SQLModel, Field, Relationship
from typing import Optional

class EquipeAcademie(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str
    academie_id: int = Field(foreign_key="academiedupays.id")

    class Config:
        orm_mode = True

from pydantic import BaseModel

class EquipeAcademieUpdate(BaseModel):
    nom: str
    academie_id: int
