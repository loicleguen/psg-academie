from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime, date

if TYPE_CHECKING:
    from .user import User


class Injury(SQLModel, table=True):
    """Modèle pour les blessures d'un joueur"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    body_part: Optional[str] = Field(default=None, max_length=100)
    injury_date: date
    injury_end_date: Optional[date]
    restriction_date: Optional[date] = None
    restriction_type: Optional[str] = None
    comment: Optional[str] = Field(default=None, max_length=500)
    coord_x: Optional[float] = Field(default=None)  # Coordonnée X en % (0-100)
    coord_y: Optional[float] = Field(default=None)  # Coordonnée Y en % (0-100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relation
    user: Optional["User"] = Relationship(back_populates="injuries")


class InjuryCreate(SQLModel):
    """Schéma pour créer une blessure"""
    body_part: Optional[str] = None
    injury_date: date
    injury_end_date: Optional[date] = None
    restriction_date: Optional[date] = None
    restriction_type: Optional[str] = None
    comment: Optional[str] = None
    coord_x: Optional[float] = None
    coord_y: Optional[float] = None


class InjuryRead(SQLModel):
    """Schéma pour lire une blessure"""
    id: int
    user_id: int
    body_part: Optional[str]
    injury_date: date
    injury_end_date: Optional[date]
    restriction_date: Optional[date]
    restriction_type: Optional[str]
    restriction_date: Optional[date]
    restriction_type: Optional[str]
    comment: Optional[str]
    coord_x: Optional[float]
    coord_y: Optional[float]
    created_at: datetime


class InjuryUpdate(SQLModel):
    """Schéma pour mettre à jour une blessure"""
    body_part: Optional[str] = None
    injury_date: Optional[date] = None
    injury_end_date: Optional[date] = None
    restriction_date: Optional[date] = None
    restriction_type: Optional[str] = None
    comment: Optional[str] = None
    coord_x: Optional[float] = None
    coord_y: Optional[float] = None
