from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .team import Team, TeamRead

class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", ondelete="CASCADE")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    name: str
    age: Optional[int]
    team: Optional["Team"] = Relationship(back_populates="players")

class PlayerCreate(SQLModel):
    name: str
    age: Optional[int]
    team_id: int

class PlayerUpdate(SQLModel):
    name: Optional[str] = None
    age: Optional[int] = None

class PlayerRead(SQLModel):
    id: int
    name: str
    age: Optional[int]
    team: Optional["TeamRead"] = None

    model_config = {"from_attributes": True}
