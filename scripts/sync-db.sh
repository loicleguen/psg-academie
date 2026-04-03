#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "❌ Docker Compose introuvable (ni 'docker compose' ni 'docker-compose')."
  exit 1
fi

CATAPULT_DUMP="./psgdb.dump"
VEO_DUMP="./veo_db.dump"

normalize_scope() {
  local raw_scope="${1:-all}"
  case "${raw_scope}" in
    all|catapult|veo)
      echo "${raw_scope}"
      ;;
    *)
      echo "❌ Scope invalide: '${raw_scope}' (valeurs: all|catapult|veo)"
      exit 1
      ;;
  esac
}

restore_catapult_db() {
  if [ ! -f "${CATAPULT_DUMP}" ]; then
    echo "⚠️  ${CATAPULT_DUMP} introuvable, restauration Catapult ignorée."
    return 1
  fi

  echo "🛑 Arrêt du backend Catapult..."
  $COMPOSE_CMD stop backend-catapult

  echo "📋 Copie du dump Catapult dans le conteneur..."
  docker cp "${CATAPULT_DUMP}" psg_db_catapult:/tmp/psgdb.dump

  echo "🗑️  Suppression de l'ancienne DB Catapult..."
  docker exec psg_db_catapult psql -U psguser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='psgdb';" || true
  docker exec psg_db_catapult psql -U psguser -d postgres -c "DROP DATABASE IF EXISTS psgdb;"
  docker exec psg_db_catapult psql -U psguser -d postgres -c "CREATE DATABASE psgdb OWNER psguser;"

  echo "📥 Restauration de la DB Catapult..."
  docker exec psg_db_catapult pg_restore -U psguser -d psgdb --clean --if-exists /tmp/psgdb.dump

  echo "🚀 Redémarrage du backend Catapult..."
  $COMPOSE_CMD start backend-catapult

  echo "✓ DB Catapult importée avec succès."
  return 0
}

restore_veo_db() {
  if [ ! -f "${VEO_DUMP}" ]; then
    echo "⚠️  ${VEO_DUMP} introuvable, restauration Veo ignorée."
    return 1
  fi

  echo "🛑 Arrêt du backend Veo..."
  $COMPOSE_CMD stop backend-veo

  echo "📋 Copie du dump Veo dans le conteneur..."
  docker cp "${VEO_DUMP}" psg_db_veo:/tmp/veo_db.dump

  echo "🗑️  Suppression de l'ancienne DB Veo..."
  docker exec psg_db_veo psql -U veo_user -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='veo_db';" || true
  docker exec psg_db_veo psql -U veo_user -d postgres -c "DROP DATABASE IF EXISTS veo_db;"
  docker exec psg_db_veo psql -U veo_user -d postgres -c "CREATE DATABASE veo_db OWNER veo_user;"

  echo "📥 Restauration de la DB Veo..."
  docker exec psg_db_veo pg_restore -U veo_user -d veo_db --clean --if-exists /tmp/veo_db.dump

  echo "🚀 Redémarrage du backend Veo..."
  $COMPOSE_CMD start backend-veo

  echo "✓ DB Veo importée avec succès."
  return 0
}

restore_scope() {
  local scope="$1"
  local restored_any=0

  case "${scope}" in
    all)
      if restore_catapult_db; then
        restored_any=1
      fi
      if restore_veo_db; then
        restored_any=1
      fi
      ;;
    catapult)
      if [ ! -f "${CATAPULT_DUMP}" ]; then
        echo "❌ ${CATAPULT_DUMP} introuvable dans $(pwd)"
        exit 1
      fi
      restore_catapult_db
      restored_any=1
      ;;
    veo)
      if [ ! -f "${VEO_DUMP}" ]; then
        echo "❌ ${VEO_DUMP} introuvable dans $(pwd)"
        exit 1
      fi
      restore_veo_db
      restored_any=1
      ;;
  esac

  if [ "${restored_any}" -eq 0 ]; then
    echo "❌ Aucun dump trouvé. Attendu: ${CATAPULT_DUMP} et/ou ${VEO_DUMP}"
    exit 1
  fi
}

push_scope() {
  local scope="$1"
  local commit_files=()

  echo "📤 Export des DB (${scope}) vers le repo..."
  case "${scope}" in
    all)
      docker exec psg_db_catapult pg_dump -U psguser -Fc -d psgdb -f /tmp/psgdb.dump
      docker cp psg_db_catapult:/tmp/psgdb.dump "${CATAPULT_DUMP}"
      docker exec psg_db_veo pg_dump -U veo_user -Fc -d veo_db -f /tmp/veo_db.dump
      docker cp psg_db_veo:/tmp/veo_db.dump "${VEO_DUMP}"
      git add "${CATAPULT_DUMP}" "${VEO_DUMP}"
      commit_files=("${CATAPULT_DUMP}" "${VEO_DUMP}")
      ;;
    catapult)
      docker exec psg_db_catapult pg_dump -U psguser -Fc -d psgdb -f /tmp/psgdb.dump
      docker cp psg_db_catapult:/tmp/psgdb.dump "${CATAPULT_DUMP}"
      git add "${CATAPULT_DUMP}"
      commit_files=("${CATAPULT_DUMP}")
      ;;
    veo)
      docker exec psg_db_veo pg_dump -U veo_user -Fc -d veo_db -f /tmp/veo_db.dump
      docker cp psg_db_veo:/tmp/veo_db.dump "${VEO_DUMP}"
      git add "${VEO_DUMP}"
      commit_files=("${VEO_DUMP}")
      ;;
  esac

  if git diff --cached --quiet -- "${commit_files[@]}"; then
    echo "ℹ️  Aucun changement de dump à commit."
  else
    git commit -m "DB sync (${scope}): $(date '+%Y-%m-%d %H:%M')" -- "${commit_files[@]}"
  fi
  git push
  echo "✓ DB exportée et poussée sur GitHub."
  echo "➜ Les autres devs font: git pull (auto-restore) ou ./scripts/sync-db.sh pull ${scope}"
}

ACTION="${1:-}"
SCOPE="$(normalize_scope "${2:-all}")"

case "${ACTION}" in
  push)
    push_scope "${SCOPE}"
    ;;

  pull)
    echo "📥 Import des DB (${SCOPE}) depuis le repo..."
    SKIP_DB_AUTO_RESTORE=1 git pull
    restore_scope "${SCOPE}"
    ;;

  restore)
    echo "📥 Restauration locale des DB (${SCOPE}) depuis dump..."
    restore_scope "${SCOPE}"
    ;;

  *)
    echo "Usage: ./scripts/sync-db.sh [push|pull|restore] [all|catapult|veo]"
    echo ""
    echo "  push [scope]    - Exporter DB locale(s) et pousser sur GitHub"
    echo "  pull [scope]    - Pull git puis restaurer DB locale(s)"
    echo "  restore [scope] - Restaurer DB locale(s) depuis dump sans git pull"
    echo ""
    echo "  scope: all (défaut) | catapult | veo"
    exit 1
    ;;
esac
