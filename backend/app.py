
from fastapi import FastAPI
from src.routes.pays import router as pays_router
from src.db.database import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(pays_router)

@app.get("/")
async def root():
    return {"message": "Welcome to PSG-ACADEMIE API"}
