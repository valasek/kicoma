#!/usr/bin/env bash
set -euo pipefail

# --- Configuration ---
REMOTE_HOST="root@162.55.185.37"
REMOTE_TMP_DIR="/tmp/sqlite_copy"
LOCAL_DEST_DIR="./"
CONTAINER_FILTER="svalasek/kicoma"

echo "📡 Connecting to $REMOTE_HOST and exporting SQLite DB..."

ssh "$REMOTE_HOST" bash -s <<REMOTE_SCRIPT
set -euo pipefail

CONTAINER_FILTER="$CONTAINER_FILTER"
REMOTE_TMP_DIR="$REMOTE_TMP_DIR"
mkdir -p "\$REMOTE_TMP_DIR"

echo "🔍 Searching for container..."
CONTAINER_ID=\$(docker ps --format '{{.ID}}' --filter "ancestor=\${CONTAINER_FILTER}" | head -n1)

if [ -z "\$CONTAINER_ID" ]; then
  echo "❌ No container found for \${CONTAINER_FILTER}" >&2
  exit 1
fi
echo "🧩 Found container: \$CONTAINER_ID"

# Detect DB file path automatically
echo "🔎 Searching for *.sqlite3 file inside container..."
DB_PATH_IN_CONTAINER=\$(docker exec "\$CONTAINER_ID" find / -type f -name "*.sqlite3" 2>/dev/null | head -n1 || true)

if [ -z "\$DB_PATH_IN_CONTAINER" ]; then
  echo "❌ No SQLite database file found inside container!" >&2
  exit 1
fi

echo "🗂️ Found database at: \$DB_PATH_IN_CONTAINER"

# Try WAL checkpoint if sqlite3 exists
if docker exec "\$CONTAINER_ID" command -v sqlite3 >/dev/null 2>&1; then
  echo "🧮 Flushing WAL changes..."
  docker exec "\$CONTAINER_ID" sqlite3 "\$DB_PATH_IN_CONTAINER" "PRAGMA wal_checkpoint(FULL);" || \
    echo "⚠️ WAL checkpoint returned non-zero status (ignored)."
else
  echo "⚠️ sqlite3 not installed in container — skipping WAL checkpoint."
fi

# Copy DB and possible WAL/SHM files
for EXT in "" "-wal" "-shm"; do
  SRC="\${DB_PATH_IN_CONTAINER}\${EXT}"
  BASENAME=\$(basename "\$SRC")
  DEST="\${REMOTE_TMP_DIR}/\${BASENAME}"

  if docker exec "\$CONTAINER_ID" test -f "\$SRC"; then
    echo "📦 Copying \$SRC..."
    docker cp "\$CONTAINER_ID:\$SRC" "\$DEST" || echo "⚠️ Failed to copy \$SRC (ignored)"
  fi
done

echo "📋 Copied files:"
ls -lh "\$REMOTE_TMP_DIR" || true
REMOTE_SCRIPT

# Copy from VPS to local machine
echo "⬇️ Copying database files from VPS to local machine..."
scp -r "${REMOTE_HOST}:${REMOTE_TMP_DIR}/" "${LOCAL_DEST_DIR}/sqlite_from_vps"

# Optional cleanup on VPS
ssh "$REMOTE_HOST" "rm -rf ${REMOTE_TMP_DIR}"

echo "✅ All SQLite files successfully fetched to ${LOCAL_DEST_DIR}/sqlite_from_vps"
echo "📂 Files:"
ls -lh "${LOCAL_DEST_DIR}/sqlite_from_vps"
