from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .academy import Academy, AcademyRead
    from .user import User

class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    academy_id: int = Field(foreign_key="academy.id", ondelete="CASCADE")
    academy: Optional["Academy"] = Relationship(back_populates="teams")
    players: List["User"] = Relationship(back_populates="team")

class TeamCreate(SQLModel):
    name: str
    academy_id: int

class TeamCreateByName(SQLModel):
    name: str
    academy_name: str

class TeamUpdate(SQLModel):
    name: Optional[str] = None

class TeamRead(SQLModel):
    id: int
    name: str
    academy: Optional["AcademyRead"] = None

    model_config = {"from_attributes": True}
