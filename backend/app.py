
from fastapi import FastAPI
from src.routes.pays import router as pays_router

app = FastAPI()

app.include_router(pays_router)

@app.get("/")
async def root():
    return {"message": "Bienvenue sur PSG-ACADEMIE API"}
