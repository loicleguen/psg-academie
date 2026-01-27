from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import seasons, teams, players, matches, metrics, analytics

app = FastAPI(
    title="Veo Module V1 API",
    description="Football analytics platform for team and player statistics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(seasons.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(metrics.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {
        "message": "Veo Module V1 API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
