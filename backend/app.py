
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from src.routes.pays import router as pays_router
from src.routes.academie import router as academie_router
from src.routes.equipe import router as equipe_router
from src.routes.joueur import router as joueur_router
from src.db.database import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)


app.include_router(pays_router)
app.include_router(academie_router)
app.include_router(equipe_router)
app.include_router(joueur_router)

@app.get("/")
async def root(request: Request):
    return RedirectResponse(url="/docs")
