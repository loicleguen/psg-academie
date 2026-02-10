from sqlmodel import SQLModel, create_engine, Session
import os

# Import models to ensure they're registered with SQLModel
from ..models.country import Country
from ..models.academy import Academy
from ..models.team import Team
from ..models.catapult import CatapultSession
from ..models.user import User

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://psguser:psgpass@db:5432/psgdb")

engine = create_engine(DATABASE_URL, echo=True)

# Utilitaire pour créer les tables

def init_db():
    SQLModel.metadata.create_all(engine)

# Utilitaire pour obtenir une session

def get_session():
    return Session(engine)
