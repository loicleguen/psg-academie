from sqlmodel import SQLModel, create_engine, Session
import os

# Paramètres de connexion PostgreSQL (doivent correspondre à docker-compose.yml)
POSTGRES_USER = os.getenv("POSTGRES_USER", "psguser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "psgpass")
POSTGRES_DB = os.getenv("POSTGRES_DB", "psgdb")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL, echo=True)

# Utilitaire pour créer les tables

def init_db():
    SQLModel.metadata.create_all(engine)

# Utilitaire pour obtenir une session

def get_session():
    return Session(engine)
