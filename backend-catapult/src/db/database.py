import os
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

# Import models to ensure they're registered with SQLModel
from ..models.country import Country
from ..models.academy import Academy
from ..models.team import Team
from ..models.catapult import CatapultSession
from ..models.user import User
from ..models.injury import Injury

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://psguser:psgpass@db:5432/psgdb")

# Augmentation du pool pour gérer plus de connexions simultanées
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=20,          # Connexions permanentes dans le pool
    max_overflow=30,       # Connexions supplémentaires en cas de pic
    pool_pre_ping=True,    # Vérifier la validité des connexions
    pool_recycle=3600,     # Recycler les connexions après 1h
)

# Utilitaire pour créer les tables
def init_db():
    """Créer toutes les tables dans la base de données"""
    SQLModel.metadata.create_all(engine)

# Utilitaire pour obtenir une session
def get_session() -> Generator[Session, None, None]:
    """
    Dépendance FastAPI pour obtenir une session DB.
    IMPORTANT: Utilise yield pour garantir la fermeture de la session.
    """
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
