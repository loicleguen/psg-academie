from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import BaseModel

class Country(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    class Config:
        orm_mode = True

class CountryUpdate(BaseModel):
    nom: str
