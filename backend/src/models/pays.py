from pydantic import BaseModel
from typing import Optional

class Pays(BaseModel):
    id: Optional[int] = None
    nom: str
