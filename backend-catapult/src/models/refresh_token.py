from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class RefreshToken(SQLModel, table=True):
    """Modèle pour stocker les refresh tokens"""

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True, max_length=500)
    user_id: int = Field(foreign_key="user.id")
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_revoked: bool = Field(default=False)
