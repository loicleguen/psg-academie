from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SessionSummary(BaseModel):
    session_title: str
    session_date: Optional[datetime] = None
    player_count: int = 0
    
    class Config:
        from_attributes = True
