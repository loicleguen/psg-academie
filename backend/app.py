
from fastapi import FastAPI
from src.routes.pays import router as pays_router
from src.db.database import init_db

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(pays_router)

@app.get("/")
async def root():
    return {"message": "Bienvenue sur PSG-ACADEMIE API"}
