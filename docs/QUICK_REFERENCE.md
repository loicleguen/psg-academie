# Veo Module V1 - Quick Reference

## 🚀 Start/Stop

```bash
# Start everything
docker-compose up -d && cd frontend && npm run dev

# Stop everything
docker-compose down

# View logs
docker-compose logs -f api
```

## 🔗 URLs

- Frontend: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: internal (PostgreSQL via Docker network)

## 📁 Project Structure

```
PSG/
├── app/                    # Backend (FastAPI)
│   ├── main.py            # API entry point
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── seed.py            # Metric definitions seed
│   ├── routes/            # API endpoints
│   │   ├── seasons.py
│   │   ├── teams.py
│   │   ├── players.py
│   │   ├── matches.py
│   │   ├── metrics.py
│   │   └── analytics.py
│   └── services/
│       └── analytics.py   # Derived metrics logic
├── alembic/               # Database migrations
├── frontend/              # React app
│   └── src/
│       ├── pages/         # Dashboard, Players, Matches
│       └── api/           # API client
├── tests/                 # Python tests
├── docker-compose.yml     # Container orchestration
└── requirements.txt       # Python dependencies
```

## 🎯 Key Endpoints

### CRUD
```
GET/POST  /seasons
GET/POST  /teams
GET/POST/PATCH/DELETE  /players
GET/POST/PATCH/DELETE  /matches
GET/PUT   /matches/{id}/participations
```

### Metrics
```
GET       /metrics
GET/PUT   /metrics/matches/{id}/team-metrics
GET/PUT   /metrics/matches/{id}/player-metrics
```

### Analytics
```
GET  /analytics/team/kpis
GET  /analytics/team/timeseries
GET  /analytics/team/radar
GET  /analytics/players/leaderboard
```

## 📊 Sample Data Flow

1. **Create Season** → `POST /seasons`
2. **Create Team** → `POST /teams`
3. **Add Players** → `POST /players`
4. **Create Match** → `POST /matches`
5. **Set Participations** → `PUT /matches/{id}/participations`
6. **Add Team Stats** → `PUT /metrics/matches/{id}/team-metrics`
7. **Add Player Stats** → `PUT /metrics/matches/{id}/player-metrics`
8. **View Analytics** → `GET /analytics/team/kpis`

## 🔧 Common Commands

```bash
# Backend
docker-compose exec api python -m app.seed    # Re-seed metrics
docker-compose exec api alembic upgrade head  # Apply migrations
docker-compose exec api pytest                # Run tests

# Frontend
cd frontend && npm run dev                    # Start dev server
cd frontend && npm run build                  # Build for production

# Database
docker compose exec -it postgres psql -U veo_user -d veo_db
```

## 📐 Metric Categories

### Player Metrics (16)
- **GENERAL**: matches, starts, captaincies, motm
- **EVENTS**: goals, shots, corners, free_kicks, penalties, assists, throw_ins
- **DERIVED**: attempts, conversion_rate, goal_involvements

### Team Metrics (29)
- **POSSESSION**: possession_pct, possession_minutes, thirds
- **PASSES**: zones, completed, sequences
- **EVENTS**: goals, shots, corners, free_kicks
- **DERIVED**: attempts, conversion_rate, offensive/defensive_events, win_rate

## 🎨 Frontend Pages

1. **Dashboard** (`/`)
   - Season/date filters
   - 4 KPI cards
   - Time series chart
   - Radar comparison

2. **Players** (`/players`)
   - List + CRUD
   - Position management

3. **Matches** (`/matches`)
   - List with filters
   - Match detail with tabs:
     - Participations
     - Team Stats
     - Player Stats

## ⚠️ Validation Rules

- Percentages: 0-100 only
- Derived metrics: Read-only (computed)
- Unique constraints: match+player, match+metric+side

## 🐛 Troubleshooting

```bash
# Reset everything
docker-compose down -v && docker-compose up -d

# Check API health
curl http://localhost:8000/health

# Check metrics seeded
curl http://localhost:8000/metrics | jq length

# Frontend not loading?
# 1. Check API is running
# 2. Clear browser cache
# 3. Restart Vite: Ctrl+C then npm run dev
```

## 📝 Environment Variables

```bash
# .env
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

## 🔐 Auth (Future V2)

Currently no authentication required.
Placeholder for JWT in `app/config.py`:
```python
# JWT_SECRET=your-secret-key
# JWT_ALGORITHM=HS256
```

## 📚 Resources

- Full docs: `README.md`
- Getting started: `GETTING_STARTED.md`
- API docs: http://localhost:8000/docs
- Tests: `tests/test_analytics.py`
