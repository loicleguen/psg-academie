from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import BaseModel

class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str
    age: Optional[int]
    equipe_id: int = Field(foreign_key="equipeacademie.id")

    class Config:
        orm_mode = True

class PlayerUpdate(BaseModel):
    nom: str
    age: Optional[int]
    equipe_id: int
