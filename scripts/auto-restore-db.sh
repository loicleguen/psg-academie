#!/bin/bash
set -euo pipefail

if [ "${SKIP_DB_AUTO_RESTORE:-0}" = "1" ]; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "${REPO_ROOT}" ]; then
  exit 0
fi

DUMP_FILE="${REPO_ROOT}/psgdb.dump"
STATE_FILE="${REPO_ROOT}/.git/.last_psgdb_dump_sha"

if [ ! -f "${DUMP_FILE}" ]; then
  exit 0
fi

current_sha="$(sha256sum "${DUMP_FILE}" | awk '{print $1}')"
last_sha=""
if [ -f "${STATE_FILE}" ]; then
  last_sha="$(cat "${STATE_FILE}")"
fi

if [ "${current_sha}" = "${last_sha}" ]; then
  exit 0
fi

echo "[db-sync] psgdb.dump changed, restoring local DB..."
"${REPO_ROOT}/scripts/sync-db.sh" restore
echo "${current_sha}" > "${STATE_FILE}"
echo "[db-sync] Local DB is now aligned with psgdb.dump."
