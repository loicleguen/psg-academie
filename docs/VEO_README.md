# Veo Module V1 - Football Analytics Platform

A full-stack football analytics application for managing teams, players, matches, and statistics with flexible metric tracking and advanced analytics.

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **API Docs**: OpenAPI/Swagger (auto-generated at `/docs`)

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Routing**: React Router
- **Charts**: Recharts
- **HTTP Client**: Axios

### Key Features
- ✅ Flexible EAV (Entity-Attribute-Value) metrics model
- ✅ Raw and derived metrics (computed on-demand)
- ✅ Team and player statistics tracking
- ✅ Analytics dashboard with KPIs, time series, and radar charts
- ✅ CRUD operations for seasons, teams, players, and matches
- ✅ Bulk data entry for metrics and participations
- ✅ Validation (percentages 0-100, no storing derived metrics)
- ✅ Docker Compose setup for easy deployment
- ✅ Match summary endpoint providing a single, Excel-like payload for frontend and export

## 📋 Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd PSG
cp .env.example .env
# Edit .env if needed (default values work for docker-compose)
```

### 2. Start with Docker Compose

```bash
# Build and start all services (PostgreSQL + API)
docker compose up -d --build

# Check logs
docker compose logs -f api

# The API will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

The startup script automatically:
- Waits for PostgreSQL to be ready
- Runs Alembic migrations
- Seeds metric definitions
- Starts the API server

### 3. Start Frontend (separately)

```bash
cd frontend
npm install
npm run dev

# Frontend will be available at http://localhost:5173
```

## 📊 Database Schema

### Core Entities

```
seasons
├── id, label, start_date, end_date

teams
├── id, name

players
├── id, team_id, first_name, last_name
├── main_position, secondary_positions

matches
├── id, team_id, season_id, date
├── opponent_name, is_home, match_type
├── competition, score_for, score_against
└── veo_title, veo_url, veo_duration, veo_camera

match_player_participations
├── id, match_id, player_id
├── is_starter, is_captain
└── minutes_played, position_played
```

### Flexible Metrics Model

```
metric_definitions
├── id, slug, label_fr, description_fr
├── scope (TEAM/PLAYER)
├── category (POSSESSION/PASSES/EVENTS/COMBINATIONS/GENERAL)
├── datatype (INT/FLOAT/PERCENT)
├── unit, side (OWN/OPPONENT/NONE)
└── is_derived, formula

team_match_metric_values
├── id, match_id, metric_id, side
└── value_number
   UNIQUE(match_id, metric_id, side)

player_match_metric_values
├── id, match_id, player_id, metric_id
└── value_number
   UNIQUE(match_id, player_id, metric_id)
```

## 🎯 API Endpoints

### CRUD Operations

```http
# Seasons
GET    /seasons
POST   /seasons
GET    /seasons/{id}

# Teams
GET    /teams
POST   /teams
GET    /teams/{id}

# Players
GET    /players?team_id={id}
POST   /players
GET    /players/{id}
PATCH  /players/{id}
DELETE /players/{id}

# Matches
GET    /matches?team_id={id}&season_id={id}&from={date}&to={date}
POST   /matches
GET    /matches/{id}
PATCH  /matches/{id}
DELETE /matches/{id}

# Participations
GET    /matches/{id}/participations
PUT    /matches/{id}/participations
POST   /matches/{id}/duplicate-participations/{source_id}
```

### Metrics Management

```http
# Metric Definitions
GET    /metrics?scope={TEAM|PLAYER}&category={...}&is_derived={bool}
GET    /metrics/{id}

# Team Metrics (per match)
GET    /metrics/matches/{id}/team-metrics
PUT    /metrics/matches/{id}/team-metrics

# Player Metrics (per match)
GET    /metrics/matches/{id}/player-metrics
PUT    /metrics/matches/{id}/player-metrics
```

### Analytics

```http
# Team KPIs (aggregated)
GET    /analytics/team/kpis
       ?team_id={id}
       &metrics=slug1,slug2,slug3
       &season_id={id}
       &from={date}&to={date}
       &compute_delta={bool}

# Time Series (last N matches)
GET    /analytics/team/timeseries
       ?team_id={id}
       &metric={slug}
       &last_n={10}

# Radar Chart (compare periods)
GET    /analytics/team/radar
       ?team_id={id}
       &metrics=slug1,slug2,...slug6
       &fromA={date}&toA={date}
       &fromB={date}&toB={date}

# Player Leaderboard
GET    /analytics/players/leaderboard
       ?team_id={id}
       &metric={slug}
       &season_id={id}
       &top_n={10}
```

### Match Summary (Excel replacement)

```http
GET /matches/{id}/summary
```

This endpoint returns a **single, structured payload** containing:

* match metadata (including VEO fields)
* player participations
* team metrics (OWN / OPPONENT)
* player metrics as an Excel-like grid (players × metrics)

It is designed to:

* replace manual Excel aggregation
* serve as the canonical payload for the frontend (Phase 2)
* act as the base for CSV/Excel export (Phase 3)

No derived metrics are computed here — only raw data.


## 📝 Sample API Payloads

### Create a Season

```bash
curl -X POST http://localhost:8000/seasons \
  -H "Content-Type: application/json" \
  -d '{
    "label": "2024-2025",
    "start_date": "2024-08-01",
    "end_date": "2025-06-30"
  }'
```

### Create a Team

```bash
curl -X POST http://localhost:8000/teams \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Paris Saint-Germain U17"
  }'
```

### Create a Player

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

### Bulk Update Participations

```bash
curl -X PUT http://localhost:8000/matches/1/participations \
  -H "Content-Type: application/json" \
  -d '{
    "participations": [
      {
        "player_id": 1,
        "is_starter": true,
        "is_captain": true,
        "minutes_played": 90,
        "position_played": "Attaquant"
      },
      {
        "player_id": 2,
        "is_starter": true,
        "is_captain": false,
        "minutes_played": 75,
        "position_played": "Milieu offensif"
      },
      {
        "player_id": 3,
        "is_starter": false,
        "is_captain": false,
        "minutes_played": 15,
        "position_played": "Attaquant"
      }
    ]
  }'
```

### Bulk Update Team Metrics

```bash
curl -X PUT http://localhost:8000/metrics/matches/1/team-metrics \
  -H "Content-Type: application/json" \
  -d '{
    "values": [
      {
        "metric_slug": "team_possession_pct",
        "side": "OWN",
        "value": 62.5
      },
      {
        "metric_slug": "team_goals_scored",
        "side": "OWN",
        "value": 3
      },
      {
        "metric_slug": "team_goals_conceded",
        "side": "OPPONENT",
        "value": 1
      },
      {
        "metric_slug": "team_shots",
        "side": "OWN",
        "value": 15
      },
      {
        "metric_slug": "team_shots_conceded",
        "side": "OPPONENT",
        "value": 8
      },
      {
        "metric_slug": "team_passes_completed",
        "side": "OWN",
        "value": 542
      }
    ]
  }'
```

### Bulk Update Player Metrics

```bash
curl -X PUT http://localhost:8000/metrics/matches/1/player-metrics \
  -H "Content-Type: application/json" \
  -d '{
    "values": [
      {
        "player_id": 1,
        "metric_slug": "player_goals",
        "value": 2
      },
      {
        "player_id": 1,
        "metric_slug": "player_shots",
        "value": 5
      },
      {
        "player_id": 1,
        "metric_slug": "player_goal_assists",
        "value": 1
      },
      {
        "player_id": 2,
        "metric_slug": "player_goals",
        "value": 1
      },
      {
        "player_id": 2,
        "metric_slug": "player_shots",
        "value": 3
      },
      {
        "player_id": 2,
        "metric_slug": "player_goal_assists",
        "value": 1
      }
    ]
  }'
```

### Get Team KPIs

```bash
curl "http://localhost:8000/analytics/team/kpis?team_id=1&metrics=team_possession_pct,team_goals_scored,team_conversion_rate,team_shots&season_id=1&compute_delta=true"
```

### Get Player Leaderboard

```bash
curl "http://localhost:8000/analytics/players/leaderboard?team_id=1&metric=player_goals&season_id=1&top_n=10"
```

## 🎨 Frontend Pages

### 1. Dashboard
- Season and date range selector
- 4 customizable KPI cards with delta indicators
- Bar chart showing last 10 matches for selected metric
- Radar chart comparing two time periods

### 2. Players
- List all players for selected team
- Create/edit player with positions
- Delete players
- Inline editing support

### 3. Matches
- List matches with filters (team, season, date range)
- Create new match
- Match detail page with 3 tabs:
  - **Participations**: Set starters, captain, minutes, positions
  - **Team Stats**: Dynamic form for all team metrics
  - **Player Stats**: Table with players × metrics grid

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_analytics.py -v
```

### Test Coverage

The test suite includes:
- ✅ Player derived metrics (attempts, conversion rate)
- ✅ Team KPI aggregation across matches
- ✅ Win rate calculation
- ✅ Zero-division handling
- ✅ Time series queries

## 📐 Seeded Metrics

### Player Metrics (16 total)

**GENERAL** (4 raw)
- `player_matches` - Matchs
- `player_starts` - Titulaire
- `player_captaincies` - Capitanats
- `player_motm` - Meilleur joueur du match

**EVENTS** (9 raw)
- `player_total_events` - Nombre total d'événements
- `player_goals` - Buts
- `player_shots` - Tirs
- `player_corners` - Corners
- `player_free_kicks` - Coups francs
- `player_goal_kicks` - Coups de pied de but
- `player_penalties` - Penaltys
- `player_goal_assists` - Goal assists
- `player_throw_ins` - Throw-ins

**COMBINATIONS** (3 derived - computed on demand)
- `player_attempts` = goals + shots
- `player_conversion_rate` = (goals / attempts) × 100
- `player_goal_involvements` = goals + assists

### Team Metrics (29 total)

**POSSESSION** (6 raw)
- `team_possession_pct` - Possession (%)
- `team_possession_minutes` - Possession (minutes)
- `team_possession_won` - Possessions gagnées
- `team_possession_third_def_pct` - Possession tiers défensif (%)
- `team_possession_third_mid_pct` - Possession tiers milieu (%)
- `team_possession_third_att_pct` - Possession tiers attaque (%)

**PASSES** (7 raw)
- `team_pass_zone_def_pct` - Passes zone défensive (%)
- `team_pass_zone_mid_pct` - Passes zone milieu (%)
- `team_pass_zone_att_pct` - Passes zone attaque (%)
- `team_passes_completed` - Passes réussies
- `team_sequences_3_5` - Séquences 3-5 passes
- `team_sequences_6_plus` - Séquences 6+ passes
- `team_longest_sequence` - Séquence la plus longue

**EVENTS** (10 raw)
- `team_goals_scored` - Buts marqués (OWN)
- `team_goals_conceded` - Buts encaissés (OPPONENT)
- `team_free_kicks` - Coups francs
- `team_shots` - Tirs
- `team_shots_conceded` - Tirs encaissés
- `team_corners` - Corners
- `team_goal_kicks` - Coups de pied de but
- `team_throw_ins` - Throw-ins

**COMBINATIONS** (6 derived)
- `team_attempts` = goals_scored + shots
- `team_conversion_rate` = (goals_scored / attempts) × 100
- `team_attempts_conceded` = goals_conceded + shots_conceded
- `team_offensive_events` = goals_scored + corners + free_kicks + shots
- `team_defensive_events` = goals_conceded + shots_conceded
- `team_win_rate` = (wins / total_matches) × 100

## 🔒 Validation Rules

1. **Percentage values**: Must be between 0 and 100
2. **Derived metrics**: Cannot be stored manually (computed server-side)
3. **Metric scope**: Team metrics only for team endpoints, player metrics for player endpoints
4. **Participations**: All players must belong to match's team

## 🔮 Future Enhancements (V2)

- 🔐 JWT authentication with role-based access (admin/coach/player-readonly)
- 📊 Export to CSV/Excel
- 📸 Veo API integration for automatic video parsing
- 📱 Mobile responsive design
- 🌍 Multi-language support (English/French)
- 🎥 Video clips linked to events
- 📈 Season-over-season comparisons
- 🏆 Multi-team support with league standings

## 🛠️ Development

### Local Backend Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+psycopg://veo_user:veo_password@postgres:5432/veo_db"

# Run migrations
alembic upgrade head

# Seed data
python -m app.seed

# Start server
uvicorn app.main:app --reload --port 8000
```

### Create New Migration

```bash
alembic revision --autogenerate -m "description of changes"
alembic upgrade head
```

### Add New Metrics

Edit `app/seed.py` and add to `PLAYER_METRICS` or `TEAM_METRICS` list, then run:

```bash
python -m app.seed
```

---

## 🧠 Module VEO — Architecture DB & Garanties (V1)

Cette section décrit les choix structurants du module VEO V1, ainsi que les garanties mises en place côté base de données et API.

---

## 🎯 Philosophie V1

Le module VEO V1 est conçu pour :

* **Remplacer la saisie Excel** par une saisie manuelle structurée
* **Stocker uniquement des données brutes (raw)** en base
* **Calculer les métriques dérivées à la demande** côté backend (analytics)
* Garantir la **cohérence des données**, même en cas d’accès direct à la base

➡️ Principe fondamental :

> **Les métriques dérivées ne sont jamais stockées en base.**

---

## 🗄️ Base de données

* **SGBD** : PostgreSQL 16+
* **ORM** : SQLAlchemy 2.0
* **Migrations** : Alembic
* **Mode d’exécution** : Docker-first

### Tables principales

* `seasons`, `teams`, `players`, `matches`
* `match_player_participations`
* `metric_definitions`
* `team_match_metric_values`
* `player_match_metric_values`

Le modèle repose sur un **schéma EAV maîtrisé**, avec :

* définitions de métriques centralisées (`metric_definitions`)
* valeurs stockées par match / joueur / équipe
* support OWN / OPPONENT pour les stats équipe

---

## 🔒 Garanties de cohérence (DB-level)

Même si l’API applique déjà des validations, des **protections supplémentaires existent au niveau PostgreSQL**.

### 1️⃣ Interdiction de stocker des métriques dérivées

Un **trigger PostgreSQL** empêche toute insertion ou mise à jour d’une métrique marquée `is_derived = true`.

✔️ Protège contre :

* insertions SQL manuelles
* bugs applicatifs futurs
* mauvaises migrations

Fonction utilisée :

* `prevent_derived_metric_values()`

Triggers actifs :

* `trg_prevent_derived_team_values`
* `trg_prevent_derived_player_values`

---

### 2️⃣ Validation des métriques de type PERCENT (0–100)

Un **trigger PostgreSQL dédié** empêche toute valeur hors plage `[0, 100]` pour les métriques de type `PERCENT`.

✔️ Validation assurée :

* côté backend (API)
* **et côté base** (DB hardening)

Fonction utilisée :

* `enforce_percent_range()`

Triggers actifs :

* `trg_enforce_percent_team_values`
* `trg_enforce_percent_player_values`

---

## ⚡ Performance & Indexation

Des indexes spécifiques ont été ajoutés pour les cas d’usage analytics :

### Index “métier” (V1)

* `matches(team_id, season_id, date)`
* `players(team_id)`
* `match_player_participations(match_id)`
* `match_player_participations(player_id)`
* `team_match_metric_values(metric_id, match_id, side)`
* `player_match_metric_values(metric_id, match_id)`
* `player_match_metric_values(player_id, match_id)`

### Index partiel (optimisation V2 anticipée)

Un **index partiel PostgreSQL** existe pour accélérer les dashboards :

* `team_match_metric_values(metric_id, match_id) WHERE side = 'OWN'`

➡️ Optimisé pour les lectures analytics courantes (stats équipe).

---

## 🧪 Tests end-to-end (preuve fonctionnelle V1)

Un **script E2E reproductible** valide le fonctionnement complet du module VEO :

* création saison / équipe / joueur
* création match avec métadonnées VEO
* saisie participations
* saisie métriques équipe & joueur
* lecture analytics avec métriques dérivées
* vérification que les dérivées **ne sont pas stockées**

📄 Script :

```bash
scripts/e2e_veo_v1.sh
```

Ce script est conçu pour :

* être rejouable localement
* servir de base pour une future CI
* garantir que la règle “raw-only” est respectée

---

## ✅ État du module VEO V1

✔️ Base de données prête
✔️ API fonctionnelle
✔️ Règles métier sécurisées (API + DB)
✔️ Analytics calculées à la demande
✔️ Remplacement Excel techniquement validé


➡️ Le module est **prêt pour la saisie manuelle frontend** et peut déjà être utilisé
comme **source unique de vérité pour remplacer les fichiers Excel existants**.


## 📄 License

This project is part of PSG's internal analytics system.

## 👥 Support

For questions or issues, contact the development team.
