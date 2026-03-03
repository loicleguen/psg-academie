from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from .team import Team
    from .injury import Injury


class UserRole(str, Enum):
    """Rôles utilisateurs disponibles"""
    ADMIN = "admin"
    COACH = "coach"
    PLAYER = "player"


class User(SQLModel, table=True):
    """Modèle utilisateur pour l'authentification"""
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.PLAYER)
    is_active: bool = Field(default=True)
    full_name: Optional[str] = Field(default=None, max_length=255)
    player_name: Optional[str] = Field(default=None, index=True)
    age: Optional[int] = Field(default=None)
    date_of_birth: Optional[datetime] = Field(default=None, nullable=True)
    adress: Optional[str] = Field(default=None, max_length=255, nullable=True)
    height: Optional[float] = Field(default=None, nullable=True)
    weight: Optional[float] = Field(default=None, nullable=True)
    strong_foot: Optional[str] = Field(default=None, max_length=10, nullable=True)
    phone_number: Optional[str] = Field(default=None, max_length=20, nullable=True)
    emergency_contact: Optional[str] = Field(default=None, max_length=255, nullable=True)
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")
    position: Optional[str] = Field(default=None, max_length=50)
    photo_url: Optional[str] = Field(default=None, max_length=1024)
    team: Optional["Team"] = Relationship(back_populates="players")
    injuries: List["Injury"] = Relationship(back_populates="user")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class UserCreate(SQLModel):
    """Schéma pour créer un utilisateur"""
    email: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.PLAYER
    player_name: Optional[str] = None
    age: Optional[int] = None
    team_id: Optional[int] = None
    position: Optional[str] = None
    photo_url: Optional[str] = None


class UserRead(SQLModel):
    """Schéma pour lire un utilisateur (sans mot de passe)"""
    id: int
    email: str
    role: UserRole
    is_active: bool
    full_name: Optional[str]
    player_name: Optional[str] = None
    age: Optional[int] = None
    team_id: Optional[int] = None
    position: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime
    date_of_birth: Optional[datetime] = None
    adress: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    strong_foot: Optional[str] = None
    phone_number: Optional[str] = None
    emergency_contact: Optional[str] = None


class UserLogin(SQLModel):
    """Schéma pour le login"""
    email: str
    password: str


class Token(SQLModel):
    """Schéma de réponse avec token JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str


class TokenData(SQLModel):
    """Données contenues dans le token JWT"""
    email: Optional[str] = None
    role: Optional[str] = None


class UserUpdate(SQLModel):
    """Schéma pour mettre à jour un utilisateur (admin)"""
    email: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    team_id: Optional[int] = None
    age: Optional[int] = None
    player_name: Optional[str] = None
    position: Optional[str] = None
    photo_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    adress: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    strong_foot: Optional[str] = None
    phone_number: Optional[str] = None
    emergency_contact: Optional[str] = None


class UserUpdateMe(SQLModel):
    """Schéma pour mettre à jour son propre profil (sans email ni role)"""
    password: Optional[str] = None
    full_name: Optional[str] = None
    team_id: Optional[int] = None
    age: Optional[int] = None
    player_name: Optional[str] = None
    position: Optional[str] = None
    photo_url: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    adress: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    strong_foot: Optional[str] = None
    phone_number: Optional[str] = None
    emergency_contact: Optional[str] = None


class RefreshToken(SQLModel, table=True):
    """Modèle pour stocker les refresh tokens"""
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True, max_length=500)
    user_id: int = Field(foreign_key="user.id")
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_revoked: bool = Field(default=False)
