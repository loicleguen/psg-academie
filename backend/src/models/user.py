from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """Rôles utilisateurs disponibles"""
    ADMIN = "admin"
    COACH = "coach"
    ANALYST = "analyst"
    PLAYER = "player"


class User(SQLModel, table=True):
    """Modèle utilisateur pour l'authentification"""
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.ANALYST)
    is_active: bool = Field(default=True)
    full_name: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class UserCreate(SQLModel):
    """Schéma pour créer un utilisateur"""
    email: str
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.ANALYST


class UserRead(SQLModel):
    """Schéma pour lire un utilisateur (sans mot de passe)"""
    id: int
    email: str
    role: UserRole
    is_active: bool
    full_name: Optional[str]
    created_at: datetime


class UserLogin(SQLModel):
    """Schéma pour le login"""
    email: str
    password: str


class Token(SQLModel):
    """Schéma de réponse avec token JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # secondes


class TokenData(SQLModel):
    """Données contenues dans le token JWT"""
    email: Optional[str] = None
    role: Optional[str] = None
