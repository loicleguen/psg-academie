# Getting Started with Veo Module V1

This guide will help you set up and run the Veo football analytics platform.

## Prerequisites

Before starting, ensure you have:

- **Docker Desktop** (recommended) or Docker + Docker Compose
- **Node.js 18+** and npm
- **Git**

## Step-by-Step Setup

### 1. Initial Configuration

```bash
# Navigate to the project directory
cd PSG

# Create environment file from template
cp .env.example .env

# The default .env values work for Docker setup
# No changes needed unless you want custom settings
```

### 2. Start Backend Services

```bash
# Build and start PostgreSQL database + API
docker compose up -d --build

# Watch logs to ensure everything starts correctly
docker-compose logs -f api

# You should see:
# - "Waiting for database..."
# - Migration messages
# - "Seeded X metric definitions"
# - "Uvicorn running on http://0.0.0.0:8000"
```

The backend will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (interactive Swagger UI)
- **Redoc**: http://localhost:8000/redoc

### 3. Start Frontend

Open a new terminal:

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The frontend will be available at:
- **App**: http://localhost:5173

### 4. Verify Installation

1. Open http://localhost:8000/docs in your browser
2. Try the `/health` endpoint - should return `{"status": "healthy"}`
3. Check `/metrics` endpoint - should return the seeded metric definitions
4. Open http://localhost:5173 - you should see the Veo Analytics dashboard

## First Steps

### Create Your First Team

**Option A: Using the API docs (http://localhost:8000/docs)**

1. Find the `POST /seasons` endpoint
2. Click "Try it out"
3. Enter:
   ```json
   {
     "label": "2024-2025",
     "start_date": "2024-08-01",
     "end_date": "2025-06-30"
   }
   ```
4. Click "Execute"

5. Then create a team at `POST /teams`:
   ```json
   {
     "name": "PSG U17"
   }
   ```

**Option B: Using curl**

```bash
# Create season
curl -X POST http://localhost:8000/seasons \
  -H "Content-Type: application/json" \
  -d '{
    "label": "2024-2025",
    "start_date": "2024-08-01",
    "end_date": "2025-06-30"
  }'

# Create team
curl -X POST http://localhost:8000/teams \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PSG U17"
  }'
```

**Option C: Using the Frontend**

The frontend pages will automatically handle creation through forms.

### Add Players

Using the frontend:
1. Navigate to "Joueurs" (Players)
2. Click "+ Nouveau joueur"
3. Fill in the form:
   - Prénom: Kylian
   - Nom: Mbappé
   - Position principale: Attaquant
   - Positions secondaires: Ailier gauche (optional)
4. Click "Créer"

Or via API:
```bash
curl -X POST http://localhost:8000/players \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": 1,
    "first_name": "Kylian",
    "last_name": "Mbappé",
    "main_position": "Attaquant",
    "secondary_positions": "Ailier gauche, Ailier droit"
  }'
```

### Create a Match

Using the frontend:
1. Navigate to "Matchs" (Matches)
2. Click "+ Nouveau match"
3. Fill in the form
4. Click "Créer"

Or via API:
```bash
curl -X POST http://localhost:8000/matches \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": 1,
    "season_id": 1,
    "date": "2024-09-15",
    "opponent_name": "Olympique de Marseille",
    "is_home": true,
    "match_type": "LEAGUE",
    "competition": "Ligue 1",
    "score_for": 3,
    "score_against": 1
  }'
```

### Add Match Data

1. In the Matches list, click "Détails" on a match
2. Use the three tabs:

   **Participations Tab:**
   - Check "Titulaire" for starting players
   - Check "Capitaine" for the captain
   - Enter minutes played
   - Enter position played
   - Click "Sauvegarder"

   **Stats équipe Tab:**
   - Fill in team statistics (possession, goals, shots, etc.)
   - Values are validated (e.g., percentages must be 0-100)
   - Click "Sauvegarder"

   **Stats joueurs Tab:**
   - Fill in player statistics in the table
   - Each row is a player, columns are metrics
   - Click "Sauvegarder"

### View Analytics

Go back to the Dashboard:
1. Select your team and season
2. The KPI cards will show aggregated statistics
3. The bar chart shows trends over the last 10 matches
4. Use the radar chart to compare two time periods

## Troubleshooting

### Backend won't start

```bash
# Check if PostgreSQL is ready
docker compose exec -T postgres pg_isready -U veo_user -d veo_db

# Check API logs
docker-compose logs api

# Restart services
docker-compose restart api
```

### Frontend can't connect to API

1. Make sure backend is running: http://localhost:8000/health
2. Check Vite proxy configuration in `frontend/vite.config.js`
3. Try hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

### Database errors

```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d

# This will recreate the database with fresh migrations
```

### Port conflicts

If ports 8000, 3306, or 5173 are already in use:

1. Edit `docker-compose.yml` to change ports:
   ```yaml
   ports:
     - "8001:8000"  # Change 8000 to 8001
   ```

2. Edit `frontend/vite.config.js`:
   ```javascript
   server: {
     port: 5174,  // Change 5173 to 5174
   }
   ```

## Development Workflow

### Making Code Changes

**Backend changes:**
- The API auto-reloads when you edit files in `app/`
- No restart needed

**Frontend changes:**
- Vite auto-reloads when you edit files in `frontend/src/`
- No restart needed

### Adding New Metrics

1. Edit `app/seed.py`
2. Add your metric to `PLAYER_METRICS` or `TEAM_METRICS`
3. Run the seed script:
   ```bash
   docker-compose exec api python -m app.seed
   ```

### Database Migrations

When you change models:

```bash
# Generate migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Apply migration
docker-compose exec api alembic upgrade head
```

## Useful Commands

```bash
# View all running containers
docker-compose ps

# Stop all services
docker-compose down

# View API logs
docker-compose logs -f api

# Access PostgreSQL
docker compose exec -it postgres psql -U veo_user -d veo_db

# Access Python shell
docker-compose exec api python

# Run tests
docker-compose exec api pytest

# Rebuild after major changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Add more data**: Create multiple matches with statistics
3. **Use analytics**: Try different KPIs and time periods on the dashboard
4. **Customize metrics**: Add your own metrics in `app/seed.py`
5. **Read the full README**: Check `README.md` for complete documentation

## Getting Help

- Check the logs: `docker-compose logs -f api`
- Review API docs: http://localhost:8000/docs
- Read the full README.md
- Check database state: Use a PostgreSQL client to connect to localhost:3306

## Sample Data Script (Optional)

Want to quickly populate with sample data?

```bash
# Create a sample data script
cat > load_sample_data.sh << 'EOF'
#!/bin/bash

# Create season
curl -X POST http://localhost:8000/seasons \
  -H "Content-Type: application/json" \
  -d '{"label": "2024-2025", "start_date": "2024-08-01", "end_date": "2025-06-30"}'

# Create team
curl -X POST http://localhost:8000/teams \
  -H "Content-Type: application/json" \
  -d '{"name": "PSG U17"}'

# Create players
for i in {1..5}; do
  curl -X POST http://localhost:8000/players \
    -H "Content-Type: application/json" \
    -d "{\"team_id\": 1, \"first_name\": \"Player\", \"last_name\": \"$i\", \"main_position\": \"Attaquant\"}"
done

echo "Sample data loaded!"
EOF

chmod +x load_sample_data.sh
./load_sample_data.sh
```

Happy analyzing! ⚽📊
