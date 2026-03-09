<h1 align="center">PSG Académie - Plateforme d'Analyse Football</h1>
<div align="center">
  <img src="frontend/public/images/imgbackground.png" alt="PSG Académie" width="100%">
</div>

<div align="center">
   Plateforme d'analyse complète pour le suivi physique et tactique des joueurs de l'académie PSG, intégrant les données GPS Catapult et les statistiques de match Veo.
</div>

## 📋 Table des matières

- [Diagramme de classes](#diagramme-de-classes)
- [Diagrammes de séquence](#diagrammes-de-séquence)
---
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Démarrage rapide](#démarrage-rapide)
- [Architecture](#architecture)
- [Fonctionnalités](#fonctionnalités)
- [Structure du projet](#structure-du-projet)
- [Commandes utiles](#commandes-utiles)
- [Développement Frontend](#développement-frontend)
- [Documentation](#documentation)
- [Workflow de développement](#workflow-de-développement)
- [Tests](#tests)
---
- [Auteurs](#auteurs)

## [Diagramme de classes](#-table-des-matières)
### Database Schema (PostgreSQL)
```mermaid
erDiagram
    COUNTRY ||--o{ COUNTRY_ACADEMY : "contains"
    COUNTRY_ACADEMY ||--o{ ACADEMY_TEAM : "contains"
    ACADEMY_TEAM ||--o{ TEAM_HUB : "contains"
    TEAM_HUB ||--o{ USER : "has"
    TEAM_HUB ||--o{ PLAYER_CARD : "manages"
    TEAM_HUB ||--o{ COLLECTIVE_SQUAD_STATS : "calculates"
    TEAM_HUB ||--o{ TRAINING_CALENDAR : "plans"
    TEAM_HUB ||--o{ DATA_IMPORT : "receives"
    
    PLAYER_CARD ||--|| PLAYER_PROFILE : "has"
    PLAYER_CARD ||--|| PLAYER_POSITION : "has"
    PLAYER_CARD ||--o{ MATCH_STATISTIC : "records"
    PLAYER_CARD ||--o{ PHYSICAL_STATISTIC : "measures"
    PLAYER_CARD ||--o{ ALERT : "generates"
    
    USER ||--o{ ALERT : "receives"
    USER ||--o{ DATA_IMPORT : "performs"
    USER ||--o{ DATA_EXPORT : "generates"
    
    COUNTRY {
        int id PK
        string name
        string iso_code
        datetime created_at
        datetime updated_at
    }
    
    COUNTRY_ACADEMY {
        int id PK
        string name
        string city
        int country_id FK
        datetime created_at
        datetime updated_at
    }
    
    ACADEMY_TEAM {
        int id PK
        string name
        string category
        int academy_id FK
        datetime created_at
        datetime updated_at
    }
    
    TEAM_HUB {
        int id PK
        string name
        string description
        int team_id FK
        datetime created_at
        datetime updated_at
    }
    
    USER {
        int id PK
        string last_name
        string first_name
        string email UK
        string password_hash
        string role
        int hub_id FK
        datetime created_at
        datetime updated_at
    }
    
    PLAYER_CARD {
        int id PK
        int hub_id FK
        int jersey_number
        string status
        datetime created_at
        datetime updated_at
    }
    
    PLAYER_PROFILE {
        int id PK
        int player_card_id FK
        string last_name
        string first_name
        date birth_date
        int age
        float height
        float weight
        string nationality
        string preferred_foot
        datetime created_at
        datetime updated_at
    }
    
    PLAYER_POSITION {
        int id PK
        int player_card_id FK
        string main_position
        string secondary_positions
        datetime created_at
        datetime updated_at
    }
    
    MATCH_STATISTIC {
        int id PK
        int player_card_id FK
        date match_date
        string opponent
        int minutes_played
        int goals
        int assists
        int shots_on_target
        int successful_passes
        int duels_won
        float match_rating
        string veo_url
        string activity_zones
        datetime created_at
        datetime updated_at
    }
    
    PHYSICAL_STATISTIC {
        int id PK
        int player_card_id FK
        date test_date
        string test_type
        float vma
        float max_speed
        float total_distance
        int sprints
        float endurance
        float strength
        float flexibility
        datetime created_at
        datetime updated_at
    }
    
    ALERT {
        int id PK
        int player_card_id FK
        int user_id FK
        string type
        string priority
        string message
        datetime creation_date
        boolean read
        datetime read_date
    }
    
    COLLECTIVE_SQUAD_STATS {
        int id PK
        int hub_id FK
        int total_squad
        float average_age
        float average_height
        date calculation_date
        datetime created_at
    }
    
    TRAINING_CALENDAR {
        int id PK
        int hub_id FK
        string title
        datetime session_date
        int duration
        string session_type
        string location
        datetime created_at
        datetime updated_at
    }
    
    DATA_IMPORT {
        int id PK
        int user_id FK
        int hub_id FK
        string file_name
        string file_type
        string status
        int lines_processed
        datetime import_date
    }
    
    DATA_EXPORT {
        int id PK
        int user_id FK
        string export_type
        string format
        datetime export_date
        string file_path
    }
```
### Description des Tables de la Base de Données

**Tables Principales :**

1. **COUNTRY** : Stocke les pays où se trouvent les académies
2. **COUNTRY_ACADEMY** : Académies de football par pays
3. **ACADEMY_TEAM** : Équipes au sein d'une académie
4. **TEAM_HUB** : Hub de gestion pour chaque équipe
5. **USER** : Utilisateurs du système (entraîneurs, admins, analystes)
6. **PLAYER_CARD** : Fiche centrale regroupant toutes les informations d'un joueur
7. **PLAYER_PROFILE** : Informations personnelles du joueur
8. **PLAYER_POSITION** : Positions du joueur sur le terrain
9. **MATCH_STATISTIC** : Statistiques détaillées par match
10. **PHYSICAL_STATISTIC** : Tests physiques et métriques athlétiques
11. **ALERT** : Alertes de performance pour les entraîneurs
12. **COLLECTIVE_SQUAD_STATS** : Statistiques collectives de l'équipe
13. **TRAINING_CALENDAR** : Calendrier des entraînements
14. **DATA_IMPORT** : Historique des imports de données
15. **DATA_EXPORT** : Historique des exports (PDF, CSV)

**Contraintes et Index :**
- Clés Primaires (PK) sur toutes les colonnes id
- Clés Étrangères (FK) pour maintenir l'intégrité référentielle
- Clé Unique (UK) sur user.email
- Index sur les colonnes fréquemment recherchées (match_date, test_date, player_card_id)
- Suppression en cascade sur certaines relations (ex : supprimer une player_card supprime ses statistiques)

## [Diagrammes de Séquence](#-table-des-matières)

Ces diagrammes de séquence illustrent les principales interactions entre les composants du système pour les fonctionnalités critiques du MVP, incluant la gestion des erreurs et les codes HTTP appropriés.

### Cas d'utilisation 1 : Authentification Utilisateur

```mermaid
sequenceDiagram
    actor Coach
    participant Frontend as React Frontend
    participant Nginx
    participant Backend as FastAPI Backend
    participant DB as PostgreSQL
    
    Coach->>Frontend: Enter credentials (email, password)
    Frontend->>Frontend: Validate form inputs
    Frontend->>Nginx: POST /api/auth/login
    Nginx->>Backend: Forward request
    Backend->>DB: Query user by email
    DB-->>Backend: Return user data
    
    alt User found and password correct
        Backend->>Backend: Verify password hash
        Backend->>Backend: Generate JWT token
        Backend-->>Nginx: 200 OK + JWT + user info
        Nginx-->>Frontend: Return JWT token
        Frontend->>Frontend: Store JWT in localStorage
        Frontend->>Frontend: Redirect to Dashboard
        Frontend-->>Coach: Display Dashboard
    else User not found
        Backend-->>Nginx: 404 Not Found
        Nginx-->>Frontend: Error response
        Frontend-->>Coach: Show "User not found" error
    else Wrong password
        Backend-->>Nginx: 401 Unauthorized
        Nginx-->>Frontend: Error response
        Frontend-->>Coach: Show "Invalid credentials" error
    else Invalid input
        Backend-->>Nginx: 400 Bad Request
        Nginx-->>Frontend: Error response
        Frontend-->>Coach: Show validation errors
    end
    
    Note over Coach,DB: Subsequent requests include JWT in Authorization header
```
**Authentification Utilisateur :**
- L'entraîneur saisit ses identifiants
- Le frontend valide et envoie les données au backend via Nginx
- Le backend vérifie les identifiants dans la base de données
- **Cas de succès :** Token JWT généré et renvoyé au frontend, token stocké pour les requêtes suivantes
- **Cas d'erreur :**
  - 404 Not Found : L'utilisateur n'existe pas
  - 401 Unauthorized : Mot de passe incorrect
  - 400 Bad Request : Format de saisie invalide

### Cas d'utilisation 2 : Consultation du Tableau de Bord de Performance d'un Joueur

```mermaid
sequenceDiagram
    actor Coach
    participant Frontend as React Frontend
    participant Nginx
    participant Backend as FastAPI Backend
    participant Redis as Redis Cache
    participant DB as PostgreSQL
    
    Coach->>Frontend: Click on player card
    Frontend->>Nginx: GET /api/players/{player_id}
    Nginx->>Backend: Forward request
    Backend->>Backend: Validate JWT token
    
    alt Valid JWT
        Backend->>Redis: Check cache for player data
        
        alt Cache hit
            Redis-->>Backend: Return cached data
            Backend-->>Nginx: 200 OK + player data
        else Cache miss
            Backend->>DB: Query player profile
            
            alt Player exists
                DB-->>Backend: Return profile data
                Backend->>DB: Query match statistics
                DB-->>Backend: Return match stats
                Backend->>DB: Query physical statistics
                DB-->>Backend: Return physical stats
                Backend->>Backend: Aggregate data
                Backend->>Redis: Store in cache (TTL: 5 min)
                Backend-->>Nginx: 200 OK + player data (JSON)
            else Player not found
                DB-->>Backend: No data
                Backend-->>Nginx: 404 Not Found
                Nginx-->>Frontend: Error response
                Frontend-->>Coach: Show "Player not found"
            end
        end
        
        Nginx-->>Frontend: Return player data
        Frontend->>Frontend: Render PlayerDetail component
        Frontend->>Frontend: Generate charts
        Frontend-->>Coach: Display player dashboard
    else Invalid/Expired JWT
        Backend-->>Nginx: 401 Unauthorized
        Nginx-->>Frontend: Auth error
        Frontend-->>Coach: Redirect to login
    end
```
**Consultation du Tableau de Bord de Performance d'un Joueur :**
- L'entraîneur sélectionne un joueur
- Le backend valide le token JWT
- Le backend vérifie d'abord le cache Redis (optimisation des performances)
- En cas de cache manquant, interroge PostgreSQL pour toutes les données du joueur
- Les données sont agrégées et mises en cache pour les requêtes futures
- Le frontend reçoit les données et affiche le tableau de bord avec les graphiques
- **Cas de succès :** L'entraîneur consulte les statistiques complètes du joueur
- **Cas d'erreur :**
  - 404 Not Found : Le joueur n'existe pas
  - 401 Unauthorized : Token JWT invalide ou expiré


## 🔧 [Prérequis](#-table-des-matières)
Avant de commencer, assurez-vous d'avoir installé :
- **Git** - [Télécharger Git](#https://git-scm.com/install/)
- **Docker** (version 20.10 ou supérieure) - [Télécharger Docker](#https://docs.docker.com/get-started/get-docker/)
- **Docker Compose** (pour développement local) - Inclus avec Docker Desktop
- **Node.js 18+** (pour développement frontend local) - [Télécharger Node.js](#https://nodejs.org/fr)
- **Python 3.11+** (optionnel, pour développement backend local)

Vérifier les installations :
```bash
git --version
docker --version
docker-compose --version
node --version
npm --version
```

## 🚀 [Installation](#-table-des-matières)

1. Cloner le repository
```bash
# Cloner le projet sur la branche loic
git clone -b loic https://github.com/loicleguen/psg-academie.git
cd psg-academie
```
Ou si vous avez déjà cloné le repo :
```bash
git clone https://github.com/loicleguen/psg-academie.git
cd psg-academie
git checkout loic
```

2. Vérifier la structure
```bash
# Lister les dossiers principaux
ls -la
# Vous devriez voir : backend-catapult, backend-veo, frontend, docker-compose.yml
```

3. Lancer tous les services
```bash
# Construire et démarrer tous les conteneurs Docker
docker-compose up -d --build
```
Cette commande va :
   - 🐳 Construire les images Docker pour les backends et le frontend
   - 🗄️ Créer et démarrer les bases de données PostgreSQL
   - ⚡ Lancer les APIs FastAPI (Catapult & Veo)
   - 🌐 Démarrer le serveur Nginx
   - 🔄 Orchestrer tout automatiquement

4. Vérifier que tout fonctionne
```bash
# Vérifier l'état des conteneurs
docker-compose ps

# Voir les logs en temps réel
docker-compose logs -f

# Voir les logs d'un service spécifique
docker-compose logs -f backend-catapult
docker-compose logs -f backend-veo
docker-compose logs -f frontend
```

## 🌐 [Démarrage rapide](#-table-des-matières)

Une fois les services démarrés, accédez à :

|Service	            |URL	                            |Description                       |
|--------------------|---------------------------------|----------------------------------|
|Frontend 🎨        |http://localhost                  |Interface utilisateur principale  |
|API Catapult 🏃    |http://localhost/api/physical/    |API données physiques GPS         |
|API Veo ⚽         |http://localhost/api/tactical/    |API données tactiques matchs      |
|Docs Catapult 📚   |http://localhost/api/physical/docs|Documentation Swagger API Catapult|
|Docs Veo 📚        |http://localhost/api/tactical/docs|Documentation Swagger API Veo     |


## 🏗️ [Architecture](#-table-des-matières)

Cette plateforme intègre **deux systèmes d'analyse complémentaires** :

### 🏃 Backend Catapult (Analyse Physique)
- **Données** : GPS, distance, vitesse, accélération, charge physique
- **Base de données** : PostgreSQL 16 (psg_db_catapult)
- **API** : FastAPI + SQLModel
- **Route** : `/api/physical/*` (via nginx)
- **Port interne** : 8000

### ⚽ Backend Veo (Analyse Tactique)
- **Données** : Matchs, buts, passes, statistiques tactiques
- **Base de données** : PostgreSQL 16 (psg_db_veo)
- **API** : FastAPI + SQLAlchemy
- **Route** : `/api/tactical/*` (via nginx)
- **Port interne** : 8001

### 🎨 Frontend
- **Framework** : React 18 + Vite
- **UI** : Interface de visualisation des données et génération de rapports
- **Graphiques** : Recharts pour les visualisations
- **Routing** : React Router

### 🔀 Nginx (Reverse Proxy)
- **Ports** : 80 (HTTP) / 443 (HTTPS)
- Routage automatique vers le bon backend selon l'URL
- Service du frontend React en production


## 📊 [Fonctionnalités](#-table-des-matières)

### Module Catapult (Physique)
- ✅ Upload de fichiers CSV Catapult
- ✅ Parsing automatique des données GPS
- ✅ Détection des phases d'entraînement (échauffement, match, cool-down)
- ✅ Génération de graphiques :
  - Comparaison entre joueurs (distance, vitesse, charge)
  - Distribution par zones de vitesse
  - Timeline d'intensité
  - Breakdown de distance
  - Radar de performance multi-métriques
- ✅ Analyse de sessions et de joueurs individuels
- ✅ Export de rapports PDF

### Module Veo (Tactique)
- ✅ Gestion des saisons, équipes et joueurs
- ✅ Suivi des matchs et participations
- ✅ Métriques flexibles (EAV model)
  - Métriques brutes (saisies manuellement)
  - Métriques dérivées (calculées à la volée)
- ✅ Analytics avancées :
  - KPIs d'équipe
  - Time series pour analyse temporelle
  - Radar charts pour comparaisons
  - Leaderboards joueurs
- ✅ Validation des données (pourcentages 0-100)
- ✅ Export de résumés de match (format Excel-like)


## 📁 [Structure du Projet](#-table-des-matières)

```
psg-academie/
├── backend-catapult/          # Backend données physiques
│   ├── app.py                 # Point d'entrée FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   ├── models/            # Modèles SQLModel
│   │   ├── routes/            # Endpoints API
│   │   └── services/          # Logique métier
│   └── migrations/            # Migrations Alembic
│
├── backend-veo/               # Backend données tactiques
│   ├── app/
│   │   ├── main.py            # Point d'entrée FastAPI
│   │   ├── models.py          # Modèles SQLAlchemy
│   │   ├── routes/            # Endpoints API
│   │   └── services/          # Logique métier & analytics
│   ├── alembic/               # Migrations
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                  # Application React
│   ├── src/
│   │   ├── components/        # Composants UI
│   │   ├── App.jsx           # Application principale
│   │   └── assets/           # Ressources statiques
│   ├── package.json
│   └── vite.config.js
│
├── nginx.conf                 # Configuration reverse proxy
├── docker-compose.yml         # Orchestration des services
├── certs/                     # Certificats SSL
└── docs/                      # Documentation
    ├── GETTING_STARTED.md     # Guide de démarrage
    ├── CATAPULT_README.md     # Documentation Catapult
    ├── VEO_README.md          # Documentation Veo
    └── QUICK_REFERENCE.md     # Référence rapide
```

## 🔧 [Commandes Utiles](#-table-des-matières)

### Docker

```bash
# Démarrer tous les services
docker-compose up -d --build

# Arrêter tous les services
docker-compose down

# Voir les logs
docker-compose logs -f                    # Tous les services
docker-compose logs -f backend-catapult   # Backend Catapult uniquement
docker-compose logs -f backend-veo        # Backend Veo uniquement

# Redémarrer un service spécifique
docker-compose restart backend-catapult
docker-compose restart backend-veo

# Exécuter des commandes dans un conteneur
docker-compose exec backend-catapult bash
docker-compose exec backend-veo bash
```

### Base de données

```bash
# Migrations Catapult
docker-compose exec backend-catapult alembic upgrade head
docker-compose exec backend-catapult alembic revision --autogenerate -m "description"

# Migrations Veo
docker-compose exec backend-veo alembic upgrade head
docker-compose exec backend-veo alembic revision --autogenerate -m "description"

# Accès direct à PostgreSQL
docker-compose exec db-catapult psql -U psguser -d psgdb
docker-compose exec db-veo psql -U veo_user -d veo_db
```

## 💻 [Développement Frontend](#-table-des-matières)

```bash
cd frontend

# Installation des dépendances
npm install

# Développement
npm run dev

# Build de production
npm run build

# Preview du build
npm run preview
```

## 📖 [Documentation](#-table-des-matières)

Pour plus de détails, consultez la documentation dans le dossier `docs/` :

- **[Getting Started](docs/GETTING_STARTED.md)** - Guide de démarrage complet
- **[Catapult Module](docs/CATAPULT_README.md)** - Documentation API données physiques
- **[Veo Module](docs/VEO_README.md)** - Documentation API données tactiques
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Référence rapide des commandes
- **[Architecture](docs/architecture.md)** - Architecture détaillée du système

## 🔄 [Workflow de Développement](#-table-des-matières)

1. **Créer une branche** pour votre fonctionnalité
   ```bash
   git checkout -b feature/nom-feature
   ```

2. **Développer et tester** localement
   ```bash
   docker-compose up -d --build
   cd frontend && npm run dev
   ```

3. **Tester les APIs** via Swagger UI
   - Catapult: http://localhost/api/physical/docs
   - Veo: http://localhost/api/tactical/docs

4. **Commiter et pusher**
   ```bash
   git add .
   git commit -m "Description des changements"
   git push origin feature/nom-feature
   ```

## 🧪 [Tests](#-table-des-matières)

```bash
# Tests backend Veo
docker-compose exec backend-veo pytest

# Tests avec coverage
docker-compose exec backend-veo pytest --cov=app tests/
```

## 👥 [Auteurs](#-table-des-matières)
  
| Author | Role | GitHub | Email |
|--------|------|--------|-------|
| **Loïc Le Guen** | Co-Developer | [https://github.com/loicleguen](https://github.com/loicleguen) | 11510@holbertonstudents.com |
| **Jules Moleins** | Co-Developer | [https://github.com/Roullito](https://github.com/Roullito) | jmoleins@gmail.com |
| **Pierre-Yves Fauconnet** | Co-Developer | [https://github.com/P-Y74](https://github.com/P-Y74) | pfauconnet@proton.me |