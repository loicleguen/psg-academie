from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import BaseModel

class Country(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    class Config:
        from_attributes = True

class CountryCreate(BaseModel):
    name: str

class CountryUpdate(BaseModel):
    name: str
