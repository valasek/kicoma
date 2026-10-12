#!/usr/bin/env bash
# Fetch the SQLite DB of one instance:  ./fetch_remote_sqlite.sh <destination>   e.g. hospic-cercany
set -euo pipefail
cd "$(dirname "$0")"

DESTINATION="${1:-}"
if [[ -z "$DESTINATION" || ! -f "config/deploy.${DESTINATION}.yml" ]]; then
  echo "Usage: $0 <destination>  (one of: $(ls config/deploy.*.yml | sed -E 's#config/deploy\.(.*)\.yml#\1#' | tr '\n' ' '))" >&2
  exit 1
fi
SERVICE=$(grep -m1 -E '^service:' "config/deploy.${DESTINATION}.yml" | awk '{print $2}')

# --- Configuration ---
REMOTE_HOST="root@162.55.185.37"
LOCAL_DEST_DIR="./sqlite_from_vps/${DESTINATION}"

mkdir -p "${LOCAL_DEST_DIR}"
LOCAL_TMP=$(mktemp "${LOCAL_DEST_DIR}/.backup.XXXXXX")
trap 'rm -f "$LOCAL_TMP"' EXIT

echo "Exporting a consistent SQLite snapshot of $DESTINATION (service $SERVICE)..."
ssh "$REMOTE_HOST" bash -s -- "$SERVICE" > "$LOCAL_TMP" <<'REMOTE_SCRIPT'
set -euo pipefail
SERVICE="$1"
CONTAINER_ID=$(docker ps --format '{{.ID}}' --filter "label=service=${SERVICE}" --filter "label=role=web" | head -n1)
if [[ -z "$CONTAINER_ID" ]]; then
  echo "No web container found for service ${SERVICE}" >&2
  exit 1
fi
docker exec -i "$CONTAINER_ID" python - <<'PY'
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from django.conf import settings

database = settings.DATABASES["default"]
if database["ENGINE"] != "django.db.backends.sqlite3":
    raise RuntimeError("The configured database is not SQLite")
source_uri = Path(database["NAME"]).resolve().as_uri() + "?mode=ro"
with tempfile.TemporaryDirectory() as directory:
    snapshot = Path(directory) / "backup.sqlite3"
    with sqlite3.connect(source_uri, uri=True) as source:
        with sqlite3.connect(snapshot) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("SQLite backup integrity check failed")
    with snapshot.open("rb") as backup:
        shutil.copyfileobj(backup, sys.stdout.buffer)
PY
REMOTE_SCRIPT
rm -f -- "${LOCAL_DEST_DIR}/kicoma.sqlite3-wal" "${LOCAL_DEST_DIR}/kicoma.sqlite3-shm"
mv "$LOCAL_TMP" "${LOCAL_DEST_DIR}/kicoma.sqlite3"

echo "SQLite snapshot fetched to ${LOCAL_DEST_DIR}/kicoma.sqlite3"
ls -lh "${LOCAL_DEST_DIR}"
