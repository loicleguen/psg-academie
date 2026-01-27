# PSG Académie - Plateforme d'Analyse Football

Plateforme d'analyse complète pour le suivi physique et tactique des joueurs de l'académie PSG, intégrant les données GPS Catapult et les statistiques de match Veo.

## 🏗️ Architecture

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

## 🚀 Démarrage Rapide

### Prérequis
- Docker & Docker Compose
- Node.js 18+ (pour développement frontend)
- Python 3.11+ (pour développement backend local)

### Installation

```bash
# Cloner le repository
git clone <repository-url>
cd psg-academie

# Lancer tous les services avec Docker
docker-compose up -d --build

# Vérifier que tout fonctionne
docker-compose ps
docker-compose logs -f
```

### Accès aux services

Une fois les services démarrés :

- **Frontend** : http://localhost (ou le port configuré)
- **API Catapult** : http://localhost/api/physical/
- **API Veo** : http://localhost/api/tactical/
- **Docs API Catapult** : http://localhost/api/physical/docs
- **Docs API Veo** : http://localhost/api/tactical/docs

### Développement Frontend (mode local)

```bash
cd frontend
npm install
npm run dev
# Disponible sur http://localhost:5173
```

## 📊 Fonctionnalités

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

## 📁 Structure du Projet

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

## 🔧 Commandes Utiles

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

### Frontend

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

## 📖 Documentation

Pour plus de détails, consultez la documentation dans le dossier `docs/` :

- **[Getting Started](docs/GETTING_STARTED.md)** - Guide de démarrage complet
- **[Catapult Module](docs/CATAPULT_README.md)** - Documentation API données physiques
- **[Veo Module](docs/VEO_README.md)** - Documentation API données tactiques
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Référence rapide des commandes
- **[Architecture](docs/architecture.md)** - Architecture détaillée du système

## 🔄 Workflow de Développement

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

## 🧪 Tests

```bash
# Tests backend Veo
docker-compose exec backend-veo pytest

# Tests avec coverage
docker-compose exec backend-veo pytest --cov=app tests/
```

## 🛣️ Roadmap

### Phase 2-3 (À venir)
- [ ] Migration Backend Veo vers SQLModel (uniformisation)
- [ ] Unification des schémas Player/Match entre les deux backends
- [ ] API unifiée fusionnant les données physiques et tactiques
- [ ] Dashboard combiné affichant les deux types de données
- [ ] Système d'authentification et gestion des rôles
- [ ] Export automatique de rapports hebdomadaires

## 🐛 Dépannage

### Le service ne démarre pas
```bash
# Vérifier les logs
docker-compose logs backend-catapult
docker-compose logs backend-veo

# Reconstruire les images
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Erreur de connexion à la base de données
```bash
# Vérifier que PostgreSQL est prêt
docker-compose ps
docker-compose logs db-catapult
docker-compose logs db-veo

# Réinitialiser les volumes si nécessaire
docker-compose down -v
docker-compose up -d
```

### Port déjà utilisé
```bash
# Vérifier les ports utilisés
netstat -tulpn | grep :80
netstat -tulpn | grep :8000
netstat -tulpn | grep :8001

# Modifier les ports dans docker-compose.yml si nécessaire
```

## 📝 Licence

Ce projet est propriétaire de l'Académie PSG.

## 👥 Support

Pour toute question ou problème, consultez la documentation dans le dossier `docs/` ou contactez l'équipe de développement.

---

**Note** : Les deux backends (Catapult et Veo) sont actuellement indépendants pour faciliter la maintenance et les tests. L'unification progressive sera effectuée dans les phases suivantes.
