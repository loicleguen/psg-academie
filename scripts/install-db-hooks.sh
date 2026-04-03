#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_DIR="${REPO_ROOT}/.git/hooks"

mkdir -p "${HOOK_DIR}"

cat > "${HOOK_DIR}/post-merge" <<'EOF'
#!/bin/bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
"${REPO_ROOT}/scripts/auto-restore-db.sh"
EOF

cat > "${HOOK_DIR}/post-checkout" <<'EOF'
#!/bin/bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
"${REPO_ROOT}/scripts/auto-restore-db.sh"
EOF

chmod +x "${HOOK_DIR}/post-merge" "${HOOK_DIR}/post-checkout"
chmod +x "${REPO_ROOT}/scripts/auto-restore-db.sh" "${REPO_ROOT}/scripts/sync-db.sh"

if [ -f "${REPO_ROOT}/psgdb.dump" ]; then
  sha256sum "${REPO_ROOT}/psgdb.dump" | awk '{print $1}' > "${REPO_ROOT}/.git/.last_psgdb_dump_sha"
else
  rm -f "${REPO_ROOT}/.git/.last_psgdb_dump_sha"
fi

if [ -f "${REPO_ROOT}/veo_db.dump" ]; then
  sha256sum "${REPO_ROOT}/veo_db.dump" | awk '{print $1}' > "${REPO_ROOT}/.git/.last_veo_db_dump_sha"
else
  rm -f "${REPO_ROOT}/.git/.last_veo_db_dump_sha"
fi

echo "✓ Hooks installés:"
echo "  - .git/hooks/post-merge"
echo "  - .git/hooks/post-checkout"
echo "✓ Auto restore activé quand psgdb.dump et/ou veo_db.dump changent."
echo "ℹ️  Le push DB reste manuel: ./scripts/sync-db.sh push [all|catapult|veo]"
