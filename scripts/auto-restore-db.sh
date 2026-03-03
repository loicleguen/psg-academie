#!/bin/bash
set -euo pipefail

if [ "${SKIP_DB_AUTO_RESTORE:-0}" = "1" ]; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "${REPO_ROOT}" ]; then
  exit 0
fi

CATAPULT_DUMP_FILE="${REPO_ROOT}/psgdb.dump"
VEO_DUMP_FILE="${REPO_ROOT}/veo_db.dump"
CATAPULT_STATE_FILE="${REPO_ROOT}/.git/.last_psgdb_dump_sha"
VEO_STATE_FILE="${REPO_ROOT}/.git/.last_veo_db_dump_sha"

catapult_changed=0
veo_changed=0

if [ -f "${CATAPULT_DUMP_FILE}" ]; then
  catapult_current_sha="$(sha256sum "${CATAPULT_DUMP_FILE}" | awk '{print $1}')"
  catapult_last_sha=""
  if [ -f "${CATAPULT_STATE_FILE}" ]; then
    catapult_last_sha="$(cat "${CATAPULT_STATE_FILE}")"
  fi
  if [ "${catapult_current_sha}" != "${catapult_last_sha}" ]; then
    catapult_changed=1
  fi
fi

if [ -f "${VEO_DUMP_FILE}" ]; then
  veo_current_sha="$(sha256sum "${VEO_DUMP_FILE}" | awk '{print $1}')"
  veo_last_sha=""
  if [ -f "${VEO_STATE_FILE}" ]; then
    veo_last_sha="$(cat "${VEO_STATE_FILE}")"
  fi
  if [ "${veo_current_sha}" != "${veo_last_sha}" ]; then
    veo_changed=1
  fi
fi

if [ "${catapult_changed}" = "0" ] && [ "${veo_changed}" = "0" ]; then
  exit 0
fi

restore_scope=""
if [ "${catapult_changed}" = "1" ] && [ "${veo_changed}" = "1" ]; then
  restore_scope="all"
elif [ "${catapult_changed}" = "1" ]; then
  restore_scope="catapult"
else
  restore_scope="veo"
fi

echo "[db-sync] Dump change detected (scope: ${restore_scope}), restoring local DB..."
"${REPO_ROOT}/scripts/sync-db.sh" restore "${restore_scope}"

if [ -f "${CATAPULT_DUMP_FILE}" ]; then
  sha256sum "${CATAPULT_DUMP_FILE}" | awk '{print $1}' > "${CATAPULT_STATE_FILE}"
fi
if [ -f "${VEO_DUMP_FILE}" ]; then
  sha256sum "${VEO_DUMP_FILE}" | awk '{print $1}' > "${VEO_STATE_FILE}"
fi

echo "[db-sync] Local DB is now aligned with dump file(s)."
