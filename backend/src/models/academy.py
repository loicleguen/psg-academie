from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import BaseModel

class Academy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    country_id: int = Field(foreign_key="country.id", ondelete="CASCADE")

    class Config:
        orm_mode = True

class AcademyUpdate(BaseModel):
    name: str
    country_id: int
