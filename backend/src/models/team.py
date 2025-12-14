from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import BaseModel

class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    academy_id: int = Field(foreign_key="academy.id", ondelete="CASCADE")

    class Config:
        orm_mode = True

class TeamCreate(BaseModel):
    name: str
    academy_id: int

class TeamUpdate(BaseModel):
    name: str
