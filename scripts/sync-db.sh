#!/bin/bash
set -e

cd "$(dirname "$0")/.."

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "❌ Docker Compose introuvable (ni 'docker compose' ni 'docker-compose')."
  exit 1
fi

restore_db() {
  if [ ! -f "./psgdb.dump" ]; then
    echo "❌ psgdb.dump introuvable dans $(pwd)"
    exit 1
  fi

  echo "🛑 Arrêt du backend..."
  $COMPOSE_CMD stop backend-catapult

  echo "📋 Copie du dump dans le conteneur..."
  docker cp ./psgdb.dump psg_db_catapult:/tmp/psgdb.dump

  echo "🗑️  Suppression de l'ancienne DB..."
  docker exec psg_db_catapult psql -U psguser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='psgdb';" || true
  docker exec psg_db_catapult psql -U psguser -d postgres -c "DROP DATABASE IF EXISTS psgdb;"
  docker exec psg_db_catapult psql -U psguser -d postgres -c "CREATE DATABASE psgdb OWNER psguser;"

  echo "📥 Restauration de la nouvelle DB..."
  docker exec psg_db_catapult pg_restore -U psguser -d psgdb --clean --if-exists /tmp/psgdb.dump

  echo "🚀 Redémarrage du backend..."
  $COMPOSE_CMD start backend-catapult

  echo "✓ DB importée avec succès !"
}

case $1 in
  push)
    echo "📤 Export de votre DB vers le repo..."
    docker exec psg_db_catapult pg_dump -U psguser -Fc -d psgdb -f /tmp/psgdb.dump
    docker cp psg_db_catapult:/tmp/psgdb.dump ./psgdb.dump
    git add psgdb.dump
    git commit -m "DB sync: $(date '+%Y-%m-%d %H:%M')"
    git push
    echo "✓ DB exportée et poussée sur GitHub"
    echo "➜ Jules doit faire: ./scripts/sync-db.sh pull"
    ;;
    
  pull)
    echo "📥 Import de la DB depuis le repo..."
    SKIP_DB_AUTO_RESTORE=1 git pull
    restore_db
    ;;

  restore)
    echo "📥 Restauration de la DB locale depuis psgdb.dump..."
    restore_db
    ;;
    
  *)
    echo "Usage: ./scripts/sync-db.sh [push|pull|restore]"
    echo ""
    echo "  push  - Exporter votre DB et la pousser sur GitHub"
    echo "  pull  - Importer la DB depuis GitHub (écrase votre DB locale)"
    echo "  restore - Restaurer la DB locale depuis psgdb.dump sans git pull"
    exit 1
    ;;
esac
