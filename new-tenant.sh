#!/usr/bin/env bash
# Create Kamal config and secrets for a new customer instance (does not deploy).
#   ./new-tenant.sh <slug> <host>
#   ./new-tenant.sh hospic-xyz hospic-xyz.kicoma.eu
set -euo pipefail
cd "$(dirname "$0")"

slug="${1:-}"
host="${2:-}"
if [[ ! "$slug" =~ ^[a-z0-9][a-z0-9-]{1,40}$ || -z "$host" ]]; then
  echo "Usage: $0 <slug: lowercase letters, digits, dashes> <host>" >&2
  exit 1
fi
if [[ "$slug" == "demo" || -e "config/deploy.$slug.yml" ]]; then
  echo "Destination '$slug' already exists or is reserved." >&2
  exit 1
fi
server=$(grep -m1 -A1 '^  web:' config/deploy.yml | grep -oE '[0-9]+(\.[0-9]+){3}')

mkdir -p "config/secrets/$slug"
python3 -c "import secrets; print(secrets.token_urlsafe(50))" > "config/secrets/$slug/django_secret.key"
python3 -c "import secrets; print(secrets.token_urlsafe(12) + '/')" > "config/secrets/$slug/django_admin_url.key"

cat > ".kamal/secrets.$slug" <<EOF
# Per-instance secrets for destination $slug (shared ones are in .kamal/secrets-common).
DJANGO_SECRET_KEY=\$(cat config/secrets/$slug/django_secret.key)
DJANGO_ADMIN_URL=\$(cat config/secrets/$slug/django_admin_url.key)
EOF

cat > "config/deploy.$slug.yml" <<EOF
# Customer instance: $slug
#   kamal deploy -d $slug
service: kicoma-$slug

servers:
  web:
    - $server

proxy:
  host: $host

volumes:
  - "kicoma_${slug//-/_}_storage:/storage"

env:
  clear:
    DJANGO_ALLOWED_HOSTS: $host
    WEB_CONCURRENCY: 2
EOF

cat <<EOF
Created config/deploy.$slug.yml, .kamal/secrets.$slug and config/secrets/$slug/.
Next steps:
  1. DNS: point $host to $server
  2. kamal deploy -d $slug
  3. kamal app exec -d $slug "./manage.py loaddata dph alergeny druhy-jidla skupiny-stravniku"
     kamal app exec -d $slug "./manage.py shell -c \\"from django.contrib.auth.models import Group; [Group.objects.get_or_create(name=n) for n in ('cook', 'stockkeeper', 'nutrition_advisor', 'admin')]\\""
  4. kamal app exec -d $slug --interactive "./manage.py createsuperuser"
  5. Back up config/secrets/$slug/ outside git; commit config/deploy.$slug.yml and .kamal/secrets.$slug
EOF
