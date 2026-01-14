
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from src.routes.country import router as country_router
from src.routes.academy import router as academy_router
from src.routes.team import router as team_router
from src.routes.player import router as player_router
from src.routes.catapult import router as catapult_router
from src.routes.auth import router as auth_router
from src.db.database import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)


app.include_router(auth_router)
app.include_router(country_router)
app.include_router(academy_router)
app.include_router(team_router)
app.include_router(player_router)
app.include_router(catapult_router)

@app.get("/")
async def root(request: Request):
    return RedirectResponse(url="/docs")
