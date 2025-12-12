
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from src.routes.pays import router as pays_router
from src.routes.academie import router as academie_router
from src.db.database import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)


app.include_router(pays_router)
app.include_router(academie_router)

@app.get("/")
async def root(request: Request):
    return RedirectResponse(url="/docs")
