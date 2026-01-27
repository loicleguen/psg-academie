# PSG Analytics - Architecture Unifiée

## 🏗️ Architecture

Ce repo intègre maintenant **deux backends complémentaires** :

### Backend Catapult (Physique)
- **Port interne** : 8000
- **Route nginx** : `/api/physical/*`
- **Données** : GPS, distance, vitesse, accélération, charge physique
- **Base de données** : PostgreSQL 16 (psg_db_catapult)
- **ORM** : SQLModel

### Backend Veo (Tactique)
- **Port interne** : 8001
- **Route nginx** : `/api/tactical/*`
- **Données** : Matchs, buts, passes, statistiques tactiques
- **Base de données** : PostgreSQL 16 (psg_db_veo)
- **ORM** : SQLAlchemy

### Nginx (Reverse Proxy)
- **Port** : 80 (HTTP) / 443 (HTTPS)
- Route automatiquement vers le bon backend selon l'URL
- Sert également le frontend React

## 🚀 Démarrage

```bash
# Lancer tous les services
docker-compose up -d --build

# Vérifier l'état
docker-compose ps

# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down
```

## 📡 Accès aux APIs

Grâce à nginx, tout passe par le port 80 :

```bash
# API Catapult (physique)
curl http://localhost/api/physical/...

# API Veo (tactique)
curl http://localhost/api/tactical/...
```

## 🗂️ Structure

```
psg-academie-fusion/
├── backend-catapult/      # Données physiques (SQLModel)
├── backend-veo/           # Données tactiques (SQLAlchemy)
├── frontend/              # React app
├── nginx.conf             # Configuration routing
├── docker-compose.yml     # Orchestration complète
└── certs/                 # Certificats SSL
```

## 🔄 Prochaines étapes (Phase 2-3)

1. **Migration vers SQLModel** : Uniformiser Veo sur SQLModel
2. **Unification des schémas** : Créer des relations Player/Match communes
3. **Backend unifié** : Fusionner progressivement les APIs

## 📝 Notes

- Les deux backends restent **totalement indépendants** pour l'instant
- Pas de couplage, facile à maintenir et tester
- L'unification se fera progressivement
