from enum import Enum
from typing import Optional
from datetime import datetime

class UserRole(str, Enum):
    ADMIN = "admin"
    COACH = "coach"
    PLAYER = "player"

class User:
    def __init__(
        self,
        id: int,
        email: str,
        role: UserRole,
        is_active: bool = True,
        full_name: Optional[str] = None,
        player_name: Optional[str] = None,
        age: Optional[int] = None,
        team_id: Optional[int] = None,
        position: Optional[str] = None,
        photo_url: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.email = email
        self.role = role
        self.is_active = is_active
        self.full_name = full_name
        self.player_name = player_name
        self.age = age
        self.team_id = team_id
        self.position = position
        self.photo_url = photo_url
        self.created_at = created_at or datetime.utcnow()

class TokenData:
    def __init__(self, email: Optional[str] = None, role: Optional[str] = None):
        self.email = email
        self.role = role