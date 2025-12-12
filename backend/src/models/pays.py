from sqlmodel import SQLModel, Field
from typing import Optional

class Pays(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nom: str
