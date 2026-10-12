#!/usr/bin/env bash
# Run the local server against the dev or demo database.
# Usage: ./run-local.sh dev | demo [--reset]
# Env vars are set only for this script, so the calling shell stays untouched.
set -euo pipefail
cd "$(dirname "$0")"

mode="${1:-}"
reset="${2:-}"

case "$mode" in
    dev)
        unset DJANGO_SQLITE_PATH KICOMA_DEMO_MODE KICOMA_DEMO_SUPERUSER_PASSWORD
        ;;
    demo)
        export DJANGO_SQLITE_PATH=storage/demo.sqlite3 KICOMA_DEMO_MODE=True
        superuser_key=config/secrets/demo/demo_superuser_password.key
        if [[ -f "$superuser_key" ]]; then
            KICOMA_DEMO_SUPERUSER_PASSWORD="$(cat "$superuser_key")"
            export KICOMA_DEMO_SUPERUSER_PASSWORD
        fi
        new_db=false
        [[ -f "$DJANGO_SQLITE_PATH" ]] || new_db=true
        ./manage.py migrate
        if [[ "$new_db" == true || "$reset" == "--reset" ]]; then
            ./manage.py reset_demo
        fi
        ;;
    *)
        echo "Usage: $0 dev | demo [--reset]" >&2
        exit 1
        ;;
esac

exec ./manage.py runserver_plus 0.0.0.0:8000
